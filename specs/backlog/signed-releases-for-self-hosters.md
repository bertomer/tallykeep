# Signed releases for self-hosters

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Self-hosters running TallyKeep via Docker Compose
  or git checkout need supply-chain credibility independent of the
  app stores. Without signed releases + checksums, "self-hosted"
  becomes a trust-the-pull-from-Docker-Hub story.
- **Sketch:** Signed git tags (developer key), signed Docker images
  (cosign or similar), published checksums alongside each release,
  documented verification steps in the install guide.
- **Touches:** release pipeline, install documentation, trust model
- **Status:** idea
- **Milestone:** **pre-shipping** — needs to land before public-ship
  alongside the reproducible-build pipeline. Self-hosters who pulled
  through the personal-use phase get this as a confidence signal.
- **Notes:** Distinct from app-store distribution. Reproducible
  builds in the ship-gate entry let third parties verify; signed
  releases let users verify against the developer key.
