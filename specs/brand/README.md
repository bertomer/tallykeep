# Brand

Canonical product identity: icon, wordmark, color palette,
typography, voice and tone, usage guidance. This is the source of
truth that everything downstream consumes — UI tokens, marketing
site, app icons, F-Droid / App Store listings, pitch decks, social
cards.

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
chrome (the docs are themselves rendered in the brand). The
extraction is mechanical — token names map to documented
palette values; no design decisions were involved. Holding-type
accents and semantic colors (success/warning/danger/info) were
not in the lock docs and stay at their pre-lock values until a
screen surfaces a problem.

## How brand work is structured

Two patterns coexist in this folder, and the difference is
intentional:

### 1. Lock documents — one big HTML page per artifact

Each canonical brand artifact (mark, wordmark, future lockup, etc.)
gets a single self-contained HTML lock document covering everything
about that artifact: form, sizes, color tokens, anatomy, decisions
log, geometry, open items.

This is **a different rule from `UI/mockups/`**, which splits one
file per screen-state. Brand and UI have different content shapes:

- A UI screen is a unit of state that evolves; per-state files let
  you iterate on "home empty" without touching "home populated."
- A brand artifact is a gestalt — the silhouette only makes sense
  alongside its size system, colors, anatomy, and decisions. Lock
  docs consolidate after the work is done; you don't iterate on the
  V-notch position one week and the biais cut the next.

When v2 of an artifact happens, it's a new file (`..._v2_lock.html`)
and v1 stays as historical reference, with v1's open-items section
documenting what motivated the revision.

Naming: `tallykeep_<artifact>_v<N>_lock.html`. Keep the
`tallykeep_` prefix and the `v<N>` suffix — these are versioned
checkpoints, not living docs (and so are exempt from the "no _v1
suffix" rule in PROCESS.md §2.4 that applies to UI specs).

### 2. Voice and narrative — markdown

Voice / about / tagline / copy guidelines are prose, not visual
artifacts. They live as markdown files at the root of `brand/` and
follow the same naming convention (e.g., `tallykeep_about_v1_draft.md`).
Status moves from `draft` → `lock` once the wording is settled.

### 3. Consumable graphic assets — `identity/`

The lock HTML docs embed inline SVG so the doc reads standalone.
**They are not the import source.** A parallel set of clean SVG
files lives in `identity/`, intended for downstream consumption:

```
identity/
├── icon-canonical.svg     # 32 px and up, with grain
├── icon-solid.svg         # ≤16 px favicon variant, no grain
├── wordmark-plain.svg     # plain wordmark
└── wordmark-icony.svg     # wordmark with embedded icon
```

(More variants — lockup, monochrome, dark-mode treatments — get
added as they're locked.)

Mockups in `UI/mockups/` reference these via inline copy or
`<img src="../../brand/identity/<file>.svg">`. The eventual
SvelteKit frontend imports them as components (`BrandIcon.svelte`,
`Wordmark.svelte`) — those components live in frontend code, not
in `specs/`. The spec tree's job ends at producing clean
consumable SVGs.

The duplication between the inline SVG in lock docs and the file
in `identity/` is deliberate. The lock doc serves human readers; the
SVG file serves machine consumers (mockups, frontend). When an
artifact is revised, both update together.

## Relationship to UI tokens

`UI/mockups/_shared/tokens.css` (and later the SvelteKit equivalent)
is the technical embodiment of brand decisions. Components and
mockups reference token names, never brand assets directly. That
keeps brand swaps a token-layer change plus rebuild-derived-assets,
not a component-by-component refactor.

When a brand value changes:

1. Update the relevant lock doc.
2. Update the matching file in `identity/` if a graphic asset
   changed.
3. Update `tokens.css` to match. (Currently stale — see "Known
   drift" above.)
4. (If brand is post-public-ship-lock) write or update the
   relevant ADR.

## Change discipline

- **Pre-public-ship (current):** brand v1 is locked as working
  truth. Edits to lock docs are allowed but should bump the version
  (v1 → v2 lock) when the artifact materially changes. Tokens
  follow in lockstep. No ADR required for v1 → v2 within the
  pre-ship phase.
- **At public-ship event** (per ADR-0003): an ADR records the
  finalized brand. v1 either stays locked or gets superseded by a
  v2 (or vN) lock doc. ADR notes which version is final.
- **Post-public-ship:** wordmark / primary color / type system /
  voice principles are foundational. Changes need an ADR + edit +
  tokens regeneration + downstream propagation (favicon rebuild,
  app-store icon rebuild, marketing material rebuild).

## Open-source posture

Brand assets ship with the repo (the app is open-source from day
one per ADR-0003 locked principles). License for brand assets is a
public-ship-event question — likely permissive (MIT or CC-BY) for
the SVGs and lock docs, with a separate trademark registration to
prevent adversaries from passing off forks as the official
TallyKeep. Trademark is a lawyer question for the public-ship phase.

## Working with the next agent

When you arrive here:

1. Read this file.
2. Read `tallykeep_brand_mark_v1_lock.html` and
   `tallykeep_wordmark_v1_lock.html` for the visual identity
   substance (form, sizes, colors, anatomy, decisions, geometry).
3. Read `tallykeep_about_v1_draft.md` for the voice and narrative
   thesis.
4. If your scope touches anything that consumes brand
   (mockups, app icons, marketing copy), use the SVGs in
   `identity/` and the tokens in `UI/mockups/_shared/tokens.css` —
   not the inline SVG in the lock docs.
5. If you're tempted to split a lock doc into per-aspect files
   (one for colors, one for sizes, etc.), don't. The lock-doc
   pattern is deliberate; see "How brand work is structured"
   above.
6. If you're sharpening an iteration that touches brand
   artifacts, route the work explicitly: mark changes → mark lock
   doc + `identity/icon-*.svg`; wordmark changes → wordmark lock
   doc + `identity/wordmark-*.svg`; voice changes → the voice
   markdown file; if a brand revision changes color values, update
   `UI/mockups/_shared/tokens.css` in the same change (mechanical
   extraction from the lock-doc chrome — not a separate iteration).
