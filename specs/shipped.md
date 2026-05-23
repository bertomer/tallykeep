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

## 2026-05-22 — Forget cascade implementation + Account wizard setup-token cache

**Forget cascade (all 4 Holding types).** `DELETE /api/v1/holdings/{id}` now accepts
Account, Purse, Strongbox, and Vault. Transaction cascade order: addresses → UTXOs →
descriptors → payment_requests / invoices → (Account only) custodial ledger entries +
custodial provider + API-credential wipe → ledger_entry_holding_link orphan cleanup →
holding row. `ON DELETE SET NULL` FK change for
`custodial_ledger_entry.linked_counterparty_holding_id` — sweep-destination Accounts retain
their incoming entries after the source Holding is Forgotten, with the back-pointer NULLed.

**Schema migration (ADR-0017).** `holding.is_archived` column dropped; two partial indexes
recreated without the `WHERE is_archived = FALSE` filter; FK posture change above. Two-release
deprecation cycle waived per ADR-0017 (personal-use phase, no external users on current
schema).

**Retired routes.** `POST /api/v1/holdings/{id}/archive` and
`DELETE /api/v1/descriptors/{id}` removed. FastAPI returns 404 for these paths (no route
template — 404, not 405). `include_archived` query parameter dropped from `GET /holdings`
and `GET /holdings/summary/global`. `is_archived` field dropped from `HoldingResponse`.

**Frontend wiring.** Forget confirm handlers on Account, Purse, and Strongbox detail pages
switched from `POST …/archive` to `DELETE …/{id}`. Body copy refreshed on all three to match
validated mockup variants (5 sentences Account, 4 Strongbox, 4 Purse WATCH_ONLY, 5 Purse
ON_DEVICE_*). Purse Forget branches on `purse_mode`.

**Account wizard setup-token cache.** `POST /holdings/account/validate` now returns a
`setup_token` UUID in its response. `POST /holdings/account` accepts an optional
`setup_token`; when present and valid (15 min TTL, single-use), the second Kraken
`validate_account_credentials` call is skipped — 8 Kraken round-trips reduced to 4. Fallback
to full re-validate if token is absent, expired, or adapter_id mismatch. In-memory dict safe
because uvicorn runs single-process (no `--workers`). Three new integration tests.
Smoke-test `Invoke-WebRequest` calls hardened with `-UseBasicParsing`.

Canonical docs touched at closeout: `api/openapi.yaml` (regenerated; retired routes +
schemas removed, `setup_token` fields added).

---

## 2026-05-20 — Strongbox detail page + Purse descriptor Copy retrofit

Strongbox detail page shipped at `/holding/[id]` for `strongbox`-type Holdings. Two-tab
layout (Operations | Settings), SSE-driven freshness, iron-stripe (`#4a4d4f`) status card
with a `signing_device_label`-driven subtitle falling back to "External signing device". Hero
balance, Send + Receive action row (both coming-soon stubs for this iteration). Operations
tab renders chain-side ledger entries newest-first with sign-based amount colour; empty-state
panel for fresh Strongboxes.

Settings tab: conditional missing-signing-metadata advisory card (`warning-soft` background,
"Fix this" CTA → coming-soon stub); Wallet info-only row (creation date); Display name with
inline Rename form; Signing device label with inline Edit form; Descriptor reveal (masked at
rest, Show → full inline card with Copy + Hide); Auto-sweep rules (coming-soon); Instant
payments row permanently gated (`settings-row--gated`) with Strongbox-specific copy; Danger
zone with Forget only. Forget bottom-sheet has the 5-second fill-bar countdown timer. No
seed-destruction warning panel (TK never holds Strongbox signing material). Connection-error
toast on `system.chain.connection_state_changed` disconnection.

**Backend addition:** `signing_device_label` (nullable str, maxLength 200) added to
`HoldingUpdate` PATCH schema and wired through repository (`subtype_data` JSONB partial
update via `MISSING` sentinel from Python stdlib), service, and endpoint
(`model_fields_set` detection). Strongbox-only guard; passing this field on a
non-Strongbox Holding returns 422. Three integration tests added.

**Purse descriptor Copy retrofit:** Copy CTA added to the revealed-descriptor state on the
Purse Settings tab (both WATCH_ONLY and ON_DEVICE modes). The privacy-first-reveal no-Copy
lock applies to signing material only, not descriptors.

**Account Rename moved out of Danger zone:** standalone "Display name" section inserted
between Provider and Observation key, matching the Purse / Strongbox pattern. Danger zone
now contains only "Forget this Account."

**Modal z-index fix:** `modal-backdrop` raised to `z-index: 110`, `modal-sheet` to 111
(clearing BottomNav's `position: fixed; z-index: 100`). Affects all Holding-type modals.

Four new coming-soon stub routes: `strongbox/[id]/send`, `strongbox/[id]/receive`,
`strongbox/[id]/sweep/add`, `strongbox/[id]/fix-metadata`.

Canonical docs touched at closeout: `api/openapi.yaml` (156187 bytes; `signing_device_label`
in `HoldingUpdate` and `HoldingResponse`).

---

## 2026-05-20 — Purse detail page + Account Forget timer + unlock consolidation

Purse detail page shipped at `/holding/[id]` for `purse`-type Holdings. Two-tab layout
(Operations | Settings), SSE-driven chain-state freshness, auburn-stripe status card with
mode subtitle ("Watch-only" / "Spending wallet"), hero with shared unit toggle, Send +
Receive action row. Operations tab renders chain-side ledger entries newest-first with
sign-based amount colour; empty-state panel for quiet Purses. Settings tab branches on
`purse_mode`: WATCH_ONLY hides the Recovery-phrase row; ON_DEVICE variants show it
routing to a coming-soon stub. Descriptor reveal is privacy-first (masked at rest, full on
tap). Forget bottom-sheet has a 5-second fill-bar countdown timer, per-mode warning copy,
and explicit inline error panel if `secureStorage.delete` fails before the backend call.

The same 5-second Forget timer also landed on the Account detail Forget modal.

Send-blocked screen shipped at `/holding/purse/[id]/send` for WATCH_ONLY mode (two
option cards: PSBT-export and Add-keys, both routing to coming-soon stubs). All other
Purse sub-flow routes (Receive, Recovery, Lightning, Auto-sweep, PSBT-export, Add-keys)
are coming-soon stubs.

**Unlock consolidation (post-greenlight fix):** `POST /api/v1/unlock` removed — it was
unreachable in practice (LockMiddleware allowlist let it through, but the phone UI never
called it). `POST /api/v1/auth/passphrase-validate` is now the single unlock path: added
to the LockMiddleware allowlist, calls `store.unlock()` instead of
`store.validate_passphrase()`, and emits `system.unlocked` on success. Rate limiting
stays on this path. The split between "server unlock" and "phone auth" was an abstraction
with no real-world caller; collapsing it fixed the `-KeepDb` restart flow where the server
started locked and the phone had no working path to unlock it.

**Dev tooling:** the dev-reset.ps1 / dev-reset.sh scripts gain `-KeepDb` / `--keep-db` (wipes
Redis + bitcoind, preserves postgres) and `-ResetPassphrase` / `--reset-passphrase`
(clears crypto_parameters + canary so the store can be re-initialized without a full
wipe). The `purse_mode` case mismatch fixed: backend enum values are lowercase
(`on_device_tk_generated`, `watch_only`); UI comparisons were against uppercase strings.

Canonical docs touched at closeout: `api/openapi.yaml` (5631 lines; `POST /api/v1/unlock`
removed).

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

backlog/worker-restart-locked-state-handshake.md deleted — moot under the
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
`holdings/02_purse.md` vocabulary lockstep (PurseMode terminology, no seed-origin language remaining).
