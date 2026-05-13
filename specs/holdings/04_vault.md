# Vault — long-term, ceremonial Holdings

A **Vault** is a wallet under additional structural protection
beyond a single hardware-wallet key: multisig (`m-of-n`),
timelocks (`older()` / `after()`), geographic key separation,
inheritance setup. Accessing the funds requires a ceremony —
multiple signers, possibly across locations.

**Key custody zone (ADR-0009):** hardware wallets + multisig
co-signers. The keys never live on any TallyKeep surface;
TallyKeep choreographs PSBTs across multiple signers.

## Pre-shipping status

**Multisig is mostly deferred.** The current build:

- Accepts Vault Holdings with multisig metadata fields populated
  (declared `custody_model=self_multisig`, declared
  `required_signers` and `total_signers`).
- Accepts only **single-key descriptors** at the descriptor
  layer. Even when the user declares a multisig Vault, the
  underlying BDK descriptor today is single-key.
- Surfaces the discrepancy honestly via the declared-vs-
  observable analyzer (`concerns/observation.md`). The
  `claimed_multisig_but_single_key` discrepancy fires at high
  severity. The user can dismiss with "yes, I know — the
  multisig setup is in progress" if intentional.

Full multisig descriptor support is captured in
`future_iterations.md` "Multisig descriptor support". When that
iteration ships, Vault Holdings will accept `sh(multi(...))`,
`wsh(multi(...))`, `tr(multi_a(...))` descriptors, the analyzer
will infer the multisig parameters from the descriptor, and the
discrepancy goes away.

## What a Vault does (target state)

- **Observes** the watched descriptor on-chain — balance, UTXOs,
  hygiene flags, declared-vs-observable analysis (including
  timelock and multisig inference). Generic mechanics in
  `concerns/observation.md`.
- **Receives** payments at fresh-per-payment addresses derived
  from the descriptor. Verify-on-device for each co-signer that
  has a screen.
- **Sends** via PSBT with multisig coordination — collect
  signatures from `m` of `n` co-signers, finalize, broadcast.
- **Surfaces** the outgoing-payment guardrail (see below) for
  Vaults declared with `purpose=long_term`.

## Vocabulary detail

The Vault type's domain model carries:

- `descriptor_ids` — one or more Descriptors backing this
  Vault.
- `required_signers` — for multisig, how many keys to spend
  (the `m` in `m-of-n`).
- `total_signers` — the `n`.
- `timelock_blocks` — if a CSV / CLTV timelock is part of the
  setup.
- `recovery_setup_notes` — user-facing free-text notes about the
  recovery / inheritance configuration.

## Add-Holding flow

1. **Descriptor + multisig metadata.** User provides:
   - A descriptor (single-key today; multisig descriptors when
     that iteration ships).
   - `required_signers` and `total_signers` (declared values).
   - `timelock_blocks` if applicable.
   - `recovery_setup_notes` free text.
2. **Validation.** BDK parses the descriptor. The declared
   multisig parameters are stored but not enforced against the
   descriptor today.
3. **Initial scan.** Backend runs the initial scan and surfaces
   balance + history. Declared-vs-observable analysis runs
   immediately; the user sees any discrepancy.

## Outgoing-payment guardrail (locked)

The Vault is the strongest user-held storage tier; outgoing-
from-Vault is a deliberate ceremony, not a routine action. The
safeguard is a **warning**, not a hardcoded block (per the
"warn-don't-block" discipline TallyKeep uses for all
user-final-authority decisions).

Trigger: a PaymentRequest from a Vault Holding with
`purpose=long_term`. The PaymentRequest creation flow returns
`requires_confirmation=true` with a clear explanation:

> *You are composing an outgoing payment from a Vault declared
> as long-term. This is unusual; confirm you intend this.*

The frontend renders this as a modal with explicit "yes, I
intend this" before proceeding. The user re-submits with
explicit acknowledgement to proceed.

The guardrail is configurable via the `banking.vault_outgoing_warns`
feature flag (default `true`; users can disable from Settings if
they want to opt out — full user-final-authority).

The condition (Holding type + purpose) depends on Holding
metadata that lives in this layer; the *behavior* (the
PaymentRequest API surface that returns `requires_confirmation`)
lives in `concerns/outflow.md` and consults this Holding's
metadata.

## Send flow (target — multisig)

When multisig descriptor support ships, the send flow becomes:

1. **Compose** — destination, amount, fee strategy. Pass the
   guardrail (above) if `purpose=long_term`.
2. **Review** — same as Strongbox.
3. **Export PSBT** — to the first co-signer's device.
4. **Re-import partially-signed PSBT** — collect signature 1.
5. **Export PSBT** — to the next co-signer.
6. **Repeat** until `m` signatures are collected.
7. **Finalize and broadcast** — once `m`-of-`n` is reached.

The pre-shipping build treats Vault sends the same as Strongbox
sends (single-key PSBT roundtrip), with the
declared-vs-observable analyzer making the discrepancy visible.

## Receive flow

Same as Strongbox: derive next unused address, verify on each
co-signer's device that has a screen, share the address (plus
BIP21 URI) externally.

For Vaults with geographically separated co-signers, only the
co-signers physically reachable at receive time need to
verify-on-device; the others can verify retrospectively when
they're consulted for the next spend. The user is responsible
for that workflow; TallyKeep surfaces the address but doesn't
choreograph the cross-location verification.

## SweepPolicy participation

Per `concerns/sweep_policies.md`:

| Direction | Feasibility |
|---|---|
| Vault as destination | Always allowed. Common destination for "promote to long-term" sweeps from Strongbox or Account. |
| Vault as source | Not auto. Reduces to a scheduled reminder that prepares a PSBT awaiting multisig coordination. Multi-signer flow is post-shipping. |

Vault-source sweeps land post-shipping alongside multisig
descriptor support.

## Type-specific safeguards

- **Vault outgoing-payment guardrail** (above) — fires for any
  `purpose=long_term` Vault outflow.
- **`claimed_vault_no_timelock_no_multisig` discrepancy** — when
  the user declares a Vault but the descriptor shows neither
  timelock nor multisig, the analyzer surfaces this honestly
  (medium severity).
- **`claimed_multisig_but_single_key` discrepancy** — high
  severity. Fires during the pre-shipping period for every
  declared-multisig Vault, because descriptors are single-key
  today. Dismissible with "yes, multisig setup is in progress."

## Deferred

| Item | Tracked in |
|---|---|
| Multisig descriptor support (the load-bearing missing piece) | `future_iterations.md` "Multisig descriptor support" |
| Multi-signer PSBT coordination UX | `future_iterations.md` "Multisig descriptor support" |
| Retirement plan with on-chain timelock | `future_iterations.md` "Retirement plan with timelock" |
| Vault → anywhere sweeps | `future_iterations.md` "Holding-to-Holding sweeps beyond Account-originated" |
| Inheritance / recovery-path UX surface | post-shipping (touched indirectly via `seed-backup-disclosure` system) |
| Investment layer with structured yield (DLC / LSP-mediated) — a sibling product, not a generalization of Vault | `future_iterations.md` "Investment layer with structured yield" |
