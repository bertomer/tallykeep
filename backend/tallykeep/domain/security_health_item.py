"""SecurityHealthItem domain entity (ADR-0019)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


# Canonical string values — used in DB and on the wire.
ITEM_STATE_OPEN = "open"
ITEM_STATE_RESOLVED_BY_FIX = "resolved_by_fix"
ITEM_STATE_DISMISSED_INTENTIONAL = "dismissed_intentional"
ITEM_STATE_ACKNOWLEDGED = "acknowledged"

ITEM_SEVERITY_CRITICAL = "critical"
ITEM_SEVERITY_WARNING = "warning"
ITEM_SEVERITY_NOTIFICATION = "notification"

# Only intentional dismissals are revivable — acknowledged states (seed backup, principles) are permanent.
USER_ATTESTED_STATES = {ITEM_STATE_DISMISSED_INTENTIONAL}

# Item type constants.
ITEM_TYPE_SEED_BACKUP = "seed_backup"
ITEM_TYPE_MISSING_SIGNING_METADATA = "missing_signing_metadata"
ITEM_TYPE_PRINCIPLES_ACK = "principles_ack"


@dataclass
class SecurityHealthItem:
    id: UUID
    item_type: str
    holding_id: UUID | None
    state: str
    severity: str
    created_at: datetime
    resolved_at: datetime | None
    dismissal_reason: str | None
    raw_context: dict[str, Any]

    @property
    def is_open(self) -> bool:
        return self.state == ITEM_STATE_OPEN

    @property
    def is_user_attested(self) -> bool:
        return self.state in USER_ATTESTED_STATES
