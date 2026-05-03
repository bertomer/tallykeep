# Project Context — TallyKeep

This file records decisions made during planning conversations with the human reviewer
(the user). It is the source of truth for "what we agreed to" outside of the spec itself.
Entries are append-only with the date the decision was made.

---

## 2026-05-01 — Initial planning session

### Environment & tooling

- **Host platform**: Windows 11. Codename for the project: `tallykeep`.
- **Containerization preference**: **everything runs in Docker**. The user prefers
  fully virtualized stack to avoid host pollution. If a tool is missing on the host
  *and* the assistant cannot install it itself, surface this to the user explicitly.
- **Database**: Postgres 15+ via Docker Compose from day one. (SQLite path from the
  spec is *not* used; we go straight to the production target.)
- **Redis**: real Redis via Docker from day one. Event bus and job queue both use it.
  An in-memory `EventBus` implementation exists alongside (for unit tests) but is not
  the runtime path.
- **Bitcoind**: Bitcoin Core via official Docker image, `regtest` mode for development.

### Iteration shape

- **Horizontal layers** (per spec module 00 ordering): scaffolding → savings → banking
  → profiles & flags → trading → UX → lightning placeholder → v1 polish.
- **Network ladder**: develop and prove on `regtest` first. Moving to `testnet` and
  `mainnet` is its own dedicated milestone *after* the local stack is fully proven.
- **No shortcuts** that compromise the v1 end goal, but **batched MVP cuts are allowed**
  if a milestone balloons — provided the deferred work is tracked and shipped before v1
  is called done. Rule: don't rewrite anything we already shipped.
- **End-to-end completion is required.** This is a long arc; we are not stopping at
  "first useful slice."

### Testing

- **Non-regression suite (NRT)** grows with each iteration. Every new feature lands
  with the tests that exercise it; every iteration must end with the full NRT green.
- **Scope per spec**: unit (domain, services, adapters), integration (FastAPI + regtest
  bitcoind), adapter tests with recorded ccxt fixtures, event-flow tests with the
  in-memory bus.
- **Coverage gate**: 80% on `services/`, `domain/`, `adapters/` (per spec). API and
  frontend coverage are not v1 gates.
- **Playwright (E2E)**: deferred to the very end (post-UX), if at all.
- **CI**: open question; see Q8 in conversation. Default for now is "local-only";
  GitHub Actions can be added when the repo is pushed.

### Open spec questions resolved

| Spec Q | Decision | Notes |
|---|---|---|
| Q1 — Sweep confirmation default for Intermediate | `required = true` | Default for first user experience; toggle-able via feature flag. |
| Q3 — Number format | sats-first, BTC secondary | User-toggleable preference. |
| Q7 — Coin-selection algorithm default | `BranchAndBound` | User-toggleable per-payment under Sovereign profile. |

### Naming

- Working **codename**: `tallykeep`. Used as the Python package name
  (`backend/tallykeep/`), repo name, Docker network name, and DB name.
- Final product name is **not yet locked**. Renaming later is acceptable; we keep
  marketing-language and branding out of code identifiers (per spec module 13).

### Test execution & CI (resolved 2026-05-01 mid-session)

- **Tests run on every commit** locally via a versioned pre-commit hook
  (`.githooks/pre-commit`) — runs `pytest` inside the backend container.
- **GitHub Actions** workflow (`.github/workflows/tests.yml`) mirrors the local hook:
  same script, same image, same exit semantics. Set up now so it activates the moment
  the repo is pushed.
- **One git repo from the start** (initialized at M0). Stages tracked through commits.
- **Bypass policy**: `--no-verify` only when the spec author explicitly authorizes
  it. Never silently.

### What is *not* yet decided

- **Real-network milestone scope** (testnet → mainnet) — separate work, after local
  proof. Will get its own Q&A pass before being scheduled.
- **Multisig descriptor support timing** (spec Q11) — defer until v1 personal use shows
  the dissonance is unbearable; otherwise v2.
- **Test fixture recording strategy for ccxt** — recorded once against a real Kraken /
  Bitstamp test account during M8, then versioned in the repo.

### Deferred to v2

- **Manual address registration past the gap-limit cap.** Descriptor `gap_limit`
  is capped at 40 (2× the BIP 44 standard of 20). Users who've already issued
  addresses far beyond that in another wallet — and so won't be picked up by a
  40-deep scan — need a way to register those addresses manually so the
  scanner can attach them to the right descriptor. Out of scope for v1;
  revisit in v2 alongside the multisig descriptor work.

---

## M0 — completed 2026-05-01

Project scaffolded, Docker Compose stack working end-to-end:
- `postgres`, `redis`, `bitcoind` (regtest), `backend`, `worker`, `frontend` all start
  cleanly and stay healthy.
- `/api/v1/health` returns the locked-shape contract; status `degraded` because
  subsystem probes are placeholders pending their respective milestones.
- 4 unit tests in the NRT, all green.
- Pre-commit hook + GitHub Actions both wired to `./scripts/run-tests.sh`.
- One commit on `main`.

---

## M1 — completed 2026-05-01

Domain types, persistence layer, secret store, and unlock flow.

Four sub-commits (M1.1 → M1.4):
- **M1.1** — every spec-module-02 entity as a frozen dataclass with construction-time
  invariants, including the structural commitment that no domain entity has a field
  for Bitcoin signing material.
- **M1.2** — SQLAlchemy 2.0 declarative models for all 21 spec-module-03 tables, an
  Alembic environment that respects test-injected URLs, and the initial migration
  with reversible `upgrade()` / `downgrade()`.
- **M1.3** — `infrastructure/cryptography.py` (Argon2id KDF, AES-256-GCM authenticated
  encryption, 12-byte fresh nonce per encryption) and `infrastructure/secrets.py`
  (SecretStore ABC + InMemorySecretStore + EncryptedDatabaseSecretStore, with a
  reserved canary secret for passphrase verification).
- **M1.4** — `POST /api/v1/unlock` and `POST /api/v1/unlock/initialize`,
  `LockMiddleware` returning 423 for non-allowlisted paths while the store is locked,
  and real probes for `database` (SELECT 1) and `unlocked` (store state) on
  `/api/v1/health`. Other subsystem probes still return `not_yet_implemented` until
  their owning milestone lands.

NRT now **121 tests** (109 unit + 12 integration). Integration tests auto-skip when
Postgres is not running locally; they execute on every CI run via the GitHub Actions
workflow. Unit tests run with the database URL cleared via an autouse marker-aware
fixture so they stay fast (~5s for 109 tests).

Verified end-to-end against the live Compose stack:
- `423` while locked → `503` on `/unlock` before init → `200` on initialize →
  `404` on `/api/v1/holdings` (route doesn't exist yet, but the middleware passes
  through, proving unlock succeeded) → `401` on `/unlock` with a wrong passphrase.

---

## 2026-05-02 — Permissions and tooling

- **Project Claude permissions** committed at `.claude/settings.json`. Allows the
  in-milestone workflow (git read & non-destructive write, `docker compose` without
  `-v`, test scripts, project-local file edits, `curl`/`curl.exe`) without prompts.
  Denies destructive operations (`docker compose down -v`, volume rm, force push,
  `git reset --hard`, `git rebase -i`, `git commit --amend`, `--no-verify`,
  `rm -rf`, `Remove-Item -Recurse|-Force`).
- **`.gitignore`** updated: `.claude/settings.json` is committed (team-wide source
  of truth); `.claude/settings.local.json` and session caches are ignored.
- **README quickstart**: PowerShell users need `curl.exe --%` (stop-parsing token)
  to pass JSON bodies cleanly — documented in the README quickstart.

---

## M2 — completed 2026-05-02

Event bus + job queue + persist-first audit reconciler.

Three sub-commits (M2.1 → M2.3):
- **M2.1** — `infrastructure/event_bus.py`: `Event` dataclass, `EventBus` ABC,
  topic-pattern matcher (`*` wildcard, dotted segments), `InMemoryEventBus`
  (synchronous, used in tests and in-process subscribers), `RedisEventBus` (Redis
  pub/sub with a background-thread read loop, JSON envelopes carrying
  id/topic/payload/timestamp). Both backends swallow handler exceptions so a
  failing subscriber cannot poison others.
- **M2.2** — `infrastructure/job_queue.py`: `JobInfo` snapshot, `JobQueue` ABC,
  `InMemoryJobQueue` (synchronous), `RedisQueueJobQueue` wrapping `rq.Queue` with
  `rq.SimpleWorker` available as a `drain_for_tests()` helper. Job ids are UUIDs.
  RQ status strings translate to our domain `JobStatus` enum.
- **M2.3** — `infrastructure/event_emission.py`: `PersistentEmitter` for the
  persist-first-emit-second pattern (writes `event_emission_log` row before
  publishing; `acknowledge(event_id)` sets `acknowledged_at`); `AuditReconciler`
  scans rows older than the grace period that are still unacknowledged and
  re-emits them with `__replay__: True` in the payload.
- `/api/v1/health` now includes real `redis` (PING with 2s timeout) and
  `event_bus` (delegates to bus.is_healthy()) probes alongside `database` and
  `unlocked`. Only `bitcoind` still returns `not_yet_implemented`.
- `tallykeep.worker` registers the AuditReconciler at startup (5-minute grace
  period, scans every 30s) when both Redis and Postgres are configured. Tolerates
  degraded environments — runs no-ops if its dependencies are missing.

Pinned new deps: redis 5.2.0, rq 1.16.2.

NRT now **181 tests** (141 unit + 40 integration). Full suite green in ~13s with
all infrastructure up.

Verified live: `database`, `redis`, `event_bus` all `ok: true`; worker logs show
`worker: started (bus=redis, reconciler=on)`.

---

## M3 — completed 2026-05-02

API skeleton: every spec-module-04 route registered. Three sub-commits:

- **M3.1** — `/api/v1/profile` GET/PATCH, `/api/v1/feature-flags` GET,
  `/api/v1/configuration` GET/PATCH (full implementations).
  - `services/profile_presets.py` is the canonical preset table (BEGINNER /
    INTERMEDIATE / SOVEREIGN dicts) plus `resolve_feature_flags(preset, overrides)`.
  - `repositories/user_profile.py` and `repositories/runtime_configuration.py`
    give thin DAOs over the singleton row and the flat key-value table.
  - `services/configuration_service.py` un/groups dotted keys into the nested
    section shape (`bitcoind`, `fee_estimation`, `custodial_polling`, `analysis`,
    `notifications`). Pydantic schemas use `extra="forbid"` so unknown sections
    or fields return 422.
- **M3.2** — Every other module-04 route registered as a 501-stub with an
  RFC 7807 Problem Details body that names the milestone the real handler lands
  in (M4: descriptors and per-type Holding creation; M5: chain-derived queries,
  utxo, ledger-entries, analysis, jobs; M6: banking; M8: trading; M14: export).
  - `api/v1/_stubs.py::not_implemented_response(milestone, route)` returns a
    `JSONResponse` directly so the body sits at the top level
    (RFC 7807-compliant; no FastAPI `{"detail": ...}` envelope).
  - 73 parametrized contract tests verify each (method, path) returns 501 with
    the right milestone tag round-tripped.
- **M3.3** — `/api/v1/events/stream` SSE scaffold + Lightning stubs (spec module
  08, milestone v1.5).
  - SSE endpoint subscribes to the bus, marshals events into an asyncio queue
    via `loop.call_soon_threadsafe` (bus handlers run on a different thread for
    Redis), formats SSE frames, drops oldest on backlog (1000-event cap), and
    unsubscribes on client disconnect. Emits a handshake comment when the
    subscription is registered so clients know the stream is live.
  - Returns 503 when no event bus is configured (e.g. `TALLYKEEP_REDIS_URL`
    unset).
  - Lightning stubs at `/api/v1/lightning/{status,balance,invoices,pay,
    payments,channels}`, all reserved for v1.5.

**Test fixture changes during M3**:
- `tests/conftest.py::client` now installs an *unlocked* InMemoryStore so tests
  reach the routes without each one re-implementing the unlock dance. The
  lock-middleware behavior is still exercised explicitly by
  `tests/unit/test_unlock_endpoints.py` via its own fixture.
- `tests/conftest.py::app_with_db` is the new fixture for endpoint integration
  tests: fresh per-test Postgres DB, migrations applied, app wired with an
  unlocked store + cheap-Argon2id parameters.

**Deferred**: SSE end-to-end streaming tests through TestClient deadlock on the
httpx + StreamingResponse + cross-thread publisher combination. The route is
covered by 503-with-no-bus, OpenAPI-inclusion, and the SSE-frame-format
helpers. Full streaming verification lands in M9 with the LiveUpdateBridge,
against a real running uvicorn or via async httpx.

NRT now **301 tests** (239 unit + 62 integration). Suite ~27s with infra up,
~5s without.

---

## 2026-05-03 — Tooling

- **`scripts/dev-reset.sh` and `.ps1`** — one-command wipe + restart of the
  Compose stack volumes (Postgres, Redis, bitcoind regtest). Optional
  `--keep-down` / `-KeepDown`. Allowlisted in `.claude/settings.json` so I
  can run it autonomously; the bare `docker compose down -v` stays denied.

---

## M4 — completed 2026-05-03

Savings layer foundations: Holdings + Descriptors + BDK address derivation.

Pinned new dep: bdkpython 2.3.1 (the BDK Rust library bindings). Spec
module 13 flags it as a "known risk"; if API churn becomes a problem we have
the option of falling back to a thin Rust sidecar — not needed at this point.

Two sub-commits:

- **M4.1** — `adapters/descriptor_adapter.py`: anti-corruption layer around
  bdkpython for parse + address derivation. Domain code never imports bdk.
  - Single-key descriptors only (PKH, WPKH, SH_WPKH, TR-single). Multisig and
    multipath descriptors parse but are rejected at import; multisig support
    is deferred to v2 per spec module 13.
  - Network mapping: bdk's `Network.BITCOIN` → our `Network.MAINNET`.
  - Cap on input length (4 KB) per spec module 10 / S6.
- **M4.2** — Holdings + Descriptors + Addresses persistence and endpoints.
  - `repositories/holding.py` adds `insert_row(...)` taking explicit fields so
    the service can write the holding row before descriptors that FK back to
    it (the domain dataclass requires non-empty `descriptor_ids` for non-Account
    types, which can only be true after descriptors are inserted).
  - `repositories/descriptor.py` covers Descriptor + Address CRUD plus
    `next_unused_address` (M5 will repopulate this once the chain scanner
    advances `first_seen_height`).
  - `services/holding_service.py` orchestrates per-type creation atomically:
    holding row → flush → descriptors + their gap-limit-many derived addresses
    → return the canonical domain Holding (validated by `__post_init__` once
    descriptor_ids is populated).
  - Endpoints fully implemented: per-type creation (Purse / Strongbox / Vault),
    list (with filters), get, patch, archive, change-type. Account creation
    stays a 501 stub pending M8's CustodialProvider integration. Descriptors
    have CRUD + addresses listing + next-receiving.

**Test fixture changes during M4**:
- `tests/conftest.py::app_with_db` carried over from M3 — fresh per-test
  Postgres database with migrations applied, unlocked InMemoryStore
  pre-installed, cheap-Argon2id parameters. Used by every M4 endpoint test.

**Notes for the reviewer**:
- BDK derivation is exercised against the standard
  `abandon abandon ... about` test mnemonic so address values are
  mnemonic-derived facts, not bdk-version-bound. Tests assert exact prefixes
  (bc1q for native segwit on mainnet, tb1q for testnet, 1 for legacy).
- Descriptor uniqueness is a database-level invariant (spec module 03):
  `uq_descriptor_expression` enforces that two holdings can't share the same
  descriptor expression. Endpoint surfaces this as 409 Conflict.
- Descriptor delete refuses if any addresses still reference it (returns 409).
  Address cascade-delete lands in M5 with the chain scanner — for now,
  archiving the owning holding is the right way to retire it.

NRT now **339 tests** (260 unit + 79 integration). Suite ~43s with infra up.

---

## M5 — in progress (M5.1 + M5.2 complete, 2026-05-03)

Savings layer foundations: live bitcoind RPC + the first end-to-end chain
scan that turns `scantxoutset` results into UTXO / OnChainTransaction /
LedgerEntry rows.

- **M5.1** — `adapters/node_adapter.py` is the anti-corruption layer for
  bitcoind JSON-RPC. Public surface: `get_blockchain_info`,
  `scan_descriptors`, `get_raw_transaction`, `get_mempool_entry`,
  `estimate_smart_fee`, `send_raw_transaction`, `is_healthy`. Translates RPC
  failures into typed exceptions (`NodeUnavailable`, `NodeAuthError`,
  `NodeMethodNotFound`, `NodeRpcError`). `/api/v1/health` adds the real
  `bitcoind` probe (`chain=regtest height=N` detail) — was the last
  `not_yet_implemented` probe.
- **M5.2** — `services/chain_scan_service.py` ties the adapter to the
  persistence layer. `ChainScanService.initial_scan(descriptor)` runs
  `scantxoutset` on the descriptor's external + change branches separately,
  parses the leaf index out of bitcoind's per-UTXO `desc` annotation
  (`wpkh([fp/branch/index]pubkey)#chk`), looks up the matching `address`
  row by `(is_change, derivation_index)`, and upserts UTXO +
  OnChainTransaction + LedgerEntry rows. Idempotent on re-run.

  Endpoints implemented (replacing M5 stubs):
    `POST /descriptors/{id}/rescan`, `GET /descriptors/{id}/utxos`,
    `GET /descriptors/{id}/balance`, `GET /utxos`,
    `POST /utxos/{id}/freeze`, `POST /utxos/{id}/unfreeze`,
    `GET /utxos/{id}/hygiene` (returns the empty hygiene_flags list — the
    actual flag computation lands in M5.4).

Two non-obvious bits worth recording for future-me:

- **bitcoind's `scantxoutset` does NOT populate the `address` field** for
  descriptor scans, only `scriptPubKey` + `desc`. String-equality matching
  on address would silently miss every UTXO; matching by leaf index parsed
  from the desc annotation works.
- **Regtest's halving cliff** at ~10 halvings (height ~1500) makes a
  newly-mined faucet wallet effectively zero-balance because the per-block
  subsidy has shrunk to fractions of a sat. The session-scoped
  `bitcoind_clean_chain` fixture in `tests/conftest.py` invalidates the
  chain back to height 1 once per session when the chain is past depth
  1500. That keeps multi-test integration sessions reliably funded.

NRT now **377 tests** (282 unit + 95 integration). Suite ~100s with infra
up.

Remaining M5 sub-stages:
- **M5.3** — ChainEventAdapter (bitcoind ZMQ) + ChainListener worker
  (live tx detection, no manual rescan needed)
- **M5.4** — UTXO hygiene flags computation
- **M5.5** — Declared-vs-observable security analyzer
- **M5.6** — LedgerEntry endpoints + categorization suggestions
- **M5.7** — Holding summary + global summary endpoints + final docs

---
