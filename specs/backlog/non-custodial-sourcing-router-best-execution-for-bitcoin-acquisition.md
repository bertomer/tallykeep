# Non-custodial sourcing router (best-execution for Bitcoin acquisition)

- **Captured:** 2026-05 (sparring session captured verbatim in
  `archive/2026-05_parking_notes_sourcing_and_decumulation.md`)
- **Motivation:** Atomic-swap venues (SideSwap, Mostro, Boltz) and
  custodial Accounts are paths to the same outcome — sats into a
  Holding. Building a venue forks scope into protocol territory
  currently being closed by Lightning Labs / Blockstream / Tether-
  Bitfinex multi-year teams. Building a **router** that picks the
  best path per transfer is the wedge: Smart Order Routing applied
  to self-custody Bitcoin acquisition. Reinforces banking-grade
  ergonomics; never asks the user the word "swap."
- **Sketch:**
    - Sourcing path becomes a first-class concept alongside
      `CustodialProvider` Accounts. User sees a single banking-style
      "transfer" UI; routing happens behind it.
    - Evaluator inputs: amount, time tolerance, counterparty
      preferences, depth, current quotes, user's connected providers.
    - Suggested integration order: SideSwap (Liquid PSBT atomic
      swaps — most production-ready) → Mostro (Nostr-based LN P2P)
      → Boltz (quote service for BTC ↔ LN ↔ Liquid) → custodial
      route + immediate sweep (the dev-phase path, becomes one
      input among many).
    - Compliance framing: **"never recustody," not "no KYC."** Most
      realistic users KYC at the on-ramp anyway. The wedge is
      "identity proven once at the on-ramp, funds stay sovereign
      forever."
- **Touches:** treasury layer, domain model (sourcing path
  concept — possibly a new entity), UI sourcing flow, threat
  model, regulatory posture
- **Status:** sketched
- **Milestone:** post-shipping (source notes explicitly v1.5+)
- **Notes:**
    - **Direct competitor on the sourcing side: Peach Bitcoin** —
      mobile-first, Swiss, EU/LatAm/Africa coverage. Different
      wedge (Peach is a venue; TallyKeep would be a router across
      venues + custodial), but the closest market overlap. Study
      feature set and traction before sharpening.
    - **SideSwap caveat:** venue (matching server) is trusted; chain
      (Liquid Federation, ~70 entities) is federated. If single-
      vendor risk matters, build on the open Liquid PSBT swap
      protocol itself (`docs.liquid.net/docs/swaps-and-smart-contracts`),
      with LiquiDEX / TDEX as alternative consumers.
    - **Vocabulary discipline.** "Swap" overloads three different
      things in crypto: (1) atomic-swap primitive (HTLC/PTLC,
      proper finance: DvP with simultaneous bilateral settlement);
      (2) CLOB trading with atomic settlement (SideSwap, Bisq —
      these are *trades*, not swaps); (3) AMM "swaps" (Uniswap-
      style, different design school, doesn't fit the wedge —
      impermanent loss, slippage on size, MEV). Integrate (2);
      skip (3). Worth a vocabulary ADR when this entry sharpens.
    - **Don't build a venue.** Source notes are emphatic — building
      an orderbook fragments solo-builder scope across two
      unrelated hard problems with no compounding leverage. The
      router is the moat; protocols underneath are commodity
      infrastructure to ride on.
