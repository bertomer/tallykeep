"""Custodial provider endpoints — spec module 07 / M8."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tallykeep.adapters.adapter_registry import SUPPORTED_ADAPTER_IDS
from tallykeep.api.dependencies import get_db_session, get_secret_store
from tallykeep.infrastructure.secrets import SecretStore
from tallykeep.schemas.treasury import (
    BalanceOut,
    CustodialProviderOut,
    PatchCustodialProviderRequest,
    WhitelistVerificationOut,
)
from tallykeep.services import treasury_service
from tallykeep.services.treasury_service import (
    ProviderConnectionError,
    ProviderNotFound,
    TreasuryServiceError,
)


router = APIRouter(tags=["custodial-providers"])


def _provider_to_out(p) -> CustodialProviderOut:  # type: ignore[no-untyped-def]
    return CustodialProviderOut(
        id=p.id,
        holding_id=p.holding_id,
        provider_kind=p.provider_kind,
        display_name=p.display_name,
        adapter_id=p.adapter_id,
        can_read=p.permissions.can_read,
        can_withdraw=p.permissions.can_withdraw,
        whitelist_address=p.whitelist_address,
        whitelist_address_descriptor_id=p.whitelist_address_descriptor_id,
        whitelist_verified=p.whitelist_verified,
        is_active=p.is_active,
        last_polled_at=p.last_polled_at,
        last_error=p.last_error,
        last_known_balance_sats=p.last_known_balance_sats,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/custodial-providers/supported")
async def supported_providers() -> dict:  # type: ignore[type-arg]
    return {"supported": SUPPORTED_ADAPTER_IDS}


@router.get("/custodial-providers/{provider_id}", response_model=CustodialProviderOut)
async def get_provider(
    provider_id: UUID, session: Session = Depends(get_db_session)
) -> CustodialProviderOut:
    try:
        provider = treasury_service.get_provider(session, provider_id)
    except ProviderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _provider_to_out(provider)


@router.patch("/custodial-providers/{provider_id}", response_model=CustodialProviderOut)
async def patch_provider(
    provider_id: UUID,
    body: PatchCustodialProviderRequest,
    session: Session = Depends(get_db_session),
    secret_store: SecretStore = Depends(get_secret_store),
) -> CustodialProviderOut:
    try:
        provider = treasury_service.patch_provider(
            session,
            provider_id,
            display_name=body.display_name,
            api_key=body.api_key,
            api_secret=body.api_secret,
            api_passphrase=body.api_passphrase,
            secret_store=secret_store if (body.api_key or body.api_secret) else None,
        )
        session.commit()
    except ProviderNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderConnectionError as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TreasuryServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _provider_to_out(provider)


@router.post("/custodial-providers/{provider_id}/refresh", response_model=CustodialProviderOut)
async def refresh_provider(
    provider_id: UUID,
    session: Session = Depends(get_db_session),
    secret_store: SecretStore = Depends(get_secret_store),
) -> CustodialProviderOut:
    try:
        provider = treasury_service.refresh_provider_balance(
            session, provider_id, secret_store=secret_store
        )
        session.commit()
    except ProviderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TreasuryServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _provider_to_out(provider)


@router.get("/custodial-providers/{provider_id}/balance", response_model=BalanceOut)
async def provider_balance(
    provider_id: UUID, session: Session = Depends(get_db_session)
) -> BalanceOut:
    try:
        provider = treasury_service.get_provider(session, provider_id)
    except ProviderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BalanceOut(
        provider_id=provider.id,
        balance_sats=provider.last_known_balance_sats or 0,
        last_polled_at=provider.last_polled_at,
    )


@router.get(
    "/custodial-providers/{provider_id}/verify-whitelist",
    response_model=WhitelistVerificationOut,
)
async def verify_whitelist(
    provider_id: UUID,
    session: Session = Depends(get_db_session),
    secret_store: SecretStore = Depends(get_secret_store),
) -> WhitelistVerificationOut:
    try:
        provider, is_whitelisted, error = treasury_service.verify_whitelist(
            session, provider_id, secret_store=secret_store
        )
        session.commit()
    except ProviderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TreasuryServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WhitelistVerificationOut(
        provider_id=provider.id,
        address=provider.whitelist_address,
        is_whitelisted=is_whitelisted,
        provider_label=provider.display_name,
        error=error,
    )
