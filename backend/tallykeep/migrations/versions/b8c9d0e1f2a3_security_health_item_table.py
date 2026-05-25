"""security_health_item_table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-25 00:00:00.000000

Creates the security_health_item table with indexes per ADR-0019.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_health_item",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_type", sa.String(60), nullable=False),
        sa.Column("holding_id", sa.UUID(), nullable=True),
        sa.Column(
            "state",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("dismissal_reason", sa.Text(), nullable=True),
        sa.Column(
            "raw_context",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint(
            "state IN ('open','resolved_by_fix','dismissed_intentional','acknowledged')",
            name="security_health_item_state_in_set",
        ),
        sa.CheckConstraint(
            "severity IN ('critical','warning','notification')",
            name="security_health_item_severity_in_set",
        ),
        sa.ForeignKeyConstraint(
            ["holding_id"],
            ["holding.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Active-tab query: open items sorted by severity desc, created_at desc.
    op.create_index(
        "ix_security_health_item_state_severity_created",
        "security_health_item",
        ["state", "severity", "created_at"],
    )
    # History-tab query.
    op.create_index(
        "ix_security_health_item_state_resolved",
        "security_health_item",
        ["state", "resolved_at"],
    )
    # Per-Holding lookups.
    op.create_index(
        "ix_security_health_item_holding_id",
        "security_health_item",
        ["holding_id"],
    )
    # Badge count: open items (filter in application layer for critical).
    op.create_index(
        "ix_security_health_item_open",
        "security_health_item",
        ["state"],
        postgresql_where=sa.text("state = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("ix_security_health_item_open", table_name="security_health_item")
    op.drop_index(
        "ix_security_health_item_holding_id", table_name="security_health_item"
    )
    op.drop_index(
        "ix_security_health_item_state_resolved", table_name="security_health_item"
    )
    op.drop_index(
        "ix_security_health_item_state_severity_created",
        table_name="security_health_item",
    )
    op.drop_table("security_health_item")
