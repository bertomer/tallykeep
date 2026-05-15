# Purse — light spending Holdings

A **Purse** is a wallet for everyday spending. The implementation
axis that matters is **whether the Purse has on-device keys**.
This is the primary distinction; the *seed source* (who generated
the seed) is a secondary classification that only matters when
there are on-device keys.

The Purse type carries a single mode field with three values:

| `purse_mode` | On-device keys? | Seed source | Spending |
|---|---|---|---|
| `WATCH_ONLY` | No | Lives in another wallet (Phoenix, BlueWallet, Mutiny, Sparrow hot mode, etc.) | Send button greyed out; tap surfaces "Import the seed of this wallet into TallyKeep to enable spending" (per pending arbitration `purse-upgrade-path`), or redirect to the source wallet. |
| `ON_DEVICE_TK_GENERATED` | Yes | TallyKeep generated the seed during Add-Holding | Native sign via NativeBridge (biometric → sign in-app → broadcast). |
| `ON_DEVICE_USER_IMPORTED` | Yes | User pasted a BIP39 mnemonic / xprv from another wallet (Mutiny shutdown migration, Phoenix-on-the-way-out, etc.) | Same as `ON_DEVICE_TK_GENERATED`. Differs only in disclosure copy and security-health framing (user already has a backup; "TallyKeep gave you this seed" wording does not apply). |

**Key custody zone (ADR-0009):**
- `WATCH_ONLY` — TallyKeep holds no key. Source wallet does.
- `ON_DEVICE_TK_GENERATED` / `ON_DEVICE_USER_IMPORTED` — key is
  in the **Capacitor client's** OS Keychain/Keystore,
  biometric-gated, on the specific device that ran the
  creation-or-import flow. Never transmitted to the backend.

**Renaming note.** Earlier drafts of this spec (ADR-0006) named
these three modes `EXTERNAL_WATCH_ONLY`, `TALLYKEEP_MANAGED`,
`EXTERNAL_IMPORTED` and called the field `seed_origin`. That
naming collapsed the *source-wallet* and *on-device-keys*
dimensions into one enum without making the primary distinction
visible. The field is renamed to `purse_mode` (or equivalent;
final name confirmed during the Treasury-rename-style janitorial
pass) and the values reorganize around the binary
on-device-keys-or-not. The migration is captured under
`purse-upgrade-path` in `pre-implementation.md`; an Alembic
migration rewrites existing values:
- `EXTERNAL_WATCH_ONLY` → `WATCH_ONLY`
- `TALLYKEEP_MANAGED` → `ON_DEVICE_TK_GENERATED`
- (`EXTERNAL_IMPORTED` was never shipped) → `ON_DEVICE_USER_IMPORTED`

## What a Purse does

- **Observes** the watched descriptor on-chain — balance, UTXOs,
  hygiene flags. Generic mechanics in `concerns/observation.md`.
- **Receives** payments at fresh-per-payment addresses derived
  from the descriptor. (Receive address derivation is a public
  operation; the backend can do it for any Purse regardless of
  whether keys live on a client.)
- **Sends** payments. The spending UX differs per purse-mode
  and per-client capability — described below.
- **Participates** in SweepPolicies as a source or destination,
  with auto-sweep feasibility per purse-mode (see
  `concerns/sweep_policies.md`).

## Vocabulary detail

The Purse type's domain model carries:

- `purse_mode` — `WATCH_ONLY` | `ON_DEVICE_TK_GENERATED` |
  `ON_DEVICE_USER_IMPORTED`. Records **intent** of the wallet at
  creation. Stable across devices.
- `descriptor_ids` — one or more Descriptors backing this
  Purse.

The backend **never** stores where the seed physically lives
(per ADR-0009). That is per-client runtime state, keyed locally
by `holding_id`. The locked principle "no spending keys to
backend" is preserved.

## Per-client signing capability

Whether a given client can sign for a Purse is a **runtime
question** answered locally by checking the client's
secure-storage backend for an entry keyed by `holding_id`. Three
outcomes:

| Purse mode × client | Outcome |
|---|---|
| `WATCH_ONLY` × any client | Always view-only. Send greyed out; tap surfaces import-seed affordance or source-wallet redirect. |
| `ON_DEVICE_*` × Capacitor on the device that holds the seed | Send enabled. Biometric → sign in-app → broadcast. |
| `ON_DEVICE_*` × Capacitor on a different device, or browser PWA anywhere | "Go sign on the device that holds the seed" gate. No PSBT export. No pretend-to-sign. |

The `NativeBridge` interface (per ADR-0007) abstracts the local
capability check. Browser builds short-circuit to view-only.

## Add-Holding — `WATCH_ONLY`

Onboarded via **xpub or descriptor only**. Single-address import
is not supported (per ADR-0006): wallet activity rotates across
many addresses; observing one misrepresents the wallet.

The source wallet (Phoenix, BlueWallet, Mutiny, Sparrow hot
mode) keeps the seed. TallyKeep watches. Available on every
client (Capacitor + browser PWA). Spending always redirects to
the source wallet.

## Add-Holding — `ON_DEVICE_TK_GENERATED`

TallyKeep **generates a fresh seed** during the Add-Holding flow
and stores it in the current client device's secure local
storage (OS Keychain/Keystore on Capacitor; biometric-gated).
The descriptor derived from the seed registers with the
backend; the seed itself never crosses to the backend.

The "Create a TallyKeep wallet" affordance is **gated client-
side** on the device's capability to generate and securely store
a seed:
- Capacitor on phone: shown.
- Browser PWA on any platform: hidden, with a "this requires the
  TallyKeep app" message.

The backend does **not** validate the client build type — it
accepts any Purse-creation request. The trade-off: an attacker
calling the API directly could register an `ON_DEVICE_TK_GENERATED`
Purse with no client actually holding a seed. Result: a Holding
nobody can spend from. UX nuisance, not a security risk.

At seed generation, the user is shown the seed and warned about
backup responsibility. The persistent-warning model lives in the
**security-health system** (pending arbitration
`seed-backup-disclosure` in `pre-implementation.md`).

## Add-Holding — `ON_DEVICE_USER_IMPORTED` (target, pending arbitration)

Per the pending `purse-upgrade-path` arbitration: the user
**upgrades** an existing `WATCH_ONLY` Purse by adding
the seed phrase / master xprv from the source wallet. The
affordance lives on the **Purse Detail page**, not in the Add
wizard.

The upgrade flow:

- Textarea accepting BIP39 mnemonic (12 / 24 words) or master
  xprv.
- Inline validation against the wallet whose descriptor is
  already imported — refuses pastes that don't derive to the
  same descriptor.
- Capacitor-only at ship; browser-fallback gating per ADR-0007.
- Disclosure copy specific to the imported-seed case:
  *"TallyKeep now stores a copy of these keys on this device.
  You already have a backup from where you exported the seed —
  keep it safe. Spending from both apps on the same wallet
  without coordinating can cause failed broadcasts."*
- Security-health surface registers the imported Purse with copy
  distinct from generated Purses (no "TallyKeep gave you this
  seed" framing).

Specific arbitration items still pending (per
`pre-implementation.md` `purse-upgrade-path`): whether
`purse_mode` is mutable in place (a `WATCH_ONLY` Purse becomes
`ON_DEVICE_USER_IMPORTED` on upgrade) or whether the upgrade
creates a new Purse and the old one is archived; exact disclosure
copy; double-spend UX disclosure timing; Capacitor gate posture
for the upgrade affordance.

## Send flow

### `WATCH_ONLY` Purse

Send is hidden by default. Primary affordance points the user at
the source wallet ("Spend in [wallet]" with a deep-link where
supported). A power-user toggle exposes "Construct PSBT for
export" for the rare workflow that wants it.

TallyKeep aggregates and observes; doesn't compete on spending
UX where the source wallet already owns it.

### `ON_DEVICE_TK_GENERATED` / `ON_DEVICE_USER_IMPORTED` Purse — on the device that holds the seed

Native send via `NativeBridge`:

1. Compose — paste/scan address, amount, fee tier, label.
2. Review — destination, amount, fee, expected confirmation
   time. Reconcilability gauntlet question 4 ("confirmation
   honesty") enforces no "Sent ✓" before broadcast
   acknowledgement.
3. Sign — biometric prompt; signing in-app.
4. Broadcast.
5. Confirmed — depth shown verbatim. Settlement-rails framing
   with confirmation probability when that feature ships (per
   `future_iterations.md`).

The PSBT-construction mechanics (BDK coin selection, fee
resolution, network validation) live in `concerns/outflow.md`;
this chapter describes what's Purse-specific.

### `ON_DEVICE_TK_GENERATED` / `ON_DEVICE_USER_IMPORTED` Purse — on any other client

Send shows a clear gate: *"This wallet's keys are on another
device. To spend, open TallyKeep on the device that holds them."*
No PSBT export, no pretend-to-sign.

Pairing-based PSBT roundtrip between TallyKeep instances ("send
a PSBT from desktop to my paired phone for signing") is captured
for later in `future_iterations.md`.

## Receive flow

Receive works identically on every client for every Purse mode —
derivation is a public operation:

- TallyKeep derives the next unused address from the descriptor.
- Display as text + QR with a BIP21 payment URI
  (`bitcoin:address?amount=X&label=Y`) for sender-wallet
  pre-fill.
- Fresh-per-payment by default; reuse is captured for later
  (`future_iterations.md` "Receive in static / merchant mode").

For `WATCH_ONLY` Purses, the source wallet observes
the chain too; both apps stay in sync because the descriptor is
the persistent identifier of the wallet.

Lightning receive (deferred per `concerns/lightning_placeholder.md`)
generates an invoice rather than an address — different
mechanic, behind a visible-disabled tab today.

## SweepPolicy participation

Per `concerns/sweep_policies.md`:

| Direction | Feasibility |
|---|---|
| Purse as destination | Always allowed (receive is public). |
| `WATCH_ONLY` Purse as source | Not auto-sweep. Spending happens in the source wallet; TallyKeep cannot drive it. |
| `ON_DEVICE_TK_GENERATED` / `ON_DEVICE_USER_IMPORTED` Purse as source, on the device that holds the seed | Auto-sweep feasible (biometric prompt + native sign on that device). Configurable schedule / threshold. |
| Same Purse, on any other client | Not auto-sweep. Scheduled reminder fires only on the device that holds the seed. |

Auto-sweep from Purse is post-shipping in current scope (see
`future_iterations.md` "Holding-to-Holding sweeps beyond
Account-originated").

## Type-specific safeguards

None at the Purse-type level. The relevant hygiene checks
(address reuse, dust, suspected consolidation) apply to all
non-Account Holdings and live in `concerns/observation.md`.

The seed-backup disclosure (pending `seed-backup-disclosure`
arbitration) is Purse-specific in that it applies to
`ON_DEVICE_TK_GENERATED` and `ON_DEVICE_USER_IMPORTED` Purses —
both modes where TallyKeep holds the seed.

## Deferred

| Item | Tracked in |
|---|---|
| Pairing-based PSBT roundtrip between TallyKeep instances | `future_iterations.md` |
| Auto-sweep from an on-device Purse (and the broader Holding-to-Holding sweep UX) | `future_iterations.md` "Holding-to-Holding sweeps beyond Account-originated" |
| `ON_DEVICE_USER_IMPORTED` upgrade flow details | `pre-implementation.md` `purse-upgrade-path` |
| Seed-backup disclosure full system | `pre-implementation.md` `seed-backup-disclosure` |
| Lightning support per Purse | `concerns/lightning_placeholder.md` + `future_iterations.md` "Lightning support" |
| Receive in static / merchant mode | `future_iterations.md` |
| Possible Purse / Strongbox vocabulary collapse (observation mode) | `future_iterations.md` "Possible Purse / Strongbox collapse" |