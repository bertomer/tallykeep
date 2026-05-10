# ADR-0001 — Spec consolidation pass

- **Date:** 2026-05
- **Status:** Accepted; refined by ADR-0002
- **Decided by:** Rémy
- **Authored by:** Claude, during consolidation session

> **Note:** ADR-0002 refines item #1 (module-retirement scope: modules
> 11–14 retire and redistribute, rather than getting absorbed into
> 01/09/10/11/12 as originally drafted) and item #4 (the planned
> `UI/backend_deltas.md` is replaced by the iteration cycle:
> `next_iteration.md` + `future_iterations.md`). The body below is
> kept as historical record.
>
> **Editorial note (2026-05):** the body's "Files affected" list still
> references the original filename `09_profiles_and_flags.md` and the
> original "absorb no named presets" plan. The actual resolutions
> went further: the file was renamed `09_feature_flags.md` and named
> presets were dropped entirely (replaced by onboarding-question-driven
> defaults). Both moves are recorded in the
> `profile-presets-vs-contextual` Decided entry in
> `pre-implementation.md`. The body below is kept as historical record
> per ADR append-only discipline; consult the Decided entry for the
> current state.

## Context

After the v1 spec session and the backend implementation up to module
10, the spec tree had drifted into multiple parallel sources of truth:

- Canonical spec modules (`00_README.md` through `14_context_handoff.md`)
- `UI/design_decisions.md` — claimed UI/UX precedence over spec, with
  amendments not yet folded back
- `UI/mobile_form_factor_decision.md` — amended `design_decisions.md`
  §10 and §12 plus spec modules 01 and 12
- `UI/drafts/spec_amendments.md` — earlier amendments, marked
  superseded but still present
- `UI/handoff.md` — chat handoff doc with its own decision summary
- Eight versions of HTML wireframes across `UI/` and `UI/drafts/`,
  partially overlapping

The amendment-then-merge pattern allowed contradictions to accumulate
without any single doc being authoritative. The next coding agent
could not be expected to navigate this cleanly without reproducing the
ambiguity in code.

## Decision

1. **Canonical specs absorb amendments.** `design_decisions.md` and
   `mobile_form_factor_decision.md` are folded into the relevant
   modules (01, 09, 10, 11, 12) in a follow-up merge session. Where
   no existing module is a clean fit, content is added to module 11
   (UX flows) or a new dedicated section.

2. **Old amendment and handoff docs move to `archive/`** after the
   merge, including `design_decisions.md`, `mobile_form_factor_decision.md`,
   `handoff.md`, `drafts/spec_amendments.md`, and superseded HTML
   wireframes.

3. **New rule:** changes go directly into the canonical doc, with an
   ADR if foundational. No parallel "amendments" docs.

4. **Backend is contract.** OpenAPI extracted from the running backend
   becomes `api/openapi.yaml`. UI specs consume it; UI work
   that requires backend changes lists them in `UI/backend_deltas.md`
   as discrete tickets.

5. **Mockups split page-per-file** under `UI/mockups/`. Multi-screen
   wireframes archived. Naming and conventions in
   `UI/mockups/README.md`.

6. **Brand decisions deferred behind a token system** in
   `UI/mockups/_shared/tokens.css`, with the SvelteKit build later
   referencing the same tokens.

7. **Working agreement** captured in `PROCESS.md`. Pre-implementation
   arbitration in `pre-implementation.md`. ADRs in `decisions/`.

8. **Reconcilability gauntlet** (PROCESS.md §3) is non-negotiable:
   every flow walks through the six-question checklist before being
   marked designed. This is the structural answer to "will the product
   end up at a feature contradicting its principles."

## Consequences

- This consolidation session creates the new structure files but does
  **not** edit canonical modules or move old files yet. Those happen
  in a follow-up merge session, after the user has resolved the
  arbitration items in `pre-implementation.md`.
- Older agent context handoffs (`UI/handoff.md`) are preserved in
  archive for traceability but never source of truth.
- Mockup work pauses until the page-per-file split is done in a
  dedicated session.
- The first ADR (this file) sets the precedent for the format and
  level of detail subsequent ADRs should target.

## Files affected by the eventual merge (not done in this session)

Edits:

- `specs/01_architecture.md` — absorb Capacitor build target,
  mobile/desktop shell separation
- `specs/09_profiles_and_flags.md` — absorb "no named presets,
  contextual feature surfacing" decision
- `specs/10_threat_model.md` — absorb spending-key-on-mobile and
  PWA-holds-no-spending-keys decisions
- `specs/11_ux_flows.md` — absorb home page, onboarding, and
  send-flow design decisions
- `specs/12_roadmap.md` — move Capacitor wrapper from v3 to v1; revise
  mobile track

Archive:

- `specs/UI/design_decisions.md`
- `specs/UI/mobile_form_factor_decision.md`
- `specs/UI/handoff.md`
- `specs/UI/drafts/spec_amendments.md`
- `specs/UI/drafts/*.html` (the v1–v6 wireframe series and one-off
  banking_app wireframes)
- `specs/UI/tallykeep_*.html` files at the top of UI/ once their
  content is captured in mockups/ or referenced from `mobile_v1.md`

Created (this session):

- `specs/PROCESS.md`
- `specs/pre-implementation.md`
- `specs/decisions/README.md`
- `specs/decisions/0001-spec-consolidation.md` (this file)
- `specs/api/README.md`
- `specs/UI/mockups/README.md`
- `specs/UI/mockups/_shared/tokens.css`
- `specs/UI/mockups/_shared/shell.css`
