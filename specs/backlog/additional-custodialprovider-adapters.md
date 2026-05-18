# Additional CustodialProvider adapters

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement);
  revised 2026-05-16 (Account-wizard iteration cut Bitstamp from
  v1 to focus on Kraken-first ship).
- **Motivation:** Pre-shipping currently ships Kraken only. Broader
  coverage matters for target markets — Bitstamp's whitelist-via-
  web-UI shape needs the withdrawal sub-flow's manual-attestation
  branch; Bitfinex has Argentine users; Coinbase Advanced has US /
  EU coverage; LatAm-native venues (Lemon, Buenbit, Belo, Ripio)
  are higher priority for the Argentina launch than Coinbase.
- **Sketch:** Each adapter is a ccxt wrapper (or custom client for
  non-ccxt venues — see the separate Swissquote entry) with
  adapter-specific fixtures, integration tests, and a per-provider
  helper-banner copy block (Step 1 of the Add Account wizard
  swaps banner content based on the picked adapter). Each adapter
  declares its `supports_withdrawal_keys` and `whitelist_read_api`
  capabilities at registration; the wizard reads them to gate
  Step 3's suggestion card and the withdrawal sub-flow's UX.
- **Touches:** treasury layer adapters, integration test harness,
  Add Account wizard provider dropdown, per-provider helper-banner
  copy registry.
- **Status:** idea
- **Milestone:** post-shipping (Bitstamp specifically: pre-public-
  ship if user demand surfaces; the v1 cut was scope-tightening,
  not architectural).
- **Notes:** Priority order is market-driven. Argentine launch
  → Lemon, Buenbit, Ripio, Belo first. Bitstamp is the lowest-
  friction next addition because the adapter is already
  contract-compatible with the treasury layer; it just lost the
  dropdown slot in v1. Bitfinex / Coinbase Advanced if user
  demand surfaces.
