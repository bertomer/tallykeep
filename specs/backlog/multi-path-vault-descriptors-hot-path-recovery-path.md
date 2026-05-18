# Multi-path Vault descriptors (hot path + recovery path)

- **Captured:** 2026-05-15 (during Vault-wizard brainstorm, ADR-0010
  β).
- **Motivation:** Real inheritance / anti-loss designs combine
  multiple spending paths: e.g. `or(2-of-3 hot keys with short
  CSV, 1-of-3 recovery key with longer CSV)`. v1 Vault accept set
  is deliberately narrow — `m-of-n` optionally + a single
  timelock — and rejects multi-path miniscript constructs
  (or-trees, decaying multisig, hashlocks) with an explicit
  "contact us" message. The use case is real; the design surface
  is bigger than the v1 wizard's parseback shape supports.
- **Touches:** Vault wizard accept set, parseback (multi-row
  spending-path display), Vault detail (per-path unlock countdown,
  per-path UTXO classification), threat model (recovery key
  custody, alternate signer coordination), holdings/04_vault.md
  vocabulary (`spending_paths` would replace the single
  `timelock_kind` / `timelock_value` pair).
- **Status:** idea
- **Milestone:** post-shipping (after the multisig-descriptor +
  Vault Send iteration; the cosigner-coordination UX from that
  iteration is a dependency)
