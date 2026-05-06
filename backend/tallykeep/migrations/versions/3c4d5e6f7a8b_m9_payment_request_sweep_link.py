"""m9_payment_request_sweep_link

Revision ID: 3c4d5e6f7a8b
Revises: 8f2a1c3d4e5b
Create Date: 2026-05-06 00:00:00.000000

Adds sweep_execution_id FK on payment_request so inter-holding sweeps can
link the auto-created PaymentRequest back to the originating SweepExecution.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "3c4d5e6f7a8b"
down_revision: str | None = "8f2a1c3d4e5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_request",
        sa.Column("sweep_execution_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_request_sweep_execution",
        "payment_request",
        "sweep_execution",
        ["sweep_execution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_payment_request_sweep_execution_id",
        "payment_request",
        ["sweep_execution_id"],
        postgresql_where=sa.text("sweep_execution_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_payment_request_sweep_execution_id", table_name="payment_request")
    op.drop_constraint("fk_payment_request_sweep_execution", "payment_request", type_="foreignkey")
    op.drop_column("payment_request", "sweep_execution_id")
