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
from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import DescriptorAdapter
from tallykeep.api.dependencies import get_db_session, get_secret_store
from tallykeep.domain.enums import HoldingType, Purpose
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.infrastructure.secrets import SecretStore
from tallykeep.repositories.descriptor import DescriptorAlreadyExists
from tallykeep.schemas.holding import (
    AccountCreate,
    ChangeTypeRequest,
    HoldingResponse,
    HoldingUpdate,
    PurseCreate,
    SecurityClaimResponse,
    StrongboxCreate,
    VaultCreate,
)
from tallykeep.services import holding_service, treasury_service
from tallykeep.services.holding_service import HoldingServiceError
from tallykeep.services.treasury_service import (
    ProviderConnectionError,
    TreasuryServiceError,
    TradePermissionsDetected,
)


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
        vendor=holding.vendor,
        signing_metadata_present=holding.signing_metadata_present,
        required_signers=holding.required_signers,
        total_signers=holding.total_signers,
        timelock_blocks=holding.timelock_blocks,
        recovery_setup_notes=holding.recovery_setup_notes,
        purse_mode=holding.purse_mode,
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
            purse_mode=body.purse_mode,
        )
        session.commit()
    except DescriptorAlreadyExists as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
            vendor=body.vendor,
            signing_metadata_present=body.signing_metadata_present,
        )
        session.commit()
    except DescriptorAlreadyExists as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
    except DescriptorAlreadyExists as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, HoldingServiceError) as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(holding)


@router.post("/holdings/account", response_model=HoldingResponse, status_code=201)
async def create_account_holding(
    body: AccountCreate,
    session: Session = Depends(get_db_session),
    secret_store: SecretStore = Depends(get_secret_store),
) -> HoldingResponse:
    cp = body.custodial_provider
    try:
        holding, _ = treasury_service.create_account_holding(
            session,
            name=body.name,
            description=body.description,
            purpose=body.purpose,
            declared_security=_claim_from_input(body.declared_security),
            display_color=body.display_color,
            display_order=body.display_order,
            provider_kind=cp.provider_kind,
            display_name=cp.display_name,
            adapter_id=cp.adapter_id,
            api_key=cp.api_key,
            api_secret=cp.api_secret,
            api_passphrase=cp.api_passphrase,
            whitelist_address=cp.whitelist_address,
            whitelist_address_descriptor_id=cp.whitelist_address_descriptor_id,
            secret_store=secret_store,
        )
        session.commit()
    except TradePermissionsDetected as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProviderConnectionError as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TreasuryServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(holding)


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


_CUSTODY_TIER: dict[HoldingType, int] = {
    HoldingType.ACCOUNT: 0,
    HoldingType.PURSE: 1,
    HoldingType.STRONGBOX: 2,
    HoldingType.VAULT: 3,
}


@router.get("/holdings/summary/global")
async def global_holdings_summary(
    include_archived: bool = False,
    session: Session = Depends(get_db_session),
):  # type: ignore[no-untyped-def]
    """Fortune view: per-Holding summary plus cross-Holding rollups.

    Spec module 05: "the global view always shows the per-Holding
    breakdown alongside the total. No silent consolidation." We honour
    that — the response includes the full summary list, not just the
    totals.

    Holdings are sorted by custody tier (Account → Purse → Strongbox → Vault),
    then by display_order within each tier. Each entry carries:
      - meta: type-specific label (provider name / device label / m-of-n)
      - scan_status: "n/a" | "scanning" | "scanned"
    """
    from sqlalchemy import select as _select

    from tallykeep.models.custodial_provider import CustodialProviderRow
    from tallykeep.repositories import (
        descriptor as descriptor_repo,
        utxo as utxo_repo,
    )

    holdings = holding_service.list_holdings(
        session, include_archived=include_archived
    )
    holdings.sort(
        key=lambda h: (_CUSTODY_TIER.get(h.holding_type, 99), h.display_order)
    )

    summaries: list[dict] = []
    by_type: dict[str, int] = {}
    by_purpose: dict[str, int] = {}
    total_sats = 0

    for h in holdings:
        descriptors = descriptor_repo.list_descriptors_for_holding(session, h.id)
        confirmed = 0
        utxo_count = 0
        for d in descriptors:
            confirmed += utxo_repo.descriptor_balance_sats(session, d.id)
            utxo_count += len(
                utxo_repo.list_for_descriptor(session, d.id, only_unspent=True)
            )

        # meta: type-specific human label
        if h.holding_type == HoldingType.ACCOUNT:
            provider_name: str | None = session.execute(
                _select(CustodialProviderRow.display_name).where(
                    CustodialProviderRow.holding_id == h.id
                )
            ).scalar_one_or_none()
            meta: str | None = provider_name
        elif h.holding_type == HoldingType.STRONGBOX:
            meta = h.signing_device_label
        elif h.holding_type == HoldingType.VAULT:
            if h.required_signers is not None and h.total_signers is not None:
                meta = f"{h.required_signers}-of-{h.total_signers} multisig"
            else:
                meta = None
        else:  # PURSE
            meta = None

        # scan_status
        if h.holding_type == HoldingType.ACCOUNT:
            scan_status = "n/a"
        elif not descriptors:
            scan_status = "n/a"
        elif all(d.last_scanned_height > 0 for d in descriptors):
            scan_status = "scanned"
        else:
            scan_status = "scanning"

        summaries.append(
            {
                "holding_id": str(h.id),
                "holding_type": h.holding_type.value,
                "name": h.name,
                "purpose": h.purpose.value,
                "confirmed_sats": confirmed,
                "descriptor_count": len(descriptors),
                "utxo_count": utxo_count,
                "is_archived": h.is_archived,
                "display_color": h.display_color,
                "display_order": h.display_order,
                "meta": meta,
                "scan_status": scan_status,
            }
        )
        total_sats += confirmed
        by_type[h.holding_type.value] = (
            by_type.get(h.holding_type.value, 0) + confirmed
        )
        by_purpose[h.purpose.value] = (
            by_purpose.get(h.purpose.value, 0) + confirmed
        )

    return {
        "holdings": summaries,
        "total_sats": total_sats,
        "by_type": by_type,
        "by_purpose": by_purpose,
    }


@router.get("/holdings/{holding_id}/summary")
async def holding_summary(
    holding_id: UUID, session: Session = Depends(get_db_session)
):  # type: ignore[no-untyped-def]
    """Per-Holding deep summary: balance + descriptor/UTXO counts +
    observable security analysis.

    Returns 404 when the holding doesn't exist.
    """
    from tallykeep.repositories import (
        descriptor as descriptor_repo,
        utxo as utxo_repo,
    )
    from tallykeep.services.analysis_service import analyze_holding

    holding = holding_service.get_holding(session, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")

    descriptor_ids = descriptor_repo.descriptor_ids_for_holding(session, holding_id)
    confirmed = 0
    utxo_count = 0
    for d_id in descriptor_ids:
        confirmed += utxo_repo.descriptor_balance_sats(session, d_id)
        utxo_count += len(
            utxo_repo.list_for_descriptor(session, d_id, only_unspent=True)
        )

    analysis = analyze_holding(session, holding_id)
    observable = analysis.observable if analysis is not None else None
    discrepancies = analysis.discrepancies if analysis is not None else []

    return {
        "holding": _to_response(holding).model_dump(),
        # `unconfirmed` will land alongside the mempool-watching path in
        # M5.x+; for now only confirmed balance is tracked. We surface 0
        # for unconfirmed and the same value for total so the contract
        # in spec module 04 stays the right shape.
        "total_balance_sats": confirmed,
        "confirmed_sats": confirmed,
        "unconfirmed_sats": 0,
        "descriptor_count": len(descriptor_ids),
        "utxo_count": utxo_count,
        "observable_security": (
            {
                "inferred_custody_model": observable.inferred_custody_model.value,
                "inferred_signing_model": observable.inferred_signing_model.value,
                "inferred_multisig_parameters": observable.inferred_multisig_parameters,
                "inferred_timelock_blocks": observable.inferred_timelock_blocks,
                "last_computed_at": observable.last_computed_at.isoformat(),
            }
            if observable is not None
            else None
        ),
        "discrepancies": [
            {
                "kind": d.kind.value,
                "severity": d.severity.value,
                "message": d.message,
                "first_detected_at": d.first_detected_at.isoformat(),
            }
            for d in discrepancies
        ],
    }


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
