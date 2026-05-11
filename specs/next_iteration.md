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

## Active iteration

### Iteration: Onboarding + Daily Unlock + Home (empty)

**Started:** 2026-05

**Goal:** A user with a TallyKeep server running somewhere can
pair their phone via QR or manual URL, choose biometric or
passphrase unlock, and land on a working empty Home — backed by a
new auth layer (device credentials + passphrase-validate
endpoint) that ends the dev-phase no-auth posture.

#### Scope (in) — required

**Backend — auth layer (private-ship gate per ADR-0003):**

- *`server_label` field* in `configuration.toml` per
  `01_architecture.md` §"Configuration model". Optional; operator
  sets it at stack deployment; surfaced to clients on pairing.
  Exposed via `GET /api/v1/server/info` (or equivalent) so the
  phone can render "Connected to: <label>" on the paired-confirm
  screen.
- *Pairing handshake* per `pre-implementation.md`
  `pairing-handshake-crypto` (leading direction: plain endpoint
  URL + single-use ephemeral token, ~60 s TTL, single-use,
  rate-limited):
  - `POST /api/v1/pairing/issue` — server-side, generates a
    one-time pairing token + endpoint payload. (Dev-phase: a CLI
    or test helper triggers issuance; the desktop "Add device"
    UI that calls this lands in a later iteration.)
  - `POST /api/v1/pairing/redeem` — phone-side, accepts the
    token, validates (TTL, single-use, not-already-redeemed),
    issues a long-lived device credential. Rate-limited.
- *Device-credential store* — new `paired_device` table
  (Alembic migration): id, credential_hash, label_optional,
  created_at, last_seen_at, revoked_at. Argon2id of the
  credential on the wire compared against stored hash; raw
  credential never stored. Server emits the credential once on
  successful redemption; phone stores it via
  `NativeBridge.secureStorage`.
- *Passphrase-validate endpoint* per ADR-0008:
  - `POST /api/v1/auth/passphrase-validate` — accepts a
    passphrase candidate, compares Argon2id of input against the
    server's existing passphrase-derived key. Never stores or
    logs the raw passphrase. Rate-limited (exact threshold +
    backoff policy sharpens during impl).
- *Auth middleware* — every API endpoint that previously had no
  auth now requires a valid device credential
  (`Authorization: Bearer <credential>` or equivalent). 401 on
  missing/invalid. Exempt: pairing endpoints, `server/info`,
  health endpoint. Per `01_architecture.md` §"Network security
  posture" — this iteration ends the "no auth on the API in the
  dev phase" relaxation.
- *Device revocation* — `DELETE /api/v1/devices/{credential_id}`.
  Marks the credential revoked; subsequent requests with that
  credential return 401. (Desktop UI to call this lands later.)
- Unit + integration tests for all of the above.

**Frontend (SvelteKit, browser-dev per ADR-0007):**

- *`NativeBridge` interface* with browser-dev stubs:
  - `scanQR()` — browser-dev: visible "this build cannot scan —
    Capacitor needed" gate banner; user falls back to manual URL
    entry. Capacitor impl lands at private-ship.
  - `secureStorage.{set, get, delete}(key)` — browser-dev:
    `localStorage` with a visible dev-mode warning that real
    builds use Keychain/Keystore.
  - `biometric.canUseBiometric()` — browser-dev: returns `false`
    by default (rendering the no-biometric variant of Onboarding
    02). A query string or toggle can override for visual
    testing.
  - `biometric.unlock()` — browser-dev: stubbed return.
- *Onboarding 01 — Connect.* Translate
  `mobile_onboarding_01_connect.html` → SvelteKit route
  `/onboarding/connect`. Manual URL entry posts to
  `/api/v1/pairing/redeem`. QR scan stubbed in browser-dev.
  Principles card with `[I understand]` acknowledgment
  (persist user pref). "Don't have a TallyKeep yet?" ghost CTA
  opens external docs link in a new tab. If user skips past
  without acknowledging the principles, the unacknowledged-
  state persists for the Security-health system to surface
  later (out-of-scope for this iteration — acceptable gap, see
  Dependencies).
- *Onboarding 02 — Paired.* Translate the four mockup variants
  to `/onboarding/paired` with a state machine:
  - On entry, call `canUseBiometric()`. If false → render
    `mobile_onboarding_02_paired_no_biometric.html`. If true →
    render `mobile_onboarding_02_paired.html` (initial).
  - `[Enable biometric]` triggers `biometric.unlock()`. On
    success → render `mobile_onboarding_02_paired_biometric_done.html` →
    `[Continue]` → `/home`.
  - `[Skip — use passphrase only]` → bottom sheet from
    `mobile_onboarding_02_paired_skip_confirm.html`. Cancel → back to initial. Confirm
    "Continue with passphrase only" → flag biometric-not-enabled
    in user prefs → `/home`.
- *Daily Unlock.* Translate the two mockups to `/unlock` with a
  state machine:
  - On app open with credential present → render
    `mobile_unlock_biometric.html`; auto-fire
    `biometric.unlock()`. On success → `/home`. (Skipped if user
    opted out of biometric or `canUseBiometric()` returned
    false — render passphrase variant directly.)
  - "Use passphrase instead" → render
    `mobile_unlock_passphrase.html`. POST input to
    `/api/v1/auth/passphrase-validate`. On OK → `/home`. On NO →
    inline error + retry; after N failures → rate-limit
    feedback.
- *Home (empty).* Translate `mobile_home_empty.html` →
  `/home`. Renders based on Holdings count (0 → empty). Brand
  mark in app bar, balance hero (`0` + `↻` cycle on `sats`),
  subdued "Show in fiat" link, "Holdings" section header with
  outlined `+` button, empty list-card placeholder, bottom nav
  (Home active, Activity/Holdings disabled, More enabled).
- *Honest gates per ADR-0007* — every Capacitor-only capability
  invocation shows a visible "Capacitor needed" gate in
  browser-dev.
- *Stub for next iteration* — the `+` button on Home empty
  no-ops (or opens a placeholder bottom sheet that says "Add
  Holding flow lands in the next iteration"). Full Add-Holding
  picker is out-of-scope (see "Pre-bagged for Add Holding"
  below).

**Brand asset discipline (locked engineering principle per
`PROCESS.md §2.4` "Consumer discipline"):**

The SvelteKit build consumes brand assets via the indirection
layer only — colors, icons, spacing, radii, shadows, type. No
hardcoded values in component files. The structural check: brand
v2 → v3 must propagate by editing source artifacts + tokens, not
by grep-and-replace through components. If a value is needed and
no token exists, add the token (lockstep with the brand lock doc)
— don't invent in component code.

Sources for this iteration:

- *Color tokens:* `UI/mockups/_shared/tokens.css` — the SvelteKit
  build imports / consumes this file directly (no parallel copy).
  Already in sync with `brand/tallykeep_palette_v2_lock.html`
  (the canonical source for color values + rationale). The
  working-surface canvas (`brand/tallykeep_palette_canvas.html`)
  is supplementary — coding agent reads it only if a value or
  rationale is unclear, never consumes from it directly.
- *Icons:* import from `brand/identity/*.svg`. The locked set so
  far includes `icon-canonical.svg`, `icon-solid.svg`,
  `wordmark-plain.svg`, `wordmark-icony.svg`, and the
  Holding-type icons holding-account/purse/strongbox/vault.svg
  (per `brand/README.md` Status table). Wrap in a thin
  `<Icon name="..." />` component so the consumer-side API stays
  stable as the icon set grows.
- *Action / nav / status icons* not yet in `brand/identity/` —
  the bottom-nav icons (home, activity, holdings, more), the `↻`
  cycle, and the `+` add are drawn inline in the mockups. For
  this iteration, the SvelteKit `<Icon>` wrapper component can
  inline these SVG paths internally with a TODO referencing the
  upcoming brand-side icon-set iteration (per `brand/README.md`:
  "next brand work is iconography beyond the brand mark +
  Holding icons"). Consumers still use `<Icon name="home" />`
  syntax. When the brand iteration ships the icons to
  `identity/`, the wrapper swaps to imports with zero
  consumer-side changes.
- *Spacing / radii / shadows / type:* `var(--space-*)`,
  `var(--radius-*)`, `var(--shadow-*)`, `var(--font-*)` from
  `tokens.css`.

**Small lockstep brand-side change in this iteration:**

- Brand v1 → v2 bump for `tallykeep_wordmark_v1_lock.html`:
  tighten the wordmark-icony viewBox at the source so the
  mockup-level override (`viewBox="0 0 450 145"` vs source
  `0 0 460 145`) becomes unnecessary. Regenerate
  `brand/identity/wordmark-icony.svg` in lockstep. Update mockup
  HTML to consume the source viewBox cleanly.
- *Optional* (defer if not blocking): extend §5 of the brand
  mark lock doc to sanction the wordmark-icony embedded Y as a
  dynamic surface alongside the bare canonical icon. The
  dynamic-mark behavior itself is deferred to
  `future_iterations.md` "Dynamic brand mark on first-touch
  surfaces" — for this iteration the wordmark is static. If the
  Connect screen is going to land the dynamic interaction in
  the same iteration as the SvelteKit build, the sanction
  extension lives here; otherwise it lives with the dynamic-
  mark iteration.

#### Scope (out) — required

- Add-Holding picker popup (the `+` button's destination). Next
  iteration: Add Holding.
- Per-Holding-type creation flows (Account / external-watch-only
  Purse / TallyKeep-managed Purse / Strongbox / Vault). Next
  iteration.
- Home populated states (single Holding, multiple Holdings,
  security-discrepancy banner, fiat-on with currency picker
  sheet). Later iteration.
- Send / Receive flows. Later iterations per roadmap.
- Activity / Categorization. Later iteration.
- Sweep Policy / Trading view. Later iteration.
- Settings page. Deferred to its own iteration; "More" tab can
  navigate to a placeholder or no-op.
- Security health zone on Home (its own pre-shipping iteration
  per `future_iterations.md` "Security-health system"). The
  unacknowledged-principles flow has a known gap here until
  that iteration ships — acceptable for personal-use phase.
- Dynamic brand mark interaction on Connect (deferred to
  `future_iterations.md` "Dynamic brand mark on first-touch
  surfaces"). Mockup wordmark stays static for this iteration.
- Hosted-tier onboarding screens (signup, backup-credentials
  acknowledgment, modified deep-recovery copy). All post-public-
  ship per `future_iterations.md` "Hosted tier infrastructure".
- Multi-server per single client. Post-public-ship per
  `future_iterations.md` "Multi-server per single client".
- Capacitor wrap, native plugins, app-store distribution.
  Separate private-ship-gate iteration after this one (per
  `future_iterations.md` "Capacitor mobile wrapper").
- Lightning. Deferred per spec module 08.
- Currency picker sheet for "Show in fiat". Deferred unless it
  surfaces naturally during Home implementation.
- Desktop UI for the "Paired devices" panel (which calls
  `/api/v1/devices/{id}` for revocation). Backend endpoint
  ships here; UI lands with the desktop iteration.

#### Affected canonical docs

- `01_architecture.md` — `server_label` field already added
  to §"Configuration model"; implementation must match. Auth-
  layer-active state is reflected in §"Network security
  posture" — this iteration ends the no-auth dev-phase
  relaxation.
- `04_api_conventions.md` — auth posture changes from no-auth
  to device-credential-required. Verify cross-cutting
  documentation matches the implementation.
- `10_threat_model.md` — Mobile addendum and auth-related
  sections; verify still consistent with the shipped model.
- `UI/README.md` — flow inventory mentions Onboarding/Home;
  verify nothing drifts.
- `UI/mobile.md` — Onboarding + Daily Unlock + Home (empty)
  sections already detail target state with §3 gauntlet
  answers.
- `decisions/0008-passphrase-and-recovery-model.md` —
  Accepted; implementation must reflect.
- `pre-implementation.md` — `pairing-handshake-crypto`
  remains open with a leading direction. Sharpen specifics
  during impl; ADR if a load-bearing call deviates.
- `PROCESS.md §2.4` "Consumer discipline" — engineering rule
  the coding agent must apply throughout (no hardcoded colors,
  icons via wrapper, single source of truth).
- `brand/tallykeep_palette_v2_lock.html` — canonical color
  source. Read-only for the coding agent (consume via
  `tokens.css`; canvas is supplementary).
- `brand/identity/*.svg` — canonical icon sources. Read-only;
  imported via `<Icon>` wrapper.

#### Affected mockups (all validated 2026-05-10)

- `mobile_onboarding_01_connect.html`
- `mobile_onboarding_02_paired.html`
- `mobile_onboarding_02_paired_biometric_done.html`
- `mobile_onboarding_02_paired_skip_confirm.html`
- `mobile_onboarding_02_paired_no_biometric.html`
- `mobile_unlock_biometric.html`
- `mobile_unlock_passphrase.html`
- `mobile_home_empty.html`

#### Tasks — required

Backend (recommended order: smallest dependencies first):

1. Add `server_label` to `configuration.toml` schema +
   load-from-config + expose via `GET /api/v1/server/info` (or
   reuse existing health/info endpoint if cleaner). Tests.
2. Alembic migration: `paired_device` table.
3. Implement `POST /api/v1/pairing/issue` (server-side token
   emit) and `POST /api/v1/pairing/redeem` (phone-side token
   exchange → credential issuance). Tests.
4. Implement `POST /api/v1/auth/passphrase-validate` per
   ADR-0008. Tests.
5. Implement auth middleware on all previously-unauthed
   endpoints (per `01_architecture.md` §"Network security
   posture"). Tests.
6. Implement `DELETE /api/v1/devices/{credential_id}`
   (revocation). Tests.

Frontend (SvelteKit, after backend endpoints exist):

7. Scaffold `NativeBridge` interface + browser-dev stubs.
8. `/onboarding/connect` from `mobile_onboarding_01_connect.html`.
9. Wire pairing handshake: manual URL → `/api/v1/pairing/redeem`
   → store device credential via `NativeBridge.secureStorage`.
   Persist principles-card ack in user prefs.
10. `/onboarding/paired` state machine (initial / biometric-done
    / skip-confirm / no-biometric). Wire `biometric.unlock()`
    for enable. Bottom sheet for skip-confirm.
11. `/unlock` state machine (biometric default, passphrase
    fallback). Wire `passphrase-validate` POST.
12. `/home` from `mobile_home_empty.html`. Bottom nav. `+`
    button = stub for next iteration. "Show in fiat" link =
    stub.
13. End-to-end smoke test: fresh install → pair manually →
    biometric setup (browser-dev: stub) → unlock → home;
    skipped-biometric path → unlock with passphrase → home.

Brand:

14. Brand v1 → v2 lock-doc bump for the wordmark-icony viewBox.
    Regenerate `brand/identity/wordmark-icony.svg`. Update
    mockup HTML to consume cleanly.

Closeout (per PROCESS.md §2.7 stage 5, only on Rémy's
greenlight after stage-4):

15. Regenerate `api/openapi.yaml`.
16. Run `tools/check-spec.ps1` (or `.sh`) — must pass.
17. Edit this file: remove shipped scope, leave a brief
    `## Shipped <date> (commit ...)` record under the iteration
    block.
18. Commit closeout in a single change. Message references
    iteration name + Rémy-greenlight date.

#### Acceptance / done-when — required

*Frontend* (open SvelteKit dev server at 360×800):

- `/onboarding/connect` matches `mobile_onboarding_01_connect.html`.
  Principles card shows. `[I understand]` dismisses permanently
  (re-visit confirms). Manual URL entry path posts to
  `/api/v1/pairing/redeem` and stores the issued credential.
- `/onboarding/paired` renders the variant matching
  `canUseBiometric()`. All four mockup states reachable. State
  transitions match the spec (initial → biometric-done OR
  skip-confirm → confirmed-skip → `/home`).
- `/unlock` matches `mobile_unlock_biometric.html` initially.
  "Use passphrase instead" → `mobile_unlock_passphrase.html`.
  Valid passphrase unlocks. Wrong passphrase shows inline
  error; N failures trigger rate-limit feedback.
- `/home` matches `mobile_home_empty.html`. Balance `0 sats`.
  `↻` icon cycles to BTC (`0.00000000`). "Show in fiat" link
  present, muted, stub on tap. `+` button stub. Bottom nav with
  the correct active/disabled/enabled states.
- Honest gates per ADR-0007 — visible "Capacitor needed" banner
  on every Capacitor-only capability invocation in dev mode.

*Backend* (Swagger UI walk-through + `.ps1` smoke tests):

- `GET /api/v1/server/info` returns `{server_label}`.
- `POST /api/v1/pairing/issue` returns a one-time token.
- `POST /api/v1/pairing/redeem` with valid token → 200 + device
  credential. Expired/invalid/redeemed token → 401.
- `POST /api/v1/auth/passphrase-validate` — correct passphrase
  → 200, wrong → 401, after N attempts → 429.
- `DELETE /api/v1/devices/{id}` revokes; subsequent requests
  with that credential → 401.
- Auth middleware: un-credentialed request to a protected
  endpoint → 401. Health/info/pairing endpoints stay un-authed.
- `api/openapi.yaml` regenerated and committed with closeout.

*Spec:*

- `tools/check-spec.ps1` (or `.sh`) passes.
- This file reflects shipped state after closeout.

*Brand asset discipline (per `PROCESS.md §2.4` "Consumer
discipline"):*

- Grep across the SvelteKit source tree for hex color literals
  (`#[0-9A-Fa-f]{3}\b` and `#[0-9A-Fa-f]{6}\b`) and inline
  `<svg>` blocks. Only `tokens.css` declarations, brand identity
  SVG sources, and the `<Icon>` wrapper's internal inline-icon
  table match. No hardcoded color values or inline SVG paths in
  feature component files.
- Theme-swap mental check: pick one token (e.g.
  `--color-primary`), change it in `tokens.css` only, rebuild,
  confirm the change propagates everywhere it's used without any
  other source edit needed.

#### Dependencies

- *`pre-implementation.md` `pairing-handshake-crypto`* — leading
  direction is in place (endpoint URL + single-use ephemeral
  token). Coding agent implements per that direction. If a
  load-bearing call deviates (e.g. switch to PAKE-style
  handshake), an ADR + Rémy arbitration is required mid-
  iteration.
- *ADR-0003* (private-ship gate) — locked. This iteration ships
  part of the private-ship-gate auth-layer scope.
- *ADR-0007* (browser-first with NativeBridge) — locked. Pattern
  applies throughout.
- *ADR-0008* (passphrase + recovery model) — locked.
- *Security-health system* — known gap. The
  unacknowledged-principles cycle doesn't fully close until
  that iteration ships. Acceptable for personal-use phase
  (Rémy as sole user); required before public-ship.
- *Brand v1 wordmark-icony viewBox* — not blocking. Mockups
  work with the override. Source fix is a small lockstep change
  inside this iteration.

#### Verification (Rémy)

*Backend:* run the project's `.ps1` smoke-test suite against
the running backend → all green. Then Swagger UI walk-through of
the new endpoints (`server/info`, `pairing/issue`,
`pairing/redeem`, `auth/passphrase-validate`, `devices/{id}`).
Verify auth middleware on at least one previously-unauthed
endpoint.

*Frontend:* open SvelteKit dev server, set viewport to 360×800
(mid Galaxy A baseline per `UI/mockups/README.md` §5), walk:

1. Fresh install / cold state → `/onboarding/connect`. Confirm
   visual match. Test manual URL entry path. Confirm principles
   `[I understand]` persistence.
2. Post-pair → `/onboarding/paired`. Confirm variant matches
   `canUseBiometric()`. Test enable-biometric path (browser-dev
   stubbed). Test skip path (bottom sheet appears, confirm
   proceeds to home).
3. Re-open app (credential present) → `/unlock`. Test biometric
   path. Test passphrase fallback against backend. Confirm
   wrong-passphrase + rate-limit behavior.
4. `/home` renders empty. Visual check vs
   `mobile_home_empty.html`. Confirm `↻` cycles sats / BTC.
5. Honest gates: confirm each Capacitor-only capability shows
   the dev-mode gate banner.

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight:

1. Regenerate `api/openapi.yaml` from the running backend (per
   `PROCESS.md §2.2`). Manual edits forbidden.
2. Run `tools/check-spec.ps1` (or `.sh`) — must pass.
3. Edit this file: remove shipped scope items; leave a brief
   `## Shipped <date> (commit ...)` record under this iteration
   block.
4. Collaboratively promote the next iteration from the roadmap
   below (Rémy picks; do not pick alone). Sharpen the next
   iteration block using the template.
5. Commit closeout in a single change. Message references the
   iteration name and the Rémy-greenlight date.

Full sequence: `PROCESS.md §2.7` stages 3–6.

---

### Pre-bagged for the next iteration (Add Holding)

**Transient.** Decisions sharpened in earlier sessions that
belong to the Add Holding iteration, not to the currently active
one. Fold into Scope (in) when the Add Holding iteration is
sharpened. Remove from this section when folded.

- Home empty's `+` button opens a popup with four type choices
  (Account / Purse / Strongbox / Vault). The four affordances
  are not inline on the empty Home — they live in the popup.
- Watch-only Purse onboarding accepts **xpub or descriptor
  only**, not single addresses (per ADR-0006, slug
  `purse-flavors`).
- TallyKeep-managed Purse creation: the "Create a TallyKeep
  wallet" affordance is gated client-side on the device's
  capability to generate and securely store a seed; browser
  builds hide it with an install-the-app message (per
  ADR-0006).

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
