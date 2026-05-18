# DCA primitive

- **Captured:** 2026-05 (from design_decisions.md §14, pre-merge)
- **Motivation:** **Dollar-Cost Averaging** — recurring scheduled
  purchases at fixed intervals regardless of price, to average out
  timing risk. Removes the no-Bitcoin-yet onboarding friction in
  target markets where users haven't accumulated yet and want a
  set-and-forget acquisition path.
- **Sketch:** Schedule + connected Account + sweep policy.
- **Touches:** treasury layer, scheduler, UI
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Pull forward only if real user feedback shows
  acquisition friction is a launch blocker. Touches the deferred
  "order placement on custodial providers" zone — likely needs that
  feature first.
