# Holdings

Per-Holding-type chapters. Each chapter describes everything
TallyKeep does with a given Holding type at **target state**
(per the three-universe framing in `PROCESS.md §1`):
observation, outflow, sweep behavior, type-specific safeguards.

This shape replaces the previous backend-layered split (Savings /
Banking / Trading) which was tied to backend implementation.
Reorganized 2026-05 — see the spec reshape session.

## The four types

| Type | Banking analogy | Key custody zone (ADR-0009) | Outflow mechanic |
|---|---|---|---|
| [Account](01_account.md) | Like an exchange account | Custodial provider holds keys | Withdraw to pre-whitelisted address (provider API) |
| [Purse](02_purse.md) | Like a checking account | Per seed-origin: external wallet **or** Capacitor client **or** browser N/A | Native sign (Capacitor) / source-wallet redirect / view-only gate |
| [Strongbox](03_strongbox.md) | Like a savings account, but you hold the key | Hardware wallet (user's external device) | PSBT export → external sign → re-import → broadcast |
| [Vault](04_vault.md) | Like a safety-deposit box | Hardware wallets + multisig co-signers | PSBT with multisig coordination (mostly deferred) |

Each chapter is the canonical source for its Holding type's
behavior. Cross-cutting machinery (PSBT construction, chain
observation, sweep policy mechanics, feature flags, threat
model) lives in `concerns/` and is referenced from these
chapters.

## What lives in this folder vs in `concerns/`

| Lives in `holdings/<type>.md` | Lives in `concerns/` |
|---|---|
| What this Holding type **is** | How TallyKeep monitors any chain activity |
| What an Add-Holding flow for this type does | How any PSBT is constructed |
| How spending from this type works (including the routing decision) | How sweep policies work as a primitive |
| Type-specific safeguards (e.g. Vault outgoing-payment warning) | Feature flag catalog |
| Type-specific UX rules (e.g. verify-on-device for Strongbox) | Threat model |
| What's deferred for this type, with pointers | What's deferred cross-cutting |

When extending TallyKeep with a new Holding type, add a new
chapter here. When extending TallyKeep with a new cross-cutting
capability, add to `concerns/`.

## Cross-references to keep in mind

- Vocabulary is locked in `02_domain_model.md` §"Vocabulary
  contract". Holding-type names (Account, Purse, Strongbox,
  Vault) are durable.
- Key custody by zone is **ADR-0009**. Each chapter cites the
  relevant zone.
- Purse seed origins are **ADR-0006** (`purse-flavors` slug) and
  the pending `purse-upgrade-path` arbitration in
  `pre-implementation.md`.
- The browser-vs-Capacitor stance is **ADR-0007**.
