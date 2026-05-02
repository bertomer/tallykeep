"""Lightning endpoints — spec module 04 / 08.

Per spec module 08: every Lightning route exists in v1's FastAPI router with
stub handlers returning 501 Not Implemented. This reserves the URL space and
keeps the OpenAPI spec consistent across versions. Real implementations land
with v1.5 once the dedicated Lightning Q&A session is done.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(prefix="/lightning", tags=["lightning"])


@router.get("/status", status_code=501)
async def lightning_status() -> JSONResponse:
    return not_implemented_response(
        milestone="v1.5", route="GET /api/v1/lightning/status"
    )


@router.get("/balance", status_code=501)
async def lightning_balance() -> JSONResponse:
    return not_implemented_response(
        milestone="v1.5", route="GET /api/v1/lightning/balance"
    )


@router.post("/invoices", status_code=501)
async def lightning_create_invoice() -> JSONResponse:
    return not_implemented_response(
        milestone="v1.5", route="POST /api/v1/lightning/invoices"
    )


@router.post("/pay", status_code=501)
async def lightning_pay() -> JSONResponse:
    return not_implemented_response(
        milestone="v1.5", route="POST /api/v1/lightning/pay"
    )


@router.get("/payments", status_code=501)
async def lightning_payments() -> JSONResponse:
    return not_implemented_response(
        milestone="v1.5", route="GET /api/v1/lightning/payments"
    )


@router.get("/channels", status_code=501)
async def lightning_channels() -> JSONResponse:
    return not_implemented_response(
        milestone="v1.5", route="GET /api/v1/lightning/channels"
    )
