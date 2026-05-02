"""User profile endpoints (spec module 04 / 09).

GET  /api/v1/profile  → singleton UserProfile
PATCH /api/v1/profile → partial update
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.repositories import user_profile as profile_repo
from tallykeep.schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdate,
)


router = APIRouter(tags=["profile"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    session: Session = Depends(get_db_session),
) -> UserProfileResponse:
    profile = profile_repo.get_or_create(session)
    return UserProfileResponse.model_validate(profile)


@router.patch("/profile", response_model=UserProfileResponse)
async def patch_profile(
    body: UserProfileUpdate,
    session: Session = Depends(get_db_session),
) -> UserProfileResponse:
    if (
        body.preset is None
        and body.feature_flags is None
        and body.base_currency is None
        and body.locale is None
    ):
        raise HTTPException(status_code=422, detail="empty update")

    try:
        profile = profile_repo.update(
            session,
            preset=body.preset,
            feature_flags=body.feature_flags,
            base_currency=body.base_currency,
            locale=body.locale,
        )
    except ValueError as exc:  # domain invariant violation
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UserProfileResponse.model_validate(profile)
