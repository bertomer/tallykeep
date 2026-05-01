"""SweepPolicy + SweepExecution + safety warnings (spec module 02 / 07).

Generalized: applies between any two Holdings. The safety validator runs on create /
modify and computes warnings; the policy cannot be enabled until all warnings are
acknowledged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from tallykeep.domain.enums import (
    SafetyWarningKind,
    SafetyWarningSeverity,
    SweepExecutionStatus,
    SweepTriggerType,
)


@dataclass
class ScheduledTriggerConfiguration:
    cron_expression: str
    timezone: str  # IANA timezone


@dataclass
class ThresholdTriggerConfiguration:
    threshold_sats: int
    cooldown_hours: int  # avoid flapping


@dataclass
class SafetyWarning:
    kind: SafetyWarningKind
    severity: SafetyWarningSeverity
    message: str  # user-facing explanation
    user_acknowledged: bool


@dataclass
class SweepPolicy:
    id: UUID
    name: str
    source_holding_id: UUID
    destination_holding_id: UUID
    is_enabled: bool
    trigger_type: SweepTriggerType
    # `trigger_configuration` is shape-dependent on trigger_type; we keep it as a dict
    # at the domain layer and validate against the trigger-type-specific dataclasses
    # in the service layer.
    trigger_configuration: dict[str, Any]
    minimum_balance_sats: int  # leave this much on the source
    maximum_per_period_sats: int | None  # safety cap; None = no cap (warn-worthy)
    requires_user_confirmation: bool
    safety_warnings: list[SafetyWarning] = field(default_factory=list)
    last_executed_at: datetime | None = None
    last_result_summary: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.source_holding_id == self.destination_holding_id:
            raise ValueError(
                "SweepPolicy source_holding_id and destination_holding_id must differ"
            )
        if self.minimum_balance_sats < 0:
            raise ValueError("SweepPolicy.minimum_balance_sats must be >= 0")
        if self.maximum_per_period_sats is not None and self.maximum_per_period_sats < 0:
            raise ValueError("SweepPolicy.maximum_per_period_sats must be >= 0")

        # Spec module 02 invariant 5: policy cannot be enabled while warnings remain
        # unacknowledged. We enforce this whenever is_enabled flips True.
        if self.is_enabled:
            unacked = [w for w in self.safety_warnings if not w.user_acknowledged]
            if unacked:
                kinds = ", ".join(w.kind.value for w in unacked)
                raise ValueError(
                    f"SweepPolicy cannot be enabled with unacknowledged warnings: {kinds}"
                )


@dataclass
class SweepExecution:
    """Audit trail. Persist-first half of the persist-first-emit-second pattern."""

    id: UUID
    sweep_policy_id: UUID
    triggered_at: datetime
    trigger_source: SweepTriggerType
    pre_balance_sats: int
    intended_amount_sats: int
    status: SweepExecutionStatus
    provider_withdrawal_id: str | None
    expected_txid: str | None
    confirmed_txid: str | None
    error_message: str | None
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if self.pre_balance_sats < 0:
            raise ValueError("SweepExecution.pre_balance_sats must be >= 0")
        if self.intended_amount_sats < 0:
            raise ValueError("SweepExecution.intended_amount_sats must be >= 0")
