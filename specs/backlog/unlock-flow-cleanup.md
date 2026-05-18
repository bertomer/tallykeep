# Unlock flow cleanup

- **Captured:** 2026-05 (Rémy, during module 03 review). Surfaced
  by an hour of manual UI testing.
- **Motivation:** The unlock flow has several real bugs and
  unclear semantics that need a dedicated design + implementation
  pass. Rémy's observed symptoms in ~1 hour of testing:
  - Pairing succeeds but passphrase remains locked.
  - Passphrase unlocked but pairing reported as lost.
  - Refreshing the home page with unlocked passphrase redirects to
    the passphrase prompt anyway.
  - Server reboot loses the passphrase but the home page is still
    refreshable (no relock).
  - Passphrase-rotation flow undocumented and unclear how a
    compromised passphrase is rotated.
  - No clear path to set up the server **without a UI** — install
    wizard happens through the web app; CLI-only setup is unclear /
    unsupported.
  - Pairing direction question: should the device-ID flow run the
    other way (server-knows-device, not device-knows-server) to
    avoid needing a desktop / web client during initial setup?
- **Sketch:** Design pass first — state machine for unlock + pair
  with all edge cases (cold boot, mid-session reboot, network
  partition, refresh, passphrase rotation, server-side rotation
  while device is paired). Then implementation pass to fix the
  state-management bugs and add the missing flows (CLI setup,
  passphrase rotation).
- **Touches:** `01_architecture.md` §"Configuration model" + the
  surfaces/trust-zones section; ADR-0008 (passphrase + recovery
  model) likely needs an addendum or supersede entry for any
  decisions taken; `concerns/threat_model.md` Mobile addendum;
  `UI/mobile.md` onboarding screens; possibly the pairing-handshake
  arbitration in `pre-implementation.md`.
- **Status:** sketched
- **Milestone:** pre-shipping — gating concern for the
  personal-use phase. Worth scheduling soon since each daily-use
  test multiplies the friction.
- **Notes:** Sequencing — the design pass is a brainstorm with
  Rémy first (spec-agent work), then iteration to fix the bugs and
  ship the missing surfaces. Probably 2 iterations end-to-end.
