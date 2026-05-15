# Shipped iterations — changelog

Brief, chronological record of iterations that closed out. The
detailed scope, tasks, and verification checklists live in git
history (search the commit message for the iteration name). This
file exists so `next_iteration.md` stays slim and an agent can
get a quick "what's already done" overview without scrolling
past the active block.

Format: one entry per closed-out iteration. Lead with what
changed. Cite the canonical-doc edits the closeout touched.
Skip the template-shaped detail — that's recoverable from the
commit.

---

## 2026-05-16 — Add Holding · Vault wizard (all initial shapes)

`POST /api/v1/descriptors/validate` response extended with
`timelock_kind` (string | null), `timelock_value` (int | null),
`cosigner_fingerprints` (list of strings), `auto_name` (string | null),
and `parse_category` (`parseback_ready` | `single_key_no_timelock`).
Descriptor adapter extended to recognise the full initial Vault accept
set: single-sig + timelock (`wsh`/`tr` with `and_v(v:after/older, pk)`),
pure multisig (`sh(multi)`, `wsh(multi/sortedmulti)`, `tr(multi_a)`),
and multisig + single timelock. Structural classification guard added:
any descriptor containing `or_i/or_d/or_c/or_b/thresh/sha256/hash256/ripemd160/hash160`
fragments routes to `UnsupportedDescriptorError` before timelock or
multisig detection, preventing multi-path miniscript constructs from
misrouting to Vault parseback. Pre-existing `_now()` datetime bug in
`descriptors.py` fixed (module vs class reference).

`POST /api/v1/holdings/vault` wired with new domain fields:
`timelock_kind`, `timelock_value`, `required_signers`, `total_signers`
(all derived server-side from the descriptor; client-supplied values
overridden). Stored in `subtype_data` JSONB. Auto-name composed
backend-side per five shape templates; collision suffix appended.

Frontend: `/holding/new/vault/+page.svelte` — 3-step wizard covering
all five Vault shape variants. Step 1: descriptor textarea + Paste /
Upload / Scan QR; parse-on-submit routes to parseback (parseback_ready),
warning redirect (single_key_no_timelock → Strongbox), or danger inline
error (unsupported). Step 2: vault-stripe auto-name preview + 4-row
parse-card (Signers required, Signing keys, Script type, Timelock) with
CLTV/CSV formatting helpers + first-three-addresses tap-to-copy. Step 3:
vault-coloured scan-row spinner. Strongbox wizard tightened: descriptors
with `timelock_kind` or `parse_category === parseback_ready` now redirect
to Vault wizard. Holding detail placeholder `/holding/[id]/+page.svelte`
added (tapping a Vault row no longer dead-ends). Home holdings list
wired: tapping any holding row navigates to `/holding/{id}`.

Tests: 4 new descriptor-validate integration tests (single-key
no-timelock, multisig, CLTV, CSV, or_d-rejection); 2 new vault-create
tests (CLTV and CSV timelock metadata persistence); 1 existing test
updated (zero-required-signers rejection). Unit test updated for renamed
`timelock_value` field. OpenAPI regenerated (107 kB).

---

## 2026-05-15 — Add Holding · Strongbox wizard

`POST /api/v1/descriptors/validate` response extended with
`signing_metadata_present: bool` (true when descriptor carries
`[fingerprint/path]` key-origin brackets; false for bare
xpub/zpub wraps). `POST /api/v1/holdings/strongbox` extended with
optional `vendor` (slug from 9 locked values) and optional
`signing_metadata_present` flag, both persisted in
`subtype_data` JSONB. Unknown vendor slug returns 422.

Frontend: `/holding/new/strongbox/+page.svelte` — full 3-step
wizard. Step 1: vendor dropdown (10 options with per-vendor export
hint banners) + descriptor textarea + Paste / Upload file /
Scan QR (Capacitor-only, hidden in browser via
`capabilities.canScanQR()` absence-of-affordance). Bare-key
advisory fires immediately from `bareKeyDetected` derived; full
`signing_metadata_present: false` advisory fires after validate.
Step 2: iron-stripe auto-name preview + parse-card (Derivation row
tinted warning when no signing metadata) + tap-to-copy addresses.
Step 3: success with chain-scan spinner row. Auto-wrap for bare
xpub/zpub/ypub/tpub. `NativeBridge` extended with
`capabilities.canScanQR()` and `filePicker.pick()`.

Tests: 3 new backend integration tests for the validate flag
(`signing_metadata_present` true/false, multisig), 3 for
strongbox-create vendor/metadata persistence and unknown-slug
rejection. Sweep: 17 pre-existing spec drift fixes (stale backtick
refs, `specs/`-prefix gap in allowlist, truncated ADR-0007 tail).
OpenAPI regenerated (138 kB, `signing_metadata_present` in
`ValidateDescriptorResponse`).

---

## 2026-05-14 — Purse-mode rename (janitorial)

Domain entity rename: `PurseSeedOrigin` → `PurseMode`, field
`seed_origin` → `purse_mode`, enum values reorganized around the
on-device-keys axis (`WATCH_ONLY`, `ON_DEVICE_TK_GENERATED`,
`ON_DEVICE_USER_IMPORTED`). The third value is reserved for the
upcoming `purse-upgrade-path` iteration — no code path yet.

Alembic migration rewrote every Purse row's
`holding.subtype_data` JSONB (key + values), idempotent. API
surface renamed; frontend types, stores, wizard request-body
updated; backend smoke-tests updated; OpenAPI regenerated (5184
lines, `PurseMode` schema, no `seed_origin` references).

Canonical-spec cleanup: `02_domain_model.md` class + enum +
section renamed; `03_data_model.md` JSONB comment updated;
`holdings/02_purse.md` two "per seed-origin" phrases updated;
`UI/README.md` Add-Purse field references updated; `UI/mobile.md`
wizard description updated; `concerns/threat_model.md` Mobile
addendum updated; `brand/identity/README.md` SVG row updated +
holding-purse-managed.svg renamed to holding-purse-on-device.svg;
`pre-implementation.md` purse-upgrade-path item updated;
`decisions/0006-purse-seed-origin.md` and
`decisions/0009-key-custody-model.md` got top-of-file vocabulary
notes (append-only). `tools/check-spec.ps1` passing (6 checks).

---

## 2026-05-14 — Treasury rename (janitorial)

Code-vocabulary alignment with the canonical-spec rename Trading
→ Treasury done earlier in the same session. Service rename
(`TradingService` → `TreasuryService`), event-topic prefix
(`trading.*` → `treasury.*`), feature-flag key rename
(`trading.enabled` → `treasury.enabled`, plus three more),
Alembic JSONB migration on `user_profile.feature_flags`, API
path rename (`/api/v1/trading/...` → `/api/v1/treasury/...`),
frontend SSE subscriptions + store filenames updated, smoke-test
suite updated.

Canonical-spec cleanup: `holdings/01_account.md` TradingService
parenthetical removed; `concerns/feature_flags.md` flag table
updated to `treasury.*` and asymmetry-explainer paragraph
removed; `01_architecture.md` event-taxonomy bullet updated.
OpenAPI regenerated (5182 lines, `treasury` tag, no `trading`
paths).

---

## 2026-05-14 — Add Holding · Purse wizard

`WizardShell.svelte` reusable 3-step chrome (grid app-bar,
scrollable slot, sticky footer with error region + CTA,
bottom-nav hidden during wizard). `/holding/new/purse` 4-state
machine (input → generate → parseback → success): mode 1
watch-only descriptor import and mode 3 TallyKeep-managed seed
generation. BIP39 mnemonic via `@scure/bip39` + BIP84 tpub
derivation via `@scure/bip32`. zpub/ypub/upub/vpub auto-wrap
(base58check version-byte conversion, frontend-only).
Wallet-tips inline banner (8 sources). Inline + redirect error
states. Progressive error disclosure. Auto-name per source and
script type. Inline parseback rename. Auth guards on all pages.

Backend: `ChainScanService.initial_scan` resilience —
`NodeRpcError` caught per-branch, `max(height_at_scan, 1)`
sentinel for genesis-height scans. Rescan triggered
automatically by the wizard after holding creation.

Testing: 7 unit tests for `ChainScanService` new resilience
paths. Smoke-test section 13d extended. Developer cheatsheet
(DEV.md in the backend repo) added. API surface unchanged — no OpenAPI regen
needed.

---

## 2026-05-13 — Add Holding scaffolding (picker + populated home + backend + Account stub)

Backend: `POST /api/v1/descriptors/validate` (pure parser —
xpub, BIP 380 wpkh / tr / sh-wpkh, multisig variants;
single-address inputs return typed `SINGLE_ADDRESS_INPUT`
rejection). Vault multisig enforcement: `create_vault` validates
descriptors and rejects non-multisig with a typed error.
`GET /api/v1/holdings/summary/global` extended with `meta`
(provider display name for Account, signing-device label for
Strongbox, "N-of-M multisig" for Vault), `scan_status`, and
custody-tier sort. Integration tests for the validate endpoint
(five cases) and vault single-key rejection.

Frontend: `HoldingIcon.svelte` — single source of truth for all
four holding-type SVGs (replaces the duplicated inline-SVG
pattern that caused vault icon drift). `AddHoldingSheet.svelte`
— bottom-sheet picker, four rows in custody-progression order.
`/holding/new/[type]/+page.svelte` — coming-soon stub
parameterized by type. `home/+page.svelte` — populated Holdings
list, hero balance sum, picker wiring. `BottomNav` active
indicator. `clipboard.paste()` added to NativeBridge. OpenAPI
regenerated (5182 lines).

---

## 2026-05-12 — Onboarding + Daily Unlock + Home (empty)

Backend: auth layer — device-credential pairing handshake
(`POST /api/v1/pairing/issue`, `POST /api/v1/pairing/redeem`),
passphrase-validate (`POST /api/v1/auth/passphrase-validate`),
device revocation (`DELETE /api/v1/devices/{id}`), auth
middleware (all endpoints except health / pairing / server-info),
server-info endpoint, `paired_device` Alembic migration, and a
new `principles_acknowledged_at` field on the user profile.
Unit + integration tests for all.

Frontend: NativeBridge with `secureStorage` (soft-fallback stub,
no DevGate) and `preferenceStorage`; `/onboarding/connect`,
`/onboarding/paired` (4-state machine), `/unlock` (biometric +
passphrase fallback), `/home` (empty), root redirect. Principles
acknowledgment persisted pre-pairing then synced to backend on
successful redeem.

Brand: wordmark-icony viewBox v1 → v2 (tightened from 460 to
450), source SVG and all five affected mockups updated.

Closeout: OpenAPI regenerated, `tools/check-spec.ps1` created
and passing (6 checks), smoke-test updated with device-credential
auth headers and a principles-acknowledgment section.
