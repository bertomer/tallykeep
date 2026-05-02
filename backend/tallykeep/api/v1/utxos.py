"""UTXO endpoints — spec module 04. Stubs land in M5."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["utxos"])


@router.get("/utxos", status_code=501)
async def list_utxos(
    descriptor_id: UUID | None = None,
    holding_id: UUID | None = None,
    min_value_sats: int | None = None,
    frozen: bool | None = None,
) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/utxos"
    )


@router.post("/utxos/{utxo_id}/freeze", status_code=501)
async def freeze_utxo(utxo_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="POST /api/v1/utxos/{id}/freeze"
    )


@router.post("/utxos/{utxo_id}/unfreeze", status_code=501)
async def unfreeze_utxo(utxo_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="POST /api/v1/utxos/{id}/unfreeze"
    )


@router.get("/utxos/{utxo_id}/hygiene", status_code=501)
async def utxo_hygiene(utxo_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/utxos/{id}/hygiene"
    )
