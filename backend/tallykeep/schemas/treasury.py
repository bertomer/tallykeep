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


class AccountValidateIn(BaseModel):
    """Request body for POST /holdings/account/validate.

    Validates API credentials against the provider without any DB writes.
    The wizard calls this on Step 1 "Continue"; only Step 2 "Looks right"
    calls the create endpoint.
    """

    model_config = _Strict

    adapter_id: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    api_passphrase: str | None = None


class AccountValidateOut(BaseModel):
    """Response for POST /holdings/account/validate — balance preview, no holding created."""

    adapter_id: str
    btc_balance_sats: int
    other_asset_tickers: list[str]
    other_asset_total_count: int


class CustodialProviderInput(BaseModel):
    """Embedded in AccountCreate (2-key model, ADR-0011).

    The read-only-only wizard captures only the provider identity and the
    read-only API credentials. Whitelist fields are not present at this stage —
    they are populated by the withdrawal sub-flow (future iteration).
    """

    model_config = _Strict

    provider_kind: ProviderKind
    display_name: str = Field(..., min_length=1, max_length=100)
    adapter_id: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    api_passphrase: str | None = None


class OtherAssetEntry(BaseModel):
    asset: str
    amount: str


class AccountCreateOut(BaseModel):
    """Response for POST /holdings/account — includes the wizard's initial poll data."""

    holding_id: UUID
    provider_id: UUID
    name: str
    adapter_id: str
    display_name: str
    btc_balance_sats: int
    # Top-3 non-BTC assets by alphabetical order + total count.
    other_asset_tickers: list[str]
    other_asset_total_count: int


# --- CustodialProvider CRUD ----------------------------------------------------


class CustodialProviderOut(BaseModel):
    id: UUID
    holding_id: UUID
    provider_kind: ProviderKind
    display_name: str
    adapter_id: str
    can_read: bool
    can_withdraw: bool
    # Nullable: populated by the withdrawal sub-flow (ADR-0011).
    whitelist_address: str | None
    whitelist_address_descriptor_id: UUID | None
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
