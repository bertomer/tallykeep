# P2P swap routes (RoboSats and similar)

- **Captured:** 2026-05 (from module 12 v3, pre-retirement)
- **Motivation:** P2P venues let users swap fiat for Bitcoin without
  KYC. RoboSats specifically targets the "no exchange account, no
  custody" path that aligns with TallyKeep's posture. As an
  optional swap route alongside CustodialProvider integration, it
  expands acquisition options.
- **Sketch:** New CustodialProvider-shaped adapter pointing at
  RoboSats (or similar) where their API permits. UX-wise more
  ceremonial than an exchange — order matching, escrow lifecycle,
  reputation scores. Likely a separate sub-flow rather than a
  dropdown option.
- **Touches:** treasury layer, adapter abstraction, threat model
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Liquidity at any P2P venue is variable; integration
  has to fail gracefully when no orders match. Regulatory implication:
  KYC-free swap routes vary by jurisdiction.
