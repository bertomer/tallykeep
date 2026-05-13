# Brand

Canonical product identity: icon, wordmark, color palette,
typography, voice and tone, usage guidance. This is the source of
truth that everything downstream consumes — UI tokens, marketing
site, app icons, F-Droid / App Store listings, pitch decks, social
cards.

Working rules for brand artifacts (lock-doc pattern, change
discipline, brand → tokens propagation, ADR thresholds) live in
`PROCESS.md §2.4`. This file holds layout and status only.

## Status

**Mark, wordmark, and palette are locked. Voice/about is draft.**

Brand work is far enough along to call the locked artifacts the
working brand, not a placeholder. The public-ship event (per
ADR-0003) will either confirm them as the final shipped brand or
revise; until then, these are canonical.

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

The wordmark and all UI body type use **Manrope** (400 / 500 / 600 / 700,
full weight set loaded from Google Fonts). Role assignments at the
wordmark level (which weight for the wordmark itself, casing, tracking)
live in `tallykeep_wordmark_v1_lock.html`.

One application-level rule lives here, not in the wordmark doc, because
it spans the whole app rather than a specific brand artifact:

- **Amounts use sans with tabular numerals.** `font-family:
  var(--font-sans); font-variant-numeric: tabular-nums`. Never mono.
  Hero balances, per-row Holding balances, sweep thresholds, fee
  displays, anything that reads as a quantity goes sans + tabular.
  Manrope supports tabular numerals so digits in a column align
  cleanly without the mono look. Locked 2026-05-13 after side-by-side
  review (earlier drafts used `--font-mono`; the Manrope-vs-Consolas
  contrast read as a typography mismatch on the populated home).
  Rationale: banking-grade ergonomics is the brand direction;
  mono pushes toward Bitcoin-native-feel which is the wrong end of
  the spectrum.
- **Mono is reserved for code-shaped content.** BIP 380 descriptors,
  Bitcoin addresses, transaction IDs, BIP identifiers, passphrase
  entry, raw API output. The `.mono` helper in `_shared/shell.css`
  and the `--font-mono` token in `_shared/tokens.css` remain in
  place for these uses.

**Tokens are in sync.** `UI/mockups/_shared/tokens.css` is sourced
from the palette v2 lock doc. The wood (Aged Oak, Grain, Cream)
mirrors the mark and wordmark. The semantic palette (success /
warning / danger / info) is the v1.1 AA-tightened leaf-bright set
— info remains provisional. The Holding-type accents (limestone,
auburn leather, iron, brushed steel) landed at v2 lock; they
replaced the pre-brand placeholder values that previously sat
in `tokens.css`. No remaining gaps in the palette layer.

The next brand work is iconography beyond the brand mark + Holding
icons (action / nav / status icons for general UI), motion principles,
and dark mode — all flagged in the palette v2 lock doc §9 Open items.

## Layout

```
brand/
├── README.md ........................... this file
├── tallykeep_<artifact>_v<N>_<status>.html ... visual lock docs
├── tallykeep_<voice-piece>_v<N>_<status>.md  ... voice / about / copy
├── identity/
│   ├── README.md ................. import-target conventions
│   └── *.svg ..................... clean SVGs extracted from lock docs
└── assets/ (when present) ........ built artifacts: favicon.ico,
                                    app-store icons, social cards
```

### Lock documents

Each canonical brand artifact (mark, wordmark, future lockup) gets
**one self-contained big-page HTML lock document** covering form,
sizes, color tokens, anatomy, decisions log, geometry, open items.
This is the lock-doc pattern (PROCESS.md §2.4) — different from
the page-per-screen rule that applies to UI mockups, on purpose:
a brand artifact is a gestalt that only makes sense seen whole.

Filenames follow `tallykeep_<artifact>_v<N>_<status>.html`. Status
moves through `draft` → `lock` → `superseded`. v2 is a new file;
v1 stays as historical reference. Full naming rules in
PROCESS.md §2.4.

### Voice and narrative

Voice / about / tagline / copy guidelines live as markdown files
in this folder, same naming convention with `.md`.

### Consumable graphic assets

`identity/` holds clean SVG files extracted from the lock docs,
intended for downstream consumption. Mockups and frontend code
import from here, **not** from the inline SVG in lock docs. The
duplication is deliberate; sync rule and per-file usage guidance
in `identity/README.md`.

## Open-source posture

Brand assets ship with the repo (the app is open-source from day
one per ADR-0003). License for brand assets is a public-ship-event
question — likely permissive (MIT or CC-BY) for the SVGs and lock
docs, with a separate trademark registration to prevent
adversaries from passing off forks as the official TallyKeep.
Trademark is a lawyer question for the public-ship phase.

## Pointers (don't duplicate the rules below)

- Lock-doc pattern, naming convention, change discipline,
  brand → tokens propagation, ADR thresholds → `PROCESS.md §2.4`
- Routing table for "where does this kind of change go" →
  `PROCESS.md §7`
- Agent boot sequence when arriving at this folder →
  `PROCESS.md §6`
- SVG sync rule between lock docs and `identity/` →
  `identity/README.md`
