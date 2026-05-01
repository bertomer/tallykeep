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

### What is *not* yet decided

- **CI provider** (Q8 from this session) — pending user answer.
- **Real-network milestone scope** (testnet → mainnet) — separate work, after local
  proof.
- **Multisig descriptor support timing** (spec Q11) — defer until v1 personal use shows
  the dissonance is unbearable; otherwise v2.
- **Test fixture recording strategy for ccxt** — recorded once against a real Kraken /
  Bitstamp test account during M8, then versioned in the repo.

---
