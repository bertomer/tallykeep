# Possible Purse / Strongbox collapse

- **Captured:** 2026-05 (from module 13 Q8, pre-retirement)
- **Motivation:** The four-Holding-type model bets that the Purse vs
  Strongbox distinction matters to a real user. The fiat-banking
  parallel — where "checking" and "card balance" collapsed into one
  account view long ago — suggests the bet might be wrong. If during
  the personal-use phase Rémy finds himself choosing one over the
  other arbitrarily, collapsing to a single "user-keys Holding" type
  with a `signing_method` attribute (light vs ceremonial) reduces
  the model to three types and may match how users actually think.
- **Sketch:** Track during personal-use phase. If the distinction
  feels artificial, draft a domain-model migration: collapse Purse
  and Strongbox into a single Holding type with a `signing_method`
  enum. Vocabulary lock means the rename is non-trivial — this would
  need an ADR.
- **Touches:** `02_domain_model.md`, `UI/README.md` Holding
  vocabulary table, every iteration that referenced Purse / Strongbox
  separately
- **Status:** observation-mode (not active work)
- **Milestone:** TBD — only acted on if the personal-use phase
  signals duplication. Likely never; flagged anyway because the
  vocabulary lock is foundational and worth re-examining once.
- **Notes:** Touches the locked "Holdings are first-class and typed"
  principle. Reducing four to three types is itself a re-litigation
  of vocabulary; deserves an ADR if pursued.
