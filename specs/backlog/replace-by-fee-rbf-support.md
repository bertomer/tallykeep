# Replace-By-Fee (RBF) support

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Lets the user bump a stuck transaction's fee
  without composing from scratch. Standard wallet feature.
- **Sketch:** Behind a `banking.rbf.enabled` flag. On a broadcast-
  but-unconfirmed tx, surface a "Bump fee" affordance. Compose a
  replacement PSBT signaling RBF, sign externally, broadcast.
- **Touches:** banking layer, send flow, UI tx detail page, threat
  model (RBF can be confusing; settlement-rails framing helps)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Pairs naturally with the settlement-rails / confirmation-
  probability entry. RBF visibility makes the "not yet final" state
  legible.
