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

When adding or removing a mockup, update the `mockups` array
near the top of `index.html`. The iteration-done sanity sweep
(`PROCESS.md §Iteration-done sanity sweep`) verifies the array
matches the files present.

Open `index.html` in any browser; click any card to open the
full-size mockup in a new tab.

## Pointers

- Mockup-iteration acceptance (validated mockups referenced
  from `UI/mobile.md`) → `PROCESS.md §Iteration cycle`
- Routing table for ADR-vs-edit decisions → `PROCESS.md §When
  things change`
