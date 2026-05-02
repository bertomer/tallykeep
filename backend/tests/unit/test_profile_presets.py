"""Pure-function tests for the feature-flag preset table and resolver."""

from __future__ import annotations

import pytest

from tallykeep.domain.enums import ProfilePreset
from tallykeep.services.profile_presets import (
    ALL_FEATURE_FLAGS,
    PROFILE_PRESETS,
    is_known_flag,
    resolve_feature_flags,
)


pytestmark = pytest.mark.unit


# --- preset table sanity --------------------------------------------------------


class TestPresetTable:
    @pytest.mark.parametrize(
        "preset",
        [
            ProfilePreset.BEGINNER,
            ProfilePreset.INTERMEDIATE,
            ProfilePreset.SOVEREIGN,
        ],
    )
    def test_each_preset_defines_every_flag(
        self, preset: ProfilePreset
    ) -> None:
        """Every named preset must enumerate every flag — no implicit defaults.

        Spec module 09: 'each flag has a one-line description in a central
        registry; adding a flag in a future version: defaults to false in
        Beginner, true in Intermediate and Sovereign.' We enforce the central
        registry by comparing key sets here."""
        assert set(PROFILE_PRESETS[preset].keys()) == set(ALL_FEATURE_FLAGS)

    def test_custom_preset_not_in_table(self) -> None:
        # CUSTOM is not a defaults source — the resolver builds from overrides.
        assert ProfilePreset.CUSTOM not in PROFILE_PRESETS

    def test_beginner_hides_strongbox_and_vault(self) -> None:
        # Spec module 09 / 11: beginner profile is "one Account, one Purse".
        beginner = PROFILE_PRESETS[ProfilePreset.BEGINNER]
        assert beginner["holding.strongbox.enabled"] is False
        assert beginner["holding.vault.enabled"] is False
        assert beginner["holding.account.enabled"] is True
        assert beginner["holding.purse.enabled"] is True

    def test_sovereign_unlocks_advanced_options(self) -> None:
        sovereign = PROFILE_PRESETS[ProfilePreset.SOVEREIGN]
        assert sovereign["banking.custom_fee_rate.enabled"] is True
        assert sovereign["utxo.coin_control.enabled"] is True
        assert sovereign["banking.rbf.enabled"] is True
        assert sovereign["advanced.api_docs_link"] is True

    def test_intermediate_default_for_sweep_confirmation(self) -> None:
        # CONTEXT.md Q1: confirmed default for INTERMEDIATE.
        intermediate = PROFILE_PRESETS[ProfilePreset.INTERMEDIATE]
        assert intermediate["trading.sweep_confirmation.required"] is True

    def test_sovereign_disables_sweep_confirmation_default(self) -> None:
        sovereign = PROFILE_PRESETS[ProfilePreset.SOVEREIGN]
        assert sovereign["trading.sweep_confirmation.required"] is False


# --- resolver -------------------------------------------------------------------


class TestResolveFeatureFlags:
    def test_named_preset_with_no_overrides_returns_preset_defaults(self) -> None:
        flags = resolve_feature_flags(ProfilePreset.BEGINNER, {})
        assert flags == PROFILE_PRESETS[ProfilePreset.BEGINNER]

    def test_named_preset_with_override_takes_precedence(self) -> None:
        # Beginner has banking.psbt_qr.enabled = False; override to True.
        flags = resolve_feature_flags(
            ProfilePreset.BEGINNER, {"banking.psbt_qr.enabled": True}
        )
        assert flags["banking.psbt_qr.enabled"] is True
        # Other flags untouched.
        assert flags["holding.strongbox.enabled"] is False

    def test_unknown_override_keys_are_ignored(self) -> None:
        flags = resolve_feature_flags(
            ProfilePreset.BEGINNER, {"not.a.real.flag": True}
        )
        # Result still contains exactly the known flag set.
        assert set(flags.keys()) == set(ALL_FEATURE_FLAGS)
        assert "not.a.real.flag" not in flags

    def test_custom_preset_only_uses_overrides(self) -> None:
        flags = resolve_feature_flags(
            ProfilePreset.CUSTOM, {"banking.psbt_file.enabled": True}
        )
        # The single override is True; everything else defaults to False.
        assert flags["banking.psbt_file.enabled"] is True
        assert flags["holding.account.enabled"] is False
        # Still includes every known flag.
        assert set(flags.keys()) == set(ALL_FEATURE_FLAGS)

    def test_resolved_set_contains_every_known_flag(self) -> None:
        for preset in (
            ProfilePreset.BEGINNER,
            ProfilePreset.INTERMEDIATE,
            ProfilePreset.SOVEREIGN,
            ProfilePreset.CUSTOM,
        ):
            flags = resolve_feature_flags(preset, {})
            assert set(flags.keys()) == set(ALL_FEATURE_FLAGS)


class TestIsKnownFlag:
    def test_known_flag_returns_true(self) -> None:
        assert is_known_flag("trading.enabled") is True

    def test_unknown_flag_returns_false(self) -> None:
        assert is_known_flag("not.a.real.flag") is False
