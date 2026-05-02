"""Feature-flag preset definitions (spec module 09).

Three named presets — Beginner, Intermediate, Sovereign — each defining a complete
flag set. Plus a `CUSTOM` preset, which means "the user's overrides in
`user_profile.feature_flags` take precedence; the named-preset defaults are not used."

Resolution rules (spec module 09):
  - If `preset == CUSTOM`: value comes from `user_profile.feature_flags` (the JSONB
    overrides column). Anything not present there returns False.
  - Otherwise: start from `PROFILE_PRESETS[preset]`, then apply any explicit
    overrides in `user_profile.feature_flags` on top.

When the user toggles a single flag while on a non-custom preset, the API switches
the preset to CUSTOM and snapshots the currently-resolved flags into the overrides
column — so future preset-flag changes do not surprise them.
"""

from __future__ import annotations

from tallykeep.domain.enums import ProfilePreset


# Locked v1 flag set (spec module 09). Adding a new flag elsewhere requires a code
# change here too — kept central so the API surface and the resolution logic stay
# in sync.
ALL_FEATURE_FLAGS: tuple[str, ...] = (
    # Holdings
    "holding.account.enabled",
    "holding.purse.enabled",
    "holding.strongbox.enabled",
    "holding.vault.enabled",
    "holding.multiple_per_type",
    # UTXO and detail view
    "utxo.detail_view.enabled",
    "utxo.coin_control.enabled",
    "utxo.hygiene_flags.shown",
    # Analysis
    "analysis.blueprint.shown",
    "analysis.security_discrepancies.shown",
    "analysis.advanced_clustering.shown",
    # Banking
    "banking.custom_fee_rate.enabled",
    "banking.psbt_qr.enabled",
    "banking.psbt_file.enabled",
    "banking.address_derivation_view",
    "banking.rbf.enabled",
    "banking.vault_outgoing_warns",
    # Trading
    "trading.enabled",
    "trading.sweep_policy.enabled",
    "trading.sweep_confirmation.required",
    "trading.bidirectional_sweeps.shown",
    # Notifications
    "notifications.in_app",
    # Display
    "display.fiat_conversion.enabled",
    # Advanced
    "advanced.show_raw_tx",
    "advanced.show_descriptors",
    "advanced.api_docs_link",
    "advanced.dry_run_sweeps",
)


PROFILE_PRESETS: dict[ProfilePreset, dict[str, bool]] = {
    ProfilePreset.BEGINNER: {
        # Holdings
        "holding.account.enabled":                  True,
        "holding.purse.enabled":                    True,
        "holding.strongbox.enabled":                False,
        "holding.vault.enabled":                    False,
        "holding.multiple_per_type":                False,
        # UTXO
        "utxo.detail_view.enabled":                 False,
        "utxo.coin_control.enabled":                False,
        "utxo.hygiene_flags.shown":                 False,
        # Analysis
        "analysis.blueprint.shown":                 False,
        "analysis.security_discrepancies.shown":    False,
        "analysis.advanced_clustering.shown":       False,
        # Banking
        "banking.custom_fee_rate.enabled":          False,
        "banking.psbt_qr.enabled":                  False,
        "banking.psbt_file.enabled":                True,
        "banking.address_derivation_view":          False,
        "banking.rbf.enabled":                      False,
        "banking.vault_outgoing_warns":             True,
        # Trading
        "trading.enabled":                          False,
        "trading.sweep_policy.enabled":             False,
        "trading.sweep_confirmation.required":      True,
        "trading.bidirectional_sweeps.shown":       False,
        # Notifications
        "notifications.in_app":                     True,
        # Display
        "display.fiat_conversion.enabled":          False,
        # Advanced
        "advanced.show_raw_tx":                     False,
        "advanced.show_descriptors":                False,
        "advanced.api_docs_link":                   False,
        "advanced.dry_run_sweeps":                  False,
    },
    ProfilePreset.INTERMEDIATE: {
        "holding.account.enabled":                  True,
        "holding.purse.enabled":                    True,
        "holding.strongbox.enabled":                True,
        "holding.vault.enabled":                    True,
        "holding.multiple_per_type":                True,
        "utxo.detail_view.enabled":                 True,
        "utxo.coin_control.enabled":                False,
        "utxo.hygiene_flags.shown":                 True,
        "analysis.blueprint.shown":                 True,
        "analysis.security_discrepancies.shown":    True,
        "analysis.advanced_clustering.shown":       False,
        "banking.custom_fee_rate.enabled":          False,
        "banking.psbt_qr.enabled":                  True,
        "banking.psbt_file.enabled":                True,
        "banking.address_derivation_view":          True,
        "banking.rbf.enabled":                      False,
        "banking.vault_outgoing_warns":             True,
        "trading.enabled":                          True,
        "trading.sweep_policy.enabled":             True,
        "trading.sweep_confirmation.required":      True,  # spec Q1: confirmed default
        "trading.bidirectional_sweeps.shown":       True,
        "notifications.in_app":                     True,
        "display.fiat_conversion.enabled":          False,
        "advanced.show_raw_tx":                     False,
        "advanced.show_descriptors":                True,
        "advanced.api_docs_link":                   False,
        "advanced.dry_run_sweeps":                  False,
    },
    ProfilePreset.SOVEREIGN: {
        "holding.account.enabled":                  True,
        "holding.purse.enabled":                    True,
        "holding.strongbox.enabled":                True,
        "holding.vault.enabled":                    True,
        "holding.multiple_per_type":                True,
        "utxo.detail_view.enabled":                 True,
        "utxo.coin_control.enabled":                True,
        "utxo.hygiene_flags.shown":                 True,
        "analysis.blueprint.shown":                 True,
        "analysis.security_discrepancies.shown":    True,
        "analysis.advanced_clustering.shown":       False,  # still a v2 feature
        "banking.custom_fee_rate.enabled":          True,
        "banking.psbt_qr.enabled":                  True,
        "banking.psbt_file.enabled":                True,
        "banking.address_derivation_view":          True,
        "banking.rbf.enabled":                      True,
        "banking.vault_outgoing_warns":             False,  # trust the user
        "trading.enabled":                          True,
        "trading.sweep_policy.enabled":             True,
        "trading.sweep_confirmation.required":      False,  # trust the policy
        "trading.bidirectional_sweeps.shown":       True,
        "notifications.in_app":                     True,
        "display.fiat_conversion.enabled":          False,
        "advanced.show_raw_tx":                     True,
        "advanced.show_descriptors":                True,
        "advanced.api_docs_link":                   True,
        "advanced.dry_run_sweeps":                  True,
    },
}


def resolve_feature_flags(
    preset: ProfilePreset,
    overrides: dict[str, bool],
) -> dict[str, bool]:
    """Compute the effective flag set for the given preset + overrides.

    Spec module 09:
      - CUSTOM preset: only `overrides` is considered. Missing flags default False.
      - Named preset: start from preset defaults, apply overrides on top.
    """
    if preset == ProfilePreset.CUSTOM:
        return {flag: bool(overrides.get(flag, False)) for flag in ALL_FEATURE_FLAGS}

    base = PROFILE_PRESETS[preset]
    return {flag: bool(overrides.get(flag, base[flag])) for flag in ALL_FEATURE_FLAGS}


def is_known_flag(flag_name: str) -> bool:
    return flag_name in ALL_FEATURE_FLAGS
