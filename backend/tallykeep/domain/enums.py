"""Domain enums.

Mirrors spec module 02 exactly. Values are the canonical strings used in the database
and on the wire — do not rename without a database migration and an API version bump.
"""

from __future__ import annotations

from enum import Enum


class Purpose(str, Enum):
    SPENDING = "spending"
    RESERVE = "reserve"
    LONG_TERM = "long_term"
    TRANSIT = "transit"
    UNDECLARED = "undeclared"


class CustodyModel(str, Enum):
    THIRD_PARTY = "third_party"
    SELF_SINGLE = "self_single"
    SELF_MULTISIG = "self_multisig"


class SigningModel(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    SOFTWARE_HOT = "software_hot"
    HARDWARE_OFFLINE = "hardware_offline"
    AIRGAPPED = "airgapped"
    CEREMONIAL = "ceremonial"
    UNKNOWN = "unknown"  # only ever appears on the observable side


class HoldingType(str, Enum):
    ACCOUNT = "account"
    PURSE = "purse"
    STRONGBOX = "strongbox"
    VAULT = "vault"


class Network(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"
    SIGNET = "signet"
    REGTEST = "regtest"


class AddressType(str, Enum):
    LEGACY = "legacy"
    NESTED_SEGWIT = "nested_segwit"
    NATIVE_SEGWIT = "native_segwit"
    TAPROOT = "taproot"


class HygieneFlag(str, Enum):
    ADDRESS_REUSED = "address_reused"
    DUST = "dust"
    SUSPECTED_CONSOLIDATION = "suspected_consolidation"
    ROUND_NUMBER = "round_number"


class ProviderKind(str, Enum):
    EXCHANGE = "exchange"
    BROKER = "broker"
    P2P_VENUE = "p2p_venue"


class Direction(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    INTERNAL = "internal"


class LedgerEntrySource(str, Enum):
    ONCHAIN_TRANSACTION = "onchain_transaction"
    LIGHTNING_PAYMENT = "lightning_payment"
    CUSTODIAL_EVENT = "custodial_event"


class LedgerCategory(str, Enum):
    # Incoming
    CUSTODIAL_WITHDRAWAL = "custodial_withdrawal"
    P2P_RECEIVE = "p2p_receive"
    SALARY = "salary"
    MERCHANT_RECEIPT = "merchant_receipt"
    # Outgoing
    MERCHANT_PAYMENT = "merchant_payment"
    P2P_SEND = "p2p_send"
    CUSTODIAL_DEPOSIT = "custodial_deposit"
    # Neutral
    INTERNAL_TRANSFER = "internal_transfer"
    CONSOLIDATION = "consolidation"
    # Fallback
    OTHER = "other"


class PaymentType(str, Enum):
    ONCHAIN = "onchain"
    LIGHTNING = "lightning"  # v1.5


class PaymentStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_SIGNATURE = "awaiting_signature"
    AWAITING_BROADCAST = "awaiting_broadcast"
    BROADCAST = "broadcast"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InvoiceStatus(str, Enum):
    OPEN = "open"
    PAID = "paid"
    OVERPAID = "overpaid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SweepTriggerType(str, Enum):
    SCHEDULED = "scheduled"
    THRESHOLD = "threshold"
    MANUAL = "manual"


class SafetyWarningKind(str, Enum):
    DESTINATION_KEYS_ON_HOST = "destination_keys_on_host"
    DESTINATION_IS_CUSTODIAL = "destination_is_custodial"
    SOURCE_AND_DESTINATION_SAME_SECURITY_TIER = "same_security_tier"
    NO_MAXIMUM_CAP_SET = "no_maximum_cap_set"
    UNVERIFIED_WHITELIST_ON_PROVIDER = "unverified_whitelist_on_provider"


class SafetyWarningSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SweepExecutionStatus(str, Enum):
    REQUESTED = "requested"
    AWAITING_USER_CONFIRMATION = "awaiting_user_confirmation"
    DISPATCHED = "dispatched"
    ONCHAIN_PENDING = "onchain_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PurseSeedOrigin(str, Enum):
    EXTERNAL_WATCH_ONLY = "external_watch_only"
    TALLYKEEP_MANAGED = "tallykeep_managed"


class DiscrepancyKind(str, Enum):
    """Spec module 02 + 05 — declared-vs-observable security analysis."""

    CLAIMED_MULTISIG_BUT_SINGLE_KEY = "claimed_multisig_but_single_key"
    CLAIMED_SINGLE_BUT_OBSERVABLE_MULTISIG = "claimed_single_but_observable_multisig"
    CLAIMED_OFFLINE_BUT_PATTERN_SUGGESTS_HOT = "claimed_offline_but_pattern_suggests_hot"
    CLAIMED_VAULT_NO_TIMELOCK_NO_MULTISIG = "claimed_vault_no_timelock_no_multisig"
    CLAIMED_INHERITANCE_NO_RECOVERY_PATH = "claimed_inheritance_no_recovery_path"


class DiscrepancySeverity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
