"""runtime_configuration repository.

The table is a flat key-value store keyed by dotted strings (`bitcoind.rpc_host`,
`fee_estimation.strategy`, ...). The API surface (spec module 04) exposes a nested
JSON shape, which the service layer assembles by un/grouping keys on a single dot
boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tallykeep.models import RuntimeConfigurationRow


def list_all(session: Session) -> dict[str, Any]:
    """Return every persisted key, mapped to its JSON-decoded value."""
    rows = session.execute(select(RuntimeConfigurationRow)).scalars().all()
    return {row.key: row.value for row in rows}


def upsert_many(session: Session, items: dict[str, Any]) -> None:
    """Insert or replace each (key, value) pair. Commits before returning."""
    if not items:
        return
    now = datetime.now(UTC)
    existing = {
        row.key: row
        for row in session.execute(
            select(RuntimeConfigurationRow).where(
                RuntimeConfigurationRow.key.in_(list(items.keys()))
            )
        ).scalars()
    }
    for key, value in items.items():
        if key in existing:
            existing[key].value = value
            existing[key].updated_at = now
        else:
            session.add(RuntimeConfigurationRow(key=key, value=value))
    session.commit()


def delete_keys(session: Session, keys: list[str]) -> None:
    if not keys:
        return
    session.execute(
        delete(RuntimeConfigurationRow).where(RuntimeConfigurationRow.key.in_(keys))
    )
    session.commit()


__all__ = ["list_all", "upsert_many", "delete_keys"]
