"""custodial_ledger_entry and custodial_provider connection-status columns."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class CustodialLedgerEntryRow(Base):
    """One entry from a provider's unified ledger feed, persisted per observation cycle."""

    __tablename__ = "custodial_ledger_entry"
    __table_args__ = (
        UniqueConstraint(
            "custodial_provider_id",
            "provider_entry_id",
            name="uq_custodial_ledger_entry_provider_entry",
        ),
        Index(
            "idx_custodial_ledger_entry_provider_timestamp",
            "custodial_provider_id",
            "timestamp",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    custodial_provider_id: Mapped[UUID] = mapped_column(
        ForeignKey("custodial_provider.id", ondelete="CASCADE"), nullable=False
    )
    provider_entry_id: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # deposit | withdrawal | trade | fee | transfer | staking
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # pending | success | failed
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
