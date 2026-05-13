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
