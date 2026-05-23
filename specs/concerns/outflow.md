# Outflow — PSBT construction, signing routing, broadcast

How TallyKeep moves value out of non-Account Holdings on-chain.
Generic machinery here; per-Holding routing in
`holdings/<type>.md`.

**Scope of this concern.** PSBT construction and broadcast are
backend-side, watch-only operations — building an unsigned PSBT
and broadcasting a finalized transaction never require keys.
**Signing** happens off-backend per ADR-0009:
- TallyKeep-managed and External-imported Purses on the device
  holding the seed → Capacitor client signs via NativeBridge.
- Strongbox / Vault → hardware wallet signs externally; user is
  the bridge.
- External-watch-only Purse → source wallet signs; TallyKeep
  redirects there.

Account outflows are **not** PSBTs — they use the custodial
provider's withdraw API. See `holdings/01_account.md`.

## Responsibilities

1. Construct PSBTs from a Holding's Descriptors using BDK coin
   selection.
2. Export PSBTs in formats compatible with common signing
   surfaces (file, single QR; multi-frame QR deferred).
3. Import signed PSBTs and finalize them.
4. Broadcast via the local bitcoind.
5. Track each PaymentRequest through its lifecycle and link it
   to the resulting LedgerEntry once confirmed.
6. Provide the Invoice flow for receiving payments.
7. Honest fee user experience using familiar fiat-banking
   vocabulary.

## Non-responsibilities

- Does NOT sign transactions. Ever. (See ADR-0009 for the
  zone-by-zone signing model.)
- Does NOT decide fee rates silently; user-selected or
  named-strategy only.
- Does NOT initiate outgoing payments from Account Holdings
  (those use sweep / withdrawal mechanisms — see
  `holdings/01_account.md`).
- Does NOT hardcode "PSBT" assumptions into the abstraction.
  PaymentRequest supports both `ONCHAIN` and `LIGHTNING` (per
  `concerns/lightning_placeholder.md`); on-chain broadcast is
  one strategy under a dispatcher.

## Outgoing payment flow (on-chain)

### Step 1: Compose

Inputs:
- **Source Holding** (non-Account; must have at least one
  Descriptor).
- **Destination** — raw address or pasted BIP21 URI.
- **Amount in sats**, or `max`.
- **Fee strategy** — `economy` / `normal` / `priority` /
  explicit `sat_per_vbyte`.
- **Description** (optional).

API surface in `api/openapi.yaml`.

### Step 2: Construct the PSBT

`BankingService.build_payment_request`:

1. Loads the source Holding and its Descriptors.
2. **Per-Holding-type guardrails** apply here. For any Vault
   source Holding, the guardrail returns
   `requires_confirmation=true` (per `holdings/04_vault.md`).
   The frontend re-submits with explicit acknowledgement to
   proceed. Configurable via `banking.vault_outgoing_warns`
   (user-final-authority feature flag; default `true`). The
   guardrail is unconditional on Vault type per ADR-0018 —
   Vault is long-term by definition (ADR-0010), so a per-Vault
   tag governing the guardrail would be redundant.
3. Loads current unspent UTXOs for the Descriptor(s), excluding
   frozen ones.
4. Asks BDK to build a transaction:
   - **Coin selection algorithm** — configurable per-installation.
     Default is **BranchAndBound** (privacy-preferring,
     minimizes change-output identifiability). Per-payment
     override gated by `banking.coin_selection_per_payment_override`.
   - **Change address** — next unused address on the change
     branch of the source Descriptor.
   - **Fee rate** — from the named strategy (resolved via
     bitcoind's `estimatesmartfee`) or the explicit input.
5. BDK returns the unsigned PSBT.
6. Backend persists a PaymentRequest with
   `status=AWAITING_SIGNATURE`, stores the PSBT.
7. Emits the corresponding domain event (taxonomy in
   `01_architecture.md`).

**Pre-build validations:**

- Source Holding has a signing-capable model (not Account).
- Amount + estimated fee ≤ available confirmed balance.
- Destination is a valid address on the correct network.
- If amount is `max`, recompute as `balance - fee`.

### Step 3: Route to a signer (per Holding type and client capability)

The routing decision is the per-Holding-type behavior. The PSBT
itself, once built, is generic — what differs is *who signs* and
*how the unsigned PSBT reaches them*.

| Source Holding | Routing |
|---|---|
| **External-watch-only Purse** | Hide Send by default. Primary affordance redirects to the source wallet ("Spend in [wallet]"). Power-user toggle exposes PSBT export. |
| **TallyKeep-managed / External-imported Purse**, on device holding the seed | Native sign via `NativeBridge` (biometric → sign in-app). |
| **TallyKeep-managed / External-imported Purse**, on any other client | View-only gate ("Open TallyKeep on the device that holds them"). No PSBT export. |
| **Strongbox** | Export PSBT (file / single QR) → user signs externally → re-import. Multi-frame QR deferred. |
| **Vault** | Same as Strongbox today (single-key). When multisig support ships: collect signatures from `m`-of-`n` co-signers. |

Per-Holding-type detail in `holdings/<type>.md`.

**Export formats** (when PSBT export applies):
- **File download** — binary `.psbt` file readable by Sparrow,
  Specter, Electrum, ColdCard, Jade Desktop, and others. Always
  available.
- **Single QR code** — for PSBTs under ~1000 bytes. Gated by
  `banking.psbt_qr.enabled`.
- **Base64 string** — for clipboard transfer.
- **Multi-frame QR (BBQr / UR2)** — deferred per
  `backlog/psbt-by-qr-roundtrip-on-mobile.md`.

### Step 4: Submit the signed PSBT

Backend accepts:
- `psbt_base64` — a signed PSBT.
- `signed_transaction_hex` — a fully finalized transaction
  (some signers produce this directly).

Backend:
1. Parses the signed PSBT or transaction.
2. Verifies it matches the original request (same input set,
   same outputs).
3. Attempts to finalize PSBT to a raw transaction.
4. On success: stores `signed_transaction_hex`, sets
   `status=AWAITING_BROADCAST`, emits the corresponding event.
5. On failure (insufficient signatures, invalid signatures,
   mismatch): returns 400 with detail.

### Step 5: Broadcast

Backend:
1. **Persists a `broadcast_attempt` row first** — audit trail.
2. Calls bitcoind RPC `sendrawtransaction`.
3. On success: stores `broadcast_txid` on the PaymentRequest,
   sets `status=BROADCAST`, emits the broadcast event.
4. On bitcoind rejection: keeps `status=AWAITING_BROADCAST`,
   sets `last_error` on the broadcast_attempt, returns 400 with
   details. User can retry, cancel, or rebuild with a different
   fee.

The persist-first-emit-second pattern (per `01_architecture.md`)
ensures broadcast attempts are reconstructable even if the event
bus loses a notification.

### Step 6: Confirmation tracking and reconciliation

When the chain scanner detects a new transaction in a block:
1. It checks whether the txid matches any PaymentRequest's
   `broadcast_txid` with `status=BROADCAST`.
2. If yes, sets `status=CONFIRMED`, populates
   `resulting_ledger_entry_id` with the LedgerEntry being
   created, and emits the confirmation event.
3. The user is notified via the SSE stream.

The link from PaymentRequest to LedgerEntry is now persistent —
the user can click any historical LedgerEntry and see "this is
the payment you composed on Tuesday for the bike purchase."

### Cancellation

Allowed while `status` is in `{DRAFT, AWAITING_SIGNATURE,
AWAITING_BROADCAST}`. Sets status to `CANCELLED`. Cancellation
after broadcast is not possible on-chain; Replace-By-Fee handles
that case once the RBF iteration ships (see
`backlog/replace-by-fee-rbf-support.md`).

## Fee user experience (honest abstraction)

The fiat-banking vocabulary mapping:

- **Standard** = on-chain, user picks one of three tiers
- **Instant** = Lightning (deferred — visible but disabled until
  the Lightning iteration ships)

Within Standard, three named tiers from bitcoind's
`estimatesmartfee`:

| Tier | Target blocks | Approx. wait |
|---|---|---|
| `economy` | 24 | ~4 hours |
| `normal` | 6 | ~1 hour |
| `priority` | 2 | ~20 minutes |

The UI displays for each tier:
- Sat/vB rate
- Estimated total fee (sats and base currency if rate source is
  configured)
- Estimated confirmation time

**Custom rate** is a power-user toggle
(`banking.custom_fee_rate.enabled`); user enters sat/vB
directly.

**No "who pays the fee" picker.** Bitcoin has no native
receiver-pays mechanism. The UI surfaces this honestly: *"Bitcoin
transactions are always sender-paid. The fee covers your
transaction's inclusion in a block."*

## Settlement-rails framing (target — pending)

The "settled" state is statistical, not binary. The settlement-
rails pattern (per
`backlog/settlement-rails-payment-status-with-confirmation-probability.md`)
surfaces:

1. Instruction composed (PSBT created, not signed)
2. Instruction signed (PSBT signed, not broadcast)
3. Instruction acknowledged (broadcast, in mempool)
4. Settlement (on-chain inclusion + depth, with finality
   probability)

This is the **target shape** for the broadcast lifecycle; the
current build uses simpler "broadcast / confirmed" labels. The
upgrade lands when the confirmation-probability feature ships.

## Incoming payments (Invoice flow)

### Step 1: Create

Inputs:
- **Destination Holding** — any non-Account Holding (receiving
  is always allowed).
- **Amount in sats** (optional; amountless is supported).
- **Description** (optional).

Backend:
1. Picks the destination Descriptor (prompts user if multiple).
2. Derives the next unused receiving Address.
3. Marks that Address as reserved for this Invoice.
4. Constructs a BIP21 URI:
   `bitcoin:bc1q...?amount=0.001&label=...`
5. Renders a QR code.
6. Persists Invoice with `status=OPEN`.
7. Emits the invoice-created event.

### Step 2: Payment detection

When the chain scanner detects a transaction sending to a
reserved Invoice address:
1. It creates the LedgerEntry as usual.
2. Matches the Invoice by `receiving_address`.
3. Populates the Invoice's `resulting_ledger_entry_id`.
4. Sets the Invoice status:
   - `PAID` if the amount matches (within rounding) and Invoice
     had an amount
   - `OVERPAID` if more was received than requested
   - `PAID` if the Invoice was amountless
5. Emits the invoice-paid event.

### Multiple payments to the same address

Bitcoin does not enforce invoice semantics, so subsequent
payments to the same address are still received. The UI surfaces
this honestly: *"This address received additional funds beyond
the requested amount."* The address is **not** reused for new
Invoices; the gap-limit mechanism advances to the next address.

### Receive in static / merchant mode (deferred)

Per `backlog/receive-in-static-merchant-mode.md`:
a per-Holding toggle for tip jars / donation addresses / static
merchant flows. The Blueprint analyzer continues to flag the
reuse honestly when that feature ships.

## PSBT format compatibility

- **BIP 174 v0** for maximum compatibility. BIP 370 (PSBT v2)
  considered later once hardware support is broader.
- Non-witness UTXO data embedded for legacy signer
  compatibility.
- BIP 32 derivation info on all inputs (required by most
  hardware signers).
- BIP 32 derivation info on change outputs so signers can verify
  the change path matches the source wallet (prevents
  change-output confusion attacks).

## Edge cases and error handling

| Situation | Handling |
|---|---|
| Source Holding has no UTXOs | 400, "Insufficient balance" |
| Coin selection cannot meet amount + fee | 400 with shortfall details |
| Submitted PSBT has different input set | 400, "Submitted PSBT does not match original request" |
| Broadcast fails: `txn-mempool-conflict` | Status remains AWAITING_BROADCAST; UI offers "Rebuild with higher fee" |
| User re-derives PSBT after one was already signed | New PSBT replaces old; old marked CANCELLED |
| bitcoind unreachable at broadcast time | 503; job retried with backoff; user notified via SSE |
| Outgoing attempted from Account | 400 with custodial-cannot-send error; suggest sweep |
| Outgoing from long-term Vault | First call returns 200 with `requires_confirmation=true`; second call with confirmation proceeds. Per `holdings/04_vault.md`. |

## Concurrency

Only one in-flight PaymentRequest per Holding at a time, to
avoid double-spending from coin-selection races. Enforced via
Postgres advisory lock keyed on `holding_id`. The UI queues
additional sends as drafts until the prior one is broadcast or
cancelled.

## Audit trail

Every state transition of a PaymentRequest emits an event and
writes to the `event_emission_log` (with `is_critical=true`).
Combined with `broadcast_attempt`, this provides a complete
reconstructable history of every outflow operation.

## Lightning outflow (interface today, behavior deferred)

PaymentRequest already supports `type=LIGHTNING`. The dispatcher
in `BankingService` has a branch:

```python
if payment_request.payment_type == PaymentType.LIGHTNING:
    if self.lightning_provider is None:
        raise NotImplementedError("Lightning support pending")
    # dispatch via self.lightning_provider
```

Concrete `LightningProvider` implementations land in the
Lightning iteration. See `concerns/lightning_placeholder.md` for
the interface contract.

## Deferred

| Item | Tracked in |
|---|---|
| Settlement-rails framing with confirmation probability | `backlog/settlement-rails-payment-status-with-confirmation-probability.md` |
| Multi-frame QR PSBT roundtrip (BBQr / UR2) | `backlog/psbt-by-qr-roundtrip-on-mobile.md` |
| Replace-By-Fee (RBF) bumping a stuck transaction | `backlog/replace-by-fee-rbf-support.md` |
| BIP21 with Lightning fallback (unified payment URI) | `backlog/bolt12-offers.md` |
