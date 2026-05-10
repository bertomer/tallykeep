# 01 — Architecture

## Service topology

The deployment is a Docker Compose stack with the following services:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         User's host (localhost)                          │
│                                                                          │
│  ┌──────────────┐                                                        │
│  │   Frontend   │  SvelteKit PWA, talks to Backend over HTTP and SSE     │
│  │  SvelteKit   │                                                        │
│  └──────┬───────┘                                                        │
│         │ HTTP + SSE                                                     │
│         ▼                                                                │
│  ┌──────────────┐         ┌────────────┐         ┌────────────────┐      │
│  │   Backend    │◀───────▶│ PostgreSQL │         │     Redis      │      │
│  │   FastAPI    │         │            │         │  (event bus +  │      │
│  │              │         └────────────┘         │   job queue)   │      │
│  └──────┬───────┘                                └────────┬───────┘      │
│         │                                                 │              │
│         │ JSON-RPC                                        │              │
│         ▼                                                 │              │
│  ┌──────────────┐                                         │              │
│  │   bitcoind   │                                         │              │
│  │              │── ZeroMQ ──────────────┐                │              │
│  └──────────────┘                        ▼                ▼              │
│                                   ┌────────────────────────────┐         │
│                                   │     Worker process(es)     │         │
│                                   │                            │         │
│                                   │  • ChainListener (ZMQ)     │         │
│                                   │  • CustodialPoller (cron)  │         │
│                                   │  • SweepEngine (subscriber)│         │
│                                   │  • Categorizer (subscriber)│         │
│                                   │  • LightningListener (1.5) │         │
│                                   └────────────────────────────┘         │
│                                                                          │
│       Network binding: ALL services on 127.0.0.1 only.                   │
│       No service listens on a public interface in the dev or            │
│       personal-use phase (per ADR-0003).                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### Services

- **bitcoind** — Official Bitcoin Core image. Runs in pruned or full mode (user choice). RPC and ZeroMQ both exposed only on the Docker internal network. The app is the only client.
- **backend** — FastAPI application. Handles HTTP API and Server-Sent Events stream. Talks to `bitcoind` (RPC), Postgres, Redis (publish events, enqueue jobs), and ccxt-wrapped custodial provider APIs. Does not run scheduled tasks itself.
- **worker** — Same Python codebase, separate entry point. Runs three kinds of components: listeners (consume external feeds and translate to events), schedulers (emit events on a timer), and subscribers (react to events from the bus).
- **postgres** — Persistent state. Schema managed via Alembic.
- **redis** — Two roles: event bus (publish/subscribe) and job queue (RQ). One service, two uses; we may split if it ever becomes a bottleneck.
- **frontend** — SvelteKit PWA served as static files by a lightweight nginx, or by the backend itself in the dev phase.

## The three-layer separation: ACL, queue, bus

External systems and our domain are separated by three distinct layers, each with a single job.

```
┌──────────────────────────────────────────────────────────────┐
│  Domain (clean types: Holding, LedgerEntry, SweepPolicy...)  │
└──────────────────────┬───────────────────────────────────────┘
                       │ uses
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Adapters (Anti-Corruption Layer)                            │
│  Translate foreign data shapes into domain types.            │
│  Pure functions and classes. No timing, no retries.          │
│                                                              │
│   • CustodialProviderAdapter (Kraken, Bitstamp via ccxt)     │
│   • NodeAdapter (bitcoind RPC)                               │
│   • ChainEventAdapter (bitcoind ZeroMQ)                      │
│   • LightningProviderAdapter (Lightning iteration)           │
└──────────────────────┬───────────────────────────────────────┘
                       │ wrapped by
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Job queue (RQ on Redis)                                     │
│  Adds: scheduling, retries, timeouts, persistence,           │
│  rate-limit handling, error capture.                         │
│  Knows nothing about external data shapes.                   │
└──────────────────────┬───────────────────────────────────────┘
                       │ publishes results to
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Event bus (Redis pub/sub, abstracted behind an interface)   │
│  Domain events: BalanceChanged, BlockSeen, SweepCompleted... │
│  Many subscribers, no coupling between producer and consumer.│
└──────────────────────────────────────────────────────────────┘
```

The three layers protect against three different failure modes:

- The **adapter layer** protects the domain's vocabulary. If Kraken renames a field tomorrow, only one file changes.
- The **job queue** protects runtime reliability. If a custodial provider call takes five seconds, no user-facing request blocks.
- The **event bus** protects coupling. New subscribers can be added without touching producers.

## Persistence-first for non-losable events

Events are not durable in Redis pub/sub. If a subscriber is down when an event fires, it is lost. This is acceptable for ephemeral notifications (UI live updates, "now categorize this transaction") but not for state transitions where loss would mean wrong information about reality.

The pattern: **persist first, emit second.** Whenever a non-losable event happens, the producer:

1. Writes a row to a domain-specific audit table (e.g., `sweep_execution`, `payment_request`, `broadcast_attempt`).
2. Then publishes the event on the bus.

If step 2 fails or no one is listening, step 1 is the source of truth. A periodic reconciler scans recent audit-table rows and re-emits events for anything that has not been acknowledged. This pattern means the system tolerates restarts, transient Redis problems, and subscriber outages without losing state.

## Event taxonomy

The bus topics are stable. Producers and subscribers both speak this taxonomy. The Lightning iteration adds the `lightning.*` topics shown below; later iterations may add more, but existing topics never change shape without a version bump.

```
# Chain events (live via bitcoind ZeroMQ)
chain.block.new                          { height, block_hash }
chain.tx.mempool                         { txid, raw_tx, affected_descriptor_ids }
chain.tx.confirmed                       { txid, height, affected_descriptor_ids }

# Holding-level derived events
holding.balance.changed                  { holding_id, old_sats, new_sats }
holding.utxo.received                    { holding_id, descriptor_id, utxo_id, value_sats }
holding.utxo.spent                       { holding_id, descriptor_id, utxo_id }

# Banking events
banking.payment_request.created          { id, holding_id }
banking.payment_request.signed           { id }
banking.payment_request.broadcast        { id, txid }
banking.payment_request.confirmed        { id, txid, height }
banking.invoice.created                  { id, holding_id }
banking.invoice.paid                     { id, txid, ledger_entry_id }

# Trading events
trading.custodial.balance_changed        { custodial_provider_id, old_sats, new_sats }
trading.sweep.triggered                  { sweep_policy_id, reason }
trading.sweep.executed                   { sweep_policy_id, withdrawal_id, amount_sats }
trading.sweep.failed                     { sweep_policy_id, error }

# Categorization events
ledger_entry.requires_categorization     { ledger_entry_id }
ledger_entry.categorized                 { ledger_entry_id, category }

# Security analysis events
analysis.discrepancy.detected            { holding_id, declared, observed, severity }

# Lightning events (defined now; emitted once the Lightning iteration ships)
lightning.invoice.paid                   { invoice_id, payment_hash, amount_sats }
lightning.payment.sent                   { payment_id, payment_hash }
lightning.channel.state_changed          { channel_id, old_state, new_state }

# System events
system.unlocked                          { }
system.bitcoind.disconnected             { last_seen }
system.bitcoind.reconnected              { height }
system.custodial.auth_failed             { custodial_provider_id }
```

## Worker components

The worker process runs the following components, each registered at startup. A single Docker container runs all of them; in larger deployments they could be split across multiple worker containers, but the current shipped layout keeps them together.

### Listeners (translate external feeds to events)

- **ChainListener** — subscribes to bitcoind ZeroMQ topics (`rawblock`, `rawtx`). For each notification, looks up which Descriptors are affected and emits `chain.tx.mempool` or `chain.tx.confirmed` events.
- **LightningListener** (Lightning iteration) — subscribes to CLN or LND streaming gRPC for invoice and payment events.

### Schedulers (emit events on a timer)

- **CustodialPollScheduler** — every N minutes (default 10), emits `trading.custodial.poll_requested` for each active CustodialProvider. The CustodialPoller subscriber reacts.
- **SweepScheduler** — at cron times defined by SweepPolicies, emits `trading.sweep.triggered`.
- **AnalysisScheduler** — periodically requests fresh security-discrepancy analysis on changed Holdings.

### Subscribers (react to events)

- **CustodialPoller** — subscribes to `trading.custodial.poll_requested`, calls the relevant CustodialProviderAdapter, persists balance, emits `trading.custodial.balance_changed` if delta detected.
- **SweepEngine** — subscribes to `trading.sweep.triggered` and `trading.custodial.balance_changed` (for threshold-triggered policies), evaluates whether to act, runs the sweep, persists to `sweep_execution`, emits `trading.sweep.executed` or `trading.sweep.failed`.
- **CategorizerSuggester** — subscribes to `ledger_entry.requires_categorization`, runs heuristics, attaches non-binding suggestions visible in the UI.
- **LiveUpdateBridge** — subscribes to all topics, forwards filtered events to connected SSE clients (the frontend).
- **AuditReconciler** — periodic; scans audit tables for rows whose corresponding event was apparently lost, re-emits.

## Request shape

### Synchronous endpoints (default)
- Read operations against local state (balances, transactions, Holdings, configuration)
- Node-local operations (derive an address, get mempool state, build a PSBT)

### Asynchronous endpoints (job queue)
- Custodial provider API calls (balance fetch, withdrawal initiation)
- Multi-step operations (e.g., "sweep all custodials now")
- Long-running blockchain scans

The async pattern:
```
POST /api/v1/trading/sweep        → 202 Accepted { job_id }
GET  /api/v1/jobs/{job_id}        → 200 OK       { status, result | error }
```

For long jobs the frontend can either poll `GET /jobs/{id}` or subscribe to events on the SSE stream filtered to that job.

### Live updates (Server-Sent Events)
The backend exposes a single SSE endpoint that streams events from the bus to the frontend, filtered by topic and by Holdings the user is viewing. This replaces frontend polling for fresh data.

```
GET /api/v1/events/stream?topics=chain.*,holding.*,banking.*
  → text/event-stream
  → events arrive as { topic, payload, timestamp }
```

## Network security posture (dev / personal-use phase)

- **All services bind to 127.0.0.1.** Docker Compose explicitly maps ports to `127.0.0.1:PORT`, never `0.0.0.0`.
- **No TLS** — everything is on localhost. Adding TLS later (when remote access via WireGuard or Tailscale is added — see `future_iterations.md` "Remote access for self-hosters") is a configuration change, not an architectural one.
- **No authentication layer on the API in the dev phase.** The security boundary is the operating system user account. The authentication layer is a private-ship requirement (per ADR-0003); the public-ship event hardens it further. Documented in the threat model.
- **CORS** — the backend accepts requests only from the local frontend origin.

## Configuration model

- All configuration is in a single `configuration.toml` mounted into the backend container.
- Secrets (custodial provider credentials, node RPC password, future Lightning macaroons) are stored encrypted; see module 03 for the cryptography details.
- Development mode uses the OS keyring; Docker mode uses an encrypted Postgres table unlocked by a passphrase the user enters at startup.
- **The passphrase is never stored.** If the user restarts the container, they re-enter it. Until unlock, all endpoints that require a secret return `423 Locked`.

## Project layout

```
btc-app/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── worker.py                # Worker entry point (registers listeners/subscribers/schedulers)
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── holdings.py
│   │   │       ├── descriptors.py
│   │   │       ├── ledger_entries.py
│   │   │       ├── banking.py
│   │   │       ├── trading.py
│   │   │       ├── analysis.py
│   │   │       ├── jobs.py
│   │   │       ├── events_stream.py
│   │   │       ├── configuration.py
│   │   │       └── unlock.py
│   │   │
│   │   ├── domain/                  # Pure domain types (dataclasses)
│   │   │   ├── holding.py           # Holding, Account, Purse, Strongbox, Vault
│   │   │   ├── descriptor.py
│   │   │   ├── ledger_entry.py
│   │   │   ├── payment_request.py
│   │   │   ├── invoice.py
│   │   │   ├── custodial_provider.py
│   │   │   ├── sweep_policy.py
│   │   │   ├── job.py
│   │   │   ├── user_profile.py
│   │   │   └── enums.py
│   │   │
│   │   ├── adapters/                # Anti-Corruption Layer
│   │   │   ├── node_adapter.py      # bitcoind JSON-RPC
│   │   │   ├── chain_event_adapter.py  # bitcoind ZeroMQ
│   │   │   ├── custodial_adapter.py # ccxt wrapper, normalizes per-provider quirks
│   │   │   └── lightning_adapter.py # Lightning iteration
│   │   │
│   │   ├── services/                # Business logic
│   │   │   ├── holding_service.py
│   │   │   ├── banking_service.py
│   │   │   ├── trading_service.py
│   │   │   ├── policy_validator.py  # warns about risky sweep configurations
│   │   │   ├── analysis_service.py  # declared-vs-observable security checks
│   │   │   ├── blueprint_analyzer.py
│   │   │   └── lightning_provider.py  # Lightning iteration interface
│   │   │
│   │   ├── workers/
│   │   │   ├── listeners/
│   │   │   │   └── chain_listener.py
│   │   │   ├── schedulers/
│   │   │   │   ├── custodial_poll_scheduler.py
│   │   │   │   ├── sweep_scheduler.py
│   │   │   │   └── analysis_scheduler.py
│   │   │   └── subscribers/
│   │   │       ├── custodial_poller.py
│   │   │       ├── sweep_engine.py
│   │   │       ├── categorizer_suggester.py
│   │   │       ├── live_update_bridge.py
│   │   │       └── audit_reconciler.py
│   │   │
│   │   ├── infrastructure/
│   │   │   ├── event_bus.py         # interface + Redis impl
│   │   │   ├── job_queue.py         # RQ wrapper
│   │   │   ├── secrets.py           # keyring + encrypted-db backends
│   │   │   └── cryptography.py      # Argon2id + AES-256-GCM helpers
│   │   │
│   │   ├── repositories/            # DAO / DB access
│   │   ├── models/                  # SQLAlchemy ORM
│   │   ├── schemas/                 # Pydantic schemas for the API
│   │   ├── migrations/              # Alembic
│   │   └── configuration.py
│   │
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   ├── lib/
│   │   │   ├── api/                 # Typed API client (generated from OpenAPI)
│   │   │   ├── components/
│   │   │   ├── stores/
│   │   │   └── events/              # SSE consumer
│   │   └── app.html
│   ├── static/
│   │   └── manifest.json
│   ├── package.json
│   ├── svelte.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

## Dependency discipline

- All Python dependencies pinned via `pyproject.toml` with exact versions.
- All npm dependencies pinned via `package-lock.json`.
- Dependency updates reviewed manually, not auto-merged.
- No dependency that requires an account, paid tier, or phone-home license check.

## Testing strategy

- **Unit tests** for all services, the policy validator, the blueprint analyzer, and the cryptography helpers.
- **Integration tests** for API endpoints, using a test Postgres and a `regtest` `bitcoind`.
- **Adapter tests** with recorded fixtures for ccxt responses (Kraken, Bitstamp), so we can detect upstream changes.
- **Event-flow tests** that publish events on a test bus and assert subscribers behave correctly.
- **End-to-end tests** (Playwright or Cypress) are post-shipping. Not a current gate.
- **Target coverage**: 80% on backend `services/`, `domain/`, and `adapters/`. Coverage on API routes and frontend is not a current gate.

## Observability (current minimum)

- Structured JSON logging to stdout (captured by Docker).
- Log levels configurable per module via configuration.
- Sensitive data redacted at the log layer (any field name matching a denylist of `key|secret|passphrase|token|cookie` is replaced with `***`).
- No metrics endpoint, no tracing, no external log shipping. (Per `00_README.md` "Out of scope": no telemetry, ever.)
- A `/api/v1/health` endpoint returns service health (database reachable, `bitcoind` reachable, Redis reachable, last custodial poll time, unlock state).
