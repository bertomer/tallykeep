"""Pure-function tests for the feature-flag resolver and defaults table."""

from __future__ import annotations

import pytest

from tallykeep.services.profile_presets import (
    ALL_FEATURE_FLAGS,
    DEFAULT_FLAG_VALUES,
    is_known_flag,
    resolve_feature_flags,
)


pytestmark = pytest.mark.unit


# --- defaults table sanity -------------------------------------------------------


class TestDefaultFlagValues:
    def test_defaults_cover_every_known_flag(self) -> None:
        assert set(DEFAULT_FLAG_VALUES.keys()) == set(ALL_FEATURE_FLAGS)

    def test_all_values_are_bool(self) -> None:
        for flag, value in DEFAULT_FLAG_VALUES.items():
            assert isinstance(value, bool), f"{flag} is not bool"

    def test_self_custody_holdings_enabled_by_default(self) -> None:
        assert DEFAULT_FLAG_VALUES["holding.purse.enabled"] is True
        assert DEFAULT_FLAG_VALUES["holding.strongbox.enabled"] is True
        assert DEFAULT_FLAG_VALUES["holding.vault.enabled"] is True
        assert DEFAULT_FLAG_VALUES["holding.account.enabled"] is True

    def test_coin_control_off_by_default(self) -> None:
        assert DEFAULT_FLAG_VALUES["utxo.coin_control.enabled"] is False

    def test_coin_selection_override_off_by_default(self) -> None:
        assert DEFAULT_FLAG_VALUES["banking.coin_selection_per_payment_override"] is False

    def test_sweep_confirmation_required_by_default(self) -> None:
        assert DEFAULT_FLAG_VALUES["trading.sweep_confirmation.required"] is True


# --- resolver -------------------------------------------------------------------


class TestResolveFeatureFlags:
    def test_no_overrides_returns_defaults(self) -> None:
        flags = resolve_feature_flags({})
        assert flags == DEFAULT_FLAG_VALUES

    def test_override_takes_precedence_over_default(self) -> None:
        flags = resolve_feature_flags({"banking.psbt_qr.enabled": False})
        assert flags["banking.psbt_qr.enabled"] is False
        assert flags["holding.strongbox.enabled"] is True

    def test_unknown_override_keys_are_ignored(self) -> None:
        flags = resolve_feature_flags({"not.a.real.flag": True})
        assert set(flags.keys()) == set(ALL_FEATURE_FLAGS)
        assert "not.a.real.flag" not in flags

    def test_result_always_contains_every_known_flag(self) -> None:
        assert set(resolve_feature_flags({}).keys()) == set(ALL_FEATURE_FLAGS)

    def test_multiple_overrides(self) -> None:
        overrides = {
            "utxo.coin_control.enabled": True,
            "banking.rbf.enabled": True,
        }
        flags = resolve_feature_flags(overrides)
        assert flags["utxo.coin_control.enabled"] is True
        assert flags["banking.rbf.enabled"] is True
        assert flags["trading.enabled"] is DEFAULT_FLAG_VALUES["trading.enabled"]


class TestIsKnownFlag:
    def test_known_flag_returns_true(self) -> None:
        assert is_known_flag("trading.enabled") is True

    def test_unknown_flag_returns_false(self) -> None:
        assert is_known_flag("not.a.real.flag") is False
