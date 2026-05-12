"""GET /api/v1/server/info — public server metadata.

Exempt from auth and lock middleware (clients need this before they have a
device credential and before the store is unlocked).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from tallykeep.configuration import get_settings

router = APIRouter(tags=["server"])


class ServerInfoResponse(BaseModel):
    server_label: str


@router.get("/server/info", response_model=ServerInfoResponse)
async def get_server_info() -> ServerInfoResponse:
    settings = get_settings()
    return ServerInfoResponse(server_label=settings.server_label)
