"""CustodialProviderAdapter ABC — spec module 07.

Anti-corruption layer between TallyKeep's domain model and exchange APIs
(ccxt-backed in first-class providers, custom in future providers).

All amounts are in sats (int). BTC↔sats conversion lives in each concrete
adapter so the domain layer never sees BTC floats.

Adapters are synchronous: the rest of the service layer is synchronous, and
ccxt provides a sync interface alongside its async one. Use ccxt's sync
exchange classes (ccxt.kraken, not ccxt.async_support.kraken).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from tallykeep.domain.custodial_provider import ProviderPermissions


# --- Data transfer types --------------------------------------------------------


@dataclass
class Withdrawal:
    id: str
    amount_sats: int
    address: str
    txid: str | None
    status: str  # "pending" | "completed" | "failed"
    created_at: datetime


@dataclass
class Deposit:
    id: str
    amount_sats: int
    txid: str | None
    status: str  # "pending" | "completed" | "failed"
    created_at: datetime


@dataclass
class WithdrawalResult:
    withdrawal_id: str
    status: str  # "pending" | "completed"


@dataclass
class WhitelistVerification:
    is_whitelisted: bool
    provider_label: str | None = None  # provider's name for the address
    error: str | None = None            # reason if is_whitelisted=False and provider was contacted


# --- Exceptions -----------------------------------------------------------------


class ProviderAuthError(RuntimeError):
    """API credentials are invalid or expired."""


class ProviderPermissionError(RuntimeError):
    """The API key lacks a required permission."""


class ProviderRateLimitError(RuntimeError):
    """Provider is rate-limiting requests."""


class ProviderError(RuntimeError):
    """Generic exchange-side error (network, maintenance, unexpected response)."""


# --- Abstract base --------------------------------------------------------------


class CustodialProviderAdapter(ABC):
    """Anti-corruption layer for custodial exchange APIs (spec module 07).

    Each concrete implementation absorbs per-provider API quirks so that
    TallyKeep's service layer never sees ccxt directly.

    Class-level capability declarations (ADR-0011): every adapter declares its
    provider's capabilities so the treasury providers endpoint can surface them
    without instantiating an adapter (which requires live credentials).
    """

    # --- Capability matrix (class-level; override in each adapter) --------------

    #: Provider slug — matches the adapter_id in the registry.
    adapter_slug: str = ""
    #: Human-readable name shown in the UI.
    display_name: str = ""
    #: Provider supports a withdrawal-key API (drives Step 3 suggestion card).
    supports_withdrawal_keys: bool = False
    #: Provider exposes a programmatic address-whitelist read API.
    whitelist_read_api: bool = False

    # --- Abstract interface -------------------------------------------------------

    @abstractmethod
    def get_permissions(self) -> ProviderPermissions:
        """Verify API key access and detect unwanted permissions.

        Raises ProviderAuthError if the key is invalid.
        Raises ProviderPermissionError if required read access is missing.
        Returns ProviderPermissions where can_trade=True indicates the key
        has trade permissions (registration must be rejected by the caller).
        """
        ...

    @abstractmethod
    def get_balance(self) -> int:
        """Return the BTC balance in sats (free/available, not total)."""
        ...

    @abstractmethod
    def get_other_balances(self) -> dict[str, str]:
        """Return non-BTC asset balances as {asset_code: human_readable_amount}."""
        ...

    @abstractmethod
    def get_recent_withdrawals(self, since: datetime) -> list[Withdrawal]:
        """Return withdrawals since the given timestamp, most recent first."""
        ...

    @abstractmethod
    def get_recent_deposits(self, since: datetime) -> list[Deposit]:
        """Return deposits since the given timestamp, most recent first."""
        ...

    @abstractmethod
    def withdraw(self, amount_sats: int, address: str) -> WithdrawalResult:
        """Submit a withdrawal request to the provider.

        The address must already be on the provider's whitelist.
        Raises ProviderError if the withdrawal is rejected.
        """
        ...

    @abstractmethod
    def verify_whitelist(self, address: str) -> WhitelistVerification:
        """Check whether `address` is on the provider's withdrawal whitelist.

        Returns WhitelistVerification with is_whitelisted=False and an error
        message if the provider does not support programmatic whitelist
        verification (e.g. Bitstamp). Does not raise.
        """
        ...


__all__ = [
    "CustodialProviderAdapter",
    "Deposit",
    "ProviderAuthError",
    "ProviderError",
    "ProviderPermissionError",
    "ProviderRateLimitError",
    "WhitelistVerification",
    "Withdrawal",
    "WithdrawalResult",
]
