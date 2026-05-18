# ADR-0016 — Custodial-provider ACL lives only in the backend

- **Date:** 2026-05
- **Status:** Accepted
- **Refines:** ADR-0015 (lock-aware worker lifecycle)
- **Decided by:** Rémy
- **Authored by:** Claude during the polling-architecture cleanup
  brainstorm, May 2026 — after the first coding-agent pass on
  ADR-0015 surfaced two latent issues: a passphrase on the bus
  and an unnoticed ccxt duplication in the worker.

## Context

ADR-0015 split custodial polling into a worker-side scheduler
and subscriber, with the implicit assumption that the
`CustodialPoller` subscriber would call Kraken directly via the
`CustodialProviderAdapter` (ccxt) machinery running in the worker
process. That implicit assumption is wrong, for two independent
reasons that surfaced when the first coding pass tried to make
it work.

**Issue 1 — Secret transport.** For the worker to call Kraken,
it needs decrypted API credentials. The credentials live
encrypted at rest in the backend's `secrets` table, decrypted
in-memory at unlock time per ADR-0008 / `01_architecture.md`
§"Configuration model". The first pass tried to bridge this by
including the passphrase in the `system.unlocked` event payload,
so the worker could maintain its own copy of the unwrapped
secret store. That violates ADR-0008 (passphrase server-side
only, never stored, never broadcast). Even alternatives — a
backend "give me decrypted creds for provider X" endpoint —
just move the secret one layer over instead of keeping it
contained.

**Issue 2 — ACL duplication.** Putting ccxt in the worker means
the entire `CustodialProviderAdapter` class hierarchy
(KrakenAdapter, future BitstampAdapter, the per-provider
permission matrices, the ledger-normalization machinery, the
connection-state machine) needs to be reachable from worker
code. That's a dependency duplication (ccxt's transitive
dependency tree weighs ~30 packages) and an ACL duplication
(every change to the adapter contract touches two import sites
instead of one). Rémy had ruled in an earlier brainstorm that
the worker should not embed a second instance of this
machinery — that ruling lived only in chat and didn't
propagate into the spec, which is why the ADR-0015 sharpening
walked past it.

These two issues have **one root cause**: putting the upstream
HTTP call in the wrong process. Move the call to the backend
and both dissolve simultaneously.

## Decision

### Locality rule

The custodial-provider ACL — ccxt, `CustodialProviderAdapter`
and its concrete subclasses, the per-provider permission
matrices, the ledger normalization tables, the
connection-state machine — lives **only in the backend**. The
worker does not import ccxt, does not import the adapter
classes, does not hold credentials in any form, and does not
make outbound HTTP calls to custodial provider APIs.

This is the locality rule for **secret-bearing, credential-
backed** external adapters. It is distinct from the
ChainListener case (`bitcoind` RPC + ZMQ), which is lock-
independent and credential-free, runs in the worker by design,
and is not affected by this ADR. The rule scopes to "adapters
that need decrypted secrets," not "all adapters."

### Cycle execution

One custodial poll cycle is a backend-side operation:

1. Worker (orchestrator) calls
   `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`
   on the backend (loopback, 127.0.0.1).
2. Backend's internal handler:
   - Decrypts the credential for `provider_id` from its
     in-memory secret store (fails with `423 Locked` if the
     backend is locked).
   - Calls Kraken via the existing `KrakenAdapter` /
     `CustodialProviderAdapter` machinery.
   - Persists fetched ledger entries to `custodial_ledger_entry`
     via `cle_repo`. Upserts on `(custodial_provider_id,
     provider_entry_id)` per ADR-0013.
   - Updates `last_known_balance_sats`, `last_polled_at`,
     `connection_status`, `consecutive_error_count` on the
     provider row.
   - Emits the standard `treasury.custodial.*` events on the
     bus (`cycle_completed`, `ledger_entry_added`,
     `ledger_entry_updated`, `connection_state_changed`).
   - Returns 200 with a short summary (rows added / updated /
     unchanged, new `last_polled_at`, current
     `connection_status`).
3. Worker logs the result at debug level and returns to its
   subscribe loop. Worker holds **no** state about the cycle
   beyond "the call happened."

### Worker's role narrows to orchestration

After this ADR, the worker's `CustodialPoller` is a pure
orchestrator:

- Subscribes to `treasury.custodial.poll_tick(provider_id)`
  (emitted by `CustodialPollScheduler` in the worker).
- Subscribes to `system.unlocked` — on receipt, fires N parallel
  `POST .../poll-cycle` calls via `asyncio.gather` (one per
  active provider).
- Subscribes to `system.locked` — short-circuits any pending
  dispatch and stops dispatching new cycles.
- Subscribes to one-shot RQ jobs (`enqueue_one_shot_custodial_poll`)
  whose body is "POST .../poll-cycle for the named provider."

Worker has no ccxt, no `CustodialProviderAdapter` import, no
secret-store reference, no in-memory credential. It is a small,
testable HTTP client + state machine + event subscriber.

### Locked-state gating happens at the endpoint

The worker does not need to maintain its own paused/active
state. If a tick arrives or `system.unlocked` is consumed while
the backend is actually locked (because of a race or because
`system.unlocked` was followed by a re-lock), the
`POST .../poll-cycle` call returns `423 Locked`; the worker
silently drops the cycle and logs at debug.

The `system.locked` / `system.unlocked` events remain useful as
**hints** that drive the catch-up burst and avoid wasteful
dispatch — but they are not the authoritative source of truth
about lock state. The endpoint is.

### Internal endpoint scope and security posture

`POST /api/v1/internal/custodial/{provider_id}/poll-cycle` and
its sibling routes are **internal-only**:

- Path prefix `/internal/` reserved for this purpose.
- Bound to `127.0.0.1` like the rest of the API per
  `01_architecture.md` §"Network security posture".
- Future: a CORS denylist and / or a process-local shared
  token (file-system permission gated) hardens this once the
  hosted tier ships. Not load-bearing in dev phase since the
  whole API has no auth yet (per ADR-0003 phase gating).
- Excluded from `api/openapi.yaml`'s public surface tooling if
  any later consumer expects only `/api/v1/<resource>/` paths;
  for now, internal routes are listed in OpenAPI like any other.

### `system.unlocked` payload is topic-only

The event carries no payload beyond `topic` and `timestamp`. No
passphrase, no credential, no decrypted blob, no flag. The
event is a signal, not a transport.

`system.locked` is identical: topic-only.

## Consequences

**What this gives us.**

- Passphrase stays where ADR-0008 says it does: in the backend
  process, in memory, never transmitted. Honored.
- One ccxt dependency footprint. One `CustodialProviderAdapter`
  class hierarchy. One ACL boundary. Half the import sites.
  When Bitstamp or Lemon or Buenbit lands, the adapter changes
  one file in one process.
- Worker becomes very small. Easier to test (mock the backend
  endpoint), easier to reason about, faster to start.
- Hosted-tier ready. When the backend moves off the user's host,
  the credential decryption still happens in the trusted
  process; nothing about the worker changes.
- The Add Account immediate-poll and Manual Refresh flows
  collapse into the same path: dispatch
  `POST /poll-cycle` (via RQ job or direct call from the worker
  on receiving a one-shot dispatch event). One code path, one
  test surface.

**What this costs us.**

- One extra HTTP hop per cycle (worker → backend → Kraken
  instead of worker → Kraken). Loopback latency is sub-
  millisecond; the cycle is already dominated by Kraken's
  response time (hundreds of ms). The extra hop is invisible.
- A small new endpoint to maintain
  (`POST /api/v1/internal/custodial/{provider_id}/poll-cycle`).
  Cost: one route handler + one request/response schema.
- The "internal" path prefix convention is new — needs a brief
  note in `04_api_conventions.md` so future agents know not to
  surface those routes to external clients.

**What this does not change.**

- ADR-0008 (passphrase model): explicitly honored — this ADR
  strengthens that posture.
- ADR-0009 (key custody model): unchanged. The backend still
  never holds spending keys; this ADR is about custodial API
  credentials, which the backend already custodies.
- ADR-0013 (mirror posture): unchanged. The cycle still upserts
  against `(custodial_provider_id, provider_entry_id)`.
- ADR-0015 (lock-aware worker lifecycle): refined, not
  superseded. The lifecycle (worker always up, secret-gated
  components, `system.locked` / `system.unlocked` events) all
  stand. What changes is **where** the cycle code runs (backend,
  not worker) and **how** the worker dispatches (HTTP call, not
  direct adapter call). ADR-0015's "secret-gated subscribers"
  bullet still applies — `CustodialPoller` is gated by virtue
  of the endpoint returning 423 when locked, not by an
  internal state machine in the worker.
- The locked-state HTTP contract (`423 Locked` on most
  endpoints when locked): unchanged. The new internal endpoint
  participates in this contract like every other.

**What this implies for the in-progress iteration.**

The first coding-agent pass against ADR-0015 produced an
implementation with three structural problems (passphrase on
the bus, RQ-job pattern not actually wired, threads instead of
`asyncio.gather`). All three dissolve under the corrected
architecture in this ADR. The current iteration in
`next_iteration.md` is rewritten against this ADR; the prior
implementation is discarded. The fresh coding agent starts
clean.

## Affected files

- `specs/01_architecture.md` — §"Internal layering" annotation
  showing adapters in the backend with worker components
  dispatching via internal HTTP; §"Worker components" /
  "Lock-aware lifecycle" updated to describe `CustodialPoller`
  as an orchestrator (no ccxt, no creds); §"Network security
  posture" adds a sentence on the `/internal/` path prefix.
- `specs/holdings/01_account.md` — §"Observation cycles"
  clarifies the cycle runs in the backend; the worker triggers
  it via internal HTTP.
- `specs/decisions/0015-lock-aware-worker-lifecycle.md` —
  Status: Accepted; refined by 0016. Forward-reference note on
  the worker/backend split.
- `specs/decisions/README.md` — ADR-0016 indexed; ADR-0015
  status updated.
- `specs/next_iteration.md` — iteration rewritten against this
  ADR.
- `specs/04_api_conventions.md` — brief sentence on the
  `/internal/` path-prefix convention (added in the iteration
  scope; lands with the coding pass that introduces the first
  internal route).
