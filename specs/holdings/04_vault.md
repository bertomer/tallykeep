# Vault — long-term, ceremonial Holdings

A **Vault** is a wallet **with multisig** (`m-of-n`), optionally
combined with timelocks (`older()` / `after()`), geographic key
separation, or inheritance setup. By definition: a Vault has
multiple keys, held by multiple parties or devices, requiring
ceremony to spend. *A single-key Holding is not a Vault — that's
a Strongbox.*

**Key custody zone (ADR-0009):** hardware wallets + multisig
co-signers. The keys never live on any TallyKeep surface;
TallyKeep choreographs PSBTs across multiple signers.

## Pre-shipping status

**Multisig descriptor support is the load-bearing missing
piece.** When it ships (per `future_iterations.md` "Multisig
descriptor support"), the Add-Vault flow accepts
`sh(multi(...))`, `wsh(multi(...))`, `tr(multi_a(...))`
descriptors; the analyzer infers the `(required, total)`
parameters from the descriptor and cross-checks against the
user's declared values.

**Open arbitration — what does Add-Vault do *before* multisig
ships?** Two reasonable shapes, both consistent with the
target-state definition above:

- *Block.* Add-Vault is disabled with a clear explanation:
  "Vault Holdings require multisig descriptor support, which
  ships in a later iteration." Cleanest match to "a Vault is
  multisig by definition", no half-state on the books.
- *Accept single-key as a temporary placeholder, surface the
  gap.* Add-Vault accepts a single-key descriptor, but the
  analyzer fires `claimed_multisig_but_single_key` at high
  severity ("yes I know — multisig setup is in progress").
  Lets users carve out a Vault slot now and migrate to multisig
  when it ships. Acknowledges the gap honestly per the
  declared-vs-observable principle.

Captured as `vault-pre-multisig-shape` in
`pre-implementation.md`. Resolved in the brainstorm session that
sharpens the Vault wizard iteration. **Whichever shape is
chosen, "Vault has a single key forever" is not a thing** —
the type's definition is multisig.

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

## Add-Holding flow (target — when multisig descriptor support ships)

1. **Multisig descriptor input.** User provides a multisig
   descriptor (`sh(multi(...))` / `wsh(multi(...))` /
   `tr(multi_a(...))`). Single-key descriptors are rejected with
   redirect to the Strongbox wizard.
2. **Validation.** BDK parses the descriptor. The
   `(required, total)` parameters are extracted directly from
   the descriptor — not declared separately. Optional metadata:
   `timelock_blocks` (declared if known; cross-checked against
   any Miniscript fragment in the descriptor),
   `recovery_setup_notes` (free text).
3. **Cosigner annotation** — for each xpub in the descriptor,
   the user can optionally label which device / co-signer it
   belongs to ("Coldcard in safe", "Cousin Marie's Trezor",
   "Geographic backup — bank deposit box").
4. **Initial scan.** Backend runs the initial scan and surfaces
   balance + history. Declared-vs-observable analysis runs
   immediately.

## Add-Holding flow (current — before multisig support ships)

**Behavior pending arbitration** — see `pre-implementation.md`
`vault-pre-multisig-shape`. Two shapes under consideration
(block vs accept-with-discrepancy); whichever lands, "Vault
with permanent single key" is not the target state.

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

Pre-multisig Send-flow behavior depends on
`vault-pre-multisig-shape` arbitration. If block: no Vault
Send runs. If accept-with-discrepancy: Vault Send mirrors
Strongbox Send (single-key PSBT roundtrip) with the analyzer's
high-severity discrepancy surfaced.

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
- **`claimed_vault_no_timelock` discrepancy** — when the user
  declares timelock-protection but the descriptor has no
  Miniscript `older()` / `after()` fragment, the analyzer
  surfaces this honestly (medium severity). Multisig
  parameters cannot diverge in the same way — they're parsed
  directly from the descriptor, not declared separately.

## Deferred

| Item | Tracked in |
|---|---|
| Multisig descriptor support (the load-bearing missing piece) | `future_iterations.md` "Multisig descriptor support" |
| Multi-signer PSBT coordination UX | `future_iterations.md` "Multisig descriptor support" |
| Retirement plan with on-chain timelock | `future_iterations.md` "Retirement plan with timelock" |
| Vault → anywhere sweeps | `future_iterations.md` "Holding-to-Holding sweeps beyond Account-originated" |
| Inheritance / recovery-path UX surface | post-shipping (touched indirectly via `seed-backup-disclosure` system) |
| Investment layer with structured yield (DLC / LSP-mediated) — a sibling product, not a generalization of Vault | `future_iterations.md` "Investment layer with structured yield" |
