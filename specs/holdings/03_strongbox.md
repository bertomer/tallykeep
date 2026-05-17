# Strongbox — hardware-wallet Holdings

A **Strongbox** is a wallet whose spending key lives on the
user's external signing device — a hardware wallet (Coldcard,
Trezor, Ledger, Jade, BitBox) or an airgapped laptop. The user
holds the key; signing requires deliberate action on the
external device.

**Key custody zone (ADR-0009):** hardware wallet. The key
**never** lives on any TallyKeep surface — not the backend, not
the Capacitor client, not the browser PWA. TallyKeep
choreographs the PSBT round-trip; the user is the bridge.

## What a Strongbox does

- **Observes** the watched descriptor on-chain — balance, UTXOs,
  hygiene flags, declared-vs-observable security analysis.
  Generic mechanics in `concerns/observation.md`.
- **Receives** payments at fresh-per-payment addresses derived
  from the hardware-wallet descriptor. Verify-on-device required
  before sharing (see Receive flow below).
- **Sends** via PSBT export → external sign → re-import →
  broadcast.
- **Participates** in SweepPolicies as a source via a scheduled-
  reminder pattern (no auto-execution; the user is in the
  signing loop). See `concerns/sweep_policies.md`.

## Vocabulary detail

The Strongbox type's domain model carries:

- `descriptor_ids` — one or more Descriptors backing this
  Strongbox.
- `signing_device_label` — user note, e.g. "Coldcard Mk4 in
  safe". Free-form text; surfaced in detail views.

## Add-Holding flow

1. **Hardware wallet descriptor input.** The user provides a
   descriptor exported from their hardware wallet. Methods:
   paste, QR scan (via Capacitor camera), or file upload
   (browser).
2. **Validation.** BDK parses and canonicalizes. Strongbox
   accepts **pure single-key descriptors only**, with no
   script complexity:
   - Accepted: `pkh()`, `sh(wpkh())`, `wpkh()`, single-key
     `tr()`.
   - Rejected: multisig (`multi`, `sortedmulti`, `multi_a`,
     etc.) → inline redirect to the Vault wizard. Already
     locked.
   - Rejected: single-key wrapped in miniscript with a timelock
     fragment (`wsh(and_v(v:after(...),pk(K)))`,
     `wsh(and_v(v:older(...),pk(K)))`, Taproot equivalents)
     → inline redirect to the Vault wizard. A timelock makes
     the wallet a Vault per ADR-0010 (Vault = friction-bearing
     = multisig OR timelock OR both); Strongbox is the
     always-spendable single-key tier.
3. **Naming + metadata.** User-facing name and the
   `signing_device_label` note.
4. **Initial scan.** Backend runs the descriptor through the
   initial chain scan (`concerns/observation.md`) and surfaces
   balance + history.

## Send flow — PSBT roundtrip

Five steps. TallyKeep choreographs; the hardware wallet signs.

1. **Compose.** User picks the destination (raw address or
   pasted BIP21), amount in sats or "max", fee strategy. The
   backend builds the unsigned PSBT via the generic
   PSBT-construction machinery (`concerns/outflow.md`).
2. **Review.** Confirmation screen shows destination, amount,
   fee, expected confirmation time. The Review screen displays
   the destination address in plain monospace with first and
   last characters highlighted, **before** PSBT construction
   commits, so a clipboard-hijack attack on the source string is
   visible before signing.
3. **Export to signing device.** PSBT exports via:
   - **File download** — binary `.psbt` file readable by
     Sparrow, Specter, Electrum, ColdCard, Jade Desktop, and
     others. Always available.
   - **Single QR code** — for PSBTs under ~1000 bytes, gated by
     `banking.psbt_qr.enabled`.
   - **Multi-frame QR (BBQr / UR2)** — deferred to
     `future_iterations.md` "PSBT-by-QR roundtrip on mobile".

   The user signs **outside** TallyKeep — on the hardware wallet
   device's screen. The user is prompted to **verify the
   destination on the signing device's screen** before signing.
   This is the actual defense against clipboard-hijack attacks
   (per `concerns/threat_model.md` S7); software-only display is
   spoofable, hardware-screen verification is not.
4. **Re-import the signed PSBT.** User submits the signed PSBT
   (base64) or fully finalized transaction hex back to
   TallyKeep. The backend parses, verifies the signed PSBT
   matches the original request's input set and outputs,
   finalizes to a raw transaction, and stores it.
5. **Broadcast.** TallyKeep broadcasts via the local bitcoind.
   The reconcilability gauntlet enforces no "Sent ✓" before
   broadcast acknowledgement; confirmation depth shown verbatim
   on the resulting LedgerEntry.

The user can cancel at steps 1–3 (status `DRAFT`,
`AWAITING_SIGNATURE`, `AWAITING_BROADCAST`). Cancellation after
broadcast is impossible on-chain; replacement is via RBF
(`future_iterations.md` "Replace-By-Fee (RBF) support") when
that iteration ships.

## Receive flow

1. Derive the next unused address from the hardware-wallet
   descriptor.
2. **Verify-on-device.** Prompt the user: *"Open your hardware
   wallet, navigate to the receive screen, and confirm the
   address matches."* This step defends against malware swapping
   the address between display and copy.
3. Display the address (and a BIP21 URI with optional amount /
   label) as text + QR for the sender to scan.

Both the address display in TallyKeep and the address on the
hardware-wallet screen must match before the user shares the
address externally. If they don't, the user has been targeted
and should not proceed.

## Hardware-wallet compatibility

Pre-shipping target:

| Signer | Supported via |
|---|---|
| ColdCard Mk4 | File over USB or SD; single QR if small |
| Trezor Model T | File over USB |
| Ledger Nano S/X | File over USB |
| Jade | File over USB; single QR if small |
| BitBox02 | File over USB |
| Sparrow (as signer) | File |
| Electrum (as signer) | File |
| Airgapped Bitcoin Core | File transfer |

The current common denominator is **file export**. Multi-frame
QR for QR-friendly signers (BBQr / UR2) lands when the
PSBT-by-QR iteration ships.

## PSBT format

- **BIP 174 v0** for maximum compatibility. BIP 370 (PSBT v2)
  considered later once hardware support is broader.
- Non-witness UTXO data embedded for legacy signer
  compatibility.
- BIP 32 derivation info on all inputs (required by most
  hardware signers).
- BIP 32 derivation info on change outputs so signers can
  verify the change path matches the source wallet (prevents
  change-output confusion attacks).

## SweepPolicy participation

Per `concerns/sweep_policies.md`:

| Direction | Feasibility |
|---|---|
| Strongbox as destination | Always allowed (receive is public). The bread-and-butter destination for Account → Strongbox sweeps. |
| Strongbox as source | Not auto. Reduces to a **scheduled reminder** that prepares a PSBT awaiting the user's external signature on the hardware wallet. Resumes the standard send flow at step 3. |

Strongbox-source sweeps land post-shipping. Pre-shipping,
Account → Strongbox outflow sweeps are the primary use case —
the minimum-exposure trading pattern: BTC bought at the venue is
swept into Strongbox (self-custody) as fast as policy allows.

## Type-specific safeguards

- **Verify-on-device** required on receive (defends against
  clipboard-hijack on the display path).
- **Strongbox frequent-usage warning** — when a Strongbox is
  used for daily-spending-frequency outflows above some
  threshold, the security-health system surfaces a warning that
  the user's declared `signing_model=hardware_offline` may not
  match observed behavior. Lives in the broader security-health
  system (pending arbitration `seed-backup-disclosure`).

## Deferred

| Item | Tracked in |
|---|---|
| Multi-frame QR PSBT roundtrip | `future_iterations.md` "PSBT-by-QR roundtrip on mobile" |
| Replace-By-Fee (RBF) | `future_iterations.md` "Replace-By-Fee (RBF) support" |
| Strongbox → anywhere sweeps (with scheduled-reminder UX) | `future_iterations.md` "Holding-to-Holding sweeps beyond Account-originated" |
| Strongbox-frequent-usage warning in security-health | `pre-implementation.md` `seed-backup-disclosure` (full security-health system) |
| Multisig descriptor support (would extend Strongbox into Vault territory) | `future_iterations.md` "Multisig descriptor support" |
 support (would extend Strongbox into Vault territory) | `future_iterations.md` "Multisig descriptor support" |
