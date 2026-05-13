# Next iteration

The sharpened, fully-detailed scope of work the coding agent is
working on (or about to start). Updated in lockstep with the canonical
specs whenever the spec evolves.

When this iteration completes:
- Items shipped → removed from this file
- Canonical specs already reflect the target (no extra "merge" work)
- One item from `future_iterations.md` is promoted, sharpened, and
  becomes the new "Next iteration"

If you're a coding agent reading this: this file is your scope. Other
docs in `specs/` are reference; this file is the assignment.

---

## Iteration template

Use this shape when sharpening an iteration. Sections marked (required)
must be filled before the iteration is given to a coding agent.

### Iteration: <short name>

**Started:** YYYY-MM
**Goal:** <single sentence — what we want to be true at the end>

#### Scope (in) — required

<bullet list of features / changes — sharp, small, fully detailed.
Each item references the canonical doc(s) and mockup file(s) that
define it. The coding agent should not need to invent anything from
this list.>

#### Scope (out) — required

<things considered for this iteration and explicitly cut. Prevents
scope creep.>

#### Affected canonical docs

<list of canonical spec files this iteration touches. Already updated
to reflect target before iteration starts.>

#### Affected mockups

<list of validated mockup files referenced by the iteration.>

#### Tasks — required

<concrete, ordered tasks for the coding agent. Each task should map to
a definition-of-done.>

#### Acceptance / done-when — required

<observable conditions: this curl returns this; this screen matches
this mockup at this viewport; this gauntlet step passes.>

#### Dependencies

<what blocks this iteration: pre-implementation items needing
arbitration, prior iterations not yet shipped, third-party things.>

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
removes shipped scope items from this file, runs
`tools/check-spec.ps1`, commits. Full sequence in
`PROCESS.md §2.7` stages 3–5.

---

## Shipped 2026-05-12 (closeout after Rémy greenlight on 2026-05-12)

### Iteration: Onboarding + Daily Unlock + Home (empty)

Backend: auth layer — device-credential pairing handshake
(`POST /api/v1/pairing/issue`, `POST /api/v1/pairing/redeem`),
passphrase-validate (`POST /api/v1/auth/passphrase-validate`),
device revocation (`DELETE /api/v1/devices/{id}`), auth middleware
(all endpoints except health / pairing / server-info), server-info
endpoint, `paired_device` Alembic migration, and a new
`principles_acknowledged_at` field on the user profile (synced
from the phone immediately after pairing). Unit + integration tests
for all of the above.

Frontend: NativeBridge with `secureStorage` (soft-fallback stub,
no DevGate) and `preferenceStorage` (no-DevGate bridge, Capacitor-
ready); `/onboarding/connect`, `/onboarding/paired` (4-state machine),
`/unlock` (biometric + passphrase fallback), `/home` (empty), root
redirect. Principles acknowledgment persisted via `preferenceStorage`
pre-pairing then synced to backend on successful redeem.

Brand: wordmark-icony viewBox v1 → v2 (tightened from 460 to 450),
source SVG and all five affected mockups updated.

Closeout: `api/openapi.yaml` regenerated from running backend,
`tools/check-spec.ps1` created and passing (6 checks), smoke-test
updated throughout with device-credential auth headers and a
principles-acknowledgment section.

---

## Shipped 2026-05-13 (closeout after Rémy greenlight on 2026-05-13)

### Iteration: Add Holding scaffolding (picker + populated home + backend + Account stub)

Backend: `POST /api/v1/descriptors/validate` (pure parser — xpub,
BIP 380 wpkh / tr / sh-wpkh, multisig variants; single-address
inputs return typed `SINGLE_ADDRESS_INPUT` rejection). Vault
multisig enforcement: `create_vault` validates descriptors and
rejects non-multisig with a typed error. `GET /api/v1/holdings/summary/global`
extended with `meta` (provider display name for Account,
signing-device label for Strongbox, "N-of-M multisig" for Vault),
`scan_status` ("n/a" / "scanning" / "scanned"), and custody-tier
sort (Account → Purse → Strongbox → Vault). Integration tests:
validate endpoint (five cases — p2wpkh, p2tr, wsh multisig, bare
address rejection, garbage rejection), vault single-key rejection.
Smoke test sections 13b (validate happy + error paths) and 13c
(global summary meta/scan_status).

Frontend: `HoldingIcon.svelte` — single source of truth for all
four holding-type SVGs, accepts `type` + `size` props (replaces
the duplicated inline-SVG pattern that caused vault icon drift).
`AddHoldingSheet.svelte` — bottom-sheet picker, four rows in
custody-progression order, cancel pinned above nav bar (z-index
above fixed BottomNav). `/holding/new/[type]/+page.svelte` —
coming-soon stub parameterized by type. `home/+page.svelte` —
populated Holdings list, hero balance sum, picker wiring via
`?sheet=add` URL param. `BottomNav` active indicator: 2 px
verdigris top stripe + semibold + primary-strong color per
validated mockups. `clipboard.paste()` added to NativeBridge.

Closeout: `api/openapi.yaml` regenerated from running backend
(5182 lines). `tools/check-spec.ps1` passing (6 checks). Picker
subtitle and cancel-button style updated to match 2026-05-13
mockup revision.

---

## Active iteration

### Iteration: Add Holding — Purse wizard

**Started:** 2026-05 · Promoted from `future_iterations.md`
2026-05-13 after Rémy greenlight on the design pass.
**Goal:** Ship the Purse-creation wizard end-to-end — both
watch-only descriptor import (mode 1) and TallyKeep-managed
seed generation (mode 3) — plus the shared wizard-shell
component that Strongbox and Vault wizards will inherit.

#### Scope (in) — required

**Shared wizard-shell component (first consumer is this
iteration; Strongbox + Vault iterations reuse).** A reusable
Svelte component encapsulating:

- Header: 3-cell grid `[back chevron 44 px] [step counter
  centered] [empty 44 px]`. Step counter format
  "STEP X OF Y" in small caps (`font-size-xs`,
  `--color-text-muted`, letter-spacing 0.08em). Back chevron
  behavior parameterised per step (step 1 → Home, step N+ →
  step N−1, success step hides the chevron).
- Body: scrollable region, default padding `var(--space-5)
  var(--space-4)`, slot for per-step content.
- Footer: pinned to the bottom of the screen. Optional error
  region (conditional render) above a full-width primary CTA.
  CTA label, enabled-state, and click handler all parameterised
  by the consumer step.
- Bottom-nav HIDDEN during the wizard (banking pattern: Wise
  add-recipient, Revolut add-account, N26 add-payee). Visible
  again after the user lands back on Home via "Done".
- **`sensitive-screen` prop** (boolean). Browser implementation:
  no-op (the DEV MODE banner is the honest signal). Capacitor
  implementation lands in the Capacitor-wrap iteration —
  Android wires to `FLAG_SECURE` on the activity window, iOS
  wires to `UIApplication.userDidTakeScreenshotNotification`
  for post-hoc detection-warning. Ship the prop with a
  `// TODO(capacitor-wrap)` comment so the grep-audit catches it.

Component lives at `frontend/src/lib/components/wizard/` (or
equivalent path per the existing project structure). Strongbox
and Vault wizards import the same component verbatim — their
iterations only ship per-type content and copy.

**BIP39 mnemonic generation utility.** Pure JS, audited
MIT-compatible library — no remote calls during generation.
Returns `{ mnemonic: string[12], descriptor: string }` where
the descriptor is the derived BIP84 native-SegWit output
descriptor (`wpkh([fingerprint/84h/0h/0h]xpub.../<0;1>/*)`)
for the user's chosen account index (default 0). Candidate
libraries the coding agent evaluates: `@scure/bip39` +
`@scure/bip32` (Paul Miller, audited, ESM-first), `bip39-light`
(thin BIP39-only, no BIP32). Coding agent picks one with
justification noted in the iteration's commit message.

**Step 1 entry surface — `/holding/new/purse`.** Matches
`UI/mockups/mobile_add_holding_purse_input.html`:

- Heading "Add a Purse" (no sub-copy).
- **Generate accent card at top** — verdigris-tinted
  (`--color-primary-soft` bg, `--color-primary` 1.5 px border),
  sparkle SVG icon left, "Let TallyKeep generate a fresh Purse"
  / "Privately and securely stored on this device", chevron
  right. Tap → routes to `/holding/new/purse/generate`.
- **"— or —" separator** with horizontal rules.
- **"Import from another wallet" section header** (small caps
  label).
- **Source dropdown** (optional, alphabetical): BlueWallet ·
  Electrum · Mutiny · Nunchuk · Phoenix · Sparrow · Specter ·
  Other · Don't specify. Default "Don't specify".
- **Wallet-tips inline banner** appears below the dropdown
  when a source is picked. Copy locked in `UI/mobile.md`
  §"Wallet-specific tips — surfaced inline when a source is
  picked". Banner uses `--color-info-soft`/`-border`/`-text-on-soft`.
- **Descriptor textarea** with monospace font, min-height
  120 px, "Paste" button in top-right consuming
  `NativeBridge.clipboard.paste()` (shipped in scaffolding).
- Primary CTA "Continue" disabled until textarea contains at
  least one non-whitespace character.
- On Continue: call `POST /api/v1/descriptors/validate` with
  the pasted text. On success → navigate to step 2 carrying
  the parsed metadata + the source pick (drives auto-name).
  On typed error → render the appropriate error state below.

**Step 1 error states — same screen, different footer content.**

- **Inline error (single-address rejection)** — matches
  `UI/mockups/mobile_add_holding_purse_input_error_inline.html`.
  Backend response: `SINGLE_ADDRESS_INPUT` typed error. Footer
  renders `wizard-error` block above the CTA (danger palette,
  warning circle icon, two-line copy "That's a single Bitcoin
  address." / "TallyKeep tracks wallets, not isolated
  addresses…"). Textarea border tinted danger. CTA remains
  enabled (user can edit and retry). Same pattern reused for
  unparseable input (`UNPARSEABLE_DESCRIPTOR` typed error) and
  duplicate-descriptor (`DUPLICATE_DESCRIPTOR` typed error —
  this error variant additionally renders an "Open this Purse"
  link inside the error block, navigating to the existing
  Holding's detail page).
- **Redirect error (multisig rejection)** — matches
  `UI/mockups/mobile_add_holding_purse_input_error_redirect.html`.
  Backend response: `is_multisig: true` on the validate
  response. Footer renders a `wizard-error redirect` block
  (warning palette, triangle-warning icon) with a "Set up as
  Vault" secondary CTA that navigates to `/holding/new/vault`
  (currently the coming-soon stub; future Vault iteration
  swaps in the real wizard). Primary "Continue" disabled
  (greyed) — the descriptor as pasted will not parse as a
  Purse.

**Step 1 alt path (Generate) — two screens.**

- `/holding/new/purse/generate` (pre-reveal) — matches
  `UI/mockups/mobile_add_holding_purse_generate.html`.
  On mount: call the BIP39 generation utility, persist the
  mnemonic via `NativeBridge.secureStorage` under the key
  `purse-pending-mnemonic-<sessionId>` (Capacitor: real
  Keychain/Keystore; browser dev-mode: `localStorage` stub
  per ADR-0007). DEV MODE banner renders in browser only,
  suppressed in Capacitor builds. Pre-reveal body: heading
  "Your new Purse is ready", sub-copy, a centered accent
  button "Reveal my recovery phrase" inside a hatched-pattern
  vault area. Below: loss-of-funds warning block (visible
  regardless of reveal), later-note "You can also reveal them
  later from Holdings → Purse → Information". CTA "Continue"
  always enabled — reveal is optional. `sensitive-screen={true}`.
- `/holding/new/purse/generate?revealed=true` (revealed state)
  — matches
  `UI/mockups/mobile_add_holding_purse_generate_revealed.html`.
  Triggered when user taps Reveal on the pre-reveal screen.
  Body: heading "Your recovery phrase", sub-copy, seed-card
  with a 3×4 numbered grid of the 12 words (monospace, tabular
  spacing) plus a "Hide" affordance top-right of the card. Same
  warning + later-note as pre-reveal. No Copy button — the user
  can manually select text but we do not surface the affordance
  (clipboard is a known seed-leak vector). CTA "Continue"
  always enabled. `sensitive-screen={true}`.

Back-chevron behavior on both generate screens: returns to the
default step 1 (Import path) — NOT to Home. The user can switch
back to descriptor paste from there.

**Step 2 — `/holding/new/purse/review`.** Matches
`UI/mockups/mobile_add_holding_purse_parseback.html`. Step
counter "STEP 2 OF 3".

- Heading: "Here's what we read" (mode 1) / "Here's what we
  generated for you" (mode 3).
- **Auto-name preview row at the top** (under the heading).
  Carries the 4 px brass-purse left stripe. Reads "Will be
  named '{auto-name}' [Rename]". Tap "Rename" to edit inline
  (the value becomes a focused text input; commit on Enter or
  blur). Auto-name derivation:
    - Mode 1 + source picked: `"{Source} Purse"` (e.g.
      "Phoenix Purse"). Source label from the dropdown's
      selected option's display text.
    - Mode 1 + source = "Don't specify": script-type label
      ("Native SegWit Purse" for P2WPKH, "Taproot Purse" for
      P2TR, "Compatibility SegWit Purse" for P2SH-P2WPKH).
    - Mode 3 (generated): `"TallyKeep Purse"`. Collision-
      incrementer: if a Purse with that name already exists,
      append " 2", " 3", etc.
- **Parse-card** (below the name preview, NO left stripe):
  three rows — Script type · Derivation · Master key
  (truncated to first 6 + last 5 chars with ellipsis).
- **Addresses-card**: card title "First three addresses", sub
  "Open your other wallet (Sparrow, Electrum, BlueWallet…)
  and confirm these match its first three receive addresses."
  Three monospaced rows numbered 0/1/2, each with a tap-to-copy
  icon button on the right. Toast or icon-flash on copy.
- CTA "Looks right" — calls `POST /api/v1/holdings/purse` with
  `{ descriptor, name, source, seed_origin }`. On success →
  navigate to step 3. On failure → render error state (see
  below).

**Step 2 error state.** Backend creation failure (network,
duplicate-on-create race, internal): footer renders
`wizard-error` block "Couldn't add the Purse. Try again." with
a retry-on-tap on the primary CTA.

**Step 3 success — two variants.**

- `/holding/new/purse/success?mode=imported` — matches
  `UI/mockups/mobile_add_holding_purse_success_imported.html`.
  Centered layout, green success indicator
  (`.success-indicator.lg`), heading "Purse added", sub-copy
  about the chain scan, scan-status row with a spinner
  ("Scanning… · balance will appear on Home shortly"). CTA
  "Done" → navigate to `/home`. The new Purse row on Home
  shows the "Scanning…" status indicator until the backend
  scan job completes; row updates to show balance when scan
  finishes. No auto-redirect.
- `/holding/new/purse/success?mode=generated` — matches
  `UI/mockups/mobile_add_holding_purse_success_generated.html`.
  Same centered shell, heading "Purse ready", sub-copy about
  the fresh wallet, "0 sats · fresh wallet" pill, a disabled
  "Show a receive address" secondary CTA with a "next
  iteration" hint. CTA "Done" → navigate to `/home`.

**Vocabulary lock (PROCESS §2.8).** User-facing copy uses
**"recovery phrase"** for the 12 BIP39 words, **"keys"** for
the abstract signing capability. The string "seed phrase"
must not appear in any user-visible string. Internal
identifiers (CSS class names like `seed-vault`, technical
comments, the DEV MODE banner if needed) are unaffected. Add
a lint rule or grep-check to the frontend CI if straightforward.

#### Scope (out) — required

- **Mode 2 (`EXTERNAL_IMPORTED`)** — the seed-import "upgrade
  to spending" path lives on Purse Detail in a follow-up
  iteration once `purse-upgrade-path` resolves in
  `pre-implementation.md`. Not part of this wizard.
- **Backup-verification quiz** (word-by-word "type back word 3,
  7, 11" confirmation). Ships at the private-ship gate as part
  of the security-health system per `seed-backup-disclosure`.
- **"Show a receive address" affordance on the generated
  success screen.** Lands enabled when the Receive iteration
  ships. In this iteration the button is rendered disabled
  with the "next iteration" hint to signal forward direction.
- **Gap-limit / "scan more addresses" tooling.** Belongs in
  Holding Detail → Settings → Scan, scoped out of the wizard.
- **QR-scan as descriptor input.** Capacitor-only, deferred.
- **Per-wallet QR import paths** (e.g. BlueWallet → QR scan
  instead of paste when that chip is selected). Capacitor-wrap
  iteration adds this; current iteration uses paste-only.
- **Cancel / X in the wizard header.** Back-chevron alone
  handles navigation in this iteration. Add the X only if
  dev-phase usage surfaces a friction.
- **Strongbox + Vault wizard implementations.** Each is its
  own iteration; both inherit the shared wizard-shell shipped
  here.

#### Affected canonical docs

- `UI/mobile.md` — "Add Holding — Purse wizard" section is
  already written and locked from the 2026-05-13 design pass.
  Coding agent reads but does not edit.
- `UI/mockups/index.html` — already lists all 8 mockups with
  `status: 'validated'`.

No backend canonical doc edits expected — the API surface
(`/api/v1/descriptors/validate`, `/api/v1/holdings/purse`)
already ships from the scaffolding iteration. The coding agent
verifies behavior matches the wizard's needs; if extensions are
required (see Backend confirmation tasks below), they land in
this iteration's scope alongside an `api/openapi.yaml`
regeneration at closeout.

#### Affected mockups

All 8 validated (Rémy greenlight 2026-05-13):

- `mobile_add_holding_purse_input.html`
- `mobile_add_holding_purse_input_error_inline.html`
- `mobile_add_holding_purse_input_error_redirect.html`
- `mobile_add_holding_purse_generate.html`
- `mobile_add_holding_purse_generate_revealed.html`
- `mobile_add_holding_purse_parseback.html`
- `mobile_add_holding_purse_success_imported.html`
- `mobile_add_holding_purse_success_generated.html`

Plus the shell convention is documented in `UI/mobile.md`
§"Wizard shell (introduced here, reused by Strongbox and
Vault)".

#### Tasks — required

Ordered. Each maps to an observable definition-of-done.

**Backend confirmation pass (do this first — may surface
extensions that need to ship in this iteration):**

1. **Confirm miniscript handling on
   `POST /api/v1/descriptors/validate`.** Test payloads:
   - Phoenix-shape swap-in legacy descriptor
     `wsh(and_v(v:pk([36550033/52h/0h/0h]xpub...),older(...)))`.
   - Phoenix-shape Taproot swap-in `tr(e4c2...)`.
   - If the endpoint can't parse miniscript fragments, return
     a typed `UNSUPPORTED_DESCRIPTOR_SHAPE` error mapping to
     the user-facing "Use the Wallet final key instead" hint
     in the wallet-tips banner. Plain xpubs/zpubs and standard
     BIP 380 descriptors (`wpkh`, `tr`, `sh-wpkh`,
     `wsh(multi(...))`) must continue to parse cleanly.
   - Done-when: integration test added covering each shape;
     a typed error fires on shapes we can't parse rather than
     a 500.

2. **Confirm `POST /api/v1/holdings/purse` accepts the
   `seed_origin=TALLYKEEP_MANAGED` variant.** The scaffolding
   iteration shipped this endpoint for `EXTERNAL_WATCH_ONLY`;
   verify the schema accepts the managed variant and that the
   `seed_origin` field persists correctly. Extend if needed.
   Done-when: integration test creates a Purse with each
   `seed_origin` value and verifies the persisted Holding.

3. **Confirm duplicate-descriptor detection.** When a user
   tries to create a Purse from a descriptor that already
   exists in their TallyKeep, the backend must return a typed
   `DUPLICATE_DESCRIPTOR` error with the existing Holding's id
   in the error payload (so the frontend can render the "Open
   it instead" link). Add the check if missing.
   Done-when: integration test creates a Purse twice with the
   same descriptor; second attempt returns the typed error
   with the existing Holding id.

**Shared wizard-shell component:**

4. Implement `<WizardShell>` component with the prop API
   spelled out in Scope (in). Stories or test pages for each
   prop combination. The component handles header + footer
   layout; consumer slots in body content + step-specific
   header values (step counter text, back behavior, sensitive-
   screen flag) + footer values (error region content, CTA
   label, CTA disabled-state, CTA onClick).
   Done-when: component renders cleanly at 360×800 in Chrome
   + Samsung Internet + Safari mobile; bottom-nav is hidden;
   sensitive-screen prop has the `// TODO(capacitor-wrap)`
   comment in place.

**BIP39 generation utility:**

5. Pick a BIP39 library (constraint: audited, MIT-compatible,
   no remote calls). Justify the pick in the commit message.
   Implement `generateMnemonic()` returning the 12-word array
   + the BIP84-derived descriptor for account 0.
   Done-when: unit tests verify the generated mnemonic
   round-trips through the library (mnemonic → seed →
   descriptor → re-parse via descriptors/validate succeeds);
   tests assert no network calls are made during generation.

**Step 1 routes (Import path):**

6. Implement `/holding/new/purse` (default Import view) per
   `mobile_add_holding_purse_input.html`. Source dropdown,
   wallet-tips banner conditional on dropdown selection,
   descriptor textarea, Paste button, Generate accent card.
   Done-when: screen renders pixel-faithful to the mockup at
   360×800 across the three target browsers; Paste button
   pulls from `NativeBridge.clipboard.paste()`; Continue is
   disabled when textarea is empty/whitespace-only; selecting
   a source surfaces the wallet-tips banner with locked copy.

7. Implement Step 1 error states (inline + redirect) per the
   two error mockups.
   Done-when: each typed error from
   `POST /api/v1/descriptors/validate` renders the correct
   error variant; "Open it instead" link on duplicate-error
   navigates to the existing Holding's detail page; "Set up
   as Vault" CTA on multisig-error navigates to
   `/holding/new/vault` (currently the stub).

**Step 1 alt path (Generate):**

8. Implement `/holding/new/purse/generate` (pre-reveal) per
   `mobile_add_holding_purse_generate.html`. On mount, call
   the BIP39 utility, persist via
   `NativeBridge.secureStorage`, render the pre-reveal layout.
   DEV MODE banner conditional on `import.meta.env.MODE` or
   equivalent — browser dev/prod shows the banner; Capacitor
   build suppresses it.
   Done-when: screen matches mockup; warning + later-note are
   visible regardless of reveal state; CTA "Continue" is
   always enabled; `sensitive-screen={true}` is passed to
   `<WizardShell>`.

9. Implement the revealed state per
   `mobile_add_holding_purse_generate_revealed.html`. Tap
   Reveal → render the 3×4 word grid + Hide affordance. Tap
   Hide → return to pre-reveal layout. No Copy button.
   Done-when: words render in tabular monospace; Hide returns
   to pre-reveal cleanly; manual text selection still works
   (we don't disable user-select); no Copy affordance exists
   in the DOM.

**Step 2 route (Parse-back):**

10. Implement `/holding/new/purse/review` per
    `mobile_add_holding_purse_parseback.html`. Auto-name
    preview at the top, brass-purse stripe, inline Rename.
    Parse-card + addresses-card below. Tap-to-copy on
    addresses. CTA "Looks right" calls
    `POST /api/v1/holdings/purse` with the assembled
    payload.
    Done-when: auto-name derives per the rules in Scope (in);
    rename inline-edit commits on Enter or blur; addresses
    copy to clipboard on tap with visible feedback; CTA
    transitions to step 3 on success; CTA renders the inline
    error on `HOLDING_CREATE_FAILED` and allows retry.

**Step 3 success route:**

11. Implement `/holding/new/purse/success` with the two mode
    variants per the success mockups. Returns to `/home` on
    Done. The Home page's populated state already renders the
    "Scanning…" status indicator on rows with
    `scan_status: 'scanning'`.
    Done-when: both variants match their mockups; Done button
    navigates to `/home` and the new Purse row is visible
    (mode 1 with scanning indicator; mode 3 with the row but
    0-sat balance).

**Wizard state management:**

12. Implement a Svelte store (or context per the project's
    existing state-management pattern) for the wizard's
    in-flight state: pasted descriptor, validate response,
    source pick, generated mnemonic + derived descriptor,
    auto-name + rename override, sensitive-screen flag. Back
    navigation must preserve state — tapping back from step 2
    returns the user to step 1 with the textarea pre-filled.
    Done-when: hand-test verifies state survives back/forward
    navigation in both modes; closing the wizard (tapping back
    on step 1 → Home) clears the state.

**Testing:**

13. Frontend tests for the wizard happy paths (mode 1 + mode 3)
    + each error state. Pattern follows existing frontend test
    convention in the project.

14. Smoke-test `.ps1` additions: end-to-end Purse creation via
    the wizard (Playwright-style if the project supports it,
    or a manual checklist in the smoke-test markdown). Cover
    both modes, all three error states, and the back-navigation
    state preservation.

**Vocabulary discipline:**

15. Grep audit before commit — no "seed phrase" / "seedphrase"
    in user-facing strings. Internal CSS class names (e.g.
    `seed-vault`) are exempt.

#### Acceptance / done-when — required

Observable conditions for the stage-3 handoff:

- **All 8 mockups render pixel-faithful at 360×800** in
  Chrome, Samsung Internet, and Safari mobile. Smoke at
  384×854 and 412×900 per PROCESS §5.
- **Mode 1 happy path** end-to-end: from Home, tap `+` →
  picker → Purse tile → step 1 → paste a valid descriptor
  (e.g. the BIP 380 test vectors) → Continue → step 2 shows
  parse-back with auto-name "Native SegWit Purse" (no source)
  or `"{Source} Purse"` (source picked) → Rename works inline
  → Looks right → step 3 imported success → Done → Home
  shows the new Purse row with "Scanning…" indicator.
- **Mode 3 happy path** end-to-end: from Home, tap `+` →
  picker → Purse tile → step 1 → tap Generate accent card →
  step 1 generate pre-reveal renders → tap Reveal → 12 words
  shown → tap Continue → step 2 parse-back shows the
  generated descriptor's derivation with auto-name "TallyKeep
  Purse" → Looks right → step 3 generated success → Done →
  Home shows the new Purse row at 0 sats.
- **Single-address rejection** renders the inline-error
  variant in the footer; CTA stays enabled for retry.
- **Multisig rejection** renders the redirect-error variant;
  "Set up as Vault" CTA navigates to `/holding/new/vault`
  (the stub for now).
- **Duplicate-descriptor rejection** renders the inline error
  with the "Open it instead" link, which navigates to the
  existing Holding's detail page.
- **Back navigation preserves wizard state** — typing in the
  textarea, navigating forward to step 2, then back to step
  1, finds the textarea content intact.
- **DEV MODE banner visible in browser builds, suppressed in
  Capacitor** (verifiable via build flag).
- **`sensitive-screen` prop wired** on the two generate
  screens; component carries the `// TODO(capacitor-wrap)`
  comment.
- **Vocabulary lock holds** — `grep -ri "seed phrase"` across
  `frontend/src/` returns no user-facing matches.
- **Backend confirmation tasks complete** — `descriptors/
  validate` handles miniscript shapes correctly (parse or
  typed error), `holdings/purse` accepts both `seed_origin`
  variants, duplicate-descriptor returns the typed error
  with the existing Holding id.
- **`tools/check-spec.ps1` / `.sh` passes** (already 6/6 ok;
  must remain so).
- **Smoke-test `.ps1` suite passes** end-to-end against the
  running backend with the new Purse-creation sections.

#### Dependencies

None blocking.

- **`seed-backup-disclosure`** (open) — does NOT block. This
  iteration ships the dev-phase placeholder (privacy-first
  reveal + visible warning + forward-reference to Holdings →
  Purse → Information, no hard backup-ack gate). The full
  security-health system lands at the private-ship gate
  iteration.
- **`purse-upgrade-path`** (open, drafted 2026-05-13) — does
  NOT block. The mode-2 seed-import upgrade flow is a Purse-
  Detail feature scheduled post-resolution. This iteration's
  wizard architecture is extensible to it but does not
  implement it.
- **`browser-pwa-auth-model`** (open) — does NOT block. The
  `secureStorage` localStorage soft-fallback continues to
  carry the browser-build session.

#### Verification (Rémy)

After the agent's stage-3 "ready for verification" handoff:

- Run the project's `.ps1` smoke-test suite against the
  running backend. New Purse-creation sections (mode 1 +
  mode 3 + each error variant) should pass.
- Swagger UI walk-through of the descriptors/validate +
  holdings/purse endpoints — verify any extensions
  (miniscript handling, duplicate detection) behave per the
  spec.
- Hand-test the wizard end-to-end in the browser at 360×800
  in Chrome and Samsung Internet, smoke at 384×854 and
  412×900. Cover both modes, all error states, back-nav
  state preservation.
- Verify auto-name behavior across source picks (Phoenix,
  BlueWallet, Don't specify) and across script types
  (P2WPKH, P2TR descriptors as input).
- Verify the DEV MODE banner is visible in the browser dev
  build but suppressed in the production build (if both are
  buildable in dev phase).
- Visual review against `UI/mockups/_shared/tokens.css` —
  confirm no raw hex values in components, all colors and
  spacing flow through tokens (PROCESS §2.4 consumer
  discipline).

#### Closeout

Standard per `PROCESS.md §2.7` stages 3–5. After Rémy
greenlight:

- Regenerate `api/openapi.yaml` from the running backend if
  any API surface changed (parser-scope extensions, duplicate
  detection, etc.).
- Edit this iteration block to mark shipped + record commit
  reference (move under a `## Shipped <date>` section
  matching the prior iterations' pattern).
- Mark the 8 validated Purse-wizard mockups referenced from
  the `UI/mobile.md` Purse-wizard section as no-change (the
  section is already written; just verify the references
  resolve and the date is current).
- Run `tools/check-spec.ps1` (or `.sh`). Must pass.
- Commit closeout in a single change. Commit message
  references the iteration name and the validation context
  ("closeout after Rémy greenlight on YYYY-MM-DD").

On closeout, the next iteration to promote from
`future_iterations.md` is **"Add Holding — Strongbox
wizard"** — copy + framing variant on the Purse pattern,
reuses the shared wizard-shell shipped here. Picker order
guides the lineup: Strongbox second, Vault third, Account
fourth (different surface — ccxt provider integration, no
descriptor parser).

---

## Iteration roadmap (rough sketch — not commitment)

For Rémy's mental model, not for the coding agent. Sequence and
scope will adjust as we learn. The roadmap targets the public-ship
event (per ADR-0003); private-ship is reached when the relevant
mobile UI iterations are stable enough and the Capacitor + auth +
security-health work lands.

### Pre-shipping iterations

**Mobile UI design and dev-phase build:**
1. **Onboarding + Home (empty + populated states)** — first-touch
   flow plus landing
2. **Add Holding** — chooser + four type-specific flows
3. **Holding Detail** — per-type detail pages
4. **Send + Receive** — per Holding type, including PSBT roundtrip
   for Strongbox and native sign for TallyKeep-managed Purse on the
   device that holds the seed
5. **Activity + Categorization** — cross-Holding feed plus
   per-Holding categorization
6. **Sweep Policy + Trading view** — Account-originated sweeps in
   the dev-phase scope
7. **Settings** — including the security-health system at least
   for seed-backup warnings (private-ship gate)

**Private-ship gate:**
- Capacitor wrap + native plugins
- Authentication layer
- Security-health (seed-backup recovery flow per pre-implementation item `seed-backup-disclosure`)
- Self-review

**Pre-public-ship enhancements** (in personal-use phase, before
public-ship):
- Iterations driven by Rémy's own daily-use feedback
- Possible candidates: settlement-rails confirmation probability,
  "tap to see under the hood" UI spine, others (see
  `future_iterations.md`)

### Public-ship event (ship-gate work bundle)

See `future_iterations.md` "Ship-gate meta-iteration" entry. Bundles
native signing, reproducible builds, app stores, F-Droid, brand,
third-party audit, and (optionally) hosted-tier launch.

### Post-shipping

Feature updates per `future_iterations.md` post-shipping entries
(Blueprint, Lightning, DCA, equity-reference, etc., depending on
user feedback and roadmap priorities).
