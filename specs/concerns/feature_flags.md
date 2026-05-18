# Feature Flags

The app adapts its surface area to the user's preferences via
**feature flags** — simple booleans that toggle UI and API behavior.
There are no named user identities ("Beginner / Intermediate /
Sovereign") and no preset switching; the user has *their setup*, not
a tier.

Initial flag values are seeded by **onboarding answers**: a small
set of questions asked once at first launch. The answers map to a
default flag bundle. After that, the user toggles any flag
individually from Settings; there is no concept to "switch back" to,
because there is no concept the user belongs to.

This shape was chosen over named presets because:

- Bundling expertise + assets + usage + density-preference into a
  single label compresses dimensions that are independent. A
  long-time Bitcoin developer with one Purse (because they don't
  hold much yet) and a newcomer with multiple Holdings are both
  poorly served by any single tier name.
- "Beginner" reads as deficient-to-be-overcome; "Sovereign" carries
  ideological framing that excludes users who want the full feature
  set without the political identity.
- The configuration is just the configuration. There is nothing for
  the user to be "Custom" relative to.

## Feature flag catalog

Flag names use dotted namespaces: `domain.feature.setting`. All
flags are positive (`enable_X` or `X.enabled`); no negations.

### UTXO and detail view

| Flag key | Description |
|---|---|
| `utxo.detail_view.enabled` | Show UTXO list in Holding view |
| `utxo.coin_control.enabled` | Allow freezing UTXOs and manual coin selection on send |
| `utxo.hygiene_flags.shown` | Display hygiene flag badges on UTXOs |

### Analysis

| Flag key | Description |
|---|---|
| `analysis.blueprint.shown` | Show Blueprint tab and recommendations (deferred — see `backlog/blueprint-analysis.md`) |
| `analysis.security_discrepancies.shown` | Show declared-vs-observable discrepancy warnings |
| `analysis.advanced_clustering.shown` | Clustering graph (deferred — see `backlog/blueprint-analysis.md`) |

### Banking — outgoing

| Flag key | Description |
|---|---|
| `banking.custom_fee_rate.enabled` | Allow entering sat/vB manually |
| `banking.psbt_qr.enabled` | Offer PSBT export via QR code |
| `banking.psbt_file.enabled` | Offer PSBT export via file download (always on) |
| `banking.address_derivation_view` | Show derivation path in receive view |
| `banking.rbf.enabled` | Replace-By-Fee toggle (deferred — see `backlog/replace-by-fee-rbf-support.md`) |
| `banking.vault_outgoing_warns` | Vault guardrail: warn before outgoing from Vault Holding |
| `banking.coin_selection_per_payment_override` | Allow choosing coin-selection algorithm per payment |

### Treasury

| Flag key | Description |
|---|---|
| `treasury.enabled` | Show Treasury section at all |
| `treasury.sweep_policy.enabled` | Allow creating sweep policies |
| `treasury.sweep_confirmation.required` | Require explicit user confirmation before each sweep execution |
| `treasury.bidirectional_sweeps.shown` | Show inter-Holding (non-Account-source) sweeps in UI |

### Notifications and display

| Flag key | Description |
|---|---|
| `notifications.in_app` | Show in-app notifications |
| `display.fiat_conversion.enabled` | Show fiat-converted amounts (deferred — see `backlog/fiat-display.md`) |

### Advanced

| Flag key | Description |
|---|---|
| `advanced.show_raw_tx` | Expose raw tx hex in transaction detail |
| `advanced.show_descriptors` | Show descriptor expression in settings |
| `advanced.api_docs_link` | Show link to OpenAPI Swagger UI |
| `advanced.dry_run_sweeps` | Allow marking SweepPolicies as dry-run |

## Onboarding-driven defaults

A small set of onboarding questions seeds initial flag values. The
**specific question wording, ordering, and answer-to-flag mapping
are designed in the onboarding UX iteration**, not pre-locked here.
What is locked is the architectural shape:

- 2–3 questions, asked once at first launch.
- Answers are not stored as domain state. The backend never sees a
  "user identity" (Beginner / Sovereign / etc.). It sees only the
  resulting flag values.
- A default flag bundle (the "no answers given" fallback) lands the
  user in a moderate, banking-first configuration.
- After onboarding, the user toggles any individual flag from
  Settings. There is no "preset" to change back to.

The questions should bifurcate the catalog meaningfully. Likely
candidates (UX iteration confirms):

- Bitcoin holding posture: do they already hold Bitcoin? Where (an
  exchange, a phone wallet, a hardware wallet, multiple of these,
  none yet)?
- Detail-density preference: do they want technical Bitcoin details
  (UTXOs, fees, descriptors) visible by default, or surfaced only
  on demand?
- Custodial connection: will they connect an exchange / broker
  account to TallyKeep, or use TallyKeep purely for self-custody?

These map to flag bundles in the onboarding-iteration design. The
mapping is implementation, not domain — refining it later does not
require an ADR or a domain-model change.

## Default flag bundle (fallback when onboarding is skipped)

Banking-first, moderate visibility. Hides the most advanced flags;
shows everything a new user reasonably needs.

```python
DEFAULT_FLAG_VALUES: dict[str, bool] = {
    # UTXO
    "utxo.detail_view.enabled":                 False,
    "utxo.coin_control.enabled":                False,
    "utxo.hygiene_flags.shown":                 False,
    # Analysis
    "analysis.blueprint.shown":                 False,    # deferred per backlog/blueprint-analysis.md
    "analysis.security_discrepancies.shown":    True,
    "analysis.advanced_clustering.shown":       False,    # deferred per backlog/blueprint-analysis.md
    # Banking
    "banking.custom_fee_rate.enabled":          False,
    "banking.psbt_qr.enabled":                  True,
    "banking.psbt_file.enabled":                True,
    "banking.address_derivation_view":          False,
    "banking.rbf.enabled":                      False,    # deferred per backlog/replace-by-fee-rbf-support.md
    "banking.vault_outgoing_warns":             True,
    "banking.coin_selection_per_payment_override": False,
    # Treasury
    "treasury.enabled":                          True,
    "treasury.sweep_policy.enabled":             True,
    "treasury.sweep_confirmation.required":      True,
    "treasury.bidirectional_sweeps.shown":       True,
    # Notifications
    "notifications.in_app":                     True,
    # Display
    "display.fiat_conversion.enabled":          False,    # deferred per backlog/fiat-display.md
    # Advanced
    "advanced.show_raw_tx":                     False,
    "advanced.show_descriptors":                False,
    "advanced.api_docs_link":                   False,
    "advanced.dry_run_sweeps":                  False,
}
```

The onboarding-iteration design tweaks individual values based on
answers. Without onboarding, the user lands here.

## Flag resolution

At API call time and frontend render time, the effective flag value is:

1. The value in `user_profile.feature_flags` (the JSONB column),
   if present for that flag key.
2. Otherwise, the value in `DEFAULT_FLAG_VALUES`.

The resolution is a simple lookup. There is no preset layer between
defaults and overrides.

## Hidden Holdings vs disabled creation

Turning off `holding.strongbox.enabled` (for example) does **not**
delete or hide existing Strongbox Holdings; it disables *creating
new ones*. Existing Holdings remain visible and operable. This
prevents flag toggles from silently changing financial behavior.

If a future iteration wants to add "hide Holdings of disabled types
from the UI," that is a separate flag (`holding.hide_disabled_types`
or similar) with its own semantics, decided in the iteration that
introduces it.

## User interface implications

The frontend fetches `GET /api/v1/feature-flags` on app load and
stores them in a Svelte store. Every UI component that should be
flag-gated wraps itself:

```svelte
{#if $flags['utxo.coin_control.enabled']}
  <CoinControlPanel ... />
{/if}
```

Navigation items are similarly gated. There is no preset-driven
nav-item list; each nav item names the flag(s) it requires.

## API implications

Flag-gated endpoints return `403 Forbidden` with
`/errors/feature-disabled` when called while the gating flag is
false. See `04_api_conventions.md` §"Flag-gated endpoints".

`PATCH /api/v1/profile` accepts individual flag overrides via the
`feature_flags` field (a partial dict). It does **not** accept a
preset name. Resetting to defaults is done by setting
`feature_flags: {}` (empty) — this clears overrides and the
defaults apply.

## Onboarding UI contract (architectural)

On first launch, the user is asked the onboarding questions.
Specific copy and ordering are in the onboarding mockups; the
architectural contract:

- The questions are presented inside the onboarding flow, between
  the passphrase / hosting-choice steps and the home page.
- Answering populates `user_profile.feature_flags` with the
  resulting bundle.
- Skipping onboarding (e.g., re-launch after partial completion) is
  allowed; flags fall back to `DEFAULT_FLAG_VALUES`.
- Onboarding is not re-run automatically. Users adjust flags in
  Settings thereafter.

## Flag naming discipline

- Keys are dotted namespaces.
- Each flag has a one-line description in a central registry
  (`FEATURE_FLAG_DEFINITIONS`) used by the UI to render help text.
- No flag is a negation.
- Removing a flag: keep for one major version as deprecated (still
  readable, no longer actionable), then remove.

## Versioning

The set of feature flags is versioned along with the API version.
Adding flags is non-breaking. Removing or renaming flags is a
`/api/v2/` change.