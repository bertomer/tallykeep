"""LedgerEntry repository — the user-facing record of a value movement.

Spec module 02: every LedgerEntry must point to exactly one source object
(`source` + `source_reference`). Entries are linked to one or more Holdings
via `ledger_entry_holding_link`. Internal transfers between two of the user's
own Holdings produce a single LedgerEntry that touches both rows in the link
table.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import (
    Direction,
    LedgerCategory,
    LedgerEntrySource,
)
from tallykeep.domain.ledger_entry import (
    LedgerEntry,
    LedgerEntryHoldingLink,
)
from tallykeep.models import LedgerEntryHoldingLinkRow, LedgerEntryRow


def _row_to_domain(row: LedgerEntryRow) -> LedgerEntry:
    return LedgerEntry(
        id=row.id,
        direction=Direction(row.direction),
        net_amount_sats=row.net_amount_sats,
        fee_sats=row.fee_sats,
        timestamp=row.timestamp,
        source=LedgerEntrySource(row.source),
        source_reference=row.source_reference,
        category=LedgerCategory(row.category) if row.category else None,
        counterparty_label=row.counterparty_label,
        note=row.note,
        suggested_category=(
            LedgerCategory(row.suggested_category)
            if row.suggested_category
            else None
        ),
        categorized_at=row.categorized_at,
        created_at=row.created_at,
    )


def get(session: Session, entry_id: UUID) -> LedgerEntry | None:
    row = session.get(LedgerEntryRow, entry_id)
    return _row_to_domain(row) if row is not None else None


def get_by_source(
    session: Session, source: LedgerEntrySource, source_reference: str
) -> LedgerEntry | None:
    """Look up by (source, source_reference). Used during scan to avoid
    creating duplicate entries when re-importing the same on-chain tx."""
    row = session.execute(
        select(LedgerEntryRow).where(
            LedgerEntryRow.source == source.value,
            LedgerEntryRow.source_reference == source_reference,
        )
    ).scalar_one_or_none()
    return _row_to_domain(row) if row is not None else None


def insert(
    session: Session,
    entry: LedgerEntry,
    *,
    holding_links: list[LedgerEntryHoldingLink] | None = None,
) -> None:
    """Persist a new LedgerEntry plus its holding links.

    Flushes between the entry insert and any link inserts so the FK from
    `ledger_entry_holding_link.ledger_entry_id -> ledger_entry.id` is
    satisfied even when many entries are added in the same transaction.
    Without the flush SQLAlchemy may batch all link inserts before all
    entry inserts and trip the constraint.
    """
    row = LedgerEntryRow(
        id=entry.id,
        direction=entry.direction.value,
        net_amount_sats=entry.net_amount_sats,
        fee_sats=entry.fee_sats,
        timestamp=entry.timestamp,
        source=entry.source.value,
        source_reference=entry.source_reference,
        category=entry.category.value if entry.category else None,
        counterparty_label=entry.counterparty_label,
        note=entry.note,
        suggested_category=(
            entry.suggested_category.value if entry.suggested_category else None
        ),
        categorized_at=entry.categorized_at,
    )
    session.add(row)
    if holding_links:
        session.flush()  # entry must exist before its links can FK to it
        for link in holding_links:
            session.add(
                LedgerEntryHoldingLinkRow(
                    ledger_entry_id=link.ledger_entry_id,
                    holding_id=link.holding_id,
                    holding_amount_sats=link.holding_amount_sats,
                )
            )


def list_filtered(
    session: Session,
    *,
    holding_id: UUID | None = None,
    direction: Direction | None = None,
    category: LedgerCategory | None = None,
    uncategorized_only: bool = False,
    from_timestamp: datetime | None = None,
    to_timestamp: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[LedgerEntry]:
    """Cross-holding LedgerEntry query.

    `holding_id`, when set, joins through `ledger_entry_holding_link` so that
    only entries touching that holding come back. The other filters apply to
    the entry row directly.
    """
    stmt = select(LedgerEntryRow)
    if holding_id is not None:
        stmt = stmt.join(
            LedgerEntryHoldingLinkRow,
            LedgerEntryHoldingLinkRow.ledger_entry_id == LedgerEntryRow.id,
        ).where(LedgerEntryHoldingLinkRow.holding_id == holding_id)
    if direction is not None:
        stmt = stmt.where(LedgerEntryRow.direction == direction.value)
    if category is not None:
        stmt = stmt.where(LedgerEntryRow.category == category.value)
    if uncategorized_only:
        stmt = stmt.where(LedgerEntryRow.category.is_(None))
    if from_timestamp is not None:
        stmt = stmt.where(LedgerEntryRow.timestamp >= from_timestamp)
    if to_timestamp is not None:
        stmt = stmt.where(LedgerEntryRow.timestamp <= to_timestamp)
    stmt = stmt.order_by(LedgerEntryRow.timestamp.desc())
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 200))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def list_holdings_for_entry(
    session: Session, entry_id: UUID
) -> list[tuple[UUID, int]]:
    """Return (holding_id, holding_amount_sats) tuples for one entry."""
    rows = session.execute(
        select(
            LedgerEntryHoldingLinkRow.holding_id,
            LedgerEntryHoldingLinkRow.holding_amount_sats,
        ).where(LedgerEntryHoldingLinkRow.ledger_entry_id == entry_id)
    ).all()
    return [(r[0], int(r[1])) for r in rows]


def list_for_holding(
    session: Session,
    holding_id: UUID,
    *,
    direction: Direction | None = None,
    uncategorized_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[LedgerEntry]:
    stmt = (
        select(LedgerEntryRow)
        .join(
            LedgerEntryHoldingLinkRow,
            LedgerEntryHoldingLinkRow.ledger_entry_id == LedgerEntryRow.id,
        )
        .where(LedgerEntryHoldingLinkRow.holding_id == holding_id)
    )
    if direction is not None:
        stmt = stmt.where(LedgerEntryRow.direction == direction.value)
    if uncategorized_only:
        stmt = stmt.where(LedgerEntryRow.category.is_(None))
    stmt = stmt.order_by(LedgerEntryRow.timestamp.desc())
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 200))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def patch(
    session: Session,
    entry_id: UUID,
    *,
    category: LedgerCategory | None = None,
    counterparty_label: str | None = None,
    note: str | None = None,
) -> LedgerEntry | None:
    row = session.get(LedgerEntryRow, entry_id)
    if row is None:
        return None
    if category is not None:
        row.category = category.value
        row.categorized_at = datetime.now(row.timestamp.tzinfo) if row.timestamp.tzinfo else datetime.utcnow()
    if counterparty_label is not None:
        row.counterparty_label = counterparty_label
    if note is not None:
        row.note = note
    return _row_to_domain(row)


__all__ = [
    "get",
    "get_by_source",
    "insert",
    "list_filtered",
    "list_for_holding",
    "list_holdings_for_entry",
    "patch",
]
