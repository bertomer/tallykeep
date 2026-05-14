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
  user-provided API credentials (read + withdrawal permissions
  only).
- **Polls** the provider on a schedule (default 10 min,
  configurable 1–60 min) plus on demand. Surfaces balance,
  recent withdrawal history, recent deposit history.
- **Detects** new BTC balances appearing on the provider
  (typically the result of a manual buy or a deposit).
- **Withdraws** to the pre-whitelisted destination address when a
  SweepPolicy fires (see `concerns/sweep_policies.md`) or on
  manual user request.
- **Reconciles** provider-reported withdrawals with the resulting
  on-chain LedgerEntries detected by the chain scanner.

## Supported providers (target state)

Pre-shipping ships Kraken and Bitstamp; broader coverage is
captured in `future_iterations.md`.

| Provider | Adapter id | Whitelist API support | Tier |
|---|---|---|---|
| Kraken | `kraken` | Yes (WithdrawAddresses) | First-class |
| Bitstamp | `bitstamp` | Whitelist set via web UI; API consumes whitelisted address names | First-class |
| Lemon / Buenbit / Belo / Coinbase / Swissquote | (per `future_iterations.md`) | Per-adapter | Post-shipping |

Adding a provider is a localized change against the
`CustodialProviderAdapter` ABC (the treasury-layer ACL described
in `01_architecture.md`). The service code never sees ccxt directly.

## Add-Holding flow

1. **Provider selection** — chooser of supported providers.
2. **Credentials** — user provides API key + secret. Backend
   calls the provider's "get key permissions" endpoint. **If any
   of `{trade, margin, staking, futures}` is enabled, the
   registration is rejected** with: *"This API credential has
   more permissions than required. Create a new credential with
   only 'query funds' and 'withdraw funds' enabled."*
3. **Whitelist verification:**
   - If the provider exposes a withdrawal-whitelist API, the
     backend verifies the configured `whitelist_address` is
     present.
   - If the provider does not expose a whitelist-check API, the
     UI displays a blocking warning: *"We cannot programmatically
     verify withdrawal whitelisting on this provider. You must
     manually configure a withdrawal whitelist on the provider's
     website for the address `{address}`. Confirm you have done
     this?"* User must check a confirmation box.
4. **Credential storage** — credentials persist in the `secret`
   table (cryptography per `03_data_model.md`). The Account
   Holding's `custodial_provider` row references credentials by
   reference string; values never appear in the row.

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
pre-whitelisted address — typically a Strongbox or Vault address
the user configured during Account onboarding.

The user does **not** choose a destination at withdraw time.
This is by design: the whitelist is the load-bearing defense
against an Account credential being compromised (per the threat
model, S4).

A SweepPolicy (see `concerns/sweep_policies.md`) is the
recommended way to drive Account outflows automatically — fire
on schedule or threshold, withdraw the available balance minus
`minimum_balance_sats`, route to the whitelisted address.

Manual "Sweep now" is available as a button on the Account
detail page.

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
| Order placement on custodial providers | `future_iterations.md` "Order placement on custodial providers" — needs fresh regulatory eval |
| Additional providers (Lemon, Buenbit, Belo, Coinbase Advanced, etc.) | `future_iterations.md` "Additional CustodialProvider adapters" |
| Custom adapter for non-ccxt venues (Swissquote) | `future_iterations.md` "Custom adapter for non-ccxt venues" |
| Whether to surface non-BTC balances at the consolidated view | `pre-implementation.md` `multi-asset-aggregation` |
| P2P swap routes (RoboSats) as a separate adapter | `future_iterations.md` "P2P swap routes" |
