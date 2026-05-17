"""CustodialLedgerEntry repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.models.custodial_ledger_entry import CustodialLedgerEntryRow


def exists(session: Session, *, custodial_provider_id: UUID, provider_entry_id: str) -> bool:
    return (
        session.execute(
            select(CustodialLedgerEntryRow.id).where(
                CustodialLedgerEntryRow.custodial_provider_id == custodial_provider_id,
                CustodialLedgerEntryRow.provider_entry_id == provider_entry_id,
            )
        ).first()
        is not None
    )


def create(session: Session, row: CustodialLedgerEntryRow) -> None:
    session.add(row)


def list_since(
    session: Session,
    custodial_provider_id: UUID,
    *,
    limit: int = 100,
) -> list[CustodialLedgerEntryRow]:
    return (
        session.execute(
            select(CustodialLedgerEntryRow)
            .where(CustodialLedgerEntryRow.custodial_provider_id == custodial_provider_id)
            .order_by(CustodialLedgerEntryRow.timestamp.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
