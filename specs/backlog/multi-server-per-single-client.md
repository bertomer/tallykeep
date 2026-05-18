# Multi-server per single client

- **Captured:** 2026-05 (during onboarding-screen-2 session, when
  Rémy considered whether the server identifier needed to be
  prominent on the paired-confirmation screen)
- **Motivation:** Power-user case for the sovereignty audience.
  Examples: home stack + parents' Umbrel for inheritance management,
  home stack + work-pseudonym stack, home stack + traveling test
  instance. Currently the architecture and onboarding assume
  single-server-per-client (one paired stack, one device credential
  in the Keychain). Extending to multi-server adds non-trivial UX
  surface.
- **Sketch:**
    - **Connect screen extension.** Currently terminal — once paired,
      the user lands on Home. Multi-server adds a Settings → "Paired
      stacks" view + an "Add another stack" affordance that
      re-runs the Connect flow without unpairing the existing one.
    - **Switch-server affordance.** Top-level UI element (likely the
      app bar or a Settings-rooted toggle) for moving between paired
      stacks. Active stack's identifier prominent; inactive stacks
      one tap away.
    - **Per-stack data isolation.** Each paired stack has its own
      device credential, its own observable Holdings, its own
      cached state. The phone holds N credentials; the user picks
      which is active.
    - **Notification routing.** When push notifications land
      (post-Lightning iteration), the notification has to indicate
      which stack it's about — otherwise tapping a notification
      lands on the wrong active context.
    - **Paired stacks server-side.** The inverse problem: the
      server's "paired devices" list shows N devices for the user.
      That part already needs to exist for single-stack
      revocation; multi-server doesn't change the server side.
- **Touches:** mobile UI (Connect, Settings, app bar, Home),
  device-credential storage shape (Keychain entry per stack vs
  array), backend (no change — multi-server is a client-side
  concern, the server doesn't know about other stacks the device
  is paired with), `UI/mobile.md` Onboarding section, future
  notification handler.
- **Status:** idea
- **Milestone:** **post-public-ship** (Rémy's call: "defers to after
  public shipping for sure"). Not blocking for personal-use phase
  or public-ship event. The single-server-per-client model is the
  default and will likely cover the majority of public-ship users;
  multi-server is power-user expansion.
- **Notes:** Onboarding-screen-2 design assumes single-server when
  rendering the paired-server identifier. If multi-server lands,
  the paired-confirmation screen gains an "and your existing
  stack(s)" line, or the Add-stack flow is folded into Settings
  rather than re-running through Onboarding. Defer the design.

---
