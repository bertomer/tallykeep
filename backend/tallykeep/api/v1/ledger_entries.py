"""LedgerEntry endpoints — spec module 04. Stubs land in M5."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["ledger-entries"])


@router.get("/ledger-entries", status_code=501)
async def list_ledger_entries(
    holding_id: UUID | None = None,
    direction: str | None = None,
    category: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    uncategorized: bool = False,
) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/ledger-entries"
    )


@router.get("/ledger-entries/pending-categorization", status_code=501)
async def pending_categorization() -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/ledger-entries/pending-categorization"
    )


@router.get("/ledger-entries/{entry_id}", status_code=501)
async def get_ledger_entry(entry_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/ledger-entries/{id}"
    )


@router.patch("/ledger-entries/{entry_id}", status_code=501)
async def patch_ledger_entry(entry_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="PATCH /api/v1/ledger-entries/{id}"
    )
