# TallyKeep — Working Process

Single source of truth for how specs evolve, where things live, and what
the next agent should expect when picking up this project. Read this
before doing any work.

---

## 1. Document layout

```
specs/
├── 00_README.md ............ product overview, motivations, scope, principles
├── 01_architecture.md
├── 02_domain_model.md
├── 03_data_model.md
├── 04_api_conventions.md
├── 05_savings_layer.md
├── 06_banking_layer.md
├── 07_trading_layer.md
├── 08_lightning_placeholder.md
├── 09_feature_flags.md
├── 10_threat_model.md
├── PROCESS.md .............. this file (working agreement)
├── pre-implementation.md ... items needing dedicated arbitration session
├── next_iteration.md ....... sharpened scope of the active iteration
├── future_iterations.md .... pot of ideas captured for later
├── api/
│   └── openapi.yaml ... frozen backend contract (generated)
├── brand/
│   ├── README.md ........... canonical product identity, layout, status
│   ├── tallykeep_<artifact>_v<N>_lock.html ... one big lock doc per artifact
│   │                       (mark, wordmark, future lockup, etc. — see brand/README.md)
│   ├── tallykeep_<voice-piece>_v<N>_<status>.md ... voice/about/tagline copy
│   ├── identity/
│   │   ├── README.md ....... import-target conventions
│   │   └── *.svg ........... clean SVGs extracted from lock docs (consumed by
│   │                       mockups and frontend code)
│   └── assets/ ............. (when present) built artifacts: favicon.ico,
│                            app-store icons, social cards, etc.
├── decisions/
│   ├── README.md ........... ADR convention
│   └── NNNN-title.md ....... one ADR per foundational decision
├── UI/
│   ├── README.md ........... cross-platform flow inventory + decisions
│   ├── mobile.md ........... mobile platform spec, screen-by-screen
│   ├── desktop.md .......... desktop platform spec (later)
│   └── mockups/
│       ├── README.md ....... naming + index
│       ├── _shared/
│       │   ├── tokens.css .. brand tokens (placeholder)
│       │   └── shell.css ... phone-frame and common layout
│       └── mobile_<flow>_<state>.html ... one page per file
└── archive/ ................ historical iterations, never source of truth
```

Modules 11–14 of the original spec retire in the consolidation merge.
Their content redistributes per ADR-0002. Modules 00–10 remain canonical
product description.

The split between **target product** (canonical specs `00`–`10`,
`decisions/`, `UI/`, `api/`) and **path to target** (`next_iteration.md`,
`future_iterations.md`, `pre-implementation.md`) is deliberate. Target
evolves in place; path cycles through iterations.

Anything not in canonical or `decisions/` is either iteration scope, a
working draft, an arbitration item, or archived history. The next agent
should never need to read `archive/` to do its job.

---

## 2. Core rules

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
janitorial iteration), not a TODO.

### 2.3 Mockups are page-per-file

One `.html` per screen-state. Shared CSS lives in `_shared/`. Big
multi-screen wireframes are dev artefacts; archive them, don't iterate
on them. Naming convention in `UI/mockups/README.md`.

### 2.4 Brand: lock-doc pattern, brand → tokens propagation

Brand identity is canonical in `brand/`. UI references CSS variables
from `UI/mockups/_shared/tokens.css` (and later the SvelteKit
equivalent), which embody the brand decisions made in `brand/`. The
relationship is one-way: brand is the source, tokens are the
consumer.

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

Naming: `tallykeep_<artifact>_v<N>_lock.html` for visual lock docs;
`tallykeep_<voice-piece>_v<N>_<status>.md` for voice/copy. The
`v<N>` suffix is intentional and exempt from the "no _v1 suffix"
rule — these are versioned checkpoints, not living docs.

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

The coding agent works one iteration at a time. The active iteration's
sharpened scope lives in `next_iteration.md`. Future iterations live in
`future_iterations.md` as rough captured ideas, awaiting promotion.

When an iteration completes:

- Items shipped → removed from `next_iteration.md`.
- OpenAPI regenerated.
- Mockups marked validated where applicable.
- One item from `future_iterations.md` is promoted, sharpened, and
  becomes the new active iteration.

When a brainstorm session produces a decision: edit the canonical doc
**and** `next_iteration.md` in lockstep, every time. New ideas not in
the active scope go to `future_iterations.md`. No parallel notes.

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
RPC, BTC, sats, LN, gRPC, SSE, API, KDF, GCM. Add to this list with
care; brevity is not a sufficient reason on its own.

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

Verdict: reconcilable in v1.

### Where the irreconcilable corners actually live

The principle-stressing flows in v1's scope are predictable. Most are
already deferred or have a path:

- **Order placement on custodial providers** — needs trade-permissioned
  API key on backend. Deferred to v2. Pulling it forward forces a
  custody-adjacent regulatory conversation.
- **Own-LSP for Lightning** — TallyKeep operates routing infrastructure
  seeing payment metadata. v2+. Flag with an ADR when pursued.
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

When starting a new session:

1. Read `00_README.md` and `PROCESS.md` (this).
2. Read `next_iteration.md` — that is your scope.
3. Read the canonical spec module(s) relevant to your scope.
4. Read `pre-implementation.md` to know what's blocked.
5. `future_iterations.md` is reference only; do not work it.
6. Confirm `api/openapi.yaml` is current; if not, regenerate
   from the running backend.
7. If your scope touches anything user-facing (UI, copy, color,
   icons, app-store assets), skim `brand/README.md` to know
   whether brand is locked or still in placeholder mode.
8. Then proceed.

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
