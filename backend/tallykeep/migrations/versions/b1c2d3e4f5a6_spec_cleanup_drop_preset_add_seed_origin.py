"""spec_cleanup_drop_preset_add_seed_origin

Revision ID: b1c2d3e4f5a6
Revises: 3c4d5e6f7a8b
Create Date: 2026-05-10 00:00:00.000000

spec-cleanup-backend-deltas iteration:
- Drop user_profile.preset (ProfilePreset concept removed; flags use DEFAULT_FLAG_VALUES fallback)
- Purse seed_origin is stored in subtype_data JSONB — no column change needed
- SweepPolicy.is_dry_run already exists (added in 8f2a1c3d4e5b); no action required
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "3c4d5e6f7a8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("user_profile", "preset")


def downgrade() -> None:
    op.add_column(
        "user_profile",
        sa.Column(
            "preset",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'intermediate'"),
        ),
    )
    # Remove the server_default after backfill to match the original schema.
    op.alter_column("user_profile", "preset", server_default=None)
