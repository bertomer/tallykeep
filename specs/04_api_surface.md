# 04 — API Surface (Internal, v1)

All endpoints are under `/api/v1/`. The frontend is the only client in v1, but the contract is designed as if an external caller would use it later.

## Conventions

- **Authentication**: none in v1. Localhost binding is the security boundary.
- **Format**: JSON in, JSON out. UTF-8. Content-Type required.
- **Errors**: RFC 7807 Problem Details format.
  ```json
  { "type": "/errors/invalid-descriptor", "title": "...", "status": 400, "detail": "...", "instance": "..." }
  ```
- **Pagination**: `?limit=N&cursor=...` on list endpoints. Default limit 50, maximum 200. Response includes `next_cursor` when more results exist.
- **Timestamps**: ISO 8601 UTC, e.g. `2026-04-27T14:30:00Z`.
- **Amounts**: integer satoshis. Field name always suffixed `_sats`.
- **Idempotency**: mutating endpoints accept an optional `Idempotency-Key` header.
- **Versioning**: URI-versioned (`/api/v1/`). Breaking changes go to `/api/v2/`.

## Locked-state behavior

When `SECRETS_BACKEND=encrypted_database` and the app is not unlocked, every endpoint except `/api/v1/unlock` and `/api/v1/health` returns `423 Locked`.

```
POST /api/v1/unlock
  body: { "passphrase": "..." }
  200  : { "unlocked": true }
  401  : bad passphrase
  503  : crypto parameters not initialized (first-run)

POST /api/v1/unlock/initialize
  Used only on first run.
  body: { "passphrase": "..." }
  200  : { "initialized": true, "unlocked": true }
  409  : already initialized
```

## Health

```
GET /api/v1/health
  200 : {
    "status": "ok" | "degraded",
    "checks": {
      "database":   { "ok": true },
      "bitcoind":   { "ok": true, "height": 832501, "mempool_size": 4213 },
      "redis":      { "ok": true },
      "event_bus":  { "ok": true },
      "unlocked":   true
    }
  }
```

## Profile and configuration

```
GET   /api/v1/profile
  200 : UserProfile

PATCH /api/v1/profile
  body: { "preset"?: ..., "feature_flags"?: {...}, "base_currency"?: "EUR", "locale"?: "en" }
  200 : UserProfile

GET   /api/v1/feature-flags
  200 : { flag_name: bool, ... }   # resolved flags (preset + overrides)

GET   /api/v1/configuration
  200 : { "bitcoind": {...}, "fee_estimation": {...}, ... }

PATCH /api/v1/configuration
  body: partial configuration
  200 : updated configuration
```

## Holdings

The API distinguishes the abstract `/holdings` collection (cross-type queries, summaries) from the type-specific creation endpoints. Each Holding type has its own creation flow because the required fields differ.

### Cross-type endpoints

```
GET    /api/v1/holdings
  Filters: ?holding_type=&purpose=&include_archived=
  200 : [Holding, ...]

GET    /api/v1/holdings/{id}
  200 : Holding (full, including computed fields like balance and observable_security)

PATCH  /api/v1/holdings/{id}
  body: { "name"?, "description"?, "purpose"?, "declared_security"?, "display_color"?, "display_order"? }
  200 : Holding

POST   /api/v1/holdings/{id}/archive
  204

POST   /api/v1/holdings/{id}/change-type
  body: { "new_type": "strongbox", "reason": "Migrated keys to Coldcard" }
  200 : Holding (now with the new type)
  Validation: target type must be compatible with the current Descriptors (e.g. cannot change Account → Purse without first attaching Descriptors)

GET    /api/v1/holdings/{id}/summary
  200 : {
    "holding": Holding,
    "total_balance_sats": 50000000,
    "confirmed_sats": 49000000,
    "unconfirmed_sats": 1000000,
    "descriptor_count": 2,
    "utxo_count": 14,
    "observable_security": ObservableSecurity,
    "discrepancies": [Discrepancy, ...]
  }

GET    /api/v1/holdings/summary/global
  200 : {
    "holdings": [HoldingSummary, ...],
    "total_sats": 52387100,
    "by_type": { "account": 1905000, "purse": 482100, "strongbox": 30000000, "vault": 20000000 },
    "by_purpose": { "spending": ..., "reserve": ..., "long_term": ..., "transit": ... }
  }
```

### Per-type creation

```
POST /api/v1/holdings/account
  body: {
    "name": "Kraken main",
    "description": "...",
    "purpose": "transit",
    "display_color": "#1e40af",
    "declared_security": { "custody_model": "third_party", "signing_model": "not_applicable", ... },
    "custodial_provider": {
      "provider_kind": "exchange",
      "adapter_id": "kraken",
      "api_credential": "...",
      "api_secret": "...",
      "api_passphrase": null,
      "whitelist_address": "bc1q...",
      "whitelist_address_descriptor_id": "..."
    }
  }
  201 : Holding (Account subtype)
  Validation: API credential must lack trade permissions. Whitelist descriptor must belong to a non-Account Holding.

POST /api/v1/holdings/purse
  body: {
    "name": "Daily phone wallet",
    "purpose": "spending",
    "display_color": "#10b981",
    "declared_security": { "custody_model": "self_single", "signing_model": "software_hot", ... },
    "descriptors": [
      { "name": "main", "expression": "wpkh([abc/84'/0'/0']xpub.../0/*)", "change_expression": "wpkh([abc/84'/0'/0']xpub.../1/*)", "network": "mainnet", "address_type": "native_segwit", "gap_limit": 20 }
    ]
  }
  201 : Holding (Purse subtype)

POST /api/v1/holdings/strongbox
  body: {
    "name": "Cold reserve",
    "purpose": "reserve",
    "declared_security": { "custody_model": "self_single", "signing_model": "hardware_offline", ... },
    "signing_device_label": "Coldcard Mk4 in safe",
    "descriptors": [...]
  }
  201 : Holding (Strongbox subtype)

POST /api/v1/holdings/vault
  body: {
    "name": "Long-term holdings",
    "purpose": "long_term",
    "declared_security": { "custody_model": "self_multisig", "signing_model": "ceremonial", ... },
    "required_signers": 2,
    "total_signers": 3,
    "timelock_blocks": null,
    "recovery_setup_notes": "...",
    "descriptors": [...]
  }
  201 : Holding (Vault subtype)
  Validation in v1: only single-signature multisig descriptors are accepted (full multisig descriptor support deferred to v2). The vault metadata fields are stored but the spec admits the descriptor-level enforcement is v2.
```

## Descriptors

```
GET    /api/v1/descriptors                            ?holding_id=
POST   /api/v1/descriptors                            (attach to existing Holding)
GET    /api/v1/descriptors/{id}
PATCH  /api/v1/descriptors/{id}                       (rename, change gap_limit)
DELETE /api/v1/descriptors/{id}                       (only if no UTXOs reference it)

POST   /api/v1/descriptors/{id}/rescan                202 + job_id
GET    /api/v1/descriptors/{id}/addresses             paginated
POST   /api/v1/descriptors/{id}/addresses/next-receiving
  200 : { address, derivation_path, qr_png_url }
GET    /api/v1/descriptors/{id}/utxos                 paginated
GET    /api/v1/descriptors/{id}/balance
```

## Custodial providers

Most Account-related operations are accessible via the parent Holding endpoints. These dedicated endpoints handle provider-specific operations.

```
GET    /api/v1/custodial-providers/supported
  200 : [{ adapter_id, display_name, capabilities, requires_passphrase }]
  Lists what the v1 build supports, with metadata.

GET    /api/v1/custodial-providers/{id}
  200 : CustodialProvider (without secret references resolved)

PATCH  /api/v1/custodial-providers/{id}
  body: { "display_name"?, "is_active"?, "api_credential"?, "api_secret"?, ... }
  Updates rotate credentials; old secrets are immediately purged.

POST   /api/v1/custodial-providers/{id}/refresh        202 + job_id (triggers balance poll)
GET    /api/v1/custodial-providers/{id}/balance        last known balance
GET    /api/v1/custodial-providers/{id}/verify-whitelist
  200 : {
    "verifiable_via_api": true,
    "configured_on_provider": true,
    "configured_address_matches": true
  }
  Fails clearly when the provider does not expose a whitelist API.
```

## Addresses

```
PATCH /api/v1/addresses/{id}
  body: { "label": "Alice payment" }
  200 : Address
```

## UTXOs

```
GET   /api/v1/utxos                                    Filters: ?descriptor_id=&holding_id=&min_value_sats=&frozen=
POST  /api/v1/utxos/{id}/freeze
POST  /api/v1/utxos/{id}/unfreeze
GET   /api/v1/utxos/{id}/hygiene                       per-UTXO hygiene detail
```

## Ledger entries

```
GET   /api/v1/ledger-entries
  Filters: ?holding_id=&direction=&category=&from_date=&to_date=&uncategorized=true
  200 : [LedgerEntry, ...]

GET   /api/v1/ledger-entries/{id}
  200 : LedgerEntry with linked underlying source
        (OnChainTransaction object, or LightningPayment in v1.5, or CustodialEvent)

PATCH /api/v1/ledger-entries/{id}
  body: { "category"?, "counterparty_label"?, "note"? }

GET   /api/v1/ledger-entries/pending-categorization
  200 : convenience: all uncategorized, ordered by recency
```

## Banking — outgoing on-chain payments

```
POST /api/v1/banking/payment-requests
  body: {
    "holding_id": "...",
    "payment_type": "onchain",
    "destination": "bc1q..." | "bitcoin:bc1q...?amount=0.01",
    "amount_sats": 100000,
    "fee_strategy": "economy" | "normal" | "priority" | { "sat_per_vbyte": 25 },
    "description": "Bike purchase"
  }
  201 : PaymentRequest (psbt_base64 set, status=AWAITING_SIGNATURE)
  Validation: source Holding's signing_model must not be NOT_APPLICABLE; otherwise 400.

GET  /api/v1/banking/payment-requests                  ?holding_id=&status=
GET  /api/v1/banking/payment-requests/{id}             includes resulting_ledger_entry if confirmed

GET  /api/v1/banking/payment-requests/{id}/psbt        Returns PSBT base64 or binary via Accept header
GET  /api/v1/banking/payment-requests/{id}/psbt.qr     Returns QR PNG (or animated frames in v1.1)

POST /api/v1/banking/payment-requests/{id}/submit-signed
  body: { "psbt_base64": "..." } | { "signed_transaction_hex": "..." }
  200 : PaymentRequest (status=AWAITING_BROADCAST)

POST /api/v1/banking/payment-requests/{id}/broadcast
  200 : PaymentRequest (status=BROADCAST, with broadcast_txid)

POST /api/v1/banking/payment-requests/{id}/cancel      Only valid before broadcast.

POST /api/v1/banking/fee-estimate
  body: { "holding_id": "...", "amount_sats": 100000, "destination": "bc1q..." }
  200 : {
    "estimates": {
      "economy":  { "sat_per_vbyte": 8,  "estimated_minutes": 60, "fee_sats": 1200 },
      "normal":   { "sat_per_vbyte": 25, "estimated_minutes": 20, "fee_sats": 3750 },
      "priority": { "sat_per_vbyte": 60, "estimated_minutes": 10, "fee_sats": 9000 }
    }
  }
```

## Banking — incoming (invoices)

```
POST /api/v1/banking/invoices
  body: {
    "holding_id": "...",
    "invoice_type": "onchain",
    "amount_sats": 100000,
    "description": "Consulting invoice"
  }
  201 : {
    "id": "...",
    "receiving_address": "bc1q...",
    "bip21_uri": "bitcoin:bc1q...?amount=0.001&label=...",
    "qr_png_url": "/api/v1/banking/invoices/{id}/qr",
    "status": "open"
  }

GET  /api/v1/banking/invoices/{id}                     includes resulting_ledger_entry if paid
GET  /api/v1/banking/invoices/{id}/qr                  PNG
GET  /api/v1/banking/invoices                          ?holding_id=&status=
POST /api/v1/banking/invoices/{id}/cancel
```

## Trading — sweep policies

Generalized: any Holding to any Holding.

```
GET    /api/v1/sweep-policies                          ?source_holding_id=&enabled=
POST   /api/v1/sweep-policies
  body: {
    "name": "Sweep Kraken weekly",
    "source_holding_id": "...",
    "destination_holding_id": "...",
    "trigger_type": "scheduled",
    "trigger_configuration": { "cron_expression": "0 3 * * FRI", "timezone": "Europe/Zurich" },
    "minimum_balance_sats": 0,
    "maximum_per_period_sats": 100000000,
    "requires_user_confirmation": true
  }
  201 : SweepPolicy (with safety_warnings populated by validator)
  Note: is_enabled defaults to false. The policy must have all warnings acknowledged before being enabled.

GET    /api/v1/sweep-policies/{id}
PATCH  /api/v1/sweep-policies/{id}                     re-runs validator on change
DELETE /api/v1/sweep-policies/{id}

POST   /api/v1/sweep-policies/{id}/acknowledge-warnings
  body: { "warning_kinds": ["destination_keys_on_host", "no_maximum_cap_set"] }
  200 : SweepPolicy

POST   /api/v1/sweep-policies/{id}/enable              Fails if unacknowledged warnings remain.
POST   /api/v1/sweep-policies/{id}/disable

POST   /api/v1/sweep-policies/{id}/execute-now         202 + job_id (manual trigger)

GET    /api/v1/sweep-policies/{id}/executions          paginated history of attempts

POST   /api/v1/sweep-policies/pause-all                global kill switch
POST   /api/v1/sweep-policies/resume-all
```

## Sweep executions

```
GET /api/v1/sweep-executions                           Filters: ?sweep_policy_id=&status=
GET /api/v1/sweep-executions/{id}
POST /api/v1/sweep-executions/{id}/confirm
  Used when requires_user_confirmation=true and execution is awaiting approval.
  body: { "approved": true | false }
```

## Security analysis

```
GET /api/v1/analysis/holding/{id}/security
  200 : {
    "declared": SecurityClaim,
    "observable": ObservableSecurity,
    "discrepancies": [
      { "kind": "claimed_multisig_but_single_key",
        "severity": "high",
        "message": "This Holding is declared as a Vault with multisig, but its descriptor is single-key.",
        "first_detected_at": "..."
      }
    ]
  }

GET /api/v1/analysis/holding/{id}/blueprint
  200 : {
    "summary": {
      "address_reuse_count": 3,
      "dust_utxo_count": 7,
      "round_number_outputs": 2,
      "suspected_consolidations": 1
    },
    "recommendations": [Recommendation, ...]
  }

GET /api/v1/analysis/utxo/{id}
  200 : per-UTXO blueprint detail

POST /api/v1/analysis/recompute
  body: { "holding_id": "..." | null }
  202 + job_id (trigger fresh recomputation)
```

## Jobs

```
GET    /api/v1/jobs                                    ?status=&job_type=
GET    /api/v1/jobs/{id}
DELETE /api/v1/jobs/{id}                               cancel if queued or running
```

## Server-Sent Events stream

The single live-update channel for the frontend. Replaces polling for fresh data.

```
GET /api/v1/events/stream
  Query: ?topics=chain.*,holding.*,banking.*,trading.*,ledger_entry.*,analysis.*,system.*
         (default: all topics)
  Response: text/event-stream

  Each event arrives as:
    event: <topic>
    data: { "topic": "...", "payload": {...}, "timestamp": "..." }
```

The frontend opens this stream once on app load and keeps it open. The backend forwards bus events through this stream, filtered by the requested topic patterns. Backpressure is handled by buffering up to N events per client and dropping the oldest if a client falls behind.

The stream is the **only** way the frontend receives live updates. There are no polling fallbacks for live data; if the stream disconnects, the frontend re-subscribes and refetches state via the regular GET endpoints.

## Export

```
GET /api/v1/export/configuration
  200 : application/json
        {
          "version": "1.0",
          "exported_at": "...",
          "profile": {...},
          "holdings": [...],            // includes declared security, no secrets
          "descriptors": [...],         // expressions only
          "custodial_providers": [...], // metadata only, no API credentials
          "labels": {...},
          "categorizations": {...},
          "sweep_policies": [...]
        }
```

Secrets are never in this export. The user separately exports those (or remembers them out-of-band).

## Rate limits

None enforced internally in v1 (single user). External custodial provider APIs are rate-limited by the worker via ccxt's built-in throttling. bitcoind RPC is rate-limited by the node's configuration.

## OpenAPI specification

FastAPI auto-generates `/openapi.json`. The frontend consumes it via a typed TypeScript client (e.g. `openapi-typescript`). This keeps the frontend and backend in sync and catches contract drift at build time.
