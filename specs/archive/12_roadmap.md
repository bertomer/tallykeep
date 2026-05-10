# 12 — Roadmap

The scope is staged. Each milestone has a clear definition of done.

## v1 — Foundation (this specification)

**Goal**: the user can run the app on their host, connect their Bitcoin node (with ZMQ), maintain Holdings of all four types (Account, Purse, Strongbox, Vault), send on-chain payments via external signer, receive payments, connect CustodialProviders, configure generalized SweepPolicies, and rely on the declared-vs-observable security analyzer for honesty checks. No Lightning yet.

### Definition of done

- Docker Compose deployment works end-to-end (bitcoind with ZMQ, backend, worker, Postgres, Redis, frontend).
- Onboarding completes successfully on regtest first, then testnet.
- A PSBT flow works with at least Sparrow, Electrum, and ColdCard via file export.
- Kraken and Bitstamp adapters pass happy-path integration tests.
- A scheduled SweepPolicy executes Account → Strongbox and confirms on-chain.
- An inter-Holding SweepPolicy (e.g. Strongbox → Purse) executes via PaymentRequest plus user signing.
- Blueprint analysis shows at least the four v1 hygiene flags.
- Declared-vs-observable security analyzer produces at least the five discrepancy kinds defined in module 02.
- Profile presets switch cleanly without data loss.
- All endpoints in module 04 are implemented or return 501 (Lightning).
- Event bus delivers SSE updates end-to-end; persist-first reconciler recovers from a simulated subscriber outage.
- Cryptography setup (Argon2id key derivation, AES-256-GCM secret encryption) functions correctly across container restarts.
- README explains installation, threat model, and non-requirements honestly.

### Non-goals (reiterated)

No Lightning. No order placement. No fiat display. No public API. No multi-user. No native mobile. No app-managed account creation. No multisig descriptor support (multisig metadata is stored, but on-chain enforcement is v2).

## v1.1 — Polish and hardening

Small items that improve usability without expanding scope.

- **Animated multi-frame QR for PSBTs** (BBQr and UR2 encoders) — broadens hardware signer compatibility.
- **Fiat display** behind the `display.fiat_conversion.enabled` flag, with the rate source being the first connected CustodialProvider.
- **LedgerEntry export to CSV** for tax or accounting integration.
- **Replace-By-Fee (RBF)** support on outgoing PaymentRequests, gated by `banking.rbf.enabled`.
- **More CustodialProvider adapters** validated end-to-end: Bitfinex, Coinbase Advanced.
- **Custom Swissquote adapter** (outside ccxt) as proof the adapter abstraction works for non-ccxt venues.
- **Signed releases** with checksums; documentation on verifying the install.
- Better error messages across the board.

## v1.5 — Lightning

**Goal**: the Banking Layer's "Instant" path becomes functional. Send and receive Lightning payments. One LightningProvider implementation, with the interface ready for the others.

### Deliverables

- `CoreLightningProvider` implementation (priority 1).
- `LndProvider` implementation (priority 2).
- `PhoenixProvider` deferred to v1.6 (waiting on a clean server-mode API from ACINQ).
- Lightning invoice creation, payment, decode, and listing.
- BIP21 with Lightning fallback URIs as the default Invoice format when LN is enabled on a Purse.
- LNURL-pay and LNURL-withdraw support.
- Lightning balance surfaced in the Purse Holding's summary.
- Settings page for LightningProvider configuration (RPC or gRPC endpoint, macaroon path or rune upload).
- Honest UI disclosure of Lightning trade-offs (channel state, force-close scenarios, backup freshness).
- Lightning event topics activated (`lightning.invoice.paid`, `lightning.payment.sent`, `lightning.channel.state_changed`).

### Preceded by

A dedicated Lightning Q&A session with the user resolving the open questions from module 08 (provider priority confirmation, channel-management UX scope, hybrid Holding routing, backup monitoring details, watchtower stance, default-Purse-with-LN configuration).

## v2 — Reach and capability

**Goal**: the app becomes useful beyond a single-machine single-user setup, and gains a deeper feature set within the existing doctrine.

### Candidate features (prioritized by demand at v1.5 wrap-up)

- **Remote access via WireGuard or Tailscale**, with API-layer authentication (token-based), TLS required.
- **Order placement on CustodialProviders**, fresh regulatory review required. Likely shape: a single `dca_order` primitive — "buy X sats at market on a schedule, auto-sweep after N hours" — rather than full-featured trading.
- **Multisig descriptor support**, both watch-only and PSBT construction. Vault Holdings finally use what they were designed for.
- **BOLT12 offers** as the default invoice format on Lightning, where supported.
- **Blueprint v2**: clustering graph visualization. Show the user which of their UTXOs an external observer would link together.
- **Contact book**: saved counterparties with metadata, recurring-payment templates.
- **Budgeting and allocation**: per-month spending categories, runway tracking.

## v3 — Native mobile, P2P rails, advanced privacy

- Native Android app (Capacitor wrapper first; a full native rewrite if PWA-via-Capacitor proves limiting).
- iOS PWA fidelity improvements; reckoning with iOS Safari's PWA limitations.
- BLE or NFC as a transport for BIP21 and BOLT11 payloads (a transport upgrade, not a new protocol). The "tap-to-pay between two app instances on the same LAN" experience.
- CoinJoin or PayJoin (Wabisabi, BIP 78 as initiator or responder).
- Deeper P2P integration — RoboSats or similar venues as optional swap routes when liquidity supports it.

## v5 — Investment layer (speculative, requires legal review)

The user has flagged interest in a fourth layer beyond the three of v1: a place where BTC can be productively committed to time-locked multisig vaults in exchange for yield, while the user retains a key.

This is genuinely interesting product territory but it is a different product from v1's banking app and must be designed separately. Initial sketch:

- Multisig vaults with discreet log contracts (DLCs) or LSP-mediated structures, where the user always retains at least one key and a clear unilateral exit path.
- Strict separation from the v1 app's domain. Likely a sibling product sharing a deployment shell (and possibly an authentication layer once v2 introduces one) but with its own database and its own threat model.
- Requires legal counsel before scoping. Specifically: does enabling such structures from within our app make us a broker, an arranger, or a custodian by some jurisdiction's reading? The v1 doctrine says "no" reflexively; v5 may require that question to be re-asked carefully.

This is **not** a backdoor for the lending-casino patterns we explicitly rejected. It is a constrained, contract-defined, sovereign-key alternative.

## Explicitly never

- Custody of user funds.
- On-behalf signing of user transactions.
- User accounts in our infrastructure.
- Token issuance.
- Proprietary lending pools.
- Acting as an exchange, broker, or money transmitter.
- Hiding operational reality behind "simplicity" — honest abstraction is the line that separates this product from its competitors.

## Staging principles

1. **Each milestone ships a coherent, honest product.** No "it works but only if you don't use this button" half-states.
2. **Regulatory surface grows slowly and deliberately.** v1 is as hands-off as possible. Every step up (v2 orders, v5 vaults) is explicitly evaluated.
3. **The core doctrine is preserved.** Self-custody, no accounts in our infra, localhost-first by default, honest abstraction. Any feature that violates these is either rejected or redesigned.
4. **The vocabulary stays stable.** Account / Purse / Strongbox / Vault / Descriptor / LedgerEntry / CustodialProvider / SweepPolicy are the durable nouns. Adding new types is allowed (a v2 multisig coordination role, a v5 contract-managed vault subtype) but renaming the existing ones is not.
