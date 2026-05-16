# ADR-0011 — Account credentials use the 2-key model

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during the Account-wizard design pass
  (session 2026-05-16)

## Context

The original `holdings/01_account.md` described a single-credential
model for connecting custodial providers (Account Holdings): one
API key per Account, with a permission level chosen at onboarding
time (Read-only OR Read+Withdrawal). The wizard branched on this
choice; Read+Withdrawal credentials additionally required a
provider-side address whitelist set up before onboarding.

During the Account-wizard design pass, three structural problems
with the single-credential model surfaced:

1. **Conflated lifecycles.** "I want to observe my exchange
   balance" and "I want TK to move funds for me" are different
   user decisions on different timelines. The single-credential
   model forced both into one wizard moment, framing later
   upgrade-to-auto-sweep as "I picked wrong at onboarding."

2. **Wizard branching explosion.** A four-step wizard (provider →
   permission → credentials → whitelist target) had to handle the
   matrix of provider capability × permission pick × user-Holdings
   state × provider-side whitelist state. Multiple drafts foundered
   on edge cases (no-Holdings + RW path; empty provider whitelist;
   provider without whitelist-read API).

3. **Honest minimum-exposure stance was diluted.** TallyKeep's
   product premise is that we take only what we need to keep blast
   radius small if a credential ever leaks. A single credential
   with optional withdraw permission undermines that — it grows
   over time (RO → RW upgrades), and we can't surface "we keep
   each capability scoped to one key" cleanly.

The 2-key model — read-only key at onboarding, separate withdrawal
key configured later — emerged as the cleaner shape and was
locked during the design pass.

## Decision

**Account credentials are split into two independent keys, each
scoped to one capability:**

1. **Read-only key (mandatory, onboarding).** Created on the
   provider with only the balance-query permission enabled
   (e.g., `Query funds` on Kraken). Stored encrypted on TallyKeep.
   Used for: balance polling, withdrawal-history reconciliation,
   read-only display of non-BTC balances. Cannot move funds.

2. **Withdrawal key (optional, configured separately later).**
   Created on the provider with only the withdraw permission
   enabled (e.g., `Withdraw funds` on Kraken, plus the
   provider-required balance-query scope where applicable).
   Stored encrypted on TallyKeep. Used for: SweepPolicy execution
   and manual "Sweep now" from the Account detail page. Configured
   from the Account detail page's Withdraw affordance, not from
   the Add Account wizard.

**The Add Account wizard ships as a 3-step read-only-only flow:**
provider pick + credentials (combined on Step 1) → parseback
recap → success. The withdrawal-enabling sub-flow is its own
design pass, captured in `future_iterations.md` and reachable
from the Account detail page.

**Per-provider capability matrix.** Each registered
`CustodialProviderAdapter` declares its capabilities:
`supports_withdrawal_keys: bool` (does the provider's API expose
withdraw operations at all?) and `whitelist_read_api: bool` (can
TallyKeep fetch the user's provider-side whitelist
programmatically?). The wizard reads these to gate UI affordances
honestly: the Step 3 "Set up auto-sweep" suggestion card is
rendered iff `supports_withdrawal_keys=true`. Providers without
withdrawal-API support land an Account that is observation-only,
no surprise gating later.

## Reasoning

### Why two keys, not one

1. **Defense in depth.** Two keys with different permissions
   means compromise of one key doesn't grant the other's
   capability. The read-only key can be long-lived and used for
   constant polling; the withdrawal key can be created
   short-lived, rotated aggressively, or revoked independently
   ("going on vacation, no sweeps for two weeks"). Same physical
   compromise (TK passphrase brute-forced, host owned) still gets
   both keys — the 2-key model does not solve full-host
   compromise. But for the partial-compromise threat surface
   (provider-side anomaly response disabling one key, TK bugs
   leaking credential info in logs, user-error scope reduction),
   it cleanly limits blast radius.

2. **Lifecycle clarity.** The observation decision is "I have a
   Kraken account I want TK to see." The withdrawal decision is
   "I want TK to act on my behalf at Kraken." These are different
   conversations with the user, often months apart. Splitting
   them treats withdrawal as a deliberate later capability, not a
   permission you wish you'd toggled differently at onboarding.

3. **Industry alignment.** Every major exchange in the target list
   (Kraken, Bitstamp, Coinbase, ccxt-supported venues) supports
   multiple API keys per account with independent permission
   scopes. It's the recommended hygiene practice for traders and
   monitoring tools. The 2-key model maps to existing user
   knowledge.

4. **Wizard simplification.** The Account wizard collapses to a
   uniform 3-step read-only-only flow regardless of provider —
   parity with Purse / Strongbox / Vault wizards. The branching
   matrix of the single-credential design (permission × Holdings
   × whitelist × provider-capability) disappears from the
   onboarding surface; the surface that remains for the
   withdrawal sub-flow is bounded to "Holdings cross-reference +
   destination picker + withdrawal-key paste".

5. **Brand-coherent minimum-exposure.** TallyKeep's banking-
   ergonomic premise is that the user gets safer defaults than
   crypto-native UX, not riskier ones. Onboarding-with-read-only
   means the worst case at the wizard's close is observation, not
   credential leak with withdrawal authority. That's the
   honest default for the type.

### Why not single-credential with safer-default at onboarding

A "single credential, defaults to read-only, upgrade in place
later" alternative was considered briefly. Rejected because:

- **Upgrade-in-place breaks key isolation.** The same persisted
  credential entry would change capability over time, which means
  log-leak / backup-snapshot recovery scenarios surface differing
  capability sets depending on the snapshot's age. A clean two-
  rows model makes the capability set time-invariant per row.

- **Replacing a credential to upgrade still imposes one-key
  thinking on the user.** "Delete and recreate to add withdraw"
  is the same friction as "create a second key for withdraw"
  with no defense-in-depth benefit.

- **Provider-side rotation lifecycles differ between capabilities.**
  Read-only keys can be long-lived; withdraw keys benefit from
  shorter lifetimes. A single credential collapses these.

### Why capability matrix per provider, not per Account

The matrix lives in the `CustodialProviderAdapter` registration
because the capability is a property of the provider, not of the
user's account at the provider. Kraken supports withdrawal keys
for all users; Bitstamp supports them but doesn't expose the
whitelist via API for any user. The wizard reads the adapter's
declared capabilities at runtime and gates UI affordances
accordingly (absence-of-affordance for unsupported capabilities,
honest gates for partial support).

## Consequences

- **`holdings/01_account.md` is updated**: the API permissions
  section, the Add-Holding flow section, and the withdrawal
  outflow section all reflect the 2-key model. The single-
  credential vocabulary (Read-only vs Read+Withdrawal) is
  retired; in its place, the doc describes an Account's
  credential state as `read_credential_id` (always present) and
  `withdraw_credential_id` (nullable; populated by the
  withdrawal sub-flow). Bitstamp is dropped from the v1
  supported list and moved to `future_iterations.md` "Additional
  CustodialProvider adapters" — same iteration that covers
  Lemon / Buenbit / Belo / Coinbase / Swissquote.

- **`UI/mobile.md` gains an Add Account wizard section** with
  the 3-step shape, references to the four validated mockups,
  and the reconcilability gauntlet answers for the flow.

- **The Add Account wizard is the only Holding wizard whose
  scope is intentionally narrower than the type's full
  capability.** Withdraw lives outside the wizard surface; the
  Account detail page's greyed-out Withdraw button is the
  canonical discovery surface for the withdrawal sub-flow. This
  is honest because withdrawal genuinely is a separate decision
  on a separate timeline, not a feature gated for engineering
  convenience.

- **The withdrawal sub-flow is its own design pass.** Captured
  in `future_iterations.md` "Account withdrawal-key sub-flow".
  Designs the Holdings cross-reference + paste-external-address
  + withdrawal-key credential paste, plus the
  whitelist-API-supported vs whitelist-API-missing branches.
  Required before any auto-sweep work on Account Holdings.

- **The SweepPolicy iteration's Account-source branch depends on
  the withdrawal sub-flow shipping.** Auto-sweep policies on
  Account Holdings without a withdraw credential fall back to
  watch-and-advise mode (per existing spec). Once the
  withdrawal sub-flow ships, the act-mode branch becomes
  reachable.

- **The capability-matrix endpoint is a backend deliverable in
  the Account-wizard iteration.** Frontend reads provider
  capabilities at wizard time (drives Step 3's
  suggestion-card visibility) and at Account detail time
  (drives the Withdraw button's affordance). The matrix is
  static per adapter, declared at adapter registration.

- **The Bitstamp deferral is scope-tightening, not
  architectural.** Bitstamp's adapter implementation in the
  backend is unchanged at the contract level; the v1 wizard
  simply doesn't surface Bitstamp in its provider dropdown
  until the "Additional CustodialProvider adapters" iteration
  promotes it. The canonical-spec target state still includes
  Bitstamp as a supported provider.

**What this ADR does not decide.** The exact UX of the
withdrawal-enabling sub-flow (Holdings picker shape, paste
fallback, ack-checkbox semantics for whitelist-API-missing
providers) and the auto-sweep policy creation UX are design
surface for the Account-withdrawal-sub-flow and SweepPolicy
iterations respectively.

## Affected files

- `holdings/01_account.md` — credential model section rewritten;
  Add-Holding flow rewritten; "Supported providers" tightened to
  Kraken at v1; capability-matrix concept introduced; outflow
  section reframed
- `UI/mobile.md` — gains `## Add Holding — Account wizard`
  section
- `UI/mockups/mobile_add_holding_account_01_connect.html` —
  validated (design pass close, Rémy greenlight 2026-05-16)
- `UI/mockups/mobile_add_holding_account_01_connect_error_overage.html` —
  validated (same)
- `UI/mockups/mobile_add_holding_account_02_parseback.html` —
  validated (same)
- `UI/mockups/mobile_add_holding_account_03_success.html` —
  validated (same)
- `UI/mockups/index.html` — mockup-index array updated
- `next_iteration.md` — sharpened block "Add Holding · Account
  wizard"
- `future_iterations.md` — entries added for the withdrawal
  sub-flow and the Bitstamp deferral; existing
  "Additional CustodialProvider adapters" updated to reflect
  Kraken-only at v1
