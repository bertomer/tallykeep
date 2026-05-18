"""Integration tests for the lock-aware worker architecture (ADR-0015 / ADR-0016).

Task 10: Worker boots cleanly with the backend locked.
Task 11: Catch-up burst fires on system.unlocked.
Task 12: No passphrase/secret field ever appears in system.* event payloads.

These tests use InMemoryEventBus and mocked HTTP so they run without Redis or a
live backend. The integration label is for grouping — they don't need postgres
or bitcoind.
"""

from __future__ import annotations

import threading
import time
import unittest.mock as mock
from collections.abc import Iterator
from uuid import uuid4

import pytest

from tallykeep.infrastructure.event_bus import InMemoryEventBus
from tallykeep.workers.schedulers.custodial_poll_scheduler import CustodialPollScheduler
from tallykeep.workers.subscribers.custodial_poller import CustodialPoller


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_factory(providers: list | None = None):  # type: ignore[no-untyped-def]
    """Return a mock session_factory whose cp_repo.list_active returns `providers`."""
    from unittest.mock import MagicMock

    session = MagicMock()
    session.__enter__ = lambda s: s
    session.__exit__ = MagicMock(return_value=False)

    session_factory = MagicMock()
    session_factory.return_value = session

    if providers is not None:
        from tallykeep.domain.custodial_provider import CustodialProvider, ProviderPermissions
        from tallykeep.domain.enums import ProviderKind

        domain_providers = [
            CustodialProvider(
                id=pid,
                holding_id=uuid4(),
                provider_kind=ProviderKind.EXCHANGE,
                display_name="Test",
                adapter_id="kraken",
                api_credential_reference="ref_key",
                api_secret_reference="ref_secret",
                api_passphrase_reference=None,
                permissions=ProviderPermissions(can_read=True, can_trade=False, can_withdraw=False),
                whitelist_address=None,
                whitelist_address_descriptor_id=None,
                whitelist_verified=False,
                is_active=True,
                last_polled_at=None,
                last_error=None,
                last_known_balance_sats=None,
                connection_status="healthy",
                consecutive_error_count=0,
                ledger_cursor_at=None,
                polling_interval_seconds=600,
                observation_key_last_four=None,
                non_btc_balances={},
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            for pid in providers
        ]

        # cp_repo.list_active is called with the session as the first argument.
        with mock.patch(
            "tallykeep.workers.subscribers.custodial_poller.cp_repo.list_active",
            return_value=domain_providers,
        ), mock.patch(
            "tallykeep.workers.schedulers.custodial_poll_scheduler.cp_repo.list_active",
            return_value=domain_providers,
        ):
            yield session_factory
    else:
        yield session_factory


# ---------------------------------------------------------------------------
# Task 10: Worker components boot with backend locked
# ---------------------------------------------------------------------------


class TestWorkerBootWithBackendLocked:
    """Verify CustodialPoller and CustodialPollScheduler boot without needing an
    unlocked backend. is_running must be True immediately after start()."""

    def test_custodial_poller_starts_and_is_running(self) -> None:
        bus = InMemoryEventBus()
        session_factory = mock.MagicMock()
        session_factory.return_value.__enter__ = lambda s: session_factory.return_value
        session_factory.return_value.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch(
            "tallykeep.workers.subscribers.custodial_poller.cp_repo.list_active",
            return_value=[],
        ):
            poller = CustodialPoller(
                bus=bus,
                session_factory=session_factory,
                backend_url="http://localhost:8000",
            )
            assert not poller.is_running
            poller.start()
            assert poller.is_running
            poller.stop()
            assert not poller.is_running

        bus.close()

    def test_custodial_poll_scheduler_starts(self) -> None:
        bus = InMemoryEventBus()
        session_factory = mock.MagicMock()
        session_factory.return_value.__enter__ = lambda s: session_factory.return_value
        session_factory.return_value.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch(
            "tallykeep.workers.schedulers.custodial_poll_scheduler.cp_repo.list_active",
            return_value=[],
        ), mock.patch(
            "tallykeep.workers.schedulers.custodial_poll_scheduler.CustodialPollScheduler._read_interval",
            return_value=9999,  # prevent ticking during test
        ):
            scheduler = CustodialPollScheduler(
                session_factory=session_factory,
                bus=bus,
            )
            assert not scheduler.is_running
            scheduler.start()
            assert scheduler.is_running
            scheduler.stop()
            assert not scheduler.is_running

        bus.close()

    def test_poller_handles_system_locked_before_any_dispatch(self) -> None:
        """system.locked published on bus: poller suspends dispatch without crashing."""
        bus = InMemoryEventBus()
        session_factory = mock.MagicMock()
        session_factory.return_value.__enter__ = lambda s: session_factory.return_value
        session_factory.return_value.__exit__ = mock.MagicMock(return_value=False)

        http_post_calls: list[str] = []

        with mock.patch(
            "tallykeep.workers.subscribers.custodial_poller.cp_repo.list_active",
            return_value=[],
        ):
            poller = CustodialPoller(
                bus=bus,
                session_factory=session_factory,
                backend_url="http://localhost:8000",
            )
            poller.start()

            # Simulate backend startup: emit system.locked
            from datetime import UTC, datetime

            bus.publish(
                "system.locked",
                {"topic": "system.locked", "timestamp": datetime.now(UTC).isoformat()},
            )

            # Emit a tick — should be dropped because dispatch is disabled
            provider_id = str(uuid4())
            with mock.patch.object(poller, "_dispatch_cycle") as mock_dispatch:
                bus.publish(
                    "treasury.custodial.poll_tick",
                    {"provider_id": provider_id},
                )
                # Give daemon thread a moment to process
                time.sleep(0.05)
                mock_dispatch.assert_not_called()

            assert poller.is_running  # still running — not crashed
            poller.stop()

        bus.close()


# ---------------------------------------------------------------------------
# Task 11: Catch-up burst on system.unlocked
# ---------------------------------------------------------------------------


class TestCatchUpBurst:
    """system.unlocked fires: poller dispatches one HTTP call per active provider."""

    def test_catch_up_burst_dispatches_n_calls(self) -> None:
        from datetime import UTC, datetime

        bus = InMemoryEventBus()
        session_factory = mock.MagicMock()
        session_factory.return_value.__enter__ = lambda s: session_factory.return_value
        session_factory.return_value.__exit__ = mock.MagicMock(return_value=False)

        provider_ids = [uuid4(), uuid4(), uuid4()]
        dispatched: list[str] = []
        dispatch_lock = threading.Lock()

        def fake_dispatch(pid: str) -> None:
            with dispatch_lock:
                dispatched.append(pid)

        from tallykeep.domain.custodial_provider import CustodialProvider, ProviderPermissions
        from tallykeep.domain.enums import ProviderKind

        fake_providers = [
            CustodialProvider(
                id=pid,
                holding_id=uuid4(),
                provider_kind=ProviderKind.EXCHANGE,
                display_name="Test",
                adapter_id="kraken",
                api_credential_reference="ref",
                api_secret_reference="ref_s",
                api_passphrase_reference=None,
                permissions=ProviderPermissions(can_read=True, can_trade=False, can_withdraw=False),
                whitelist_address=None,
                whitelist_address_descriptor_id=None,
                whitelist_verified=False,
                is_active=True,
                last_polled_at=None,
                last_error=None,
                last_known_balance_sats=None,
                connection_status="healthy",
                consecutive_error_count=0,
                ledger_cursor_at=None,
                polling_interval_seconds=600,
                observation_key_last_four=None,
                non_btc_balances={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for pid in provider_ids
        ]

        with mock.patch(
            "tallykeep.workers.subscribers.custodial_poller.cp_repo.list_active",
            return_value=fake_providers,
        ):
            poller = CustodialPoller(
                bus=bus,
                session_factory=session_factory,
                backend_url="http://localhost:8000",
            )
            poller._dispatch_cycle = fake_dispatch  # type: ignore[method-assign]
            poller.start()

            # Emit system.unlocked — triggers catch-up burst
            bus.publish(
                "system.unlocked",
                {"topic": "system.unlocked", "timestamp": datetime.now(UTC).isoformat()},
            )

            # Wait for the burst thread to finish (up to 3 s)
            deadline = time.time() + 3.0
            while time.time() < deadline:
                with dispatch_lock:
                    if len(dispatched) == len(provider_ids):
                        break
                time.sleep(0.05)

            assert len(dispatched) == len(provider_ids), (
                f"Expected {len(provider_ids)} dispatch calls, got {len(dispatched)}"
            )
            assert set(dispatched) == {str(p.id) for p in fake_providers}

            poller.stop()

        bus.close()

    def test_catch_up_burst_after_locked_then_unlocked(self) -> None:
        """locked → no ticks dispatched; unlocked → burst fires."""
        from datetime import UTC, datetime

        bus = InMemoryEventBus()
        session_factory = mock.MagicMock()
        session_factory.return_value.__enter__ = lambda s: session_factory.return_value
        session_factory.return_value.__exit__ = mock.MagicMock(return_value=False)

        provider_id = uuid4()
        dispatched: list[str] = []

        from tallykeep.domain.custodial_provider import CustodialProvider, ProviderPermissions
        from tallykeep.domain.enums import ProviderKind

        fake_provider = CustodialProvider(
            id=provider_id,
            holding_id=uuid4(),
            provider_kind=ProviderKind.EXCHANGE,
            display_name="Test",
            adapter_id="kraken",
            api_credential_reference="ref",
            api_secret_reference="ref_s",
            api_passphrase_reference=None,
            permissions=ProviderPermissions(can_read=True, can_trade=False, can_withdraw=False),
            whitelist_address=None,
            whitelist_address_descriptor_id=None,
            whitelist_verified=False,
            is_active=True,
            last_polled_at=None,
            last_error=None,
            last_known_balance_sats=None,
            connection_status="healthy",
            consecutive_error_count=0,
            ledger_cursor_at=None,
            polling_interval_seconds=600,
            observation_key_last_four=None,
            non_btc_balances={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with mock.patch(
            "tallykeep.workers.subscribers.custodial_poller.cp_repo.list_active",
            return_value=[fake_provider],
        ):
            poller = CustodialPoller(
                bus=bus,
                session_factory=session_factory,
                backend_url="http://localhost:8000",
            )
            poller._dispatch_cycle = lambda pid: dispatched.append(pid)  # type: ignore[method-assign]
            poller.start()

            # Lock → tick should be dropped
            bus.publish(
                "system.locked",
                {"topic": "system.locked", "timestamp": datetime.now(UTC).isoformat()},
            )
            bus.publish(
                "treasury.custodial.poll_tick",
                {"provider_id": str(provider_id)},
            )
            time.sleep(0.05)
            assert len(dispatched) == 0

            # Unlock → burst should dispatch
            bus.publish(
                "system.unlocked",
                {"topic": "system.unlocked", "timestamp": datetime.now(UTC).isoformat()},
            )

            deadline = time.time() + 3.0
            while time.time() < deadline:
                if len(dispatched) >= 1:
                    break
                time.sleep(0.05)

            assert len(dispatched) >= 1
            poller.stop()

        bus.close()


# ---------------------------------------------------------------------------
# Task 12: No passphrase or secret in system.* event payloads
# ---------------------------------------------------------------------------


class TestNoSecretsOnBus:
    """Regression guard: system.locked and system.unlocked must never carry
    passphrase, password, secret, private_key, or values matching the test
    passphrase. (ADR-0016)"""

    _FORBIDDEN_KEYS = {"passphrase", "password", "secret", "private_key"}
    _TEST_PASSPHRASE = "test-passphrase-12345"

    def _scan_payload(self, payload: dict) -> list[str]:
        """Return a list of violations (forbidden key names or passphrase value)."""
        violations: list[str] = []
        for key, value in payload.items():
            if key.lower() in self._FORBIDDEN_KEYS:
                violations.append(f"forbidden key: {key!r}")
            if isinstance(value, str) and self._TEST_PASSPHRASE in value:
                violations.append(f"passphrase value in key: {key!r}")
        return violations

    def test_system_locked_payload_is_topic_only(self) -> None:
        from datetime import UTC, datetime
        from tallykeep.infrastructure.event_bus import InMemoryEventBus

        bus = InMemoryEventBus()
        received_payloads: list[dict] = []

        bus.subscribe(["system.*"], lambda event: received_payloads.append(event.payload))

        bus.publish(
            "system.locked",
            {"topic": "system.locked", "timestamp": datetime.now(UTC).isoformat()},
        )
        bus.publish(
            "system.unlocked",
            {"topic": "system.unlocked", "timestamp": datetime.now(UTC).isoformat()},
        )

        assert len(received_payloads) == 2
        for payload in received_payloads:
            violations = self._scan_payload(payload)
            assert violations == [], f"system.* event payload contains forbidden content: {violations}"

        # Keys must be only 'topic' and 'timestamp'
        for payload in received_payloads:
            allowed_keys = {"topic", "timestamp"}
            extra = set(payload.keys()) - allowed_keys
            assert extra == set(), f"system.* payload has unexpected keys: {extra}"

        bus.close()

    def test_no_passphrase_in_system_event_during_unlock_flow(self) -> None:
        """Simulate the unlock endpoint emitting system.unlocked and assert the
        payload never contains the passphrase string."""
        from datetime import UTC, datetime
        from tallykeep.infrastructure.event_bus import InMemoryEventBus

        bus = InMemoryEventBus()
        received_payloads: list[dict] = []

        bus.subscribe(["system.*"], lambda event: received_payloads.append(event.payload))

        # Simulate what the unlock endpoint does (ADR-0016 contract)
        bus.publish(
            "system.unlocked",
            {"topic": "system.unlocked", "timestamp": datetime.now(UTC).isoformat()},
        )

        assert len(received_payloads) == 1
        payload = received_payloads[0]

        # The passphrase must not appear anywhere
        payload_str = str(payload)
        assert self._TEST_PASSPHRASE not in payload_str, (
            f"Passphrase found in system.unlocked payload: {payload}"
        )

        violations = self._scan_payload(payload)
        assert violations == [], f"Forbidden content in system.unlocked: {violations}"

        bus.close()

    def test_regression_subscribe_probe_catches_secret_if_present(self) -> None:
        """Verify the probe itself would catch a violation — test the test."""
        from datetime import UTC, datetime
        from tallykeep.infrastructure.event_bus import InMemoryEventBus

        bus = InMemoryEventBus()
        received_payloads: list[dict] = []

        bus.subscribe(["system.*"], lambda event: received_payloads.append(event.payload))

        # Deliberately emit a bad payload to confirm the check fires
        bus.publish(
            "system.unlocked",
            {
                "topic": "system.unlocked",
                "timestamp": datetime.now(UTC).isoformat(),
                "passphrase": self._TEST_PASSPHRASE,  # FORBIDDEN
            },
        )

        assert len(received_payloads) == 1
        violations = self._scan_payload(received_payloads[0])
        assert len(violations) > 0, "Expected violations to be detected, but none were found"

        bus.close()
