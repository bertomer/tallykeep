# Architecture Decision Records

ADRs capture decisions worth remembering — particularly ones we'd
otherwise re-litigate.

## When to write one

- Foundational tech choices (libraries, protocols, deployment models)
- Security model decisions (custody, key storage, threat model deltas)
- Product principle changes
- Scope changes (in or out of v1)
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

## Index

- 0001 — Spec consolidation pass
