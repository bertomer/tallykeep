"""Holdings endpoints — spec module 04. Stubs land in M4 (creation) and M5 (queries)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["holdings"])


# --- Cross-type queries ---------------------------------------------------------


@router.get("/holdings", status_code=501)
async def list_holdings(
    holding_type: str | None = None,
    purpose: str | None = None,
    include_archived: bool = False,
) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/holdings"
    )


@router.get("/holdings/summary/global", status_code=501)
async def global_holdings_summary() -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/holdings/summary/global"
    )


@router.get("/holdings/{holding_id}", status_code=501)
async def get_holding(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/holdings/{id}"
    )


@router.patch("/holdings/{holding_id}", status_code=501)
async def patch_holding(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="PATCH /api/v1/holdings/{id}"
    )


@router.post("/holdings/{holding_id}/archive", status_code=501)
async def archive_holding(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="POST /api/v1/holdings/{id}/archive"
    )


@router.post("/holdings/{holding_id}/change-type", status_code=501)
async def change_holding_type(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="POST /api/v1/holdings/{id}/change-type"
    )


@router.get("/holdings/{holding_id}/summary", status_code=501)
async def holding_summary(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/holdings/{id}/summary"
    )


# --- Per-type creation ---------------------------------------------------------


@router.post("/holdings/account", status_code=501)
async def create_account_holding() -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="POST /api/v1/holdings/account"
    )


@router.post("/holdings/purse", status_code=501)
async def create_purse_holding() -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="POST /api/v1/holdings/purse"
    )


@router.post("/holdings/strongbox", status_code=501)
async def create_strongbox_holding() -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="POST /api/v1/holdings/strongbox"
    )


@router.post("/holdings/vault", status_code=501)
async def create_vault_holding() -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="POST /api/v1/holdings/vault"
    )
