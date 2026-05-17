"""Treasury service — spec module 07 (M8).

Handles:
  - Account Holding creation + CustodialProvider registration
  - CustodialProvider credential rotation + balance refresh
  - SweepPolicy CRUD + safety validator
  - SweepExecution user confirmation
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from tallykeep.adapters.adapter_registry import UnsupportedAdapterError, build_adapter
from tallykeep.adapters.custodial_provider_adapter import (
    CustodialLedgerEntry,
    ProviderAuthError,
    ProviderError,
)
from tallykeep.domain.custodial_provider import CustodialProvider, ProviderPermissions
from tallykeep.domain.enums import (
    CustodyModel,
    HoldingType,
    ProviderKind,
    SafetyWarningKind,
    SafetyWarningSeverity,
    SigningModel,
    SweepExecutionStatus,
    SweepTriggerType,
)
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.domain.sweep_policy import SafetyWarning, SweepExecution, SweepPolicy
from tallykeep.infrastructure.secrets import LockedError, SecretStore
from tallykeep.repositories import custodial_provider as cp_repo
from tallykeep.repositories import holding as holding_repo
from tallykeep.repositories import sweep_execution as se_repo
from tallykeep.repositories import sweep_policy as sp_repo
from tallykeep.services import holding_service


# --- Exceptions -----------------------------------------------------------------


class TreasuryServiceError(ValueError):
    """Base for treasury-layer errors (API layer catches this)."""


class ProviderNotFound(TreasuryServiceError):
    pass


class PolicyNotFound(TreasuryServiceError):
    pass


class ExecutionNotFound(TreasuryServiceError):
    pass


class TradePermissionsDetected(TreasuryServiceError):
    """Registration rejected because the API key has trade permissions."""


class OveragePermissionsDetected(TradePermissionsDetected):
    """Read-only credential has permissions beyond the observation set (ADR-0012).

    Carries the verbatim provider permission names for the wizard's danger band.
    """

    def __init__(self, extra_permissions: list[str]) -> None:
        super().__init__(
            f"Key has extra permissions: {', '.join(extra_permissions)}"
        )
        self.extra_permissions = extra_permissions


class CredentialPermissionMismatch(TreasuryServiceError):
    """Key's permissions don't match the adapter's observation_permission_set (ADR-0012).

    Carries both overage and underage lists (either can be empty, but at least one is
    non-empty). The API layer maps this to HTTP 409 with code "permission_mismatch".
    """

    def __init__(self, overage: list[str], underage: list[str]) -> None:
        parts = []
        if overage:
            parts.append(f"overage: {', '.join(overage)}")
        if underage:
            parts.append(f"underage: {', '.join(underage)}")
        super().__init__(f"Credential permission mismatch — {'; '.join(parts)}")
        self.overage = overage
        self.underage = underage


class ProviderConnectionError(TreasuryServiceError):
    """Wrapped adapter error surfaced at the API layer."""


class PolicyHasUnacknowledgedWarnings(TreasuryServiceError):
    pass


class PolicyAlreadyEnabled(TreasuryServiceError):
    pass


class WrongExecutionStatus(TreasuryServiceError):
    pass


# --- Safety validator -----------------------------------------------------------


def _compute_safety_warnings(
    *,
    source_holding: Holding,
    destination_holding: Holding,
    maximum_per_period_sats: int | None,
    source_provider: CustodialProvider | None = None,
    existing_warnings: list[SafetyWarning] | None = None,
) -> list[SafetyWarning]:
    """Re-compute safety warnings for a SweepPolicy.

    Acknowledgement carryover: if the same (kind, message) tuple was previously
    acknowledged, the acknowledgement is preserved. Warnings with changed messages
    (e.g. parameter change) lose their acknowledgement.
    """
    acked: dict[tuple[SafetyWarningKind, str], bool] = {
        (w.kind, w.message): w.user_acknowledged
        for w in (existing_warnings or [])
    }

    warnings: list[SafetyWarning] = []

    def _warn(kind: SafetyWarningKind, severity: SafetyWarningSeverity, message: str) -> None:
        acknowledged = acked.get((kind, message), False)
        warnings.append(
            SafetyWarning(kind=kind, severity=severity, message=message,
                          user_acknowledged=acknowledged)
        )

    if destination_holding.holding_type == HoldingType.PURSE:
        _warn(
            SafetyWarningKind.DESTINATION_KEYS_ON_HOST,
            SafetyWarningSeverity.HIGH,
            "Destination Holding is a Purse — signing keys may live on the same host as the app.",
        )

    if destination_holding.holding_type == HoldingType.ACCOUNT:
        _warn(
            SafetyWarningKind.DESTINATION_IS_CUSTODIAL,
            SafetyWarningSeverity.HIGH,
            "Destination Holding is an Account (custodial) — this defeats the minimum-exposure principle.",
        )

    src_tier = source_holding.declared_security.signing_model
    dst_tier = destination_holding.declared_security.signing_model
    if src_tier == dst_tier and src_tier != SigningModel.NOT_APPLICABLE:
        _warn(
            SafetyWarningKind.SOURCE_AND_DESTINATION_SAME_SECURITY_TIER,
            SafetyWarningSeverity.MEDIUM,
            f"Source and destination both declare {src_tier.value} signing — no security tier upgrade.",
        )

    if maximum_per_period_sats is None:
        _warn(
            SafetyWarningKind.NO_MAXIMUM_CAP_SET,
            SafetyWarningSeverity.MEDIUM,
            "No maximum_per_period_sats cap is set — sweeps are unbounded.",
        )

    if (
        source_holding.holding_type == HoldingType.ACCOUNT
        and source_provider is not None
        and not source_provider.whitelist_verified
    ):
        _warn(
            SafetyWarningKind.UNVERIFIED_WHITELIST_ON_PROVIDER,
            SafetyWarningSeverity.HIGH,
            f"The withdrawal whitelist for {source_provider.display_name} could not be "
            "verified via the provider's API. Confirm it is configured manually.",
        )

    return warnings


# --- Account Holding creation ---------------------------------------------------


def validate_account_credentials(
    *,
    adapter_id: str,
    api_key: str,
    api_secret: str,
    api_passphrase: str | None = None,
) -> tuple[int, dict[str, str], list[CustodialLedgerEntry], int]:
    """Validate API credentials against the provider without any DB writes.

    Steps:
    1. Validate adapter_id.
    2. Build adapter with provided credentials.
    3. get_permissions() — reject with CredentialPermissionMismatch if overage/underage.
    4. Fetch initial BTC balance + other-asset balances.
    5. Fetch recent ledger entries (non-fatal — preview only).

    Returns (btc_balance_sats, other_balances, recent_entries_newest_first, total_count).
    Raises TreasuryServiceError, CredentialPermissionMismatch, ProviderConnectionError.
    """
    try:
        adapter = build_adapter(
            adapter_id, api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase
        )
    except UnsupportedAdapterError as exc:
        raise TreasuryServiceError(str(exc)) from exc

    try:
        perms = adapter.get_permissions()
    except ProviderAuthError as exc:
        raise TreasuryServiceError(f"Provider authentication failed: {exc}") from exc
    except ProviderError as exc:
        raise ProviderConnectionError(f"Could not reach provider: {exc}") from exc

    if perms.overage or perms.underage:
        raise CredentialPermissionMismatch(perms.overage, perms.underage)

    try:
        btc_balance_sats = adapter.get_balance()
        other_balances = adapter.get_other_balances()
    except ProviderError:
        btc_balance_sats = 0
        other_balances = {}

    recent_entries: list[CustodialLedgerEntry] = []
    ledger_total = 0
    try:
        all_entries, _ = adapter.fetch_ledger_since(None)
        ledger_total = len(all_entries)
        recent_entries = list(reversed(all_entries[-3:]))
    except Exception:
        pass

    return btc_balance_sats, other_balances, recent_entries, ledger_total


def create_account_holding(
    session: Session,
    *,
    name: str,
    description: str | None,
    purpose,
    declared_security: SecurityClaim,
    display_color: str,
    display_order: int,
    provider_kind: ProviderKind,
    display_name: str,
    adapter_id: str,
    api_key: str,
    api_secret: str,
    api_passphrase: str | None,
    secret_store: SecretStore,
) -> tuple[Holding, CustodialProvider, int, dict[str, str]]:
    """Create an Account Holding + CustodialProvider (2-key model, ADR-0011).

    Validates credentials via validate_account_credentials, then persists
    the Holding + CustodialProvider rows (whitelist fields null until the
    withdrawal sub-flow, ADR-0011).

    Returns (holding, provider, btc_balance_sats, other_balances).
    """
    btc_balance_sats, other_balances, _, _ = validate_account_credentials(
        adapter_id=adapter_id,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
    )

    # Persist credentials (read-only key only; withdrawal key comes later).
    holding_id = uuid4()
    provider_id = uuid4()
    cred_ref = f"provider:{provider_id}:read_api_key"
    secret_ref = f"provider:{provider_id}:read_api_secret"
    passphrase_ref: str | None = None

    try:
        secret_store.set_secret(cred_ref, api_key.encode())
        secret_store.set_secret(secret_ref, api_secret.encode())
        if api_passphrase is not None:
            passphrase_ref = f"provider:{provider_id}:read_api_passphrase"
            secret_store.set_secret(passphrase_ref, api_passphrase.encode())
    except LockedError as exc:
        raise TreasuryServiceError("Secret store is locked; unlock before registering a provider") from exc

    # Build a read-only ProviderPermissions (no trade, no withdraw).
    read_only_perms = ProviderPermissions(
        can_read=True,
        can_trade=False,
        can_withdraw=False,
    )

    # Persist Holding
    now = datetime.now(UTC)
    holding = Holding(
        id=holding_id,
        holding_type=HoldingType.ACCOUNT,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        is_archived=False,
        created_at=now,
        updated_at=now,
        descriptor_ids=[],
        custodial_provider_id=provider_id,
    )
    holding_repo.insert_row(
        session,
        holding_id=holding_id,
        holding_type=HoldingType.ACCOUNT,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        subtype_data={},
    )
    session.flush()

    # Persist CustodialProvider (whitelist fields null until withdrawal sub-flow).
    provider = CustodialProvider(
        id=provider_id,
        holding_id=holding_id,
        provider_kind=provider_kind,
        display_name=display_name,
        adapter_id=adapter_id,
        api_credential_reference=cred_ref,
        api_secret_reference=secret_ref,
        api_passphrase_reference=passphrase_ref,
        permissions=read_only_perms,
        whitelist_address=None,
        whitelist_address_descriptor_id=None,
        whitelist_verified=False,
        is_active=True,
        last_polled_at=now,
        last_error=None,
        last_known_balance_sats=btc_balance_sats,
        connection_status="healthy",
        consecutive_error_count=0,
        ledger_cursor_at=None,
        created_at=now,
        updated_at=now,
    )
    cp_repo.create(session, provider)

    return holding, provider, btc_balance_sats, other_balances


# --- CustodialProvider CRUD ----------------------------------------------------


def get_provider(session: Session, provider_id: UUID) -> CustodialProvider:
    p = cp_repo.get(session, provider_id)
    if p is None:
        raise ProviderNotFound(f"CustodialProvider {provider_id} not found")
    return p


def list_providers(session: Session) -> list[CustodialProvider]:
    return cp_repo.list_active(session)


def patch_provider(
    session: Session,
    provider_id: UUID,
    *,
    display_name: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    api_passphrase: str | None = None,
    secret_store: SecretStore | None = None,
) -> CustodialProvider:
    provider = get_provider(session, provider_id)

    if api_key is not None or api_secret is not None:
        if secret_store is None:
            raise TreasuryServiceError("secret_store is required for credential rotation")
        new_key = api_key or secret_store.get_secret(provider.api_credential_reference).decode()
        new_secret = api_secret or secret_store.get_secret(provider.api_secret_reference).decode()
        new_pass = api_passphrase

        # Validate new credentials
        try:
            adapter = build_adapter(provider.adapter_id, api_key=new_key, api_secret=new_secret,
                                    api_passphrase=new_pass)
            perms = adapter.get_permissions()
        except ProviderAuthError as exc:
            raise TreasuryServiceError(f"New credentials are invalid: {exc}") from exc
        except ProviderError as exc:
            raise ProviderConnectionError(str(exc)) from exc

        if perms.can_trade:
            raise TradePermissionsDetected(
                "New credential still has trade permissions. Use a read+withdraw-only key."
            )

        # Purge old secrets and store new ones
        try:
            secret_store.delete_secret(provider.api_credential_reference)
            secret_store.delete_secret(provider.api_secret_reference)
            if provider.api_passphrase_reference:
                secret_store.delete_secret(provider.api_passphrase_reference)
        except KeyError:
            pass  # Old reference may have been deleted already

        new_cred_ref = f"provider:{provider_id}:api_key:{uuid4().hex[:8]}"
        new_secret_ref = f"provider:{provider_id}:api_secret:{uuid4().hex[:8]}"
        new_pass_ref: str | None = None

        secret_store.set_secret(new_cred_ref, new_key.encode())
        secret_store.set_secret(new_secret_ref, new_secret.encode())
        if new_pass is not None:
            new_pass_ref = f"provider:{provider_id}:api_passphrase:{uuid4().hex[:8]}"
            secret_store.set_secret(new_pass_ref, new_pass.encode())

        updated = cp_repo.update_credentials(
            session, provider_id,
            api_credential_reference=new_cred_ref,
            api_secret_reference=new_secret_ref,
            api_passphrase_reference=new_pass_ref,
        )
        provider = updated or provider

    return provider


def refresh_provider_balance(
    session: Session,
    provider_id: UUID,
    *,
    secret_store: SecretStore,
) -> CustodialProvider:
    """Immediately poll balance and update the provider row."""
    provider = get_provider(session, provider_id)
    try:
        api_key = secret_store.get_secret(provider.api_credential_reference).decode()
        api_secret = secret_store.get_secret(provider.api_secret_reference).decode()
        api_passphrase = (
            secret_store.get_secret(provider.api_passphrase_reference).decode()
            if provider.api_passphrase_reference else None
        )
    except (KeyError, LockedError) as exc:
        raise TreasuryServiceError(f"Cannot read provider credentials: {exc}") from exc

    try:
        adapter = build_adapter(provider.adapter_id, api_key=api_key, api_secret=api_secret,
                                api_passphrase=api_passphrase)
        balance = adapter.get_balance()
    except ProviderAuthError as exc:
        cp_repo.update_error(session, provider_id,
                             error=str(exc), polled_at=datetime.now(UTC))
        raise TreasuryServiceError(f"Provider authentication failed: {exc}") from exc
    except ProviderError as exc:
        cp_repo.update_error(session, provider_id,
                             error=str(exc), polled_at=datetime.now(UTC))
        raise ProviderConnectionError(str(exc)) from exc

    updated = cp_repo.update_balance(session, provider_id,
                                     balance_sats=balance, polled_at=datetime.now(UTC))
    return updated or provider


def verify_whitelist(
    session: Session,
    provider_id: UUID,
    *,
    secret_store: SecretStore,
) -> tuple[CustodialProvider, bool, str | None]:
    """Run whitelist verification and update whitelist_verified on the provider."""
    provider = get_provider(session, provider_id)
    try:
        api_key = secret_store.get_secret(provider.api_credential_reference).decode()
        api_secret = secret_store.get_secret(provider.api_secret_reference).decode()
        api_passphrase = (
            secret_store.get_secret(provider.api_passphrase_reference).decode()
            if provider.api_passphrase_reference else None
        )
    except (KeyError, LockedError) as exc:
        raise TreasuryServiceError(f"Cannot read provider credentials: {exc}") from exc

    adapter = build_adapter(provider.adapter_id, api_key=api_key, api_secret=api_secret,
                            api_passphrase=api_passphrase)
    result = adapter.verify_whitelist(provider.whitelist_address)

    if result.is_whitelisted:
        cp_repo.set_whitelist_verified(session, provider_id, verified=True)

    updated = cp_repo.get(session, provider_id)
    return (updated or provider), result.is_whitelisted, result.error


# --- SweepPolicy CRUD ----------------------------------------------------------


def create_sweep_policy(
    session: Session,
    *,
    name: str,
    source_holding_id: UUID,
    destination_holding_id: UUID,
    trigger_type: SweepTriggerType,
    trigger_configuration: dict,
    minimum_balance_sats: int,
    maximum_per_period_sats: int | None,
    requires_user_confirmation: bool,
    is_dry_run: bool,
) -> SweepPolicy:
    source = holding_service.get_holding(session, source_holding_id)
    if source is None:
        raise TreasuryServiceError(f"Source holding {source_holding_id} not found")
    destination = holding_service.get_holding(session, destination_holding_id)
    if destination is None:
        raise TreasuryServiceError(f"Destination holding {destination_holding_id} not found")
    if source_holding_id == destination_holding_id:
        raise TreasuryServiceError("Source and destination holdings must differ")

    source_provider: CustodialProvider | None = None
    if source.holding_type == HoldingType.ACCOUNT and source.custodial_provider_id:
        source_provider = cp_repo.get(session, source.custodial_provider_id)

    warnings = _compute_safety_warnings(
        source_holding=source,
        destination_holding=destination,
        maximum_per_period_sats=maximum_per_period_sats,
        source_provider=source_provider,
    )

    now = datetime.now(UTC)
    policy = SweepPolicy(
        id=uuid4(),
        name=name,
        source_holding_id=source_holding_id,
        destination_holding_id=destination_holding_id,
        is_enabled=False,
        trigger_type=trigger_type,
        trigger_configuration=trigger_configuration,
        minimum_balance_sats=minimum_balance_sats,
        maximum_per_period_sats=maximum_per_period_sats,
        requires_user_confirmation=requires_user_confirmation,
        is_dry_run=is_dry_run,
        safety_warnings=warnings,
        created_at=now,
        updated_at=now,
    )
    sp_repo.create(session, policy)
    return policy


def get_sweep_policy(session: Session, policy_id: UUID) -> SweepPolicy:
    p = sp_repo.get(session, policy_id)
    if p is None:
        raise PolicyNotFound(f"SweepPolicy {policy_id} not found")
    return p


def list_sweep_policies(
    session: Session,
    *,
    source_holding_id: UUID | None = None,
    enabled: bool | None = None,
) -> list[SweepPolicy]:
    return sp_repo.list_policies(session, source_holding_id=source_holding_id, enabled=enabled)


def update_sweep_policy(
    session: Session,
    policy_id: UUID,
    *,
    name: str | None = None,
    trigger_type: SweepTriggerType | None = None,
    trigger_configuration: dict | None = None,
    minimum_balance_sats: int | None = None,
    maximum_per_period_sats: int | None = None,
    requires_user_confirmation: bool | None = None,
    is_dry_run: bool | None = None,
) -> SweepPolicy:
    policy = get_sweep_policy(session, policy_id)

    # Re-run safety validator if key fields changed.
    if any(v is not None for v in [
        trigger_type, trigger_configuration, minimum_balance_sats,
        maximum_per_period_sats, is_dry_run,
    ]):
        source = holding_service.get_holding(session, policy.source_holding_id)
        destination = holding_service.get_holding(session, policy.destination_holding_id)
        if source and destination:
            source_provider: CustodialProvider | None = None
            if source.holding_type == HoldingType.ACCOUNT and source.custodial_provider_id:
                source_provider = cp_repo.get(session, source.custodial_provider_id)
            effective_cap = (
                maximum_per_period_sats
                if maximum_per_period_sats is not None
                else policy.maximum_per_period_sats
            )
            new_warnings = _compute_safety_warnings(
                source_holding=source,
                destination_holding=destination,
                maximum_per_period_sats=effective_cap,
                source_provider=source_provider,
                existing_warnings=policy.safety_warnings,
            )
        else:
            new_warnings = policy.safety_warnings
    else:
        new_warnings = None

    updated = sp_repo.update_policy(
        session, policy_id,
        name=name,
        trigger_type=trigger_type,
        trigger_configuration=trigger_configuration,
        minimum_balance_sats=minimum_balance_sats,
        maximum_per_period_sats=maximum_per_period_sats,
        requires_user_confirmation=requires_user_confirmation,
        is_dry_run=is_dry_run,
        safety_warnings=new_warnings,
    )
    return updated or policy


def delete_sweep_policy(session: Session, policy_id: UUID) -> None:
    policy = get_sweep_policy(session, policy_id)
    if policy.is_enabled:
        raise TreasuryServiceError("Disable the policy before deleting it")
    sp_repo.delete(session, policy_id)


def enable_sweep_policy(session: Session, policy_id: UUID) -> SweepPolicy:
    policy = get_sweep_policy(session, policy_id)
    unacked = [w for w in policy.safety_warnings if not w.user_acknowledged]
    if unacked:
        kinds = ", ".join(w.kind.value for w in unacked)
        raise PolicyHasUnacknowledgedWarnings(
            f"Acknowledge all safety warnings before enabling. Pending: {kinds}"
        )
    updated = sp_repo.set_enabled(session, policy_id, enabled=True)
    return updated or policy


def disable_sweep_policy(session: Session, policy_id: UUID) -> SweepPolicy:
    policy = get_sweep_policy(session, policy_id)
    updated = sp_repo.set_enabled(session, policy_id, enabled=False)
    return updated or policy


def acknowledge_warnings(session: Session, policy_id: UUID) -> SweepPolicy:
    get_sweep_policy(session, policy_id)
    updated = sp_repo.acknowledge_all_warnings(session, policy_id)
    if updated is None:
        raise PolicyNotFound(f"SweepPolicy {policy_id} not found")
    return updated


def pause_all_policies(session: Session) -> int:
    return sp_repo.pause_all(session)


def resume_all_policies(session: Session) -> int:
    return sp_repo.resume_all(session)


# --- SweepExecution ------------------------------------------------------------


def list_sweep_executions(
    session: Session,
    *,
    sweep_policy_id: UUID | None = None,
    status: SweepExecutionStatus | None = None,
    limit: int = 50,
) -> list[SweepExecution]:
    return se_repo.list_executions(session, sweep_policy_id=sweep_policy_id,
                                   status=status, limit=limit)


def get_sweep_execution(session: Session, execution_id: UUID) -> SweepExecution:
    e = se_repo.get(session, execution_id)
    if e is None:
        raise ExecutionNotFound(f"SweepExecution {execution_id} not found")
    return e


def confirm_sweep_execution(session: Session, execution_id: UUID) -> SweepExecution:
    execution = get_sweep_execution(session, execution_id)
    if execution.status != SweepExecutionStatus.AWAITING_USER_CONFIRMATION:
        raise WrongExecutionStatus(
            f"SweepExecution {execution_id} is in status {execution.status.value!r}; "
            "only AWAITING_USER_CONFIRMATION executions can be confirmed"
        )
    updated = se_repo.update_status(session, execution_id,
                                    status=SweepExecutionStatus.REQUESTED)
    return updated or execution


def execute_sweep_now(
    session: Session,
    policy_id: UUID,
    *,
    secret_store: SecretStore,
    amount_sats: int | None = None,
) -> SweepExecution:
    """Create a manual SweepExecution and attempt the withdrawal immediately.

    For Account → self-custody policies: calls the custodial provider's withdraw
    method using the destination holding's next unused receive address.

    Returns the SweepExecution (status REQUESTED or FAILED if the withdrawal call
    itself raised immediately).
    """
    from tallykeep.repositories import descriptor as descriptor_repo

    policy = get_sweep_policy(session, policy_id)
    if not policy.is_enabled:
        raise TreasuryServiceError("Policy must be enabled before manual execution")

    source = holding_service.get_holding(session, policy.source_holding_id)
    if source is None:
        raise TreasuryServiceError(f"Source holding {policy.source_holding_id} not found")

    if source.holding_type != HoldingType.ACCOUNT or not source.custodial_provider_id:
        raise TreasuryServiceError(
            "Manual execute-now is only supported for Account → self-custody policies"
        )

    provider = cp_repo.get(session, source.custodial_provider_id)
    if provider is None:
        raise TreasuryServiceError("CustodialProvider not found for source holding")

    # Resolve destination address from the first descriptor of the destination holding.
    dest_descriptors = descriptor_repo.list_descriptors_for_holding(
        session, policy.destination_holding_id
    )
    if not dest_descriptors:
        raise TreasuryServiceError(
            "Destination holding has no descriptors — cannot derive a receive address"
        )
    address_row = descriptor_repo.next_unused_address(
        session, dest_descriptors[0].id, is_change=False
    )
    if address_row is None:
        raise TreasuryServiceError(
            "No unused receive address available on destination holding's descriptor"
        )

    # Resolve credentials.
    try:
        api_key = secret_store.get_secret(provider.api_credential_reference).decode()
        api_secret = secret_store.get_secret(provider.api_secret_reference).decode()
        api_passphrase = (
            secret_store.get_secret(provider.api_passphrase_reference).decode()
            if provider.api_passphrase_reference else None
        )
    except (KeyError, LockedError) as exc:
        raise TreasuryServiceError(f"Cannot read provider credentials: {exc}") from exc

    # Calculate sweep amount.
    current_balance = provider.last_known_balance_sats or 0
    if amount_sats is None:
        sweep_amount = current_balance - policy.minimum_balance_sats
        if policy.maximum_per_period_sats is not None:
            sweep_amount = min(sweep_amount, policy.maximum_per_period_sats)
    else:
        sweep_amount = amount_sats

    if sweep_amount <= 0:
        raise TreasuryServiceError(
            "Calculated sweep amount is zero or negative — "
            "check the balance and minimum_balance_sats"
        )

    now = datetime.now(UTC)
    execution = SweepExecution(
        id=uuid4(),
        sweep_policy_id=policy.id,
        triggered_at=now,
        trigger_source=SweepTriggerType.MANUAL,
        pre_balance_sats=current_balance,
        intended_amount_sats=sweep_amount,
        status=SweepExecutionStatus.REQUESTED,
        provider_withdrawal_id=None,
        expected_txid=None,
        confirmed_txid=None,
        error_message=None,
        completed_at=None,
    )
    se_repo.create(session, execution)
    session.flush()

    # Attempt the withdrawal immediately.
    try:
        adapter = build_adapter(
            provider.adapter_id,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )
        result = adapter.withdraw(sweep_amount, address_row.address)
        updated = se_repo.update_status(
            session,
            execution.id,
            status=SweepExecutionStatus.REQUESTED,
            provider_withdrawal_id=result.withdrawal_id,
        )
        return updated or execution
    except (ProviderAuthError, ProviderError) as exc:
        failed = se_repo.update_status(
            session,
            execution.id,
            status=SweepExecutionStatus.FAILED,
            error_message=str(exc),
            completed_at=datetime.now(UTC),
        )
        return failed or execution


__all__ = [
    "TreasuryServiceError",
    "TradePermissionsDetected",
    "OveragePermissionsDetected",
    "CredentialPermissionMismatch",
    "ProviderNotFound",
    "PolicyNotFound",
    "ExecutionNotFound",
    "NoReadPermissionError",
    "ProviderConnectionError",
    "PolicyHasUnacknowledgedWarnings",
    "WrongExecutionStatus",
    "validate_account_credentials",
    "create_account_holding",
    "get_provider",
    "list_providers",
    "patch_provider",
    "refresh_provider_balance",
    "verify_whitelist",
    "execute_sweep_now",
    "create_sweep_policy",
    "get_sweep_policy",
    "list_sweep_policies",
    "update_sweep_policy",
    "delete_sweep_policy",
    "enable_sweep_policy",
    "disable_sweep_policy",
    "acknowledge_warnings",
    "pause_all_policies",
    "resume_all_policies",
    "list_sweep_executions",
    "get_sweep_execution",
    "confirm_sweep_execution",
]
