"""CustodialPollHandler — self-contained custodial poll scheduler + executor.

Owns the full custodial poll lifecycle in the backend process:
  - Internal 15-second timer checks each provider's polling_interval_seconds.
  - When an interval elapses, dispatches a poll thread directly (no event bus).
  - poll_all_immediately() is called on unlock to bypass the interval guard.

All ccxt calls (Kraken API) run here where the secret store is always available.

Connection state machine:
  healthy → degraded (1 transient error)
  degraded → unreachable (after _N_UNREACHABLE consecutive errors)
  any → auth_failed (auth error; terminal until credential replaced)
  degraded/unreachable/auth_failed → healthy (first successful poll)
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
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
_CHECK_INTERVAL = 15  # seconds between scheduler ticks


class CustodialPollHandler:
    """Backend scheduler + executor: checks intervals, runs polls, writes DB, emits SSE."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        secret_store: SecretStore,
        bus: EventBus,
    ) -> None:
        self._session_factory = session_factory
        self._secret_store = secret_store
        self._bus = bus
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_scheduler, name="CustodialPollScheduler", daemon=True
        )
        self._thread.start()
        logger.info("CustodialPollHandler: started (check_interval=%ds)", _CHECK_INTERVAL)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def poll_all_immediately(self) -> None:
        """Bypass the interval guard — call this on unlock so data is current right away."""
        with self._session_factory() as session:
            providers = cp_repo.list_active(session)
        for provider in providers:
            self._dispatch(provider.id)
        if providers:
            logger.info(
                "CustodialPollHandler: immediate poll dispatched for %d provider(s)",
                len(providers),
            )

    def poll_provider_immediately(self, provider_id: UUID) -> None:
        """Dispatch a single provider poll bypassing the interval guard."""
        self._dispatch(provider_id)
        logger.info("CustodialPollHandler: immediate poll dispatched for provider %s", provider_id)

    # ------------------------------------------------------------------
    # Internal scheduler
    # ------------------------------------------------------------------

    def _run_scheduler(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("CustodialPollHandler: scheduler tick failed")
            self._stop_event.wait(timeout=_CHECK_INTERVAL)

    def _tick(self) -> None:
        with self._session_factory() as session:
            providers = cp_repo.list_active(session)

        now = datetime.now(UTC)
        for provider in providers:
            if provider.last_polled_at is not None:
                elapsed = (now - provider.last_polled_at).total_seconds()
                if elapsed < provider.polling_interval_seconds:
                    continue
            self._dispatch(provider.id)
            logger.info(
                "CustodialPollHandler: scheduled poll for provider %s", provider.id
            )

    def _dispatch(self, provider_id: UUID) -> None:
        threading.Thread(
            target=self._poll_provider,
            args=(provider_id,),
            name=f"CustodialPoll-{str(provider_id)[:8]}",
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Poll execution (unchanged from before)
    # ------------------------------------------------------------------

    def _poll_provider(self, provider_id: UUID) -> None:
        if not self._secret_store.is_unlocked():
            logger.info(
                "CustodialPollHandler: secret store locked, skipping poll for %s",
                provider_id,
            )
            return

        from tallykeep.adapters.adapter_registry import UnsupportedAdapterError, build_adapter
        from tallykeep.adapters.custodial_provider_adapter import ProviderAuthError, ProviderError

        with self._session_factory() as session:
            provider = cp_repo.get(session, provider_id)

        if provider is None:
            logger.warning("CustodialPollHandler: provider %s not found", provider_id)
            return

        try:
            api_key = self._secret_store.get_secret(provider.api_credential_reference).decode()
            api_secret = self._secret_store.get_secret(provider.api_secret_reference).decode()
            api_passphrase = (
                self._secret_store.get_secret(provider.api_passphrase_reference).decode()
                if provider.api_passphrase_reference
                else None
            )
        except (KeyError, LockedError):
            logger.warning(
                "CustodialPollHandler: cannot read secrets for provider %s", provider_id
            )
            return

        polled_at = datetime.now(UTC)
        try:
            adapter = build_adapter(
                provider.adapter_id,
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=api_passphrase,
            )
            balance_sats = adapter.get_balance()
            other_balances = adapter.get_other_balances()
            with self._session_factory() as session:
                cursor = cp_repo.get_ledger_cursor(session, provider_id)
            new_entries, newest_ts = adapter.fetch_ledger_since(cursor)
        except ProviderAuthError as exc:
            logger.warning(
                "CustodialPollHandler: auth error for provider %s: %s", provider_id, exc
            )
            self._handle_auth_error(provider, str(exc), polled_at)
            return
        except (ProviderError, UnsupportedAdapterError) as exc:
            logger.warning(
                "CustodialPollHandler: transient error for provider %s: %s", provider_id, exc
            )
            self._handle_transient_error(provider, str(exc), polled_at)
            return
        except Exception:  # noqa: BLE001
            logger.exception(
                "CustodialPollHandler: unexpected error for provider %s", provider_id
            )
            return

        self._handle_success(provider, balance_sats, other_balances, new_entries, newest_ts, polled_at)
        self._check_withdrawal_txids(provider_id, adapter)

    def _handle_success(
        self,
        provider: CustodialProvider,
        balance_sats: int,
        other_balances: dict[str, str],
        new_entries: list,
        newest_ts: datetime | None,
        polled_at: datetime,
    ) -> None:
        old_status = provider.connection_status
        added_entries: list[CustodialLedgerEntryRow] = []
        updated_entries: list[tuple[CustodialLedgerEntryRow, list[str]]] = []

        with self._session_factory() as session:
            for entry in new_entries:
                fee_sats: int | None = None
                if entry.fee is not None:
                    fee_sats = int(round(entry.fee * _SATS))
                row = CustodialLedgerEntryRow(
                    id=uuid4(),
                    holding_id=provider.holding_id,
                    custodial_provider_id=provider.id,
                    provider_entry_id=entry.provider_entry_id,
                    kind=entry.kind,
                    asset=entry.asset,
                    amount_sats=int(round(entry.amount * _SATS)),
                    fee_sats=fee_sats,
                    status=entry.status,
                    timestamp=entry.timestamp,
                    raw_payload=entry.raw,
                )
                result = cle_repo.upsert(session, row)
                if result.is_new:
                    added_entries.append(result.row)
                elif result.changed_fields:
                    updated_entries.append((result.row, result.changed_fields))

            cp_repo.update_balance(
                session, provider.id, balance_sats=balance_sats, polled_at=polled_at
            )
            cp_repo.update_non_btc_balances(session, provider.id, balances=other_balances)
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

        def _entry_payload(r: CustodialLedgerEntryRow) -> dict:
            return {
                "id": str(r.id),
                "provider_entry_id": r.provider_entry_id,
                "kind": r.kind,
                "asset": r.asset,
                "amount_sats": r.amount_sats,
                "fee_sats": r.fee_sats,
                "status": r.status,
                "timestamp": r.timestamp.isoformat(),
            }

        self._bus.publish(
            "treasury.custodial.cycle_completed",
            {
                "holding_id": str(provider.holding_id),
                "provider_id": str(provider.id),
                "observed_at": polled_at.isoformat(),
                "balance_sats": balance_sats,
                "new_ledger_entries": [_entry_payload(r) for r in added_entries],
            },
        )
        for r in added_entries:
            self._bus.publish(
                "treasury.custodial.ledger_entry_added",
                {
                    "holding_id": str(provider.holding_id),
                    "provider_id": str(provider.id),
                    "observed_at": polled_at.isoformat(),
                    "balance_sats": balance_sats,
                    "entry": _entry_payload(r),
                },
            )
        for r, changed in updated_entries:
            self._bus.publish(
                "treasury.custodial.ledger_entry_updated",
                {
                    "holding_id": str(provider.holding_id),
                    "provider_id": str(provider.id),
                    "observed_at": polled_at.isoformat(),
                    "entry": _entry_payload(r),
                    "changed_fields": changed,
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
            "CustodialPollHandler: provider %s balance=%d sats, %d new entries",
            provider.id,
            balance_sats,
            len(added_entries),
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
        from tallykeep.adapters.custodial_provider_adapter import ProviderError

        since = datetime.now(UTC) - timedelta(days=7)
        try:
            withdrawals = adapter.get_recent_withdrawals(since)
        except ProviderError as exc:
            logger.debug(
                "CustodialPollHandler: get_recent_withdrawals failed for %s: %s",
                provider_id,
                exc,
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
                    "CustodialPollHandler: promoted %d execution(s) to ONCHAIN_PENDING "
                    "for provider %s",
                    updated_count,
                    provider_id,
                )


__all__ = ["CustodialPollHandler"]
