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


# --- M6.2: submit-signed + broadcast + fee-estimate ------------------------


class SubmitSignedRequest(BaseModel):
    psbt_base64: str | None = None
    signed_transaction_hex: str | None = None


class FeeEstimateRequest(BaseModel):
    target_blocks: int | None = None
    strategy: str | None = None  # economy | normal | priority


@router.post(
    "/payment-requests/{request_id}/submit-signed",
    response_model=PaymentRequestOut,
)
async def submit_signed_payment(
    request_id: UUID,
    body: SubmitSignedRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> PaymentRequestOut:
    """Accept a signed PSBT or a finalized tx hex.

    The PaymentRequest must be in AWAITING_SIGNATURE. On success, status
    flips to AWAITING_BROADCAST and `signed_transaction_hex` is stored.
    """
    if body.psbt_base64 is None and body.signed_transaction_hex is None:
        raise HTTPException(
            status_code=400,
            detail="Provide psbt_base64 or signed_transaction_hex",
        )
    try:
        updated = banking_service.submit_signed_payment_request(
            session,
            request_id=request_id,
            psbt_base64=body.psbt_base64,
            signed_transaction_hex=body.signed_transaction_hex,
        )
    except banking_service.PaymentRequestNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except banking_service.WrongStatusForOperation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except banking_service.PsbtMismatch as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except banking_service.SignedTransactionInvalid as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except banking_service.BankingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()

    bus = get_event_bus(request)
    if bus is not None:
        bus.publish(
            "banking.payment_request.signed",
            {"id": str(request_id)},
        )
    return _to_out(updated)


@router.post(
    "/payment-requests/{request_id}/broadcast",
    response_model=PaymentRequestOut,
)
async def broadcast_payment(
    request_id: UUID,
    request: Request,
    session: Session = Depends(get_db_session),
    node: NodeAdapter = Depends(get_node_adapter),
) -> PaymentRequestOut:
    """Submit the signed transaction to bitcoind.

    Records a `broadcast_attempt` (status=submitted) BEFORE the RPC call
    so the audit trail captures the attempt even if bitcoind crashes
    mid-RPC.
    """
    try:
        updated = banking_service.broadcast_payment_request(
            session, request_id=request_id, node=node
        )
    except banking_service.PaymentRequestNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except banking_service.WrongStatusForOperation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except banking_service.BroadcastRejected as exc:
        # Persist the rejected attempt before bubbling up.
        session.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except banking_service.BankingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    session.commit()

    bus = get_event_bus(request)
    if bus is not None:
        bus.publish(
            "banking.payment_request.broadcast",
            {
                "id": str(request_id),
                "txid": updated.broadcast_txid,
            },
        )
    return _to_out(updated)


@router.post("/fee-estimate")
async def fee_estimate(
    body: FeeEstimateRequest,
    node: NodeAdapter = Depends(get_node_adapter),
):  # type: ignore[no-untyped-def]
    """Return the current sat/vB rate for one of the named tiers.

    Pass `strategy` (`economy` | `normal` | `priority`) for the named
    tiers, or `target_blocks` for a custom horizon. Returns
    `{"sat_per_vbyte": float, "target_blocks": int}` plus a flag
    indicating whether bitcoind's estimator returned a real value or we
    fell back to the static default.
    """
    target_map = {"economy": 24, "normal": 6, "priority": 2}
    if body.target_blocks is not None:
        target = body.target_blocks
    elif body.strategy in target_map:
        target = target_map[body.strategy]
    else:
        target = 6
    from tallykeep.adapters.node_adapter import NodeError

    fallback = 10.0
    try:
        result = node.estimate_smart_fee(target)
    except NodeError:
        return {
            "sat_per_vbyte": fallback,
            "target_blocks": target,
            "is_fallback": True,
        }
    feerate = result.get("feerate")
    if feerate is None or float(feerate) <= 0:
        return {
            "sat_per_vbyte": fallback,
            "target_blocks": target,
            "is_fallback": True,
        }
    return {
        "sat_per_vbyte": float(feerate) * 100_000,
        "target_blocks": target,
        "is_fallback": False,
    }


# --- still stubbed for M6.4 / M6.5 -----------------------------------------


@router.get("/payment-requests/{request_id}/psbt.qr", status_code=501)
async def get_payment_psbt_qr(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="v1.1",
        route="GET /api/v1/banking/payment-requests/{id}/psbt.qr",
    )


@router.post("/payment-requests/{request_id}/cancel", status_code=501)
async def cancel_payment_request(request_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M6.5",
        route="POST /api/v1/banking/payment-requests/{id}/cancel",
    )


# --- Incoming invoices (M6.4) ----------------------------------------------


class InvoiceCreate(BaseModel):
    holding_id: UUID
    amount_sats: int | None = None
    description: str | None = None


class InvoiceOut(BaseModel):
    id: UUID
    holding_id: UUID
    invoice_type: str
    status: str
    amount_sats: int | None
    description: str | None
    receiving_address: str | None
    bip21_uri: str | None
    resulting_ledger_entry_id: UUID | None


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceOut]


def _invoice_to_out(inv) -> InvoiceOut:  # type: ignore[no-untyped-def]
    return InvoiceOut(
        id=inv.id,
        holding_id=inv.holding_id,
        invoice_type=inv.invoice_type.value,
        status=inv.status.value,
        amount_sats=inv.amount_sats,
        description=inv.description,
        receiving_address=inv.receiving_address,
        bip21_uri=inv.bip21_uri,
        resulting_ledger_entry_id=inv.resulting_ledger_entry_id,
    )


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    request: Request,
    session: Session = Depends(get_db_session),
) -> InvoiceOut:
    try:
        invoice = banking_service.create_invoice(
            session,
            holding_id=body.holding_id,
            amount_sats=body.amount_sats,
            description=body.description,
        )
    except banking_service.HoldingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except banking_service.HoldingCannotReceive as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except banking_service.NoUnusedAddress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except banking_service.InvoiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()

    bus = get_event_bus(request)
    if bus is not None:
        bus.publish(
            "banking.invoice.created",
            {"id": str(invoice.id), "holding_id": str(invoice.holding_id)},
        )
    return _invoice_to_out(invoice)


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    holding_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> InvoiceListResponse:
    from tallykeep.domain.enums import InvoiceStatus
    from tallykeep.repositories import invoice as invoice_repo

    try:
        status_enum = InvoiceStatus(status) if status else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    invoices = invoice_repo.list_filtered(
        session,
        holding_id=holding_id,
        status=status_enum,
        limit=limit,
        offset=offset,
    )
    return InvoiceListResponse(
        invoices=[_invoice_to_out(i) for i in invoices]
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: UUID, session: Session = Depends(get_db_session)
) -> InvoiceOut:
    from tallykeep.repositories import invoice as invoice_repo

    invoice = invoice_repo.get(session, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_to_out(invoice)


@router.get("/invoices/{invoice_id}/qr")
async def get_invoice_qr(
    invoice_id: UUID, session: Session = Depends(get_db_session)
):  # type: ignore[no-untyped-def]
    """Render the BIP21 URI as a 400×400 PNG QR code."""
    import io

    import qrcode

    from tallykeep.repositories import invoice as invoice_repo

    invoice = invoice_repo.get(session, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.bip21_uri is None:
        raise HTTPException(
            status_code=409,
            detail="Invoice has no BIP21 URI to encode",
        )

    img = qrcode.make(invoice.bip21_uri, box_size=10, border=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{invoice_id}.png"',
        },
    )


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceOut)
async def cancel_invoice(
    invoice_id: UUID, session: Session = Depends(get_db_session)
) -> InvoiceOut:
    from tallykeep.repositories import invoice as invoice_repo

    try:
        cancelled = invoice_repo.cancel(session, invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if cancelled is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    session.commit()
    return _invoice_to_out(cancelled)
