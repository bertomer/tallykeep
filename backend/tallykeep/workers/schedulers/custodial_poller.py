"""CustodialPoller — spec module 07 / M8 + M9.

Polls all active CustodialProviders on a fixed interval:
  1. Updates balance rows and publishes `custodial_provider.balance_updated`.
  2. Checks recent withdrawals for pending SweepExecutions and promotes them
     to ONCHAIN_PENDING once the provider supplies a txid.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.domain.enums import SweepExecutionStatus
from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.infrastructure.secrets import LockedError, SecretStore
from tallykeep.repositories import custodial_provider as cp_repo
from tallykeep.repositories import sweep_execution as se_repo


logger = logging.getLogger(__name__)


class CustodialPoller:
    """Background thread that polls exchange balances every `interval_seconds`."""

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

        from tallykeep.adapters.adapter_registry import build_adapter, UnsupportedAdapterError
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

            try:
                adapter = build_adapter(
                    provider.adapter_id,
                    api_key=api_key,
                    api_secret=api_secret,
                    api_passphrase=api_passphrase,
                )
                balance_sats = adapter.get_balance()
            except (ProviderAuthError, ProviderError, UnsupportedAdapterError) as exc:
                logger.warning(
                    "CustodialPoller: poll failed for provider %s: %s", provider.id, exc
                )
                with self._session_factory() as session:
                    cp_repo.update_error(
                        session,
                        provider.id,
                        error=str(exc),
                        polled_at=datetime.now(UTC),
                    )
                    session.commit()
                continue
            except Exception:  # noqa: BLE001
                logger.exception("CustodialPoller: unexpected error for provider %s", provider.id)
                continue

            with self._session_factory() as session:
                updated = cp_repo.update_balance(
                    session,
                    provider.id,
                    balance_sats=balance_sats,
                    polled_at=datetime.now(UTC),
                )
                session.commit()

            self._bus.publish(
                "custodial_provider.balance_updated",
                {
                    "provider_id": str(provider.id),
                    "holding_id": str(provider.holding_id),
                    "balance_sats": balance_sats,
                },
            )
            logger.debug(
                "CustodialPoller: updated provider %s balance=%d sats", provider.id, balance_sats
            )

            # Check if any REQUESTED executions now have a txid from the exchange.
            self._check_withdrawal_txids(provider.id, adapter)


    def _check_withdrawal_txids(self, provider_id: UUID, adapter) -> None:  # type: ignore[no-untyped-def]
        """For REQUESTED executions on this provider, try to find the on-chain txid."""
        from datetime import timedelta
        from tallykeep.adapters.custodial_provider_adapter import ProviderError

        since = datetime.now(UTC) - timedelta(days=7)
        try:
            withdrawals = adapter.get_recent_withdrawals(since)
        except ProviderError as exc:
            logger.debug("CustodialPoller: get_recent_withdrawals failed for %s: %s", provider_id, exc)
            return

        txid_by_withdrawal_id = {
            w.id: w.txid for w in withdrawals if w.txid
        }
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
                    updated_count, provider_id,
                )


__all__ = ["CustodialPoller"]
