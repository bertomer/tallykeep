"""Persist-first-emit-second pattern (spec module 01).

Critical events — the ones whose loss would mean wrong information about
reality — are written to ``event_emission_log`` BEFORE being published on the
bus. If the publish fails (subscriber outage, Redis blip, restart in flight),
the row is the source of truth and the AuditReconciler subscriber re-emits
later.

Subscribers acknowledge a critical event by calling ``acknowledge(event_id)``
on the ``PersistentEmitter``, which sets ``event_emission_log.acknowledged_at``.
The reconciler only watches rows where that column is still NULL after a
configurable grace period.

Non-critical (ephemeral) events bypass this layer and go straight to the
``EventBus`` — losing a "now categorize this transaction" prompt is acceptable
because the row in ``ledger_entry`` already exists.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from tallykeep.infrastructure.event_bus import Event, EventBus
from tallykeep.models import EventEmissionLogRow


logger = logging.getLogger(__name__)


# Marker injected into the published payload so reconciled (re-emitted) events
# are distinguishable from their first publish. Subscribers can ignore replays
# they have already processed.
REPLAY_MARKER_KEY = "__replay__"


class PersistentEmitter:
    """Wrap an EventBus with persist-first semantics for critical events.

    Use ``emit_critical(topic, payload)`` for events that must survive subscriber
    outages. Use ``emit(topic, payload)`` for ephemeral events.

    Thread-safety: all methods are safe to call concurrently — the underlying
    EventBus and SQLAlchemy session factory both handle their own locking.
    """

    def __init__(
        self,
        bus: EventBus,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._bus = bus
        self._session_factory = session_factory

    # --- emission ----------------------------------------------------------

    def emit(self, topic: str, payload: dict[str, Any]) -> Event:
        """Ephemeral publish — no persistence."""
        return self._bus.publish(topic, payload)

    def emit_critical(self, topic: str, payload: dict[str, Any]) -> Event:
        """Persist first, then publish.

        Returns the Event with `id` matching the persisted row. Subscribers can
        use that id to call `acknowledge()`.

        If the persist step fails the call raises and nothing is published. If
        the publish step fails after a successful persist, the row remains
        unacknowledged and the reconciler re-emits it later — exactly the
        property the persist-first pattern is designed to give us.
        """
        # Pre-allocate a UUID so the row id and the emitted Event id match.
        from uuid import uuid4

        event_id = uuid4()

        with self._session_factory() as session:
            session.add(
                EventEmissionLogRow(
                    id=event_id,
                    topic=topic,
                    payload=payload,
                    is_critical=True,
                )
            )
            session.commit()

        try:
            event = self._bus.publish(topic, payload, event_id=event_id)
        except Exception:  # noqa: BLE001 — log and let the reconciler recover
            logger.exception(
                "publish failed for critical event topic=%s id=%s; "
                "audit reconciler will re-emit",
                topic,
                event_id,
            )
            # Synthesize an Event so callers still get a usable handle.
            event = Event(
                topic=topic,
                payload=payload,
                timestamp=datetime.now(UTC),
                id=event_id,
            )
        return event

    # --- acknowledgement ---------------------------------------------------

    def acknowledge(self, event_id: UUID) -> bool:
        """Mark a persisted event as delivered.

        Returns True if the row was found and updated; False if the event was
        not persisted (e.g. ephemeral event id).
        """
        with self._session_factory() as session:
            stmt = (
                update(EventEmissionLogRow)
                .where(
                    EventEmissionLogRow.id == event_id,
                    EventEmissionLogRow.acknowledged_at.is_(None),
                )
                .values(acknowledged_at=datetime.now(UTC))
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def is_acknowledged(self, event_id: UUID) -> bool:
        """Test helper / introspection — was this event acknowledged?"""
        with self._session_factory() as session:
            row = session.get(EventEmissionLogRow, event_id)
            return row is not None and row.acknowledged_at is not None


class AuditReconciler:
    """Periodic re-emitter for unacknowledged critical events (spec module 01).

    Scans `event_emission_log` for rows where:
      - `is_critical` is True
      - `acknowledged_at` is NULL
      - `emitted_at` is older than `grace_period` seconds ago

    Each matching row is re-published with the `REPLAY_MARKER_KEY` set in the
    payload so subscribers can distinguish replays. The reconciler does NOT
    acknowledge on behalf of subscribers — the subscriber must still call
    `PersistentEmitter.acknowledge` once it has processed the replay.

    The grace period gives the original handler a chance to ack before we
    consider the event lost. Typical value: 5 minutes. In tests we use a much
    smaller value to exercise the recovery path.
    """

    def __init__(
        self,
        bus: EventBus,
        session_factory: sessionmaker[Session],
        *,
        grace_period: timedelta = timedelta(minutes=5),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._bus = bus
        self._session_factory = session_factory
        self._grace_period = grace_period
        self._clock = clock

    def run_once(self) -> int:
        """Find candidates older than the grace period and re-emit each.

        Returns the number of events re-emitted.
        """
        cutoff = self._clock() - self._grace_period

        with self._session_factory() as session:
            stmt = select(EventEmissionLogRow).where(
                EventEmissionLogRow.is_critical.is_(True),
                EventEmissionLogRow.acknowledged_at.is_(None),
                EventEmissionLogRow.emitted_at < cutoff,
            )
            rows = list(session.execute(stmt).scalars().all())

        for row in rows:
            payload = dict(row.payload or {})
            payload[REPLAY_MARKER_KEY] = True
            try:
                self._bus.publish(row.topic, payload, event_id=row.id)
            except Exception:  # noqa: BLE001 — keep going; we'll retry next run
                logger.exception(
                    "AuditReconciler failed to re-emit topic=%s id=%s",
                    row.topic,
                    row.id,
                )

        return len(rows)


__all__ = [
    "AuditReconciler",
    "PersistentEmitter",
    "REPLAY_MARKER_KEY",
]
