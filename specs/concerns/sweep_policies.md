# Sweep policies — cross-Holding automated rebalancing

The **SweepPolicy** primitive moves value automatically from one
Holding to another under specified conditions. Generalized:
**any Holding to any Holding**, with a safety validator that
warns but never blocks. The user is the final authority.

## Why this primitive matters

Two product patterns are powered by the same primitive:

- **Minimum-exposure trading** (the bread-and-butter pre-shipping
  use case) — Account → Strongbox/Vault. The CustodialProvider
  is pass-through liquidity; SweepPolicies enforce *get the BTC
  off the provider as fast as policy allows.* See
  `holdings/01_account.md` for the Account-side product
  principle.
- **Holding-to-Holding rebalancing** — e.g. Strongbox → Purse
  ("top up the spending stack"), Purse → Strongbox ("daily
  spending bounded"), Strongbox → Vault ("promote to long-term").
  **Purse-on-device → anywhere is in dev-phase scope** (sweep
  fires on the Capacitor device that holds the seed; biometric
  prompt + native sign + broadcast). **Strongbox- and
  Vault-source sweeps stay scheduled-reminder shape** (no
  auto-execution; the user signs externally) — architecturally
  present, UI surface deferred per `future_iterations.md`
  "Holding-to-Holding sweeps beyond Account-originated".

The Treasury layer is the primary user of this primitive (for
Account → non-Account sweeps), but the primitive itself is
cross-cutting.

## Trigger types

**Scheduled** — cron-driven via APScheduler in the
SweepScheduler component.

```json
{
  "trigger_type": "scheduled",
  "trigger_configuration": {
    "cron_expression": "0 3 * * FRI",
    "timezone": "Europe/Zurich"
  }
}
```

**Threshold** — fires when the source balance crosses a value,
with cooldown to avoid flapping.

```json
{
  "trigger_type": "threshold",
  "trigger_configuration": {
    "threshold_sats": 5000000,
    "cooldown_hours": 24
  }
}
```

The SweepEngine subscriber listens for
`treasury.custodial.balance_changed` events and re-evaluates
threshold policies for the affected Holding.

**Manual** — fires on user request only.

## Safety validator (warns, does not block)

When a SweepPolicy is created or modified, the validator runs
and computes `safety_warnings`. The policy **cannot be enabled
until all warnings are acknowledged**. The user explicitly
acknowledges each.

Validator rules (current minimum — see open question below):

| Warning | Severity | Condition |
|---|---|---|
| `no_maximum_cap_set` | medium | `maximum_per_period_sats` is None for non-trivial amounts |
| `unverified_whitelist_on_provider` | high | Source Holding is an Account whose CustodialProvider whitelist could not be verified via API |

The warnings persist on the policy row. Once acknowledged, the
policy can be enabled. Re-running the validator on policy
modification produces fresh warnings; if a previously
acknowledged warning kind reappears unchanged, its
acknowledgement carries over; if the warning reappears with
different parameters, acknowledgement is cleared and the user
must re-confirm.

The "warn don't block" discipline is locked: the validator's job
is to make sure the user knows what they're doing, not to
second-guess them. Risky configurations are allowed if the user
acknowledges.

**Open question — extended validator rules.** Earlier drafts of
the validator carried three additional warnings —
`destination_is_custodial`, `destination_keys_on_host`,
`same_security_tier` — that opinionated which destination shapes
"defeat minimum-exposure." Those warnings have been removed
from the current rule-set because:

- *Decumulation is a legitimate flow* (saved → custodial to
  sell, or to pay a bill that needs fiat off-ramp). Flagging
  Account-as-destination at `high` reads the wrong way for that
  use case.
- *On-device-keys Purse* is not inherently more dangerous as a
  sweep destination than another Purse; if anything, a
  TallyKeep-managed Purse with biometric-gated keys is a tighter
  surface than an external hot wallet.
- *Same-tier sweeps* (Strongbox → Strongbox) can be legitimate
  for rotation / device migration; flagging is informational at
  best.

The full set of "what should the safety validator warn about?"
is open arbitration pending the brainstorm session once all
four Holding types are working in code (per
`pre-implementation.md` item `sweep-validator-extended-rules`).
Until then the validator runs with the two rules above only.

## Execution path

When `treasury.sweep.triggered` fires (from the scheduler) or
`treasury.custodial.balance_changed` matches a threshold policy:

### 1. Pre-check

- Fetch fresh balance from the source (for Account, fresh
  provider call; for non-Account Holdings, sum of confirmed
  UTXOs).
- Compute `intended_amount = balance - minimum_balance_sats`.
- Abort if `intended_amount <= 0`.
- If `maximum_per_period_sats` is set, check accumulated daily
  total against the cap.
- Persist a `sweep_execution` row with `status=REQUESTED`.
  **Persist first** (per `01_architecture.md` persistence-first
  pattern).

### 2. User-confirmation gate (if `requires_user_confirmation=true`)

- Set `sweep_execution.status=AWAITING_USER_CONFIRMATION`.
- Emit the trigger event so the UI shows a confirmation prompt.
- Wait for user response (endpoint in `api/openapi.yaml`).
- If denied, set `status=CANCELLED` and end.

### 3. Dispatch (per source-Holding-type)

The dispatch differs by source:

| Source | Dispatch |
|---|---|
| **Account** | Call `CustodialProviderAdapter.withdraw(amount, whitelist_address)`. The adapter wraps ccxt and normalizes provider quirks. |
| **TallyKeep-managed / External-imported Purse** on the device holding the seed | Construct a PaymentRequest (`concerns/outflow.md`), sign in-app via NativeBridge with biometric prompt, broadcast. |
| **Strongbox / Vault** | Construct a PaymentRequest awaiting external signing. Reduces to a **scheduled reminder** — see "Non-auto sweeps" below. |
| **TallyKeep-managed / External-imported Purse** on any other client, or **External-watch-only Purse** | Sweep cannot execute. UX surfaces "go sign on the device that holds the seed" or "spending happens in the source wallet." |

On dispatch, set `sweep_execution.status=DISPATCHED` and store
any `provider_withdrawal_id`.

### 4. On-chain pending

Once the provider acknowledges (Account) or the PSBT is
broadcast (non-Account), set `status=ONCHAIN_PENDING` and store
`expected_txid`. Emit the executed event.

### 5. Reconciliation

When the chain scanner detects the corresponding incoming
transaction at the destination (matching by amount and
approximate timing), it links it. Set
`sweep_execution.status=COMPLETED`, store `confirmed_txid` and
`completed_at`.

Auto-suggest the resulting LedgerEntry's category as
`CUSTODIAL_WITHDRAWAL` (for Account sources) or
`INTERNAL_TRANSFER` (for inter-Holding rebalances). User
confirms.

### 6. Failure paths

- Provider rejection (insufficient funds, KYC block, withdrawal
  limit): set `status=FAILED`, store `error_message`, emit the
  failure event. Disable further attempts on this policy until
  user reviews.
- Network error: retry with exponential backoff up to 3
  attempts within the same execution; then mark FAILED.

## Non-auto sweeps (Strongbox, Vault, External-watch-only Purse)

Sources whose keys are not on a TallyKeep surface that can sign
automatically reduce sweeps to **scheduled reminders**:

- Strongbox / Vault → anywhere: the SweepPolicy fires the
  trigger, the SweepEngine constructs the PaymentRequest, and
  the policy enters `AWAITING_USER_CONFIRMATION` indefinitely
  until the user processes it externally. The user's signing
  device must be reachable when the policy fires; if not, the
  sweep waits until the user is.
- External-watch-only Purse → anywhere: not feasible. Spending
  from this Holding type happens in the source wallet, not in
  TallyKeep. The SweepPolicy can be created (the validator
  warns it's not auto) but won't execute; it surfaces as a
  manual reminder in the UI.

This is the "scheduled reminder" pattern. Pre-shipping ships
Account-source sweeps with full automation; non-Account-source
sweeps are architecturally supported but UX-deferred (per
`future_iterations.md`).

## Daily caps and safety controls

- **`maximum_per_period_sats`** — enforced. Accumulated total of
  completed sweeps in the rolling 24h window is checked before
  each execution.
- **Dry-run flag** per policy (`is_dry_run` field) — when true,
  the sweep evaluates and persists `sweep_execution` rows but
  does not dispatch. Useful for testing setup. Gated by
  `advanced.dry_run_sweeps`.
- **Global pause** — sets a runtime-configuration flag. While
  paused, the SweepEngine consumes events but does not execute.
  UI surfaces prominently.
- **Per-policy `requires_user_confirmation`** — when true, every
  execution prompts. The default for newly-created policies is
  controlled by the `treasury.sweep_confirmation.required`
  feature flag (default `true`); users can change it per policy
  thereafter.

## Account → Strongbox/Vault sweep mechanics (the common path)

The bread-and-butter use case for pre-shipping:

```
Account (Kraken) ──▶ SweepPolicy ──▶ Strongbox (cold reserve)

Trigger fires (scheduled or threshold)
  │
  ▼
SweepEngine pre-check
  │
  ▼
[optional: AWAITING_USER_CONFIRMATION]
  │
  ▼
CustodialProviderAdapter.withdraw(
  amount = intended_amount,
  address = whitelist_address (= a Strongbox-owned address)
)
  │
  ▼
Provider returns withdrawal id
  │ (provider broadcasts on-chain when its internal queue clears)
  ▼
ChainListener detects incoming tx at the destination Address
  │
  ▼
LedgerEntry created with direction=INCOMING and link to destination Holding
  │
  ▼
SweepEngine matches expected_txid → confirmed_txid
  │
  ▼
sweep_execution.status = COMPLETED
LedgerEntry suggested category = CUSTODIAL_WITHDRAWAL
```

## Inter-Holding rebalancing (Holding-to-Holding)

The same primitive supports user-driven rebalancing. Examples:

- Strongbox → Purse, top up to 50,000 sats every Monday.
- Purse → Strongbox, threshold-based when daily-spending
  balance exceeds a cap.
- Strongbox → Vault, threshold-based when reserve exceeds
  600,000 sats ("promote to long-term").

Mechanics differ from Account-source sweeps: the SweepEngine
constructs a PaymentRequest, the user signs (in-app on
Capacitor for on-device Purses, externally for Strongbox / Vault),
broadcast happens via the normal outflow flow. The sweep is
driven by the policy but the signing remains user-controlled.

UX for non-Account-source sweeps is deferred (per
`future_iterations.md` "Holding-to-Holding sweeps beyond
Account-originated"). The architectural primitive ships pre-
shipping; only the UI surface is deferred.

## What the user sees (target UX)

The Treasury view shows, per Account Holding:

- Active SweepPolicy summaries ("Auto-sweep weekly every Friday
  at 03:00 to Strongbox").
- "Sweep now" button.
- Recent sweep history with status badges.

For non-Account Holdings with outgoing SweepPolicies
(rebalancing), the same panel appears on the Holding's detail
page when that UX ships.

Specific layout and component naming lives in `UI/README.md`
and the iteration that ships the sweep-creation UI.

## Deferred

| Item | Tracked in |
|---|---|
| UX for Holding-to-Holding sweeps (non-Account source) | `future_iterations.md` "Holding-to-Holding sweeps beyond Account-originated" |
| DCA (recurring scheduled purchases) — depends on order placement | `future_iterations.md` "DCA primitive" |