# Mobile mockups

Page-per-file HTML mockups for visual fine-tuning. Each file is
self-contained, imports shared tokens and shell styles, and
targets the mobile baseline viewport.

Working rules for mockups (page-per-file rule, status semantics,
ADR thresholds, baseline + smoke-test viewports) live in
`PROCESS.md §2.3` and `§5`. This file holds operational layout
only — naming, header structure, file structure, contact sheet.

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

Status field is one of `draft` / `review` / `validated`. Semantics
and the "ADR or no ADR" test for changes to a validated mockup are
in `PROCESS.md §7`.

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
- If a state needs interactivity to communicate, draft both states
  as separate files (e.g. `..._fiat_off.html` and
  `..._fiat_on.html`) rather than relying on JS toggles.
- Inline any per-screen CSS overrides in a `<style>` block at the
  top of `<head>`, after the shared CSS imports.

## Visual contact sheet

`index.html` in this directory loads all mockups as iframes for
at-a-glance review — useful for spotting drift across screens
(colors, type, spacing, navigation conventions).

When adding or removing a mockup, update the `mockups` array near
the top of `index.html`. The iteration-done sanity sweep
(`PROCESS.md §2.9`) verifies the array matches the files present.

Open `index.html` in any browser; click any card to open the
full-size mockup in a new tab.

## Pointers (don't duplicate the rules below)

- Page-per-file rule and rationale → `PROCESS.md §2.3`
- Baseline + smoke-test viewports, browser matrix →
  `PROCESS.md §5`
- Status semantics and ADR test → `PROCESS.md §7`
- Mockup-iteration acceptance (validated mockups referenced from
  `UI/mobile.md`) → `PROCESS.md §2.7`
