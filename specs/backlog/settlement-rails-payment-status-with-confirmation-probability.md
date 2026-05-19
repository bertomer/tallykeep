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
- **Sketch — status flow:** Each transaction surfaces a status
  flow modeled on institutional payment rails:
    1. Instruction composed (PSBT created, not signed)
    2. Instruction signed (PSBT signed, not broadcast)
    3. Instruction acknowledged (broadcast, in mempool)
    4. Settlement (on-chain inclusion + depth)

  At each step, surface a finality probability:
    - In mempool: probability of inclusion in next N blocks,
      computed from fee rate vs current mempool dynamics
    - At depth k: reversal probability under a stated adversary
      model
    - At depth ≥ 6: ~99.99% finality, "settled" (assumptions
      visible)
- **Sketch — UI placement (sharpened 2026-05-19 with Rémy):** The
  per-Holding Operations tab gains a dedicated **Pending section
  at the top**, distinct from the main settled-history feed below.
  Reasoning: the current Operations row is at 3 lines (kind/time
  + category chip + amount); adding a 4th line for "Confirmed 87%"
  on every row would clutter the entire feed, and most entries in
  the feed have long since crossed finality thresholds where the
  percentage adds noise. Instead:
    - **Pending section** (top of Operations, when non-empty):
      uppercase section label "Pending" / "Settling" /
      "In transit" — exact vocabulary call deferred to this
      iteration's design pass; "Pending" is the banking-app
      norm but "Settling" reads more honestly per the
      settlement-rails framing. The Pending section can afford
      richer rows (4–5 lines: kind + amount + settlement
      progress + counterparty/note + tap-for-detail chevron)
      because there are fewer entries — typically 0 to a
      handful at any time. Auto-promotes a row to the main
      feed below when the configured finality threshold is
      crossed (default ~6 conf / ~99.99% by Nakamoto's
      probability model; user-configurable per Holding).
    - **Main feed** (below Pending, the existing chrome from
      the Purse-detail iteration): stays compact at 3 lines
      (kind/time, optional category chip, amount). Settlement
      percentage NOT shown here — every entry has settled past
      the threshold by definition. The simplicity is a feature.
    - **Progress indicator** on Pending rows: small inline
      pill or progress bar showing the current settlement
      percentage + a human-readable depth ("3/6 blocks",
      "in mempool"). Settlement-rails framing in the tap-into
      detail page (institutional vocabulary: "settling",
      "settlement risk window", "T+block-time").
    - **Empty-state** for the Pending section: collapse the
      section entirely when there are no pending transactions
      (no chrome at rest). Re-appears the moment a Send is
      broadcast or an incoming TX is observed in the mempool.
- **Touches:** UI Purse / Strongbox / Vault Operations tabs
  (Pending section + auto-promotion rule); new TX detail page
  surfacing the full status flow; new `confirmation_probability`
  service in backend (mempool dynamics + reorg modeling); threat
  model nuance for the adversary assumptions.
- **Out of current Purse-detail iteration scope.** The current
  Operations tab ships the main feed only; rows are deliberately
  compact at 3 lines because the in-transit detail will live in
  the Pending section above when this iteration ships. The
  current iteration's `UI/mobile.md §Purse detail` Operations
  tab description carries a forward-reference to this file so
  the next agent doesn't redesign the row layout.
- **Status:** sketched
- **Milestone:** TBD — best guess: pre-shipping if the pattern
  validates as a defining feature during the personal-use phase.
  Strong differentiator candidate; if Rémy decides this is what
  TallyKeep's distinctive UI surface should be, it ships at
  public-ship. A lighter version could be a post-shipping
  enhancement.
- **Notes:** Probability math has well-known formulas (Nakamoto's
  original paper; Wuille and others have refined them). Care
  needed to avoid false precision: showing "99.99%" requires the
  user to see the assumed adversary hashpower and the natural-
  orphan baseline, otherwise the number is meaningless.
  Mempool.space surfaces fee-based inclusion estimates already;
  the novel part here is the institutional payment-rails framing
  and the integration as a first-class transaction status.
  Aligns naturally with the banking vocabulary the product
  already uses.
