# 09 — Profiles and Feature Flags

The app adapts its surface area to the user's maturity and personal preferences via **feature flags** — simple booleans that toggle UI and API behavior. Three **preset profiles** provide sensible defaults; the user can override any individual flag, which moves them to a `CUSTOM` profile.

## Feature flags (v1)

Flag names use dotted namespaces: `domain.feature.setting`. All flags are positive (`enable_X` or `X.enabled`); no negations.

### Holding type visibility

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `holding.account.enabled` | true | true | true | Allow creating Account Holdings |
| `holding.purse.enabled` | true | true | true | Allow creating Purse Holdings |
| `holding.strongbox.enabled` | false | true | true | Allow creating Strongbox Holdings |
| `holding.vault.enabled` | false | true | true | Allow creating Vault Holdings |
| `holding.multiple_per_type` | false | true | true | Allow multiple Holdings of the same type |

**Beginner default behavior**: one Account and one Purse, no Strongbox or Vault visible. Migration to Intermediate unlocks Strongbox and Vault.

### UTXO and detail view

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `utxo.detail_view.enabled` | false | true | true | Show UTXO list in Holding view |
| `utxo.coin_control.enabled` | false | false | true | Allow freezing UTXOs and manual coin selection on send |
| `utxo.hygiene_flags.shown` | false | true | true | Display hygiene flag badges on UTXOs |

### Analysis and blueprint

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `analysis.blueprint.shown` | false | true | true | Show Blueprint tab and recommendations |
| `analysis.security_discrepancies.shown` | false | true | true | Show declared-vs-observable discrepancy warnings |
| `analysis.advanced_clustering.shown` | false | false | false | (v2 feature, all profiles default off) |

### Banking — outgoing

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `banking.custom_fee_rate.enabled` | false | false | true | Allow entering sat/vB manually |
| `banking.psbt_qr.enabled` | false | true | true | Offer PSBT export via QR code |
| `banking.psbt_file.enabled` | true | true | true | Offer PSBT export via file download (always on) |
| `banking.address_derivation_view` | false | true | true | Show derivation path in receive view |
| `banking.rbf.enabled` | false | false | true | Replace-By-Fee toggle on outgoing payments (v1.x) |
| `banking.vault_outgoing_warns` | true | true | false | Vault guardrail: warn before outgoing from Vault Holding |

### Trading

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `trading.enabled` | false | true | true | Show Trading section at all |
| `trading.sweep_policy.enabled` | false | true | true | Allow creating sweep policies |
| `trading.sweep_confirmation.required` | true | true | false | Require explicit user confirmation before each sweep execution |
| `trading.bidirectional_sweeps.shown` | false | true | true | Show inter-Holding (non-Account-source) sweeps in UI |

### Notifications and display

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `notifications.in_app` | true | true | true | Show in-app notifications |
| `display.fiat_conversion.enabled` | false | false | false | (v1.1) Show fiat-converted amounts |

### Advanced

| Flag key | Beginner | Intermediate | Sovereign | Controls |
|---|---|---|---|---|
| `advanced.show_raw_tx` | false | false | true | Expose raw tx hex in transaction detail |
| `advanced.show_descriptors` | false | true | true | Show descriptor expression in settings |
| `advanced.api_docs_link` | false | false | true | Show link to OpenAPI Swagger UI |
| `advanced.dry_run_sweeps` | false | false | true | Allow marking SweepPolicies as dry-run |

## Preset definitions (code)

```python
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
        "trading.sweep_confirmation.required":      True,
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
        "analysis.advanced_clustering.shown":       False,    # still a v2 feature
        "banking.custom_fee_rate.enabled":          True,
        "banking.psbt_qr.enabled":                  True,
        "banking.psbt_file.enabled":                True,
        "banking.address_derivation_view":          True,
        "banking.rbf.enabled":                      True,
        "banking.vault_outgoing_warns":             False,    # trust the user
        "trading.enabled":                          True,
        "trading.sweep_policy.enabled":             True,
        "trading.sweep_confirmation.required":      False,    # trust the policy
        "trading.bidirectional_sweeps.shown":       True,
        "notifications.in_app":                     True,
        "display.fiat_conversion.enabled":          False,
        "advanced.show_raw_tx":                     True,
        "advanced.show_descriptors":                True,
        "advanced.api_docs_link":                   True,
        "advanced.dry_run_sweeps":                  True,
    },
}
```

## Flag resolution

At API call time and frontend render time, the effective flag value is computed as follows:

1. If `user_profile.preset == CUSTOM`: value comes from `user_profile.feature_flags` (the JSONB overrides column).
2. Otherwise: value comes from `PROFILE_PRESETS[preset]`, with any explicit overrides in `user_profile.feature_flags` taking precedence.

When the user toggles a single flag while on a non-custom preset, their preset transitions to `CUSTOM` and the *currently-resolved* flag values are snapshot into their overrides — so they are not surprised by future preset-flag changes.

Switching back to a named preset clears `feature_flags` to empty, so the named preset's defaults apply cleanly.

## Preset switching

`PATCH /api/v1/profile` with a new `preset` value triggers a transition. Important behaviors:

- **No data is destroyed.** Switching from Intermediate (with Strongbox and Vault Holdings) to Beginner (which hides them) does not delete the Holdings. They become hidden in the UI but remain in the database. Switching back makes them visible again.
- **Active sweep policies that depend on hidden Holdings continue to run.** This is intentional: turning off a UI flag should not silently change financial behavior. The preset-switch confirmation modal warns the user about this and offers to disable affected policies.
- **Onboarding wizards adapt.** A user on Beginner who creates their first Holding sees a simplified wizard (one Account or one Purse). On Intermediate, the wizard offers all four types.

## User interface implications

The frontend fetches `GET /api/v1/feature-flags` on app load and stores them in a Svelte store. Every UI component that should be flag-gated wraps itself:

```svelte
{#if $flags['utxo.coin_control.enabled']}
  <CoinControlPanel ... />
{/if}
```

Navigation items are similarly gated:
- Beginner: Home, Holdings, Send, Receive, Settings
- Intermediate: adds Trading, Blueprint
- Sovereign: adds Advanced, API Docs

## API implications

Flag-gated endpoints return `403 Forbidden` with an explicit error type when called while the gating flag is false:

```
GET /api/v1/analysis/holding/xxx/blueprint
  → 403 {
      "type": "/errors/feature-disabled",
      "title": "Feature disabled",
      "detail": "analysis.blueprint.shown is false in the current profile."
    }
```

This way an external API consumer (in the future) gets a clear signal rather than a silent empty response.

## Onboarding selection

On first launch, the user sees a profile selector:

> Welcome. Pick a starting profile.
>
> **Beginner**: One Account, one Purse. Simple send and receive. No exchange integration.
>
> **Intermediate**: Multiple Holdings by type, hygiene warnings, security analysis, trading and sweep automation.
>
> **Sovereign**: Everything. Coin control, custom fees, replace-by-fee, unattended sweeps, API access.
>
> *You can change this anytime in Settings.*

Default pre-selection: **Intermediate**. Beginner is for users who explicitly want hand-holding; Sovereign is for users who already know what they want.

## Flag naming discipline

- Keys are dotted namespaces.
- Each flag has a one-line description in a central registry (`FEATURE_FLAG_DEFINITIONS`) used by the UI to render help text.
- No flag is a negation.
- Adding a flag in a future version: defaults to false in Beginner, true in Intermediate and Sovereign, unless the flag is itself an advanced-only feature (then default false everywhere except Sovereign).
- Removing a flag: keep for one major version as deprecated (still readable, no longer actionable), then remove.

## Versioning

The set of feature flags is versioned along with the API version. Adding flags is non-breaking. Removing or renaming flags is a `/api/v2/` change.
