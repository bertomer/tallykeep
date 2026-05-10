# 11 — User Experience Flows

This module specifies the key user flows as screen-by-screen expectations. Not pixel-perfect mockups — the frontend implementation owns those — but sequence, state transitions, and must-have elements.

## Navigation

Top-level navigation (desktop sidebar; mobile bottom bar):

| Nav item | Visible when |
|---|---|
| **Home** | always |
| **Holdings** | always |
| **Send** | always |
| **Receive** | always |
| **Trading** | `trading.enabled` |
| **Blueprint** | `analysis.blueprint.shown` |
| **Settings** | always |
| **Advanced** | `advanced.api_docs_link` |

Mobile collapses these into a hamburger menu plus floating Send and Receive action buttons.

## Onboarding (first launch)

```
[Welcome]
  "BTC self-hosted banking, savings, and trading.
   No accounts. No custody. Your keys, your coins."
  [ Let's set up → ]

[Cryptography setup — Docker mode only]
  "Choose a passphrase to encrypt local secrets.
   This passphrase will be required every time the app starts.
   It is never stored or transmitted."
  [ Passphrase: _____________ ]
  [ Confirm:    _____________ ]
  Strength: [strong]
  [ Initialize ]

[Profile selection]
  [ Beginner | Intermediate (default) | Sovereign ]
  "You can change this anytime."
  [ Continue ]

[Node connection]
  "Bitcoin node connection:"
  [ RPC host: localhost ]
  [ RPC port: 8332      ]
  [ RPC user: _________ ]
  [ RPC pass: _________ ]
  [ ZMQ block endpoint: tcp://localhost:28332 ]
  [ ZMQ tx endpoint:    tcp://localhost:28333 ]
  [ Test connection ] → ✅ Connected to mainnet, height 832501
                     → ✅ ZeroMQ subscriptions OK
  [ Continue ]

  If ZMQ is not reachable:
  ⚠ ZMQ not configured on bitcoind.
   Add these lines to your bitcoin.conf and restart bitcoind:
     zmqpubrawblock=tcp://127.0.0.1:28332
     zmqpubrawtx=tcp://127.0.0.1:28333
   [ I've done this — retest ]

[Add your first Holding]
  "What kind of Holding do you want to add?"
  
  [Account]    Funds at a custodial provider (Kraken, Bitstamp...).
               They hold the keys.
  [Purse]      Wallet on a connected day-to-day device.
               You hold the keys; signing is light.
  [Strongbox]  Wallet on a hardware or airgapped signer.        (Intermediate+)
               You hold the keys; signing requires the device.
  [Vault]      Wallet under multisig, timelock, or geographic   (Intermediate+)
               separation. Ceremonial access.

  [Skip for now]

[Per-type wizard runs — see flows below]

[Home]
```

## Adding a Holding — per-type wizards

### Adding an Account

```
[Add Account]
  Provider:  [ Kraken ▼ ]   (only providers in trading.enabled list)

  Before continuing:
  1. On Kraken, create an API key with ONLY "Query Funds" and
     "Withdraw Funds" enabled. Do NOT enable trade or staking.
  2. Configure a withdrawal whitelist on Kraken for your cold
     address. We will verify this when possible.

  [ I understand ]

  Display name:    [ Kraken main         ]
  Purpose:         [ Transit ▼           ]   (auto-selected; can change)

  API key:         [ ___________________ ]
  API secret:      [ ___________________ ]

  Whitelist target Holding:
    [ Cold reserve / Strongbox (bc1q...r3x5z) ▼ ]
    (only Strongbox and Vault Holdings shown by default)

  [ Verify & Save ]

[Verification]
  Checking API permissions...      ✅ Read OK, trade DISABLED
  Verifying whitelist on Kraken... ✅ bc1q...r3x5z is whitelisted
  Fetching balance...              ✅ 0.01905000 BTC

  ✅ Account "Kraken main" added.
  [ Configure auto-sweep now ]   [ Done ]
```

If verification cannot complete:
```
  ⚠ Could not verify whitelist on Kraken's side.
   Please confirm you have manually configured a withdrawal-address
   whitelist on Kraken for: bc1q...r3x5z

   [ I have done this — proceed ]   [ Cancel ]
```

### Adding a Purse

```
[Add Purse]
  Display name:    [ Daily phone wallet ]
  Purpose:         [ Spending ▼         ]

  How are the keys held?
    [ ● Software wallet on this or a connected device ]
    [ ○ Other (describe in notes)                     ]
  
  Notes (optional): [ ______________________________ ]

  Wallet descriptor or xpub:
    [ wpkh([abc/84'/0'/0']xpub.../0/*)                    ]
    [ Paste or scan                                       ]

  Change descriptor (optional, separate path):
    [                                                     ]

  Network:        [ Mainnet ▼ ]
  Address type:   [ Native SegWit ▼ ]
  Gap limit:      [ 20 ]

  [ Scan & Add ]

[Scanning]
  (progress bar via SSE)
  ✅ Found 12 transactions, current balance: 0.00482100 BTC

  Security check:
  ✅ Declared "software, single-sig"; observed matches.

  [ Done ]
```

### Adding a Strongbox

Similar to Purse, but the "How are the keys held?" prompt offers:
- Hardware wallet (specify model)
- Airgapped computer
- Other / describe

The user can label the signing device (`signing_device_label`).

The descriptor input often comes pre-formatted from the hardware wallet's setup tool (Sparrow, Coldcard's CCFile export, Jade's QR export). The wizard accepts these directly.

### Adding a Vault

```
[Add Vault]
  Display name:    [ Long-term holdings ]
  Purpose:         [ Long-term ▼        ]

  Vault structure:
    [ Required signers (e.g. 2): _____ ]
    [ Total signers   (e.g. 3): _____ ]
    [ Timelock blocks (optional): _____ ]
    [ Recovery setup notes:           ]
    [                                  ]

  Descriptor:
    [                                  ]
    Paste the multisig descriptor produced by your coordination tool.
    (v1: only single-key descriptors accepted; multisig support v2)

  ⚠ v1 limitation:
   In this version, the descriptor must be single-key. Vault metadata
   (multisig parameters, timelock) is stored but the analyzer will
   surface a discrepancy because the on-chain reality is single-key.
   Multisig descriptor support arrives in v2.

  [ Acknowledge & Add ]
```

This honest disclosure is part of the v1 product: we explicitly tell the user we are not yet implementing the full Vault model. The analyzer's discrepancy detection is the bridge.

## Home screen

```
┌────────────────────────────────────────────────────────────┐
│  Total: 0.52387100 BTC                                     │
│  ────────────────────────────────────                      │
│  Account     Kraken main           0.01905000 BTC  ●       │
│              (last seen 3m ago)                            │
│  Purse       Daily phone wallet    0.00482100 BTC  ●       │
│  Strongbox   Cold reserve          0.30000000 BTC  ●       │
│  Vault       Long-term holdings    0.20000000 BTC  ●       │
│                                                            │
│  [Send]  [Receive]                                         │
│                                                            │
│  Pending categorization (2)                                │
│  ────────────────────────────────────                      │
│   ↓ 0.00150000 BTC, 2 hours ago, Cold reserve              │
│     Suggestion: Custodial withdrawal                       │
│     [Categorize]                                           │
│   ↓ 0.00050000 BTC, 1 day ago, Daily phone wallet          │
│     [Categorize]                                           │
│                                                            │
│  Recent confirmed                                          │
│   ↓ 0.00150000 BTC  Kraken withdrawal     3d ago           │
│   ↑ 0.00200000 BTC  Bike shop             5d ago           │
│                                                            │
│  Security checks: ✅ All Holdings consistent.              │
│                                                            │
│  [View all →]                                              │
└────────────────────────────────────────────────────────────┘
```

If the security checks reveal discrepancies, the panel turns yellow or red and lists them.

## Send (on-chain)

### Step 1 — Compose

```
[Send]

From:     [ Daily phone wallet (Purse) ▼ ]
          Balance: 0.00482100 BTC

To:       [ Paste address or BIP21 URI...  ]
          [Scan QR]

Amount:   [ 0.00200000 ] BTC   [ Max ]

Speed:    [ ● Standard – Economy  (≈1h, 1200 sats)  ]
          [ ○ Standard – Normal   (≈20m, 3750 sats) ]
          [ ○ Standard – Priority (≈10m, 9000 sats) ]
          [ ○ Instant (Lightning) — coming v1.5     ]

Description: [ Bike purchase ]

[Review →]
```

If the source is a Vault and `banking.vault_outgoing_warns` is on:

```
⚠ You are about to send from a Vault marked Long-term.
 This is unusual. Vaults are designed for ceremonial access.
 Confirm you intend this.
 [ Yes, I intend this ]   [ Cancel ]
```

### Step 2 — Review

```
[Review]

From:     Daily phone wallet (Purse)
To:       bc1q...r3x5z
                ^^^^^   (highlighted)
Amount:   0.00200000 BTC
Fee:      0.00001200 BTC   (8 sat/vB, ≈1h)
Total:    0.00201200 BTC

ⓘ Verify the destination on your signing device before confirming.

[← Back]                              [Prepare PSBT →]
```

### Step 3 — Sign externally

```
[Sign this transaction]

Transfer the PSBT to your signing device.

[ Download .psbt ]
[ Show QR code ]                (if banking.psbt_qr.enabled)
[ Copy as base64 ]

Once signed, return here:
[ Upload signed .psbt ]
[ Scan signed QR ]
[ Paste signed base64 ]

This request expires in 24h.
```

### Step 4 — Broadcast

```
[Ready to broadcast]

PSBT verified. Transaction is fully signed.

Txid:  a3f5...9c2b
Size:  141 vbytes
Fee:   1200 sats (8 sat/vB)

[Broadcast now]   [Cancel]
```

### Step 5 — Confirmation

```
✅ Broadcast
Txid: a3f5...9c2b   [copy]
Status: 0 confirmations. Notification on confirmation.
```

When confirmed, the LedgerEntry appears in history and the PaymentRequest's `resulting_ledger_entry_id` is populated, so the user can navigate from history back to the original request.

## Receive (on-chain)

```
[Receive]

To Holding: [ Daily phone wallet (Purse) ▼ ]
Amount:     [ 0.00100000 ] BTC   (optional)
Description: [ Consulting invoice ]

[Generate]
```

After generation:

```
┌──────────────────┐
│                  │
│   (QR code)      │
│                  │
└──────────────────┘

Address:  bc1q...r3x5z   [copy]
URI:      bitcoin:bc1q...?amount=0.001   [copy]

Status: Waiting for payment...

[Cancel invoice]
```

When payment lands (SSE push):

```
✅ Payment received
Amount: 0.00100000 BTC
Txid: 7b2c...1f4a
Status: 0/6 confirmations

The Invoice's resulting_ledger_entry_id is now populated;
clicking the entry in history returns to this Invoice's detail.
```

## Categorize a transaction

Entry points: notification banner on Home, Pending Categorization list, direct tap on a LedgerEntry.

```
[Categorize]

Incoming 0.00150000 BTC
Received by: Cold reserve (Strongbox)
At: 2026-04-22 14:30 UTC
From: bc1q... (matches Kraken main's whitelist)

ⓘ Suggestion: Custodial withdrawal
   This transaction came from an address matching one of your
   CustodialProviders. Likely a withdrawal you initiated.

Category:        [ Custodial withdrawal ▼ ]
Counterparty:    [ Kraken main ]
Note:            [ Weekly auto-sweep ]

[Save]
```

## SweepPolicy creation and execution

### Configure a policy

```
[Sweep policy]

Name:   [ Sweep Kraken to Cold reserve weekly ]

From:   [ Kraken main (Account) ▼ ]
To:     [ Cold reserve (Strongbox) ▼ ]

When:   [ Scheduled ▼ ]
        [ Weekly ▼ ] on [ Friday ▼ ] at [ 03:00 ]
        Timezone: [ Europe/Zurich ▼ ]

Leave on source (minimum): [ 0 ] sats
Maximum per day (cap):     [ 100,000,000 ] sats

Confirmation: 
  [ ● Require my confirmation before each sweep ]
  [ ○ Execute automatically                     ]

[Validate & save]
```

If the validator finds warnings, they are shown and must be acknowledged:

```
⚠ Safety check found 1 warning:

  • No maximum cap set
    [Severity: medium]
    A sweep policy without a daily cap could move large amounts
    on a single trigger. Consider setting maximum_per_period_sats.

[ Acknowledge ]   [ Edit policy ]

After acknowledgement: policy can be enabled.
```

### Sweep firing with confirmation required

```
🔔 Sweep ready — Kraken main → Cold reserve
  Move 0.01905000 BTC?
  [Approve]  [Skip this time]  [Review details]
```

Approval triggers execution; status flows through DISPATCHED → ONCHAIN_PENDING → COMPLETED with notifications at each.

## Blueprint analysis

```
[Blueprint — Cold reserve (Strongbox)]

Summary
─────────────────────────────────────
Address reuse:           3 addresses reused
Dust UTXOs:              7 below economic spend
Round-number outputs:    2
Suspected consolidations: 1

Recommendations
─────────────────────────────────────
🟡 Medium — Address reused 4 times
   bc1q...a2x3
   Consider deriving a new receive address for future payments.
   [Details]   [Dismiss for this address]

🔴 High — 7 UTXOs below dust threshold
   Total: 2,340 sats. At current fees (25 sat/vB), spending them
   would cost more than their value.
   [View UTXOs]

🟢 Low — Round-number output
   5,000,000 sats output in tx 7b2c...
   [Dismiss]
```

## Security analysis (declared vs observable)

A panel on every Holding's detail page:

```
[Security check — Long-term holdings (Vault)]

Declared:
  Custody:           Self, multisig
  Signing:           Ceremonial
  Multisig:          2-of-3
  Geographic:        Yes
  Inheritance:       Configured

Observable:
  Custody:           Self, single-key
  Signing:           Unknown
  Multisig:          Not detected
  Timelock:          Not detected

Discrepancies:
🔴 High — Claimed multisig but observable single-key
   This Holding is declared as a Vault with 2-of-3 multisig,
   but the underlying descriptor is single-key. Either the
   declaration is aspirational or the descriptor needs updating.
   
   [Acknowledge — this is intentional]
   [Show me how to fix this]
```

## Settings

A single-page settings view, sectioned:

- **Profile** — preset selector, individual feature flags grouped by category
- **Node** — bitcoind RPC and ZMQ configuration, health status, quick test
- **Security** — (Docker mode) re-enter or change passphrase
- **Backups** — download configuration export (JSON, no secrets)
- **About** — version, build hash, link to project repository

## Notifications

In-app banner at top of screen, dismissible. Triggered by:
- Incoming payment detected
- Outgoing payment confirmed
- Sweep completed or failed
- Sweep awaiting confirmation
- CustodialProvider connection lost or auth failed
- New transaction needs categorization
- Security discrepancy newly detected
- bitcoind disconnected or reconnected

No email, no push, no desktop-notification API in v1. All notifications live in the app and arrive via the SSE stream.

## Error and empty states

| Situation | Handling |
|---|---|
| No Holdings yet | Big CTA "Add your first Holding" |
| No transactions yet | "Waiting for activity on watched addresses" |
| bitcoind offline | Red banner "Bitcoin node unreachable. Check Node settings." Outgoing payments blocked. |
| ZMQ unsubscribed | Yellow banner "Live chain updates unavailable. Falling back to RPC polling." |
| CustodialProvider disconnected | Yellow banner per provider; sweeps skipped with explanation in execution history |
| Database migration pending | Blocking modal "Updating database schema. Please wait..." |
| App locked (Docker mode) | Unlock screen replaces all content |

## Mobile-first considerations

- Send and Receive are primary; floating buttons on the bottom bar.
- QR scanning uses the device camera via the standard Web API (`MediaDevices.getUserMedia`).
- Biometric unlock (Web Authentication API on Android) is a v2 enhancement; v1 uses passphrase prompt for the secrets unlock.
- Install-to-home-screen: PWA manifest must be complete (icons, theme color, `display: standalone`).
- The four Holding type icons are designed to be readable at 24x24 px.
