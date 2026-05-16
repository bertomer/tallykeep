"""Unit tests for the treasury service safety validator and account-creation logic.

All tests are fully in-process — no database, no exchange API calls.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from tallykeep.domain.custodial_provider import CustodialProvider, ProviderPermissions
from tallykeep.domain.enums import (
    CustodyModel,
    HoldingType,
    Purpose,
    SafetyWarningKind,
    SafetyWarningSeverity,
    SigningModel,
)
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.domain.sweep_policy import SafetyWarning
from tallykeep.services.treasury_service import (
    TreasuryServiceError,
    TradePermissionsDetected,
    OveragePermissionsDetected,
    _compute_safety_warnings,
)


pytestmark = pytest.mark.unit


# --- Helpers -------------------------------------------------------------------

_NOW = datetime.now(UTC)


def _make_account_holding(
    custodial_provider_id: UUID | None = None,
) -> Holding:
    """Constructs a valid Account Holding (THIRD_PARTY / NOT_APPLICABLE)."""
    return Holding(
        id=uuid4(),
        holding_type=HoldingType.ACCOUNT,
        name="test account",
        description=None,
        purpose=Purpose.SPENDING,
        declared_security=SecurityClaim(
            custody_model=CustodyModel.THIRD_PARTY,
            signing_model=SigningModel.NOT_APPLICABLE,
        ),
        display_color="#000000",
        display_order=0,
        is_archived=False,
        created_at=_NOW,
        updated_at=_NOW,
        descriptor_ids=[],
        custodial_provider_id=custodial_provider_id or uuid4(),
    )


def _make_holding(
    holding_type: HoldingType,
    signing_model: SigningModel = SigningModel.SOFTWARE_HOT,
) -> Holding:
    """Constructs a valid non-Account Holding (SELF_SINGLE / given signing model)."""
    return Holding(
        id=uuid4(),
        holding_type=holding_type,
        name="test",
        description=None,
        purpose=Purpose.RESERVE,
        declared_security=SecurityClaim(
            custody_model=CustodyModel.SELF_SINGLE,
            signing_model=signing_model,
        ),
        display_color="#000000",
        display_order=0,
        is_archived=False,
        created_at=_NOW,
        updated_at=_NOW,
        descriptor_ids=[uuid4()],
    )


def _make_provider(whitelist_verified: bool = True) -> CustodialProvider:
    return CustodialProvider(
        id=uuid4(),
        holding_id=uuid4(),
        provider_kind=MagicMock(),
        display_name="Test Exchange",
        adapter_id="kraken",
        api_credential_reference="provider:xxx:api_key",
        api_secret_reference="provider:xxx:api_secret",
        api_passphrase_reference=None,
        permissions=ProviderPermissions(can_read=True, can_trade=False, can_withdraw=True),
        whitelist_address="tb1q...",
        whitelist_address_descriptor_id=uuid4(),
        whitelist_verified=whitelist_verified,
        is_active=True,
        last_polled_at=None,
        last_error=None,
        last_known_balance_sats=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


# --- Safety validator ----------------------------------------------------------


def test_no_warnings_for_clean_account_to_vault() -> None:
    src = _make_account_holding()
    dst = _make_holding(HoldingType.VAULT, SigningModel.HARDWARE_OFFLINE)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=1_000_000,
    )
    # Account source + Vault destination + different tiers + cap set + no provider passed.
    # None of the 5 rules fire.
    assert warnings == []


def test_destination_purse_warns_keys_on_host() -> None:
    src = _make_account_holding()
    dst = _make_holding(HoldingType.PURSE)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.DESTINATION_KEYS_ON_HOST in kinds


def test_destination_account_warns_custodial() -> None:
    src = _make_account_holding()
    dst = _make_account_holding()
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.DESTINATION_IS_CUSTODIAL in kinds


def test_same_security_tier_warns() -> None:
    # Use Purse → Strongbox both with SOFTWARE_HOT so same-tier warning fires.
    src = _make_holding(HoldingType.PURSE, SigningModel.SOFTWARE_HOT)
    dst = _make_holding(HoldingType.STRONGBOX, SigningModel.SOFTWARE_HOT)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.SOURCE_AND_DESTINATION_SAME_SECURITY_TIER in kinds


def test_different_tiers_no_same_tier_warning() -> None:
    src = _make_holding(HoldingType.PURSE, SigningModel.SOFTWARE_HOT)
    dst = _make_holding(HoldingType.VAULT, SigningModel.HARDWARE_OFFLINE)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.SOURCE_AND_DESTINATION_SAME_SECURITY_TIER not in kinds


def test_no_cap_warns() -> None:
    src = _make_account_holding()
    dst = _make_holding(HoldingType.VAULT, SigningModel.HARDWARE_OFFLINE)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=None,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.NO_MAXIMUM_CAP_SET in kinds


def test_unverified_whitelist_warns() -> None:
    provider_id = uuid4()
    src = _make_account_holding(custodial_provider_id=provider_id)
    dst = _make_holding(HoldingType.VAULT, SigningModel.HARDWARE_OFFLINE)
    provider = _make_provider(whitelist_verified=False)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
        source_provider=provider,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.UNVERIFIED_WHITELIST_ON_PROVIDER in kinds


def test_verified_whitelist_no_warning() -> None:
    provider_id = uuid4()
    src = _make_account_holding(custodial_provider_id=provider_id)
    dst = _make_holding(HoldingType.VAULT, SigningModel.HARDWARE_OFFLINE)
    provider = _make_provider(whitelist_verified=True)
    warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
        source_provider=provider,
    )
    kinds = {w.kind for w in warnings}
    assert SafetyWarningKind.UNVERIFIED_WHITELIST_ON_PROVIDER not in kinds


def test_acknowledgement_carryover() -> None:
    """If a warning (kind, message) pair is unchanged after a patch, the prior
    acknowledgement is preserved; changed messages lose the acknowledgement."""
    src = _make_account_holding()
    dst = _make_holding(HoldingType.PURSE)
    existing = [
        SafetyWarning(
            kind=SafetyWarningKind.DESTINATION_KEYS_ON_HOST,
            severity=SafetyWarningSeverity.HIGH,
            message="Destination Holding is a Purse — signing keys may live on the same host as the app.",
            user_acknowledged=True,
        )
    ]
    new_warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
        existing_warnings=existing,
    )
    on_host = next(
        w for w in new_warnings if w.kind == SafetyWarningKind.DESTINATION_KEYS_ON_HOST
    )
    assert on_host.user_acknowledged is True


def test_acknowledgement_lost_on_message_change() -> None:
    """A warning with a different message must NOT carry over the acknowledgement."""
    src = _make_account_holding()
    dst = _make_holding(HoldingType.PURSE)
    existing = [
        SafetyWarning(
            kind=SafetyWarningKind.DESTINATION_KEYS_ON_HOST,
            severity=SafetyWarningSeverity.HIGH,
            message="Old message that won't match.",
            user_acknowledged=True,
        )
    ]
    new_warnings = _compute_safety_warnings(
        source_holding=src,
        destination_holding=dst,
        maximum_per_period_sats=100_000,
        existing_warnings=existing,
    )
    on_host = next(
        w for w in new_warnings if w.kind == SafetyWarningKind.DESTINATION_KEYS_ON_HOST
    )
    assert on_host.user_acknowledged is False


# --- Account creation ----------------------------------------------------------


def _account_creation_args(store, adapter_id: str = "kraken") -> dict:
    return dict(
        session=MagicMock(),
        name="Test",
        description=None,
        purpose=Purpose.SPENDING,
        declared_security=SecurityClaim(
            custody_model=CustodyModel.THIRD_PARTY,
            signing_model=SigningModel.NOT_APPLICABLE,
        ),
        display_color="#000000",
        display_order=0,
        provider_kind=MagicMock(),
        display_name="Test Exchange",
        adapter_id=adapter_id,
        api_key="key",
        api_secret="secret",
        api_passphrase=None,
        secret_store=store,
    )


def _read_only_store():
    from tallykeep.infrastructure.secrets import InMemorySecretStore
    store = InMemorySecretStore()
    store.initialize("test")
    return store


def test_create_account_holding_rejects_trade_permissions(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """create_account_holding raises TradePermissionsDetected when the adapter
    reports can_trade=True via detected_extra_permissions."""
    from tallykeep.services.treasury_service import create_account_holding

    store = _read_only_store()
    mock_adapter = MagicMock()
    mock_adapter.get_permissions.return_value = MagicMock(
        can_read=True, can_trade=True, can_withdraw=False,
        detected_extra_permissions=["Trade"],
    )

    with patch("tallykeep.services.treasury_service.build_adapter", return_value=mock_adapter):
        with pytest.raises(TradePermissionsDetected):
            create_account_holding(**_account_creation_args(store))


def test_create_account_holding_rejects_unknown_adapter() -> None:
    """Unsupported adapter_id raises TreasuryServiceError, not a bare ValueError."""
    from tallykeep.services.treasury_service import create_account_holding

    with pytest.raises(TreasuryServiceError, match="Unsupported adapter"):
        create_account_holding(**_account_creation_args(_read_only_store(), adapter_id="nonexistent_xyz"))


def test_create_account_holding_ok_returns_balance_tuple() -> None:
    """Read-only key with no extra permissions succeeds and returns balance data."""
    from tallykeep.services.treasury_service import create_account_holding

    store = _read_only_store()
    mock_adapter = MagicMock()
    mock_adapter.get_permissions.return_value = MagicMock(
        can_read=True, can_trade=False, can_withdraw=False,
        detected_extra_permissions=[],
    )
    mock_adapter.get_balance.return_value = 1_500_000
    mock_adapter.get_other_balances.return_value = {"ETH": "1.5", "SOL": "10.0"}

    with patch("tallykeep.services.treasury_service.build_adapter", return_value=mock_adapter):
        with patch("tallykeep.services.treasury_service.cp_repo") as mock_cp, \
             patch("tallykeep.services.treasury_service.holding_repo"):
            mock_cp.create.return_value = None
            holding, provider, btc_sats, other = create_account_holding(
                **_account_creation_args(store)
            )

    assert btc_sats == 1_500_000
    assert set(other.keys()) == {"ETH", "SOL"}
    assert provider.whitelist_address is None
    assert provider.whitelist_address_descriptor_id is None


def test_create_account_holding_overage_withdraw_funds() -> None:
    """Key with 'Withdraw funds' is rejected with OveragePermissionsDetected."""
    from tallykeep.services.treasury_service import create_account_holding

    store = _read_only_store()
    mock_adapter = MagicMock()
    mock_adapter.get_permissions.return_value = MagicMock(
        can_read=True, can_trade=False, can_withdraw=True,
        detected_extra_permissions=["Withdraw funds"],
    )

    with patch("tallykeep.services.treasury_service.build_adapter", return_value=mock_adapter):
        with pytest.raises(OveragePermissionsDetected) as exc_info:
            create_account_holding(**_account_creation_args(store))

    assert exc_info.value.extra_permissions == ["Withdraw funds"]


def test_create_account_holding_overage_multiple_permissions() -> None:
    """Key with Trade + Margin is rejected; all detected names are reported."""
    from tallykeep.services.treasury_service import create_account_holding

    store = _read_only_store()
    mock_adapter = MagicMock()
    mock_adapter.get_permissions.return_value = MagicMock(
        can_read=True, can_trade=True, can_withdraw=False,
        detected_extra_permissions=["Trade", "Margin"],
    )

    with patch("tallykeep.services.treasury_service.build_adapter", return_value=mock_adapter):
        with pytest.raises(OveragePermissionsDetected) as exc_info:
            create_account_holding(**_account_creation_args(store))

    assert set(exc_info.value.extra_permissions) == {"Trade", "Margin"}
