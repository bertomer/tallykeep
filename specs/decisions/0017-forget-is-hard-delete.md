# ADR-0017 — Forget is hard delete; archive mechanism retires

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during the Forget-vs-archive brainstorm
  session (2026-05-20)

## Context

The Forget button on Holding detail pages (Account, Purse,
Strongbox, Vault) currently maps to `POST /api/v1/holdings/{id}/archive`
for non-Account types, which flips an `is_archived` boolean and
leaves every chain-side row in place — descriptor, addresses,
UTXOs, ledger entries, link rows. The UI copy on every Forget
mockup tells a different story: *"TallyKeep forgets the descriptor
and stops scanning the chain"*, *"Forget destroys the chain-side
ledger entries the user's category labels attach to"*. The mockup
design notes go further: *"Backend Forget call deletes the
descriptor row and related chain-side state."*

So the frontend has been promising privacy-grade Forget while the
backend has been delivering a soft-archive. No ADR justified the
gap; no `pre-implementation.md` entry flagged it; the soft-archive
choice was made silently at code time, almost certainly because
the data-model rule "no hard deletes for entities referenced by
historical records" plus `ON DELETE RESTRICT` on every chain-side
FK made a real cascade look like more work than the iteration
could absorb. That's a §2 silent role-mix failure mode (per
PROCESS.md) — code shipped under copy it does not satisfy.

Two paths to reconcile: bend the copy to match the code, or bend
the code to match the copy. The copy is the user's privacy
contract; it's what they're told they get when they tap Forget.
The data-model "no hard deletes" rule was written before the
Forget conversation, to protect aggregate history (P&L, tax
exports, realised gains). It was never reconciled against the
privacy intent. The privacy contract wins.

A second question the brainstorm raised — whether to keep an
Archive feature alongside Forget as a "temporary hide from UI"
ergonomic for cold storage clutter — was considered and dropped.
No user has asked for it. The `is_archived` column existed only
because the soft-delete rule put it there. Retrofitting a product
feature onto a column that exists for the wrong reason is the
founder-bias pattern. If real users surface a hide-without-delete
need post-public-ship, the cheaper alternatives
(`display_order` reordering, per-Holding "include in headline
total" toggle) come up first; only after those fail does a real
Archived state earn its way in. Captured for re-evaluation in
`backlog/anonymous-public-feedback-channel.md` if and when public
feedback raises it.

## Decision

1. **Forget = hard delete with cascade.** On Forget of a Holding,
   in a single transaction:
   - Delete `descriptor`, `address`, `utxo`, `payment_request`,
     `invoice` rows owned by the Holding.
   - Delete `ledger_entry_holding_link` rows where
     `holding_id` = the Forgotten Holding. For each affected
     `ledger_entry`, if its remaining link count is zero, delete
     the `ledger_entry`. If at least one other Holding still
     links to it (the internal-transfer case where two TK
     Holdings touched the same on-chain movement), the
     `ledger_entry` survives — only the Forgotten Holding's
     claim on it disappears.
   - `onchain_transaction` rows are **never** deleted by Forget.
     They are chain truth keyed by txid, shared across every
     Holding that touched the tx; deleting them on one Holding's
     Forget would orphan other Holdings' history.
   - For Accounts: delete `custodial_provider`, all
     `custodial_ledger_entry` rows for that Account, and clear
     stored API-credential bytes from secret storage. This is
     what `DELETE /api/v1/holdings/{holding_id}` already does
     for Accounts.
   - For non-Accounts: NULL out any
     `custodial_ledger_entry.linked_counterparty_holding_id`
     that points at the Forgotten Holding (an Account on the
     other side of a past sweep keeps its mirror row; only the
     dangling back-pointer to the now-deleted Holding goes).
   - For on-device Purses: client-side
     `NativeBridge.secureStorage.delete(holding_id)` runs before
     the backend call. Failure surfaces an inline error and the
     backend call does not proceed (existing Purse-detail Forget
     contract).
   - Capacitor sensitive-screen state for the Holding clears as
     a consequence of the holding-id key disappearing.

2. **Archive mechanism retires entirely.** The
   `holding.is_archived` column drops. The two partial indexes
   (`idx_holding_type_active`, `idx_holding_purpose`) become
   plain indexes without the `WHERE is_archived = FALSE` clause.
   The `include_archived` query parameter on
   `GET /api/v1/holdings` and `GET /api/v1/holdings/summary/global`
   drops. The `is_archived` field on `HoldingResponse` drops.

3. **API surface unifies on DELETE.** `DELETE /api/v1/holdings/{holding_id}`
   becomes the single Forget endpoint, accepting all four Holding
   types (Account, Purse, Strongbox, Vault). The 422-on-non-Account
   guard goes away. `POST /api/v1/holdings/{holding_id}/archive`
   retires. The frontend Forget button switches to DELETE.

4. **Foreign-key posture changes.**
   - `custodial_ledger_entry.linked_counterparty_holding_id`:
     `ON DELETE RESTRICT` → `ON DELETE SET NULL` (matches the
     service-layer behavior of the cascade).
   - `ledger_entry_holding_link.holding_id`: stays `ON DELETE RESTRICT`
     at the FK level. The service layer deletes link rows
     explicitly in the cascade transaction before the Holding
     itself, preserving the explicit-deletion-not-cascade
     pattern the file already uses for `custodial_ledger_entry`
     on Account removal. Documented in `03_data_model.md`.
   - All other FKs from `holding(id)` (`descriptor`,
     `payment_request`, `invoice`, `custodial_provider`,
     `custodial_ledger_entry.holding_id`): stay `ON DELETE RESTRICT`;
     the service-layer cascade deletes children first.

5. **Data-model invariant changes.** `03_data_model.md`'s
   "Soft deletes via `is_archived` flags. No hard deletes for
   entities that are referenced by historical records." rule is
   replaced by: **Holdings hard-delete on Forget via a
   service-layer cascade; chain-truth tables
   (`onchain_transaction`) and aggregate-history tables
   (`ledger_entry` when still linked by surviving Holdings) are
   preserved.** `02_domain_model.md`'s "Holdings are soft-deleted
   (archived). No hard delete, to preserve LedgerEntry integrity."
   rule is replaced by the same.

6. **Forget UI copy is now backend-truthful.** Every existing
   Forget mockup body copy aligns to the new behavior with no
   edits required. The Strongbox mockup design note saying
   *"Backend Forget call deletes the descriptor row and related
   chain-side state"* becomes accurate prose, no longer
   aspirational.

## Consequences

**Implementation work** — captured in the active iteration block of `next_iteration.md` (promoted from a backlog file 2026-05-20 per ADR-0014). Scope: backend
service-layer cascade for non-Account types; FK posture changes
in a schema migration; data migration handling existing
`is_archived=TRUE` rows (decision deferred to the iteration spec —
default leaning is to forget them at migration time, matching the
new semantics); frontend Forget button switches from POST /archive
to DELETE; openapi regeneration drops `/archive`, the
`include_archived` query param, and the `is_archived` response
field.

**Aggregate-history loss is the explicit trade.** Total realised
P&L, tax exports, and any other cross-Holding aggregation that
relied on Forgotten Holdings' historical contribution loses that
contribution. This is the price of the privacy contract. Users
who want pre-Forget exports should export *before* tapping
Forget. The Forget bottom-sheet copy is already structurally
honest about categorization loss; it now also implies aggregate
loss, which the implementation iteration may or may not surface
explicitly in the modal body (UX call, not a domain decision).

**Account behavior unchanged in spirit, formalised in writing.**
`DELETE /api/v1/holdings/{holding_id}` for Accounts already
hard-deletes with secret cleanup. The footnote in
`03_data_model.md` that called this "a deliberate divergence
from the file's default ON DELETE RESTRICT convention" gets
rewritten — it is no longer a divergence, it is the standard
pattern, generalised across all four Holding types.

**The deferred "Holding-deletion iteration" referenced by the
footnote** now lives in the active iteration block of `next_iteration.md` (promoted from a backlog file 2026-05-20 per ADR-0014). The reference in
`03_data_model.md` updates accordingly.

**Archive does not get a second life as a hide-from-UI feature.**
If real public users surface that need, revisit via
`backlog/anonymous-public-feedback-channel.md` (the channel
through which such signal could arrive), and prefer
`display_order` reordering or a per-Holding "include in headline
total" toggle before reintroducing a state machine.

**The `purse-upgrade-path` arbitration item** in
`pre-implementation.md` includes "creates a new Purse and the
old one is archived" as one option. With Archive retired,
that option becomes "the old one is Forgotten." Substantive
arbitration unchanged (in-place mode mutation vs new-Purse +
old-Purse-Forgotten); only the verb updates. The
`pre-implementation.md` entry will be edited in the same change
that lands this ADR.

**`DELETE /api/v1/descriptors/{descriptor_id}`** becomes
functional once the service-layer cascade exists (today it
refuses because addresses reference the descriptor). Whether to
keep it as a public surface or remove it as redundant with
Holding-level Forget is an iteration-time call.

## Affected files

- `decisions/README.md` — index entry added
- `02_domain_model.md` — `is_archived` field removed from
  Holding; soft-delete invariant replaced; CustodialLedgerEntry
  footnote rewritten
- `03_data_model.md` — Conventions soft-delete rule replaced;
  `is_archived` column dropped from `holding`; partial-index
  filters dropped; CustodialLedgerEntry footnote rewritten;
  FK posture documented
- `concerns/observation.md` — "non-archived Holdings" wording
  dropped (Fortune view simply sums across Holdings)
- `holdings/02_purse.md` — purse-upgrade-path forward-reference
  vocabulary updated ("archived" → "Forgotten")
- `pre-implementation.md` — `purse-upgrade-path` entry verb
  lockstep update
- `next_iteration.md` — active iteration block carries the coding-agent iteration scope (promoted from a backlog file on 2026-05-20 per ADR-0014)
- `backlog/anonymous-public-feedback-channel.md` — new file,
  captures the related public-feedback-channel question Rémy
  raised in the same brainstorm

`api/openapi.yaml` is **not** edited by hand — regenerates from
the running backend at the implementation iteration's closeout
per ADR-0004 + PROCESS.md §4.2. Drift between the current
openapi (which still has `/archive` and `include_archived`) and
this ADR's target is real but transient; it resolves at
implementation closeout.

Mockup files are **not** edited — their copy and design notes
already match the new behavior.
