"""Internal custodial endpoints — not part of the public API surface.

POST /api/v1/internal/custodial/{provider_id}/poll-cycle

Loopback-only by convention (per 01_architecture.md §"Network security posture").
Process-level shared-token hardening is deferred to a later hosted-tier iteration.

The lock middleware applies: returns 423 when the secret store is locked, same as
every other secret-requiring endpoint (04_api_conventions.md).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session, get_event_bus, get_secret_store
from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.infrastructure.secrets import LockedError, SecretStore
from tallykeep.models.custodial_ledger_entry import CustodialLedgerEntryRow
from tallykeep.repositories import custodial_ledger_entry as cle_repo
from tallykeep.repositories import custodial_provider as cp_repo


logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal"])

_SATS = 100_000_000
_N_UNREACHABLE = 5


class PollCycleOut(BaseModel):
    rows_added: int
    rows_updated: int
    rows_unchanged: int
    last_polled_at: datetime
    connection_status: str


@router.post(
    "/internal/custodial/{provider_id}/poll-cycle",
    response_model=PollCycleOut,
    responses={
        423: {"description": "Secret store is locked"},
        404: {"description": "Provider not found or archived"},
    },
)
async def poll_cycle(
    provider_id: UUID,
    session: Session = Depends(get_db_session),
    secret_store: SecretStore = Depends(get_secret_store),
    bus: EventBus | None = Depends(get_event_bus),
) -> PollCycleOut:
    from tallykeep.adapters.adapter_registry import UnsupportedAdapterError, build_adapter
    from tallykeep.adapters.custodial_provider_adapter import ProviderAuthError, ProviderError

    provider = cp_repo.get(session, provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status_code=404, detail="Provider not found or archived")

    try:
        api_key = secret_store.get_secret(provider.api_credential_reference).decode()
        api_secret = secret_store.get_secret(provider.api_secret_reference).decode()
        api_passphrase = (
            secret_store.get_secret(provider.api_passphrase_reference).decode()
            if provider.api_passphrase_reference
            else None
        )
    except (KeyError, LockedError) as exc:
        logger.warning("poll_cycle: cannot read secrets for provider %s: %s", provider_id, exc)
        raise HTTPException(status_code=423, detail="Secrets unavailable") from exc

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
        cursor = cp_repo.get_ledger_cursor(session, provider_id)
        new_entries, newest_ts = adapter.fetch_ledger_since(cursor)
    except ProviderAuthError as exc:
        logger.warning("poll_cycle: auth error for provider %s: %s", provider_id, exc)
        _handle_auth_error(session, provider, str(exc), polled_at)
        if bus is not None:
            _emit_connection_state_changed(bus, provider, "auth_failed")
        raise HTTPException(status_code=502, detail=f"Provider auth error: {exc}") from exc
    except (ProviderError, UnsupportedAdapterError) as exc:
        logger.warning("poll_cycle: transient error for provider %s: %s", provider_id, exc)
        new_status = _handle_transient_error(session, provider, str(exc), polled_at)
        if bus is not None and provider.connection_status != new_status:
            _emit_connection_state_changed(bus, provider, new_status)
        raise HTTPException(status_code=502, detail=f"Provider error: {exc}") from exc

    # --- persist ---
    added_entries: list[CustodialLedgerEntryRow] = []
    updated_entries: list[tuple[CustodialLedgerEntryRow, list[str]]] = []

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

    rows_unchanged = len(new_entries) - len(added_entries) - len(updated_entries)

    cp_repo.update_balance(session, provider_id, balance_sats=balance_sats, polled_at=polled_at)
    cp_repo.update_non_btc_balances(session, provider_id, balances=other_balances)
    if newest_ts is not None:
        cp_repo.update_ledger_cursor(session, provider_id, cursor_at=newest_ts)

    old_status = provider.connection_status
    cp_repo.update_connection_status(
        session,
        provider_id,
        status="healthy",
        consecutive_error_count=0,
        polled_at=polled_at,
    )
    session.commit()

    # --- emit events ---
    if bus is not None:
        _emit_cycle_events(
            bus, provider, balance_sats, added_entries, updated_entries, polled_at, old_status
        )

    # --- check withdrawal txids (best-effort) ---
    try:
        _check_withdrawal_txids(session, provider_id, adapter)
    except Exception:  # noqa: BLE001
        logger.debug("poll_cycle: withdrawal txid check failed for %s", provider_id)

    return PollCycleOut(
        rows_added=len(added_entries),
        rows_updated=len(updated_entries),
        rows_unchanged=max(0, rows_unchanged),
        last_polled_at=polled_at,
        connection_status="healthy",
    )


# --- helpers -----------------------------------------------------------------


def _handle_auth_error(session: Session, provider, error: str, polled_at: datetime) -> None:  # type: ignore[no-untyped-def]
    if provider.connection_status == "auth_failed":
        return
    cp_repo.update_connection_status(
        session,
        provider.id,
        status="auth_failed",
        consecutive_error_count=0,
        polled_at=polled_at,
        error=error,
    )
    session.commit()


def _handle_transient_error(session: Session, provider, error: str, polled_at: datetime) -> str:  # type: ignore[no-untyped-def]
    if provider.connection_status == "auth_failed":
        return "auth_failed"
    new_count = provider.consecutive_error_count + 1
    if new_count >= _N_UNREACHABLE:
        new_status = "unreachable"
    elif provider.connection_status == "healthy":
        new_status = "degraded"
    else:
        new_status = provider.connection_status
    cp_repo.update_connection_status(
        session,
        provider.id,
        status=new_status,
        consecutive_error_count=new_count,
        polled_at=polled_at,
        error=error,
    )
    session.commit()
    return new_status


def _emit_cycle_events(
    bus,  # type: ignore[no-untyped-def]
    provider,  # type: ignore[no-untyped-def]
    balance_sats: int,
    added_entries: list[CustodialLedgerEntryRow],
    updated_entries: list[tuple[CustodialLedgerEntryRow, list[str]]],
    polled_at: datetime,
    old_status: str,
) -> None:
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

    bus.publish(
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
        bus.publish(
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
        bus.publish(
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
        _emit_connection_state_changed(bus, provider, "healthy")


def _emit_connection_state_changed(bus, provider, new_status: str) -> None:  # type: ignore[no-untyped-def]
    bus.publish(
        "treasury.custodial.connection_state_changed",
        {
            "holding_id": str(provider.holding_id),
            "provider_id": str(provider.id),
            "old_status": provider.connection_status,
            "new_status": new_status,
        },
    )


def _check_withdrawal_txids(session: Session, provider_id: UUID, adapter) -> None:  # type: ignore[no-untyped-def]
    from tallykeep.adapters.custodial_provider_adapter import ProviderError
    from tallykeep.domain.enums import SweepExecutionStatus
    from tallykeep.repositories import sweep_execution as se_repo

    since = datetime.now(UTC) - timedelta(days=7)
    try:
        withdrawals = adapter.get_recent_withdrawals(since)
    except ProviderError:
        return

    txid_by_withdrawal_id = {w.id: w.txid for w in withdrawals if w.txid}
    if not txid_by_withdrawal_id:
        return

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


__all__ = ["router"]
