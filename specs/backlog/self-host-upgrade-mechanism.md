# Self-host upgrade mechanism

- **Captured:** 2026-05 (Rémy, module 03 review).
- **Motivation:** When TallyKeep ships a new version, self-hosted
  users need a way to upgrade their stack cleanly — pull new
  Docker images, run Alembic migrations, restart, verify, roll
  back if needed. Today there's no documented upgrade path; an
  agent landing on this question has to invent one.
- **Sketch:**
  - Versioned Docker images (semver, tagged per release).
  - Release notes (changelog) per version, including any manual
    pre-upgrade or post-upgrade steps (e.g. "this version drops
    `feature_flags.holding.*` keys — run the bundled
    migration").
  - A simple upgrade script (`./tk upgrade` or similar) that
    pulls images, runs migrations inside the backend container
    (`alembic upgrade head`), bumps the stack, and runs a
    health-check.
  - Rollback path: pinning to the previous image tag if the
    health-check fails. Database backups before migration are
    user responsibility (documented in install guide).
  - Notification surface: TallyKeep periodically checks GitHub
    releases (or a configurable update channel) and shows the
    user "v0.X.Y available — release notes / changelog link" on
    the home page. Opt-out for users who don't want
    network-checks (config flag).
- **Touches:** release pipeline, install guide, configuration
  model, UI (update notification surface), backend (`/health`
  + version reporting endpoint).
- **Status:** sketched
- **Milestone:** **pre-shipping** for the public-ship event
  alongside signed releases and reproducible builds (per the
  ship-gate meta-iteration).
- **Notes:** App-store builds (Capacitor) have store-managed
  updates; this entry is the self-hosted backend equivalent.
  Hosted-tier users update transparently as the operator pushes
  releases — separate mechanism.
