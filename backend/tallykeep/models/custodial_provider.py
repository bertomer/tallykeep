"""custodial_provider table (spec module 03)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class CustodialProviderRow(Base):
    __tablename__ = "custodial_provider"
    __table_args__ = (
        # One CustodialProvider per Account Holding.
        UniqueConstraint("holding_id", name="uq_custodial_provider_holding_id"),
        CheckConstraint(
            "provider_kind IN ('exchange','broker','p2p_venue')",
            name="custodial_provider_kind_in_set",
        ),
        CheckConstraint(
            "can_read = TRUE",
            name="custodial_provider_can_read_true",
        ),
        CheckConstraint(
            "can_trade = FALSE",
            name="custodial_provider_can_trade_false",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"), nullable=False
    )
    provider_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(50), nullable=False)
    api_credential_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    api_secret_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    api_passphrase_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    can_read: Mapped[bool] = mapped_column(nullable=False, server_default=text("TRUE"))
    can_trade: Mapped[bool] = mapped_column(nullable=False, server_default=text("FALSE"))
    can_withdraw: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    # Nullable: populated by the withdrawal sub-flow (ADR-0011), not at wizard creation.
    whitelist_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    whitelist_address_descriptor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("descriptor.id", ondelete="RESTRICT"), nullable=True
    )
    whitelist_verified: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("TRUE"), index=True
    )
    last_polled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_known_balance_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Connection health state machine (ADR-0012 / iteration A).
    # healthy | degraded | unreachable | auth_failed
    connection_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'healthy'")
    )
    consecutive_error_count: Mapped[int] = mapped_column(
        nullable=False, server_default=text("0")
    )
    ledger_cursor_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    polling_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("600")
    )
    observation_key_last_four: Mapped[str | None] = mapped_column(
        String(4), nullable=True
    )
    non_btc_balances: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
