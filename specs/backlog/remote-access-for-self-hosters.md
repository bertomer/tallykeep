# Remote access for self-hosters

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** Localhost-only is the locked dev / personal-use
  posture. Self-hosters who want their TallyKeep available from
  outside their LAN need a way that doesn't require flipping the
  app's auth posture.
- **Sketch:** Recommended path is WireGuard or Tailscale — the user
  brings their own VPN, TallyKeep stays localhost-bound on the
  remote network. For users who want direct exposure, an API-layer
  auth (bearer token + TLS at minimum) gates the localhost-only
  policy.
- **Touches:** API surface, threat model, settings, install guide
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Touches the locked "Internal API-first" principle —
  any change to the localhost-only posture deserves an ADR. The
  default stays localhost; remote access is opt-in with a clear
  hardening path.
