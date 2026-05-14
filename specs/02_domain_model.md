# 02 — Domain Model

This module defines the core entities. These are the nouns of the application. All API contracts, database schemas, and user interface state derive from these.

## Vocabulary contract

The user-facing words are chosen deliberately. They are used consistently throughout the spec and the codebase.

- **Holding** — the abstract container concept. A purpose-bound bucket of value the user wants to see, manage, and reason about as a unit. Has four concrete subtypes: Account, Purse, Strongbox, Vault.
- **Account** — a Holding backed by a custodial provider. The provider holds the keys; we read balances and trigger withdrawals via API.
- **Purse** — a Holding for everyday spending. The implementation axis that matters is **whether the Purse has on-device keys**:
   - *Descriptor-only* — TallyKeep watches an xpub / descriptor; the seed lives in another hot wallet (Phoenix, BlueWallet, Mutiny, Sparrow hot mode). TallyKeep never holds the key. Spending redirects to the source wallet.
   - *On-device-keys* — the seed lives in the Capacitor client's OS Keychain/Keystore (biometric-gated), on the specific device that ran creation or import. Never on the backend. Signing happens in-app via the `NativeBridge` interface.
   The seed *source* — TallyKeep generated it (`ON_DEVICE_TK_GENERATED`) or the user imported it from another wallet (`ON_DEVICE_USER_IMPORTED`, pending arbitration `purse-upgrade-path`) — is a secondary classification carried for disclosure copy and security-health framing. It does not change the implementation axis (both have on-device keys).
- **Strongbox** — a Holding backed by a wallet whose private keys are on an offline or hardware signing device. User holds the keys; signing requires the external device.
- **Vault** — a Holding backed by a wallet under additional structural protection (multisig, timelocks, geographic separation, inheritance setup). User holds the keys; access requires ceremony. Multisig descriptors are deferred; pre-shipping accepts single-key descriptors with the analyzer surfacing the gap.
- **Descriptor** — the technical primitive (BIP 380) that defines how a wallet derives its addresses. A Holding of type Purse, Strongbox, or Vault references one or more Descriptors. Account does not have a Descriptor.
- **CustodialProvider** — the technical primitive that defines a connection to a third-party custodian that holds keys on the user's behalf (Kraken, Bitstamp, Swissquote). An Account references exactly one CustodialProvider. **P2P acquisition venues** (RoboSats, Bisq, future similar) are *not* CustodialProviders — keys stay with the user — and are tracked separately when their iteration lands; see `future_iterations.md`.
- **LedgerEntry** — a recorded movement of value affecting one or more Holdings. May be backed by an OnChainTransaction, a Lightning payment (when that iteration ships), or a CustodialProvider event (deposit, withdrawal).
- **OnChainTransaction** — a Bitcoin blockchain transaction record, identified by txid.
- **PaymentRequest** — a user-initiated outgoing payment, in lifecycle from draft to confirmed.
- **Invoice** — a user-generated request for an incoming payment.
- **SweepPolicy** — a rule that moves value automatically from one Holding to another under specified conditions.

## Core entities

### Holding (abstract)

The primary organizational unit. Every Holding shares the following base shape; concrete subtypes add their own fields.

```python
@dataclass
class Holding(ABC):
    id: UUID
    name: str                           # user-chosen, e.g. "Daily spending", "Cold reserve"
    description: str | None
    purpose: Purpose
    declared_security: SecurityClaim    # what the user says this Holding is
    display_color: str                  # UI hint, hex
    display_order: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
```

```python
class Purpose(Enum):
    SPENDING = "spending"               # day-to-day outflows
    RESERVE = "reserve"                 # medium-term hold
    LONG_TERM = "long_term"             # multi-year, retirement-style
    TRANSIT = "transit"                 # in motion, e.g. funds on a custodial provider
    UNDECLARED = "undeclared"           # default when user has not tagged
```

```python
@dataclass
class SecurityClaim:
    """
    What the user declares about how this Holding is protected.
    Free-form claim; the analyzer separately determines observable security
    and surfaces discrepancies.
    """
    custody_model: CustodyModel
    signing_model: SigningModel
    geographic_distribution: bool       # are keys in multiple physical locations?
    inheritance_configured: bool        # is there a recovery path for heirs?
    notes: str | None

class CustodyModel(Enum):
    THIRD_PARTY = "third_party"         # Account: someone else holds keys
    SELF_SINGLE = "self_single"         # one person holds keys
    SELF_MULTISIG = "self_multisig"     # multiple keys, may include co-signers

class SigningModel(Enum):
    NOT_APPLICABLE = "not_applicable"   # for Account
    SOFTWARE_HOT = "software_hot"       # connected device, software wallet
    HARDWARE_OFFLINE = "hardware_offline"  # hardware wallet
    AIRGAPPED = "airgapped"             # fully offline computer
    CEREMONIAL = "ceremonial"           # multisig with co-signers, geographic dispersion
```

The four concrete subtypes:

```python
@dataclass
class Account(Holding):
    custodial_provider_id: UUID         # exactly one CustodialProvider
    # No descriptors. Balance is read from the provider's API.

@dataclass
class Purse(Holding):
    descriptor_ids: list[UUID]          # one or more Descriptors
    purse_mode: PurseMode               # see "Purse mode" below

class PurseMode(Enum):
    WATCH_ONLY             = "watch_only"              # imported xpub/descriptor; seed lives in another hot wallet
    ON_DEVICE_TK_GENERATED = "on_device_tk_generated"  # TallyKeep generated the seed; seed lives in a client device's secure local storage
    ON_DEVICE_USER_IMPORTED = "on_device_user_imported" # user imported a seed from another wallet; same storage mechanic (pending purse-upgrade-path)

@dataclass
class Strongbox(Holding):
    descriptor_ids: list[UUID]
    signing_device_label: str | None    # user note, e.g. "Coldcard Mk4 in safe"

@dataclass
class Vault(Holding):
    descriptor_ids: list[UUID]
    required_signers: int | None        # for multisig, how many keys to spend
    total_signers: int | None
    timelock_blocks: int | None         # if a timelock is part of the setup
    recovery_setup_notes: str | None
```

### Purse mode

`purse_mode` records **what kind of wallet this Purse is** in a way
that is stable across devices and meaningful to all of them. It is
the resolution recorded in ADR-0006 (slug `purse-flavors`). The
split is structural because the spending UX differs materially.

`purse_mode` does **not** record where the seed physically lives.
That is a per-client, runtime concern (see "Signing capability is
per-client" below) — and the locked principle "no signing keys to
backend" forbids the backend from holding a seed reference at all.

- **Watch-only Purse** (`PurseMode.WATCH_ONLY`).
  Onboarded by importing an xpub or descriptor. The seed lives in
  another hot wallet (Phoenix, BlueWallet, Mutiny, Sparrow's hot
  mode, etc.). TallyKeep observes activity and aggregates balances;
  spending always points the user back to the source wallet. Single-
  address import is **not** supported (a wallet's activity rotates
  across many addresses; observing one address shows a misleading
  slice).

- **TallyKeep-generated Purse** (`PurseMode.ON_DEVICE_TK_GENERATED`).
  TallyKeep generated a fresh seed into a client device's secure
  local storage (iOS Keychain / Android Keystore, biometric-gated)
  during the Add-Holding flow. The descriptor (public part) is
  registered with the backend so the chain scanner observes balances;
  the seed itself never crosses to the backend. From the *device that
  generated and holds the seed*, native signing is available
  (biometric prompt, sign in-app, broadcast). From any other device,
  the same Purse appears as view-only with a "go sign on the device
  that holds the seed" gate.

- **User-imported Purse** (`PurseMode.ON_DEVICE_USER_IMPORTED`).
  The user imported a seed from another wallet (pending
  `purse-upgrade-path` iteration). Same on-device storage mechanic as
  `ON_DEVICE_TK_GENERATED`; differs only in disclosure copy and
  security-health framing (user already has a backup from the source
  wallet).

A user may have multiple Purses simultaneously (for example, a
watch-only Purse mirroring their Phoenix balance, plus an
on-device Purse for fresh receipts directly into TallyKeep).

### Signing capability is per-client, not per-Holding

Whether a *given client right now* can sign for a Purse is a runtime
question, not a domain field. The check is local: does this client's
secure-storage backend contain a seed reference keyed by this
Holding's `id`?

- **Capacitor app on the phone where the seed was generated:**
  Keychain/Keystore has the entry. Send is enabled. Biometric prompts
  unlock; signing happens in-app; broadcast goes through the backend.
- **Capacitor app on a different phone** (e.g., a new device, or one
  that hasn't restored from a seed backup yet): no entry. Send shows
  the "go sign on the device that holds the seed" gate.
- **Browser PWA on desktop or mobile:** no Keychain access at all.
  Same gate.
- **Any watch-only Purse, any client:** Send always points
  to the source wallet (Phoenix, BlueWallet, etc.), regardless of
  client. There is no scenario in which TallyKeep signs a
  watch-only Purse.

The "Create a TallyKeep wallet" affordance during Add-Holding is
gated **client-side** based on the client's capability to generate
and securely store a seed. Capacitor on phone: shown. PWA in any
browser: hidden (with a "this requires the TallyKeep app" message).
The backend does not enforce or detect build type; it accepts any
Purse-creation request and stores the asserted `purse_mode`.

This keeps the locked principle clean: the backend never holds
signing material in any form, encrypted or otherwise. The trade-off
is that an attacker calling the API directly could create an
`ON_DEVICE_TK_GENERATED` Purse for which no client actually
holds a seed; the result is a Holding nobody can spend from, which
is a UX nuisance, not a security risk.

This model is reflected in the threat model
(`concerns/threat_model.md` §Mobile addendum) and the UX specifications in
`UI/README.md` (Add-Holding, Send, Receive sections).

### Mutability rules

- **Type** (Account vs Purse vs Strongbox vs Vault) is **mutable but requires deliberate confirmation**. A user may migrate a Holding from Purse to Strongbox after moving keys to a hardware wallet. The transition is recorded in an audit log.
- **Purpose** is **freely mutable**. Just a tag.
- **declared_security** is **freely mutable**. Just a claim.
- **observable_security** (computed by the analyzer) is **never user-editable**. It is a function of the underlying Descriptors and on-chain reality.

### Invariants

- Account has no Descriptors and exactly one CustodialProvider.
- Purse, Strongbox, and Vault have at least one Descriptor and no CustodialProvider.
- Vault may have multisig parameters (`required_signers`, `total_signers`); Purse and Strongbox should not.
- Holdings are soft-deleted (archived). No hard delete, to preserve LedgerEntry integrity.
- Every Purse has a `purse_mode` value. The field is required at creation and immutable thereafter.
- The backend never stores any reference to the seed itself. For `purse_mode=ON_DEVICE_TK_GENERATED` (or `ON_DEVICE_USER_IMPORTED`), the seed lives only in a client device's secure local storage; the backend has no field, encrypted or otherwise, that points at it.

### Descriptor

The technical primitive backing a non-Account Holding.

```python
@dataclass
class Descriptor:
    id: UUID
    holding_id: UUID
    name: str
    expression: str                     # BIP 380 output descriptor (external chain)
    change_expression: str | None       # BIP 380 output descriptor (internal/change chain)
    network: Network
    address_type: AddressType
    gap_limit: int                      # default 20
    is_watch_only: bool                 # always True (locked principle: app holds no signing keys)
    last_scanned_height: int            # height of last full scan
    created_at: datetime
```

```python
class Network(Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"
    SIGNET = "signet"
    REGTEST = "regtest"

class AddressType(Enum):
    LEGACY = "legacy"                   # P2PKH
    NESTED_SEGWIT = "nested_segwit"     # P2SH-P2WPKH
    NATIVE_SEGWIT = "native_segwit"     # P2WPKH
    TAPROOT = "taproot"                 # P2TR
```

Rules:
- `expression` is canonical input. xpub or similar legacy formats are converted to descriptor form at import.
- `is_watch_only` is always `True` on Descriptors. The app never holds Bitcoin private keys via descriptors. (For TallyKeep-managed Purses, the seed lives in the secure local storage of *whichever client device generated it*, never on the backend — see §"Purse seed origin" and §"Signing capability is per-client" above. Seeds never become Descriptor private keys.)
- A Descriptor belongs to exactly one Holding.

### Address

Individual addresses derived from a Descriptor.

```python
@dataclass
class Address:
    id: UUID
    descriptor_id: UUID
    address: str
    derivation_path: str                # e.g. "m/84'/0'/0'/0/5"
    is_change: bool
    derivation_index: int
    label: str | None                   # user-provided
    first_seen_height: int | None       # None if never used
    is_reused: bool                     # True if received funds in more than one separate batch
    created_at: datetime
```

### UTXO

```python
@dataclass
class UTXO:
    id: UUID
    descriptor_id: UUID
    address_id: UUID
    txid: str
    vout: int
    value_sats: int
    confirmation_height: int | None     # None = unconfirmed
    is_frozen: bool                     # user-locked, excluded from coin selection
    is_spent: bool
    spent_in_txid: str | None
    hygiene_flags: list[HygieneFlag]
    created_at: datetime
```

```python
class HygieneFlag(Enum):
    ADDRESS_REUSED = "address_reused"
    DUST = "dust"                       # below economic spend threshold at current fee
    SUSPECTED_CONSOLIDATION = "suspected_consolidation"
    ROUND_NUMBER = "round_number"       # heuristic privacy leak
```

### CustodialProvider

The technical primitive backing an Account.

```python
@dataclass
class CustodialProvider:
    id: UUID
    provider_kind: ProviderKind         # which third party
    display_name: str                   # user-chosen, e.g. "Kraken main"
    adapter_id: str                     # ccxt id or custom adapter id: "kraken", "bitstamp", "swissquote"
    api_credential_reference: str       # reference into secrets store, never the value
    api_secret_reference: str
    api_passphrase_reference: str | None  # some providers use a third credential
    permissions: ProviderPermissions
    whitelist_address: str              # the only address funds can be withdrawn to
    whitelist_address_descriptor_id: UUID  # the Descriptor that owns the whitelist address
    is_active: bool
    last_polled_at: datetime | None
    last_error: str | None
    last_known_balance_sats: int | None
    created_at: datetime
```

```python
class ProviderKind(Enum):
    EXCHANGE = "exchange"               # Kraken, Bitstamp
    BROKER = "broker"                   # Swissquote
    P2P_VENUE = "p2p_venue"             # future, e.g. RoboSats
```

```python
@dataclass
class ProviderPermissions:
    can_read: bool                      # always True
    can_trade: bool                     # locked invariant: must be False (no order placement)
    can_withdraw: bool
```

Rules:
- The app refuses to register a CustodialProvider whose API credential has trade permissions enabled. The check is done against the provider's API at registration time. This is locked by the "no order placement" principle (see `holdings/01_account.md` §"Regulatory posture (locked)").
- `whitelist_address` must be derivable from a Descriptor whose Holding is **not** an Account (you cannot whitelist to another custodial Account; that would defeat the point).
- The validator strongly recommends the whitelist destination be an offline-signed Holding (Strongbox or Vault); see SweepPolicy section for the sweep-destination rule.

### LedgerEntry

The user-facing record of a value movement. May be backed by different underlying primitives.

```python
@dataclass
class LedgerEntry:
    id: UUID
    direction: Direction
    net_amount_sats: int                # positive for incoming, negative for outgoing
    fee_sats: int | None                # only when known (e.g. on-chain tx)
    timestamp: datetime                 # block time, mempool first-seen, or provider event time
    source: LedgerEntrySource
    source_reference: str               # txid, payment_hash, or provider event id
    category: LedgerCategory | None     # user-set, with optional analyzer suggestion
    counterparty_label: str | None      # user-set, free text
    note: str | None
    suggested_category: LedgerCategory | None  # non-binding analyzer suggestion
    categorized_at: datetime | None
    created_at: datetime
```

```python
class Direction(Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    INTERNAL = "internal"               # between user's own Holdings

class LedgerEntrySource(Enum):
    ONCHAIN_TRANSACTION = "onchain_transaction"
    LIGHTNING_PAYMENT = "lightning_payment"          # populated once the Lightning iteration ships
    CUSTODIAL_EVENT = "custodial_event"              # withdrawal, deposit on a CustodialProvider

class LedgerCategory(Enum):
    # Incoming
    CUSTODIAL_WITHDRAWAL = "custodial_withdrawal"
    P2P_RECEIVE = "p2p_receive"
    SALARY = "salary"
    MERCHANT_RECEIPT = "merchant_receipt"
    # Outgoing
    MERCHANT_PAYMENT = "merchant_payment"
    P2P_SEND = "p2p_send"
    CUSTODIAL_DEPOSIT = "custodial_deposit"
    # Neutral
    INTERNAL_TRANSFER = "internal_transfer"
    CONSOLIDATION = "consolidation"
    # Fallback
    OTHER = "other"
```

Many-to-many link to Holdings, since a single LedgerEntry can affect multiple Holdings simultaneously (an internal transfer between two of the user's own Holdings produces one entry that touches both):

```python
@dataclass
class LedgerEntryHoldingLink:
    ledger_entry_id: UUID
    holding_id: UUID
    holding_amount_sats: int            # net effect on this specific Holding
```

Rules:
- A LedgerEntry with `direction=INTERNAL` must link to at least two user-owned Holdings.
- Categorization is always user-initiated. The app may suggest via `suggested_category` but never auto-applies.
- Backing reference rule: every LedgerEntry must point to exactly one source object identified by `source` plus `source_reference`. The cross-reference table (next entity) makes this navigable.

### OnChainTransaction

The Bitcoin blockchain record. Stored once, may be referenced by zero, one, or many LedgerEntries (e.g. an on-chain tx involving multiple of our Holdings produces one OnChainTransaction and one or more LedgerEntries).

```python
@dataclass
class OnChainTransaction:
    txid: str                           # primary key
    raw_hex: str | None                 # populated when available
    confirmation_height: int | None
    block_time: datetime | None
    first_seen_at: datetime
    fee_sats: int | None
    size_vbytes: int | None
    is_coinjoin_suspected: bool         # heuristic flag
```

### PaymentRequest

The user-initiated outgoing payment.

```python
@dataclass
class PaymentRequest:
    id: UUID
    holding_id: UUID                    # source Holding
    payment_type: PaymentType
    amount_sats: int | None             # None = encoded in destination (e.g. BOLT11)
    description: str | None
    status: PaymentStatus
    expires_at: datetime | None
    psbt_base64: str | None             # on-chain only
    signed_transaction_hex: str | None  # on-chain only
    broadcast_txid: str | None
    resulting_ledger_entry_id: UUID | None  # populated after on-chain confirmation
    created_at: datetime
    updated_at: datetime

    # On-chain destination
    destination_address: str | None
    bip21_uri: str | None

    # Lightning destination (populated once the Lightning iteration ships)
    lightning_invoice: str | None
    lightning_payment_hash: str | None
```

```python
class PaymentType(Enum):
    ONCHAIN = "onchain"
    LIGHTNING = "lightning"             # used once the Lightning iteration ships

class PaymentStatus(Enum):
    DRAFT = "draft"
    AWAITING_SIGNATURE = "awaiting_signature"
    AWAITING_BROADCAST = "awaiting_broadcast"
    BROADCAST = "broadcast"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
```

Rules:
- A PaymentRequest with `holding_id` referencing a Holding that has `declared_security.signing_model == NOT_APPLICABLE` (i.e. an Account) is rejected. Outgoing from an Account uses the SweepPolicy / withdrawal mechanism, not PaymentRequest.
- The validator warns (does not block) for outgoing PaymentRequests from Vaults flagged as long-term, since the user might be unintentionally accessing ceremonial storage.
- The link from `resulting_ledger_entry_id` to a confirmed LedgerEntry is established by the chain scanner when it matches the broadcast txid.

### Invoice

The user-generated request for an incoming payment.

```python
@dataclass
class Invoice:
    id: UUID
    holding_id: UUID                    # destination Holding
    invoice_type: PaymentType           # ONCHAIN or LIGHTNING (LIGHTNING used once the Lightning iteration ships)
    amount_sats: int | None             # None = amountless
    description: str | None
    status: InvoiceStatus

    # On-chain
    receiving_address: str | None
    receiving_address_id: UUID | None
    bip21_uri: str | None

    # Lightning (populated once the Lightning iteration ships)
    bolt11: str | None
    payment_hash: str | None

    resulting_ledger_entry_id: UUID | None  # populated when payment is detected
    expires_at: datetime | None
    created_at: datetime
```

```python
class InvoiceStatus(Enum):
    OPEN = "open"
    PAID = "paid"
    OVERPAID = "overpaid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
```

### SweepPolicy

Generalized: applies between any two Holdings, not just custodial-to-cold.

```python
@dataclass
class SweepPolicy:
    id: UUID
    name: str                           # user-chosen, e.g. "Sweep Kraken to Strongbox weekly"
    source_holding_id: UUID
    destination_holding_id: UUID
    is_enabled: bool
    trigger_type: SweepTriggerType
    trigger_configuration: dict         # shape depends on trigger_type
    minimum_balance_sats: int           # leave this much on the source
    maximum_per_period_sats: int | None # safety cap
    requires_user_confirmation: bool    # if True, sweep creates a confirmation prompt
    is_dry_run: bool                    # if True, evaluate and persist sweep_execution rows but do not dispatch
    safety_warnings: list[SafetyWarning]  # set by the policy validator
    last_executed_at: datetime | None
    last_result_summary: dict | None
    created_at: datetime
    updated_at: datetime
```

```python
class SweepTriggerType(Enum):
    SCHEDULED = "scheduled"             # cron-like
    THRESHOLD = "threshold"             # when balance crosses a value
    MANUAL = "manual"                   # only on user request
```

```python
@dataclass
class ScheduledTriggerConfiguration:
    cron_expression: str
    timezone: str                       # IANA timezone

@dataclass
class ThresholdTriggerConfiguration:
    threshold_sats: int
    cooldown_hours: int                 # avoid flapping
```

```python
class SafetyWarningKind(Enum):
    DESTINATION_KEYS_ON_HOST = "destination_keys_on_host"
    DESTINATION_IS_CUSTODIAL = "destination_is_custodial"
    SOURCE_AND_DESTINATION_SAME_SECURITY_TIER = "same_security_tier"
    NO_MAXIMUM_CAP_SET = "no_maximum_cap_set"
    UNVERIFIED_WHITELIST_ON_PROVIDER = "unverified_whitelist_on_provider"

@dataclass
class SafetyWarning:
    kind: SafetyWarningKind
    severity: str                       # "low", "medium", "high"
    message: str                        # user-facing explanation
    user_acknowledged: bool             # True after explicit acknowledgement
```

The policy validator runs at policy creation and modification, computes warnings, and stores them on the policy. Warnings do **not** block; they require user acknowledgement before the policy can be enabled. The user can override any warning by acknowledging it.

Validator rules (warn, do not block):
- If destination Holding is a Purse (keys on host or connected device), warn `DESTINATION_KEYS_ON_HOST` — sweep into something an attacker on the same host could drain.
- If destination Holding is an Account, warn `DESTINATION_IS_CUSTODIAL` — moving from one custodian to another defeats minimum-exposure.
- If source and destination have the same `signing_model`, warn `SAME_SECURITY_TIER` — this is unusual and may indicate the user did not understand the model.
- If `maximum_per_period_sats` is None, warn `NO_MAXIMUM_CAP_SET` for any policy moving more than a small amount.
- For Account sources, if the CustodialProvider's `whitelist_address` could not be programmatically verified on the provider side, warn `UNVERIFIED_WHITELIST_ON_PROVIDER`.

The user can explicitly acknowledge each warning. The policy stores the acknowledgement state and the validator does not re-warn for the same configuration.

### SweepExecution

Audit trail; one row per sweep attempt. This is the persist-first half of the persist-first-emit-second pattern.

```python
@dataclass
class SweepExecution:
    id: UUID
    sweep_policy_id: UUID
    triggered_at: datetime
    trigger_source: SweepTriggerType    # what fired this
    pre_balance_sats: int               # source balance at trigger
    intended_amount_sats: int
    status: SweepExecutionStatus
    provider_withdrawal_id: str | None  # for Account sources
    expected_txid: str | None
    confirmed_txid: str | None
    error_message: str | None
    completed_at: datetime | None
```

```python
class SweepExecutionStatus(Enum):
    REQUESTED = "requested"
    AWAITING_USER_CONFIRMATION = "awaiting_user_confirmation"
    DISPATCHED = "dispatched"           # provider acknowledged the request
    ONCHAIN_PENDING = "onchain_pending" # tx broadcast, awaiting confirmation
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Job

For asynchronous operations.

```python
@dataclass
class Job:
    id: UUID
    job_type: str                       # "custodial_poll" | "sweep" | "blockchain_scan" | ...
    status: JobStatus
    parameters: dict
    result: dict | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
```

```python
class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### UserProfile

Singleton per installation.

```python
@dataclass
class UserProfile:
    id: UUID                            # always the same singleton id
    feature_flags: dict[str, bool]      # see concerns/feature_flags.md
    base_currency: str                  # display only
    locale: str
    created_at: datetime
    updated_at: datetime
```

There is **no** preset / tier / named-identity concept on
`UserProfile`. Initial flag values are seeded by onboarding answers
(see `09_feature_flags.md`); after onboarding the user toggles
individual flags from Settings. The configuration is just the
configuration.

### Declared vs observable security

The analyzer (`concerns/observation.md`) computes an `ObservableSecurity` record per Holding from the on-chain reality and the configured Descriptors. This is **not** a stored field on Holding; it is a derived view, recomputed on demand.

```python
@dataclass
class ObservableSecurity:
    holding_id: UUID
    inferred_custody_model: CustodyModel
    inferred_signing_model: SigningModel
    inferred_multisig_parameters: tuple[int, int] | None  # (required, total) if applicable
    inferred_timelock_blocks: int | None
    last_computed_at: datetime
```

When the user views a Holding, the UI compares `declared_security` and `observable_security`. Discrepancies are surfaced as `analysis.discrepancy.detected` events and shown prominently. Examples:

- Declared as Vault with multisig, but Descriptor is single-key → loud warning.
- Declared as Strongbox (HARDWARE_OFFLINE), but recent transactions show signing patterns suggesting hot software signing → medium warning.
- Declared as Vault with timelock, but Descriptor has no Miniscript `older()` / `after()` fragment → medium warning.

The analyzer never modifies declared values automatically. It only surfaces observations.

## Relationships (summary)

```
UserProfile (singleton)

Holding (abstract)
├── Account ──────── CustodialProvider (1-to-1)
├── Purse ────────── Descriptor (1-to-many)
├── Strongbox ────── Descriptor (1-to-many)
└── Vault ────────── Descriptor (1-to-many)

Descriptor 1──* Address 1──* UTXO
                              │
                              └── HygieneFlag[]

LedgerEntry *──* Holding (via LedgerEntryHoldingLink)
LedgerEntry  ──→ OnChainTransaction (or LightningPayment, or CustodialEvent)

PaymentRequest 1──0..1 LedgerEntry  (resulting_ledger_entry_id)
Invoice 1──0..1 LedgerEntry         (resulting_ledger_entry_id)

SweepPolicy ── source_holding_id → Holding
            └─ destination_holding_id → Holding

SweepExecution *──1 SweepPolicy

Job (standalone, linked to whatever triggered it via parameters)
```

## Invariants summarized

1. Account has a CustodialProvider, no Descriptors.
2. Purse, Strongbox, Vault have at least one Descriptor, no CustodialProvider.
3. A LedgerEntry with `direction=INTERNAL` must link to at least two user-owned Holdings.
4. A SweepPolicy's source and destination must both be active Holdings.
5. A SweepPolicy's safety warnings must all be acknowledged before the policy can be enabled.
6. A CustodialProvider cannot be registered with `permissions.can_trade=True` (locked: no order placement).
7. The whitelist address of a CustodialProvider must be owned by a non-Account Holding.
8. No domain entity exposes a private key, seed, or signing material in any field. The type system forbids it.
9. PaymentRequest from a Holding whose `signing_model == NOT_APPLICABLE` is rejected at construction.
10. A Purse's `purse_mode` is immutable after creation. Migrating between modes requires creating a new Purse and moving funds; the original is archived.
11. The backend never validates client build type. The "create a TallyKeep wallet" affordance is gated client-side on the client's capability to generate and securely store a seed. The backend accepts any Purse-creation request that satisfies the schema.
