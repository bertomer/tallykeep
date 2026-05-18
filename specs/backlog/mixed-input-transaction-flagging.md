# Mixed-input transaction flagging

- **Captured:** 2026-05 (from module 13 Q6, pre-retirement; Rémy
  flagged for explicit follow-up so it doesn't fold silently into
  the broader Blueprint / CoinJoin work)
- **Motivation:** When an on-chain transaction has some inputs from
  user-controlled Holdings and some from external sources, the
  default LedgerEntry classification is net-effect-only (OUTGOING
  if balance goes down, INCOMING if up). That hides a meaningful
  pattern: the transaction is likely a CoinJoin, a PayJoin (receiver
  contributing inputs for privacy), or a multi-party split payment.
  The user's categorization options for a "real" outgoing payment
  versus a collaborative transaction differ; squashing them looks
  fine until the distinction matters.
- **Sketch:** Detect mixed-input transactions during chain scan.
  Surface a tag on the LedgerEntry — "collaborative transaction" or
  similar — without changing the LedgerEntry's direction (net
  effect is still net effect). Categorization UI offers
  collaborative-transaction-specific labels alongside the standard
  set. Blueprint analyzer surfaces the count of such transactions
  per Holding.
- **Touches:** chain scanner, LedgerEntry schema (new tag field
  or flag), categorization UI, Blueprint analyzer
- **Status:** sketched (lean from original Q6: don't change
  direction, flag distinctly)
- **Milestone:** **pre-shipping**, after private-ship — sits in the
  personal-use phase, between private-ship and public-ship. Can
  defer to post-shipping if it doesn't surface as friction during
  Rémy's daily-use period.
- **Notes:** Distinct from the CoinJoin / PayJoin entry, which
  covers TallyKeep *initiating* collaborative transactions. This
  entry is about *detecting* them when they happen — including
  cases where the user's other wallet (Sparrow, Wasabi, Phoenix)
  was the one initiating. The detection logic doesn't depend on
  TallyKeep supporting CoinJoin / PayJoin natively.
