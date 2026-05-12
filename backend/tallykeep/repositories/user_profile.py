"""user_profile repository — singleton row management."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from tallykeep.domain.user_profile import USER_PROFILE_SINGLETON_ID, UserProfile
from tallykeep.models import UserProfileRow


def _row_to_domain(row: UserProfileRow) -> UserProfile:
    return UserProfile(
        id=row.id,
        feature_flags=dict(row.feature_flags or {}),
        base_currency=row.base_currency,
        locale=row.locale,
        principles_acknowledged_at=row.principles_acknowledged_at,
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
    feature_flags: dict[str, bool] | None = None,
    base_currency: str | None = None,
    locale: str | None = None,
    principles_acknowledged: bool | None = None,
) -> UserProfile:
    """Apply a partial update to the singleton."""
    row = session.get(UserProfileRow, USER_PROFILE_SINGLETON_ID)
    if row is None:
        get_or_create(session)
        row = session.get(UserProfileRow, USER_PROFILE_SINGLETON_ID)
        assert row is not None  # noqa: S101 — internal invariant after get_or_create

    if feature_flags is not None:
        row.feature_flags = dict(feature_flags)
    if base_currency is not None:
        row.base_currency = base_currency
    if locale is not None:
        row.locale = locale
    if principles_acknowledged is True and row.principles_acknowledged_at is None:
        row.principles_acknowledged_at = datetime.now(UTC)

    row.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return _row_to_domain(row)


def replace_feature_flags(
    session: Session, flags: dict[str, bool]
) -> UserProfile:
    return update(session, feature_flags=flags)


__all__ = [
    "get_or_create",
    "update",
    "replace_feature_flags",
]
