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

1. Read `00_README.md`, `PROCESS.md`, this file.
2. If Rémy is in the conversation, say so and ask which screen-flow
   he wants to sharpen first (the roadmap below is the candidate
   list).
3. If Rémy is not in the conversation, do not invent scope. Report
   the current state and stop.

### Decisions already pre-bagged for the first iterations

- Home empty's four Add affordances are a popup on Add-Holding tap,
  not directly inline on the empty state.
- Watch-only Purse onboarding accepts xpub or descriptor only, not
  single addresses (per pre-implementation item `purse-flavors`).
- TallyKeep-managed Purse creation: the "Create a TallyKeep wallet"
  affordance is gated client-side on the device's capability to
  generate and securely store a seed; browser builds hide it with
  an install-the-app message (per `purse-flavors`).
- Mobile baseline viewport: 360 × 800 (per `UI/mockups/README.md`).

When the next iteration is sharpened, this section gets filled in
using the template above.

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
   v1 dev-phase scope
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
