# ADR-0002 — Iteration cycle and module retirement

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during consolidation session
- **Refines:** ADR-0001 items #1 (module-retirement scope) and #4
  (the planned `backend_deltas.md`)

## Context

ADR-0001 proposed a single growing `backlog.md` at root for tracking
pending work (originally drafted as `UI/backend_deltas.md`). On
review, that shape didn't match how this project actually evolves:

- Brainstorm sessions produce decisions that update the canonical
  spec immediately. Some are implementable now; others are flagged
  "yes, but later."
- The coding agent works one iteration at a time, not a flat backlog.
- The next iteration must be sharp, small, fully detailed; future
  iterations can be rougher.
- The original modules 00–13 worked as an implementation sequence
  because they didn't overlap. Now that the product is functional,
  any new feature touches multiple modules (domain + banking + UI)
  and module-as-iteration-unit no longer maps.

Three categories of "path-to-target" docs emerge from how Rémy
actually wants to work:

1. Items requiring a dedicated arbitration session before the agent
   can move forward — `pre-implementation.md`. Rémy's decision,
   reasoned, not the agent's autonomy.
2. The current sharpened iteration — single source for what the
   coding agent is working on. Updated in lockstep with canonical
   specs whenever the spec evolves.
3. Future iterations — captured ideas, rougher, awaiting promotion.

A second observation: modules 11–14 of the original spec are not
actually canonical product description. They are path-or-meta material
wearing canonical-spec clothing, and should retire.

## Decision

### Iteration model

1. Replace the proposed `backlog.md` with two files at root:
   - `next_iteration.md` — sharpened, fully detailed scope of work
     the coding agent is working on (or about to start). Updated in
     lockstep with canonical specs.
   - `future_iterations.md` — the pot. Roughly captured ideas for
     later iterations.
2. `pre-implementation.md` keeps its role: items needing a dedicated
   arbitration session.
3. The proposed `UI/backend_deltas.md` is not created; UI-driven
   backend changes are tracked as part of the relevant iteration in
   `next_iteration.md`.
4. Iteration lifecycle:
   - **Brainstorm session:** edit canonical doc + edit
     `next_iteration.md` in lockstep. Ideas flagged "later" go to
     `future_iterations.md`. Items needing dedicated arbitration go
     to `pre-implementation.md`.
   - **Coding agent** reads `next_iteration.md` and works it. Other
     docs are reference.
   - **Iteration completes:** items removed from `next_iteration.md`;
     OpenAPI regenerated; mockups validated; one item promoted from
     `future_iterations.md` and sharpened.

### Module retirement (refines ADR-0001 §1)

Modules 11, 12, 13, 14 of the original spec retire during the merge
session. Their content redistributes:

| Original | Content type | New home |
|---|---|---|
| 11_ux_flows.md | Cross-platform UX flows + decisions | `UI/README.md` (cross-platform) + `UI/mobile.md` + `UI/desktop.md` (platform-specific) |
| 12_roadmap.md | Implementation staging (v1/v1.5/v2) | `next_iteration.md` + `future_iterations.md` (with milestone tags) |
| 12_roadmap.md | Permanent out-of-scope items | `00_README.md` "Out of scope" section + ADRs for any contested |
| 13_open_questions.md | Decisions deferred | `pre-implementation.md` (if blocking) or `future_iterations.md` (if deferable) |
| 14_context_handoff.md | User motivations, product philosophy | `00_README.md` |
| 14_context_handoff.md | Locked design principles | `decisions/` as a series of ADRs (each principle becomes one) |
| 14_context_handoff.md | Rejected decisions with reasoning | `decisions/` as ADRs (one per rejection, kept for breadcrumb) |
| 14_context_handoff.md | Tone, working register | `PROCESS.md` |

The numbering 00–10 is preserved. Modules 11–14 are simply absent
post-merge; the gap is harmless.

### Filename hygiene

- UI specs are `UI/mobile.md` and `UI/desktop.md`, no `_v1` suffix.
  Living docs; version control gives history.
- The same applies to any future canonical doc — no version suffixes
  in filenames.

## Consequences

- Coding agents have a single file to read for "what is my work":
  `next_iteration.md`. Other specs are reference.
- Brainstorming has a clear lockstep: spec edit + iteration edit, every
  time. No drift between target and pending work.
- "Beautiful new idea but later" gets a real home in
  `future_iterations.md` rather than getting lost or polluting the
  current scope.
- The canonical-spec tree shrinks to 00–10 (target product) + UI/
  (target UX) + decisions/ (rules). Path-to-target lives outside.
- The merge session that follows ADR-0001 also executes this
  retirement (modules 11–14 redistribute, deprecated files archive).

## Affected files

Created (this session):

- `specs/next_iteration.md`
- `specs/future_iterations.md`
- `specs/decisions/0002-iteration-cycle.md` (this file)

Updated (this session):

- `specs/PROCESS.md` — §1 layout, §4.2 backend contract, §6 working
  agreement, §7 when things change, plus filename hygiene throughout.
- `specs/pre-implementation.md` — intro updated to reflect iteration
  model.
- `specs/decisions/0001-spec-consolidation.md` — top note pointing to
  this ADR for refinements.

Removed (instruction for migration):

- `specs/UI/backend_deltas.md` — the file was created during this
  session; delete during migration. Its role is replaced by the
  iteration cycle.

Pending in the merge session (not done now):

- Edit `00_README.md` to absorb 14's user motivations, product
  philosophy, and the explicit out-of-scope list from 12.
- Create ADRs from 14's locked design principles and rejected
  decisions (ten or so ADRs).
- Migrate 11's UX flow content to `UI/README.md`, `UI/mobile.md`,
  `UI/desktop.md`.
- Migrate 12's v1/v1.5/v2 staging into `future_iterations.md` items.
- Migrate 13's open questions into `pre-implementation.md` /
  `future_iterations.md`.
- Archive: `11_ux_flows.md`, `12_roadmap.md`, `13_open_questions.md`,
  `14_context_handoff.md`, `UI/design_decisions.md`,
  `UI/mobile_form_factor_decision.md`, `UI/handoff.md`,
  `UI/drafts/spec_amendments.md`, `UI/drafts/*.html`, top-level
  `UI/tallykeep_*.html` once content is captured.

**Status (2026-05):** All items above executed in the consolidation
merge. See `archive/README.md` for the migration map and per-item
disposition. One intentional deviation from this ADR: the
principle / rejection ADRs from 14 were *not* created. The content
was already encoded across canonical modules 00–10 and UI/README;
new ADRs would have been paperwork. The two genuine gaps surfaced
by triage (no marketing in domain, no abbreviations in identifiers)
were lifted into `PROCESS.md` §4.5. Multi-asset aggregation, which
ADR-0002 had implicitly assumed was a settled rejection, surfaced
as an actually-open arbitration question and lives in
`pre-implementation.md` item `multi-asset-aggregation`.
