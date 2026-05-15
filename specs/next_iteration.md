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

#### Affected mockups

<list of validated mockup files referenced by the iteration.>

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

No active iteration. See `future_iterations.md` for the next
candidate to promote and sharpen.

---

## Iteration roadmap (rough sketch — not commitment)

For Rémy's mental model, not for the coding agent. Sequence and
scope will adjust as we learn. The roadmap targets the
public-ship event (per ADR-0003); private-ship is reached when
the relevant mobile UI iterations are stable enough and the
Capacitor + auth + security-health work lands.

### Pre-shipping iterations

**Mobile UI design and dev-phase build:**
1. **Onboarding + Home (empty + populated states)** — first-touch
   flow plus landing
2. **Add Holding** — chooser + four type-specific flows
3. **Holding Detail** — per-type detail pages
4. **Send + Receive** — per Holding type, including PSBT
   roundtrip for Strongbox and native sign for TallyKeep-managed
   Purse on the device that holds the seed
5. **Activity + Categorization** — cross-Holding feed plus
   per-Holding categorization
6. **Sweep Policy + Treasury view** — Account-originated sweeps
   in the dev-phase scope
7. **Settings** — including the security-health system at least
   for seed-backup warnings (private-ship gate)

**Private-ship gate:**
- Capacitor wrap + native plugins
- Authentication layer
- Security-health (seed-backup recovery flow per
  pre-implementation item `seed-backup-disclosure`)
- Self-review

**Pre-public-ship enhancements** (in personal-use phase, before
public-ship):
- Iterations driven by Rémy's own daily-use feedback
- Possible candidates: settlement-rails confirmation probability,
  "tap to see under the hood" UI spine, others (see
  `future_iterations.md`)

### Public-ship event (ship-gate work bundle)

See `future_iterations.md` "Ship-gate meta-iteration" entry.
Bundles native signing, reproducible builds, app stores, F-Droid,
brand, third-party audit, and (optionally) hosted-tier launch.

### Post-shipping

Feature updates per `future_iterations.md` post-shipping entries
(Blueprint, Lightning, DCA, equity-reference, etc., depending on
user feedback and roadmap priorities).
