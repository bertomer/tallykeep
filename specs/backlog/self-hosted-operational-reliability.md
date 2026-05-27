# Self-hosted operational reliability

- **Captured:** 2026-05-27 (Rémy, during the auth-model + install
  brainstorm). Triggered by a lived-experience moment that same
  morning: his Docker installation crashed, required killing the
  Docker process, a PC reboot, a system update, and ~10 minutes
  before the daemon came back. Frame: "self-custody has to be
  reliable, same as for banks — the credit-card-capacity check
  cannot fail half of the time."
- **Motivation:** Banking-grade ergonomics is locked principle
  (per `00_README.md`, brand voice docs, and the project's
  founding framing). The principle isn't just an aesthetic
  commitment — it implies an operational floor the product has
  to clear on the *infrastructure* side, not just the UI side. A
  pretty mobile app on top of a flaky server stack fails the
  promise. Self-hosters who lose access to their funds-related
  app for ten minutes because of a daemon crash will not extend
  the trust the brand asks for.

  Most self-hosted Bitcoin products are notably weak on this
  layer. Umbrel / Start9 invest heavily in it because it's their
  whole product. Standalone install-it-yourself products
  (BTCPay's docker path, Mempool self-hosted, RTL) often punt to
  "you're a self-hoster, you'll figure it out." If banking-grade
  is the bar TallyKeep claims, we have to do better than punt.
- **Sketch:** The full reliability layer has several distinct
  dimensions worth scoping separately. None of these are
  v1-blocking individually; in aggregate they're the
  difference between "self-hosted toy" and "product I'd trust
  with real money."

    1. **Service supervision.** Auto-restart on crash, with
       backoff. systemd unit on Linux, LaunchAgent on macOS,
       Windows Service on Windows. Docker users get this for
       free via `restart: unless-stopped`; non-docker users need
       it explicit. Decision needed: do we ship the service-unit
       files in the install package, or document them?
    2. **Health visibility from the mobile app.** Server status
       surfaced honestly in the phone UI: `reachable / unreachable`,
       `unlocked / locked`, `chain-tip lag` (last block N minutes
       ago — surface degradation, not just binary up/down), `LN
       channel state` (when applicable), `last poll cycle status`
       for connected custodians. The Security Health surface
       (shipped 2026-05-25) is the natural home for the
       persistent operational warnings; transient connection
       states stay on the Home / Holding-detail pages.
    3. **Update mechanism with rollback safety.** See
       `self-host-upgrade-mechanism.md` for the existing scope —
       versioned Docker images, release notes, `tk upgrade`
       script, rollback via image-tag pinning. The broader concern
       here is **migration safety**: if an Alembic migration fails
       mid-run, the server must not be left in a half-migrated
       state that prevents both forward progress and rollback.
       Pattern: pre-migration backup of `data/` directory,
       transactional migrations where possible, explicit
       "migration failed, rolled back to vN" status visible from
       both server logs and the mobile app's "server health" view.
    4. **Multi-OS native packaging.** Docker is the easiest dev /
       CI / quick-try distribution but it's a reliability
       liability for Windows and macOS users running Docker
       Desktop (the lived-experience trigger for this entry).
       Native binaries with proper OS service integration are the
       higher-floor distribution for those platforms. ONE
       source-of-truth binary (FastAPI + worker + chosen Bitcoin
       backend), multiple packagings around it: `.deb` / `.rpm` /
       AUR on Linux, `.pkg` (notarized) on macOS, `.msi` (signed)
       on Windows, plus the docker-compose path for users who
       want it. BTCPay does roughly this. Significant engineering
       — months of work — but load-bearing for the banking
       claim. Probably folds into the ship-gate meta-iteration.
    5. **Log rotation, disk monitoring, reorg handling.** Disk
       space exhaustion silently corrupts data on most systems
       if unhandled. bitcoind reorgs invalidate cached UTXO state
       and must be re-scanned. Sustained loss of mempool
       connectivity needs explicit user surfacing rather than
       silent staleness. All of these are operational maturity
       items that a v1 can ignore but a public-ship cannot.
    6. **Encrypted-state backup for the server.** Distinct from
       seed backup (which is the user's responsibility). The
       server holds: descriptors, paired-device credentials,
       runtime configuration, sweep policies, security-health
       history, custodial-ledger mirror, optionally pricing
       cache. Losing this without a backup means the user has to
       rebuild from seeds + re-pair every phone + reconfigure.
       Recoverable but painful. Pattern: bundled backup CLI
       (`tk backup --output ./backup.tar.zst.enc`), restore CLI,
       documentation on what to store where (off-box, encrypted
       at rest, ideally one copy off-site).

- **Touches:** release pipeline (packaging multi-OS, signing,
  notarization), `concerns/threat_model.md` (operational
  failure modes), `01_architecture.md` (service-supervision +
  packaging postures), `concerns/observation.md` (chain-tip
  health surfacing), `concerns/feature_flags.md` (probably no
  new flags — these are operational invariants, not user
  preferences), security-health system (operational warnings
  as items), mobile app server-health view (new surface,
  designed as part of this work), install guide (documenting
  the supervision + backup story).
- **Status:** sketched (this file is the umbrella; specific
  dimensions will sharpen separately as their iterations
  approach).
- **Milestone:** **pre-shipping (public-ship gate).** Not
  required for the private-ship event — Rémy can tolerate
  flakiness on his own box during personal-use. Becomes
  load-bearing the moment the project takes external users,
  because the banking-grade claim is what the brand sells and
  external users will judge the product on whether it holds up
  operationally, not just whether the UI looks nice. Probably
  folds into the ship-gate meta-iteration as a workstream.
- **Notes:**
    - Cross-references `self-host-upgrade-mechanism.md`
      (dimension 3 above is a superset of that file's scope —
      migration-safety + rollback-safety + atomic-update; keep
      both entries until sharpening folds them).
    - Dimensions 1, 2, and 6 are individually small enough to
      bundle into a single "operational floor v1" iteration.
      Dimensions 4 and 5 each deserve their own iteration —
      multi-OS packaging is months of pipeline work; full
      observability infrastructure is a separate design pass.
    - The mobile-app side of dimension 2 (server-health view)
      is a real UI surface that needs mockups when sharpened.
      Likely lives under `/settings/server` or as a top-level
      health card on Home below the existing holdings list.
      Locked principle: honest about degradation — the UI
      should not paper over a server-side problem with "all
      good ✓" rendering.
    - Worth a critique-mode flag on direction: the temptation
      will be to build elaborate operational tooling in v1
      because the principle is compelling. Resist. Ship the
      floor that catches the obvious failure modes (crash
      restart, disk full, migration mid-flight), defer the
      sophisticated parts (multi-region replication,
      observability dashboards, automated rollback heuristics)
      until real users surface real failure modes.
    - Hosted-tier users get this for free (the operator handles
      reliability) — this entry is the self-hosted side
      specifically. Hosted-tier reliability is the operator's
      problem and doesn't belong in this entry.
