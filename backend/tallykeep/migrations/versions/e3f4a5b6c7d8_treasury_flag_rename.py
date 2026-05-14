"""Rename trading.* feature-flag keys to treasury.* in user_profile.feature_flags.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-14

Idempotent: if a treasury.* key already exists for a given suffix it takes
precedence and the trading.* key is removed. Re-running is safe.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None

_SUFFIXES = [
    "enabled",
    "sweep_policy.enabled",
    "sweep_confirmation.required",
    "bidirectional_sweeps.shown",
]


def upgrade() -> None:
    conn = op.get_bind()
    for suffix in _SUFFIXES:
        old_key = f"trading.{suffix}"
        new_key = f"treasury.{suffix}"
        # For each row: if old_key exists and new_key does not, rename it.
        # If new_key already exists, just delete old_key.
        conn.execute(
            text(
                """
                UPDATE user_profile
                SET feature_flags =
                    CASE
                        WHEN (feature_flags ? :new_key)
                            THEN (feature_flags - :old_key)
                        ELSE (feature_flags - :old_key) || jsonb_build_object(:new_key, feature_flags -> :old_key)
                    END
                WHERE feature_flags ? :old_key
                """
            ),
            {"old_key": old_key, "new_key": new_key},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for suffix in _SUFFIXES:
        old_key = f"trading.{suffix}"
        new_key = f"treasury.{suffix}"
        conn.execute(
            text(
                """
                UPDATE user_profile
                SET feature_flags =
                    CASE
                        WHEN (feature_flags ? :old_key)
                            THEN (feature_flags - :new_key)
                        ELSE (feature_flags - :new_key) || jsonb_build_object(:old_key, feature_flags -> :new_key)
                    END
                WHERE feature_flags ? :new_key
                """
            ),
            {"old_key": old_key, "new_key": new_key},
        )
