# ADR-0007 — Browser-first development with NativeBridge stubs

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during consolidation merge
- **Migrated from:** `pre-implementation.md` Decided item
  `browser-vs-capacitor-fine-tuning` (2026-05).

## Context

The shipped product is a Capacitor app on the user's phone. Most
of the screens, however, can be designed and fine-tuned without
the Capacitor build pipeline — and the Capacitor wrap, app-store
build, and physical-device validation are a separate phase per
ADR-0003 (gating the private-ship event). The question was
whether to design and iterate on the mobile UI in the browser
against the real backend, or to wait for the Capacitor build to
land before touching UI work.

## Decision

1. Build the mobile UI in SvelteKit and run it in the browser at
   mobile viewport against the real backend. This is the dev
   phase per ADR-0003.
2. Native operations sit behind a **`NativeBridge` interface** in
   the SvelteKit code:
   - secure storage (Keychain / Keystore)
   - biometric prompt
   - PSBT signing
   - QR camera scan
   - push notification subscription
3. The browser implementation of `NativeBridge` either throws or
   returns visible-fixture values, with a "this build cannot do
   X — Capacitor needed" banner in dev mode.
4. The Capacitor implementation lands later as a swap, ideally
   with no UI changes.
5. The UI is designed for the **Capacitor target** — the eventual
   shipped version with native plugins, on-device keys,
   biometric unlock, push notifications. Where the browser cannot
   fulfill a Capacitor-only capability, the screen still exists
   and the operation is gated honestly. Screens are not deleted
   because the browser can't fully execute them, and the browser
   does not pretend to have capabilities it doesn't.
6. The browser version is **the Capacitor UI plus honest gates**,
   not a different UI.

## Consequences

- Capacitor wrap, app-store packaging, and physical-device
  validation move to the **private-ship gate** per ADR-0003.
- Any flow that would silently work in browser but break in
  Capacitor (or vice versa) shows up as a stub call. The
  irreconcilable corner is felt during dev, not at launch.
- Reconcilability gauntlet question 5 ("browser-only fallback")
  becomes physical rather than aspirational: if the screen
  doesn't render its honest gate when the bridge stubs out, the
  iteration isn't done.
- JS-side `@noble/secp256k1` signing remains acceptable through
  the personal-use phase (per ADR-0003 — relaxes during
  personal-use phase). Native signing replaces it at the
  public-ship event (per ADR-0003).

## Affected files

- `01_architecture.md` — Capacitor build target, mobile/desktop
  shell separation
- `PROCESS.md §5` — "Browser fine-tuning (no Capacitor yet)"
- `PROCESS.md §3 question 5` — browser-only fallback
- `concerns/threat_model.md` Mobile addendum
- `UI/README.md` — Send / Receive flows reflecting NativeBridge
  gating
- `decisions/0003-personal-use-phase.md` — phase model that this
  ADR sits inside
