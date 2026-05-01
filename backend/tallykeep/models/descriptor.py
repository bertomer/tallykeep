"""descriptor + address + utxo tables (spec module 03)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
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


class DescriptorRow(Base):
    __tablename__ = "descriptor"
    __table_args__ = (
        CheckConstraint(
            "network IN ('mainnet','testnet','signet','regtest')",
            name="descriptor_network_in_set",
        ),
        CheckConstraint(
            "is_watch_only = TRUE",
            name="descriptor_is_watch_only",
        ),
        UniqueConstraint("expression", name="uq_descriptor_expression"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("holding.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    change_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    network: Mapped[str] = mapped_column(String(10), nullable=False)
    address_type: Mapped[str] = mapped_column(String(20), nullable=False)
    gap_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("20")
    )
    is_watch_only: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("TRUE")
    )
    last_scanned_height: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class AddressRow(Base):
    __tablename__ = "address"
    __table_args__ = (
        UniqueConstraint(
            "descriptor_id",
            "is_change",
            "derivation_index",
            name="uq_address_descriptor_branch_index",
        ),
        Index("ix_address_lookup", "address"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    descriptor_id: Mapped[UUID] = mapped_column(
        ForeignKey("descriptor.id", ondelete="RESTRICT"), nullable=False
    )
    address: Mapped[str] = mapped_column(String(100), nullable=False)
    derivation_path: Mapped[str] = mapped_column(String(100), nullable=False)
    is_change: Mapped[bool] = mapped_column(nullable=False)
    derivation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_reused: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )


class UTXORow(Base):
    __tablename__ = "utxo"
    __table_args__ = (
        UniqueConstraint("txid", "vout", name="uq_utxo_outpoint"),
        Index(
            "ix_utxo_descriptor_unspent",
            "descriptor_id",
            postgresql_where=text("is_spent = FALSE"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    descriptor_id: Mapped[UUID] = mapped_column(
        ForeignKey("descriptor.id", ondelete="RESTRICT"), nullable=False
    )
    address_id: Mapped[UUID] = mapped_column(
        ForeignKey("address.id", ondelete="RESTRICT"), nullable=False
    )
    txid: Mapped[str] = mapped_column(String(64), nullable=False)
    vout: Mapped[int] = mapped_column(Integer, nullable=False)
    value_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    confirmation_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_frozen: Mapped[bool] = mapped_column(nullable=False, server_default=text("FALSE"))
    is_spent: Mapped[bool] = mapped_column(nullable=False, server_default=text("FALSE"))
    spent_in_txid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hygiene_flags: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
