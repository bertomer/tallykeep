# ADR-0015 — Lock-aware worker lifecycle

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude during the polling-architecture cleanup
  brainstorm, May 2026

## Context

The 2026-05-18 Account-detail iteration migrated custodial polling
from a worker-side scheduler+subscriber pair into a self-scheduled
`CustodialPollHandler` thread running inside the backend FastAPI
process. The motivation was correct — the worker→event→backend
pattern that the previous iteration had left behind degraded into
two stacked poll loops with unclear ownership — but the chosen
fix moved the scheduler into the backend, contradicting
`01_architecture.md` §"Services": the backend "does not run
scheduled tasks itself."

The implementation also coupled worker liveness to backend unlock
state: when the backend is locked under a passphrase, the worker
stops doing useful work, including chain observation that does
not depend on any decrypted secret. This is incorrect.
Descriptors are plaintext on disk per `03_data_model.md`; only
custodial credentials are encrypted under the passphrase per
`01_architecture.md` §"Configuration model". The chain side has
no reason to pause when the backend is locked, and pausing it
would force a chain catch-up flow that should not exist.

Two questions surfaced in the brainstorm:

1. **Should the backend run schedulers under any circumstance?**
   No. `01_architecture.md` is explicit and the rationale — the
   HTTP request thread pool should not absorb long-lived polling
   work, single source of truth for periodic tasks belongs in
   the worker — has not changed. A "scheduler thread inside the
   backend" is the same anti-pattern in a different costume.

2. **What is the worker's lifecycle relative to backend lock
   state?** Independent. The worker is always up. Per-subscriber
   readiness gates on whether that subscriber needs a decrypted
   secret to do its job.

## Decision

### Worker lifecycle: always-on, independent of lock state

The worker process starts at stack boot and runs continuously,
regardless of whether the backend has been unlocked. Subscribers
fall in two classes:

**Always-on subscribers** (no decrypted secret required):

- `ChainListener` — bitcoind ZMQ → `chain.*` events. Descriptors
  are plaintext; no secret needed.
- `CategorizerSuggester` — reads existing data; writes
  `suggested_category`. No secret.
- `LiveUpdateBridge` — forwards bus events to SSE.
- `AuditReconciler` — persistence-first reconciliation on
  existing audit-table rows.

**Secret-gated subscribers** (require decrypted custodial
credentials or, later, encrypted Lightning macaroons):

- `CustodialPoller` — calls custodial-provider APIs using
  decrypted credentials.
- `SweepEngine` outflow path — fires the provider's withdraw API
  using the withdrawal credential.
- Future Lightning components consuming encrypted macaroons.

### Two new domain events under the `system.*` namespace

- `system.locked` — emitted at backend startup before any unlock,
  and (future) when an explicit re-lock is invoked. Secret-gated
  subscribers transition to a paused state and ignore further
  ticks until unlocked.
- `system.unlocked` — emitted when the backend successfully
  validates the passphrase via `POST /api/v1/unlock` and loads
  decrypted secrets. Secret-gated subscribers transition to
  active state and run one immediate **catch-up cycle** before
  resuming the heartbeat-driven schedule.

The catch-up cycle is the same logic as a regular cycle
(paginated against the persisted cursor from `last_polled_at`),
not a special code path. It just runs without waiting for the
next scheduler tick.

### Schedulers stay in the worker, gating happens at the subscriber

Schedulers (heartbeat emitters) remain in the worker. They emit
ticks unconditionally; they do not consult lock state. Gating
happens at the subscriber.

This keeps schedulers simple. A paused subscriber does not
meaningfully lose ticks — when it resumes, the immediate
catch-up cycle subsumes whatever ticks it missed.

### Backend's role in the polling path

- Emit `system.locked` / `system.unlocked` on the bus when the
  lock state changes (startup, post-unlock).
- Forward `treasury.custodial.*` and `chain.*` events to
  connected SSE clients via `LiveUpdateBridge`.
- Dispatch RQ jobs for one-shot work (immediate poll after
  Account creation, manual "Refresh now" requests) — the work
  runs in the worker, the backend returns 202 with a `job_id`.
- **No timers. No poll loops. No scheduler threads.**

## Consequences

**What this gives us.**

- Single source of truth for periodic work: the worker. Spec and
  reality agree.
- Chain observation is uninterrupted by lock state. No chain-side
  catch-up flow is needed; the on-chain ledger stays current.
- Custodial catch-up after unlock is bounded by Kraken's ledger
  pagination plus stored-cursor recency. Practical numbers per
  Account: hundreds of milliseconds in the common case, single-
  digit seconds after a multi-day lock, tens of seconds after a
  long lock with heavy venue activity. Runs in parallel across
  Accounts.
- The "Updated N minutes ago" + `connection_state` indicators
  already in spec (per `holdings/01_account.md`) carry the
  catch-up UX honestly: `connection_state = degraded` during the
  catch-up window, freshness timestamp lags until the cycle
  completes. No new UI element needed.
- The backend FastAPI process stops carrying long-lived
  background threads. Restarts cleaner; resource accounting more
  obvious; the HTTP thread pool is dedicated to request handling.

**What this costs us.**

- The 2026-05-18 `CustodialPollHandler` retires. A
  `CustodialPoller` (worker-side, subscriber) and
  `CustodialPollScheduler` (worker-side, heartbeat) come back —
  familiar shape from the pre-2026-05-18 design, this time
  without the broken intermediate event-then-backend-poll loop.
- The unlock endpoint changes from calling
  `poll_all_immediately()` in-process to emitting
  `system.unlocked` on the bus and returning. The catch-up runs
  in the worker as a subscriber reaction.
- Add Account's post-creation immediate poll changes from a
  direct call to enqueuing an RQ job. Frontend behavior unchanged
  from the user's POV — the detail page still has entries by the
  time the user navigates to it — but the work runs in the
  worker.

**What this does not change.**

- ADR-0008 (passphrase + recovery): the passphrase is still
  server-side, still typed at startup, still forwarded for
  fallback unlock. Credential storage is unchanged.
- ADR-0011 (Account 2-key model) and ADR-0013 (mirror posture):
  unchanged. Catch-up cycles upsert against the same
  `(provider_id, provider_entry_id)` key as regular cycles.
- ADR-0007 (NativeBridge): unchanged. Browser-build behavior
  under lock is identical to today.
- The locked-state endpoint contract — `423 Locked` on all
  endpoints except `/api/v1/unlock` and `/api/v1/health` per
  `04_api_conventions.md` — unchanged.

**Open follow-ups out of this ADR's scope.**

- Explicit re-lock UX (Settings → "Lock now") is a future
  iteration. `system.locked` is defined here so the contract is
  stable, but no UI surface emits it in current scope; the event
  fires only on startup before the first unlock.
- Multi-process worker scaling is out of scope. The current
  single-worker process consumes both schedulers and subscribers
  in one event loop.
- The broader unlock-flow cleanup (see
  `backlog/unlock-flow-cleanup.md`) covers UI bugs, CLI setup,
  passphrase rotation. This ADR coordinates with that work but
  does not block it — both touch the unlock endpoint, but the
  contracts are layered cleanly (this ADR adds two bus events;
  the cleanup will sharpen the surrounding state machine).

## Affected files

- `specs/01_architecture.md` — §"Worker components" expanded
  with a lock-aware lifecycle subsection; explicit re-statement
  that the backend runs no schedulers.
- `specs/holdings/01_account.md` — §"Observation cycles"
  documents the catch-up cycle on unlock and the
  `connection_state = degraded` UI affordance during it.
- `specs/decisions/README.md` — ADR-0015 indexed.
- `specs/next_iteration.md` — coding iteration sharpened
  against this ADR.
