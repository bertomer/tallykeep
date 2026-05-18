# Ship-gate meta-iteration (the public-ship event)

- **Captured:** 2026-05 (ADR-0003 — Project phases and shipping
  milestones)
- **Motivation:** This entry IS the public-ship event in
  `future_iterations.md` form. Once Rémy is satisfied with the
  product (after iterating on his own phone post-private-ship), the
  ship-gate is the dedicated session bundle that finalizes
  everything before going public. Reaching it is Rémy's explicit
  call ("I'm satisfied; finalize and ship"), not a tech checklist.
- **Sketch:** A meta-iteration bundling the items below. Some need
  their own dedicated arbitration when the ship-gate approaches
  (notably authentication-layer hardening and the third-party
  security audit scope).
- **Touches:** auth, signing, build pipeline, distribution, threat
  model, brand
- **Status:** sketched
- **Milestone:** **pre-shipping** (this entry's items collectively
  constitute the public-ship event itself).
- **Notes:** Items bundled into the ship-gate:
    - **Native secp256k1 signing** — replaces JS @noble/secp256k1
      from the personal-use phase (was pre-implementation item
      `native-secp256k1-signing`).
    - **Authentication layer hardening** — passphrase + biometric
      requirements tightened for public users (the private-ship
      version is enough for Rémy's own daily use).
    - **End-to-end third-party security audit** — verify no security
      breaks, no leaks, no inadvertent custody surface.
    - **Reproducible build pipeline** (CI).
    - **App Store / Play Store distribution** + listing assets.
    - **F-Droid licensing audit** — Capacitor licence chain, any
      Lightning SDK if Lightning is in scope.
    - **Brand voice and identity finalization**.
    - **Public privacy policy + terms of service**.
    - **Customer support infrastructure** — triage, response
      expectations.
