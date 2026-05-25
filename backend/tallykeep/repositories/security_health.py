"""Repository for security_health_item table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from tallykeep.domain.security_health_item import (
    ITEM_STATE_OPEN,
    SecurityHealthItem,
)
from tallykeep.models.security_health_item import SecurityHealthItemRow


def _row_to_domain(row: SecurityHealthItemRow) -> SecurityHealthItem:
    return SecurityHealthItem(
        id=row.id,
        item_type=row.item_type,
        holding_id=row.holding_id,
        state=row.state,
        severity=row.severity,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
        dismissal_reason=row.dismissal_reason,
        raw_context=dict(row.raw_context or {}),
    )


def insert(
    session: Session,
    *,
    id: UUID,
    item_type: str,
    holding_id: UUID | None,
    severity: str,
    raw_context: dict[str, Any],
) -> SecurityHealthItem:
    row = SecurityHealthItemRow(
        id=id,
        item_type=item_type,
        holding_id=holding_id,
        state=ITEM_STATE_OPEN,
        severity=severity,
        created_at=datetime.now(UTC),
        resolved_at=None,
        dismissal_reason=None,
        raw_context=raw_context,
    )
    session.add(row)
    session.flush()
    return _row_to_domain(row)


def get(session: Session, item_id: UUID) -> SecurityHealthItem | None:
    row = session.get(SecurityHealthItemRow, item_id)
    return _row_to_domain(row) if row else None


def list_open(
    session: Session,
    *,
    holding_id: UUID | None = None,
    include_application_level: bool = True,
) -> list[SecurityHealthItem]:
    """Return open items sorted by severity desc (critical > warning > notification)
    then created_at desc.

    If `holding_id` is set, return items for that Holding only.
    If `include_application_level` is True and `holding_id` is None, return all open
    items (application-level + per-Holding — only used by the dashboard endpoint).
    """
    severity_order = sa.case(
        (SecurityHealthItemRow.severity == "critical", 0),
        (SecurityHealthItemRow.severity == "warning", 1),
        else_=2,
    )
    q = session.query(SecurityHealthItemRow).filter(
        SecurityHealthItemRow.state == ITEM_STATE_OPEN
    )
    if holding_id is not None:
        q = q.filter(SecurityHealthItemRow.holding_id == holding_id)
    elif not include_application_level:
        q = q.filter(SecurityHealthItemRow.holding_id.isnot(None))
    q = q.order_by(severity_order, SecurityHealthItemRow.created_at.desc())
    return [_row_to_domain(r) for r in q.all()]


def list_application_level_open(session: Session) -> list[SecurityHealthItem]:
    """Open items with holding_id IS NULL (application-level)."""
    return list_open(session, holding_id=None, include_application_level=False)


def list_application_level_open_real(session: Session) -> list[SecurityHealthItem]:
    """Dedicated query for Home section: open items with holding_id IS NULL."""
    severity_order = sa.case(
        (SecurityHealthItemRow.severity == "critical", 0),
        (SecurityHealthItemRow.severity == "warning", 1),
        else_=2,
    )
    rows = (
        session.query(SecurityHealthItemRow)
        .filter(
            SecurityHealthItemRow.state == ITEM_STATE_OPEN,
            SecurityHealthItemRow.holding_id.is_(None),
        )
        .order_by(severity_order, SecurityHealthItemRow.created_at.desc())
        .all()
    )
    return [_row_to_domain(r) for r in rows]


def list_history(session: Session) -> list[SecurityHealthItem]:
    """All non-open items, reverse-chronological by resolved_at."""
    rows = (
        session.query(SecurityHealthItemRow)
        .filter(SecurityHealthItemRow.state != ITEM_STATE_OPEN)
        .order_by(SecurityHealthItemRow.resolved_at.desc().nullsfirst())
        .all()
    )
    return [_row_to_domain(r) for r in rows]


def count_open_critical(session: Session) -> int:
    return (
        session.query(SecurityHealthItemRow)
        .filter(
            SecurityHealthItemRow.state == ITEM_STATE_OPEN,
            SecurityHealthItemRow.severity == "critical",
        )
        .count()
    )


def has_open_item_of_type(
    session: Session,
    item_type: str,
    *,
    holding_id: UUID | None = None,
) -> bool:
    q = session.query(SecurityHealthItemRow).filter(
        SecurityHealthItemRow.state == ITEM_STATE_OPEN,
        SecurityHealthItemRow.item_type == item_type,
    )
    if holding_id is not None:
        q = q.filter(SecurityHealthItemRow.holding_id == holding_id)
    else:
        q = q.filter(SecurityHealthItemRow.holding_id.is_(None))
    return q.first() is not None


def resolve(
    session: Session,
    item_id: UUID,
    *,
    new_state: str,
    dismissal_reason: str | None = None,
) -> SecurityHealthItem | None:
    row = session.get(SecurityHealthItemRow, item_id)
    if row is None:
        return None
    row.state = new_state
    row.resolved_at = datetime.now(UTC)
    if dismissal_reason is not None:
        row.dismissal_reason = dismissal_reason
    session.flush()
    return _row_to_domain(row)


def revive(session: Session, item_id: UUID) -> SecurityHealthItem | None:
    row = session.get(SecurityHealthItemRow, item_id)
    if row is None:
        return None
    row.state = ITEM_STATE_OPEN
    row.resolved_at = None
    row.dismissal_reason = None
    session.flush()
    return _row_to_domain(row)


def resolve_open_items_for_holding(
    session: Session,
    holding_id: UUID,
    item_type: str,
    new_state: str,
) -> list[SecurityHealthItem]:
    """Flip all open items of a given type for a holding to a terminal state."""
    rows = (
        session.query(SecurityHealthItemRow)
        .filter(
            SecurityHealthItemRow.state == ITEM_STATE_OPEN,
            SecurityHealthItemRow.item_type == item_type,
            SecurityHealthItemRow.holding_id == holding_id,
        )
        .all()
    )
    now = datetime.now(UTC)
    resolved = []
    for row in rows:
        row.state = new_state
        row.resolved_at = now
        resolved.append(_row_to_domain(row))
    session.flush()
    return resolved
