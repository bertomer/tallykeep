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

**Credential model (ADR-0011):** Account credentials are split
across two independent provider-side API keys, each scoped to one
capability. The **read-only key** is mandatory and captured at
onboarding (Add Account wizard). The **withdrawal key** is
optional and configured separately, post-onboarding, via the
Account detail page's Withdraw affordance. Both are stored
encrypted on TallyKeep; neither has more permissions than the one
TallyKeep operation it serves.

## Vocabulary

> *An Account is what someone owes you, not what you own.* — the
> framing carried through the spec since `00_README.md` to keep
> custodial Holdings honest about their custody model.

## Product principle: minimum-exposure trading

The CustodialProvider is **pass-through liquidity, not storage**.
The design assumption: the user has placed (or will place) the
trade manually on the provider's website. TallyKeep's job is to
enforce *get the BTC off the provider as fast as policy allows.*

This is what distinguishes Account Holdings from a portfolio
tracker. Order placement (`ccxt.create_order` and all trade
endpoints) is **never called**; the API credential is registered
with withdrawal-only permissions and Account creation rejects
credentials with trade / margin / staking / futures permissions
enabled. Order placement is captured in `future_iterations.md`
("Order placement on custodial providers") and requires fresh
regulatory evaluation before commit.

## What an Account does

- **Connects** to a supported CustodialProvider via ccxt using
  user-provided API credentials. The read-only credential is
  mandatory and captured at onboarding; the withdrawal
  credential is optional and configured separately later (see
  "Credentials — 2-key model" below).
- **Polls** the provider's API on a schedule (default 10 min,
  configurable 1–60 min) plus on demand. One polling call
  fetches: current BTC balance, recent withdrawal history,
  recent deposit history, other-asset balances (read-only).
  This is the only source of truth about the Account — there is
  no chain scan for an Account, because the Account doesn't have
  a descriptor and TallyKeep doesn't know which on-chain
  addresses belong to the user at the provider. Polling uses
  the read-only credential.
- **Surfaces balance changes** by comparing the latest poll's
  balance to the previous one. A delta fires
  `treasury.custodial.balance_changed` (typically the result of
  a manual buy on the provider's website, a deposit, or an
  external withdrawal). The "detect" verb here = "noticed a
  balance change between two polls"; not chain scanning.
- **Withdraws** to the pre-whitelisted destination address when
  a SweepPolicy fires (see `concerns/sweep_policies.md`) or on
  manual user request — **only when the Account has a
  withdrawal credential configured** (post-onboarding via the
  withdrawal sub-flow). Accounts without a withdrawal credential
  watch-and-advise like external-key Holdings; SweepPolicies on
  them fire as notifications, not as API calls.
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
  Account wizard. Carries only the provider's balance-query
  permission (`Query funds` on Kraken). Used by TallyKeep for:
  balance polling, withdrawal-history reconciliation, read-only
  display of non-BTC balances. **Cannot move funds.** If this
  credential ever leaks, the blast radius is information
  disclosure of balance and history at the provider — nothing
  is moved.

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
   Read`), the single permission to enable (`Query funds` on
   Kraken), and which permissions to leave off. Sub-banner
   warning that the provider's create-key dialog shows the
   private key once. API Key + Private Key inputs (Private Key
   uses a password field with a reveal toggle, no Copy
   affordance — per the privacy-first-reveal memory). Continue
   validates the credentials against the provider; rejects
   overage (any permission beyond the expected single scope).
   Error variant surfaces the specific overage detail and a
   tap-to-clear-both coding rule.

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

## Balance polling

- Default cadence: every 10 minutes.
- Configurable: 1–60 minutes via
  `runtime_configuration.custodial_polling.interval_seconds`.
- On demand: refresh endpoint (path in `api/openapi.yaml`).

The poller fetches BTC balance, other-asset balances (read-only
display; never actionable), recent withdrawal history, and
recent deposit history. Updates the provider row's
`last_known_balance_sats`, `last_polled_at`, `last_error`. Emits
`treasury.custodial.balance_changed` on delta.

Polling failures (rate-limit hits, network errors, auth errors)
are logged and surfaced via `system.custodial.auth_failed`. After
N consecutive auth errors (default 5), the provider is marked
`is_active=FALSE` and the user is alerted via SSE.

## Outflow — "Withdraw to whitelist"

Account is the only Holding type whose outflow is **not** a PSBT.
It uses the provider's withdraw API and the destination is the
pre-whitelisted address — typically a Strongbox or Vault address.
Outflow requires the withdrawal credential to be configured (see
"Credentials — 2-key model" above); Accounts in the
`withdraw_credential_id = null` state cannot withdraw via
TallyKeep regardless of the read-only credential's capabilities.

The user does **not** choose a destination at withdraw time.
This is by design: the whitelist is the load-bearing defense
against the withdrawal credential being compromised (per the
threat model, S4). The destination is bound when the withdrawal
credential is registered, in the withdrawal sub-flow.

A SweepPolicy (see `concerns/sweep_policies.md`) is the
recommended way to drive Account outflows automatically — fire
on schedule or threshold, withdraw the available balance minus
`minimum_balance_sats`, route to the whitelisted address. Policies
on Accounts without a withdrawal credential run in
watch-and-advise mode.

Manual "Sweep now" is available as a button on the Account
detail page (active when `withdraw_credential_id` is non-null;
greyed out otherwise with a tap-prompt routing to the
withdrawal sub-flow).

Order placement, partial withdrawal to multiple addresses, and
non-BTC withdrawals are explicitly **out of scope**.

## What the user sees (target UX)

The Account detail page shows:

- Provider name, last poll time, connection status (green /
  amber / red).
- Current BTC balance (and read-only breakdown of other assets
  if present — see `pre-implementation.md`
  `multi-asset-aggregation` for the open question of whether
  these surface on the Home).
- Active SweepPolicy summaries ("Auto-sweep weekly every Friday
  at 03:00 to Strongbox").
- "Sweep now" button.
- Recent sweep history with status badges.
- Prominent warning if provider-side whitelist is unverified.

Specific layout and component naming lives in `UI/README.md`
and `UI/mobile.md`.

## Regulatory posture (locked)

These lines are firm:

- TallyKeep does NOT route buy/sell orders → no broker role.
- TallyKeep does NOT custody fiat or crypto → no custodian role.
- TallyKeep does NOT pool user funds → no money-transmitter role.
- TallyKeep does NOT match buyers and sellers → no exchange
  role.

The user's relationship with each CustodialProvider is direct;
TallyKeep is a client to the provider's API, on the user's
behalf, from the user's own machine, with the user's own
credentials. This is the architectural shape that keeps order
placement (and the regulatory escalation it triggers) out of
scope.

## Deferred

| Item | Tracked in |
|---|---|
| Account withdrawal-key sub-flow (post-onboarding flow to configure the withdrawal credential + destination whitelist) | `future_iterations.md` "Account withdrawal-key sub-flow" |
| Additional providers — Bitstamp (cut from v1), Lemon, Buenbit, Belo, Coinbase Advanced, etc. | `future_iterations.md` "Additional CustodialProvider adapters" |
| Order placement on custodial providers | `future_iterations.md` "Order placement on custodial providers" — needs fresh regulatory eval |
| Custom adapter for non-ccxt venues (Swissquote) | `future_iterations.md` "Custom adapter for non-ccxt venues" |
| Whether to surface non-BTC balances at the consolidated view | `pre-implementation.md` `multi-asset-aggregation` |
| P2P swap routes (RoboSats) as a separate adapter | `future_iterations.md` "P2P swap routes" |
