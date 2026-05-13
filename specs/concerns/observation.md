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

Supported descriptor types: `pkh(...)`, `sh(wpkh(...))`,
`wpkh(...)`, `tr(...)` — single-key only.

**Multisig descriptors are deferred.** Even when creating a Vault
Holding (which has multisig metadata fields), the current build
accepts only single-key descriptors. The Vault metadata is stored
for future use; the analyzer surfaces the discrepancy honestly.
Captured in `future_iterations.md` as "Multisig descriptor
support." See `holdings/04_vault.md` for the per-Vault treatment.

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
outgoing payment. See `future_iterations.md` "Mixed-input
transaction flagging".

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
`future_iterations.md` "Push-driven categorization workflow".

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

Output value matches a round-number heuristic: multiples of
100,000 sats or 1,000,000 sats, or values matching common fiat
denominations at the transaction's block-time price. Severity:
low (informational).

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
`future_iterations.md` "Blueprint analysis"). The backend logic
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
| `claimed_multisig_but_single_key` | High | Holding declared as multisig, descriptor is single-key |
| `claimed_single_but_observable_multisig` | Informational | Declared single-sig, descriptor is multisig (user understated) |
| `claimed_offline_but_pattern_suggests_hot` | Medium | Declared `hardware_offline`, heuristic suggests software-hot |
| `claimed_vault_no_timelock_no_multisig` | Medium | Declared as Vault but neither timelock nor multisig present |
| `claimed_inheritance_no_recovery_path` | Low | Declared `inheritance_configured`, no observable recovery setup |

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

Sums confirmed balances across non-archived Holdings. Account
balances use `last_known_balance_sats` with an "as of {timestamp}"
indicator. Breaks down by holding_type and purpose. Optional
fiat conversion gated by `display.fiat_conversion.enabled` (see
`future_iterations.md` "Fiat display"). UI contract: the global
view always shows the per-Holding breakdown alongside the total.
No silent consolidation. API surface in `api/openapi.yaml`.

## Fiat display

Fiat conversion is gated behind the
`display.fiat_conversion.enabled` flag and deferred to a future
iteration. Rate source: the first connected CustodialProvider's
ticker. See "Fiat display" in `future_iterations.md`.
