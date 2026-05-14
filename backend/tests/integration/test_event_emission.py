"""Persist-first emitter and audit reconciler integration tests.

These exercise the full spec-module-01 contract: critical events persist to
``event_emission_log`` before publish, subscribers acknowledge by event id, and
the AuditReconciler re-emits anything still unacknowledged after the grace
period — even if all subscribers were down at the original publish time.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from tallykeep.infrastructure.event_bus import Event, InMemoryEventBus
from tallykeep.infrastructure.event_emission import (
    REPLAY_MARKER_KEY,
    AuditReconciler,
    PersistentEmitter,
)
from tallykeep.models import EventEmissionLogRow


pytestmark = pytest.mark.integration


@pytest.fixture()
def session_factory(clean_test_database: str) -> Iterator[sessionmaker]:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", clean_test_database)
    command.upgrade(cfg, "head")

    engine = sa.create_engine(clean_test_database, future=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def bus() -> Iterator[InMemoryEventBus]:
    b = InMemoryEventBus()
    try:
        yield b
    finally:
        b.close()


# --- PersistentEmitter ------------------------------------------------------


def test_emit_critical_persists_then_publishes(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    received: list[Event] = []
    bus.subscribe(["chain.tx.confirmed"], received.append)

    emitter = PersistentEmitter(bus, session_factory)
    event = emitter.emit_critical("chain.tx.confirmed", {"txid": "abc"})

    # Subscriber received the event with the persisted id.
    assert len(received) == 1
    assert received[0].id == event.id
    assert received[0].payload == {"txid": "abc"}

    # And there's a row in event_emission_log with is_critical=True and
    # acknowledged_at NULL (no one has acked yet).
    with session_factory() as session:
        row = session.get(EventEmissionLogRow, event.id)
        assert row is not None
        assert row.topic == "chain.tx.confirmed"
        assert row.is_critical is True
        assert row.acknowledged_at is None


def test_emit_ephemeral_does_not_persist(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    emitter = PersistentEmitter(bus, session_factory)
    event = emitter.emit("ledger_entry.requires_categorization", {"id": "x"})

    with session_factory() as session:
        row = session.get(EventEmissionLogRow, event.id)
        assert row is None


def test_acknowledge_marks_row_delivered(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    emitter = PersistentEmitter(bus, session_factory)
    event = emitter.emit_critical("banking.payment_request.broadcast", {"id": "p1"})

    assert emitter.is_acknowledged(event.id) is False

    updated = emitter.acknowledge(event.id)
    assert updated is True
    assert emitter.is_acknowledged(event.id) is True

    # Re-acking is a no-op (row already has acknowledged_at set).
    again = emitter.acknowledge(event.id)
    assert again is False


def test_acknowledge_unknown_event_returns_false(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    emitter = PersistentEmitter(bus, session_factory)
    assert emitter.acknowledge(uuid4()) is False


def test_publish_failure_still_leaves_row_for_replay(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    """Spec module 01: 'persist first, emit second. If step 2 fails or no one is
    listening, step 1 is the source of truth.'"""

    class _FailingBus(InMemoryEventBus):
        def publish(self, topic, payload, *, event_id=None):  # type: ignore[override]
            raise RuntimeError("bus down")

    failing_bus = _FailingBus()
    emitter = PersistentEmitter(failing_bus, session_factory)

    event = emitter.emit_critical("treasury.sweep.executed", {"id": "s1"})

    # The publish raised internally — the emitter caught it and synthesized an
    # Event handle so the caller still has a usable reference.
    assert event.topic == "treasury.sweep.executed"

    # The row exists and is unacknowledged — the reconciler can replay later.
    with session_factory() as session:
        row = session.get(EventEmissionLogRow, event.id)
        assert row is not None
        assert row.acknowledged_at is None


# --- AuditReconciler --------------------------------------------------------


def _frozen_clock(at: datetime):
    return lambda: at


def test_reconciler_skips_recent_events(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    """An event that was just emitted is still inside the grace period — the
    reconciler must NOT re-emit it."""
    emitter = PersistentEmitter(bus, session_factory)
    received: list[Event] = []
    bus.subscribe(["*"], received.append)

    emitter.emit_critical("treasury.sweep.executed", {"id": "s1"})
    received.clear()  # don't count the original publish

    reconciler = AuditReconciler(
        bus=bus,
        session_factory=session_factory,
        grace_period=timedelta(minutes=5),
    )
    n = reconciler.run_once()

    assert n == 0
    assert received == []


def test_reconciler_replays_unacknowledged_old_events(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    """Once the grace period has passed and no one has acked, the reconciler
    re-emits with the replay marker set."""
    emitter = PersistentEmitter(bus, session_factory)
    received: list[Event] = []
    bus.subscribe(["*"], received.append)

    event = emitter.emit_critical("treasury.sweep.executed", {"id": "s1"})
    received.clear()

    # Fast-forward the reconciler's clock past the grace period.
    future = datetime.now(UTC) + timedelta(minutes=10)
    reconciler = AuditReconciler(
        bus=bus,
        session_factory=session_factory,
        grace_period=timedelta(minutes=5),
        clock=_frozen_clock(future),
    )

    n = reconciler.run_once()
    assert n == 1
    assert len(received) == 1
    replayed = received[0]
    assert replayed.id == event.id
    assert replayed.topic == event.topic
    assert replayed.payload.get(REPLAY_MARKER_KEY) is True


def test_reconciler_does_not_replay_acknowledged_events(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    """If a subscriber acked the event, the reconciler must leave it alone even
    after the grace period."""
    emitter = PersistentEmitter(bus, session_factory)
    received: list[Event] = []
    bus.subscribe(["*"], received.append)

    event = emitter.emit_critical("banking.invoice.paid", {"id": "i1"})
    emitter.acknowledge(event.id)
    received.clear()

    reconciler = AuditReconciler(
        bus=bus,
        session_factory=session_factory,
        grace_period=timedelta(minutes=5),
        clock=_frozen_clock(datetime.now(UTC) + timedelta(minutes=10)),
    )
    n = reconciler.run_once()

    assert n == 0
    assert received == []


def test_reconciler_recovers_event_lost_to_subscriber_outage(
    session_factory: sessionmaker,
) -> None:
    """Full spec scenario: event published with no subscribers (subscriber down),
    then a subscriber comes online, then the reconciler runs — the subscriber
    should now see the event via replay."""

    bus = InMemoryEventBus()
    try:
        emitter = PersistentEmitter(bus, session_factory)

        # No subscribers yet — emit the critical event. The publish goes nowhere.
        event = emitter.emit_critical("treasury.sweep.executed", {"id": "s1"})

        # Subscriber comes online (analogue: worker process restarts).
        received: list[Event] = []
        bus.subscribe(["treasury.*"], received.append)

        # Run the reconciler with the clock fast-forwarded past the grace period.
        future = datetime.now(UTC) + timedelta(minutes=10)
        reconciler = AuditReconciler(
            bus=bus,
            session_factory=session_factory,
            grace_period=timedelta(minutes=5),
            clock=_frozen_clock(future),
        )
        n = reconciler.run_once()

        assert n == 1
        assert len(received) == 1
        assert received[0].id == event.id
        assert received[0].payload.get(REPLAY_MARKER_KEY) is True
    finally:
        bus.close()


def test_reconciler_run_is_concurrent_safe(
    session_factory: sessionmaker, bus: InMemoryEventBus
) -> None:
    """Two reconciler runs in parallel should both be safe (the worst case is a
    duplicate replay; we are at-least-once delivery semantics by design)."""
    emitter = PersistentEmitter(bus, session_factory)
    received: list[Event] = []
    bus.subscribe(["*"], received.append)

    for i in range(5):
        emitter.emit_critical("treasury.sweep.executed", {"i": i})
    received.clear()

    future = datetime.now(UTC) + timedelta(minutes=10)
    reconciler = AuditReconciler(
        bus=bus,
        session_factory=session_factory,
        grace_period=timedelta(minutes=5),
        clock=_frozen_clock(future),
    )

    threads = [threading.Thread(target=reconciler.run_once) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
        assert not t.is_alive()

    # 5 events × up to 3 reconciler runs ⇒ at most 15 deliveries; minimum 5
    # (each event re-emitted at least once).
    assert len(received) >= 5
    assert len(received) <= 15
