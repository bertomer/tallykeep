# Account withdrawal-key sub-flow

- **Captured:** 2026-05-16 (deferred during the Account-wizard
  design pass; design pass close locked the wizard's read-only-
  only scope, but the withdrawal capability still needs its own
  design pass to ship before SweepPolicy-on-Account work begins).
- **Motivation:** Per ADR-0011, the Account Holding type carries
  a separate withdrawal credential and provider-side whitelist
  configuration. The Add Account wizard does not capture these
  (its read-only-only scope is deliberate). The Account detail
  page's Withdraw affordance is the canonical discovery surface
  but routes to a sub-flow that doesn't exist yet — until it
  ships, the Withdraw button is greyed-out with a tap-prompt
  ("coming in a later iteration"), and SweepPolicies on Account
  Holdings run in watch-and-advise mode only.
- **Sketch:** Likely 3–4 steps, reachable from Account detail OR
  from the Add Account wizard's Step 3 capability-gated
  suggestion card:
  1. **Whitelist destination.** Cross-reference UI: list the
     user's existing TK Holdings (Strongbox / Vault / Purse) as
     candidate destinations with verification badges, plus a
     "paste external address" affordance, plus the provider's
     fetched whitelist (when `whitelist_read_api = true` — Kraken)
     OR a manual attestation checkbox (when
     `whitelist_read_api = false` — Bitstamp). Picking a TK
     Holding derives its next-unused address; pasting external
     accepts any address the user has whitelisted on the
     provider's side.
  2. **Withdrawal credential paste.** API Key + Private Key
     fields, paste pattern parity with the Add Account wizard's
     Step 1. Backend validates the credential has *only* the
     provider's withdraw permission (plus the provider-required
     balance-query scope where applicable — Kraken needs both).
     Overage rejected with the same locked-copy pattern as the
     read-only credential's overage error.
  3. **Confirmation / parseback.** Recap the destination, the
     credential's permission scope, and the activation conditions.
  4. **Success.** Withdraw becomes active on Account detail;
     SweepPolicy creation surfaces full act-mode options.
- **Touches:** new sub-flow design + mockups, `holdings/01_account.md`
  withdrawal-credential and outflow sections (reference the
  shipped sub-flow), `concerns/sweep_policies.md` Account-source
  branch (act-mode unlocked when `withdraw_credential_id` is
  non-null), Account detail page (Withdraw button activation
  logic), Treasury-view iteration's SweepPolicy creation flow.
- **Status:** sketched (the design discussion in the 2026-05-16
  brainstorm produced the decision-tree; sharpening needs its own
  session covering Holdings cross-reference UI, Bitstamp manual-
  attestation branch, withdrawal-key tap-to-clear coding rule).
- **Milestone:** pre-shipping (private-ship gate — Rémy needs
  this to actually use auto-sweep on his own Kraken Account).
- **Notes:** Touches the `concerns/sweep_policies.md` open
  arbitration `sweep-validator-extended-rules` indirectly (the
  validator can ground its warnings against this sub-flow's
  output — confirmed whitelisted destination, scoped credential
  presence). The "Bitstamp can't verify whitelists via API"
  asymmetry is real and lives in this sub-flow's design pass;
  the wizard does not touch it.
