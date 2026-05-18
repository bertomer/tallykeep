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

### Iteration: Lock-aware worker + backend-only custodial ACL

**Started:** 2026-05
**Goal:** Custodial polling is orchestrated by the worker and
executed by the backend. The worker holds no credentials and
imports no ccxt. The backend runs no timers and no scheduler
threads. `system.locked` / `system.unlocked` events are
topic-only (no secrets on the bus). The chain side runs
continuously regardless of lock state.

**Note to incoming coding agent.** A previous coding pass
against an earlier shape of this iteration produced a broken
implementation (passphrase on the Redis bus, ccxt duplicated
into the worker, RQ-job pattern shimmed inline, threads
instead of `asyncio.gather`). That work is **discarded** —
start from current `main`, do not pick up the previous branch.
ADR-0015 and ADR-0016 together define the corrected
architecture; this iteration block is the assignment.

#### Scope (in) — required

- **Retire `CustodialPollHandler` from the backend.** Remove
  the scheduler thread (`_run_scheduler`, `_tick`), the
  `poll_all_immediately()` / `poll_provider_immediately()`
  callsites from request handlers, the threading lifecycle
  wiring. Per `01_architecture.md` §"Services" and ADR-0015.

- **Add the internal cycle endpoint** (per ADR-0016):
  `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`.
  Loopback-only (per `01_architecture.md` §"Network security
  posture"). Behavior:
  1. Locked state → return `423 Locked` (same contract as
     every other secret-requiring endpoint per
     `04_api_conventions.md`).
  2. Provider not found / archived → `404`.
  3. Otherwise: decrypt the credential from the in-memory
     secret store, call the provider via the existing
     `CustodialProviderAdapter` machinery, persist entries to
     `custodial_ledger_entry` via `cle_repo` (upsert on
     `(custodial_provider_id, provider_entry_id)` per
     ADR-0013), update the provider row's
     `last_known_balance_sats`, `last_polled_at`,
     `connection_status`, `consecutive_error_count`, emit the
     `treasury.custodial.*` events on the bus (same set as
     today: `cycle_completed`, `ledger_entry_added`,
     `ledger_entry_updated`, `connection_state_changed`).
  4. Return `200` with a small summary: `rows_added`,
     `rows_updated`, `rows_unchanged`, `last_polled_at`,
     `connection_status`.

  Body of this handler reuses the per-cycle logic that
  previously lived inside the retired `CustodialPollHandler`
  / earlier `CustodialPoller` — same fetch / persist / emit;
  what changes is the trigger (HTTP call) and the location
  (in a route handler, not a thread loop).

- **Reintroduce `CustodialPollScheduler` in the worker.**
  Heartbeat-only component that emits
  `treasury.custodial.poll_tick(provider_id)` events on a
  per-provider timer. Reads
  `runtime_configuration.custodial_polling.interval_seconds`
  (default 600, range 60–3600). Emits ticks unconditionally —
  no lock-state check (the gate is at the backend endpoint).
  Iterates `is_active = TRUE` providers; archived providers
  don't get ticks.

- **Reintroduce `CustodialPoller` in the worker, as a pure
  orchestrator.** The component:
  - Has no ccxt dependency. Does not import
    `CustodialProviderAdapter` or any concrete adapter
    subclass.
  - Has no secret-store reference. Does not decrypt
    credentials.
  - Holds an HTTP client (backend loopback) — that's its only
    outbound dependency.
  - Subscribes to three events:
    1. `treasury.custodial.poll_tick(provider_id)` — fire one
       `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`.
       On `423 Locked`: drop the cycle, log at debug. On
       `404`: log at info. On other non-2xx: log at warn,
       continue. On `200`: log at debug.
    2. `system.unlocked` (topic-only payload) — query the
       list of active providers, fire N parallel
       `POST .../poll-cycle` calls via `asyncio.gather` (one
       per active provider). This is the **catch-up burst**.
       Same per-call handling as on tick.
    3. `system.locked` (topic-only payload) — short-circuit
       any pending dispatch (cancel pending tasks in flight),
       stop dispatching new cycles. The next `system.unlocked`
       re-enables.

- **Emit `system.locked` / `system.unlocked` from the
  backend, topic-only.**
  - Backend startup: emit `system.locked` on the bus once,
    before serving any request. Payload contract:
    `{ "topic": "system.locked", "timestamp": "..." }` —
    nothing else. **No passphrase, no flag, no secret.**
  - `POST /api/v1/unlock` on successful passphrase
    validation: emit `system.unlocked` on the bus
    (`{ "topic": "system.unlocked", "timestamp": "..." }`),
    then return 200. The endpoint does **not** call any
    poller in-process and does **not** include the
    passphrase or any derived material in the event payload.

- **Migrate post-Account-creation immediate poll to a worker-
  side one-shot dispatch.**
  - `POST /api/v1/holdings/account` no longer calls
    `poll_provider_immediately(new_provider_id)` in-process.
  - It enqueues an RQ job
    `one_shot_custodial_poll(provider_id: UUID)`. Job body
    has only the serializable `provider_id` arg; inside the
    job, the worker reconstructs its own HTTP client + bus +
    repo handles from configuration, then dispatches
    `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`
    against the backend. No unpicklable refs, no inline shim.
  - If the project's current scope does not yet need a real
    Redis Queue (RQ) executor and uses an in-memory queue for
    tests, that's fine — but the production path executes the
    job in the worker process, not in the FastAPI request
    thread. If only an in-memory shim exists today, this
    iteration adds the Redis-backed executor as the real
    production path. Document the choice in the closeout
    entry.
  - Response shape gains `kickoff_job_id: UUID`. Update the
    `AccountCreateOut` schema (or equivalent name in code).

- **Migrate manual refresh to the same one-shot dispatch
  pattern.** The existing manual-refresh endpoint (current
  path in `api/openapi.yaml`; the UI's Account-detail refresh
  affordance hits it today — current Section 16 in
  `scripts/smoke-test.ps1` confirms it) currently invokes the
  retired backend handler. Migrate to: enqueue
  `one_shot_custodial_poll(provider_id)`; return
  `202 Accepted` with `{ "job_id": "..." }`. Frontend's
  spin-and-settle affordance behavior is unchanged from the
  user's POV (the existing SSE subscription delivers
  `treasury.custodial.*` events when the cycle completes; the
  spin can settle on `cycle_completed` for the matching
  provider).

- **Worker boot must succeed with the backend locked.**
  - `ChainListener` boots and listens to bitcoind ZMQ
    immediately — same as today.
  - `CustodialPollScheduler` boots and starts emitting ticks
    immediately. (It doesn't need to know the lock state; the
    endpoint will return 423 to the orchestrator's dispatch
    calls until the backend is unlocked.)
  - `CustodialPoller` (orchestrator) boots and starts
    subscribing immediately. On any tick / `system.unlocked`
    that fires before the backend is unlocked, dispatch
    yields `423`, orchestrator drops the cycle silently. No
    exception, no exit code, no log spam.
  - No worker component decrypts a secret or imports ccxt.

- **Retire any remnant of the prior shape.** Specifically:
  - `treasury.custodial.poll_requested` event (if any
    reference survived the 2026-05-18 cleanup) — replaced by
    `treasury.custodial.poll_tick` plus the internal cycle
    endpoint.
  - Any `EncryptedDatabaseSecretStore` instance inside the
    worker process (if the prior broken pass introduced one)
    — the worker has no secret store.
  - Any passphrase-bearing field in any `system.*` event
    schema — strictly `{ topic, timestamp }`.

#### Scope (out) — required

- **Explicit re-lock UX** (Settings → "Lock now"). The
  `system.locked` event is defined for contract stability,
  but the only emitter in current scope is backend startup.
- **Worker multi-process scaling.** Single worker process
  consumes schedulers + orchestrator in one event loop.
- **Changes to the locked-state HTTP contract.** `423 Locked`
  on all endpoints except `/api/v1/unlock` and
  `/api/v1/health` stays as-is per `04_api_conventions.md`.
  The new internal cycle endpoint participates in this
  contract like every other.
- **Touching the unlock UX or the broader unlock state
  machine bugs.** Covered by `backlog/unlock-flow-cleanup.md`,
  separate effort. Coordinate at promotion time; do not
  merge.
- **Mid-session worker restart resync.** Covered by
  `backlog/worker-restart-locked-state-handshake.md`. Under
  ADR-0016 the orchestrator has no internal lock state to
  lose on restart — the next tick simply dispatches and gets
  a 423 or a cycle result depending on backend state. The
  backlog item should be re-evaluated at closeout; it may
  be unnecessary.
- **`ChainListener` internals.** Already runs lock-
  independent. This iteration only verifies the property.
- **Hardening of the `/internal/` route prefix** (process-
  local shared token, CORS denylist). Future hosted-tier
  iteration per `01_architecture.md` §"Network security
  posture".

#### Affected canonical docs

Already updated to reflect target before this iteration
starts:

- `01_architecture.md` — §"Internal layering" adapter-locality
  block; §"Worker components" → "Lock-aware lifecycle"
  describes `CustodialPoller` as an orchestrator;
  §"Network security posture" adds the `/internal/` prefix
  convention.
- `holdings/01_account.md` — §"Observation cycles" describes
  the cycle as backend-executed and worker-orchestrated; the
  catch-up burst on `system.unlocked` uses `asyncio.gather`
  against the internal endpoint.
- `decisions/0015-lock-aware-worker-lifecycle.md` —
  refinement note pointing to ADR-0016.
- `decisions/0016-custodial-acl-backend-only.md` — new ADR.
- `decisions/README.md` — both index entries.

#### Mockup contract — required if iteration touches UI

None. Backend-only. UI affordances (`connection_state` dot,
"Updated N minutes ago" freshness stamp, refresh button)
already exist in validated mockups and need no visual change.

#### Tasks — required

1. **Add `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`**
   route to the backend. Route handler runs the cycle logic
   (decrypt cred, ccxt call, persist, emit events) and returns
   the small summary described in Scope. Locked-state check
   returns 423. Provider-not-found returns 404.
2. **Delete `CustodialPollHandler`** from the backend along
   with its scheduler thread, startup/shutdown wiring, and
   all callsites of `poll_all_immediately()` /
   `poll_provider_immediately()`.
3. **Backend startup — emit `system.locked`** on the bus
   once, before any HTTP listener is bound. Payload
   `{ "topic": "system.locked", "timestamp": "..." }`.
4. **`POST /api/v1/unlock`** — on successful passphrase
   validation, emit `system.unlocked` (topic-only) on the
   bus, then return 200. No in-process polling call. No
   passphrase in the event payload.
5. **`POST /api/v1/holdings/account`** — replace direct poll
   call with `enqueue('one_shot_custodial_poll', provider_id)`.
   Response gains `kickoff_job_id: UUID` field. Update
   OpenAPI schema accordingly.
6. **Manual refresh endpoint** — locate the existing route
   (current path in `api/openapi.yaml`, currently invokes the
   retired handler). Migrate to enqueue
   `one_shot_custodial_poll(provider_id)`; return
   `202 Accepted` with `{ "job_id": "..." }`.
7. **RQ job `one_shot_custodial_poll(provider_id: UUID)`.**
   Job body takes only the UUID; constructs its HTTP client +
   bus + repos from configuration inside the job; dispatches
   `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`
   against the backend; sets job status `success` /  `failed`
   per the async-job pattern in `04_api_conventions.md`. If
   the project currently uses an in-memory queue stub, also
   wire the real Redis-backed RQ executor for production.
8. **Worker — `CustodialPollScheduler` component.** Per-
   provider timer reading `interval_seconds`. Emits
   `treasury.custodial.poll_tick(provider_id)` on the bus.
   Iterates `is_active = TRUE` providers. No lock-state
   check.
9. **Worker — `CustodialPoller` orchestrator component.**
   Subscribes to `treasury.custodial.poll_tick`,
   `system.unlocked`, `system.locked`. On tick: one dispatch.
   On `system.unlocked`: `asyncio.gather` of N dispatches.
   On `system.locked`: cancel pending dispatches, stop
   dispatching. **No ccxt, no adapter import, no secret-store
   reference, no credential field.**
10. **Verify always-on components boot with backend locked.**
    Add an integration test that boots the worker with
    `SECRETS_BACKEND=encrypted_database` and no unlock
    having occurred, asserts `ChainListener.is_running ==
    True`, `CategorizerSuggester.is_running == True`,
    `LiveUpdateBridge.is_running == True`,
    `AuditReconciler.is_running == True`,
    `CustodialPoller.is_running == True`. No exception
    during boot. The orchestrator is "running" even with
    the backend locked — its dispatches just get 423 until
    unlock.
11. **Catch-up integration test.** Boot worker, boot backend
    locked, emit `system.unlocked` on the bus (simulating
    successful unlock). Assert one
    `treasury.custodial.cycle_completed` event per active
    Account within N seconds. Assert the
    orchestrator's HTTP client made N parallel POSTs.
12. **Regression test for the no-secrets-on-bus rule.**
    Subscribe a probe to the `system.*` topic family during
    the test suite; assert that no event payload ever
    contains keys named `passphrase`, `password`, `secret`,
    `private_key`, or values that match the test passphrase
    string. Lightweight runtime check that ADR-0016's main
    rule isn't quietly violated by a future change.
13. **Regenerate `api/openapi.yaml`** (closeout stage) — the
    new internal route, the modified `AccountCreateOut`
    (with `kickoff_job_id`), the modified manual-refresh
    response (now 202 + job_id). Verify no other drift.

#### Acceptance / done-when — required

- `grep -rEi '_run_scheduler|_tick|poll_all_immediately|poll_provider_immediately|CustodialPollHandler'`
  against `backend/` returns no matches. (Cycle logic now
  lives in the new internal route handler.)
- `grep -rEi 'import ccxt|CustodialProviderAdapter|KrakenAdapter|EncryptedDatabaseSecretStore'`
  against `worker/` returns no matches.
- `grep -rEi 'passphrase|secret|private_key' tests/` shows no
  occurrence inside a `system.unlocked` or `system.locked`
  event payload assertion (positive test that we never expect
  these fields there).
- Manual hand test 1 — **locked boot:** start backend without
  unlocking; start worker. Backend logs include "emitted
  system.locked (topic-only)". Worker logs include
  "ChainListener: running", "CustodialPoller: running
  (orchestrator)", "CustodialPollScheduler: running". Touch
  bitcoind regtest to generate a block; observe `chain.*`
  events on the bus. The scheduler emits ticks; the
  orchestrator dispatches; each dispatch yields `423 Locked`
  and is silently dropped. No `treasury.custodial.*` events
  fire.
- Manual hand test 2 — **unlock catch-up:**
  `POST /api/v1/unlock` with the correct passphrase. Backend
  logs "emitted system.unlocked (topic-only)". Verify the
  emitted event payload via `redis-cli SUBSCRIBE system.*`
  and confirm it contains only `topic` and `timestamp`
  fields. Within seconds, one
  `treasury.custodial.cycle_completed` event per active
  Account fires on the bus. `last_polled_at` updates in the
  DB. Account detail page (already open via SSE) reflects
  updated balance and new entries.
- Manual hand test 3 — **new Account creation:** Run the Add
  Account wizard with valid Kraken credentials. Response
  carries `kickoff_job_id`. Within seconds, the kickoff job
  completes; ledger entries appear in
  `custodial_ledger_entry`; navigating to the detail page
  renders entries on first paint.
- Manual hand test 4 — **manual refresh:** with backend
  unlocked, tap the Account-detail refresh affordance.
  Response is `202 Accepted` with `job_id`. Within seconds,
  one `treasury.custodial.cycle_completed` event fires for
  the named provider; the UI's freshness stamp updates; the
  spin indicator settles.
- Manual hand test 5 — **passphrase audit:**
  `redis-cli MONITOR` running during an unlock. Verify the
  passphrase string never appears in MONITOR output (sample
  passphrase like `test-passphrase-12345` to make grep
  unambiguous).
- `tools/check-spec.sh` / `.ps1` passes (no ADR-index drift,
  no broken refs, no mtime gaps on the touched files).
- Smoke-test `.ps1` suite passes against the running
  backend. The smoke test for the manual refresh endpoint
  is updated to expect `202` instead of `200`.
- Swagger UI walk-through of `POST /api/v1/unlock`,
  `POST /api/v1/holdings/account`,
  `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`,
  the manual refresh endpoint, and `GET /api/v1/jobs/{id}` —
  response shapes match the regenerated OpenAPI.

#### Dependencies

- ADR-0015 + ADR-0016 land as part of this iteration's spec-
  agent sharpening (already authored). No external blockers.
- `backlog/unlock-flow-cleanup.md` shares surface (it touches
  the unlock state machine more broadly). That work is later
  and broader; this one is a focused architectural cleanup.
- `backlog/worker-restart-locked-state-handshake.md` is
  weakly related but probably becomes unnecessary under
  ADR-0016 (orchestrator has no internal lock state to lose
  on restart). Mark for re-evaluation when this iteration
  closes.

#### Verification (Rémy)

- Hand tests 1–5 above.
- `grep` audit per the acceptance section: no ccxt in
  worker, no `system.unlocked` payload containing the
  passphrase, no surviving `CustodialPollHandler`.
- `redis-cli MONITOR` during an unlock — verify the
  passphrase does not appear anywhere on the wire.
- `tools/check-spec.ps1` (Windows) passes.
- `.ps1` smoke-test suite passes (updated to expect 202 on
  the manual refresh endpoint).
- Swagger UI walk-through of the five endpoints touched.

#### Closeout

Standard PROCESS.md §4.4 stage 5 sequence. On Rémy's explicit
greenlight after stage-4 validation:

- Regenerate `api/openapi.yaml` from the running backend.
  Confirms: new
  `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`
  route; `AccountCreateOut` schema gained `kickoff_job_id`;
  manual refresh route response shape changed to `202`
  + `job_id`.
- Append a condensed entry to `shipped.md` describing the
  migration: `CustodialPollHandler` retired from the
  backend; new internal cycle endpoint;
  `CustodialPollScheduler` + `CustodialPoller`
  (orchestrator) re-introduced in the worker (no ccxt, no
  secret store); `system.locked` / `system.unlocked`
  topic-only events; post-Account-creation and manual-
  refresh flows migrated to one-shot RQ jobs; worker boots
  cleanly with backend locked. Note whether Redis-backed RQ
  executor was implemented in this iteration or remains a
  follow-up.
- Re-evaluate
  `backlog/worker-restart-locked-state-handshake.md`. If the
  orchestrator-no-internal-state shape eliminates the
  failure mode, `rm` the backlog file.
- Clear this active iteration block back to "No active
  coding iteration."
- Run `tools/check-spec.ps1` / `.sh` one final time. Must
  pass.
- Commit the closeout in a single change. Commit message
  references the iteration name and the validation date.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only; everything
else is reference.
