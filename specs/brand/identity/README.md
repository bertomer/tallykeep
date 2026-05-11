# brand/identity

Consumable graphic assets — clean SVG files extracted from the
brand lock documents. **This is the import source for mockups and
frontend code.** The lock HTML docs (one folder up) embed inline
SVG for human readers; these files are for machine consumers.

## Files

### Brand identity (mark + wordmark, v1 locked)

| File | Source lock doc | When to use |
|---|---|---|
| `icon-canonical.svg` | `tallykeep_brand_mark_v1_lock.html` §1 | Default. 32 px and up. With grain stripes. |
| `icon-solid.svg`     | `tallykeep_brand_mark_v1_lock.html` §2 | Favicon, ≤16 px. No grain (sub-pixel noise at small sizes). |
| `wordmark-plain.svg` | `tallykeep_wordmark_v1_lock.html` §3   | Plain typeset wordmark, no embedded icon. Display tier (92 px). |
| `wordmark-icony.svg` | `tallykeep_wordmark_v1_lock.html` §4   | Wordmark with the canonical icon between "tall" and "keep". Display tier (92 px). |

### Holding-type icons (v2 palette lock)

| File | Source lock doc | When to use |
|---|---|---|
| `holding-account.svg`           | `tallykeep_palette_v2_lock.html` §4 | Account type — classical pediment institution. Filled limestone. |
| `holding-purse-watch-only.svg`  | `tallykeep_palette_v2_lock.html` §4 | Purse with `seed_origin=external_watch_only`. Brass cord variant. Also the default/canonical "Purse" icon for the type chooser. |
| `holding-purse-managed.svg`     | `tallykeep_palette_v2_lock.html` §4 | Purse with `seed_origin=tallykeep_managed`. Dark cord variant. |
| `holding-strongbox.svg`         | `tallykeep_palette_v2_lock.html` §4 | Strongbox — iron chest. Filled dark steel. |
| `holding-vault.svg`             | `tallykeep_palette_v2_lock.html` §4 | Vault — brushed-steel door with brass hub, three T-handles, six inner tubes. Hinge on left. |

Holding icons are designed for ≥32 px (Add-Holding popup, detail headers). In Holding-list rows the icon is omitted and a 4 px colored stripe carries the type identification (color tokens `--color-holding-*`).

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

## Color tokens used

### Brand identity (locked v1)

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

### Holding-type icons (locked v2 palette)

- **Limestone** `#9c9388` — Account fill
- **Auburn leather** `#80452f` — Purse fill (both variants)
- **Iron** `#4a4d4f` — Strongbox fill
- **Brushed steel body** `#7a8189` and **frame** `#5c6470` — Vault
- **Brass** `#b89968` — Vault hub + ring, Purse watch-only cord
- **Dark cord** `#1a0805` — Purse managed cord (high-contrast against auburn)

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
