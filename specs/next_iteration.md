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

No active coding iteration.

<!--

### Iteration: Strongbox detail page + Purse descriptor Copy retrofit

**Started:** 2026-05
**Goal:** Tapping a Strongbox row on Home opens a per-Holding
detail page that renders honestly for the hardware-wallet trust
posture, generalising the Purse-detail chrome and adding the
Strongbox-specific bits (signing-device-label subtitle,
missing-signing-metadata inline advisory, permanently-gated
Lightning) — plus a small cross-type retrofit adding a Copy
affordance to the Purse descriptor reveal now that the
privacy-first-reveal rule has been sharpened to apply to
signing material only, not descriptors.

#### Scope (in) — required

- **Strongbox detail page** at `/holding/[id]` for Holdings of
  type `strongbox`. Two-tab layout (Operations | Settings),
  SSE-driven freshness, single-unit hero with the shared ↻
  toggle, pull-to-refresh + tap-status-card-to-refresh. Same
  chrome generalised from the Purse-detail iteration. Mockups
  listed in the Mockup contract below. Canonical prose:
  `UI/mobile.md §Strongbox detail` (new section, written in
  the design pass alongside the mockups).

- **Status card** carries a Strongbox-type left-stripe (iron,
  `--color-holding-strongbox: #4a4d4f`) and a **status-card
  subtitle** that uses the user-set `signing_device_label`
  when present (e.g. "Coldcard Mk4 in safe", "BitBox02 —
  drawer"), falling back to **"External signing device"** when
  the label is empty. Connection-state dot sources from
  `system.chain.connection_state_changed` (bitcoind health),
  same as Purse. Per-Holding-type stripe-colour lock from the
  Account-detail iteration; subtitle-fallback vocabulary lock
  established here.

- **Action row — Send + Receive** at light-CTA weight, using
  the unified arrow-and-wallet icon pair locked in the
  Purse-detail iteration. Both Send and Receive route to
  **coming-soon stubs** in this iteration — the real
  PSBT-export Send and the verify-on-device Receive ship with
  the Send + Receive iteration (roadmap step 4). No
  Send-blocked screen variant: Strongbox always has a path,
  it's just deferred. Same routing posture as Purse Receive.

- **Operations tab.** Activity feed from chain-side
  `LedgerEntry` rows for the descriptor (BDK observation,
  per-Strongbox). Identical row shape to Purse Operations:
  text-only kind descriptor, relative time, optional category
  chip (read-only on this surface, same as Purse), signed
  amount in the active unit with sign-based colour. SSE-driven
  insertion at the top via the existing chain-scan event
  topic. Empty state for fresh Strongboxes: title "No activity
  yet", sub "Incoming and outgoing payments will surface here
  as they hit the chain." No illustration.

- **Settings tab — single variant** (Strongbox has no mode
  axis like Purse's `purse_mode`; the only conditional bit is
  the missing-metadata advisory, surfaced as a card overlay
  rather than a mode variant). Sections (top to bottom):
    - **Missing-signing-metadata advisory** (conditional —
      only when the descriptor was imported without
      `[fingerprint/path]` brackets, i.e. bare xpub). A
      `warning-soft` card at the top of the Settings tab,
      above Wallet. Copy: *"Missing derivation metadata. Your
      hardware wallet may refuse to sign transactions with
      this descriptor. Receiving funds works as expected."* +
      **Fix this** CTA → coming-soon stub. Per-Holding inline
      surfacing of a security-health item; the centralised
      Security-health surface is still under arbitration
      (`seed-backup-disclosure`) and out of scope. The
      Fix-this remediation sub-flow (re-export from HW wallet
      with full origin metadata; manual fingerprint +
      derivation-path entry) ships with the Security-health-
      system iteration per `backlog/security-health-system.md`.
    - **Wallet** — info-only. Line 1: "External signing
      device". Line 2: creation date ("Imported on May 14,
      2026"). No "TallyKeep generated/imported keys" framing
      because TallyKeep never sees the keys for a Strongbox.
    - **Display name** — current display name + **Rename**
      CTA. Same pattern as Purse / Account post-2026-05-19
      round-2 fix (Rename is non-destructive; lives outside
      Danger zone).
    - **Signing device label** — current `signing_device_label`
      (e.g. "Coldcard Mk4 in safe") + **Edit** CTA → inline
      edit. Free-text. Persisted via the existing Holding-
      update endpoint. This is the field that drives the
      status-card subtitle.
    - **Descriptor** — last 6 chars (mono, masked) + short
      explanation + **Show** CTA. Tap to reveal full
      descriptor inline in a bordered card, with sensitive-
      screen flag for Capacitor (FLAG_SECURE / iOS sensitive-
      screen) when the NativeBridge ships. **Copy CTA on the
      revealed state** — descriptors are public-key data
      routinely pasted between wallet clients; the
      privacy-first-reveal feedback memory's no-Copy rule
      applies to signing material only (recovery phrases,
      xprv), not descriptors. Tap Hide to mask again.
    - **Auto-sweep rules** — "None" + explanation + **Add
      rule** CTA. Routes to SweepPolicy creation (coming-soon
      stub). Same as Purse.
    - **Instant payments** — **permanently gated.** Row
      visible with greyed `settings-row--gated` styling; copy:
      *"Strongbox keys live on your hardware wallet only.
      Lightning needs hot keys — activate it on a Spending
      wallet."* CTA disabled. Same three-state gating pattern
      as Purse Lightning, with the distinction that this gate
      is permanent (not "fix it later" — the type definition
      makes it unreachable). Row stays visible for
      discoverability per the no-dead-capability rule.
    - **Danger zone** — last section, label in `danger` text
      colour. **Forget only.** Body copy: *"TallyKeep forgets
      the descriptor and stops scanning the chain. Your
      hardware wallet and the keys it holds are unaffected.
      Any categories you've assigned to this Strongbox's
      activity are erased with it."* No seed-destruction
      warning panel (no seed on TK side).

- **No Recovery phrase row.** TK never holds Strongbox
  signing material. Same logic as Purse WATCH_ONLY.

- **Forget bottom-sheet modal.** Two-button confirm pattern
  with the **5-second fill-bar timer** locked cross-type in
  the Purse-detail iteration. Forget body copy per the
  Danger-zone bullet above. No load-bearing warning panel
  above the body (no seed to destroy). Cancel active
  throughout; Forget button enables at zero. Mocked in
  `mobile_strongbox_detail_forget_confirm.html`.

- **Connection-error toast** (bitcoind unreachable). Identical
  pattern to Purse: `danger-soft` toast slide-in below the
  app bar, title "Cannot reach the Bitcoin network", "Try
  again now" CTA, persistent red dot in the status card with
  "Connection lost · Last seen N min ago". Driven by
  `system.chain.connection_state_changed`. Auto-dismisses
  after ~5 seconds; re-appears on each failed retry.

- **Home → Strongbox detail navigation.** Tapping a Strongbox
  row on Home navigates to `/holding/[id]`. The placeholder
  route shipped 2026-05-16 is replaced for `strongbox`-type
  Holdings. Vault placeholder remains.

- **Purse descriptor Copy retrofit (cross-type fix).** Per
  the corrected privacy-first-reveal scope (sharpened
  2026-05-20), descriptors are not in scope of the no-Copy
  lock. The lock applies to signing material only. The Purse
  detail Settings mockups
  (`mobile_purse_detail_settings_watch_only.html`,
  `mobile_purse_detail_settings_on_device.html`) gain a Copy
  CTA on the revealed descriptor state, matching the new
  Strongbox pattern. The corresponding implementation on the
  Purse detail Settings tab gains the same affordance.
  `UI/mobile.md §Purse detail` Descriptor bullet and the
  Behaviors section's "Descriptor reveal" paragraph are
  edited in lockstep to remove the no-Copy lock and document
  the Copy affordance. Cosmetic-class edit per PROCESS.md §7
  routing table (no ADR — corrects a prior over-application
  of a feedback rule; doesn't touch a locked principle,
  vocabulary, or trust boundary). Both retrofitted mockup
  files' `Date last touched` bumped.

#### Scope (out) — required

- **Send and Receive flows.** Both route to coming-soon stubs.
  The real PSBT-export Send (with the "verify destination on
  signing device" prompt) and the verify-on-device Receive
  flow ship with the Send + Receive iteration (roadmap
  step 4).
- **The real "Fix this" remediation sub-flow** for missing
  signing metadata. Routes to coming-soon stub; the
  re-export-or-manual-entry sub-flow ships with the
  Security-health-system iteration per
  `backlog/security-health-system.md`.
- **Centralised Security-health surface.** Out of scope. The
  missing-metadata advisory on this iteration is per-Holding
  inline surfacing only; the Home aggregator surface remains
  under arbitration.
- **Auto-sweep rule creation.** Coming-soon stub. SweepPolicy
  creation UX is its own iteration.
- **Lightning activation flow.** Permanently gated by type
  definition. No flow lives behind this row.
- **Categorization affordances** on Operations entries.
  Read-only chip only; assignment lives on the future
  Accounting page per the Purse iteration's posture.
- **Strongbox geolocation correlation.** Out of scope
  (idea-likely-discard per
  `backlog/strongbox-geolocation-correlation-idea-low-priority.md`).
- **TK-initiated vs external on-chain event distinction.**
  Same posture as Purse / Account detail; render all entries
  identically until the chain-side linkage arbitration
  closes.
- **Vault detail page.** Own future iteration; this one only
  changes `strongbox`-type routing on Home.
- **API changes.** None expected. The detail page consumes
  existing endpoints (`GET /api/v1/holdings/{id}`, the
  chain-scan SSE topics, the ledger-by-holding query) and
  existing domain shapes. The Signing-device-label inline
  editor uses the existing Holding-update endpoint; if the
  coding agent finds that `signing_device_label` is not in
  the current PATCH shape, surface to Rémy before scoping a
  backend addition (do not silently add it). No OpenAPI regen
  unless that surfaces.

#### Affected canonical docs

- `UI/mobile.md` — new `## Strongbox detail` section after
  `## Purse detail`; small in-lockstep edits to
  `## Purse detail` Descriptor bullet + Behaviors "Descriptor
  reveal" paragraph removing the no-Copy lock.
- `holdings/03_strongbox.md` — short forward-reference
  paragraph acknowledging the Strongbox detail page surface;
  vocabulary lockstep on the action verbs (Send / Receive)
  and the wallet-card subtitle fallback ("External signing
  device").
- `UI/README.md §Holding detail` — small update so the
  per-type bullet for Strongbox references the mockups.

These edits land in the design pass alongside the mockups
(per PROCESS.md §2 Design / brand agent — mobile.md prose
describes intent, mockup HTML is the contract).

#### Mockup contract — required if iteration touches UI

By design-pass close (Rémy greenlight), each of these is
`Status: validated`. The coding agent reads every file in
this list before writing the corresponding screen. Copy,
spacing, states, affordances, error variants — the mockup
HTML is the contract. Deviation rule per PROCESS.md §2
Coding agent.

New mockups:

- `UI/mockups/mobile_strongbox_detail_operations_populated.html` — default state, balance hero, status card with `signing_device_label`-driven subtitle, 6 chain-side activity entries.
- `UI/mockups/mobile_strongbox_detail_operations_empty.html` — fresh Strongbox, zero activity, no balance.
- `UI/mockups/mobile_strongbox_detail_settings.html` — Settings tab with cleanly-parsed descriptor (no missing-metadata advisory). All sections rendered.
- `UI/mockups/mobile_strongbox_detail_settings_missing_metadata.html` — Settings tab variant rendering the `warning-soft` advisory card at the top + Fix-this CTA.
- `UI/mockups/mobile_strongbox_detail_forget_confirm.html` — Forget bottom-sheet, Strongbox body copy, 5-second fill-bar timer (mid-countdown sample state).
- `UI/mockups/mobile_strongbox_detail_connection_error.html` — Operations tab with red dot in the status card + slide-in connection-error toast + cached activity entries rendered normally.

Retrofitted mockups (Purse descriptor Copy):

- `UI/mockups/mobile_purse_detail_settings_watch_only.html` — gains Copy CTA on revealed descriptor state; `Date last touched` bumped.
- `UI/mockups/mobile_purse_detail_settings_on_device.html` — same.

#### Tasks — required

1. **Read every mockup file in the Mockup contract.** Required
   before writing any code; the visual ground truth is the
   mockup, not the prose.
2. **Wire `/holding/[id]` routing for `strongbox` Holdings.**
   Add the Strongbox page component to the type-dispatch
   alongside the existing Purse case. Vault placeholder stays.
3. **Build the page chrome** — app bar, status card with
   `signing_device_label`-driven subtitle + "External signing
   device" fallback, hero, action row, sticky tab strip,
   bottom nav. Reuse Purse-detail-shipped chrome components;
   Strongbox-specifics are the stripe colour, the subtitle
   resolver, and the action-row routing.
4. **Build the Operations tab.** SSE subscription + entry
   rendering identical to Purse Operations. Empty-state panel
   per mockup.
5. **Build the Settings tab.** Conditional rendering of the
   missing-metadata advisory card (descriptor parsed without
   `bip32_derivation_origins` → render the card). All
   non-real CTAs route to the parameterized `coming-soon`
   stub.
6. **Build the descriptor reveal with Copy.** Privacy-first
   reveal (masked at rest, full on tap) + Copy CTA on the
   revealed state + sensitive-screen flag scaffolded for
   Capacitor. Browser is the dev surface. Copy triggers the
   shared "Copied" toast confirmation.
7. **Build the Signing-device-label inline editor.** Free-text
   input bound to `signing_device_label`. Verify the existing
   Holding-update endpoint accepts this field via Swagger /
   the OpenAPI contract; if missing, **stop and surface to
   Rémy** before scoping a backend change (do not silently
   add). On success, the status-card subtitle updates
   immediately.
8. **Build the Forget bottom-sheet modal** with the 5-second
   fill-bar timer + Strongbox body copy. Wire to the backend
   Forget endpoint. **No** NativeBridge.secureStorage.delete
   call (no seed on TK side for Strongbox).
9. **Build the connection-error toast** on
   `system.chain.connection_state_changed` transitions. Reuse
   the Purse-detail-shipped component.
10. **Retrofit Purse descriptor Copy.** Edit the two Purse
    Settings mockups (`Date last touched` bump) + the
    corresponding implementation on the Purse detail Settings
    tab. Add the Copy CTA on the revealed descriptor state.
    Update `UI/mobile.md §Purse detail` Descriptor bullet +
    Behaviors "Descriptor reveal" paragraph in lockstep.
11. **Run `tools/check-spec.ps1`** (Windows) or
    `tools/check-spec.sh` (Linux/Mac). Must pass before
    stage-3 handoff.
12. **Stop and report** per PROCESS.md §4.4 stage 3. No
    OpenAPI regen unless task 7 surfaced a missing PATCH path
    and a backend change landed.

#### Acceptance / done-when — required

- Tapping a Strongbox row on Home navigates to
  `/holding/[id]`; title bar shows the Holding's display
  name; status card shows the iron stripe and the
  `signing_device_label` subtitle (or "External signing
  device" fallback when the label is empty).
- The Operations tab shows the user's chain-side activity for
  this Strongbox, newest-first, with sign-based amount
  colour. Empty Strongboxes render the empty-state panel.
- The Settings tab renders the missing-metadata advisory card
  iff the descriptor's bip32-derivation-origin info was
  absent at parse time. Fix-this CTA routes to coming-soon.
  All other Settings CTAs route correctly (Rename, Edit
  signing-device-label, Add rule → coming-soon, disabled
  Lightning, Forget).
- Descriptor reveal: masked at rest; Show flips to revealed +
  Copy + Hide; tapping Copy puts the descriptor on the
  clipboard with a brief "Copied" toast.
- The Forget bottom-sheet shows the 5-second fill-bar timer;
  Cancel is active immediately; confirming triggers the
  backend Forget call; no NativeBridge.secureStorage.delete
  call fires.
- The Lightning row is rendered greyed and disabled with the
  Strongbox-specific copy; tap surfaces the explanation.
- Disconnecting bitcoind (smoke-test) flips the connection
  dot red and slides the connection-error toast in.
- Purse descriptor reveal now ships with the Copy CTA on
  both Settings mockups + the corresponding screens; the
  `UI/mobile.md §Purse detail` no-Copy language is gone.
- `tools/check-spec.ps1` passes (8 checks): mockup index
  includes the 6 new files; both retrofitted Purse mockup
  mtimes are recent enough to escape the un-flushed-edit
  flag.
- No OpenAPI regen needed (verified: no endpoint, schema,
  SSE topic, error type, or locked-state behaviour changed)
  — unless task 7 surfaced a missing PATCH path, in which
  case the change landed and the regen ran as part of the
  same iteration.

#### Dependencies

- **Design-pass validation by Rémy.** The 6 new mockups and
  the 2 retrofitted Purse mockups must be `Status: validated`
  before the coding agent starts. Per PROCESS.md §2 Design
  agent — mockup status flips at the design-pass greenlight,
  not at coding closeout. The design pass also writes the
  new `## Strongbox detail` section in `UI/mobile.md` and
  performs the small `## Purse detail` no-Copy retrofit.
- **No arbitration blockers.** `seed-backup-disclosure` and
  the wider security-health framing remain open in
  `pre-implementation.md`; the Fix-this CTA routes to a
  coming-soon stub the future Security-health-system
  iteration replaces.
- **Purse detail iteration shipped.** Generalises chrome,
  Forget fill-bar timer, descriptor-reveal pattern (now
  retrofitted with Copy), the SSE plumbing, and the
  connection-error toast component.

#### Verification (Rémy)

- Open each of the 6 new mockups in the browser at 360×800;
  verify chrome consistency with the validated Purse-detail
  mockups, copy correctness, and the missing-metadata
  advisory card placement.
- Open the 2 retrofitted Purse mockups; confirm the Copy CTA
  is present on the revealed descriptor state without
  regressing the rest of the Settings layout.
- Hand-test the running app: tap a Strongbox row on Home,
  exercise both tabs, edit the `signing_device_label` and
  verify the status-card subtitle updates, test the
  descriptor reveal + Copy, test Forget, simulate a bitcoind
  disconnect to surface the toast.
- Test the Purse descriptor reveal in the running app — Copy
  CTA present and copies cleanly.
- Run the project's `.ps1` smoke-test suite. Walk through
  Swagger UI for any touched endpoint (read-only — none
  expected unless task 7 surfaced one).

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight
the agent: appends a condensed entry to `shipped.md`, clears
the active block in this file, runs `tools/check-spec.ps1`,
commits. **No OpenAPI regen** for this iteration unless
task 7 surfaced a missing PATCH path. Full sequence in
`PROCESS.md §4.4` stages 3–5.

-->

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only; everything
else is reference.
