# 06 — Banking Layer (On-Chain)

Scope: **send and receive Bitcoin on-chain** for non-Account Holdings. PSBTs are signed on the user's external device; we never sign. Lightning is deferred to a later iteration and defined behind the `LightningProvider` interface (module 08).

## Responsibilities

1. Construct PSBTs from a Holding's Descriptors using BDK coin selection.
2. Export PSBTs in formats compatible with common signing devices.
3. Import signed PSBTs and finalize them.
4. Broadcast via the local bitcoind.
5. Track each PaymentRequest through its lifecycle and link it to the resulting LedgerEntry once confirmed.
6. Provide the Invoice flow for receiving payments.
7. Honest fee user experience using familiar fiat-banking vocabulary.

## Non-responsibilities

- Does NOT sign transactions. Ever.
- Does NOT decide fee rates silently; user-selected or named-strategy only.
- Does NOT initiate outgoing payments from Account Holdings (those use sweep / withdrawal mechanisms, not PaymentRequest).
- Does NOT block outgoing from Vaults; warns instead via the Vault guardrail in module 05.

## Outgoing payment flow

### Step 1: User composes a payment

Inputs:
- **Source Holding** (must not be an Account; must have at least one Descriptor)
- **Destination**: a raw address or a pasted BIP21 URI
- **Amount in sats**, or "max"
- **Fee strategy**: `economy` / `normal` / `priority` / explicit `sat_per_vbyte`
- **Description** (optional)

The frontend posts to `POST /api/v1/banking/payment-requests`.

### Step 2: Backend constructs the PSBT

`BankingService.build_payment_request`:

1. Loads the source Holding and its Descriptors.
2. **Vault guardrail**: applied per the description in module 05 §"Vault outgoing-payment guardrail" — that module is the canonical home for the rule. The endpoint behavior is the one described there (returns 200 with `requires_confirmation=true` and explanation; frontend re-submits with explicit acknowledgement). The behavior is gated by the `banking.vault_outgoing_warns` feature flag.
3. Loads current unspent UTXOs for the Descriptor(s), excluding frozen ones.
4. Asks BDK to build a transaction:
   - Coin selection algorithm: configurable per-installation. Default is **BranchAndBound** (privacy-preferring, minimizes change-output identifiability). Per-payment override is gated by the `banking.coin_selection_per_payment_override` feature flag.
   - Change address: next unused address on the change branch of the source Descriptor.
   - Fee rate: from the named strategy (resolved using bitcoind's `estimatesmartfee`) or the explicit input.
5. BDK returns the unsigned PSBT.
6. Backend persists a PaymentRequest with `status=AWAITING_SIGNATURE`, stores the PSBT.
7. Emits `banking.payment_request.created`.

**Pre-build validations:**

- Source Holding's `signing_model` is not `NOT_APPLICABLE`. Otherwise 400 with `/errors/account-cannot-send`.
- Amount + estimated fee ≤ available confirmed balance. Otherwise 400.
- Destination is a valid address on the correct network. Otherwise 400.
- If amount is `max`, recompute as `balance - fee`.

### Step 3: User exports the PSBT to their signing device

The PaymentRequest exposes the PSBT through:

- **File download** — `GET /api/v1/banking/payment-requests/{id}/psbt` returns a binary `.psbt` file readable by Sparrow, Specter, Electrum, ColdCard, Jade Desktop, and others. Always available.
- **Single QR code** — for PSBTs under approximately 1000 bytes, returned by the `.qr` endpoint as a PNG. Available when `banking.psbt_qr.enabled` is on.
- **Base64 string** — for clipboard transfer, returned in the JSON response of the GET endpoint.

**Currently implemented:** file download and single QR. **Deferred (see `future_iterations.md` "PSBT-by-QR roundtrip on mobile"):** animated multi-frame QR using BBQr or UR2 specifications, for PSBTs that exceed the single-QR size limit.

### Step 4: User signs externally

This happens outside our app. Compatible signers include:

- ColdCard Mk4 (USB, SD card, single QR; multi-frame QR deferred)
- Trezor Model T (USB)
- Ledger Nano S/X (USB)
- Jade (USB; multi-frame QR deferred)
- Sparrow as a software signer
- Electrum as a software signer
- Airgapped Bitcoin Core via file transfer

Currently, file export covers all of them.

### Step 5: User submits the signed PSBT

`POST /api/v1/banking/payment-requests/{id}/submit-signed` accepts:
- `psbt_base64` — a signed PSBT
- `signed_transaction_hex` — a fully finalized transaction (some signers produce this directly)

Backend:
1. Parses the signed PSBT or transaction.
2. Verifies it matches the original request (same input set, same outputs).
3. Attempts to finalize PSBT to a raw transaction.
4. On success: stores `signed_transaction_hex`, sets `status=AWAITING_BROADCAST`, emits `banking.payment_request.signed`.
5. On failure (insufficient signatures, invalid signatures, mismatch): returns 400 with detail.

### Step 6: User broadcasts

`POST /api/v1/banking/payment-requests/{id}/broadcast`.

Backend:
1. Calls bitcoind RPC `sendrawtransaction`.
2. **Persists a `broadcast_attempt` row first** (audit trail).
3. On success: stores `broadcast_txid` on the PaymentRequest, sets `status=BROADCAST`, emits `banking.payment_request.broadcast`.
4. On bitcoind rejection: keeps `status=AWAITING_BROADCAST`, sets `last_error` on the broadcast_attempt, returns 400 with details. User can retry, cancel, or rebuild with a different fee.

### Step 7: Confirmation tracking and reconciliation

When the chain scanner detects a new transaction in a block:
1. It checks whether the txid matches any PaymentRequest's `broadcast_txid` that has `status=BROADCAST`.
2. If yes, it sets the PaymentRequest's `status=CONFIRMED`, populates `resulting_ledger_entry_id` with the LedgerEntry being created from this transaction, and emits `banking.payment_request.confirmed`.
3. The user is notified via the SSE stream.

The link from PaymentRequest to LedgerEntry is now persistent. The user can click any historical LedgerEntry and see "this is the payment you composed on Tuesday for the bike purchase."

### Cancellation

`POST /api/v1/banking/payment-requests/{id}/cancel`:
- Allowed when status is in `{DRAFT, AWAITING_SIGNATURE, AWAITING_BROADCAST}`.
- Sets status to `CANCELLED`.
- Cancellation after broadcast is not possible on-chain. Replace-By-Fee handles this case once that iteration ships — see `future_iterations.md` "Replace-By-Fee (RBF) support".

## Fee user experience (honest abstraction)

The fiat-banking vocabulary mapping:

- **Standard** = on-chain, user picks one of three tiers
- **Instant** = Lightning (deferred; visible but disabled until the Lightning iteration ships)

Within Standard, three named tiers from bitcoind's `estimatesmartfee`:

| Tier | Target blocks | Approx. wait |
|---|---|---|
| `economy` | 24 | ~4 hours |
| `normal` | 6 | ~1 hour |
| `priority` | 2 | ~20 minutes |

The UI displays for each tier:
- Sat/vB rate
- Estimated total fee (sats and base currency if rate source is configured)
- Estimated confirmation time

**Custom rate** is a power-user toggle (`banking.custom_fee_rate.enabled`); user enters sat/vB directly.

**No "who pays the fee" picker.** Bitcoin has no native receiver-pays mechanism. The UI surfaces this as: *"Bitcoin transactions are always sender-paid. The fee covers your transaction's inclusion in a block."*

## Incoming payments (Invoice flow)

### Step 1: User creates an Invoice

`POST /api/v1/banking/invoices`.

Inputs:
- **Destination Holding** (any non-Account Holding; receiving is always allowed)
- **Amount in sats** (optional; can be amountless)
- **Description** (optional)

Backend:
1. Picks the destination Descriptor (if multiple, the user is prompted; otherwise default to first).
2. Derives the next unused receiving Address.
3. Marks that Address as reserved for this Invoice.
4. Constructs a BIP21 URI: `bitcoin:bc1q...?amount=0.001&label=...`
5. Renders a QR code (PNG, 400×400 default).
6. Persists Invoice with `status=OPEN`.
7. Emits `banking.invoice.created`.

### Step 2: Payment detection

When the chain scanner detects a transaction sending to a reserved Invoice address:
1. It creates the LedgerEntry as usual.
2. It matches the Invoice by `receiving_address`.
3. It populates the Invoice's `resulting_ledger_entry_id`.
4. It sets the Invoice status:
   - `PAID` if the amount matches (within rounding) and Invoice had an amount
   - `OVERPAID` if more was received than requested
   - `PAID` if the Invoice was amountless
5. Emits `banking.invoice.paid` with the invoice id and resulting LedgerEntry id.

### Multiple payments to the same address

Bitcoin does not enforce invoice semantics, so subsequent payments to the same address are still received. The UI surfaces this as: *"This address received additional funds beyond the requested amount."* The address is **not** reused for new Invoices; the gap-limit mechanism advances to the next address.

## PSBT format compatibility

- **BIP 174 v0** for maximum compatibility. BIP 370 (PSBT v2) considered later once hardware support is broader.
- Non-witness UTXO data embedded for legacy signer compatibility.
- BIP 32 derivation info on all inputs (required by most hardware signers).
- BIP 32 derivation info on change outputs so signers can verify the change path matches the source wallet (prevents change-output confusion attacks).

## Hardware signer compatibility targets

| Signer | Supported via |
|---|---|
| ColdCard Mk4 | File over USB or SD; single QR if small |
| Trezor Model T | File over USB |
| Ledger Nano S/X | File over USB |
| Jade | File over USB; single QR if small |
| Sparrow (as signer) | File |
| Electrum (as signer) | File |
| Airgapped Bitcoin Core | File transfer |

The current common denominator is file export. Multi-frame QR for the QR-friendly signers is captured in `future_iterations.md` ("PSBT-by-QR roundtrip on mobile").

## Edge cases and error handling

| Situation | Handling |
|---|---|
| Source Holding has no UTXOs | 400, "Insufficient balance" |
| Coin selection cannot meet amount + fee | 400 with shortfall details |
| User submits a signed PSBT with a different input set | 400, "Submitted PSBT does not match original request" |
| Broadcast fails: `txn-mempool-conflict` | Status remains AWAITING_BROADCAST; UI offers "Rebuild with higher fee" |
| User re-derives PSBT after one was already signed | New PSBT replaces old; old marked CANCELLED |
| bitcoind unreachable at broadcast time | 503; job retried by worker with backoff; user notified via SSE |
| User attempts outgoing from Account | 400, `/errors/account-cannot-send`, suggests using sweep |
| User attempts outgoing from long-term Vault | First call returns 200 with `requires_confirmation=true`; second call with explicit confirmation proceeds. Behavior canonically defined in module 05 §"Vault outgoing-payment guardrail". |

## Concurrency

Only one in-flight PaymentRequest per Holding at a time, to avoid double-spending from coin-selection races. Enforced via Postgres advisory lock keyed on `holding_id`. The UI queues additional sends as drafts until the prior one is broadcast or cancelled.

## Audit trail

Every state transition of a PaymentRequest emits an event and writes to the `event_emission_log` (with `is_critical=true`). Combined with `broadcast_attempt`, this provides a complete reconstructable history of every banking operation.
