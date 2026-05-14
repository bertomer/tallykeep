"""RedisEventBus integration tests.

Pub/sub delivery is asynchronous, so each test waits on a `threading.Event` that the
handler sets when the expected message arrives. Tests use a unique topic prefix per
test so concurrent runs do not cross-talk over a shared Redis instance.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Iterator

import pytest

from tallykeep.infrastructure.event_bus import Event, RedisEventBus


pytestmark = pytest.mark.integration


# Receiving a pub/sub message after subscribe should be quick on a local Redis;
# 2 seconds is generous and covers slow CI runners.
DELIVERY_TIMEOUT_SECONDS = 2.0


@pytest.fixture()
def topic_prefix() -> str:
    """Per-test prefix so tests can run concurrently without seeing each other's events."""
    return f"test_{secrets.token_hex(4)}"


@pytest.fixture()
def bus(redis_url: str) -> Iterator[RedisEventBus]:
    b = RedisEventBus(redis_url)
    try:
        yield b
    finally:
        b.close()


def _wait_for(event: threading.Event, timeout: float = DELIVERY_TIMEOUT_SECONDS) -> bool:
    return event.wait(timeout=timeout)


# --- delivery -------------------------------------------------------------------


def test_publish_then_subscribe_delivers_event(
    bus: RedisEventBus, topic_prefix: str
) -> None:
    received: list[Event] = []
    arrived = threading.Event()

    def handler(event: Event) -> None:
        received.append(event)
        arrived.set()

    bus.subscribe([f"{topic_prefix}.*"], handler)
    # Small grace period so psubscribe propagates before the publish hits the
    # server; without this, a fast test can publish before Redis registers the
    # pattern.
    time.sleep(0.05)

    bus.publish(f"{topic_prefix}.greeting", {"hello": "world"})

    assert _wait_for(arrived), "event was not delivered within timeout"
    assert len(received) == 1
    assert received[0].topic == f"{topic_prefix}.greeting"
    assert received[0].payload == {"hello": "world"}


def test_event_id_survives_round_trip(
    bus: RedisEventBus, topic_prefix: str
) -> None:
    """An explicit event_id passed to publish must arrive intact at the subscriber.
    This is what lets the persist-first emitter (M2.3) tie published events back
    to their event_emission_log row."""
    from uuid import uuid4

    received_id: list = []
    arrived = threading.Event()

    def handler(event: Event) -> None:
        received_id.append(event.id)
        arrived.set()

    bus.subscribe([f"{topic_prefix}.*"], handler)
    time.sleep(0.05)

    expected_id = uuid4()
    bus.publish(f"{topic_prefix}.x", {"k": "v"}, event_id=expected_id)

    assert _wait_for(arrived)
    assert received_id == [expected_id]


def test_pattern_matches_select_subscribers(
    bus: RedisEventBus, topic_prefix: str
) -> None:
    """A second subscriber on a non-matching pattern must NOT receive the event."""
    chain_received: list[Event] = []
    treasury_received: list[Event] = []
    chain_arrived = threading.Event()

    def chain_handler(e: Event) -> None:
        chain_received.append(e)
        chain_arrived.set()

    bus.subscribe([f"{topic_prefix}.chain.*"], chain_handler)
    bus.subscribe([f"{topic_prefix}.treasury.*"], treasury_received.append)
    time.sleep(0.05)

    bus.publish(f"{topic_prefix}.chain.tx.confirmed", {"txid": "abc"})

    assert _wait_for(chain_arrived)
    # Give any erroneous treasury delivery a chance to land.
    time.sleep(0.1)
    assert len(chain_received) == 1
    assert treasury_received == []


def test_multiple_subscribers_each_receive(
    bus: RedisEventBus, topic_prefix: str
) -> None:
    a_arrived = threading.Event()
    b_arrived = threading.Event()
    a_received: list[Event] = []
    b_received: list[Event] = []

    def a(e: Event) -> None:
        a_received.append(e)
        a_arrived.set()

    def b(e: Event) -> None:
        b_received.append(e)
        b_arrived.set()

    bus.subscribe([f"{topic_prefix}.*"], a)
    bus.subscribe([f"{topic_prefix}.*"], b)
    time.sleep(0.05)

    bus.publish(f"{topic_prefix}.x", {"k": "v"})

    assert _wait_for(a_arrived)
    assert _wait_for(b_arrived)
    assert len(a_received) == 1
    assert len(b_received) == 1


def test_unsubscribe_stops_delivery(
    bus: RedisEventBus, topic_prefix: str
) -> None:
    received: list[Event] = []
    arrived_first = threading.Event()

    def handler(e: Event) -> None:
        received.append(e)
        arrived_first.set()

    sub = bus.subscribe([f"{topic_prefix}.*"], handler)
    time.sleep(0.05)

    bus.publish(f"{topic_prefix}.first", {})
    assert _wait_for(arrived_first)
    assert len(received) == 1

    sub.unsubscribe()
    bus.publish(f"{topic_prefix}.second", {})

    # Allow time for any erroneous late delivery.
    time.sleep(0.1)
    assert len(received) == 1


# --- failure isolation ---------------------------------------------------------


def test_failing_handler_does_not_break_other_subscribers(
    bus: RedisEventBus, topic_prefix: str
) -> None:
    good_received: list[Event] = []
    arrived = threading.Event()

    def explode(_: Event) -> None:
        raise RuntimeError("boom")

    def good(e: Event) -> None:
        good_received.append(e)
        arrived.set()

    bus.subscribe([f"{topic_prefix}.*"], explode)
    bus.subscribe([f"{topic_prefix}.*"], good)
    time.sleep(0.05)

    bus.publish(f"{topic_prefix}.x", {})

    assert _wait_for(arrived)
    assert len(good_received) == 1


# --- health --------------------------------------------------------------------


def test_is_healthy_returns_true_when_connected(bus: RedisEventBus) -> None:
    assert bus.is_healthy() is True


def test_is_healthy_returns_false_after_close(bus: RedisEventBus) -> None:
    bus.close()
    assert bus.is_healthy() is False


def test_publish_after_close_rejected(bus: RedisEventBus) -> None:
    bus.close()
    with pytest.raises(RuntimeError, match="closed"):
        bus.publish("any", {})
