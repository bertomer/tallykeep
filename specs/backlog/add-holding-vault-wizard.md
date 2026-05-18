# Add Holding — Vault wizard

- **Captured:** 2026-05 (split 2026-05-13, see Purse-wizard
  entry above).
- **Motivation:** Long-term ceremonial multi-key hold. Designed
  as the default destination for auto-sweep policies once the
  SweepPolicy iteration lands. Completes the four-Holding-type
  onboarding surface in dev phase.
- **Sketch:** 5-step wizard. Same parser as Purse / Strongbox
  but with multisig-only validation and a pre-card framing.
    1. *Framing pre-card* — "Vault is for amounts you rarely
       touch — long-term reserve, family savings, future income.
       Several keys are required to move funds. Vault will become
       the default destination for auto-sweeps from your other
       Holdings. Today, you can import the descriptor; spending
       and auto-sweep land in later iterations." Primary CTA:
       "Continue".
    2. *Descriptor input* — multisig only. Bare xpubs and
       single-key descriptors rejected with "Vault requires a
       multisig descriptor — `wsh(multi(...))` or similar."
    3. *Parse-back* — M-of-N, co-signer count, any timelocks
       present, first three derived addresses.
    4. *Label* — default suggestion "My Vault".
    5. *Success* — "Vault is set up. Spending ceremony and the
       auto-sweep destination feature ship in later iterations."
  Reuses the shared wizard shell.
- **Touches:** `UI/mobile.md` Add-Holding Vault section, five new
  mockup files, frontend wizard implementation. Backend already
  shipped. No new shell or bridge work.
- **Status:** sharpened-ready-to-promote
- **Milestone:** pre-shipping
- **Notes:** Promote **third**. Vault's framing pre-card is the
  key design difference from Purse / Strongbox; the rest of the
  wizard reuses the pattern. Operational features (signing
  ceremony, blueprint analysis, declared-vs-observable mismatch
  warnings) stay deferred to the Vault-detail iteration.
