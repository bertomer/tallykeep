"""EventBus unit tests — pattern matcher and InMemoryEventBus.

The Redis backend is exercised by the integration suite. Anything covered here
applies to both backends because they share the same `topic_matches_pattern`.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest

from tallykeep.infrastructure.event_bus import (
    Event,
    InMemoryEventBus,
    topic_matches_pattern,
)


pytestmark = pytest.mark.unit


# --- pattern matcher ------------------------------------------------------------


class TestTopicMatchesPattern:
    @pytest.mark.parametrize(
        ("topic", "pattern", "expected"),
        [
            # Exact matches.
            ("chain.tx.confirmed", "chain.tx.confirmed", True),
            ("chain.tx.confirmed", "chain.tx.mempool", False),
            # Wildcard matches.
            ("chain.tx.confirmed", "chain.*", True),
            ("chain.block.new", "chain.*", True),
            ("treasury.sweep.executed", "chain.*", False),
            # Multi-segment wildcards.
            ("chain.tx.confirmed", "chain.tx.*", True),
            ("chain.block.new", "chain.tx.*", False),
            # Catch-all.
            ("chain.tx.confirmed", "*", True),
            ("system.unlocked", "*", True),
            # Dots are literal — `chain.tx` does NOT match `chainXtx`.
            ("chainXtx", "chain.tx", False),
            # Empty payload still matches its own topic.
            ("", "*", True),
            # Distinct topic-roots do not bleed.
            ("treasury.sweep.executed", "treasury.*", True),
            ("treasury_sweep.executed", "treasury.*", False),
        ],
    )
    def test_match(self, topic: str, pattern: str, expected: bool) -> None:
        assert topic_matches_pattern(topic, pattern) is expected


# --- InMemoryEventBus -----------------------------------------------------------


@pytest.fixture()
def bus() -> Iterator[InMemoryEventBus]:
    b = InMemoryEventBus()
    try:
        yield b
    finally:
        b.close()


class TestInMemoryBusBasics:
    def test_publish_returns_event(self, bus: InMemoryEventBus) -> None:
        event = bus.publish("chain.tx.confirmed", {"txid": "abc"})
        assert isinstance(event, Event)
        assert event.topic == "chain.tx.confirmed"
        assert event.payload == {"txid": "abc"}

    def test_publish_to_no_subscribers_is_a_noop(
        self, bus: InMemoryEventBus
    ) -> None:
        bus.publish("nobody.cares", {})  # must not raise

    def test_subscriber_receives_matching_event(self, bus: InMemoryEventBus) -> None:
        received: list[Event] = []
        bus.subscribe(["chain.*"], received.append)

        bus.publish("chain.tx.confirmed", {"txid": "abc"})

        assert len(received) == 1
        assert received[0].topic == "chain.tx.confirmed"
        assert received[0].payload == {"txid": "abc"}

    def test_subscriber_does_not_receive_non_matching_event(
        self, bus: InMemoryEventBus
    ) -> None:
        received: list[Event] = []
        bus.subscribe(["treasury.*"], received.append)

        bus.publish("chain.tx.confirmed", {})

        assert received == []


class TestSubscriptionLifecycle:
    def test_unsubscribe_stops_delivery(self, bus: InMemoryEventBus) -> None:
        received: list[Event] = []
        sub = bus.subscribe(["*"], received.append)

        bus.publish("a.b.c", {})
        sub.unsubscribe()
        bus.publish("a.b.c", {})

        assert len(received) == 1

    def test_subscribe_with_empty_patterns_rejected(
        self, bus: InMemoryEventBus
    ) -> None:
        with pytest.raises(ValueError):
            bus.subscribe([], lambda e: None)

    def test_subscriber_count_tracks_active_subscriptions(
        self, bus: InMemoryEventBus
    ) -> None:
        assert bus.subscriber_count() == 0
        s1 = bus.subscribe(["a"], lambda e: None)
        s2 = bus.subscribe(["b"], lambda e: None)
        assert bus.subscriber_count() == 2
        s1.unsubscribe()
        assert bus.subscriber_count() == 1
        s2.unsubscribe()
        assert bus.subscriber_count() == 0

    def test_publish_after_close_rejected(self, bus: InMemoryEventBus) -> None:
        bus.close()
        with pytest.raises(RuntimeError, match="closed"):
            bus.publish("anything", {})


class TestFanout:
    def test_multiple_subscribers_each_receive(self, bus: InMemoryEventBus) -> None:
        a: list[Event] = []
        b: list[Event] = []
        bus.subscribe(["chain.*"], a.append)
        bus.subscribe(["chain.tx.*"], b.append)

        bus.publish("chain.tx.confirmed", {"txid": "abc"})

        assert len(a) == 1
        assert len(b) == 1

    def test_handler_can_subscribe_more_during_dispatch(
        self, bus: InMemoryEventBus
    ) -> None:
        """Spec module 01 doesn't require this but it's a sanity check that the
        bus doesn't deadlock when a handler mutates the subscription set."""
        received: list[str] = []

        def first_handler(_: Event) -> None:
            received.append("first")
            bus.subscribe(["a.*"], lambda e: received.append("late"))

        bus.subscribe(["a.*"], first_handler)
        bus.publish("a.x", {})

        # First publish only triggers `first_handler` — `late` registers AFTER
        # the dispatch snapshot was taken.
        assert received == ["first"]

        # Second publish hits both.
        received.clear()
        bus.publish("a.x", {})
        assert sorted(received) == ["first", "late"]


class TestErrorIsolation:
    def test_failing_subscriber_does_not_break_others(
        self, bus: InMemoryEventBus
    ) -> None:
        good: list[Event] = []

        def explode(_: Event) -> None:
            raise RuntimeError("intentional")

        bus.subscribe(["*"], explode)
        bus.subscribe(["*"], good.append)

        bus.publish("anything", {"k": "v"})  # must not raise

        assert len(good) == 1


class TestThreadSafety:
    """The in-memory bus is mostly used single-threaded, but it MUST tolerate
    concurrent publish + subscribe because the production Redis bus delivers via
    a background thread that may publish while user code subscribes."""

    def test_concurrent_publish_and_subscribe_does_not_deadlock(
        self, bus: InMemoryEventBus
    ) -> None:
        received: list[Event] = []
        bus.subscribe(["*"], received.append)

        def publisher() -> None:
            for i in range(100):
                bus.publish("x.y", {"i": i})

        threads = [threading.Thread(target=publisher) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
            assert not t.is_alive(), "publisher thread hung — possible deadlock"

        assert len(received) == 4 * 100
