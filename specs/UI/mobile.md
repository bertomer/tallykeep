# UI — Mobile platform spec

This is the mobile platform spec. Cross-platform decisions (Holding
type vocabulary, unit + currency controls, flow inventory, honest
abstraction enforcement) live in `UI/README.md`. This file describes
how those decisions render on mobile, screen by screen, with the
reconcilability gauntlet answers attached.

## Status

The mobile spec is **iteration-driven**. Per ADR-0002 and the
working agreement in `PROCESS.md`, screen-by-screen detail is
authored alongside each iteration's mockups, not pre-specified
upfront. The active iteration's scope lives in `next_iteration.md`.

The original module 11 (`11_ux_flows.md`) carried screen-by-screen
ASCII layouts that predated the current mobile-first thinking and
the UI/README cross-platform decisions. That module retires in
the consolidation merge; its content is not ported here. Mockups
are authored fresh per iteration.

## What lives here

When an iteration produces mobile screen designs, this file gains a
section per flow, in the form:

```
## <Flow name>

### Screens
- `mobile_<flow>_<state>.html` — short description
- ...

### Reconcilability gauntlet answers
1. Trust boundary: ...
2. Keys and secrets: ...
3. Self-hosted vs hosted: ...
4. Confirmation honesty: ...
5. Browser-only fallback: ...
6. Open-source and reproducibility: ...

### Notes
<anything else worth keeping at the platform-spec level>
```

Mockups themselves live in `UI/mockups/` (one HTML file per
screen-state) per the convention in `UI/mockups/README.md`.

## What does NOT live here

- Cross-platform UX decisions — see `UI/README.md`.
- The flow inventory — see `UI/README.md` §"Flow inventory".
- Visual styling specifics — see `UI/mockups/_shared/tokens.css`
  and `UI/mockups/_shared/shell.css`.
- Implementation specifics (SvelteKit components, routing, state
  stores) — those are code, not spec.
- Brand identity, copy voice — placeholder per ADR-0003.

## Migration note for the first Send / Receive iteration

The per-Holding Send and Receive flow detail (Account "Withdraw
to whitelist", Purse external-watch-only redirect to source
wallet, TallyKeep-managed Purse native-sign vs gate, Strongbox
PSBT roundtrip, Vault) currently lives in `UI/README.md` §Send
and §Receive because it predates the iteration-driven
mobile-spec convention. **The first Send/Receive iteration's
scope must include moving that detail into the corresponding
flow sections of this file**, alongside the gauntlet answers,
and stripping it from `UI/README.md` (which then keeps only the
cross-platform flow inventory). This avoids the per-Holding
detail living in two places once mobile.md gains a real
`## Send` and `## Receive` section.

## Iteration roadmap (rough)

The pre-shipping mobile UI iterations target the private-ship event
(per ADR-0003). The roadmap is sketched in `next_iteration.md` and
typically begins with Onboarding + Home (empty + populated states),
followed by Add Holding, Holding detail per type, Send + Receive,
Activity + Categorization, Sweep policy + Treasury view, Settings.

When an iteration ships, its corresponding section appears below.

---

## Onboarding

### Screens

- `mobile_onboarding_01_connect.html` — first screen. Single
  question: "Connect to your TallyKeep." Primary path is QR scan
  (paired-from-desktop / Umbrel admin / hosted-tier instance).
  Secondary path is manual URL entry. Ghost CTA links out to docs
  for users who don't have a TallyKeep server running yet. A
  persistent "How TallyKeep works" disclosure card carries the
  three principles (open source, no accounts, TallyKeep never
  holds your keys) with an explicit "I understand" acknowledgment.
  Wordmark-icony at 280 px is the brand surface; intended to land
  as the dynamic-mark surface (tap to regenerate matching grain
  on both halves of the embedded Y) when the SvelteKit build
  ships — see `future_iterations.md` "Dynamic brand mark on
  first-touch surfaces". *Status: validated (Rémy greenlight 2026-05-10).*
- `mobile_onboarding_02_paired.html` — second screen (initial
  state). Combines pair-success confirmation + biometric setup.
  Header carries the same wordmark-icony (static after Screen 1).
  Below: green checkmark, "Paired with your TallyKeep", server
  label (`server_label` from `01_architecture.md`
  §"Configuration model"; absent ⇒ render endpoint or
  connection-ID instead). Divider, then the active section:
  "Lock TallyKeep with your biometric" with a Why-block
  explaining the threat model honestly ("Without it, anyone who
  can unlock your phone can open TallyKeep. With it, only you
  can."). Two CTAs: [Enable biometric unlock] primary,
  [Skip for now] text-link. *Status: validated (Rémy greenlight 2026-05-10).*
- `mobile_onboarding_02_paired_biometric_done.html` — second
  screen, post-biometric-enabled state. Single prominent
  success indicator (large green check), "All set" heading, a
  facts card showing both anchors ("Connected to: Rémy's home
  server" + "Daily unlock: Biometric · passphrase fallback"),
  [Continue] primary.
  Single CTA — no skip path from this state. *Status: validated (Rémy greenlight 2026-05-10).*
- `mobile_onboarding_02_paired_skip_confirm.html` — second
  screen, with bottom-sheet modal confirming the skip-biometric
  intent. Underlying screen visible behind a scrim
  (`var(--color-overlay)`); the sheet rises from the bottom with
  rounded top corners, grab-handle, "Skip biometric?" heading,
  body copy clarifying the consequence and that biometric is
  available later in Settings, two actions:
  [Cancel — set up biometric] (secondary surface) and
  [Skip — continue without] (warning-tinted, brand-soft amber).
  Pattern is mobile-native (iOS / Android both default to bottom
  sheets for confirm-or-cancel choices); preserves context so
  the user sees what they're about to skip past. *Status: validated (Rémy greenlight 2026-05-10).*
- `mobile_onboarding_02_paired_no_biometric.html` — second screen,
  variant rendered when the device's biometric capability check
  returns unavailable (no sensor, or OS disabled biometric for
  this app). Same paired-block at the top; the body section
  replaces the biometric prompt with an honest disclosure block
  ("This device doesn't have biometric. TallyKeep will rely on
  your phone's lock screen. ... Use your TallyKeep server
  passphrase to re-pair if needed.") tinted with the
  `--color-info-*` token family. Single [Continue] CTA — no
  enable / skip choice to make. `NativeBridge.canUseBiometric()`
  decides at Screen 02 entry which variant renders. *Status:
  draft.*

**Hosted-tier variant — not yet drafted, materially different.**
Sharpened during onboarding-screen-2 review 2026-05-10. The
self-hosted onboarding flow above (Connect → Paired →
biometric / passphrase / no-biometric variants → Home) is
distinct from the hosted-tier flow, which adds at least one
new screen and modifies others. Captured for sharpening when
the hosted-tier iteration promotes from `future_iterations.md`:

- *Hosted-tier signup* (likely happens in a web browser, outside
  the app — TBD). Generates a `crisp-river-7842`-style
  connection-ID; user sets a server passphrase.
- *Backup-credentials screen* (new, app-side). Critical step
  after first hosted-tier pairing: user must save their
  connection-ID + passphrase somewhere safe. Without email-based
  recovery, losing both = instance is gone (Bitcoin recoverable
  via hardware backup; TallyKeep state — categorizations, sweep
  policies, history — gone). Acknowledgment-required: "I've
  saved my credentials somewhere safe" before continuing. Same
  pattern as the `seed-backup-disclosure` security-health item.
- *Paired (biometric)* — same screen as self-hosted but server
  identifier surfaces the connection-ID alongside the label
  (e.g. `crisp-river-7842 · TallyKeep hosted`), endpoint is a
  TallyKeep-hosted URL (e.g. `https://app.tallykeep.io/...`).
- *Deep recovery copy differs.* Self-hosted shows "Re-pair from
  desktop"; hosted-tier shows "Re-pair from your hosted
  dashboard" (and the dashboard URL is part of the saved
  credentials). The traveling-hosted-tier-user-without-second-
  device edge case sharpens during the hosted-tier iteration.
- *Passphrase-fallback unlock* — same mechanism as self-hosted.
  Phone forwards passphrase to hosted backend for validation.

The hosted-tier flow is post-public-ship per
`future_iterations.md` "Hosted tier infrastructure", so it is
not drafted for the current iteration. The
`traveling-user-recovery` arbitration is resolved by ADR-0008
(two-layer unlock model). The `pairing-handshake-crypto` crypto
specifics remain open in `pre-implementation.md` but do not
block Screen 02 design.

## Daily Unlock

### Screens

- `mobile_unlock_biometric.html` — default daily-launch state.
  Brand strip (same wordmark, no dynamic-mark behavior on this
  surface), generic biometric glyph (Aged Oak primary tones)
  with "Unlock TallyKeep" heading and "Use your biometric to
  open the app" hint, "Use passphrase instead" text-link below.
  Bottom: small connection-status anchor ("Connected · server
  label") with a green dot. Renders by default when biometric
  is configured; the OS-native biometric prompt fires
  automatically on app open and overlays this view. *Status:
  draft.*
- `mobile_unlock_passphrase.html` — passphrase-entry variant.
  Renders when user (a) taps "Use passphrase instead" on the
  biometric variant, (b) is on a device without biometric, or
  (c) opted out of biometric during onboarding. Centered
  passphrase input (monospace, letter-spaced for password
  feel), [Unlock] primary CTA below, "Use biometric instead"
  text-link as the alt action (hidden if no biometric
  available). Same connection-status anchor at bottom. The
  typed passphrase is forwarded to the backend over the paired
  connection for validation; the phone never stores it.
  *Status: validated (Rémy greenlight 2026-05-10).*

### Reconcilability gauntlet answers

1. **Trust boundary.** Phone (UI + Keychain), the paired
   TallyKeep stack (passphrase validation endpoint, device
   credential registry). The Keychain entry holds the
   long-lived device credential; biometric (OS-managed) gates
   access to it. On passphrase-fallback unlock, the typed
   passphrase transits the paired connection — TLS in
   production deployments, plaintext-on-localhost in dev (per
   `01_architecture.md` §"Network security posture"; remote
   access adds TLS per `future_iterations.md` "Remote access
   for self-hosters").
2. **Keys and secrets.** Device credential lives in Keychain
   biometric-protected. Server passphrase is typed transiently
   for fallback validation; never stored on the phone, never
   logged.
3. **Self-hosted vs hosted.** Identical mechanism, different
   connection target. Self-hosted: phone talks to user's stack
   on LAN. Hosted: phone talks to TallyKeep-hosted backend over
   TLS. Both validate against the server's in-memory passphrase
   (server-side, established at server startup / hosted-tier
   claim).
4. **Confirmation honesty.** No positive end state to fake
   here — unlock either succeeds (lands on Home) or fails (error
   + retry). After N failed attempts, rate-limit kicks in
   (specifics sharpen during auth-layer iteration).
5. **Browser-only fallback.** Per ADR-0007. Browser-dev: the
   biometric glyph and "Use Face ID" copy stub via
   `NativeBridge.biometricUnlock()` returning a fixture or
   triggering the manual passphrase flow. The passphrase
   variant works in browser-dev against the local backend.
   Capacitor build replaces the stub with real biometric API
   calls.
6. **Open-source and reproducibility.** No closed-source
   dependency. Biometric is delegated to OS-provided APIs
   accessed via Capacitor plugins (license to verify before
   adoption).

### Notes

**Biometric is OS-managed; the in-app glyph is a waiting state,
not the prompt.** When the app opens with biometric enabled,
the OS-native biometric prompt fires immediately (overlay on
top of this view). The glyph rendered in
`mobile_unlock_biometric.html` is what the user sees if they
dismiss the OS prompt or while waiting for it to render. It is
explicitly *not* the prompt itself — that's OS chrome and
varies by device.

**Connection-status anchor at the bottom is a deliberate
banking-grade choice.** The user sees that their server is
reachable BEFORE they've unlocked the app. Adapted from
`archive/UI/tallykeep_mobile_v2.html` §A3, with one important
change: we do NOT show the balance pre-unlock. Showing the
balance pre-unlock is a small but real privacy leak (anyone
glancing at a locked phone sees the user's holdings). The
v2 mockup had "Connected · 832,501 sats" — that's a leak.
Corrected here to "Connected · Rémy's home server" (just the
reachability + label, no balance).

**Passphrase input is monospace with letter-spacing.** Banking-
app convention for masked input fields. The user can confirm
they're typing the right number of characters; the
letter-spacing visually distinguishes from regular text input.

**Unlock screen has no nav, no escape.** The user can only
unlock or quit the app. No bottom nav, no settings access from
this surface. Matches banking norms.

---

## Home

### Screens

- `mobile_home_empty.html` — empty state, post-onboarding, no
  Holdings yet. App bar with small wordmark-icony at left
  (120 px, static, no dynamic-mark behavior on this surface).
  Hero on its own white-surface block (`--color-surface` with
  bottom border, visually distinct from the page bg below):
  "TOTAL BALANCE" small uppercase label, left-aligned `0` amount
  at 36 px semibold in Manrope tabular-nums (per
  `brand/README.md` §"Typography conventions"), baseline-aligned
  with a small unit column to the right (a 14-px cycle icon
  stacked above a `sats` label — the icon is the affordance for
  cycling sats / BTC, the label is just the unit). Subdued
  `Show in fiat` link beneath the amount (dim, no underline, no
  arrow — we don't push fiat). Below the hero: a "HOLDINGS"
  section header (uppercase 11 px, muted) with a small
  filled-primary `+` button right-aligned. An empty list-card
  placeholder below the header carries "No Holdings yet"
  (`--color-text-dim`, small, centered). Bottom nav with four
  tabs: Home (active, with a 2 px verdigris top-indicator),
  Activity (greyed, no transactions yet), Holdings (greyed,
  no Holdings yet), More (enabled — Settings always works).
  *Status: validated (Rémy greenlight 2026-05-10; re-validated
  2026-05-13 after the cosmetic pass — filled-primary `+`
  button, 2 px verdigris top-indicator on active nav, hero
  amount swapped to Manrope tabular-nums).*

- `mobile_home_populated.html` — populated state, one row per
  Holding type as the canonical sample. Same chrome as empty.
  Hero amount shows the consolidated total (`4 358 921 sats` in
  the sample) in Manrope tabular-nums. Below the section
  header, a list-card with rows in custody-tier order
  (Account → Purse → Strongbox → Vault). Each row: 4 px stripe
  in `--color-holding-{type}` (brass for Vault per palette v2
  lock §4 update 2026-05-13), name (Manrope 600), meta line
  (source name — Phoenix / Coldcard Mk4 / Kraken; or
  "2-of-3 multisig" for Vault since multisig structure is the
  identity), amount in Manrope tabular-nums right-aligned with a
  small `sats` unit label. Filled-primary `+` button and active-
  nav indicator match the re-validated empty state. *Status:
  validated (Rémy greenlight 2026-05-13).*

Remaining populated variants — discrepancy banner (driven by
the security-health system), fiat-on display, scanning-in-
progress row state (driven by scan-status SSE event) — are
deferred to subsequent iterations once their drivers ship.

### Reconcilability gauntlet answers

1. **Trust boundary.** Phone (UI). The Home screen renders
   data the backend already sent (balance = 0 in empty state).
   No signing material, no credential transit on this surface.
   The Add-Holding CTA opens a popup with four type choices
   (per `next_iteration.md` transient — "Home empty's four Add
   affordances are a popup on Add-Holding tap, not directly
   inline on the empty state"); each Holding-type flow then
   carries its own gauntlet, sharpened in the Add-Holding
   iteration.
2. **Keys and secrets.** None on this screen. The aggregated
   balance comes from cached server state (or live data via
   SSE when populated). No descriptors, no API keys, no
   passphrases displayed.
3. **Self-hosted vs hosted.** Identical surface. The server
   identifier appears in Settings (More → Settings), not on
   Home. Per ADR-0008, the same passphrase model applies on
   both; that's an auth-layer concern that doesn't surface on
   Home.
4. **Confirmation honesty.** Balance shown is the latest
   confirmed value from the backend (which the backend
   computed from confirmed UTXOs only — pending UTXOs surface
   on Activity or in per-Holding detail per `concerns/observation.md`,
   not on the consolidated total). At zero state there's
   nothing to confuse.
5. **Browser-only fallback.** Per ADR-0007. The Home screen
   itself works fully in browser-dev — no
   Capacitor-only capability is exercised here. Add-Holding
   tap opens a popup that fans out into type-specific flows;
   the TallyKeep-managed Purse path is the only branch that
   needs Capacitor and renders an honest gate in browser
   ("this requires the TallyKeep app" per ADR-0006).
6. **Open-source and reproducibility.** No closed-source
   dependency. SVG icons in the nav are inline geometric
   shapes (draft-tier; will refine with the icon system later).

### Notes

**Banking-grade structure, not minimal aesthetic.** Sharpened
in two passes 2026-05-10. The first pass (rejected by Rémy)
centered everything and showed a big primary "Add Holding"
button — too close to Phoenix's wallet aesthetic, not banking-
grade. The corrected design adapts the v2 §B1 (populated)
layout pulled back to zero state: left-aligned mono amount
(institutional — numerals don't shift position as they grow),
hero on its own white-surface block, sectioned layout with a
"Holdings" header + `+ Add` link, empty placeholder card
beneath. The user feels the app's information architecture
from the start.

**Amount typography — Manrope tabular-nums, left-aligned.**
Tabular numerals are the institutional-banking default —
they read as data, not display copy, AND digits in a column
align (1 occupies the same width as 8). Left-aligned means the
leftmost digit stays at a fixed position as the number grows
(0, 100, 1,000, 1,000,000 all start at the same x-coordinate).
Centered numerals shift around; banking-grade does not.

Earlier draft used `--font-mono` (system monospace) for the
"institutional data" effect; swapped 2026-05-13 to
`--font-sans` + `font-variant-numeric: tabular-nums` after
side-by-side review revealed the Manrope-vs-Consolas mismatch
on Windows read worse than mono did better. Manrope supports
tabular numerals — same alignment property, native to the
brand typeface. Convention locked in `brand/README.md`
§"Typography conventions"; `--font-mono` stays defined and is
reserved for code-shaped content (BIP 380 descriptors,
addresses, transaction IDs, passphrase entry).

**Unit-label sized for cycle balance.** The `sats` label sits at
`--font-size-md` (16 px) rather than `--font-size-base` (14 px).
The bump anticipates the cycled state — lowercase `sats` next to
all-caps `BTC` would feel weight-asymmetric if `sats` were
minimally sized. 16 px keeps both states visually balanced when
the user toggles.

**Unit cycle is `↻` in superscript-position next to "sats".**
Sharpened across three passes 2026-05-10. First: `sats ⇄`
pill (rejected, made the unit feel like a button). Second:
Feather-style refresh-cw SVG stacked above "sats" (rejected,
read as "system reload"). Final: literal Unicode `↻` (U+21BB
"Clockwise Open Circle Arrow") rendered in superscript-position
to the right of `sats` — think `sats²` notation but with `↻`
as the exponent. The `↻` is the tap-affordance for cycling
sats / BTC. The "what's behind" gesture is the right metaphor
— same family as the "Tap to see under the hood" UI spine
pattern captured in `future_iterations.md`. The Unicode
character keeps the rendering simple (no SVG mimicry, single
glyph) and lighter than the rotate-style SVG variants. On
cycle, the amount re-formats (e.g. `0` sats → `0.00000000`
BTC) and the label changes (`sats` → `BTC`). When fiat is
enabled, a third state is reachable: the fiat amount appears
on its own line below.

**Show-fiat is intentionally suppressed.** First-pass had it
as a primary-color underlined link. Corrected: dim text, no
underline, no arrow. Fiat consolidation is opt-in per
`UI/README.md`; we surface the option but don't push it. The
brand position is sats-first — fiat is a translation layer
for users who want it, not a recommendation.

**Bottom nav present from empty state.** Sharpened
2026-05-10. Rémy's call against hiding the nav until populated:
"I want to feel what should be inside. Phoenix doesn't have a
nav bar and has an overcrowded burger menu — it's not better."
Tabs are placeholders for plausible top-level surfaces
(Activity, Holdings, More) and let the user feel the app's
shape from the first launch. Activity and Holdings are greyed
since they have nothing to show yet; More stays enabled
(Settings always works — server identifier, biometric toggle,
unpair, etc.). The exact tab set is not locked — sharpens with
the Settings + Activity iterations.

**Section structure is preserved even at zero state.** The
"Holdings" section header + `+ Add` link sits between the
consolidated view and the (empty) list — even with nothing in
the list. Rémy's explicit call: "the section should be marked
between the consolidated view and the start of the list of
holdings, even if there is none." This locks the user's mental
model of the app's information architecture from the first
launch; subsequent populated states slot into the same
structure without re-organizing the screen.

**Add affordance is a 28 px rounded-square filled-primary
button.** Sharpened across four passes 2026-05-10 → 2026-05-13.
First (2026-05-10): big centred primary CTA (rejected — too
"shiny", Phoenix-coded). Second: small `+ Add` text-link in
the section-head (rejected — translation friction: "Add"
varies in width across languages and `+` alone is universal).
Third: circular filled button with a bold `+` glyph (rejected
— felt "fat" and too prominent for a section-header
affordance). Fourth (2026-05-10 landing): 28-px rounded-square
(`--radius-md`), 1.5-px solid primary-colour outline,
transparent background, SVG `+` inside — quieter than filled,
still unambiguous. Fifth (2026-05-13 cosmetic pass): swapped
to filled-primary verdigris with white glyph after the
populated home felt under-coloured (the earth-tone Holding
stripes were the only colour on the page, primary verdigris
only appeared in the active-nav label). Rounded-square filled
at 28 px reads as a banking-grade CTA (the earlier "too fat"
rejection was about CIRCULAR filled, which feels chubby —
rounded-square reads taut). On tap, opens the Add-Holding
picker bottom sheet (see `## Add Holding` below).

**Active nav indicator — 2 px verdigris top stripe.** Added
2026-05-13 alongside the filled `+` button to plant the brand
colour more visibly on the page. The 60 %-width centred
indicator above the active tab works in peripheral vision; the
user can spot the active tab without reading the label. Bottom
rounding on the indicator (`border-radius: 0 0 sm sm`) gives
it a softer landing.

**Translation-free affordances where possible — locks a
discipline for the rest of the app.** This is the first surface
where translation friction surfaced; the discipline going
forward is: prefer icon-only or symbol-only affordances over
labeled buttons when the meaning is unambiguous from context
(section-head `+`, unit cycle icon, etc.). Use labels when the
meaning needs words (primary CTAs like "Enable biometric
unlock", "Continue", "Unlock" — these carry semantic content
that can't be reduced to a symbol). LatAm/Africa target markets
will multiply translation surfaces; small affordances multiplied
across screens compound the impact.

**Empty placeholder card marks the structure.** A thin
`--color-surface` card beneath the section header with "No
Holdings yet" centered in muted text. Banking-grade restraint:
the section is visibly there, marked as empty, no welcome
copy.

**No Send / Receive on empty Home.** v2's populated home had
these as primary actions next to the hero. On empty Home there's
nothing to Send (zero balance, no Holding to send from) and
Receive only makes sense per-Holding (each Holding has its own
descriptor). Both surface on the populated states + per-Holding
detail pages, not here.

**No security-discrepancy banner on empty Home.** Per
`UI/README.md` "Home" — the banner fires when the analyzer
detects declared-vs-observable mismatch; with no Holdings,
nothing to analyze. Banner sharpens when populated states are
drafted.

**Populated home sort order — custody tier ascending.** Sorted
by Holding type in the same order as the Add-Holding picker
(Account → Purse → Strongbox → Vault — hot-to-cold,
least-sovereign-to-most-sovereign). Within a tier with
multiple Holdings of the same type, secondary sort is
creation-date ascending (oldest first). Sort options (toggle
to by-amount or by-recency) are a polish concern for a
follow-up iteration if the default doesn't hold for real use.

**Source-name meta lines over script-type jargon.** The line
under each Holding name shows the source identity (provider
for Account, hot-wallet app for Purse, hardware device for
Strongbox) rather than the technical script-type
(`P2WPKH`, `P2TR`). Target-market users know "Phoenix" and
"Coldcard Mk4"; they don't know what P2WPKH means. Vault is
the exception — multi-sig structure ("2-of-3 multisig") IS the
identity, no single device name captures it. The source-name
field is captured optionally in each per-type wizard's label
step (per-type dropdown + Other → free-text); when skipped,
meta falls back to friendlier script-type spellings ("Native
segwit", "Taproot", "Multi-sig").

**Brass Vault stripe — brand-cohesion thread.** The Vault
row's 4 px stripe renders in brass (`#b89968`) rather than
brushed steel (`#6c7682`) per the palette v2 lock §4 update
2026-05-13. Brass echoes the brass hub in the Vault icon and
the brass cord in watch-only Purse — same brand-cohesion
thread carried out from icon-detail to surface-wide identity.
The Vault icon body itself stays brushed-steel internally; the
brass move is on the framing (token-driven stripe + picker
icon-border), not on the icon's body fill.

### Reconcilability gauntlet answers

1. **Trust boundary.** Phone (UI), local browser/Capacitor runtime
   (renders the screen, holds no state yet), the user's TallyKeep
   stack (the QR's source — desktop, Umbrel/Start9, or future
   hosted-tier). At this screen no credential, no key, and no
   user data has been exchanged. Scanning the QR initiates the
   pairing handshake; only after pairing succeeds does the phone
   begin to hold a device credential in its Keychain/Keystore. The
   phone never sees signing material; signing material lives only
   on devices that hold it (per the locked architecture in
   `01_architecture.md` and `concerns/threat_model.md`).
2. **Keys and secrets.** None on this screen. The QR carries an
   endpoint URL plus a single-use ephemeral pairing token (per
   `pre-implementation.md` `pairing-handshake-crypto`'s leading
   direction). The phone exchanges the token for a long-lived
   per-device credential stored in Keychain/Keystore
   biometric-protected. The user's app-encryption passphrase
   (per `01_architecture.md` §"Configuration model") is set
   server-side once when the stack is deployed; the phone never
   learns it.
3. **Self-hosted vs hosted.** Identical structurally — the question
   "where is your TallyKeep?" has one answer-shape: an endpoint
   the phone can reach. Mechanics differ behind the screen
   (mDNS/local-LAN pairing for desktop self-host, server-URL entry
   for Umbrel/Start9 self-host, future connection-ID claim for
   hosted-tier). Disclosed honestly in the principles card; the
   hosted-tier-specific privacy boundary is acknowledged via the
   security-health system once that path is functional (see
   `future_iterations.md` "Hosted tier infrastructure").
4. **Confirmation honesty.** The screen has no positive end state
   to fake. The QR scan initiates pairing; the post-pair
   confirmation screen (next iteration) shows pairing-completed
   only after the backend acknowledges the device credential.
   No "connected" tick before the handshake completes.
5. **Browser-only fallback.** Per ADR-0007, the screen is designed
   for the Capacitor target and renders in the browser with honest
   gates. In browser-dev: the QR scan affordance is visible but
   the camera launch is stubbed via `NativeBridge.scanQR()` (returns
   a fixture URL or a "this build cannot scan — Capacitor needed"
   banner per ADR-0007). The "Enter server URL manually" path is
   fully functional in browser-dev — typically `http://localhost:8080`
   in dev — and is what Rémy uses today before the Capacitor wrap
   lands.
6. **Open-source and reproducibility.** No closed-source
   dependency. The QR-scan plugin (private-ship gate) will be a
   Capacitor community plugin — license to verify before adoption.
   The "How TallyKeep works" card asserts open-source as a
   principle the user can verify; this is bound to the ship-gate
   reproducible-build pipeline in `future_iterations.md` to make
   the assertion provable.

### Notes

**Welcome screen killed deliberately.** Earlier drafts (e.g.
`archive/UI/tallykeep_onboarding_validated.html` step 1, and
`archive/UI/tallykeep_mobile_v2.html` §A1's logo header) had a
standalone Welcome with a logo and tagline. We dropped it: a
splash with "banking ergonomics for your Bitcoin" before the
content screen is marketing self-talk that any wallet app would
write. The first screen's *shape* is the positioning — asking
"where is your TallyKeep?" tells the crypto-aware user "we know
you know" without lecturing, and tells the curious user "this
is a tool, not a one-tap wallet." A skippable Welcome would be
clutter; either it's load-bearing or it's gone.

**Principles card — acknowledgment flow with Security health
fallback.** Sharpened across the onboarding sessions
2026-05-10. Two paths:

- *Acknowledged on Screen 01.* User clicks `[I understand]`.
  Card disappears permanently. Principles never re-surface
  on subsequent onboarding screens or on Home. Re-readable
  anytime via Settings → "How TallyKeep works".
- *Skipped on Screen 01.* User taps "scan QR" (or the manual
  URL entry / docs ghost CTA) without clicking
  `[I understand]`. The card disappears from the onboarding
  flow (we don't re-surface it across Screens 02 / Unlock /
  etc. — those are not the place). Instead, an "Acknowledge
  how TallyKeep works" item appears in the **Security health**
  zone on Home, alongside the seed-backup warning, future
  UTXO-reuse warnings, declared-vs-observable mismatches, etc.
  User dismisses it from there by tapping into the item and
  acknowledging.

The Security health zone is its own iteration (per
`future_iterations.md` "Security-health system", milestone
pre-shipping). For the current Onboarding iteration's empty
Home, the zone does not yet appear — meaning a skip during
personal-use phase leaves the principles unacknowledged with
no re-surface (acceptable since Rémy is the only user during
this phase and will acknowledge on first launch). Public-ship
requires the Security health iteration to have landed for the
cycle to close cleanly. Cross-iteration dependency captured
in `next_iteration.md` transient bullets.

The user-visible heading on Home for this zone is
**"Security health"** — consistent with banking-grade norms
(Apple Health "Health checks", "Account health" in retail
banking apps) and accurate to the framing: the principles
(open source, no accounts, no key custody) ARE the security
model at the architecture level. Item copy stays calm and
descriptive; the heading carries the seriousness register.

**"Don't have a TallyKeep yet? →" links out to docs, not in-app.**
There is no in-app fictional mode — the architecture (Docker
Compose stack with bitcoind, ~hundreds of GB) cannot run on a
phone. The honest path for a user without a stack is an external
docs link explaining what TallyKeep is and how to get a stack
running (Docker Compose on a desktop, Umbrel/Start9 install,
eventually the hosted tier when it ships per ADR-0003).

**One passphrase per stack.** Sharpened during this session: the
only passphrase TallyKeep asks for is the server-side one
(per `01_architecture.md` §"Configuration model"). The mobile
client uses biometric to unlock its Keychain entry — no separate
mobile-side app-lock passphrase — and recovers from broken
biometric by re-pairing from the desktop. The traveling-user
edge case (hosted-tier, biometric-broken, no other device) is
arbitrated separately under `pre-implementation.md`
`traveling-user-recovery`.

**Third principle line — architectural truth, not a specific case.**
"Your keys stay on your phone" (the wording in
`archive/UI/tallykeep_mobile_v2.html` §A1) is only accurate for the
TallyKeep-managed Purse on the Capacitor device that created its
seed. For Account, external-watch-only Purse, Strongbox, and Vault,
TallyKeep doesn't hold keys at all — they live at the custodian, in
the user's other wallet, on a hardware device, or distributed across
multisig cosigners. The cross-type architectural truth is that
TallyKeep itself never holds spending keys. The 1-liner used —
*"Your keys stay yours. TallyKeep never holds them."* — captures
that universal principle. Specific per-Holding key-storage
disclosures appear contextually on each Holding-creation flow and
detail page, not on the onboarding screen.

**Brand v1 lockstep.** The screen uses `_shared/tokens.css` and
`_shared/shell.css`. The brand mark is currently inlined in the
mockup as a frozen copy of `brand/identity/icon-canonical.svg` —
`<img src="../../brand/identity/icon-canonical.svg">` proved
unreliable under the design machine's local file:// loading.
Comment in the mockup flags the lockstep responsibility. The
SvelteKit build will consume identity/ directly via component
imports, removing this workaround. Colors, typography, and spacing
are all token-driven; no inline brand decisions.

**Two-layer unlock model — biometric default, passphrase fallback,
QR-re-pair for deep recovery.** Sharpened during the
onboarding-screen-2 sessions 2026-05-10. The unlock model is:

- *Daily unlock — biometric.* Default and convenient. Gates the
  Keychain entry holding the device credential.
- *Daily unlock — passphrase fallback.* Always available, on the
  unlock screen as a "Use passphrase instead" text-link below the
  biometric prompt. User types their TallyKeep passphrase; the
  phone forwards it to the server over the paired connection;
  server validates against the in-memory passphrase (the same one
  it uses to decrypt secrets per `01_architecture.md`
  §"Configuration model"); server returns OK / NO; phone unlocks
  the local credential on OK. The phone never *stores* the
  passphrase — it accepts user input and forwards. Standard
  banking-app pattern.
- *Deep recovery — re-pair via QR.* For the case where the local
  device credential is lost entirely (app reinstall, phone wipe,
  factory reset). User runs the pairing flow again — same QR
  scan as initial pairing. Self-hosted: walk to desktop, generate
  fresh QR from "Paired devices" panel, scan. Hosted-tier: open
  the hosted dashboard via web browser, authenticate with
  connection-ID + passphrase, generate fresh QR, scan.

The model preserves "one passphrase per stack" — the only
passphrase that exists is the server's, used in three places:
(i) server startup (decrypts secrets), (ii) phone unlock
fallback (validated by server, unlocks local credential),
(iii) hosted-tier dashboard auth. No second passphrase to
remember.

**Why biometric is opt-in, not required.** Target markets
(LatAm/Africa) include significant Android device populations
where biometric sensors are inconsistent in quality or
availability. A required biometric would lock those users out.
With the corrected model above, "skipping biometric" no longer
trades security for convenience — it just means using the
passphrase as the daily unlock instead of as a fallback.
ADR-0003's mention of "passphrase + biometric" for the
private-ship gate maps onto this corrected model cleanly: there
is a passphrase (the server's) and biometric is an additional
convenience layer.

**Threat-model copy was wrong — softened on review 2026-05-10.**
The skip-confirm bottom sheet originally carried scary "anyone
who unlocks your phone can open TallyKeep" copy. That copy was
written under the assumption that skipping biometric meant
OS-lock-only protection. With passphrase fallback always
available, the choice between biometric and passphrase-only is
just a preference between two valid unlock methods — not a
security tradeoff. The sheet copy now reflects this honestly:
"You'll type your TallyKeep passphrase each time. You can
enable biometric anytime in Settings."

**Recovery model — resolved 2026-05-10.** Resolves
`pre-implementation.md` `traveling-user-recovery`. There is no
separate mobile-side recovery passphrase. The phone-side
unlock surface offers biometric (with passphrase fallback);
when the local credential is fully lost, the user re-pairs via
QR. Self-hosted recovery = trip to desktop; hosted-tier
recovery = authenticate to hosted dashboard, regenerate QR.
The traveling-user edge case (hosted-tier user without a
second device to show a QR) sharpens during the hosted-tier
iteration — but the passphrase-fallback unlock path covers
day-to-day frustration without requiring re-pair.

**Skip-biometric confirmation is a bottom sheet, not a full page.**
The skip-confirm answer was an open question when Screen 02 was
sharpened. Drafting all three states (initial, biometric-done,
skip-confirm) as separate mockup files forced the answer
explicitly: bottom sheet wins because it's a momentary pause to
confirm a choice, not a destination state, and it preserves
context (the underlying screen stays visible behind the scrim so
the user sees what they're skipping past). Industry pattern is
identical (iOS / Android both default to bottom sheets for
confirm-or-cancel choices). Consequence: the same pattern can be
reused throughout the app for any "are you sure?" gate
(skip-onboarding-step, hide-balance, sign-out, delete-Holding,
etc.).

**Server identifier rule.** Sharpened during the
onboarding-screen-2 session 2026-05. Single-server-per-client is
the default; the Connect screen and Paired screen render the
server's identifier (server_label if set, falling back to
endpoint URL or hosted-tier connection-ID) primarily for sanity
("did I scan the right QR?"). Multi-server-per-client is captured
as a post-public-ship future iteration (`future_iterations.md`
"Multi-server per single client") and is not blocking for
private-ship or public-ship.

**Brand strip continuity across onboarding.** Same wordmark-icony
at 280px on every onboarding screen. Visual continuity = "we're
still in the onboarding surface" without needing a step indicator.
Going smaller after Screen 1 would feel like the brand recedes,
fighting the relationship-establishment beat of Screen 02.
Dynamic-mark behavior is Screen-1-only (per the "first-touch only"
sanctioning); Screen 02's wordmark is static.

**Dynamic brand mark — proposed extension, deferred.** The brand
v1 mark lock doc (`brand/tallykeep_brand_mark_v1_lock.html` §5)
already implements the tap-to-regenerate-grain interaction (~80
LOC, seeded PRNG, both halves regenerate matching stripes — the
verification metaphor of split tally sticks made tactile). It is
currently sanctioned for the **landing-page hero only**. A natural
fit candidate is this Connect screen — the user's first-touch
moment in the app is the same shape of moment as a landing-page
hero, and the verification metaphor is what TallyKeep's whole
brand argues. Bringing it into Connect requires a brand v1 → v2
lock-doc bump (per `PROCESS.md §2.4` — pre-public-ship lock-doc
edits allowed without an ADR) updating §5 to extend the sanction.
Captured for sharpening in `future_iterations.md` as
"Dynamic brand mark on first-touch surfaces"; not landed in this
mockup because mockups are static-only per
`UI/mockups/README.md`.

---

## Add Holding

The scaffolding iteration (`next_iteration.md`) ships the
picker entry surface plus a type-parameterized "coming soon"
stub for every tile tap. Per-wizard surfaces (Purse / Strongbox
/ Vault descriptor wizards, Account provider-key wizard) ship
in subsequent iterations as each design pass validates the
relevant mockups — entries will appear in this section as those
iterations close, each with its own gauntlet pass.

### Screens

- `mobile_add_holding_picker.html` — bottom-sheet picker open
  over Home empty (scrimmed). Four rows in custody-progression
  order: Account → Purse → Strongbox → Vault. Each row carries
  a 44 px icon (inlined from `brand/identity/holding-*.svg`)
  inside a 2 px-bordered rounded square, with the border
  tinted `--color-holding-{type}`; bold name; one-line
  description; chevron. Sheet title *"Add a Holding"*, sub
  *"Each holds your keys differently."* Cancel button at
  the bottom. Sheet rises from the bottom with slide-up
  animation; scrim at `--color-overlay`. *Status: validated
  (Rémy greenlight 2026-05-13).*

- `mobile_add_holding_coming_soon.html` — one-screen stub
  parameterized by Holding type, used in this iteration by all
  four tile taps. (Account because the Add Account wizard ships
  in its own follow-up iteration with ccxt provider integration;
  Purse / Strongbox / Vault because their descriptor wizards
  ship in subsequent iterations each.) App bar with back
  chevron + screen title ("Add a Purse" / "Add a Strongbox" /
  etc.), centred body with a 96 px Holding icon (same per-type
  bordered framing as the picker row, sized up), heading
  *"Coming in an upcoming iteration"*, paragraph copy
  acknowledging API workaround for dev-phase users, "Return to
  Home" secondary CTA. Bottom nav unchanged. *Status: validated
  (Rémy greenlight 2026-05-13).*

As each wizard iteration ships, its tile starts routing to the
real wizard instead of the coming-soon stub. Promotion order
locked in `future_iterations.md`: **Purse first** (canonical
descriptor wizard, also carries the shared wizard shell into
the codebase since it's the first consumer), then Strongbox
(copy + framing variant on Purse), then Vault (multisig-only
+ framing pre-card), then Account (different surface — ccxt
provider integration, no descriptor parser).

### Reconcilability gauntlet answers

1. **Trust boundary.** Phone (UI only). The picker is local
   sheet state — no backend call when opening or dismissing.
   The coming-soon stub is a UI dead-end — no backend
   interaction. The backend interaction (descriptor validation,
   per-type Holding creation) lives in the per-wizard
   iterations that ship later; for this scaffolding iteration
   the stub is the honest "nothing happens yet" gate. The
   backend endpoints DO ship in this iteration (so the
   populated home can render against Swagger-seeded fixture
   data), they're just not yet reachable from inside the app.

2. **Keys and secrets.** None on these surfaces. No descriptor
   input, no API keys, no passphrases. Per-wizard gauntlet
   answers — touching descriptors (Purse / Strongbox / Vault)
   and API credentials (Account) — land with each wizard's
   iteration.

3. **Self-hosted vs hosted.** Identical surface. The picker
   and stub render identically regardless of the connection
   target. The Holding-create backend endpoints behave
   identically on both deployment models per
   `01_architecture.md`.

4. **Confirmation honesty.** Picker doesn't promise anything
   — it presents the four type choices. Stub is explicit
   ("Coming in an upcoming iteration") plus an API-workaround
   disclosure for technical users ("Backend support is in
   place — Holdings can be added via the API for now"). No
   "added!" state shown before anything is added.

5. **Browser-only fallback.** Per ADR-0007. Both surfaces are
   fully browser-compatible. No Capacitor-only capability is
   exercised on the picker or stub — no QR scan, no biometric,
   no secure-storage write. The deferred wizard capability
   checks (managed-Purse on Capacitor-with-secure-storage,
   QR-scan via camera) land with their respective wizard
   iterations alongside honest browser gates.

6. **Open-source and reproducibility.** No closed-source
   dependency. Inline SVG icons from `brand/identity/`,
   token-driven styling (no raw hex in component CSS), no
   third-party JS libraries on these surfaces.

### Notes

**Picker order is custody-progression / lifecycle, not
brand-pitch.** Sharpened during the design pass 2026-05-13.
Hot-to-cold, least-sovereign-to-most-sovereign: Account
(third-party custody) → Purse (your phone, daily) → Strongbox
(hardware, short-term cold) → Vault (multisig, long-term
ceremonial). Pedagogically stronger than "lead with the
sovereignty pitch" (Purse first) because the ordering tells a
story across the four rows — where money typically starts,
where it lives daily, where it accumulates short-term, where
it sits long-term. Earlier draft proposed Purse-first; Rémy
reframed as lifecycle arc.

**Rows-only layout, cards variant rejected.** Earlier
design-tool prototype toggled between row and 2×2 card
variants. Rows won: four options on a mobile sheet earn rows
(single-column read, no eye-darting, description text never
crops). Cards earn their keep at 6+ options or when each
option's thumbnail is the primary signal — neither holds for
four Holding types.

**No "Recommended" pill in this iteration.** The pill is
meaningful only when managed-Purse capability is available
(Capacitor with secure-storage backend). Shipping a
conditionally-rendered pill that's always-false in dev phase
would mean shipping capability-check infrastructure with no
visible consumer. The pill, the capability check
(`device.capabilities.canStoreSeed`), and the Purse-wizard
managed-flavor branch all land together in the Capacitor-wrap
iteration, where they have a working surface to attach to.
General discipline: honest gate via *absence of affordance*,
not stubbed APIs returning false.

**Picker tile copy — locked.** Each row's one-line description
follows a parallel axis (where the key is + how often you
touch it):

- *Account:* "Held at an exchange or broker. They hold the
  keys; you see balances."
- *Purse:* "On your phone. For daily spending."
- *Strongbox:* "On a hardware wallet. For amounts you spend
  rarely."
- *Vault:* "Multiple keys required. For amounts you rarely
  touch — years, not days."

Earlier design-tool prototype said "you hold the key" on
Strongbox specifically, which was wrong — true of Purse and
Vault too; only differentiator-from-Account. The parallel axis
(where + when) is what distinguishes the four types from each
other, not what each shares with three of them.

**2 px coloured icon-border at picker scale; same convention
extends to the stub.** Each picker tile's 44 px icon sits
inside a 2 px-bordered rounded square; border colour is the
matching `--color-holding-{type}` (limestone / auburn / iron /
brass). The icon itself carries its own internal colours from
`brand/identity/`. The border makes the type readable at a
glance even before the user reads the name. The coming-soon
stub uses the same border convention at 96 px scale.

**Coming-soon stub treatment — visible-with-stub for all four
tiles in this iteration.** All four tile taps route to the
same parameterized stub (icon + name change per type). Earlier
plan had a unique Account-only stub with the other three tiles
leading to their wizards directly. Once the iteration was
split (wizards to their own follow-on iterations), the stub
treatment generalised to all four — keeps the picker visibly
honest about what's coming across the board, avoids the "why
is Account special?" question, and the parameterized stub is
one mockup instead of three placeholders.

**Backend ships before per-type frontend wizards.** The
descriptor-validate endpoint and the three Holding-create
endpoints (purse / strongbox / vault) ship in this scaffolding
iteration alongside the picker + stub frontend. Without the
wizards, Holdings can be created via Swagger UI for testing
the populated home rendering. This decouples backend
correctness testing from wizard UX work, and means each
wizard's coding session focuses purely on the per-type UI
rather than re-discovering backend shapes.

---

## Add Holding — Purse wizard

Promoted from `future_iterations.md` as the first per-type
wizard (canonical descriptor-wizard pattern carrying the shared
wizard shell into the codebase; Strongbox and Vault wizards
derive). Design pass closed 2026-05-13; lands after the Add
Holding scaffolding iteration closes.

The Purse wizard covers the two `purse_mode` values Purse supports
at creation per ADR-0006: `WATCH_ONLY` (the user pastes a descriptor
exported from an existing wallet) and `ON_DEVICE_TK_GENERATED` (the
user asks TallyKeep to generate a fresh seed on-device). The third
mode (`ON_DEVICE_USER_IMPORTED` — user pastes a seed/xprv from
another wallet to make their existing Purse spendable from TallyKeep)
is **not** part of this wizard — it lands as a separate Purse-
detail "upgrade to spending" feature once `purse-upgrade-path`
in `pre-implementation.md` resolves.

### Vocabulary lock

Locked during the 2026-05-13 design pass:

- **"Recovery phrase"** is the user-facing term for the 12-word
  BIP39 mnemonic. Matches Trezor / Ledger conventions. Used in
  screen copy, button labels, ARIA labels.
- **"Keys"** is the user-facing abstract term for spending
  capability. Used when the location of the signing material is
  what matters ("on this device", "TallyKeep holds the keys",
  "import the keys from another wallet").
- **"Seed phrase"** retires from user-facing copy — overlapping
  vocabulary that the user shouldn't have to disambiguate.
- **"Seed"** survives only in internal contexts (CSS class
  names, technical comments, the DEV MODE banner's pre-Capacitor
  copy uses "keys" too — `seed-vault` etc. CSS classes are
  internal identifiers, not user-facing).

### Wizard shell (introduced here, reused by Strongbox and Vault)

The shared wizard-shell pattern lands with this iteration since
the Purse wizard is its first consumer. Splitting the shell into
its own iteration would have produced a no-consumer artifact —
the anti-pattern §2 of `PROCESS.md` warns against.

**Header.** 3-cell grid `[back chevron 44 px] [step counter
centered] [empty 44 px]`. The step counter renders as
"STEP 1 OF 3" in small caps (`font-size-xs`, `--color-text-muted`,
letter-spacing 0.08em). Wizard runs 3 steps: step 1 is the
entry surface (with two paths — Generate or Import), step 2 is
parse-back with the auto-name preview, step 3 is success.
Back chevron at step 1 returns to Home (picker dismissed); at
step 2 returns to step 1; step 3 (success) hides the back
chevron — only path forward is "Done".

**Sensitive-screen flag.** The shell component carries a
`sensitive-screen={boolean}` flag on each step. When true, the
Capacitor layer wires it to:

- *Android:* `FLAG_SECURE` on the activity window — prevents
  screenshots and screen recording at the OS level. Standard
  pattern across Trezor / Bitkey / BitBox apps.
- *iOS:* `UIApplication.userDidTakeScreenshotNotification` — iOS
  doesn't expose screenshot *prevention*, only post-hoc
  detection. The wizard shows a warning after the fact if the
  user took a screenshot of the recovery phrase.
- *Browser (current iteration target):* No-op. Browsers do not
  expose screenshot prevention APIs. The DEV MODE banner is
  the honest signal that the surface isn't shipped-quality
  privacy.

The Generate-path mockups
(`mobile_add_holding_purse_generate.html`,
`mobile_add_holding_purse_generate_revealed.html`) carry
`sensitive-screen={true}`.
All others carry `false`. The Capacitor-wrap iteration owns the
platform-side wiring; the current iteration ships the component
API and the no-op browser implementation.

**Body.** Per-step content scrolls inside the body region.
Padding `var(--space-5) var(--space-4)` by convention.

**Footer.** Pinned to the bottom of the screen. Contains an
error region (rendered only when an error is active — see
*Error states* below) and a full-width primary CTA. The CTA
label is step-specific: "Continue" (step 1 Import path; step 1
Generate alt path) → "Looks right" (step 2) → "Done" (step 3).
The CTA is disabled when the step has invalid input (empty
textarea at step 1 Import); enabled in step 1 Generate
(regardless of reveal) and step 2 (post-parse) and step 3.

**Bottom nav is hidden during the wizard.** Banking convention
for focused multi-step flows (Wise add-recipient, Revolut
add-account, N26 add-payee). The wizard owns the screen; nav
distractions return when the user lands back on Home via the
step-3 "Done" CTA.

### Screens

Mode 1 (watch-only / imported) flow path: Input → Parse-back →
Success (imported).

Mode 3 (TallyKeep-generated) flow path: Generate (pre-reveal +
revealed) → Parse-back → Success (generated). Same step counter
on both modes (3 steps each); step 1 has two distinct surfaces
the user navigates between via the Generate accent card.

**Step 1 entry — `mobile_add_holding_purse_input.html`.** The
two-paths-from-the-top layout: a verdigris-tinted Generate
accent card at the top (sparkle icon + "Let TallyKeep generate
a fresh Purse" + sub-line "Privately and securely stored on
this device" + chevron), an "— or —" separator, then an
**Import from another wallet** labelled section grouping the
source dropdown + wallet-tips hint banner + descriptor textarea.
Source dropdown values (alphabetical): BlueWallet · Electrum ·
Mutiny · Nunchuk · Phoenix · Sparrow · Specter · Other · Don't
specify. List is broad on purpose — provenance is a bookkeeping
label, not a capability filter. Tapping a source surfaces a
wallet-specific hint banner inline; the same source pick
populates the auto-name on step 2. The "Paste" button inside
the textarea's top-right consumes `NativeBridge.clipboard.
paste()`. Primary CTA "Continue" disabled until textarea
non-empty.

The two-paths layout puts Generate at the top because it's a
self-contained one-tap action; Import below is a multi-field
form. Visual hierarchy doesn't map to brand priority (import is
still the assumed default for most users) — it maps to UI
coherence (Generate stands alone; source + descriptor belong
together).

**Step 1 error states.**

- `mobile_add_holding_purse_input_error_inline.html` — inline
  error pattern. Used for single-address rejection, unparseable
  text, duplicate-descriptor (the duplicate case adds a
  secondary "Open it instead" CTA in the error region linking
  to the existing Holding). Error region in the footer above
  the CTA, danger palette, textarea border tinted danger.
- `mobile_add_holding_purse_input_error_redirect.html` —
  redirect error pattern (multisig rejection). Warning palette
  (not danger — input is structurally valid, just belongs in
  Vault). Error block carries a "Set up as Vault" secondary
  CTA that routes the user out of the wizard back to the
  picker, then into the Vault wizard. Primary "Continue" stays
  present but disabled. Pattern locks for sibling wizards'
  cross-flow rejections (Vault rejecting single-key, etc.).

**Step 1 Generate alt path.** Reached via the Generate accent
card on the input screen.

- `mobile_add_holding_purse_generate.html` — pre-reveal state.
  A 12-word recovery phrase has been generated client-side and
  stored in secure storage (Capacitor: Keychain/Keystore;
  browser dev-mode: localStorage stub with the DEV MODE banner
  visible). The words are NOT shown by default — a centered
  accent button "Reveal my recovery phrase" gates the visual
  exposure. Privacy-first reveal pattern (Trezor Suite,
  Coldcard, BitBox, 1Password secret reveal). Below the reveal
  area, a loss-of-funds warning paragraph is visible regardless
  of reveal state (the recovery phrase exists either way — the
  warning shouldn't be conditional on the user looking). A
  later-note points the user to where they can return to the
  view: "You can also reveal them later from Holdings → Purse
  → Information" — forward-reference to the Purse-detail
  iteration's Information section.
  Continue CTA is **always enabled** in this state. Reveal is
  optional; the user can write the words down later from Purse
  Detail. No backup-acknowledgement checkbox — per the leading
  direction in `pre-implementation.md` `seed-backup-disclosure`,
  the persistent-warning model lives on Home in the
  security-health system (private-ship gate iteration), not as
  a hard gate at seed-generation time.
  No "Copy" button. Clipboard is a known seed-leak vector
  (Windows Clipboard History, Apple Universal Clipboard,
  Microsoft Cloud Clipboard, Gboard suggestions all persist or
  sync clipboard content past the user's awareness). The user
  can manually select text if they insist; we do not provide
  the affordance.
  Back chevron returns to the Import view at step 1 (not Home);
  the user can switch back to descriptor paste from there.
- `mobile_add_holding_purse_generate_revealed.html` — post-
  reveal state. Same shell. The 12 words render in a 3×4
  numbered grid (numbered so the user can write in order). A
  "Hide" affordance above the grid lets the user re-obscure
  without leaving the screen (useful if someone walks up).
  Same loss-of-funds warning and same later-note as pre-reveal.

**Step 2 — `mobile_add_holding_purse_parseback.html`.** Trust
handoff moment: TallyKeep shows what it parsed (or what it
generated) so the user verifies. The screen lands with the
**auto-name preview at the top**, directly under the heading:
"Will be named '{auto-name}' [Rename]" — the name-preview row
carries the 4 px brass left stripe (`--color-holding-purse`)
that the picker and populated-home rows use. Tap Rename to
edit inline.

Auto-name derivation:

- Mode 1 + source picked: "{Source} Purse" (e.g. "Phoenix
  Purse", "BlueWallet Purse"). 90% of users accept — most
  users have one wallet per source.
- Mode 1 + source = "Don't specify": script-type fallback —
  "Native SegWit Purse" / "Taproot Purse" / etc.
- Mode 3 (generated): "TallyKeep Purse" — parallel construction
  to "Phoenix Purse" / "BlueWallet Purse". Increments if a
  TallyKeep Purse already exists ("TallyKeep Purse 2").

Below the name-preview: the parse-card (script type, derivation
path, master-key summary truncated) and the addresses-card
(first three derived addresses with tap-to-copy). The parse-
card no longer carries a left stripe (would compete with the
name-preview's stripe). CTA label "Looks right" — names the
verification action.

Generated variant (mode 3) reuses the component with heading
copy adapted to "Here's what we generated for you" and a small
"Generated by TallyKeep · keys on this device" badge.

**Step 3 success.**

- `mobile_add_holding_purse_success_imported.html` — watch-only
  variant. Confirmation-honesty (gauntlet 4): the screen
  acknowledges Holding *registration* only, not balance load.
  Green success indicator, heading "Purse added", sub-copy
  about the chain scan, spinner-row "Scanning… · balance will
  appear on Home shortly". CTA: "Done". Returns to Home where
  the new row appears with the populated-home "Scanning…"
  status indicator; row updates to show balance when scan
  completes. No auto-redirect.
- `mobile_add_holding_purse_success_generated.html` — generated
  variant. Fresh wallet has zero history — nothing to scan that
  would reveal funds. Honest framing: "Purse ready" + "no funds
  yet" pill. A disabled "Show a receive address" affordance
  hints at the next iteration (Receive). CTA: "Done".

### Reconcilability gauntlet answers

1. **Trust boundary.** Phone screen (UI). The descriptor textarea
   and the name (auto-derived, optionally edited inline on
   step 2) are local UI state until step 2's "Looks right" tap.
   Backend interactions at:
   - Step 1 Import path *Continue*: `POST /api/v1/descriptors/
     validate` to parse the descriptor and detect single-address
     / multisig / unparseable cases. Pure parser — no state
     mutation.
   - Step 2 *Looks right*: `POST /api/v1/holdings/purse` to
     create the Holding (with the auto-derived or user-renamed
     name) and kick off the chain-scan job.
   - Mode 3 (generated): seed generation happens **on device**
     (BIP39 mnemonic), then the derived descriptor is sent to
     the backend. The seed never crosses to the backend.
   The DEV MODE banner makes browser-build localStorage storage
   visible until Capacitor secure storage replaces the stub
   (`browser-pwa-auth-model` and the Capacitor-wrap iteration).

2. **Keys and secrets.** Mode 1: **none** — the user pastes a
   public descriptor or xpub. No spending material crosses any
   boundary. Mode 3: a fresh BIP39 mnemonic is generated and
   stored in the device's secure storage (Capacitor: Keychain
   / Keystore; browser dev-mode: localStorage with the DEV MODE
   banner). The seed is **never** sent to the backend; only the
   derived descriptor is registered. Future *upgrade-path*
   feature (Purse-detail) will introduce a third surface where
   the user pastes a seed phrase from another wallet — that
   surface inherits this same boundary discipline. Resolution
   of the security-health surface for backup acknowledgement
   stays open in `pre-implementation.md` under
   `seed-backup-disclosure`.

3. **Self-hosted vs hosted.** Identical phone-side flow on both
   deployment models. The Holding-create and descriptor-validate
   endpoints behave identically. The hosted-tier privacy
   boundary (TallyKeep operators can see descriptors at rest)
   is disclosed at hosted-tier onboarding, not at Add Purse
   time — that's a one-time boundary acknowledgement, not a
   per-Holding one.

4. **Confirmation honesty.** Three deliberate honesty beats in
   the flow:
   - Step 2 *parse-back* frames itself as "Here's what **we
     read**" and invites the user to verify against their other
     wallet. The user does the verification; TallyKeep shows
     its work.
   - Step 3 *success (imported)* acknowledges Holding
     registration, **not** balance load. The "Scanning…" hint
     and the populated-home row treatment carry the truth across
     the boundary — the Holding exists, the chain scan is still
     running.
   - Step 3 *success (generated)* names the empty state honestly
     — "no funds yet · fresh wallet". No "balance loaded" copy;
     the user did not expect a balance and TallyKeep does not
     fake one.
   Plus the privacy-first reveal on step 1 Generate alt-path:
   recovery phrase isn't shown until the user explicitly taps
   to reveal, and the loss-of-funds warning + "you can reveal
   later from Holdings → Purse → Information" are visible in
   both pre-reveal and revealed states.
   No "Sent ✓" / "Confirmed" semantics in this wizard — those
   come with Send / Receive iterations.

5. **Browser-only fallback.** Watch-only mode is fully browser-
   compatible — no keys, no secure storage, all backend
   endpoints reachable via fetch. Generated mode in browser
   relies on the localStorage soft-fallback per ADR-0007 with
   the DEV MODE banner making the fallback visible. Capacitor
   builds replace the fallback with platform Keychain/Keystore
   and the banner disappears. The generate path remains
   reachable in both builds — gauntlet #5 forbids silent
   capability degradation, not feature gating. (The pre-
   implementation item `browser-pwa-auth-model` covers the
   long-term browser-PWA authentication model; the dev-mode
   localStorage stub is a personal-shipping crutch, not the
   shipped behaviour.)

6. **Open-source and reproducibility.** No closed-source
   dependency. Descriptor parsing (BIP 380 + miniscript) lives
   in