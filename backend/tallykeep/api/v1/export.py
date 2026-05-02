"""Export endpoint — spec module 04. Stubs land in M14 (v1 polish)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["export"])


@router.get("/export/configuration", status_code=501)
async def export_configuration() -> JSONResponse:
    return not_implemented_response(
        milestone="M14", route="GET /api/v1/export/configuration"
    )
