# ADR-0013 — Custodial ledger is mirrored, not cached

**Date:** 2026-05

**Status:** Accepted

**Decided by:** Rémy

**Authored by:** Claude during the Account-detail-page brainstorm, May 2026

**Migrated from:** `future_iterations.md` "Custodial ledger mirroring
posture and TK-initiated event linkage" (captured 2026-05-17; resolved
2026-05-18).

## Context

Iteration A shipped `custodial_ledger_entry` — a table that persists,
on disk, every ledger row TallyKeep observes at each connected
CustodialProvider (deposits, withdrawals, trades, fees, transfers).
The table-shape itself was uncontroversial; what it implies for
posture was not. Two postures fit the same table:

- **Mirror.** The table is a persistent copy of the provider's ledger
  feed. TallyKeep upserts on each observation cycle; the table
  persists across provider unreachability, key revocation, and
  account-detail-page reloads without an active connection. The
  Operations tab on the Account detail page renders from this table.
- **Cache.** The table is short-TTL pass-through, refreshed on
  Operations-tab access. No source-of-truth claim; the provider's
  ledger endpoint is the only source of truth and the table is
  scaffolding for performance.

The Account-detail-page iteration ships against this table —
snapshot endpoint returns the most recent N rows, SSE
(`treasury.custodial.ledger_entry_added`) drives realtime inserts.
The two postures look identical on a healthy connection. They
diverge sharply when the provider connection is broken, when the
user revokes the API key, or when the provider mutates an entry
post-hoc (Kraken: pending → success → cancelled, fee correction).

This decision settles the posture before the page goes live and
locks the schema and reconciliation discipline that follow from it.

## Decision

**`custodial_ledger_entry` is a mirror.** The table is the canonical
on-disk record of what TallyKeep has observed at each provider's
ledger endpoint. Polling upserts by `(custodial_provider_id,
provider_entry_id)`; the table persists across degraded states and
serves as the read source for the Operations tab regardless of
current provider reachability.

Three consequences follow and are locked in lockstep with this ADR:

1. **Kind enum is narrow + adapter-owned.** The TK domain enum is
   `{trade, deposit, withdrawal, transfer, fee, other}` —
   stable across providers, models only what TK acts on
   structurally. Each `CustodialProviderAdapter` carries a
   per-provider mapping table from the provider's kinds to the TK
   kinds; anything not in the explicit map normalizes to `other`.
   The full provider record always goes into `raw_payload` (JSONB),
   so unknown kinds are still observable and never break the
   pipeline.

2. **Provider-side mutations are tracked.** Kraken (and others) can
   mutate ledger rows after first emission. The mirror reconciles
   by `provider_entry_id`: new rows insert and emit
   `treasury.custodial.ledger_entry_added`; existing rows that
   changed update in place and emit a new
   `treasury.custodial.ledger_entry_updated` event; missing rows
   from a paginated past are not deleted (providers don't delete
   historical entries — missing means out of the polled window).

3. **TK-initiated event linkage lives on the table.** When a
   SweepPolicy fires, the resulting provider ledger entry is
   linkable to the originating `sweep_execution`, the counterparty
   TK Holding, and the chain-side `ledger_entry` produced by the
   on-chain leg. Three nullable FKs on `custodial_ledger_entry`
   carry the linkage; a reconciler subscriber populates them with
   conservative matching criteria (provider + direction + amount
   ± fee + time window + address-match for inflow). Unmatched
   entries stay pure observation — the framing is "TK did this"
   vs. "the user did this on the provider's site," never a
   judgment.

## Consequences

**What this gives us.** The Operations tab renders honestly under
degraded states: a user who revoked their API key for a quiet week,
or whose provider is mid-outage, or who lives in a market with
intermittent exchange access, still sees what TallyKeep knew last.
The banking-ergonomics premise from `00_README.md` — that a normal
person can read their balances and history without ceremony —
survives provider failure. This is the load-bearing reason and the
only one that would justify the schema and reconciliation cost.

**What this costs us.** Reconciliation discipline:

- Adapter-side normalization, with a per-provider kind-mapping
  table and explicit handling of multi-row events (Kraken trades
  emit one ledger row per asset leg, paired by `refid`; v1 stores
  the BTC leg only and stashes the fiat leg in `raw_payload`).
- A reconciler subscriber that watches incoming entries and
  attempts the three-way linkage. Conservative criteria — false
  positives ("we said TK did this; user did it on the provider's
  site") are a trust break; false negatives just leave the row
  unlinked, which is honest.
- A new `treasury.custodial.ledger_entry_updated` SSE event for
  provider-side mutations. Frontends that don't subscribe degrade
  silently (the row is stale until next page load).

**What this closes.** Two open branches from the captured
brainstorm: the mirror-vs-cache posture itself, and the TK-initiated
event linkage shape. Both are resolved.

**What this leaves open.** The *visual* TK-vs-external distinction
on the Operations tab is deferred to the iteration after the
Account-detail-page ships. The page-iteration's scope-out names
this explicitly. The linkage data exists from day one; the UI
surface lights up later, no migration needed.

**What this does not address.** Account removal cascade (whether
`custodial_ledger_entry` rows + linked `sweep_execution` rows
should hard-delete or soft-null when an Account is removed) is
left to a future Holding-deletion iteration. The page-iteration's
current cascade-delete behavior stands until that iteration
revisits it.

## Affected files

- `holdings/01_account.md` — §Observation cycles expanded with
  mirror posture, kind enum, provider_entry_id, linkage paragraph,
  and the new `ledger_entry_updated` event.
- `02_domain_model.md` — new `CustodialLedgerEntry` entity defined.
- `03_data_model.md` — new `custodial_ledger_entry` table schema.
- `concerns/sweep_policies.md` — §Reconciliation extended to
  include custodial-side matching.
- `next_iteration.md` — Account-detail iteration prepended with
  the backend-only ledger-mirror block (Task 0).
- `future_iterations.md` — the captured "Custodial ledger
  mirroring posture and TK-initiated event linkage" entry removed
  (resolved by this ADR and the active iteration).
