"""sweep_policy + sweep_execution tables (spec module 03)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class SweepPolicyRow(Base):
    __tablename__ = "sweep_policy"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('scheduled','threshold','manual')",
            name="sweep_policy_trigger_type_in_set",
        ),
        CheckConstraint(
            "source_holding_id <> destination_holding_id",
            name="sweep_policy_source_neq_destination",
        ),
        Index(
            "ix_sweep_policy_enabled",
            "is_enabled",
            postgresql_where=text("is_enabled = TRUE"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_configuration: Mapped[Any] = mapped_column(JSONB, nullable=False)
    minimum_balance_sats: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    maximum_per_period_sats: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    requires_user_confirmation: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("TRUE")
    )
    is_dry_run: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    safety_warnings: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    last_executed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_result_summary: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class SweepExecutionRow(Base):
    __tablename__ = "sweep_execution"
    __table_args__ = (
        Index(
            "ix_sweep_execution_policy",
            "sweep_policy_id",
            text("triggered_at DESC"),
        ),
        Index(
            "ix_sweep_execution_pending",
            "status",
            postgresql_where=text(
                "status NOT IN ('completed','failed','cancelled')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    sweep_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("sweep_policy.id", ondelete="RESTRICT"),
        nullable=False,
    )
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    pre_balance_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    intended_amount_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_withdrawal_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    expected_txid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmed_txid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
