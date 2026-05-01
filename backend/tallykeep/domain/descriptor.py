"""Descriptor, Address, UTXO domain types (spec module 02).

Descriptor is the BIP 380 output descriptor that backs a Purse, Strongbox, or Vault
Holding. v1 supports only watch-only single-key descriptors; the validator may parse
multisig descriptors but BDK construction of multisig PSBTs is deferred to v2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import AddressType, HygieneFlag, Network


@dataclass
class Descriptor:
    id: UUID
    holding_id: UUID
    name: str
    expression: str  # BIP 380 output descriptor (external chain)
    change_expression: str | None
    network: Network
    address_type: AddressType
    gap_limit: int
    is_watch_only: bool  # always True in v1; enforced below
    last_scanned_height: int
    created_at: datetime

    def __post_init__(self) -> None:
        # Central security commitment: the app never holds private keys. v1
        # descriptors are always watch-only.
        if not self.is_watch_only:
            raise ValueError("Descriptor must be watch-only in v1")
        if self.gap_limit < 1:
            raise ValueError("Descriptor gap_limit must be >= 1")
        if self.last_scanned_height < 0:
            raise ValueError("last_scanned_height must be >= 0")
        if not self.expression:
            raise ValueError("Descriptor expression cannot be empty")


@dataclass
class Address:
    id: UUID
    descriptor_id: UUID
    address: str
    derivation_path: str  # e.g. "m/84'/0'/0'/0/5"
    is_change: bool
    derivation_index: int
    label: str | None
    first_seen_height: int | None
    is_reused: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if self.derivation_index < 0:
            raise ValueError("Address derivation_index must be >= 0")


@dataclass
class UTXO:
    id: UUID
    descriptor_id: UUID
    address_id: UUID
    txid: str
    vout: int
    value_sats: int
    confirmation_height: int | None  # None = unconfirmed
    is_frozen: bool
    is_spent: bool
    spent_in_txid: str | None
    hygiene_flags: list[HygieneFlag] = field(default_factory=list)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.value_sats < 0:
            raise ValueError("UTXO value_sats must be >= 0")
        if self.vout < 0:
            raise ValueError("UTXO vout must be >= 0")
        if self.is_spent and self.spent_in_txid is None:
            raise ValueError("Spent UTXO must record spent_in_txid")
        if not self.is_spent and self.spent_in_txid is not None:
            raise ValueError("Unspent UTXO must not have spent_in_txid")
