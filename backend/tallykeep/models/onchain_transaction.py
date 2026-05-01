"""onchain_transaction table (spec module 03).

Stored once per txid, regardless of how many of our Holdings it touches.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from tallykeep.models.base import Base


class OnChainTransactionRow(Base):
    __tablename__ = "onchain_transaction"
    __table_args__ = (
        Index("ix_onchain_transaction_block_time", text("block_time DESC")),
        Index(
            "ix_onchain_transaction_unconfirmed",
            "txid",
            postgresql_where=text("confirmation_height IS NULL"),
        ),
    )

    txid: Mapped[str] = mapped_column(String(64), primary_key=True)
    raw_hex: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    fee_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    size_vbytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_coinjoin_suspected: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("FALSE")
    )
