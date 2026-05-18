# LedgerEntry CSV export

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Tax filing and accounting integration. Self-hosted
  users in particular need to produce reports for their tax
  authorities; exports let them feed into existing tools without
  TallyKeep having to grow into an accounting suite.
- **Sketch:** Settings → Export → CSV of LedgerEntries with all
  available fields (txid, direction, amount, fee, counterparty if
  categorized, label, timestamp, confirmation depth at export time).
  Per-Holding or whole-portfolio. Per-year filter.
- **Touches:** API (new export endpoint), UI settings, accounting
  format conventions (probably plain CSV + a sidecar JSON for
  schema)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Hosted-tier privacy implications worth surfacing — the
  exporter sees everything regardless of who runs it.
