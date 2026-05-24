# Observation — chain monitoring, UTXO tracking, security analysis

How TallyKeep watches the chain on behalf of non-Account Holdings
(Purse, Strongbox, Vault). Single-source for the mechanics;
per-Holding specializations live in `holdings/<type>.md`.

**Scope of this concern.** Backend-side, watch-only by
construction. The observation layer **never signs**, regardless
of Holding type or client capability (per ADR-0009 key custody
zone for the backend). PSBT construction is `concerns/outflow.md`;
sweep policies are `concerns/sweep_policies.md`.

## Responsibilities

1. Ingest Descriptors, derive addresses, track balances per
   Descriptor and per Holding.
2. Continuously scan the blockchain via `bitcoind` JSON-RPC and
   ZeroMQ for activity on watched addresses.
3. Surface incoming and outgoing transactions for user
   categorization.
4. Compute and display UTXO hygiene flags.
5. Produce per-Holding and global "fortune view" summaries.
6. Compute observable security per Holding and surface
   discrepancies against declared security.

## Descriptor import

Accepts BIP 380 output descriptors or legacy xpub/ypub/zpub
(converted to canonical form via BDK).

The decision of *which Holding type a pasted descriptor belongs
to* — single-key Purse vs Strongbox vs multisig/timelock Vault
vs unsupported — lives in `concerns/classification.md`. This
section covers what the observation layer does *after* a
descriptor has been classified and a Holding has been created:
address derivation, gap-limit handling, chain scanning, UTXO
persistence.

Per-type accept-set detail (the full Vault accept set under
ADR-0010 β, Strongbox signing-metadata semantics, Purse
script-type set) lives in `holdings/<type>.md` and is summarised
in `classification.md`'s routing table.

## Gap limit

Default 20, per BIP 44. Configurable per Descriptor. After
scanning, if the last `gap_limit` consecutive addresses on a
branch are all unused, scanning stops for that branch. Past-gap
usage forces the user to raise the gap limit and rescan.

## Blockchain scanning

Two modes work together.

**Initial scan** (one-time, on Descriptor import): BDK derives
addresses to `gap_limit`; the backend uses `scantxoutset` for
current UTXOs (fast — no full chain rescan) and
`getrawtransaction` / paged `getblock` for history. Discovered
UTXOs and their transactions persist immediately.

**Incremental scan** (continuous): the ChainListener subscribes
to bitcoind ZeroMQ for new blocks and new mempool transactions.
On any notification touching a watched Address, the listener
persists the UTXO and transaction records and emits the domain
events the UI subscribes to (event taxonomy in
`01_architecture.md` §"Event taxonomy"; specific topic names
live in code).

**Configuration requirement:** the user's bitcoind must have ZMQ
enabled. The README documents the required `bitcoin.conf` lines:

```
zmqpubrawblock=tcp://127.0.0.1:28332
zmqpubrawtx=tcp://127.0.0.1:28333
zmqpubhashblock=tcp://127.0.0.1:28334
```

Onboarding verifies ZMQ is reachable before the first Descriptor
import. If unreachable, onboarding shows the exact lines to add.

## UTXO persistence

Every detected UTXO is persisted. When spent, it is marked
`is_spent=TRUE` with `spent_in_txid`. Rows are never deleted —
historical record.

## LedgerEntry classification

When a transaction affects watched addresses, the scanner creates
one `ledger_entry` linked to the affected Holdings.

- `direction`:
  - `INCOMING` if net effect on user's Holdings is positive
  - `OUTGOING` if net effect is negative
  - `INTERNAL` if both inputs and outputs are entirely
    user-owned across our Holdings
- `net_amount_sats`: sum of outputs to user addresses minus sum
  of inputs from user addresses
- `fee_sats`: sum of inputs minus sum of outputs
- `timestamp`: block time, or first-seen for mempool entries

### Mixed-input transactions (target — pending implementation)

When a transaction has some inputs from user-controlled Holdings
and some from external sources (likely a CoinJoin or PayJoin),
the LedgerEntry retains net-effect direction (so balances stay
correct) but gains a tag distinguishing it from a "real"
outgoing payment. See
`backlog/mixed-input-transaction-flagging.md`.

### Suggested category (non-binding)

The backend computes a `suggested_category` heuristically and
writes it to the LedgerEntry. The user always confirms before it
applies to `category`.

Heuristics:

- If counterparty address matches a CustodialProvider's
  `whitelist_address` → suggest `CUSTODIAL_WITHDRAWAL` (incoming)
  or `CUSTODIAL_DEPOSIT` (outgoing)
- If `direction=INTERNAL` → suggest `INTERNAL_TRANSFER`
- If a recent PaymentRequest's `broadcast_txid` matches → link it
  and suggest that PaymentRequest's category

### Categorization flow

The scanner creates the entry with `category=NULL`. A
CategorizerSuggester subscriber populates `suggested_category`.
The UI surfaces a "Pending categorization" badge via SSE. The
user accepts or overrides; the choice records to the LedgerEntry
and sets `categorized_at`. API surface lives in
`api/openapi.yaml`.

Push-driven categorization prompts (event-driven popups when the
bitcoin node detects new on-chain activity) are captured in
`backlog/push-driven-categorization-workflow.md`.

## UTXO hygiene flags

Computed at UTXO detection and recomputed on material fee-rate
changes (the dust threshold depends on current fees).

### `ADDRESS_REUSED`

An address is reused if it has received funds in more than one
independent transaction batch (independent = not from the same
single transaction). Severity: medium.

### `DUST`

`value_sats < 3 * current_fee_rate * typical_input_size_vbytes`

- `typical_input_size_vbytes`: 68 (P2WPKH), 148 (P2PKH), 57.5
  (P2TR)
- `current_fee_rate`: median of the last N blocks from the
  user's bitcoind
- Severity: high
- Recomputed when fee rates change by more than 50% since last

### `ROUND_NUMBER`

Why this matters: a round-number output reveals the user's
intent in a way most amounts don't. A transaction with output
`100,000 sats` (or `1,000,000 sats`, or any clean multiple) is
visibly different from `94,318 sats` to a chain-analysis tool.
Similarly, `0.001 BTC` worth exactly `€50.00` at the block's
timestamp price is observable as a fiat-denominated payment. The
flag tells the user: "this output advertises that it's
denominated in something else — round sats or a fiat amount —
which leaks info about the source of funds (likely an exchange
buy or a fiat-priced purchase) and helps cluster-analysis tools
group your outputs."

Trigger conditions (any of):

- Output value is a multiple of 100,000 sats or 1,000,000 sats
  (BTC-denominated "round number").
- Output value matches a common fiat denomination at the
  transaction's block-time exchange rate, within a small
  tolerance (e.g. resolves to within ±0.5% of $10, $20, $50,
  $100, €10, €20, €50, €100, etc.). The fiat-denomination
  check is gated by the same rate-source plumbing as
  `display.fiat_conversion.enabled`.

Severity: low (informational). Not actionable per-payment; the
user can opt to use non-round amounts for privacy-sensitive
sends, but the flag is a flag, not a recommendation to redo the
transaction.

### `SUSPECTED_CONSOLIDATION`

A transaction with at least 5 inputs and at most 2 outputs, where
most inputs are from user addresses. The resulting output is
flagged because it links many prior UTXOs. Severity: medium.

### Recommendation generation

Each flag generates a recommendation surfaced via the analysis
endpoint (`api/openapi.yaml`). Templates live in code (i18n
surface). Recommendations are advisory, never blocking; the user
can dismiss per-item, and dismissals persist.

The Blueprint analysis UI surface that aggregates these
recommendations is deferred to post-shipping (per
`backlog/blueprint-analysis.md`). The backend logic
ships pre-shipping so the data accumulates.

## Declared vs observable security analysis

One of TallyKeep's core differentiators and the realization of
the "honest abstraction" principle.

### What is computed

For each non-Account Holding, the analyzer derives an
`ObservableSecurity` from on-chain reality:

```python
ObservableSecurity(
    holding_id,
    inferred_custody_model,         # SELF_SINGLE | SELF_MULTISIG
    inferred_signing_model,         # SOFTWARE_HOT | HARDWARE_OFFLINE | AIRGAPPED | CEREMONIAL | UNKNOWN
    inferred_multisig_parameters,   # (required, total) or None
    inferred_timelock_blocks,       # if a timelock is detected
    last_computed_at
)
```

### How inference works

- **inferred_custody_model**: derived from descriptor structure.
  `pkh()`, `wpkh()`, `tr()` single-key → SELF_SINGLE.
  `sh(multi(...))`, `wsh(multi(...))`, `tr(multi_a(...))` →
  SELF_MULTISIG.
- **inferred_multisig_parameters**: parsed directly from the
  descriptor when multisig.
- **inferred_signing_model**: harder to infer purely from chain
  data. Heuristics:
  - xpub fingerprint matching a known hardware-wallet pattern
    (Coldcard, Trezor, Ledger annotate descriptors) →
    `HARDWARE_OFFLINE`.
  - Very fast back-to-back signing during normal hours →
    `SOFTWARE_HOT`.
  - Otherwise `UNKNOWN`. The discrepancy detector treats
    `UNKNOWN` as no information, not as a contradiction.
- **inferred_timelock_blocks**: parsed from the descriptor if it
  includes an `older()`/`after()` Miniscript fragment.

### Discrepancy detection

A `Discrepancy` compares `declared_security` and
`observable_security`:

| Discrepancy kind | Severity | Trigger |
|---|---|---|
| `claimed_offline_but_pattern_suggests_hot` | Medium | Declared `hardware_offline`, heuristic suggests software-hot |
| `claimed_vault_no_timelock` | Medium | Declared timelock-protection on a Vault, but the descriptor has no Miniscript `older()` / `after()` fragment |
| `claimed_inheritance_no_recovery_path` | Low | Declared `inheritance_configured`, no observable recovery setup |

The discrepancies that **don't fire post-onboarding** because the wizards prevent the mismatch at descriptor-paste time:

- `claimed_single_but_observable_multisig` — user declared Purse but pasted a multisig descriptor. Purse wizard redirects to Vault creation.
- `claimed_multisig_but_single_key` — user declared Vault but pasted a single-key descriptor. Vault wizard rejects and redirects to Strongbox (per `holdings/04_vault.md`, target — once the Vault wizard ships with multisig support).

Both are kept as defensive enums in code for safety against database corruption or migration bugs, but should never fire on a normally-created Holding.

Surfaced via the analysis endpoint and fired as domain events
when newly detected. UI surfaces in real time.

### Recomputation cadence

- On Descriptor import or change: immediate.
- On any new transaction affecting the Holding: immediate.
- Periodic background recomputation: default 24h, configurable
  via the `analysis.recompute_interval_minutes` flag.

### Honest surfacing in the UI

The Holding detail page shows a "Security check" panel: green
(agreement), yellow (low/informational), red (medium/high).
Clicking opens the discrepancy list with explanatory text. The
user can dismiss specific discrepancies if intentional ("yes I
know this Vault is currently single-key, the multisig setup is
in progress").

## Fortune view (global consolidation)

Sums confirmed balances across all Holdings (per ADR-0017 there is no archived state — Forgotten Holdings are gone from the database entirely, so "all Holdings" is unambiguous). Account
balances use `last_known_balance_sats` with an "as of {timestamp}"
indicator. Breaks down by holding_type and purpose. Optional
fiat conversion gated by `display.fiat_conversion.enabled` (see
`backlog/fiat-display.md`). UI contract: the global
view always shows the per-Holding breakdown alongside the total.
No silent consolidation. API surface in `api/openapi.yaml`.

## Fiat display

Fiat conversion is gated behind the
`display.fiat_conversion.enabled` flag and deferred to a future
iteration. Rate source: the first connected CustodialProvider's
ticker. See `backlog/fiat-display.md`.
