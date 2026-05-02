"""Security and blueprint analysis endpoints — spec module 04 / 05. M5."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/holding/{holding_id}/security", status_code=501)
async def holding_security(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/analysis/holding/{id}/security"
    )


@router.get("/holding/{holding_id}/blueprint", status_code=501)
async def holding_blueprint(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/analysis/holding/{id}/blueprint"
    )


@router.get("/utxo/{utxo_id}", status_code=501)
async def utxo_blueprint(utxo_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/analysis/utxo/{id}"
    )


@router.post("/recompute", status_code=501)
async def recompute_analysis() -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="POST /api/v1/analysis/recompute"
    )
