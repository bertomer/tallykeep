# Settlement-rails payment status with confirmation probability

- **Captured:** 2026-05 (mid-conversation, during gauntlet reframe)
- **Motivation:** Bitcoin confirmation is a statistical finality
  function, not binary. Most apps treat either 0-conf or 1-conf as
  "done." TallyKeep's locked "honest abstraction" principle turns
  this into a differentiator: show the truth in the vocabulary
  institutions already use for settlement (T+0, T+2, settlement-risk
  windows). Strong candidate for the product's single most
  distinctive feature, on two axes: vs other Bitcoin apps (which
  hide settlement reality behind binary "sent"/"confirmed"
  language), and vs retail banking apps (which often cannot show
  in-transit states at all, because their settlement infrastructure
  doesn't expose them to the customer-facing layer). Bitcoin's
  on-chain transparency makes the in-transit visible by default;
  TallyKeep is the surface that does it justice.
- **Sketch:** Each transaction surfaces a status flow modeled on
  institutional payment rails:
    1. Instruction composed (PSBT created, not signed)
    2. Instruction signed (PSBT signed, not broadcast)
    3. Instruction acknowledged (broadcast, in mempool)
    4. Settlement (on-chain inclusion + depth)
  At each step, surface a finality probability:
    - In mempool: probability of inclusion in next N blocks, computed
      from fee rate vs current mempool dynamics
    - At depth k: reversal probability under a stated adversary model
    - At depth ≥ 6: ~99.99% finality, "settled" (assumptions visible)
- **Touches:** UI tx detail page, new `confirmation_probability`
  service in backend (mempool dynamics + reorg modeling), threat
  model nuance
- **Status:** sketched
- **Milestone:** TBD — best guess: pre-shipping if the pattern
  validates as a defining feature during the personal-use phase.
  Strong differentiator candidate; if Rémy decides this is what
  TallyKeep's distinctive UI surface should be, it ships at
  public-ship. A lighter version could be a post-shipping
  enhancement.
- **Notes:** Probability math has well-known formulas (Nakamoto's
  original paper; Wuille and others have refined them). Care needed
  to avoid false precision: showing "99.99%" requires the user to
  see the assumed adversary hashpower and the natural-orphan
  baseline, otherwise the number is meaningless. Mempool.space
  surfaces fee-based inclusion estimates already; the novel part
  here is the institutional payment-rails framing and the
  integration as a first-class transaction status. Aligns naturally
  with the banking vocabulary the product already uses.
