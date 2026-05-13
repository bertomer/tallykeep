# Concerns

Cross-cutting capabilities and constraints — the machinery
that powers TallyKeep across all Holding types. Each file
describes one concern at **target state** (per the
three-universe framing in `PROCESS.md §1`); per-Holding
specializations live in `holdings/<type>.md`.

This shape replaces the previous layered modules (Savings /
Banking / Trading / Lightning placeholder / Feature flags /
Threat model). Reorganized 2026-05.

## Index

| File | Covers |
|---|---|
| [observation.md](observation.md) | Chain monitoring, UTXO persistence, hygiene flags, declared-vs-observable security analysis, categorization, fortune view |
| [outflow.md](outflow.md) | PSBT construction, fee user experience, broadcast, payment-request lifecycle, invoice flow |
| [sweep_policies.md](sweep_policies.md) | Cross-Holding sweep model, safety validator (warn-don't-block), daily caps, execution path |
| [feature_flags.md](feature_flags.md) | Flag catalog, onboarding-question-driven defaults, resolution rules |
| [lightning_placeholder.md](lightning_placeholder.md) | LightningProvider interface, stubbed endpoints, domain integration today |
| [threat_model.md](threat_model.md) | Security posture, assets, attack scenarios, controls — including Mobile addendum |

## When to look here vs in `holdings/`

- "How does the chain scanner work?" → `observation.md`.
- "How does TallyKeep observe a Strongbox specifically?" →
  `holdings/03_strongbox.md`, which references `observation.md`
  for the generic mechanics.
- "What's a SweepPolicy?" → `sweep_policies.md`.
- "Does TallyKeep auto-sweep from a TallyKeep-managed Purse?" →
  `holdings/02_purse.md`, which describes the per-Purse-mode
  signing routing for sweeps.

In general: cross-cutting machinery is documented once, here;
per-Holding specialization is documented in the Holding's
chapter, which links back.
