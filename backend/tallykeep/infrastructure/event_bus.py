"""Event bus — interface plus in-memory and Redis backends.

Spec module 01: domain events flow on a bus. Producers publish to a topic; many
subscribers can listen, with no coupling between them.

Topic shape: dotted segments like ``chain.tx.confirmed`` or ``treasury.sweep.executed``.
Pattern matching uses a single ``*`` wildcard per segment-or-tail:
- ``*`` matches every topic
- ``chain.*`` matches ``chain.tx.confirmed``, ``chain.block.new``, etc.
- ``chain.tx.confirmed`` matches that exact topic only

Two backends:
- ``InMemoryEventBus`` — synchronous dispatch, used for unit tests and where the
  bus does not cross processes.
- ``RedisEventBus`` — production backend per spec; uses Redis pub/sub.

Both implementations satisfy the same ABC, so subscribers and publishers do not
care which backend is in use.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    """An event delivered to a subscriber.

    `id` is set when the event was published via the persist-first emitter
    (M2.3). For non-persistent publishes, `id` is generated fresh per event so
    subscribers always have a unique identifier they can log or de-dup on.
    """

    topic: str
    payload: dict[str, Any]
    timestamp: datetime
    id: UUID = field(default_factory=uuid4)


EventHandler = Callable[[Event], None]


class Subscription(ABC):
    """A token returned from `subscribe`. Calling unsubscribe stops delivery."""

    @abstractmethod
    def unsubscribe(self) -> None: ...


# --- pattern matching ------------------------------------------------------------

_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a topic pattern to a regex.

    `*` becomes `.*`, dots are escaped literally. The pattern is anchored at both
    ends so partial matches do not leak between unrelated topics.
    """
    if pattern in _PATTERN_CACHE:
        return _PATTERN_CACHE[pattern]
    # Escape dots, then turn the literal-escaped \* back into a regex .*
    escaped = re.escape(pattern).replace(r"\*", ".*")
    compiled = re.compile(f"^{escaped}$")
    _PATTERN_CACHE[pattern] = compiled
    return compiled


def topic_matches_pattern(topic: str, pattern: str) -> bool:
    """True if `topic` matches `pattern` under our wildcard rules."""
    return bool(_compile_pattern(pattern).match(topic))


# --- bus interface ---------------------------------------------------------------


class EventBus(ABC):
    @abstractmethod
    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        event_id: UUID | None = None,
    ) -> Event:
        """Publish an event. Returns the Event object that was sent."""

    @abstractmethod
    def subscribe(
        self,
        patterns: list[str],
        handler: EventHandler,
    ) -> Subscription: ...

    @abstractmethod
    def close(self) -> None:
        """Tear down the bus, stopping delivery threads and closing connections."""


# --- in-memory implementation ----------------------------------------------------


@dataclass
class _InMemorySubscription(Subscription):
    bus: InMemoryEventBus
    sub_id: UUID

    def unsubscribe(self) -> None:
        self.bus._remove_subscription(self.sub_id)


class InMemoryEventBus(EventBus):
    """Synchronous, in-process bus.

    `publish` invokes every matching handler before returning. Handler exceptions
    are caught and logged so one bad subscriber does not poison the rest, matching
    the production semantics where Redis pub/sub failures on one subscriber do not
    affect others.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Each subscription is recorded as (sub_id, [patterns], handler).
        self._subs: list[tuple[UUID, list[str], EventHandler]] = []
        self._closed = False

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        event_id: UUID | None = None,
    ) -> Event:
        if self._closed:
            raise RuntimeError("InMemoryEventBus is closed")
        event = Event(
            topic=topic,
            payload=payload,
            timestamp=datetime.now(UTC),
            id=event_id or uuid4(),
        )
        # Snapshot subscribers so handler-induced subscribe/unsubscribe calls do
        # not mutate the iteration list.
        with self._lock:
            snapshot = list(self._subs)
        for _, patterns, handler in snapshot:
            if any(topic_matches_pattern(topic, p) for p in patterns):
                try:
                    handler(event)
                except Exception:  # noqa: BLE001 — logged and swallowed
                    logger.exception(
                        "subscriber raised handling event topic=%s id=%s",
                        topic,
                        event.id,
                    )
        return event

    def subscribe(
        self,
        patterns: list[str],
        handler: EventHandler,
    ) -> Subscription:
        if not patterns:
            raise ValueError("subscribe requires at least one pattern")
        sub_id = uuid4()
        with self._lock:
            self._subs.append((sub_id, list(patterns), handler))
        return _InMemorySubscription(self, sub_id)

    def _remove_subscription(self, sub_id: UUID) -> None:
        with self._lock:
            self._subs = [s for s in self._subs if s[0] != sub_id]

    def close(self) -> None:
        with self._lock:
            self._subs.clear()
            self._closed = True

    # Test helper.
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subs)


# --- Redis implementation --------------------------------------------------------


@dataclass
class _RedisSubscription(Subscription):
    bus: RedisEventBus
    sub_id: UUID

    def unsubscribe(self) -> None:
        self.bus._remove_subscription(self.sub_id)


class RedisEventBus(EventBus):
    """Redis pub/sub backend.

    A single background thread reads messages from the underlying Redis pubsub
    connection and dispatches them to the registered handlers. New subscribers add
    their patterns dynamically via `psubscribe`; closing the bus shuts down the
    thread and the connection.

    Topics are sent as JSON-encoded payloads. Subscribers receive the same Event
    shape as the in-memory bus.
    """

    # Internal control channel — not advertised; used to wake the read loop on
    # shutdown so we don't block forever in `get_message`.
    _CONTROL_CHANNEL = "_tallykeep_control"

    def __init__(self, redis_url: str) -> None:
        # Local imports so test environments without `redis` installed (none, in
        # practice — it's a hard dependency) don't pay an import cost just for
        # the in-memory bus.
        import redis

        self._redis = redis.Redis.from_url(redis_url, decode_responses=False)
        # Verify connectivity early — better to fail at construction than to
        # crash the worker thread on first publish.
        self._redis.ping()
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe(self._CONTROL_CHANNEL)

        self._lock = threading.RLock()
        self._subs: list[tuple[UUID, list[str], EventHandler]] = []
        self._active_patterns: set[str] = set()
        self._closed = threading.Event()
        self._thread = threading.Thread(
            target=self._read_loop,
            name="tallykeep-event-bus",
            daemon=True,
        )
        self._thread.start()

    # --- publish/subscribe surface -------------------------------------------

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        event_id: UUID | None = None,
    ) -> Event:
        if self._closed.is_set():
            raise RuntimeError("RedisEventBus is closed")
        event = Event(
            topic=topic,
            payload=payload,
            timestamp=datetime.now(UTC),
            id=event_id or uuid4(),
        )
        envelope = {
            "id": str(event.id),
            "topic": event.topic,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
        }
        self._redis.publish(topic, json.dumps(envelope).encode("utf-8"))
        return event

    def subscribe(
        self,
        patterns: list[str],
        handler: EventHandler,
    ) -> Subscription:
        if not patterns:
            raise ValueError("subscribe requires at least one pattern")
        sub_id = uuid4()
        new_patterns: list[str] = []
        with self._lock:
            self._subs.append((sub_id, list(patterns), handler))
            for pattern in patterns:
                if pattern not in self._active_patterns:
                    self._active_patterns.add(pattern)
                    new_patterns.append(pattern)
        # Translate our `*` wildcard into Redis's `*` (both happen to be the same).
        # Issue psubscribe outside the lock so a slow Redis call cannot block
        # other publishers.
        for pattern in new_patterns:
            self._pubsub.psubscribe(_pattern_to_redis(pattern))
        return _RedisSubscription(self, sub_id)

    def _remove_subscription(self, sub_id: UUID) -> None:
        with self._lock:
            self._subs = [s for s in self._subs if s[0] != sub_id]
            # We deliberately do not punsubscribe — channel-level cleanup is
            # cheap on the Redis side and would complicate concurrent sub/unsub.

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        # Wake the read loop with a control message so the thread exits promptly.
        try:
            self._redis.publish(self._CONTROL_CHANNEL, b"shutdown")
        except Exception:  # noqa: BLE001 — best-effort during shutdown
            pass
        self._thread.join(timeout=2.0)
        try:
            self._pubsub.close()
        finally:
            self._redis.close()

    # --- internal: read loop --------------------------------------------------

    def _read_loop(self) -> None:
        while not self._closed.is_set():
            try:
                message = self._pubsub.get_message(timeout=1.0)
            except Exception:  # noqa: BLE001 — keep looping unless asked to stop
                logger.exception("RedisEventBus get_message failed; retrying")
                continue

            if not message:
                continue
            if message.get("type") not in ("message", "pmessage"):
                continue
            channel = message.get("channel")
            if isinstance(channel, bytes):
                channel = channel.decode("utf-8")
            if channel == self._CONTROL_CHANNEL:
                # Shutdown signal or a stray write to the control channel.
                continue

            data = message.get("data", b"")
            if not isinstance(data, (bytes, bytearray)):
                continue
            try:
                envelope = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(
                    "RedisEventBus dropped malformed event on channel=%s", channel
                )
                continue

            event = self._envelope_to_event(envelope)
            self._dispatch(event)

    @staticmethod
    def _envelope_to_event(envelope: dict[str, Any]) -> Event:
        return Event(
            topic=str(envelope["topic"]),
            payload=dict(envelope.get("payload", {})),
            timestamp=datetime.fromisoformat(envelope["timestamp"]),
            id=UUID(envelope["id"]),
        )

    def _dispatch(self, event: Event) -> None:
        with self._lock:
            snapshot = list(self._subs)
        for _, patterns, handler in snapshot:
            if any(topic_matches_pattern(event.topic, p) for p in patterns):
                try:
                    handler(event)
                except Exception:  # noqa: BLE001 — logged and swallowed
                    logger.exception(
                        "subscriber raised handling event topic=%s id=%s",
                        event.topic,
                        event.id,
                    )

    # --- diagnostics ----------------------------------------------------------

    def is_healthy(self) -> bool:
        if self._closed.is_set():
            return False
        try:
            return bool(self._redis.ping())
        except Exception:  # noqa: BLE001
            return False


def _pattern_to_redis(pattern: str) -> str:
    """Translate our pattern syntax to Redis's pubsub-pattern syntax.

    Both use `*` as a multi-character wildcard, so the pattern is identical. The
    function exists to make the translation point explicit and to give us a single
    place to evolve the syntax later (e.g., adding `?` or `+` wildcards).
    """
    return pattern


__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "InMemoryEventBus",
    "RedisEventBus",
    "Subscription",
    "topic_matches_pattern",
]
