# Budgeting and allocation

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** Banking-ergonomics promise extends to "where is
  my money going." Per-month spending categories, runway tracking
  (how many months of declared monthly spend at current balance),
  Holding-level allocation targets.
- **Sketch:** Categories already exist (categorization is in
  pre-shipping scope). Budgeting is the layer above: monthly limits
  per category, runway computed from declared monthly spend, alerts
  when categories cross thresholds.
- **Touches:** UI (new section), domain model (Budget entity),
  alerts/notifications system
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Touches the rejected "trading terminal" zone if not
  careful — budgeting is about consumption planning, not portfolio
  performance. Stay on the consumption side.
