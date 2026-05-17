"""CustodialProvider domain type (spec module 02).

A CustodialProvider is a connection to a third party that holds custody (Kraken,
Bitstamp, Swissquote, future P2P venues). An Account references exactly one
CustodialProvider.

Invariants enforced here:
  - Permissions: can_read must be True and can_trade must be False (the v1 doctrine).
  - Credential references are reference strings into the secret store, never values.
  - whitelist_address is nullable — it is populated by the withdrawal sub-flow
    (ADR-0011: 2-key model), not at the Add Account wizard step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from tallykeep.domain.enums import ProviderKind


@dataclass
class ProviderPermissions:
    can_read: bool
    can_trade: bool
    can_withdraw: bool
    # Verbatim names of permissions beyond the adapter's observation_permission_set
    # (e.g. "Withdraw funds", "Trade"). Empty if the key is exactly scoped.
    overage: list[str] = field(default_factory=list)
    # Verbatim names from the adapter's observation_permission_set that the key
    # does not carry (e.g. "Query ledger entries"). Empty if fully scoped.
    underage: list[str] = field(default_factory=list)


@dataclass
class CustodialProvider:
    id: UUID
    holding_id: UUID
    provider_kind: ProviderKind
    display_name: str
    adapter_id: str  # ccxt id or custom adapter id
    api_credential_reference: str  # reference into secrets store, never the value
    api_secret_reference: str
    api_passphrase_reference: str | None  # some providers use a third credential
    permissions: ProviderPermissions
    # whitelist_address is None until the withdrawal sub-flow runs (ADR-0011).
    whitelist_address: str | None
    whitelist_address_descriptor_id: UUID | None
    whitelist_verified: bool
    is_active: bool
    last_polled_at: datetime | None
    last_error: str | None
    last_known_balance_sats: int | None
    # Connection health state machine (ADR-0012 / iteration A).
    connection_status: str  # healthy | degraded | unreachable | auth_failed
    consecutive_error_count: int
    ledger_cursor_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.adapter_id:
            raise ValueError("CustodialProvider adapter_id is required")
        if not self.api_credential_reference or not self.api_secret_reference:
            raise ValueError(
                "CustodialProvider api_credential_reference and api_secret_reference "
                "are required"
            )
        if "{" in self.api_credential_reference or "{" in self.api_secret_reference:
            # Defensive: if a literal API key got assigned by mistake, JSON braces or
            # similar markers would tip us off. Reference strings are short identifiers.
            raise ValueError(
                "Credential references must be lookup strings, not credential values"
            )
        if self.last_known_balance_sats is not None and self.last_known_balance_sats < 0:
            raise ValueError("last_known_balance_sats must be >= 0")
