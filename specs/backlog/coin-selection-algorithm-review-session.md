# Coin selection algorithm review session

- **Captured:** 2026-05 (from module 13 Q7, pre-retirement; Rémy
  flagged for explicit re-review during the consolidation merge)
- **Motivation:** The current default is `BranchAndBound`
  (privacy-preferring), with per-payment override gated by the
  `banking.coin_selection_per_payment_override` feature flag. That
  default was set early in the spec and hasn't been revisited with
  current understanding of fee dynamics, privacy practice, and
  target-market behaviour. Worth a dedicated session before
  public-ship to confirm or change.
- **Sketch:** Walk through the trade-offs across the standard
  algorithms (BranchAndBound, Single Random Draw, Knapsack, Largest
  First) with current data — fee landscape, privacy implications,
  expected wallet sizes for target users. Decide the default plus
  per-profile overrides. If the default changes, document with an
  ADR and update module 06.
- **Touches:** banking layer (coin selection), profiles + flags,
  threat model (privacy implications), tx composition tests
- **Status:** sketched
- **Milestone:** **pre-shipping** — between the private-ship event
  and the public-ship event, during the personal-use phase. Rémy's
  explicit ask: dedicated session in that window.
- **Notes:** Per-payment override is gated behind the
  `banking.coin_selection_per_payment_override` flag — power-user
  territory. The question is whether the *default algorithm* is
  right. Privacy-preferring defaults age well; fee-minimizing
  defaults age noisily.
