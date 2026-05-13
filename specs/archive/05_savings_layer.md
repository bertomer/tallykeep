# 05 — Savings Layer

Scope: **watch-only view** over Holdings of type Purse, Strongbox, and Vault. Continuous chain monitoring, UTXO tracking, hygiene flags, and the **declared-vs-observable security analysis** that is one of TallyKeep's core differentiators.

## Responsibilities

1. Ingest Descriptors, derive addresses, track balances per Descriptor and per Holding.
2. Continuously scan the blockchain (via `bitcoind` JSON-RPC and ZeroMQ) for activity on watched addresses.
3. Surface incoming and outgoing transactions for user categorization.
4. Compute and display UTXO hygiene flags.
5. Produce per-Holding and global "fortune view" summaries.
6. **Compute observable security per Holding and surface discrepancies against declared security.**
7. Enforce structural safeguards on certain Holding types (e.g. Vault outgoing payments warn before proceeding).

## Non-responsibilities

- Does NOT construct PSBTs (that is Banking).
- Does NOT hold private keys.
- Does NOT rely on third-party chain data; the user's own bitcoind is the only source.
- Does NOT manage Account Holdings (those have no descriptors; they are handled by the Trading layer).

## Data ingestion

### Descriptor import

The user provides a BIP 380 output descriptor or a legacy xpub/ypub/zpub which is converted to canonical descriptor form using BDK.

Supported descriptor types:
- `pkh(...)` — legacy P2PKH
- `sh(wpkh(...))` — nested SegWit
- `wpkh(...)` — native SegWit
- `tr(...)` — Taproot, single-key

**Multisig descriptors are deferred.** Even when creating a Vault Holding (which has multisig metadata fields), the current build accepts only single-key descriptors. The Vault metadata is stored for future use; the analyzer surfaces the discrepancy honestly. The deferred work is captured in `future_iterations.md` as "Multisig descriptor support".

### Gap limit

- Default 20, per BIP 44.
- Configurable per Descriptor.
- After scanning, if the last `gap_limit` consecutive addresses on a branch are all unused, scanning stops for that branch. If the user has used addresses past the gap, they must increase the gap limit and trigger a rescan.

### Blockchain scanning

The scanner has two modes that work together.

**Initial scan (one-time, on Descriptor import):**

1. BDK derives all addresses up to `gap_limit` for both the external and change branches.
2. The backend asks bitcoind for the current UTXO set affecting those addresses via `scantxoutset` (fast — no full chain rescan).
3. For historical transactions involving those addresses, the backend uses `getrawtransaction` if `txindex=1` is enabled on the user's bitcoind, or paged `getblock`/`gettransaction` calls otherwise.
4. As UTXOs are discovered they are persisted to `utxo` and the corresponding `onchain_transaction` and `ledger_entry` records are created.

**Incremental scan (continuous, while the app runs):**

1. The ChainListener subscribes to bitcoind ZeroMQ topics:
   - `rawblock` — every new block
   - `rawtx` — every new mempool transaction
2. For each notification, the listener checks whether the transaction touches any watched Address.
3. If it does, the listener emits domain events (`chain.tx.mempool` or `chain.tx.confirmed`) and persists the resulting `onchain_transaction`, updates `utxo` rows, and creates a `ledger_entry`.

**Configuration requirement:** the user's bitcoind must have ZMQ enabled. The README documents the required `bitcoin.conf` lines:

```
zmqpubrawblock=tcp://127.0.0.1:28332
zmqpubrawtx=tcp://127.0.0.1:28333
zmqpubhashblock=tcp://127.0.0.1:28334
```

Onboarding verifies ZMQ is reachable before allowing the user to import their first Descriptor. If not reachable, onboarding shows the exact lines to add to bitcoin.conf.

### UTXO persistence

Every UTXO detected is persisted. When spent, it is marked `is_spent=TRUE` with `spent_in_txid`. Rows are never deleted — historical record.

## LedgerEntry creation and categorization

### Auto-detected fields

When a transaction affects watched addresses, the scanner creates one `ledger_entry` and links it to the affected Holdings via `ledger_entry_holding_link`.

- `direction`:
  - `INCOMING` if net effect on user's Holdings is positive
  - `OUTGOING` if net effect is negative
  - `INTERNAL` if both inputs and outputs are entirely user-owned across our Holdings
- `net_amount_sats`: sum of outputs to user addresses minus sum of inputs from user addresses
- `fee_sats`: from raw transaction (sum of inputs minus sum of outputs)
- `timestamp`: block time, or first-seen-at for mempool entries

### Suggested category (non-binding)

The backend computes a `suggested_category` heuristically and writes it to the LedgerEntry. The user always confirms before it is applied to `category`.

Heuristics:
- If counterparty address matches the `whitelist_address` of a CustodialProvider, suggest `CUSTODIAL_WITHDRAWAL` (incoming) or `CUSTODIAL_DEPOSIT` (outgoing)
- If the LedgerEntry has `direction=INTERNAL`, suggest `INTERNAL_TRANSFER`
- If a recent PaymentRequest's `broadcast_txid` matches and is not yet linked, link it via `resulting_ledger_entry_id` and suggest the category that PaymentRequest used

### User categorization flow

1. ChainListener creates a LedgerEntry with `category=NULL`.
2. ChainListener emits `ledger_entry.requires_categorization`.
3. CategorizerSuggester subscriber populates `suggested_category` and emits the event again so the UI sees the suggestion.
4. LiveUpdateBridge forwards the event to connected SSE clients.
5. Frontend shows a "Pending categorization" badge.
6. User opens the entry, sees the suggestion, accepts or overrides.
7. PATCH on `/api/v1/ledger-entries/{id}` records the user's choice; `categorized_at` is set.

## UTXO hygiene flags

Computed at UTXO detection time and recomputed on fee-rate changes (the dust threshold depends on current fees).

### `ADDRESS_REUSED`

An address is reused if it has received funds in more than one independent transaction batch. Independent = not from the same single transaction.

- Severity: medium
- Recomputed: when a new incoming transaction lands

### `DUST`

A UTXO is dust if `value_sats < 3 * current_fee_rate * typical_input_size_vbytes`.

- `typical_input_size_vbytes`: 68 for P2WPKH, 148 for P2PKH, 57.5 for P2TR
- `current_fee_rate`: median of the last N blocks from the user's bitcoind
- Severity: high
- Recomputed: when fee rates change by more than 50% since last computation

### `ROUND_NUMBER`

Output value matches a round-number heuristic: multiples of 100,000 sats or 1,000,000 sats, or values that match common fiat denominations at the transaction's block-time price.

- Severity: low (informational)
- Computed once at UTXO detection

### `SUSPECTED_CONSOLIDATION`

A transaction with at least 5 inputs and at most 2 outputs, where most inputs are from user addresses. The single resulting output UTXO is flagged because it is now linked to many prior UTXOs.

- Severity: medium
- Computed once at UTXO detection

### Recommendation generation

Each flag generates a recommendation in `GET /api/v1/analysis/holding/{id}/blueprint`:

| Flag | Recommendation template |
|---|---|
| `ADDRESS_REUSED` | "Address {address} has been reused {n} times. Derive a new address for future receipts." |
| `DUST` | "UTXO of {value} sats is below the economic spend threshold at the current fee rate ({rate} sat/vB). Consolidating it would cost more than its value." |
| `ROUND_NUMBER` | "Output {vout} of transaction {txid} is a round-number value, which may indicate a fiat-denominated payment and reduce privacy." |
| `SUSPECTED_CONSOLIDATION` | "This UTXO is the result of consolidating {n} prior UTXOs. All those prior UTXOs are now publicly linked to your wallet." |

Recommendations are advisory, never blocking. The user can dismiss each per-item; dismissal is stored.

## Declared vs observable security analysis

This is one of TallyKeep's core differentiators and the realization of the "shed light on your holdings" principle.

### What is computed

For each non-Account Holding, the analyzer derives an `ObservableSecurity` from the on-chain reality:

```python
ObservableSecurity(
    holding_id,
    inferred_custody_model,         # SELF_SINGLE | SELF_MULTISIG (Account is excluded)
    inferred_signing_model,         # SOFTWARE_HOT | HARDWARE_OFFLINE | AIRGAPPED | CEREMONIAL
    inferred_multisig_parameters,   # (required, total) or None
    inferred_timelock_blocks,       # if any timelock detected
    last_computed_at
)
```

### How inference works

- **inferred_custody_model**: derived from descriptor structure. `pkh()`, `wpkh()`, `tr()` with one key → SELF_SINGLE. `sh(multi(...))`, `wsh(multi(...))`, `tr(multi_a(...))` → SELF_MULTISIG.
- **inferred_multisig_parameters**: parsed directly from the descriptor when multisig.
- **inferred_signing_model**: harder to infer purely from chain data. Current heuristics:
  - If the descriptor has a clear xpub fingerprint matching a known hardware-wallet signing-pattern (Coldcard, Trezor, Ledger usually annotate descriptors), suggest `HARDWARE_OFFLINE`.
  - If recent signing patterns show very fast back-to-back transactions during normal hours, suggest `SOFTWARE_HOT`.
  - Otherwise, leave as `UNKNOWN` rather than guess.
- **inferred_timelock_blocks**: parsed from the descriptor if it includes a `older()`/`after()` Miniscript fragment.

Where the observable side genuinely cannot determine something, it returns `UNKNOWN` rather than a guess. The discrepancy detector treats `UNKNOWN` as "no information," not as a contradiction.

### Discrepancy detection

A `Discrepancy` is computed by comparing `declared_security` and `observable_security`:

| Discrepancy kind | Severity | Trigger |
|---|---|---|
| `claimed_multisig_but_single_key` | High | Holding declared as multisig, descriptor is single-key |
| `claimed_single_but_observable_multisig` | Informational | Holding declared as single-sig, descriptor is multisig (user understated) |
| `claimed_offline_but_pattern_suggests_hot` | Medium | Declared `hardware_offline`, but signing-pattern heuristic suggests software-hot |
| `claimed_vault_no_timelock_no_multisig` | Medium | Declared as Vault but neither timelock nor multisig is present |
| `claimed_inheritance_no_recovery_path` | Low | Declared `inheritance_configured`, but no observable recovery setup is detectable |

Discrepancies are returned by `GET /api/v1/analysis/holding/{id}/security`. They also fire `analysis.discrepancy.detected` events when newly detected, so the UI surfaces them in real time.

### Recomputation cadence

- On Descriptor import or change: immediate.
- On any new transaction affecting the Holding: immediate.
- Periodic background recomputation: every 24 hours by default (configurable via `analysis.recompute_interval_minutes`).

### Honest surfacing in the UI

The Holding detail page shows a "Security check" panel:
- Green: declared and observable agree, no discrepancies.
- Yellow: low or informational discrepancies present.
- Red: medium or high discrepancies present.

Clicking opens a list of specific discrepancies with explanatory text. The user can dismiss specific discrepancies if they are intentional ("yes I know this Vault is currently single-key, the multisig setup is in progress").

## Vault outgoing-payment guardrail

The Vault type is the strongest user-held storage tier; outgoing-from-Vault is a deliberate-by-design ceremony, not a routine action. The safeguard for Vaults is implemented as a **warning** during PaymentRequest creation (not a hardcoded type-system block — per the generalized-SweepPolicy / warn-don't-block discipline):

- If the source Holding is a Vault with `purpose=long_term`, the PaymentRequest creation endpoint returns a 200 response with `requires_confirmation=true` and a clear explanation: "You are composing an outgoing payment from a Vault declared as long-term. This is unusual; confirm you intend this." The frontend re-submits the request with explicit acknowledgement to proceed.
- The frontend renders this as a modal with explicit "yes, I intend this" before proceeding.
- The policy is configurable via the `banking.vault_outgoing_warns` feature flag (default `true`; users can disable from Settings if they want to opt out of the warning).

This keeps the safeguard real but moves it out of the type system into the UX policy layer, where the user has the final say.

## Fortune view (global consolidation)

Endpoint: `GET /api/v1/holdings/summary/global`.

Logic:
- Sum confirmed balances across all non-archived Holdings.
- For Account Holdings, use `last_known_balance_sats` with an "as of {timestamp}" indicator.
- Break down by holding_type and by purpose.
- Optionally convert to base currency (deferred, gated by `display.fiat_conversion.enabled` — see `future_iterations.md` "Fiat display").

UI contract: the global view always shows the per-Holding breakdown alongside the total. No silent consolidation.

## Fiat display

Fiat conversion is gated behind the `display.fiat_conversion.enabled`
flag and is deferred to a future iteration. The rate source is the
first connected CustodialProvider's ticker (no third-party
dependency added). See the "Fiat display" entry in
`future_iterations.md` for the full sketch.
