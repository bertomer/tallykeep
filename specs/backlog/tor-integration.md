# Tor integration

- **Captured:** 2026-05 (from module 13 Q15, pre-retirement)
- **Motivation:** Privacy posture. Self-hosted users running their
  own bitcoind already have the option of Tor-routed RPC; TallyKeep
  itself doesn't currently route its outbound traffic (provider APIs,
  rate feeds) through Tor.
- **Sketch:** Optional, off by default. When enabled, all outbound
  HTTPS requests (CustodialProvider APIs, optional rate feeds) route
  through a configured Tor SOCKS proxy. Recommended in the hardening
  guide; surfaced as a settings toggle.
- **Touches:** networking layer, settings, hardening guide
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Some provider APIs block Tor exit nodes; UX needs to
  fail gracefully and tell the user which provider blocked them.
