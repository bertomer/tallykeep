# Mobile mockups

Page-per-file HTML mockups for visual fine-tuning. Each file is
self-contained, imports shared tokens and shell styles, and targets a
mobile viewport.

## Why page-per-file

- Easier to fine-tune one screen without scrolling through 1000 lines.
- Easier to point a coding agent at "implement this screen" with one
  filename.
- Easier to diff individual screens across iterations.
- A mockup's status (draft / review / validated) is per-screen, which
  matches how decisions actually move through the project.

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
...

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

## Viewport target

Calibrated to the Argentine market (primary launch geography per
project plan): Samsung ~48% of devices, Motorola ~27%, Apple ~12%.
Mid-range Galaxy A and Motorola Moto G dominate.

- **Baseline: 360 × 800** (mid Galaxy A, Moto G — the broad
  mid-range). Mobile-first principle: if it works here, it works
  everywhere.
- **Smoke-test at:** 384 × 854 (Galaxy A56-class), 390 × 844
  (iPhone 14 / 15 / 16), 412 × 900 (larger Android, Pixel-style).
- **Browsers to check:** Chrome (region-leading), Samsung Internet
  (default on the largest phone share — Chromium-based but with
  quirks), Safari mobile (Apple share).
- Safe-area insets respected via the `.phone-screen` paddings in
  `_shared/shell.css`.

## Self-contained for review

- No JS dependencies. Static HTML + CSS.
- If a state needs interactivity to communicate, draft both states as
  separate files (e.g. `..._fiat_off.html` and `..._fiat_on.html`)
  rather than relying on JS toggles.
- Inline any per-screen CSS overrides in a `<style>` block at the top
  of `<head>`, after the shared CSS imports.

## Status field

Header `Status:` is one of:

- **draft** — under iteration; not yet reviewed
- **review** — submitted for review; pending feedback
- **validated** — design locked; the corresponding section in
  `UI/mobile.md` references this file

When a screen moves to validated, edit `UI/mobile.md` to lock the
reference. Cosmetic iteration on a validated mockup is fine
afterwards — edit the file and update its date. Changes that touch a
locked principle, reverse a foundational design decision, or affect
security / posture / vocabulary need an ADR plus a fresh draft.

Examples:

- *Edit, no ADR:* refining a label, tweaking tap targets, adjusting
  spacing, adding a tap-to-toggle on the unit indicator.
- *ADR + fresh draft:* adding a Send button to a screen previously
  decided to be view-only on browser, changing the trust boundary,
  modifying vocabulary, reversing a posture call.

The test: if it feels like *let me refine this*, edit. If it feels
like *wait, should we even do this?* — that's an ADR moment. (See
`PROCESS.md` §7.)

## Visual contact sheet

The visual index lives at `index.html` in this directory — a grid of
all mockups loaded as iframes for at-a-glance review. Useful for
spotting drift across screens (colors, type, spacing, navigation
conventions).

When adding or removing a mockup, update the `mockups` array near the
top of `index.html`.

Open `index.html` in any browser; click any card to open the full-size
mockup in a new tab.
