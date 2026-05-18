# BTC-Centric Self-Hosted Banking App — Specification

## Purpose

A self-hosted, Bitcoin-first application that integrates three personal-finance domains under one user interface and one internal API:

- **Savings** — watch-only multi-Holding view over user-controlled Bitcoin, with UTXO hygiene flags, transaction categorization, and security-claim verification (declared vs observable).
- **Payment** — on-chain Bitcoin send and receive via PSBT (signed on an external device, or on the Capacitor client for Purses with on-device keys per ADR-0009). Lightning support is deferred to a future iteration behind a defined interface (see `concerns/lightning_placeholder.md`).
- **Treasury** — balance aggregation across custodial providers (centralized exchanges and brokers), plus native BTC flow control in both directions to enforce minimum-exposure trading: outflow (Account → TK Holding, via the provider's withdraw API — sweep BTC off the venue right after a buy) and inflow (TK Holding → Account, via PSBT broadcast to a pinned deposit address — push BTC to the venue only when the user is about to sell). Both directions are driven by SweepPolicies (scheduled or threshold-triggered) and by manual one-off actions on the Account detail page. Direct trading from the custodian (buy/sell order routing) is **not** in scope and is captured for much later — TallyKeep is a treasury surface, not a trading terminal.

Banking is the *whole* product — these three are its functional surfaces.

The app is designed for a single self-hosted user. It does not custody keys, does not hold funds, does not create user accounts, and exposes no public network surface in the dev or personal-use phase.

## Why this exists

The product targets three audience layers, in increasing depth.

**Personal utility.** A tool that lets a sovereignty-minded user hold Bitcoin sovereignly while still acquiring through fiat rails, spending for real-world purchases, and planning long-term around it. None of the existing tools do this without compromising on custody, vocabulary, or trust posture.

**Addressable market.** Latin America (Argentina specifically), parts of Africa (Nigeria, Kenya, Ghana, South Africa), parts of the Middle East. Markets where currency instability, capital controls, and fragile banking infrastructure make sovereignty over one's own assets a daily concern rather than an abstract ideal.

**Underlying conviction.** A working hypothesis that Western financial systems are heading toward serious dysfunction and that the right response is to build the alternative rather than wait for institutions to self-correct. This is the engine, not the message of the front door.

Marketing voice should foreground the first two layers — concrete utility for real problems for real people — and let the third stay available for those who want to dig deeper. The product's voice is quietly serious, not fire-breathing.

## Design principles (locked)

1. **Honest abstraction.** Reuse familiar banking vocabulary in the UI; surface Bitcoin reality in detail panes; never hide consequences.
2. **Holdings are first-class and typed.** Account, Purse, Strongbox, Vault are not labels — they are distinct types in the domain, each with its own creation flow, security profile, and operational rules.
3. **Declared security versus observable security.** The user declares what each Holding is supposed to be; the analyzer continuously checks whether the on-chain reality matches the declaration. Discrepancies are surfaced.
4. **Minimum-exposure trading via pass-through liquidity.** Custodial providers are transit, not storage. The user's BTC sits at a venue only as long as a trade window requires; TallyKeep enforces this by controlling BTC flow in both directions (outflow after a buy, inflow before a sell), via SweepPolicies and manual one-off actions. Withdraw and Deposit are both native Account capabilities. BTC-only at the provider boundary — TallyKeep never initiates, holds, or transfers fiat; fiat balances at the provider are read-only display only.
5. **Generalized SweepPolicy.** Not just "exchange to cold." Any Holding to any Holding, with a safety validator that warns about risky configurations but never blocks. The user is the final authority; the validator just makes sure they know what they are doing before they do it.
6. **No custody of funds. Key custody is bounded and explicit.** TallyKeep never custodies user funds and never creates user accounts on TallyKeep infrastructure. Where signing keys live is a four-zone model (per ADR-0009):
   - *Backend:* never holds spending keys, ever. Holds descriptors (public-key info), custodial-provider API credentials (encrypted at rest with the user's passphrase), configuration.
   - *Capacitor client:* holds spending keys only for Purses with `purse_mode = ON_DEVICE_TK_GENERATED` or `ON_DEVICE_USER_IMPORTED`, in OS secure storage (iOS Keychain / Android Keystore), biometric-gated, never transmitted to the backend.
   - *Hardware wallet:* Strongbox and Vault keys live on the user's external signing device. TallyKeep choreographs PSBTs; never sees keys.
   - *Custodial provider:* Account keys are held by the third party (Kraken, Bitstamp, etc.). TallyKeep reads balances and triggers withdrawals via API.
   The browser PWA explicitly never holds spending keys (no OS-grade secure storage); operations requiring local keys gate honestly.
7. **Internal API-first.** The frontend is one consumer of the backend API. External or public API exposure is explicitly out of scope through the personal-use phase. The architecture stays ready for future external exposure (institutional reuse, third-party services) without designing for it now.
8. **Event-driven where appropriate, persistent where loss is unacceptable.** Domain events flow on a bus for live UI updates and decoupled subscribers; critical state transitions are also written to audit tables so nothing is lost if a subscriber misses an event.
9. **Non-requirement discipline.** Anything that brings regulatory or compliance surface is rejected by default.

## Scope

Phases and shipping milestones are defined in ADR-0003 (dev phase →
private-ship event → personal-use phase → public-ship event → public
phase). The "v1 / v1.5 / v2 / v3" framing the spec used originally
is dropped in favor of those events. The active iteration's scope
lives in `next_iteration.md`; the deferred backlog with milestone
tags lives in `backlog/` (one file per entry, per ADR-0014).

### Dev-phase target scope

What the dev phase aims to converge on. This is target state
per `PROCESS.md §1` — not a checklist of what's live today.
Already shipped lives in `shipped.md`; deferred items live in
`backlog/` (one file per entry) with a milestone tag; questions
blocking work live in `pre-implementation.md`.

- Watch-only Holdings (Account, Purse, Strongbox, Vault) with descriptor-based wallets
- Node integration via local `bitcoind` JSON-RPC plus ZeroMQ subscription for live chain events
- PSBT construction, export (file and QR), re-import, and broadcast
- Custodial provider integration (Kraken, Bitstamp) via the ccxt library — observation (balance + ledger entries, both read-only at the provider, per ADR-0012) plus withdrawal-to-whitelist plus deposit-to-pinned-address. **No order placement at the provider** — the user trades on the provider's site directly. Both BTC flows (Withdraw and Deposit) are in dev-phase scope because SweepPolicies need both directions.
- Generalized sweep policies between any two Holdings, with a safety validator that warns but does not block
- Live blockchain scanning and user-driven transaction categorization
- UTXO hygiene flags computed in the backend (address reuse, dust, change larger than payment, suspected consolidation) — UI surface deferred per `backlog/`
- Declared-vs-observable security analysis
- Onboarding-question-driven feature-flag defaults (no named user identities — see `concerns/feature_flags.md`)
- Security-health system surfacing persistent warnings (seed-backup not yet acknowledged, declared-vs-observable discrepancies, hosted-tier privacy boundary, principles acknowledgement). Full specification pending arbitration `seed-backup-disclosure` in `pre-implementation.md`; minimum-viable surface in dev-phase scope so warnings accumulate before the private-ship event needs them.
- Internal REST API (localhost-bound) plus Server-Sent Events stream for live updates
- SvelteKit Progressive Web App frontend, mobile-first, fine-tuned in browser at mobile viewport against the real backend (per ADR-0003 dev phase)
- Deployment via Docker Compose

### Deferred

See `backlog/` (and its `README.md`) for the full backlog with
`pre-shipping` / `post-shipping` / TBD milestone tags. Major
deferred items include:

- Lightning support (CoreLightning, LND, Phoenix) behind the `LightningProvider` interface
- Capacitor mobile wrapper + native plugins (private-ship enabler)
- Authentication layer + security-health system (private-ship gate)
- Multisig descriptor support
- Order placement on custodial providers
- Additional custodial providers beyond Kraken and Bitstamp
- Custom adapter for non-ccxt venues (Swissquote and similar)
- Blueprint analysis UI surface
- Clustering graph visualization
- Public-ship event work bundle (native signing, reproducible builds, app stores, F-Droid, brand finalization, third-party security audit)

### Explicitly out of scope (forever, unless revisited with a lawyer)
- Custody of user funds
- On-behalf signing of user transactions
- User account creation in our app
- Acting as an exchange, broker, or money transmitter on the user's behalf — the app is a tool the user drives, not a service handling money for them
- Lending, borrowing, yield, collateralization
- Public API or multi-tenant SaaS deployment
- Token issuance
- Stablecoins, Monero, non-Bitcoin chains *as custody*. (Read-only aggregation of non-BTC balances at connected providers is an open arbitration item — see `pre-implementation.md`.)
- Inventing a new offline payment protocol
- Telemetry, usage analytics, or crash reporting to TallyKeep or any third-party endpoint. The app is self-hosted; the user is the customer, not the data source. If a user wants to share a crash log, it is a manual file they choose to send.

## Module map

The specification splits into four numbered modules at the root,
plus two subfolders: `holdings/` (per-Holding-type chapters)
and `concerns/` (cross-cutting capabilities). Reorganized
2026-05 in the spec reshape — the previous layered split
(Savings / Banking / Trading) retired because layer-named
modules fought the user's mental model.

| Slot | File | Purpose |
|---|---|---|
| 01 | `01_architecture.md` | Surfaces, trust zones, key custody model, internal layering, runtime patterns |
| 02 | `02_domain_model.md` | Holdings hierarchy, Descriptor, LedgerEntry, CustodialProvider, generalized SweepPolicy |
| 03 | `03_data_model.md` | Database schema, secret storage, cryptographic parameters, migration strategy |
| 04 | `04_api_conventions.md` | API cross-cutting conventions (auth, errors, pagination, SSE pattern, async-job pattern). Endpoint shapes live in `api/openapi.yaml`. |
| — | `holdings/` | Per-Holding-type chapters: Account, Purse, Strongbox, Vault |
| — | `concerns/` | Cross-cutting capabilities: observation, outflow, sweep policies, feature flags, lightning placeholder, threat model |

UI specs live in `UI/` (cross-platform decisions in `UI/README.md`,
platform-specific in `UI/mobile.md` and `UI/desktop.md`, page-per-file
HTML mockups in `UI/mockups/`). Brand identity (icon, wordmark, color
palette, typography, voice) lives in `brand/` — mark, wordmark, and
palette are locked (v1 / v1 / v2); voice/about is draft. The
public-ship event (per ADR-0003) confirms or revises. ADRs
live in `decisions/`. The OpenAPI extract from the running backend
lives in `api/openapi.yaml`. The working process and document layout
are described in `PROCESS.md`.

## Stack (locked)

| Concern | Choice |
|---|---|
| Backend language | Python 3.11+ |
| Backend framework | FastAPI |
| Bitcoin wallet library | BDK via `bdkpython` |
| Bitcoin network access | Local `bitcoind` over JSON-RPC and ZeroMQ |
| Custodial provider library | ccxt (Python) |
| Database | PostgreSQL 15+ (SQLite acceptable for minimal single-user deploy) |
| ORM and migrations | SQLAlchemy 2.x with Alembic |
| Event bus | Redis pub/sub (abstracted behind an `EventBus` interface) |
| Job queue | RQ (Redis Queue) |
| Scheduling | APScheduler in the worker process |
| Lightning (deferred iteration) | CoreLightning or LND over gRPC; Phoenix as alternative |
| Frontend | SvelteKit Progressive Web App |
| Styling | TailwindCSS |
| Packaging | Docker Compose |
| Secrets storage | OS keyring (development) or encrypted database table (Docker) |
| Cryptography | Argon2id for key derivation, AES-256-GCM for symmetric encryption |

## How to use this spec

This is the canonical product description, describing the
**target state** (per `PROCESS.md §1` three-universe framing).
Modules 00–04 hold the foundations (vision, architecture,
domain, data, API conventions). The `holdings/` subfolder
describes each Holding type end-to-end (Account, Purse,
Strongbox, Vault). The `concerns/` subfolder describes
cross-cutting capabilities (observation, outflow, sweep
policies, feature flags, lightning placeholder, threat model).
UI work is iteration-driven against the real backend. Working
process — iteration cycle, ADR routing, mockup conventions,
working agreement for new agents — lives in `PROCESS.md`. The
active iteration's scope lives in `next_iteration.md`.

## Vocabulary primer

Because vocabulary matters in this spec, the four user-facing Holding types and their meanings are introduced here and used consistently throughout:

- **Account** — a balance held by a custodial provider on the user's behalf. The provider holds the keys. Examples: a Kraken balance, a Bitstamp balance, a Swissquote crypto position. An Account is *what someone owes you*, not what you own.
- **Purse** — a wallet for everyday spending. The implementation axis that matters is **whether the Purse has on-device keys**: either it's **descriptor-only** (the seed lives in another hot wallet — Phoenix, BlueWallet, Mutiny, Sparrow hot mode; TallyKeep observes only), or it's **on-device-keys** (the seed lives in the Capacitor client's OS Keychain/Keystore, biometric-gated, never on the backend). The seed *source* (TallyKeep generated it, or the user imported it from another wallet) is a secondary classification carried for disclosure copy and security-health framing — not a structural axis. See ADR-0006 and the pending `purse-upgrade-path` arbitration for the seed-origin enumeration.
- **Strongbox** — a wallet whose private keys are on an offline or hardware signing device (Coldcard, Trezor, Ledger, Jade, an airgapped laptop). The user holds the keys; signing requires deliberate action with the external device. TallyKeep choreographs the PSBT round-trip but never sees the key.
- **Vault** — a wallet under additional structural protection: multisig, timelocks, geographic key separation, inheritance setup. The user holds the keys but accessing the funds requires a ceremony involving multiple steps or co-signers. Multisig descriptor support is deferred; current build accepts single-key descriptors with the analyzer surfacing the gap honestly.

The technical primitive that backs Purse, Strongbox, and Vault is called a **Descriptor** (from BIP 380). A Holding may reference one or more Descriptors (typically one descriptor encodes both the receive and change branches of a wallet; multisig Vaults may reference multiple). Account has no Descriptor — it has a CustodialProvider connection instead.

A movement of value, whether on-chain, on Lightning (when that iteration ships), or a custodial-provider event, is recorded as a **LedgerEntry**. The on-chain transaction itself, when applicable, is the **OnChainTransaction** that the LedgerEntry references.