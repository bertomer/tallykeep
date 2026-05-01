"""PaymentRequest domain type (spec module 02 / 06).

A user-initiated outgoing payment, in lifecycle from draft to confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import PaymentStatus, PaymentType


@dataclass
class PaymentRequest:
    id: UUID
    holding_id: UUID  # source Holding
    payment_type: PaymentType
    amount_sats: int | None  # None = encoded in destination (e.g. BOLT11)
    description: str | None
    status: PaymentStatus
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # On-chain destination
    destination_address: str | None = None
    bip21_uri: str | None = None
    psbt_base64: str | None = None
    signed_transaction_hex: str | None = None
    broadcast_txid: str | None = None

    # Lightning destination (v1.5)
    lightning_invoice: str | None = None
    lightning_payment_hash: str | None = None

    # Realized movement reference. Populated by the chain scanner once the broadcast
    # txid lands in a block. Spec module 06.
    resulting_ledger_entry_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.amount_sats is not None and self.amount_sats <= 0:
            raise ValueError("PaymentRequest.amount_sats must be > 0 when provided")

        if self.payment_type == PaymentType.ONCHAIN:
            if self.lightning_invoice is not None or self.lightning_payment_hash is not None:
                raise ValueError(
                    "Onchain PaymentRequest cannot carry Lightning invoice fields"
                )
            # destination_address may be None during DRAFT; once status > DRAFT the
            # service layer guarantees it. Domain-level we only forbid lightning fields.
        elif self.payment_type == PaymentType.LIGHTNING:
            if self.psbt_base64 is not None or self.signed_transaction_hex is not None:
                raise ValueError(
                    "Lightning PaymentRequest cannot carry on-chain PSBT fields"
                )
            if self.broadcast_txid is not None:
                raise ValueError(
                    "Lightning PaymentRequest cannot carry an on-chain broadcast_txid"
                )
