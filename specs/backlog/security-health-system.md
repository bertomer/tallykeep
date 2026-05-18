# Security-health system

- **Captured:** 2026-05 (pre-implementation item
  `seed-backup-disclosure`, plus broader scope from the original
  design_decisions.md §9 Blueprint analysis)
- **Framing review needed before sharpening** (Rémy 2026-05-14,
  during the Strongbox-wizard advisory copy pass). "Security
  health" as a product-design concept the user encounters
  directly — a dedicated Home section / tab grouping these items
  under that heading — is **not yet committed**. The current
  entry assumes that surface; revisit whether the right model is
  (a) the centralised "Security health" surface as sketched, or
  (b) per-Holding inline surfacing (warnings live on the relevant
  Holding's detail page, not in a generic dashboard), or
  (c) some hybrid. Items themselves (missing signing metadata,
  seed-backup-disclosure ack, declared-vs-observable mismatch,
  Blueprint findings, hosted-tier privacy ack) all still need a
  persistence home and a resolution path — that part is firm.
  The user-facing taxonomy is the open question. Wizard-side
  copy in the Strongbox-wizard iteration (`UI/mobile.md` Add
  Holding — Strongbox wizard, Step 1 advisory) deliberately
  avoids forward-referencing any specific surface until this
  resolves.
- **Motivation:** Several persistent items need a shared home so
  the user has one place to see ongoing security concerns, without
  any of them being silently hidden. Includes:
    - Purse seed not backed up (`seed-backup-disclosure`)
    - Strongbox used too frequently for spending (declared vs observable)
    - **Strongbox missing signing metadata** — captured 2026-05-14
      during the Strongbox-wizard design pass. Triggered when a
      Strongbox is imported from a bare xpub (no `[fingerprint/path]`
      brackets — typical of Trezor Suite "Show xpub", Ledger Live,
      Phoenix "Wallet final", BlueWallet xpub export). Receiving
      works; spending may need extra setup at the hardware-wallet
      side because the PSBT `bip32_derivation` field can't be
      populated cleanly. Item copy: *"Your '{vendor} Strongbox' is
      missing signing metadata. Spending later may need an extra
      step on your hardware wallet."* Item has a **"Fix this"**
      affordance opening a small remediation sub-flow with two
      paths: (a) **re-export from your HW wallet** with full
      origin metadata (Coldcard Generic JSON / Sparrow descriptor
      export / Trezor Suite Advanced → Descriptor / Ledger Live
      equivalent / etc.) — user pastes or uploads; backend verifies
      derived addresses still match the existing watched ones; same
      Strongbox record updated in place. (b) **Manual entry**
      (advanced): master fingerprint freetext input (8 hex chars,
      validated case-insensitive), derivation path dropdown
      (BIP 84 `m/84'/0'/0'` default + BIP 49 / BIP 44 / BIP 86 /
      Custom escape hatch). Backend verifies derived addresses
      match before persisting. Most users will pick re-export.
      Strongbox-only — Purse doesn't surface this because TallyKeep
      never signs for a watch-only Purse. The wizard-side
      detection lands with the Strongbox-wizard iteration (parse-
      back warning variant already mocked); the security-health
      surface + the Fix-this sub-flow are this iteration's scope.
    - Vault metadata mismatch
    - Address reuse / dust / round-number outputs (Blueprint findings)
    - Hosted-tier privacy boundary not acknowledged
    - Principles acknowledgment not yet given — informational,
      joins after Onboarding screen 01 skip (per `UI/mobile.md`
      Onboarding Notes 2026-05-10). **This iteration is the
      first to need persistent stack-bound state for unack'd
      items** — the Onboarding + Daily Unlock + Home (empty)
      iteration deliberately deferred the persistence question
      to here. Decide the model when sharpening: a generic
      backend preferences endpoint
      (`GET /api/v1/preferences` + `PUT /api/v1/preferences/{key}`)
      vs an open-items table keyed by item-type (more aligned
      with the Security-health surface). Latter is probably
      cleaner because the items are heterogeneous (acks,
      warnings, dismissals) and benefit from a uniform
      schema.
- **Sketch:** A dedicated section on Home (heading: **"Security
  health"**) and/or a dedicated tab showing all open security and
  acknowledgment items, severity-tagged where applicable,
  dismissible-with-acknowledgment, never silently hidden.
  User-visible heading "Security health" matches banking-grade
  norms (Apple Health "Health checks", "Account health" in retail
  banking). Item copy stays calm; the heading carries the
  seriousness register.
- **Touches:** UI mobile + desktop, backend events, threat model
- **Status:** sketched
- **Milestone:** **pre-shipping** — at least the seed-backup warning
  part is a private-ship requirement (per ADR-0003); broader
  security-health (Strongbox usage, Vault mismatch, hosted-tier
  acknowledgment) can land progressively. Blueprint findings are
  themselves post-shipping, so that part of the security-health
  system follows Blueprint.
- **Notes:** Specify in the dedicated session for pre-implementation
  pre-implementation item `seed-backup-disclosure`. Touches the
  Blueprint feature spec (originally module 05).
