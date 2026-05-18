# Target-price accumulation (limit-bid sourcing)

- **Captured:** 2026-05 (same sparring session as the sourcing-
  router entry; archive file as above)
- **Motivation:** Once instant-execution sourcing exists, the
  natural follow-on is letting the user post a passive limit bid
  at the price they're happy to buy at, routed to the best venue.
  The fill IS the goal — no adverse-selection problem, no market-
  making risk. Banking-grade framing: **"Set the price you want
  to buy at. We route your bid to the best venue. Fill auto-sweeps
  to Strongbox."** Same liquidity-contribution effect as market-
  makers without the structural risk story.
- **Sketch:** New SourcingPolicy variant (sibling to instant-
  sourcing): limit-price bid posted to the routed venue, listening
  for fill, on-fill triggers auto-sweep to the destination Holding.
  Cancel / amend affordances. Execution-uncertainty disclosure
  honest — bid at X, BTC rallies past X without touching it →
  user watched from sidelines, capital locked. That's the cost of
  being a patient buyer, which is what the target user signed up
  for.
- **Touches:** treasury layer, sourcing-router (blocks on the entry
  above), UI sourcing flow, threat model
- **Status:** sketched
- **Milestone:** post-shipping (sequencable: instant-execution
  router first, limit-price router after — source notes frame as
  v1 → v1.5)
- **Notes:**
    - **Vocabulary lock candidates (sharpen alongside brand voice
      work):**
        - ❌ "Earn the spread" — misleading. Real spread capture
          (50–200 bps on thin books) requires posting both sides
          and getting filled on both = market making. Likely trips
          AMF/CSSF marketing rules in EU.
        - ✅ "Skip the taker fee" — honest. User saves the venue's
          taker fee (typically 0.2%) by being a maker. Fee saving,
          not spread capture.
    - **Do not build market-making.** Onboarding clients into a
      structurally losing game dressed as "earn the maker fee" =
      reputational damage. Strict distinction in source notes:
      target-price accumulation is single-sided and aligned with
      directional view; market-making is two-sided and faces
      adverse selection on thin books.
    - Reference precedents: Strike's "buy the dip," Swan's limit
      orders. Neither does this well in a self-custody, route-
      across-venues shape.
