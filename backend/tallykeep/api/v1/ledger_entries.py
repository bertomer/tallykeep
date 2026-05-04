"""LedgerEntry endpoints — spec module 04 / 05.

Implements:
  - GET /api/v1/ledger-entries (filtered list)
  - GET /api/v1/ledger-entries/{id}
  - GET /api/v1/ledger-entries/pending-categorization
  - PATCH /api/v1/ledger-entries/{id}

The auto-categorization heuristics live in
`services/categorizer_service.py` and run inside the
CategorizerSuggester subscriber. The PATCH endpoint here lets the user
accept the suggestion or override it explicitly; that's what binds the
`category` field. `suggested_category` is informational and never set by
this endpoint.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.domain.enums import Direction, LedgerCategory
from tallykeep.repositories import ledger_entry as ledger_repo


router = APIRouter(tags=["ledger-entries"])


# --- response shapes --------------------------------------------------------


class HoldingLink(BaseModel):
    holding_id: UUID
    holding_amount_sats: int


class LedgerEntryOut(BaseModel):
    id: UUID
    direction: str
    net_amount_sats: int
    fee_sats: int | None
    timestamp: datetime
    source: str
    source_reference: str
    category: str | None
    counterparty_label: str | None
    note: str | None
    suggested_category: str | None
    categorized_at: datetime | None
    created_at: datetime
    holdings: list[HoldingLink]


class LedgerEntryListResponse(BaseModel):
    entries: list[LedgerEntryOut]


class LedgerEntryPatch(BaseModel):
    category: str | None = None
    counterparty_label: str | None = None
    note: str | None = None


def _to_out(session: Session, entry) -> LedgerEntryOut:  # type: ignore[no-untyped-def]
    holdings = [
        HoldingLink(holding_id=h_id, holding_amount_sats=amt)
        for h_id, amt in ledger_repo.list_holdings_for_entry(session, entry.id)
    ]
    return LedgerEntryOut(
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
        created_at=entry.created_at,
        holdings=holdings,
    )


# --- endpoints --------------------------------------------------------------


@router.get("/ledger-entries", response_model=LedgerEntryListResponse)
async def list_ledger_entries(
    holding_id: UUID | None = None,
    direction: str | None = None,
    category: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    uncategorized: bool = False,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> LedgerEntryListResponse:
    """List ledger entries with optional filtering.

    `direction` and `category`, when given, must be valid enum values
    (`incoming|outgoing|internal` and the LedgerCategory set respectively).
    Bad values yield 400.
    """
    try:
        direction_enum = Direction(direction) if direction else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        category_enum = LedgerCategory(category) if category else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    entries = ledger_repo.list_filtered(
        session,
        holding_id=holding_id,
        direction=direction_enum,
        category=category_enum,
        uncategorized_only=uncategorized,
        from_timestamp=from_date,
        to_timestamp=to_date,
        limit=limit,
        offset=offset,
    )
    return LedgerEntryListResponse(
        entries=[_to_out(session, e) for e in entries]
    )


@router.get(
    "/ledger-entries/pending-categorization",
    response_model=LedgerEntryListResponse,
)
async def pending_categorization(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> LedgerEntryListResponse:
    """Convenience: every entry without a binding category, newest first."""
    entries = ledger_repo.list_filtered(
        session,
        uncategorized_only=True,
        limit=limit,
        offset=offset,
    )
    return LedgerEntryListResponse(
        entries=[_to_out(session, e) for e in entries]
    )


@router.get("/ledger-entries/{entry_id}", response_model=LedgerEntryOut)
async def get_ledger_entry(
    entry_id: UUID, session: Session = Depends(get_db_session)
) -> LedgerEntryOut:
    entry = ledger_repo.get(session, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="LedgerEntry not found")
    return _to_out(session, entry)


@router.patch("/ledger-entries/{entry_id}", response_model=LedgerEntryOut)
async def patch_ledger_entry(
    entry_id: UUID,
    body: LedgerEntryPatch,
    session: Session = Depends(get_db_session),
) -> LedgerEntryOut:
    """Update category / counterparty_label / note.

    Setting `category` flips the entry from "pending" to "confirmed" and
    stamps `categorized_at`. Setting `category` is the only way to bind
    a category — `suggested_category` is informational.
    """
    try:
        category_enum = (
            LedgerCategory(body.category) if body.category is not None else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated = ledger_repo.patch(
        session,
        entry_id,
        category=category_enum,
        counterparty_label=body.counterparty_label,
        note=body.note,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="LedgerEntry not found")
    session.commit()
    return _to_out(session, updated)
