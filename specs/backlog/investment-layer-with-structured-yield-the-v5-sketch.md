# Investment layer with structured yield (the "v5" sketch)

- **Captured:** 2026-05 (from module 12 v5, pre-retirement)
- **Motivation:** A constrained, contract-defined alternative to
  the lending / yield zone the spec rejects by default. Multisig
  vaults with discreet log contracts (DLCs) or LSP-mediated
  structures, where the user always retains at least one key and a
  clear unilateral exit path. Distinct from the simpler "Retirement
  plan with timelock" entry — this is yield-bearing under a contract,
  not just a CSV/CLTV lock.
- **Sketch:** A sibling product to TallyKeep's banking app, sharing
  deployment shell and possibly auth (post-public-ship). Own
  database, own threat model, own regulatory analysis. Not a
  generalization of the current banking-app domain.
- **Touches:** new product surface, regulatory analysis,
  legal counsel
- **Status:** idea
- **Milestone:** post-shipping (likely far post)
- **Notes:** Requires legal review before scoping. The question is
  whether enabling these structures from within the app makes us a
  broker / arranger / custodian by some jurisdiction's reading. The
  default reflexive answer is "no"; this entry forces that question
  to be re-asked carefully if pursued. Rejected adjacent: lending,
  borrowing, yield without contract-bound user-key retention.
