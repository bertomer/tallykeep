# Retirement plan with timelock

- **Captured:** 2026-05 (from design_decisions.md §14, pre-merge)
- **Motivation:** Bitcoin script-enforced lock period for long-term
  holdings, supporting structured retirement planning.
- **Sketch:** New Holding sub-type or Vault variant with CSV/CLTV
  timelock.
- **Touches:** domain model, banking layer, UI vault flows, threat
  model
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Touches the rejected "yield" zone if not careful —
  strictly self-custodial timelock, no collateralization. Needs
  legal review before commit.
