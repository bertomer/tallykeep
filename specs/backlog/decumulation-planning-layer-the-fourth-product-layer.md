# Decumulation + planning layer (the fourth product layer)

- **Captured:** 2026-05 (same sparring session; archive file as above)
- **Motivation:** TallyKeep's three current layers (savings /
  banking / trading) cover accumulation and current spending.
  They don't cover decumulation — "how do I spend this when I no
  longer earn." Pensions are roughly 70% decumulation, 30% growth;
  current spec is the opposite. Vault-as-pension is **segment-
  dependent**: in high-inflation economies (Argentina, Turkey,
  Nigeria, Lebanon) the Vault IS the pension because the local
  "risk-free fiat asset" doesn't exist; in EU the Vault
  *complements* traditional pension infrastructure (PEA / PER /
  assurance-vie give tax wrappers self-custody can't replicate
  without becoming a PSAN/CASP custodian — which would destroy
  the self-custody thesis).
- **Sketch:** SweepPolicy in reverse, same primitive. Vault /
  Strongbox as source, Account / Purse as sink, scheduled or
  trigger-driven. Three additions beyond raw periodic sweep:
    1. **Buffer layer (bucket strategy from CFP literature).**
       12–24 months of declared monthly spend in stable form
       (Purse, plus possibly a small stablecoin sleeve depending
       on resolution of the "stablecoins as transit" candidate
       principle below). Replenish when BTC is up. Textbook fix
       for **sequence-of-returns risk** — the classic retirement-
       finance failure mode (force-selling stack at the bottom
       during drawdowns).
    2. **Dynamic withdrawal rate.** Even the simple "draw 4% of
       vault annually, recalculate yearly" beats fixed-EUR/month
       substantially. Guyton-Klinger guardrails or variable-
       percentage-withdrawal as a policy layer on top of
       SweepPolicy.
    3. **Tax-aware projection.** France: 30% PFU on crypto capital
       gains. **Show** projected tax events alongside projected
       purchasing power; do not **advise** (configurable
       simulator, not "we recommend X% per year" — that crosses
       AMF rules on personalized financial advice).
- **Touches:** new product layer (significant enough to warrant
  its own spec scope — likely a new top-level concern, e.g.
  concerns/decumulation.md, or a sibling subdirectory to
  `holdings/` / `concerns/` if it grows multi-file; exact module
  shape decided at sharpen time), domain model (SweepPolicy
  direction + new Buffer / WithdrawalRate entities), treasury
  layer (cap-gains tagging in LedgerEntry), UI (calculator +
  planning view), threat model, regulatory framing
- **Status:** sketched
- **Milestone:** post-shipping (far post — needs a population of
  users who have accumulated enough to plan decumulation)
- **Notes:**
    - **Regulatory framing locked in source notes:** frame as
      **configurable calculator + automation the user drives**,
      never as personalized advice. AMF actively polices
      personalized financial advice in France.
    - **"Without any risk" doesn't appear in user-facing copy.**
      BTC has volatility (60–80% drawdowns are historically
      normal), regulatory, and operational risk (lost keys,
      multisig coordination). Source notes flag the language as
      trip-wire for MiCA marketing rules in EU. Candidate brand-
      voice guardrail.
    - Segment-driven UX: Argentine schoolteacher vs French
      employee with a PER have different decumulation needs. The
      planning view exploration for each is itself a sharpening-
      session when this entry promotes.
    - Direct-BTC-payment as a withdrawal path is bonus; off-ramp
      is the realistic default for the foreseeable future (BTC
      direct-pay still <5% of normal household spend even in
      target markets, per source notes).
    - Adjacent to but distinct from the existing "Retirement plan
      with timelock" entry. Timelock is the script-enforced
      lock-period mechanic on a Holding; this entry is the
      consumption-planning layer on top of accumulated Holdings.
      They compose.
