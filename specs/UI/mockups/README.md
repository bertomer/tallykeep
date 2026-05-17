# Mobile mockups

Page-per-file HTML mockups for visual fine-tuning. Each file is
self-contained, imports shared tokens and shell styles, and
targets the mobile baseline viewport.

This file is canonical for all mockup-process rules:
page-per-file discipline, naming, header structure, status
semantics, viewports, browser matrix. PROCESS.md points here.

## Page-per-file rule

One `.html` per screen-state. Shared CSS lives in `_shared/`.
Big multi-screen wireframes are dev artefacts; archive them,
don't iterate on them.

The rule exists because mockup files diverge fast when they
carry multiple states. A single big-page mockup with five
sub-screens drifts on each edit; one of them gets fresh tokens
applied, the others don't, and a reviewer can't tell which
sub-screen represents current truth. One file per state, one
truth per file.

## Naming

```
mobile_<flow>_<step-or-state>.html
```

Examples:

```
mobile_home_empty.html
mobile_home_populated_fiat_off.html
mobile_home_populated_fiat_on.html
mobile_home_populated_security_discrepancy.html

mobile_send_01_compose.html
mobile_send_02_review.html
mobile_send_03_sign_external.html
mobile_send_04_broadcast.html
mobile_send_05_confirmed.html

mobile_holding_account_detail.html
mobile_holding_purse_detail.html
mobile_holding_strongbox_detail.html

mobile_add_holding_chooser.html
mobile_add_account_01_provider.html
mobile_add_account_02_credentials.html
mobile_add_purse_01_origin.html
mobile_add_purse_02_seed_backup.html

mobile_onboarding_01_welcome.html
mobile_onboarding_02_passphrase.html
mobile_onboarding_03_hosting_choice.html
mobile_onboarding_04a_connection_self.html
mobile_onboarding_04b_hosted_welcome.html

mobile_categorization_queue.html
mobile_categorization_item.html

mobile_blueprint_overview.html
mobile_blueprint_finding.html

mobile_settings_root.html
mobile_settings_technical_details.html
```

## File structure

Header comment lines (always include):

```html
<!--
  Title: Mobile — Home (populated, fiat off)
  Status: draft
  Date last touched: 2026-05-08
  Replaces: archive/UI/tallykeep_mobile_v2.html §Home (legacy)
-->
```

Status field is one of `draft` / `review` / `validated`.

**Status semantics:**
- *draft* — agent or Rémy is iterating on form / copy / layout;
  may break or contradict another mockup mid-pass.
- *review* — ready for Rémy's eyes; held at this status until
  he validates or sends back.
- *validated* — Rémy gave the explicit greenlight. The
  corresponding section of `UI/mobile.md` references the file.

**Cosmetic iteration on a validated mockup** (label tweak,
tap-target adjustment, micro-interaction polish, layout
reshuffle that doesn't change what's on the screen) — edit the
file and bump the date. No ADR.

**Structural change to a validated mockup** (touches a locked
principle, vocabulary, security/posture, trust boundary, or
reverses a foundational design decision) — new ADR, fresh
draft. Adding a Send button to a screen previously decided to
be view-only is the canonical example.

Each file imports shared CSS:

```html
<link rel="stylesheet" href="_shared/tokens.css">
<link rel="stylesheet" href="_shared/shell.css">
```

Body wraps content in a `phone-frame` for visual review:

```html
<body>
  <div class="phone-frame">
    <div class="phone-screen">
      <!-- screen content here -->
    </div>
  </div>
</body>
```

## Self-contained for review

- No JS dependencies. Static HTML + CSS.
- If a state needs interactivity to communicate, draft both
  states as separate files (e.g. `..._fiat_off.html` and
  `..._fiat_on.html`) rather than relying on JS toggles.
- Inline any per-screen CSS overrides in a `<style>` block at
  the top of `<head>`, after the shared CSS imports.

## Viewports

- **Baseline: 360×800** (mid Samsung Galaxy A, Motorola Moto G
  — broad Argentine mid-range). Mobile-first principle: if it
  works here, it works everywhere.
- **Smoke-test at:** 384×854 (Galaxy A56-class), 390×844
  (iPhone), 412×900 (larger Android).

## Browsers

Check at Chrome, Samsung Internet (default on the ~48% Samsung
share), Safari mobile.

## Visual contact sheet

`index.html` in this directory loads all mockups as iframes for
at-a-glance review — useful for spotting drift across screens
(colors, type, spacing, navigation conventions).

Open `index.html` in any browser; click any card to open the
full-size mockup in a new tab.

### Adding or removing a mockup

Edit the `mockups` array near the top of `index.html`. Every
entry has four fields:

```js
{ file:   'mobile_<flow>_<state>.html',
  title:  'Human-readable card title (matches the mockup header)',
  status: 'draft' | 'review' | 'validated',
  group:  '<one of the ids in GROUPS above>' }
```

The iteration-done sanity sweep (`PROCESS.md §Iteration-done
sanity sweep`) verifies the array matches the files present on
disk. The `group` field is enforced softly: an unknown id still
renders the card but logs a `console.warn` and the card stops
showing under a section pill — so check the browser console
after editing.

### Section pills (groups)

The gallery has two filter rows: **Section** (which flow) and
**Status** (draft/review/validated). Cards are also visually
grouped under a sticky section heading per group when scrolling,
so the structure is visible without filtering. The Section row
is driven by the `GROUPS` array near the top of the script:

```js
const GROUPS = [
  { id: 'onboarding',  label: 'Onboarding' },
  { id: 'unlock',      label: 'Unlock' },
  { id: 'home',        label: 'Home' },
  { id: 'add-holding', label: 'Add holding' },
  { id: 'account',     label: 'Account wizard' },
  { id: 'purse',       label: 'Purse wizard' },
  { id: 'strongbox',   label: 'Strongbox wizard' },
  { id: 'vault',       label: 'Vault wizard' },
];
```

Rules:

- **Order is user-lifecycle**, not spec-drafting order or
  custody-tier order. A pill row is a picker; the
  Holdings-picker discipline applies (Account first as the most
  common starting point for target-market users, then Purse,
  Strongbox, Vault). Section headers in the gallery render in
  this same `GROUPS` order regardless of the order entries
  appear in the `mockups` array, so re-ordering the array has
  no visual effect — re-order `GROUPS` if you want to change
  what users see.
- **No ad-hoc groups in entries.** If a new flow doesn't fit an
  existing group, add a new entry to `GROUPS` at its lifecycle
  position, then reference the new id from your mockup entries.
- **Empty groups are hidden.** The Section row only renders
  pills for groups that have at least one mockup, so adding a
  group ahead of its mockups is harmless.

### Preview frame sizing

The contact sheet renders each mockup at exactly the body's
natural content area — `392 × 896` — so every card shows the
full phone-screen including the bottom nav and any primary CTA
above it, with no spare slate background bleeding above or
below the phone-frame.

That `392 × 896` is derived from `_shared/shell.css`:

```
body padding:  var(--space-7) (48) top/bottom
               var(--space-4) (16) sides
phone-frame:   var(--mobile-viewport-width)  = 360
               var(--mobile-viewport-height) = 800   (border-box)
=> body content area = (16+360+16) × (48+800+48) = 392 × 896
```

If any of those tokens change, or `body { padding }` in
`shell.css` changes, update the `IFRAME_W` / `IFRAME_H`
constants in `index.html` and the `.preview { aspect-ratio }`
in lockstep — otherwise cards will show clipped chrome again.

Per-mockup content that lives **outside** the `.phone-frame`
(banners, debug helpers, mockup-meta overlays) is the one thing
that can break this contract: if it pushes the body taller than
896px, the bottom of the phone-frame gets cropped in the
gallery. Keep dev-only chrome inside fixed-position elements or
inside the phone-frame.

## Pointers

- Mockup-iteration acceptance (validated mockups referenced
  from `UI/mobile.md`) → `PROCESS.md §Iteration cycle`
- Routing table for ADR-vs-edit decisions → `PROCESS.md §When
  things change`
es the files present on disk.
