# Account — custodial Holdings

An **Account** is a balance held by a custodial provider on the
user's behalf — Kraken, Bitstamp, future Lemon / Buenbit / Belo /
Coinbase Advanced / Swissquote. The provider holds the keys.
TallyKeep observes balances and triggers withdrawals via the
provider's API.

**Key custody zone (ADR-0009):** custodial provider. The user
manages keys with the provider, not with TallyKeep. TallyKeep
holds only the API credentials, encrypted at rest with the user's
passphrase.

**Credential model (ADR-0011, observation scope per ADR-0012):**
Account credentials are split across two independent provider-side
API keys, each scoped to one TK capability. The **read-only key**
is mandatory and captured at onboarding (Add Account wizard); it
carries the provider's full observation-permission set (balance
query + ledger query for Kraken — both read-only, neither can move
funds). The **withdrawal key** is optional and configured
separately, post-onboarding, via the Account detail page's
Withdraw affordance. Both are stored encrypted on TallyKeep;
neither carries permissions beyond the one TK capability it serves
(observation or withdrawal).

## Vocabulary

> *An Account is what someone owes you, not what you own.* — the
> framing carried through the spec since `00_README.md` to keep
> custodial Holdings honest about their custody model.

## Product principle: minimum-exposure trading via pass-through liquidity

The CustodialProvider is **pass-through liquidity, not storage**.
The user's BTC should sit at the venue only as long as the trade
window requires — minutes-to-hours, not days-to-months. The user's
fiat likewise transits the venue rather than accumulating there
indefinitely. This is the **minimum-exposure trading** pattern:
the user controls when value enters and leaves the venue, the
venue holds value only during active use.

TallyKeep enforces the pattern by controlling BTC flow in both
directions on the user's terms:

- **Outflow** (Account → TK Holding) — sweep BTC off the provider
  as fast as policy allows, typically right after the user buys
  BTC on the provider's site. Accumulation pattern: fiat → BTC at
  the venue → BTC at self-custody. Driven by SweepPolicies with
  source = Account or by manual Withdraw on the Account detail
  page.
- **Inflow** (TK Holding → Account) — push BTC to the provider
  only when the user is about to sell, scheduled or threshold-
  triggered. Decumulation pattern: BTC at self-custody → BTC at
  the venue → fiat off the venue (user's wallet, not TallyKeep's
  surface). Driven by SweepPolicies with destination = Account or
  by manual Deposit on the Account detail page.

Both directions are native Account capabilities. The pattern is
the same in both: BTC arrives at the venue only when needed for
an imminent trade, leaves immediately after. Without minimum-
exposure enforcement, the venue accumulates the user's BTC and
the FTX-class threat surface grows; with it, the user keeps
exposure to a bounded window.

**Locked principle: BTC only, no fiat operations.** TallyKeep
never initiates, holds, or transfers fiat. Fiat balances at the
provider are read-only display surface (consolidation rows,
fiat-denominated thresholds in SweepPolicies). The fiat side of
any trade happens on the provider's site, by the user, outside
TallyKeep — TallyKeep observes the resulting BTC balance change
between two cycles and ledger entries via the provider's API.

**Out of current scope: order placement at the provider.**
TallyKeep does not route buy/sell orders — the user trades on the
provider's site. The natural use case for order routing crosses
the fiat-operations boundary which is locked out, so pursuing it
would require a separate regulatory evaluation. Captured in
`future_iterations.md` for much-later consideration; this is a
current scope cut, not a foundational principle.

## What an Account does

- **Connects** to a supported CustodialProvider via ccxt using
  user-provided API credentials. The read-only credential is
  mandatory and captured at onboarding; the withdrawal
  credential is optional and configured separately later (see
  "Credentials — 2-key model" below).
- **Observes** the provider's state on a schedule (default 10
  min, configurable 1–60 min) plus on demand. One observation
  cycle fetches: current BTC balance and other-asset balances
  (the provider's balance endpoint), plus new ledger entries
  since the last cycle (the provider's ledger endpoint —
  deposits, withdrawals, trades, fees, transfers, all unified
  in one feed). The ledger feed is the activity source for the
  Account detail page's Operations tab. This is the only source
  of truth about the Account — there is no chain scan for an
  Account, because the Account doesn't have a descriptor and
  TallyKeep doesn't know which on-chain addresses belong to the
  user at the provider. Observation uses the read-only
  credential's observation-permission set (per ADR-0012).
- **Surfaces balance changes** by comparing the latest poll's
  balance to the previous one. A delta fires
  `treasury.custodial.balance_changed` (typically the result of
  a manual buy on the provider's website, a deposit, or an
  external withdrawal). The "detect" verb here = "noticed a
  balance change between two polls"; not chain scanning.
- **Withdraws** BTC to the pre-whitelisted destination address
  when an outflow SweepPolicy fires (see
  `concerns/sweep_policies.md`) or on manual user request via
  the Account detail page's Withdraw affordance. Requires the
  withdrawal credential to be configured (per the 2-key model;
  see "Credentials" below). Accounts without a withdrawal
  credential land outflow SweepPolicies in watch-and-advise
  mode — the trigger fires, the user is told to act, but no
  API call is made.
- **Receives deposits** from the user's other Holdings. The
  source-Holding side composes and signs a PSBT (Strongbox /
  Vault / Purse machinery, no Account-side credential needed),
  broadcasts as a regular outgoing Bitcoin transaction to the
  Account's **pinned deposit address**. Driven by inflow
  SweepPolicies (source = TK Holding, destination = this
  Account) or by manual Deposit on the Account detail page.
  TallyKeep observes the incoming deposit on the next
  observation cycle as a ledger entry of kind `deposit`. The
  pinned deposit address is captured once on the Account (user
  pastes it from the provider's funding page); no provider-side
  credential scope is required on the TallyKeep side for
  deposits.
- **Reconciles** withdrawals across two surfaces. When the
  provider reports a withdrawal in its history, TallyKeep
  expects a corresponding on-chain incoming transaction at the
  whitelisted destination address (which belongs to a non-Account
  Holding — Strongbox, Vault, etc.). The chain scanner detects
  that incoming tx and links the `sweep_execution` row to the
  resulting LedgerEntry. The reconciliation closes the loop:
  "the provider said the withdrawal completed; the chain
  confirmed it landed at the right address."

## Supported providers (target state)

Pre-shipping ships **Kraken** as the v1 provider. Bitstamp and
broader coverage are deferred to the "Additional CustodialProvider
adapters" iteration in `future_iterations.md` — the v1 scope cut
shipped with the Account-wizard iteration (per ADR-0011).

| Provider | Adapter id | Withdrawal keys | Whitelist read API | Tier |
|---|---|---|---|---|
| Kraken | `kraken` | Yes | Yes (WithdrawAddresses) | v1 |
| Bitstamp | `bitstamp` | Yes | No (web UI only) | post-v1 |
| Lemon / Buenbit / Belo / Coinbase / Swissquote | (per `future_iterations.md`) | Per-adapter | Per-adapter | post-shipping |

Adding a provider is a localized change against the
`CustodialProviderAdapter` ABC (the treasury-layer ACL described
in `01_architecture.md`). The service code never sees ccxt directly.

### Provider capability matrix

Each `CustodialProviderAdapter` declares its capabilities at
registration:

- `supports_withdrawal_keys: bool` — does the provider's API
  expose withdraw operations? Drives whether the Account-detail
  Withdraw affordance is offered and whether the Add Account
  wizard's Step 3 "Set up auto-sweep" suggestion card renders.
  Providers with `false` land Accounts that are observation-only;
  the suggestion card is absent (absence-of-affordance per ADR-0007,
  not a stubbed always-disabled button).
- `whitelist_read_api: bool` — can TallyKeep fetch the user's
  provider-side withdrawal whitelist programmatically? Drives
  the withdrawal sub-flow's verification UX. Providers with
  `true` (Kraken) let the sub-flow cross-reference TK Holdings
  with verified provider-side whitelist entries; providers with
  `false` (Bitstamp) fall back to manual user attestation
  ("yes, I configured this address on the provider's site").

Frontend reads the matrix at wizard time and at Account detail
time. Backend exposes the matrix via the treasury providers
endpoint (path in `api/openapi.yaml`).

## Credentials — 2-key model

Per ADR-0011, an Account has up to two independent provider-side
API keys, each scoped to one TallyKeep operation. The single-
credential design with an in-place permission upgrade was retired
during the Account-wizard design pass; the rationale lives in the
ADR.

- **Read-only credential (mandatory).** Captured at the Add
  Account wizard. Carries the provider's full observation-
  permission set — for Kraken (v1), this is `Query funds` **and**
  `Query ledger entries` (both read-only flags on Kraken; neither
  grants fund-movement capability). The exact accepted set is
  declared per-provider on each `CustodialProviderAdapter` at
  registration time; the wizard reads it for helper-banner copy
  and for overage rejection (per ADR-0012). Used by TallyKeep
  for: balance observation, activity-feed observation (ledger
  entries — deposits, withdrawals, trades, fees, transfers, all
  unified), withdrawal-history reconciliation, read-only display
  of non-BTC balances. **Cannot move funds** under any
  composition of the locked permissions. If this credential ever
  leaks, the blast radius is information disclosure of balance
  and history at the provider — nothing is moved.

- **Withdrawal credential (optional, post-onboarding).**
  Configured separately from the Account detail page's Withdraw
  affordance — its own design pass, captured in
  `future_iterations.md` "Account withdrawal-key sub-flow".
  Carries only the provider's withdraw permission (`Withdraw
  funds` on Kraken, plus the provider's balance-query scope
  where required by the withdraw endpoints — Kraken needs both;
  ccxt adapter handles the per-provider detail). Used by
  TallyKeep for: SweepPolicy execution and manual "Sweep now".
  Paired with a provider-side address whitelist that pins the
  destination — the load-bearing defense if the withdraw
  credential ever leaks.

**Both credentials reject overage.** Registration of either
credential calls the provider's key-permissions endpoint and
verifies the key has *only* the expected single capability — no
`Trade`, `Margin`, `Futures`, `Earn / Staking`, and no spillover
across the two scopes. Overage is a hard reject with the locked
message: *"This API credential has more permissions than required.
Create a new credential with only [scope] enabled."* (Verbatim
copy is per-scope; the wizard's Step 1 error variant carries the
read-only version.)

**Account state machine:**

- `read_credential_id` — non-null after the Add Account wizard
  succeeds.
- `withdraw_credential_id` — nullable; null after onboarding,
  populated by the post-onboarding withdrawal sub-flow.

SweepPolicies attached to an Account inspect
`withdraw_credential_id`:

- null → **watch-and-advise mode** (per `concerns/sweep_policies.md`):
  trigger fires, UI shows "your balance crossed the threshold;
  configure withdrawal or move funds manually on the provider",
  no API call is made.
- non-null → **act mode**: SweepPolicy fires the provider's
  withdraw API to the whitelisted destination.

**Replacing a credential.** Either credential can be replaced
independently (rotate the read-only key on a schedule; revoke the
withdraw key on a vacation freeze; etc.). Replacement is a delete-
old-row + create-new-row operation; the new credential is
permission-validated the same way as initial creation. The
Account's state is preserved across replacement.

## Add-Holding flow

The Add Account wizard is a 3-step **read-only-only** flow (per
ADR-0011). The withdrawal credential is configured separately
post-onboarding from the Account detail page — its own design
pass.

Visual contract: the four validated mockups in `UI/mockups/`
(`mobile_add_holding_account_01_connect.html`,
`mobile_add_holding_account_01_connect_error_overage.html`,
`mobile_add_holding_account_02_parseback.html`,
`mobile_add_holding_account_03_success.html`) are the source of
truth for screen layout, copy, states, and affordances. Per-screen
detail and gauntlet answers live in the `## Add Holding — Account
wizard` section of `UI/mobile.md`.

1. **Step 1 — Connect (provider + credentials).** Searchable
   provider dropdown (v1 list: Kraken only). Per-provider helper
   banner with the exact steps to create a read-only API key on
   the provider side, the key-naming convention (`TallyKeep
   Read`), the observation-permission set to enable (`Query funds`
   **and** `Query ledger entries` on Kraken, per ADR-0012), and
   which permissions to leave off. Sub-banner warning that the
   provider's create-key dialog shows the private key once. API
   Key + Private Key inputs (Private Key uses a password field
   with a reveal toggle, no Copy affordance — per the
   privacy-first-reveal memory). Continue validates the
   credentials against the provider; rejects overage (any
   permission beyond the declared observation set) and rejects
   underage (any of the required observation permissions
   missing). Error variant surfaces the specific overage /
   underage detail and a tap-to-clear-both coding rule.

2. **Step 2 — Parseback.** Recap card showing provider name,
   permission qualifier ("Read-only — this key cannot move
   funds"), and a cap-and-overflow summary of non-BTC balances
   detected at the provider (top three currency tickers + "+ N
   more"). Auto-name preview ("Kraken account" with collision
   suffix) editable inline. No BTC balance row here — the BTC
   balance is the success step's headline value. No withdrawal
   mention on this step; the wizard's single deferred-withdrawal
   forward-reference lives in Step 1's sub-heading.

3. **Step 3 — Success.** Success indicator + heading + headline
   BTC balance card (single unit per the user's home preference;
   defaults to sats per `UI/README.md`). **Capability-gated
   suggestion card**: rendered iff the connected provider's
   adapter has `supports_withdrawal_keys=true`. Card surfaces
   the provider-specific framing ("Kraken supports automated
   withdrawals…") and routes to the withdrawal sub-flow when
   the user wants it immediately. Primary CTA "Done" returns to
   Home.

Specific API request/response shapes live in `api/openapi.yaml`.

## Observation cycles

- Default cadence: every 10 minutes.
- Configurable: 1–60 minutes via
  `runtime_configuration.custodial_polling.interval_seconds`.
- On demand: refresh endpoint (path in `api/openapi.yaml`).

Each cycle fetches BTC balance, other-asset balances (read-only
display only — never actionable on the provider's side), and new
or updated ledger entries since the last cycle's cursor (deposits,
withdrawals, trades, fees, transfers, all unified). Updates the
provider row's `last_known_balance_sats`, `last_updated_at`,
`last_error`. Persists ledger entries in `custodial_ledger_entry`
under the mirror posture (per ADR-0013).

**Mirror posture (per ADR-0013).** `custodial_ledger_entry` is the
canonical on-disk record of what TallyKeep has observed at the
provider's ledger endpoint — not a short-TTL cache. The Operations
tab on the Account detail page reads from this table, so it renders
honestly even when the provider is unreachable, the user has revoked
the API key, or the polling cycle is paused. The trade-off is
reconciliation discipline: provider-side mutations are tracked and
unknown kinds are pass-through-preserved rather than dropped. See
ADR-0013 for the full reasoning.

**Per-cycle persistence contract.**

- **Upsert by `(custodial_provider_id, provider_entry_id)`.** Each
  observed row carries the provider's stable row id (Kraken's `id`
  field on a ledger entry). New refids insert; existing refids
  update in place when fields changed (status transitions like
  `pending → success → cancelled`, fee corrections); missing refids
  from a paginated past are not deleted (providers don't delete
  historical entries — missing means out of the polled window).
- **Kind normalization is adapter-owned.**
  `CustodialProviderAdapter.normalize_ledger_entry(raw)` returns the
  TK kind (`trade`, `deposit`, `withdrawal`, `transfer`, `fee`,
  `other`) from a per-provider mapping table. Anything not in the
  explicit map normalizes to `other`. The full provider record
  always goes into `raw_payload` (JSONB), so unknown kinds remain
  fully readable even when the TK enum doesn't represent them
  structurally.
- **Multi-row events stay coherent.** Kraken trades return one
  ledger row per asset leg, paired by `refid`. For v1 (BTC-only
  display), the adapter emits the BTC leg only and stashes the
  fiat leg inside `raw_payload`. Non-BTC-only events drop at
  normalization time. If `multi-asset-aggregation` (per
  `pre-implementation.md`) decides the other way later, the
  adapter stops dropping; pass-through means no provider-side
  re-poll is required.

**Per-cycle SSE.** The poller emits four event topics, all under the
`treasury.custodial.*` namespace:

- `treasury.custodial.balance_changed` — fires on a balance delta
  between the previous cycle and the current one (typical cause:
  the user made a manual buy on the provider's site, or a deposit
  cleared, or an external withdrawal landed).
- `treasury.custodial.ledger_entry_added` — per new ledger row
  (refid not previously seen at this provider). Carries the full
  normalized entry payload.
- `treasury.custodial.ledger_entry_updated` — per existing ledger
  row that mutated in the latest cycle (status transitioned, fee
  corrected, etc.). Carries the post-update entry payload plus a
  delta hint (`changed_fields: list[str]`). Frontends that do not
  subscribe degrade silently — the row is stale until the next
  page load.
- `treasury.custodial.connection_state_changed` — connection-state
  transitions (`healthy → degraded → unreachable → auth_failed`).

Cycle failures (rate-limit hits, network errors, auth errors) are
logged and surfaced via `system.custodial.auth_failed` and the
connection-state event above. After N consecutive auth errors
(default 5), the provider is marked `is_active=FALSE` and the user
is alerted via SSE.

**TK-initiated event linkage.** Some custodial ledger entries
correspond to TK-initiated flows — a SweepPolicy that fired an
outflow produces a `withdrawal` entry at the provider; an inflow
sweep that broadcast a PSBT produces a `deposit` entry at the
provider once it confirms. These entries carry richer semantics
than "the user did something on the provider's site," and TK
records that richness via three nullable FKs on
`custodial_ledger_entry`: `linked_sweep_execution_id`,
`linked_counterparty_holding_id` (the TK Holding on the *other*
side of the flow — source for a withdrawal, destination's source
for a deposit), and `linked_chain_ledger_entry_id` (the chain-side
`LedgerEntry` produced by the on-chain leg). A reconciler
subscriber populates the FKs on each new `kind=deposit`/`withdrawal`
entry; matching criteria and the reconciler's persist-first flow
live in `concerns/sweep_policies.md §5. Reconciliation`. Entries
that don't match a pending `sweep_execution` stay pure observation
("the user did this on the provider's site") — no judgment.

**What the page surfaces in v1.** The Account-detail page's
Operations tab renders all entries identically — text-only
descriptor, relative time, single-unit BTC amount with sign-based
color. The visual TK-vs-external distinction is deferred (see
`future_iterations.md` and the Account-detail iteration's scope-out
list); the linkage data exists from day one and the next UI
iteration lights it up without a migration.

## Flows — Withdraw and Deposit

The Account holding type carries two native BTC flows, each tied to
a different mechanism on the provider side.

### Outflow — Withdraw to whitelist (Account → TK Holding)

Outflow uses the provider's withdraw API (not a PSBT) and routes to
a **pre-whitelisted destination address** — typically a Strongbox
or Vault address belonging to the user. Outflow requires the
withdrawal credential to be configured (see "Credentials — 2-key
model" above); Accounts with `withdraw_credential_id = null` cannot
withdraw via TallyKeep regardless of the observation credential.

The user does **not** choose a destination at withdraw time. The
whitelist is the load-bearing defense against the withdrawal
credential being compromised (per the threat model, S4). The
destination is bound when the withdrawal credential is registered.

Outflow SweepPolicies (`source = this Account`,
`destination = a TK Holding`) drive automated outflows on schedule
or threshold — fire, withdraw the available balance minus
`minimum_balance_sats`, route to the whitelisted address. Policies
on Accounts without a withdrawal credential run in watch-and-advise
mode (the trigger fires, the user is notified, no API call is made).

Manual Withdraw is available as a button on the Account detail
page. It's a one-off outflow execution to the whitelisted address,
mechanically equivalent to a SweepPolicy firing once.

### Inflow — Deposit to pinned address (TK Holding → Account)

Inflow is a regular Bitcoin transaction composed and signed on the
**source-Holding side** (Strongbox / Vault / Purse PSBT machinery —
no Account-side credential needed for the signing). The destination
is the Account's **pinned deposit address**, captured once on the
Account (the user pastes it from the provider's funding page) and
stored in `Account.deposit_address`. TallyKeep does not fetch the
deposit address via the provider's API — that would require an
elevated credential scope, and the user-pasted pinned pattern keeps
the observation credential narrow.

TallyKeep observes the incoming deposit on the next observation
cycle as a ledger entry of kind `deposit`. The reconciliation loop
links the TK-attested on-chain broadcast to the provider-reported
deposit ledger entry.

Inflow SweepPolicies (`source = a TK Holding`,
`destination = this Account`) drive automated inflows on schedule
or threshold — fire, compose a PSBT on the source side, sign,
broadcast. Used for scheduled decumulation: send BTC to the
provider before manually selling on the provider's site.

Manual Deposit is available as a button on the Account detail page.
It opens a Send flow from a user-picked source TK Holding to the
Account's pinned deposit address, mechanically equivalent to an
inflow SweepPolicy firing once.

### What is explicitly out of scope on Account flows

- **Order placement at the provider.** TallyKeep does not route
  buy/sell orders; the user trades on the provider's site directly.
  Captured for much-later consideration in `future_iterations.md`
  ("Order placement on custodial providers"); pursuing it would
  require a separate regulatory evaluation because the natural use
  case crosses the fiat-operations boundary which is locked out.
- **Fiat operations.** TallyKeep never initiates, holds, or
  transfers fiat. Fiat balances are read-only display only. The
  fiat side of any sell happens on the provider's site, outside
  TallyKeep.
- **Partial withdrawals to multiple addresses.** Outflow always
  goes to the single whitelisted address.
- **Non-BTC withdrawals or deposits.** Both flows operate on BTC
  only.

## What the user sees (target UX)

The Account detail page shows:

- Provider name, connection status (green / amber / red), freshness
  indicator ("Updated N minutes ago" — refreshed by observation
  cycles and incoming SSE events; no manual refresh button).
- Current BTC balance (and read-only breakdown of other assets if
  present — see `pre-implementation.md` `multi-asset-aggregation`
  for the open question of whether these surface on the Home).
- **Withdraw** action — one-off outflow to the whitelisted address.
  Greyed (with a tap-prompt routing to the withdrawal-credential
  configuration sub-flow) when `withdraw_credential_id = null`.
- **Deposit** action — one-off inflow from a picked TK Holding to
  the pinned deposit address. Greyed (with a tap-prompt routing to
  the pin-a-deposit-address sub-flow) when `deposit_address = null`.
- Active SweepPolicy summaries, both directions: outflow ("Auto-
  sweep weekly every Friday at 03:00 to Strongbox") and inflow
  ("Deposit 0.01 BTC monthly from Purse").
- Recent activity from the observation ledger (deposits, withdrawals,
  trades, fees, transfers).
- Prominent warning if the provider-side whitelist is unverified or
  if the pinned deposit address has never been used.

Specific layout and component naming lives in `UI/README.md` and
`UI/mobile.md`.

## Regulatory posture (locked)

These lines are firm:

- TallyKeep does NOT initiate, hold, or transfer fiat. Fiat
  balances at the provider are read-only display only.
- TallyKeep does NOT route buy/sell orders at the provider. The
  user places trades on the provider's site directly.
- TallyKeep does NOT custody fiat or crypto on the user's behalf
  in a pooled account.
- TallyKeep does NOT match buyers and sellers.

The user's relationship with each CustodialProvider is direct;
TallyKeep is a client to the provider's API, on the user's behalf,
from the user's own machine, with the user's own credentials. This
is the architectural shape that keeps order routing, exchange
operation, and money-transmitter activities out of scope.

BTC flows in both directions (Withdraw and Deposit) are within
scope — both are direct API or PSBT operations the user authorizes
on their own behalf, neither involves TallyKeep custody of funds
nor fiat operations.

## UX design surface still to land

The Account flows are native canonical features (above). Their UX
design passes are iteration-scoped:

| Item | Tracked in |
|---|---|
| Withdrawal credential configuration UX (capture the withdraw credential + pre-whitelisted destination picker; activates the Withdraw button on Account detail) | `future_iterations.md` "Account withdrawal-key UX" |
| Deposit-address capture UX (paste the provider's BTC deposit address; activates the Deposit button on Account detail) | `future_iterations.md` "Account deposit-address UX" |
| Bi-directional SweepPolicy creation UX (source / destination picker, schedule and threshold rules across both directions) | `future_iterations.md` "SweepPolicy creation UX" |
| Additional providers — Bitstamp (cut from v1), Lemon, Buenbit, Belo, Coinbase Advanced, etc. | `future_iterations.md` "Additional CustodialProvider adapters" |
| Order placement on custodial providers | `future_iterations.md` "Order placement on custodial providers" — requires fresh regulatory evaluation because it crosses the fiat boundary |
| Custom adapter for non-ccxt venues (Swissquote) | `future_iterations.md` "Custom adapter for non-ccxt venues" |
| Whether to surface non-BTC balances at the consolidated view | `pre-implementation.md` `multi-asset-aggregation` |
| P2P swap routes (RoboSats) as a separate adapter | `future_iterations.md` "P2P swap routes" |
