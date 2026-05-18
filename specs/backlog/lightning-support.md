# Lightning support

- **Captured:** 2026-05 (from design_decisions.md §12, pre-merge)
- **Motivation:** Instant low-value spending. Mobile-first feature
  for daily-use markets where on-chain fees price out small payments.
- **Sketch:** Breez SDK first; evaluate own LSP later (LSPS0/1/2).
  Mobile-only spending path (Capacitor); desktop read-only for
  hosted-tier users; both surfaces for self-hosted users running
  CLN/LND.
- **Touches:** `concerns/lightning_placeholder.md`, mobile spec, UI send/receive,
  threat model
- **Status:** sketched
- **Milestone:** TBD — Rémy explicitly flagged this as needing
  re-analysis. Lightning may be a public-shipping differentiator
  (instant low-value spending is a real target-market need) or a
  post-shipping enhancement. Breez SDK license terms also need
  verification before commit.
- **Notes:** Capacitor-only for spending per
  mobile_form_factor_decision.md. If pre-shipping, increases the
  ship-gate scope significantly.
