# ADR-0008 — Passphrase and recovery model (two-layer unlock)

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during onboarding-screen-2 design sessions
- **Migrated from:** `pre-implementation.md` Open item
  `traveling-user-recovery` (resolved 2026-05-10)

## Context

The mobile onboarding flow needs to settle two adjacent questions:

1. **How is TallyKeep locked on the user's phone day-to-day?**
   Biometric is the obvious convenience answer, but biometric isn't
   universally available — the target markets (LatAm, Africa)
   include significant Android device populations where biometric
   sensors are inconsistent or absent. Required biometric would
   lock those users out; opt-in biometric needs a fallback that
   isn't OS-lock-only (which leaks the device credential to anyone
   who can unlock the phone at the OS layer).

2. **What happens if the phone loses its device credential
   entirely?** App reinstall, phone factory-reset, lost device.
   The user needs a path back into their TallyKeep state without
   us having stored an email (per locked principle: no accounts in
   our app).

Earlier draft thinking made two errors that were corrected during
the design sessions:

- *"One passphrase per stack" alone implies biometric-only
  protection.* This forces "trip to the desktop" as the recovery
  path for any biometric failure — too much friction for daily
  use, and impossible for hosted-tier users without a second
  device.
- *"The server passphrase IS the recovery"* — proposed as a way
  to avoid a second passphrase, but contradicted the QR-only
  initial-pairing argument by making recovery *harder* than
  onboarding (re-pairing should be the same primitive as initial
  pairing, not stricter).

The resolution below splits the question into two layers — daily
unlock and deep recovery — each with its own mechanism, both
preserving the one-passphrase-per-stack principle.

## Decision

### Two-layer unlock model

**Layer 1 — daily unlock (no server round-trip needed for
biometric; passphrase fallback always available).**

- *Default:* biometric unlocks the Keychain entry holding the
  device credential. OS-native prompt (Face ID / Touch ID / Android
  biometric) fires on app open. Convenient, hard to shoulder-surf,
  hard to extract.
- *Fallback (always present):* a "Use passphrase instead"
  text-link on the unlock screen. The user types their TallyKeep
  passphrase; the phone forwards it to the backend over the paired
  connection; the backend validates against its in-memory
  passphrase (the same one it uses to decrypt secrets at rest per
  `01_architecture.md` §"Configuration model"); on OK, the phone
  unlocks the local credential.
- **The phone never stores the passphrase.** It accepts user
  input and forwards. Same model as any banking app — password
  typed, app forwards to server, server validates.
- *If biometric is unavailable on the device* (no sensor, OS
  disabled): passphrase becomes the only unlock mechanism. Same
  forwarding model. No tradeoff vs the biometric-enabled case
  except for the typing friction.

**Layer 2 — deep recovery (device credential fully lost).**

- *Triggered by:* app reinstall, phone factory-reset,
  device-credential-not-found state.
- *Self-hosted recovery:* user walks to their desktop, generates
  a fresh QR from the "Paired devices" panel (same UI used for
  initial pairing), scans with phone. **Same primitive as initial
  pairing**, just run again.
- *Hosted-tier recovery:* user opens the hosted-tier dashboard
  via web browser, authenticates with their connection-ID +
  passphrase, generates a fresh QR, scans with phone. The
  passphrase is used to authenticate to the dashboard, not
  forwarded by the phone app.
- The hosted-tier "no second device available" edge case
  sharpens during the hosted-tier iteration (see
  `future_iterations.md` "Hosted tier infrastructure").

### One passphrase per stack

There is one passphrase, the server's. It is used in three places:

1. **Server startup** — decrypts the secrets table at rest
   (custodial provider credentials, future Lightning macaroons).
   Per `01_architecture.md` §"Configuration model".
2. **Phone unlock fallback** — forwarded by the phone for
   validation against the in-memory copy.
3. **Hosted-tier dashboard auth** — authenticates the user to
   the hosted admin surface for re-pairing and account
   management.

No mobile-side passphrase. No second passphrase. The user has
one secret to remember.

### Auth-layer scope (implementation implications)

- Backend exposes a passphrase-validate endpoint:
  `POST /api/v1/auth/passphrase-validate` (or equivalent — exact
  shape sharpens during the auth-layer iteration). Rate-limited
  to prevent brute-force. Argon2id-derived comparison; never
  stores or logs the raw passphrase.
- The pairing handshake crypto (token format, TTL, credential
  format, revocation semantics) remains an open arbitration in
  `pre-implementation.md` `pairing-handshake-crypto`; this ADR
  does not pre-empt those choices.
- Per ADR-0003, the auth layer is private-ship gate work. The
  endpoint and validation logic land in the auth-layer iteration.
- For browser-dev (current phase), the API has no auth layer. The
  passphrase-validate endpoint is stubbed or not exercised; the
  unlock flow can be tested by the manual-URL-entry path on Screen
  01 connecting to the unauth'd backend.

## Consequences

- **No "set a recovery passphrase" screen during onboarding.** The
  passphrase already exists (set at server startup or hosted-tier
  claim). Communicated to the user on the biometric-done
  onboarding screen via a fact-row + short explainer.
- **`pre-implementation.md` `traveling-user-recovery` is closed.**
  Slug migrates here per `decisions/README.md` "Migrated from"
  convention.
- **Skip-biometric is no longer a security tradeoff.** It's a
  preference between biometric and passphrase-only unlock.
  Skip-confirm bottom-sheet copy softened on
  `mobile_onboarding_02_paired_skip_confirm.html` to reflect this.
- **`UI/mobile.md`'s Onboarding section + new Daily Unlock
  section** carry the per-flow gauntlet answers consistent with
  this model.
- **Hosted-tier onboarding gains additional screens** (backup-
  credentials acknowledgment, modified deep-recovery copy). Not
  drafted yet; tracked in `future_iterations.md` "Hosted tier
  infrastructure" as a gap-list for when that iteration promotes.
- **ADR-0003's "passphrase + biometric" private-ship gate
  requirement maps onto this model cleanly.** There is a
  passphrase (the server's, forwarded for fallback unlock) and
  biometric is the convenience layer. No revision of ADR-0003
  needed.

## Affected files

- `pre-implementation.md` — `traveling-user-recovery` slug
  removed (resolution preserved here under "Migrated from").
- `UI/mobile.md` — Onboarding section's Notes capture the
  two-layer model; new Daily Unlock section drafts the mockups
  consistent with it.
- `UI/mockups/mobile_onboarding_02_paired_biometric_done.html` —
  facts card surfaces the model.
- `UI/mockups/mobile_onboarding_02_paired_skip_confirm.html` —
  copy reflects the corrected (softer) model.
- `UI/mockups/mobile_onboarding_02_paired_no_biometric.html` —
  copy reflects passphrase-as-daily-unlock.
- `UI/mockups/mobile_unlock_biometric.html`,
  `mobile_unlock_passphrase.html` — drafted to match this model.
- `next_iteration.md` "Decisions already pre-bagged" — the
  unlock + recovery model bullet captures the implementation
  scope (`passphrase-validate` endpoint) for the eventual
  Onboarding + Home iteration.
- `future_iterations.md` "Hosted tier infrastructure" — gap-list
  for hosted-tier-specific onboarding screens (backup-credentials
  acknowledgment, modified deep-recovery copy, traveling-user
  edge case) noted under the same model.
