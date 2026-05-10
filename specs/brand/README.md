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

**v1 mark and wordmark are locked. Voice/about is draft.**

Brand work is far enough along to call the locked artifacts the
working v1 brand, not a placeholder. The public-ship event (per
ADR-0003) will either confirm v1 as the final shipped brand or
revise it; until then, v1 is what's canonical.

| Artifact | Status | File |
|---|---|---|
| Brand mark (icon) | Locked v1 | `tallykeep_brand_mark_v1_lock.html` |
| Wordmark | Locked v1 | `tallykeep_wordmark_v1_lock.html` |
| Voice / about | Draft v1 | `tallykeep_about_v1_draft.md` |
| Tagline | In consideration | (inside the wordmark lock doc, §9) |

**Tokens are in sync.** `UI/mockups/_shared/tokens.css` was
remapped 2026-05 by extracting values from the lock-doc page
chrome (the docs are themselves rendered in the brand). Holding-
type accents and semantic colors (success/warning/danger/info)
were not in the lock docs and stay at their pre-lock values until
the public-ship-event brand finalization extends the palette
explicitly. Documented as a known gap in `tokens.css`.

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
