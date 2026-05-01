"""invoice table (spec module 03)."""

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


class InvoiceRow(Base):
    __tablename__ = "invoice"
    __table_args__ = (
        CheckConstraint(
            "invoice_type IN ('onchain','lightning')",
            name="invoice_type_in_set",
        ),
        Index(
            "ix_invoice_receiving_address",
            "receiving_address",
            postgresql_where=text("receiving_address IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    invoice_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    receiving_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    receiving_address_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("address.id", ondelete="RESTRICT"), nullable=True
    )
    bip21_uri: Mapped[str | None] = mapped_column(Text, nullable=True)

    bolt11: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    resulting_ledger_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ledger_entry.id", ondelete="RESTRICT"), nullable=True
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
