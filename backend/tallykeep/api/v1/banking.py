"""Banking endpoints — spec module 04 / 06.

M6.1 implements the construction half of the outgoing flow:

  - POST /api/v1/banking/payment-requests
  - GET  /api/v1/banking/payment-requests
  - GET  /api/v1/banking/payment-requests/{id}
  - GET  /api/v1/banking/payment-requests/{id}/psbt
        (returns base64 in JSON; binary form via Accept: application/octet-stream)

submit-signed / broadcast / cancel / fee-estimate / QR / Invoice flow
land in M6.2..M6.4 and stay 501 for now.
"""

from __future__ import annotations

import base64
import binascii
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import DescriptorAdapter
from tallykeep.adapters.node_adapter import NodeAdapter
from tallykeep.api.dependencies import (
    get_db_session,
    get_event_bus,
    get_node_adapter,
)
from tallykeep.api.v1._stubs import not_implemented_response
from tallykeep.domain.enums import PaymentStatus
from tallykeep.repositories import payment_request as payment_request_repo
from tallykeep.services import banking_service
from tallykeep.services.banking_service import (
    HoldingCannotSend,
    HoldingNotFound,
    InFlightPaymentExists,
    InsufficientBalance,
    InvalidDestination,
    PaymentRequestBuildResult,
)


router = APIRouter(prefix="/banking", tags=["banking"])


# Single shared descriptor adapter — bdkpython is stateless on this surface.
_DESCRIPTOR_ADAPTER = DescriptorAdapter()


# --- request / response shapes ---------------------------------------------


class PaymentRequestCreate(BaseModel):
    holding_id: UUID
    destination: str
    amount_sats: int | None = None  # None = drain wallet
    fee_strategy: str | None = "normal"  # economy | normal | priority
    fee_sat_per_vbyte: float | None = None  # explicit override
    description: str | None = None
    confirmed: bool = False  # Vault long-term guardrail acknowledgement


class PaymentRequestOut(BaseModel):
    id: UUID
    holding_id: UUID
    payment_type: str
    status: str
    amount_sats: int | None
    description: str | None
    destination_address: str | None
    bip21_uri: str | None
    psbt_base64: str | None
    signed_transaction_hex: str | None
    broadcast_txid: str | None
    resulting_ledger_entry_id: UUID | None


class PaymentRequestListResponse(BaseModel):
    payment_requests: list[PaymentRequestOut]


class ConfirmationRequiredResponse(BaseModel):
    requires_confirmation: bool = True
    message: str


def _to_out(req) -> PaymentRequestOut:  # type: ignore[no-untyped-def]
    return PaymentRequestOut(
        id=req.id,
        holding_id=req.holding_id,
        payment_type=req.payment_type.value,
        status=req.status.value,
        amount_sats=req.amount_sats,
        description=req.description,
        destination_address=req.destination_address,
        bip21_uri=req.bip21_uri,
        psbt_base64=req.psbt_base64,
        signed_transaction_hex=req.signed_transaction_hex,
        broadcast_txid=req.broadcast_txid,
        resulting_ledger_entry_id=req.resulting_ledger_entry_id,
    )


# --- create ----------------------------------------------------------------


@router.post(
    "/payment-requests",
    responses={
        201: {"model": PaymentRequestOut},
        200: {"model": ConfirmationRequiredResponse},
    },
)
async def create_payment_request(
    body: PaymentRequestCreate,
    request: Request,
    session: Session = Depends(get_db_session),
    node: NodeAdapter = Depends(get_node_adapter),
):  # type: ignore[no-untyped-def]
    """Construct a PSBT for the user to sign externally.

    On the first attempt against a long-term Vault, the response is a
    200 with `requires_confirmation=true` instead of the usual 201; the
    user re-submits with `confirmed=true` after acknowledging the
    warning.
    """
    try:
        result: PaymentRequestBuildResult = banking_service.build_payment_request(
            session,
            holding_id=body.holding_id,
            destination_address=body.destination,
            amount_sats=body.amount_sats,
            fee_strategy=body.fee_strategy,
            fee_sat_per_vbyte=body.fee_sat_per_vbyte,
            description=body.description,
            confirmed_long_term=body.confirmed,
            descriptor_adapter=_DESCRIPTOR_ADAPTER,
            node=node,
        )
    except HoldingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HoldingCannotSend as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "/errors/account-cannot-send",
                "title": "This holding cannot create on-chain payment requests",
                "detail": str(exc),
            },
        ) from exc
    except InsufficientBalance as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidDestination as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InFlightPaymentExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except banking_service.BankingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result.requires_confirmation:
        return JSONResponse(
            status_code=200,
            content={
                "requires_confirmation": True,
                "message": result.confirmation_message,
            },
        )

    assert result.payment_request is not None
    session.commit()

    bus = get_event_bus(request)
    if bus is not None:
        bus.publish(
            "banking.payment_request.created",
            {
                "id": str(result.payment_request.id),
                "holding_id": str(result.payment_request.holding_id),
            },
        )

    return JSONResponse(
        status_code=201,
        content=_to_out(result.payment_request).model_dump(mode="json"),
    )


# --- list / get ------------------------------------------------------------


@router.get(
    "/payment-requests",
    response_model=PaymentRequestListResponse,
)
async def list_payment_requests(
    holding_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> PaymentRequestListResponse:
    try:
        status_enum = PaymentStatus(status) if status else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    requests = payment_request_repo.list_filtered(
        session,
        holding_id=holding_id,
        status=status_enum,
        limit=limit,
        offset=offset,
    )
    return PaymentRequestListResponse(
        payment_requests=[_to_out(r) for r in requests]
    )


@router.get(
    "/payment-requests/{request_id}",
    response_model=PaymentRequestOut,
)
async def get_payment_request(
    request_id: UUID, session: Session = Depends(get_db_session)
) -> PaymentRequestOut:
    req = payment_request_repo.get(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="PaymentRequest not found")
    return _to_out(req)


# --- PSBT export -----------------------------------------------------------


@router.get("/payment-requests/{request_id}/psbt")
async def get_payment_psbt(
    request_id: UUID,
    request: Request,
    session: Session = Depends(get_db_session),
):  # type: ignore[no-untyped-def]
    """Return the PSBT.

    Default Accept (`application/json`) yields `{"psbt_base64": "..."}`.
    Pass `Accept: application/octet-stream` for the binary PSBT bytes
    suitable for `<input type=file>` style download to a hardware
    signer's SD-card path.
    """
    req = payment_request_repo.get(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="PaymentRequest not found")
    if req.psbt_base64 is None:
        raise HTTPException(
            status_code=409,
            detail="PaymentRequest has no PSBT (lightning or already broadcast)",
        )

    accept = (request.headers.get("accept") or "application/json").lower()
    wants_binary = "application/octet-stream" in accept

    if wants_binary:
        try:
            raw = base64.b64decode(req.psbt_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=500,
                detail="Stored PSBT is not valid base64",
            ) from exc
        return Response(
            content=raw,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{request_id}.psbt"',
            },
        )

    return JSONResponse(
        content={
            "psbt_base64": req.psbt_base64,
            "filename": f"{request_id}.psbt",
        }
    )


# --- still stubbed for M6.2..M6.4 ------------------------------------------


@router.get("/payment-requests/{request_id}/psbt.qr", status_code=501)
async def get_payment_psbt_qr(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.2",
        route="GET /api/v1/banking/payment-requests/{id}/psbt.qr",
    )


@router.post("/payment-requests/{request_id}/submit-signed", status_code=501)
async def submit_signed_payment(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.2",
        route="POST /api/v1/banking/payment-requests/{id}/submit-signed",
    )


@router.post("/payment-requests/{request_id}/broadcast", status_code=501)
async def broadcast_payment(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.2",
        route="POST /api/v1/banking/payment-requests/{id}/broadcast",
    )


@router.post("/payment-requests/{request_id}/cancel", status_code=501)
async def cancel_payment_request(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.5",
        route="POST /api/v1/banking/payment-requests/{id}/cancel",
    )


@router.post("/fee-estimate", status_code=501)
async def fee_estimate() -> JSONResponse:
    return not_implemented_response(
        milestone="M6.2", route="POST /api/v1/banking/fee-estimate"
    )


# --- Incoming invoices (M6.4) ----------------------------------------------


@router.get("/invoices", status_code=501)
async def list_invoices(
    holding_id: UUID | None = None, status: str | None = None
) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.4", route="GET /api/v1/banking/invoices"
    )


@router.post("/invoices", status_code=501)
async def create_invoice() -> JSONResponse:
    return not_implemented_response(
        milestone="M6.4", route="POST /api/v1/banking/invoices"
    )


@router.get("/invoices/{invoice_id}", status_code=501)
async def get_invoice(invoice_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.4", route="GET /api/v1/banking/invoices/{id}"
    )


@router.get("/invoices/{invoice_id}/qr", status_code=501)
async def get_invoice_qr(invoice_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.4", route="GET /api/v1/banking/invoices/{id}/qr"
    )


@router.post("/invoices/{invoice_id}/cancel", status_code=501)
async def cancel_invoice(invoice_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.4", route="POST /api/v1/banking/invoices/{id}/cancel"
    )
