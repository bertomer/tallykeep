"""payment_request + broadcast_attempt tables (spec module 03)."""

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


class PaymentRequestRow(Base):
    __tablename__ = "payment_request"
    __table_args__ = (
        CheckConstraint(
            "payment_type IN ('onchain','lightning')",
            name="payment_request_type_in_set",
        ),
        Index(
            "ix_payment_request_broadcast_txid",
            "broadcast_txid",
            postgresql_where=text("broadcast_txid IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    destination_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bip21_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    psbt_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_transaction_hex: Mapped[str | None] = mapped_column(Text, nullable=True)
    broadcast_txid: Mapped[str | None] = mapped_column(String(64), nullable=True)

    lightning_invoice: Mapped[str | None] = mapped_column(Text, nullable=True)
    lightning_payment_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    resulting_ledger_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ledger_entry.id", ondelete="RESTRICT"), nullable=True
    )
    sweep_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sweep_execution.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class BroadcastAttemptRow(Base):
    """Spec module 03: distinct from payment_request because a single payment may have
    multiple broadcast attempts (initial fail, retry, RBF in v1.x)."""

    __tablename__ = "broadcast_attempt"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    payment_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("payment_request.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    transaction_hex: Mapped[str] = mapped_column(Text, nullable=False)
    txid: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
