# UI — Web admin platform spec

This is the web admin platform spec. Cross-platform decisions
(Holding type vocabulary, brand, gauntlet) live in `UI/README.md`.
This file describes the operator-facing admin surface introduced by
ADR-0020, screen by screen, with the reconcilability gauntlet
answers attached.

## Status

The web admin spec lands with its Tier 1 iteration (login + install
wizard + paired-devices + revoke). Tier 2 (passphrase rotation,
version status, log access) sharpens at
`backlog/web-admin-tier-2-rotation-and-status.md` and adds
sections to this file when promoted.

## What lives here

Per-flow sections with the same shape as `UI/mobile.md`:

```
## <Flow name>

### Screens
- `web_admin_<flow>_<state>.html` — short description
- ...

### Reconcilability gauntlet answers
1. Trust boundary: ...
2. Keys and secrets: ...
3. Self-hosted vs hosted: ...
4. Confirmation honesty: ...
5. Browser-only fallback: ...
6. Open-source and reproducibility: ...

### Notes
<anything else worth keeping at the platform-spec level>
```

Mockups live in `UI/mockups/` (one HTML file per screen-state,
prefixed `web_admin_*`) per the convention in
`UI/mockups/README.md`. The web admin uses a desktop viewport
(1280×800) with a centered max-width content column; see
`UI/mockups/_shared/web_admin_shell.css`.

## What does NOT live here

- Cross-platform / per-Holding decisions — see `UI/README.md`.
- Mobile screen detail — see `UI/mobile.md`.
- Visual styling specifics — see
  `UI/mockups/_shared/tokens.css` and
  `UI/mockups/_shared/web_admin_shell.css`.
- The eventual full daily-use browser PWA / desktop operations
  console — separate surface, deferred to pre-public-ship per
  ADR-0020.

---

## Login

Authenticated landing surface for the web admin after first-boot
setup is done. Shown whenever the operator opens `/admin/*`
without a valid session token in `sessionStorage` (per ADR-0020).

### Screens

- `web_admin_login.html` — single passphrase field, "Sign in"
  primary CTA, "Forgot passphrase?" ghost link (points at the
  recovery doc; we can't reset what we don't store). Banking-
  ergonomic chrome: wordmark-icony top-left, server-label top-
  right ("Rémy's home server" — sourced from
  `configuration.toml server_label` per
  `01_architecture.md §"Configuration model"`; falls back to
  origin URL when absent). Empty middle, single form card. After
  failed attempts the form shows an inline error ("Wrong
  passphrase") and a rate-limit counter once the server-side
  rate limit fires. On server-locked (post-restart), shows the
  same screen with an inline note "Server was restarted — sign
  in to unlock."

### Reconcilability gauntlet answers

1. **Trust boundary.** Browser → backend over HTTP(S) at the
   server's origin. The browser does not hold any persistent
   credential; the passphrase is typed into the form each
   session. The backend holds the Argon2id-derived comparison
   material (per ADR-0008) plus the in-memory passphrase that
   decrypts the secrets store while unlocked.
2. **Keys and secrets.** Passphrase typed into the form,
   POSTed once over the connection, validated against the
   Argon2id comparison material on the backend. The backend
   issues a short-lived bearer session token; the frontend
   stores it in `sessionStorage` only (no `localStorage`, no
   cookies with persistent expiry). Token TTL: sliding 30 min
   / absolute 8 h per ADR-0020. The passphrase is never stored
   on the browser side.
3. **Self-hosted vs hosted.** Identical from the browser's POV.
   Self-hosted: the operator is the only user; the form's
   server-label corresponds to their own stack. Hosted-tier
   (when it ships per
   `backlog/hosted-tier-infrastructure.md`): the form is
   identical, with the server-label corresponding to the
   hosted instance. Auth model is the same.
4. **Confirmation honesty.** "Signed in" is implicit by
   navigating away from the form. No celebratory toast. Wrong
   passphrase shows inline error before any navigation; correct
   passphrase navigates without "Success!" theatre. Rate-limit
   counter accurate to the server-side state.
5. **Browser-only fallback.** N/A — web admin **is** browser-
   only by definition. Capacitor / NativeBridge affordances are
   suppressed under the `/admin/*` layout.
6. **Open-source and reproducibility.** Same SvelteKit codebase
   as the rest of the frontend; no closed dependency. The
   passphrase-validate endpoint is part of the open-source
   backend.

### Notes

- The "Forgot passphrase?" ghost link leads to documentation
  describing the recovery model from ADR-0008 (one passphrase
  per stack; deep recovery requires either a backup of the
  encrypted store and the passphrase, or starting fresh and
  re-pairing). We cannot reset what we never stored.
- The server-label is the only humanizing element — keeps the
  surface from feeling like a bare auth wall while staying
  banking-formal.

---

## Install wizard (first-boot mode)

Entered automatically when the operator opens `/admin/*` and the
backend reports first-boot state (no passphrase set, no paired
devices). Three steps, no back-skip between steps — each step
commits before the next opens.

### Screens

- `web_admin_install_step1_passphrase.html` — set the server
  passphrase. Two fields (passphrase + confirm), inline strength
  meter, server-side minimum-length enforced on submit. Below
  the form, a "What this passphrase does" disclosure listing the
  three uses per ADR-0008: server startup decrypts the secrets
  store, mobile-fallback unlock, hosted-tier dashboard auth
  (when applicable). On submit, backend derives Argon2id
  comparison material, stores it, marks the install one-third
  done; the wizard advances to step 2.
- `web_admin_install_step2_infrastructure.html` — display-only
  infrastructure review. Four rows (Bitcoin node, Lightning,
  Privacy network / Tor, Pricing source), each showing the
  current state — "Built-in bitcoind, syncing", "Lightning not
  yet — ships with the Lightning iteration", "Tor disabled —
  set in `configuration.toml` when needed", "Default rate
  source". No interactive controls in iteration v1; the rows
  exist so the operator sees the slot, not so they can toggle
  it. "Continue" advances to step 3.
- `web_admin_install_step3_pair.html` — first-pair surface, two
  cards. **Top card: "URL your phone will use".** Editable text
  field pre-filled from `window.location.origin` as a hint;
  operator confirms or replaces with the deployment-appropriate
  URL (Umbrel MagicDNS, Tailscale, Cloudflare Tunnel, plain
  LAN IP). Inline `Update` button POSTs to `PUT /api/v1/admin/
  pairing/url`. Warning chips render when the URL hits the
  known-unreliable patterns from ADR-0021 (`localhost`,
  `.local` mDNS, plain-HTTP private IP); informational, not
  blocking. Inline examples shown beneath. **Bottom card: QR
  + manual entry.** Generates a single-use 90s-TTL 12-char
  base32 pairing token per ADR-0021, renders the QR (encodes
  `<pairing_url>/api/v1/admin/pairing/redeem?t=<token>`),
  the TTL ribbon, and a `Refresh now` button. Beneath the QR,
  separated by a divider, the manual-entry display: server URL
  and pairing key (formatted `XXXX-XXXX-XXXX`) as discrete
  copyable lines so the operator can read them aloud or copy
  them into the phone's manual-pairing form. QR auto-refreshes
  every 60s; refresh re-emits both the QR and the visible
  pairing key together. On successful redemption (the
  `POST /api/v1/admin/pairing/redeem` returns 200), the screen
  flips to "Phone paired" — shows the device label as
  registered by the phone, with a "Pair another device"
  secondary CTA and a "Finish setup" primary CTA. Finish
  issues a session token to the browser and lands the
  operator on the paired-devices view.

### Reconcilability gauntlet answers

1. **Trust boundary.** Step 1: browser → backend, passphrase in
   POST body. Step 2: backend reads `configuration.toml` and
   bitcoind health state; returns to browser. Step 3: backend
   generates pairing token and QR payload, phone scans and
   POSTs the token back to the backend. The phone is the third
   participant in step 3; everything else is browser ↔ backend.
2. **Keys and secrets.** Step 1: passphrase typed, POSTed once,
   Argon2id-derived material stored, plaintext discarded. Step
   2: no secrets in flight; display-only. Step 3: pairing token
   is high-entropy (256-bit random base32 per ADR-0021), TTL-
   bound, single-use; per-device credential issued to the phone
   on redemption, returned in the redemption response, stored
   in Keychain/Keystore by the phone.
3. **Self-hosted vs hosted.** Step 1 + step 3 are identical.
   Step 2's infrastructure rows differ: self-hosted shows the
   operator's bitcoind / Tor / etc.; hosted-tier (when it
   ships) shows the hosted-tier's infrastructure (which is
   shared across pods). The display-only nature stays the same;
   the row content is data-driven.
4. **Confirmation honesty.** Step 1: passphrase saved →
   advances. No "Passphrase set ✓" toast; the advance to step
   2 *is* the confirmation. Step 2: display-only; no state to
   confirm. Step 3: "Phone paired" only shown **after** the
   backend has issued the per-device credential AND the phone
   has POSTed back (which is the redemption event itself —
   atomic from the backend's POV). No optimistic "QR scanned"
   state on the browser side.
5. **Browser-only fallback.** N/A — web admin is browser-only.
6. **Open-source and reproducibility.** All three steps run
   against the open-source backend with no closed dependency.
   QR generation uses an OSS lib (e.g. `qrcode-svg`) inlined
   in the SvelteKit build.

### Notes

- The three-step ordering is deliberate: passphrase first
  because it gates the secrets store; infrastructure review
  second so the operator sees what came up before doing
  anything they'd want to roll back; pairing last so the
  operator's phone has a passphrase to fall back to if its
  device credential is ever lost (per ADR-0008).
- Step 2's display-only nature is the gating discipline. The
  moment any row grows a toggle that does nothing it crosses
  into dead-capability territory (per the project memory
  feedback on dead capability code). Real toggles land in
  iterations that ship real capability.
- The pairing flow's "Phone paired" state matches the mobile
  side's `mobile_onboarding_02_paired.html` — same vocabulary,
  same confirmation timing, so the operator and the phone user
  (often the same person) see consistent state.

---

## Paired devices

Authenticated admin view. Lists all per-device credentials
issued by this stack, with metadata, last-seen timestamps, and
a per-device revoke affordance. Also the surface for issuing
new pairing QRs after first-boot.

### Screens

- `web_admin_paired_devices.html` — list of paired devices, one
  row per device. Each row shows device label (editable inline),
  platform (`iPhone` / `Pixel 7` / `Android`), paired-at
  timestamp, last-seen timestamp (relative — "2 min ago",
  "yesterday", "3 weeks ago"), and a "Revoke" button. Top-right
  primary CTA: "Pair a new device" — opens the same QR pane as
  the install wizard's step 3 (sub-route or modal). The list's
  empty state ("No devices paired yet") shouldn't normally appear
  post-install since the wizard requires the first pair; could
  appear if the operator revoked all devices.

### Reconcilability gauntlet answers

1. **Trust boundary.** Browser ↔ backend, session-token-
   authenticated. The phone is not in this flow except via the
   "Pair a new device" affordance (which is the same shape as
   the install wizard step 3).
2. **Keys and secrets.** No keys in flight on this surface. The
   per-device credentials are server-side; the list shows
   metadata only. Revoking deletes the credential row server-
   side; the phone's local copy becomes a stale string that the
   backend rejects on next use.
3. **Self-hosted vs hosted.** Identical.
4. **Confirmation honesty.** Revoke is confirm-modal'd
   ("Revoke <device label>? The next request from this device
   will fail and the operator will need to re-pair.") and only
   shows the row as removed after the backend confirms
   deletion. No optimistic UI. "Phone paired" timing for new
   pairs matches the install wizard step 3.
5. **Browser-only fallback.** N/A — web admin is browser-only.
6. **Open-source and reproducibility.** Same as other web admin
   screens.

### Notes

- The revoke modal copy is deliberate: it tells the operator
  the device "will fail on next request" rather than "is gone
  immediately." The backend's session-validation is the
  enforcement point; the credential is dead the moment the row
  is gone, but the user-facing language matches the operator's
  mental model (request-by-request).
- Inline-editable device label: the operator can rename "Phone"
  to "Rémy's iPhone" or "Argentina parents' Pixel" without
  re-pairing. Persisted via a small PATCH endpoint.
- The "Pair a new device" affordance reuses the install
  wizard's step 3 screen (same QR component, same auto-refresh,
  same LAN-reachability reminder). Code-reuse, vocabulary-
  consistency.

---

## Cross-flow notes

- **Server relock.** Any web admin route that gets `423
  Locked` from the backend kicks the user back to the login
  screen with the inline "Server was restarted — sign in to
  unlock" note. This is the relock-detection path that fixes
  bug 4 from `backlog/unlock-flow-cleanup.md` on the web admin
  side; the mobile side has its own SSE-driven path covered by
  the remaining unlock-flow-cleanup scope.
- **Session expiry.** Same path as server relock for the user
  (kick to login). Distinguishable in the backend's response
  (different error code) but indistinguishable in the user-
  facing copy by design — both are "you need to sign in
  again." Adding a distinction would just create more error
  cases for the operator to interpret.
- **Wordmark / brand surface.** The login + install wizard
  screens carry the wordmark-icony at a desktop scale (~320px
  wide) top-left of the layout. Paired-devices and other
  authenticated admin screens carry only the wordmark text
  variant in a compact header. Same `tokens.css`
  brand-mark-* class hooks as mobile mockups.
- **Sensitive-screen flag.** The Capacitor-only sensitive-
  screen flag from `feedback_privacy_first_reveal` does not
  apply — web admin is not a Capacitor surface. Browsers
  handle screenshot behavior at the OS level, not at the page
  level.
