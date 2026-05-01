"""ObservableSecurity + Discrepancy (spec module 02 / 05).

The analyzer computes ObservableSecurity from on-chain reality and the configured
Descriptors. ObservableSecurity is *not* a stored field on Holding — it is a derived
view, recomputed on demand and surfaced via /api/v1/analysis endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import (
    CustodyModel,
    DiscrepancyKind,
    DiscrepancySeverity,
    SigningModel,
)


@dataclass
class ObservableSecurity:
    holding_id: UUID
    inferred_custody_model: CustodyModel
    inferred_signing_model: SigningModel  # may be UNKNOWN
    inferred_multisig_parameters: tuple[int, int] | None  # (required, total)
    inferred_timelock_blocks: int | None
    last_computed_at: datetime


@dataclass
class Discrepancy:
    holding_id: UUID
    kind: DiscrepancyKind
    severity: DiscrepancySeverity
    message: str
    first_detected_at: datetime
    user_acknowledged: bool = False
