"""Banking endpoints — spec module 04 / 06. Stubs land in M6."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(prefix="/banking", tags=["banking"])


# --- Outgoing payment requests --------------------------------------------------


@router.get("/payment-requests", status_code=501)
async def list_payment_requests(
    holding_id: UUID | None = None, status: str | None = None
) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="GET /api/v1/banking/payment-requests"
    )


@router.post("/payment-requests", status_code=501)
async def create_payment_request() -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="POST /api/v1/banking/payment-requests"
    )


@router.get("/payment-requests/{request_id}", status_code=501)
async def get_payment_request(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="GET /api/v1/banking/payment-requests/{id}"
    )


@router.get("/payment-requests/{request_id}/psbt", status_code=501)
async def get_payment_psbt(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="GET /api/v1/banking/payment-requests/{id}/psbt"
    )


@router.get("/payment-requests/{request_id}/psbt.qr", status_code=501)
async def get_payment_psbt_qr(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6",
        route="GET /api/v1/banking/payment-requests/{id}/psbt.qr",
    )


@router.post("/payment-requests/{request_id}/submit-signed", status_code=501)
async def submit_signed_payment(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6",
        route="POST /api/v1/banking/payment-requests/{id}/submit-signed",
    )


@router.post("/payment-requests/{request_id}/broadcast", status_code=501)
async def broadcast_payment(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6",
        route="POST /api/v1/banking/payment-requests/{id}/broadcast",
    )


@router.post("/payment-requests/{request_id}/cancel", status_code=501)
async def cancel_payment_request(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6",
        route="POST /api/v1/banking/payment-requests/{id}/cancel",
    )


@router.post("/fee-estimate", status_code=501)
async def fee_estimate() -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="POST /api/v1/banking/fee-estimate"
    )


# --- Incoming invoices ----------------------------------------------------------


@router.get("/invoices", status_code=501)
async def list_invoices(
    holding_id: UUID | None = None, status: str | None = None
) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="GET /api/v1/banking/invoices"
    )


@router.post("/invoices", status_code=501)
async def create_invoice() -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="POST /api/v1/banking/invoices"
    )


@router.get("/invoices/{invoice_id}", status_code=501)
async def get_invoice(invoice_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="GET /api/v1/banking/invoices/{id}"
    )


@router.get("/invoices/{invoice_id}/qr", status_code=501)
async def get_invoice_qr(invoice_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="GET /api/v1/banking/invoices/{id}/qr"
    )


@router.post("/invoices/{invoice_id}/cancel", status_code=501)
async def cancel_invoice(invoice_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6", route="POST /api/v1/banking/invoices/{id}/cancel"
    )
