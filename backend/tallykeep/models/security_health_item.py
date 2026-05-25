"""security_health_item table (ADR-0019)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class SecurityHealthItemRow(Base):
    __tablename__ = "security_health_item"
    __table_args__ = (
        CheckConstraint(
            "state IN ('open','resolved_by_fix','dismissed_intentional','acknowledged')",
            name="security_health_item_state_in_set",
        ),
        CheckConstraint(
            "severity IN ('critical','warning','notification')",
            name="security_health_item_severity_in_set",
        ),
        # Active query: open items sorted by severity desc, created_at desc.
        Index(
            "ix_security_health_item_state_severity_created",
            "state", "severity", "created_at",
        ),
        # History query: resolved items sorted by resolved_at desc.
        Index(
            "ix_security_health_item_state_resolved",
            "state", "resolved_at",
        ),
        # Per-Holding lookups.
        Index("ix_security_health_item_holding_id", "holding_id"),
        # Badge count: open critical items.
        Index(
            "ix_security_health_item_open",
            "state",
            postgresql_where=text("state = 'open'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    item_type: Mapped[str] = mapped_column(String(60), nullable=False)
    holding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("holding.id", ondelete="CASCADE"), nullable=True
    )
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'open'")
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
