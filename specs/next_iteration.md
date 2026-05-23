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

### Iteration: Vault detail page

**Started:** 2026-05
**Goal:** Tapping a Vault row on Home opens a per-Holding detail
page that renders honestly for the friction-bearing Vault type —
shape-aware lockup visualization, structured per-cosigner
descriptor display, grouped missing-derivation-metadata advisory,
shape-branched Forget body — while keeping Send and Receive
deferred to the dedicated Vault Send iteration.

#### Scope (in) — required

- **Vault detail page** at `/holding/[id]` for Holdings of type
  `vault`. Two-tab layout (Operations | Settings), SSE-driven
  freshness, single-unit hero with the shared ↻ toggle,
  pull-to-refresh + tap-status-card-to-refresh. Generalised
  chrome from the shipped Strongbox / Purse detail pages.
- **Status card** carries the Vault-type left-stripe (brass,
  `--color-holding-vault: #b89968`) and a **shape-summary
  subtitle** following the per-shape mapping locked in
  `UI/mobile.md §Vault detail`:
  - Single-sig + CLTV → "Single-sig · unlocks ~{Month Year}"
  - Single-sig + CSV → "Single-sig · {N}-{unit} lock per deposit"
  - Pure multisig → "{M}-of-{N} multisig"
  - Multisig + CLTV → "{M}-of-{N} · unlocks ~{Month Year}"
  - Multisig + CSV → "{M}-of-{N} · {N}-{unit} lock per deposit"

  Connection-state dot reads `system.chain.connection_state_changed`,
  cross-type pattern.
- **Lockup bar** — Vault-specific component, placed directly
  below the status card, above the hero. Three segments
  (Available / Sooner / Later) sized by sats-weighted share of
  total Vault sats, ordered by unlock date. Sats-weighted median
  splits Sooner from Later. CLTV is the degenerate single-segment
  case; pure multisig (no timelock) renders **no bar** at all.
  Per the harmonization pass: amount only inside each segment,
  status / date label below (with lock icon prefixing locked-
  segment labels). Tap a segment → scroll Operations to the
  matching UTXO. Tap the bar header chevron → open the expanded
  per-deposit schedule. See
  `mobile_vault_detail_lockup_schedule_expanded.html` for the
  expanded surface.
- **Action row — Send + Receive both greyed.** Cross-type icon
  lock (arrow-and-wallet pair), visually distinguished from the
  active Strongbox state via reduced opacity + neutral fill
  (per the mockup styling). Tap surfaces the deferred-reason
  copy. Per ADR-0010, both ship in the Vault Send iteration.
- **Operations tab.** Activity feed from chain-side `LedgerEntry`
  rows for the descriptor(s). Identical row shape to Strongbox /
  Purse: "Received · BTC" / "Sent · BTC", relative time, optional
  category chip (read-only on this surface), signed amount in the
  active unit. SSE-driven insertion at the top via the existing
  chain-scan event topic. Empty state for fresh Vaults per the
  empty mockup.
- **Settings tab** — flat-list-of-cards (Bucket A cross-type
  restructure parked indefinitely per
  `backlog/holding-detail-settings-reorganisation.md`). Card
  order top to bottom:
    1. **Wallet** — info-only. Line 1: shape-and-lock summary
       (mirrors status card subtitle). Line 2: creation date.
    2. **Display name** — Rename CTA (cross-type lockstep).
    3. **Recovery setup notes** — free-text `recovery_setup_notes`
       + Edit CTA. New per Vault detail. Same shape as
       Strongbox's signing-device-label card.
    4. **Descriptor** — masked at rest; revealed state shows
       the **structured per-cosigner view** with per-xpub
       free-text label affordance, timelock parameters
       (read-only), sub-link to the raw descriptor string,
       Copy CTA on the raw-string state. When any xpub lacks
       `[fingerprint/path]` derivation metadata, an
       **aggregated indicator** lives inside the masked tile
       header ("N cosigners missing metadata") with an inline
       "Fix this" CTA → coming-soon stub. Per-xpub warning
       icons render in the revealed view next to the affected
       rows.
    5. **Auto-sweep rules** — "None" + "Add rule" CTA →
       coming-soon stub. Cross-type lock.
    6. **Instant payments** — permanently gated. Same
       `settings-row--gated` styling as Strongbox; Vault-
       specific copy ("Vault keys live on your hardware
       wallets only. Lightning needs hot keys — activate it
       on a Spending wallet.").
    7. **Danger zone** — Forget only. Body copy per the
       shape-branched variant (multisig: plural "wallets";
       single-sig + timelock: singular "wallet"; otherwise
       identical four-sentence shape).
- **No `purpose=long_term` Settings affordance** per ADR-0018.
  Not in the flat-list card order; the field retired from the
  domain.
- **No `banking.vault_outgoing_warns` opt-out on Vault detail.**
  The user-final-authority feature flag lives in global Settings
  (designed later). Per ADR-0018, a per-Vault opt-out is not
  built proactively.
- **Forget bottom-sheet modal** with the 5-second fill-bar timer
  (cross-type lock from Purse), branched body copy on Vault
  shape, no load-bearing warning panel (no seed on TallyKeep
  side). Wire to the backend Forget endpoint (ADR-0017 cascade).
- **Connection-error toast** — `danger-soft` slide-in, identical
  pattern to Strongbox / Purse. Reuse the shipped component.
  The lockup bar renders the cached state without any error
  decoration; last-known facts are still facts.
- **Home → Vault detail navigation.** Tapping a Vault row on
  Home navigates to `/holding/[id]`. The placeholder route
  shipped in earlier iterations is replaced for `vault`-type
  Holdings.

#### Scope (out) — required

- **Vault Send and Receive flows.** Both greyed; ship together
  in the Vault Send iteration per
  `backlog/vault-send-for-all-shapes.md`.
- **The real "Fix this" remediation sub-flow** for missing
  derivation metadata. Coming-soon stub; ships with the
  Security-health-system iteration per
  `backlog/security-health-system.md`. Same stub Strongbox uses.
- **Centralised Security-health surface.** Out of scope. The
  Vault-detail advisory is per-Holding inline surfacing only;
  the Home aggregator surface remains under arbitration.
- **Auto-sweep rule creation.** Coming-soon stub.
- **Lightning activation flow.** Permanently gated by type
  definition. No flow lives behind that row.
- **Categorization affordances** on Operations entries.
  Read-only chip only; assignment lives on the future
  Accounting page per the cross-type posture.
- **Cross-type Settings-tab restructure** (`backlog/holding-detail-settings-reorganisation.md`).
  Parked indefinitely; Vault ships in the current flat-list
  shape.
- **Strongbox → Vault promotion** migration path. Lives in
  `backlog/vault-send-for-all-shapes.md`.
- **API changes.** None expected. The detail page consumes
  existing endpoints (`GET /api/v1/holdings/{id}`, chain-scan
  SSE topics, ledger-by-holding query) and existing domain
  shapes. The cosigner-label inline editors and the
  recovery-setup-notes editor use the existing Holding-update
  endpoint; if the coding agent finds either field missing from
  the current PATCH shape, **stop and surface to Rémy** before
  scoping a backend addition (do not silently add). No OpenAPI
  regen unless that surfaces.

#### Affected canonical docs

All already updated in lockstep during the 2026-05-22 design
pass (no further canonical-doc edits expected from the coding
agent):

- `UI/mobile.md §Vault detail` — ground truth for screen-by-screen intent.
- `UI/README.md §Holding detail` — Vault per-type bullet updated.
- `holdings/04_vault.md` — ADR-0018 + Vault-detail-page forward-references.
- `02_domain_model.md` — `Purpose.LONG_TERM` removed from the enum.
- `03_data_model.md` — `'long_term'` dropped from the `purpose` CHECK constraint.
- `concerns/outflow.md` — Vault guardrail unconditional on type.
- `decisions/0018-vault-is-long-term-by-type.md` — Accepted.
- `decisions/README.md` — ADR-0018 indexed.

#### Mockup contract — required if iteration touches UI

All 11 files at `Status: validated`, `Date last touched:
2026-05-22`, flipped at the 2026-05-22 design-pass greenlight
per PROCESS.md §2 Design / brand agent. Coding-agent rule
(PROCESS.md §2 Coding agent — Visual contract): read each file
before writing the corresponding screen. The mockup HTML is the
contract; deviation is either a code bug or a spec drift event.

- `UI/mockups/mobile_vault_detail_operations_populated_csv_mixed.html`
  — anchor mockup for the lockup bar's three-segment shape.
- `UI/mockups/mobile_vault_detail_operations_populated_cltv.html`
  — single-segment CLTV variant.
- `UI/mockups/mobile_vault_detail_operations_populated_matured.html`
  — fully-unlocked variant.
- `UI/mockups/mobile_vault_detail_operations_empty.html`
  — fresh Vault, no deposits, bar collapses.
- `UI/mockups/mobile_vault_detail_settings_multisig_csv.html`
  — anchor Settings mockup.
- `UI/mockups/mobile_vault_detail_settings_singlesig_cltv.html`
  — single-sig + CLTV Settings variant.
- `UI/mockups/mobile_vault_detail_settings_missing_metadata.html`
  — Settings with grouped missing-metadata indicator.
- `UI/mockups/mobile_vault_detail_descriptor_revealed_multisig.html`
  — structured per-cosigner reveal state.
- `UI/mockups/mobile_vault_detail_lockup_schedule_expanded.html`
  — post-tap full per-deposit schedule.
- `UI/mockups/mobile_vault_detail_forget_confirm.html`
  — multisig Forget body; single-sig variant documented in
  the header `Replaces:` block.
- `UI/mockups/mobile_vault_detail_connection_error.html`
  — toast + red dot + cached lockup bar.

#### Tasks — required

1. **Read every mockup file in the Mockup contract**, plus
   `decisions/0010-vault-gated-until-multisig.md`,
   `decisions/0018-vault-is-long-term-by-type.md`,
   `holdings/04_vault.md`, and `UI/mobile.md §Vault detail`.
   Required before writing any code; the mockup HTML is the
   visual ground truth, not the prose.
2. **Wire `/holding/[id]` routing for `vault` Holdings.** Add
   the Vault detail page component to the type-dispatch
   alongside Account / Purse / Strongbox. Placeholder removal.
3. **Build the page chrome** — app bar, status card with the
   per-shape subtitle resolver, hero, action row (both greyed),
   sticky tab strip, bottom nav. Reuse Strongbox / Purse-detail
   chrome components; Vault-specifics are the brass stripe
   colour, the subtitle resolver (five shape variants), and the
   action-row gating.
4. **Build the lockup bar component.** Sats-weighted three-
   bucket grouping; handle CLTV (single segment), CSV (three
   segments), pure multisig (no bar), empty Vault (collapsed).
   Amount-only inside segments, status/date labels below per
   the harmonized pattern (lock icon on locked-segment labels).
   Tap-to-scroll-to-UTXO behaviour. Tap-bar-header → expanded
   schedule modal/route. Compute against the current chain tip
   exposed via the existing chain-state SSE topic.
5. **Build the Operations tab.** SSE-driven activity feed, row
   rendering identical to Strongbox / Purse. Empty-state panel
   per the empty mockup.
6. **Build the Settings tab.** Flat-list card order per Scope
   (in). Recovery-setup-notes editor is new (free-text
   textarea, same shape as `signing_device_label`). All
   non-real CTAs route to the parameterised coming-soon stub.
   Verify `recovery_setup_notes` (and the per-xpub
   cosigner-label field used by task 7) are in the existing
   Holding-update PATCH shape via Swagger / the OpenAPI
   contract; if missing, **stop and surface to Rémy** before
   scoping a backend change.
7. **Build the structured descriptor reveal.** Privacy-first
   reveal (masked at rest, structured per-cosigner on tap) +
   per-xpub free-text label affordances + timelock-parameter
   row + sub-link to raw descriptor + Copy CTA on the raw
   state + sensitive-screen flag scaffolded for Capacitor.
   Browser is the dev surface (NativeBridge stub is a no-op
   there).
8. **Build the grouped missing-derivation-metadata advisory.**
   Aggregated count on the masked tile header; per-row icons
   on the revealed view next to affected xpubs. "Fix this" →
   coming-soon stub (same one Strongbox uses).
9. **Build the Forget bottom-sheet modal** with the 5-second
   fill-bar timer + shape-branched body copy (the frontend
   selects the variant by inspecting `subtype_data.total_signers`
   — if 1, singular hardware-wallet sentence; otherwise plural).
   Wire to the backend Forget endpoint (ADR-0017 cascade).
   **No** `NativeBridge.secureStorage.delete` call (no seed on
   TK side for Vault).
10. **Build the connection-error toast** on
    `system.chain.connection_state_changed` transitions. Reuse
    the Strongbox-shipped component. The lockup bar continues
    to render cached state without error decoration.
11. **Run `tools/check-spec.ps1`** (Windows) or
    `tools/check-spec.sh` (Linux/Mac). Must pass before
    stage-3 handoff.
12. **Stop and report** per PROCESS.md §4.4 stage 3. Surface as
    a Decision-needed item any cosigner-label / recovery-notes
    backend gap if task 6 or 7 hit it.

#### Acceptance / done-when — required

- Tapping a Vault row on Home navigates to `/holding/[id]`;
  title bar shows the Holding's display name; status card
  shows the brass stripe and the per-shape subtitle.
- The lockup bar renders correctly across all five Vault
  shapes (the four observable variants — CLTV, CSV mixed,
  CSV matured, multisig no-timelock — exercise the
  Available-only / three-segment / single-segment / no-bar
  code paths). Amount inside segments, status/date labels
  below per the harmonized pattern.
- Tapping a bar segment scrolls Operations to the matching
  UTXO; tapping the bar header opens the expanded schedule
  view with Available / Sooner / Later groupings.
- The Operations tab renders the user's chain-side activity
  for the Vault, newest-first, with sign-based amount
  colour. Empty Vaults render the empty-state panel.
- The Settings tab renders the seven cards in the locked
  order. The descriptor tile's revealed state renders the
  structured per-cosigner view with per-xpub label editors,
  timelock parameters, raw-descriptor sub-link, Copy. The
  missing-metadata indicator renders inside the descriptor
  tile when any xpub lacks origin metadata.
- The Forget bottom-sheet shows the 5-second fill-bar timer;
  Cancel is active immediately; confirming triggers the
  backend Forget call. Body copy matches the multisig or
  single-sig variant per `subtype_data.total_signers`.
- The Lightning row is rendered greyed and disabled with
  Vault-specific copy.
- Disconnecting bitcoind (smoke-test) flips the connection
  dot red and slides the connection-error toast in. The
  cached lockup bar continues to render.
- `tools/check-spec.ps1` passes (8 checks).
- No OpenAPI regen needed (verified: no endpoint, schema,
  SSE topic, error type, or locked-state behaviour changed)
  — unless tasks 6 or 7 surfaced a missing PATCH path, in
  which case the change landed and the regen ran as part of
  the same iteration.

#### Dependencies

- **Forget-cascade iteration shipped** (2026-05-22, per
  `shipped.md`). The Vault Forget bottom-sheet calls the
  unified `DELETE /holdings/{id}` endpoint introduced by
  ADR-0017.
- **Design-pass shipped 2026-05-22.** 11 new mockups
  validated, canonical docs updated, ADR-0018 accepted,
  backlog hygiene done. Coding agent does not need to do any
  spec work to start.
- **No arbitration blockers.** `seed-backup-disclosure` and
  the wider security-health framing remain open in
  `pre-implementation.md`; the Fix-this CTA routes to a
  coming-soon stub.

#### Verification (Rémy)

- Open each of the 11 new mockups at 360×800 in the running
  app; verify chrome consistency with shipped Strongbox /
  Purse detail mockups, copy correctness, lockup-bar shape
  correctness across the four observable variants, and the
  missing-metadata indicator placement (inside the descriptor
  tile, not as a wallet-wide card).
- Hand-test the running app for each Vault shape: lockup bar
  correctness against known unlock dates, status-card
  subtitle correctness, structured descriptor reveal, per-
  cosigner label editing, Forget body copy branch.
- Run the project's `.ps1` smoke-test suite. Walk through
  Swagger UI for any touched endpoint (read-only — none
  expected unless tasks 6 or 7 surfaced one).

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight
the agent: appends a condensed entry to `shipped.md`, clears
the active block in this file back to "No active coding
iteration.", runs `tools/check-spec.ps1`, commits. **No
OpenAPI regen** for this iteration unless tasks 6 or 7
surfaced a missing PATCH path. Full sequence in
`PROCESS.md §4.4` stages 3–5.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only.
