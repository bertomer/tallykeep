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

*No active coding iteration. The `spec-cleanup-backend-deltas`
iteration shipped 2026-05-10 (commit `cf62741`). All acceptance
criteria passed — 460 tests passed, 1 skipped.*

---

### Current bottleneck — design iteration with Rémy

If you are an agent landing here expecting code work: there is none
ready. The current bottleneck is **design conversations between Rémy
and the agent**, screen by screen, that produce sharpened iteration
scope plus mockups under `UI/mockups/`. Only after that does coding
work appear in this file.

The previous Welcome + Home-empty draft was pulled back: sharpening
individual screens before walking through the existing wireframes
together would have skipped a step. Each iteration's scope is
co-sharpened in conversation against the existing wireframes (bulked
into multi-screen HTMLs in `archive/UI/`, with unclear validated
state). The next session is that walk-through, not a pre-spec'd
iteration.

### What an arriving agent should do

The boot sequence is in `PROCESS.md §6`. Don't duplicate it here.
The thing specific to the current bottleneck:

- If Rémy is in the conversation, ask which screen-flow he wants to
  sharpen first (the roadmap below is the candidate list).
- If Rémy is not in the conversation, do not invent scope. Report
  the current state and stop.

### Decisions already pre-bagged for the first iterations

**Transient.** This section captures decisions sharpened during
brainstorm sessions that haven't yet been folded into a concrete
iteration. When the first Onboarding + Home iteration is
sharpened using the template above, **these bullets fold into
its Scope (in) section** and this transient block is removed.
It's not canonical and shouldn't be referenced from outside this
file.

- Home empty's four Add affordances are a popup on Add-Holding
  tap, not directly inline on the empty state.
- Watch-only Purse onboarding accepts xpub or descriptor only,
  not single addresses (per ADR-0006, slug `purse-flavors`).
- TallyKeep-managed Purse creation: the "Create a TallyKeep
  wallet" affordance is gated client-side on the device's
  capability to generate and securely store a seed; browser
  builds hide it with an install-the-app message (per ADR-0006).
- Mobile baseline viewport: 360 × 800 (per `UI/mockups/README.md`).
- *(Onboarding screen 1 — Connect)* Welcome screen killed; the
  Connect screen is the first-touch surface. Single question:
  "Connect to your TallyKeep" — QR scan primary, manual URL
  entry secondary, "don't have one yet" ghost CTA opens external
  docs link. Persistent acknowledgment-required principles card
  with three lines (open source / no accounts / TallyKeep never
  holds your keys) and an [I understand] button. Card appears
  on Screen 1 only. If the user clicks [I understand], the
  principles are dismissed permanently. If the user skips past
  without acknowledging, the principles surface as an item in
  the **Security health** zone on Home (per the corrected
  acknowledgment flow sharpened 2026-05-10).
- *(Cross-iteration dependency — Security health system)* The
  full re-surface cycle for the principles acknowledgment (and
  the seed-backup warning, Strongbox frequent-usage, Vault
  mismatch, hosted-tier privacy ack, future Blueprint findings)
  depends on the Security-health system landing — captured in
  `future_iterations.md` "Security-health system", milestone
  pre-shipping. For personal-use phase the gap is acceptable
  (Rémy as sole user will acknowledge on first launch). Public-
  ship requires the Security-health iteration to have shipped
  for the unacknowledged-principles cycle to close cleanly.
- *(Onboarding screen 1 — Connect)* Wordmark-icony at 280 px
  is the brand surface; intended to land as the dynamic-mark
  surface (tap-to-regenerate-grain) when implemented in
  SvelteKit. Mockup is static per `UI/mockups/README.md`. The
  brand v1 → v2 lock-doc bump that sanctions the wordmark-icony
  embedded Y as a dynamic surface is part of this iteration's
  scope (per `future_iterations.md` "Dynamic brand mark on
  first-touch surfaces").
- *(Onboarding screen 2 — Paired)* Single screen combining
  pair-success confirmation + biometric setup. Initial state
  shows green checkmark, "Paired with your TallyKeep", server
  label, then a "Lock TallyKeep with your biometric" prompt
  with [Enable biometric unlock] primary and [Skip for now]
  text-link. Skip triggers a bottom-sheet modal asking for
  explicit confirmation. Biometric is opt-in (not required) —
  tradeoff per `pre-implementation.md` `traveling-user-recovery`.
- *(Onboarding screen 2 — Paired)* Brand-strip continues with
  the same 280-px wordmark; the dynamic-mark behavior is
  Screen-1-only per the "first-touch only" sanctioning.
- *(Backend, Onboarding screen 2)* `server_label` field added
  to `01_architecture.md` §"Configuration model". Operator sets
  it during stack installation; surfaced to clients on pairing.
  Optional; absent ⇒ clients render endpoint or connection-ID
  only.
- *(Hosted-tier, deferred)* Connection-ID format favors
  word-pair-encoded memorable strings (e.g. `crisp-river-7842`)
  over raw UUID — non-predictable AND human-handleable. Captured
  in `future_iterations.md` "Hosted tier infrastructure".
- *(Auth-layer scope)* When this iteration sharpens for code, the
  pairing-handshake crypto choice (`pre-implementation.md`
  `pairing-handshake-crypto`) needs to be settled, because it
  shapes the backend's pairing endpoints and the device-credential
  format.
- *(Unlock + recovery model — locked by ADR-0008, two-layer)*
  Per `decisions/0008-passphrase-and-recovery-model.md`. Layer 1:
  daily unlock = biometric default + "Use passphrase instead"
  text-link fallback on the lock screen. Phone forwards the
  typed passphrase to the backend for validation; phone never
  stores the passphrase. Layer 2: deep recovery when the local
  credential is fully lost = re-pair via QR (same flow as
  initial pairing). One passphrase per stack — the user has one
  secret to remember (the server's). Communicated on the
  biometric-done onboarding screen via the facts card
  ("Daily unlock: Biometric · passphrase fallback" /
  "Deep recovery: Re-pair from desktop") plus a short explainer.
  Iteration scope includes the daily-unlock mockups
  (`mobile_unlock_biometric.html`, `mobile_unlock_passphrase.html`).
- *(Backend, auth layer)* Backend exposes
  `POST /api/v1/auth/passphrase-validate` (or equivalent) for the
  phone to call during fallback unlock. Rate-limited to prevent
  brute-force. Endpoint compares Argon2id of input against the
  stored derivation; never stores or logs the raw passphrase.
  Exact shape + comparison method + rate-limit policy sharpen
  during the auth-layer iteration (private-ship gate per
  ADR-0003).
- *(Onboarding screen 2 — `no_biometric` variant)* When
  `NativeBridge.canUseBiometric()` returns false at Screen 02
  entry, render `mobile_onboarding_02_paired_no_biometric.html`
  instead of the biometric-prompt variant. Single [Continue]
  CTA; threat-model copy is honest about OS-lock-only protection
  plus recovery path.
- *(Screen 02 wording — warning placement)* The threat-model
  explainer ("Without it, anyone who can unlock your phone...")
  appears ONLY in the skip-confirm bottom sheet, not on the
  initial Paired screen. Banking-grade discipline: warnings on
  the path that warrants them, not on the default path.
- *(Home empty — banking-grade structure)* Sharpened across
  three passes 2026-05-10. First pass (centered hero + big
  primary CTA) rejected as Phoenix-aesthetic. Second pass
  (`+ Add` text-link) rejected on translation grounds. Final:
  app-bar wordmark; hero on its own white surface, left-aligned
  mono amount with a small single-arrow rotate icon stacked
  above the `sats` label, subdued `Show in fiat` link below;
  "Holdings" section header with right-aligned 28-px circular
  filled `+` button (translation-free); empty list-card
  placeholder ("No Holdings yet"); bottom nav. No tagline, no
  explainer copy, no big shiny button. Section structure
  preserved at zero state. The Add-Holding popup (four type
  choices: Account / Purse / Strongbox / Vault) is its own
  surface, sharpens during the Add-Holding iteration.
- *(Affordance discipline — translation-free where unambiguous)*
  Sharpened during Home-empty session 2026-05-10. Prefer icon-
  only or symbol-only affordances over labeled buttons when
  the meaning is unambiguous from context. Labels stay where
  they carry semantic content that can't be reduced to a
  symbol (primary CTAs: "Enable biometric unlock", "Continue",
  "Unlock"). This compounds positively across LatAm/Africa
  translation surfaces.
- *(Bottom nav)* Present from the empty state per Rémy's call.
  Four tabs: Home (active), Activity (greyed when empty),
  Holdings (greyed when empty), More (enabled — Settings always
  works). Exact tab set is not locked; sharpens with the
  Settings + Activity iterations.
- *(Unit + currency on Home)* Sats default, unit pill cycles
  sats / BTC on tap. Show-fiat link opens a currency picker
  sheet; once a fiat is selected, the fiat line appears below
  the sats amount with source attribution per `UI/README.md`.
  The picker sheet sharpens in the same iteration or with
  Settings.

When the next iteration is sharpened, this section gets filled
in using the template above and the bullets above migrate into
it.

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
