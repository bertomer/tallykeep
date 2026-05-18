# Purse upgrade path (watch-only → on-device-imported)

- **Captured:** 2026-05-13 (Purse-wizard design pass; sharpened
  out of the original `pre-implementation.md` `purse-upgrade-path`
  entry on 2026-05-14 once the design parts stabilised)
- **Motivation:** When a `WATCH_ONLY` Purse becomes degraded —
  source wallet shutting down (Mutiny), service deprecating
  (Phoenix on some platforms), or the user just wants to spend
  from TallyKeep — let the user import the source wallet's seed
  so the *same* Purse becomes spendable. Better for the brand
  than forcing a fresh `ON_DEVICE_TK_GENERATED` Purse + funds
  migration.
- **Sketch:**
    - **Where it lives.** Affordance on the **Purse Detail
      page**, not in the Add wizard. Watch-only Purses surface
      a discoverable but greyed-out Send control; tapping
      presents the upgrade flow ("Add the keys to this Purse
      so you can spend from TallyKeep"). The wizard's job is
      *registering* a new Purse; the upgrade is *transforming*
      an existing one. Forcing both verbs through the same
      wizard would either fork step 1 three ways or require a
      bizarre "are you upgrading or registering?" step.
    - **Input.** Textarea accepting BIP39 mnemonic (12 / 24
      words) or master xprv. Inline validation against the
      wallet whose descriptor is already imported — refuses
      pastes that don't derive to the same descriptor.
    - **Capacitor-only at ship**, with browser-fallback gating
      per ADR-0007. The dev-mode `localStorage` stub from the
      Purse-wizard iteration is acceptable for Rémy-only
      personal-shipping but not the right shape for a
      user-facing affordance.
    - **Disclosure copy** (imported-seed case): *"TallyKeep
      now stores a copy of these keys on this device. You
      already have a backup from where you exported the seed
      — keep it safe. Spending from both apps on the same
      wallet without coordinating can cause failed broadcasts
      (the protocol prevents double-spend; the UX gets
      confusing)."*
    - **Security-health surface** registers the imported Purse
      with copy distinct from generated Purses (no "TallyKeep
      gave you this seed" framing — the user got it
      elsewhere).
- **Touches:** `holdings/02_purse.md` (Add-Holding —
  `ON_DEVICE_USER_IMPORTED` section), `UI/mobile.md` Purse
  Detail section, `concerns/threat_model.md` Mobile addendum,
  Capacitor NativeBridge `secureStorage` write path,
  `seed-backup-disclosure` security-health item lockstep.
- **Status:** sketched
- **Milestone:** pre-shipping — lands during personal-use
  phase, after Capacitor wrap. Sharpens once
  `pre-implementation.md` `purse-upgrade-path` closes (the
  structural question: mutable `purse_mode` vs separate
  `spending_capability` flag).
- **Open at sharpen time:**
    - Disclosure copy lockstep with `seed-backup-disclosure`
      — the imported-seed variant differs from the
      TallyKeep-generated case.
    - Double-spend UX timing — surface text only at upgrade
      time, or also at first Send on an imported wallet?
    - Capacitor gate posture: hide the upgrade affordance on
      browser builds (gauntlet 5 absence-of-affordance) or
      show with banner (gauntlet 5 honest gate)? Probably the
      former.
- **Notes:** ADR-0006 may need an editorial note or
  amendment recording the `purse_mode` mutability relaxation
  if the structural arbitration goes that way.
