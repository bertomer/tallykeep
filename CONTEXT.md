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
