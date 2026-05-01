# 07 — Trading Layer (v1: read-only and policy-driven sweeps)

Scope: aggregate **read-only views** across CustodialProviders and execute **withdrawal-only operations** driven by SweepPolicies. Order placement is explicitly out of scope for v1.

## Product principle: minimum-exposure trading

The CustodialProvider is **pass-through liquidity, not storage**. The design assumption is that the user has placed (or will place) the trade manually on the provider's website. Our app's job is to enforce: *get the BTC off the provider as fast as policy allows.*

This is the insight of the Trading layer. It is what distinguishes the product from a portfolio tracker.

## Responsibilities (v1)

1. Connect to supported CustodialProviders via ccxt using user-provided API credentials with read and withdrawal permissions only (trade permissions are rejected at registration).
2. Poll provider balances and surface them through Account Holdings.
3. Detect new BTC balances appearing on a provider (likely the result of a manual buy or a deposit).
4. Execute withdrawals according to SweepPolicies, with safety validation, daily caps, and optional per-execution user confirmation.
5. Persist every sweep attempt to `sweep_execution` for audit.
6. Reconcile provider-reported withdrawals with the resulting on-chain LedgerEntries.

## Non-responsibilities (v1)

- **No order placement.** ccxt's `create_order` and all trade endpoints are never called. This keeps v1 out of any "trading bot" regulatory framing.
- **No stablecoin or non-BTC asset tracking.** Other-asset balances may be displayed read-only but are not actionable.
- **No fiat deposit or withdrawal automation.**

## Supported CustodialProviders (v1)

| Provider | Adapter id | Whitelist API support | Tier |
|---|---|---|---|
| Kraken | `kraken` | Yes (WithdrawAddresses) | First-class |
| Bitstamp | `bitstamp` | Whitelist set via web UI; API consumes whitelisted address names | First-class |

Future v1.x: Bitfinex, Coinbase Advanced. Future v1.x: a custom Swissquote adapter (outside ccxt). The adapter abstraction makes adding providers a localized change — see module 01's three-layer separation.

## API credential constraints

### Registration flow

The user provides API credentials when creating an Account Holding (see module 04, `POST /api/v1/holdings/account`).

Backend:
1. Calls the provider's "get key permissions" endpoint via the appropriate adapter.
2. Parses permissions. **If any of `{trade, margin, staking, futures}` is enabled, the registration is rejected** with a clear message: *"This API credential has more permissions than required. Create a new credential with only 'query funds' and 'withdraw funds' enabled."*
3. If the provider exposes a withdrawal-whitelist API, verifies that the configured `whitelist_address` is on the provider's side-of-the-fence whitelist.
4. If the provider does not expose a whitelist-check API, the app displays a blocking warning during creation: *"We cannot programmatically verify withdrawal whitelisting on this provider. You must manually configure a withdrawal whitelist on the provider's website for the address {address}. Confirm you have done this?"* The user must check a confirmation box.

### Credential storage

API credentials are stored in the `secret` table per the cryptography defined in module 03. The Account Holding's `custodial_provider` row references credentials by reference string only; values never appear in the row itself.

### Credential rotation

`PATCH /api/v1/custodial-providers/{id}` accepts new credentials. Old ones are immediately purged from the secret store.

## Balance polling

The CustodialPollScheduler (module 01) emits `trading.custodial.poll_requested` events on a schedule:
- Default: every 10 minutes.
- Configurable: 1 to 60 minutes via `runtime_configuration.custodial_polling.interval_seconds`.
- On demand: `POST /api/v1/custodial-providers/{id}/refresh` triggers an immediate poll.

The CustodialPoller subscriber consumes these events, calls the relevant CustodialProviderAdapter, and:

1. Fetches BTC balance and other-asset balances.
2. Fetches recent withdrawal history (to reconcile with `sweep_execution`).
3. Fetches recent deposit history (to correlate with on-chain incoming).
4. Updates the provider row's `last_known_balance_sats`, `last_polled_at`, `last_error`.
5. If BTC balance has changed since last poll, emits `trading.custodial.balance_changed`.

Polling failures (rate-limit hits, network errors, auth errors) are logged and surfaced via `system.custodial.auth_failed` events. After N consecutive auth errors (default 5), the provider is marked `is_active=FALSE` and the user is alerted via SSE.

## SweepPolicy execution

SweepPolicy is now a generalized concept (module 02) that applies between any two Holdings. The Trading layer is its primary user, especially for Account → non-Account sweeps. Bidirectional Holdings-to-Holdings rebalancing is supported by the same primitive.

### Trigger types

**Scheduled** — cron-driven via APScheduler in the SweepScheduler component.

```json
{
  "trigger_type": "scheduled",
  "trigger_configuration": { "cron_expression": "0 3 * * FRI", "timezone": "Europe/Zurich" }
}
```

**Threshold** — fires when the source balance crosses a value, with cooldown to avoid flapping.

```json
{
  "trigger_type": "threshold",
  "trigger_configuration": { "threshold_sats": 5000000, "cooldown_hours": 24 }
}
```

The SweepEngine subscriber listens for `trading.custodial.balance_changed` events and re-evaluates threshold policies for the affected Holding.

**Manual** — only fires on user request via `POST /api/v1/sweep-policies/{id}/execute-now`.

### Safety validator (warns, does not block)

When a SweepPolicy is created or modified, the validator runs and computes `safety_warnings`. The policy cannot be enabled until all warnings are acknowledged. The user can acknowledge them via `POST /api/v1/sweep-policies/{id}/acknowledge-warnings`.

Validator rules in v1:

| Warning | Severity | Condition |
|---|---|---|
| `destination_keys_on_host` | high | Destination Holding is a Purse — keys may live on the same host |
| `destination_is_custodial` | high | Destination Holding is an Account — defeats minimum-exposure |
| `same_security_tier` | medium | Source and destination have the same `signing_model` |
| `no_maximum_cap_set` | medium | `maximum_per_period_sats` is None for non-trivial amounts |
| `unverified_whitelist_on_provider` | high | Source Holding is an Account whose CustodialProvider whitelist could not be verified via API |

The warnings are stored on the policy row. The user explicitly acknowledges each. Once acknowledged, the policy can be enabled. Re-running the validator on policy modification produces fresh warnings; if a previously acknowledged warning kind reappears unchanged, its acknowledgement carries over; if the warning reappears with different parameters, acknowledgement is cleared and the user must re-confirm.

### Execution path (SweepEngine subscriber)

When `trading.sweep.triggered` fires (from the scheduler) or `trading.custodial.balance_changed` matches a threshold policy:

1. **Pre-check.**
   - Fetch fresh balance from the source (for Account, this is a fresh provider call; for non-Account Holdings, sum of confirmed UTXOs).
   - Compute `intended_amount = balance - minimum_balance_sats`.
   - Abort if `intended_amount <= 0`.
   - If `maximum_per_period_sats` is set, check accumulated daily total against the cap.
   - Persist a `sweep_execution` row with `status=REQUESTED`. **Persist first.**

2. **User-confirmation gate (if `requires_user_confirmation=true`).**
   - Set `sweep_execution.status=AWAITING_USER_CONFIRMATION`.
   - Emit `trading.sweep.triggered` so the UI shows a confirmation prompt.
   - Wait for user response via `POST /api/v1/sweep-executions/{id}/confirm`.
   - If denied, set `status=CANCELLED` and end.

3. **Dispatch.**
   - For Account sources: call `CustodialProviderAdapter.withdraw(amount, whitelist_address)`. The adapter wraps ccxt and normalizes provider quirks.
   - For non-Account sources (rebalancing between user Holdings): construct a PaymentRequest under the hood with the destination as the next receive address of the destination Holding. This requires the source to be signing-capable (Purse, Strongbox, Vault). The user still has to sign the resulting PSBT externally.
   - On dispatch, set `sweep_execution.status=DISPATCHED` and store any `provider_withdrawal_id`.

4. **On-chain pending.**
   - Once the provider acknowledges or the PSBT is broadcast, set `status=ONCHAIN_PENDING` and store `expected_txid`.
   - Emit `trading.sweep.executed`.

5. **Reconciliation.**
   - When the chain scanner detects the corresponding incoming transaction at the destination (matching by amount and approximate timing), it links it.
   - Set `sweep_execution.status=COMPLETED`, store `confirmed_txid`, `completed_at`.
   - Auto-suggest the resulting LedgerEntry's category as `CUSTODIAL_WITHDRAWAL` (for Account sources) or `INTERNAL_TRANSFER` (for inter-Holding rebalances). User confirms.

6. **Failure paths.**
   - Provider rejection (insufficient funds, KYC block, withdrawal limit): set `status=FAILED`, store `error_message`, emit `trading.sweep.failed`. Disable further attempts on this policy until user reviews.
   - Network error: retry with exponential backoff up to 3 attempts within the same execution; then mark FAILED.

### Account → non-Account sweep mechanics (the common path)

This is the bread-and-butter use case. Flow:

```
Account (Kraken) ──▶ SweepPolicy ──▶ Strongbox (cold reserve)

Trigger fires (scheduled or threshold)
  │
  ▼
SweepEngine pre-check
  │
  ▼
[optional: AWAITING_USER_CONFIRMATION]
  │
  ▼
CustodialProviderAdapter.withdraw(
  amount = intended_amount,
  address = whitelist_address (= a Strongbox-owned address)
)
  │
  ▼
Provider returns withdrawal id
  │ (provider broadcasts on-chain when its internal queue clears)
  ▼
ChainListener detects incoming tx at the destination Address
  │
  ▼
LedgerEntry created with direction=INCOMING and link to destination Holding
  │
  ▼
SweepEngine matches expected_txid → confirmed_txid
  │
  ▼
sweep_execution.status = COMPLETED
LedgerEntry suggested category = CUSTODIAL_WITHDRAWAL
```

### Inter-Holding rebalancing (Holding-to-Holding sweeps)

The same primitive supports the user's other use cases. Examples:

- Strongbox → Purse, top up to 50,000 sats every Monday (your "topping up the spending stack" case).
- Purse → Strongbox, threshold-based when daily-spending balance exceeds a cap.
- Strongbox → Vault, threshold-based when reserve exceeds 600,000 sats (your "promote to long-term" case).

The mechanics differ from Account-source sweeps: the SweepEngine constructs a PaymentRequest, the user signs externally, broadcast happens via the normal banking flow. The sweep is driven by the policy but the signing remains user-controlled. The user's signing device must be reachable when the policy fires; if not, the sweep waits as `AWAITING_USER_CONFIRMATION` until the user processes it.

### Daily caps and safety controls

- **`maximum_per_period_sats`**: enforced. The accumulated total of completed sweeps in the rolling 24h window is checked before each execution.
- **Dry-run flag** per policy (`is_dry_run` field): when true, the sweep evaluates and persists `sweep_execution` rows but does not dispatch. Useful for testing setup.
- **Global pause**: `POST /api/v1/sweep-policies/pause-all` sets a runtime-configuration flag. While paused, the SweepEngine consumes events but does not execute. UI surfaces this prominently.
- **Per-policy `requires_user_confirmation`**: when true, every execution prompts. Default for Beginner and Intermediate profiles. Sovereign profile defaults this to false.

## What the user sees

The Trading view shows, per Account Holding:

- Provider name, last poll time, connection status (green / amber / red).
- Current BTC balance (and read-only breakdown of other assets if present).
- Active SweepPolicy summaries ("Auto-sweep weekly every Friday at 03:00 to Strongbox").
- "Sweep now" button.
- Recent sweep history with status badges.
- Prominent warning if provider-side whitelist is unverified.

For non-Account Holdings with outgoing SweepPolicies (rebalancing), the same panel appears on the Holding's detail page.

## Provider adapter responsibilities

Each CustodialProviderAdapter implements:

```python
class CustodialProviderAdapter(ABC):
    @abstractmethod
    async def get_permissions(self) -> ProviderPermissions: ...

    @abstractmethod
    async def get_balance(self) -> int: ...                  # sats

    @abstractmethod
    async def get_other_balances(self) -> dict[str, str]: ... # asset -> human-readable amount

    @abstractmethod
    async def get_recent_withdrawals(self, since: datetime) -> list[Withdrawal]: ...

    @abstractmethod
    async def get_recent_deposits(self, since: datetime) -> list[Deposit]: ...

    @abstractmethod
    async def withdraw(self, amount_sats: int, address: str) -> WithdrawalResult: ...

    @abstractmethod
    async def verify_whitelist(self, address: str) -> WhitelistVerification: ...
```

This is the Anti-Corruption Layer for trading. ccxt's per-provider quirks are absorbed here. The Trading service code never sees ccxt directly.

## Regulatory distance posture (locked by design)

The architecture keeps the app on the right side of these lines:

- We do NOT route buy/sell orders → no broker role.
- We do NOT custody fiat or crypto → no custodian role.
- We do NOT pool user funds → no money-transmitter role.
- We do NOT match buyers and sellers → no exchange role.
- The user's relationship with each CustodialProvider is direct; we are a client to their API, on the user's behalf, from the user's own machine, with the user's own credentials.

This is why v1 is read-only plus withdrawal-only. Adding order placement in v2 is a deliberate step up the regulatory ladder and will require fresh evaluation.
