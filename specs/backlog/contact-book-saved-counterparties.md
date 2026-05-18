# Contact book / saved counterparties

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** Recurring counterparties (rent recipient, family
  member, regular vendor) currently require pasting an address each
  time. A saved-counterparty model with metadata makes recurring
  payments faster and harder to misdirect.
- **Sketch:** Per-counterparty record with a name, one or more
  addresses (or a static address for vendors who use it), notes,
  preferred fee tier. Send flow gets a "From contact" affordance.
  Categorization can auto-populate counterparty when a saved
  address matches.
- **Touches:** domain model (new entity), send flow, categorization,
  receive flow (sharing your address as a contact)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Privacy implications: a contact book on a hosted-tier
  backend is a higher-value target. Consider client-side encryption
  or self-hosted-only at first.
