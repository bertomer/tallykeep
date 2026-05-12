"""auth_layer_paired_device

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-05-11 00:00:00.000000

Onboarding + Daily Unlock + Home iteration — auth layer:
- Add paired_device table for device credential registry.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paired_device",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("credential_hash", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paired_device")),
    )
    op.create_index(
        op.f("ix_paired_device_revoked_at"),
        "paired_device",
        ["revoked_at"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_paired_device_revoked_at"), table_name="paired_device")
    op.drop_table("paired_device")
