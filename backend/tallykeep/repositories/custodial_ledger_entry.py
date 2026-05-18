"""CustodialLedgerEntry repository — ADR-0013 mirror posture."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from tallykeep.models.custodial_ledger_entry import CustodialLedgerEntryRow


@dataclass
class UpsertResult:
    row: CustodialLedgerEntryRow
    is_new: bool
    changed_fields: list[str]  # field names that changed (empty for new rows)


def get_by_refid(
    session: Session,
    *,
    custodial_provider_id: UUID,
    provider_entry_id: str,
) -> CustodialLedgerEntryRow | None:
    return session.execute(
        select(CustodialLedgerEntryRow).where(
            CustodialLedgerEntryRow.custodial_provider_id == custodial_provider_id,
            CustodialLedgerEntryRow.provider_entry_id == provider_entry_id,
        )
    ).scalar_one_or_none()


def upsert(
    session: Session,
    row: CustodialLedgerEntryRow,
) -> UpsertResult:
    """Insert or update a ledger entry keyed by (custodial_provider_id, provider_entry_id).

    Returns UpsertResult with is_new=True for inserts, changed_fields for updates.
    Callers must commit after calling this.
    """
    existing = get_by_refid(
        session,
        custodial_provider_id=row.custodial_provider_id,
        provider_entry_id=row.provider_entry_id,
    )
    if existing is None:
        session.add(row)
        return UpsertResult(row=row, is_new=True, changed_fields=[])

    # Compare mutable fields — status and raw_payload can change between polls.
    changed: list[str] = []
    mutable_fields = ("kind", "amount_sats", "fee_sats", "status", "raw_payload")
    for field in mutable_fields:
        if getattr(existing, field) != getattr(row, field):
            setattr(existing, field, getattr(row, field))
            changed.append(field)

    if changed:
        existing.updated_at = datetime.now(UTC)

    return UpsertResult(row=existing, is_new=False, changed_fields=changed)


def create(session: Session, row: CustodialLedgerEntryRow) -> None:
    session.add(row)


def set_reconciled(
    session: Session,
    entry_id: UUID,
    *,
    linked_sweep_execution_id: UUID | None,
    linked_counterparty_holding_id: UUID | None,
    linked_chain_ledger_entry_id: UUID | None,
) -> None:
    session.execute(
        update(CustodialLedgerEntryRow)
        .where(CustodialLedgerEntryRow.id == entry_id)
        .values(
            linked_sweep_execution_id=linked_sweep_execution_id,
            linked_counterparty_holding_id=linked_counterparty_holding_id,
            linked_chain_ledger_entry_id=linked_chain_ledger_entry_id,
            reconciled_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )


def mark_unmatched(session: Session, entry_id: UUID) -> None:
    """Set reconciled_at with linkage FKs still null — pure observation entry."""
    session.execute(
        update(CustodialLedgerEntryRow)
        .where(CustodialLedgerEntryRow.id == entry_id)
        .values(
            reconciled_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )


def list_paginated(
    session: Session,
    custodial_provider_id: UUID,
    *,
    limit: int = 50,
    before_timestamp: datetime | None = None,
) -> list[CustodialLedgerEntryRow]:
    """Return up to `limit` entries ordered by timestamp desc.

    Pass `before_timestamp` (exclusive) to page forward through older entries.
    """
    q = (
        select(CustodialLedgerEntryRow)
        .where(CustodialLedgerEntryRow.custodial_provider_id == custodial_provider_id)
        .order_by(CustodialLedgerEntryRow.timestamp.desc())
        .limit(limit)
    )
    if before_timestamp is not None:
        q = q.where(CustodialLedgerEntryRow.timestamp < before_timestamp)
    return list(session.execute(q).scalars().all())


def list_since(
    session: Session,
    custodial_provider_id: UUID,
    *,
    limit: int = 100,
) -> list[CustodialLedgerEntryRow]:
    return list(
        session.execute(
            select(CustodialLedgerEntryRow)
            .where(CustodialLedgerEntryRow.custodial_provider_id == custodial_provider_id)
            .order_by(CustodialLedgerEntryRow.timestamp.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
