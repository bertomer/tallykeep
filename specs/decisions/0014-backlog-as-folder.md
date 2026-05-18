# ADR-0014 — Backlog lives in a folder, not a flat file

**Date:** 2026-05

**Status:** Accepted

**Decided by:** Rémy

**Authored by:** Claude during the Account-detail-page brainstorm, May 2026

## Context

`future_iterations.md` has accumulated ~60 entries and 2,200+ lines
over the project's history. The §4.8 Cowork-file-tool stale-buffer
bug triggers on long markdown files with repeated `Edit` operations
— and `future_iterations.md` is the most-edited file in the spec
tree (every brainstorm session captures, refines, promotes, or
removes entries). The corruption pattern has hit it multiple times
in recent weeks, in one case costing brainstorm output and in
another requiring git recovery plus a clean redo of a spec edit.

The corruption isn't a property of "ideas captured in markdown" —
it's a property of "repeated `Edit`s on one long file." Splitting
into smaller files moves the operation from `Edit` (fragile) to
`Write` (reliable for new files) at capture time, and from "delete
this section" (Edit-heavy) to `rm` (atomic) at resolution time.
The bug class is sidestepped, not just made less frequent.

The same reasoning does **not** apply to `shipped.md`, which is
cold (one append per iteration closeout, never re-edited) and is
optimized for chronological reading. That file stays flat.

## Decision

The "captured ideas, awaiting promotion" pot becomes a folder:
`specs/backlog/`. One file per entry.

**Naming convention.** Lowercase, hyphen-separated slug derived
from the entry title. No numeric prefix — the iteration roadmap
carries priority, and the backlog itself is unordered.

- `backlog/account-withdrawal-key-sub-flow.md`
- `backlog/holding-to-holding-sweeps-beyond-account-originated.md`
- `backlog/custom-adapter-for-non-ccxt-venues-swissquote-and-similar.md`

**Lifecycle.**

- **Capture.** Spec agent writes a new file via `Write` — one
  shot, fresh path, no `Edit` fragility.
- **Promotion to active iteration.** When the entry is sharpened
  into the active iteration block in `next_iteration.md`, the
  backlog file is deleted (`rm`). Git history retains it; the
  closeout entry in `shipped.md` is the durable trail.
- **Resolution via ADR.** When a brainstorm settles the question
  without an iteration (ADR-0013 is the canonical example), the
  file is deleted; the ADR's `Migrated from:` line preserves the
  slug.
- **Drop.** A captured idea that turns out to be wrong is deleted
  with a brief commit message saying why. Git log is the audit
  trail; the folder represents current state only.

**Folder structure.**

```
specs/backlog/
├── README.md ............... conventions + iteration roadmap + milestone tagging
└── <slug>.md ............... one captured idea per file
```

The `README.md` carries the conventions, lifecycle, the milestone
tag explanation (per ADR-0003), and the "Iteration roadmap"
content that previously lived at the top of `future_iterations.md`
(Rémy's mental model of upcoming pre-shipping / public-ship-gate /
post-shipping work).

## Consequences

**What this gives us.** Corruption from §4.8 on the backlog file
class effectively eliminated. Captures are `Write` of fresh files;
resolutions are `rm`. Cleaner git diffs — adding or removing one
entry no longer creates a diff across a 2,000-line file with
potential whitespace drift. Easier grep ("what's in the backlog"
= the folder listing) versus open-the-file ("what's in this
entry"). Easier cross-reference: `future_iterations.md "Account
withdrawal-key UX"` becomes `backlog/account-withdrawal-key-sub-flow.md`
— the new form survives entry-name drift if the slug is stable.

**What this costs us.** More files on disk: ~60 entries → ~60
files. Manageable; `decisions/` already runs at 14 files. Naming
discipline matters more — slugs need to stay stable enough for
cross-references to survive. The one-time migration script
enforces consistent slugging; ongoing captures need a one-line
convention check.

**What this does not change.**

- `shipped.md` stays a single file. Cold append-only changelog,
  tiny §4.8 surface, optimized for chronological reading. Different
  concern entirely.
- `next_iteration.md` stays a single file. Hot but small; one
  active iteration block at a time.
- `pre-implementation.md` stays a single file. Open-arbitration
  items only, bounded set, closes via ADR or canonical-doc edit.

## Migration

One-time PowerShell script run by Rémy on real disk (bash mount
not trusted for this — see the §4.8 stale-buffer pattern that
prompted this ADR):

- Parses `future_iterations.md`, finds the `## Open` boundary.
- For each `### Header` block below it, derives a slug and writes
  one file to `specs/backlog/<slug>.md` (body preserved as-is,
  with `# Title` as the new top line).
- The `## Promoted` section is dropped — its entries are already
  reflected in `shipped.md` or `next_iteration.md`'s active block.
- The intro + iteration roadmap sections move to
  `backlog/README.md` (authored by hand in this session).
- `future_iterations.md` is replaced with a deprecation pointer
  to `backlog/`, kept around so existing cross-references in
  canonical docs still resolve until a follow-up spec-agent
  session can purge them.

## Affected files

- `specs/backlog/` — new folder with `README.md` plus one file per
  captured entry.
- `specs/future_iterations.md` — replaced with a deprecation
  pointer; deleted in a follow-up cleanup pass.
- `specs/PROCESS.md` — §1 doc layout, §6 boot sequence (step 7),
  §7 routing table updated.
- `specs/decisions/README.md` — ADR-0014 indexed.
- Canonical docs referencing `future_iterations.md "Foo"` — the
  cross-reference cleanup is deferred to a follow-up session
  (running it now risks colliding with the coding agent on
  `next_iteration.md`; the deprecation pointer keeps the
  references resolving in the meantime).
