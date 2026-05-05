"""Invoice repository — spec module 03 / 06.

CRUD for the `invoice` table plus a couple of lookups the chain listener
needs (match-by-receiving-address) and the API uses (cross-holding list).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import InvoiceStatus, PaymentType
from tallykeep.domain.invoice import Invoice
from tallykeep.models import InvoiceRow


def _row_to_domain(row: InvoiceRow) -> Invoice:
    return Invoice(
        id=row.id,
        holding_id=row.holding_id,
        invoice_type=PaymentType(row.invoice_type),
        amount_sats=row.amount_sats,
        description=row.description,
        status=InvoiceStatus(row.status),
        expires_at=row.expires_at,
        created_at=row.created_at,
        receiving_address=row.receiving_address,
        receiving_address_id=row.receiving_address_id,
        bip21_uri=row.bip21_uri,
        bolt11=row.bolt11,
        payment_hash=row.payment_hash,
        resulting_ledger_entry_id=row.resulting_ledger_entry_id,
    )


def insert(session: Session, invoice: Invoice) -> None:
    row = InvoiceRow(
        id=invoice.id,
        holding_id=invoice.holding_id,
        invoice_type=invoice.invoice_type.value,
        amount_sats=invoice.amount_sats,
        description=invoice.description,
        status=invoice.status.value,
        receiving_address=invoice.receiving_address,
        receiving_address_id=invoice.receiving_address_id,
        bip21_uri=invoice.bip21_uri,
        bolt11=invoice.bolt11,
        payment_hash=invoice.payment_hash,
        resulting_ledger_entry_id=invoice.resulting_ledger_entry_id,
        expires_at=invoice.expires_at,
    )
    session.add(row)


def get(session: Session, invoice_id: UUID) -> Invoice | None:
    row = session.get(InvoiceRow, invoice_id)
    return _row_to_domain(row) if row is not None else None


def get_open_by_address(
    session: Session, receiving_address: str
) -> Invoice | None:
    """Find an OPEN invoice waiting on `receiving_address`. Used by the
    chain listener when an incoming tx pays one of our watched
    addresses; the invoice that reserved it gets linked to the resulting
    LedgerEntry."""
    row = session.execute(
        select(InvoiceRow).where(
            InvoiceRow.receiving_address == receiving_address,
            InvoiceRow.status == InvoiceStatus.OPEN.value,
        ).order_by(InvoiceRow.created_at.desc()).limit(1)
    ).scalar_one_or_none()
    return _row_to_domain(row) if row is not None else None


def list_filtered(
    session: Session,
    *,
    holding_id: UUID | None = None,
    status: InvoiceStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Invoice]:
    stmt = select(InvoiceRow)
    if holding_id is not None:
        stmt = stmt.where(InvoiceRow.holding_id == holding_id)
    if status is not None:
        stmt = stmt.where(InvoiceRow.status == status.value)
    stmt = stmt.order_by(InvoiceRow.created_at.desc())
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 200))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def mark_paid(
    session: Session,
    invoice_id: UUID,
    *,
    resulting_ledger_entry_id: UUID,
    overpaid: bool,
) -> Invoice | None:
    row = session.get(InvoiceRow, invoice_id)
    if row is None:
        return None
    row.resulting_ledger_entry_id = resulting_ledger_entry_id
    row.status = (
        InvoiceStatus.OVERPAID.value if overpaid else InvoiceStatus.PAID.value
    )
    return _row_to_domain(row)


def cancel(session: Session, invoice_id: UUID) -> Invoice | None:
    row = session.get(InvoiceRow, invoice_id)
    if row is None:
        return None
    if row.status != InvoiceStatus.OPEN.value:
        raise ValueError(
            f"Cannot cancel an Invoice with status={row.status!r}"
        )
    row.status = InvoiceStatus.CANCELLED.value
    return _row_to_domain(row)


__all__ = [
    "cancel",
    "get",
    "get_open_by_address",
    "insert",
    "list_filtered",
    "mark_paid",
]
