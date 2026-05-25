"""SQLAlchemy ORM models — persistence concern only.

Each model row class ends with `Row` to keep them visually distinct from the domain
dataclass with the same conceptual name. Mapping between the two layers is done in
the repositories.
"""

from tallykeep.models.base import Base
from tallykeep.models.custodial_ledger_entry import CustodialLedgerEntryRow
from tallykeep.models.security_health_item import SecurityHealthItemRow
from tallykeep.models.custodial_provider import CustodialProviderRow
from tallykeep.models.descriptor import AddressRow, DescriptorRow, UTXORow
from tallykeep.models.holding import HoldingRow, HoldingTypeChangeLogRow
from tallykeep.models.invoice import InvoiceRow
from tallykeep.models.ledger_entry import LedgerEntryHoldingLinkRow, LedgerEntryRow
from tallykeep.models.onchain_transaction import OnChainTransactionRow
from tallykeep.models.paired_device import PairedDeviceRow
from tallykeep.models.payment_request import BroadcastAttemptRow, PaymentRequestRow
from tallykeep.models.sweep import SweepExecutionRow, SweepPolicyRow
from tallykeep.models.user_profile import (
    CryptoParametersRow,
    EventEmissionLogRow,
    JobRow,
    RuntimeConfigurationRow,
    SecretRow,
    UserProfileRow,
)

# This list is what Alembic's autogenerate sees. Adding a new model? Import it here.
__all__ = [
    "Base",
    "UserProfileRow",
    "RuntimeConfigurationRow",
    "CryptoParametersRow",
    "SecretRow",
    "EventEmissionLogRow",
    "JobRow",
    "HoldingRow",
    "HoldingTypeChangeLogRow",
    "DescriptorRow",
    "AddressRow",
    "UTXORow",
    "CustodialLedgerEntryRow",
    "CustodialProviderRow",
    "OnChainTransactionRow",
    "LedgerEntryRow",
    "LedgerEntryHoldingLinkRow",
    "PaymentRequestRow",
    "BroadcastAttemptRow",
    "InvoiceRow",
    "SweepPolicyRow",
    "SweepExecutionRow",
    "PairedDeviceRow",
    "SecurityHealthItemRow",
]
