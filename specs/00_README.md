# BTC-Centric Self-Hosted Banking App — v1 Specification

## Purpose

A self-hosted, Bitcoin-first application that integrates three personal-finance domains under one user interface and one internal API:

- **Savings** — watch-only multi-Holding view over user-controlled Bitcoin, with UTXO hygiene flags, transaction categorization, and security-claim verification (declared vs observable).
- **Banking** — on-chain Bitcoin payments and receipts via PSBT (signed on an external device). Lightning support is deferred to v1.5 behind a defined interface.
- **Trading** — read-only balance aggregation across custodial providers (centralized exchanges and brokers), plus policy-driven auto-sweep between any two Holdings ("minimum-exposure trading").

The app is designed for a single self-hosted user. It does not custody keys, does not hold funds, does not create user accounts, and exposes no public network surface in v1.

## Design principles (locked)

1. **Honest abstraction.** Reuse familiar banking vocabulary in the UI; surface Bitcoin reality in detail panes; never hide consequences.
2. **Holdings are first-class and typed.** Account, Purse, Strongbox, Vault are not labels — they are distinct types in the domain, each with its own creation flow, security profile, and operational rules.
3. **Declared security versus observable security.** The user declares what each Holding is supposed to be; the analyzer continuously checks whether the on-chain reality matches the declaration. Discrepancies are surfaced.
4. **Minimum-exposure trading.** Custodial providers are pass-through liquidity, not storage. Funds leave them as fast as policy allows.
5. **No custody, no accounts, no signing keys held by the app.** The app is a tool the user drives; it never owns user funds or identity material. Only third-party access credentials are stored, encrypted at rest.
6. **Internal API-first.** The frontend is one consumer of the backend API. External or public API exposure is explicitly out of scope for v1.
7. **Event-driven where appropriate, persistent where loss is unacceptable.** Domain events flow on a bus for live UI updates and decoupled subscribers; critical state transitions are also written to audit tables so nothing is lost if a subscriber misses an event.
8. **Non-requirement discipline.** Anything that brings regulatory or compliance surface is rejected by default.

## Scope

### In scope for v1
- Watch-only Holdings (Account, Purse, Strongbox, Vault) with descriptor-based wallets
- Node integration via local `bitcoind` JSON-RPC plus ZeroMQ subscription for live chain events
- PSBT construction, export (file and QR), re-import, and broadcast
- Read-only custodial provider integration (Kraken, Bitstamp) via the ccxt library
- Generalized sweep policies between any two Holdings, with a safety validator that warns but does not block
- Live blockchain scanning and user-driven transaction categorization
- UTXO hygiene flags (address reuse, dust, change larger than payment, suspected consolidation)
- Declared-vs-observable security analysis (basic v1 set; full clustering view in v2)
- Profile presets (Beginner / Intermediate / Sovereign) implemented as feature-flag bundles
- Internal REST API (localhost-bound) plus Server-Sent Events stream for live updates
- SvelteKit Progressive Web App frontend, mobile-first
- Deployment via Docker Compose

### Deferred to v1.5
- Lightning support (CoreLightning, LND, Phoenix) behind the `LightningProvider` interface defined in v1

### Deferred to v2 and later
- Order placement on custodial providers (v1 is withdrawal-only)
- Additional custodial providers beyond Kraken and Bitstamp
- Multisig descriptor support (v1 single-key only)
- Clustering graph visualization (blueprint analysis v2)
- Native mobile wrapper
- Custom adapter for Swissquote and other non-ccxt venues

### Explicitly out of scope (forever, unless revisited with a lawyer)
- Custody of user funds
- On-behalf signing of user transactions
- User account creation in our app
- Lending, borrowing, yield, collateralization
- Public API or multi-tenant SaaS deployment
- Token issuance
- Stablecoins, Monero, non-Bitcoin chains
- Inventing a new offline payment protocol

## Module map

The specification is split into the following modules. Read in order.

| # | File | Purpose |
|---|------|---------|
| 01 | `01_architecture.md` | Service topology, event-bus design, stack choices, deployment model |
| 02 | `02_domain_model.md` | Holdings hierarchy, Descriptor, LedgerEntry, CustodialProvider, generalized SweepPolicy |
| 03 | `03_data_model.md` | Database schema, secret storage, cryptographic parameters, migration strategy |
| 04 | `04_api_surface.md` | Internal REST API contract and Server-Sent Events stream |
| 05 | `05_savings_layer.md` | Watch-only Holdings, UTXO hygiene, declared-vs-observable security analysis |
| 06 | `06_banking_layer.md` | PSBT flow, fee user experience, on-chain send and receive |
| 07 | `07_trading_layer.md` | Custodial provider integration, generalized sweep policy engine |
| 08 | `08_lightning_placeholder.md` | Interface for v1.5 Lightning integration |
| 09 | `09_profiles_and_flags.md` | Profile presets and feature-flag system |
| 10 | `10_threat_model.md` | Security scope, blast radius, what is defended and what is not |
| 11 | `11_ux_flows.md` | Key user flows with screen-by-screen expectations |
| 12 | `12_roadmap.md` | v1 to v1.5 to v2 to v3 staging |
| 13 | `13_open_questions.md` | Items deliberately unresolved, for later decision |

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
| Lightning (v1.5) | CoreLightning or LND over gRPC; Phoenix as alternative |
| Frontend | SvelteKit Progressive Web App |
| Styling | TailwindCSS |
| Packaging | Docker Compose |
| Secrets storage | OS keyring (development) or encrypted database table (Docker) |
| Cryptography | Argon2id for key derivation, AES-256-GCM for symmetric encryption |

## How to use this spec

This document is written to be handed to a coding agent. Each module is self-contained but cross-references others. The agent should implement in this order:

1. Scaffolding (modules 00 to 04): project structure, domain model, database schema, API skeleton, event bus
2. Savings layer (module 05)
3. Banking layer on-chain (module 06)
4. Profile presets and feature flags (module 09)
5. Trading layer (module 07)
6. User experience flows (module 11) — frontend build
7. Lightning (module 08) — v1.5, follows a separate Lightning-focused session

The human reviewer (the user) validates after each milestone.

## Vocabulary primer

Because vocabulary matters in this spec, the four user-facing Holding types and their meanings are introduced here and used consistently throughout:

- **Account** — a balance held by a custodial provider on the user's behalf. The provider holds the keys. Examples: a Kraken balance, a Bitstamp balance, a Swissquote crypto position. An Account is *what someone owes you*, not what you own.
- **Purse** — a wallet whose private keys are on a connected, day-to-day device (mobile wallet, hot software wallet on the user's phone or laptop). The user holds the keys; signing is light (PIN, biometric, app prompt). Suited to small-value daily spending.
- **Strongbox** — a wallet whose private keys are on an offline or hardware signing device (Coldcard, Trezor, Ledger, Jade, an airgapped laptop). The user holds the keys; signing requires deliberate action with the external device.
- **Vault** — a wallet under additional structural protection: multisig, timelocks, geographic key separation, inheritance setup. The user holds the keys but accessing the funds requires a ceremony involving multiple steps or co-signers.

The technical primitive that backs Purse, Strongbox, and Vault is called a **Descriptor** (from BIP 380). A Holding may reference one or more Descriptors. Account has no Descriptor — it has a CustodialProvider connection instead.

A movement of value, whether on-chain, on Lightning (v1.5), or a custodial-provider event, is recorded as a **LedgerEntry**. The on-chain transaction itself, when applicable, is the **OnChainTransaction** that the LedgerEntry references.
