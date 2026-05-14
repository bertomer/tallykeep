# Brand

Canonical product identity: icon, wordmark, color palette,
typography, voice and tone, usage guidance. This is the source
of truth that everything downstream consumes — UI tokens,
marketing site, app icons, F-Droid / App Store listings, pitch
decks, social cards.

This file is canonical for all brand-process rules: lock-doc
pattern, naming, consumer discipline, status-driven lifecycle,
brand → tokens propagation, ADR thresholds. PROCESS.md points
here.

## Status

**Mark, wordmark, and palette are locked. Voice/about is draft.**

Brand work is far enough along to call the locked artifacts the
working brand, not a placeholder. The public-ship event (per
ADR-0003) will either confirm them as the final shipped brand
or revise; until then, these are canonical.

| Artifact | Status | File |
|---|---|---|
| Brand mark (icon) | Locked v1 | `tallykeep_brand_mark_v1_lock.html` |
| Wordmark | Locked v1 | `tallykeep_wordmark_v1_lock.html` |
| Palette (semantic + Holding-type identity) | Locked v2 | `tallykeep_palette_v2_lock.html` |
| Holding-type icons (4 + Purse variants) | Locked v2 | `identity/holding-*.svg` |
| Voice / about | Draft v1 | `tallykeep_about_v1_draft.md` |
| Tagline | In consideration | (inside the wordmark lock doc, §9) |
| Palette v1 | Superseded by v2 | `tallykeep_palette_v1_superseded.html` |

## Typography conventions

The wordmark and all UI body type use **Manrope** (400 / 500 /
600 / 700, full weight set loaded from Google Fonts). Role
assignments at the wordmark level (which weight for the wordmark
itself, casing, tracking) live in
`tallykeep_wordmark_v1_lock.html`.

One application-level rule lives here, not in the wordmark doc,
because it spans the whole app rather than a specific brand
artifact:

- **Amounts use sans with tabular numerals.** `font-family:
  var(--font-sans); font-variant-numeric: tabular-nums`. Never
  mono. Hero balances, per-row Holding balances, sweep
  thresholds, fee displays, anything that reads as a quantity
  goes sans + tabular. Manrope supports tabular numerals so
  digits in a column align cleanly without the mono look.
  Locked 2026-05-13 after side-by-side review (earlier drafts
  used `--font-mono`; the Manrope-vs-Consolas contrast read as
  a typography mismatch on the populated home). Rationale:
  banking-grade ergonomics is the brand direction; mono pushes
  toward Bitcoin-native-feel which is the wrong end of the
  spectrum.
- **Mono is reserved for code-shaped content.** BIP 380
  descriptors, Bitcoin addresses, transaction IDs, BIP
  identifiers, passphrase entry, raw API output. The `.mono`
  helper in `_shared/shell.css` and the `--font-mono` token in
  `_shared/tokens.css` remain in place for these uses.

**Tokens are in sync.** `UI/mockups/_shared/tokens.css` is
sourced from the palette v2 lock doc. The wood (Aged Oak,
Grain, Cream) mirrors the mark and wordmark. The semantic
palette (success / warning / danger / info) is the v1.1
AA-tightened leaf-bright set — info remains provisional. The
Holding-type accents (limestone, auburn leather, iron, brushed
steel) landed at v2 lock; they replaced the pre-brand
placeholder values that previously sat in `tokens.css`. No
remaining gaps in the palette layer.

The next brand work is iconography beyond the brand mark +
Holding icons (action / nav / status icons for general UI),
motion principles, and dark mode — all flagged in the palette
v2 lock doc §9 Open items.

## Layout

```
brand/
├── README.md ........................... this file (canonical for brand process)
├── tallykeep_<artifact>_v<N>_<status>.html ... visual lock docs
├── tallykeep_<voice-piece>_v<N>_<status>.md  ... voice / about / copy
├── identity/
│   ├── README.md ................. import-target conventions + SVG sync rule
│   └── *.svg ..................... clean SVGs extracted from lock docs
└── assets/ (when present) ........ built artifacts: favicon.ico,
                                    app-store icons, social cards
```

## Lock-doc pattern (different from UI mockups, on purpose)

Each canonical brand artifact (mark, wordmark, future lockup,
etc.) gets **one self-contained big-page HTML lock document**
covering form, sizes, color tokens, anatomy, decisions log,
geometry, open items. Voice/about/tagline content is markdown,
same all-in-one shape.

This differs from `UI/mockups/`, which splits one file per
screen-state. Brand and UI have different content shapes — a
brand artifact is a gestalt that only makes sense seen whole;
a UI screen is a unit of state that evolves independently.
Don't try to "normalize" the brand folder into per-aspect files
(a `colors.md`, a `typography.md`, etc.). The lock-doc pattern
is the spec.

**Naming.** `tallykeep_<artifact>_v<N>_<status>.html` for visual
lock docs; `tallykeep_<voice-piece>_v<N>_<status>.md` for
voice/copy. Status is one of `lock` / `draft` / `superseded`.
The `tallykeep_` prefix is kept (brand artifacts are consumed
outside this folder by mockups, frontend, and future marketing
— self-identifying filenames matter). The `v<N>` suffix is
intentional and exempt from the "no _v1 suffix" rule that
applies to UI specs — brand lock docs are versioned
checkpoints, not living docs.

**Brand → identity → consumers.** Lock docs embed inline SVG so
they read standalone. Clean SVG files for downstream
consumption live in `brand/identity/`, extracted from the lock
docs. Mockups and frontend code import from `identity/`, never
from inline SVG in lock docs. The duplication is deliberate;
sync rule is documented in `brand/identity/README.md`.

The brand-side working surface for palette exploration is
`brand/tallykeep_palette_canvas.html`. It is not a lock doc and
not a consumer source-of-truth — read it only when adding a new
token or understanding the rationale behind a value. The
canonical sources stay the lock docs.

## Brand → tokens propagation (consumer discipline, no hardcoding)

UI references CSS variables from `UI/mockups/_shared/tokens.css`
(which the SvelteKit build consumes directly — same file, not
a parallel copy, so mockups and shipped code stay in lockstep
mechanically), which embody the brand decisions made in this
folder. The relationship is one-way: brand is the source,
tokens are the consumer.

Downstream code — mockups, SvelteKit components, marketing
site, future F-Droid / App Store listings, anything visual —
consumes via the indirection layer only:

- **Colors:** `var(--color-*)` from `tokens.css`. Never raw hex
  values in component files (`#A88554`, `#2e8a3f`) — every
  color reference goes through a token.
- **Icons:** import from `brand/identity/*.svg`, always via a
  thin wrapper component (e.g. `<Icon name="home" />` for nav
  icons, `<HoldingIcon type="vault" size={32} />` for
  holding-type icons) so the consumer-side API stays stable as
  the icon set grows. **Never inline SVG paths in feature
  component files — not even once, not even as a "quick
  copy".** Inlining creates diverging copies: the next
  component that needs the same icon will copy it again,
  detail will drift between copies, and bugs like missing
  spoke lines will appear. The rule: one domain object = one
  component = one source of truth. `HoldingIcon.svelte` is the
  mandatory wrapper for all four holding-type icons; any
  feature component that needs a holding-type icon imports it
  and passes `type` and `size`. The mockup-tier inlining of
  `wordmark-icony` and the nav icons is a workaround for
  static-HTML / `file://` loading; SvelteKit must import
  cleanly.
- **Spacing, radii, shadows, type:** `var(--space-*)`,
  `var(--radius-*)`, `var(--shadow-*)`, `var(--font-*)`. Never
  raw values.

**Structural check:** swapping brand v2 → v3 must be possible
by editing the source artifacts only (palette lock doc +
identity SVGs) and propagating to `tokens.css`. No
grep-and-replace through component files. If a component needs
a value that doesn't exist as a token, **add the token**
(lockstep with the brand lock doc per the status-driven
discipline below) — don't invent the value in the component.

## Status-driven discipline

Brand v1 (mark, wordmark) and v2 (palette) are locked as the
working truth. The public-ship event (per ADR-0003) confirms
or revises:

- **Pre-public-ship (current):** edits to lock docs allowed;
  bump the version (v1 → v2 lock) when the artifact materially
  changes. Update `tokens.css` and `identity/*.svg` in
  lockstep. No ADR for v1 → v2 within this phase.
- **At public-ship event:** ADR records the finalized brand.
  v1/v2 either stays locked or gets superseded by a successor.
- **Post-public-ship:** wordmark / primary color / type system
  / voice principles are foundational. ADR + edit + tokens
  regeneration + downstream propagation (favicon, app icons,
  marketing material).

## Voice and narrative

Voice / about / tagline / copy guidelines live as markdown
files in this folder, same naming convention with `.md`.

## Consumable graphic assets

`identity/` holds clean SVG files extracted from the lock docs,
intended for downstream consumption. Mockups and frontend code
import from here, **not** from the inline SVG in lock docs. The
duplication is deliberate; sync rule and per-file usage
guidance in `identity/README.md`.

## Open-source posture

Brand assets ship with the repo (the app is open-source from
day one per ADR-0003). License for brand assets is a
public-ship-event question — likely permissive (MIT or CC-BY)
for the SVGs and lock docs, with a separate trademark
registration to prevent adversaries from passing off forks as
the official TallyKeep. Trademark is a lawyer question for the
public-ship phase.

## Pointers

- Routing table for "where does this kind of change go" →
  `PROCESS.md §When things change`
- Agent boot sequence when arriving at this folder →
  `PROCESS.md §Working agreement`
- SVG sync rule between lock docs and `identity/` →
  `identity/README.md`
