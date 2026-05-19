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

### Iteration: Purse detail page + Account Forget timer

**Started:** 2026-05
**Goal:** Tapping a Purse row on Home opens a per-Holding detail
page that renders honestly for all three purse modes, with the
chrome decisions locked at the Account-detail iteration carried
forward where they generalise and Purse-specific affordances
designed from Purse's own process where they don't.

#### Scope (in) — required

- **Purse detail page** at `/holding/[id]` for Holdings of type
  `purse`. Two-tab layout (Operations | Settings), SSE-driven
  freshness, single-unit hero with ↻ toggle shared with Home,
  pull-to-refresh + tap-status-card-to-refresh. Mockups:
  `mobile_purse_detail_operations_populated.html`,
  `mobile_purse_detail_operations_empty.html`,
  `mobile_purse_detail_settings_watch_only.html`,
  `mobile_purse_detail_settings_on_device.html`,
  `mobile_purse_detail_forget_confirm.html`,
  `mobile_purse_detail_connection_error.html`,
  `mobile_purse_detail_send_blocked_watch_only.html`. Canonical
  prose: `UI/mobile.md §Purse detail` (new section).

- **Status card** carries a Purse-type left-stripe (auburn
  leather, `--color-holding-purse`) and a **mode subtitle** —
  "Watch-only", "Spending wallet", or "Spending wallet ·
  imported" (the third reserved; not yet shipped). Connection-
  state dot sources from
  `system.chain.connection_state_changed` (bitcoind RPC/ZMQ
  health) rather than the Account topic. Per-Holding-type lock
  from the Account-detail iteration.

- **Action row — Send + Receive** at light-CTA weight, using a
  unified directional-arrows-on-wallet icon pair (arrow leaving
  the wallet for Send, arrow entering the wallet for Receive).
  This icon pair is the new cross-type standard for Holdings
  that are the user's own wallet (Purse / Strongbox / Vault);
  the Account "Deposit / Withdraw + card-with-arrow" pair stays
  put because Account is structurally a different kind of
  thing (custodial pass-through, not the user's wallet).

- **Send routing — per purse_mode:**
    - `WATCH_ONLY` → real screen
      `mobile_purse_detail_send_blocked_watch_only.html` (not a
      coming-soon stub). Explains "TallyKeep doesn't hold the
      keys for this Purse", offers two paths: (a) "Construct a
      PSBT and show as QR for [source wallet]" → coming-soon
      stub (the PSBT-export sub-flow ships with the Send
      iteration), (b) "Add the keys to this Purse" →
      upgrade-path coming-soon stub (per
      `backlog/purse-upgrade-path-watch-only-on-device-imported.md`).
    - `ON_DEVICE_TK_GENERATED` (and `ON_DEVICE_USER_IMPORTED`
      when it ships) → coming-soon stub mirroring
      `mobile_add_holding_coming_soon.html` (the native-sign
      Send flow ships in its own iteration).

- **Receive routing — all modes route to a coming-soon stub.**
  Receive mechanics are mode-agnostic (address derivation is
  public) and small, but the Receive flow has its own UX
  surface (QR + BIP21 + tap-to-copy) and ships in its own
  iteration.

- **Operations tab.** Activity feed from chain-side
  `LedgerEntry` rows for the descriptor (BDK observation,
  per-Purse). Text-only kind descriptor + relative time +
  signed amount in the active unit with sign-based color
  (positive `success-text-on-soft`, negative
  `danger-text-on-soft`). SSE-driven live insertion at the
  top via the existing chain-scan event topic. Empty state
  for fresh / quiet Purses: title "No activity yet", sub
  "Incoming and outgoing payments will surface here as they
  hit the chain." No illustration.

- **Settings tab — `WATCH_ONLY` variant.** Sections (top to
  bottom): Wallet (mode "Watch-only" + creation date, info
  only); Descriptor (xpub, masked + reveal); Auto-sweep rules
  ("None" + "Add rule" → coming-soon); Instant payments
  ("Lightning · Not enabled" + "Activate" → coming-soon, per
  `backlog/lightning-support.md`); Danger zone (Rename +
  Forget).

- **Settings tab — `ON_DEVICE_TK_GENERATED` variant.**
  Sections (top to bottom): Wallet (mode "Spending wallet" +
  creation date); Descriptor (xpub, masked + reveal);
  Recovery phrase ("View recovery phrase" → coming-soon stub,
  deferred to the Security-health-system iteration per
  `backlog/security-health-system.md`); Auto-sweep rules
  ("None" + "Add rule" → coming-soon); Instant payments
  ("Lightning · Not enabled" + "Activate" → coming-soon);
  Danger zone (Rename + Forget with the seed-destruction
  warning copy).

  The `ON_DEVICE_USER_IMPORTED` variant is structurally
  identical to `ON_DEVICE_TK_GENERATED` with disclosure-copy
  framing differences (no "TallyKeep gave you this seed"
  language); not mocked in this iteration because the
  creation flow doesn't ship yet (per
  `backlog/purse-upgrade-path-watch-only-on-device-imported.md`).

- **Descriptor reveal.** Privacy-first-reveal pattern per the
  feedback memory: at rest, masked display (last 6 chars in
  mono); tap "Show descriptor" → full descriptor in mono
  inside a bordered card, with sensitive-screen flag for
  Capacitor (FLAG_SECURE / iOS sensitive-screen) when that
  bridge lands. No Copy affordance on Purse descriptor in v1
  (descriptors carry the wallet's persistent identifier; the
  privacy-first-reveal memory's no-Copy rule applies). Coding
  agent may add one if Rémy revisits during validation.

- **Forget bottom-sheet modal.** Two-button confirm pattern
  matching `mobile_account_detail_remove_confirm.html`, with
  **two Purse-specific changes**:
    1. **5-second timer on the Forget button.** Button is
       initially disabled with a countdown ("Forget · 5",
       "Forget · 4", …) and becomes active at zero. Cancel
       is active throughout. Prevents misfire on a
       destructive action; gives the user 5 seconds to read
       the body. The same timer also lands on the
       Account-detail Forget modal in this iteration (see
       the Account update below).
    2. **For `ON_DEVICE_*` Purses only, a load-bearing
       warning above the body copy:** *"You told us you
       backed up your recovery phrase. Verify your backup is
       intact and you can read it. Once you forget this
       Purse, the keys are destroyed and any forgotten
       backup is gone forever."* (Final wording iterable in
       the mockup; the intent is locked.) The warning is
       rendered in a `danger-soft` panel with
       `danger-text-on-soft` text, visually distinct from the
       regular body copy.

    For `WATCH_ONLY` Purses, the modal uses the parallel-to-
    Account copy ("TallyKeep forgets the descriptor and
    stops scanning the chain for these addresses. Funds at
    your source wallet are unaffected."). The mockup ships
    the `ON_DEVICE_*` variant (the load-bearing one); the
    `WATCH_ONLY` copy is documented in
    `UI/mobile.md §Purse detail`.

- **Connection-error toast** (bitcoind unreachable). Same
  toast pattern as Account, copy adjusted: title "Cannot
  reach the Bitcoin network", retry CTA, persistent red dot
  in the status card with "Connection lost · Last seen N min
  ago". Driven by `system.chain.connection_state_changed`.

- **Home → Purse detail navigation.** Tapping a Purse row on
  Home navigates to `/holding/[id]`. The placeholder route
  shipped 2026-05-16 (Vault iteration) is replaced for
  `purse` type Holdings only; Strongbox / Vault placeholders
  remain.

- **Account-detail Forget modal edit.** Add the same
  5-second timer to
  `mobile_account_detail_remove_confirm.html`. Cosmetic-class
  edit per PROCESS.md §7 routing table (no ADR — doesn't
  touch a locked principle, vocabulary, or trust boundary).
  Update the file's `Date last touched`. The matching prose
  in `UI/mobile.md §Account detail` gains a note about the
  timer.

#### Scope (out) — required

- **Send and Receive flows** (other than the WATCH_ONLY
  Send-blocked screen which is real). Tapping Send on
  ON_DEVICE_* / Receive on any mode lands on the existing
  coming-soon stub.
- **`ON_DEVICE_USER_IMPORTED` Settings variant** — creation
  flow doesn't ship; not mocked.
- **Recovery phrase reveal mechanic.** Routes to coming-soon
  stub; the real reveal lands with the Security-health-system
  iteration (lockstep with `seed-backup-disclosure`).
- **Lightning activation flow.** Routes to coming-soon stub;
  per-Purse Lightning capability ships with the Lightning
  iteration.
- **Auto-sweep rule creation.** Routes to coming-soon stub;
  the SweepPolicy creation UX is its own iteration.
- **Upgrade-to-spending flow** for WATCH_ONLY. Routes to
  coming-soon stub; the upgrade-path flow ships per
  `backlog/purse-upgrade-path-watch-only-on-device-imported.md`.
- **Categorization affordances** on Operations entries. Per
  `UI/README.md` Activity + Categorization, categorization
  is its own iteration; this page renders read-only entries.
- **TK-initiated vs external on-chain event distinction.**
  Same posture as the Account-detail iteration: render all
  entries identically; the visual distinction lands when the
  chain-side TK-initiated linkage arbitration closes.
- **Strongbox / Vault detail pages.** Their own future
  iterations. This iteration only changes the `purse`-type
  routing on Home.
- **API changes.** None. The detail page consumes existing
  endpoints (`GET /api/v1/holdings/{id}`, the chain-scan SSE
  topics, the ledger-by-holding query) and existing domain
  shapes. No OpenAPI regen.

#### Affected canonical docs

- `UI/mobile.md` — new `## Purse detail` section after
  `## Account detail`; small append-only note in `## Account
  detail` documenting the 5-second timer.
- `holdings/02_purse.md` — short forward-reference paragraph
  acknowledging the Purse detail page surface; vocabulary
  lockstep on the action verbs (Send / Receive) and the
  Forget warning.
- `UI/README.md §Holding detail` — small update so the
  per-type bullet for Purse references the mockups instead
  of the older free-form text.

#### Mockup contract — required if iteration touches UI

By design-pass close (Rémy greenlight), each of these is
`Status: validated`. The coding agent reads every file in
this list before writing the corresponding screen. Copy,
spacing, states, affordances, error variants — the mockup
HTML is the contract. Deviation rule per PROCESS.md §2
Coding agent.

- `UI/mockups/mobile_purse_detail_operations_populated.html` — default state, ON_DEVICE_TK_GENERATED, 6 activity entries, balance hero, mode subtitle in status card.
- `UI/mockups/mobile_purse_detail_operations_empty.html` — fresh Purse, zero activity, no balance.
- `UI/mockups/mobile_purse_detail_settings_watch_only.html` — WATCH_ONLY Settings: Wallet / Descriptor / Auto-sweep / Instant payments / Danger zone (no Recovery phrase row).
- `UI/mockups/mobile_purse_detail_settings_on_device.html` — ON_DEVICE_TK_GENERATED Settings: includes Recovery phrase row.
- `UI/mockups/mobile_purse_detail_forget_confirm.html` — Forget bottom-sheet, ON_DEVICE_* variant (renders the load-bearing seed-destruction warning + 5-second timer).
- `UI/mockups/mobile_purse_detail_connection_error.html` — bitcoind unreachable toast + red dot.
- `UI/mockups/mobile_purse_detail_send_blocked_watch_only.html` — real screen, two paths (PSBT-export → coming-soon, Add keys → coming-soon).

Plus the structural edit:

- `UI/mockups/mobile_account_detail_remove_confirm.html` — gains the 5-second timer; `Date last touched` bumped.

#### Tasks — required

1. **Read every mockup file listed in the Mockup contract.**
   Required before writing any code in this iteration; the
   visual ground truth is the mockup, not the prose.
2. **Wire `/holding/[id]` routing for `purse` Holdings.** The
   existing placeholder route handles the navigation; this
   task adds the Purse-specific page component and selects
   it when the loaded Holding's type is `purse`. Strongbox /
   Vault placeholders unchanged.
3. **Build the page chrome** (app bar, status card with mode
   subtitle, hero with shared ↻ unit toggle, action row,
   sticky tab strip, bottom nav). Reuse the
   Account-detail-shipped chrome components where possible;
   the Purse-specific bits are the stripe colour, the mode
   subtitle, and the action-row icons.
4. **Build the Operations tab.** Subscribe to the chain-scan
   SSE topic for this Holding; render entries via the
   existing activity-row component; empty state per mockup.
5. **Build the Settings tab.** Conditional rendering per
   `purse_mode` for the Recovery-phrase row and the Wallet
   subtitle. All CTAs that route to coming-soon use the
   parameterized `coming-soon` route.
6. **Build the descriptor reveal.** Privacy-first-reveal
   pattern: masked at rest, full on tap. NativeBridge
   sensitive-screen flag scaffolded for Capacitor; browser
   build is the dev surface.
7. **Build the Forget bottom-sheet modal** with the
   5-second timer + the per-mode body-copy variant. Wire to
   the backend's Forget endpoint (existing for Account;
   verify the Purse case calls the right repo method and,
   for `ON_DEVICE_*`, calls
   `NativeBridge.secureStorage.delete` for the seed entry
   before the backend call). Cancel must abort cleanly.
8. **Build the connection-error toast** on
   `system.chain.connection_state_changed` transitions.
9. **Build the Send-blocked screen** for WATCH_ONLY (real
   screen, not a stub). Wire the two CTAs to their
   respective coming-soon stubs.
10. **Edit the Account remove-confirm modal**
    (`mobile_account_detail_remove_confirm.html`) to add the
    matching 5-second timer. Update the mockup's
    `Date last touched`. Update the corresponding
    implementation on the Account-detail page.
11. **Run `tools/check-spec.ps1`** (Windows) or
    `tools/check-spec.sh` (Linux/Mac). Must pass before
    stage-3 handoff.
12. **Stop and report** per PROCESS.md §4.4 stage 3. Do not
    regenerate OpenAPI (no API surface changes). Do not edit
    `next_iteration.md` or append to `shipped.md` until
    Rémy's explicit greenlight.

#### Acceptance / done-when — required

- Tapping a Purse row on Home navigates to `/holding/[id]`
  and renders the Purse detail page; the title bar shows the
  Holding's display name; the status card shows the
  Purse-type stripe (auburn) and the correct mode subtitle.
- The Operations tab shows the user's chain-side activity
  for this Purse, newest-first, with sign-based amount
  colour. Empty Purses render the empty-state panel from the
  mockup.
- The Settings tab renders the right variant for the Purse's
  mode (WATCH_ONLY shows no Recovery phrase row;
  ON_DEVICE_TK_GENERATED shows it routing to coming-soon).
  Every CTA either routes to a real screen (Send for
  WATCH_ONLY → the Send-blocked screen) or to the
  coming-soon stub.
- Tapping Forget on either Purse mode opens the bottom-sheet
  with the right body copy variant. Forget button is
  disabled for the first 5 seconds with a visible countdown;
  Cancel is active immediately. Confirming Forget for an
  `ON_DEVICE_*` Purse calls
  `NativeBridge.secureStorage.delete(holding_id)` before the
  backend Forget call.
- Tapping Forget on Account also shows the 5-second timer
  (this iteration extends that flow).
- Disconnecting bitcoind (smoke-test) flips the connection
  dot red and slides the connection-error toast in.
- `tools/check-spec.ps1` passes (8 checks): mockup index
  includes the 7 new files; no broken backtick refs; no
  un-flushed canonical-doc edits.
- No OpenAPI regen needed (verified: no endpoint, schema,
  SSE topic, error type, or locked-state behaviour changed).

#### Dependencies

- **Design-pass validation by Rémy.** The 7 new mockups and
  the edited Account remove-confirm must be `validated`
  before the coding agent starts. Per PROCESS.md §2 Design
  agent — mockup status flips at the design-pass greenlight,
  not at coding closeout.
- **No arbitration blockers.** `purse-upgrade-path`,
  `seed-backup-disclosure`, and `multi-asset-aggregation`
  remain open in `pre-implementation.md` but do not block
  this iteration — every entry that touches them routes to
  a coming-soon stub that the future arbitration's iteration
  replaces.
- **No backend changes required.** Account-detail iteration
  already shipped the SSE-driven Holding detail
  infrastructure and the chain-scan SSE topics already exist
  from the Add-Purse-wizard iteration.

#### Verification (Rémy)

- Open each of the 7 new mockups in the browser at 360×800;
  verify chrome consistency with the validated Account-detail
  mockups, copy correctness, and per-mode Settings variants.
- Hand-test the running app: tap a Purse row on Home (each
  mode if multiple Purses exist), exercise both tabs, test
  Forget (both modes — verify the timer and the per-mode
  warning copy), test the descriptor reveal, test the
  Send-blocked screen for a WATCH_ONLY Purse, simulate a
  bitcoind disconnect to surface the toast.
- Test the updated Account Forget modal — verify the
  5-second timer landed and didn't regress the rest of the
  flow.
- Run the project's `.ps1` smoke-test suite. Walk through
  Swagger UI for the touched endpoints (read-only — no API
  surface changes expected).

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight
the agent: appends a condensed entry to `shipped.md`, clears
the active block in this file, runs `tools/check-spec.ps1`,
commits. **No OpenAPI regen** for this iteration (no API
surface changes). Full sequence in `PROCESS.md §4.4` stages
3–5.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only; everything
else is reference.
