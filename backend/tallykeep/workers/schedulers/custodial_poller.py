"""CustodialPoller — custodial observation cycle (iteration A).

Polls all active CustodialProviders on a fixed interval:
  1. Fetches balance + new ledger entries per provider (one atomic DB commit).
  2. Emits three SSE topics per cycle:
     - treasury.custodial.cycle_completed (Option B: balance + new entries, atomic)
     - treasury.custodial.ledger_entry_added (per new entry; granular subscriptions)
     - treasury.custodial.connection_state_changed (on health transitions only)
  3. Checks recent withdrawals for pending SweepExecutions.

Connection state machine:
  healthy → degraded (1 transient error)
  degraded → unreachable (after _N_UNREACHABLE consecutive errors)
  any → auth_failed (auth error; terminal until credential replaced)
  degraded/unreachable/auth_failed → healthy (first successful poll)

SSE consistency (Option B rationale): balance_sats and new_ledger_entries in
treasury.custodial.cycle_completed are written in the same DB transaction and
published after commit, so subscribers that derive balance from the stream see
consistent state at every point — no "fresh entries, stale balance" window.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.domain.custodial_provider import CustodialProvider
from tallykeep.domain.enums import SweepExecutionStatus
from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.infrastructure.secrets import LockedError, SecretStore
from tallykeep.models.custodial_ledger_entry import CustodialLedgerEntryRow
from tallykeep.repositories import custodial_ledger_entry as cle_repo
from tallykeep.repositories import custodial_provider as cp_repo
from tallykeep.repositories import sweep_execution as se_repo


logger = logging.getLogger(__name__)

_N_UNREACHABLE = 5
_SATS = 100_000_000


class CustodialPoller:
    """Background thread that polls exchange balances and ledger entries every `interval_seconds`."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        secret_store: SecretStore,
        bus: EventBus,
        interval_seconds: int = 300,
    ) -> None:
        self._session_factory = session_factory
        self._secret_store = secret_store
        self._bus = bus
        self._interval = interval_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="CustodialPoller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def _run(self) -> None:
        logger.info("CustodialPoller: started (interval=%ds)", self._interval)
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception:  # noqa: BLE001
                logger.exception("CustodialPoller: poll_once failed")
            self._stop_event.wait(timeout=self._interval)
        logger.info("CustodialPoller: stopped")

    def _poll_once(self) -> None:
        if not self._secret_store.is_unlocked():
            logger.debug("CustodialPoller: secret store locked, skipping poll")
            return

        from tallykeep.adapters.adapter_registry import UnsupportedAdapterError, build_adapter
        from tallykeep.adapters.custodial_provider_adapter import ProviderAuthError, ProviderError

        with self._session_factory() as session:
            providers = cp_repo.list_active(session)

        for provider in providers:
            try:
                api_key = self._secret_store.get_secret(provider.api_credential_reference).decode()
                api_secret = self._secret_store.get_secret(provider.api_secret_reference).decode()
                api_passphrase = (
                    self._secret_store.get_secret(provider.api_passphrase_reference).decode()
                    if provider.api_passphrase_reference
                    else None
                )
            except (KeyError, LockedError):
                logger.warning("CustodialPoller: cannot read secrets for provider %s", provider.id)
                continue

            polled_at = datetime.now(UTC)
            try:
                adapter = build_adapter(
                    provider.adapter_id,
                    api_key=api_key,
                    api_secret=api_secret,
                    api_passphrase=api_passphrase,
                )
                balance_sats = adapter.get_balance()
                with self._session_factory() as session:
                    cursor = cp_repo.get_ledger_cursor(session, provider.id)
                new_entries, newest_ts = adapter.fetch_ledger_since(cursor)
            except ProviderAuthError as exc:
                logger.warning(
                    "CustodialPoller: auth error for provider %s: %s", provider.id, exc
                )
                self._handle_auth_error(provider, str(exc), polled_at)
                continue
            except (ProviderError, UnsupportedAdapterError) as exc:
                logger.warning(
                    "CustodialPoller: transient error for provider %s: %s", provider.id, exc
                )
                self._handle_transient_error(provider, str(exc), polled_at)
                continue
            except Exception:  # noqa: BLE001
                logger.exception("CustodialPoller: unexpected error for provider %s", provider.id)
                continue

            self._handle_success(provider, balance_sats, new_entries, newest_ts, polled_at)
            self._check_withdrawal_txids(provider.id, adapter)

    def _handle_success(
        self,
        provider: CustodialProvider,
        balance_sats: int,
        new_entries: list,
        newest_ts: datetime | None,
        polled_at: datetime,
    ) -> None:
        old_status = provider.connection_status
        persisted_entries: list[CustodialLedgerEntryRow] = []

        with self._session_factory() as session:
            for entry in new_entries:
                if cle_repo.exists(
                    session,
                    custodial_provider_id=provider.id,
                    provider_entry_id=entry.provider_entry_id,
                ):
                    continue
                row = CustodialLedgerEntryRow(
                    id=uuid4(),
                    custodial_provider_id=provider.id,
                    provider_entry_id=entry.provider_entry_id,
                    kind=entry.kind,
                    asset=entry.asset,
                    amount_sats=int(round(entry.amount * _SATS)),
                    status=entry.status,
                    timestamp=entry.timestamp,
                    raw_payload=entry.raw,
                )
                cle_repo.create(session, row)
                persisted_entries.append(row)

            cp_repo.update_balance(
                session, provider.id, balance_sats=balance_sats, polled_at=polled_at
            )
            if newest_ts is not None:
                cp_repo.update_ledger_cursor(session, provider.id, cursor_at=newest_ts)
            cp_repo.update_connection_status(
                session,
                provider.id,
                status="healthy",
                consecutive_error_count=0,
                polled_at=polled_at,
            )
            session.commit()

        entry_payloads = [
            {
                "provider_entry_id": r.provider_entry_id,
                "kind": r.kind,
                "asset": r.asset,
                "amount_sats": r.amount_sats,
                "status": r.status,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in persisted_entries
        ]
        self._bus.publish(
            "treasury.custodial.cycle_completed",
            {
                "holding_id": str(provider.holding_id),
                "provider_id": str(provider.id),
                "observed_at": polled_at.isoformat(),
                "balance_sats": balance_sats,
                "new_ledger_entries": entry_payloads,
            },
        )
        for r in persisted_entries:
            self._bus.publish(
                "treasury.custodial.ledger_entry_added",
                {
                    "holding_id": str(provider.holding_id),
                    "provider_id": str(provider.id),
                    "observed_at": polled_at.isoformat(),
                    "balance_sats": balance_sats,
                    "entry": {
                        "provider_entry_id": r.provider_entry_id,
                        "kind": r.kind,
                        "asset": r.asset,
                        "amount_sats": r.amount_sats,
                        "status": r.status,
                        "timestamp": r.timestamp.isoformat(),
                    },
                },
            )
        if old_status != "healthy":
            self._bus.publish(
                "treasury.custodial.connection_state_changed",
                {
                    "holding_id": str(provider.holding_id),
                    "provider_id": str(provider.id),
                    "old_status": old_status,
                    "new_status": "healthy",
                },
            )
        logger.debug(
            "CustodialPoller: provider %s balance=%d sats, %d new entries",
            provider.id,
            balance_sats,
            len(persisted_entries),
        )

    def _handle_auth_error(
        self,
        provider: CustodialProvider,
        error: str,
        polled_at: datetime,
    ) -> None:
        old_status = provider.connection_status
        if old_status == "auth_failed":
            return
        with self._session_factory() as session:
            cp_repo.update_connection_status(
                session,
                provider.id,
                status="auth_failed",
                consecutive_error_count=0,
                polled_at=polled_at,
                error=error,
            )
            session.commit()
        self._bus.publish(
            "treasury.custodial.connection_state_changed",
            {
                "holding_id": str(provider.holding_id),
                "provider_id": str(provider.id),
                "old_status": old_status,
                "new_status": "auth_failed",
            },
        )

    def _handle_transient_error(
        self,
        provider: CustodialProvider,
        error: str,
        polled_at: datetime,
    ) -> None:
        old_status = provider.connection_status
        if old_status == "auth_failed":
            return
        new_count = provider.consecutive_error_count + 1
        if new_count >= _N_UNREACHABLE:
            new_status = "unreachable"
        elif old_status == "healthy":
            new_status = "degraded"
        else:
            new_status = old_status
        with self._session_factory() as session:
            cp_repo.update_connection_status(
                session,
                provider.id,
                status=new_status,
                consecutive_error_count=new_count,
                polled_at=polled_at,
                error=error,
            )
            session.commit()
        if old_status != new_status:
            self._bus.publish(
                "treasury.custodial.connection_state_changed",
                {
                    "holding_id": str(provider.holding_id),
                    "provider_id": str(provider.id),
                    "old_status": old_status,
                    "new_status": new_status,
                },
            )

    def _check_withdrawal_txids(self, provider_id: UUID, adapter) -> None:  # type: ignore[no-untyped-def]
        """For REQUESTED executions on this provider, try to find the on-chain txid."""
        from datetime import timedelta

        from tallykeep.adapters.custodial_provider_adapter import ProviderError

        since = datetime.now(UTC) - timedelta(days=7)
        try:
            withdrawals = adapter.get_recent_withdrawals(since)
        except ProviderError as exc:
            logger.debug(
                "CustodialPoller: get_recent_withdrawals failed for %s: %s", provider_id, exc
            )
            return

        txid_by_withdrawal_id = {w.id: w.txid for w in withdrawals if w.txid}
        if not txid_by_withdrawal_id:
            return

        with self._session_factory() as session:
            executions = se_repo.list_executions(
                session,
                status=SweepExecutionStatus.REQUESTED,
                limit=100,
            )
            updated_count = 0
            for execution in executions:
                if execution.provider_withdrawal_id is None:
                    continue
                txid = txid_by_withdrawal_id.get(execution.provider_withdrawal_id)
                if txid:
                    se_repo.update_status(
                        session,
                        execution.id,
                        status=SweepExecutionStatus.ONCHAIN_PENDING,
                        expected_txid=txid,
                    )
                    updated_count += 1
            if updated_count:
                session.commit()
                logger.info(
                    "CustodialPoller: promoted %d execution(s) to ONCHAIN_PENDING for provider %s",
                    updated_count,
                    provider_id,
                )


__all__ = ["CustodialPoller"]
