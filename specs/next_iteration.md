# Next iteration

The sharpened, fully-detailed scope of work the coding agent is
working on (or about to start). Updated in lockstep with the
canonical specs whenever the spec evolves.

When this iteration completes:
- Items shipped → condensed entry appended to `shipped.md`,
  removed from this file.
- Canonical specs already reflect the target (no extra "merge"
  work).
- One item from `future_iterations.md` is promoted, sharpened,
  and becomes the new active iteration here.

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

### Iteration: Account observation scope amendment + ledger polling

**Started:** 2026-05
**Goal:** Land ADR-0012's observation-scope amendment end-to-end so the
Account read-only credential carries both Kraken-side observation
permissions (`Query funds` + `Query ledger entries`), and so the
backend has the ledger-polling infrastructure and SSE topics the
Account-detail-page iteration (B) will consume. Self-contained
follow-up to the Add Account wizard iteration that closed 2026-05-16;
unlocks the activity-feed surface that iteration B will design.

#### Scope (in) — required

The full visual ground truth for the wizard surface that changes here
is in the **Mockup contract** below — two of the four validated wizard
mockups had in-place copy refreshes per ADR-0012. The bullets below
are *implementation scope*, not *UI specification*.

**Backend changes:**

1. **Per-provider overage logic.** The Account-create validation
   endpoint (`POST /api/v1/holdings/account/validate`) currently
   rejects keys with any permission beyond `Query funds`. Replace
   with per-provider declared observation-set comparison:
   - Each `CustodialProviderAdapter` declares its
     `observation_permission_set` at registration. For Kraken v1:
     `{Funds: Query, Data: Query ledger entries}`.
   - The validation endpoint compares the key's actual permissions
     (verbatim from the provider's key-permissions response) against
     the adapter's declared set. Rejects on **overage** (any
     permission not in the set) AND on **underage** (any permission
     in the set missing from the key).
   - The error response surfaces both kinds in the danger-band payload
     so the frontend can render the verbatim permission names per the
     error-variant mockup.

2. **Ledger-polling subscriber/scheduler.** Add a new worker
   component (`CustodialLedgerPoller` or equivalent — exact naming
   per existing convention in `01_architecture.md` §Worker components)
   that, on each `CustodialPollScheduler` tick, fetches new ledger
   entries since the last cycle's `cursor` for each Account. Calls
   ccxt's `fetchLedger` (Kraken's `Ledgers` endpoint under the hood).
   Persists each new ledger entry to a new `custodial_ledger_entry`
   table (or extends an existing one — coding-agent call, document
   in commit) keyed on Account + provider-side entry id, with
   columns: provider entry id, kind (deposit / withdrawal / trade /
   fee / transfer / staking), asset, amount, status (pending /
   success / failed per provider), timestamp, raw payload (JSONB
   for forward-compatibility).

3. **New SSE topic `treasury.custodial.ledger_entry_added`.** Fires
   on every new persisted ledger entry. Payload includes
   `holding_id`, the persisted row, and the Account's updated
   freshness timestamp. Subscribers: the frontend (for iteration B's
   Operations tab) and the `AuditReconciler` if relevant.

4. **New SSE topic `treasury.custodial.connection_state_changed`.**
   Fires when an Account's connection health transitions
   (healthy / degraded / unreachable / auth-failed). Drives the
   per-Holding connection-status dot on iteration B's Account
   detail page. Backend-side state machine: N consecutive successful
   polls → healthy; 1 transient error → degraded; N consecutive
   errors → unreachable; auth error → auth-failed (terminal until
   credential replaced).

5. **New SSE topic `system.chain.connection_state_changed` (if
   absent).** Verify against the running backend; if it doesn't
   exist, add it. Mirror semantics of the custodial connection-state
   topic but for the backend's RPC + ZMQ link to bitcoind. Iteration
   B's chain-based Holding detail pages will consume it, but it
   belongs to the cross-cutting SSE inventory and ships here so it
   doesn't get tacked onto iteration B's scope. The coding agent
   should check both the topic and the producer (`ChainListener` or
   equivalent) before adding.

6. **OpenAPI regeneration.** Per ADR-0004 / PROCESS.md §4.2 the
   regenerated `api/openapi.yaml` reflects the updated validate
   endpoint's response shape (now carries `overage` AND `underage`
   fields), the new ledger-entry shape if exposed via REST, and
   any new SSE topic registrations.

**Frontend changes:**

7. **Wizard Step 1 helper banner copy.** Update the rendered helper
   banner to instruct enabling both Kraken permissions per the
   updated validated mockup
   (`mobile_add_holding_account_01_connect.html`). Vocabulary:
   "Name it `TallyKeep Read` and tick **only** `Query funds` and
   `Query ledger entries`." Per-provider banner registry stays
   structurally unchanged; Kraken's entry now carries the two-flag
   string.

8. **Wizard Step 1 error-variant danger band copy.** Update the
   rendered danger band to reflect the amended observation set per
   the updated validated mockup
   (`mobile_add_holding_account_01_connect_error_overage.html`):
   "Replace these keys on Kraken Pro with ones that have **ONLY**
   `Query funds` and `Query ledger entries` ticked." The verbatim
   permission-list rendering, the tap-to-clear-both behaviour, and
   the field-error styling are unchanged.

9. **Underage handling on Step 1.** The validation response's new
   `underage` field carries any required-but-missing observation
   permissions. Surface in the danger band the same way as overage,
   distinct title: "This key is missing required permissions"
   listing the missing ones. The tap-to-clear-both behaviour applies
   identically.

#### Scope (out) — required

- **Account detail page UI.** Iteration B; full design pass to come.
  Until iteration B ships, the Account detail placeholder page
  (`/holding/[id]` route from the prior iteration) stays as-is.
- **Deposit Send-to-Account flow.** Captured in
  `future_iterations.md` "Deposit Send-to-Account flow". Iteration B
  surfaces a Deposit button that routes to a coming-soon stub until
  this flow ships.
- **Withdrawal credential changes.** ADR-0011's withdrawal
  credential definition stands unchanged. The withdrawal sub-flow
  is its own future iteration.
- **Other providers.** Kraken-only at v1; the per-provider
  declaration pattern is in place but no other adapter is registered.
  Bitstamp / Coinbase / etc. land in "Additional CustodialProvider
  adapters".
- **Activity-feed UI on the Account detail page.** Iteration B
  consumes the new SSE topic; the surface design lands there.
- **Backend-side replay / catch-up for ledger entries during downtime.**
  The first cycle after restart should fetch since the last persisted
  cursor; deeper backfill / replay against missed ledger history is
  out of scope. If gaps are detected, log and continue — recovery
  pattern is its own concern if it becomes an issue in personal-use
  phase.
- **Visualization or analytics of ledger entries.** This iteration
  persists them and emits the SSE topic; iteration B and later
  iterations decide how they're displayed.

#### Affected canonical docs

Already updated to reflect target state (2026-05-17):

- `holdings/01_account.md` — credentials section reflects ADR-0012's
  observation-permission-set model; §"What an Account does" reframed
  to "observes" instead of "polls" with ledger entries explicit in
  the observation cycle.
- `UI/mobile.md` Add-Holding Account-wizard section — *deferred* due to prior-iteration drift discovered during iteration A sanity sweep: the on-disk file dates from 2026-05-15 and never received the Account-wizard section the prior closeout reported. To be addressed in a separate small drift-cleanup pass; iteration A does not block on it. Original intended edit: permission
  references reflect the two-flag observation set; overage / underage
  error semantics.
- `decisions/0012-observation-scope-expansion.md` — new ADR.
- `decisions/0011-account-two-key-model.md` — status updated:
  permission-list section superseded by 0012.
- `decisions/README.md` — ADR index updated (and a duplicate 0011
  entry cleaned up).
- `future_iterations.md` — new entry "Deposit Send-to-Account flow"
  captured.
- `UI/mockups/mobile_add_holding_account_01_connect.html` — helper
  banner copy + design-notes comment refreshed in-place; date bumped
  to 2026-05-17; status remains `validated` per
  `UI/mockups/README.md` cosmetic-refinement rule.
- `UI/mockups/mobile_add_holding_account_01_connect_error_overage.html` —
  helper banner + danger-band copy + design-notes comment refreshed
  in-place; date bumped; status remains `validated`.

#### Mockup contract — required

The two refreshed mockups are the visual ground truth for the
wizard-copy changes in this iteration. The structural shape (layout,
palette, error-variant flow, tap-to-clear behaviour, paste / reveal
affordances, step counter, footer CTA) is unchanged from the prior
iteration's validation pass; only the helper-banner and error-variant
permission strings change.

- `UI/mockups/mobile_add_holding_account_01_connect.html` — Step 1
  default state. Helper banner now reads "`Query funds` and
  `Query ledger entries`". `validated`.
- `UI/mockups/mobile_add_holding_account_01_connect_error_overage.html`
  — Step 1 post-rejection state. Helper banner and danger band's
  corrective instruction both reflect the two-permission set.
  `validated`.

The other two wizard mockups carry no permission references and are
not in this iteration's mockup contract:

- `UI/mockups/mobile_add_holding_account_02_parseback.html` —
  untouched.
- `UI/mockups/mobile_add_holding_account_03_success.html` —
  untouched.

**Coding-agent rule (PROCESS.md §2 Coding agent — Visual contract):**
read each mockup in the contract before writing the corresponding
screen code. The copy strings in the mockup are the contract;
implementation may not paraphrase. Deviation is either a code bug
(fix it) or a spec drift event (stop, surface to Rémy, mockup
update). No third path.

#### Tasks — required

Concrete, ordered. Each maps to a definition-of-done.

1. **Backend: per-provider observation set declaration.** Add an
   `observation_permission_set` attribute to the
   `CustodialProviderAdapter` ABC and to the Kraken adapter's
   registration. **Done when:** the adapter exposes the set as
   `{"Query funds", "Query ledger entries"}` (or the verbatim Kraken
   permission strings the backend already uses); the attribute is
   read by the validation endpoint at request time.

2. **Backend: validation endpoint rejects overage AND underage.**
   `POST /api/v1/holdings/account/validate` compares the key's actual
   permissions against the adapter's declared set. Rejects with HTTP
   409 (the existing locked-state pattern) on either overage or
   underage. Response payload's `detail` carries both `overage:
   list[str]` and `underage: list[str]` fields (always present;
   empty lists if no items). **Done when:** integration tests cover
   the OK case (exactly the two permissions, nothing else), the
   overage case (one extra: e.g. `{Query funds, Query ledger entries,
   Withdraw funds}`), the underage case (one missing: e.g. only
   `Query funds` ticked), and the both-missing-and-overaged case
   (e.g. `{Query funds, Trade}` — missing ledger, extra Trade).

3. **Backend: ledger-polling subscriber.** Implement a new worker
   component that, on each `CustodialPollScheduler` tick (or as a
   separate scheduler if cleaner — coding-agent call), fetches new
   ledger entries since the last cycle's persisted cursor for each
   Account via ccxt's `fetchLedger`. Persist each new entry. **Done
   when:** an integration test against a Kraken sandbox or fixtures
   replays a sequence of poll cycles and asserts the persisted set
   matches the expected ledger entries; no duplicates on re-poll;
   cursor advances correctly across cycles.

4. **Backend: SSE topic `treasury.custodial.ledger_entry_added`.**
   Emit on every new persisted ledger entry. Payload includes
   `holding_id`, the persisted row's fields, and the Account's
   updated freshness timestamp. **Done when:** an integration test
   subscribes to the topic, triggers a ledger-poll cycle that yields
   new entries, and asserts the emitted events match the persisted
   set 1-to-1.

5. **Backend: SSE topic
   `treasury.custodial.connection_state_changed`.** Define the topic
   and emit on connection-health transitions per the state machine
   in scope-bullet 4. **Done when:** an integration test forces an
   auth-error response from the Kraken adapter and asserts the
   emitted event reflects `auth_failed`; recovery on a successful
   poll emits a transition back to `healthy`.

6. **Backend: verify / add SSE topic
   `system.chain.connection_state_changed`.** Inspect the running
   backend for the topic and its producer. If absent, add to
   `ChainListener` (or equivalent) and emit on bitcoind RPC / ZMQ
   health transitions. **Done when:** the topic exists, an
   integration test forces an RPC error and asserts the emitted
   event reflects the degraded state. If the topic already exists,
   this task is a no-op; document the no-op in the closeout
   commit message.

7. **Backend: OpenAPI regeneration.** Per ADR-0004 / PROCESS.md
   §4.2, regenerate `api/openapi.yaml` from the running backend at
   closeout. **Done when:** the file reflects the validation
   endpoint's new response shape, any new REST surfaces for ledger
   entries, and the new SSE topic registrations.

8. **Frontend: wizard Step 1 helper banner copy.** Update the
   rendered Kraken helper-banner copy to match
   `mobile_add_holding_account_01_connect.html`'s validated state.
   **Done when:** the wizard's Step 1 default state renders
   "`Query funds`" and "`Query ledger entries`" in the bolded-only
   list; pixel comparison against the mockup at 360×800 passes.

9. **Frontend: wizard Step 1 error-variant danger-band copy.**
   Update the danger-band's corrective instruction to match
   `mobile_add_holding_account_01_connect_error_overage.html`'s
   validated state ("`Query funds` and `Query ledger entries`
   ticked"). **Done when:** the wizard's Step 1 error variant
   renders the updated corrective copy; the verbatim overage list
   continues to surface backend-supplied permission strings.

10. **Frontend: Step 1 underage handling.** When the validation
    response carries non-empty `underage`, render a danger band
    with title "This key is missing required permissions" and the
    list of missing permissions verbatim from the response. Same
    tap-to-clear-both behaviour as the overage variant. **Done
    when:** an end-to-end test (or hand-test against the running
    backend with a `Query funds`-only key) lands on the underage
    danger band; the tap-to-clear-both rule fires correctly.

#### Acceptance / done-when — required

- A fresh Kraken key with `Query funds` + `Query ledger entries`
  (and nothing else) ticked, pasted into the wizard, succeeds
  through Step 1 → Step 2 → Step 3 → Home with the new Account
  visible.
- A Kraken key carrying any permission outside the observation
  set (Trade, Margin, Futures, Earn, Withdraw funds, Deposit
  funds, anything beyond the two) is rejected at Step 1 with
  the overage danger band, listing the extras verbatim.
- A Kraken key missing either of the two required permissions
  (e.g. only `Query funds`) is rejected at Step 1 with the
  underage danger band, listing the missing permission.
- Subscribing to `treasury.custodial.ledger_entry_added` from a
  manual SSE client (curl + EventStream) after triggering a poll
  cycle yields events whose payloads match the persisted
  `custodial_ledger_entry` rows.
- Subscribing to `treasury.custodial.connection_state_changed`
  yields a state transition when the Kraken adapter returns an
  auth error and a recovery transition when polling resumes.
- `system.chain.connection_state_changed` exists and emits on
  bitcoind RPC health transitions.
- The two updated wizard mockups match the shipped Step 1
  screens at 360×800; pixel comparison passes.
- `api/openapi.yaml` regenerated; the validation endpoint's
  response shape now carries `overage` and `underage`.
- `tools/check-spec.ps1` (or `.sh`) passes after the closeout
  edits land.

#### Dependencies

- **None blocking.** The prior Add Account wizard iteration shipped
  cleanly on 2026-05-16; this is a follow-up contained amendment.
  Bitstamp deferral and Account withdrawal sub-flow remain in
  `future_iterations.md`; the Account detail page (iteration B)
  depends on this iteration but not the reverse.

#### Verification (Rémy)

After the coding-agent's stage-3 handoff:

- Run the project's `.ps1` smoke-test suite against the running
  backend to confirm the tightened validation endpoint behaves
  correctly across the OK / overage / underage / auth-fail cases.
- Walk Swagger UI for the validate endpoint; confirm the new
  response shape (`overage`, `underage` fields) renders.
- Subscribe to each of the new SSE topics from a manual client
  (curl + EventStream or equivalent) and trigger a poll cycle on
  the running backend; confirm events arrive shaped as expected.
- In a browser at 360×800, walk Step 1 of the wizard with three
  Kraken keys: a clean observation-set key (success), an overage
  key (overage danger band), an underage key (underage danger
  band). Confirm screens match the validated mockups; confirm the
  tap-to-clear behaviour works for both error variants.
- Confirm `system.chain.connection_state_changed` exists and emits
  by simulating an RPC error against bitcoind.

#### Closeout

The agent does **not** start closeout until Rémy gives an explicit
greenlight after stage-4 validation. On greenlight the agent:
regenerates `api/openapi.yaml` (yes — API surface changed), appends
a condensed entry to `shipped.md`, clears the active block in this
file back to "No active coding iteration.", runs
`tools/check-spec.ps1` (or `.sh`), commits. Full sequence in
`PROCESS.md §4.4` stages 3–5.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`future_iterations.md §Iteration roadmap`, not here.
`next_iteration.md` carries the active block only; everything
else is reference.
