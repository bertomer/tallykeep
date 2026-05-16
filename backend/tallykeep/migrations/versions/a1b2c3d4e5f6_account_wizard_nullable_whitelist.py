"""Account wizard — 2-key model: make whitelist fields nullable on custodial_provider.

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-05-16

The 2-key credential model (ADR-0011) separates the read-only credential
(captured at the Add Account wizard) from the withdrawal credential (configured
later via the Account detail page). The whitelist address and its descriptor
reference belong to the withdrawal credential, so they are not present at
Account creation time and must be nullable.

Existing rows (created under the old single-credential model) retain their
whitelist values unchanged.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "a1b2c3d4e5f6"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old NOT NULL constraints on whitelist columns.
    op.alter_column(
        "custodial_provider",
        "whitelist_address",
        existing_type=sa.String(100),
        nullable=True,
    )
    op.alter_column(
        "custodial_provider",
        "whitelist_address_descriptor_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Restore NOT NULL — only safe if all rows have values; fails otherwise.
    op.alter_column(
        "custodial_provider",
        "whitelist_address",
        existing_type=sa.String(100),
        nullable=False,
    )
    op.alter_column(
        "custodial_provider",
        "whitelist_address_descriptor_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=False,
    )
