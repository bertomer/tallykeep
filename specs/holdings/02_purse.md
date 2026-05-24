# Purse — light spending Holdings

A **Purse** is a wallet for everyday spending. The implementation
axis that matters is **whether the Purse has on-device keys**.
This is the primary distinction; the *seed source* (who generated
the seed) is a secondary classification that only matters when
there are on-device keys.

The Purse type carries a single mode field with three values:

| `purse_mode` | On-device keys? | Seed source | Spending |
|---|---|---|---|
| `WATCH_ONLY` | No | Lives in another wallet (Phoenix, BlueWallet, Mutiny, Sparrow hot mode, etc.) | Send button visible; tap routes to a real "Send blocked" screen (`UI/mobile.md §Purse detail` → Send routing) with two paths: sign with the source wallet via PSBT, or add the keys to this Purse (upgrade-path entry per `backlog/purse-upgrade-path-watch-only-on-device-imported.md`). |
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
| `WATCH_ONLY` × any client | Always view-only from TK's POV. Send button visible at the detail page; tap routes to the "Send blocked" screen with two paths: sign with the source wallet (PSBT QR), or add the keys to this Purse (upgrade-path). |
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
**security-health system** (locked per ADR-0019; the seed-backup
item is `critical`-severity, bell-badge bearer, surfaces inline on
Purse detail Settings and in the central dashboard until the user
acknowledges).

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
creates a new Purse and the old one is Forgotten (per ADR-0017); exact disclosure
copy; double-spend UX disclosure timing; Capacitor gate posture
for the upgrade affordance.

## Send flow

### `WATCH_ONLY` Purse

Send button is visible on the Purse detail page; tapping it
routes to a real "Send blocked" screen (see
`UI/mobile.md §Purse detail` → Send routing for the screen
spec, mockup `mobile_purse_detail_send_blocked_watch_only.html`).
The screen acknowledges that TallyKeep doesn't hold this
Purse's keys and presents two equally-weighted paths:

1. **Sign with the source wallet (PSBT)** — TallyKeep
   constructs a PSBT and displays it as a QR (or copyable /
   file later) for the source wallet (Phoenix, BlueWallet,
   etc.) to sign and broadcast. Source-wallet name pulls
   from import metadata when available.
2. **Add the keys to this Purse** — Upgrade-path entry:
   import the source wallet's recovery phrase to this
   Purse so TallyKeep can sign natively. The flow ships
   per `backlog/purse-upgrade-path-watch-only-on-device-imported.md`.

The earlier "Send hidden by default + power-user PSBT-export
toggle" sketch is retired: it hid the affordance that's
load-bearing for a WATCH_ONLY user who wants to spend, and
the new shape makes the choice between PSBT and upgrade
explicit rather than burying one behind a toggle.

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
   `backlog/settlement-rails-payment-status-with-confirmation-probability.md`).

The PSBT-construction mechanics (BDK coin selection, fee
resolution, network validation) live in `concerns/outflow.md`;
this chapter describes what's Purse-specific.

### `ON_DEVICE_TK_GENERATED` / `ON_DEVICE_USER_IMPORTED` Purse — on any other client

Send shows a clear gate: *"This wallet's keys are on another
device. To spend, open TallyKeep on the device that holds them."*
No PSBT export, no pretend-to-sign.

Pairing-based PSBT roundtrip between TallyKeep instances ("send
a PSBT from desktop to my paired phone for signing") is captured
for later in `backlog/psbt-by-qr-roundtrip-on-mobile.md`.

## Receive flow

Receive works identically on every client for every Purse mode —
derivation is a public operation:

- TallyKeep derives the next unused address from the descriptor.
- Display as text + QR with a BIP21 payment URI
  (`bitcoin:address?amount=X&label=Y`) for sender-wallet
  pre-fill.
- Fresh-per-payment by default; reuse is captured for later
  (`backlog/receive-in-static-merchant-mode.md`).

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
`backlog/holding-to-holding-sweeps-beyond-account-originated.md`).

## Type-specific safeguards

None at the Purse-type level. The relevant hygiene checks
(address reuse, dust, suspected consolidation) apply to all
non-Account Holdings and live in `concerns/observation.md`.

The seed-backup disclosure (locked per ADR-0019) is Purse-specific
in that it applies to `ON_DEVICE_TK_GENERATED` and
`ON_DEVICE_USER_IMPORTED` Purses — both modes where TallyKeep holds
the seed.

## Purse detail page

The per-Holding detail page surface for a Purse is specified
in `UI/mobile.md §Purse detail`. Cross-type chrome decisions
(SSE-driven freshness, two-tab Operations | Settings layout,
shared unit-toggle, "Forget" cross-type vocabulary lock,
5-second Forget-button timer for misfire prevention) carry
over from the Account-detail iteration; Purse-specific
calls are:

- **Action-row verb pair: Send + Receive** (not Deposit /
  Withdraw), because the Holding *is* the user's wallet —
  no perspective ambiguity. The unified arrow-and-wallet
  icon pair is the cross-type standard for Purse /
  Strongbox / Vault detail pages.
- **Status-card mode subtitle**: "Watch-only" / "Spending
  wallet" / "Spending wallet · imported" — the user-facing
  rendering of `purse_mode`. Locked vocabulary.
- **Per-mode Send routing**: WATCH_ONLY taps the real
  Send-blocked screen (see §Send flow above); ON_DEVICE_*
  taps a coming-soon stub until the Send iteration ships.
- **Per-mode Settings**: WATCH_ONLY omits the Recovery
  phrase row; ON_DEVICE_TK_GENERATED includes it (routes
  to coming-soon, deferred to the Security-health-system
  iteration). ON_DEVICE_USER_IMPORTED Settings variant
  sharpens with the upgrade-path iteration.
- **Per-mode Forget**: WATCH_ONLY uses the descriptor-only
  body copy ("funds at your source wallet are unaffected");
  ON_DEVICE_* uses the load-bearing seed-destruction
  warning panel + body copy spelling out the
  permanent-loss-if-unbacked-up consequence. The warning
  panel is non-negotiable for ON_DEVICE_*; it is the only
  Holding-type case where Forget has on-chain consequences.
  **Both variants** end with a categorization-loss
  disclosure ("Any categories you've assigned to this
  Purse's activity are erased with it") — Forget destroys
  the chain-side ledger entries the user's category labels
  attach to, regardless of mode. Re-importing the Purse
  brings back tracking but not categorization work.
- **Lightning (instant payments) activation**: a per-Purse
  Settings entry exists for "Activate instant payments".
  CTA routes to coming-soon until the Lightning iteration
  ships (`backlog/lightning-support.md`).

The detail page is the home for the upgrade-to-spending
affordance for WATCH_ONLY Purses; per the design pass, the
entry point is the Send-blocked screen (intent-driven
funnel), not a separate promotion banner or Settings card.

## Deferred

| Item | Tracked in |
|---|---|
| Pairing-based PSBT roundtrip between TallyKeep instances | `backlog/psbt-by-qr-roundtrip-on-mobile.md` |
| Auto-sweep from an on-device Purse (and the broader Holding-to-Holding sweep UX) | `backlog/holding-to-holding-sweeps-beyond-account-originated.md` |
| `ON_DEVICE_USER_IMPORTED` upgrade flow details | `pre-implementation.md` `purse-upgrade-path` + `backlog/purse-upgrade-path-watch-only-on-device-imported.md` |
| Seed-backup disclosure full system | ADR-0019; v1 iteration active in `next_iteration.md` (Security-health-system v1) |
| Lightning support per Purse | `concerns/lightning_placeholder.md` + `backlog/lightning-support.md` |
| Receive in static / merchant mode | `backlog/receive-in-static-merchant-mode.md` |
| Possible Purse / Strongbox vocabulary collapse (observation mode) | `backlog/possible-purse-strongbox-collapse.md` |
