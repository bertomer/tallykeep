# brand/identity

Consumable graphic assets — clean SVG files extracted from the
brand lock documents. **This is the import source for mockups and
frontend code.** The lock HTML docs (one folder up) embed inline
SVG for human readers; these files are for machine consumers.

## Files

| File | Source lock doc | When to use |
|---|---|---|
| `icon-canonical.svg` | `tallykeep_brand_mark_v1_lock.html` §1 | Default. 32 px and up. With grain stripes. |
| `icon-solid.svg`     | `tallykeep_brand_mark_v1_lock.html` §2 | Favicon, ≤16 px. No grain (sub-pixel noise at small sizes). |
| `wordmark-plain.svg` | `tallykeep_wordmark_v1_lock.html` §3   | Plain typeset wordmark, no embedded icon. Display tier (92 px). |
| `wordmark-icony.svg` | `tallykeep_wordmark_v1_lock.html` §4   | Wordmark with the canonical icon between "tall" and "keep". Display tier (92 px). |

All SVGs use `viewBox` for resolution-independent scaling. Sizing
in CSS via `width` / `height` overrides the intrinsic `width`/
`height` attributes.

## Sync rule

These files duplicate visual decisions made in the lock docs. The
duplication is deliberate:

- The lock doc serves human readers (the doc embeds inline SVG so
  it reads standalone).
- The SVG files serve machine consumers (mockups, frontend).

When a lock doc revises (v1 → v2), regenerate the corresponding SVG
file in this folder in the same change. Do not edit these files
without updating the source lock doc.

## Color tokens used (locked v1)

- **Aged Oak** `#A88554` — wood (stock + foil fill)
- **Grain** `#6F5638` — stripe lines (stroke 1.4, opacity 0.6)
- **Cream** `#F4EAD5` — carving fill in `icon-canonical.svg` and
  `icon-solid.svg` (the cream background of the rounded-square
  container shows through the cuts)
- **Page background cream** `#FAFAF7` — carving fill in
  `wordmark-icony.svg` (the icon reads as cuts into the page,
  not into a separate cream container)
- **Wordmark text** `#1A1A1A` (light surfaces) / `#F4EAD5` (dark
  surfaces) — see wordmark lock doc §7 for dark-mode rules

If the consumer renders on a different background than the locked
defaults, override the carving fill to match. The SVGs are
straightforward to override at the consumer site.

## Naming convention

`<artifact>-<variant>.svg`:

- `icon-canonical` — the default icon
- `icon-solid` — favicon variant
- `wordmark-plain` — wordmark without icon
- `wordmark-icony` — wordmark with embedded icon

When new variants are locked (e.g., dark-mode treatments, lockup
arrangements, monochrome versions), follow the same pattern.

## What does NOT live here

- React / Svelte components — those live in frontend code
  (e.g., `frontend/src/lib/components/BrandIcon.svelte`), not in
  the spec tree. Components import from this folder.
- Built artifacts (favicon.ico, app icon PNGs, social-card PNGs)
  — those are generated from these SVGs at build time and live
  alongside the frontend / marketing site, or in `brand/assets/`
  if a separate folder is added.
- Brand decisions, anatomy, geometry, color rationale — those
  stay in the lock docs one folder up.
