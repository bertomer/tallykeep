# Tor support (server + mobile)

- **Captured:** 2026-05-27 (during the auth + install architecture
  brainstorm). Surfaced when working through the Umbrel migration
  path — Umbrel and Start9 both publish apps as Tor hidden services
  by default for remote access, and that pattern is currently
  unsupported on the TallyKeep side.
- **Motivation:** Two distinct concerns, each load-bearing for the
  appliance ecosystem:

    1. **Server-side: web admin + JSON API must work behind Tor.**
       No required external CDN (TallyKeep's bundle is already
       self-contained, but verify), no hardcoded IP / DNS
       assumptions that break under onion routing, no APIs that
       fail on `.onion` addresses (geo-IP lookups, OCSP stapling,
       etc.). The web admin must render identically whether
       reached at `http://localhost:port`, `http://192.168.x.y:port`
       on the LAN, or `http://tallykeep-<hash>.onion` over Tor.
    2. **Mobile-side: the phone must be able to reach a `.onion`
       URL** from outside the user's LAN. Without this, an
       Umbrel-hosted TallyKeep only works when the user is at
       home. The whole point of an always-on server for a banking-
       grade product is that it's always reachable — Tor is how
       the appliance ecosystem solves "reachable from anywhere
       without port forwarding."

  The privacy posture aligns: Tor makes the user's server location
  unobservable to ISPs and network adversaries, matching the
  sovereignty-minded target audience.
- **Sketch:**

    1. **Server-side audit.** Confirm the web admin SvelteKit
       build has no required external CDN URLs, no required
       third-party JS/CSS, no API calls to external services that
       block on Tor (price oracles already gate the "bring your
       own URL" wizard question; chain-state subscriptions are
       internal to the pod's bitcoind/indexer choice). Audit
       FastAPI for any geo-IP, OCSP, or "phone-home" defaults
       that break under Tor.
    2. **Mobile-side Tor integration (Android).** Two paths:
       integrate with Orbot via the VPN service (user must
       install Orbot separately, but it's the cleanest mainline
       Android Tor experience), OR embed `tor-android` library
       inside the Capacitor app (no external dependency but more
       maintenance burden + larger APK). Decision needed.
       Locked principle: graceful degradation — when Tor is not
       available, surface honestly ("This server is behind Tor.
       Install Orbot or switch to LAN access").
    3. **Mobile-side Tor integration (iOS).** Apple's
       `NEPacketTunnelProvider` can host a Tor implementation
       (Onion Browser uses this pattern). App Store submission
       review is more scrutinized for Tor-using apps; submission
       language matters. Investigate the `tor-nspv` /
       `onion-browser` open-source patterns.
    4. **Server-URL configuration in mobile.** The pairing flow
       (per `pre-implementation.md pairing-handshake-crypto`
       leading direction) carries the server URL in the QR. When
       that URL is a `.onion`, mobile knows to route via Tor.
       The web admin's "Add device" QR generator surfaces both
       the LAN URL and the .onion URL (when running on an
       appliance that exposes both); the user picks per device.
    5. **Health-view integration.** Server reachability state
       extends to "reachable via Tor", "reachable via LAN",
       "unreachable" — surfaced in the mobile app's server-health
       view per `backlog/self-hosted-operational-reliability.md`
       dimension 2.

- **Touches:** mobile `NativeBridge` (new Tor capability,
  honest gates when unavailable), Capacitor build pipeline
  (Orbot integration vs bundled Tor library on Android; iOS
  NEPacketTunnelProvider), `concerns/threat_model.md` (Tor
  adversary model, .onion vs LAN trust distinction, what's
  observable to ISPs vs to a Tor adversary), Umbrel / Start9
  manifests (declare Tor dependency at appliance level), web
  admin (URL display: LAN + .onion variants), server config
  (Tor-friendliness audit).
- **Status:** sketched
- **Milestone:** **pre-shipping (public-ship gate).** Specifically:
  required to deliver a usable Umbrel / Start9 self-host
  experience. Lower priority for the private-ship event if
  Rémy's own use case stays LAN-only initially (server at home,
  phone uses Tailscale or LAN when at home, no remote access).
  Becomes load-bearing the moment users want their TallyKeep
  reachable from outside their home network without VPN or port
  forwarding.
- **Notes:**
    - Connects to `pre-implementation.md pairing-handshake-crypto`
      — the leading direction in that arbitration explicitly
      mentions revisiting the same-LAN constraint if remote
      pairing lands. Tor support is that "remote pairing"
      condition.
    - Connects to `backlog/remote-access-for-self-hosters.md`
      (likely already overlapping in scope — when this sharpens,
      check whether the two entries fold or stay separate).
    - Apple App Store review historically tightens around Tor
      apps. Worth scoping submission risk early; F-Droid is the
      Android side's parallel concern (lower risk there since
      F-Droid is more permissive than Play Store).
    - The "Tor not available" gracefully-degraded state is the
      honest-gate per ADR-0007 pattern: capability absent, UI
      surfaces clearly, no silent breakage. Phone shows "Server
      requires Tor connection. Install Orbot (Android) or
      connect via LAN" rather than failing opaquely.
    - Two distinct trust boundaries: server-on-LAN (the user's
      home network is the adversary model) vs server-on-Tor
      (Tor adversary model + appliance is the trust anchor).
      Threat model addendum needed when sharpened.
