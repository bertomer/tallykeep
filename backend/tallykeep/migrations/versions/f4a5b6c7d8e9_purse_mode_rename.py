"""Rename seed_origin -> purse_mode and rewrite enum values in holding.subtype_data.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-05-14

Rewrites every Purse row's subtype_data JSONB:
- key "seed_origin" -> "purse_mode"
- value "external_watch_only" -> "watch_only"
- value "tallykeep_managed" -> "on_device_tk_generated"

Idempotent: rows that already carry "purse_mode" are left unchanged.
Re-running is safe.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Value map: old string -> new string
    value_map = {
        "external_watch_only": "watch_only",
        "tallykeep_managed": "on_device_tk_generated",
    }

    rows = conn.execute(
        sa.text(
            "SELECT id, subtype_data FROM holding "
            "WHERE holding_type = 'purse' AND subtype_data IS NOT NULL"
        )
    ).fetchall()

    for row_id, subtype_data in rows:
        if subtype_data is None:
            continue

        changed = False

        # Rename key: seed_origin -> purse_mode
        if "seed_origin" in subtype_data and "purse_mode" not in subtype_data:
            old_val = subtype_data.pop("seed_origin")
            subtype_data["purse_mode"] = old_val
            changed = True
        elif "seed_origin" in subtype_data and "purse_mode" in subtype_data:
            # purse_mode already present; just drop the old key
            subtype_data.pop("seed_origin")
            changed = True

        # Rewrite enum value if needed
        if "purse_mode" in subtype_data and subtype_data["purse_mode"] in value_map:
            subtype_data["purse_mode"] = value_map[subtype_data["purse_mode"]]
            changed = True

        if changed:
            conn.execute(
                sa.text(
                    "UPDATE holding SET subtype_data = :data::jsonb WHERE id = :id"
                ),
                {"data": __import__("json").dumps(subtype_data), "id": str(row_id)},
            )


def downgrade() -> None:
    conn = op.get_bind()

    reverse_value_map = {
        "watch_only": "external_watch_only",
        "on_device_tk_generated": "tallykeep_managed",
    }

    rows = conn.execute(
        sa.text(
            "SELECT id, subtype_data FROM holding "
            "WHERE holding_type = 'purse' AND subtype_data IS NOT NULL"
        )
    ).fetchall()

    for row_id, subtype_data in rows:
        if subtype_data is None:
            continue

        changed = False

        if "purse_mode" in subtype_data and "seed_origin" not in subtype_data:
            val = subtype_data.pop("purse_mode")
            subtype_data["seed_origin"] = val
            changed = True

        if "seed_origin" in subtype_data and subtype_data["seed_origin"] in reverse_value_map:
            subtype_data["seed_origin"] = reverse_value_map[subtype_data["seed_origin"]]
            changed = True

        if changed:
            conn.execute(
                sa.text(
                    "UPDATE holding SET subtype_data = :data::jsonb WHERE id = :id"
                ),
                {"data": __import__("json").dumps(subtype_data), "id": str(row_id)},
            )
