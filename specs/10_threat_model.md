# 10 — Threat Model (v1)

## Summary

The v1 app runs on a host machine owned by the user, binds only to localhost, holds no Bitcoin signing material, never places orders, and can withdraw from CustodialProviders only to addresses pre-whitelisted on the provider's side and verified by the app.

**Single-line security property**: *an attacker who fully compromises the host machine can drain operational balances (Account funds via withdrawal-to-whitelisted-only, plus future Lightning balance), and can read the user's complete transaction history, but cannot drain Strongbox or Vault funds.*

## Assets

| Asset | Sensitivity | Where it lives |
|---|---|---|
| Private keys for Strongbox Holdings | Critical | Hardware wallet or airgapped device. Never on the host. |
| Private keys for Vault Holdings | Critical | Multisig co-signers, possibly geographically separated. Never on the host. |
| Private keys for Purse Holdings | High | On the user's connected day-to-day device (phone, laptop). May or may not be on the same host as the app. |
| CustodialProvider API credentials (read + withdrawal-whitelisted) | High | OS keyring (development) or encrypted database (Docker), never plaintext on disk |
| Lightning node credentials (v1.5: macaroons, runefile, gRPC certs) | Medium-High | Encrypted on the host |
| Descriptors and xpubs | Medium (privacy) | Database on the host |
| LedgerEntries, labels, categorizations | Medium (privacy) | Database on the host |
| SweepPolicy configurations | Low | Database on the host |
| The user's passphrase (Docker mode) | Critical | Held in-memory only after unlock; never persisted |

**Central commitment, restated:** Bitcoin signing material is never on the host machine in any form, encrypted or not. The encrypted secret store holds *third-party access credentials* — Kraken API keys, the bitcoind RPC password, future Lightning node access tokens — but never anything that signs Bitcoin transactions. This is enforced by the type system: no domain entity has a field that could carry signing material.

## Actors

| Actor | Capability | Defended in v1? |
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
- (v1.5) Read Lightning node credentials. Drain Lightning operational balance.
- Submit PaymentRequests through the backend's banking API. **However**: the attacker cannot sign them. The PSBT is built but cannot be broadcast without the user's external signing device.

**What the attacker cannot do:**

- Drain Strongbox or Vault on-chain funds (no signing material on the host).
- Change the withdrawal whitelist on the provider's side (requires provider-side authentication with 2FA, not just the API key).
- Forge a signed PSBT.

**Mitigations in v1:**
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

**Mitigation:** minimum-exposure trading doctrine. Sweeps run frequently. `minimum_balance_sats` defaults to 0. Threshold triggers fire as soon as a buy lands.

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

**Mitigation:** out of scope for v1. Documented in the README. v1.0 release ships with checksums and signed releases as a v1.1 hardening item.

### S9 — Subscriber outage causing missed events

A worker subscriber is down when an event fires. The bus does not retain the event.

**Impact:** state divergence. Example: a sweep completes, `trading.sweep.executed` fires, but the LiveUpdateBridge is restarting and the user's UI never gets the notification. The audit-table row exists, so the data is correct, but the UI lags.

**Mitigation:** persist-first-emit-second pattern (module 01). The audit reconciler subscriber periodically scans `event_emission_log` for unacknowledged critical events and re-emits them. State is reconstructable from audit tables even if all subscribers crashed.

### S10 — Compromised passphrase

User reuses a weak passphrase, or it is keylogged.

**Impact:** in Docker mode, an attacker with the passphrase plus a stolen database dump can decrypt all secrets and make withdrawal requests. Whitelisting still applies — funds still go to the user's cold address.

**Mitigation:** the unlock screen shows passphrase strength feedback. Argon2id makes brute-force expensive. The user is the responsible party for passphrase choice; the app cannot enforce a strong choice but warns about weak ones.

## Security controls summary

| Control | v1 status |
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
| Signed releases | Planned for v1.0; not v1-dev |
| TLS | Not needed in v1 (localhost). Required if v2 enables remote access. |
| Backup guidance in documentation | Yes |

## Things explicitly NOT defended in v1

- Root attacker on the host: out of scope.
- Signing device compromise: out of scope; user's responsibility.
- Supply chain: partial — dep pinning, no active monitoring.
- Side channels (timing, power analysis on the host): out of scope.
- Denial of service by malicious bitcoind: user runs their own node; out of scope.
- Phishing of the app itself: out of scope.

## Posture for future versions

- **v2** — when remote access is added (recommended via WireGuard or Tailscale), API-layer auth becomes required: token-based, not passwords. TLS is required for any traffic beyond localhost, even over an encrypted tunnel.
- **v2** — when order placement is added, a new threat class appears (loss via malicious orders). Dry-run mode and per-order confirmation become required defaults; auto-execution behind extra gates.
- **v3** — if multi-user support is ever considered, the entire threat model is revisited. User isolation, per-user secret storage, audit trails become first-class concerns.
- **v5+** — multisig vault primitives with structured collaboration (DLCs, LSP-mediated arrangements) introduce counterparty risk that does not exist in v1. Each one needs its own threat model.
