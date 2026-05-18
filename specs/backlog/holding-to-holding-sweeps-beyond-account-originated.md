# Holding-to-Holding sweeps beyond Account-originated

- **Captured:** 2026-05 (custodial-and-sweeps review)
- **Motivation:** Per `concerns/sweep_policies.md`, SweepPolicy is generalized:
  any Holding to any Holding, in any direction, with a safety
  validator. Pre-shipping surfaces Account-originated outflow sweeps
  (Account → TK Holding — the minimum-exposure-trading accumulation
  pattern). Other directions — TK-Holding-source sweeps (inflow
  TK → Account for decumulation, plus inter-Holding rebalancing) —
  are architecturally supported but their UX hasn't been designed.
- **Sketch:** Surface sweep-policy creation for non-Account sources:
    - **TallyKeep-managed Purse → Strongbox/Vault** — auto-sweep
      with biometric prompt or background signing on the Capacitor
      device that holds the seed. Use case: keep daily-spending
      balance bounded; push excess to cold storage automatically.
    - **Strongbox → anywhere** — not auto; reduces to a scheduled
      reminder that prepares a PSBT awaiting the user's external
      signature on the hardware wallet.
    - **Vault → anywhere** — not auto; same as Strongbox plus
      multisig coordination.
- **Touches:** UI sweep-policy creation flow, scheduler / reminder
  system, threat model
- **Status:** idea
- **Milestone:** TBD — best guess: post-shipping. Architecture is in
  place per `concerns/sweep_policies.md`; only UI surface and reminder workflow are
  deferred. Pick up after primary sweep flows are stable.
