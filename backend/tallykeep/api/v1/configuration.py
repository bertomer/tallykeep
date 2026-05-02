"""Runtime configuration endpoints (spec module 04).

GET   /api/v1/configuration → full nested configuration
PATCH /api/v1/configuration → partial update; returns the new full configuration
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.schemas.configuration import (
    ConfigurationResponse,
    ConfigurationUpdate,
)
from tallykeep.services import configuration_service


router = APIRouter(tags=["configuration"])


@router.get("/configuration", response_model=ConfigurationResponse)
async def get_configuration(
    session: Session = Depends(get_db_session),
) -> ConfigurationResponse:
    return configuration_service.get_configuration(session)


@router.patch("/configuration", response_model=ConfigurationResponse)
async def patch_configuration(
    body: ConfigurationUpdate,
    session: Session = Depends(get_db_session),
) -> ConfigurationResponse:
    return configuration_service.patch_configuration(session, body)
