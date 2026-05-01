"""ledger_entry + ledger_entry_holding_link tables (spec module 03)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class LedgerEntryRow(Base):
    __tablename__ = "ledger_entry"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('incoming','outgoing','internal')",
            name="ledger_entry_direction_in_set",
        ),
        CheckConstraint(
            "source IN ('onchain_transaction','lightning_payment','custodial_event')",
            name="ledger_entry_source_in_set",
        ),
        Index("ix_ledger_entry_timestamp", text("timestamp DESC")),
        Index(
            "ix_ledger_entry_uncategorized",
            "id",
            postgresql_where=text("category IS NULL"),
        ),
        Index("ix_ledger_entry_source_reference", "source", "source_reference"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    net_amount_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fee_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    counterparty_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    categorized_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class LedgerEntryHoldingLinkRow(Base):
    """Many-to-many between LedgerEntry and Holding.

    A single LedgerEntry can affect multiple Holdings (internal transfer).
    """

    __tablename__ = "ledger_entry_holding_link"

    ledger_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("ledger_entry.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    holding_amount_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
