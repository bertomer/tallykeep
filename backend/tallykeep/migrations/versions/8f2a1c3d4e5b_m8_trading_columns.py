"""m8_trading_columns

Revision ID: 8f2a1c3d4e5b
Revises: 452e0572a690
Create Date: 2026-05-05 00:00:00.000000

Adds columns required for the M8 Trading layer:
  - custodial_provider.whitelist_verified — tracks whether the withdrawal
    address was confirmed via the provider's API at registration time.
  - sweep_policy.is_dry_run — when true, the SweepEngine evaluates and
    persists sweep_execution rows but does not dispatch withdrawal requests.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "8f2a1c3d4e5b"
down_revision: str | None = "452e0572a690"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "custodial_provider",
        sa.Column(
            "whitelist_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "sweep_policy",
        sa.Column(
            "is_dry_run",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )


def downgrade() -> None:
    op.drop_column("sweep_policy", "is_dry_run")
    op.drop_column("custodial_provider", "whitelist_verified")
