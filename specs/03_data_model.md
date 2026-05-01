# 03 — Data Model

## Database choice

**PostgreSQL 15 or later** for Docker deployments. SQLite is acceptable for minimal single-user installations but is not the primary target. The schema is compatible with both; we use SQLAlchemy 2.x Core and ORM and avoid Postgres-specific features in v1 except where noted.

## Conventions

- All tables use UUIDv4 primary keys, except where noted (singletons use a fixed UUID; OnChainTransaction uses txid as natural key).
- All timestamps are `TIMESTAMPTZ` in UTC.
- Money values are stored as integer **satoshis** in `BIGINT` columns. Never floating point.
- Soft deletes via `is_archived` flags. No hard deletes for entities that are referenced by historical records.
- All foreign keys use ON DELETE RESTRICT. Cascading deletes would let us lose history.

## Schema

### `user_profile`

Singleton table.

```sql
CREATE TABLE user_profile (
    id UUID PRIMARY KEY CHECK (id = '00000000-0000-0000-0000-000000000001'),
    preset VARCHAR(20) NOT NULL,
    feature_flags JSONB NOT NULL DEFAULT '{}',
    base_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    locale VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `holding`

Single table with discriminator column. The four subtype-specific fields are stored in a JSONB column to avoid sprawling NULL columns; this is acceptable because the count of subtype-specific fields is small and queries are mostly type-aware.

```sql
CREATE TABLE holding (
    id UUID PRIMARY KEY,
    holding_type VARCHAR(20) NOT NULL CHECK (holding_type IN ('account','purse','strongbox','vault')),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    purpose VARCHAR(20) NOT NULL CHECK (purpose IN ('spending','reserve','long_term','transit','undeclared')),

    -- Declared security (user's claim about how this Holding is protected)
    declared_custody_model VARCHAR(30) NOT NULL,
    declared_signing_model VARCHAR(30) NOT NULL,
    declared_geographic_distribution BOOLEAN NOT NULL DEFAULT FALSE,
    declared_inheritance_configured BOOLEAN NOT NULL DEFAULT FALSE,
    declared_security_notes TEXT,

    -- Subtype-specific data
    subtype_data JSONB NOT NULL DEFAULT '{}',
    -- For 'vault': { "required_signers": 2, "total_signers": 3, "timelock_blocks": null, "recovery_setup_notes": "..." }
    -- For 'strongbox': { "signing_device_label": "Coldcard Mk4 in safe" }
    -- For 'account': empty (CustodialProvider link is in custodial_provider table)
    -- For 'purse': empty

    display_color VARCHAR(7) NOT NULL DEFAULT '#000000',
    display_order INTEGER NOT NULL DEFAULT 0,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_holding_type_active ON holding(holding_type) WHERE is_archived = FALSE;
CREATE INDEX idx_holding_purpose ON holding(purpose) WHERE is_archived = FALSE;
```

### `holding_type_change_log`

Audit log for the rare case of changing a Holding's type (e.g. migrating Purse → Strongbox after moving keys to a hardware wallet).

```sql
CREATE TABLE holding_type_change_log (
    id UUID PRIMARY KEY,
    holding_id UUID NOT NULL REFERENCES holding(id),
    previous_type VARCHAR(20) NOT NULL,
    new_type VARCHAR(20) NOT NULL,
    reason TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `descriptor`

```sql
CREATE TABLE descriptor (
    id UUID PRIMARY KEY,
    holding_id UUID NOT NULL REFERENCES holding(id),
    name VARCHAR(100) NOT NULL,
    expression TEXT NOT NULL,
    change_expression TEXT,
    network VARCHAR(10) NOT NULL CHECK (network IN ('mainnet','testnet','signet','regtest')),
    address_type VARCHAR(20) NOT NULL,
    gap_limit INTEGER NOT NULL DEFAULT 20,
    is_watch_only BOOLEAN NOT NULL DEFAULT TRUE CHECK (is_watch_only = TRUE),
    last_scanned_height INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_descriptor_holding ON descriptor(holding_id);
CREATE UNIQUE INDEX idx_descriptor_expression ON descriptor(expression);
```

### `address`

```sql
CREATE TABLE address (
    id UUID PRIMARY KEY,
    descriptor_id UUID NOT NULL REFERENCES descriptor(id),
    address VARCHAR(100) NOT NULL,
    derivation_path VARCHAR(100) NOT NULL,
    is_change BOOLEAN NOT NULL,
    derivation_index INTEGER NOT NULL,
    label TEXT,
    first_seen_height INTEGER,
    is_reused BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_address_descriptor_index ON address(descriptor_id, is_change, derivation_index);
CREATE INDEX idx_address_lookup ON address(address);
```

### `utxo`

```sql
CREATE TABLE utxo (
    id UUID PRIMARY KEY,
    descriptor_id UUID NOT NULL REFERENCES descriptor(id),
    address_id UUID NOT NULL REFERENCES address(id),
    txid VARCHAR(64) NOT NULL,
    vout INTEGER NOT NULL,
    value_sats BIGINT NOT NULL,
    confirmation_height INTEGER,
    is_frozen BOOLEAN NOT NULL DEFAULT FALSE,
    is_spent BOOLEAN NOT NULL DEFAULT FALSE,
    spent_in_txid VARCHAR(64),
    hygiene_flags JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_utxo_outpoint ON utxo(txid, vout);
CREATE INDEX idx_utxo_descriptor_unspent ON utxo(descriptor_id) WHERE is_spent = FALSE;
```

### `custodial_provider`

```sql
CREATE TABLE custodial_provider (
    id UUID PRIMARY KEY,
    holding_id UUID NOT NULL UNIQUE REFERENCES holding(id),
    provider_kind VARCHAR(20) NOT NULL CHECK (provider_kind IN ('exchange','broker','p2p_venue')),
    display_name VARCHAR(100) NOT NULL,
    adapter_id VARCHAR(50) NOT NULL,
    api_credential_reference VARCHAR(200) NOT NULL,
    api_secret_reference VARCHAR(200) NOT NULL,
    api_passphrase_reference VARCHAR(200),
    can_read BOOLEAN NOT NULL DEFAULT TRUE CHECK (can_read = TRUE),
    can_trade BOOLEAN NOT NULL DEFAULT FALSE CHECK (can_trade = FALSE),  -- v1 invariant
    can_withdraw BOOLEAN NOT NULL DEFAULT FALSE,
    whitelist_address VARCHAR(100) NOT NULL,
    whitelist_address_descriptor_id UUID NOT NULL REFERENCES descriptor(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_polled_at TIMESTAMPTZ,
    last_error TEXT,
    last_known_balance_sats BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_custodial_active ON custodial_provider(is_active);
```

### `onchain_transaction`

The blockchain record. Stored once per txid, regardless of how many of our Holdings it touches.

```sql
CREATE TABLE onchain_transaction (
    txid VARCHAR(64) PRIMARY KEY,
    raw_hex TEXT,
    confirmation_height INTEGER,
    block_time TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fee_sats BIGINT,
    size_vbytes INTEGER,
    is_coinjoin_suspected BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_onchain_block_time ON onchain_transaction(block_time DESC);
CREATE INDEX idx_onchain_unconfirmed ON onchain_transaction(txid) WHERE confirmation_height IS NULL;
```

### `ledger_entry`

The user-facing record of a value movement.

```sql
CREATE TABLE ledger_entry (
    id UUID PRIMARY KEY,
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('incoming','outgoing','internal')),
    net_amount_sats BIGINT NOT NULL,
    fee_sats BIGINT,
    timestamp TIMESTAMPTZ NOT NULL,

    source VARCHAR(30) NOT NULL CHECK (source IN ('onchain_transaction','lightning_payment','custodial_event')),
    source_reference VARCHAR(200) NOT NULL,
    -- For onchain_transaction: the txid
    -- For lightning_payment: the payment_hash (v1.5)
    -- For custodial_event: the provider's event id

    category VARCHAR(40),
    counterparty_label TEXT,
    note TEXT,
    suggested_category VARCHAR(40),
    categorized_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ledger_entry_timestamp ON ledger_entry(timestamp DESC);
CREATE INDEX idx_ledger_entry_uncategorized ON ledger_entry(id) WHERE category IS NULL;
CREATE INDEX idx_ledger_entry_source ON ledger_entry(source, source_reference);
```

### `ledger_entry_holding_link`

Many-to-many between LedgerEntry and Holding. A single LedgerEntry can affect multiple Holdings (internal transfer).

```sql
CREATE TABLE ledger_entry_holding_link (
    ledger_entry_id UUID NOT NULL REFERENCES ledger_entry(id),
    holding_id UUID NOT NULL REFERENCES holding(id),
    holding_amount_sats BIGINT NOT NULL,
    PRIMARY KEY (ledger_entry_id, holding_id)
);

CREATE INDEX idx_lehl_holding ON ledger_entry_holding_link(holding_id);
```

### `payment_request`

```sql
CREATE TABLE payment_request (
    id UUID PRIMARY KEY,
    holding_id UUID NOT NULL REFERENCES holding(id),
    payment_type VARCHAR(20) NOT NULL CHECK (payment_type IN ('onchain','lightning')),
    amount_sats BIGINT,
    description TEXT,
    status VARCHAR(30) NOT NULL,
    expires_at TIMESTAMPTZ,

    -- On-chain
    destination_address VARCHAR(100),
    bip21_uri TEXT,
    psbt_base64 TEXT,
    signed_transaction_hex TEXT,
    broadcast_txid VARCHAR(64),

    -- Lightning (v1.5)
    lightning_invoice TEXT,
    lightning_payment_hash VARCHAR(64),

    -- The link to the realized movement, populated when chain scanner matches.
    -- Without this link, reconciling "this payment I composed" with "this transaction in my history" is fragile.
    resulting_ledger_entry_id UUID REFERENCES ledger_entry(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_request_status ON payment_request(status);
CREATE INDEX idx_payment_request_holding ON payment_request(holding_id);
CREATE INDEX idx_payment_request_broadcast_txid ON payment_request(broadcast_txid) WHERE broadcast_txid IS NOT NULL;
```

### `invoice`

```sql
CREATE TABLE invoice (
    id UUID PRIMARY KEY,
    holding_id UUID NOT NULL REFERENCES holding(id),
    invoice_type VARCHAR(20) NOT NULL CHECK (invoice_type IN ('onchain','lightning')),
    amount_sats BIGINT,
    description TEXT,
    status VARCHAR(20) NOT NULL,

    -- On-chain
    receiving_address VARCHAR(100),
    receiving_address_id UUID REFERENCES address(id),
    bip21_uri TEXT,

    -- Lightning (v1.5)
    bolt11 TEXT,
    payment_hash VARCHAR(64),

    -- Same link pattern as payment_request: realized movement reference
    resulting_ledger_entry_id UUID REFERENCES ledger_entry(id),

    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invoice_status ON invoice(status);
CREATE INDEX idx_invoice_holding ON invoice(holding_id);
CREATE INDEX idx_invoice_receiving_address ON invoice(receiving_address) WHERE receiving_address IS NOT NULL;
```

### `sweep_policy`

Generalized: any Holding to any Holding.

```sql
CREATE TABLE sweep_policy (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    source_holding_id UUID NOT NULL REFERENCES holding(id),
    destination_holding_id UUID NOT NULL REFERENCES holding(id),
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    trigger_type VARCHAR(20) NOT NULL CHECK (trigger_type IN ('scheduled','threshold','manual')),
    trigger_configuration JSONB NOT NULL,
    minimum_balance_sats BIGINT NOT NULL DEFAULT 0,
    maximum_per_period_sats BIGINT,
    requires_user_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
    safety_warnings JSONB NOT NULL DEFAULT '[]',
    last_executed_at TIMESTAMPTZ,
    last_result_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (source_holding_id != destination_holding_id)
);

CREATE INDEX idx_sweep_policy_source ON sweep_policy(source_holding_id);
CREATE INDEX idx_sweep_policy_enabled ON sweep_policy(is_enabled) WHERE is_enabled = TRUE;
```

### `sweep_execution`

Audit trail. Persist-first half of the persist-first-emit-second pattern.

```sql
CREATE TABLE sweep_execution (
    id UUID PRIMARY KEY,
    sweep_policy_id UUID NOT NULL REFERENCES sweep_policy(id),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trigger_source VARCHAR(20) NOT NULL,
    pre_balance_sats BIGINT NOT NULL,
    intended_amount_sats BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL,
    provider_withdrawal_id VARCHAR(100),
    expected_txid VARCHAR(64),
    confirmed_txid VARCHAR(64),
    error_message TEXT,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_sweep_execution_policy ON sweep_execution(sweep_policy_id, triggered_at DESC);
CREATE INDEX idx_sweep_execution_pending ON sweep_execution(status) WHERE status NOT IN ('completed','failed','cancelled');
```

### `broadcast_attempt`

Audit trail for transaction broadcasts. Distinct from `payment_request` because a single payment may have multiple broadcast attempts (initial fail, retry, RBF in v1.x).

```sql
CREATE TABLE broadcast_attempt (
    id UUID PRIMARY KEY,
    payment_request_id UUID NOT NULL REFERENCES payment_request(id),
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    transaction_hex TEXT NOT NULL,
    txid VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL,
    rejection_reason TEXT,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_broadcast_attempt_payment_request ON broadcast_attempt(payment_request_id);
```

### `job`

```sql
CREATE TABLE job (
    id UUID PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX idx_job_status_active ON job(status) WHERE status IN ('queued','running');
CREATE INDEX idx_job_type_created ON job(job_type, created_at DESC);
```

### `runtime_configuration`

Key-value store for runtime configuration that changes without app restart. (No abbreviation: full word.)

```sql
CREATE TABLE runtime_configuration (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Example keys:
- `bitcoind.rpc_host`, `bitcoind.rpc_port`, `bitcoind.zmq_block_endpoint`, `bitcoind.zmq_tx_endpoint`
- `fee_estimation.strategy`
- `notifications.enabled`
- `custodial_polling.interval_seconds`
- `analysis.recompute_interval_minutes`

### `event_emission_log`

For the persist-first-emit-second pattern. Whenever a non-losable event is published to the bus, a row is also written here. The audit reconciler subscriber compares this log against acknowledgements and re-emits anything that appears lost.

```sql
CREATE TABLE event_emission_log (
    id UUID PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    emitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_critical BOOLEAN NOT NULL DEFAULT FALSE,  -- if True, the reconciler watches it
    acknowledged_at TIMESTAMPTZ                  -- set when at least one expected subscriber confirmed
);

CREATE INDEX idx_event_critical_unack ON event_emission_log(emitted_at)
  WHERE is_critical = TRUE AND acknowledged_at IS NULL;
```

## Cryptography for secret storage

Two storage backends, selected at deployment.

### Development mode (`SECRETS_BACKEND=keyring`)

Uses the operating system's native keyring via the Python `keyring` library:
- Linux: Secret Service API (libsecret, GNOME Keyring, KWallet)
- macOS: Keychain
- Windows: Credential Manager

`api_credential_reference` in the database is a string like `kraken_main:api_key`. The actual secret value lives in the OS keyring under that key and is retrieved at runtime. Postgres never sees the secret.

### Docker mode (`SECRETS_BACKEND=encrypted_database`)

Secrets are stored in the Postgres database, encrypted at rest. Two cryptographic operations are involved:

**Step 1 — Deriving an encryption key from the user's passphrase.**

The passphrase the user types is not used directly as the encryption key (passphrases are too low-entropy and predictable). Instead, it is run through a key derivation function with a per-installation random salt and tunable cost parameters. The resulting 32-byte key is held in process memory only and discarded on restart.

- KDF: **Argon2id** (current standard; resistant to GPU and ASIC attacks)
- Per-installation salt: 16 random bytes generated at first setup
- Memory cost, time cost, parallelism: stored in the database so they can be tuned upward in future versions without breaking existing deployments
- Output: 32-byte symmetric encryption key

**Step 2 — Encrypting each secret with that derived key.**

Each individual secret (Kraken API key, bitcoind RPC password, future LN macaroon) is encrypted independently with a fresh nonce.

- Algorithm: **AES-256-GCM** (authenticated encryption: encrypts and detects tampering)
- Per-secret nonce: 12 random bytes, fresh for every encryption, stored alongside the ciphertext
- Authentication tag: 16 bytes, produced by GCM, stored alongside the ciphertext

The salt is not secret — it is stored in plaintext alongside the algorithm parameters. The nonce is not secret either. The security comes from the secrecy of the user's passphrase plus the cryptographic strength of Argon2id and AES-256-GCM.

```sql
-- Stored once at app initialization
CREATE TABLE crypto_parameters (
    id UUID PRIMARY KEY CHECK (id = '00000000-0000-0000-0000-000000000001'),
    kdf_algorithm VARCHAR(20) NOT NULL DEFAULT 'argon2id',
    kdf_salt BYTEA NOT NULL,                    -- 16 random bytes, per-installation
    kdf_memory_cost INTEGER NOT NULL DEFAULT 65536,    -- KiB
    kdf_time_cost INTEGER NOT NULL DEFAULT 3,          -- iterations
    kdf_parallelism INTEGER NOT NULL DEFAULT 4,
    encryption_algorithm VARCHAR(20) NOT NULL DEFAULT 'aes-256-gcm',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One row per encrypted secret
CREATE TABLE secret (
    reference VARCHAR(200) PRIMARY KEY,
    ciphertext BYTEA NOT NULL,
    nonce BYTEA NOT NULL,                       -- 12 random bytes, unique per secret
    authentication_tag BYTEA NOT NULL,          -- 16 bytes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### What goes in the secret table

Only third-party access credentials. Specifically:
- Custodial provider API credentials (Kraken, Bitstamp, Swissquote keys and secrets)
- bitcoind RPC password
- Lightning node credentials in v1.5 (macaroon for LND, runefile for CLN, gRPC TLS certs)

### What never goes in the secret table

Bitcoin signing material. Seeds, mnemonics, private keys, xprv. None of it is ever on the host machine in any form, encrypted or otherwise. This is the central security commitment of the app and is enforced by the type system: no domain entity has a field for it.

### Unlock flow

On container startup, the app cannot use any secret until the encryption key is derived from the user's passphrase. The flow:

1. Backend starts; `secret` table contains encrypted values but they cannot be decrypted yet.
2. All endpoints requiring a secret return `423 Locked`.
3. User opens the app, lands on the unlock screen.
4. User submits passphrase to `POST /api/v1/unlock`.
5. Backend reads `crypto_parameters`, runs Argon2id with the stored salt and cost parameters, derives the 32-byte key.
6. Backend attempts to decrypt one canary secret to verify the passphrase is correct. On success, the derived key is held in process memory.
7. App is unlocked; subsequent endpoint calls work normally.

If the backend process dies, the in-memory key dies with it and the user must unlock again. This is intentional.

### Logging redaction

The structured logger has a denylist. Any field name matching `(?i)(key|secret|passphrase|token|cookie|macaroon|api[_-]?credential|api[_-]?secret)` is replaced with `***` before serialization. The denylist is configurable via runtime configuration.

## Migrations

- Alembic is the sole migration tool.
- On container startup, the backend runs `alembic upgrade head` before opening the API port.
- Migrations are reviewed by hand; no auto-generated migrations are committed without manual edit.
- Every schema change has a rollback path (`downgrade()`).
- A destructive migration (drop column, drop table) requires a two-release deprecation cycle: release N marks deprecated and stops writing; release N+1 removes.

## Backup and recovery

### What must be backed up

- The Postgres database (`pg_dump`).
- The OS keyring (in development mode) or the encrypted secret table (in Docker mode, plus the user's passphrase remembered out-of-band).

### What does not need to be backed up

- bitcoind blockchain data (re-syncable).
- Address derivations, UTXO lists, cached balances (rebuildable from descriptors plus the chain).
- Redis (ephemeral event bus and job queue).

### Recovery from total loss

1. Install the app fresh.
2. Restore Holdings by re-entering descriptors (they are not private, no urgency).
3. Re-register custodial providers with API credentials from the user's password manager.
4. Re-sync from chain via bitcoind.
5. User-provided labels and categorizations are lost unless the database was backed up.

The app provides `GET /api/v1/export/configuration` which outputs a JSON file containing all Holdings, Descriptors (expressions only), labels, categorizations, sweep policies, and metadata. Secrets are never in this export. This is the recommended manual backup format for users who do not want to back up the whole Postgres database.
