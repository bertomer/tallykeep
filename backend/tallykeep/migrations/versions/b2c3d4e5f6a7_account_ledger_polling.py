"""Account observation scope amendment — ledger polling infrastructure (iteration A).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17

Adds:
  - custodial_ledger_entry table: persists provider ledger entries per observation cycle.
  - custodial_provider.connection_status: 'healthy' | 'degraded' | 'unreachable' | 'auth_failed'
  - custodial_provider.consecutive_error_count: tracks consecutive poll failures.
  - custodial_provider.ledger_cursor_at: timestamp of the newest ledger entry fetched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- New columns on custodial_provider -----------------------------------
    op.add_column(
        "custodial_provider",
        sa.Column(
            "connection_status",
            sa.String(20),
            nullable=False,
            server_default="healthy",
        ),
    )
    op.add_column(
        "custodial_provider",
        sa.Column(
            "consecutive_error_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "custodial_provider",
        sa.Column(
            "ledger_cursor_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # --- New table: custodial_ledger_entry -----------------------------------
    op.create_table(
        "custodial_ledger_entry",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "custodial_provider_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("custodial_provider.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_entry_id", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("amount_sats", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_constraint(
        "uq_custodial_ledger_entry_provider_entry",
        "custodial_ledger_entry",
        ["custodial_provider_id", "provider_entry_id"],
    )
    op.create_index(
        "idx_custodial_ledger_entry_provider_timestamp",
        "custodial_ledger_entry",
        ["custodial_provider_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_custodial_ledger_entry_provider_timestamp",
        table_name="custodial_ledger_entry",
    )
    op.drop_constraint(
        "uq_custodial_ledger_entry_provider_entry",
        "custodial_ledger_entry",
        type_="unique",
    )
    op.drop_table("custodial_ledger_entry")

    op.drop_column("custodial_provider", "ledger_cursor_at")
    op.drop_column("custodial_provider", "consecutive_error_count")
    op.drop_column("custodial_provider", "connection_status")
