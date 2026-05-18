# Deposit Send-to-Account flow

- **Captured:** 2026-05-17 (Account-detail-page brainstorm, after
  Rémy reframed deposit as the decumulation pathway — sending BTC
  from a TK Holding *to* the custodial Account, so the user can
  sell on the provider's site and exit to fiat).
- **Motivation:** Decumulation symmetry. The accumulation flow
  (provider → TK Holding via Withdraw / SweepPolicy) is locked.
  The reverse — TK Holding → provider for selling — currently has
  no in-app path. The user has to copy their Kraken deposit
  address manually from kraken.com, paste it into a Send flow
  from a separate Holding, and remember to use it. The product
  narrative reads cleaner with TK as the **outflow / inflow
  controller** enforcing minimum-exposure trading in both
  directions: pass-through liquidity, not storage — BTC sits at
  the venue only for the trade window the user actually needs.
- **Sketch:** Reached from the Account detail page's **Deposit**
  action button. Likely 3 steps:
  1. **Source picker.** List the user's other TK Holdings
     (Strongbox / Vault / Purse) with their available balances.
     Tap to pick. (Single source per deposit; multi-source split
     is out of scope.)
  2. **Amount + fee.** Amount field with max-balance affordance
     (minus an unspent-buffer per the source Holding's policy),
     fee selection per the standard Send pattern (fast / normal /
     economy + custom). Show the pinned destination address read-
     only ("Sending to your Kraken deposit address — set in
     Account → Settings").
  3. **Review + sign.** Standard PSBT review for the source
     Holding type. Strongbox / Vault → export PSBT for signing
     elsewhere. Purse → in-app sign on the device that holds the
     seed. Broadcast on user confirmation; activity row lands on
     both the source Holding's detail page and the destination
     Account's Operations tab (as a `deposit` ledger entry once
     Kraken polls it).
- **Pinned destination address pattern:** the user pastes their
  Kraken BTC deposit address into TK once, stored in the Account
  row as `deposit_address` (nullable; configurable from the
  Account Settings tab's "Deposit address" section). TK does not
  fetch the address via API — that would require
  `Funds: Deposit` scope on Kraken, which also unlocks
  `DepositCancel` (fund-state-changing), breaking the
  observation-credential's "no fund movement" property per
  ADR-0012. The user-pasted pattern is the mirror image of the
  withdrawal whitelist — TK-side pinned destination instead of
  provider-side pinned destination. No new credential scope.
- **SweepPolicy extension for scheduled decumulation:** the
  SweepPolicy model is currently directional (Account →
  Holding). The deposit flow extends it to bi-directional
  (Holding → Account also supported). Scheduled decumulation
  becomes a SweepPolicy with `source_holding_type ≠ account`,
  `destination_holding_type = account`. Fires on schedule or
  threshold, composes a PSBT on the source side, broadcasts.
  Belongs in `concerns/sweep_policies.md` scope when this
  iteration is sharpened.
- **Touches:** Account detail page (Deposit button + Settings tab
  "Deposit address" affordance — both forward-reference this
  sub-flow until it ships), `concerns/sweep_policies.md` (bi-
  directional SweepPolicy model), source-Holding Send-flow code
  paths (PSBT compose / sign / broadcast already exist for
  Strongbox + Vault + Purse — this iteration may or may not
  reuse them depending on how deeply the new flow integrates),
  domain model (`Account.deposit_address` column).
- **Status:** sketched (the 2026-05-17 brainstorm produced the
  shape and the pinned-address rationale; sharpening needs its
  own design pass covering: the source picker's filtering rules
  for available balance, the activity-row reconciliation on
  arrival, the SweepPolicy bi-directional UI, and the empty-
  state when no source Holding has a sufficient balance).
- **Milestone:** post-shipping (good post-public-ship feature
  enhancement — proves the bi-directional pass-through narrative
  and unlocks scheduled decumulation as a differentiator).
  Pre-shipping is conceivable if Rémy's own daily-use feedback
  flags it as a friction point during the personal-use phase.
- **Notes:** Until this ships, the Account detail page's Deposit
  button routes to a coming-soon stub (mirror of
  `mobile_add_holding_coming_soon.html`). The Settings tab's
  "Deposit address" section likewise — capture the field but
  forward-reference the sub-flow that consumes it. Honest
  absence-of-affordance for the actual deposit action.
