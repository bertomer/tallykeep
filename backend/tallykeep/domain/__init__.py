"""Domain types for TallyKeep.

Pure dataclasses with construction-time invariants. Persistence (`models/`), API I/O
(`schemas/`), and behavior (`services/`) live in sibling packages — the domain depends
on none of them.
"""

from tallykeep.domain.custodial_provider import (
    CustodialProvider,
    ProviderPermissions,
)
from tallykeep.domain.descriptor import Address, Descriptor, UTXO
from tallykeep.domain.enums import (
    AddressType,
    CustodyModel,
    Direction,
    DiscrepancyKind,
    DiscrepancySeverity,
    HoldingType,
    HygieneFlag,
    InvoiceStatus,
    JobStatus,
    LedgerCategory,
    LedgerEntrySource,
    Network,
    PaymentStatus,
    PaymentType,
    ProviderKind,
    Purpose,
    SafetyWarningKind,
    SafetyWarningSeverity,
    SigningModel,
    SweepExecutionStatus,
    SweepTriggerType,
)
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.domain.invoice import Invoice
from tallykeep.domain.job import Job
from tallykeep.domain.ledger_entry import (
    LedgerEntry,
    LedgerEntryHoldingLink,
    OnChainTransaction,
)
from tallykeep.domain.observable_security import Discrepancy, ObservableSecurity
from tallykeep.domain.payment_request import PaymentRequest
from tallykeep.domain.sweep_policy import (
    SafetyWarning,
    ScheduledTriggerConfiguration,
    SweepExecution,
    SweepPolicy,
    ThresholdTriggerConfiguration,
)
from tallykeep.domain.user_profile import USER_PROFILE_SINGLETON_ID, UserProfile

__all__ = [
    # Holdings
    "Holding",
    "HoldingType",
    "SecurityClaim",
    "CustodyModel",
    "SigningModel",
    "Purpose",
    # Descriptor + chain
    "Descriptor",
    "Address",
    "UTXO",
    "Network",
    "AddressType",
    "HygieneFlag",
    # Custodial
    "CustodialProvider",
    "ProviderKind",
    "ProviderPermissions",
    # Ledger
    "LedgerEntry",
    "LedgerEntryHoldingLink",
    "OnChainTransaction",
    "Direction",
    "LedgerEntrySource",
    "LedgerCategory",
    # Banking
    "PaymentRequest",
    "PaymentStatus",
    "PaymentType",
    "Invoice",
    "InvoiceStatus",
    # Trading
    "SweepPolicy",
    "SweepExecution",
    "SweepTriggerType",
    "ScheduledTriggerConfiguration",
    "ThresholdTriggerConfiguration",
    "SafetyWarning",
    "SafetyWarningKind",
    "SafetyWarningSeverity",
    "SweepExecutionStatus",
    # Job
    "Job",
    "JobStatus",
    # User profile
    "UserProfile",
    "USER_PROFILE_SINGLETON_ID",
    # Analysis
    "ObservableSecurity",
    "Discrepancy",
    "DiscrepancyKind",
    "DiscrepancySeverity",
]
