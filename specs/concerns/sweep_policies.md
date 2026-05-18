# Sweep policies — cross-Holding automated rebalancing

The **SweepPolicy** primitive moves BTC automatically from one
Holding to another under specified conditions. Generalized:
**any Holding to any Holding**, in any direction, with a safety
validator that warns but never blocks. The user is the final
authority.

## Why this primitive matters

SweepPolicies are the mechanism that enforces the **minimum-
exposure trading** principle (per `holdings/01_account.md` —
custodial providers are pass-through liquidity, not storage):
BTC sits at a venue only as long as a trade window requires,
the user controls when value enters and leaves. The primitive
also serves as the general inter-Holding rebalancing tool.
Three product patterns share the same primitive, all in
dev-phase scope at the architectural level:

- **Outflow** (Account → TK Holding) — sweep BTC off a custodial
  provider into a self-custody Holding as fast as policy allows.
  The bread-and-butter accumulation pattern: fiat → BTC at the
  venue (user trades on the provider's site) → BTC at self-
  custody (SweepPolicy fires). Minimum-exposure trading in the
  buy direction. Uses the provider's withdraw API via the
  Account's withdrawal credential.
- **Inflow** (TK Holding → Account) — push BTC from a self-
  custody Holding to a custodial provider only when the user is
  about to sell. The bread-and-butter decumulation pattern: BTC
  at self-custody → BTC at the venue (SweepPolicy fires) → fiat
  off the venue (user trades on the provider's site, fiat exit
  on the provider's surface). Minimum-exposure trading in the
  sell direction. Composes a PSBT on the source-Holding side,
  broadcasts to the Account's pinned deposit address.
- **Inter-Holding rebalancing** (TK Holding → TK Holding) — e.g.
  Strongbox → Purse ("top up the spending stack"), Purse →
  Strongbox ("daily spending bounded"), Strongbox → Vault
  ("promote to long-term"). PSBT-driven on both sides. Not
  custodian-related; same primitive, different goal.

The directionality is unconstrained at the type level. Whether a
specific direction makes sense is the user's call; the validator
makes sure they know what they're doing.

**Source-side signing capability gates auto-execution:**

- **Account source** (outflow) — auto-executes via the provider's
  withdraw API.
- **Purse-on-device source** (inflow or rebalance, on the
  Capacitor device that holds the seed) — auto-executes via
  biometric prompt + native sign + broadcast.
- **Strongbox / Vault source** — reduces to a scheduled reminder
  (no auto-execution; the user signs externally). Architecturally
  present, UI surface deferred per `future_iterations.md`
  "Holding-to-Holding sweeps beyond Account-originated".

The Treasury layer is the primary user of the primitive for
Account-touching flows (outflow and inflow); the same primitive
also drives rebalancing between TK Holdings.

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
were "wrong" without a clear use-case basis. Those warnings have
been removed from the current rule-set because:

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

Dispatch differs by source — destination kind (Account vs TK
Holding) determines where the BTC lands but does not change the
source-side dispatch:

| Source | Dispatch |
|---|---|
| **Account** (outflow only — Account-source policies always have a TK-Holding destination per the whitelist invariant) | Call `CustodialProviderAdapter.withdraw(amount, whitelist_address)`. The adapter wraps ccxt and normalizes provider quirks. |
| **TallyKeep-managed / External-imported Purse** on the device holding the seed (inflow or rebalance) | Construct a PaymentRequest (`concerns/outflow.md`), sign in-app via NativeBridge with biometric prompt, broadcast to the destination address. For inflow, the destination address is the destination Account's `deposit_address`; for rebalance, it's a derived address of the destination TK Holding. |
| **Strongbox / Vault** (inflow or rebalance) | Construct a PaymentRequest awaiting external signing; destination address resolved the same way as above. Reduces to a **scheduled reminder** — see "Non-auto sweeps" below. |
| **TallyKeep-managed / External-imported Purse** on any other client, or **External-watch-only Purse** | Sweep cannot execute. UX surfaces "go sign on the device that holds the seed" or "spending happens in the source wallet." |

On dispatch, set `sweep_execution.status=DISPATCHED` and store
any `provider_withdrawal_id`.

### 4. On-chain pending

Once the provider acknowledges (Account) or the PSBT is
broadcast (non-Account), set `status=ONCHAIN_PENDING` and store
`expected_txid`. Emit the executed event.

### 5. Reconciliation

Reconciliation closes the loop between three sources of truth: the
TK domain (the `sweep_execution` row TK wrote at pre-check), the
provider-side ledger (a `custodial_ledger_entry` row mirrored from
the provider's feed per ADR-0013), and the chain-side ledger (a
`LedgerEntry` produced by the chain scanner). Two-sided matching;
both sides may fire in either order depending on the provider's
internal queue and on-chain confirmation timing.

**Chain-side matching (was: the only side).** When the chain
scanner detects the corresponding incoming transaction at the
destination — matching by destination address (and, for Account
outflows, the whitelist address) plus amount within tolerance plus
approximate timing — it links the resulting chain-side `LedgerEntry`
to the pending `sweep_execution`. Set
`sweep_execution.status=COMPLETED`, store `confirmed_txid` and
`completed_at`. Auto-suggest the resulting LedgerEntry's category
as `CUSTODIAL_WITHDRAWAL` (for Account sources) or
`INTERNAL_TRANSFER` (for inter-Holding rebalances). User confirms.

**Custodial-side matching (per ADR-0013).** The reconciler
subscriber listens to `treasury.custodial.ledger_entry_added`. On a
new entry of `kind=withdrawal` (Account is the source side) or
`kind=deposit` (Account is the destination side), it attempts to
match against pending `sweep_execution` rows:

| Direction | Match criteria |
|---|---|
| **Outflow** (Account → TK Holding) — incoming `withdrawal` entry on this Account | Same `custodial_provider_id`; sweep_execution status in `(REQUESTED, AWAITING_USER_CONFIRMATION, DISPATCHED)`; amount within tolerance (configurable, default ±provider-reported fee or a small fraction of intended amount); timestamp within window (configurable, default ±N minutes from `sweep_execution.triggered_at`). |
| **Inflow** (TK Holding → Account) — incoming `deposit` entry on this Account | Same `custodial_provider_id`; sweep_execution status in `(DISPATCHED, ONCHAIN_PENDING)`; amount within tolerance (allowing for on-chain fee deduction); timestamp within window (default wider — provider deposit credits lag on-chain confirmation); **address match** against the Account's pinned `deposit_address` (the provider should not credit a different address, but the check is cheap insurance). |

On match, the reconciler:

- Populates `custodial_ledger_entry.linked_sweep_execution_id`,
  `linked_counterparty_holding_id` (the other side of the sweep —
  `destination_holding_id` for an outflow, `source_holding_id` for
  an inflow), and `linked_chain_ledger_entry_id` (if the chain side
  has already landed; otherwise null, set later when the chain
  matcher fires).
- Sets `custodial_ledger_entry.reconciled_at = NOW()`.
- For outflows: advances the `sweep_execution` to `DISPATCHED` if
  not already (the provider just acknowledged), stores the
  provider's withdrawal id in `provider_withdrawal_id`.
- For inflows: advances the `sweep_execution` to `COMPLETED` once
  both sides have linked (chain leg + provider deposit credit).

On no-match within the time window, the reconciler sets
`reconciled_at = NOW()` with all linkage FKs still null. The entry
is pure observation — the user did this on the provider's site, not
through TK. Honest framing; no judgment.

**Conservative matching is locked.** False positives ("TK reports a
sweep completed, but actually the user did a manual withdrawal at
the same time for the same amount") are a trust break. False
negatives just leave a `custodial_ledger_entry` row unlinked, which
is the same display as a true external action. When the matcher is
ambiguous between two candidate `sweep_execution` rows, it links to
neither and flags the entry for the next iteration's "manual
linkage" UI surface (deferred).

**Three-way coherence.** After both sides have fired, the linkage
graph for a successful TK-initiated flow is:

```
sweep_execution ─┬─ custodial_ledger_entry (linked_sweep_execution_id)
                 └─ chain LedgerEntry      (resulting_ledger_entry_id-style match,
                                            also reachable via
                                            custodial_ledger_entry
                                            .linked_chain_ledger_entry_id)
```

The Operations tab on the Account detail page can surface this
linkage visually in a later iteration (per `future_iterations.md`);
v1 keeps entries text-only and the linkage stays in the data layer.

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

## Account → Strongbox/Vault sweep mechanics (the common outflow path)

The bread-and-butter outflow use case for pre-shipping:

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

## Inflow and inter-Holding rebalancing (PSBT-driven dispatch)

The same primitive supports any sweep whose source is a TK
Holding (Purse / Strongbox / Vault). The destination can be
another TK Holding (rebalancing) or a custodial Account
(inflow / scheduled decumulation). Examples:

- Strongbox → Purse, top up to 50,000 sats every Monday
  (rebalance).
- Purse → Strongbox, threshold-based when daily-spending
  balance exceeds a cap (rebalance).
- Strongbox → Vault, threshold-based when reserve exceeds
  600,000 sats ("promote to long-term"; rebalance).
- Purse → Kraken Account, 0.01 BTC monthly to fund scheduled
  selling on the provider's site (inflow / decumulation).
- Strongbox → Kraken Account, threshold-based when reserve
  exceeds a chosen ceiling and the user wants to monetize
  partially (inflow / decumulation).

Mechanics: the SweepEngine constructs a PaymentRequest, the user
signs (in-app on Capacitor for on-device Purses, externally for
Strongbox / Vault), broadcast happens via the normal outflow
flow. The destination address resolution depends on the
destination Holding type: a TK Holding yields a derived address
from its descriptor; an Account yields its `deposit_address`
pinned by the user.

UX for non-Account-source sweeps (the source-side composition,
review, sign, broadcast surface) is deferred (per
`future_iterations.md` "Holding-to-Holding sweeps beyond
Account-originated", which now covers both inter-Holding
rebalancing and TK → Account inflow). The architectural
primitive ships pre-shipping; the UI surface for these flows
follows once Send / Receive iterations land.

## What the user sees (target UX)

The Account detail page shows, per Account:

- Active outflow SweepPolicy summaries ("Auto-sweep weekly
  every Friday at 03:00 to Strongbox").
- Active inflow SweepPolicy summaries ("Deposit 0.01 BTC
  monthly from Purse").
- Withdraw and Deposit one-off actions (per
  `holdings/01_account.md` §"What the user sees").
- Recent activity from the observation ledger including
  TK-initiated sweep executions (both directions).

For TK Holdings with outgoing SweepPolicies (rebalance or
inflow), the same panel appears on the Holding's detail page
when that UX ships.

Specific layout and component naming lives in `UI/README.md`
and the iteration that ships the sweep-creation UI.

## Deferred

| Item | Tracked in |
|---|---|
| UX for Holding-to-Holding sweeps (non-Account source) | `future_iterations.md` "Holding-to-Holding sweeps beyond Account-originated" |
| DCA (recurring scheduled purchases) — depends on order placement | `future_iterations.md` "DCA primitive" |
