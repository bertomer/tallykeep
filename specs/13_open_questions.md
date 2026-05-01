# 13 — Open Questions

This module lists decisions that are intentionally deferred or unresolved. None of them block starting v1 implementation. They need resolution before the related feature ships.

## v1 open questions

### Q1 — Sweep confirmation default for Intermediate

The spec sets `trading.sweep_confirmation.required` to `true` for Beginner and Intermediate, `false` for Sovereign. This is a policy call. Confirm at UI implementation time whether Intermediate should nag (recommended) or trust the policy.

### Q2 — DUST threshold recomputation cadence

Dust threshold depends on current fee rates, and rates are volatile. A UTXO that is dust at 100 sat/vB is fine at 5 sat/vB. The current spec says "recompute when fee rates change by more than 50% since last computation." Confirm or tune.

### Q3 — Number format and locale handling

Sats vs BTC display, thousand separator, decimal separator — depend on locale. The spec says integer sats are the truth; display is derivative. Concrete decision needed at frontend implementation: always show sats, always show BTC, or user preference?

Lean: user preference, sats-first default, BTC secondary on hover or tap.

### Q4 — Development network ladder

The coding agent should start on regtest for safety, move to testnet, mainnet last and only after every integration test passes. Lock as a development practice; document in CONTRIBUTING.

### Q5 — Changing bitcoind host mid-operation

Edge case but real (user moves their node). The spec says configuration can be updated via PATCH. The app should drop cached chain-derived data and re-scan. Is this acceptable UX, or do we require explicit acknowledgement from the user?

Lean: explicit acknowledgement. Changing nodes is rare; friction is fine.

### Q6 — Internal-transfer detection edge case

A transaction with some inputs from user Holdings and some from external sources is currently classified `OUTGOING` (net effect negative) or `INCOMING` (positive). But semantically it might be a coinjoin or a multi-party payment. Do we flag this differently?

Lean: flag in Blueprint as "this transaction mixes your inputs with external inputs — possible coinjoin or collaborative transaction." Do not change the LedgerEntry's direction.

### Q7 — Coin selection algorithm default

The spec sets `BranchAndBound` as the default (privacy-preferring). Sovereign profile allows per-payment override. Confirm or change.

### Q8 — Should Purse and Strongbox collapse if v1 usage shows duplication?

The four-type model (Account, Purse, Strongbox, Vault) is a bet that the Purse vs Strongbox distinction matters to a real user. The fiat-banking parallel (where "checking" and "card balance" collapsed) suggests the bet might be wrong. Track during the personal-use phase: if the user finds themselves choosing one over the other arbitrarily, collapse to a single "user-keys Holding" type with a `signing_method` attribute and reduce to three types.

### Q9 — Lightning on Strongbox

When v1.5 ships, the canonical pairing is Purse-with-Lightning. But could a Strongbox also have a Lightning component? Conceptually yes — the on-chain backing is signed offline, the LN node operates online with a separate key. Practically, this duplicates the security model in a confusing way. Defer to the Lightning Q&A session.

### Q10 — LedgerEntry-vs-OnChainTransaction split

The spec currently has both. A LedgerEntry is the user-facing record; an OnChainTransaction is the chain primitive. Right now they are two tables linked by `source_reference`. Re-evaluate during implementation: if the join becomes hot, denormalize.

### Q11 — Multisig descriptor support timing

v1 explicitly does not support multisig descriptors at the BDK level. Vault metadata is stored but the analyzer surfaces a discrepancy. The plan is v2. If the user finds this dissonance unbearable in v1 personal use, we can prioritize multisig descriptor support into v1.x rather than v2.

## v1.5 open questions (Lightning)

These resolve during the dedicated Lightning Q&A session. See module 08 for the complete list.

- Provider priority (CLN > LND > Phoenix is the current lean).
- Channel management UI scope.
- Hybrid Holding routing logic (user-chooses-per-payment is the lean for v1.5).
- Backup monitoring details.
- Watchtower stance.
- Default-Purse-with-LN configuration.

## v2+ open questions

### Q12 — Authentication model for remote access

When remote access is added, what auth model? Bearer token, mTLS, OAuth-via-proxy? Bearer token is simplest. Needs design.

### Q13 — Order placement UX without becoming a trading terminal

The product doctrine says we are not a trading terminal. But "buy X BTC and sweep it" is a natural follow-up to the Trading layer. How do we surface this without becoming another exchange frontend?

Lean: a single "DCA order" primitive — "buy X sats worth at market on a schedule, auto-sweep after N hours." No limit orders, no shorts, no leverage, no derivatives. Single-purpose buy-and-sweep.

### Q14 — Multi-user, what does it mean?

If an organization wants to use this for treasury: multi-user-per-installation, or multiple single-user installations sharing one Bitcoin Core? v2 scope at earliest; not designing here.

### Q15 — Privacy network integration

Should the backend talk to providers and bitcoind over Tor by default? Easy if bitcoind is already Tor-routed. Provider APIs sometimes block Tor exit nodes.

Lean: optional, off by default, recommended in the hardening guide.

## Meta and process

### Q16 — How to version the API

`/api/v1/` is frozen once we call a release v1.0. Additive changes only. v1.5 and v2 add new endpoints under `/api/v1/`; breaking changes go to `/api/v2/`.

### Q17 — Schema migration discipline

Every app version bump that touches the DB is risk for self-hosters. Need a clear "how to upgrade" story. Automated `alembic upgrade head` on startup is the default; rollback is manual. Document a tested rollback per migration.

### Q18 — Telemetry

None in v1. Proposed policy: never. The app is self-hosted; the user is the customer. No phone-home, no usage analytics, no crash reporting to Anthropic-style endpoints. If the user wants to share a crash log, it is a manual file they send.

### Q19 — Marketing-free domain

The domain model is intentionally marketing-free. Any future tone, voice, or branding decisions belong in a separate document and never leak into entity names, API field names, or database column names.

## Known risks

- **`bdkpython` maturity**: less mature than the core Rust library. May hit bugs. Fallback: call BDK via a thin Rust sidecar service if Python bindings prove inadequate. Evaluate during v1 implementation.
- **ccxt consistency across providers**: ccxt normalizes a lot, but per-provider quirks leak through. Each adapter integration needs specific testing against recorded fixtures.
- **bitcoind RPC stability**: some methods get deprecated between Bitcoin Core releases. Pin to a minimum node version (Bitcoin Core 26.0+).
- **SvelteKit PWA on iOS Safari**: PWA installability and offline behavior on iOS have rough edges. Acceptable for v1; revisit for v3 native consideration.
- **Argon2id parameter tuning**: the defaults in module 03 (`memory_cost=65536`, `time_cost=3`, `parallelism=4`) are reasonable for 2026 hardware. They will need to be raised over time. The crypto_parameters table makes this a configuration change rather than a schema migration.

## Decisions explicitly made (logged here for reference)

- **No authentication in v1**: localhost is the boundary. Not a bug.
- **No third-party chain data**: the user's own bitcoind is the only source. Not a bug.
- **PSBT file download is the v1 export default**: most compatible. QR is a v1.1 broadening (single QR is in v1, multi-frame QR is v1.1).
- **Python backend**: chosen for ecosystem maturity, not raw speed.
- **SvelteKit frontend**: chosen for development speed, PWA fit, and cleaner code surface for an AI coding agent.
- **Holding hierarchy: Account, Purse, Strongbox, Vault**: chosen over generic "wallet" or "stack" vocabulary because the type names encode the security reality, which is the central differentiator.
- **Descriptor as a separate first-class entity**: avoids the overloading of "wallet" to mean both technical concept and user-facing concept.
- **LedgerEntry as the user-facing record**: BTC-specific by construction, with a source discriminator for `onchain_transaction`, `lightning_payment`, and `custodial_event`. No prefix; multi-asset support is a different product if it ever exists.
- **SweepPolicy generalized to any-Holding-to-any-Holding** with a safety validator that warns but does not block.
- **Declared-vs-observable security as a first-class analyzer output**, not a stored field. Discrepancies surface in real time via events.
- **Event-driven architecture from day one**, with persist-first-emit-second for non-losable events. Listeners and subscribers and schedulers as distinct worker components.
- **Cryptography**: Argon2id for KDF, AES-256-GCM for symmetric encryption. Parameters stored in a `crypto_parameters` singleton for forward compatibility.
- **No abbreviations in identifiers**: `runtime_configuration` not `config_kv`, `authentication_tag` not `auth_tag` (in domain), `derivation_index` not `idx`. Industry-standard exceptions: UTXO, PSBT, BIP, RPC, BTC, sats, LN, gRPC, SSE, API, KDF, GCM.
- **No marketing language in the domain or anywhere in the code**. Branding belongs in a separate document yet to be written.
