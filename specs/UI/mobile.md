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

The original module 11 (11_ux_flows.md) carried screen-by-screen
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
- Brand identity, copy voice — see `brand/README.md` (mark,
  wordmark, palette locked; voice/about draft; finalized at the
  public-ship event per ADR-0003).

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
  ships — see `backlog/dynamic-brand-mark-on-first-touch-surfaces.md`.
  *Status: validated (Rémy greenlight 2026-05-10).*
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
the hosted-tier iteration promotes from
`backlog/hosted-tier-infrastructure.md`:

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
`backlog/hosted-tier-infrastructure.md`, so it is not drafted
for the current iteration. The
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
   access adds TLS per
   `backlog/remote-access-for-self-hosters.md`).
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
pattern captured in
`backlog/tap-to-see-under-the-hood-ui-spine-pattern.md`. The Unicode
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
   `backlog/hosted-tier-infrastructure.md`).
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
   reproducible-build pipeline in
   `backlog/ship-gate-meta-iteration-the-public-ship-event.md`
   to make the assertion provable.

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
`backlog/security-health-system.md`, milestone pre-shipping). For
the current Onboarding iteration's empty
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
as a post-public-ship future iteration (per
`backlog/multi-server-per-single-client.md`) and is not blocking
for private-ship or public-ship.

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
lock-doc bump (per `brand/README.md` §Status-driven discipline —
pre-public-ship lock-doc edits allowed without an ADR) updating §5
to extend the sanction.
Captured for sharpening in
`backlog/dynamic-brand-mark-on-first-touch-surfaces.md`; not
landed in this mockup because mockups are static-only per
`UI/mockups/README.md`.

---

## Add Holding

The picker entry surface plus all four per-type wizards have
shipped. Tile taps route to the live wizard for each Holding
type — Account, Purse, Strongbox, Vault — documented in their
own §Add Holding — *type* sections below. The scaffolding
iteration originally shipped a type-parameterized coming-soon
stub as the routing target for every tile; each wizard
iteration since (Purse → Strongbox → Vault → Account) replaced
the corresponding `/holding/new/<type>` route with its real
wizard surface. The stub mockup itself is preserved as the
canonical visual template for future coming-soon stubs (see
`backlog/deposit-send-to-account-flow.md`) and is no longer
reached from this picker.

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

- `mobile_add_holding_coming_soon.html` — **pattern reference,
  no longer reached from the Add Holding picker.** Originally
  shipped as the type-parameterized routing target for all four
  tile taps during the scaffolding iteration, replaced by each
  per-type wizard as they shipped (Purse → Strongbox → Vault →
  Account). Kept on disk as the canonical visual template for
  future coming-soon stubs (cf.
  `backlog/deposit-send-to-account-flow.md`). Anatomy: app bar
  with back chevron +
  screen title ("Add a Purse" / "Add a Strongbox" / etc.),
  centred body with a 96 px Holding icon (same per-type
  bordered framing as the picker row, sized up), heading
  *"Coming in an upcoming iteration"*, paragraph copy
  acknowledging API workaround for dev-phase users, "Return to
  Home" secondary CTA. Bottom nav unchanged. *Status: validated
  (Rémy greenlight 2026-05-13); role demoted to template
  2026-05-17 as the last wizard shipped.*

Promotion order followed the iteration roadmap (now in
`backlog/README.md`): **Purse first**
(canonical descriptor wizard, also carried the shared wizard
shell into the codebase since it was the first consumer), then
Strongbox (copy + framing variant on Purse), then Vault
(multisig-only + framing pre-card), then Account (different
surface — ccxt provider integration, no descriptor parser).

### Reconcilability gauntlet answers

Gauntlet answers below cover the picker surface only. Per-wizard
gauntlet answers — descriptor handling (Purse / Strongbox /
Vault), API credentials (Account), and Capacitor capability
gates — live with each wizard's section below. The coming-soon
stub's gauntlet was answered for the scaffolding iteration and
is preserved in `shipped.md`; the screen is no longer a live
surface so no current gauntlet attaches.

1. **Trust boundary.** Phone (UI only). The picker is local
   sheet state — no backend call when opening or dismissing.
   Tile taps route into the per-type wizard, which carries its
   own trust-boundary answer.

2. **Keys and secrets.** None on the picker surface. No
   descriptor input, no API keys, no passphrases.

3. **Self-hosted vs hosted.** Identical surface. The picker
   renders identically regardless of the connection target.

4. **Confirmation honesty.** Picker doesn't promise anything —
   it presents the four type choices. No "added!" state shown
   before anything is added.

5. **Browser-only fallback.** Per ADR-0007. The picker is
   fully browser-compatible. No Capacitor-only capability is
   exercised here — no QR scan, no biometric, no secure-storage
   write. Capability gates land with the wizards that need them.

6. **Open-source and reproducibility.** No closed-source
   dependency. Inline SVG icons from `brand/identity/`,
   token-driven styling (no raw hex in component CSS), no
   third-party JS libraries on the picker surface.

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

**Coming-soon stub treatment — historical, all four tiles
routed to one parameterized stub during the scaffolding
iteration.** All four tile taps once routed to the same
parameterized stub (icon + name change per type). Earlier plan
had a unique Account-only stub with the other three tiles
leading to their wizards directly. Once the iteration was
split (wizards to their own follow-on iterations), the stub
treatment generalised to all four — kept the picker visibly
honest about what was coming across the board, avoided the
"why is Account special?" question, and the parameterized stub
was one mockup instead of three placeholders. Resolved as each
wizard shipped and took over its `/holding/new/<type>` route.

**Backend shipped before per-type frontend wizards.** The
descriptor-validate endpoint and the three Holding-create
endpoints (purse / strongbox / vault) shipped in the
scaffolding iteration alongside the picker + stub frontend.
Without the wizards yet, Holdings were created via Swagger UI
for testing the populated-home rendering. This decoupled
backend correctness testing from wizard UX work, and meant
each wizard's coding session focused purely on the per-type UI
rather than re-discovering backend shapes.

---

## Add Holding — Purse wizard

Promoted from the backlog as the first per-type wizard
(canonical descriptor-wizard pattern carrying the shared
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
the role-mixing / scope-creep anti-pattern `PROCESS.md` §2 warns
against.

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
   in BDK's miniscript module (Rust, MIT-licensed). The
   `@scure/bip39` and `@scure/bip32` JS libraries are MIT,
   in-tree-buildable, no closed deps.

<!-- 2026-05-14 spec-cleanup note: section 6 above ("Open-source and
reproducibility") was truncated mid-sentence on disk by a tool-side
write bug during this session. The closure is a minimal-fidelity
reconstruction from project context (BDK, scure libs already referenced
elsewhere). Restore from git history if a more accurate version is
needed. -->

---

## Add Holding — Strongbox wizard

Second per-type wizard. Reuses the wizard shell introduced by the
Purse wizard (header, step counter, body, footer, sensitive-screen
flag, hidden bottom-nav). Design pass closed 2026-05-14 (all 7
mockups validated); promoted to `next_iteration.md` as the active
coding iteration.

The Strongbox wizard covers a single creation path: the user
pastes / scans / uploads a watch-only descriptor (or bare xpub)
exported from a hardware wallet, and TallyKeep registers a
Strongbox-typed Holding against it. No generate path — Strongbox
spending keys live on the user's hardware wallet, never on any
TallyKeep surface (per ADR-0009 key-custody zones). The
`signing_device_label` free-form note ("Coldcard Mk4 in safe")
is set on the Strongbox detail page post-creation, not in the
wizard — same shape as renaming a Purse later. Holding the
wizard at three steps preserves parity with the Purse pattern.

### Vocabulary lock

Inherited from the Purse-wizard vocabulary lock (2026-05-13):
"keys" stays the user-facing abstract term for spending
capability ("the hardware wallet keeps the spending key"). One
Strongbox-specific addition:

- **"Hardware wallet"** — user-facing term for the external
  signing device (Coldcard, Trezor, Ledger, Jade, BitBox02,
  airgapped laptop running Sparrow / Electrum, Specter DIY).
  Used in the vendor dropdown label and step copy. The
  domain-model term `signing_device_label` is internal only.
- **"Descriptor"** — singular field label on step 1, dropping
  the Purse wizard's "Descriptor or xpub". Hardware wallets
  export output descriptors more commonly than bare xpubs; the
  shorter label is honest about the typical input shape
  without rejecting bare xpubs (the backend parser accepts
  both, same as Purse).

### Wizard shape (3 steps, parity with Purse)

Step counter "STEP 1 OF 3 / 2 OF 3 / 3 OF 3". Back chevron at
step 1 returns to Home (picker dismissed); at step 2 returns to
step 1; at step 3 (success) hidden — only path forward is
"Done". Bottom-nav hidden during the wizard.

**Sensitive-screen flag.** None of the Strongbox steps carry
`sensitive-screen={true}`. The descriptor is public-key data; no
recovery phrase is ever shown by this wizard (no generate path).
The wizard shell still inherits the same flag mechanism so the
Capacitor layer wiring is component-uniform with Purse — it
just always passes `false`.

### Screens

**Step 1 — `mobile_add_holding_strongbox_input.html`.** Heading
"Add a Strongbox", no Generate accent card (the Purse
two-paths-from-the-top layout collapses to one path). Vendor
dropdown directly under the heading, optional with "Don't
specify" as the production default (rendered "Coldcard" in this
mockup for narrative realism). Vendor list (alphabetical, matching
the Purse dropdown's discipline): Airgapped laptop · BitBox02 ·
Coldcard · Jade · Ledger · Sparrow (as signer) · Specter DIY ·
Trezor · Other · Don't specify. The list is broad on purpose —
provenance is a bookkeeping label, not a capability filter. The
backend parser doesn't care which vendor produced the descriptor;
this metadata just drives the auto-name on step 2 and the
vendor-specific export-instruction hint banner below.

Picking a vendor surfaces a wallet-specific hint banner inline,
same content shape as the Purse Phoenix hint — title + body with
step-by-step export instructions and any vendor-specific gotchas.
Coldcard hint is locked in the input mockup; remaining vendor
hints land in the production component (`Advanced/Tools → Export
Wallet → Generic JSON` for Coldcard; `Settings → Wallet info →
Show xpub` for Trezor Suite; analogous paths for Ledger Live,
Jade, BitBox02, etc.). "Other…" surfaces a generic prompt rather
than a per-device walkthrough.

Below the vendor block: descriptor textarea with three input
affordances grouped under it.

- **Paste button** inside the textarea's top-right consumes
  `NativeBridge.clipboard.paste()` (same hook as Purse).
- **Scan QR button** opens the camera via Capacitor (`Native​
  Bridge.camera.scanQR()`). Browser build **hides** this button
  (absence-of-affordance per ADR-0007 / gauntlet 5). The mockup
  renders the Capacitor target — both buttons visible.
- **Upload file button** opens a file picker for `.txt`, `.json`,
  or `.psbt`-adjacent descriptor exports. Always available in both
  builds — file system access is the common-denominator import
  channel for Coldcard SD card, Sparrow exports, Specter, and
  airgapped-laptop flows.

QR earns its place in Strongbox because hardware wallets *display*
QRs precisely because they're offline (Coldcard, Jade, BitBox02,
Specter DIY all export descriptors via QR). The Purse wizard
doesn't surface QR because Purse descriptors come from hot wallets
that live on the same phone (Phoenix, BlueWallet, Mutiny, Sparrow
hot mode) and expose a "Copy descriptor" button instead. The
asymmetry is honest, not arbitrary.

Primary CTA "Continue" disabled until textarea non-empty.

**Step 1 footer-banner states.** Three distinct shapes — locked
across the wizard for future per-type sibling reuse:

- `mobile_add_holding_strongbox_input_error_inline.html` — **inline
  error** pattern. Triggers on single-address rejection ("That's a
  single Bitcoin address. TallyKeep tracks wallets, not isolated
  addresses — export the wallet descriptor or xpub from your
  hardware wallet and paste that instead.") and on unparseable
  text (generic shape). Danger palette, textarea border tinted
  danger, vendor hint banner hidden (error region carries the
  informational role). Primary CTA **disabled** (blocking —
  structural input invalid). Duplicate-descriptor case adds a
  secondary "Open it instead" CTA in the error region linking to
  the existing Holding (per the Purse pattern; not rendered as a
  separate mockup in this iteration but the component carries
  the affordance).
- `mobile_add_holding_strongbox_input_error_redirect.html` —
  **redirect error** pattern (multisig rejection). Warning
  palette (not danger — input is structurally valid, just belongs
  in Vault). Error block carries a "Set up as Vault" secondary
  CTA routing the user out of this wizard back to the picker,
  then into the Vault wizard. Primary "Continue" stays present
  but **disabled** (blocking — input belongs in a different
  wizard). Pattern locked across sibling wizards (Vault rejects
  single-key with the inverse redirect; Account doesn't apply).
- `mobile_add_holding_strongbox_input_advisory_no_metadata.html` —
  **advisory** pattern (new shape, locked here). Triggers when
  the backend descriptor-validate parses the input successfully
  but the descriptor lacks key-origin brackets — typical for bare
  zpubs from Trezor Suite "Show xpub", Ledger Live, Phoenix
  "Wallet final", BlueWallet xpub view. Warning palette, smaller
  / lighter visual treatment than the redirect-error band (xs
  font, tighter padding, single compact paragraph, no secondary
  CTA inside). Primary CTA **enabled** — non-blocking,
  informational. Copy: *"**Missing derivation metadata.** Your
  hardware wallet may refuse to sign transactions with this
  descriptor. Receiving funds will work as expected. Re-export
  your descriptor to enable signing, or continue as is."* Voice is declarative, consequence-first
  (the user-visible impact — hardware-wallet refusal — comes
  before the technical cause), banking-grade per
  `brand/tallykeep_about_v1_draft.md` reference points
  (Revolut / Wise / Qonto / N26). Vendor hint banner stays
  visible alongside (hint = how to export from this wallet,
  advisory = what we noticed about the paste — two different
  conceptual roles).

  No forward-reference to any specific resolution surface in the
  banner. The user gets two clear actions ("re-export" /
  "continue as is") and the in-wizard signal continues on step 2
  via the tinted Derivation row. Where the warning persists
  post-Holding-create and how the user later resolves it is a
  design question carried by the security-health iteration in
  `backlog/security-health-system.md` — flagged there as needing
  rework before the user-facing surface lands, since "Security health"
  as a product-design concept users encounter directly is not
  yet committed (Rémy 2026-05-14).

  Why this is Strongbox-only and not Purse: TallyKeep coordinates
  PSBT signing for Strongbox (per `holdings/03_strongbox.md`
  §"Send flow"), so missing `bip32_derivation` data in the PSBT
  causes interop friction at spend time. TallyKeep never signs
  for a watch-only Purse — the user spends from their hot wallet
  directly — so the same descriptor shape has zero spending-time
  consequences on the Purse side.

  Why the advisory lives at step 1 and not step 2: surfacing
  this on parse-back after the user clicks Continue feels like a
  gotcha ("AH YOU MESSED UP" — Rémy 2026-05-14). Step 1 advisory
  lets the user re-export now if they want to spend later, or
  proceed knowing the trade-off. Step 2 then just confirms what
  TallyKeep couldn't determine (Derivation row tinted in warning
  palette — see Step 2 below) without repeating the lecture.

**Step 2 — `mobile_add_holding_strongbox_parseback.html`.** Two
variants in this iteration:

- *Default* (`mobile_add_holding_strongbox_parseback.html`) —
  descriptor carried full key-origin brackets, all parsed fields
  populated.
- *Missing signing metadata* (`mobile_add_holding_strongbox_parseback_no_metadata.html`) —
  same screen, but reached after the user continued past the
  step-1 advisory. The backend wrapped the bare xpub in the
  script-type descriptor BDK needs (`wpkh(zpub.../0/*)#checksum`)
  and stored the master-fingerprint / derivation-path columns
  NULL. **No warning banner on this step** — the user was already
  informed at step 1; repeating the lecture here would be a
  gotcha. The "Derivation" row in the parse-card alone renders in
  the warning palette: yellow-tinted row background bleeding to
  the card edges, "not provided" in warning text colour, small
  inline info icon for users who want to re-read the why. Other
  parse-card rows stay neutral. CTA "Looks right" enabled — the
  user proceeds; the security-health item gets created server-
  side on Holding-create so the same warning surfaces on Home
  under the security-health heading with a "Fix this" affordance
  (remediation sub-flow specified in
  `backlog/security-health-system.md`).

Both variants share the same shape. The screen lands with the
**auto-name preview at the top**, directly under the heading:
"Will be named '{auto-name}' [Rename]" — the name-preview row
carries the 4 px iron left stripe (`--color-holding-strongbox`).
Tap Rename to edit inline.

Auto-name derivation:

- Vendor picked: "{Vendor} Strongbox" (e.g. "Coldcard Strongbox",
  "Trezor Strongbox", "Ledger Strongbox", "Sparrow Strongbox").
  Mirrors Purse "{Source} Purse" construction. Most users will
  accept the derived name without renaming.
- Vendor = "Don't specify": script-type fallback — "Native SegWit
  Strongbox" / "Taproot Strongbox" / etc. Same fallback rule as
  the Purse wizard's "Don't specify" path.
- Multiple Strongboxes with same vendor: increment at backend
  create time ("Coldcard Strongbox 2"), same convention as
  "TallyKeep Purse 2".

Verification copy emphasises hardware-wallet verification
specifically: "Open your hardware wallet (or Sparrow / Specter /
its companion app) and confirm these match the wallet's first
three receive addresses." This matches the receive-flow
verify-on-device discipline in `holdings/03_strongbox.md` —
TallyKeep showing addresses on the phone screen isn't proof on
its own; the hardware wallet's own display is the reference.

Below the name-preview: the parse-card (script type, derivation
path, master-key summary truncated) and the addresses-card
(first three derived addresses with tap-to-copy). Same components
as Purse parse-back. CTA label "Looks right".

**Step 3 — `mobile_add_holding_strongbox_success.html`.** Same
confirmation-honesty shape (gauntlet 4) as Purse imported success:
the screen acknowledges Holding *registration* only, not balance
load. Iron stripe on the scanning row, heading "Strongbox added",
sub-copy about the chain scan, spinner-row "Scanning… · balance
will appear on Home shortly". CTA: "Done" — returns to Home where
the new row appears with the populated-home "Scanning…" status
indicator; row updates to show balance when scan completes. No
auto-redirect.

No "signing happens on your hardware wallet" disclosure on
success. Send / Receive iterations ship separately; their copy
will handle verify-on-device and PSBT-roundtrip discipline.
Saying it on the success screen would invite users to look for a
Send button that isn't built yet.

### Reconcilability gauntlet answers

1. **Trust boundary.** Phone screen (UI). The descriptor textarea
   and the name (auto-derived, optionally edited inline on
   step 2) are local UI state until step 2's "Looks right" tap.
   Backend interactions at:
   - Step 1 *Continue*: `POST /api/v1/descriptors/validate` to
     parse the descriptor and detect single-address / multisig /
     unparseable cases. Pure parser — no state mutation. Same
     endpoint as Purse.
   - Step 2 *Looks right*: `POST /api/v1/holdings/strongbox` to
     create the Holding (with the auto-derived or user-renamed
     name and vendor metadata if picked) and kick off the
     chain-scan job.
   QR scan and file upload are device-side reads — the camera /
   file picker plugin reads the descriptor text into the
   textarea, then step 1 proceeds normally. No additional
   network surface beyond the standard descriptor-validate path.

2. **Keys and secrets.** **None on any wizard surface.** Strongbox
   keys live on the user's hardware wallet, in the user's
   custody zone (ADR-0009). The wizard accepts public-key data
   only — output descriptors, xpubs. The descriptor itself is
   not a secret; it's the public projection of the wallet's
   address space. The spending keys never touch any TallyKeep
   surface (backend, Capacitor, browser). No biometric prompt,
   no secure-storage write, no localStorage stub. This is the
   cleanest wizard in the four-type set from a custody-surface
   perspective.

3. **Self-hosted vs hosted.** Identical phone-side flow. The
   Holding-create and descriptor-validate endpoints behave
   identically per `01_architecture.md`. The hosted-tier
   privacy boundary (TallyKeep operators can read descriptors
   at rest) is disclosed at hosted-tier onboarding, not at Add
   Strongbox time. Same boundary as Purse watch-only.

4. **Confirmation honesty.** Three deliberate honesty beats:
   - Step 2 *parse-back* frames itself as "Here's what **we
     read**" and invites the user to verify against the hardware
     wallet's own display (not just another wallet app). The
     user does the verification; TallyKeep shows its work.
   - Step 3 *success* acknowledges Holding registration, **not**
     balance load. The "Scanning…" hint and the populated-home
     row treatment carry the truth across the boundary — the
     Holding exists, the chain scan is still running.
   - Success copy does **not** preview Send capability. Sending
     from a Strongbox requires PSBT roundtrip with the hardware
     wallet, which ships in a later iteration. No "you can spend
     from this Strongbox now" implied; no Send button stubbed in.
   No "Sent ✓" / "Confirmed" semantics in this wizard — those
   come with the Strongbox-Send iteration.

5. **Browser-only fallback.** Strongbox is fully browser-
   compatible *except* for QR scan (Capacitor camera plugin
   only). Browser build hides the Scan QR button per
   absence-of-affordance — no banner, no honest gate, just the
   button isn't there. Paste and Upload-file work in both
   builds. The honest browser-build path: user copy-pastes the
   descriptor from their HW companion app (Trezor Suite, Ledger
   Live, Sparrow, Specter), or uploads the descriptor file. The
   shipped behaviour matches the gauntlet-5 discipline —
   capability degradation is *visible* (button absent), not
   silent (button shown, click does nothing).

6. **Open-source and reproducibility.** No closed-source
   dependency. Descriptor parsing reuses the Purse wizard's BDK
   miniscript path. Camera-plugin and file-picker plugins are
   Capacitor community plugins (MIT-licensed) — in-tree
   buildable, no closed deps on the Strongbox path. The QR
   decoder library used by the camera plugin will be confirmed
   MIT or Apache-2 at Capacitor-wrap iteration time; the
   Strongbox wizard's browser-build path doesn't depend on it.

### Notes

**Three steps, not four.** The future-iterations sketch
captured 2026-05 proposed four steps with a dedicated "Label"
step. That sketch predated the Purse-wizard convergence to three
steps (2026-05-13), where the dedicated label step retired in
favour of the auto-name preview on parse-back. Strongbox follows
the locked Purse pattern: name preview on step 2, inline rename,
no separate label step. The `signing_device_label` free-form
note ("in safe at home") is set on Strongbox detail post-
creation, same way a Purse gets renamed there.

**Vendor dropdown discipline.** Same shape as the Purse source
dropdown: optional, alphabetical, broad list, "Don't specify"
default in production, "Other…" tail for the long-tail. Vendor
drives the auto-name and the per-vendor export-instruction hint
banner. It does **not** filter the parser, gate any capability,
or alter the backend descriptor-validate path. The vendor is a
bookkeeping label — same vocabulary the user uses when
describing their setup ("my Coldcard"), surfaced consistently in
the Holdings list, the Strongbox detail page, and any future
declared-vs-observable warning copy ("your declared 'Coldcard'
Strongbox has had …").

**QR scan justified for Strongbox, not retroactive for Purse.**
QR earns its place in Strongbox because hardware wallets export
descriptors via QR (Coldcard, Jade, BitBox02, Specter DIY all do
this natively — it's the canonical airgapped transport). Purse
descriptors come from hot wallets on the same phone where
clipboard / Copy-descriptor is the natural channel. The
asymmetry is intentional. Adding QR to the Purse wizard later
remains an option, but it doesn't earn its place there in the
current scope.

**No `sensitive-screen={true}` on any step.** The shell flag
exists for screens where a recovery phrase is exposed (Purse
generate path). Strongbox never exposes recovery material — the
keys live on the hardware wallet, on the user's side of the
trust boundary. Inheriting the flag mechanism keeps component
uniformity with Purse; the value is always `false`.

**Auto-rename is non-mutable post-creation? No — same as Purse.**
The user can rename the Strongbox from its detail page later, no
constraint. The auto-name is a default, not a lock. Vendor
metadata (if picked) persists on the Holding record independently
of the name; if the user renames "Coldcard Strongbox" to "Office
safe", the vendor metadata stays `coldcard` for downstream uses
(security-health copy, declared-vs-observable framing).

## Add Holding — Vault wizard

Third per-type wizard. Reuses the same wizard shell (header,
step counter, body, footer, hidden bottom-nav) introduced by the
Purse wizard and refined for Strongbox. Drawn under ADR-0010 β
2026-05-15; pending Rémy greenlight to flip mockups from review
to validated.

The v1 Vault wizard accepts both Vault shapes per ADR-0010:
single-sig + script-enforced timelock, and multisig (with or
without an additional timelock). The user pastes / scans /
uploads the descriptor; the parser routes by shape; the Vault
is registered. Pure-single-key-without-timelock redirects to
Strongbox; multi-path miniscript / exotic constructs surface an
unsupported-form error.

**Vault Send is deferred for v1** regardless of shape, per
ADR-0010; the Vault detail page surfaces balance + activity +
unlock-countdown but Send is greyed out. The genuinely hard
surface (multi-signer PSBT coordination, cosigner-status UI,
partial-signature collection, chain-side timelock-check display)
is folded into the dedicated Vault-Send iteration where all
shapes are designed together.

The Vault wizard is the first wizard in TallyKeep whose accept
set covers multiple descriptor shapes. The branching happens at
parse time — the user enters one textarea, and the parser routes
to one of five parseback variants (single-sig + CLTV, single-sig
+ CSV, pure multisig, multisig + CLTV, multisig + CSV) or one of
two error variants (single-key-no-timelock → Strongbox;
unsupported form → contact us).

### Vocabulary lock

Inherited from the Purse / Strongbox wizards' "keys" framing.
Vault-specific additions:

- **"Vault"** — the friction-bearing Holding type. Per
  ADR-0010 β, a Vault is a wallet whose spending requires
  intentional friction: a script-enforced timelock, multiple
  keys, or both. User-facing copy emphasises the
  friction-as-defining-property (e.g. "wallet whose spending is
  locked behind friction"), not the multisig-by-definition
  framing of earlier drafts.
- **"Timelock"** — surfaced in the parseback's row label as
  either "Unlocks on" (CLTV / absolute) or "Each deposit locks
  for" (CSV / relative). The shape-specific labels are honest
  about the difference; we don't collapse them into a single
  generic "Timelock" row, because the per-UTXO vs wallet-wide
  unlock semantics matter and surface differently on Vault
  detail later.
- **"Coordinator" / "wallet you exported the descriptor from"**
  — the source-of-truth wallet the user verifies against during
  parseback. Liana / Bitcoin Core / Sparrow / Specter / a
  miniscript-capable hardware wallet's companion app. The
  parseback copy is intentionally generic ("the wallet you
  exported this descriptor from") because the v1 source space
  is wider than Strongbox's hardware-wallet-only assumption.

### Wizard shape (3 steps, parity with Strongbox / Purse)

Step counter "STEP 1 OF 3 / 2 OF 3 / 3 OF 3". Back chevron at
step 1 returns to Home (picker dismissed); at step 2 returns to
step 1; at step 3 (success) hidden — only path forward is
"Done". Bottom-nav hidden during the wizard.

**No vendor dropdown.** Unlike Strongbox, Vault's input screen
has no vendor pick — a Vault descriptor may come from
miniscript-coordinator software, from a hardware wallet's
multisig export, or from any combination. The vendor-as-label
bookkeeping that earns its place for Strongbox (single-vendor,
hardware-wallet-driven) doesn't earn its place for Vault.
Provenance, when relevant, surfaces post-creation on Vault
detail (cosigner annotation in the multisig case; signing key's
fingerprint in the single-sig case).

**Sensitive-screen flag.** None of the Vault steps carry
`sensitive-screen={true}`. The descriptor is public-key data; no
recovery phrase is shown by this wizard. Same shell-uniformity
posture as Strongbox.

### Screens

**Step 1 — `mobile_add_holding_vault_input.html`.** Heading
"Add a Vault", sub stating the type plainly without leaking
internal vocabulary ("A Vault is a wallet whose spending is
locked behind a script-enforced timelock, multiple keys, or
both."). **No inline help/hint banner** — earlier drafts
carried an info-tinted "Accepted descriptors" banner naming the
canonical miniscript shapes; Rémy's review (2026-05-15) flagged
that the banner was inconsistent with the Purse / Strongbox
wizards (which don't carry such banners) and that a
product-wide "tap anything for detail" pattern is the right
place for that kind of help. The banner was removed; the future
pattern is captured in
`backlog/tap-anything-for-detail-help-affordance.md`. **No third-party
product names in user copy** — the descriptor's source software
(Liana, Bitcoin Core, Sparrow, Specter, hardware-wallet
exports, etc.) varies, isn't TallyKeep's to endorse, and
shifts over time; copy refers generically to "the wallet you
exported this descriptor from." Below the heading: descriptor
textarea with placeholder showing a single-sig + CLTV example,
plus the three input affordances grouped under it.

Three input affordances:

- **Paste** (always available, primary affordance — same shape
  as Purse / Strongbox).
- **Scan QR** (Capacitor-only — hidden in browser build per
  absence-of-affordance discipline, ADR-0007). Multi-frame QR
  (BBQr / UR2) for descriptors that exceed single-frame capacity
  lands when the PSBT-by-QR roundtrip iteration ships;
  single-frame QR works for typical single-sig + timelock
  descriptors which are usually well under 1 KB.
- **Upload file** (always available — coordinators export
  `.json` / `.txt` descriptors).

Continue button disabled until a non-empty parseable descriptor
is in the textarea.

**Step 1 — error variants.** Two error variants of step 1,
selected by what the parser identifies in the pasted descriptor:

- **`mobile_add_holding_vault_input_error_redirect.html`** —
  user pasted a pure single-key descriptor with no timelock
  (`wpkh(...)`, `pkh(...)`, single-key `tr(...)`, etc.). Warning
  palette. Error title: "No timelock or multi-signature
  detected." Body: "Set this up as a Strongbox instead. If you
  meant to add a timelock, export the descriptor again with the
  lock fragment." Secondary CTA "Set up as Strongbox" routes to
  the Strongbox wizard. Mirror of the Strongbox-wizard's
  multisig-redirect pattern, reversed.
- **`mobile_add_holding_vault_input_error_inline.html`** — user
  pasted something the parser couldn't classify as a supported
  Vault shape (bare `multi(...)` without script wrapper,
  multi-path miniscript, or unparseable text). Danger palette.
  Error title: "Unsupported descriptor." (not "TallyKeep can't
  read this as a Vault" — the failure is the input, not
  TallyKeep, per Rémy's review 2026-05-15). The error region
  lists the v1 supported forms (single-sig + timelock and
  multisig variants) and points users with complex setups to a
  "contact us" path.

The earlier "multisig-deferred" error variant (drawn 2026-05-15,
archived same day) is gone — under the broader β scope multisig
descriptors are accepted in v1 onboarding, so the error has
nothing to fire on.

**Step 2 — `mobile_add_holding_vault_parseback.html` (unified).**
One mockup covers all five Vault shape variants by filling four
characteristic rows. Earlier drafts (2026-05-15) had a separate
mockup per shape combination; Rémy's review surfaced that they
were redundant — every variant filled the same row schema with
different values, and the per-shape visual distinctions weren't
load-bearing. The five drafts archived; the unified mockup
supersedes them.

Parse-card rows (always present, value-bearing):

1. **Signers required** — "1 of 1" (single-sig shapes), "2 of 3"
   / "3 of 5" / etc (multisig). The "1 of 1" value for
   single-sig keeps the row schema uniform — parseback reads the
   same way regardless of shape.
2. **Signing keys** — comma-separated fingerprint list. One
   entry for single-sig; n entries for multisig.
3. **Script type** — "Native SegWit · P2WSH",
   "Native SegWit · P2WSH miniscript", "Taproot · P2TR", etc.
4. **Timelock** — value carries the type name inline: "None",
   "CLTV — unlocks on block X (~ calendar date)" (absolute), or
   "CSV — each deposit locks for N blocks (~ duration)"
   (relative). Power user reads the script-level construct
   (CLTV / CSV); casual user reads the calendar-shaped value.

Auto-name templates (backend composes, UI renders the resulting
string):

- Single-sig + CLTV: "Vault unlocking {year}".
- Single-sig + CSV: "{duration} Vault" (1-year, 6-month,
  30-day as appropriate).
- Pure multisig: "{M}-of-{N} Vault".
- Multisig + CLTV: "{M}-of-{N} Vault unlocking {year}".
- Multisig + CSV: "{M}-of-{N} Vault · {duration} lock".

Year derived from parsed block height × ~10-min average,
rounded. Duration translated to the largest natural unit
(years ≥ 365 days, months ≥ 30 days, days otherwise). Increment
suffix (` (2)`, ` (3)`) added at backend create time when
auto-name would collide with an existing Vault.

The mockup renders the **multisig + CLTV** combination
(`2-of-3 Vault unlocking 2031`) because that case exercises
every row meaningfully (signers required > 1; signing keys
plural; script type carries "miniscript"; timelock present).
Single-sig and pure-multisig cases drop respective row values
to "1 of 1" / "None" but render the same schema.

**Per-UTXO unlock semantics (CSV case) are not surfaced at
parseback.** The "Timelock" row's "each deposit locks for"
phrasing carries the gist; the Vault detail page renders the
actual per-UTXO unlock schedule once funds arrive. Parseback's
job is "do we agree on the parameters?", not "explain the
consequences."

CTA label "Looks right" — same tonal shift as Strongbox
(confirming, not just proceeding).

CTA label "Looks right" — same tonal shift as Strongbox
(confirming, not just proceeding).

**Step 3 — `mobile_add_holding_vault_success.html`.** Centred
success indicator + heading "Vault added" + scan-row with
Vault-coloured left stripe. Same shape as Strongbox / imported
Purse success states. "Done" returns to Home; the new Vault
appears in the Holdings list with a "Scanning…" status indicator
inline until the chain scan completes. Shape-agnostic — the
same success step renders for CLTV and CSV cases alike; the
detail page handles the shape-specific UI.

### Reconcilability gauntlet answers

1. *Trust boundary:* phone screen (UI) + backend (descriptor
   parse, descriptor registration, chain scan). The hardware
   wallet / coordinator that emitted the descriptor sits outside
   TallyKeep — the user is the bridge (paste / QR / file).
   Backend stores the descriptor (public-key data plus
   miniscript fragments); spending keys never cross to backend
   per ADR-0009.
2. *Keys:* spending key lives on the user's hardware wallet (for
   the single-sig + timelock case, on one device; for the future
   multisig case, on n devices). Never on any TallyKeep surface.
   Vault detail surfaces unlock-countdown UI but doesn't touch
   keys.
3. *Self-hosted vs hosted:* identical from the phone's POV. Both
   backends register the descriptor, scan the chain, and surface
   balance + activity. Neither sees the spending key. The wizard
   does not differentiate.
4. *Confirmation honesty:* the success step uses "Vault added"
   only after the backend has confirmed Holding creation (not
   when the user taps "Looks right"). The "Scanning…" indicator
   on the scan-row honestly communicates that balance is not yet
   loaded; the home Holdings list shows the same indicator until
   the scan completes. No "Active" / "Ready" claim before the
   chain has been scanned. Vault Send is greyed out on detail
   per ADR-0010 — no pretend-to-sign affordance.
5. *Browser-only fallback:* paste, file upload, and parseback all
   work in the browser. Scan QR is Capacitor-only (camera
   plugin); hidden in browser per ADR-0007 absence-of-affordance.
   The wizard is fully functional in the browser via paste /
   file.
6. *Open-source and reproducibility:* descriptor parsing uses
   BDK's miniscript support (Rust, MIT/Apache-2.0). No
   closed-source dependency in the Vault path. No TallyKeep
   server-side secret involved in descriptor registration or
   chain scan.

### Notes

**Three steps, not four.** Same convergence the Purse and
Strongbox wizards reached: auto-name on parse-back, no dedicated
label step. The `recovery_setup_notes` free-text field is set on
Vault detail post-creation, same shape as Strongbox's
`signing_device_label` or a Purse rename. Cosigner annotation
(future multisig shape only) is also a Vault-detail concern, not
a wizard step.

**No vendor dropdown.** Single biggest UX divergence from
Strongbox. The Vault input is descriptor-first because the
descriptor's miniscript structure carries far more identifying
information than the source vendor — at parseback the user sees
the timelock shape and the key fingerprint, which together are
more useful than a "from Coldcard" label would be. Vendor
context becomes relevant post-creation if and when we surface
cosigner-device annotation for multisig Vaults.

**Branching at parse time, not at wizard entry.** The wizard
opens onto a single input screen regardless of intended Vault
shape. The parser branches on what's in the descriptor —
single-sig+timelock to one of two parsebacks (CLTV / CSV),
multisig (with or without timelock) to one of three parsebacks
(pure-multisig / multisig+CLTV / multisig+CSV),
single-sig-no-timelock to redirect, unsupported to inline error.
This is intentional: the user thinks "I have this descriptor
from my wallet"; the wizard handles classification. A
shape-picker pre-step would be ergonomic noise.

**Vault detail page is the home of unlock-countdown UI.** The
parseback shows the lock parameters but doesn't compute "X days
left" — that requires the chain tip, which is more usefully
surfaced on Vault detail (a recurring view) than on parseback (a
one-shot screen). Detail page surfaces:
  - For CLTV: wallet-wide countdown to the unlock block.
  - For CSV: per-UTXO unlock schedule sorted by earliest
    spendable.
Vault detail design is scoped to the next Vault iteration; the
wizard hands off cleanly by registering the parsed
`timelock_kind` and `timelock_value` for detail to consume.

**No `sensitive-screen={true}` on any step.** Same as Strongbox.
The wizard never exposes recovery material — spending keys live
on the hardware wallet, on the user's side of the trust
boundary.

---

## Add Holding — Account wizard

Fourth and final per-type wizard. Reuses the same wizard shell
introduced by Purse and refined for Strongbox / Vault. Design
pass closed 2026-05-16 (Rémy greenlight on all four validated
mockups); ships under ADR-0011 (2-key credential model) with
v1 scope narrowed to Kraken.

Unlike the descriptor-based wizards, the Account wizard does
not parse a descriptor — it pairs TallyKeep with a user-created
API key on the connected provider. The matrix of decisions the
earlier Account-wizard drafts struggled with (Read-only vs
Read+Withdraw permission, whitelist target picker, provider-side
whitelist verification, no-Holdings handling) is retired by
ADR-0011's 2-key model: this wizard captures **only the
read-only credential**. The withdrawal credential is configured
separately post-onboarding via the Account detail page's
Withdraw affordance, in its own design pass (captured in
`backlog/account-withdrawal-key-sub-flow.md`).

### Vocabulary lock

- **"Provider"** — the user-facing umbrella term for the
  connected service. Covers exchanges, brokers, and custodial
  banks. Earlier drafts used "exchange," which is too narrow
  (Swissquote is a broker; Lemon is a payments app; both are
  legitimate `CustodialProvider` adapters). The Add Holding
  picker's row description ("Held at an exchange or broker. They
  hold the keys; you see balances.") stays as-is — provider is
  the wizard-internal vocab, the picker stays banking-natural.
- **"API Key" / "Private Key"** — TallyKeep's two input field
  labels carry the provider's exact field names as muted
  aliases (e.g., "Kraken: Clé API" / "Kraken: Clé privée") so
  users mapping from the provider's create-key dialog don't
  need to translate. Per-provider aliases live alongside the
  adapter registration.
- **"Read-only key"** — the credential captured by this wizard.
  Wizard copy is explicit about this scope and forward-
  references the separate withdrawal-key configuration without
  insisting.
- **"Auto-sweep"** — TallyKeep's term for SweepPolicy-driven
  withdrawal. Surfaces only on the Step 3 capability-gated
  suggestion card. The fuller policy concept lives in
  `concerns/sweep_policies.md`.

### Wizard shape (3 steps, parity with Purse / Strongbox / Vault)

Step counter "STEP 1 OF 3 / 2 OF 3 / 3 OF 3". Back chevron at
Step 1 returns to the Add Holding picker (sheet redismissed);
at Step 2 returns to Step 1; at Step 3 (success) hidden — only
path forward is "Done". Bottom-nav hidden during the wizard.

**Sensitive-screen flag.** None of the Account-wizard steps
carry `sensitive-screen={true}`. The API Key and Private Key
strings are credentials with provider-side rate limits and
whitelist defenses, not recovery material in the wallet-seed
sense. Same shell-uniformity posture as Strongbox / Vault. The
Private-Key input does hide its value by default (password
field with reveal toggle) — that's a UX-level concern handled
in the input component, not a screen-level sensitive-flag.

### Screens

**Step 1 — `mobile_add_holding_account_01_connect.html`.**
Heading "Connect a provider," sub naming the breadth ("An
exchange, broker, or custodial bank where you hold funds.
TallyKeep observes your balance with a read-only key.
Automated withdrawal can be configured separately."). Provider
dropdown (searchable; v1 list = Kraken only — see ADR-0011 for
the v1 scope cut). Per-provider helper banner appears once a
provider is selected (info palette, compressed): create the
read-only key on the provider, name it `TallyKeep Read`, enable
only the observation-permission set (for Kraken, `Query funds`
and `Query ledger entries` per ADR-0012), leave everything else
off.
Sub-banner warning (warning palette) about the provider's
shown-once behavior: copy both keys before closing the dialog;
losing one means deleting the key and creating a new one. Two
input fields below: API Key (plain text input + Paste icon) and
Private Key (password input + reveal eye-icon + Paste icon, no
Copy affordance per the privacy-first-reveal memory). Continue
disabled until both fields are non-empty.

On Continue, the backend validates the credential against the
provider's key-permissions endpoint:

- Auth failure → inline error "Invalid API Key or Private Key,"
  user re-pastes.
- Permission overage (any permission beyond the locked
  observation set) or underage (any required observation
  permission missing) → danger band, see error variant below.
- OK → backend persists encrypted credential, fires initial
  poll, advances to Step 2.

**Step 1 — error variant
`mobile_add_holding_account_01_connect_error_overage.html`.**
Same screen with a danger band below the credentials. Title
"This key has too many permissions." Body explains TallyKeep's
minimum-exposure posture, lists the specific overage
permissions detected (verbatim from the provider's key-
permissions response, using the provider's permission names),
and tells the user to replace the keys on the provider with
ones that have only the observation set ticked (for Kraken,
`Query funds` and `Query ledger entries`).

**Tap-to-clear coding rule (Rémy 2026-05-16).** When the user
focuses either input field (API Key or Private Key) after a
rejection, the implementation must clear **both** fields and
dismiss the danger band in the same motion. The two keys are
a *pair* from a single provider dialog; once rejected, they're
deadweight. Holding stale text alongside a danger band creates
half-stale state that confuses. Clean reset is honest. The tap-
to-clear fires on focus event, not on edit, so the reset is
visible the moment the user signals intent-to-edit. Paste-button
usage doesn't trigger an additional clear (paste overwrites
cleanly).

**Step 2 — `mobile_add_holding_account_02_parseback.html`.**
Heading "Here's what we read," sub "Last check before we save
it — does this match what you set up on Kraken?". Auto-name
preview card with the limestone left-stripe (`--color-holding-
account`); value template "{Provider} account" with collision
suffix; inline rename affordance.

Parse-card rows, three on this step:

1. **Provider** — display name only. No region / market
   qualifier (earlier draft had "Global · USD / EUR / GBP pairs"
   under Kraken; dropped — invented flavor text without a clean
   generalization to other providers, plus the provider name
   alone is sufficient identification).
2. **Permission** — "Observe only" with the muted qualifier
   "Read-only — this key cannot move funds." Scoped to *this
   key*, not to TallyKeep in general — earlier draft said
   "TallyKeep can watch, cannot move funds" which contradicted
   the very-next-step auto-sweep suggestion. The 2-key model
   makes the scoping precise.
3. **Other assets** — cap-and-overflow display of non-BTC
   balances detected at the provider ("USDT, ETH, ADA, + N
   more"). Hidden when zero other assets. Earlier draft listed
   asset values verbatim ("USDT 1,234 · ETH 0.05") and didn't
   scale (a 150-position account would render awful). The
   cap-and-overflow pattern confirms multi-asset detection
   without committing to a values display; Account detail
   handles the full multi-asset surface per pre-implementation
   `multi-asset-aggregation`.

No BTC balance row on this step — moves to Step 3 as the
headline value.

No withdrawal mention on this step. The wizard's single
deferred-withdrawal forward-reference lives in Step 1's sub-
heading. Step 2 is for confirmation, not for surfacing future
capabilities.

CTA label "Looks right" — same tonal shift as Purse / Strongbox
/ Vault parsebacks (confirming, not just proceeding).

**Step 3 — `mobile_add_holding_account_03_success.html`.**
Centred success indicator + heading "{Provider} account
connected" + sub "Your balance is live. It'll appear on Home
alongside your other Holdings." Below the heading: headline
balance card with the limestone left-stripe — single-unit
display per the user's home `currency_preference` (sats by
default, BTC if the user has switched; mockup renders the sats
default). No spinner row — the balance was already polled at
Step 1's credential validation.

**Capability-gated suggestion card** below the balance card.
Rendered iff the connected provider's adapter has
`supports_withdrawal_keys = true`. Card carries:

- Heading: "Keep these sats under your control"
- Body: "{Provider} supports automated withdrawals. Let
  TallyKeep move your balance to one of your Holdings when it
  crosses a threshold you set."
- Outlined CTA button: "Set up auto-sweep" — routes to the
  withdrawal sub-flow.

For providers with `supports_withdrawal_keys = false`, the
suggestion card is absent (absence-of-affordance per ADR-0007).
Step 3 then collapses to balance card + Done.

Primary CTA in the wizard footer: "Done" — returns to Home,
new Account appears in the Holdings list with the polled
balance.

### Reconcilability gauntlet answers

1. *Trust boundary:* phone screen (UI) + backend (credential
   validation, encrypted credential storage, polling against
   the provider's API). The user's account at the provider sits
   outside TallyKeep — TallyKeep is a client to the provider's
   API on the user's behalf, with the user's own credentials.
   The provider sees TallyKeep's IP and the API key; it does
   not see the user's TallyKeep passphrase or any other
   TallyKeep secret.
2. *Keys and secrets:* the read-only API credential (API Key +
   Private Key strings from the provider) lives encrypted at
   rest on the TallyKeep backend, encrypted under the user's
   passphrase per `03_data_model.md`. The Private Key string is
   never re-displayed after Account creation; Account detail
   shows only the last-4 characters for identification.
   TallyKeep never has the user's provider-account password,
   2FA secret, or any other credential beyond the API key pair.
3. *Self-hosted vs hosted:* identical from the phone's POV.
   Both backends store the encrypted credential, run the
   polling schedule, and surface balance changes. Neither has
   plaintext access to the credential outside of the
   passphrase-unlocked session. Hosted-tier privacy notice (per
   the onboarding hosted-welcome screen) covers the
   "operationally TallyKeep-hosted backend sees this account's
   activity" disclosure.
4. *Confirmation honesty:* the success step's "{Provider}
   account connected" message is shown only after the backend
   has confirmed credential persistence AND the initial poll
   has returned a balance — no optimistic claim before the
   provider has actually confirmed the credential works. The
   parseback's "Read-only — this key cannot move funds" copy
   is honest about the wizard-scoped credential's actual
   capability; it does not claim TallyKeep has no withdrawal
   capability in general (which would contradict the
   suggestion card on the next step and the withdrawal sub-flow
   path).
5. *Browser-only fallback:* the wizard is fully functional in
   the browser build. No Capacitor-only capability is exercised
   — no QR scan (irrelevant; API credentials are not standard
   QR payloads), no biometric, no native secure-storage. The
   passphrase-encrypted credential storage is uniform across
   browser PWA and Capacitor.
6. *Open-source and reproducibility:* credential validation
   uses the open-source `ccxt` library (Python, MIT-licensed)
   for provider API access. No closed-source dependency on the
   Account path. The `CustodialProviderAdapter` ABC keeps
   provider integrations swappable; adding an adapter is a
   localized change.

### Notes

**Three steps, not four.** Sharpened during the design pass
2026-05-16. Earlier drafts had a separate provider step and a
separate credentials step; the collapse fixes three problems
that surfaced in review: redundant guidance (Step 1's helper
banner already taught the user; the dedicated credentials step
re-stated it), a forgotten paste-warning (the shown-once warning
belongs at the paste moment), and broken parity with
Purse / Strongbox / Vault (3-step wizards). The collapsed Step 1
carries the provider dropdown, helper banner, shown-once
warning, and both credential inputs in a single coherent screen.

**Read-only-only by design, per ADR-0011.** This wizard scopes
deliberately narrower than the Account Holding type's full
capability. The withdrawal credential is a separate
configuration moment, on a separate user timeline, with its own
design pass. The wizard's single forward-reference to that
deferred capability lives in Step 1's sub-heading (informational)
and the Step 3 suggestion card (actionable, capability-gated).
Two mentions across the whole flow; both load-bearing. Earlier
drafts over-leaked the deferred-withdrawal message across all
four prior steps and got flagged for it.

**Capability matrix drives wizard UI.** The provider's
`supports_withdrawal_keys` flag gates the Step 3 suggestion
card's visibility (absence-of-affordance for unsupported
providers). The `whitelist_read_api` flag does not surface in
the wizard at all — it's a withdrawal-sub-flow concern, where
it drives the destination-picker UX (Kraken: read existing
whitelist; Bitstamp / no-API: manual user attestation). Both
flags live in the adapter registration; frontend reads them
via the treasury providers endpoint.

**Bitstamp deferred at v1, not architecturally cut.** The v1
provider dropdown lists only Kraken. Bitstamp moves to
`backlog/additional-custodialprovider-adapters.md` — the same
iteration that covers Lemon, Buenbit, Belo, Coinbase,
Swissquote. Backend adapter is
unchanged at the contract level; the dropdown filter is the
scope-tightening surface.

**No vendor dropdown for the credential source.** Strongbox
has a vendor dropdown because the descriptor's source (Coldcard,
Ledger, etc.) carries meaningful metadata. Account's credential
source is the user's account at the provider — no equivalent
metadata pre-paste. The provider dropdown at the top of Step 1
is the only "which thing am I connecting" affordance the wizard
needs.

---

## Account detail

The per-Holding detail page for an Account. Reached from the
Home Holdings row tap. This is where the user goes to see
their custodial-provider balance, recent activity at the
provider, and to configure the Account (keys, sweep rules,
polling, removal). Design pass closed 2026-05-17 (Rémy
greenlight on all five validated mockups); ships under
ADR-0011 (2-key credential model) + ADR-0012 (observation
scope expansion).

The page anchors around three commitments:

1. **SSE-driven realtime.** No manual refresh button anywhere.
   Balance + ledger updates land via SSE (per iteration A's
   consistency rule); the user trusts the page to be live.
2. **Banking-grade ergonomics.** Two-tab layout (Operations |
   Settings) matches Revolut / N26 / Boursorama. Single-unit
   hero (sats default, ↻ toggle cycles the whole page —
   same component and state-key as the home-page hero).
3. **Honest absence-of-affordance for deferred flows.** Withdraw,
   Deposit, Auto-sweep "Add rule", and the Settings tab's
   key-setup / address-setup / key-replace CTAs all render as
   real action buttons but route to coming-soon placeholders
   until their dependent flows ship. The mockup specifies the
   target; the implementation gates the routing.

### Vocabulary lock

- **"Operations"** — the activity-feed tab. Locked across
  spec, code, and user-facing UI.
- **"Settings"** — the configure-this-Account tab. Distinct
  from the app-wide Settings nav item; this one is per-Account.
- **"Updated N min ago"** — the freshness indicator copy.
  Locked. *Never* "Last polled X ago" anywhere user-facing.
- **"Connected" / "Connection lost"** — the connection-state
  copy in the status card. Maps to backend's
  `treasury.custodial.connection_state_changed` SSE states.
- **"Card-with-arrow"** — the action-button icon metaphor for
  Deposit (arrow going into the card) and Withdraw (arrow
  going out of the card). The Account is the card; arrow
  direction shows the flow relative to it. Sidesteps the
  up-vs-down ambiguity.
- **"Cannot reach Kraken"** — the toast title for transient
  connection issues. Provider-specific; coding agent
  substitutes the actual provider name.
- **"Danger zone"** — Settings tab's bottom section housing
  Rename + Remove. GitHub / Vercel convention.

### Page chrome (consistent across tabs)

Stacked top-to-bottom:

- **App bar** — back chevron returns to Home; account name
  centered (e.g. "Kraken account"); right slot reserved for
  future per-page actions, empty in v1.
- **Status card** — limestone left-stripe (Account-type anchor,
  same accent as the Holdings row on Home); provider name on
  the first line; connection-state dot + state copy + middot
  separator + freshness on the second. The whole card is
  tap-to-refresh (force-poll).
- **Hero** — BTC balance in the user's active unit (sats
  default), large tabular-nums; ↻ toggle next to the unit label
  cycles the whole page sats ↔ BTC. Non-BTC cap-and-overflow
  row below ("Other assets: USDT, ETH, ADA · + 9 more"),
  hidden entirely when zero non-BTC balances.
- **Action row** — Deposit + Withdraw, light-CTA weight
  (`primary-soft` background, `primary-strong` text/icon),
  card-with-arrow icons.
- **Tab strip** — Operations | Settings, swipeable +
  segmented-control, sticky on scroll. Active-tab underline =
  brand verdigris.
- **Bottom nav** — Home tab active (the user is in the
  home-section of the app).

### Operations tab

The activity feed of recent ledger entries from the provider's
unified ledger (per ADR-0012's observation scope). Each entry:

- Text-only descriptor ("Deposit · BTC", "Trade · BTC/EUR",
  "Withdraw · BTC", "Fee · BTC", …). **No kind-icons**:
  Kraken's ledger surfaces more kinds than we've enumerated
  (fees, transfers, stake events, rebates, adjustments,
  others); committing to a per-kind icon vocabulary before
  the wild data is in lock-in we might have to redraw. Defer
  the icon vocabulary; text alone carries the row.
- Relative time ("2h ago", "yesterday", "5d ago"). Switches
  to absolute date past ~7 days ("May 10").
- Single-unit amount in the active unit, right-aligned,
  sign-based color (positive `success-text-on-soft`, negative
  `danger-text-on-soft`, neutral default text).
- Pull-to-refresh on the whole scroll area triggers a
  force-poll. Standard mobile gesture; no chrome at rest.

**Empty state** (fresh accounts or no activity in observation
window): sober text-only panel. Title "No activity yet", sub
"Your deposits, withdrawals, and trades will surface here as
they happen on Kraken." No illustration.

### Settings tab

Per-section configuration cards, iOS-style uppercase labels
above each card:

- **Provider** — display name + connection-established date.
  Pure info, no CTA.
- **Observation key** — last-4 chars (mono, masked) +
  configured date + **Replace** CTA. Replace routes to a
  coming-soon stub in v1 (key-replace lands in its own small
  iteration).
- **Withdrawal key** — "Not configured" + short explanation
  + **Set up** CTA. Routes to the withdrawal sub-flow per
  `backlog/account-withdrawal-key-sub-flow.md`.
- **Deposit address** — "Not configured" + short explanation
  + **Set up** CTA. Routes to the deposit-flow address-capture
  per `backlog/deposit-send-to-account-flow.md`.
- **Auto-sweep rules** — "None" + explanation + **Add rule**
  CTA. Routes to SweepPolicy creation (its own iteration).
- **Polling** — current cadence (default 10 min) + **Change**
  CTA. Real in v1: picker for 1 / 5 / 10 / 30 / 60 min.
- **Danger zone** — last section, label in `danger` text
  colour. Two rows: Rename (neutral CTA) + Forget (`danger`-
  coloured CTA). Forget opens the two-button bottom-sheet
  confirm modal. The verb is "Forget" rather than "Remove" or
  "Delete" — TK never custodies user funds and never destroys
  anything outside its own observation surface; "Forget"
  describes what TK actually does. Locked across all Holding
  types (see Cross-type vocabulary lock below).

**Whitelist destination** section is conditional — appears
between Deposit address and Auto-sweep rules once the
withdrawal key is configured. Hidden in v1's fresh-account
state (honest absence-of-affordance).

### Behaviors

**Unit toggle (sats ↔ BTC).** The ↻ next to the hero unit
label cycles the whole page's amount displays (hero + activity
entries). State is shared with the home-page hero — same
preference key, same component. No per-page divergence.

**Pull-to-refresh.** Standard iOS/Android overscroll gesture
at scroll position 0 triggers a force-poll. When mid-list, the
gesture scrolls back to top without triggering refresh. No
conflict with normal scrolling.

**Tap-to-refresh on the status card.** Tapping anywhere on the
status card triggers a force-poll. Complementary path for users
who don't know the pull gesture. On press: dot briefly becomes
a spinner; on response: dot returns + freshness resets to
"Updated just now".

**SSE-driven live updates.** `treasury.custodial.ledger_entry_added`
inserts new entries at the top of the activity feed and updates
the displayed balance atomically (per iteration A's consistency
rule — Option A or B from the iteration A scope; the page
consumes whichever the coding agent picked).
`treasury.custodial.connection_state_changed` drives the status
card's dot colour and triggers the connection-error toast on
transitions to unreachable.

**Connection-error toast.** On transition to unreachable, a
red-soft toast slides down from below the app bar with title
"Cannot reach Kraken" + dismiss × + "Try again now" CTA.
Auto-dismisses after ~5 seconds. Re-appears on each failed
retry. The page content itself renders normally — only the
status card's red dot is persistent. The toast is the
transient action prompt; the dot is the at-rest state.

### Screens

- **Operations tab — populated.** `mobile_account_detail_operations_populated.html`.
  Default state with non-zero balance, 6+ activity entries.
  The visual anchor mockup for the iteration; chrome and
  conventions defined here propagate to all four variants.
- **Operations tab — empty.** `mobile_account_detail_operations_empty.html`.
  Fresh-account state: balance zero, no non-BTC row, sober
  text-only empty-state panel in the activity area.
- **Settings tab — default state.** `mobile_account_detail_settings.html`.
  All sections at their fresh-account defaults; six set-up
  CTAs route to coming-soon stubs (per the deferred-flows
  list above); Polling Change CTA is real; Danger zone at
  the bottom.
- **Remove-confirm modal.** `mobile_account_detail_remove_confirm.html`.
  Bottom-sheet reached from the Settings tab's Danger-zone
  Remove. Dimmed Settings-tab silhouette behind. Two-tone red
  two-button confirm: light-red Cancel (left), `danger`-filled
  Remove (right). No type-to-confirm — the action is
  reversible (re-add via the Add Account wizard).
- **Connection-error toast variant.** `mobile_account_detail_connection_error.html`.
  Operations tab with a red dot in the status card +
  slide-in toast at the top + cached activity entries
  rendered normally. The toast pattern (not a banner)
  signals transience without painting the page broken.

### Reconcilability gauntlet (per PROCESS.md §3)

1. *Trust boundary.* Page sits on the phone (UI); reads from
   the backend (cached Account row + ledger entries). Backend
   talks to the provider (Kraken) over the ccxt adapter. Keys
   never leave the backend; the page never touches credentials
   directly.
2. *Keys and secrets.* Observation credential lives encrypted
   on TallyKeep (ADR-0011 + ADR-0012). Withdrawal credential,
   when configured (future iteration), lives the same way. The
   Settings tab shows only the last-4 chars of the observation
   key for identification; never the full credential. Replace
   re-captures the key in a future iteration.
3. *Self-hosted vs hosted.* Identical from the page's POV.
   Both backends serve the same SSE topics and REST endpoints;
   the connection-state dot reflects whichever backend the user
   is connected to. Hosted-tier privacy notice (per onboarding
   hosted-welcome) covers the visibility disclosure.
4. *Confirmation honesty.* Freshness indicator is honest about
   staleness ("Updated N min ago" updates live, resets on each
   new event). Balance is the last-known polled value with the
   staleness signal carried by the freshness indicator and the
   connection dot. The connection-error toast surfaces transient
   drops; cached entries stay visible without false confidence
   that the data is live.
5. *Browser-only fallback.* Fully functional in the browser
   build. No Capacitor-only capability exercised. SSE works in
   the browser; pull-to-refresh is browser-native; the toast
   and bottom-sheet patterns are CSS+JS only.
6. *Open-source and reproducibility.* SSE topics consumed
   (`treasury.custodial.*`, `system.chain.*`) are all defined
   by the open-source backend (FastAPI + ccxt). Frontend
   subscribes via standard `EventSource`. No closed-source
   dependency on the Account-detail path.

### Notes

**Two-tab structure locks across Holding types.** "Operations" and
"Settings" are the two tabs for all per-Holding detail pages.
Purse / Strongbox / Vault detail pages (future iterations)
inherit this shape — same chrome, same tabs, different content
per type. The card-with-arrow Deposit / Withdraw icons are
Account-specific; chain-based Holdings have different action sets
(Receive / Send) and may use different icon metaphors.

**Connection-status dot semantics per Holding type:**

- Account: backend's connection to the provider API
  (`treasury.custodial.connection_state_changed`).
- Chain-based Holdings (Purse / Strongbox / Vault): backend's
  connection to bitcoind (`system.chain.connection_state_changed`).

Same UI affordance, per-Holding-type meaning. Locked.

**Activity feed kind-icons deferred.** Per the 2026-05-17 Step 2
follow-up, text-only descriptors carry the activity rows. Kraken's
unified ledger surfaces more kinds than enumerated; committing
to per-kind icons before iteration B's Operations tab has seen
the full wild set risks lock-in. Sign-based amount colour does
the visual lift for now.

**TK-initiated vs external activity distinction deferred.** Per
ADR-0013 (custodial ledger mirroring posture and TK-initiated
event linkage). v1 renders all entries identically; the visual
distinction lands when that arbitration's UI follow-up is
sharpened.

**Deferred CTAs route to coming-soon stubs.** Withdraw, Deposit,
Auto-sweep "Add rule", Observation key "Replace", Withdrawal key
"Set up", Deposit address "Set up" — all six route to a
parameterized coming-soon screen mirroring
`mobile_add_holding_coming_soon.html`. Mockup specifies the
target; implementation gates the routing.

**No type-to-confirm on Forget.** Dropped after the 2026-05-17
review. The action is genuinely reversible for Account (re-add
via the Add Account wizard); the friction wasn't earning its
keep. Two-tone red confirm (light-red Cancel + red Forget)
carries the are-you-sure.

**"Forget" cross-type vocabulary lock.** The destructive Settings-
tab action is **"Forget"** across all Holding types — not
"Remove" or "Delete". Reasoning: TK never custodies user funds
and never destroys anything outside its own observation
surface. For most Holding types, Forget literally just means
"TK loses memory of this Holding". Per type:

- **Account** — TK forgets the API credentials and stops
  polling. Provider-side account, balance, and history are
  untouched.
- **Strongbox** — TK forgets the descriptor and stops chain-
  scanning these addresses. Hardware-wallet keys + on-chain
  UTXOs persist.
- **Vault** — TK forgets the multisig descriptor + cosigner
  annotations + any sweep rules. Cosigner keys + on-chain
  funds persist.
- **Watch-only Purse** — TK forgets the descriptor. Funds on
  the external wallet persist.
- **TK-managed Purse (`ON_DEVICE_TK_GENERATED` /
  `ON_DEVICE_USER_IMPORTED`)** — **the load-bearing exception.**
  TK forgets the descriptor AND destroys the on-device seed via
  NativeBridge. If the user hasn't backed up the recovery
  phrase, the funds become permanently inaccessible. The
  Purse-detail Forget modal body MUST carry an explicit
  warning: "If you haven't backed up the recovery phrase,
  you'll lose access to these funds permanently." This is the
  only Holding-type case where Forget has material on-chain
  consequences; the warning is non-negotiable, and the modal
  body for this case may also include a "Have you backed up?"
  acknowledgement-style checkbox (final UX call deferred to
  the Purse-detail iteration).

The "Forget" vocabulary is locked across iteration B (Account
detail) and inherited by the future Purse / Strongbox / Vault
detail iterations.

