"""Address endpoints — spec module 04. Stubs land in M4 / M5."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["addresses"])


@router.patch("/addresses/{address_id}", status_code=501)
async def patch_address(address_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="PATCH /api/v1/addresses/{id}"
    )
