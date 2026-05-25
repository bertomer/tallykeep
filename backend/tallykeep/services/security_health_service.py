"""Security health service — item lifecycle, hooks, and fix-metadata logic (ADR-0019)."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from tallykeep.domain.security_health_item import (
    ITEM_SEVERITY_CRITICAL,
    ITEM_SEVERITY_WARNING,
    ITEM_STATE_ACKNOWLEDGED,
    ITEM_STATE_DISMISSED_INTENTIONAL,
    ITEM_STATE_OPEN,
    ITEM_STATE_RESOLVED_BY_FIX,
    ITEM_TYPE_MISSING_SIGNING_METADATA,
    ITEM_TYPE_PRINCIPLES_ACK,
    ITEM_TYPE_SEED_BACKUP,
    USER_ATTESTED_STATES,
    SecurityHealthItem,
)
from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.repositories import security_health as security_health_repo

_FINGERPRINT_RE = re.compile(r'\[([0-9a-fA-F]{8})[/\]]')


class SecurityHealthServiceError(ValueError):
    pass


class InvalidStateTransition(SecurityHealthServiceError):
    pass


class ReviveNotAllowed(SecurityHealthServiceError):
    pass


# ---------------------------------------------------------------------------
# Item creation hooks (called from holding_service after holding creation)
# ---------------------------------------------------------------------------


def emit_seed_backup_item(
    session: Session,
    *,
    holding_id: UUID,
    purse_mode: str,
    bus: EventBus | None,
) -> SecurityHealthItem | None:
    """Emit a critical seed_backup item for ON_DEVICE Purses."""
    if security_health_repo.has_open_item_of_type(
        session, ITEM_TYPE_SEED_BACKUP, holding_id=holding_id
    ):
        return None
    from tallykeep.models.holding import HoldingRow
    holding = session.get(HoldingRow, holding_id)
    item = security_health_repo.insert(
        session,
        id=uuid4(),
        item_type=ITEM_TYPE_SEED_BACKUP,
        holding_id=holding_id,
        severity=ITEM_SEVERITY_CRITICAL,
        raw_context={"purse_mode": purse_mode, "holding_name": holding.name if holding else ""},
    )
    session.commit()
    _publish_item_added(bus, item)
    return item


def emit_missing_signing_metadata_item(
    session: Session,
    *,
    holding_id: UUID,
    vendor: str | None,
    bus: EventBus | None,
) -> SecurityHealthItem | None:
    """Emit a warning missing_signing_metadata item for Strongbox / Vault."""
    if security_health_repo.has_open_item_of_type(
        session, ITEM_TYPE_MISSING_SIGNING_METADATA, holding_id=holding_id
    ):
        return None
    from tallykeep.models.holding import HoldingRow
    holding = session.get(HoldingRow, holding_id)
    ctx: dict[str, Any] = {"holding_name": holding.name if holding else ""}
    if vendor:
        ctx["vendor"] = vendor
    item = security_health_repo.insert(
        session,
        id=uuid4(),
        item_type=ITEM_TYPE_MISSING_SIGNING_METADATA,
        holding_id=holding_id,
        severity=ITEM_SEVERITY_WARNING,
        raw_context=ctx,
    )
    session.commit()
    _publish_item_added(bus, item)
    return item


def emit_principles_ack_item_if_needed(
    session: Session,
    *,
    bus: EventBus | None,
) -> SecurityHealthItem | None:
    """Idempotently emit a warning principles_ack item (application-level)."""
    if security_health_repo.has_open_item_of_type(
        session, ITEM_TYPE_PRINCIPLES_ACK, holding_id=None
    ):
        return None
    item = security_health_repo.insert(
        session,
        id=uuid4(),
        item_type=ITEM_TYPE_PRINCIPLES_ACK,
        holding_id=None,
        severity=ITEM_SEVERITY_WARNING,
        raw_context={},
    )
    session.commit()
    _publish_item_added(bus, item)
    return item


# ---------------------------------------------------------------------------
# Resolve / revive
# ---------------------------------------------------------------------------


_VALID_TRANSITIONS: dict[str, set[str]] = {
    ITEM_STATE_OPEN: {
        ITEM_STATE_RESOLVED_BY_FIX,
        ITEM_STATE_DISMISSED_INTENTIONAL,
        ITEM_STATE_ACKNOWLEDGED,
    },
}


def resolve_item(
    session: Session,
    item_id: UUID,
    *,
    new_state: str,
    dismissal_reason: str | None = None,
    bus: EventBus | None,
) -> SecurityHealthItem:
    item = security_health_repo.get(session, item_id)
    if item is None:
        raise SecurityHealthServiceError(f"Item {item_id} not found")

    allowed = _VALID_TRANSITIONS.get(item.state, set())
    if new_state not in allowed:
        raise InvalidStateTransition(
            f"Cannot transition from '{item.state}' to '{new_state}'"
        )

    updated = security_health_repo.resolve(
        session, item_id, new_state=new_state, dismissal_reason=dismissal_reason
    )
    assert updated is not None  # noqa: S101

    if item.item_type == ITEM_TYPE_PRINCIPLES_ACK and new_state == ITEM_STATE_ACKNOWLEDGED:
        from tallykeep.repositories import user_profile as profile_repo
        profile_repo.update(session, principles_acknowledged=True)

    session.commit()
    _publish_item_resolved(bus, updated)
    return updated


def revive_item(
    session: Session,
    item_id: UUID,
    *,
    bus: EventBus | None,
) -> SecurityHealthItem:
    item = security_health_repo.get(session, item_id)
    if item is None:
        raise SecurityHealthServiceError(f"Item {item_id} not found")

    if item.state not in USER_ATTESTED_STATES:
        raise ReviveNotAllowed(
            "revive_not_allowed_on_system_verified: only user-attested items can be revived"
        )

    updated = security_health_repo.revive(session, item_id)
    assert updated is not None  # noqa: S101
    session.commit()
    _publish_item_revived(bus, updated)
    return updated


# ---------------------------------------------------------------------------
# Fix-metadata re-checker: called after a descriptor update succeeds
# ---------------------------------------------------------------------------


def resolve_missing_metadata_items_for_holding(
    session: Session,
    holding_id: UUID,
    *,
    bus: EventBus | None,
) -> list[SecurityHealthItem]:
    """Flip any open missing_signing_metadata items for a Holding to RESOLVED_BY_FIX."""
    resolved = security_health_repo.resolve_open_items_for_holding(
        session,
        holding_id=holding_id,
        item_type=ITEM_TYPE_MISSING_SIGNING_METADATA,
        new_state=ITEM_STATE_RESOLVED_BY_FIX,
    )
    session.commit()
    for item in resolved:
        _publish_item_resolved(bus, item)
    return resolved


# ---------------------------------------------------------------------------
# Principles-ack resolution (also sets user.principles_acknowledged_at)
# ---------------------------------------------------------------------------


def acknowledge_principles(
    session: Session,
    *,
    bus: EventBus | None,
) -> list[SecurityHealthItem]:
    """Acknowledge all open principles_ack items."""
    from tallykeep.repositories import user_profile as profile_repo

    profile_repo.update(session, principles_acknowledged=True)

    resolved = security_health_repo.resolve_open_items_for_holding(
        session,
        holding_id=None,  # type: ignore[arg-type]  — application-level
        item_type=ITEM_TYPE_PRINCIPLES_ACK,
        new_state=ITEM_STATE_ACKNOWLEDGED,
    )
    # resolve_open_items_for_holding uses holding_id==None to filter; patch it
    # to also handle None:
    # (The repo function filters by holding_id == holding_id which for None
    #  becomes IS NULL — which is correct for application-level items.)
    session.commit()
    for item in resolved:
        _publish_item_resolved(bus, item)
    return resolved


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _item_payload(item: SecurityHealthItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "item_type": item.item_type,
        "holding_id": str(item.holding_id) if item.holding_id else None,
        "state": item.state,
        "severity": item.severity,
        "created_at": item.created_at.isoformat(),
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "dismissal_reason": item.dismissal_reason,
        "raw_context": item.raw_context,
    }


def _publish_item_added(bus: EventBus | None, item: SecurityHealthItem) -> None:
    if bus is None:
        return
    try:
        bus.publish("security_health.item_added", _item_payload(item))
    except Exception:  # noqa: BLE001
        pass


def _publish_item_resolved(bus: EventBus | None, item: SecurityHealthItem) -> None:
    if bus is None:
        return
    try:
        bus.publish("security_health.item_resolved", _item_payload(item))
    except Exception:  # noqa: BLE001
        pass


def _publish_item_revived(bus: EventBus | None, item: SecurityHealthItem) -> None:
    if bus is None:
        return
    try:
        bus.publish("security_health.item_revived", _item_payload(item))
    except Exception:  # noqa: BLE001
        pass
