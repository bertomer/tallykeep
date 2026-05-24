# Next iteration

The sharpened, fully-detailed scope of work the coding agent is
working on (or about to start). Updated in lockstep with the
canonical specs whenever the spec evolves.

When this iteration completes:
- Items shipped → condensed entry appended to `shipped.md`,
  removed from this file.
- Canonical specs already reflect the target (no extra "merge"
  work).
- One file from `backlog/` is promoted, sharpened, and becomes
  the new active iteration here; on promotion, the backlog file
  is deleted (per ADR-0014).

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

#### Mockup contract — required if iteration touches UI

<List of mockup files defining the visual ground truth for
this iteration. By the time an iteration is given to the
coding agent, every listed mockup is `Status: validated` —
flipped at the spec/design agent's design-pass greenlight
(see PROCESS.md §2 Design / brand agent — *Output*), not at
coding closeout.

**Coding-agent rule (PROCESS.md §2 Coding agent — Visual
contract):** read every file in this list before writing the
corresponding screen. Copy, spacing, states, affordances,
error variants — the mockup HTML is the contract. Deviation
is either a code bug (fix it) or a spec drift event (stop,
surface to Rémy, edit mockup + ADR if structural). No third
path.>

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

### Iteration: Security-health system v1

**Started:** 2026-05
**Goal:** A user has one persistent place to see every security or
acknowledgment item the system has surfaced about their setup, can
fix or acknowledge them in-flow, and sees critical items propagate
to a red badge that follows them across every page until resolved.

#### Coding-agent guard rails — read these FIRST

Two cross-cutting rules the coding agent MUST observe. These exist
because past iterations drifted on similar points; the mockups
encode them but the rules are stated explicitly to prevent
misimplementation.

**1. ONE shared bottom-nav component, ONE shared app-bar component.**
The bottom nav (Home / Security Health / Activity) and the app-bar
(wordmark left, gear icon right) ARE NOT per-page implementations.
They live in shared layout components and every page that shows them
uses them by reference. If a mockup file's nav glyph or icon looks
different from another mockup's, that's mockup drift to flag back to
spec/design — never a reason to fork the nav implementation. v1
contract: the 3 tabs render identically on every page that shows
the bottom nav; the gear icon renders identically on every page that
shows the app bar. The Security Health tab's red badge is the only
intentional cross-page variation (driven by the SSE-fed
critical-count store).

Tab destinations in v1:

- **Home** → `/` (already shipped).
- **Security Health** → `/security-health` (built this iteration).
- **Activity** → `/activity` (**NOT built this iteration** — the
  Activity / transaction-categorization center is a future
  iteration). Route exists and resolves to a coming-soon stub page
  reusing the visual treatment of `mobile_add_holding_coming_soon.html`
  (parameterized for "Activity"). The tab itself renders normally
  (enabled-inactive) on every page; tap routes to the stub.
- **Gear icon** → `/settings` (minimal landing stub this iteration
  with one row only — "How TallyKeep works" → bottom-sheet principles
  re-read. Full Settings design — server identifier, biometric
  toggle, unpair, feature-flag panel, etc. — is a future iteration).

The coding agent must NOT skip rendering the Activity tab because
its destination page is a stub. The nav has 3 slots; that's part
of the locked global chrome.

**2. Every security-health item has exactly ONE parent page.** This
is the load-bearing contract behind the hybrid surface model
(ADR-0019). The `holding_id` field on `security_health_item` IS the
parent pointer:

- `holding_id IS NULL` → application-level item; parent page is
  **Home**. Inline card renders in the Home "Security health"
  section. Dashboard row-tap → bottom-sheet rendered inside the
  dashboard (the item has no per-Holding detail page to deep-link
  to). v1 example: principles-ack-on-skip.
- `holding_id IS NOT NULL` → per-Holding item; parent page is
  **that Holding's detail page Settings tab**. Inline card renders
  there. Dashboard row-tap → deep-link to that detail page +
  scroll to the inline card. v1 examples: seed-backup (parent =
  the Purse), missing-derivation-metadata (parent = the Strongbox
  or Vault). Per-Holding items NEVER surface in the Home "Security
  health" section — that would duplicate the source-of-truth (per
  ADR-0019 §Discovery channels).

The dashboard's row-tap routing branches on this single field
alone; no per-item-type special casing. The inline-card-rendering
logic on each parent page subscribes to the open-items list,
filters by its own `holding_id` (or NULL for Home), and renders
whatever it finds.

#### Scope (in) — required

**Backend — persistence and API**

- New table `security_health_item(id uuid PK, item_type text,
  holding_id uuid NULL FK, state text, severity text,
  created_at timestamptz, resolved_at timestamptz NULL,
  dismissal_reason text NULL, raw_context jsonb)`. Migration via
  Alembic. Indexes: `(state, severity, created_at desc)` for the
  dashboard Active query; `(state, resolved_at desc)` for History;
  `(holding_id)` for per-Holding lookups; partial index on
  `state='open'` for the badge count. See `03_data_model.md` for
  the canonical schema commentary (added in this iteration's
  spec-sharpen pass).
- Endpoints:
  - `GET /security_health/items?state=open|history` — paginated per
    the existing convention in `04_api_conventions.md`. Items
    sorted by severity descending, then `created_at` descending.
  - `POST /security_health/items/{id}/resolve` body
    `{state: 'resolved_by_fix' | 'dismissed_intentional' |
    'acknowledged', dismissal_reason?: string}`. Returns 422 if
    state transition is invalid; 404 if id missing.
  - `POST /security_health/items/{id}/revive` for user-attested
    items only. Returns 422 with locked code
    `revive_not_allowed_on_system_verified` if the source state
    was `resolved_by_fix`.
- SSE topics (publisher in the backend, subscribers on every
  client): `security_health.item_added`, `security_health.item_resolved`,
  `security_health.item_revived`. Payloads carry the full
  `SecurityHealthItem` schema.
- Per-type item creation hooks integrated into existing services:
  - `purse_service.create_holding` — when `purse_mode IN
    ('on_device_tk_generated', 'on_device_user_imported')`, emit
    a `seed_backup` item (`critical`) with `raw_context.purse_mode`.
  - `strongbox_service.create_holding` — when descriptor has no
    `bip32_derivation` origin (already detected as
    `signing_metadata_present=false` per the Strongbox-wizard
    iteration), emit `missing_signing_metadata` item (`warning`)
    with `raw_context.vendor` from the wizard-captured slug.
  - `vault_service.create_holding` — same shape, one item per
    cosigner whose xpub lacks origin metadata.
  - First-Home-land hook (existing Home GET endpoint): if
    `user.principles_acknowledged_at IS NULL`, emit `principles_ack`
    item (`warning`) idempotently (no duplicate if already open).
- Server-side condition re-checker for `missing_signing_metadata`:
  when a Strongbox / Vault descriptor is updated (via the Fix-this
  flow), re-evaluate and flip any open item for that Holding to
  `RESOLVED_BY_FIX`. SSE `security_health.item_resolved` fires.

**Frontend — global chrome**

- **Bottom-nav restructure: 4 → 3 tabs.** Drop Holdings + More
  tabs. New layout: **Home (1) / Security Health (2) / Activity
  (3)**. Per ADR-0019 + the in-chat 2026-05-24 visualization Rémy
  greenlit. Active-tab indicator (2 px verdigris top stripe) carries
  over from the existing Home mockups.
- **Security Health tab visual.** Bell-icon glyph (Tabler `ti-bell`
  equivalent at 22 px stroke-2 outline; final glyph at mockup
  pass). When the nav-tab's badge subscription reports >0
  `critical`-severity open items, render a **red pill badge**
  positioned at the top-right of the bell glyph: `#b8351b`
  background, white text, 16 px min-width, 1.5 px white border
  to separate from the bell. Badge contents: integer count
  (no "99+" cap needed at v1 — item velocity is low).
- **App-bar gear icon (top-right) → Settings entry-point.** 24 px
  gear glyph, `--color-text-muted` stroke, 44 × 44 px hit target.
  Tap → `/settings` (new route). Visible on every page that shows
  the app bar. Replaces the retired More-tab entry.
- **Minimal Settings landing stub** at `/settings`. One row at v1:
  "How TallyKeep works" → re-shows the three-line Onboarding 01
  principles card content as a bottom sheet (read-only re-read,
  not the acknowledgment flow). Full Settings design lives in the
  dedicated Settings iteration; this stub satisfies the gear
  icon's tap target without expanding scope.

**Frontend — Security Health dashboard at `/security-health`**

- Page chrome: app bar (back chevron + "Security health" title +
  gear icon top-right). Two-tab segmented control: Active |
  History.
- **Active tab.** Subscribes to the three SSE topics; renders the
  list of open items sorted by severity desc then `created_at`
  desc. Row shape: severity dot (red `#b8351b` for critical,
  amber `#a05210` for warning) + item summary (per-type one-line
  copy renderer) + chevron. Tap on per-Holding item →
  deep-link to that Holding's detail page Settings tab,
  scrolled to the inline card. Tap on application-level item →
  bottom-sheet resolution flow rendered in the dashboard.
- **History tab.** Reverse-chronological list of resolved items.
  Row shape: terminal-state verb prefix ("Fixed", "Acknowledged
  as intentional", "Acknowledged") + item summary + relative
  date. For `DISMISSED_INTENTIONAL` and `ACKNOWLEDGED` rows
  (user-attested), a small "Move back to open" affordance opens
  a confirm and calls the revive endpoint.
- **Empty states.** Active-empty: a calm "No open items" panel
  with a one-liner explaining the system's role ("This page
  shows anything TallyKeep wants your attention on. You're all
  caught up."). History-empty: "Nothing has been resolved yet."

**Frontend — per-item resolution flows**

- **Seed-backup item (critical).** Inline card above the Wallet
  card on Purse detail Settings tab (only when this Holding's
  item is `OPEN`). Title: "Back up your recovery phrase". Body
  (locked): "Without a backup, losing this device means losing
  these funds. TallyKeep cannot recover them — the keys live
  only on this phone." Primary CTA: **I've backed it up** →
  resolve with state `acknowledged`. The card also appears on
  the dashboard's Active tab; tapping it from there deep-links
  here.
- **Missing-derivation-metadata item (warning).** Inline card
  already shipped on Strongbox / Vault Settings; the existing
  **Fix this** CTA stops being a coming-soon stub and opens
  the sub-flow at `/security-health/fix-metadata/{holding_id}`:
  - **Path A (recommended): Re-export from your hardware wallet.**
    Per-vendor hint banner (using the slug from `raw_context.vendor`)
    + textarea / file-picker / QR-scan triad for the re-exported
    descriptor. On submit, backend parses, checks
    `bip32_derivation` origin present, verifies derived addresses
    match the existing watched ones. On success: same Holding
    record updated in place, item flips to `RESOLVED_BY_FIX`,
    SSE fires, user routed back to the originating detail page.
    On failure: inline error explaining the address-mismatch
    consequence + "try a different export" CTA.
  - **Path B (advanced): Enter the metadata manually.** Master
    fingerprint input (8 hex chars, case-insensitive, validated
    inline). Derivation path dropdown (BIP 84 `m/84'/0'/0'`
    default + BIP 49 `m/49'/0'/0'` + BIP 44 `m/44'/0'/0'` +
    BIP 86 `m/86'/0'/0'` + Custom escape hatch). On submit,
    backend re-derives the first N addresses with the supplied
    metadata, verifies match against the existing watched
    addresses. Same success / failure as Path A.
  - Secondary CTA on the inline card: **It's intentional** →
    confirm, optional `dismissal_reason` textarea, resolve with
    state `dismissed_intentional`.
- **Principles-ack-on-skip item (warning).** Surfaces in the
  Home "Security health" section + on the dashboard Active tab.
  No inline card on any Holding page (application-level). Tap
  → bottom-sheet inside the dashboard re-shows the three
  principle lines from the Onboarding 01 card (locked content:
  "Open source. The code is public. / No accounts. We don't
  know who you are. / Your keys stay yours. TallyKeep never
  holds them.") + a 4-sentence summary written in
  banking-grade register (no "treasury management" / "be your
  own bank" wording — see the mockup for locked copy). Primary
  CTA: **I understand and accept** → resolve with state
  `acknowledged`, sets `user.principles_acknowledged_at`.

**Frontend — Home updates**

- Existing `mobile_home_empty.html` and `mobile_home_populated.html`
  updated for the new 3-tab nav + app-bar gear icon. No other
  content changes; Holdings list-card chrome unchanged.
- New Home section **"Security health"** — renders inline only
  when at least one application-level item is open (currently
  only the principles-ack-on-skip item; hosted-tier items join
  later). Section header + item-summary rows + "View all" link
  to the dashboard. Absent when no application-level items open.

#### Scope (out) — required

- Strongbox-frequent-usage item, Vault-frequency item, full
  declared-vs-observable surfacing — all deferred indefinitely
  per ADR-0019.
- Blueprint findings UI — post-shipping per
  `backlog/blueprint-analysis.md`.
- Hosted-tier privacy + credentials-backup items — wait for the
  hosted-tier iteration per
  `backlog/hosted-tier-infrastructure.md`.
- Full Settings page design — gear-icon entry + minimal landing
  stub are in scope; full Settings layout / per-row design /
  feature-flag panel land in the dedicated Settings iteration.
- Bottom-nav restructure rolling out to detail-page mockups
  beyond the explicitly listed ones — every mockup with a bottom
  nav technically needs the 3-tab + gear-icon update, but a
  full sweep across the 60+ existing mockups balloons the
  iteration. Detail-page mockup nav updates ride along when
  those screens get next-touched (Send + Receive iteration,
  etc.). Acceptable drift: coding agent renders the new nav
  + gear in the live app regardless; mockup library lags until
  the next touch-up.
- Per-Vault opt-out of `banking.vault_outgoing_warns` (ADR-0018
  decided this is YAGNI until a real user surfaces the case).

#### Affected canonical docs

- `decisions/0019-security-health-system-hybrid-surface.md` — already
  drafted; no further edits during this iteration.
- `UI/mobile.md` — extensive additions during the design pass:
  new "Security health dashboard" section, new "Security health
  item resolution flows" section, Home Notes update reflecting the
  3 → 1 nav structure change, gear-icon notes added to the
  Strongbox / Vault / Purse / Account detail page-chrome
  descriptions.
- `02_domain_model.md` — add the `SecurityHealthItem` entity to
  the domain model with the same shape as the table.
- `03_data_model.md` — add the `security_health_item` table
  schema with column-by-column commentary.
- `04_api_conventions.md` — note the new `security_health.*`
  SSE namespace pattern in the SSE-stream section.
- `concerns/observation.md` — add a short cross-reference noting
  that declared-vs-observable discrepancies are deferred from
  the v1 security-health surface per ADR-0019, with a forward-
  reference to future surfacing.
- `holdings/02_purse.md` — wording update on the seed-backup
  hook ("emits a `seed_backup` security-health item on Holding-
  create").
- `holdings/03_strongbox.md` — same shape, for the
  missing-metadata hook.
- `holdings/04_vault.md` — same shape; per-cosigner emission.

(api/openapi.yaml regenerates at coding-iteration closeout per
ADR-0004; not in the spec-side Affected-canonical-docs list — manual
edits to that file are forbidden per ADR-0004.)

#### Mockup contract — required

Eleven mockup files. By coding-agent handoff, every file is
`Status: validated`. The mockup HTML is the visual contract per
PROCESS.md §2 Coding agent / Visual contract.

Updated (existing files):

- `UI/mockups/mobile_home_empty.html` — 3-tab nav + app-bar gear
  icon. No security-health items shown.
- `UI/mockups/mobile_home_populated.html` — same; populated
  Holdings list unchanged.

New:

- `UI/mockups/mobile_home_populated_security_critical_badge.html` —
  3-tab nav with red badge "2" on Security Health tab. Locks the
  badge visual.
- `UI/mockups/mobile_home_populated_security_health_zone.html` —
  Home inline "Security health" section showing the
  principles-ack-on-skip item.
- `UI/mockups/mobile_security_health_dashboard_active_populated.html`
  — dashboard Active tab with one critical (seed-backup) + two
  warnings (missing-metadata for a Strongbox + principles-ack).
- `UI/mockups/mobile_security_health_dashboard_active_empty.html` —
  "No open items" calm-empty state.
- `UI/mockups/mobile_security_health_dashboard_history.html` —
  History tab with mixed terminal states + revive affordance on
  user-attested rows.
- `UI/mockups/mobile_security_health_principles_ack_bottomsheet.html`
  — bottom-sheet over the dashboard, principles re-show +
  "I understand and accept" CTA.
- `UI/mockups/mobile_security_health_fix_metadata_reexport.html` —
  Path A: per-vendor hint + paste/upload/QR + verification result
  states.
- `UI/mockups/mobile_security_health_fix_metadata_manual.html` —
  Path B: fingerprint input + derivation dropdown + verification.
- `UI/mockups/mobile_purse_detail_settings_on_device_with_seed_backup.html`
  — variant of the existing on_device Settings mockup adding the
  critical seed-backup inline card above the Wallet card.

#### Tasks — required

Ordered for the coding agent.

1. **DB + Alembic.** Create `security_health_item` table +
   migration. Indexes as specified. Domain class
   `SecurityHealthItem` in `02_domain_model.md`'s code mirror.
2. **API surface.**
   - `GET /security_health/items?state=open|history` with
     pagination.
   - `POST /security_health/items/{id}/resolve` with state
     transition validation.
   - `POST /security_health/items/{id}/revive` with
     user-attested check.
3. **SSE topics.** Publisher hooks; subscriber wire-up on the
   frontend store.
4. **Per-type item creation hooks.**
   - `purse_service.create_holding` — `seed_backup` on
     `ON_DEVICE_*` modes.
   - `strongbox_service.create_holding` —
     `missing_signing_metadata` when descriptor has no origin.
   - `vault_service.create_holding` — same, per-cosigner.
   - Home GET handler — `principles_ack` on first land with
     `principles_acknowledged_at IS NULL`.
5. **Server-side re-checker** for `missing_signing_metadata`
   on descriptor update.
6. **Frontend nav restructure.** Drop Holdings + More from
   bottom nav. Add Security Health tab #2 (bell glyph + badge
   subscription). Update active-tab routing logic.
7. **App-bar gear icon.** Component + route to `/settings`.
   Visible on every page with the app bar.
8. **Settings landing stub** (`/settings`). One-row layout
   ("How TallyKeep works" → bottom-sheet principles re-read).
9. **Security Health dashboard** (`/security-health`). Active
   + History tabs. SSE subscription. Per-type item renderer.
10. **Per-item resolution flows.**
    - Seed-backup inline card on Purse detail Settings +
      acknowledge CTA.
    - Missing-metadata Fix-this sub-flow (Path A + Path B) at
      `/security-health/fix-metadata/{holding_id}`. Replace
      the existing coming-soon stub routes.
    - Principles-ack bottom-sheet inside the dashboard.
11. **Home section "Security health"** — conditional renderer
    + SSE-driven update.
12. **Tests** — backend integration tests (table CRUD, item
    creation hooks, SSE emission, revive guard). Frontend
    smoke tests for the new routes.

#### Acceptance / done-when — required

- A fresh `ON_DEVICE_TK_GENERATED` Purse Holding creation
  causes a `security_health.item_added` SSE with severity
  `critical`. The Security Health tab badge shows "1". The
  Purse detail Settings tab renders the seed-backup inline
  card. The dashboard Active tab shows the item at top of the
  list. Tapping **I've backed it up** removes the card,
  decrements the badge to 0 (badge hides), and the row moves
  to History with the verb "Acknowledged".
- A fresh Strongbox creation from a bare xpub creates the
  `missing_signing_metadata` item with severity `warning`.
  The badge does NOT change (warning severity). The dashboard
  Active tab shows the item with an amber dot. The Strongbox
  Settings tab continues to show its inline advisory (already
  shipped). Tap **Fix this** routes to the sub-flow; both
  Path A and Path B successfully verify and flip the item to
  `RESOLVED_BY_FIX`, the inline card disappears, and the row
  lands in History with verb "Fixed".
- The principles-ack item is created on first Home GET with
  `principles_acknowledged_at IS NULL`. It appears in the
  Home "Security health" section AND in the dashboard. The
  Security Health tab badge does NOT change (warning). The
  bottom-sheet acknowledgment moves it to History with verb
  "Acknowledged" and sets `user.principles_acknowledged_at`.
- **Every Active dashboard row shows an "Opened {relative date}"
  stamp** (e.g. "Opened today", "Opened 3 days ago"). Every
  History row shows the terminal-state verb + relative date
  ("Fixed today", "Acknowledged 2 days ago"). Dates are
  client-side relative renderings of `created_at` (Active) and
  `resolved_at` (History); the API ships ISO timestamps and the
  UI formats them.
- A History row for an `ACKNOWLEDGED` item shows the "Move
  back to open" affordance. Tapping it (with confirm) calls
  `revive`, the item returns to Active, the SSE fires, and
  the appropriate inline / Home / badge surfaces re-render.
- The gear icon is visible top-right on Home, Activity,
  Security Health dashboard, and every Holding detail page.
  Tap routes to the Settings landing stub.
- All eleven mockups in the contract render in the live app
  within reasonable pixel tolerance at 360 × 800 viewport.
- Smoke tests (`.ps1` suite) pass; Swagger UI walk-through
  shows the new endpoints with valid request/response shapes;
  `tools/check-spec.sh` clean.

#### Dependencies

- ADR-0019 — already accepted; this iteration implements it.
- ADR-0006 (Purse seed origin) — already implemented; the
  `purse_mode` field this iteration's hook consumes is live.
- ADR-0010 (Vault accept set) — already implemented; the
  per-cosigner descriptor structure this iteration's hook
  parses is live.
- ADR-0017 (Forget is hard delete) — Forget cascades need to
  also delete `security_health_item` rows for the Holding;
  add to the cascade ordering in the existing service.
- No pre-implementation arbitration blocks.
- No backlog items block.

#### Verification (Rémy)

Default UI iteration verification — plus the security-health-
specific items:

- Open the eleven mockups in the Mockup contract list at
  360 × 800 and confirm visual match against the live app.
- Create a Capacitor-side `ON_DEVICE_TK_GENERATED` Purse
  (or use the browser dev stub) and confirm the seed-backup
  flow end-to-end: badge appears, inline card on Purse
  Settings, dashboard row, acknowledge → all surfaces clear.
- Import a Strongbox from a bare xpub and confirm
  missing-metadata appears in dashboard without changing the
  badge. Run both Fix-this paths to terminal `RESOLVED_BY_FIX`.
- Reach Home without acknowledging Onboarding 01 principles
  (reset the user's `principles_acknowledged_at`) and confirm
  the Home section renders + dashboard shows the item +
  bottom-sheet ack resolves it.
- Revive a user-attested History item; confirm the round-trip
  works.
- Confirm Active rows display "Opened {relative date}" and
  History rows display the terminal-state verb + date.
- Swagger UI walk-through of the new endpoints.
- `.ps1` smoke-test suite passes.

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight the
agent: regenerates `api/openapi.yaml` (touches the new
`/security_health/*` endpoints + `SecurityHealthItem` schema),
appends a condensed entry to `shipped.md`, clears the active
block in this file, runs `tools/check-spec.sh`, commits. Full
sequence in `PROCESS.md §4.4` stages 3–5.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only.
