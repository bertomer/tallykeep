# ADR-0009 — Key custody model

> **Vocabulary update (2026-05):** The `seed_origin` field (ADR-0006) was
> renamed to `purse_mode`; values `TALLYKEEP_MANAGED` → `ON_DEVICE_TK_GENERATED`
> and `EXTERNAL_IMPORTED` → `ON_DEVICE_USER_IMPORTED`. The custody-zone logic
> described below is unchanged; only the names differ. See `02_domain_model.md`
> §"Purse mode" for the current enum.

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during spec restructure
- **Refines:** principle #6 of `00_README.md` "Design principles
  (locked)". The original principle ("no custody, no accounts, no
  signing keys held by the app") was correct at the time but too
  coarse for TallyKeep's current shape. This ADR replaces it with
  a four-zone model that is honest about what TallyKeep holds and
  where.

## Context

The original principle stated: *"No custody, no accounts, no
signing keys held by the app. The app is a tool the user drives;
it never owns user funds or identity material. Only third-party
access credentials are stored, encrypted at rest."*

That was true when TallyKeep was conceived as a self-hosted
backend that watched user-controlled wallets and bridged to
custodial providers. It is **no longer accurate** since
ADR-0006 (Purse seed origin) introduced `ON_DEVICE_TK_GENERATED`
Purses — wallets where TallyKeep generates the seed and stores it
in the **Capacitor client's** OS keychain/keystore. The
`purse-upgrade-path` arbitration item further introduces
`ON_DEVICE_USER_IMPORTED` Purses, where TallyKeep stores a key the
user brought from another wallet.

"We never hold keys" is therefore a half-truth. The backend never
holds keys; the Capacitor client may. Saying it the original way
obscures what TallyKeep is actually doing, which is the opposite
of the locked "honest abstraction" principle.

## Decision

The key-custody model is **four zones**, each with explicit
custody facts:

1. **The backend never holds spending keys, ever.** It holds
   descriptors (public-key info), custodial-provider API
   credentials (encrypted at rest with the user's passphrase),
   and configuration. Backend access via OS user account and (in
   personal-use and public phases) an authentication layer. No
   private-key material crosses to or persists in the backend in
   any form.

2. **The Capacitor client may hold spending keys** for the two
   Purse modes that require local signing:
   - `ON_DEVICE_TK_GENERATED` — the client generated the seed during
     Add-Holding.
   - `ON_DEVICE_USER_IMPORTED` — the user imported a seed from another
     wallet via the Purse-detail upgrade flow.
   Storage is **OS-provided secure storage** (iOS Keychain backed
   by Secure Enclave; Android Keystore backed by TEE / StrongBox
   where available). Access is **biometric-gated**. Keys are
   **never transmitted to the backend**, encrypted or otherwise;
   the per-client signing-capability check (ADR-0006) is purely
   local. The browser PWA explicitly cannot hold keys (no
   OS-grade secure storage primitive) and surfaces the operation
   as a gate.

3. **Hardware-wallet keys** (Strongbox; Vault) live on the
   user's hardware device(s). TallyKeep choreographs (PSBT
   export → external signing → signed PSBT re-import →
   broadcast). TallyKeep never sees these keys. The Vault zone
   covers both shapes per ADR-0010:
   - *Single-sig + script-enforced timelock* — one hardware
     wallet, script enforces the wait. PSBT-roundtrip with one
     signer, gated by the chain-side timelock at broadcast.
   - *Multisig (+ optional timelock)* — multiple hardware
     wallets / cosigners, script requires m of n signatures plus
     any timelock. PSBT-roundtrip across multiple signers.

4. **Custodial-provider keys** (Account) are held by the third
   party (Kraken, Bitstamp, Swissquote, future P2P venues).
   TallyKeep reads balances and triggers withdrawals via the
   provider's API. The user manages keys with the provider, not
   with TallyKeep.

## Consequences

- The "no custody" claim stays accurate: TallyKeep never custodies
  user **funds**, and the backend never holds **signing keys**.
  The Capacitor client's per-Holding key storage is custody *of
  the key* in the strict sense, but not custody of the funds — the
  user retains the seed backup, controls the device, controls
  access, and can revoke the device. The framing is honest about
  what TallyKeep does, which is what the brand requires.
- The threat-model "Mobile addendum" in
  `concerns/threat_model.md` already captures most of this;
  that section's relationship to the README's principle
  becomes coherent rather than contradictory.
- The Capacitor-client zone is what enables a UX that doesn't
  force the user to use an external wallet for every payment.
  This is a real product value. The trade-off (Capacitor client
  is a higher-value target than a pure watch-only client) is
  explicit and lives in the threat model.
- The browser PWA can never have full Holding-spend parity with
  the Capacitor build for Purse Holdings, because the browser
  lacks the secure-storage primitive. This was already true; this
  ADR makes it official as a custody-model constraint, not an
  implementation gap.
- Every spec module that touches Holding behavior — chain
  observation, outflow construction, sweep policies, threat model
  — references this ADR for "where does the key live?" rather than
  restating the answer per module.

## Affected files

- `00_README.md` — principle #6 rewritten using the four-zone
  language (this is the load-bearing edit; this ADR's purpose is
  to record the foundational decision)
- `01_architecture.md` — gains an explicit "Key custody model"
  section that mirrors this ADR
- `concerns/threat_model.md` — Mobile addendum's framing updated
  to reference this ADR
- `holdings/` chapters (when the restructure lands per the spec
  reshape) — each Holding type's chapter cites the relevant zone
- `02_domain_model.md` — `seed_origin` documentation cross-refs
  this ADR alongside ADR-0006

## Vocabulary note

Earlier drafts of the spec used "no signing keys held by the app"
as a single phrase. The new vocabulary distinguishes:

- **The app** is no longer a useful unit. Replace with: *the
  backend*, *the Capacitor client*, *the browser PWA client*.
- **Spending keys** specifically — distinct from API credentials
  (custodial), passphrases (unlock), or descriptor watch material
  (public).

Use the precise term per zone. "TallyKeep holds keys" without
qualification is now wrong; "the Capacitor client holds keys for
TallyKeep-managed Purses, in OS secure storage, biometric-gated"
is the correct shape.
