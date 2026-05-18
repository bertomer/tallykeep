# Dynamic brand mark on first-touch surfaces

- **Captured:** 2026-05 (during onboarding-screen-1 session, after
  Rémy noted excitement about showcasing the dynamic mark)
- **Motivation:** The brand v1 mark lock doc
  (`brand/tallykeep_brand_mark_v1_lock.html` §5) already implements
  a working tap-to-regenerate-grain interaction (~80 LOC, seeded
  xorshift32 PRNG, both halves regenerate matching stripes — the
  verification metaphor of split tally sticks made tactile, the
  pedagogical heart of the brand). v1 sanctions it for the
  **landing-page hero only**; everywhere else uses the locked
  static seed. Extending the sanction to one or more first-touch
  surfaces in the app would let new users experience the verification
  metaphor at the moment of first arrival, which is structurally
  the same shape of moment as a landing-page hero.
- **Sketch:**
    - **Connect screen (primary candidate, `mobile_onboarding_01_connect.html`).**
      The screen's brand surface is `wordmark-icony` (the wordmark
      with the canonical Y embedded between "tall" and "keep"),
      not the bare icon. Make the whole wordmark area the tap
      target; on tap, only the embedded Y's grain regenerates
      (the "tall" and "keep" text stays static). This is a small
      extension of brand v1 §5, which demoed the dynamic
      interaction on the bare canonical icon — the same seeded
      PRNG and rendering function applies, only the surrounding
      typography changes. v1 → v2 lock-doc bump should explicitly
      sanction the wordmark-icony embedded Y as a dynamic surface
      alongside the bare icon. This is the user's first-touch
      moment in the app; the metaphor lands hardest here, and zero
      additional screen real estate is consumed (the brand mark
      was already going to be there).
    - **Settings → About / How it works (secondary candidate).**
      A dedicated explainer page where the mark is the visual
      anchor for "what tallykeep means as a verification primitive."
      Less time-pressured than the Connect screen, more room for
      the full caption ("The grain matches. A tally stick is split
      from a single piece of wood. The pattern on both halves is
      the proof — that's how you knew it was real.").
    - **Other surfaces** (home page, Holding detail, etc.) stay
      static-mark-with-locked-seed per the current brand rule.
- **Touches:**
    - **Brand:** v1 → v2 lock-doc bump for the mark, updating §5
      "Landing-page interaction" to extend the sanction list. Per
      `PROCESS.md §2.4`, pre-public-ship lock-doc edits are
      allowed without an ADR; v1 → v2 is the convention. Update
      the canonical SVG export in `brand/identity/` if any visual
      detail changes (probably not — the dynamic component reuses
      the canonical geometry).
    - **Frontend:** SvelteKit component implementing the demo from
      §5 of the lock doc. Mockups are static (per
      `UI/mockups/README.md`); the dynamic version lands in code.
    - **`UI/mobile.md` Onboarding section:** note that the Connect
      screen's brand mark is the dynamic variant (when this
      iteration ships).
- **Status:** sketched
- **Milestone:** **TBD** — best guess: pre-shipping (between
  private-ship and public-ship), since the personal-use phase is
  exactly when defining UX patterns get tested against daily use.
  Could also pull forward into the Capacitor / private-ship
  iteration if the wrapping work is touching this screen anyway.
- **Notes:**
    - Discoverability: the demo-hint text ("Tap to verify a new
      pair") in the lock doc is for a documentation context; the
      Connect screen probably wants a subtler hint (a one-time
      pulse on first launch? no hint and trust the affordance is
      noticed?). Sharpen during the iteration.
    - Accessibility: keyboard-activate (`Enter` / `Space`) already
      implemented in the lock doc demo. Carry forward.
    - Animation budget: the lock doc uses an 180ms opacity
      crossfade. Cheap enough on any phone. No perf concern.
    - Content of the seed display ("seed · 7777" in the lock doc
      demo) does not belong on the Connect screen — that's a
      doc-context affordance for the lock doc only.

---
