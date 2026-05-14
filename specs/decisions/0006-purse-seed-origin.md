# ADR-0006 — Purse seed origin and per-client signing capability

> **Vocabulary update (2026-05):** The `seed_origin` field was renamed to
> `purse_mode`; the enum values were reorganized around the on-device-keys
> axis: `EXTERNAL_WATCH_ONLY` → `WATCH_ONLY`, `TALLYKEEP_MANAGED` →
> `ON_DEVICE_TK_GENERATED`, and `ON_DEVICE_USER_IMPORTED` reserved for the
> upcoming `purse-upgrade-path` iteration. The substantive decision — three
> Purse flavors, per-client signing-capability check, no seed reference on
> the backend — is unchanged. See `02_domain_model.md` §"Purse mode" for
> the current shape.

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during consolidation merge
- **Migrated from:** `pre-implementation.md` Decided item
  `purse-flavors` (2026-05).

## Context

Browser builds cannot hold spending keys (no platform-grade
secure-storage primitive equivalent to iOS Keychain or Android
Keystore). The Capacitor build can. The same backend may be
reached from multiple clients with different local capabilities
— a phone, a laptop browser, a second phone. The Purse type had
to model "what kind of wallet is this" in a way that is stable
across devices and meaningful to all of them, without leaking
"where the seed lives" into the backend's view of the world (the
locked principle is "no signing keys to backend, ever").

## Decision

1. Purse has a `seed_origin` field with two values capturing the
   **intent** of the wallet at creation:
   - `EXTERNAL_WATCH_ONLY` — onboarded via xpub or descriptor
     only. Single-address import is not supported (wallet
     activity rotates across many addresses; observing one
     misrepresents the wallet). The seed lives in another hot
     wallet (Phoenix, BlueWallet, Mutiny, Sparrow's hot mode).
     Spending always points back to the source wallet.
   - `TALLYKEEP_MANAGED` — TallyKeep generated the seed during
     the Add-Holding flow and stored it in **the current client
     device's** secure local storage (iOS Keychain / Android
     Keystore on Capacitor; biometric-gated). The descriptor
     derived from the seed registers with the backend; the seed
     itself never crosses to the backend.

2. The backend **never** holds a reference to the seed,
   encrypted or otherwise. There is no `on_device_seed_reference`
   field. The locked principle is preserved.

3. Whether a given client can sign for a TallyKeep-managed Purse
   is a **runtime question** answered locally by checking that
   client's secure-storage backend for an entry keyed by the
   Holding's `id`. Three outcomes:
   - Capacitor on the device that generated (or restored) the
     seed → entry present → Send is enabled, biometric, sign
     in-app, broadcast.
   - Capacitor on a different device, or browser PWA on any
     device → no entry → Send shows a "go sign on the device
     that holds the seed" gate. No PSBT export, no
     pretend-to-sign.
   - External-watch-only Purse, any client → always view-only;
     Send always points to the source wallet.

4. The "Create a TallyKeep wallet" affordance in Add-Holding is
   gated **client-side** on the device's capability to generate
   and securely store a seed. Browser PWA hides it with a "this
   requires the TallyKeep app" message. The backend does not
   validate the client build type; it accepts any Purse-creation
   request. An attacker calling the API directly could register
   a `tallykeep_managed` Purse with no client actually holding a
   seed — the result is a Holding nobody can spend from. UX
   nuisance, not security risk.

5. Pairing-based PSBT roundtrip between TallyKeep instances
   ("send a PSBT from desktop to my paired phone for signing")
   is **out of current scope**. Send on a device-without-seed
   redirects to the device-with-seed and stops there. Pairing is
   captured for post-shipping in `future_iterations.md`.

6. Specific wording at gates ("Install the app", "Spend in
   [wallet]", "Open TallyKeep on the device that holds this
   key") is a design decision evaluated alongside the send-flow
   mockup, not arbitration.

## Consequences

- The four-Holding-type model holds: Account, Purse, Strongbox,
  Vault, with Purse internally split by `seed_origin` for
  spending UX divergence.
- The same Holding can appear with different signing affordances
  on different clients without any backend state representing
  this. The only backend fact is "this Purse exists with this
  descriptor"; everything else is client-local runtime.
- The threat model gains a "browser-build-pretending-to-sign"
  scenario; mitigation is the runtime capability check plus
  honest gates.

## Affected files

- `02_domain_model.md` §"Purse seed origin" and §"Signing
  capability is per-client"
- `03_data_model.md` `holding.subtype_data` JSONB shape for
  `purse`
- `UI/README.md` — Add-Holding, Send, Receive sections per
  Holding type
- `concerns/threat_model.md` Mobile addendum — S13 (browser-build
  pretending to sign)
- `09_feature_flags.md` — no flag implications, but documented
  as runtime capability rather than user preference
