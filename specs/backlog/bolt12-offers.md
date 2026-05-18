# BOLT12 offers

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** BOLT11 invoices are single-use; BOLT12 offers are
  reusable, smaller, and avoid the "regenerate the invoice every
  time" flow. Where supported, they are a better default for
  Lightning receive.
- **Sketch:** Default to BOLT12 on Purse-with-Lightning where the
  LightningProvider supports it (CLN: yes; LND: experimental;
  Phoenix: depends on version). Fall back to BOLT11 otherwise.
- **Touches:** Lightning placeholder module, LightningProvider
  interface, receive flow
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Lightning-dependent — only relevant once the Lightning
  iteration ships.
