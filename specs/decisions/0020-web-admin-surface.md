# ADR-0020 — Web admin as third surface, per-session passphrase login

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during unlock-flow-cleanup design session
  2026-05-27
- **Migrated from:** `pre-implementation.md` Open item
  `browser-pwa-auth-model` (resolved 2026-05-27)

## Context

TallyKeep's architecture as written in `01_architecture.md` enumerates
three runtime surfaces participating in a user's stack: the **Backend**
(FastAPI + Postgres + Redis + worker, on the user's host), the
**Capacitor client** (mobile app, holds spending keys), and the
**Browser PWA client** (SvelteKit PWA in any browser, watch-only).

That table is incomplete. A real install — Umbrel, Raspberry Pi, plain
Linux server, Windows or macOS — needs a **surface that lets the
operator set up the stack in the first place**: pick the passphrase
that encrypts the secrets store, pair the first phone, see what
infrastructure the install brought up, manage paired devices over
time, and rotate the passphrase when needed. CLI-only setup exists for
developers but is not a path normal users can be expected to walk.

Two earlier framings shaped this discussion:

- *"The mobile app does the install wizard."* Considered and rejected.
  An Umbrel-class deployment ships before the operator has paired any
  phone; the wizard has to live somewhere reachable from a laptop
  browser. Mobile-first-then-pair is the wrong sequence — the user
  has to be able to set the passphrase before pairing makes sense.
- *"The browser PWA grows admin screens."* Considered and rejected.
  The browser PWA is a per-session watch-only client per
  `pre-implementation.md browser-pwa-auth-model`'s leading direction;
  conflating "daily-use browser viewer" with "admin console" muddles
  both surfaces. The admin operations (rotation, pairing, device
  revoke) are small enough to deserve a clean, dedicated surface.

The arbitration item `browser-pwa-auth-model` settled the auth model
for the per-session client surface; this ADR pulls that out of the
"browser PWA" framing and gives it its proper home — a separate **web
admin** surface — while preserving the same per-session passphrase-
login auth.

## Decision

### 1. The web admin is a third runtime surface

TallyKeep's surfaces and trust zones are now four (was three):

- **Backend** — unchanged.
- **Capacitor client** — unchanged. Daily-use, holds spending keys
  for on-device Purses, biometric-unlocked.
- **Web admin** — *new.* SvelteKit route-group inside the same
  frontend codebase, served by the same backend at the same origin
  under `/admin/*`. Hosts the install wizard in first-boot mode and
  the small set of ongoing admin operations (paired devices,
  passphrase rotation, version status, log access — landing
  iteratively, not all in iteration v1; see Tier 1 / Tier 2 in
  `backlog/web-admin-tier-2-rotation-and-status.md`).
- **Browser PWA client (future, pre-public-ship)** — the
  full-daily-use browser/desktop PWA mentioned in `UI/README.md`.
  **Defers to the pre-public-ship phase per Rémy 2026-05-27.**
  Private-ship is mobile (daily-use) + web admin (setup + admin
  ops). The "desktop operations console" mentioned in
  `UI/README.md` is a separate, larger surface whose architecture
  remains TBD; the web admin is *not* its beachhead.

### 2. Codebase placement

Same SvelteKit project as the mobile PWA. The web admin lives under
the `/admin/*` route group with its own layout that suppresses
Capacitor / install-PWA / native-bridge affordances. One bundle, one
type-gen run, one test suite. The build output is a single PWA whose
behavior branches by route.

### 3. Auth: per-session passphrase login

The web admin authenticates per session against the server passphrase
(the same one introduced in ADR-0008 — one passphrase per stack).
Flow:

1. User opens the web admin in a browser.
2. If the server is in first-boot mode, the install wizard runs
   (see *Install wizard scope* below). Otherwise the login screen
   renders.
3. User types the server passphrase. Frontend POSTs to
   `POST /api/v1/admin/session` with the passphrase in the request
   body. Backend validates using the same passphrase-validate
   primitive ADR-0008 names.
4. On success, backend issues a **short-lived session token**.
   Returned in the response body; the frontend stores it in
   `sessionStorage` keyed by origin.
5. Subsequent requests carry the token via `Authorization: Bearer
   <token>` (or equivalent). Backend validates against an in-memory
   table.
6. Token TTL: 30 minutes of inactivity (sliding) or 8 hours absolute,
   whichever fires first. Exact values sharpen at implementation;
   the principle is "short enough that an unattended laptop self-
   locks, long enough that the admin operator can complete a
   rotation flow without re-auth interrupting it".
7. Token is invalidated on logout, on server relock (passphrase
   revoked on backend restart), or on TTL expiry.
8. When the backend is locked (post-restart, before unlock), every
   protected admin route returns `423 Locked` — the frontend kicks
   back to the login screen.

**Why `sessionStorage` and not in-memory only.** The frontend's
recovered-from-refresh state is the bug-1 (`refreshing-redirects-to-
passphrase`) failure mode. `sessionStorage` survives `F5` and tab
close-then-reopen-within-session, dies on tab close. That's the
right durability — the operator's expectation is "I haven't closed
the tab, I shouldn't have to re-auth". Persistent storage
(`localStorage`, cookies with long expiry) would be wrong; it leaks
the credential to anyone who can open the browser later.

**Why per-session, not per-device.** The web admin is rarely-used
admin surface, not a daily client. The cost of typing the passphrase
each session is acceptable. Per-device credentials (the mobile
model) carry persistence-over-time risk that the admin surface
doesn't need.

**Why no biometric.** Browsers don't have OS-grade biometric
integration. WebAuthn is its own decision (see `Open part` below).
Banking-grade is achieved via TLS + short-lived tokens + the
passphrase quality requirement, not via biometric on this surface.

### 4. Install wizard scope (first-boot mode)

The web admin enters wizard mode when the backend reports
"first-boot" state — no passphrase has been set, no paired devices
exist. The wizard runs in three steps:

- **Step 1 — Set passphrase.** Operator types the passphrase that
  will encrypt the secrets store at rest and serve as the auth
  primitive for this admin surface and for mobile fallback unlock
  (per ADR-0008). Passphrase strength shown inline; minimum-length
  enforced server-side. Server stores the Argon2id-derived
  comparison material (not the passphrase itself; per ADR-0008).
- **Step 2 — Infrastructure review.** Display-only summary of
  what the install brought up. Four rows: Bitcoin node, Lightning
  node, Privacy network (Tor), Pricing source. Each row honest
  about its current state — "Built-in bitcoind, syncing",
  "Lightning not yet — ships with the Lightning iteration",
  "Tor disabled — set in configuration.toml when needed", "Default
  rate source". No interactive controls in iteration v1; the
  display exists so the operator sees the slot, not so they can
  toggle it. Adding interactivity here without a working
  implementation behind it would be a dead-capability surface (per
  user preferences memory `feedback_no_dead_capability_code`); the
  controls land in iterations that ship real capability.
- **Step 3 — Pair your phone.** First-pair QR. Generated on this
  step; auto-refresh on TTL elapse; explicit "Refresh QR" button.
  Pairing details in ADR-0021. On successful redemption the wizard
  shows "Phone paired" with the device label and proceeds to the
  paired-devices view, where the operator can pair additional
  devices or finish.

The wizard issues a session token on completion so the operator
isn't bounced to a fresh login immediately after setup.

### 5. Network reachability — pairing URL is operator-configured

The web admin lives at the same origin as the backend, bound per
`01_architecture.md §"Network security posture"` to `127.0.0.1`
in the dev / personal-use phase. **The URL the phone uses to
reach the server is a separate concern from the URL the operator
uses to reach the admin** — the operator might browse the wizard
on their laptop at `http://localhost:8000` (loopback to their own
machine) while the phone needs to reach the same server over the
LAN, over Tailscale, or via a Cloudflare Tunnel.

Auto-deriving the pairing URL from `window.location.origin` is
the wrong default. It works only for the narrow case where the
operator is browsing the wizard from a separate device on the
same network as the phone — not for the common Umbrel / Pi /
local-Linux case where the operator runs both the wizard and the
server on the same machine.

The wizard's step 3 therefore **explicitly asks** for the URL the
phone will use, pre-fills from `window.location.origin` as a
hint, and stores the operator's answer in the configuration
table. Warnings (not blocks) surface for known-unreliable values:

- `localhost` / `127.0.0.1` / `0.0.0.0` — phone can't reach
  loopback.
- `.local` mDNS names — reliable on iOS, flaky on Android,
  never on cellular.
- RFC1918 private IPs over plain HTTP — phone-side TLS pinning
  may reject.

Per-deployment paths:

- **Umbrel:** Umbrel exposes services via its own MagicDNS / Tor
  / Tailscale layer. The pairing URL is whatever Umbrel surfaces
  for this app.
- **Tailscale on plain Linux / Pi:** `https://tallykeep.<tailnet>.ts.net`.
  Works across cellular, all platforms.
- **Cloudflare Tunnel:** `https://tallykeep.<your-domain>.com`.
  Works across cellular.
- **LAN-only on trusted Wi-Fi:** `https://<private-ip>:<port>`
  with a self-signed cert or `http://` (phone will warn).

Deployment-layer reachability is not a TallyKeep architecture
problem — it's the same problem every self-hosted admin UI faces
(Home Assistant, Sonarr, Pi-hole). The wizard's responsibility
is to capture the operator's answer and use it, not to invent
it.

ADR-0021 carries the field name (`pairing_external_url`), the
storage location, the URL-validation endpoints, and the warning
flags.

## Consequences

- **`pre-implementation.md browser-pwa-auth-model` is closed.**
  Slug migrates here per the convention.
- **`01_architecture.md` surfaces table grows a fourth row** for
  the web admin. The "Browser PWA client" row stays, with a note
  that the full-daily-use PWA defers to pre-public-ship.
- **`UI/README.md` flow inventory grows a Web admin section** and
  records the private-ship-is-mobile-plus-web-admin framing.
- **A new module `UI/web_admin.md` lands** with screen-by-screen
  prose + gauntlet answers for the iteration v1 scope (login,
  install wizard 1/2/3, paired devices).
- **The `pre-implementation.md browser-pwa-auth-model` direction
  on a per-session browser PWA is preserved.** The eventual
  full-daily-use browser PWA (pre-public-ship) inherits the same
  auth model documented here, plus whatever WebAuthn / read-only-
  vs-write gating sharpens at that point. This ADR does not
  pre-empt that.
- **The dev-mode `localStorage` NativeBridge fallback** mentioned
  in `pre-implementation.md browser-pwa-auth-model` still needs to
  be replaced when the Capacitor-wrap iteration finishes — the
  decision now reads "browser branch = per-session passphrase
  login + sessionStorage". A `// TODO(browser-pwa-auth-model)`
  comment grep-audit at that point should turn up empty after
  this iteration ships.
- **ADR-0008 unchanged at the principle level.** The web admin is
  a new consumer of the same one-passphrase-per-stack model.
  ADR-0008 gains an addendum noting that passphrase rotation is
  hosted by the web admin (deferred implementation in Tier 2).
- **ADR-0007 unchanged.** Browser-first-with-NativeBridge-stubs
  remains the rule for the Capacitor target. The web admin is
  not Capacitor-targeted and the `NativeBridge` interface is
  inert on its routes.

## Open part — not in this iteration

- **WebAuthn as a complementary auth mechanism** on the web admin.
  Considered for the eventual full-daily-use browser PWA. Out of
  scope for the web admin in private-ship.
- **Hosted-tier web admin variant** (when hosted-tier ships per
  `backlog/hosted-tier-infrastructure.md`). The same web admin
  code presumably serves the hosted-tier customer-facing admin
  console with hosted-tier-specific auth grafted on (connection-ID
  + passphrase, per ADR-0008's hosted-tier recovery branch). Out
  of scope until hosted-tier itself sharpens.

## Affected files

- `pre-implementation.md` — `browser-pwa-auth-model` slug removed
  (resolution preserved here under "Migrated from").
- `01_architecture.md` — surfaces table grows web admin row;
  network-posture section notes LAN-reachability assumption for
  pairing.
- `UI/README.md` — Web admin section added to the flow inventory;
  mobile-and-desktop framing clarified.
- `UI/web_admin.md` — new module, screen-by-screen prose.
- `UI/mockups/web_admin_*.html` — five new mockups
  (login, install_step1_passphrase, install_step2_infrastructure,
  install_step3_pair, paired_devices).
- `UI/mockups/_shared/web_admin_shell.css` — desktop shell styles
  (1280×800 viewport, centered content column, no phone-frame).
- `UI/mockups/index.html` — new `web-admin` group + 5 mockup
  entries; per-group aspect ratio override for desktop preview.
- `decisions/0008-passphrase-and-recovery-model.md` — addendum
  noting rotation hosted by web admin.
- `backlog/web-admin-tier-2-rotation-and-status.md` — new file
  capturing Tier 2 (rotation, version, logs).
- `backlog/unlock-flow-cleanup.md` — edited to note web-admin
  Tier 1 carved out; remaining scope (backend bug investigation +
  mobile paired-vs-unlocked + relock handling) preserved.
