# 08 — Lightning Placeholder (v1.5)

This module defines the **interface** that v1 must build to, so that v1.5's Lightning integration slots in without disrupting the rest of the app. No concrete Lightning code is implemented in v1.

## Why this matters in v1

If v1's Banking layer hardcodes on-chain assumptions (a payment is a PSBT), Lightning will force a rewrite. Instead, v1's PaymentRequest abstraction supports both `ONCHAIN` and `LIGHTNING` payment types, the corresponding API endpoints exist (returning 501 Not Implemented in v1), and the UI is built to accommodate both even when only on-chain is functional.

## The `LightningProvider` interface

Defined in v1 in `backend/app/services/lightning_provider.py` as an abstract base class. Imported by `BankingService`. No concrete implementation exists in v1.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LightningBalance:
    local_sats: int                  # outbound capacity
    remote_sats: int                 # inbound capacity
    channel_count: int

@dataclass
class LightningInvoice:
    bolt11: str
    payment_hash: str
    amount_sats: int | None          # None for amountless
    description: str | None
    expires_at: datetime

@dataclass
class LightningPaymentResult:
    payment_hash: str
    status: str                      # 'succeeded' | 'failed' | 'pending'
    fee_sats: int | None
    error: str | None

@dataclass
class LightningChannelState:
    channel_id: str
    state: str                       # 'opening' | 'open' | 'closing' | 'force_closing' | 'closed'
    local_sats: int
    remote_sats: int
    peer_node_id: str

class LightningProvider(ABC):

    @abstractmethod
    async def get_balance(self) -> LightningBalance: ...

    @abstractmethod
    async def create_invoice(
        self,
        amount_sats: int | None,
        description: str,
        expiry_seconds: int = 3600,
    ) -> LightningInvoice: ...

    @abstractmethod
    async def pay_invoice(
        self,
        bolt11: str,
        max_fee_sats: int | None = None,
    ) -> LightningPaymentResult: ...

    @abstractmethod
    async def decode_invoice(self, bolt11: str) -> LightningInvoice: ...

    @abstractmethod
    async def list_payments(self, since: datetime | None = None) -> list[LightningPaymentResult]: ...

    @abstractmethod
    async def list_channels(self) -> list[LightningChannelState]: ...

    @abstractmethod
    async def is_healthy(self) -> tuple[bool, str]: ...    # (healthy, detail)
```

In v1, `BankingService` has branches that look like:

```python
if payment_request.payment_type == PaymentType.LIGHTNING:
    if self.lightning_provider is None:
        raise NotImplementedError("Lightning support pending v1.5")
    # ... dispatch via self.lightning_provider
```

## Concrete implementations (v1.5)

Three providers planned, in priority order.

### 1. `CoreLightningProvider` (priority 1)

- Connects to a user-run Core Lightning (CLN) node via gRPC or RPC over UNIX socket.
- Most sovereign option. The user owns everything.
- Python ecosystem: `pyln-client` is mature.
- Configuration: path to CLN socket, or gRPC host plus TLS cert plus rune.

### 2. `LndProvider` (priority 2)

- Connects to a user-run LND node via gRPC.
- Second most sovereign.
- Configuration: gRPC host, macaroon file path, TLS cert path.

### 3. `PhoenixProvider` (priority 3, possibly deferred to v1.6)

- Connects to Phoenix daemon (when ACINQ ships a clean server-mode API).
- Custodial-ish: ACINQ manages channel liquidity; user keys remain user-owned and the user can always force-close back to their on-chain address.
- Lowest operational burden for the user.

The user chooses one provider at configuration time. Only one active LightningProvider per Holding in v1.5. Multi-provider support is v1.6+.

## API endpoints (stubs in v1, implemented in v1.5)

```
GET  /api/v1/lightning/status                            v1: 501; v1.5: provider health
GET  /api/v1/lightning/balance                           v1: 501; v1.5: LightningBalance for the configured provider
POST /api/v1/lightning/invoices                          v1: 501; v1.5: create invoice (also reachable via banking/invoices with type=lightning)
POST /api/v1/lightning/pay                               v1: 501; v1.5: pay an invoice (also reachable via banking/payment-requests with type=lightning)
GET  /api/v1/lightning/payments                          v1: 501; v1.5: list of recent payments
GET  /api/v1/lightning/channels                          v1: 501; v1.5: channel state list
```

These routes **exist** in v1's FastAPI router with stub handlers returning `501 Not Implemented`. This reserves the URL space and keeps the OpenAPI spec consistent across versions.

## Domain integration

LedgerEntry already supports `source=LIGHTNING_PAYMENT` (module 02). PaymentRequest and Invoice already support `type=LIGHTNING`. The domain is ready.

When v1.5 ships, the LightningListener subscriber consumes events from CLN/LND and:
- Creates LedgerEntries with `source=LIGHTNING_PAYMENT`
- Updates Invoice and PaymentRequest statuses based on payment events
- Emits `lightning.invoice.paid`, `lightning.payment.sent`, `lightning.channel.state_changed`

## User experience implications for v1

Even without Lightning, the v1 UI accommodates it:

- The "Create invoice" screen has a type toggle (On-chain / Lightning); Lightning is disabled in v1 with a tooltip "Coming in v1.5".
- The "Send" screen accepts pasted payment strings and detects BIP21 vs BOLT11 vs LNURL. In v1, anything that is not BIP21 or a bare address returns a clear "Lightning payments coming in v1.5" message.
- The fee tier UI shows "Standard" and "Instant"; "Instant" is visible but disabled in v1.
- Purse Holdings show a "Lightning" section with a "Not configured" badge.

## BIP21 with Lightning fallback

Modern BIP21 URIs can include a Lightning invoice as a fallback:

```
bitcoin:bc1q...?amount=0.001&lightning=lnbc1...
```

In v1.5, our Invoice generator produces these joint URIs when Lightning is enabled on the destination Purse. In v1, we produce plain BIP21 only.

**v1's parser must consume joint URIs gracefully** — ignore the `lightning=` parameter and use the on-chain part. This avoids breaking when the user pastes an invoice from another app that includes a Lightning fallback.

## Open Lightning questions (resolved in dedicated session before v1.5)

These are flagged for the dedicated Lightning Q&A session that precedes v1.5 implementation:

1. **Provider priority confirmation.** Recommendation: CoreLightning first (priority 1), LND second (priority 2), Phoenix deferred.
2. **Channel management UX.** How much surface? Open/close flows, force-close warnings, liquidity rebalancing? Recommendation: hide in v1.5 (use the user's CLN/LND interface for channel ops); add as v1.6 if needed.
3. **Hybrid Holdings.** A Purse with both on-chain and Lightning balances. How is "send 50,000 sats" routed — on-chain or Lightning? Recommendation: user chooses per payment in v1.5; automatic routing rules are v2.
4. **Backup monitoring.** CLN has `lightning-backup-plugin`, LND has static channel backups. The app monitors backup freshness and alerts if stale. Confirmed for v1.5.
5. **Watchtowers.** For users running their own node, do we configure a watchtower automatically? Recommendation: document in README, do not automate in v1.5.
6. **Default Holding type for Lightning.** Per user preference: Lightning is best paired with Purse (online/connected keys). The v1.5 spec should make Purse-with-Lightning the recommended default for daily spending.

## What v1 must NOT do (to keep v1.5 clean)

- Do not hardcode "PSBT" into the generic PaymentRequest type. (Already done correctly: PSBT fields are nullable; LedgerEntry uses a discriminator.)
- Do not put broadcast logic in a generic `BankingService`. The on-chain broadcast belongs to an `OnChainBankingHandler` which is one strategy under the BankingService dispatcher.
- Do not assume an Invoice is reusable indefinitely. BOLT11 has expiry; the Invoice domain already supports `expires_at`.

## What v1 ships that supports v1.5

- PaymentRequest and Invoice support both `ONCHAIN` and `LIGHTNING`.
- LedgerEntrySource enum includes `LIGHTNING_PAYMENT`.
- Event taxonomy in module 01 includes `lightning.*` topics.
- The UI fee-strategy component already labels "Standard" vs "Instant".
- The BIP21 parser already accepts joint URIs.
