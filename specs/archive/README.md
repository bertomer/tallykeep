# Archive

Historical files retired during the spec consolidation merge
(2026-05). They are kept for traceability and never source of truth.
The next agent should not need to read this directory to do its job
— if you find yourself reaching here for active product information,
something is missing in the canonical specs.

Per `PROCESS.md` and ADR-0001 / ADR-0002, the canonical product
description is in `specs/00_README.md` through `specs/10_threat_model.md`,
the UI specs are in `specs/UI/`, the ADRs are in `specs/decisions/`,
and the working-process / iteration-cycle docs are
`specs/PROCESS.md`, `specs/next_iteration.md`,
`specs/future_iterations.md`, and `specs/pre-implementation.md`.

## What moved here, and where its content went

### `04_api_surface.md`

Original module that listed every endpoint by hand. Retired
2026-05 per pre-implementation item `api-surface-canonical-source`
and superseded by:

- `api/openapi.yaml` — the source of truth for endpoint shapes
  (paths, methods, request/response schemas). Regenerated from the
  running backend on every iteration that touches the API, per
  PROCESS.md §2.2.
- `04_api_conventions.md` — cross-cutting rules only (auth, errors,
  pagination, idempotency, locked-state, SSE pattern, async-job
  pattern, URI versioning).

The file is preserved here for traceability. Do not consult it for
current behavior.

### `11_ux_flows.md`

Original module of UX flows with screen-by-screen ASCII layouts.
Predated the mobile-first / iteration-driven design model.

- Cross-platform UX truth → `UI/README.md`
- Platform-specific specs → `UI/mobile.md` (stub; iteration-driven)
  and `UI/desktop.md` (stub; deferred until mobile is stable)
- Mockups → page-per-file under `UI/mockups/` per the convention
  in `UI/mockups/README.md`. Authored fresh per iteration; ASCII
  layouts in this archived module are not ported.

### `12_roadmap.md`

Original "v1 / v1.5 / v2 / v3 / v5" staging document.

- The "v1 / v1.5 / v2 / v3" framing is dropped per ADR-0003 in
  favor of three phases separated by two events: dev → private-ship
  → personal-use → public-ship → public.
- In-scope-for-v1 list → `00_README.md` §"Currently in scope (dev
  phase)".
- Deferred items (v1.5, v2, v3, v5) → `future_iterations.md` with
  `pre-shipping` / `post-shipping` / TBD milestone tags.
- "Explicitly never" rejection list → `00_README.md` §"Explicitly
  out of scope".

### `13_open_questions.md`

Original module of deferred questions and decisions.

- Most Q1–Q19 were either already decided in canonical specs,
  implementation-level details that don't need spec-tree presence,
  or had leans that have since been folded in. These dropped.
- Q6 (mixed-input transaction flagging) → `future_iterations.md`
  (pre-shipping, after private-ship)
- Q7 (coin selection algorithm review) → `future_iterations.md`
  (pre-shipping session, between private-ship and public-ship)
- Q8 (possible Purse / Strongbox collapse) → `future_iterations.md`
- Q15 (Tor integration) → `future_iterations.md`
- Q18 (telemetry rejection) → `00_README.md` §"Explicitly out of
  scope"
- Q19 (no marketing in domain) → `PROCESS.md` §2.8 Naming
  discipline (alongside the no-abbreviations rule).
- Known risks (bdkpython, ccxt, bitcoind RPC stability, iOS Safari
  PWA, Argon2id parameters) → already mentioned in canonical stack
  and threat-model modules; not separately migrated.

### `14_context_handoff.md`

Original "context for the next agent" document.

- User motivations (Layer 1 / 2 / 3) → `00_README.md` §"Why this
  exists".
- Locked design principles (10) → already encoded across canonical
  modules `00_README` + `01`–`10` and `UI/README.md`. Not migrated as
  ADRs (would have been paperwork; see merge session notes). Two
  rules previously implicit (no marketing in domain, no
  abbreviations in identifiers) lifted to `PROCESS.md` §2.8.
- Decisions explicitly rejected → already encoded in `00_README.md`
  §"Explicitly out of scope".
- Tone-and-voice substance → `PROCESS.md` §6 "Defaults".
- Architecture summary diagram, "what was non-obviously hard"
  breadcrumbs, marketing / business-model sketch — kept here as
  historical context only. Not part of canonical product
  description.

### `UI/design_decisions.md`

Old amendment doc that claimed UX/UI precedence over the canonical
spec. Content folded into:

- `UI/README.md` — cross-platform UX decisions, flow inventory
- `00_README.md` — design principles
- `future_iterations.md` — items captured as later iterations
  (hosted tier, Lightning, DCA, equity reference, inflation graphs,
  retirement plan, Blueprint analysis)

### `UI/mobile_form_factor_decision.md`

Old amendment specifying that the mobile form factor is
Capacitor-wrapped SvelteKit PWA, with browser builds never holding
spending keys.

- The Capacitor decision and its threat-model implications are now
  in ADR-0003 and `10_threat_model.md` Mobile addendum.
- The "Capacitor wrapper as private-ship enabler" status is in
  `future_iterations.md`.
- Browser-vs-Capacitor capability divide is encoded in
  `PROCESS.md` §3 reconcilability gauntlet question 5 and §4
  Browser fine-tuning.

### `UI/handoff.md`

Old chat-handoff doc with its own decision summary. Superseded
entirely by `PROCESS.md` §6 "Working agreement for the next agent".

### `UI/drafts/spec_amendments.md`

Earlier set of amendments, marked superseded but still present.
Content already absorbed into the canonical specs by the time of
the merge.

### `UI/drafts/*.html` and `UI/tallykeep_*.html`

Multi-screen wireframe HTMLs in versions v2–v8 plus stand-alone
"home final," "onboarding validated," "mobile v2," "Y v3," and
"brand mark v1 lock" files.

These are reference material for upcoming iteration sessions —
when the Onboarding + Home iteration is sharpened, the existing
wireframes are pulled up here, then proper page-per-file mockups
are produced under `UI/mockups/` per the convention in
`UI/mockups/README.md`.

The original `UI/drafts/` directory remains in place as an empty
folder (the underlying mount disallows directory removal); its
contents have all moved here under `archive/UI/drafts/`.
