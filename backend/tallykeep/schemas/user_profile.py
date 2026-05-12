"""Pydantic schemas for the /api/v1/profile and /api/v1/feature-flags endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    base_currency: str
    locale: str
    principles_acknowledged_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_flags: dict[str, bool] | None = None
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    locale: str | None = Field(default=None, min_length=2, max_length=10)
    principles_acknowledged: bool | None = None


class FeatureFlagsResponse(BaseModel):
    """Resolved-flag map: every known flag with its effective value."""

    flags: dict[str, bool]
