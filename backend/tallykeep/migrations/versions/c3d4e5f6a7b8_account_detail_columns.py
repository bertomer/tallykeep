"""Account detail page — new custodial_provider columns.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-17

Adds:
  - custodial_provider.polling_interval_seconds: per-provider polling cadence (seconds).
    Default 600 (10 min); user-adjustable from {60, 300, 600, 1800, 3600}.
  - custodial_provider.observation_key_last_four: last 4 chars of the read-only API key,
    stored at creation time for display in the Settings tab without exposing the full key.
  - custodial_provider.non_btc_balances: JSONB map {ticker: amount_str} of non-BTC asset
    balances fetched from the provider, updated each poll cycle.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custodial_provider",
        sa.Column(
            "polling_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("600"),
        ),
    )
    op.add_column(
        "custodial_provider",
        sa.Column(
            "observation_key_last_four",
            sa.String(4),
            nullable=True,
        ),
    )
    op.add_column(
        "custodial_provider",
        sa.Column(
            "non_btc_balances",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("custodial_provider", "non_btc_balances")
    op.drop_column("custodial_provider", "observation_key_last_four")
    op.drop_column("custodial_provider", "polling_interval_seconds")
