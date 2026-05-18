"""custodial_ledger_entry table — per ADR-0013 (mirror posture)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base

_VALID_KINDS = ("trade", "deposit", "withdrawal", "transfer", "fee", "reward", "other")
_KIND_CHECK = f"kind IN ({', '.join(repr(k) for k in _VALID_KINDS)})"


class CustodialLedgerEntryRow(Base):
    """One entry from a provider's unified ledger feed, persisted per ADR-0013."""

    __tablename__ = "custodial_ledger_entry"
    __table_args__ = (
        UniqueConstraint(
            "custodial_provider_id",
            "provider_entry_id",
            name="uq_custodial_ledger_entry_provider_entry",
        ),
        CheckConstraint(_KIND_CHECK, name="ck_custodial_ledger_entry_kind"),
        Index(
            "idx_custodial_ledger_entry_provider_timestamp",
            "custodial_provider_id",
            "timestamp",
        ),
        Index(
            "idx_custodial_ledger_entry_holding_time",
            "holding_id",
            text("timestamp DESC"),
        ),
        Index(
            "idx_custodial_ledger_entry_unreconciled",
            "holding_id",
            "timestamp",
            postgresql_where=text(
                "reconciled_at IS NULL AND kind IN ('deposit', 'withdrawal')"
            ),
        ),
        Index(
            "idx_custodial_ledger_entry_sweep_link",
            "linked_sweep_execution_id",
            postgresql_where=text("linked_sweep_execution_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"), nullable=False
    )
    custodial_provider_id: Mapped[UUID] = mapped_column(
        ForeignKey("custodial_provider.id", ondelete="CASCADE"), nullable=False
    )
    provider_entry_id: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fee_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))

    # TK-initiated linkage — null = pure observation entry.
    linked_sweep_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sweep_execution.id", ondelete="RESTRICT"), nullable=True
    )
    linked_counterparty_holding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"), nullable=True
    )
    linked_chain_ledger_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ledger_entry.id", ondelete="RESTRICT"), nullable=True
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
