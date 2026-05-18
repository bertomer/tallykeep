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

## 2026-05-19 — Lock-aware worker + backend-only custodial ACL (ADR-0015 / ADR-0016)

`CustodialPollHandler` retired from the backend entirely — its scheduler thread,
`poll_all_immediately()`, and `poll_provider_immediately()` callsites removed.
The backend now runs no custodial timer threads.

New internal endpoint `POST /api/v1/internal/custodial/{provider_id}/poll-cycle`
(loopback-only, auth-exempt, 423 via existing LockMiddleware) carries the full
cycle logic: decrypt credential from in-memory store, ccxt call, upsert to
`custodial_ledger_entry`, emit `treasury.custodial.*` events, return a small
summary. Worker holds no credentials and imports no ccxt.

Backend startup now emits `system.locked` on the bus (`{topic, timestamp}` only).
`POST /api/v1/unlock` on success emits `system.unlocked` (same shape, no
passphrase or derived material in payload).

Worker gains `CustodialPollScheduler` (per-provider heartbeat timer, configurable
60–3600 s, default 600 s, no lock-state check) and `CustodialPoller`
(orchestrator: subscribes to `poll_tick` / `system.unlocked` / `system.locked`,
dispatches HTTP to the internal endpoint, drops 423 silently, runs catch-up burst
on unlock via `ThreadPoolExecutor`). Both boot cleanly with the backend locked.
Worker also runs an RQ `SimpleWorker` daemon thread consuming the `tallykeep`
queue (signal-handler and SIGALRM death-penalty overridden for daemon-thread
compatibility).

Post-Account-creation poll and manual refresh both migrated to
`one_shot_custodial_poll(provider_id)` RQ jobs. `AccountCreateOut` gains
`kickoff_job_id`. Manual refresh endpoint now returns `202 Accepted + {job_id}`.

`backlog/worker-restart-locked-state-handshake.md` deleted — moot under the
new design: `CustodialPoller` defaults to enabled on boot, so a mid-session
worker restart reactivates dispatch immediately without waiting for a fresh
`system.unlocked` event.

Integration tests added: worker boot lifecycle assertions, catch-up burst
dispatches N calls per active provider, regression guard that `system.*`
payloads never carry forbidden keys.

Canonical docs touched: `api/openapi.yaml` (5559 lines; new internal endpoint,
updated `AccountCreateOut`, 202 on refresh). `specs/decisions/0016-custodial-acl-backend-only.md`
authored as part of spec sharpening prior to this iteration.

---

## 2026-05-18 — Account detail page + custodial polling architecture

Five Account detail page screens shipped: Operations (populated + empty state),
Settings, Forget bottom-sheet modal, and Connection-error toast. The page is
SSE-driven (balance + ledger entries update in realtime), with a status-card
connection-state dot, a unit toggle shared with Home, and six coming-soon stub
routes for deferred sub-flows (Rename, Change polling, Forget → all wired;
Deposit / Withdraw / Convert → stubs). Tapping a Kraken Account row on Home
now navigates to `/holding/[id]`.

**Backend — KrakenAdapter normalization fixes:** `receive` and `spend` Kraken
ledger types now map to `trade` kind (not `deposit`/`withdrawal` — they are
trade-settlement legs, not on-chain movements). `transaction` type is
direction-disambiguated: `direction=in` → `deposit`, `direction=out` →
`withdrawal`. `reward`/`staking` → `other`. Direction-based sign normalization:
ccxt strips signs from amounts; `direction=out, amount>0` is negated.

**Backend — `CustodialPollHandler` architectural refactor:** collapsed two-poller
design into a single self-contained handler in the backend process. Handler owns
its own 15-second scheduler thread (`_run_scheduler` / `_tick`), dispatches poll
threads directly, and no longer subscribes to any Redis event. The worker's
`CustodialPoller` and the `system.custodial.poll_requested` event topic are
retired — handler self-schedules against `polling_interval_seconds` per provider.
`poll_all_immediately()` called from `POST /api/v1/unlock` bypasses the interval
guard so data is current immediately after login. `poll_provider_immediately(id)`
called from `POST /api/v1/holdings/account` after creation so entries are
present before the user reaches the detail page.

**Backend — ledger entries persisted at account creation:** `create_account_holding`
now persists all entries returned by `validate_account_credentials` in the same
DB transaction (upsert via `cle_repo`). Previously these were fetched for the
wizard preview and discarded, leaving a balance/entries mismatch on the detail page.

Canonical docs touched at closeout: `api/openapi.yaml` (5328 lines),
`specs/decisions/0013-custodial-ledger-mirror-posture.md` (ADR-0013).

---

## 2026-05-17 — Account observation scope amendment + ledger polling

ADR-0012 landed end-to-end: the Account credential now requires both Kraken
observation permissions (`Query funds` + `Query ledger entries`), the backend
has the ledger-polling infrastructure, and the wizard Step 2 shows the last 3
ledger entries as an activity preview.

**Backend:** `CustodialProviderAdapter.observation_permission_set` ABC attribute
declared; Kraken adapter declares `{"Query funds", "Query ledger entries"}`.
Validation endpoint rejects on both **overage** and **underage** via unified
`CredentialPermissionMismatch` exception (HTTP 409, `permission_mismatch` code,
`overage: list[str]` + `underage: list[str]` always present). `CustodialPoller`
fully rewritten: ledger-polling via `fetch_ledger_since()` integrated into each
observation cycle; new `custodial_ledger_entry` table (migration `b2c3d4e5f6a7`)
persists entries keyed on `(provider_id, provider_entry_id)`; connection state
machine (`healthy → degraded → unreachable → auth_failed`) with three SSE
topics: `treasury.custodial.cycle_completed` (Option B atomic batch),
`treasury.custodial.ledger_entry_added` (per-entry granular),
`treasury.custodial.connection_state_changed` (on transitions). `ChainListener`
gains `system.chain.connection_state_changed` (bitcoind RPC/ZMQ health
transitions). `CustodialProvider` domain dataclass extended with
`connection_status`, `consecutive_error_count`, `ledger_cursor_at`. Validation
endpoint extended: calls `fetch_ledger_since(None)` (non-fatal) and returns
`recent_ledger_entries: list[LedgerEntryPreview]` + `ledger_total_count: int`
for the Step 2 activity preview.

**Frontend:** Step 1 helper banner updated to instruct ticking `Query funds` +
`Query ledger entries`. Overage danger band corrective copy updated; underage
danger band added ("This API key is missing required permissions"); legacy
`no_read_permission` 422 branch removed. Step 2 parseback gains an activity
preview card (last 3 entries newest-first, `Kind · asset` + relative time,
overflow line "+ N more on your Account page", empty state).

**Tests:** unit tests updated for new `ProviderPermissions` shape
(`overage`/`underage`); `_make_provider()` extended; new tests for
underage-only and combined overage+underage cases. Smoke test section 15.13
updated with documented OK response shape.

Canonical docs touched at closeout: `api/openapi.yaml` (5328 lines,
`LedgerEntryPreview` schema + `AccountValidateOut` extensions).

---

## 2026-05-16 — Add Holding · Account wizard

3-step wizard at `/holding/new/account` lets a user connect a Kraken
account with a read-only API key. Step 1 validates credentials against a
new `POST /api/v1/holdings/account/validate` endpoint (no DB write) and
rejects any key with permissions beyond Query Funds, showing the raw
Kraken permission strings verbatim in the danger band. Step 2 confirms
the parseback (provider, permission level, other-asset cap-and-overflow);
Step 3 shows the polled BTC balance and the capability-gated auto-sweep
suggestion card. Step 2's "Looks right" CTA is the only point that writes
to the DB (`POST /api/v1/holdings/account`). Home now displays Account
holding BTC balance from `last_known_balance_sats`.

Backend: `POST /api/v1/holdings/account/validate` (new); Kraken adapter
permission detection rewritten — primary path via `privatePostGetApiKeyInfo`
(ccxt 4.5.54, bumped from 4.4.57), corrected fallback probes using
`privatePost*` prefix throughout; `binascii.Error` caught in `_call()` and
mapped to `ProviderAuthError`; `NoReadPermissionError` added for keys that
lack Query Funds scope entirely; raw permission strings returned verbatim
so all extra scopes appear in the danger band. `global_holdings_summary`
fixed to read `last_known_balance_sats` for Account rows. `list_holdings`
fixed for Account holdings that require a `CustodialProviderRow` join.

Frontend: validate-first wizard pattern; `loadingLabel="Connecting…"` on
Step 1 CTA; tap-to-clear fires on `onfocus` + `onclick` + `ontouchstart`;
three distinct 422 messages (no read permission / bad credentials / generic);
409 overage message checks `data.detail.code` (FastAPI wraps detail).

Canonical docs touched at closeout: `api/openapi.yaml`.

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
sion.
