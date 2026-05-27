# Next iteration

The sharpened, fully-detailed scope of work the coding agent is
working on (or about to start). Updated in lockstep with the
canonical specs whenever the spec evolves.

When this iteration completes:
- Items shipped, condensed entry appended to `shipped.md`,
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
**Goal:** <single sentence, what we want to be true at the end>

#### Scope (in) — required

<bullet list of features / changes, sharp, small, fully
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
coding agent, every listed mockup is `Status: validated`,
flipped at the spec/design agent's design-pass greenlight
(see PROCESS.md §2 Design / brand agent — *Output*), not at
coding closeout.

**Coding-agent rule (PROCESS.md §2 Coding agent — Visual
contract):** read every file in this list before writing the
corresponding screen. Copy, spacing, states, affordances,
error variants, the mockup HTML is the contract. Deviation
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
named mockups + hand-test the new flow at 360x800. Add anything
iteration-specific.>

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight the
agent: regenerates `api/openapi.yaml` (if API surface changed),
appends a condensed entry to `shipped.md`, clears the active
block in this file, runs `tools/check-spec.ps1`, commits. Full
sequence in `PROCESS.md §4.4` stages 3-5.

---

## Active iteration

### Iteration: Web admin Tier 1, login + install wizard + paired devices

**Started:** 2026-05-27 (sharpening pass)
**Goal:** Ship the web admin surface so a fresh-install operator
can set the server passphrase, see the infrastructure that came
up, pair the first phone, and afterward manage paired devices,
all from a browser, without CLI. Replace the legacy
`/api/v1/pairing/issue` curl-paste flow with the new admin
pairing surface end-to-end (backend + admin UI + mobile pairing-
key input). Fix the two `unlock-flow-cleanup` bugs that ride
entirely on the web admin side (refresh-redirects-to-passphrase
and server-reboot-no-relock).

#### Scope (in) — required

- **Backend, admin session endpoint.** `POST /api/v1/admin/session`
  validates the typed passphrase against the Argon2id comparison
  material stored at first-boot, issues a short-lived bearer
  session token. Rate-limited per-IP. Per ADR-0020.
- **Backend, admin route protection.** All `/api/v1/admin/*`
  routes (except `session` and `pairing/redeem`) require the
  bearer token. Unauthenticated or expired-token requests return
  401; locked-state returns 423. Per ADR-0020.
- **Backend, first-boot state surface.** A read endpoint reports
  `{ first_boot: true|false }` so the frontend knows whether to
  show the login screen or the install wizard. Surfaces
  infrastructure status (Bitcoin node, Lightning, Tor, pricing) as
  display-only data for the wizard's step 2.
- **Backend, passphrase-set endpoint (first-boot only).** `POST
  /api/v1/admin/passphrase` accepts the initial passphrase, derives
  Argon2id comparison material, stores it, marks first-boot done.
  Returns a session token in the same response (so the wizard
  doesn't need to re-auth immediately).
- **Backend, pairing URL configuration.** `GET
  /api/v1/admin/pairing/url` (authenticated; returns the
  operator-configured URL or null). `PUT /api/v1/admin/pairing/url`
  (authenticated; stores the URL the operator's phone will use,
  returns warning flags for known-unreliable values per
  ADR-0021). Stored in the configuration table as
  `pairing_external_url`.
- **Backend, pairing endpoints per ADR-0021.** `POST
  /api/v1/admin/pairing/qr` (authenticated; returns
  `{ token, qr_payload, key_grouped, expires_at }`; QR uses the
  stored `pairing_external_url` as host prefix; returns
  `409 Conflict { error: "pairing_url_unset" }` when not yet set).
  `POST /api/v1/admin/pairing/redeem` (unauthenticated; accepts
  the 12-char base32 token with or without hyphens,
  case-insensitive; returns per-device credential + device_id).
  Rate-limited per ADR-0021.
- **Backend, paired-devices endpoints.** `GET
  /api/v1/admin/devices` (authenticated; returns list with
  metadata including last_seen). `PATCH
  /api/v1/admin/devices/{device_id}` (authenticated; rename).
  `DELETE /api/v1/admin/devices/{device_id}` (authenticated;
  revoke).
- **Backend, LockMiddleware coverage on `/api/v1/admin/*`.**
  When the backend is locked (post-restart pre-unlock), every
  admin route except `session` returns 423. This is the relock-
  detection mechanism the web admin uses to kick back to the
  login screen on server restart, fixing bug 4 from
  `backlog/unlock-flow-cleanup.md` on the web admin side.
- **Backend, delete the legacy pairing endpoints.** Remove
  `POST /api/v1/pairing/issue` and its legacy redeem
  counterpart per ADR-0021. Nothing public has shipped; no
  deprecation period. After Tier 1 closes, the only pairing
  path is the new admin flow.
- **Frontend, SvelteKit `/admin/*` route group.** Layout that
  suppresses Capacitor / install-PWA / NativeBridge affordances.
  Per ADR-0020.
- **Frontend, login screen.** `web_admin_login.html` is the
  visual contract. Session-token storage in `sessionStorage`
  keyed by origin (fixes bug 3 from
  `backlog/unlock-flow-cleanup.md` on the web admin side). 423
  on any admin request kicks back to this screen with the
  inline "server was restarted" note.
- **Frontend, install wizard (3 steps).** Three routes,
  visual contracts in `web_admin_install_step1_passphrase.html`,
  `web_admin_install_step2_infrastructure.html`,
  `web_admin_install_step3_pair.html`. Step 3 has two cards:
  the URL field (operator confirms / overrides
  `pairing_external_url`, pre-filled from current origin, with
  inline warnings on `localhost` / `.local` / plain-HTTP
  private IP per ADR-0021), and the QR + manual-entry surface
  below it (12-char base32 pairing key grouped `XXXX-XXXX-XXXX`,
  shown next to the URL for manual entry on the phone). QR
  auto-refreshes every 60s; explicit "Refresh now" always
  available. On successful redemption the screen flips to
  "Phone paired" state (visual variant inside the same file is
  acceptable for this iteration; if it grows materially, split
  into a separate mockup).
- **Frontend, paired-devices view.** `web_admin_paired_devices.html`
  visual contract. Includes "Pair a new device" affordance (reuses
  the install wizard's step-3 QR component as a modal or
  sub-route).
- **Mobile, pairing-key input format swap.** The existing manual
  paste UI for the legacy 43-char base64url token updates to
  accept the new 12-char base32 format (with optional `-`
  separators, case-insensitive), and POSTs to the new
  `POST /api/v1/admin/pairing/redeem` endpoint shape per
  ADR-0021. Per-device-credential handling on receipt is
  unchanged. This is the only mobile-side scope in Tier 1; the
  larger mobile work (paired-vs-unlocked surfacing, credential
  read-failure path, SSE handlers) stays in
  `backlog/unlock-flow-cleanup.md`.

#### Scope (out) — required

- **Passphrase rotation, version status, log access.** Tier 2 per
  `backlog/web-admin-tier-2-rotation-and-status.md`. The admin
  sub-nav in `web_admin_paired_devices.html` shows these as
  greyed-out "Tier 2" pills, honest about what's coming and what
  isn't.
- **Mobile-side relock handling, credential read-failure path,
  paired-vs-unlocked state surfacing.** These are the remaining
  scope in `backlog/unlock-flow-cleanup.md`; separate iteration
  after this one closes.
- **WebAuthn or any non-passphrase auth.** Future, not in
  private-ship scope per ADR-0020.
- **Hosted-tier variant of the web admin.** Sharpens when
  hosted-tier infrastructure does, per
  `backlog/hosted-tier-infrastructure.md`.
- **Full daily-use browser PWA / desktop operations console.**
  Defers to pre-public-ship per ADR-0020.
- **Live wiring of the infrastructure-review rows.** Step 2 is
  display-only; the rows are honest about their state but the
  Bitcoin node / Tor / Lightning / Pricing toggles don't yet
  exist as backend capabilities. Per the no-dead-capability
  principle, the rows show status only, not fake controls.

#### Affected canonical docs

- `01_architecture.md`, surfaces table grew a Web admin row;
  network-posture section gained web-admin-auth and pairing-LAN-
  reachability paragraphs (lockstep with this iteration's
  brainstorm 2026-05-27); Configuration model section gained
  the `pairing_external_url` field.
- `UI/README.md`, flow inventory gained a Web admin section;
  Mobile-and-desktop section reframed to acknowledge web admin
  as a third surface and defer the full browser PWA to
  pre-public-ship.
- `UI/web_admin.md`, new module, screen-by-screen prose +
  gauntlet answers for login, install wizard 1/2/3, paired
  devices.
- `decisions/0020-web-admin-surface.md`, new ADR.
- `decisions/0021-pairing-handshake-crypto.md`, new ADR.
- `decisions/0008-passphrase-and-recovery-model.md`, addendum
  noting rotation hosted by web admin.
- `decisions/README.md`, ADR index updated.
- `pre-implementation.md`, `browser-pwa-auth-model` and
  `pairing-handshake-crypto` slugs closed (migrated to ADRs).
- `backlog/unlock-flow-cleanup.md`, edited to note Tier 1
  carved out; remaining scope (backend bug investigation +
  mobile-side work) preserved.
- `backlog/web-admin-tier-2-rotation-and-status.md`, new
  backlog file capturing rotation + version + logs.

#### Mockup contract — required if iteration touches UI

By coding-agent pickup time, every file below is `Status:
validated` (per PROCESS.md §2 Coding agent, Visual contract).
Currently `draft` pending Rémy's design-pass greenlight.

- `UI/mockups/web_admin_login.html`
- `UI/mockups/web_admin_install_step1_passphrase.html`
- `UI/mockups/web_admin_install_step2_infrastructure.html`
- `UI/mockups/web_admin_install_step3_pair.html`
- `UI/mockups/web_admin_paired_devices.html`

Plus the new shared CSS: `UI/mockups/_shared/web_admin_shell.css`
(no status flag; reviewed in lockstep with the mockups).

**Coding-agent rule (PROCESS.md §2 Coding agent, Visual
contract):** read every file in this list before writing the
corresponding screen. Copy, spacing, states, affordances, error
variants, the mockup HTML is the contract. Deviation is either
a code bug (fix it) or a spec drift event (stop, surface to
Rémy, edit mockup + ADR if structural). No third path.

#### Tasks — required

1. Backend, admin session endpoint + token table + middleware
   hookup. Includes the rate-limit per ADR-0020.
2. Backend, first-boot detection + read endpoint + passphrase-
   set endpoint. Argon2id comparison-material storage per
   ADR-0008.
3. Backend, infrastructure-status read endpoint backing
   step 2's display (Bitcoin node sync state, Tor disabled flag,
   Lightning not-configured flag, pricing default).
4. Backend, `pairing_external_url` GET / PUT endpoints +
   URL-validation warning flags per ADR-0021.
5. Backend, new pairing endpoints per ADR-0021. Token table +
   per-device credential table. 12-char base32 token generation,
   QR uses stored `pairing_external_url` as host prefix.
   Rate-limit.
6. Backend, paired-devices CRUD endpoints.
7. Backend, LockMiddleware audit + 423 enforcement on
   `/api/v1/admin/*` (except `session` and `pairing/redeem`).
8. Backend, delete legacy `POST /api/v1/pairing/issue` and its
   redeem counterpart per ADR-0021. Atomic cutover, no
   coexistence.
9. Backend, OpenAPI regenerated at closeout per
   PROCESS.md §4.2 + ADR-0004.
10. Frontend, `/admin/*` route group + layout with Capacitor
    affordance suppression.
11. Frontend, login screen + sessionStorage handling + 423-
    detection-kicks-to-login wiring.
12. Frontend, install wizard 3 steps, including the URL field
    on step 3 + warning rendering + auto-refresh timer on the
    QR.
13. Frontend, paired-devices view + revoke modal + inline
    rename. Reuse the install wizard's step-3 QR + URL
    components for "Pair a new device".
14. Frontend, server-relock detection: any 423 from an admin
    route triggers kick-to-login + inline "server was restarted"
    note.
15. Mobile, swap the pairing-key input from 43-char base64url
    paste to 12-char base32 with optional hyphens (case-
    insensitive); POST to the new admin redeem endpoint.
    Per-device-credential handling unchanged.
16. Backend + frontend + mobile, smoke-test suite extensions
    for the new endpoints + UI flows. Cold-boot pair via the
    web admin, phone scans, credential persists, phone hits
    an authenticated endpoint successfully.

#### Acceptance / done-when — required

- Fresh stack with no passphrase set: opening `/admin/*`
  renders `web_admin_install_step1_passphrase.html`. Submitting
  a passphrase advances to step 2; step 2 "Continue" advances
  to step 3.
- Step 3 of the install wizard refuses to issue a QR until
  `pairing_external_url` is set; the wizard captures the
  operator's URL choice and the QR payload uses it. Warning
  chips render for `localhost`, `.local`, and plain-HTTP
  private-IP values.
- Pairing key on step 3 renders as a 12-char base32 token
  grouped `XXXX-XXXX-XXXX` next to the server URL for manual
  entry on the phone.
- Phone scanning the QR (or typing URL + key by hand on the
  mobile pairing-key field, accepting the new 12-char base32
  format) successfully redeems the token and receives a
  per-device credential. The web admin screen flips to "Phone
  paired" state.
- Web admin "Finish setup" lands on the paired-devices view
  with the just-paired device visible.
- Subsequent visits to `/admin/*` (post-setup) render the
  login screen. Correct passphrase, paired-devices view.
  Wrong passphrase, inline error + rate-limit counter as
  expected.
- Page refresh on the paired-devices view (or any admin route)
  preserves the session: no redirect to login. This is the
  acceptance criterion for bug 3 (`refreshing-redirects-to-
  passphrase`) on the web admin side.
- Backend restart while a session is active: next admin
  request returns 423; frontend kicks to login with the
  "server was restarted" inline note. This is the acceptance
  criterion for bug 4 (`server-reboot-no-relock`) on the web
  admin side.
- Revoking a device deletes the credential row; any subsequent
  request from that device's bearer fails. Validated by
  smoke-test that runs the device's bearer against
  `/api/v1/admin/devices` and expects 401.
- Legacy `POST /api/v1/pairing/issue` is gone (404). OpenAPI
  no longer lists it.
- Mockup contract: each rendered screen matches the
  corresponding `web_admin_*.html` at 1280x800 (Chrome, Firefox,
  Safari).
- OpenAPI regenerated; sanity sweep passes.

#### Dependencies

- **ADR-0020 (Web admin surface), ADR-0021 (Pairing crypto),
  and ADR-0008 Addendum (rotation hosts on web admin)** are
  accepted and committed. Already done in this design-pass
  session.
- **Mockups flipped to `validated`.** Awaiting Rémy's
  design-pass greenlight; once flipped, the coding agent can
  pick this up.
- **`api/openapi.yaml` regeneration at closeout** per
  PROCESS.md §4.2 + ADR-0004.
- Independent from
  `pre-implementation.md per-pod-stack-architecture`, auth
  model and admin endpoints work on either Postgres or SQLite.

#### Verification (Rémy)

- Run the project's `.ps1` smoke-test suite against the
  running backend after the coding agent's stage-3 handoff.
  Suite should cover: fresh-install, set passphrase, capture
  pairing URL, pair device, revoke device, re-pair; relock
  detection (restart backend, observe 423 on next admin
  request); session expiry (token TTL elapses, 401, kick to
  login).
- Swagger UI walk-through of `/api/v1/admin/*` endpoints,
  shapes match ADR-0020 + ADR-0021. Confirm legacy
  `/api/v1/pairing/issue` is gone.
- Hand-test the install wizard end-to-end at 1280x800 in
  Chrome (or your daily browser). Compare each screen against
  its `web_admin_*.html` mockup. Drift is a coding-agent bug,
  not a spec issue at this point (mockups are the contract).
- Test pairing from a mobile device on the same LAN, confirm
  the redeemed credential persists and the phone can hit
  authenticated endpoints with it. Exercise both paths: scan
  the QR, and type URL + 12-char pairing key by hand. The
  legacy curl-paste flow is gone, no fallback to test.

#### Closeout

The agent does **not** start closeout until Rémy gives an
explicit greenlight after stage-4 validation. On greenlight the
agent: regenerates `api/openapi.yaml` (API surface changed,
eight new admin endpoints land and two legacy pairing endpoints
are removed), appends a condensed entry to `shipped.md`, clears
the active block in this file, runs `tools/check-spec.ps1`,
commits. Full sequence in `PROCESS.md §4.4` stages 3-5.

---

The rough sequence ("Onboarding, Add Holding, Holding detail,
Send + Receive, ...") for Rémy's mental model lives in
`backlog/README.md` (Iteration roadmap section), not here.
`next_iteration.md` carries the active block only.
