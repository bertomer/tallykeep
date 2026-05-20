# Holding-detail Settings reorganisation

- **Captured:** 2026-05-21 (Rémy, after hand-testing the Purse +
  Strongbox detail Settings tabs and noting the flat-list-of-cards
  shape is getting hard to scan).
- **Motivation:** Settings on every Holding-detail page is currently
  a flat list of 6-9 cards (Wallet, Display name, Descriptor /
  API keys, Recovery phrase / Signing device label, Auto-sweep,
  Lightning, Danger zone, plus type-specific bits). Adding more
  affordances over time without thematic grouping is making it
  harder for the user to understand *what kind of thing* each card
  represents, and the absence of grouping doesn't reflect the real
  structural axes that exist across Holdings — every Holding has a
  watching surface, an identity surface, and a rules-and-automation
  surface. Surfacing those axes as sections (with consistent
  cross-type vocabulary) is also a "banking-grade ergonomics" win:
  Revolut / N26 / Boursorama all group settings into named sections
  rather than rendering a long flat list.

- **Sketch:** three named sections in Settings, applied lockstep
  across Account / Purse / Strongbox / Vault detail pages. **Labels
  are not yet locked** — section names need a dedicated brainstorm
  before sharpening. Candidates and the tension behind each:

    1. **Watching surface** — the public-side data that lets
       TallyKeep observe this Holding on its underlying network.
       Account: read-only API key. Purse / Strongbox: descriptor.
       Vault: descriptor set. The genuinely-unifying abstraction
       across types; spec doesn't currently surface it.
       Candidate labels: "Connection" / "Watching" / "Observation".
       **Tension:** Account isn't *only* a watching surface —
       trade-scoped and withdraw-scoped credentials also live there
       (sweep policies need withdrawal-scoped keys). Either
       broaden the section ("Connection" covers descriptors AND
       the multi-scoped API key set) or split off a separate
       "Operating credentials" section only for Account. Lean:
       broaden. Honesty cost is small, cross-type consistency is
       the win.

    2. **About this Holding / Identity** — user-editable labels +
       descriptor-parsed read-only properties. Display name
       (Rename), signing-device label (Strongbox), cosigner labels
       (Vault), recovery-setup notes (Vault), M-of-N parameters
       (Vault, read-only), timelock characteristics (Vault,
       read-only). **Tension:** mixes editable affordances and
       read-only properties in one section — fine if the section
       name is broad enough ("About this Holding" works; "Identity"
       reads odd for a wallet), deliberate not accidental. The user
       sees CTAs on some rows and not others; needs to be by design.

    3. **Rules / Automation / Money rules** — the configurable
       behaviour layer. Auto-sweep policies (all types). Lightning
       activation (Purse — capability toggle; permanently gated
       for Strongbox / Vault). Account: deposit / withdraw
       whitelist + the API-key-scope question (could live here
       rather than in "Connection"; needs the brainstorm).
       **Tension on naming:** Rémy's first pass was "Treasury
       management" — captures the substance but reads as
       corporate-finance jargon; ordinary self-custodians don't
       speak that vocabulary. Banking-grade ergonomics means
       borrowing banking apps' clarity, not their CFO-vocabulary.
       Plainer candidates: "Automation", "Rules", "Money rules".
       Locked vocabulary still to settle in the brainstorm.

- **Out-of-scope insights worth recording** (so the sharpening
  session doesn't re-litigate):

    - **Receive capabilities (QR / file / BIP21) are NOT settings.**
      They're behaviours of the Receive flow, not per-Holding
      configurables. Putting them in Settings would either need
      them to become real toggles (they aren't) or treats them as
      documentation, which belongs in a help / about surface, not
      the action-oriented Settings tab. Same for "no auto-send for
      Strongbox / Vault / watch-only Purse" — type behaviour, not a
      setting. Surface in Wallet card meta line, future Help
      affordance, or the Send/Receive flow itself.
    - **Lightning's home is genuinely ambiguous.** Is it
      "Connection" (a new protocol/channel)? "Rules" (a Holding
      capability toggle alongside sweep policies)? Its own
      "Payments" section? Weak lean: Rules. Could defensibly be
      its own one-line section. Settle in the brainstorm.

- **Touches:** all four detail pages — `UI/mobile.md §Account
  detail` / `§Purse detail` / `§Strongbox detail` / `§Vault detail`
  (the last one not yet written). All Settings mockup files for
  the four types. Cross-type vocabulary lock for the section
  labels. `UI/README.md §Holding detail` per-type bullets need
  the new section structure named.

- **Status:** idea (needs a dedicated brainstorm session to settle
  the section labels + per-type contents before sharpening as an
  iteration).

- **Milestone:** TBD — sequencing options:
    - **Option A:** sharpen + ship as a cross-type iteration
      AFTER Vault detail lands (touches all four pages in
      lockstep, one design pass).
    - **Option B:** settle the structure during the Vault-detail
      brainstorm so Vault doesn't ship with the old flat
      structure and need a same-week reorg.
    - Lean toward (B) for sequencing economy — Vault detail will
      need a Settings tab from scratch anyway, so designing it in
      the new structure is cheaper than designing it old then
      redesigning it new.

- **Notes:**
    - Discovered while reviewing the Purse-detail validated
      mockups + the Strongbox-detail iteration in flight (Rémy
      noted "it feels like all these stuff are in a bucket of
      settings, but while reading it it's hard to understand what
      this is all about").
    - Related but separate concerns surfaced in the same
      conversation, not folded into this entry: (a) Account
      detail's Rename CTA may still be inside Danger zone while
      Purse / Strongbox have it pulled out — lockstep drift to
      fix on its own; (b) the frontend `/holding/[id]/+page.svelte`
      type-dispatch shape needs a triage pass to confirm whether
      the dispatch is config-driven (drift-resistant) or
      per-type-branches (drift-prone) — Rémy tracking both
      separately.
    - The Rename-Danger-zone drift specifically is evidence that
      the "cross-type lockstep" intent in iteration scopes
      doesn't always land cleanly in code. The sanity sweep is
      mechanical (file existence, mtime, backtick refs); it
      doesn't catch "iteration said X applies cross-type but the
      Account file wasn't touched". The reorganisation iteration
      will need explicit per-type checklist acceptance criteria
      to avoid the same shape of miss.
