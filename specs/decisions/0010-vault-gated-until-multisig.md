# ADR-0010 — Vault type definition + Vault Send deferral

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during the Vault-wizard brainstorm session
- **Migrated from:** `pre-implementation.md` slug
  `vault-pre-multisig-shape`

## Context

The original spec defined Vault as multisig-by-definition: *"A
single-key Holding is not a Vault — that's a Strongbox."* The
implementation reality is that multisig descriptor support is
not in the current backend; it lives in `future_iterations.md`
"Multisig descriptor support". The question was what Add-Vault
does during the gap.

Two narrow shapes were considered first (block-the-whole-type
vs. accept-single-key-with-discrepancy). Both were rejected
during the brainstorm in favor of a deeper rethink of the type's
defining axis.

**The deeper question that surfaced:** is the Vault type axis
*number of keys* (single vs multi) or *friction at spend time*
(always-spendable vs ceremony-or-wait)? The original spec
implicitly chose key-count and put timelock as a secondary
attribute. Examining the alternative — friction as the type
axis — produced a cleaner mapping to the banking-ergonomics
target user, who thinks in terms of "money I can grab" vs
"money I've put away."

## Decision

**Two-part decision:**

1. **Vault is redefined as the friction-bearing Holding.** A
   Vault is a wallet whose spending requires intentional
   friction — script-enforced timelock (CLTV `after()` or CSV
   `older()`), multisig coordination (m ≥ 2), or both. Single-key
   wallets without timelock are Strongboxes, not Vaults. Wallets
   with a script-enforced timelock are Vaults regardless of key
   count.

2. **Vault onboarding ships in v1 for both shapes; Vault Send is
   deferred.** The Add Vault wizard accepts both single-sig +
   timelock and multisig (with or without timelock) descriptors.
   The Vault detail page surfaces balance, activity, and
   unlock-countdown information. **Vault Send is deferred** to
   the dedicated Vault-Send iteration — the genuinely hard
   surface is multi-signer PSBT coordination, cosigner-status
   UI, partial-signature collection, and the chain-side
   timelock-check display, all of which deserve their own
   design pass. The deferral is shape-agnostic: even the
   single-sig + timelock case waits, so the detail page surface
   is designed once for all shapes when Send arrives.

The Add Vault wizard accepts single-sig + timelock descriptors
AND multisig descriptors (with or without an additional
timelock) in v1. Pure single-key descriptors without timelock
are rejected with redirect to the Strongbox wizard (mirror of
the Strongbox-wizard's multisig redirect). Multi-path miniscript
(or-trees, decaying multisig, hashlocks) is rejected with an
"unsupported form, contact us" message.

## Reasoning

### Why friction-as-type-axis wins for TallyKeep

1. **Banking-ergonomics design principle.** The target user
   thinks in friction terms ("locked away vs. accessible"), not
   in key-count terms. A single-sig + 10-year-timelock pension
   maps more naturally to "Vault" than to "Strongbox with extra
   conditions." Multisig coordination is also friction, just a
   different shape. The user-mental-model axis is intentional,
   not multi-party-specifically.

2. **Display surface consolidates.** Unlock-countdown UI, the
   long-term-purpose framing, and the outgoing-payment guardrail
   live on Vault detail only. Under the key-count axis (single
   = Strongbox always, multi = Vault always), the
   unlock-countdown UI would duplicate across Strongbox detail
   (for timelocked Strongboxes) and Vault detail.

3. **Strongbox stays simple.** Always-spendable single-key
   hardware-wallet wallet. No internal timelock variants. The
   Strongbox-frequent-usage warning and the
   savings-account-with-key analogy stay clean.

4. **Multisig convention exists in crypto-native products
   (Casa, Bitkey, Unchained, Sparrow's multisig flow), but
   TallyKeep does not target those users primarily.** The
   convention break is real but bounded. Bitcoin-native users
   arriving from those products may briefly expect "Vault =
   multisig"; the wizard's introductory copy resolves the
   ambiguity quickly.

### Why ship onboarding for both shapes now (rather than gate multisig)

1. **The use cases are both real.** Pension / inheritance /
   time-locked savings (single-sig + timelock), and family /
   geographically-distributed / hot+recovery storage
   (multisig). Both are legitimate Vault setups; neither has
   a strong case for being deferred behind the other.

2. **Multisig onboarding is structurally cheaper than
   single-sig + timelock.** Pure multisig descriptors
   (`wsh(multi(...))`, `wsh(sortedmulti(...))`,
   `tr(multi_a(...))`) are plain descriptor-level constructs;
   they don't need miniscript parsing. Single-sig + timelock
   does need miniscript (`and_v` / `older` / `after`
   fragments). Once we commit to miniscript parsing for the
   single-sig + timelock case, adding multisig branches to
   the parser is incremental — and the multisig-without-
   timelock variant doesn't even need miniscript.

3. **The genuinely hard surface is Vault Send.** Multi-signer
   PSBT coordination, cosigner-status UI, partial-signature
   collection, chain-side timelock-check display — these
   deserve their own design pass with all Vault shapes in
   hand. Deferring Send (rather than multisig onboarding) is
   the honest scope cut.

4. **Onboarding parity reduces wizard cognitive load.** A
   Vault wizard that accepts only single-sig + timelock and
   tells multisig users "supported but not yet" is harder to
   reason about than one that accepts all v1 Vault shapes
   and rejects only the genuinely unsupported (pure
   single-key without timelock → Strongbox; multi-path
   miniscript → contact us). Two rejection paths, both
   honest.

5. **Deferring this gets costlier with time.** A Vault
   ecosystem built one-shape-only would push toward
   shape-specific UI patterns that would need refactoring
   when the other shape arrives. Shipping the type-system
   call together with onboarding for both shapes locks in β
   cleanly.

6. **Rollback is cheap as long as Vault Send isn't built
   yet.** If the call proves wrong, removing either shape
   from Vault later costs the rejected descriptors themselves
   and the type's accept-set documentation — small surface.
   Send hasn't shipped; no Send-flow code to refactor.

### Why narrower options were rejected

- **Block the whole Vault type until multisig ships.** Pension
  use case waits for nothing in particular. Designed surface
  duplicates anyway when both shapes arrive.
- **Accept single-key as a temporary placeholder with
  discrepancy warning.** Permanent declared-vs-observable
  mismatch by design; noise out the discrepancy system. (This
  was the original arbitration question before the deeper
  rethink.)
- **Extend Strongbox to single-sig + timelock (γ in the
  brainstorm).** Industry-convention-cleaner but stretches
  Strongbox's "always-spendable savings" semantics and
  duplicates the unlock-countdown display across types. The
  user-mental-model axis wins.
- **Ship single-sig + timelock onboarding only; defer multisig
  onboarding.** Initially proposed, then rejected after design
  draft revealed that the multisig parseback was as cheap to
  ship as single-sig + timelock — multisig descriptors don't
  need miniscript parsing, while single-sig + timelock does.
  The deferral didn't match the actual scope difficulty
  ordering. The true difficulty wall is Vault Send, not
  multisig onboarding.

## Consequences

- `holdings/04_vault.md` is rewritten: new opening definition
  (friction-as-type), descriptor accept set covers all v1
  shapes (single-sig + timelock; multisig with or without
  timelock), parseback rules cover all five shape variants
  (single-sig + CLTV, single-sig + CSV, pure multisig,
  multisig + CLTV, multisig + CSV). Vault Send is deferred
  shape-agnostic — one Vault detail / send surface designed
  together when Send is on the table.
- `holdings/03_strongbox.md` is tightened: accepts only pure
  single-key descriptors (no timelock fragment). Timelock-bearing
  descriptors redirect to the Vault wizard. Mirror of the
  multisig-redirect pattern, symmetric.
- ADR-0009 (key custody model) is updated: the Vault custody
  zone covers both single-key hardware-wallet + script timelock
  AND multisig cosigners. Both ship in v1 onboarding.
- The Add Holding picker is unchanged. The Vault tile routes to
  the Vault wizard, which accepts any v1 Vault shape and rejects
  only pure single-key (redirect to Strongbox) and multi-path
  miniscript (unsupported-form error).
- Vault detail page ships in v1 with balance, activity, and
  unlock-countdown (CLTV: wallet-wide countdown to the unlock
  block; CSV: per-UTXO unlock schedule once UTXOs land).
  Cosigner labels for multisig Vaults are post-creation
  Detail-page edits. Send affordance is greyed-out with "Vault
  spending ships in a later iteration."
- The Vault outgoing-payment guardrail (`purpose=long_term`
  triggers a confirmation modal on send) is unreachable in v1
  because Vault Send is deferred; it becomes reachable when
  Vault Send ships.
- The "promote a Strongbox to a Vault" path is captured for
  the Vault-Send iteration as a single-Holding type-relabel
  migration. Straightforward when adding multisig to the
  descriptor (no on-chain action); single-sig + timelock
  promotion would require spending to a new script, so the
  promotion-migration story is for the multisig direction only.

**What this ADR does not decide.** The exact Vault Send flow
(single-sig signing path with chain-side timelock check vs
multi-signer coordination path with optional timelock check),
the cosigner-coordination UX, and the Strongbox→Vault promotion
migration are design surface for the future "Vault Send for all
shapes" iteration.

## Affected files

- `holdings/04_vault.md` — rewritten under β; v1 accept set
  covers single-sig+timelock and multisig (+ optional timelock)
- `holdings/03_strongbox.md` — accept-set tightened to reject
  timelock-bearing descriptors
- `pre-implementation.md` — slug `vault-pre-multisig-shape`
  removed (closed by this ADR)
- `decisions/0009-key-custody-model.md` — Vault custody zone
  updated to cover both single-sig+timelock and multisig
- `UI/README.md` — Add Holding section reflects β with v1
  onboarding for both Vault shapes
- `UI/mobile.md` — gains `## Add Holding — Vault wizard`
  section with gauntlet answers
- `UI/mockups/mobile_add_holding_vault_*.html` — wizard mockups
  for v1 (input + redirect-error + unsupported-form-error +
  five parseback variants + success)
- `UI/mockups/index.html` — mockup-index array updated
- `next_iteration.md` — Vault-wizard iteration scope: full
  v1 onboarding for both shapes
- `future_iterations.md` — entry narrows to "Vault Send for
  all shapes"
