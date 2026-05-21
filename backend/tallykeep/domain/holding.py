"""Holding domain types — Account, Purse, Strongbox, Vault.

Per spec module 02: Holdings are the primary organizational unit. Account is backed by
a CustodialProvider; Purse / Strongbox / Vault are backed by Descriptors.

Invariants enforced at construction time (`__post_init__`):

- Account has no Descriptors.
- Purse / Strongbox / Vault have at least one Descriptor and no CustodialProvider.
- Vault may have multisig parameters; Purse and Strongbox should not.

No domain entity exposes a private key, seed, or signing material — enforced
structurally (no field for it). This is the central security commitment from
spec module 03.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import (
    CustodyModel,
    HoldingType,
    Purpose,
    PurseMode,
    SigningModel,
)


@dataclass
class SecurityClaim:
    """User-declared description of how a Holding is protected.

    The analyzer (module 05) separately computes `ObservableSecurity` from the on-chain
    reality and surfaces discrepancies. SecurityClaim is freely user-mutable.
    """

    custody_model: CustodyModel
    signing_model: SigningModel
    geographic_distribution: bool = False
    inheritance_configured: bool = False
    notes: str | None = None


@dataclass
class Holding:
    """Common shape for all Holdings. Concrete subtypes carry the differentiator.

    Not abstract in the strict sense — we use a discriminator (`holding_type`) plus
    type-specific fields, so the Python type can be deserialized from the database
    without a class hierarchy. Concrete factories are at the module bottom.
    """

    id: UUID
    holding_type: HoldingType
    name: str
    description: str | None
    purpose: Purpose
    declared_security: SecurityClaim
    display_color: str  # hex, e.g. "#10b981"
    display_order: int
    created_at: datetime
    updated_at: datetime

    # Subtype-specific. Only one of these is meaningful per holding_type.
    custodial_provider_id: UUID | None = None  # account only

    descriptor_ids: list[UUID] = field(default_factory=list)  # purse / strongbox / vault

    # Purse metadata
    purse_mode: PurseMode | None = None

    # Strongbox metadata
    signing_device_label: str | None = None
    vendor: str | None = None
    signing_metadata_present: bool | None = None

    # Vault metadata
    required_signers: int | None = None
    total_signers: int | None = None
    timelock_kind: str | None = None    # "cltv" | "csv" | None
    timelock_value: int | None = None   # block height (CLTV) or count (CSV)
    recovery_setup_notes: str | None = None

    def __post_init__(self) -> None:
        # Spec module 02 invariants:
        #
        # 1. Account has no Descriptors and exactly one CustodialProvider.
        # 2. Purse / Strongbox / Vault have at least one Descriptor and no
        #    CustodialProvider.
        # 3. Strongbox optionally has signing_device_label; Purse / Vault should not.
        # 4. Vault may have multisig parameters; Purse / Strongbox should not.

        if self.holding_type == HoldingType.ACCOUNT:
            if self.descriptor_ids:
                raise ValueError("Account holdings cannot have descriptors")
            if self.custodial_provider_id is None:
                raise ValueError("Account holdings require a CustodialProvider id")
            if self.declared_security.signing_model != SigningModel.NOT_APPLICABLE:
                raise ValueError(
                    "Account holdings must declare signing_model=NOT_APPLICABLE"
                )
            if self.declared_security.custody_model != CustodyModel.THIRD_PARTY:
                raise ValueError(
                    "Account holdings must declare custody_model=THIRD_PARTY"
                )
            self._reject_vault_metadata()
            self._reject_strongbox_metadata()
        else:
            if not self.descriptor_ids:
                raise ValueError(
                    f"{self.holding_type.value} holdings require at least one descriptor"
                )
            if self.custodial_provider_id is not None:
                raise ValueError(
                    f"{self.holding_type.value} holdings cannot have a CustodialProvider"
                )
            if self.declared_security.signing_model == SigningModel.NOT_APPLICABLE:
                raise ValueError(
                    f"{self.holding_type.value} holdings cannot declare "
                    f"signing_model=NOT_APPLICABLE"
                )
            if self.declared_security.custody_model == CustodyModel.THIRD_PARTY:
                raise ValueError(
                    f"{self.holding_type.value} holdings cannot declare "
                    f"custody_model=THIRD_PARTY"
                )

        if self.holding_type != HoldingType.STRONGBOX:
            if self.signing_device_label is not None:
                raise ValueError("signing_device_label is only valid on Strongbox holdings")
            if self.vendor is not None:
                raise ValueError("vendor is only valid on Strongbox holdings")
            if self.signing_metadata_present is not None:
                raise ValueError("signing_metadata_present is only valid on Strongbox holdings")

        if self.holding_type != HoldingType.VAULT:
            self._reject_vault_metadata()
        else:
            self._validate_vault_metadata()

    # ---- helpers ---------------------------------------------------------------

    def _reject_vault_metadata(self) -> None:
        if (
            self.required_signers is not None
            or self.total_signers is not None
            or self.timelock_kind is not None
            or self.timelock_value is not None
            or self.recovery_setup_notes is not None
        ):
            raise ValueError(
                "Vault metadata (required_signers, total_signers, timelock_kind, "
                "timelock_value, recovery_setup_notes) only valid on Vault holdings"
            )

    def _reject_strongbox_metadata(self) -> None:
        if self.signing_device_label is not None:
            raise ValueError("signing_device_label is only valid on Strongbox holdings")
        if self.vendor is not None:
            raise ValueError("vendor is only valid on Strongbox holdings")
        if self.signing_metadata_present is not None:
            raise ValueError("signing_metadata_present is only valid on Strongbox holdings")

    def _validate_vault_metadata(self) -> None:
        # Either both signer fields set, or neither.
        if (self.required_signers is None) != (self.total_signers is None):
            raise ValueError(
                "Vault required_signers and total_signers must be set together "
                "or both omitted"
            )
        if self.required_signers is not None and self.total_signers is not None:
            if self.required_signers < 1:
                raise ValueError("Vault required_signers must be >= 1")
            if self.total_signers < self.required_signers:
                raise ValueError(
                    "Vault total_signers must be >= required_signers"
                )
        valid_timelock_kinds = {None, "cltv", "csv"}
        if self.timelock_kind not in valid_timelock_kinds:
            raise ValueError(
                f"Vault timelock_kind must be one of {valid_timelock_kinds}, "
                f"got {self.timelock_kind!r}"
            )
        if self.timelock_kind is not None and self.timelock_value is None:
            raise ValueError(
                "Vault timelock_value must be set when timelock_kind is not None"
            )
        if self.timelock_value is not None and self.timelock_value < 0:
            raise ValueError("Vault timelock_value must be >= 0")
