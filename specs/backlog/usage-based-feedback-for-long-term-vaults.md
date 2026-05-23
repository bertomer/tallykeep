# Usage-based feedback for long-term Vaults

- **Captured:** 2026-05-15 (during Vault-wizard brainstorm, ADR-0010
  β). **Reframed 2026-05-22** per ADR-0018 — `Purpose.LONG_TERM`
  retired; Vault is long-term by type. The analyzer no longer
  needs a per-Vault tag to compare against; the baseline is the
  type definition itself.
- **Motivation:** Any Vault whose observed outflow frequency
  contradicts the type-implied long-term-storage intent is signal
  worth surfacing — a Vault with weekly outflows is the canonical
  treasury-misuse pattern. With ADR-0018 the analyzer compares
  observed spend frequency against the type-implied "rare-by-
  design" baseline rather than a user-declared tag. Surface as a
  security-health item suggesting a tighter setup (on-chain
  timelock, or possibly that the user wanted an Account / Purse).
- **Touches:** security-health system (pending `seed-backup-
  disclosure` arbitration), Vault detail (where the user sees the
  warning), holdings/04_vault.md type-specific safeguards (already
  captures this as deferred).
- **Status:** idea
- **Milestone:** post-shipping. Folds into the broader
  security-health system iteration when that arbitration closes.
