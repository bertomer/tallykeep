"""Pydantic schemas for /api/v1/holdings.

The four per-type creation schemas (Account, Purse, Strongbox, Vault) inherit
from a common base. Account is the only one that takes a `custodial_provider`
sub-object instead of a `descriptors` list — Account has no descriptors per
spec module 02.

CustodialProvider creation lands in M8 alongside the actual ccxt integration;
the M4 Account-creation endpoint will return 501 with a milestone tag pointing
the caller at M8.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tallykeep.schemas.trading import CustodialProviderInput
from tallykeep.domain.enums import (
    AddressType,
    CustodyModel,
    HoldingType,
    Network,
    Purpose,
    SigningModel,
)


_StrictBase = ConfigDict(extra="forbid")


# --- inputs: nested types ---------------------------------------------------


class SecurityClaimInput(BaseModel):
    model_config = _StrictBase

    custody_model: CustodyModel
    signing_model: SigningModel
    geographic_distribution: bool = False
    inheritance_configured: bool = False
    notes: str | None = None


class DescriptorInput(BaseModel):
    """Single descriptor specification at holding-creation time.

    `gap_limit` is the number of consecutive unused addresses we derive when
    importing a descriptor. The BIP 44 standard is 20 (also the BDK / Sparrow
    / Electrum default); capped at 40 (2× the standard) to leave headroom for
    power users who've issued a few extra addresses outside the app, without
    inviting nonsense workflows that pre-derive thousands of addresses. Users
    who've issued addresses far past the default gap need a manual-address-
    registration path — deferred to v2 (see CONTEXT.md).
    """

    model_config = _StrictBase

    name: str = Field(..., min_length=1, max_length=100)
    expression: str = Field(..., min_length=1, max_length=4096)
    change_expression: str | None = Field(default=None, max_length=4096)
    network: Network
    gap_limit: int = Field(default=20, ge=1, le=40)


# --- inputs: per-type creation requests --------------------------------------


class _HoldingCreateBase(BaseModel):
    model_config = _StrictBase

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    purpose: Purpose
    declared_security: SecurityClaimInput
    display_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    display_order: int = Field(default=0, ge=0)


class PurseCreate(_HoldingCreateBase):
    descriptors: list[DescriptorInput] = Field(..., min_length=1)


class StrongboxCreate(_HoldingCreateBase):
    descriptors: list[DescriptorInput] = Field(..., min_length=1)
    signing_device_label: str | None = Field(default=None, max_length=200)


class VaultCreate(_HoldingCreateBase):
    descriptors: list[DescriptorInput] = Field(..., min_length=1)
    required_signers: int | None = Field(default=None, ge=1)
    total_signers: int | None = Field(default=None, ge=1)
    timelock_blocks: int | None = Field(default=None, ge=0)
    recovery_setup_notes: str | None = Field(default=None, max_length=2000)


class AccountCreate(_HoldingCreateBase):
    custodial_provider: CustodialProviderInput


# --- inputs: management ------------------------------------------------------


class HoldingUpdate(BaseModel):
    model_config = _StrictBase

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    purpose: Purpose | None = None
    declared_security: SecurityClaimInput | None = None
    display_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    display_order: int | None = Field(default=None, ge=0)


class ChangeTypeRequest(BaseModel):
    model_config = _StrictBase

    new_type: HoldingType
    reason: str | None = Field(default=None, max_length=2000)


# --- responses ---------------------------------------------------------------


class SecurityClaimResponse(BaseModel):
    custody_model: CustodyModel
    signing_model: SigningModel
    geographic_distribution: bool
    inheritance_configured: bool
    notes: str | None = None


class HoldingResponse(BaseModel):
    """Single nested response that covers all four subtypes.

    Subtype-specific fields are present only when applicable (None otherwise),
    so a frontend can render any holding from this single shape.
    """

    id: UUID
    holding_type: HoldingType
    name: str
    description: str | None
    purpose: Purpose
    declared_security: SecurityClaimResponse
    display_color: str
    display_order: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    descriptor_ids: list[UUID]
    custodial_provider_id: UUID | None = None

    # Strongbox
    signing_device_label: str | None = None

    # Vault
    required_signers: int | None = None
    total_signers: int | None = None
    timelock_blocks: int | None = None
    recovery_setup_notes: str | None = None


class DescriptorResponse(BaseModel):
    id: UUID
    holding_id: UUID
    name: str
    expression: str
    change_expression: str | None
    network: Network
    address_type: AddressType
    gap_limit: int
    is_watch_only: bool
    last_scanned_height: int
    created_at: datetime


class AddressResponse(BaseModel):
    id: UUID
    descriptor_id: UUID
    address: str
    derivation_path: str
    is_change: bool
    derivation_index: int
    label: str | None
    first_seen_height: int | None
    is_reused: bool


class AddressListResponse(BaseModel):
    addresses: list[AddressResponse]


class NextReceivingAddressResponse(BaseModel):
    address: str
    derivation_path: str
    derivation_index: int
