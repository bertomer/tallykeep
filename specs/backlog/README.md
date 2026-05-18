# Backlog

The pot. Ideas captured during brainstorm sessions but flagged as
"later." Sharpening happens when an item is promoted to the active
iteration block in `../next_iteration.md`.

Each file in this folder is one captured idea — intentionally
rougher than a `next_iteration.md` entry, just enough to remember
the motivation and where it came up. Sharpening is a deliberate
session, not done in-pot.

**If you're a coding agent reading this:** this folder is reference,
not work. Do not implement from here. Your scope is
`../next_iteration.md`'s active iteration block.

Structure decided in ADR-0014; the per-file form sidesteps the
§4.8 Cowork-file-tool stale-buffer pattern that long-file Edits
on the prior flat backlog kept triggering.

---

## File conventions

- **Filename.** Lowercase, hyphen-separated slug derived from the
  entry title. No numeric prefix — entries aren't ordered; the
  iteration roadmap below carries priority.
  - `account-withdrawal-key-sub-flow.md`
  - `holding-to-holding-sweeps-beyond-account-originated.md`
- **First line.** `# <Title>` matching the slug.
- **Body shape.** Same as the prior monolithic entries —
  Captured / Motivation / Sketch / Touches / Status / Milestone /
  Notes. Free-form prose where the categories don't fit.
- **Optional YAML frontmatter** (`status`, `captured`, `milestone`)
  for entries that want machine-readable tagging. Not required;
  the body fields are the source of truth either way.

## Lifecycle

- **Capture.** Spec agent creates a new file via `Write` (not
  `Edit`). Fresh path, atomic, no §4.8 fragility.
- **Promotion to active iteration.** When the entry is sharpened
  into the active iteration block in `../next_iteration.md`, the
  backlog file is deleted (`rm`). Git history retains it; the
  closeout entry in `../shipped.md` is the durable trail. If a
  back-pointer to the original capture is useful, the shipped.md
  entry names the slug.
- **Resolution via ADR.** When a brainstorm settles the question
  without an iteration (ADR-0013 is the canonical example), the
  file is deleted; the ADR's `Migrated from:` line preserves the
  slug for back-reference.
- **Drop.** A captured idea that turns out to be wrong is deleted
  with a brief commit message saying why. Git log is the audit
  trail; the folder represents current state only.

There is no "Promoted" or "Decided" section. If an entry is
neither current backlog nor a real ADR, it doesn't live here.

## Milestone tag

Per ADR-0003, the project tracks two ship events:

- **private-ship event** — Rémy's Capacitor app on his own phone,
  sideloaded, real value at small amounts. No public users.
- **public-ship event** — app stores + brand + audit +
  reproducible builds, for public users.

Backlog items are tagged in their body (or frontmatter):

- `pre-shipping` — needed before the public-ship event. May be
  required specifically for the private-ship event (noted in
  entry) or more generally for public-ship.
- `post-shipping` — to land after the public-ship event.
- `TBD` — Rémy hasn't decided yet; best guess (if any) lives in
  the entry's notes.

---

## Iteration roadmap (rough sketch — not commitment)

For Rémy's mental model, not for the coding agent. Sequence and
scope will adjust as we learn. The roadmap targets the
public-ship event (per ADR-0003); private-ship is reached when
the relevant mobile UI iterations are stable enough and the
Capacitor + auth + security-health work lands.

### Pre-shipping iterations

**Mobile UI design and dev-phase build:**

1. **Onboarding + Home (empty + populated states)** — first-touch
   flow plus landing.
2. **Add Holding** — chooser + four type-specific flows.
3. **Holding Detail** — per-type detail pages.
4. **Send + Receive** — per Holding type, including PSBT
   roundtrip for Strongbox and native sign for TallyKeep-managed
   Purse on the device that holds the seed.
5. **Activity + Categorization** — cross-Holding feed plus
   per-Holding categorization.
6. **Sweep Policy + Treasury view** — Account-originated sweeps
   in the dev-phase scope.
7. **Settings** — including the security-health system at least
   for seed-backup warnings (private-ship gate).

**Private-ship gate.** The above mobile flows stable enough for
Rémy's day-to-day use, plus Capacitor wrapper + native signing +
auth-handshake hardening.

### Public-ship event (ship-gate work bundle)

See the `ship-gate-meta-iteration` backlog entry. Bundles native
signing, reproducible builds, app stores, F-Droid, brand,
third-party audit, and (optionally) hosted-tier launch.

### Post-shipping

Feature updates per the post-shipping entries in this folder
(Blueprint, Lightning, DCA, equity-reference unit, retirement
planning, etc.), prioritized by user feedback and roadmap
priorities after public ship.
