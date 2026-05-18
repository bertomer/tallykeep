# Capacitor mobile wrapper

- **Captured:** 2026-05 (originally module 12 v3, moved by
  mobile_form_factor_decision.md)
- **Motivation:** Native plugin access (Keychain, biometric, camera,
  push). Required for TallyKeep-managed Purses (whose seeds live in
  the device's Keychain/Keystore) and for the private-ship event
  per ADR-0003.
- **Touches:** build pipeline, UI mobile (NativeBridge implementation),
  threat model
- **Status:** sharpened-ready-to-promote
- **Milestone:** **pre-shipping (private-ship enabler).** Promotes
  to `next_iteration.md` once the mobile UI is fine-tuned in browser
  to Rémy's satisfaction. Concrete iteration includes:
    - Integrate Capacitor; build pipeline for the wrapped app.
    - Swap NativeBridge stubs for real plugin calls on the
      Capacitor branch (Keychain/Keystore, biometric, camera,
      share, clipboard).
    - **Remove the dev-mode `localStorage` fallback for
      `secureStorage`** that the Onboarding + Daily Unlock + Home
      iteration's NativeBridge browser branch ships as a dev
      crutch. Grep the codebase for
      `// TODO(browser-pwa-auth-model)` markers and resolve each.
    - **Implement the browser-PWA long-term auth model** per the
      resolution of `pre-implementation.md` `browser-pwa-auth-model`
      (leading direction: per-session passphrase login, no
      pairing, no persistent credential, session token in memory
      only). This includes simplifying or removing the Connect /
      Paired flow from browser PWA routing and adding a
      browser-PWA-specific entry screen.
    - Build the authentication layer hardening for the
      Capacitor side (the dev-phase auth layer shipped in the
      Onboarding iteration is sufficient for personal-use; review
      and harden as needed for sideload).
    - Build the security-health seed-backup minimum for
      `seed-backup-disclosure`.
    - Sideload to Rémy's phone for private-ship.
  Blocked by: arbitration on `browser-pwa-auth-model` in
  `pre-implementation.md` (gates the browser-branch cleanup).

---
