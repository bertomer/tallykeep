# TallyKeep — Working Process

Single source of truth for how specs evolve, where things live, and what
the next agent should expect when picking up this project. Read this
before doing any work.

---

## 1. Document layout

```
specs/
├── 00_README.md ............ product overview, motivations, scope, principles
├── 01_architecture.md ...... surfaces, trust zones, key custody, internal layering
├── 02_domain_model.md ...... vocabulary contract (Holding, Descriptor, …)
├── 03_data_model.md ........ schema invariants, secret storage
├── 04_api_conventions.md ... cross-cutting API rules
├── holdings/ ............... per-Holding-type chapters (target behavior)
│   ├── README.md
│   ├── 01_account.md ....... custodial Holdings
│   ├── 02_purse.md ......... light-spending Holdings (three seed origins)
│   ├── 03_strongbox.md ..... hardware-wallet Holdings
│   └── 04_vault.md ......... multisig / timelock Holdings
├── concerns/ ............... cross-cutting capabilities
│   ├── README.md
│   ├── observation.md ...... chain monitoring, hygiene, declared-vs-observable
│   ├── outflow.md .......... PSBT machinery, broadcast, payment-request lifecycle
│   ├── sweep_policies.md ... cross-Holding sweep model
│   ├── feature_flags.md .... flag catalog, onboarding-driven defaults
│   ├── lightning_placeholder.md ... LightningProvider interface, deferred
│   └── threat_model.md ..... security posture + Mobile addendum
├── PROCESS.md .............. this file (working agreement)
├── pre-implementation.md ... items needing dedicated arbitration session
├── next_iteration.md ....... sharpened scope of the active iteration
├── future_iterations.md .... pot of ideas captured for later
├── api/
│   └── openapi.yaml ... frozen backend contract (generated)
├── brand/
│   ├── README.md ........... brand layout, status, pointers
│   ├── tallykeep_<artifact>_v<N>_<status>.html ... one big lock doc per artifact
│   │                       (mark, wordmark, future lockup). status: lock | draft | superseded
│   ├── tallykeep_<voice-piece>_v<N>_<status>.md ... voice/about/tagline copy
│   ├── identity/
│   │   ├── README.md ....... import-target conventions
│   │   └── *.svg ........... clean SVGs extracted from lock docs (consumed by
│   │                       mockups and frontend code)
│   └── assets/ ............. (when present) built artifacts: favicon.ico,
│                            app-store icons, social cards, etc.
├── decisions/
│   ├── README.md ........... ADR convention + index
│   └── NNNN-title.md ....... one ADR per foundational decision
├── UI/
│   ├── README.md ........... cross-platform flow inventory + decisions
│   ├── mobile.md ........... mobile platform spec, screen-by-screen
│   ├── desktop.md .......... desktop platform spec (later)
│   └── mockups/
│       ├── README.md ....... naming + index
│       ├── _shared/
│       │   ├── tokens.css .. brand tokens
│       │   └── shell.css ... phone-frame and common layout
│       └── mobile_<flow>_<state>.html ... one page per file
├── tools/
│   └── check-spec.ps1 ...... iteration-done sanity sweep (see §2.9)
│   └── check-spec.sh ....... portable sibling for Linux/Mac
└── archive/ ................ historical iterations, never source of truth
```

Modules 11–14 of the original spec retired in the consolidation
merge per ADR-0002. Modules 05–10 retired in the 2026-05 spec
reshape; their content redistributed into `holdings/` (per-type
chapters) and `concerns/` (cross-cutting capabilities). Modules
00–04 remain canonical product description; everything else
lives in the two subfolders.

**Three doc roles, one job each:**

- **Target-product canon** (`00`–`04`, `holdings/`, `concerns/`,
  `UI/`, `api/openapi.yaml`, `brand/`) — what TallyKeep IS.
  Edited in lockstep with every brainstorm decision. Never
  describes process.
- **Path-to-target** (`next_iteration.md`, `future_iterations.md`,
  `pre-implementation.md`) — what's being worked, what's open,
  what's deferred. Never describes the canonical product.
- **Rules and decisions** (this file, `decisions/`) — how we work,
  what we've decided. **Process lives in PROCESS only.**
  Foundational decisions live as ADRs only. Other READMEs in the
  tree describe layout and status; for rules they point here.

Anything not in canonical, path-to-target, or `decisions/` is
either a working draft or archived history. The next agent should
never need to read `archive/` to do its job.

**Three universes of state, three homes.** Because the spec is
read by agents who need to know not just *what TallyKeep is* but
*where it is right now*:

- **Target state** — the canonical specs above. Describes the
  product we are building toward. Features marked "deferred"
  here are target behavior that hasn't shipped yet, with a
  pointer to where the work is tracked.
- **Current state** — the **code**, plus the OpenAPI export from
  the running backend. The code is what is actually live. Reading
  current state means reading code and the OpenAPI YAML; the spec
  does not redundantly describe "what ships today."
- **Open decisions** — `pre-implementation.md` (must-decide,
  blocking) and `future_iterations.md` (parked ideas). The
  decisions not yet made; what TallyKeep *might* be.

The bridge between target and current is the **"deferred" marker**
in canonical specs and the iteration cycle (§2.7). An iteration
implements a slice of target → current; on closeout, the slice's
"deferred" marker comes out of the canonical specs and the
feature is live. The spec never describes "what's live today"
separately from "what's target" — that would require
sync-discipline we know we can't maintain. Code is the truth for
current; spec is the truth for target.

---

## 2. Core rules

### Roles

A new agent landing in this repo plays one of a small set of
roles. The roles are not tools or personas — they are different
**work-shapes**, each with its own input, output, and acceptance
gate. The first thing an arriving agent should do (before
anything in §6) is locate which role the current session is in.
The boot sequence routes by role implicitly; this section makes
the routing explicit.

**Specification agent** — drafts and edits the spec.
- *Input:* a brainstorm session with Rémy, an open question in
  `pre-implementation.md`, or drift the §2.9 sweep surfaced.
- *Output:* edits to canonical docs (`00`–`10`, `UI/`, `brand/`),
  entries in `next_iteration.md` /
  `pre-implementation.md` / `future_iterations.md`, ADRs in
  `decisions/`, mockup files when the iteration includes them.
  **Never code.**
- *Gate:* Rémy reads the spec edits and confirms ("yes, that's
  the call"), or sends back to arbitration.

**Coding agent** — implements a sharpened iteration.
- *Input:* `next_iteration.md`'s active iteration block.
  Does not invent scope; if scope is empty, stops and reports
  per `next_iteration.md` "What an arriving agent should do".
- *Output:* code commits implementing the iteration. At
  closeout: regenerated `api/openapi.yaml` and edited
  `next_iteration.md` removing shipped items.
- *Gate:* the human-validation handoff in §2.7 stages 3–4 —
  smoke tests + Swagger UI check + Rémy's explicit greenlight.
  See §2.7 for the mandatory stop and the closeout sequence.

**Design / brand agent** — draws and locks the visual surface.
- *Input:* a UI iteration block, or a brand-artifact revision
  (mark, wordmark, future lockup, voice draft).
- *Output:* mockup HTML files in `UI/mockups/`, brand lock docs
  in `brand/`, regenerated `brand/identity/*.svg`, lockstep
  `tokens.css` updates, edits to `UI/mobile.md` flow sections
  when a mockup is validated.
- *Gate:* Rémy's visual validation (look, vocabulary, gauntlet
  question 4 "confirmation honesty"). **Not** smoke tests, not
  OpenAPI regeneration. The lockstep propagation rule (brand →
  identity SVGs → tokens.css) is §2.4.

**Marketing agent** (future, post-public-ship event) — drafts
external-facing copy.
- *Input:* brand voice principles
  (`brand/tallykeep_about_v1_draft.md`) plus a brief.
- *Output:* tagline, marketing-site copy, app-store listings,
  social cards, blog drafts. Lives outside the spec tree
  (probably a sibling marketing-site repo).
- *Gate:* Rémy on voice and factual accuracy. Banking-ergonomics
  framing per `00_README.md` "Why this exists"; never the maxi
  voice (no "be your own bank", "stack sats", "orange-pill",
  "sound money", laser eyes).

**Triage / consolidation agent** (rare, on demand) — audits the
spec tree for drift and proposes targeted fixes.
- *Input:* suspicion that multi-session work has drifted, or a
  failing §2.9 sanity sweep that needs more than mechanical fixes.
- *Output:* an audit report, then targeted edits closing the
  gaps. The work that produced the current shape of this
  PROCESS.md was a triage pass.
- *Gate:* Rémy reviews the findings and prioritizes the fix
  order before any edits land.

**One agent, one role per session — with a deliberate escape
hatch.** The base rule is one role per session. Mixing roles
unconsciously — "I'll code AND update the spec while I'm here" —
is how the original consolidation merge became necessary.

The escape hatch: an agent **may** transition roles within a
single session if the transition is **explicit** and the next
role's input is sharpened first.

- *Tight iteration (one screen, narrow bug fix, single-flow
  mockup):* one session can run spec-agent → coding-agent
  end-to-end. The agent says, in chat to Rémy, "scope is
  sharpened — switching to coding agent now, working against
  this specific scope." From that moment it does not edit
  canonical specs except for the §2.7 closeout.
- *Large iteration (multiple modules, multi-day work, new
  feature surface):* split sessions. Spec agent sharpens with
  Rémy, hands off; coding agent picks up the sharpened
  iteration in a fresh session. The session boundary enforces
  the role boundary mechanically — the right shape when the
  iteration is large enough that role-mixing risk is real.

If a coding session uncovers a real spec issue, the agent
stops, names the issue, and either explicitly transitions to
spec-agent (after Rémy confirms scope of the spec change) or
hands the issue to a separate session. Same in reverse: a spec
agent that finds itself wanting to write production code has
stepped out of role; sharpen the iteration and hand off
instead. The forbidden move is silent role-mixing — discovering
spec ambiguity, picking an interpretation, and shipping both
the code and the matching spec edit in the same commit without
Rémy seeing the spec call. That is the failure mode this rule
exists to prevent.

**Which rules apply to which role.** Most rules in this section
apply to every role. The role-specific bits are signaled by the
gates: §2.7 (iteration cycle stages) is the coding agent's loop,
§3 (gauntlet) is run primarily by spec and design agents,
§2.3 (mockups page-per-file) + §2.4 (brand lock-doc pattern) +
§4 (browser fine-tuning) + §5 (mockup convention) are mostly
the design/brand agent's territory, §2.8 (naming discipline)
binds the coding agent at the identifier layer and the spec
agent at the vocabulary layer. §2.9 (sanity sweep) and §6 (boot
sequence) apply to every role.

### 2.1 No parallel "amendments" docs

Every change goes directly into the canonical doc, with an ADR if the
decision is foundational. The amendment-then-merge pattern is what
produced the contradictions this project just escaped. Do not recreate.

If a change feels too big to put directly into the canonical doc, that
means it deserves an ADR + an explicit edit to the doc — not a parallel
amendment file.

### 2.2 Backend is contract

The OpenAPI extract from the running backend (`api/openapi.yaml`)
is **the** source of truth for the API surface — endpoints, request
shapes, response shapes, schemas. Canonical specs and UI specs
consume it; they do not redefine it.

`04_api_conventions.md` covers cross-cutting rules that don't
belong in OpenAPI (auth posture, error format, pagination convention,
idempotency, locked-state semantics, SSE stream pattern, async-job
pattern). It does not duplicate endpoint shapes.

When work (UI or otherwise) requires a backend change, the change
is listed as part of the relevant iteration in `next_iteration.md`
— endpoint name, proposed shape, motivation, acceptance. Backend
changes are decided explicitly, not folded silently into UI specs.

**OpenAPI regeneration is mandatory.** Any iteration whose code
changes touch:

- a new or removed endpoint
- a request or response schema (added/removed/renamed field, type
  change, validation rule change)
- an SSE event topic or payload shape
- error type registry
- locked-state behavior

…must regenerate `api/openapi.yaml` from the running backend as part
of that iteration's acceptance. The iteration is **not done** until
the file is up to date and committed in the same change. The coding
agent owns this; reviewers should reject any iteration that landed
backend changes without regenerating.

Drift between code and `api/openapi.yaml` is a bug, not a deferred
chore. If you find drift, treat it as iteration scope (open a small
janitorial iteration), not a TODO. The iteration-done sanity sweep
(§2.9) catches this mechanically.

### 2.3 Mockups are page-per-file

One `.html` per screen-state. Shared CSS lives in `_shared/`. Big
multi-screen wireframes are dev artefacts; archive them, don't iterate
on them. Naming convention in `UI/mockups/README.md`.

### 2.4 Brand: lock-doc pattern, brand → tokens propagation

Brand identity is canonical in `brand/`. UI references CSS variables
from `UI/mockups/_shared/tokens.css` (which the SvelteKit build
consumes directly — same file, not a parallel copy, so mockups and
shipped code stay in lockstep mechanically), which embody the brand
decisions made in `brand/`. The relationship is one-way: brand is
the source, tokens are the consumer.

**Consumer discipline (no hardcoding).** Downstream code — mockups,
SvelteKit components, marketing site, future F-Droid / App Store
listings, anything visual — consumes via the indirection layer
only:

- *Colors:* `var(--color-*)` from `tokens.css`. Never raw hex
  values in component files (`#A88554`, `#2e8a3f`) — every color
  reference goes through a token.
- *Icons:* import from `brand/identity/*.svg`, always via a thin
  wrapper component (e.g. `<Icon name="home" />` for nav icons,
  `<HoldingIcon type="vault" size={32} />` for holding-type icons)
  so the consumer-side API stays stable as the icon set grows.
  **Never inline SVG paths in feature component files — not even
  once, not even as a "quick copy".** Inlining creates diverging
  copies: the next component that needs the same icon will copy it
  again, detail will drift between copies, and bugs like missing
  spoke lines will appear. The rule: one domain object = one
  component = one source of truth. `HoldingIcon.svelte` is the
  mandatory wrapper for all four holding-type icons; any feature
  component that needs a holding-type icon imports it and passes
  `type` and `size`. The mockup-tier inlining of `wordmark-icony`
  and the nav icons is a workaround for static-HTML / file://
  loading; SvelteKit must import cleanly.
- *Spacing, radii, shadows, type:* `var(--space-*)`,
  `var(--radius-*)`, `var(--shadow-*)`, `var(--font-*)`. Never
  raw values.

The structural check: swapping brand v2 → v3 must be possible by
editing the source artifacts only (palette lock doc + identity/
SVGs) and propagating to `tokens.css`. No grep-and-replace
through component files. If a component needs a value that
doesn't exist as a token, **add the token** (lockstep with the
brand lock doc per the status-driven discipline below) — don't
invent the value in the component.

The brand-side working surface for palette exploration is
`brand/tallykeep_palette_canvas.html`. It is not a lock doc and
not the consumer's source-of-truth — read it only when adding a
new token or understanding the rationale behind a value. The
canonical sources stay the lock docs:
`tallykeep_palette_v<N>_lock.html`, `tallykeep_brand_mark_v<N>_lock.html`,
etc.

**Lock-doc pattern (different from UI mockups, on purpose).** Each
canonical brand artifact (mark, wordmark, future lockup, etc.) gets
**one self-contained big-page HTML lock document** covering form,
sizes, color tokens, anatomy, decisions log, geometry, open items.
Voice/about/tagline content is markdown, same all-in-one shape.

This is a different rule from `UI/mockups/`, which splits one file
per screen-state. Brand and UI have different content shapes — a
brand artifact is a gestalt that only makes sense seen whole; a UI
screen is a unit of state that evolves independently. Don't try to
"normalize" the brand folder into per-aspect files (a `colors.md`,
a `typography.md`, etc.). The lock-doc pattern is the spec.

Naming: `tallykeep_<artifact>_v<N>_<status>.html` for visual lock
docs; `tallykeep_<voice-piece>_v<N>_<status>.md` for voice/copy.
Status is one of `lock` / `draft` / `superseded`. The `tallykeep_`
prefix is kept (brand artifacts are consumed outside this folder
by mockups, frontend, and future marketing — self-identifying
filenames matter). The `v<N>` suffix is intentional and exempt
from the "no _v1 suffix" rule that applies to UI specs — brand
lock docs are versioned checkpoints, not living docs.

**Brand → identity → consumers.** Lock docs embed inline SVG so
they read standalone. Clean SVG files for downstream consumption
live in `brand/identity/`, extracted from the lock docs. Mockups
and frontend code import from `identity/`, never from inline SVG
in lock docs. The duplication is deliberate; sync rule is documented
in `brand/identity/README.md`.

**Status-driven discipline.** Brand v1 is locked as the working
truth. The public-ship event (per ADR-0003) confirms or revises:

- **Pre-public-ship (current):** edits to lock docs allowed; bump
  the version (v1 → v2 lock) when the artifact materially changes.
  Update tokens.css and `identity/*.svg` in lockstep. No ADR for
  v1 → v2 within this phase.
- **At public-ship event:** ADR records the finalized brand. v1
  either stays locked or gets superseded by v2.
- **Post-public-ship:** wordmark / primary color / type system /
  voice principles are foundational. ADR + edit + tokens
  regeneration + downstream propagation (favicon, app icons,
  marketing material).

See `brand/README.md` for the full layout and the brand → tokens
propagation rule. See `brand/identity/README.md` for the SVG
sync rule.

### 2.5 Reconcilability gauntlet

Every flow passes the six-question checklist in §3 before being marked
"designed." No exceptions. The flow's answers are documented in its
section in `UI/mobile.md` / `UI/desktop.md`. This is the structural
answer to "will the product end up at a feature that contradicts its
principles."

### 2.6 Open arbitration is explicit

`pre-implementation.md` lists every decision needing a dedicated
arbitration session. Items do not silently go away; they are closed by
Rémy with a decision and date, then moved to the "Decided" section.

If an agent encounters a question whose answer is not in the spec, the
answer goes into `pre-implementation.md` (if it needs Rémy's
arbitration) or `future_iterations.md` (if it's a capturable idea for
later) — not into the agent's head.

### 2.7 Iteration cycle

The coding agent works one iteration at a time. The active
iteration's sharpened scope lives in `next_iteration.md`. Future
iterations live in `future_iterations.md` as rough captured ideas,
awaiting promotion.

**Stages of a coding iteration:**

1. **Sharpen.** Rémy + agent fill in the iteration template in
   `next_iteration.md` (scope in/out, tasks, acceptance, deps). The
   coding agent does not start work on a half-sharpened iteration.

2. **Code.** Agent implements the scope. Runs the in-tree test
   suites (pytest, frontend tests if any) and the spec sanity
   sweep (`tools/check-spec.ps1` on Windows or `check-spec.sh`
   on Linux/Mac, per §2.9).

3. **Stop and hand off.** When the agent thinks the work is done,
   it **stops**. It posts a "ready for verification" message that
   summarizes:
   - what changed (files, endpoints, schemas, UI)
   - what was tested on the agent's side and the results
   - what's left for Rémy to verify (typically: smoke-test
     `.ps1` against the running backend, Swagger UI manual
     check, hand-test of any new flow)
   - what should happen on greenlight (the closeout list below,
     so Rémy knows what "go" triggers)

   **The agent does not start cleanup work at this stage.** It
   does **not** regenerate `api/openapi.yaml`, does **not** edit
   `next_iteration.md`, does **not** promote the next item, does
   **not** assume "my tests passed" means "shipped." Those are
   post-validation steps. The handoff is a hard stop.

4. **Rémy validates.** Smoke tests (the project's `.ps1` suite
   against the running backend), Swagger UI check, anything else
   relevant to the iteration. He responds with one of:
   - **Greenlight** — "go", "ship it", "OK", or equivalent.
     Proceed to closeout.
   - **Fixes needed** — specific issues. Agent loops back to
     stage 2.

5. **Closeout.** Only on Rémy's explicit greenlight. The agent:
   - Regenerates `api/openapi.yaml` from the running backend if
     this iteration touched any API surface (per §2.2). Manual
     edits to the file are forbidden — if it's wrong, fix the
     backend, restart, regenerate.
   - Edits `next_iteration.md`: removes shipped scope items;
     leaves a brief `## Shipped <date> (commit ...)` record
     under the iteration block, or empties the active section
     back to template if this iteration was the last.
   - Marks any newly validated mockups in `UI/mobile.md` per §5.
   - Runs the sanity sweep (§2.9) one final time. **Must pass.**
   - Commits the closeout in a single change. Commit message
     references the iteration name and the validation context
     ("closeout after Rémy greenlight on YYYY-MM-DD").

6. **Promote.** One item from `future_iterations.md` is sharpened
   into the new active-iteration block. Picking the next item is
   **collaborative** — the agent does not pick alone. If Rémy
   isn't in the conversation, the agent stops here and reports
   "iteration closed; no successor sharpened yet."

**Why the stage-3 stop is mandatory.** The smoke-test suite plus
Swagger UI check is what catches the "agent thinks the API is
right but a real client says otherwise" failure mode. The
agent's own tests don't substitute. Skipping to closeout because
"my tests passed" is the same shape of error as bypassing
OpenAPI regeneration because "I didn't change much."

When a brainstorm session produces a decision: edit the canonical
doc **and** `next_iteration.md` in lockstep, every time. New ideas
not in the active scope go to `future_iterations.md`. No parallel
notes. Foundational decisions get an ADR (per §7); non-foundational
decisions ride in the canonical-doc edit alone.

### 2.8 Naming discipline

Two rules apply to every identifier in the codebase — entity names,
API field names, database column names, event topics, environment
variables.

**No marketing language in the domain.** Vocabulary in code is
durable and shipped under everyone's eyes. Brand voice changes;
identifiers do not. A field is `total_balance_sats`, not `your_money`.

**No abbreviations in identifiers.** `runtime_configuration`, not
`config_kv`. `derivation_index`, not `idx`. `authentication_tag`, not
`auth_tag`. The cost of typing the longer name is paid once; the
cost of decoding the abbreviation is paid by every reader forever.

Industry-standard exceptions are accepted as-is: UTXO, PSBT, BIP,
RPC, BTC, sats, LN, gRPC, SSE, API, KDF, GCM, plus the SQL prefix
`idx_*` for index names. Add to this list with care; brevity is
not a sufficient reason on its own.

### 2.9 Iteration-done sanity sweep

The sweep runs at two points:

- **Coding stage 2** (per §2.7) — agent runs it locally before the
  stage-3 handoff, so the "ready for verification" message reflects
  a clean tree.
- **Closeout stage 5** — agent runs it again after regenerating
  OpenAPI and editing `next_iteration.md`. **Must pass before the
  closeout commit lands.**

Most checks are mechanical and run via `tools/check-spec.ps1`
(Windows) or `tools/check-spec.sh` (Linux/Mac). Either is
sufficient; the two are kept in sync. A few seconds either way.

Checklist:

1. **OpenAPI matches code.** If the iteration touched any
   endpoint, schema, SSE event, error type, or locked-state
   behavior, `api/openapi.yaml` was regenerated from the running
   backend during the closeout commit (§2.7 stage 5). The check
   verifies the file exists and is non-trivial in size; mismatch
   between the file and the live backend surfaces only when Rémy
   re-checks Swagger.
2. **ADR index is current.** Every file in `decisions/NNNN-*.md`
   appears in the index in `decisions/README.md`, and no entry in
   the index points at a missing file.
3. **Mockup index is current.** The `mockups` array near the top
   of `UI/mockups/index.html` matches the set of
   `mobile_*.html` files in `UI/mockups/`. New mockups added,
   removed mockups taken out.
4. **No broken backtick file refs.** Cross-references like
   `\`02_domain_model.md\`` resolve to a real file, in non-archive
   docs. Archive references are exempt; retired-filename
   references in ADRs (kept for historical context) pass via the
   script's allow-list.
5. **Brand → tokens lockstep.** If a brand lock doc was edited
   (color values, typography, spacing scales used by tokens), the
   matching values in `UI/mockups/_shared/tokens.css` were updated
   in the same change, and the file's "Last touched" stamp was
   bumped. The script flags any lock doc whose mtime is newer
   than tokens.css. If `brand/identity/*.svg` was edited, the
   inline SVG in the source lock doc matches.
6. **No "Decided" parallel ledger.** `pre-implementation.md`
   contains only Open items. Closed items left the file (to ADR or
   canonical doc edits, per §2.6).
7. **No NUL-byte trails on edited files.** After any large or
   structural edit on a markdown / yaml / css / html / svg file,
   verify the file ends cleanly — no trailing NUL bytes (`\x00`),
   no truncation mid-sentence, no spurious whitespace block at
   the tail. **This is a recurring failure mode.** Multiple
   sessions have produced files corrupted by tool / linter
   interactions, with hundreds of NUL bytes appended after the
   last real line, or with the tail of the file silently dropped
   mid-paragraph. The sanity sweep grep-checks for `\x00` in
   non-binary spec files; the agent should also eyeball the
   `tail -10` of any file it just substantially rewrote.

If any check fails, the iteration isn't done. Fix in the same
commit, not as a TODO. Drift is a bug, not a chore (per §2.2).

---

## 3. The reconcilability gauntlet

Run every flow through these six questions. Document the answers in the
flow's section in `UI/mobile.md` / `UI/desktop.md`. If a flow fails any
of these, escalate as arbitration.

1. **Trust boundary.** Where does the screen sit (device, browser,
   backend, third-party)? What data crosses each boundary?

2. **Keys and secrets.** Does this flow touch signing material or
   sensitive credentials? Where is each item stored, what's the access
   pattern, what does the backend ever see?

3. **Self-hosted vs hosted.** Does the flow behave differently on a
   self-hosted backend vs a TallyKeep-hosted backend? Both must work,
   and the differences must be honestly disclosed in-app.

4. **Confirmation honesty.** Does the UI ever show a positive end
   state ("sent", "received", "saved", "confirmed") before it's
   actually true? Bitcoin makes this trap easy: tapping Sign isn't
   sending; broadcasting isn't confirming; one confirmation isn't
   final. Every state shown to the user must match what's verifiably
   true on-chain (or in the protocol layer it claims to represent).
   When the truth is probabilistic (mempool inclusion, confirmation
   depth), say so explicitly — and ideally surface the math.

5. **Browser-only fallback.** "Browser build" means desktop browser,
   mobile browser, or PWA installed from any of these — all
   functionally equivalent (no native plugins, no spending keys held).
   The architectural divide that matters operationally is browser vs
   Capacitor, not PWA vs not-PWA. If the user is on the browser build,
   what do they see? Watch-only states or honest "install the app /
   sign externally" gates — never silent breakage or pretend-to-sign.

6. **Open-source and reproducibility.** Does this introduce a
   closed-source dependency, a server-side secret only the TallyKeep
   team has, or anything that would prevent third-party reproducible
   builds?

### Worked example — "Send from Purse"

1. *Trust boundary:* phone screen (UI), phone Keychain/Keystore (key),
   backend (descriptor + UTXO data + tx broadcast). Backend signs
   nothing.
2. *Keys:* Purse seed in iOS Keychain / Android Keystore via Capacitor
   secure-storage. Biometric prompt unlocks. Native plugin signs
   (pending ADR §A in pre-implementation.md). Seed never crosses to
   backend.
3. *Self-hosted vs hosted:* identical from the phone's POV. Both
   backends serve descriptor data and broadcast; neither sees the seed.
4. *Confirmation honesty:* the flow distinguishes four states —
   composed (PSBT created, not signed), signed (PSBT signed, not
   broadcast), broadcast (txid in mempool), confirmed (depth shown
   explicitly). No "Sent ✓" before broadcast acknowledgement; no
   "Confirmed" before on-chain inclusion. Confirmation depth shown
   verbatim, with probability framing if the
   confirmation-probability feature is enabled (see
   `future_iterations.md`).
5. *Browser-only:* compose + review screens render; sign step is gated
   with "this build cannot sign — install the TallyKeep app or sign
   externally with the wallet that holds the key."
6. *OSS:* native signing plugin is in-tree, MIT-compatible. No closed
   deps on the Bitcoin path. (Lightning will reintroduce this question
   when Breez SDK lands; flag there.)

Verdict: reconcilable in current scope (dev / personal-use phase
per ADR-0003).

### Where the irreconcilable corners actually live

The principle-stressing flows in current scope are predictable.
Most are already deferred or have a path:

- **Order placement on custodial providers** — needs trade-permissioned
  API key on backend. Deferred to post-shipping (see
  `future_iterations.md`). Pulling it forward forces a
  custody-adjacent regulatory conversation.
- **Own-LSP for Lightning** — TallyKeep operates routing infrastructure
  seeing payment metadata. Post-shipping. Flag with an ADR when
  pursued.
- **Tax / accounting export on hosted tier** — backend already has the
  data; hosted-tier privacy notice covers it. Reconcilable but
  explicit.
- **Multi-device sync** — only viable as blind-relay encrypted blobs.
  Architecturally clean but client-side crypto discipline is
  load-bearing. Surface in the ADR when the feature is scheduled.
- **Recovery without phone** — Purse seed lives only on phone (or in
  the user's seed backup). Lose both, lose the funds. UX disclosure
  problem, not architectural.

If you find a flow that fails the gauntlet and isn't on this list, stop
and add it to `pre-implementation.md`. Do not paper over.

---

## 4. Browser fine-tuning (no Capacitor yet)

The mobile UI is being fine-tuned in the browser at mobile viewport,
running against the real backend. Capacitor wrap, app-store builds, and
native key signing are deferred to a later phase.

**Constraint:** design the UI for the Capacitor target — the
eventual shipped version, with native plugins, on-device keys,
biometric unlock, push notifications. Run that same UI in the
browser. Where the browser cannot fulfill a Capacitor-only capability
(signing with on-device keys, biometric prompts, push subscriptions,
QR scanning via camera), the screen still exists and the operation
is gated honestly with a message like "this build cannot sign —
install the app or sign externally."

In other words: do not delete screens because the browser can't
fully execute them, and do not pretend the browser has capabilities
it doesn't. The browser version is the Capacitor UI plus honest
gates, not a different UI.

Implementation pattern:

- Native operations (secure storage, biometric, signing, QR scanner,
  push notifications) sit behind a `NativeBridge` interface in the
  SvelteKit code.
- Browser implementation throws or returns fixtures with a visible
  "this build cannot sign — Capacitor needed" banner in dev mode.
- Capacitor implementation lands later and replaces the stub, ideally
  with no UI changes.

This makes the gauntlet enforcement physical: any flow that would
silently work in browser but break in Capacitor (or vice versa) shows
up as a stub call. You feel the irreconcilable corner when you hit it,
not at launch.

---

## 5. Mockup convention

See `UI/mockups/README.md` for naming and index. Summary:

- One file per screen-state.
- `mobile_<flow>_<step-or-state>.html`.
- Header comment lines: title, status (draft / review / validated),
  date last touched, replaces (if redoing an earlier version).
- Imports `_shared/tokens.css` and `_shared/shell.css`.
- **Baseline: 360×800** (mid Samsung Galaxy A, Motorola Moto G —
  broad Argentine mid-range). Mobile-first principle: if it works
  here, it works everywhere.
- **Smoke-test at:** 384×854 (Galaxy A56-class), 390×844 (iPhone),
  412×900 (larger Android).
- **Browsers to check:** Chrome, Samsung Internet (default on the
  ~48% Samsung share), Safari mobile.
- Self-contained for visual review (no JS dependencies).

When a mockup is marked validated, the corresponding section of
`UI/mobile.md` references the file. Cosmetic iteration is fine
afterwards — edit the file and update its date. Changes that touch a
locked principle, reverse a foundational design decision, or affect
security / posture / vocabulary need an ADR plus a fresh draft. See
§7 for the ADR test.

---

## 6. Working agreement for the next agent

This is the **canonical agent boot sequence**. Other READMEs in
the spec tree (`brand/README.md`, `UI/mockups/README.md`, etc.)
point here rather than duplicating it.

When starting a new session:

0. **Identify your role.** Read §2 "Roles" first. Determine
   whether this session is spec-agent work, coding-agent work,
   design/brand-agent work, or triage. If you're not sure, ask
   Rémy before doing anything else — the gates and outputs differ
   per role and "I'll figure it out" is how role-mixing starts.
1. Read `00_README.md` — what TallyKeep is.
2. Read `PROCESS.md` (this) — how we work, including the
   reconcilability gauntlet (§3) and the iteration-done sanity
   sweep (§2.9).
3. Walk the ADR index in `decisions/README.md`; read every ADR.
   These are the foundational decisions that don't get
   re-litigated. They are short and worth the time.
4. Read `next_iteration.md` — that is your scope. If there is no
   active iteration, do not invent one; report current state and
   stop.
5. Read the canonical spec module(s) relevant to your scope.
6. Read `pre-implementation.md` — Open items only; that's what's
   blocked on Rémy's arbitration.
7. `future_iterations.md` is reference only; do not work it.
8. Confirm `api/openapi.yaml` is current; if not, regenerate
   from the running backend.
9. If your scope touches anything user-facing (UI, copy, color,
   icons, app-store assets), skim `brand/README.md` to confirm
   brand status (v1 locked / v2 in flight / etc.).
10. Then proceed.

Iteration handling, in one paragraph: code → run `tools/check-spec.ps1`
(or `.sh`) → **stop and say "ready for verification"** → wait for
Rémy's smoke-tests + Swagger check + explicit greenlight → on
greenlight, regenerate OpenAPI, clean up `next_iteration.md`, run
the sweep one final time, commit. Full sequence with the
mandatory stop is in §2.7; the sanity sweep is §2.9.

Specifically: do **not** regenerate `api/openapi.yaml`, do **not**
edit `next_iteration.md`, do **not** promote the next item before
Rémy gives an explicit go. "My tests passed" is not "shipped."

Defaults:

- **Build mode is the default.** Draft, design, code. Don't preface
  every helpful action with skepticism.
- **Critique mode activates on decisions expensive to reverse.** Tech
  lock-in, custody posture, regulatory surface, brand naming,
  distribution choice. Push back unprompted on these.
- **Reconcilability gauntlet is non-negotiable.** Every flow, every
  time.
- **If a decision is required, add to `pre-implementation.md`.** Do
  not guess and run.
- **Tone:** direct, calibrated, honest. Rémy prefers being corrected
  over being flattered. He responds well to clear pushback with
  reasoning over deference, honest acknowledgement of limits ("I
  don't know" / "I'm guessing" are fine), specific recommendations
  with the trade-offs named, and deliberate convergence over rapid
  approval. He does not respond well to agreement-by-default,
  over-formatting (lists everywhere when prose would do),
  marketing-coded language masquerading as analysis, long preambles
  and recapitulations, or performative humility ("I might be wrong
  but...") that softens substance.

---

## 7. When things change

### The ADR test

ADRs exist for decisions worth remembering and not re-litigating.
The rough test:

- **Edit, no ADR:** cosmetic refinement, label tweak, tap-target
  adjustment, micro-interaction polish, visual iteration on a
  validated mockup, layout reshuffle that doesn't change what's on
  the screen, wording fix in a spec module, adding a tap-to-toggle
  on the unit indicator.
- **ADR + edit:** anything that touches a locked principle, reverses
  a foundational design decision, affects security / regulatory /
  open-source posture, changes vocabulary, or that any future agent
  might be tempted to undo without reading the reasoning. Adding a
  Send button to a screen previously decided to be view-only is the
  canonical example.

Self-test: if the change feels like *let me refine this*, edit. If
it feels like *wait, should we even do this?* — that's an ADR
moment.

### Routing table

| Change type | Where it goes |
|---|---|
| Bug or wording fix in canonical spec | Edit the module directly |
| Decision sharpened during brainstorm | Edit canonical doc + edit `next_iteration.md` in lockstep + ADR if foundational |
| Idea captured but flagged "later" | Entry in `future_iterations.md` |
| Decision overriding an earlier one | New ADR (Status: Supersedes NNNN), edit canonical doc |
| Decision affecting custody, regulatory, or open-source posture | New ADR + explicit user sign-off, edit canonical doc |
| UI screen design (new screen or new draft) | Mockup file + section in `UI/mobile.md` (or `UI/desktop.md`) |
| Cosmetic refinement to a validated mockup | Edit the mockup file, update its date — no ADR |
| Structural change to a validated mockup (touches a locked principle, vocabulary, or trust boundary) | New ADR + fresh draft, update section in `UI/mobile.md` |
| Backend or domain change required by an active iteration | Item in `next_iteration.md` |
| Question requiring dedicated arbitration | Entry in `pre-implementation.md` |
| Question deferable to a later iteration | Entry in `future_iterations.md` |
| New brand artifact (pre-public-ship) | New `tallykeep_<artifact>_v1_lock.html` in `brand/` + extracted SVG in `brand/identity/` + tokens lockstep if values changed |
| Material revision to a locked brand artifact (pre-public-ship) | New `..._v<N+1>_lock.html` (don't edit a published lock doc) + regenerated SVG in `brand/identity/` + tokens lockstep |
| Cosmetic / typo fix in a lock doc | Edit in place — bump nothing |
| Brand finalization (public-ship event) | New ADR recording the final brand version + lockstep edits |
| Wordmark / primary color / type system / voice change (post-public-ship) | New ADR + new `..._vN_lock.html` + regenerated SVG + tokens regeneration + rebuild derived assets |
| Old wireframe / amendment / draft | `archive/` once superseded |

If unsure: ask. Better to surface a small decision than to fork the
spec tree again.
