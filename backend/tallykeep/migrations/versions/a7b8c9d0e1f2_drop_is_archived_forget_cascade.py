"""Drop is_archived from holding; update indexes; SET NULL on linked_counterparty FK.

Revision ID: a7b8c9d0e1f2
Revises: e5f6a7b8c9d0
Create Date: 2026-05-20

Per ADR-0017 (Forget is hard delete; archive mechanism retires):
- Drop holding.is_archived column (no data migration; dev DB reset accompanies this).
- Drop the two partial indexes that filtered on is_archived = FALSE; recreate as
  plain indexes (ix_holding_holding_type, ix_holding_purpose).
- Change custodial_ledger_entry.linked_counterparty_holding_id FK from
  ON DELETE RESTRICT to ON DELETE SET NULL so that forgetting a non-Account
  Holding automatically NULLs the back-pointer on any custodial_ledger_entry
  row that referenced it.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop partial indexes (filter on is_archived = FALSE).
    op.drop_index("ix_holding_holding_type_active", table_name="holding")
    op.drop_index("ix_holding_purpose_active", table_name="holding")

    # 2. Drop is_archived column.
    op.drop_column("holding", "is_archived")

    # 3. Recreate plain indexes (no WHERE clause).
    op.create_index("ix_holding_holding_type", "holding", ["holding_type"])
    op.create_index("ix_holding_purpose", "holding", ["purpose"])

    # 4. Drop the RESTRICT FK on linked_counterparty_holding_id and recreate
    #    with ON DELETE SET NULL.
    op.drop_constraint(
        "fk_custodial_ledger_entry_counterparty",
        "custodial_ledger_entry",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_custodial_ledger_entry_counterparty",
        "custodial_ledger_entry",
        "holding",
        ["linked_counterparty_holding_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # 4. Restore RESTRICT FK.
    op.drop_constraint(
        "fk_custodial_ledger_entry_counterparty",
        "custodial_ledger_entry",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_custodial_ledger_entry_counterparty",
        "custodial_ledger_entry",
        "holding",
        ["linked_counterparty_holding_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 3. Drop plain indexes.
    op.drop_index("ix_holding_holding_type", table_name="holding")
    op.drop_index("ix_holding_purpose", table_name="holding")

    # 2. Re-add is_archived column (default FALSE for all existing rows).
    op.add_column(
        "holding",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    # 1. Recreate partial indexes.
    op.create_index(
        "ix_holding_holding_type_active",
        "holding",
        ["holding_type"],
        postgresql_where=sa.text("is_archived = FALSE"),
    )
    op.create_index(
        "ix_holding_purpose_active",
        "holding",
        ["purpose"],
        postgresql_where=sa.text("is_archived = FALSE"),
    )
