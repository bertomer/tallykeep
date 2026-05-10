"""Feature-flags endpoint (spec module 04 / 09).

GET /api/v1/feature-flags → resolved flag map (preset + overrides applied).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.repositories import user_profile as profile_repo
from tallykeep.schemas.user_profile import FeatureFlagsResponse
from tallykeep.services.profile_presets import resolve_feature_flags


router = APIRouter(tags=["profile"])


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    session: Session = Depends(get_db_session),
) -> FeatureFlagsResponse:
    profile = profile_repo.get_or_create(session)
    flags = resolve_feature_flags(profile.feature_flags)
    return FeatureFlagsResponse(flags=flags)
