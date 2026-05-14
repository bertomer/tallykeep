# 01 — Architecture

This module describes TallyKeep's architecture at the level the
spec needs to lock: surfaces, trust zones, key custody, the
backend's internal layering, and the runtime patterns
(persistence-first, event bus, request shapes). Implementation
detail — the directory tree, exact event-topic strings, specific
worker-component file names — lives in code, not here. Cross-refs
into `decisions/` for foundational calls.

## Surfaces and trust zones

TallyKeep is **not** a backend-only product. Several surfaces
participate at runtime, each with different capabilities and
different trust posture. An agent reasoning about any feature
should first locate which surface is responsible.

| Surface | What it runs | What it can do | What it cannot do |
|---|---|---|---|
| **Backend** | FastAPI app, Postgres, Redis, worker process. Docker Compose stack on the user's host (or hosted-tier infrastructure when that ships). | Observe the chain via bitcoind. Construct PSBTs. Persist Holdings, Descriptors, LedgerEntries. Call custodial-provider APIs. Emit and consume domain events. Encrypt and decrypt third-party credentials with the user's passphrase. | **Hold spending keys.** Sign anything. Create user accounts on TallyKeep infrastructure. |
| **Capacitor client** | The mobile app (Capacitor wrap of the SvelteKit PWA), distributed via app store / sideload. | Hold spending keys for `TALLYKEEP_MANAGED` and `EXTERNAL_IMPORTED` Purses, in OS Keychain/Keystore, biometric-gated. Sign with the on-device key via NativeBridge. Read camera (QR). Subscribe to push notifications. | Transmit spending keys to the backend. Sign for Holdings whose keys live elsewhere (a Strongbox's hardware wallet, an external-watch-only Purse's source wallet). |
| **Browser PWA client** | The SvelteKit PWA in any browser (desktop Chrome / Safari / Firefox, mobile browsers, or installed-as-PWA). Same SvelteKit code as the Capacitor client; the `NativeBridge` interface stubs out. | Observe Holdings. Render flows. Compose PSBTs server-side and download the file. | Hold spending keys (no OS-grade secure storage primitive). Sign with on-device keys. Operations requiring keys gate honestly with "install the app / sign externally". |
| **bitcoind** | Bitcoin Core node, pruned or full, running on the user's host (or shared in the hosted tier — see `future_iterations.md`). | Serve chain data via JSON-RPC. Push live events via ZeroMQ. Hold the source-of-truth view of the chain. | Sign anything. The backend never sends keys to bitcoind for signing. |
| **Custodial provider** | Third-party exchange / broker API (Kraken, Bitstamp; future Lemon, Buenbit, Belo, Coinbase Advanced, Swissquote). | Hold custody of the user's BTC (and stablecoin) balances at the provider. Accept withdrawals to whitelisted addresses. | Anything TallyKeep is responsible for. TallyKeep owns the API credentials encrypted at rest; the provider owns the funds. |
| **Hardware wallet** | The user's external signing device (Coldcard, Trezor, Ledger, Jade, BitBox, airgapped laptop). | Hold the spending key for Strongbox or Vault Holdings. Sign PSBTs offered to it by file / USB / QR. | Reach TallyKeep directly. The user is the bridge — they export a PSBT, walk it to the hardware wallet, walk the signed PSBT back. |

**Backend network binding (dev / personal-use phase):** all
services bind to `127.0.0.1` only. Docker Compose maps ports to
`127.0.0.1:PORT`, never `0.0.0.0`. No public listener. The
security boundary is the OS user account. The authentication
layer (passphrase + biometric on Capacitor) is a private-ship
requirement (per ADR-0003); the public-ship event hardens it
further. Remote access for self-hosters is documented in
`future_iterations.md` "Remote access for self-hosters" and is
opt-in.

**Hosted-tier surface:** when the hosted tier ships (per
`future_iterations.md`), the backend moves from "user's host" to
"TallyKeep infrastructure" but the trust zones do **not** change:
the backend still never holds spending keys. The Capacitor
client's key-holding model is identical between self-hosted and
hosted tiers — the seed lives on the user's phone, never on the
server, regardless of which backend the phone talks to.

## Key custody model

Per **ADR-0009**, key custody splits into four zones. The spec
states it once here; per-Holding modules reference back rather
than restating.

1. **Backend** — never holds spending keys, ever. Holds
   descriptors, custodial credentials (encrypted at rest with
   the user's passphrase), configuration.
2. **Capacitor client** — holds spending keys for
   `TALLYKEEP_MANAGED` and `EXTERNAL_IMPORTED` Purses, in OS
   secure storage, biometric-gated, never transmitted to the
   backend. Per-client signing-capability check (per ADR-0006)
   is local: a different Capacitor instance reaching the same
   backend will see the Holding as view-only.
3. **Hardware wallet** — holds Strongbox / Vault keys. TallyKeep
   choreographs (PSBT export → external sign → re-import →
   broadcast); never sees the key.
4. **Custodial provider** — holds Account keys server-side; the
   user manages keys with the provider.

The browser PWA never holds spending keys (no OS-grade secure
storage primitive). Operations requiring local keys present
honest gates ("install the app / sign externally"), not
fake-signing.

## Service topology

The backend deployment is a Docker Compose stack:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         User's host (localhost)                          │
│                                                                          │
│  ┌──────────────┐                                                        │
│  │   Frontend   │  SvelteKit PWA (browser) or Capacitor wrap (mobile).   │
│  │  SvelteKit   │  Talks to Backend over HTTP and SSE.                   │
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
│                                   │  listeners / schedulers /  │         │
│                                   │  subscribers (see below)   │         │
│                                   └────────────────────────────┘         │
│                                                                          │
│       Network binding: ALL services on 127.0.0.1 only.                   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Services

- **bitcoind** — Bitcoin Core image. Pruned or full (user choice).
  RPC and ZeroMQ on the Docker internal network only. Backend is
  the sole client.
- **backend** — FastAPI application. HTTP API + Server-Sent
  Events. Talks to bitcoind (RPC), Postgres, Redis (events + job
  queue), and ccxt-wrapped custodial-provider APIs. Does not run
  scheduled tasks itself.
- **worker** — same Python codebase, separate entry point. Runs
  three component kinds: listeners (consume external feeds →
  events), schedulers (emit events on a timer), subscribers
  (react to events).
- **postgres** — persistent state. Schema managed via Alembic.
- **redis** — two roles: event bus (publish/subscribe) and job
  queue (RQ). One service, two uses; may split if it ever
  bottlenecks.
- **frontend** — SvelteKit PWA static files served by a
  lightweight nginx, or by the backend itself in the dev phase.

## Internal layering: ACL, queue, bus

External systems and the domain are separated by three distinct
layers, each with a single job:

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
│   • CustodialProviderAdapter (ccxt: Kraken, Bitstamp, …)     │
│   • NodeAdapter (bitcoind RPC)                               │
│   • ChainEventAdapter (bitcoind ZeroMQ)                      │
│   • LightningProviderAdapter (Lightning iteration)           │
└──────────────────────┬───────────────────────────────────────┘
                       │ wrapped by
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Job queue (RQ on Redis)                                     │
│  Scheduling, retries, timeouts, persistence, rate-limit      │
│  handling, error capture. Knows nothing about data shapes.   │
└──────────────────────┬───────────────────────────────────────┘
                       │ publishes results to
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Event bus (Redis pub/sub, abstracted behind an interface)   │
│  Domain events. Many subscribers, no producer↔consumer       │
│  coupling.                                                   │
└──────────────────────────────────────────────────────────────┘
```

Each layer protects against a different failure mode:

- The **adapter layer** protects the domain's vocabulary. If
  Kraken renames a field, one file changes.
- The **job queue** protects runtime reliability. A slow
  custodial API call doesn't block a user-facing request.
- The **event bus** protects coupling. New subscribers attach
  without touching producers.

## Persistence-first for non-losable events

Redis pub/sub is not durable. A subscriber that's down when an
event fires loses it. Acceptable for ephemeral notifications
(UI live updates, "categorize this transaction"); **not**
acceptable for state transitions where loss means wrong
information about reality.

The pattern: **persist first, emit second.** When a non-losable
event happens, the producer:

1. Writes a row to a domain-specific audit table
   (`sweep_execution`, `payment_request`, `broadcast_attempt`).
2. Then publishes the event on the bus.

If step 2 fails or no subscriber is listening, step 1 is the
source of truth. A periodic reconciler scans recent audit-table
rows and re-emits events for anything not acknowledged. The
system tolerates restarts, transient Redis problems, and
subscriber outages without losing state.

## Event taxonomy

Event topics are stable. Producers and subscribers both speak
this taxonomy. Topics are namespaced by domain area:

- `chain.*` — chain events from bitcoind ZeroMQ
- `holding.*` — Holding-level derived events (balance changed,
  UTXO received/spent)
- `banking.*` — PaymentRequest and Invoice lifecycle events
- `treasury.*` — custodial balance and sweep events
- `ledger_entry.*` — categorization events
- `analysis.*` — declared-vs-observable discrepancy events
- `lightning.*` — defined now; emitted once the Lightning
  iteration ships
- `system.*` — startup, unlock, external service connectivity

Existing topics never change shape without a version bump. The
exhaustive topic list with payload shapes lives in code (event
constants module); the spec promises only stability of names and
the namespace prefixes above.

## Worker components

The worker process runs three component kinds:

- **Listeners** translate external feeds into events. Current:
  `ChainListener` (bitcoind ZMQ). Lightning iteration adds
  `LightningListener` (CLN / LND gRPC).
- **Schedulers** emit events on a timer. Current:
  `CustodialPollScheduler`, `SweepScheduler`, `AnalysisScheduler`.
- **Subscribers** react to events. Current: `CustodialPoller`,
  `SweepEngine`, `CategorizerSuggester`, `LiveUpdateBridge`,
  `AuditReconciler`.

Specific component file names and exact responsibilities live in
the codebase; the spec promises only that the three kinds exist
and that adding a new component fits one of them.

## Request shape

### Synchronous endpoints (default)
- Read operations against local state (balances, transactions,
  Holdings, configuration).
- Node-local operations (derive an address, get mempool state,
  build a PSBT).

### Asynchronous endpoints (job queue)
- Custodial-provider API calls (balance fetch, withdrawal
  initiation).
- Multi-step operations ("sweep all custodials now").
- Long-running blockchain scans.

The async pattern: a POST returns `202 Accepted` with a `job_id`;
the client polls a `GET /jobs/{id}` endpoint or subscribes to
the SSE stream filtered to that job. Specific endpoint paths
live in `api/openapi.yaml`.

### Live updates (Server-Sent Events)
The backend exposes a single SSE endpoint that streams events
from the bus to the frontend, filtered by topic and by Holdings
the user is viewing. Replaces frontend polling. Endpoint shape
in `api/openapi.yaml`.

## Network security posture (dev / personal-use phase)

- All services bind to `127.0.0.1`.
- No TLS — everything is on localhost. Adding TLS later (with
  WireGuard / Tailscale for remote access — see
  `future_iterations.md`) is a configuration change, not an
  architectural one.
- No authentication layer on the API in the dev phase. Security
  boundary is the OS user account. The auth layer (passphrase +
  biometric on Capacitor) is a private-ship requirement (per
  ADR-0003); the public-ship event hardens it further.
- CORS — backend accepts requests only from the local frontend
  origin.

## Configuration model

- All configuration in a single `configuration.toml` mounted into
  the backend container.
- Secrets (custodial-provider credentials, node RPC password,
  future Lightning macaroons) stored encrypted — see module 03
  for the cryptography details.
- Dev mode uses the OS keyring; Docker mode uses an encrypted
  Postgres table unlocked by a passphrase the user enters at
  startup.
- **The passphrase is never stored.** On container restart the
  user re-enters it. Until unlock, all endpoints that require a
  secret return `423 Locked`.
- `server_label` — free-form human-readable name the operator
  sets during stack installation ("Rémy's home stack",
  "Argentina parents' Umbrel"). Surfaced to clients on pairing
  and connection sanity-checks. Optional; absent value means
  clients render only the connection endpoint or hosted-tier
  connection-ID.

## Dependency discipline

- Python dependencies pinned via `pyproject.toml` with exact
  versions.
- npm dependencies pinned via `package-lock.json`.
- Dependency updates reviewed manually, not auto-merged.
- No dependency that requires an account, paid tier, or
  phone-home license check.

## Testing strategy

- **Unit tests** for services, the policy validator, the
  blueprint analyzer, the cryptography helpers.
- **Integration tests** for API endpoints, using a test Postgres
  and a `regtest` `bitcoind`.
- **Adapter tests** with recorded fixtures for ccxt responses
  (Kraken, Bitstamp), so upstream changes surface.
- **Event-flow tests** that publish events on a test bus and
  assert subscribers behave correctly.
- **End-to-end tests** (Playwright / Cypress) are post-shipping.
  Not a current gate.
- **Smoke tests** — a `.ps1` suite run against the running
  backend at iteration handoff (per PROCESS.md §2.7 stage 4).
- **Target coverage**: 80% on backend `services/`, `domain/`,
  `adapters/`. Coverage on API routes and frontend is not a
  current gate.

## Observability (current minimum)

- Structured JSON logging to stdout (captured by Docker).
- Log levels configurable per module via configuration.
- Sensitive data redacted at the log layer — any field name
  matching the denylist `key|secret|passphrase|token|cookie` is
  replaced with `***`.
- No metrics endpoint, no tracing, no external log shipping.
  (Per `00_README.md` "Out of scope": no telemetry, ever.)
- A health endpoint (path in `api/openapi.yaml`) reports service
  health: database reachable, bitcoind reachable, Redis reachable,
  last custodial poll time, unlock state.

## What lives in code, not here

- Directory tree of `backend/` and `frontend/` — lives in the
  repo; reading it costs zero. The spec doesn't restate it.
- Exact event-topic strings with payload shapes — the event
  constants module is the source of truth.
- Specific worker-component file names and responsibilities —
  see the worker module.
- Endpoint paths, request and response shapes — `api/openapi.yaml`.
- SQL DDL for tables — Alembic migrations; module 03 documents
  the invariants and secret-storage cryptography.
