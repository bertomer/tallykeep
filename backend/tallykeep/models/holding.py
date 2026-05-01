"""holding + holding_type_change_log tables (spec module 03)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class HoldingRow(Base):
    """Single table for all holding subtypes; subtype-specific data lives in JSONB.

    Per spec module 03: "this is acceptable because the count of subtype-specific
    fields is small and queries are mostly type-aware."
    """

    __tablename__ = "holding"
    __table_args__ = (
        CheckConstraint(
            "holding_type IN ('account','purse','strongbox','vault')",
            name="holding_type_in_set",
        ),
        CheckConstraint(
            "purpose IN ('spending','reserve','long_term','transit','undeclared')",
            name="purpose_in_set",
        ),
        Index(
            "ix_holding_holding_type_active",
            "holding_type",
            postgresql_where=text("is_archived = FALSE"),
        ),
        Index(
            "ix_holding_purpose_active",
            "purpose",
            postgresql_where=text("is_archived = FALSE"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)

    declared_custody_model: Mapped[str] = mapped_column(String(30), nullable=False)
    declared_signing_model: Mapped[str] = mapped_column(String(30), nullable=False)
    declared_geographic_distribution: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    declared_inheritance_configured: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    declared_security_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    subtype_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    display_color: Mapped[str] = mapped_column(
        String(7), nullable=False, server_default=text("'#000000'")
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_archived: Mapped[bool] = mapped_column(nullable=False, server_default=text("FALSE"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class HoldingTypeChangeLogRow(Base):
    """Audit log for the rare case of changing a Holding's type.

    Spec module 02: "Type is mutable but requires deliberate confirmation."
    """

    __tablename__ = "holding_type_change_log"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"), nullable=False
    )
    previous_type: Mapped[str] = mapped_column(String(20), nullable=False)
    new_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
