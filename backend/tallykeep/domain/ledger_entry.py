"""LedgerEntry, LedgerEntryHoldingLink, OnChainTransaction (spec module 02).

LedgerEntry is the user-facing record of a value movement; it may be backed by an
OnChainTransaction (v1), a Lightning payment (v1.5), or a CustodialProvider event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import Direction, LedgerCategory, LedgerEntrySource


@dataclass
class LedgerEntry:
    id: UUID
    direction: Direction
    net_amount_sats: int  # positive for incoming, negative for outgoing
    fee_sats: int | None
    timestamp: datetime  # block time, mempool first-seen, or provider event time
    source: LedgerEntrySource
    source_reference: str  # txid, payment_hash, or provider event id
    category: LedgerCategory | None
    counterparty_label: str | None
    note: str | None
    suggested_category: LedgerCategory | None
    categorized_at: datetime | None
    created_at: datetime

    def __post_init__(self) -> None:
        # Spec module 02:
        #   "every LedgerEntry must point to exactly one source object identified by
        #    `source` plus `source_reference`."
        if not self.source_reference:
            raise ValueError("LedgerEntry.source_reference is required")

        # Direction-amount consistency. Internal transfers can have net 0 across the
        # *user's full set of holdings*, but on a single LedgerEntry the net_amount_sats
        # is the user's perspective; we keep the sign rule loose for INTERNAL because
        # both sides are the user.
        if self.direction == Direction.INCOMING and self.net_amount_sats < 0:
            raise ValueError("Incoming LedgerEntry must have net_amount_sats >= 0")
        if self.direction == Direction.OUTGOING and self.net_amount_sats > 0:
            raise ValueError("Outgoing LedgerEntry must have net_amount_sats <= 0")

        if self.fee_sats is not None and self.fee_sats < 0:
            raise ValueError("LedgerEntry.fee_sats must be >= 0")

        if self.category is not None and self.categorized_at is None:
            raise ValueError(
                "LedgerEntry with category set must also have categorized_at"
            )


@dataclass
class LedgerEntryHoldingLink:
    """Spec module 02: many-to-many between LedgerEntry and Holding.

    A single LedgerEntry can affect multiple Holdings simultaneously (e.g. an internal
    transfer between two of the user's own Holdings produces one entry that touches
    both).
    """

    ledger_entry_id: UUID
    holding_id: UUID
    holding_amount_sats: int  # net effect on this specific Holding


@dataclass
class OnChainTransaction:
    """Spec module 02: the Bitcoin blockchain record.

    Stored once per txid, regardless of how many Holdings it touches.
    """

    txid: str
    raw_hex: str | None
    confirmation_height: int | None
    block_time: datetime | None
    first_seen_at: datetime
    fee_sats: int | None
    size_vbytes: int | None
    is_coinjoin_suspected: bool

    def __post_init__(self) -> None:
        if not self.txid:
            raise ValueError("OnChainTransaction.txid is required")
        if len(self.txid) != 64:
            raise ValueError("OnChainTransaction.txid must be a 64-char hex string")
        if self.fee_sats is not None and self.fee_sats < 0:
            raise ValueError("OnChainTransaction.fee_sats must be >= 0")
        if self.size_vbytes is not None and self.size_vbytes < 0:
            raise ValueError("OnChainTransaction.size_vbytes must be >= 0")
        if self.confirmation_height is not None and self.confirmation_height < 0:
            raise ValueError("confirmation_height must be >= 0")
