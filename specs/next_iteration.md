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

### Iteration: Descriptor classification consolidation

**Started:** 2026-05
**Goal:** Collapse the scattered "given this descriptor, which Holding type fits?" decision onto one backend surface so all three Add-Holding wizards (and future descriptor-ingesting flows) call it instead of re-implementing accept-set checks inline; add specific rejection categories for Lightning-coordinated wallets and multi-path miniscript so the inline-error copy can be honest about *why* a descriptor was rejected.

#### Scope (in) — required

- Extend `POST /api/v1/descriptors/validate` response with two new fields per `concerns/classification.md`: `best_fit: "purse" | "strongbox" | "vault" | null` and `rejection_category` (one of `single_address_input` / `lsp_coordinated_wallet` / `multi_path_miniscript` / `unsupported_form` / `unparseable`, present iff `best_fit` is `null`).
- Move into the backend descriptor adapter: bare-xpub / zpub / ypub / tpub auto-wrap (canonicalisation step before classification); single-address detection (currently inline in Purse / Strongbox / Vault wizards); generic multi-path miniscript detection (today's `UnsupportedDescriptorError` guard surfaces this — extend to populate `rejection_category`).
- Add LSP-coordinated-wallet pattern detector. Today's multi-path miniscript guard returns a single rejection; extend it to recognise the specific Phoenix swap-in-potentiam shape (`or_d(pk(K_lsp), and_v(v:pk(K_user), older(N)))` or structurally equivalent) and similar two-party-with-timelock-fallback constructs, returning `rejection_category: lsp_coordinated_wallet` for those. Generic multi-path constructs that don't match the LSP shape return `multi_path_miniscript`. Specific-before-generic match order.
- Refactor all three Add-Holding wizard frontends (Purse, Strongbox, Vault) to be **thin clients** of the extended endpoint. Per-wizard behaviour: paste-time debounced call (~300ms after last keystroke) → compare `best_fit` to the wizard's own type → match continues to parseback, mismatch shows the existing redirect popup, `null` shows the inline-error variant for the returned `rejection_category`. No per-wizard inline classification logic remains.
- Add one new mockup file `UI/mockups/mobile_add_holding_vault_input_error_inline_lsp_wallet.html` demonstrating the `lsp_coordinated_wallet` rejection copy in the Vault wizard. Cloned from `mobile_add_holding_vault_input_error_inline.html`; body copy from the `classification.md` rejection-taxonomy table.
- Reconcile body copy on the three existing inline-error mockups (`mobile_add_holding_{purse,strongbox,vault}_input_error_inline.html`) with the locked copy strings in `classification.md` if they diverge. Visual structure unchanged; cosmetic refinement only (per PROCESS.md §7 "Cosmetic refinement to a validated mockup — Edit the mockup file, update its date — no ADR").
- Janitorial sweep acceptance: grep the frontend for inline descriptor parsing / classification logic and replace each call site with the endpoint. **No caller in the frontend computes Holding-type fit from descriptor shape itself; all fit decisions come from the endpoint.**

#### Scope (out) — required

- **Send-from-Account source picker integration.** Will consume the classification surface when it ships, but that flow is its own iteration (`backlog/deposit-send-to-account-flow.md`).
- **Purse upgrade path integration.** Same — will consume the surface; not in this iteration (`backlog/purse-upgrade-path-watch-only-on-device-imported.md`).
- **Validation-result caching.** Classification is sub-millisecond pure-CPU; the cache-and-token pattern from the Account wizard is not needed today. The revisit condition is documented in `classification.md §Caching posture`.
- **New endpoint surface.** Everything rides on the existing `POST /api/v1/descriptors/validate`; no `POST /api/v1/descriptors/classify`. Justification in `classification.md §Where it lives`.
- **Per-Holding chapter edits.** `holdings/02_purse.md`, `holdings/03_strongbox.md`, `holdings/04_vault.md` already describe their accept sets; `classification.md` summarises and forward-references those chapters. No edits to the per-type chapters in this iteration unless an accept-set drift is discovered during implementation (treat as spec drift event per PROCESS.md §2).
- **Stale-language sweep on `observation.md`.** The "Multisig descriptors are deferred" framing in `observation.md` is pre-existing drift from the Vault wizard shipping (2026-05-16); fold into a future janitorial pass, not this iteration. (The descriptor-import section's classification cross-ref is updated as part of this iteration; the multisig-deferred prose is left alone.)

#### Affected canonical docs

- `concerns/classification.md` (**new**, landed at spec sharpening 2026-05-24).
- `concerns/README.md` (index updated at spec sharpening).
- `concerns/observation.md` (Descriptor import section cross-refs `classification.md` — updated at spec sharpening).

(The OpenAPI contract file is regenerated at closeout per §4.2 — new response fields on `POST /descriptors/validate`. Tracked in Task #12 and Closeout below; not listed in this block so the §4.6 check #8 mtime sweep doesn't false-positive at sharpening time.)

#### Mockup contract — required if iteration touches UI

The visual contract is the existing six wizard inline-error / redirect mockups plus one new file. All listed mockups are `Status: validated` (the three existing inline-error files were validated at their respective wizard greenlights; the new LSP-wallet variant flips to `validated` at this iteration's design-pass greenlight per PROCESS.md §2 Design / brand agent).

- `UI/mockups/mobile_add_holding_purse_input_error_inline.html` — `single_address_input` rejection in the Purse wizard. Body copy reconciled to `classification.md` table (cosmetic only).
- `UI/mockups/mobile_add_holding_strongbox_input_error_inline.html` — `single_address_input` rejection in the Strongbox wizard. Body copy reconciled.
- `UI/mockups/mobile_add_holding_vault_input_error_inline.html` — `unsupported_form` (residual catch-all) rejection in the Vault wizard. Body copy reconciled.
- `UI/mockups/mobile_add_holding_vault_input_error_inline_lsp_wallet.html` — **new** — `lsp_coordinated_wallet` rejection demonstrated in the Vault wizard. Pattern carries to Purse / Strongbox wizards for the same category (visual treatment identical, body copy from the locked table). Same pattern carries to `multi_path_miniscript` in any wizard.
- `UI/mockups/mobile_add_holding_purse_input_error_redirect.html`, `mobile_add_holding_strongbox_input_error_redirect.html`, `mobile_add_holding_vault_input_error_redirect.html` — `best_fit ≠ wizard.type` redirect popup. No visual change; the popup is now driven by `best_fit` rather than by per-wizard branching.
- Parseback happy-path mockups (`mobile_add_holding_{purse,strongbox,vault}_parseback.html` and the per-shape Vault variants) — no visual change; parseback card is populated from the endpoint response as today.

**Coding-agent rule (PROCESS.md §2 Coding agent — Visual contract):** read every file in this list before writing the corresponding screen. The new LSP-wallet mockup is the visual template for *any* of the new rejection-category variants — same danger palette, same source-hint-banner hidden, same disabled primary CTA, body text per the `classification.md` table.

#### Tasks — required

1. **Backend — classification logic.** In the descriptor adapter, implement `best_fit` derivation (one of `purse` / `strongbox` / `vault` / `null`) and `rejection_category` derivation per `concerns/classification.md` taxonomy. Match order: `unparseable` → `single_address_input` → `lsp_coordinated_wallet` → `multi_path_miniscript` → `unsupported_form` → otherwise valid → classify by accept set. LSP-pattern detector recognises the Phoenix swap-in-potentiam shape (`or_d(pk(K_lsp), and_v(v:pk(K_user), older(N)))` and structurally equivalent two-party-with-timelock-fallback constructs). Generic multi-path detector covers `or_i / or_d / or_c / or_b / thresh / sha256 / hash256 / ripemd160 / hash160` fragments not matching the LSP pattern.

2. **Backend — endpoint extension.** Extend `POST /api/v1/descriptors/validate` response schema with `best_fit` (nullable string enum) and `rejection_category` (nullable string enum, present iff `best_fit` is `null`). Request shape unchanged. Status codes unchanged — the response carries the rejection in-band; the endpoint does not return 4xx for "classified-but-not-supported" cases (rejection is information, not error). Pre-existing 4xx responses for malformed requests stay.

3. **Backend — canonicalisation pull-in.** Move bare-xpub / zpub / ypub / tpub auto-wrap from the three wizard frontends into the backend descriptor adapter, applied as a normalisation step before classification. The wrapped descriptor is reflected back in the response (existing parser-metadata fields).

4. **Backend — integration tests.** One test per rejection category (single_address_input, lsp_coordinated_wallet, multi_path_miniscript, unsupported_form, unparseable); one test per `best_fit` value (purse, strongbox, vault, including the Strongbox-via-metadata-presence vs Purse tie-break); idempotency test (same input twice returns same response); auto-wrap test (bare xpub returns wrapped descriptor + `best_fit` populated).

5. **Frontend — Purse wizard refactor.** `/holding/new/purse/+page.svelte` (and any imported wizard helpers): replace inline bare-xpub auto-wrap, single-address detection, accept-set filter with a paste-time debounced (~300ms) call to `POST /descriptors/validate`. Branch on response: `best_fit === "purse"` → continue to parseback, `best_fit ∈ {strongbox, vault}` → existing redirect popup, `best_fit === null` → inline error with body copy keyed by `rejection_category` from the locked table in `classification.md`.

6. **Frontend — Strongbox wizard refactor.** Same shape. Strongbox-specific: when `best_fit === "purse"` because the descriptor lacks signing metadata, the existing `signing_metadata_present: false` advisory variant still fires (parser metadata is unchanged); the wizard can choose to accept the descriptor with the advisory rather than redirecting, per the existing Strongbox wizard behaviour. Confirm during implementation that this case still routes correctly.

7. **Frontend — Vault wizard refactor.** Same shape. Vault-specific: the `single_key_no_timelock` redirect case (Strongbox-shaped descriptor in the Vault wizard) becomes a `best_fit === "strongbox"` mismatch and routes through the same redirect popup as any other mismatch — the per-wizard `parse_category` branching collapses into `best_fit` comparison.

8. **Mockups — new LSP-wallet variant.** Create `UI/mockups/mobile_add_holding_vault_input_error_inline_lsp_wallet.html` by cloning `mobile_add_holding_vault_input_error_inline.html` and substituting body copy from the `lsp_coordinated_wallet` row of the `classification.md` table. Header status block: `Status: draft` at creation → `validated` at design-pass greenlight (per PROCESS.md §2). Update `UI/mockups/index.html`'s `mockups` array to include the new file (sanity-sweep check #3).

9. **Mockups — copy reconciliation.** Read each existing inline-error mockup and confirm its body copy matches the locked text in `classification.md`'s rejection-taxonomy table for its category. If a mockup's body diverges, update the mockup in place (cosmetic refinement, no ADR per §7). Bump the "Last touched" date in each touched mockup's header block.

10. **Frontend — janitorial sweep.** Grep `src/lib`, `src/routes`, and wherever else descriptor parsing or classification might live, for: bare-xpub regex / startsWith checks, `or_d` / `or_i` / `thresh` string matching, single-address detection (`startsWith("bc1") && length < 70` or similar heuristics), accept-set filters. Each site is either removed (logic moved to backend) or replaced with a call to the classification endpoint. Acceptance: zero remaining sites that compute Holding-type fit from descriptor shape itself.

11. **Smoke tests.** Add `Invoke-WebRequest` cases to the project's `.ps1` smoke-test suite covering the new response fields per category, and update any existing cases that assert the pre-classification response shape.

12. **OpenAPI regeneration at closeout.** Per PROCESS.md §4.2, regenerate `api/openapi.yaml` from the running backend in the closeout commit (not during the stage-3 handoff).

#### Acceptance / done-when — required

- `POST /api/v1/descriptors/validate` returns `best_fit` and `rejection_category` per the `classification.md` taxonomy for every input in the test fixtures. Swagger UI shows the new fields on the response schema.
- Phoenix-style swap-in-potentiam descriptor (test fixture) pasted into any of the three Add-Holding wizards renders the `lsp_coordinated_wallet` inline-error variant with the locked title and body copy.
- Generic multi-path miniscript descriptor (test fixture — e.g. `or_d(pk(A), pk(B))` without the LSP shape) renders the `multi_path_miniscript` variant.
- A single Bitcoin address (bech32, bech32m, P2SH, P2PKH) pasted into any wizard renders the `single_address_input` variant.
- A bare xpub (no `[fingerprint/path]` brackets) pasted into the Strongbox wizard returns from the endpoint with a canonicalised wrapped descriptor + `signing_metadata_present: false` in the parser metadata; the existing Strongbox advisory variant continues to fire.
- A bare xpub pasted into the Purse wizard returns the same auto-wrap; `best_fit === "purse"`; parseback continues.
- A Vault-shaped descriptor (any of the five ADR-0010 β accept-set variants) pasted into the Vault wizard returns `best_fit === "vault"` with all parser-metadata fields (`timelock_kind`, `required_signers`, `total_signers`, `cosigner_fingerprints`, `auto_name`, `parse_category`) populated as today.
- A Strongbox-shaped descriptor (single-key with signing metadata, no timelock) pasted into the Vault wizard returns `best_fit === "strongbox"` and the existing redirect popup fires.
- Frontend grep audit returns zero sites computing Holding-type fit from descriptor shape itself; all fit decisions come from the endpoint.
- Each touched mockup file's body copy matches the locked text in `classification.md`; visual structure unchanged.
- All checks in `tools/check-spec.ps1` / `.sh` pass — the new `classification.md` file is reachable from `concerns/README.md`'s index, the new mockup is in `UI/mockups/index.html`'s array, no broken backtick refs, no tail truncation, mtime sync on touched canonical docs.
- `api/openapi.yaml` regenerated at closeout; condensed entry in `shipped.md`; active block in `next_iteration.md` cleared; the prior backlog file (slug: `descriptor-holding-type-classification-cleanup`) was deleted at spec-sharpening per ADR-0014.
- Reconcilability gauntlet (PROCESS.md §3) passes — no trust-boundary, key-custody, self-hosted-vs-hosted, confirmation-honesty, browser-fallback, or open-source posture is touched. Classification is pure descriptor parsing on the backend, no signing material, no chain calls.

#### Dependencies

- None blocking. ADR-0010 β (the locked Vault accept set) is the structural ground for the `best_fit === "vault"` branch and is consumed as-is.
- No open `pre-implementation.md` items relate to classification.
- The backlog entry (slug: `descriptor-holding-type-classification-cleanup`) was deleted at spec-sharpening per ADR-0014 promotion semantics; git history retains it.

#### Verification (Rémy)

- Smoke-test `.ps1` suite against the running backend — confirms new `best_fit` / `rejection_category` fields on `/descriptors/validate` per the cases in §Acceptance.
- Swagger UI walkthrough of `POST /api/v1/descriptors/validate` — confirms the response schema reflects the new fields with the enum values from `classification.md`.
- Manual hand-test at 360×800: paste a Phoenix-style descriptor (test fixture provided by the coding agent) into each of Purse / Strongbox / Vault wizards in turn; confirm consistent `lsp_coordinated_wallet` inline-error copy across all three.
- Manual hand-test: paste a single Bitcoin address into each wizard; confirm consistent `single_address_input` copy.
- Manual hand-test: paste a bare xpub into the Strongbox wizard; confirm the auto-wrap happens server-side and the existing `signing_metadata_present: false` advisory still fires.
- Visual contract spot-check: open the new `mobile_add_holding_vault_input_error_inline_lsp_wallet.html` mockup and the live LSP-wallet error state in the Vault wizard side-by-side — confirm copy and visual structure match.

#### Closeout

The agent does **not** start closeout until Rémy gives an explicit greenlight after stage-4 validation. On greenlight the agent: regenerates `api/openapi.yaml` (API surface changed — `best_fit` and `rejection_category` fields added to `ValidateDescriptorResponse`), appends a condensed entry to `shipped.md`, clears this active block back to "No active coding iteration.", runs `tools/check-spec.ps1` (or `.sh`) and confirms it passes, commits. Full sequence in `PROCESS.md §4.4` stages 3–5.

---

The rough sequence ("Onboarding → Add Holding → Holding detail
→ Send + Receive → …") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only.
