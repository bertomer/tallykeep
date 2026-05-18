# Usage-based feedback for long-term Vaults

- **Captured:** 2026-05-15 (during Vault-wizard brainstorm, ADR-0010
  β).
- **Motivation:** A `purpose=long_term` Vault whose observed
  outflow frequency contradicts the declared long-term intent is
  a real declared-vs-observable mismatch — declaration is the
  flag, observable is the spend frequency, the analyzer has
  substance to flag. Surface as a security-health item suggesting
  an on-chain timelock upgrade or migration to Strongbox when the
  gap is wide enough. Honest variant of the rejected
  soft-timelock-declaration idea.
- **Touches:** security-health system (pending `seed-backup-
  disclosure` arbitration), Vault detail (where the user sees the
  warning), holdings/04_vault.md type-specific safeguards (already
  captures this as deferred).
- **Status:** idea
- **Milestone:** post-shipping. Folds into the broader
  security-health system iteration when that arbitration closes.
