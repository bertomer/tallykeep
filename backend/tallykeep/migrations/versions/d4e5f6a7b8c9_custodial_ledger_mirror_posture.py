"""Custodial ledger mirror posture — ADR-0013 schema additions.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-18

Adds to custodial_ledger_entry (provider_entry_id column is unchanged):
  - holding_id: direct FK to holding for efficient per-account queries.
  - fee_sats: fee amount when the provider reports it separately.
  - linked_sweep_execution_id: reconciler linkage (nullable).
  - linked_counterparty_holding_id: the TK Holding on the other side (nullable).
  - linked_chain_ledger_entry_id: on-chain confirmation linkage (nullable).
  - reconciled_at: null = reconciler has not yet attempted matching.
  - updated_at: tracks in-place updates (status transitions etc.).
  - kind CHECK constraint: narrows to TK enum values; existing non-enum rows
    normalised to 'other' before the constraint is applied.
  - Three supporting indexes (holding+time, unreconciled, sweep-link).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

_VALID_KINDS = ("trade", "deposit", "withdrawal", "transfer", "fee", "other")


def upgrade() -> None:
    # 1. Add holding_id (nullable; backfilled below; then set NOT NULL).
    op.add_column(
        "custodial_ledger_entry",
        sa.Column("holding_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE custodial_ledger_entry cle "
        "SET holding_id = cp.holding_id "
        "FROM custodial_provider cp "
        "WHERE cle.custodial_provider_id = cp.id"
    )
    op.alter_column("custodial_ledger_entry", "holding_id", nullable=False)
    op.create_foreign_key(
        "fk_custodial_ledger_entry_holding",
        "custodial_ledger_entry",
        "holding",
        ["holding_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 2. fee_sats — nullable, provider may not report it.
    op.add_column(
        "custodial_ledger_entry",
        sa.Column("fee_sats", sa.BigInteger(), nullable=True),
    )

    # 3. TK-initiated linkage FKs (all nullable — pure-observation entries leave them null).
    op.add_column(
        "custodial_ledger_entry",
        sa.Column("linked_sweep_execution_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_custodial_ledger_entry_sweep_execution",
        "custodial_ledger_entry",
        "sweep_execution",
        ["linked_sweep_execution_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "custodial_ledger_entry",
        sa.Column("linked_counterparty_holding_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_custodial_ledger_entry_counterparty",
        "custodial_ledger_entry",
        "holding",
        ["linked_counterparty_holding_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "custodial_ledger_entry",
        sa.Column("linked_chain_ledger_entry_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_custodial_ledger_entry_chain_ledger",
        "custodial_ledger_entry",
        "ledger_entry",
        ["linked_chain_ledger_entry_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 4. reconciled_at — null means the reconciler has not yet attempted matching.
    op.add_column(
        "custodial_ledger_entry",
        sa.Column("reconciled_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # 5. updated_at — tracks in-place status transitions from the provider.
    op.add_column(
        "custodial_ledger_entry",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 6. Normalise existing kind values to the TK enum before adding the constraint.
    #    Values like 'staking', 'earn', and any other non-enum strings → 'other'.
    valid_kinds_sql = ", ".join(f"'{k}'" for k in _VALID_KINDS)
    op.execute(
        f"UPDATE custodial_ledger_entry "
        f"SET kind = 'other' "
        f"WHERE kind NOT IN ({valid_kinds_sql})"
    )
    op.create_check_constraint(
        "ck_custodial_ledger_entry_kind",
        "custodial_ledger_entry",
        f"kind IN ({valid_kinds_sql})",
    )

    # 7. Three supporting indexes.
    op.create_index(
        "idx_custodial_ledger_entry_holding_time",
        "custodial_ledger_entry",
        ["holding_id", sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_custodial_ledger_entry_unreconciled",
        "custodial_ledger_entry",
        ["holding_id", "timestamp"],
        postgresql_where=sa.text(
            "reconciled_at IS NULL AND kind IN ('deposit', 'withdrawal')"
        ),
    )
    op.create_index(
        "idx_custodial_ledger_entry_sweep_link",
        "custodial_ledger_entry",
        ["linked_sweep_execution_id"],
        postgresql_where=sa.text("linked_sweep_execution_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_custodial_ledger_entry_sweep_link",
        table_name="custodial_ledger_entry",
    )
    op.drop_index(
        "idx_custodial_ledger_entry_unreconciled",
        table_name="custodial_ledger_entry",
    )
    op.drop_index(
        "idx_custodial_ledger_entry_holding_time",
        table_name="custodial_ledger_entry",
    )

    op.drop_constraint(
        "ck_custodial_ledger_entry_kind",
        "custodial_ledger_entry",
        type_="check",
    )
    op.drop_column("custodial_ledger_entry", "updated_at")
    op.drop_column("custodial_ledger_entry", "reconciled_at")

    op.drop_constraint(
        "fk_custodial_ledger_entry_chain_ledger",
        "custodial_ledger_entry",
        type_="foreignkey",
    )
    op.drop_column("custodial_ledger_entry", "linked_chain_ledger_entry_id")

    op.drop_constraint(
        "fk_custodial_ledger_entry_counterparty",
        "custodial_ledger_entry",
        type_="foreignkey",
    )
    op.drop_column("custodial_ledger_entry", "linked_counterparty_holding_id")

    op.drop_constraint(
        "fk_custodial_ledger_entry_sweep_execution",
        "custodial_ledger_entry",
        type_="foreignkey",
    )
    op.drop_column("custodial_ledger_entry", "linked_sweep_execution_id")

    op.drop_column("custodial_ledger_entry", "fee_sats")

    op.drop_constraint(
        "fk_custodial_ledger_entry_holding",
        "custodial_ledger_entry",
        type_="foreignkey",
    )
    op.drop_column("custodial_ledger_entry", "holding_id")
