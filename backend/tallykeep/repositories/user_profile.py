"""user_profile repository — singleton row management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from tallykeep.domain.enums import ProfilePreset
from tallykeep.domain.user_profile import USER_PROFILE_SINGLETON_ID, UserProfile
from tallykeep.models import UserProfileRow


_DEFAULT_PRESET = ProfilePreset.INTERMEDIATE  # spec module 11 onboarding default


def _row_to_domain(row: UserProfileRow) -> UserProfile:
    return UserProfile(
        id=row.id,
        preset=ProfilePreset(row.preset),
        feature_flags=dict(row.feature_flags or {}),
        base_currency=row.base_currency,
        locale=row.locale,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get_or_create(session: Session) -> UserProfile:
    """Return the singleton UserProfile, creating it with sensible defaults if absent.

    Idempotent: repeated calls in the same process or across processes return the
    same row (CHECK constraint in the database guards the singleton id).
    """
    row = session.get(UserProfileRow, USER_PROFILE_SINGLETON_ID)
    if row is None:
        row = UserProfileRow(
            id=USER_PROFILE_SINGLETON_ID,
            preset=_DEFAULT_PRESET.value,
            feature_flags={},
            base_currency="EUR",
            locale="en",
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return _row_to_domain(row)


def update(
    session: Session,
    *,
    preset: ProfilePreset | None = None,
    feature_flags: dict[str, bool] | None = None,
    base_currency: str | None = None,
    locale: str | None = None,
) -> UserProfile:
    """Apply a partial update to the singleton."""
    row = session.get(UserProfileRow, USER_PROFILE_SINGLETON_ID)
    if row is None:
        # Auto-create on first PATCH so callers don't need a separate "create" step.
        get_or_create(session)
        row = session.get(UserProfileRow, USER_PROFILE_SINGLETON_ID)
        assert row is not None  # noqa: S101 — internal invariant after get_or_create

    if preset is not None:
        row.preset = preset.value
    if feature_flags is not None:
        # Replace the overrides map entirely. Spec module 09: switching back to a
        # named preset clears feature_flags to empty.
        row.feature_flags = dict(feature_flags)
    if base_currency is not None:
        row.base_currency = base_currency
    if locale is not None:
        row.locale = locale

    row.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return _row_to_domain(row)


def replace_feature_flags(
    session: Session, flags: dict[str, bool]
) -> UserProfile:
    """Helper for the preset-transition logic in M7.

    Currently a thin wrapper; promoted to its own function so the future
    "transition to CUSTOM and snapshot resolved flags" code lives in one place.
    """
    return update(session, feature_flags=flags)


__all__ = [
    "get_or_create",
    "update",
    "replace_feature_flags",
]
