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
removes shipped scope items from this file, runs
`tools/check-spec.ps1`, commits. Full sequence in
`PROCESS.md §2.7` stages 3–5.

---

## Shipped 2026-05-12 (closeout after Rémy greenlight on 2026-05-12)

### Iteration: Onboarding + Daily Unlock + Home (empty)

Backend: auth layer — device-credential pairing handshake
(`POST /api/v1/pairing/issue`, `POST /api/v1/pairing/redeem`),
passphrase-validate (`POST /api/v1/auth/passphrase-validate`),
device revocation (`DELETE /api/v1/devices/{id}`), auth middleware
(all endpoints except health / pairing / server-info), server-info
endpoint, `paired_device` Alembic migration, and a new
`principles_acknowledged_at` field on the user profile (synced
from the phone immediately after pairing). Unit + integration tests
for all of the above.

Frontend: NativeBridge with `secureStorage` (soft-fallback stub,
no DevGate) and `preferenceStorage` (no-DevGate bridge, Capacitor-
ready); `/onboarding/connect`, `/onboarding/paired` (4-state machine),
`/unlock` (biometric + passphrase fallback), `/home` (empty), root
redirect. Principles acknowledgment persisted via `preferenceStorage`
pre-pairing then synced to backend on successful redeem.

Brand: wordmark-icony viewBox v1 → v2 (tightened from 460 to 450),
source SVG and all five affected mockups updated.

Closeout: `api/openapi.yaml` regenerated from running backend,
`tools/check-spec.ps1` created and passing (6 checks), smoke-test
updated throughout with device-credential auth headers and a
principles-acknowledgment section.

---

## Shipped 2026-05-13 (closeout after Rémy greenlight on 2026-05-13)

### Iteration: Add Holding scaffolding (picker + populated home + backend + Account stub)

Backend: `POST /api/v1/descriptors/validate` (pure parser — xpub,
BIP 380 wpkh / tr / sh-wpkh, multisig variants; single-address
inputs return typed `SINGLE_ADDRESS_INPUT` rejection). Vault
multisig enforcement: `create_vault` validates descriptors and
rejects non-multisig with a typed error. `GET /api/v1/holdings/summary/global`
extended with `meta` (provider display name for Account,
signing-device label for Strongbox, "N-of-M multisig" for Vault),
`scan_status` ("n/a" / "scanning" / "scanned"), and custody-tier
sort (Account → Purse → Strongbox → Vault). Integration tests:
validate endpoint (five cases — p2wpkh, p2tr, wsh multisig, bare
address rejection, garbage rejection), vault single-key rejection.
Smoke test sections 13b (validate happy + error paths) and 13c
(global summary meta/scan_status).

Frontend: `HoldingIcon.svelte` — single source of truth for all
four holding-type SVGs, accepts `type` + `size` props (replaces
the duplicated inline-SVG pattern that caused vault icon drift).
`AddHoldingSheet.svelte` — bottom-sheet picker, four rows in
custody-progression order, cancel pinned above nav bar (z-index
above fixed BottomNav). `/holding/new/[type]/+page.svelte` —
coming-soon stub parameterized by type. `home/+page.svelte` —
populated Holdings list, hero balance sum, picker wiring via
`?sheet=add` URL param. `BottomNav` active indicator: 2 px
verdigris top stripe + semibold + primary-strong color per
validated mockups. `clipboard.paste()` added to NativeBridge.

Closeout: `api/openapi.yaml` regenerated from running backend
(5182 lines). `tools/check-spec.ps1` passing (6 checks). Picker
subtitle and cancel-button style updated to match 2026-05-13
mockup revision.

---

## Shipped 2026-05-14 (closeout after Rémy greenlight on 2026-05-14)

### Iteration: Add Holding — Purse wizard

Frontend: `WizardShell.svelte` reusable 3-step chrome (grid
app-bar, scrollable slot, sticky footer with error region +
CTA, bottom-nav hidden during wizard). `/holding/new/purse`
4-state machine (input → generate → parseback → success):
mode 1 watch-only descriptor import and mode 3
TallyKeep-managed seed generation. BIP39 mnemonic via
`@scure/bip39` + BIP84 tpub derivation via `@scure/bip32`.
zpub/ypub/upub/vpub auto-wrap (base58check version-byte
conversion, frontend-only, no new dependency). Wallet-tips
inline banner (8 sources, copy locked in `UI/mobile.md`).
Inline + redirect error states. Progressive error disclosure
("Show details" toggle). Auto-name per source and script
type. Inline parseback rename. Auth guards on all pages;
home page probes the API on mount instead of redirecting on
stale in-memory `unlocked` flag.

Backend: `ChainScanService.initial_scan` resilience —
`NodeRpcError` caught per-branch (e.g. mainnet xpub on
regtest) so a node rejection doesn't leave `scan_status`
stuck at "scanning". `max(height_at_scan, 1)` sentinel for
genesis-height (height=0) scans. Rescan triggered
automatically by the wizard after holding creation, so the
Home row shows "scanned" by the time the success screen
clears. `DEV.md` developer cheatsheet added.

Testing: 7 unit tests for `ChainScanService` new resilience
paths (`test_chain_scan_service.py`). Smoke-test section 13d
extended: rescan called after `tallykeep_managed` purse
creation, `utxos_discovered` and `height_at_scan` verified.

API surface unchanged — no `api/openapi.yaml` regeneration.

---

## Shipped 2026-05-14 — Treasury rename (closeout after Rémy greenlight on 2026-05-14)

### Iteration: Treasury rename (janitorial)

**Started:** 2026-05-14
**Goal:** Replace every "trading-named" identifier in backend
code, frontend code, API surface, database, and tests with
"treasury-named" equivalents, so that the codebase matches the
canonical-spec vocabulary. Breaking compatibility is acceptable
— TallyKeep is in the dev phase with one user (Rémy); no
back-compat shims.

The product is **not a trading terminal**; auto-sweep and
internal-transfer are treasury management. Real trading
(UniSwap, custodian order placement, P2P acquisition) is
captured for much later and is clearly distinct (per
`00_README.md` line 9). Code-vocabulary alignment with the
spec closes the last surface of the rename done earlier this
session.

#### Scope (in) — required

- **Backend service rename.** `app/services/trading_service.py`
  → `app/services/treasury_service.py`. Class `TradingService`
  → `TreasuryService`. All imports and call sites
  (`routes/`, `workers/`, `tests/`) updated. If there are
  trading-prefixed worker components (e.g.
  `TradingSweepEngine` — verify in code), rename them too. The
  `CustodialPoller`, `CategorizerSuggester`, `SweepEngine`,
  `LiveUpdateBridge`, `AuditReconciler` names stay as-is.
- **Event-topic prefix rename:** `trading.*` → `treasury.*`
  in the event constants module. Specific topics to rename:
  - `trading.custodial.balance_changed` → `treasury.custodial.balance_changed`
  - `trading.custodial.poll_requested` → `treasury.custodial.poll_requested`
  - `trading.sweep.triggered` → `treasury.sweep.triggered`
  - `trading.sweep.executed` → `treasury.sweep.executed`
  - `trading.sweep.failed` → `treasury.sweep.failed`
  Update every publisher, every subscriber, every SSE
  subscription on the frontend, every test that asserts
  against a topic name.
- **Feature-flag key rename** in `DEFAULT_FLAG_VALUES`, the
  flag catalog table, the flag-resolution code, and the
  frontend store:
  - `trading.enabled` → `treasury.enabled`
  - `trading.sweep_policy.enabled` → `treasury.sweep_policy.enabled`
  - `trading.sweep_confirmation.required` → `treasury.sweep_confirmation.required`
  - `trading.bidirectional_sweeps.shown` → `treasury.bidirectional_sweeps.shown`
- **Alembic migration** rewriting `user_profile.feature_flags`
  JSONB keys from `trading.*` to `treasury.*` for every row.
  Idempotent (re-run safe) — read each key, if it starts with
  `trading.` replace the prefix; if a `treasury.*` key already
  exists for the same suffix, prefer it. Tested locally on a
  populated DB.
- **API path rename:** any `/api/v1/trading/...` paths to
  `/api/v1/treasury/...`. Router prefix + every test fixture
  hitting those paths.
- **Frontend updates:** SSE topic subscriptions, Svelte store
  filenames (if any are trading-named), API-client modules,
  route groups, component names that carry "trading".
- **Backend smoke-test suite** (`.ps1`) — every reference to
  `/api/v1/trading/...` and every event-name assertion updated.
- **OpenAPI regen** from the running backend (closeout step).
- **Canonical-spec cleanup** — these notes I left in place
  while keeping back-compat language go stale once the rename
  ships:
  - `holdings/01_account.md` — remove the "(currently
    `TradingService` in the codebase; will rename to
    `TreasuryService`…)" parenthetical. Reads cleanly as
    "the service code never sees ccxt directly."
  - `concerns/feature_flags.md` — remove the paragraph after
    the Treasury flag table that explains the `trading.*`
    namespace asymmetry. Flag keys are clean `treasury.*` now.
  - `01_architecture.md` — verify the event taxonomy section
    references `treasury.*` (it currently lists `trading.*`).
    Update the namespace prefix bullet.

#### Scope (out) — required

- **No product / domain changes.** Rename-only. No new flags,
  no new endpoints, no behavior changes, no schema additions.
- **No back-compat shims.** Old topic names, flag keys, and
  paths stop working in the same commit they're renamed.
- The **unlock-flow cleanup** (separate iteration, captured in
  `future_iterations.md` "Unlock flow cleanup").
- Any work on **trading proper** (custodian order placement,
  P2P swap routes, etc.) — those are out of current scope by
  ADR-0008 / `holdings/01_account.md` regulatory posture and
  `future_iterations.md`.

#### Affected canonical docs

- `holdings/01_account.md` (cleanup of placeholder note)
- `concerns/feature_flags.md` (cleanup of asymmetry-explainer
  paragraph; flag table reads `treasury.*`)
- `01_architecture.md` (event taxonomy prefix list, worker
  component names if any rename)
- `api/openapi.yaml` (regenerated after backend changes)

No new ADR required — the rename is a vocabulary alignment, not
a foundational decision. The conceptual call was already taken
(canonical specs renamed Trading → Treasury earlier this
session); this iteration closes the code-side drift.

#### Affected mockups

None. No UI change visible to the user; flag-gating logic and
SSE-topic filters update internally.

#### Tasks — required

Ordered. Each task is one atomic move with tests passing before
the next starts.

1. Rename `app/services/trading_service.py` →
   `treasury_service.py`. Rename class `TradingService` →
   `TreasuryService`. Fix all imports across the codebase
   until the backend unit-test suite compiles.
2. Run backend unit + integration tests. Fix failures.
3. Rename event-topic constants (`TRADING_CUSTODIAL_BALANCE_CHANGED`
   → `TREASURY_CUSTODIAL_BALANCE_CHANGED`, etc.) and their
   string values. Update every publisher and subscriber.
4. Run the full backend test suite. Fix failures (subscribers
   not finding their topics, etc.) until green.
5. Write the Alembic migration for `user_profile.feature_flags`
   JSONB key rewrite. Apply locally; verify with `SELECT
   feature_flags FROM user_profile`.
6. Rename flag keys in `DEFAULT_FLAG_VALUES` and the flag
   catalog. Update the frontend store that consumes the
   `treasury.*` keys.
7. Rename API route prefix in the router. Update every test
   fixture's URL.
8. Update the `.ps1` smoke-test suite — replace `/trading/`
   path fragments and event-name assertions.
9. Run the full test suite again. Run
   `tools/check-spec.ps1` — fix any orphaned references.
10. **Stop and hand off to Rémy** (per `PROCESS.md §2.7`
    stage 3). Post a "ready for verification" message listing:
    everything changed, on-agent test results, what Rémy needs
    to verify (.ps1 smoke + Swagger walk through `treasury.*`
    + one manual sweep policy creation against the renamed
    flag), and what greenlight triggers.
11. **On Rémy's greenlight only:** regenerate
    `api/openapi.yaml` from the running backend.
12. Apply the canonical-spec cleanup (the three doc edits
    listed under "Affected canonical docs"). Run
    `tools/check-spec.ps1` once more.
13. Edit `next_iteration.md` — move this Active block to a
    `## Shipped <date>` record; clear the active-iteration
    section back to the template placeholder; add the
    `future_iterations.md` "Promoted" breadcrumb.
14. Commit the closeout in a single change. Commit message:
    `Treasury rename closeout after Rémy greenlight YYYY-MM-DD`.

#### Acceptance / done-when — required

- `grep -rn "trading\." backend/ frontend/` returns **zero
  hits** outside (a) test names that explicitly cover the
  migration, (b) historical-record comments referencing the
  old name with explicit explanation.
- `grep -rn "TradingService\|trading_service" backend/`
  returns zero hits.
- `api/openapi.yaml` shows `/api/v1/treasury/...` paths and
  no `/api/v1/trading/...`.
- `concerns/feature_flags.md` flag table uses `treasury.*`
  keys; the asymmetry-explainer paragraph is gone.
- `holdings/01_account.md` reads "the service code never sees
  ccxt directly" without the rename parenthetical.
- `01_architecture.md` event-taxonomy section lists
  `treasury.*` (and other prefixes unchanged).
- `tools/check-spec.ps1` passes (all six checks green).
- Rémy's `.ps1` smoke-test suite passes against the running
  backend.
- A manual sweep policy created via the UI uses the new flag
  namespace (frontend reads `treasury.*` keys correctly,
  backend persists, fires `treasury.sweep.triggered`).

#### Dependencies

None. No pre-implementation arbitration blocking. No prior
iteration to wait on. Self-contained.

#### Verification (Rémy)

- Run the `.ps1` smoke-test suite against the running backend
  with the renamed routes. Expect green.
- Open Swagger UI. Verify `/api/v1/treasury/...` routes exist
  and `/api/v1/trading/...` routes are gone.
- Hand-test: create one sweep policy through the UI. Confirm
  the policy persists, the trigger fires correctly, and the
  SSE stream emits a `treasury.sweep.triggered` event (visible
  in the network panel or via a manual SSE subscription).
- Hand-test: open Settings → Treasury section. Confirm the
  feature-flag toggles operate cleanly and persist (they're
  reading `treasury.*` keys from the migrated JSONB).
- Read the three affected canonical-spec docs — confirm the
  placeholder notes are gone and the prose reads cleanly.

Closeout: `api/openapi.yaml` regenerated from running backend
(5182 lines, `treasury` tag, no `trading` paths). Canonical-spec
cleanup: `holdings/01_account.md` TradingService parenthetical
removed; `concerns/feature_flags.md` flag table updated to
`treasury.*` keys and asymmetry-explainer paragraph removed;
`01_architecture.md` event-taxonomy bullet updated to `treasury.*`.
`tools/check-spec.ps1` passing (6 checks).

---

## Active iteration

No active coding iteration. Next promotion from
`future_iterations.md` when Rémy is ready to start the next
session.

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
6. **Sweep Policy + Treasury view** — Account-originated sweeps in
   the dev-phase scope
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
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          