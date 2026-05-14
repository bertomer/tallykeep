"""Pydantic schemas for /api/v1/holdings/account, /custodial-providers,
/sweep-policies, and /sweep-executions (spec module 04 / 07 / M8).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tallykeep.domain.enums import (
    ProviderKind,
    SafetyWarningKind,
    SafetyWarningSeverity,
    SweepExecutionStatus,
    SweepTriggerType,
)


_Strict = ConfigDict(extra="forbid")


# --- Account Holding creation ---------------------------------------------------


class CustodialProviderInput(BaseModel):
    """Embedded in AccountCreate; wired to CustodialProvider at creation time."""

    model_config = _Strict

    provider_kind: ProviderKind
    display_name: str = Field(..., min_length=1, max_length=100)
    adapter_id: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    api_passphrase: str | None = None
    whitelist_address: str = Field(..., min_length=10, max_length=100)
    whitelist_address_descriptor_id: UUID


# --- CustodialProvider CRUD ----------------------------------------------------


class CustodialProviderOut(BaseModel):
    id: UUID
    holding_id: UUID
    provider_kind: ProviderKind
    display_name: str
    adapter_id: str
    can_read: bool
    can_withdraw: bool
    whitelist_address: str
    whitelist_address_descriptor_id: UUID
    whitelist_verified: bool
    is_active: bool
    last_polled_at: datetime | None
    last_error: str | None
    last_known_balance_sats: int | None
    created_at: datetime
    updated_at: datetime


class PatchCustodialProviderRequest(BaseModel):
    model_config = _Strict

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None


class BalanceOut(BaseModel):
    provider_id: UUID
    balance_sats: int
    last_polled_at: datetime | None


class WhitelistVerificationOut(BaseModel):
    provider_id: UUID
    address: str
    is_whitelisted: bool
    provider_label: str | None = None
    error: str | None = None


# --- SweepPolicy CRUD ----------------------------------------------------------


class SafetyWarningOut(BaseModel):
    kind: SafetyWarningKind
    severity: SafetyWarningSeverity
    message: str
    user_acknowledged: bool


class SweepPolicyCreate(BaseModel):
    model_config = _Strict

    name: str = Field(..., min_length=1, max_length=100)
    source_holding_id: UUID
    destination_holding_id: UUID
    trigger_type: SweepTriggerType
    trigger_configuration: dict[str, Any]
    minimum_balance_sats: int = Field(default=0, ge=0)
    maximum_per_period_sats: int | None = Field(default=None, ge=0)
    requires_user_confirmation: bool = True
    is_dry_run: bool = False


class SweepPolicyPatch(BaseModel):
    model_config = _Strict

    name: str | None = Field(default=None, min_length=1, max_length=100)
    trigger_type: SweepTriggerType | None = None
    trigger_configuration: dict[str, Any] | None = None
    minimum_balance_sats: int | None = Field(default=None, ge=0)
    maximum_per_period_sats: int | None = Field(default=None, ge=0)
    requires_user_confirmation: bool | None = None
    is_dry_run: bool | None = None


class SweepPolicyOut(BaseModel):
    id: UUID
    name: str
    source_holding_id: UUID
    destination_holding_id: UUID
    is_enabled: bool
    trigger_type: SweepTriggerType
    trigger_configuration: dict[str, Any]
    minimum_balance_sats: int
    maximum_per_period_sats: int | None
    requires_user_confirmation: bool
    is_dry_run: bool
    safety_warnings: list[SafetyWarningOut]
    last_executed_at: datetime | None
    last_result_summary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


# --- SweepExecution ------------------------------------------------------------


class SweepExecutionOut(BaseModel):
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
