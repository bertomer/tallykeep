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
Activity + Categorization, Sweep policy + Trading view, Settings.

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
  first-touch surfaces". *Status: draft.*
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
  [Skip for now] text-link. *Status: draft.*
- `mobile_onboarding_02_paired_biometric_done.html` — second
  screen, post-biometric-enabled state. Single prominent
  success indicator (large green check), "All set" heading, a
  facts card showing both anchors ("Connected to: Rémy's home
  server" + "Daily unlock: Biometric · passphrase fallback"),
  [Continue] primary.
  Single CTA — no skip path from this state. *Status: draft.*
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
  the user sees what they're about to skip past. *Status: draft.*
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
  *Status: draft.*

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
  "TOTAL BALANCE" small uppercase label, left-aligned mono `0`
  amount at 36 px semibold, baseline-aligned with a small unit
  column to the right (a 14-px cycle icon stacked above a
  `sats` label — the icon is the affordance for cycling
  sats / BTC, the label is just the unit). Subdued
  `Show in fiat` link beneath the amount (dim, no underline, no
  arrow — we don't push fiat). Below the hero: a "HOLDINGS"
  section header (uppercase 11 px, muted) with a small
  `+ Add` affordance right-aligned. An empty list-card
  placeholder below the header carries "No Holdings yet"
  (`--color-text-dim`, small, centered). Bottom nav with four
  tabs: Home (active), Activity (greyed, no transactions yet),
  Holdings (greyed, no Holdings yet), More (enabled — Settings
  always works). *Status: validated (Rémy greenlight 2026-05-10).*

Populated states (single Holding, multiple Holdings,
discrepancy banner, fiat-on) are not yet drafted — they sharpen
in subsequent sessions once the empty state is locked.

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
   on Activity or in per-Holding detail per spec module 05,
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

**Mono amount, left-aligned.** Mono numerals are the
institutional-banking default — they read as data, not
display copy. Left-aligned means the leftmost digit stays at
a fixed position as the number grows (0, 100, 1,000,
1,000,000 all start at the same x-coordinate). Centered
numerals shift around; banking-grade does not.

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

**Add affordance is a small rounded-square outlined `+`
button.** Sharpened across three passes 2026-05-10. First:
big centered primary CTA (rejected — too "shiny",
Phoenix-coded). Second: small `+ Add` text-link in the
section-head (rejected — translation friction: "Add" varies in
width across languages and `+` alone is universal). Third:
circular filled button with a bold `+` glyph (rejected — felt
"fat" and too prominent for a section-header affordance).
Final: 28-px rounded-square (`--radius-md`), 1.5-px solid
primary-color outline, transparent background, SVG `+` inside
with stroke-width 2 at 14×14 px (visually ~1.2 px effective
stroke — elegant, not heavy). Quieter than filled, still
unambiguous as an affordance. On tap, opens the Add-Holding
picker popup (per `next_iteration.md` transient — four type
choices in a popup, not inline on the empty state).

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
   `01_architecture.md` and `10_threat_model.md`).
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

**Principles card is acknowledgment-required, onboarding-only.**
Until the user clicks "I understand," the card stays visible
on this screen; it does not gate the primary CTA (the user can
tap "scan QR" without acknowledging). After acknowledgment, the
card does not appear again — neither on subsequent onboarding
screens nor on the home page. Principles get re-anchored later
via Settings → "How TallyKeep works" page, first-time tooltips
on sensitive flows, and the security-health system. One light
pass at the door, not a permanent banner.

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
