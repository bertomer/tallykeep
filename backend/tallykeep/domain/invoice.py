"""Invoice domain type (spec module 02 / 06).

A user-generated request for an incoming payment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import InvoiceStatus, PaymentType


@dataclass
class Invoice:
    id: UUID
    holding_id: UUID  # destination Holding
    invoice_type: PaymentType  # ONCHAIN or LIGHTNING (v1.5)
    amount_sats: int | None  # None = amountless
    description: str | None
    status: InvoiceStatus
    expires_at: datetime | None
    created_at: datetime

    # On-chain
    receiving_address: str | None = None
    receiving_address_id: UUID | None = None
    bip21_uri: str | None = None

    # Lightning (v1.5)
    bolt11: str | None = None
    payment_hash: str | None = None

    # Same persistent link as PaymentRequest; populated when payment is detected.
    resulting_ledger_entry_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.amount_sats is not None and self.amount_sats <= 0:
            raise ValueError("Invoice.amount_sats must be > 0 when provided")

        if self.invoice_type == PaymentType.ONCHAIN:
            if self.bolt11 is not None or self.payment_hash is not None:
                raise ValueError("Onchain Invoice cannot carry Lightning fields")
        elif self.invoice_type == PaymentType.LIGHTNING:
            if self.receiving_address is not None or self.bip21_uri is not None:
                raise ValueError(
                    "Lightning Invoice cannot carry on-chain receiving_address or "
                    "bip21_uri"
                )
