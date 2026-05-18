# Vault Send for all shapes

- **Captured:** 2026-05 (from module 12, pre-retirement). Re-scoped
  2026-05-15 under ADR-0010 β: v1 ships Vault onboarding for both
  shapes (single-sig + timelock; multisig with or without timelock)
  via the Vault wizard. This iteration is now narrowly about Vault
  Send — the genuinely hard surface — plus the Vault detail page
  that hosts the Send affordance.
- **Motivation:** Per ADR-0010 β, Vault Send is deferred
  shape-agnostic because the multi-signer PSBT coordination,
  cosigner-status UI, partial-signature collection, and
  chain-side timelock-check display deserve their own design
  pass. Shipping Send for both shapes together preserves Vault
  detail UX uniformity — one detail page across shapes; Send
  greyed-out in v1 lifts for both at the same time when this
  iteration ships.
- **Touches:** banking layer (PSBT construction + multi-signer
  coordination + timelock-check at broadcast), UI Vault detail
  page (full design lands here — currently a v1 placeholder),
  UI Vault Send flow (compose / review / export / re-import /
  broadcast across all five Vault shape variants), threat model
  (PSBT roundtrip with chain-side timelock check; cosigner
  coordination ceremony), brand / mockups (cosigner annotation
  UI, per-signer-status UI, per-UTXO unlock ledger for CSV
  shapes).
- **Status:** sketched. v1 ships descriptor onboarding for all
  five Vault shapes; this iteration picks up Vault detail + Send
  for the same five shapes.
- **Milestone:** post-shipping
- **Notes:** "Promote a Strongbox to a Vault" migration lands here
  too — a single-Holding type-relabel when the user adds multisig
  to the descriptor (no on-chain action, the chain sees the same
  descriptor before and after). Single-sig + timelock cannot be
  promoted from Strongbox the same way (would require an on-chain
  send to a new script).
