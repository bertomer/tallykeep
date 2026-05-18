# "Tap to see under the hood" — UI spine pattern

- **Captured:** 2026-05 (mid-conversation, exploring TallyKeep's
  distinctive UI behavior)
- **Motivation:** Bitcoin makes nearly every number a value with
  nuance behind it (balance = pending + confirmed UTXOs;
  confirmation count = probabilistic finality; fee = mempool
  dynamics; rate = source + staleness). Most apps hide this nuance
  to feel clean. TallyKeep's honest-abstraction principle says
  don't hide; this pattern says surface on demand. Strong candidate
  for the product's spine behavior — a behavior flowing through
  every screen rather than a separate feature module. Aligns
  directly with the settlement-rails / confirmation-probability
  idea.
- **Sketch:** every numeric or stateful element is tappable; tap
  surfaces what's behind it.
    - Tap a balance → UTXO breakdown, pending vs confirmed split
    - Tap a confirmation count → probability framing with assumed
      adversary hashpower and natural-orphan baseline visible
    - Tap a fee tier → mempool dynamics, fee distribution,
      expected time-to-confirm
    - Tap a "via [source]" rate attribution → fetch timestamp,
      last N quotes, divergence from another source
    - Tap a security indicator (declared-vs-observable) → the chain
      observation that produced the verdict
    - Tap a Holding type badge → the banking analogy expanded
- **Touches:** every UI surface (this is a spine pattern, not a
  feature module)
- **Status:** sketched — candidate for a defining UX pattern
- **Milestone:** TBD — decision path is mockup iteration. If the
  pattern feels natural after a few screens, becomes pre-shipping
  (defining UX); if forced, drops or scopes down.
- **Open questions (block commit-as-direction):**
    - **Mobile friendliness.** Tap targets are premium on small
      screens; "everything is tappable" risks accidental taps and
      conflicts with scroll/swipe gestures. Maybe restricted to
      specific element types only.
    - **Visual signaling.** How do users know what's tappable
      without cluttering every screen? Options to evaluate in
      mockups: subtle dotted underline on tappable values; a
      consistent color tint on tappable numbers; a single info
      icon adjacent to tappable groups; long-press instead of tap;
      a dedicated "explain mode" toggle that highlights everything
      at once. None is obviously right; each has trade-offs.
    - **Consistency of disclosure.** Every tappable should reveal
      the same SHAPE of info (popover? bottom sheet? inline
      expand?). Inconsistency would feel chaotic.
    - **Discoverability.** If it's the spine, users need to know
      about it. Onboarding mention? First-run hint? Or let them
      discover by accident?

---
