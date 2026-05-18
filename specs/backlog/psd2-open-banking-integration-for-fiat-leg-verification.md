# PSD2 / Open Banking integration for fiat-leg verification

- **Captured:** 2026-05 (same sparring session — EU-specific angle
  on the non-custodial sourcing question; archive file as above)
- **Motivation:** Every "P2P BTC-fiat" platform (Bisq, HodlHodl,
  Peach, Mostro) faces the same asymmetry: BTC leg is verifiable
  on-chain, fiat leg isn't — atomicity is cryptographically
  impossible, so they all bolt on a multisig + arbitrator pattern
  resolving fiat disputes socially. **PSD2 Access-to-Account (AIS)
  APIs** let a regulated entity programmatically verify "€X landed
  in this IBAN from that IBAN at this timestamp." Not trustless —
  bank and AISP are trust anchors — but **collapses ~95% of fiat-
  receipt disputes into automated resolution.** No existing P2P
  platform has built this properly. If TallyKeep is EU-domiciled
  and partners with an AISP (Tink, TrueLayer, Bridge by Bud) or
  holds an AISP license itself, there's a real wedge for the
  sourcing-router's EU-fiat-input path.
- **Sketch:**
    - For the EU sourcing-router path on P2P venues: when the user
      receives fiat into their connected IBAN as part of a P2P
      sell-side leg, the AISP integration verifies receipt
      automatically and releases the BTC leg from escrow without
      arbitrator involvement.
    - Two licensing paths: (a) partner with an existing AISP —
      lower regulatory cost, dependency on the partner; (b) become
      AISP-licensed under ACPR — higher cost, fewer dependencies,
      real moat.
    - Honest disclosure: AISP + bank are trust anchors; the
      "atomicity" here is regulatory-grade, not cryptographic.
- **Touches:** treasury layer, sourcing-router (blocks on the
  router entry above), regulatory posture (AISP licensing is a
  real regime change), threat model, new external dependency
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:**
    - **Hostage to the sourcing-router entry sharpening + a
      separate regulatory analysis** of AISP licensing cost (PSD2
      AIS under ACPR in France — the lighter end of the payment-
      services regime; PSP authorization is heavier and not the
      target here). Verify current ACPR / PSD2 framework before
      committing.
    - Why no P2P platform has built it: most are non-EU or pre-
      EU-presence, and the AISP path is real work. This entry is
      what "EU domicile is a wedge instead of a tax" looks like
      for TallyKeep on the sourcing side.
