"""UserProfile domain type (spec module 02 / 09).

Singleton per installation. Feature flags are resolved from user_profile.feature_flags
(explicit overrides) falling back to DEFAULT_FLAG_VALUES. There is no preset concept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

# Spec module 03: the singleton row's id is fixed.
USER_PROFILE_SINGLETON_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class UserProfile:
    id: UUID
    feature_flags: dict[str, bool] = field(default_factory=dict)  # overrides only
    base_currency: str = "EUR"
    locale: str = "en"
    principles_acknowledged_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.id != USER_PROFILE_SINGLETON_ID:
            raise ValueError(
                f"UserProfile id must equal the singleton id "
                f"{USER_PROFILE_SINGLETON_ID}"
            )
        if len(self.base_currency) != 3:
            raise ValueError("UserProfile.base_currency must be a 3-letter code")
