# Threat Model

## Summary

The app runs on a host machine owned by the user, binds only to localhost, holds no Bitcoin signing material, never places orders, and can withdraw from CustodialProviders only to addresses pre-whitelisted on the provider's side and verified by the app.

**Single-line security property**: *an attacker who fully compromises the host machine can drain operational balances (Account funds via withdrawal-to-whitelisted-only, plus future Lightning balance), and can read the user's complete transaction history, but cannot drain Strongbox or Vault funds.*

## Assets

| Asset | Sensitivity | Where it lives |
|---|---|---|
| Private keys for Strongbox Holdings | Critical | Hardware wallet or airgapped device. Never on the host. |
| Private keys for Vault Holdings | Critical | Multisig co-signers, possibly geographically separated. Never on the host. |
| Private keys for Purse Holdings | High | On the user's connected day-to-day device (phone, laptop). May or may not be on the same host as the app. |
| CustodialProvider API credentials (read + withdrawal-whitelisted) | High | OS keyring (development) or encrypted database (Docker), never plaintext on disk |
| Lightning node credentials (once the Lightning iteration ships: macaroons, runefile, gRPC certs) | Medium-High | Encrypted on the host |
| Descriptors and xpubs | Medium (privacy) | Database on the host |
| LedgerEntries, labels, categorizations | Medium (privacy) | Database on the host |
| SweepPolicy configurations | Low | Database on the host |
| The user's passphrase (Docker mode) | Critical | Held in-memory only after unlock; never persisted |

**Central commitment, restated:** Bitcoin signing material is never on the host machine in any form, encrypted or not. The encrypted secret store holds *third-party access credentials* — Kraken API keys, the bitcoind RPC password, future Lightning node access tokens — but never anything that signs Bitcoin transactions. This is enforced by the type system: no domain entity has a field that could carry signing material.

## Actors

| Actor | Capability | Defended? |
|---|---|---|
| Curious roommate / passerby | Brief physical access to unlocked screen | Yes — sensitive data visible but no irreversible action without external signing device |
| Opportunistic malware (user-level execution) | Read keyring or DB; act through the app's API | Partially — see attack S1 |
| Targeted attacker with root | Full operating-system control | No — out of scope; documented honestly |
| Network attacker on LAN | Sniff packets, MITM | Yes — app is localhost-only, nothing on the wire |
| Network attacker on the internet | Probe externally | Yes — app has no public network surface |
| Malicious CustodialProvider | Lies via API, attempts to seize funds | Partially — see attack S5 |
| Malicious bitcoind | User's own node, but compromised | Out of scope — user owns and controls |
| Compromised dependency | Supply-chain attack on Python or npm package | Partially — pinned versions, manual review; not actively monitored |
| App phishing or clone | Adversary publishes a malicious fork | Out of scope — user must verify they run the genuine release |

## Trust boundaries

```
┌──────────────────────────────────────────────────────────────────┐
│                        TRUSTED ZONE                              │
│            (user's host machine; OS integrity assumed)           │
│                                                                  │
│   ┌──────────┐    ┌──────────┐    ┌────────────────────────┐     │
│   │ Frontend │───▶│ Backend  │───▶│  bitcoind (RPC + ZMQ)  │     │
│   └──────────┘    └────┬─────┘    └────────────────────────┘     │
│                        │                                         │
│                        │ keyring / encrypted DB                  │
│                        ▼                                         │
│                  ┌──────────────┐                                │
│                  │   Secrets    │  (third-party credentials      │
│                  │              │   only; no signing material)   │
│                  └──────────────┘                                │
└──────────┬───────────────────────────────────────────────────────┘
           │
           │ HTTPS to provider APIs (ccxt)
           ▼
     ┌──────────────┐         ┌──────────────┐
     │    Kraken    │         │   Bitstamp   │     UNTRUSTED
     └──────────────┘         └──────────────┘
                                                    
           │
           │ (offline transfer: USB / SD / QR)
           ▼
     ┌──────────────────────────────┐
     │  Signing device              │     TRUSTED (user-owned,
     │  (hardware wallet, airgapped │      airgapped or hardware)
     │   laptop, multisig co-signer)│
     └──────────────────────────────┘
```

## Attack scenarios

### S1 — User-level code execution on the host

**Example**: malicious browser extension, phishing link triggering code execution, trojan from a downloaded file.

**What the attacker can do:**

- Read the OS keyring (development mode) or read the encrypted database file. In Docker mode, the encryption key is in the running backend's process memory, so the attacker can dump that memory. Either way, **CustodialProvider API credentials are exposed**.
- Read the database directly: descriptors (privacy loss), labels, transaction history, sweep policies.
- Submit withdrawal requests through provider APIs. **However**: the provider's whitelist limits withdrawals to the user's whitelisted address (a Strongbox or Vault address). The attacker drains the Account, but the funds land in the user's own cold storage. This is by design.
- Once the Lightning iteration ships: read Lightning node credentials. Drain Lightning operational balance.
- Submit PaymentRequests through the backend's banking API. **However**: the attacker cannot sign them. The PSBT is built but cannot be broadcast without the user's external signing device.

**What the attacker cannot do:**

- Drain Strongbox or Vault on-chain funds (no signing material on the host).
- Change the withdrawal whitelist on the provider's side (requires provider-side authentication with 2FA, not just the API key).
- Forge a signed PSBT.

**Mitigations:**
- Provider API credentials are withdraw-whitelisted to non-Account Holdings.
- Passphrase unlock in Docker mode ensures the encryption key requires user presence at startup. (Note: once the app is unlocked, the key is in process memory and an attacker with the right access can read it. The unlock barrier protects against attackers who get a stale disk image, not against attackers running concurrently with an unlocked app.)
- Account balances are the only liquid asset on the host's surface; sweep policies minimize this balance.

### S2 — Attacker gains root

Game over. Documented honestly in the README: *"This app does not defend against a compromised operating system. If you run this on a machine you do not trust, no software can protect you."*

Specifically, with root the attacker can:
- Dump the backend process's memory and read the decrypted Argon2id-derived key, then decrypt all secrets at rest.
- Hook or replace the backend binary.
- Keylog the unlock passphrase.
- Modify the whitelist address in the database before a sweep fires.

**Why the last point matters and the partial mitigation:** with root, the attacker could change `custodial_provider.whitelist_address` to an attacker-controlled address. This is why we **also verify the whitelist on the provider's side** — changing the provider-side whitelist requires 2FA outside the host machine. So even with root, the attacker can corrupt local state but the provider would refuse to withdraw to the new address.

This means: in the most pessimistic scenario (host root), the attacker can prevent sweeps from working but cannot redirect funds to themselves.

### S3 — Stolen backup or database dump

Someone obtains the Postgres dump, but not the host's secrets backend (and not the user's passphrase in Docker mode).

**Impact:** privacy loss (descriptors, transaction history, labels). No fund loss.

**Mitigation:** Secrets are not in the Postgres dump path in development mode (they are in the OS keyring). In Docker mode, secrets ARE in the database, but they are encrypted with a key derived from the passphrase that was not dumped. The attacker would need to brute-force the passphrase against Argon2id, which is by design slow.

### S4 — CustodialProvider account takeover (separately from app)

The user's Kraken or Bitstamp account is compromised through means unrelated to the app — phishing on the provider's website, password reuse, SIM swap.

**Impact:** the attacker tries to withdraw. If the user has correctly configured the provider-side whitelist (which the app continually nags them about), withdrawals can only go to the user's whitelisted cold address. The attacker gets nothing.

**Mitigation:** the withdrawal-whitelist pattern is the core defense. The app's whitelist verification at registration plus its periodic re-verification keeps this honest.

### S5 — Malicious or failing CustodialProvider

The provider lies about balances, seizes funds, or collapses (the FTX scenario).

**Impact:** whatever was on the provider at the time of failure is lost. Sweep policies minimize the exposure window.

**Mitigation:** minimum-exposure trading doctrine. Outflow SweepPolicies (Account → TK Holding) move BTC off the provider frequently, reducing the exposure window. `minimum_balance_sats` defaults to 0. Threshold triggers fire as soon as a buy lands on the provider. Inflow SweepPolicies (TK Holding → Account) push BTC to the provider only at trade time, not for storage. Users with active sweep policies on tight thresholds have minutes-to-hours of exposure rather than days.

### S6 — Malicious descriptor as input

User pastes a descriptor crafted to exploit BDK.

**Impact:** potentially arbitrary code execution in the backend. BDK is Rust and hardened, but unknown vulnerabilities exist.

**Mitigation:** input length limit (4 KB), descriptor validated through BDK's safe parser before persistence, crash recovery via process restart on unhandled exception.

### S7 — Malicious destination address in pasted BIP21 URI

The user scans a QR or pastes a BIP21 URI where the address has been swapped via clipboard hijacking (a common malware pattern).

**Impact:** funds sent to the attacker.

**Mitigations:**
- The Review screen shows the destination address in plain monospace with first and last characters highlighted, before PSBT construction.
- The Confirmation screen shows destination, amount, and fee in large text.
- The user is prompted to verify the destination on their signing device's screen — this is the actual defense, since the clipboard-swap attack does not modify the address on the hardware wallet's screen.
- For repeat counterparties, the app supports saved address labels; the UI warns when sending to a never-before-seen address.

### S8 — Phishing or clone of the app

An adversary publishes a malicious fork that looks identical and tricks the user into running it.

**Impact:** potentially everything.

**Mitigation:** out of scope through the personal-use phase. Documented in the README. The public-ship event includes signed releases + reproducible builds (per ADR-0003 ship-gate bundle) and signed releases for self-hosters (see `backlog/signed-releases-for-self-hosters.md`).

### S9 — Subscriber outage causing missed events

A worker subscriber is down when an event fires. The bus does not retain the event.

**Impact:** state divergence. Example: a sweep completes, `treasury.sweep.executed` fires, but the LiveUpdateBridge is restarting and the user's UI never gets the notification. The audit-table row exists, so the data is correct, but the UI lags.

**Mitigation:** persist-first-emit-second pattern (module 01). The audit reconciler subscriber periodically scans `event_emission_log` for unacknowledged critical events and re-emits them. State is reconstructable from audit tables even if all subscribers crashed.

### S10 — Compromised passphrase

User reuses a weak passphrase, or it is keylogged.

**Impact:** in Docker mode, an attacker with the passphrase plus a stolen database dump can decrypt all secrets and make withdrawal requests. Whitelisting still applies — funds still go to the user's cold address.

**Mitigation:** the unlock screen shows passphrase strength feedback. Argon2id makes brute-force expensive. The user is the responsible party for passphrase choice; the app cannot enforce a strong choice but warns about weak ones.

## Security controls summary

| Control | Status |
|---|---|
| Localhost-only binding | Enforced |
| No public API | Enforced |
| No user accounts (no password database) | Enforced |
| Secrets in OS keyring (dev) or encrypted database (Docker) | Enforced |
| Passphrase-derived key via Argon2id | Enforced |
| AES-256-GCM authenticated encryption for secrets | Enforced |
| Passphrase never persisted | Enforced |
| Withdraw-only provider API credentials | Enforced — `can_trade=False` invariant in DB |
| Provider-side whitelist verified at registration when API supports it | Enforced for Kraken |
| Provider-side whitelist warning when unverifiable | Enforced (blocking confirmation required) |
| Vault outgoing payments warn before proceeding | Enforced via UX, configurable per profile |
| No auto-categorization without user confirmation | Enforced |
| Provider API rate limiting | Via ccxt |
| Dependency pinning | Enforced |
| Logging redaction (denylist) | Enforced |
| Persist-first-emit-second for critical events | Enforced |
| Audit tables (sweep_execution, broadcast_attempt, event_emission_log) | Enforced |
| Signed releases | Public-ship event (per ADR-0003 ship-gate bundle); not in dev or personal-use phase |
| TLS | Not needed currently (localhost). Required when remote access is added — see `backlog/remote-access-for-self-hosters.md`. |
| Backup guidance in documentation | Yes |

## Things explicitly NOT defended

- Root attacker on the host: out of scope.
- Signing device compromise: out of scope; user's responsibility.
- Supply chain: partial — dep pinning, no active monitoring.
- Side channels (timing, power analysis on the host): out of scope.
- Denial of service by malicious bitcoind: user runs their own node; out of scope.
- Phishing of the app itself: out of scope.

## Mobile addendum (Capacitor build)

The threat model above is host-centered: it covers TallyKeep's
backend running on the user's host machine, with the SvelteKit
frontend served from there or from the hosted tier. The mobile build
(Capacitor wrap, distributed via app store / sideload, also reachable
in the dev phase via direct APK / TestFlight) introduces a second
surface with its own asset model and adversary considerations. This
addendum captures the load-bearing decisions per ADR-0002, ADR-0003,
ADR-0006 (slug `purse-flavors`), ADR-0007, and ADR-0009 (the
four-zone key-custody model that supersedes the original
"no signing keys held by the app" framing). Full interleaving of
mobile assets into the host-centered sections above is documentation
work that may land in a future iteration; the addendum is
authoritative until then.

### Mobile-specific assets

| Asset | Sensitivity | Where it lives |
|---|---|---|
| TallyKeep-managed Purse seed | Critical | iOS Keychain (Secure Enclave) / Android Keystore (TEE / StrongBox where available), AES-256-GCM at rest, biometric-gated. Lives only on the specific client device that generated (or restored) it. Capacitor build only. |
| Lightning channel state and node keys (Lightning iteration) | Critical | Same — iOS Keychain / Android Keystore. Capacitor build only. |
| Hosted-tier session token | High | Keychain/Keystore on Capacitor; encrypted IndexedDB on browser PWA |
| Paired-device bearer tokens | High | Same as session token |

### Mobile-specific principles (locked)

- **Browser build holds no Bitcoin signing material, ever.** Desktop
  browser, mobile browser, installed PWA — none of them. Recovery
  for connection-only material is "revoke and re-pair," so eviction
  is annoying but not catastrophic.
- **Capacitor build is the only surface that holds spending keys.**
  TallyKeep-managed Purse seeds and Lightning material live there
  (in iOS Keychain / Android Keystore). Strongbox and Vault keys
  never live on any TallyKeep build — they remain on hardware
  wallets / multisig co-signers, exactly as in the host-centered
  model above.
- **The backend never holds a reference to a Purse seed**, encrypted
  or otherwise. `purse_mode` records intent (on-device keys or
  watch-only); it does not record where the seed lives. The seed
  location is per-client runtime state, indexed locally by
  `holding_id`.
- **Purse has three modes** (resolved per ADR-0006, slug
  `purse-flavors`; field renamed to `purse_mode` in the
  Purse-mode-rename janitorial iteration):
  - *Watch-only* (`WATCH_ONLY`) — onboarded via xpub / descriptor.
    No seed lives in any TallyKeep client; the seed is in another
    hot wallet (Phoenix, BlueWallet, Mutiny, Sparrow's hot mode).
    Available on browser and Capacitor. Spending always points back
    to the source wallet.
  - *TallyKeep-generated* (`ON_DEVICE_TK_GENERATED`) — TallyKeep
    generated the seed during Add-Holding. The seed lives in *the
    client device that ran the creation flow*, in its
    Keychain/Keystore. Other clients accessing the same backend
    see the same Holding but as view-only, with a "go sign on the
    device that holds the seed" gate. The "create TallyKeep wallet"
    affordance is gated
    client-side by the client's capability to generate and securely
    store a seed (Capacitor: yes; browser PWA: no).

### Mobile-specific scenarios

**S11 — Lost or stolen phone (Capacitor build).** An attacker obtains
the user's unlocked phone, or bypasses the lock screen.

- *Impact:* if the attacker bypasses biometric (face presented,
  sleeping user, coercion), they can spend from any TallyKeep-managed
  Purse whose seed lives on this phone, plus Lightning balances.
  Strongbox and Vault funds remain safe (no keys on phone). The
  dev-phase JS-signing posture (per ADR-0003) does not worsen this
  scenario; the bottleneck is still phone access.
- *Mitigation:* biometric prompt on every signing operation;
  passphrase fallback for high-value spends (configurable);
  out-of-band seed backup is the load-bearing recovery (per pending
  pre-implementation item `seed-backup-disclosure`).

**S12 — Mobile-device user-level malware.** A malicious app sandboxed
on the same device attempts to read TallyKeep's Keychain/Keystore
entries.

- *Impact:* Keychain/Keystore is sandboxed per-app on iOS and Android
  with hardware-backed isolation (Secure Enclave / TEE / StrongBox).
  A user-level malicious app cannot read another app's Keychain
  entries without privilege elevation.
- *Mitigation:* OS sandbox; do not write seed material to shared
  storage; do not log seed-derived intermediates. Native signing
  plugin (ship-gate item per ADR-0003) tightens this further by
  keeping the seed inside native code during signing — replaces the
  dev-phase JS-signing posture.

**S13 — Browser-build pretending to sign.** The browser build does
not have access to any client-local seed. An attacker compromises the
browser-served frontend code and tries to capture seed material.

- *Impact:* none, because the browser build has no seed available
  to capture — it has no Keychain/Keystore access, and the backend
  has no seed reference to leak. The "spending requires the app or
  external sign" gate (per ADR-0006) is enforced at the
  architectural level.
- *Mitigation:* architectural — the gate is in the SvelteKit code
  itself (`NativeBridge` interface throws on browser builds for
  native operations, and the per-client signing-capability check
  short-circuits to view-only). Designing to a single shared codebase
  with platform-conditional behaviour avoids the temptation of
  "let's just sign in JS for browser convenience."

### Dev-phase relaxation (per ADR-0003)

During the development phase, JS-side signing in the Capacitor build
(using `@noble/secp256k1` with the seed retrieved from
Keychain/Keystore) is acceptable instead of native-code signing. The
known weaker model — a malicious dependency or WebView RCE during the
signing window can extract the seed — is tolerable when the assets
and devices are Rémy's. Native signing becomes a ship-gate item; the
dev-phase posture is **not** the public-ship posture.

## Posture for deferred work

Each item below is captured as a backlog entry in `backlog/`; this
section sketches the threat-model delta each one introduces, so
the iteration that picks it up has a starting point for its own
threat-model addendum.

- **Remote access for self-hosters** — when remote access is added (recommended via WireGuard or Tailscale), API-layer auth becomes required: token-based, not passwords. TLS is required for any traffic beyond localhost, even over an encrypted tunnel.
- **Order placement on custodial providers** — when order placement is added, a new threat class appears (loss via malicious orders). Dry-run mode and per-order confirmation become required defaults; auto-execution behind extra gates.
- **Multi-user support** — if ever considered, the entire threat model is revisited. User isolation, per-user secret storage, audit trails become first-class concerns. Not in any current iteration plan.
- **Investment layer with structured yield** (per `backlog/investment-layer-with-structured-yield-the-v5-sketch.md`) — multisig vault primitives with structured collaboration (DLCs, LSP-mediated arrangements) introduce counterparty risk that does not exist today. Requires its own threat model.