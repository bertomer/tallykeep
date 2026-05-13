# ADR-0003 — Project phases and shipping milestones

- **Date:** 2026-05
- **Status:** Accepted (refined within the same consolidation
  session — earlier drafts framed this as a two-phase model with
  "v1" as the reference point; that framing didn't capture the
  intermediate **private-ship** state Rémy identified)
- **Decided by:** Rémy
- **Authored by:** Claude
- **Supersedes (in spirit):** prior drafts of this ADR titled
  "Personal-use phase as v1 milestone" / "Development phase before
  v1 ship"

> **Editorial note (2026-05):** vocabulary in this ADR was updated
> in place to use "TallyKeep-managed Purse" wherever earlier drafts
> said "on-device-keys Purse." The substantive decision is
> unchanged. Done by exception to keep canonical vocabulary
> consistent across the spec tree; ADRs are otherwise append-only.

## Context

The original spec talked about "v1, v1.5, v2, v3" without sharply
distinguishing what those boundaries meant. Earlier drafts of this
ADR proposed a two-phase model — "dev phase" then "public ship" —
but missed an important intermediate state Rémy identified: the
mobile app can be **shipped privately** (Capacitor wrap, native
plugins, sideloaded APK / TestFlight) without going public. That
private-ship state is materially different from both the dev phase
and the public ship.

This ADR replaces "v1" as the reference point with **three phases
separated by two explicit events**: a private-ship event and a
public-ship event. Each event gates a specific bundle of work.

## Decision

### Phases and events

```
       ┌─────────────────────┐
       │     Dev phase       │  Browser at mobile viewport, against
       │                     │  a live backend. No Capacitor wrap.
       │                     │  Native operations stubbed behind
       │                     │  NativeBridge. Currently active.
       └──────────┬──────────┘
                  │
                  ▼  private-ship event
                  │
       ┌─────────────────────┐
       │  Personal-use phase │  Capacitor app sideloaded to Rémy's
       │                     │  own phone (APK / TestFlight). Real
       │                     │  value at small amounts. No public
       │                     │  users. No app store. JS signing
       │                     │  acceptable; auth layer required.
       └──────────┬──────────┘
                  │
                  ▼  public-ship event
                  │
       ┌─────────────────────┐
       │   Public phase      │  App Store, Play Store, F-Droid,
       │                     │  reproducible builds, finalized
       │                     │  brand, third-party security audit,
       │                     │  hosted tier (or explicit defer).
       └─────────────────────┘
```

### What gates the private-ship event

Things needed before Rémy installs the app on his own phone with
real value:

- **Capacitor wrap** built and working.
- **Native plugins** integrated: secure storage (Keychain /
  Keystore), biometric, camera (QR), share, clipboard.
- **Authentication layer**: app lock with passphrase + biometric.
  Rémy needs his daily-use phone app locked.
- **Recovery flow disclosure** (per pending pre-implementation
  item `seed-backup-disclosure`): seed-backup warning +
  acknowledgment for TallyKeep-managed Purse (per
  `purse-flavors`). Required because Rémy will be putting real
  value in Purse seeds whose loss = funds gone.
- **Self-review** of security posture: walk through the threat
  model addendum, verify nothing leaks.
- **Mobile UI fine-tuned** to the level Rémy considers fit for his
  own daily use.

### What gates the public-ship event (additional to private-ship)

Things needed before TallyKeep ships beyond Rémy:

- **Native secp256k1 signing** (replaces JS `@noble/secp256k1`).
  The bar in this segment (Phoenix, Aqua) is native sign + signed
  releases.
- **Reproducible build pipeline** in CI. Supply-chain credibility
  for public users.
- **App Store / Play Store distribution** + listing assets.
- **F-Droid licensing audit** (Capacitor licence chain, any
  Lightning SDK).
- **Third-party security audit** of the full system.
- **Brand voice and identity finalized** — placeholder amber gone,
  copy written.
- **Public privacy policy and terms of service**.
- **Customer support infrastructure** (issue triage, response
  expectations).
- **Hosted tier launch** — or an explicit decision to defer it past
  public-ship.

### What stays locked from day one (regardless of phase)

The architectural commitments that shape the code itself:

- No custody, ever.
- No keys to backend.
- No accounts on TallyKeep infrastructure.
- Open source from day one.
- Honest abstraction in UX.

These are not phase-gated. Relaxing them in any phase would mean
rewriting at the next phase, defeating the point.

### What relaxes during the dev phase only

- Capacitor wrap not yet built.
- Native plugins stubbed.
- Backend wiring partial (we use what's there; deltas land in
  iterations).

### What relaxes during the personal-use phase

These are still acceptable while Rémy is the only user, on his own
devices, with small amounts:

- JS-side `@noble/secp256k1` signing (instead of native plugin).
  Known weaker model: a malicious dependency or WebView RCE during
  the signing window could extract the seed; tolerable when assets
  and devices are Rémy's. Public-ship requires the native plugin.
- Reproducible builds optional.
- F-Droid audit deferred.
- Brand placeholder remains.
- Self-conducted security review.
- Sideload distribution only (no store).

## Consequences

- **"v1" as a project reference is dropped.** Tagging items as
  "v1.5", "v2", "v3" no longer maps cleanly. The reference points
  are the two events: private-ship and public-ship.
- **`future_iterations.md` entries are tagged** as `pre-shipping`
  (before the public-ship event; may be needed for either private-
  ship or public-ship), `post-shipping` (after public-ship), or
  TBD (Rémy's call when sharpening).
- **The threshold for the private-ship event is Rémy's call:** "I
  want this in my pocket, on my phone, with real value." Relatively
  close — the Capacitor wrap is mostly mechanical work after the UI
  is fine-tuned, plus the security-health and auth-layer work.
- **The threshold for the public-ship event is also Rémy's call:**
  "I want this in other people's pockets." Materially further — the
  ship-gate work bundle is substantial.
- **Authentication layer becomes a private-ship requirement**, not
  a public-ship requirement. Rémy needs an app lock for his own
  daily phone, not just for hypothetical future users.
- The `ship-gate` term remains useful as the name of the **work
  bundle** that gates public-ship. The event itself is the
  public-ship event.

## Affected files

- `pre-implementation.md` — item `native-secp256k1-signing`
  reference still valid; the text "ship-gate" still maps to the
  public-ship event work bundle.
- `future_iterations.md` — entries tagged with `Milestone:`
  pre-shipping / post-shipping / TBD; the "Ship-gate
  meta-iteration" entry refines into the public-ship event bundle.
- `concerns/threat_model.md` Mobile addendum — JS-signing-relaxation
  applies through the personal-use phase, not just dev phase.
- `UI/README.md` — "ship-gate" references continue to mean the
  public-ship event work bundle.
- `next_iteration.md` — mentions of "v1" updated to phase
  references.
