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

*No active iteration sharpened yet. Next to promote:
**"Add Holding — Purse wizard"** from `future_iterations.md`
(sharpened-ready-to-promote; carries the shared wizard shell
as scaffolding since Purse is its first consumer).
Promote collaboratively with Rémy.*

#### Scope (in) — required

**Picker — bottom sheet from Home empty's `+` button.**

Per the pre-bagged decisions (now folded): the four type
affordances live in the popup, not inline on Home empty. Bottom
sheet, scrim, slide-up animation, swipe-down or Cancel to
dismiss. Single-column rows (cards variant from earlier
prototype dropped). Four rows in **custody-progression order**
(hot-to-cold, least-sovereign-to-most-sovereign):
Account → Purse → Strongbox → Vault. The ordering reads as the
user's lifecycle arc — where the money starts (third-party
custody), where it lives daily, where it accumulates
short-term, where it sits long-term. Each row: 40px icon (2px
border in `--tk-holding-*`), bold name, one-line description,
chevron.

Copy locked in this iteration (revisit only on Rémy's call):

- Sheet title: *"Add a Holding"*
- Sheet sub: *"Each holds your keys differently."*
- Account: *"Held at an exchange or broker. They hold the
  keys; you see balances."* — visible in the picker, but tap
  leads to a one-screen *"Add Account ships in the next
  iteration"* stub. Stub has back to picker and no other
  functionality.
- Purse: *"On your phone. For daily spending."*
- Strongbox: *"On a hardware wallet. For amounts you spend
  rarely."*
- Vault: *"Multiple keys required. For amounts you rarely
  touch — years, not days."*

No *Recommended* pill in this iteration. The pill is meaningful
only when managed-Purse capability lands (Capacitor with
secure-storage backend); shipping a conditionally-rendered pill
that's always-false in dev phase would mean shipping
capability-check infrastructure with no visible consumer. The
pill, the capability check (`device.capabilities.canStoreSeed`),
and the Purse-wizard managed-flavor branch all land together in
the Capacitor-wrap iteration, where they have a working surface
to attach to.

**Non-Account tile behaviour in this iteration.** Tiles Purse,
Strongbox, Vault all lead to a single shared "Coming next
iteration" placeholder screen (same mockup as the Account stub,
parameterized by the picked type for icon + name continuity).
This keeps the picker visually honest about all four types being
real options while each wizard's iteration ships. As each wizard
lands, its tile starts routing to the real wizard instead of the
placeholder. (Alternative considered: disable the non-Account
tiles. Rejected — visible-with-stub is consistent with the
Account treatment Rémy already chose and avoids "is it broken?"
ambiguity.)

**Home populated — `mobile_home_populated.html`.**

Same shell as Home empty. Holdings list renders as a list-card
with rows in custody-tier order (Account → Purse → Strongbox →
Vault). Row anatomy per the validated mockup. Hero amount sums
across the rendered Holdings.

**Testability without wizards.** No in-app way to create Holdings
yet in this iteration's scope. Rémy verifies the populated home by
seeding Holdings via Swagger UI / the `.ps1` smoke-test suite
(direct API POSTs against the backend endpoints shipped in this
iteration). That's a legitimate dev-phase test surface per
ADR-0007.

**Backend (extend existing API surface):**

- `POST /api/v1/descriptors/validate` — accept xpub or BIP 380
  descriptor; return `script_type`, `derivation_path`,
  `first_addresses` (3), `is_multisig`, `required_signers`,
  `total_signers`, `timelocks`. Pure parser, no state mutation.
  Single-address inputs return a typed error.
- `POST /api/v1/holdings/purse` — create Purse with
  `seed_origin: EXTERNAL_WATCH_ONLY`. Validate descriptor
  server-side regardless of client validation. Kick off scan
  via existing scan-job pattern.
- `POST /api/v1/holdings/strongbox` — same shape, type
  strongbox.
- `POST /api/v1/holdings/vault` — accepts only multisig
  descriptors; returns typed rejection error otherwise.
- `GET /api/v1/holdings` — verify response includes the fields
  Home populated needs (type, name, meta, balance, scan_status).
  If missing fields, extend.

**NativeBridge:**

- `clipboard.paste()` — real on browser, stub for Capacitor
  pending its iteration.

(`device.capabilities.canStoreSeed` is **not** introduced in
this iteration. It lands in the Capacitor-wrap iteration
together with its consumers — the Purse wizard's
managed-flavor branch and the picker's Recommended pill.)

#### Scope (out) — required

- **Per-wizard mockups + frontends** (Purse, Strongbox, Vault).
  Each becomes its own subsequent iteration once its design pass
  validates the wizard mockups. See `future_iterations.md` entries
  marked `sharpened-ready-to-promote`. Promotion order: Purse
  first (canonical descriptor wizard, also carries the shared
  wizard shell as scaffolding), then Strongbox, then Vault.
- **Shared wizard shell** (step counter, back chevron, primary
  CTA pinned to bottom, error region above CTA). Lands with the
  Purse-wizard iteration since that's the first consumer.
- **Account wizard.** Different surface (ccxt provider
  integration, live API validation, no descriptor parser).
  Follow-up iteration "Add Account." In this iteration the
  Account tile leads to the stub.
- **TallyKeep-managed Purse** (`TALLYKEEP_MANAGED`, on-device
  seed generation). Gated on Capacitor + `seed-backup-disclosure`
  arbitration. Capacitor-wrap iteration.
- **Vault operational features** — spending ceremony, blueprint
  analysis, declared-vs-observable mismatch warnings. Vault
  detail iteration.
- **Strongbox / Vault spending (PSBT export-sign-import)** —
  Send + Receive iteration.
- **QR-scan as descriptor input.** Capacitor-only, deferred.
- **Withdrawal whitelisting on the exchange side.** SweepPolicy
  iteration (`07_trading_layer.md`).
- **Multi-asset balance display.** `multi-asset-aggregation`
  open arbitration; gates Holding Detail iteration.
- **Hardware-wallet-specific export tips** (per-device guides
  for Coldcard / Trezor / etc.). Nice-to-have, deferred.

#### Affected canonical docs

- `02_domain_model.md` — Add-Holding flow notes may need a small
  section; check during sharpening.
- `05_savings_layer.md` — descriptor validation / parse-back
  semantics; confirm or add.
- `07_trading_layer.md` — Account stub note (this iteration
  ships a placeholder tile only).
- `UI/mobile.md` — Add-Holding scaffolding flow section
  (picker + populated home + stub); gauntlet 1-6 answers for
  the three surfaces. Per-wizard gauntlet entries land with
  the wizard iterations.
- `UI/README.md` — cross-platform flow inventory addition.

#### Affected mockups

Validated, ready for coding-agent intake:

- `mobile_home_empty.html` — re-validated 2026-05-13 (filled `+`
  button, 2 px verdigris top-indicator on active nav, hero
  amount in Manrope tabular-nums).
- `mobile_home_populated.html` — validated 2026-05-13.
- `mobile_add_holding_picker.html` — validated 2026-05-13.

- `mobile_add_holding_coming_soon.html` — validated 2026-05-13.
  One-screen stub parameterized by Holding type. Used by Account
  tile and (in this iteration) by Purse / Strongbox / Vault
  tiles before their wizards ship.

Wizard mockups (Purse / Strongbox / Vault) are **not** in
scope of this iteration — see `future_iterations.md` entries
"Add Holding — Purse wizard", "Add Holding — Strongbox
wizard", "Add Holding — Vault wizard".

#### Tasks — required

Ordered. Stage gate: the design pass mockup ships first so coding
agent has a validated stub to wire to.

**Design pass — already shipped (2026-05-13):**

All four mockups for this iteration are validated and ready
for coding-agent intake: `mobile_home_empty.html`,
`mobile_home_populated.html`, `mobile_add_holding_picker.html`,
`mobile_add_holding_coming_soon.html`.

1. ~~Draft + validate `mobile_add_holding_coming_soon.html`~~ — done.
2. ~~Update `UI/mobile.md` with the Add-Holding scaffolding flow
   section (picker → coming-soon stub) + gauntlet 1-6 answers
   for those surfaces + populated-home notes for the new
   custody-tier sort, source-name meta, brass Vault stripe,
   amount typography swap, filled-primary `+`, and active-nav
   indicator.~~ — done 2026-05-13.

**Backend pass (coding agent):**

3. Implement `POST /api/v1/descriptors/validate` covering xpub,
   BIP 380 wpkh / tr / sh-wpkh, multisig variants; reject
   single addresses with a typed error.
4. Implement or confirm `POST /api/v1/holdings/{type}` per
   type (purse / strongbox / vault). Vault rejects non-multisig
   descriptors.
5. Verify `GET /api/v1/holdings` returns the populated shape
   Home populated needs; extend if missing.
6. Unit + integration tests: parser correctness across script
   types, Holding creation per type, multisig-only enforcement
   on Vault.

**Frontend pass (coding agent):**

7. Picker bottom-sheet component (reusable; wizard sheets will
   reuse this when they ship).
8. Coming-soon stub screen (one route, parameterized by
   Holding type).
9. Home populated state with row rendering per type.
10. Wire end-to-end against the backend: `+` from Home →
    picker → tile tap → stub (all four tiles route to the
    coming-soon stub in this iteration; navigation back works
    correctly).

**NativeBridge:**

11. `clipboard.paste()` — real on browser. (No consumer in
    this iteration but the bridge ships now to unblock the
    Purse-wizard iteration.)

#### Acceptance / done-when — required

Observable conditions:

- From Home empty, tap `+` → picker bottom sheet appears within
  ~250 ms with rows in declared order (Account → Purse →
  Strongbox → Vault), copy verbatim from the validated picker
  mockup. Cancel and swipe-down dismiss.
- Tap any tile → coming-soon stub for that Holding type (Account
  shows "Add Account ships in an upcoming iteration"; the other
  three show the same stub parameterized for their type). Back
  returns to picker.
- Backend `POST /api/v1/descriptors/validate` returns the
  expected shape for all four script families (P2WPKH, P2TR,
  P2SH-P2WPKH, multisig); single-address inputs return the typed
  rejection error. Covered in the `.ps1` smoke-test suite.
- Backend `POST /api/v1/holdings/{type}` creates a Holding (with
  scan job kicked off) for purse / strongbox / vault. Vault
  rejects non-multisig descriptors with a typed error. All three
  covered in the `.ps1` smoke-test suite.
- Backend `GET /api/v1/holdings` returns the shape Home populated
  consumes; verified by seeding Holdings via Swagger UI and
  reloading the populated home in the browser.
- Home populated renders one row per type with the validated
  mockup's anatomy (stripe colour, name, meta, amount in Manrope
  tabular-nums) when Holdings are seeded.
- Swagger UI shows the four new/extended endpoints; manual
  walk-through passes.
- The three surfaces (picker, populated home, coming-soon stub)
  pass gauntlet 1-6 with answers documented in `UI/mobile.md`.
- `tools/check-spec.ps1` passes.

#### Dependencies

None blocking.

- `multi-asset-aggregation` (open) — gates Holding Detail
  iteration, not this one.
- `seed-backup-disclosure` (open) — gates managed-Purse
  flavor; intentionally out of scope this iteration.
- `browser-pwa-auth-model` (open) — does not block; the
  dev-mode `localStorage` crutch from the prior iteration
  continues to carry the browser session.

#### Verification (Rémy)

- Run the project's `.ps1` smoke-test suite against the running
  backend.
- Swagger UI walk-through of the four new/extended endpoints.
  Seed at least one Holding of each type via the UI.
- Reload the browser PWA and hand-test: picker → tile taps →
  stub returns; populated home renders the seeded Holdings at
  360×800 in Chrome and Samsung Internet; smoke at 384×854 and
  412×900 per `PROCESS.md §5`.
- Visual review of the new `mobile_add_holding_coming_soon.html`
  mockup against `tokens.css` — confirm no raw hex values, all
  colours and spacing flow through tokens.

#### Closeout

Standard per `PROCESS.md §2.7` stages 3–5. After Rémy greenlight:
regenerate `api/openapi.yaml`, edit this iteration block to mark
shipped + record commit reference, mark validated mockups in
`UI/mobile.md`, run `tools/check-spec.ps1`, commit.

On closeout, the next iteration to promote is **"Add Holding —
Purse wizard"** from `future_iterations.md` (sharpened-ready-to-
promote; carries the shared wizard shell as scaffolding since
Purse is its first consumer).

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
