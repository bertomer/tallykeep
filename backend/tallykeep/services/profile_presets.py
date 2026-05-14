"""Feature-flag registry and resolution (spec module 09).

Resolution rule: the effective flag value for a flag is the user's stored override
(user_profile.feature_flags JSONB) if present, else DEFAULT_FLAG_VALUES[flag].

Resetting to defaults: PATCH /profile with feature_flags:{} clears overrides,
so every subsequent GET /feature-flags returns DEFAULT_FLAG_VALUES.
"""

from __future__ import annotations


# Locked v1 flag set (spec module 09). Adding a flag requires a code change here.
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
    "banking.coin_selection_per_payment_override",
    # Treasury
    "treasury.enabled",
    "treasury.sweep_policy.enabled",
    "treasury.sweep_confirmation.required",
    "treasury.bidirectional_sweeps.shown",
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


DEFAULT_FLAG_VALUES: dict[str, bool] = {
    # Holdings
    "holding.account.enabled":                      True,
    "holding.purse.enabled":                        True,
    "holding.strongbox.enabled":                    True,
    "holding.vault.enabled":                        True,
    "holding.multiple_per_type":                    True,
    # UTXO
    "utxo.detail_view.enabled":                     True,
    "utxo.coin_control.enabled":                    False,
    "utxo.hygiene_flags.shown":                     True,
    # Analysis
    "analysis.blueprint.shown":                     True,
    "analysis.security_discrepancies.shown":        True,
    "analysis.advanced_clustering.shown":           False,
    # Banking
    "banking.custom_fee_rate.enabled":              False,
    "banking.psbt_qr.enabled":                      True,
    "banking.psbt_file.enabled":                    True,
    "banking.address_derivation_view":              True,
    "banking.rbf.enabled":                          False,
    "banking.vault_outgoing_warns":                 True,
    "banking.coin_selection_per_payment_override":  False,
    # Treasury
    "treasury.enabled":                              True,
    "treasury.sweep_policy.enabled":                 True,
    "treasury.sweep_confirmation.required":          True,
    "treasury.bidirectional_sweeps.shown":           True,
    # Notifications
    "notifications.in_app":                         True,
    # Display
    "display.fiat_conversion.enabled":              False,
    # Advanced
    "advanced.show_raw_tx":                         False,
    "advanced.show_descriptors":                    True,
    "advanced.api_docs_link":                       False,
    "advanced.dry_run_sweeps":                      False,
}

assert set(ALL_FEATURE_FLAGS) == set(DEFAULT_FLAG_VALUES), (
    "ALL_FEATURE_FLAGS and DEFAULT_FLAG_VALUES are out of sync"
)


def resolve_feature_flags(overrides: dict[str, bool]) -> dict[str, bool]:
    """Compute the effective flag set: DEFAULT_FLAG_VALUES with user overrides applied.

    Spec module 09: user_profile.feature_flags contains only explicit overrides.
    Missing flags fall back to DEFAULT_FLAG_VALUES. Setting feature_flags:{} resets
    all flags to their defaults.
    """
    return {flag: bool(overrides.get(flag, DEFAULT_FLAG_VALUES[flag])) for flag in ALL_FEATURE_FLAGS}


def is_known_flag(flag_name: str) -> bool:
    return flag_name in ALL_FEATURE_FLAGS
