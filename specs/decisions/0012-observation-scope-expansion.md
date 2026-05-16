# ADR-0012 — Observation credential carries balance + ledger scopes

- **Date:** 2026-05
- **Status:** Accepted; supersedes the permission-list section of ADR-0011 (the rest of 0011 stands)
- **Decided by:** Rémy
- **Authored by:** Claude, during the Account-detail-page design pass
  (session 2026-05-17)

## Context

The Account-detail-page design pass surfaced a contradiction in the
shipped Account specification:

- `holdings/01_account.md` §"What an Account does" promises that
  Account polling fetches *"current BTC balance, recent withdrawal
  history, recent deposit history, other-asset balances."*
- ADR-0011 locks the read-only key's permission scope to *"only the
  balance-query permission (Query funds on Kraken)."* The Add Account
  wizard's Step 1 hard-rejects any key that carries anything beyond
  Query funds; the shipped wizard rejects keys with even one extra
  flag.

These two statements cannot both be true. Per Kraken's current API
documentation:

- `Funds: Query` (the locked v1 scope) grants `Balance` and
  `TradeBalance` only.
- `Data: Query ledger entries` is required for `Ledgers` /
  `QueryLedgers` — the comprehensive ledger feed (deposits,
  withdrawals, trades, fees, transfers, all unified).
- `WithdrawStatus` requires either `Funds: Withdraw` or
  `Data: Query ledger entries`.
- `DepositStatus` requires `Funds: Deposit`.

With the locked Query-funds-only scope, the wizard ships a credential
that can fetch the balance but **cannot fetch any history**. The
spec's history claim is unreachable. The shipped Account would
therefore display a balance and nothing else — no activity feed, no
deposit/withdrawal history, no per-row reconciliation.

The drift was caught during the Account-detail-page brainstorm when
the Operations-tab activity-feed shape forced the scope question.
Without the amendment, the page either ships dishonestly (showing a
greyed "Transaction history needs ledger access" affordance that the
user has to figure out how to unlock — the dead-capability anti-
pattern) or ships without history at all (information-thin, defeats
the page's primary purpose).

The pattern generalizes beyond Kraken. Every major custodial provider
in the target list exposes ledger query under a separate read scope
from balance query: Bitstamp splits `Account balance` from
`User transactions`; Binance splits balance from `USER_DATA` snapshot
endpoints; Coinbase Advanced Trade collapses both under a single
`view` scope. The ccxt unified `fetchLedger` is implemented for
Kraken, Bitstamp, Coinbase, Bybit, KuCoin, OKX, Bitget. The
architectural shape (observation credential = two-or-more read-only
provider permissions composing into one TK capability) holds across
the supported-provider roadmap.

## Decision

**The read-only credential's locked scope expands from a single
provider permission to a defined set of observation-only provider
permissions, all of which must be read-only with no fund-movement
power.**

For Kraken (v1):

- Locked scope: `Funds: Query` **and** `Data: Query ledger entries`.
- The wizard's Step 1 helper banner instructs enabling both
  permissions and only those two.
- The wizard's Step 1 overage-rejection logic accepts a key with
  exactly those two permissions and rejects keys carrying any
  additional permission (Trade, Margin, Futures, Earn / Staking,
  Withdraw funds, Deposit funds, anything else).
- The wizard rejects keys missing either of the two required
  permissions with the same locked-copy pattern, surfacing which
  permission is missing.

For future providers, each `CustodialProviderAdapter` declares its
required observation-permission set at registration. The wizard's
helper banner and overage-rejection logic are per-provider. Coinbase
ships with a single `view` permission in its set; Bitstamp ships with
`Account balance` and `User transactions`; the shape is uniform but
the named flags differ.

**The principle locked in ADR-0011 — "one TK capability per
credential, with blast radius scoped to that capability" — is
preserved.** "Observation" is one TK capability. It requires more
than one Kraken-side permission flag, but those flags compose into a
single capability with a single blast radius (information disclosure
of balance and history; no funds can move under any composition of
read scopes).

ADR-0011's other elements stand unchanged:

- The 2-key model (read-only + withdrawal as independent credentials).
- The wizard's 3-step shape and read-only-only scope at onboarding.
- The withdrawal credential's separate post-onboarding configuration
  via the Account detail page's Withdraw affordance.
- The capability matrix per provider.
- The Bitstamp deferral to the "Additional CustodialProvider
  adapters" iteration.

## Reasoning

### Why expand the observation scope rather than ship without history

The Operations tab's activity feed is the primary surface of the
Account detail page. Banking-app convention puts the transactions
list directly under the balance; users expect to see what happened.
Shipping an Account page with balance only would defeat banking-
ergonomic framing — the page would look stale and information-thin
compared to a normal bank account view.

Surfacing a greyed "Transaction history needs ledger access"
affordance with instructions for the user to reconfigure their
Kraken key is the dead-capability anti-pattern. The page would
pretend a feature exists that the user has to figure out how to
unlock through provider-side configuration. That is exactly what
the absence-of-affordance rule was written against.

### Why two flags on one credential, not two credentials

The defense-in-depth argument for splitting credentials (per
ADR-0011) applies when each credential grants a *different
capability* with a *different blast radius*. Splitting observation
into two credentials (one for balance, one for ledger) does not
satisfy this — both are read-only at the provider, both have the
same blast radius (information disclosure of the user's Kraken
state), and a leak of either grants the same observation surface
TallyKeep already had. There is no defensive benefit to splitting.

There is a real UX cost to splitting: the user creates two keys on
Kraken instead of one, the wizard captures two pairs of credentials,
the per-credential rotation lifecycle multiplies. None of this buys
additional security.

The clean reading of ADR-0011's principle is "one TK capability per
credential, where capability is the user-facing operation." TK has
three user-facing operations: observe / withdraw / deposit.
Observation is one TK capability composed of multiple provider-side
read scopes. That maps to one observation credential.

### Why not extend the scope further (e.g. include Funds: Deposit)

`Funds: Deposit` on Kraken would unlock `DepositMethods` /
`DepositAddresses` (so TK could surface the deposit address inline
on the Account page) but it also unlocks `DepositCancel`, which is
*fund-state-changing on Kraken*. That breaks the "no fund movement"
property of the observation credential. Deposit-address surfacing
is therefore not part of this ADR; the deposit flow's design pass
(captured in `future_iterations.md` "Deposit Send-to-Account flow")
adopts a different pattern — user-pasted pinned deposit address,
no provider-side credential scope on the TK side.

`Funds: Withdraw` is the withdrawal credential's scope and is
captured separately by ADR-0011's 2-key model.

### Why generalize the pattern across providers

The "observation = balance + ledger" composition is uniform across
the target-market provider list. Locking the shape now (per-provider
declared observation-permission set, wizard reads it, overage logic
enforces it) means each future adapter's onboarding work is bounded
to: (a) listing the provider's observation permission flags in the
adapter registration, (b) writing the per-provider helper-banner
copy, (c) ensuring the adapter's `fetchBalance` + `fetchLedger`
calls work against the locked scope. No wizard rework per provider.

## Consequences

- **Backend overage-rejection logic becomes per-provider.** The
  wizard's Step 1 validation no longer hardcodes "Query funds only";
  it reads the provider's declared observation-permission set from
  the adapter registration and rejects any key whose actual
  permissions differ (extra or missing). For Kraken, the accepted
  set is exactly `{Funds: Query, Data: Query ledger entries}`. For
  Coinbase (when its adapter lands), the accepted set is `{view}`.
  Etc.

- **The wizard's Step 1 helper banner copy is updated** to instruct
  enabling both required Kraken permissions. The error variant's
  danger band lists the specific overage permissions (verbatim
  from Kraken's response) and the corrective instruction
  ("Replace these keys on Kraken Pro with ones that have **only**
  `Query funds` and `Query ledger entries` ticked").

- **`holdings/01_account.md` credentials section is updated** to
  describe the read-only credential as "carrying the provider's
  observation permission set" (balance-query + ledger-query for
  Kraken) rather than "the provider's balance-query permission".
  §"What an Account does" no longer drifts from the credential's
  reachable surface — the polling section legitimately fetches
  balance plus ledger entries.

- **The shipped wizard mockups need a copy refresh in place.**
  `mobile_add_holding_account_01_connect.html` and
  `mobile_add_holding_account_01_connect_error_overage.html` carry
  the now-stale "only Query funds" copy in the helper banner and
  the error variant's overage band. Per `UI/mockups/README.md`
  cosmetic-refinement rule, in-place edit + date bump; mockup
  status stays `validated` because the structural shape
  (layout, palette, error-variant flow, tap-to-clear behaviour)
  is unchanged. The other two mockups (`02_parseback`,
  `03_success`) carry no permission references and are
  untouched.

- **The Account-detail-page iteration depends on this ADR shipping
  first.** The Operations tab's activity feed is fed by the
  ledger-query side of the amended scope. Iteration A
  (this ADR + wizard rework + backend ledger-polling
  infrastructure + new SSE topics) ships before iteration B
  (Account detail page).

- **The Bitstamp adapter (when promoted from
  `future_iterations.md`) will declare its observation set as
  `{Account balance, User transactions}`** with no further
  ADR — the per-provider declaration pattern is now the locked
  shape.

- **Withdrawal-credential scope is unchanged.** ADR-0011's
  withdrawal-credential definition stands: Kraken `Withdraw funds`
  plus the balance-query scope where required by the withdraw
  endpoints. This ADR does not touch the withdrawal credential.

- **No security posture change.** Both `Funds: Query` and
  `Data: Query ledger entries` are read-only at Kraken. Neither
  grants fund-movement capability under any composition. The
  combined credential's blast radius if leaked is information
  disclosure of balance and transaction history at the provider —
  the same blast radius a hosted-tier TallyKeep backend has on
  the user's behalf when self-hosting is not in use. No new
  attack surface; no widened blast radius.

**What this ADR does not decide.** The exact UX of the activity
feed on the Account detail page (row format, badge taxonomy,
filter affordances, empty-state copy) is design surface for the
Account-detail-page iteration. The deposit-address pattern and
the deposit-flow design are design surface for the deposit
Send-to-Account flow iteration captured in `future_iterations.md`.

## Affected files

- `holdings/01_account.md` — credentials section reflects the
  expanded observation scope; §"What an Account does" stays
  consistent with what the credential can actually fetch;
  freshness vocabulary cleanup ("polled" / "polling" stays in
  spec architecture descriptions, but user-facing surfaces use
  "updated" / "freshness indicator" — separate cleanup pass)
- `UI/mobile.md` Add-Holding Account-wizard section — permission
  references updated to reflect the two-permission observation set
- `UI/mockups/mobile_add_holding_account_01_connect.html` — helper
  banner copy + design-notes comment updated in-place; date
  bumped; status stays `validated`
- `UI/mockups/mobile_add_holding_account_01_connect_error_overage.html` —
  helper banner + error-variant danger band copy + design-notes
  comment updated in-place; date bumped; status stays `validated`
- `UI/mockups/mobile_add_holding_account_02_parseback.html` — no
  changes (no permission references in the file)
- `UI/mockups/mobile_add_holding_account_03_success.html` — no
  changes (no permission references in the file)
- `decisions/0011-account-two-key-model.md` — status updated to
  "Accepted; permission-list section superseded by ADR-0012"
- `decisions/README.md` — ADR index gains the 0012 entry; 0011
  status note updated
- `next_iteration.md` — sharpened iteration A block: backend
  overage logic per-provider, wizard implementation copy update,
  ledger-polling infrastructure, new SSE topics, integration
  tests, OpenAPI regeneration.
