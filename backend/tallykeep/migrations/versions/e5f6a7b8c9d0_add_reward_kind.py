"""Add 'reward' to custodial_ledger_entry kind check constraint.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-18

Kraken staking rewards arrive with ccxt type 'reward' or 'staking' / 'earn';
the adapter normalises these to TK kind 'reward'. The existing CHECK constraint
must be widened to accept it.

The constraint's DB name includes the naming-convention prefix applied by
SQLAlchemy MetaData: ck_<table>_<explicit_name>, which produces the doubly-
prefixed name 'ck_custodial_ledger_entry_ck_custodial_ledger_entry_kind'.
Raw SQL is used here to avoid ambiguity when dropping/recreating.
"""
from __future__ import annotations

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_OLD_KINDS = ("trade", "deposit", "withdrawal", "transfer", "fee", "other")
_NEW_KINDS = ("trade", "deposit", "withdrawal", "transfer", "fee", "reward", "other")

_CONSTRAINT_DB_NAME = "ck_custodial_ledger_entry_ck_custodial_ledger_entry_kind"


def upgrade() -> None:
    old_sql = ", ".join(f"'{k}'" for k in _OLD_KINDS)
    new_sql = ", ".join(f"'{k}'" for k in _NEW_KINDS)

    op.execute(
        f'ALTER TABLE custodial_ledger_entry '
        f'DROP CONSTRAINT IF EXISTS "{_CONSTRAINT_DB_NAME}"'
    )
    op.execute(
        f'ALTER TABLE custodial_ledger_entry '
        f'ADD CONSTRAINT "{_CONSTRAINT_DB_NAME}" '
        f'CHECK (kind IN ({new_sql}))'
    )


def downgrade() -> None:
    old_sql = ", ".join(f"'{k}'" for k in _OLD_KINDS)
    new_sql = ", ".join(f"'{k}'" for k in _NEW_KINDS)

    op.execute(
        f'ALTER TABLE custodial_ledger_entry '
        f'DROP CONSTRAINT IF EXISTS "{_CONSTRAINT_DB_NAME}"'
    )
    # Normalise 'reward' rows back to 'other' before re-applying the old constraint.
    op.execute(
        f"UPDATE custodial_ledger_entry SET kind = 'other' WHERE kind NOT IN ({old_sql})"
    )
    op.execute(
        f'ALTER TABLE custodial_ledger_entry '
        f'ADD CONSTRAINT "{_CONSTRAINT_DB_NAME}" '
        f'CHECK (kind IN ({old_sql}))'
    )
