"""Domain invariant tests.

Each spec invariant from module 02 is exercised at least once. These tests are the
canonical reference for "what is structurally enforced at construction time" — if a
test changes, a spec invariant is changing too.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tallykeep.domain import (
    USER_PROFILE_SINGLETON_ID,
    Address,
    AddressType,
    CustodialProvider,
    CustodyModel,
    Descriptor,
    Direction,
    Holding,
    HoldingType,
    InvoiceStatus,
    LedgerCategory,
    LedgerEntry,
    LedgerEntrySource,
    Network,
    PaymentStatus,
    PaymentType,
    ProfilePreset,
    ProviderKind,
    ProviderPermissions,
    Purpose,
    SafetyWarning,
    SafetyWarningKind,
    SafetyWarningSeverity,
    SecurityClaim,
    SigningModel,
    SweepPolicy,
    SweepTriggerType,
    UTXO,
    UserProfile,
)
from tallykeep.domain.invoice import Invoice
from tallykeep.domain.payment_request import PaymentRequest


pytestmark = pytest.mark.unit


# --- helpers ----------------------------------------------------------------------

NOW = datetime(2026, 5, 1, tzinfo=UTC)


def _self_single_claim(signing: SigningModel = SigningModel.SOFTWARE_HOT) -> SecurityClaim:
    return SecurityClaim(
        custody_model=CustodyModel.SELF_SINGLE,
        signing_model=signing,
    )


def _third_party_claim() -> SecurityClaim:
    return SecurityClaim(
        custody_model=CustodyModel.THIRD_PARTY,
        signing_model=SigningModel.NOT_APPLICABLE,
    )


def _make_holding(
    holding_type: HoldingType,
    *,
    descriptor_ids: list[UUID] | None = None,
    custodial_provider_id: UUID | None = None,
    declared_security: SecurityClaim | None = None,
    **subtype_kwargs: object,
) -> Holding:
    if declared_security is None:
        declared_security = (
            _third_party_claim()
            if holding_type == HoldingType.ACCOUNT
            else _self_single_claim()
        )
    return Holding(
        id=uuid4(),
        holding_type=holding_type,
        name="Test holding",
        description=None,
        purpose=Purpose.UNDECLARED,
        declared_security=declared_security,
        display_color="#000000",
        display_order=0,
        is_archived=False,
        created_at=NOW,
        updated_at=NOW,
        descriptor_ids=descriptor_ids or [],
        custodial_provider_id=custodial_provider_id,
        **subtype_kwargs,  # type: ignore[arg-type]
    )


# --- Holding invariants -----------------------------------------------------------


class TestAccountHolding:
    """Spec module 02 invariant 1: Account has no Descriptors and exactly one
    CustodialProvider."""

    def test_account_with_provider_succeeds(self) -> None:
        h = _make_holding(HoldingType.ACCOUNT, custodial_provider_id=uuid4())
        assert h.holding_type == HoldingType.ACCOUNT
        assert h.descriptor_ids == []

    def test_account_without_provider_rejected(self) -> None:
        with pytest.raises(ValueError, match="CustodialProvider id"):
            _make_holding(HoldingType.ACCOUNT)

    def test_account_with_descriptors_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot have descriptors"):
            _make_holding(
                HoldingType.ACCOUNT,
                custodial_provider_id=uuid4(),
                descriptor_ids=[uuid4()],
            )

    def test_account_must_declare_third_party_custody(self) -> None:
        with pytest.raises(ValueError, match="custody_model=THIRD_PARTY"):
            _make_holding(
                HoldingType.ACCOUNT,
                custodial_provider_id=uuid4(),
                declared_security=_self_single_claim(SigningModel.NOT_APPLICABLE),
            )

    def test_account_must_declare_signing_not_applicable(self) -> None:
        with pytest.raises(ValueError, match="signing_model=NOT_APPLICABLE"):
            _make_holding(
                HoldingType.ACCOUNT,
                custodial_provider_id=uuid4(),
                declared_security=SecurityClaim(
                    custody_model=CustodyModel.THIRD_PARTY,
                    signing_model=SigningModel.SOFTWARE_HOT,
                ),
            )


class TestPurseStrongboxVaultHoldings:
    """Spec module 02 invariant 2: Purse / Strongbox / Vault have at least one
    Descriptor and no CustodialProvider."""

    @pytest.mark.parametrize(
        "holding_type",
        [HoldingType.PURSE, HoldingType.STRONGBOX, HoldingType.VAULT],
    )
    def test_with_descriptor_succeeds(self, holding_type: HoldingType) -> None:
        h = _make_holding(holding_type, descriptor_ids=[uuid4()])
        assert h.holding_type == holding_type

    @pytest.mark.parametrize(
        "holding_type",
        [HoldingType.PURSE, HoldingType.STRONGBOX, HoldingType.VAULT],
    )
    def test_without_descriptor_rejected(self, holding_type: HoldingType) -> None:
        with pytest.raises(ValueError, match="require at least one descriptor"):
            _make_holding(holding_type, descriptor_ids=[])

    @pytest.mark.parametrize(
        "holding_type",
        [HoldingType.PURSE, HoldingType.STRONGBOX, HoldingType.VAULT],
    )
    def test_with_custodial_provider_rejected(self, holding_type: HoldingType) -> None:
        with pytest.raises(ValueError, match="cannot have a CustodialProvider"):
            _make_holding(
                holding_type,
                descriptor_ids=[uuid4()],
                custodial_provider_id=uuid4(),
            )

    @pytest.mark.parametrize(
        "holding_type",
        [HoldingType.PURSE, HoldingType.STRONGBOX, HoldingType.VAULT],
    )
    def test_signing_not_applicable_rejected(self, holding_type: HoldingType) -> None:
        with pytest.raises(ValueError, match="cannot declare signing_model"):
            _make_holding(
                holding_type,
                descriptor_ids=[uuid4()],
                declared_security=SecurityClaim(
                    custody_model=CustodyModel.SELF_SINGLE,
                    signing_model=SigningModel.NOT_APPLICABLE,
                ),
            )


class TestHoldingSubtypeMetadataIsolation:
    """Subtype-specific metadata may only appear on its owning subtype."""

    def test_signing_device_label_only_on_strongbox(self) -> None:
        with pytest.raises(ValueError, match="signing_device_label"):
            _make_holding(
                HoldingType.PURSE,
                descriptor_ids=[uuid4()],
                signing_device_label="Coldcard Mk4 in safe",
            )

    def test_strongbox_with_signing_device_label_succeeds(self) -> None:
        h = _make_holding(
            HoldingType.STRONGBOX,
            descriptor_ids=[uuid4()],
            signing_device_label="Coldcard Mk4 in safe",
            declared_security=_self_single_claim(SigningModel.HARDWARE_OFFLINE),
        )
        assert h.signing_device_label == "Coldcard Mk4 in safe"

    @pytest.mark.parametrize(
        "holding_type",
        [HoldingType.ACCOUNT, HoldingType.PURSE, HoldingType.STRONGBOX],
    )
    def test_vault_metadata_only_on_vault(self, holding_type: HoldingType) -> None:
        common: dict[str, object] = {"required_signers": 2, "total_signers": 3}
        if holding_type == HoldingType.ACCOUNT:
            with pytest.raises(ValueError, match="Vault metadata"):
                _make_holding(holding_type, custodial_provider_id=uuid4(), **common)
        else:
            with pytest.raises(ValueError, match="Vault metadata"):
                _make_holding(holding_type, descriptor_ids=[uuid4()], **common)


class TestVaultMultisigParameters:
    """Vault multisig metadata consistency (spec module 02 / 04 / 11)."""

    def test_required_total_must_be_set_together(self) -> None:
        with pytest.raises(ValueError, match="set together"):
            _make_holding(
                HoldingType.VAULT,
                descriptor_ids=[uuid4()],
                declared_security=_self_single_claim(SigningModel.CEREMONIAL),
                required_signers=2,
            )

    def test_required_must_be_at_least_one(self) -> None:
        with pytest.raises(ValueError, match="required_signers must be >= 1"):
            _make_holding(
                HoldingType.VAULT,
                descriptor_ids=[uuid4()],
                declared_security=_self_single_claim(SigningModel.CEREMONIAL),
                required_signers=0,
                total_signers=3,
            )

    def test_total_must_be_at_least_required(self) -> None:
        with pytest.raises(ValueError, match="total_signers must be >="):
            _make_holding(
                HoldingType.VAULT,
                descriptor_ids=[uuid4()],
                declared_security=_self_single_claim(SigningModel.CEREMONIAL),
                required_signers=3,
                total_signers=2,
            )

    def test_negative_timelock_rejected(self) -> None:
        with pytest.raises(ValueError, match="timelock_blocks must be >= 0"):
            _make_holding(
                HoldingType.VAULT,
                descriptor_ids=[uuid4()],
                declared_security=_self_single_claim(SigningModel.CEREMONIAL),
                timelock_blocks=-1,
            )


# --- Descriptor / Address / UTXO --------------------------------------------------


class TestDescriptorInvariants:
    def test_descriptor_must_be_watch_only(self) -> None:
        with pytest.raises(ValueError, match="watch-only"):
            Descriptor(
                id=uuid4(),
                holding_id=uuid4(),
                name="x",
                expression="wpkh(...)",
                change_expression=None,
                network=Network.MAINNET,
                address_type=AddressType.NATIVE_SEGWIT,
                gap_limit=20,
                is_watch_only=False,
                last_scanned_height=0,
                created_at=NOW,
            )

    def test_descriptor_gap_limit_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="gap_limit"):
            Descriptor(
                id=uuid4(),
                holding_id=uuid4(),
                name="x",
                expression="wpkh(...)",
                change_expression=None,
                network=Network.MAINNET,
                address_type=AddressType.NATIVE_SEGWIT,
                gap_limit=0,
                is_watch_only=True,
                last_scanned_height=0,
                created_at=NOW,
            )

    def test_descriptor_expression_required(self) -> None:
        with pytest.raises(ValueError, match="expression"):
            Descriptor(
                id=uuid4(),
                holding_id=uuid4(),
                name="x",
                expression="",
                change_expression=None,
                network=Network.MAINNET,
                address_type=AddressType.NATIVE_SEGWIT,
                gap_limit=20,
                is_watch_only=True,
                last_scanned_height=0,
                created_at=NOW,
            )


class TestUTXOInvariants:
    def _make(self, **kwargs: object) -> UTXO:
        defaults: dict[str, object] = dict(
            id=uuid4(),
            descriptor_id=uuid4(),
            address_id=uuid4(),
            txid="a" * 64,
            vout=0,
            value_sats=10_000,
            confirmation_height=100,
            is_frozen=False,
            is_spent=False,
            spent_in_txid=None,
            hygiene_flags=[],
            created_at=NOW,
        )
        defaults.update(kwargs)
        return UTXO(**defaults)  # type: ignore[arg-type]

    def test_negative_value_rejected(self) -> None:
        with pytest.raises(ValueError, match="value_sats"):
            self._make(value_sats=-1)

    def test_spent_requires_spent_in_txid(self) -> None:
        with pytest.raises(ValueError, match="Spent UTXO must record"):
            self._make(is_spent=True, spent_in_txid=None)

    def test_unspent_with_spent_in_txid_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unspent UTXO must not"):
            self._make(is_spent=False, spent_in_txid="b" * 64)


# --- CustodialProvider ------------------------------------------------------------


class TestCustodialProvider:
    def test_can_trade_must_be_false(self) -> None:
        with pytest.raises(ValueError, match="can_trade must be False"):
            ProviderPermissions(can_read=True, can_trade=True, can_withdraw=False)

    def test_can_read_must_be_true(self) -> None:
        with pytest.raises(ValueError, match="can_read must be True"):
            ProviderPermissions(can_read=False, can_trade=False, can_withdraw=False)

    def test_credential_reference_cannot_look_like_a_value(self) -> None:
        with pytest.raises(ValueError, match="lookup strings"):
            CustodialProvider(
                id=uuid4(),
                holding_id=uuid4(),
                provider_kind=ProviderKind.EXCHANGE,
                display_name="Kraken main",
                adapter_id="kraken",
                api_credential_reference='{"key":"shouldnt-be-here"}',
                api_secret_reference="kraken_main:api_secret",
                api_passphrase_reference=None,
                permissions=ProviderPermissions(
                    can_read=True, can_trade=False, can_withdraw=True
                ),
                whitelist_address="bc1qexample",
                whitelist_address_descriptor_id=uuid4(),
                whitelist_verified=False,
                is_active=True,
                last_polled_at=None,
                last_error=None,
                last_known_balance_sats=None,
                created_at=NOW,
                updated_at=NOW,
            )


# --- LedgerEntry -------------------------------------------------------------------


class TestLedgerEntry:
    def _make(self, **kwargs: object) -> LedgerEntry:
        defaults: dict[str, object] = dict(
            id=uuid4(),
            direction=Direction.INCOMING,
            net_amount_sats=1_000,
            fee_sats=None,
            timestamp=NOW,
            source=LedgerEntrySource.ONCHAIN_TRANSACTION,
            source_reference="a" * 64,
            category=None,
            counterparty_label=None,
            note=None,
            suggested_category=None,
            categorized_at=None,
            created_at=NOW,
        )
        defaults.update(kwargs)
        return LedgerEntry(**defaults)  # type: ignore[arg-type]

    def test_incoming_negative_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="Incoming"):
            self._make(direction=Direction.INCOMING, net_amount_sats=-100)

    def test_outgoing_positive_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="Outgoing"):
            self._make(direction=Direction.OUTGOING, net_amount_sats=100)

    def test_category_without_categorized_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="categorized_at"):
            self._make(category=LedgerCategory.MERCHANT_RECEIPT, categorized_at=None)

    def test_source_reference_required(self) -> None:
        with pytest.raises(ValueError, match="source_reference"):
            self._make(source_reference="")


# --- PaymentRequest / Invoice cross-type fields ----------------------------------


class TestPaymentRequestCrossTypeFields:
    """Spec module 02 / 06: Onchain PaymentRequest cannot carry Lightning fields and
    vice versa."""

    def test_onchain_with_lightning_invoice_rejected(self) -> None:
        with pytest.raises(ValueError, match="Lightning invoice fields"):
            PaymentRequest(
                id=uuid4(),
                holding_id=uuid4(),
                payment_type=PaymentType.ONCHAIN,
                amount_sats=1_000,
                description=None,
                status=PaymentStatus.DRAFT,
                expires_at=None,
                created_at=NOW,
                updated_at=NOW,
                lightning_invoice="lnbc1...",
            )

    def test_lightning_with_psbt_rejected(self) -> None:
        with pytest.raises(ValueError, match="on-chain PSBT"):
            PaymentRequest(
                id=uuid4(),
                holding_id=uuid4(),
                payment_type=PaymentType.LIGHTNING,
                amount_sats=1_000,
                description=None,
                status=PaymentStatus.DRAFT,
                expires_at=None,
                created_at=NOW,
                updated_at=NOW,
                psbt_base64="cHNidP8B...",
            )


class TestInvoiceCrossTypeFields:
    def test_onchain_invoice_with_bolt11_rejected(self) -> None:
        with pytest.raises(ValueError, match="Lightning fields"):
            Invoice(
                id=uuid4(),
                holding_id=uuid4(),
                invoice_type=PaymentType.ONCHAIN,
                amount_sats=1_000,
                description=None,
                status=InvoiceStatus.OPEN,
                expires_at=None,
                created_at=NOW,
                bolt11="lnbc1...",
            )

    def test_lightning_invoice_with_address_rejected(self) -> None:
        with pytest.raises(ValueError, match="receiving_address"):
            Invoice(
                id=uuid4(),
                holding_id=uuid4(),
                invoice_type=PaymentType.LIGHTNING,
                amount_sats=1_000,
                description=None,
                status=InvoiceStatus.OPEN,
                expires_at=None,
                created_at=NOW,
                receiving_address="bc1q...",
            )


# --- SweepPolicy ------------------------------------------------------------------


def _empty_warning() -> SafetyWarning:
    return SafetyWarning(
        kind=SafetyWarningKind.NO_MAXIMUM_CAP_SET,
        severity=SafetyWarningSeverity.MEDIUM,
        message="No max cap",
        user_acknowledged=False,
    )


class TestSweepPolicy:
    def _make(self, **kwargs: object) -> SweepPolicy:
        defaults: dict[str, object] = dict(
            id=uuid4(),
            name="Test policy",
            source_holding_id=uuid4(),
            destination_holding_id=uuid4(),
            is_enabled=False,
            trigger_type=SweepTriggerType.MANUAL,
            trigger_configuration={},
            minimum_balance_sats=0,
            maximum_per_period_sats=None,
            requires_user_confirmation=True,
            safety_warnings=[],
        )
        defaults.update(kwargs)
        return SweepPolicy(**defaults)  # type: ignore[arg-type]

    def test_source_and_destination_must_differ(self) -> None:
        same = uuid4()
        with pytest.raises(ValueError, match="must differ"):
            self._make(source_holding_id=same, destination_holding_id=same)

    def test_enabled_with_unacknowledged_warning_rejected(self) -> None:
        # Spec module 02 invariant 5.
        with pytest.raises(ValueError, match="unacknowledged warnings"):
            self._make(is_enabled=True, safety_warnings=[_empty_warning()])

    def test_enabled_with_all_warnings_acked_succeeds(self) -> None:
        warning = _empty_warning()
        warning.user_acknowledged = True
        p = self._make(is_enabled=True, safety_warnings=[warning])
        assert p.is_enabled is True

    def test_negative_minimum_balance_rejected(self) -> None:
        with pytest.raises(ValueError, match="minimum_balance_sats"):
            self._make(minimum_balance_sats=-1)


# --- UserProfile ------------------------------------------------------------------


class TestUserProfile:
    def test_singleton_id_enforced(self) -> None:
        with pytest.raises(ValueError, match="singleton id"):
            UserProfile(
                id=uuid4(),
                preset=ProfilePreset.INTERMEDIATE,
            )

    def test_singleton_id_accepted(self) -> None:
        p = UserProfile(
            id=USER_PROFILE_SINGLETON_ID,
            preset=ProfilePreset.INTERMEDIATE,
        )
        assert p.preset == ProfilePreset.INTERMEDIATE

    def test_base_currency_must_be_three_letters(self) -> None:
        with pytest.raises(ValueError, match="base_currency"):
            UserProfile(
                id=USER_PROFILE_SINGLETON_ID,
                preset=ProfilePreset.INTERMEDIATE,
                base_currency="EURO",
            )


# --- Address ----------------------------------------------------------------------


class TestAddress:
    def test_negative_derivation_index_rejected(self) -> None:
        with pytest.raises(ValueError, match="derivation_index"):
            Address(
                id=uuid4(),
                descriptor_id=uuid4(),
                address="bc1q...",
                derivation_path="m/84'/0'/0'/0/0",
                is_change=False,
                derivation_index=-1,
                label=None,
                first_seen_height=None,
                is_reused=False,
                created_at=NOW,
            )
