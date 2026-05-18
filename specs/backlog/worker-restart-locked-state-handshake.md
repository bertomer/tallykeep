# Worker restart — locked-state handshake

- **Captured:** 2026-05 (surfaced during ADR-0015 sharpening).
- **Motivation:** The lock-aware worker lifecycle (ADR-0015) gates
  the `CustodialPoller` on `system.unlocked` / `system.locked`
  events emitted by the backend. The backend emits `system.locked`
  once at startup and `system.unlocked` on each successful
  passphrase validation. If the **worker** restarts mid-session
  while the backend stays unlocked, the new worker boots into
  `paused` because no fresh `system.unlocked` arrives — and won't
  receive one until the next backend restart + unlock cycle. The
  on-chain side is unaffected (`ChainListener` doesn't need a
  secret), but custodial polling silently stalls until the next
  manual unlock.

  Today's recovery is to restart the backend (which re-emits
  `system.locked` and then awaits a fresh unlock). Acceptable for
  v1 of the lock-aware iteration but not for personal-use phase.
- **Sketch:** On worker boot, the worker emits a `system.lock_state_query`
  event (or calls a small internal RPC — `GET /api/v1/internal/lock-state`)
  to ask the backend for the current state. The backend replies
  with `locked` or `unlocked`. If `unlocked`, the worker fires the
  same code path as receiving `system.unlocked` — transition to
  `active`, run the immediate catch-up cycle. If `locked`, stay
  paused. Symmetric to existing event flow; just a one-shot pull
  at boot to bridge the gap.

  Open sub-question: query event vs HTTP endpoint. Query-event is
  bus-symmetric but needs a request-reply pattern over Redis
  pub/sub which Redis doesn't natively have. HTTP endpoint is
  simpler but requires the worker to know the backend's
  loopback address (it already does — they share the docker-
  compose network). Probably HTTP wins on simplicity. Sharpen
  during the iteration.
- **Touches:** `01_architecture.md` §"Worker components"
  Lock-aware lifecycle subsection (one paragraph on boot
  handshake); backend exposes a new (likely internal) lock-state
  endpoint or `system.*` query topic; worker boot adds the query
  + branch.
- **Status:** sketched
- **Milestone:** personal-use phase — operationally important
  once the user does any non-trivial worker maintenance. Not
  blocking the lock-aware iteration that introduced the gap.
- **Notes:** Likely a small iteration (one endpoint, one worker-
  boot branch, one test). Pairs naturally with
  `backlog/unlock-flow-cleanup.md` if that one promotes first —
  both touch the unlock state machine — but it can also stand
  alone.
