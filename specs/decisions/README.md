# Architecture Decision Records

ADRs capture decisions worth remembering — particularly ones we'd
otherwise re-litigate.

## When to write one

- Foundational tech choices (libraries, protocols, deployment models)
- Security model decisions (custody, key storage, threat model deltas)
- Product principle changes
- Scope changes (in or out of pre-shipping / post-shipping per ADR-0003)
- Anything that took more than 30 minutes of discussion to settle, or
  that any future agent might be tempted to undo without reading the
  reasoning

## When NOT to write one

- Obvious choices nobody would question
- Reversible UI tweaks
- Implementation details below the spec level (which JSON serializer,
  which logging library, etc.)

## Format

Filename: `NNNN-short-title.md` where `NNNN` is a 4-digit sequential
number, zero-padded.

Sections:

- **Date** — YYYY-MM
- **Status** — Proposed / Accepted / Superseded by NNNN / Deprecated
- **Decided by** — usually Rémy
- **Authored by** — useful context for future agents (e.g. "Claude
  during consolidation session, May 2026")
- **Context** — the situation that forced the decision; why default
  inertia was insufficient
- **Decision** — what was chosen, in plain terms
- **Consequences** — what changes downstream; what's now closed; what
  follow-up work this implies
- **Affected files** — if any docs / code paths need editing as a
  result

When superseding an earlier ADR, set the old one's status to
`Superseded by NNNN` and link forward.

When migrating a closed item out of `pre-implementation.md` into an
ADR, add a `Migrated from:` line in the header preserving the
original slug, so existing back-references in canonical docs still
resolve.

## Index

Keep this list in sync with the files in this folder. The
iteration-done sanity sweep (`PROCESS.md §4.6`) checks it.

- [0001 — Spec consolidation pass](0001-spec-consolidation.md) — Accepted; refined by 0002
- [0002 — Iteration cycle and module retirement](0002-iteration-cycle.md) — Accepted
- [0003 — Project phases and shipping milestones](0003-personal-use-phase.md) — Accepted
- [0004 — Backend OpenAPI is the API contract](0004-api-as-contract.md) — Accepted
- [0005 — Feature flags replace named user profiles](0005-feature-flags-replace-presets.md) — Accepted
- [0006 — Purse seed origin and per-client signing capability](0006-purse-seed-origin.md) — Accepted
- [0007 — Browser-first development with NativeBridge stubs](0007-browser-first-with-nativebridge.md) — Accepted
- [0008 — Passphrase and recovery model (two-layer unlock)](0008-passphrase-and-recovery-model.md) — Accepted
- [0009 — Key custody model](0009-key-custody-model.md) — Accepted; refines principle #6 of 00_README
- [0010 — Vault type definition + Vault Send deferral](0010-vault-gated-until-multisig.md) — Accepted; migrated from `vault-pre-multisig-shape`
- [0011 — Account credentials use the 2-key model](0011-account-two-key-model.md) — Accepted; permission-list section superseded by 0012
- [0012 — Observation credential carries balance + ledger scopes](0012-observation-scope-expansion.md) — Accepted; supersedes the permission-list section of 0011
- [0013 — Custodial ledger is mirrored, not cached](0013-custodial-ledger-mirror-posture.md) — Accepted; migrated from `custodial-ledger-mirror-posture` future-iterations entry
- [0014 — Backlog lives in a folder, not a flat file](0014-backlog-as-folder.md) — Accepted
- [0015 — Lock-aware worker lifecycle](0015-lock-aware-worker-lifecycle.md) — Accepted
