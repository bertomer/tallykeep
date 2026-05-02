"""Custodial provider endpoints — spec module 04. Stubs land in M8."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["custodial-providers"])


@router.get("/custodial-providers/supported", status_code=501)
async def supported_providers() -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/custodial-providers/supported"
    )


@router.get("/custodial-providers/{provider_id}", status_code=501)
async def get_provider(provider_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/custodial-providers/{id}"
    )


@router.patch("/custodial-providers/{provider_id}", status_code=501)
async def patch_provider(provider_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="PATCH /api/v1/custodial-providers/{id}"
    )


@router.post("/custodial-providers/{provider_id}/refresh", status_code=501)
async def refresh_provider(provider_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/custodial-providers/{id}/refresh"
    )


@router.get("/custodial-providers/{provider_id}/balance", status_code=501)
async def provider_balance(provider_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/custodial-providers/{id}/balance"
    )


@router.get(
    "/custodial-providers/{provider_id}/verify-whitelist", status_code=501
)
async def verify_whitelist(provider_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8",
        route="GET /api/v1/custodial-providers/{id}/verify-whitelist",
    )
