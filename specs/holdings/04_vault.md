# Vault — friction-bearing Holdings

A **Vault** is a wallet whose spending requires intentional
friction — either a script-enforced timelock (CLTV / CSV),
multisig coordination (m ≥ 2 keys), or both. By definition: a
Vault is **not** always-spendable on demand. A single-key wallet
without timelock is a Strongbox, not a Vault.

Friction-as-type-axis (per ADR-0010) replaces the earlier
"multisig-by-definition" framing. A pension setup (single
hardware-wallet key + 10-year CLTV) and a family multisig
(2-of-3 with no timelock) are both Vaults under this definition,
because both encode the same banking-ergonomics mental model:
"money I've put away for the long term, that I cannot just grab."

**Key custody zone (ADR-0009):** hardware wallets — either one
device for the single-sig + timelock shape, or multiple
cosigners for the multisig shape. The keys never live on any
TallyKeep surface; TallyKeep choreographs the PSBT round-trip
(future Send iteration).

## Pre-shipping status

**Vault onboarding ships in v1 for both shapes** (per ADR-0010).
The Add Vault wizard accepts:

- **Single-sig + timelock** descriptors (one key combined with
  a script-enforced CLTV `after()` or CSV `older()` fragment).
- **Multisig** descriptors with or without an additional
  timelock (`wsh(multi(...))`, `wsh(sortedmulti(...))`,
  `tr(multi_a(...))`, and the same wrappers combined with a
  single timelock fragment).

In both cases the Vault is created, the chain is scanned, and
the detail page surfaces balance, activity, and the
unlock-countdown when a timelock is present.

**Vault Send is deferred regardless of shape.** The Vault detail
page's Send affordance is greyed out for all Vault shapes —
designing the Send surface (multi-signer PSBT coordination,
cosigner-status UI, partial-signature collection, chain-side
timelock-check display) is the genuinely hard part and is folded
into the dedicated "Vault Send for all shapes" iteration. Until
then, Vaults receive and observe but do not spend.

## What a Vault does (target state)

- **Observes** the watched descriptor on-chain — balance, UTXOs,
  hygiene flags, declared-vs-observable analysis. Generic
  mechanics in `concerns/observation.md`.
- **Receives** payments at fresh-per-payment addresses derived
  from the descriptor. Verify-on-device for each cosigner that
  has a screen (or for the single signer in the single-sig +
  timelock case).
- **Sends** via PSBT — single-signer flow with chain-side
  timelock check (single-sig + timelock case) OR multi-signer
  coordination (multisig case). Deferred per the pre-shipping
  status above.
- **Surfaces** the outgoing-payment guardrail for Vaults flagged
  `purpose=long_term` (reachable once Send ships).

## Vocabulary detail

The Vault type's domain model carries:

- `descriptor_ids` — one or more Descriptors backing this
  Vault.
- `required_signers` — for multisig, the `m` in `m-of-n`.
  Equals 1 for the single-sig + timelock shape. Parsed from
  the descriptor.
- `total_signers` — the `n`. Equals 1 for the single-sig +
  timelock shape. Parsed from the descriptor.
- `timelock_kind` — `null` / `cltv` (absolute, `after()`) /
  `csv` (relative, `older()`). Parsed from the descriptor's
  miniscript when present. At least one of
  `timelock_kind != null` OR `total_signers ≥ 2` must hold —
  otherwise the wallet is a Strongbox, not a Vault.
- `timelock_value` — block height (CLTV) or block count (CSV).
  Parsed from the descriptor; never user-declared. Read-only on
  Vault detail.
- `cosigner_labels` — optional per-xpub free-text labels set
  post-creation on Vault detail (empty for single-cosigner
  Vaults).
- `recovery_setup_notes` — user-facing free-text notes about
  the recovery / inheritance configuration. Free-form intent
  capture (e.g., "intended for inheritance, untouched until
  2050").
- `purpose` — `long_term` flag (drives the outgoing-payment
  guardrail once Send ships).

A user-declared timelock that isn't enforced on-chain is **not**
a vocabulary field. The `purpose=long_term` flag carries the
long-term-intent signal cleanly; the outgoing-payment guardrail
enforces the discipline. The soft-declaration pattern would have
been a permanent declared-vs-observable mismatch by design (not
a transient one), which would noise out the discrepancy system.
Usage-based feedback (observed spend frequency vs declared
purpose) is the right honest variant of that idea and is
captured in `backlog/usage-based-feedback-for-long-term-vaults.md`.

## Add-Holding flow (v1 — both shapes)

1. **Descriptor input.** User provides a descriptor via paste,
   QR scan (Capacitor only — hidden in browser build per
   absence-of-affordance discipline, ADR-0007), or file upload.
2. **Validation.** BDK parses the descriptor statically (no
   bitcoind round-trip needed — descriptors are self-describing).
   The wizard branches on what's parsed:
   - **Single-sig + timelock** (`wsh(and_v(v:after(...),pk(K)))`
     or the CSV / Taproot variants) → parseback shows the key
     fingerprint, script type, timelock info → user confirms →
     Holding created.
   - **Multisig with or without timelock** (`wsh(multi(...))`,
     `wsh(sortedmulti(...))`, `tr(multi_a(...))`, or the same
     wrappers combined with a single `after()` / `older()`
     fragment) → parseback shows (M, N), cosigners,
     script type, and the parsed timelock when present → user
     confirms → Holding created.
   - **Pure single-sig without timelock** (`wpkh`, `tr` with one
     key, etc.) → inline redirect to the Strongbox wizard.
     Mirror of the Strongbox-wizard's multisig-redirect pattern.
   - **Unsupported form** (bare `multi(...)` without script
     wrapper, multi-path miniscript, exotic constructs,
     unparseable string) → inline error "TallyKeep can't read
     this as a Vault, contact us if you need this."
3. **Initial scan.** Backend scans the descriptor against the
   chain and surfaces balance + history.

Post-creation on Vault detail:

- **Recovery setup notes** — free-text `recovery_setup_notes`.
- **Cosigner annotation** (multisig shape only) — for each xpub
  in the descriptor, label which device / cosigner it belongs
  to ("Coldcard in safe", "Cousin Marie's Trezor", "Geographic
  backup — bank deposit box"). Not applicable to the
  single-sig + timelock shape (one cosigner; the descriptor's
  key fingerprint identifies it).

Vault detail does **not** expose a "set timelock" affordance.
Timelock is purely descriptor-parsed; if a Vault has no on-chain
lock, it has no lock. Long-term-intent is signalled via
`purpose=long_term` (which drives the outgoing-payment guardrail
once Send ships), not via a soft-declaration field.

### Descriptor accept set

All accepted shapes onboard in v1; the deferral is Vault Send,
not Vault onboarding.

- **Single-sig + timelock** (requires miniscript parsing):
  - `wsh(and_v(v:after(<height>),pk(K)))` — single-key + CLTV
    (SegWit v0)
  - `wsh(and_v(v:older(<blocks>),pk(K)))` — single-key + CSV
    (SegWit v0)
  - Taproot equivalents (`tr(...)` with appropriate miniscript
    leaves)
- **Multisig** (plain descriptor constructs, no miniscript
  required):
  - `sh(multi(...))` — legacy P2SH multisig
  - `wsh(multi(...))` / `wsh(sortedmulti(...))` — SegWit v0
    multisig
  - `tr(multi_a(...))` / `tr(sortedmulti_a(...))` — Taproot
    multisig
- **Multisig + timelock** (multisig fragment combined with a
  **single** `after()` / `older()` in miniscript):
  - `wsh(and_v(v:older(...),multi(...)))` and
    `wsh(and_v(v:after(...),multi(...)))` (and `sortedmulti`
    variants)
  - Taproot equivalents (`tr(...)` with multisig+timelock
    miniscript leaves)

Rejected shapes (with explicit error states):

- **Pure single-key without timelock** (`wpkh`, `pkh`,
  single-key `tr`, etc.) → inline redirect to the Strongbox
  wizard. Mirror of the Strongbox-wizard's multisig-redirect
  pattern.
- **Bare `multi(...)` without script wrapper** — not a real
  on-chain script. Inline error: "unsupported descriptor form."
- **Multi-path miniscript** (decaying multisig with thresholds
  that change over time, hashlocks, or-constructs combining
  multiple spending paths with different keys / timelocks) —
  inline error: "unsupported descriptor form, contact us if you
  need this." Multi-path designs are captured in
  `backlog/multi-path-vault-descriptors-hot-path-recovery-path.md`.

The miniscript language is rich; the v1 accept set is
deliberately narrow but covers all five shape variants of
"multisig and/or single-timelock" Vaults. Adding shapes later
(multi-path, hashlocks, decaying thresholds) is additive — a
new parser branch, not a vocabulary change.

### Parseback — five Vault shapes (all v1)

1. **Single-sig + CLTV.** One key + `after(<height>)`.
   Parseback shows the key fingerprint, the script type, and a
   single read-only timelock row: "Unlocks on block X
   (~calendar-date)". All UTXOs at this script unlock
   simultaneously when the chain reaches block X. Vault detail
   surfaces a wallet-wide countdown to that block.
2. **Single-sig + CSV.** One key + `older(<blocks>)`.
   Parseback shows the key fingerprint, the script type, and a
   single read-only timelock row: "Each deposit locks for N
   blocks (~duration)". UTXOs unlock individually, each on the
   block where `confirmation_block + N` is reached. Vault detail
   surfaces a per-UTXO unlock schedule once UTXOs arrive.
3. **Pure multisig.** `m-of-n` keys, no timelock fragment.
   Parseback shows `(M, N)`, cosigner fingerprints (truncated,
   labelable post-creation), and the script type. No timelock
   row. Vault detail surfaces cosigner labels and balance.
4. **Multisig + CLTV.** `m-of-n` keys + `after(<height>)`.
   Parseback shows `(M, N)`, cosigners, script type, plus the
   wallet-wide "Unlocks on block X" row (same shape as #1).
   Vault detail surfaces both the cosigner labels and the
   wallet-wide unlock countdown.
5. **Multisig + CSV.** `m-of-n` keys + `older(<blocks>)`.
   Parseback shows `(M, N)`, cosigners, script type, plus the
   per-deposit "Each deposit locks for N blocks" row (same
   shape as #2). Vault detail surfaces cosigner labels and the
   per-UTXO unlock schedule.

Calendar-date translations are approximate (10-minute block
average drifts ±10–15 % depending on hash-rate conditions). The
parseback shows the block-count or block-height as the primary
number with the date as a muted "~" estimate.

## Outgoing-payment guardrail (locked, currently unreachable)

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
intend this" before proceeding.

The guardrail is configurable via the
`banking.vault_outgoing_warns` feature flag (default `true`;
users can disable from Settings if they want to opt out — full
user-final-authority).

**Currently unreachable** because Vault Send is deferred (see
Pre-shipping status). Becomes reachable when Send ships.

The condition (Holding type + purpose) depends on Holding
metadata that lives in this layer; the *behavior* (the
PaymentRequest API surface that returns `requires_confirmation`)
lives in `concerns/outflow.md` and consults this Holding's
metadata.

## Send flow (deferred)

Vault Send is deferred for v1 regardless of shape. The Vault
detail page's Send affordance is greyed out with "Vault spending
ships in a later iteration."

When Send ships, the flow branches by Vault shape:

**Single-sig + timelock:**
1. **Compose** — destination, amount, fee strategy. Pass the
   guardrail if `purpose=long_term`.
2. **Review.**
3. **Export PSBT** — to the (single) signing device.
4. **Re-import the signed PSBT.**
5. **Broadcast.** Chain-side timelock check at mempool / block
   validation: rejected if the lock hasn't expired, included
   once it has.

**Multisig (with or without timelock):**
1. **Compose** — destination, amount, fee strategy. Pass the
   guardrail if `purpose=long_term`.
2. **Review.**
3. **Export PSBT** — to the first cosigner's device.
4. **Re-import partially-signed PSBT** — collect signature 1.
5. **Export PSBT** — to the next cosigner.
6. **Repeat** until `m` signatures are collected.
7. **Finalize and broadcast** — with any timelock check applied
   at validation time.

## Receive flow

Derive the next unused address from the descriptor. For
single-sig + timelock Vaults, verify-on-device on the (single)
hardware wallet. For multisig Vaults, verify-on-device for each
cosigner that has a screen; for geographically separated
cosigners, only those physically reachable at receive time need
to verify, the others can verify retrospectively at the next
spend ceremony.

Share the address (plus BIP21 URI) externally.

## SweepPolicy participation

Per `concerns/sweep_policies.md`:

| Direction | Feasibility |
|---|---|
| Vault as destination | Always allowed. Common destination for "promote to long-term" sweeps from Strongbox or Account. |
| Vault as source | Not auto. Reduces to a scheduled reminder that prepares a PSBT awaiting external signing (single signer for the single-sig + timelock shape, plus the timelock check at broadcast; multi-signer coordination for multisig). |

Vault-source sweeps land post-shipping alongside Vault Send.

## Type-specific safeguards

- **Vault outgoing-payment guardrail** (above) — fires for any
  `purpose=long_term` Vault outflow. The load-bearing
  user-discipline mechanism for the type; operates independently
  of whether the descriptor encodes a timelock. Currently
  unreachable because Send is deferred.
- **Usage-based feedback (deferred)** — for `purpose=long_term`
  Vaults whose observed outflow frequency contradicts the
  declared long-term intent, surface a security-health item
  suggesting an on-chain timelock or migration to Strongbox. The
  honest declared-vs-observable formulation (`purpose=long_term`
  declared, observed N spends/year). Captured in
  `backlog/usage-based-feedback-for-long-term-vaults.md`; lives
  in the broader security-health system pending
  `seed-backup-disclosure` arbitration.

Multisig parameters cannot diverge from the descriptor —
they're parsed, not declared. Same for any present timelock
(read-only post-parse).

## Deferred

| Item | Tracked in |
|---|---|
| Multisig descriptor support + Vault Send (single-sig + timelock and multisig flows together) | `backlog/vault-send-for-all-shapes.md` |
| Strongbox → Vault promotion (single-Holding type-relabel when adding multisig to the descriptor) | `backlog/vault-send-for-all-shapes.md` |
| Multi-path Vault descriptors (hot path + recovery path) | `backlog/multi-path-vault-descriptors-hot-path-recovery-path.md` |
| Usage-based feedback for long-term Vaults | `backlog/usage-based-feedback-for-long-term-vaults.md` |
| Vault → anywhere sweeps | `backlog/holding-to-holding-sweeps-beyond-account-originated.md` |
| Inheritance / recovery-path UX surface | post-shipping (touched indirectly via `seed-backup-disclosure` system) |
| Investment layer with structured yield (DLC / LSP-mediated) — a sibling product, not a generalization of Vault | `backlog/investment-layer-with-structured-yield-the-v5-sketch.md` |
