# Next iteration

The sharpened, fully-detailed scope of work the coding agent is
working on (or about to start). Updated in lockstep with the
canonical specs whenever the spec evolves.

When this iteration completes:
- Items shipped → condensed entry appended to `shipped.md`,
  removed from this file.
- Canonical specs already reflect the target (no extra "merge"
  work).
- One file from `backlog/` is promoted, sharpened, and becomes
  the new active iteration here; on promotion, the backlog file
  is deleted (per ADR-0014).

If you're a coding agent reading this: this file is your scope.
Other docs in `specs/` are reference; this file is the
assignment. The historical record of iterations that already
shipped lives in `shipped.md`.

---

## Iteration template

Use this shape when sharpening an iteration. Sections marked
(required) must be filled before the iteration is given to a
coding agent.

### Iteration: <short name>

**Started:** YYYY-MM
**Goal:** <single sentence — what we want to be true at the end>

#### Scope (in) — required

<bullet list of features / changes — sharp, small, fully
detailed. Each item references the canonical doc(s) and mockup
file(s) that define it. The coding agent should not need to
invent anything from this list.>

#### Scope (out) — required

<things considered for this iteration and explicitly cut.
Prevents scope creep.>

#### Affected canonical docs

<list of canonical spec files this iteration touches. Already
updated to reflect target before iteration starts.>

#### Mockup contract — required if iteration touches UI

<List of mockup files defining the visual ground truth for
this iteration. By the time an iteration is given to the
coding agent, every listed mockup is `Status: validated` —
flipped at the spec/design agent's design-pass greenlight
(see PROCESS.md §2 Design / brand agent — *Output*), not at
coding closeout.

**Coding-agent rule (PROCESS.md §2 Coding agent — Visual
contract):** read every file in this list before writing the
corresponding screen. Copy, spacing, states, affordances,
error variants — the mockup HTML is the contract. Deviation
is either a code bug (fix it) or a spec drift event (stop,
surface to Rémy, edit mockup + ADR if structural). No third
path.>

#### Tasks — required

<concrete, ordered tasks for the coding agent. Each task should
map to a definition-of-done.>

#### Acceptance / done-when — required

<observable conditions: this curl returns this; this screen
matches this mockup at this viewport; this gauntlet step passes.>

#### Dependencies

<what blocks this iteration: pre-implementation items needing
arbitration, prior iterations not yet shipped, third-party
things.>

#### Verification (Rémy)

<what Rémy will run / check after the agent's stage-3 handoff,
before greenlighting closeout. Default for backend iterations:
the project's `.ps1` smoke-test suite + a Swagger UI walk-through
of any touched endpoint. Default for UI iterations: open the
named mockups + hand-test the new flow at 360×800. Add anything
iteration-specific.>

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight the
agent: regenerates `api/openapi.yaml` (if API surface changed),
appends a condensed entry to `shipped.md`, clears the active
block in this file, runs `tools/check-spec.ps1`, commits. Full
sequence in `PROCESS.md §4.4` stages 3–5.

---

## Active iteration

### Iteration: Lock-aware worker + retire backend-side polling

**Started:** 2026-05
**Goal:** Custodial polling lives entirely in the worker, gated
on backend unlock state. The backend runs no timers, no
scheduler threads, no in-process poll loops. Chain observation
runs continuously regardless of lock state.

#### Scope (in) — required

- **Retire `CustodialPollHandler` from the backend process.**
  Remove the 15-second scheduler thread (`_run_scheduler`,
  `_tick`), the `poll_all_immediately()` /
  `poll_provider_immediately()` callsites in route handlers, and
  the threading lifecycle wiring (start at app startup, stop at
  shutdown). Per `01_architecture.md` §"Services" and ADR-0015.
- **Reintroduce `CustodialPollScheduler` in the worker.**
  Heartbeat-only component that emits
  `treasury.custodial.poll_tick` events on a per-provider timer.
  Reads `runtime_configuration.custodial_polling.interval_seconds`
  (default 600, range 60–3600). Emits ticks unconditionally —
  no lock-state check, no provider-active check beyond
  `is_active = TRUE`. Per `01_architecture.md` §"Worker
  components" → "Lock-aware lifecycle".
- **Reintroduce `CustodialPoller` in the worker.** Subscriber
  with three subscriptions:
  1. `treasury.custodial.poll_tick(provider_id)` — IF internal
     state is `active`, run one cycle for the named provider via
     the existing `CustodialProviderAdapter` machinery (same
     fetch + persist + emit path as before; no functional
     change to a single cycle).
  2. `system.unlocked` — transition state `paused → active`,
     then run one **immediate catch-up cycle per active
     Account, in parallel** (`asyncio.gather` over the active
     set). Same cycle code path; paginates against
     `last_polled_at`.
  3. `system.locked` — transition state `active → paused`.
     Subsequent ticks are dropped silently until next
     `system.unlocked`.
  Initial state at worker boot: `paused`.
- **Emit `system.locked` and `system.unlocked` from the
  backend.**
  - Backend startup: emit `system.locked` on the bus once,
    before serving any request. Idempotent with respect to
    worker boot order (worker may receive it before or after
    its own boot; either way, paused stays paused).
  - `POST /api/v1/unlock` on successful passphrase validation:
    emit `system.unlocked` on the bus, then return 200. The
    endpoint does **not** call any poller in-process. The
    `poll_all_immediately()` callsite is deleted entirely; the
    catch-up runs in the worker as the subscriber reaction.
- **Migrate post-Account-creation immediate poll to an RQ job.**
  `POST /api/v1/holdings/account` no longer calls
  `poll_provider_immediately(new_provider_id)` in-process.
  Instead it enqueues an RQ job
  `enqueue_one_shot_custodial_poll(new_provider_id)`; the
  response gains a `kickoff_job_id` field. The job body runs in
  the worker, executes one cycle for the named provider, emits
  the standard `treasury.custodial.*` events.
- **Manual "Refresh now" migrates to the same RQ-job pattern.**
  The existing manual-refresh endpoint (current path in
  `api/openapi.yaml`; the UI's Account-detail refresh affordance
  hits it today) currently invokes the backend-side
  `CustodialPollHandler`. After retirement, it dispatches
  `enqueue_one_shot_custodial_poll(provider_id)` and returns
  `202 Accepted` with `{ "job_id": "..." }`. The frontend's
  spin-and-settle indicator switches from "wait for synchronous
  response" to "subscribe to job status via SSE / poll
  `GET /jobs/{id}`", but the user-visible behavior is unchanged
  (tap refresh → indicator spins → events fan out over SSE →
  indicator settles).
- **Worker boot must succeed with the backend locked.**
  - `ChainListener` boots and listens to bitcoind ZMQ
    immediately.
  - `CustodialPoller` boots into `paused` state, registers its
    subscriptions, waits.
  - No exception, no exit code, no "credentials not available"
    log spam from secret-gated components — they don't try to
    decrypt until they receive `system.unlocked`.
- **Retire the `treasury.custodial.poll_requested` event** if
  any reference survived the 2026-05-18 cleanup. The new tick
  topic is `treasury.custodial.poll_tick`; the migration
  doesn't reintroduce the old name.

#### Scope (out) — required

- **Explicit re-lock UX** (Settings → "Lock now"). The
  `system.locked` event is defined here for contract stability,
  but the only emitter in current scope is backend startup. A
  future iteration may add an explicit re-lock surface.
- **Worker multi-process scaling.** Single worker process
  consumes schedulers + subscribers in one event loop.
- **Changes to the locked-state HTTP contract.** `423 Locked` on
  all endpoints except `/api/v1/unlock` and `/api/v1/health`
  stays as-is per `04_api_conventions.md`.
- **Touching the unlock UX or the broader unlock state machine
  bugs.** Those are covered by `backlog/unlock-flow-cleanup.md`,
  a separate effort. Coordinate at promotion time; do not merge.
- **`ChainListener` internals.** It already runs lock-
  independent. This iteration only verifies the property in a
  test; it does not refactor the listener.
- **Re-enabling worker→event→backend round-tripping.** The
  retired pattern stays retired. New flow is
  worker-scheduler-tick → worker-subscriber → events on bus.

#### Affected canonical docs

Already updated to reflect the target before this iteration
starts:

- `01_architecture.md` — §"Services" backend bullet
  strengthened; §"Worker components" gains a "Lock-aware
  lifecycle" subsection.
- `holdings/01_account.md` — §"Observation cycles" documents
  the catch-up cycle on `system.unlocked` and the
  `connection_state = degraded` UI affordance during it.
- `decisions/0015-lock-aware-worker-lifecycle.md` — new ADR.
- `decisions/README.md` — index entry.

#### Mockup contract — required if iteration touches UI

None. This iteration is backend-only. UI surfaces involved
(`connection_state` dot, "Updated N minutes ago" indicator on
Account detail) already exist in validated mockups and need no
visual change — `connection_state = degraded` already renders
honestly during the catch-up window. The visual contract is
unchanged; coding agent does not need to open mockup files for
this iteration.

#### Tasks — required

1. **Delete `CustodialPollHandler`** and its scheduler thread
   from `backend/`. Remove startup/shutdown wiring. Remove all
   callsites of `poll_all_immediately()` and
   `poll_provider_immediately()`.
2. **Backend startup — emit `system.locked`** on the bus once,
   before any HTTP listener is bound. Idempotent.
3. **`POST /api/v1/unlock`** — on successful passphrase
   validation, emit `system.unlocked` on the bus, then return
   200. No in-process polling call.
4. **`POST /api/v1/holdings/account`** — replace direct poll
   call with `enqueue_one_shot_custodial_poll(provider_id)`.
   Response gains `kickoff_job_id: UUID`. Update OpenAPI
   schema for the response (`AccountCreationResponse` or
   equivalent).
4b. **Manual refresh endpoint** — locate the existing manual-
    refresh route in `api/openapi.yaml` (Account-detail refresh
    affordance hits it today; it currently calls into the
    retired backend handler). Migrate to the RQ-job pattern:
    dispatch `enqueue_one_shot_custodial_poll(provider_id)`,
    return `202 Accepted` with `{ "job_id": "..." }`. Frontend
    refresh-affordance behavior shifts from sync response to
    job-status subscription over SSE; user-visible spin/settle
    behavior must remain identical.
5. **Worker — `CustodialPollScheduler` component.** Per-provider
   timer reading `interval_seconds`. Emits
   `treasury.custodial.poll_tick(provider_id)` on the bus. No
   lock-state awareness.
6. **Worker — `CustodialPoller` component.** Subscribes to the
   three events listed in Scope. Internal state machine
   `paused ↔ active`. Cycle logic reused as-is from the
   retired `CustodialPollHandler` (same fetch / persist / emit
   path).
7. **Worker — `enqueue_one_shot_custodial_poll(provider_id)`
   RQ job handler.** Body runs one cycle for the named
   provider; emits the standard
   `treasury.custodial.cycle_completed` /
   `ledger_entry_added` / `ledger_entry_updated` /
   `connection_state_changed` events. Sets job status `success`
   / `failed` per the async-job pattern in
   `04_api_conventions.md`.
8. **Verify always-on components boot with backend locked.** Add
   a small integration test that boots the worker with
   `SECRETS_BACKEND=encrypted_database` and no unlock having
   occurred, asserts `ChainListener.is_running == True`,
   `CategorizerSuggester.is_running == True`,
   `LiveUpdateBridge.is_running == True`,
   `AuditReconciler.is_running == True`,
   `CustodialPoller.state == "paused"`. No exception during
   boot.
9. **Catch-up cycle integration test.** Boot worker, boot
   backend locked, emit `system.unlocked` (simulating
   successful unlock), assert one
   `treasury.custodial.cycle_completed` event per active
   Account within N seconds (N depending on test fixture
   provider response time).
10. **Regenerate `api/openapi.yaml`** (closeout stage) — the
    `AccountCreationResponse` schema gained `kickoff_job_id`;
    new SSE topic `treasury.custodial.poll_tick` if it surfaces
    publicly (it shouldn't — internal bus topic only — but
    verify); ensure no other drift.

#### Acceptance / done-when — required

- `grep -rEi '_run_scheduler|_tick|poll_all_immediately|poll_provider_immediately'`
  against `backend/` returns no matches. Equivalents may exist
  in `worker/`; that is the expected migration.
- `grep -rEi 'CustodialPollHandler'` against `backend/`
  returns no matches.
- Manual hand test 1 — **locked boot:** start backend without
  unlocking; start worker. Backend logs include "emitted
  system.locked". Worker logs include "ChainListener: running",
  "CustodialPoller: paused". Touch bitcoind regtest to generate
  a block; observe `chain.*` events on the bus. No
  `treasury.custodial.*` events fire.
- Manual hand test 2 — **unlock catch-up:** `POST /api/v1/unlock`
  with the correct passphrase. Backend logs "emitted
  system.unlocked". Within seconds, one
  `treasury.custodial.cycle_completed` event per active Account
  fires on the bus. `last_polled_at` updates in the DB.
  Account detail page (already open via SSE) reflects updated
  balance and any new ledger entries.
- Manual hand test 3 — **new Account creation:** Run the Add
  Account wizard with valid Kraken credentials. Response
  carries `kickoff_job_id`. Within seconds, the kickoff job
  completes; ledger entries appear in `custodial_ledger_entry`;
  navigating to the detail page renders entries on first paint.
- Manual hand test 4 — **manual refresh:** with backend
  unlocked, tap the Account-detail refresh affordance. Response
  is `202 Accepted` with `job_id`. Within seconds, one
  `treasury.custodial.cycle_completed` event fires for the
  named provider; the UI's freshness stamp updates; the spin
  indicator settles.
- Known edge case, **out of scope for this iteration:** if the
  worker process restarts mid-session while the backend stays
  unlocked, the new worker boots in `paused` because no fresh
  `system.unlocked` is re-emitted. Documented in
  `backlog/worker-restart-locked-state-handshake.md` as the
  future fix (worker requests current lock state from backend
  on boot). Recovery today: restart the backend, which fires
  `system.locked` and awaits a fresh unlock.
- `tools/check-spec.sh` passes (no ADR-index drift, no broken
  refs, no tail-malformed files, no mtime gaps).
- Smoke-test `.ps1` suite passes against the running backend.
- Swagger UI walk-through of `POST /api/v1/unlock`,
  `POST /api/v1/holdings/account`, `GET /api/v1/jobs/{id}` —
  response shapes match the regenerated OpenAPI.

#### Dependencies

- ADR-0015 lands as part of this iteration's spec-agent
  sharpening (already authored). No external blockers.
- `backlog/unlock-flow-cleanup.md` shares surface (it touches
  the unlock state machine more broadly). That work is later
  and broader; this iteration is a focused architectural
  cleanup. Both touch `POST /api/v1/unlock` but the contracts
  are layered: this iteration adds two bus events; the cleanup
  will sharpen the surrounding state machine. They don't block
  each other.

#### Verification (Rémy)

- Hand tests 1–4 above.
- Spot-check: `ls backend/ | grep -i poll` should not surface a
  scheduler / handler class; `ls worker/ | grep -i poll` should
  surface the new scheduler + subscriber.
- `tools/check-spec.ps1` (Windows) passes.
- `.ps1` smoke-test suite passes.
- Swagger UI: open the regenerated `api/openapi.yaml` in
  Swagger UI; walk `/unlock`, `/holdings/account`, `/jobs/{id}`.

#### Closeout

Standard PROCESS.md §4.4 stage 5 sequence. On Rémy's explicit
greenlight after stage-4 validation:

- Regenerate `api/openapi.yaml` from the running backend
  (`AccountCreationResponse` schema gained `kickoff_job_id`).
- Append a condensed entry to `shipped.md` describing the
  migration: `CustodialPollHandler` retired from backend;
  `CustodialPollScheduler` + `CustodialPoller` re-introduced in
  worker; `system.locked` / `system.unlocked` events
  introduced; post-Account-creation immediate poll migrated to
  RQ job; worker boots cleanly with backend locked.
- Clear this active iteration block back to "No active coding
  iteration."
- Run `tools/check-spec.ps1` / `.sh` one final time. Must pass.
- Commit the closeout in a single change. Commit message
  references the iteration name and the validation date.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only; everything
else is reference.
