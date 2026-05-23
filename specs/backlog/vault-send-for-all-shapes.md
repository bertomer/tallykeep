# Vault Send for all shapes

- **Captured:** 2026-05 (from module 12, pre-retirement). Re-scoped
  2026-05-15 under ADR-0010 β. **Narrowed 2026-05-22** — Vault
  detail page design landed in its own iteration
  (promoted into `next_iteration.md` as the active iteration on 2026-05-22).
  This entry is now narrowly about Vault Send (and Receive, which
  ships in lockstep). The detail-page-as-host language retires;
  the Send affordance is already greyed and ready to lift when
  Send ships.
- **Motivation:** Per ADR-0010 β, Vault Send is deferred
  shape-agnostic because the multi-signer PSBT coordination,
  cosigner-status UI, partial-signature collection, and
  chain-side timelock-check display deserve their own design
  pass. Shipping Send for both shapes together preserves Vault
  detail UX uniformity — one detail page across shapes; Send
  greyed-out in v1 lifts for both at the same time when this
  iteration ships. Receive ships with Send: the verify-on-device-
  for-each-cosigner ceremony belongs in the same dedicated design
  pass.
- **Touches:** banking layer (PSBT construction + multi-signer
  coordination + timelock-check at broadcast), UI Vault Send +
  Receive flows (compose / review / export / re-import /
  broadcast across all five Vault shape variants; verify-on-
  device-per-cosigner address ceremony for Receive), threat model
  (PSBT roundtrip with chain-side timelock check; cosigner
  coordination ceremony), brand / mockups (Send + Receive
  surfaces; per-signer-status UI; partial-signature collection
  UX). **Vault detail page is no longer in this iteration's
  scope** — it shipped via the Vault-detail iteration.
- **Milestone:** post-shipping
- **Notes:** "Promote a Strongbox to a Vault" migration lands here
  too — a single-Holding type-relabel when the user adds multisig
  to the descriptor (no on-chain action, the chain sees the same
  descriptor before and after). Single-sig + timelock cannot be
  promoted from Strongbox the same way (would require an on-chain
  send to a new script).
