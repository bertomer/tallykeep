# Unlock flow cleanup — remaining backend + mobile work

- **Captured:** 2026-05 (Rémy, during module 03 review). Surfaced by
  an hour of manual UI testing.
- **Sharpened 2026-05-27:** the architecture brainstorm settled the
  foundational positions (ADR-0020 web admin surface, ADR-0021
  pairing handshake crypto, ADR-0008 Addendum on rotation surface).
  The web-admin slice of this backlog carved out into its own
  iteration (Tier 1: login + install wizard + paired-devices +
  revoke). This file now tracks the **remaining backend +
  mobile** scope, plus the cross-cutting smoke tests.

## What carved out

- **Web admin Tier 1** — login, install wizard (passphrase +
  infrastructure review + first-pair QR), paired-devices view
  with revoke. Live in `next_iteration.md`.
- **Web admin Tier 2** — passphrase rotation, version status, log
  access. Captured at
  `backlog/web-admin-tier-2-rotation-and-status.md`.
- **Architecture decisions** — web admin surface (ADR-0020),
  pairing crypto (ADR-0021), rotation hosts on web admin
  (ADR-0008 addendum 2026-05-27).

## Remaining scope

The five original symptoms, re-investigated against the post-2026-
05-27 architecture, and what's left to do after Tier 1 ships:

1. *"Pairing succeeds but passphrase remains locked":* not a bug —
   pairing and passphrase are separate concerns. Pairing issues the
   device credential; passphrase unlocks the encrypted store. The
   mobile UI should surface the two states independently: "paired,
   server locked, enter passphrase to unlock." Current mobile
   UI conflates them.
   **Remaining work (mobile):** surface paired-vs-unlocked as two
   distinct states; show "enter passphrase to unlock" when paired
   but server-locked.

2. *"Passphrase unlocked but pairing reported as lost":* real bug —
   per-device credential storage in Keychain/Keystore, possibly
   evicted under memory pressure or on iOS background suspend.
   **Remaining work (mobile + backend):** instrument credential
   read-failure path on the phone; identify root cause (Keychain
   eviction? plugin race? wrong key on read?); add resilience or
   a clean re-pair CTA in the mobile UI ("This phone's pairing
   credential is no longer available — re-pair from the web admin
   to continue"). Backend investigation: confirm the credential is
   still active in the `paired_device` table (per ADR-0021 schema)
   so we can distinguish "credential evicted client-side" from
   "credential revoked server-side".

3. *"Refreshing the home page with unlocked passphrase redirects to
   the passphrase prompt":* **fixed by web admin Tier 1** — session
   token persists in `sessionStorage` per ADR-0020. If the mobile
   side has a parallel symptom (Svelte store hydration on page
   refresh dropping unlock state in the Capacitor wrap or PWA
   install), the same `sessionStorage` move applies. Verify after
   Tier 1 ships; capture as a separate small iteration if mobile is
   still affected.

4. *"Server reboot loses the passphrase but the home page is still
   refreshable (no relock)":* **partially fixed by web admin
   Tier 1** — every web admin route returns `423 Locked` when the
   backend is locked, so the web admin kicks back to login on a
   relocked backend. Mobile still needs its SSE `system.locked`
   handler to react to the lock event and re-prompt the user.
   **Remaining work (mobile + backend):** confirm LockMiddleware
   coverage on every route except the published allowlist; confirm
   mobile reacts to SSE `system.locked` by entering the
   passphrase-prompt state on next decryption-required operation.

5. *"Passphrase-rotation flow undocumented":* **moved to Tier 2** —
   web admin grows the rotate-passphrase affordance + backend
   endpoint + `system.passphrase_rotated` SSE event in the Tier 2
   iteration. Mobile detects rotation via the SSE event and
   re-prompts the user on next decryption-required op. Captured at
   `backlog/web-admin-tier-2-rotation-and-status.md`.

## Sketch (post-carve-out)

Single iteration after Web Admin Tier 1 closes. Split:

- **Backend:** confirm LockMiddleware coverage on every route
  except the published allowlist; document the allowlist explicitly
  in `04_api_conventions.md`; add observability around
  credential-validation failures (per bug 2 investigation).
- **Mobile:** distinct paired-vs-unlocked state (bug 1); credential
  read-failure path with clear re-pair CTA (bug 2); SSE
  `system.locked` handler that triggers passphrase re-prompt on
  next op (bug 4); `system.passphrase_rotated` handler scaffolding
  (no-op until Tier 2 ships the backend event, but the handler
  registers; bug 5 prerequisite).
- **Smoke tests:** cold-boot pair (already covered by Tier 1
  iteration); mid-session reboot (server relock then mobile detects
  then re-prompt); network partition (mobile loses connection then
  reconnects then state recovered); refresh-while-unlocked on
  mobile Capacitor wrap.

## Touches (remaining)

- `concerns/threat_model.md` Mobile addendum (per-device credential
  read-failure path, observability of credential validation).
- `UI/mobile.md` onboarding / unlock sections (paired-vs-unlocked
  state, re-pair CTA copy, SSE-driven re-prompt flow).
- `04_api_conventions.md` (LockMiddleware allowlist documented
  explicitly).

## Status

**partially carved-out; remaining-scope-not-yet-sharpened.** Web
admin Tier 1 is in progress as a separate iteration. This file's
remaining scope sharpens into a follow-up iteration after Tier 1
closes and the Tier 1 work surfaces what bugs 2 / 3 / 4 actually
require on the mobile + backend side.

## Milestone

**Pre-shipping (private-ship gate).** The remaining symptoms are
daily-use friction multipliers; should land before private-ship.
Probably scheduled after Web Admin Tier 1 and after Strongbox Send
+ Receive depending on signer arrival.

## Notes

- The CLI-only-setup question is resolved by exclusion: web admin
  is the only setup surface. CLI setup remains available for
  developers but is not promised to end users. This is captured in
  `01_architecture.md` and `UI/README.md` per the 2026-05-27 edit
  pass.
- Tier 2 (rotation, version, logs) lives at
  `backlog/web-admin-tier-2-rotation-and-status.md` and is
  scheduled separately.
