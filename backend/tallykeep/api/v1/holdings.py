"""Holdings endpoints — spec module 04.

M4 implements:
  - per-type creation for Purse / Strongbox / Vault (Account stays a 501
    stub until M8 wires CustodialProvider)
  - cross-type list / get / patch / archive / change-type

Cross-type queries that aggregate balance, security analysis, etc. land in M5
(those still return 501 from this router).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import DescriptorAdapter
from tallykeep.api.dependencies import get_db_session
from tallykeep.api.v1._stubs import not_implemented_response
from tallykeep.domain.enums import HoldingType, Purpose
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.schemas.holding import (
    ChangeTypeRequest,
    HoldingResponse,
    HoldingUpdate,
    PurseCreate,
    SecurityClaimResponse,
    StrongboxCreate,
    VaultCreate,
)
from tallykeep.services import holding_service
from tallykeep.services.holding_service import HoldingServiceError


router = APIRouter(tags=["holdings"])


# A single shared adapter — bdkpython is stateless so this is safe.
_ADAPTER = DescriptorAdapter()


def _to_response(holding: Holding) -> HoldingResponse:
    return HoldingResponse(
        id=holding.id,
        holding_type=holding.holding_type,
        name=holding.name,
        description=holding.description,
        purpose=holding.purpose,
        declared_security=SecurityClaimResponse(
            custody_model=holding.declared_security.custody_model,
            signing_model=holding.declared_security.signing_model,
            geographic_distribution=holding.declared_security.geographic_distribution,
            inheritance_configured=holding.declared_security.inheritance_configured,
            notes=holding.declared_security.notes,
        ),
        display_color=holding.display_color,
        display_order=holding.display_order,
        is_archived=holding.is_archived,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
        descriptor_ids=list(holding.descriptor_ids),
        custodial_provider_id=holding.custodial_provider_id,
        signing_device_label=holding.signing_device_label,
        required_signers=holding.required_signers,
        total_signers=holding.total_signers,
        timelock_blocks=holding.timelock_blocks,
        recovery_setup_notes=holding.recovery_setup_notes,
    )


def _claim_from_input(claim_input) -> SecurityClaim:
    return SecurityClaim(
        custody_model=claim_input.custody_model,
        signing_model=claim_input.signing_model,
        geographic_distribution=claim_input.geographic_distribution,
        inheritance_configured=claim_input.inheritance_configured,
        notes=claim_input.notes,
    )


# --- per-type creation -------------------------------------------------------


@router.post(
    "/holdings/purse",
    response_model=HoldingResponse,
    status_code=201,
)
async def create_purse(
    body: PurseCreate, session: Session = Depends(get_db_session)
) -> HoldingResponse:
    try:
        holding = holding_service.create_purse(
            session,
            name=body.name,
            description=body.description,
            purpose=body.purpose,
            declared_security=_claim_from_input(body.declared_security),
            display_color=body.display_color,
            display_order=body.display_order,
            descriptors=body.descriptors,
            adapter=_ADAPTER,
        )
        session.commit()
    except (ValueError, HoldingServiceError) as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(holding)


@router.post(
    "/holdings/strongbox",
    response_model=HoldingResponse,
    status_code=201,
)
async def create_strongbox(
    body: StrongboxCreate, session: Session = Depends(get_db_session)
) -> HoldingResponse:
    try:
        holding = holding_service.create_strongbox(
            session,
            name=body.name,
            description=body.description,
            purpose=body.purpose,
            declared_security=_claim_from_input(body.declared_security),
            display_color=body.display_color,
            display_order=body.display_order,
            descriptors=body.descriptors,
            adapter=_ADAPTER,
            signing_device_label=body.signing_device_label,
        )
        session.commit()
    except (ValueError, HoldingServiceError) as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(holding)


@router.post(
    "/holdings/vault",
    response_model=HoldingResponse,
    status_code=201,
)
async def create_vault(
    body: VaultCreate, session: Session = Depends(get_db_session)
) -> HoldingResponse:
    try:
        holding = holding_service.create_vault(
            session,
            name=body.name,
            description=body.description,
            purpose=body.purpose,
            declared_security=_claim_from_input(body.declared_security),
            display_color=body.display_color,
            display_order=body.display_order,
            descriptors=body.descriptors,
            adapter=_ADAPTER,
            required_signers=body.required_signers,
            total_signers=body.total_signers,
            timelock_blocks=body.timelock_blocks,
            recovery_setup_notes=body.recovery_setup_notes,
        )
        session.commit()
    except (ValueError, HoldingServiceError) as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(holding)


# Account creation requires a CustodialProvider — that lands in M8.
@router.post("/holdings/account", status_code=501)
async def create_account_holding() -> JSONResponse:
    # Body schema (AccountCreate) intentionally not declared here so the stub
    # returns 501 even on empty payloads. M8 will swap in
    # `body: AccountCreate` along with the CustodialProvider integration.
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/holdings/account"
    )


# --- cross-type list / get / patch / archive / change-type -------------------


@router.get("/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    holding_type: HoldingType | None = None,
    purpose: Purpose | None = None,
    include_archived: bool = False,
    session: Session = Depends(get_db_session),
) -> list[HoldingResponse]:
    holdings = holding_service.list_holdings(
        session,
        holding_type=holding_type,
        purpose=purpose,
        include_archived=include_archived,
    )
    return [_to_response(h) for h in holdings]


@router.get("/holdings/summary/global", status_code=501)
async def global_holdings_summary() -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/holdings/summary/global"
    )


@router.get("/holdings/{holding_id}", response_model=HoldingResponse)
async def get_holding(
    holding_id: UUID, session: Session = Depends(get_db_session)
) -> HoldingResponse:
    holding = holding_service.get_holding(session, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    return _to_response(holding)


@router.patch("/holdings/{holding_id}", response_model=HoldingResponse)
async def patch_holding(
    holding_id: UUID,
    body: HoldingUpdate,
    session: Session = Depends(get_db_session),
) -> HoldingResponse:
    if body.model_dump(exclude_unset=True) == {}:
        raise HTTPException(status_code=422, detail="empty update")

    declared_security = (
        _claim_from_input(body.declared_security)
        if body.declared_security is not None
        else None
    )
    try:
        holding = holding_service.update_holding(
            session,
            holding_id,
            name=body.name,
            description=body.description,
            purpose=body.purpose,
            declared_security=declared_security,
            display_color=body.display_color,
            display_order=body.display_order,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    return _to_response(holding)


@router.post("/holdings/{holding_id}/archive", status_code=204)
async def archive_holding(
    holding_id: UUID, session: Session = Depends(get_db_session)
) -> Response:
    ok = holding_service.archive_holding(session, holding_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Holding not found")
    session.commit()
    return Response(status_code=204)


@router.post(
    "/holdings/{holding_id}/change-type",
    response_model=HoldingResponse,
)
async def change_holding_type(
    holding_id: UUID,
    body: ChangeTypeRequest,
    session: Session = Depends(get_db_session),
) -> HoldingResponse:
    try:
        holding = holding_service.change_holding_type(
            session, holding_id, body.new_type, body.reason
        )
        session.commit()
    except (ValueError, HoldingServiceError) as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    return _to_response(holding)


@router.get("/holdings/{holding_id}/summary", status_code=501)
async def holding_summary(holding_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/holdings/{id}/summary"
    )
