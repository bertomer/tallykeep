# UI — cross-platform truth

This file captures cross-platform UX decisions and the high-level
flow inventory. Platform-specific implementation lives elsewhere:

- `mobile.md` — mobile screens, screen-by-screen
- `desktop.md` — desktop screens (later)
- `mockups/` — page-per-file HTML mockups for visual fine-tuning

When something here contradicts a platform spec, this file wins for
the cross-platform decision; the platform spec implements it
appropriately for its surface. When this file is silent on something
platform-specific, the platform spec decides.

This doc absorbed the cross-platform content from the retired
UI/design_decisions.md (now under `archive/UI/`) during the
consolidation merge. The retirement and consolidation are recorded
in ADR-0001 and ADR-0002.

---

## Product positioning

**TallyKeep is for users who want banking ergonomics on Bitcoin.**

The user we are designing for understands checking accounts, savings
accounts, and safety-deposit boxes — and wants the same mental model
for their Bitcoin without the crypto-native friction. They are *not*:

- A Bitcoin power-user who wants UTXO control as the primary
  interface (Sparrow, Specter, and Electrum exist for them).
- A trader looking for price charts and percentage moves.
- A fintech-native who wants their bank to also speculate.

We will not bend the design to also serve those users. The
sophisticated user who values both can use TallyKeep when they want
banking ergonomics and switch to Sparrow when they need descriptor
surgery. That's a feature, not a gap.

---

## Mobile and desktop

Mobile and desktop are two surfaces with different jobs. Mobile is
the daily-use surface — quick balance checks, send, receive,
categorize. Desktop is an operations console — setup, configuration,
deep transaction history, accounting export, hardware-wallet PSBT
roundtrips. They share the backend, the brand, and the data model.

**Mobile is being built first.** The Capacitor build is the only
surface that holds spending keys; browser PWA on either platform
never holds signing material. This is locked per ADR-0002 / ADR-0003
/ threat model §Mobile addendum.

**Codebase architecture for desktop is TBD.** A "single SvelteKit
codebase, layout shell branches on viewport" pattern works only if
mobile and desktop are mostly the same with light layout changes.
Real-world banking apps suggest that's often not the case — CIC's
mobile and web apps are an instructive comparison: same brand, same
data, fundamentally different information architecture (mobile: one
prominent account card with stacked actuality below; desktop: a
three-column overview console). The call — one project with route-
group divergence vs. two projects sharing an npm-package'd library
— is deferred until desktop work begins and we have actual mobile UX
to compare against.

---

## Current cross-platform direction

These hold on every platform unless an iteration decides otherwise
explicitly. The label "current direction" is deliberate: only one of
these (honest abstraction) is locked at the principle level. The
rest are working calls that may evolve as we learn what's
distinctive about TallyKeep.

### Sats are the default unit

Sats make small amounts feel real (21,000 sats > 0.00021 BTC,
psychologically) and are the native Bitcoin unit. BTC and (optionally)
fiat are alternative views toggled by the user. Fiat is a translation
layer, not the home unit.

### Currency consolidation is opt-in via a single dropdown

Empty selection = no consolidation, sats only. A selected currency
gives a consolidated value across all Holdings in that currency. No
separate on/off toggle; the dropdown's empty state IS the off state.
Default: empty (no consolidation).

### Rate source surfaced honestly when fiat is on

Small "via [source] · 2m ago" attribution next to the consolidated
value. Not authoritative; transparent about its origin.

### No performance metrics on the landing surface

No "↑ 1.2% today," no daily change indicators, no portfolio-up/down
vocabulary. TallyKeep's user is *holding*, not trading. Performance
and cost-basis surface on Holding detail pages (especially long-term
ones — Vault), not on the landing.

### Banking-first defaults

The user shouldn't see UTXO views, raw transaction hex, descriptor
expressions, coin control, or RBF mechanics in the default UI. How
exactly these are revealed (master toggle, per-feature toggles,
contextual prompts, advanced-mode flag) is designed in the relevant
iteration, not pre-stated here.

### Honest abstraction (locked from spec)

Reuse familiar banking vocabulary in the UI; surface Bitcoin reality
in detail panes; never hide consequences. The reconcilability
gauntlet (PROCESS.md §3) enforces this at design time. The
*confirmation honesty* gauntlet question specifically catches
optimistic UI states — never "sent" before broadcast acknowledgement,
never "confirmed" before chain inclusion, confirmation depth shown
verbatim. Settlement-rails framing with confirmation probability is
in `future_iterations.md` as a strong differentiator candidate.

---

## Holding type vocabulary

The four user-facing Holding types preserve their domain-model names
in the UI. Banking analogies appear in pickers and tooltips for
clarity, not in the primary labels.

| Type | Banking analogy | Description shown to user |
|---|---|---|
| Account | Like an exchange account | Money you've got at a custodial provider that you want to manage from here |
| Purse | Like a checking account | An everyday wallet for spending and small amounts |
| Strongbox | Like a savings account, but you hold the key | A safer spot for medium-term holdings, usually on a hardware wallet |
| Vault | Like a safety-deposit box | A heavily-protected long-term holding, multi-key, used rarely |

Purse has two seed origins per ADR-0006 (slug `purse-flavors`).
The seed origin is a backend-stored intent field;
*which client device actually holds the seed* is a per-client,
runtime fact (see module 02 §"Signing capability is per-client").

- **External-watch-only Purse** — onboarded via xpub / descriptor.
  No seed lives in any TallyKeep client; the user's seed is in
  another hot wallet. Available on every platform. Spending always
  points back to the source wallet.
- **TallyKeep-managed Purse** — TallyKeep generated the seed during
  Add-Holding; the seed lives in the Keychain/Keystore of *the
  specific client device that ran the creation flow*. From that
  device, native send (biometric + sign in-app + broadcast) is
  available. From any other client viewing the same backend, the
  same Holding appears with a "go sign on the device that holds the
  seed" gate. The "Create a TallyKeep wallet" affordance is gated
  client-side on the device's capability to generate and securely
  store a seed (Capacitor on phone: shown; browser PWA on any
  platform: hidden, with a "this requires the TallyKeep app"
  message).

---

## Flow inventory

The product surfaces these flows. Each has its own section in
`mobile.md` (and later `desktop.md`) with screen-by-screen detail
plus reconcilability gauntlet answers. This list is the
cross-platform truth about *which flows exist and what each one
does*; the *how* lives in the platform specs.

### Onboarding

Five screens: Welcome → Passphrase + biometric daily-unlock toggle →
Hosting choice → Connection (self-hosted) or Hosted welcome (privacy
acknowledgment).

After step 4, the user lands on the home page in its empty state. No
"first Holding" wizard step — the home page itself is where the user
starts adding Holdings.

### Home

Same page in empty and populated states; the empty state is the
first visit. Contains:

- Unit + currency controls (always visible)
- Total balance hero + Send/Receive primary actions (populated)
- Holdings table (populated)
- Security discrepancy banner (when analyzer fires)
- Add affordances for the four Holding types

Recent activity and categorization live in the Activity tab
(cross-Holding view) and on per-Holding detail pages — never on the
home / consolidated landing page. The home is for at-a-glance
"where is my money" and primary actions; the Activity tab is for
review and categorization work. The push-driven categorization
prompt is captured for later in `future_iterations.md`.

### Add Holding

Type chooser → type-specific flow.

- **Add Account:** provider selection → credentials → whitelist
  verification.
- **Add Purse:** binary at the start of the flow:
    - **Import an existing wallet** (`purse_mode=watch_only`)
      — paste / QR an xpub or descriptor. **xpub or descriptor only**
      — single-address import is not supported (per ADR-0006;
      observing one address misrepresents wallet activity that
      rotates across many addresses).
    - **Create a new TallyKeep wallet**
      (`purse_mode=on_device_tk_generated`) — TallyKeep generates a
      fresh seed into the current client's Keychain/Keystore and
      registers the derived descriptor with the backend. Includes
      the seed-backup warning per pending pre-implementation item
      `seed-backup-disclosure`. The affordance is shown only on
      clients with the capability to generate and securely store a
      seed (Capacitor on phone). Hidden on browser PWAs with a
      "this requires the TallyKeep app" message.
- **Add Strongbox:** hardware wallet descriptor (paste / QR / wallet-
  app handoff).
- **Add Vault** (single-key only in dev phase): metadata + descriptor.

### Holding detail

Per type:

- **Account:** balance, recent activity, sweep policy status, manual
  sweep.
- **Purse:** balance, send / receive, recent activity, categorization.
- **Strongbox:** balance, send (PSBT) / receive, recent activity,
  categorization.
- **Vault:** balance, send (PSBT) / receive, declared-vs-observable
  status, recent activity, categorization.

### Send

The Send experience differs significantly per Holding type because
the underlying mechanic differs. Per type:

- **Account** — "Withdraw to whitelist." Triggers a withdrawal at
  the CustodialProvider via API; funds go to the pre-whitelisted
  destination set during Account onboarding (typically a Strongbox
  or Vault). The user does not choose a destination here. This is
  the only way TallyKeep moves funds out of an Account today.

- **Purse (external-watch-only)** — Send is hidden by default.
  Primary affordance points the user at the source wallet ("Spend in
  [wallet]" with a deep-link where supported). Power-user toggle
  exposes "Construct PSBT for export" for the rare workflow that
  wants it. TallyKeep aggregates and observes; doesn't compete on
  spending UX where the source wallet already owns it.

- **Purse (TallyKeep-managed)** — behavior depends on whether *this
  client* holds the seed for this Holding (runtime check against
  local Keychain/Keystore, keyed by holding_id):

  - *On the device that holds the seed* — Native send:
    1. Compose (paste/scan address, amount, fee tier, label)
    2. Review
    3. Sign — biometric prompt + signing in-app
    4. Broadcast
    5. Confirmed (depth shown verbatim; confirmation probability
       when implemented per `future_iterations.md`)
  - *On any other client* (different phone, browser PWA on
    desktop or mobile) — Send shows a clear gate: "This wallet's
    keys are on another device. To spend, open TallyKeep on the
    device that holds them." No PSBT export, no pretend-to-sign.
    Pairing-based PSBT roundtrip between TallyKeep instances is
    captured for later in `future_iterations.md`.

- **Strongbox** — Five-step PSBT flow with the user's hardware
  wallet at step 3:
    1. Compose
    2. Review (with "verify destination on signing device" warning)
    3. Export PSBT (file / QR / base64); user signs externally on
       the hardware wallet; user re-imports the signed PSBT
    4. Broadcast
    5. Confirmed

- **Vault** — Five-step PSBT flow with multisig coordination at
  step 3. Single-key Vault in the dev phase reduces to
  Strongbox-shaped behavior; full multisig comes post-ship.

**Cross-platform behavior.** Only the TallyKeep-managed Purse on
the Capacitor device that actually holds its seed signs natively
inside TallyKeep. Everything else — external-watch-only Purse,
Strongbox, Vault, **and TallyKeep-managed Purse viewed from any
device that doesn't hold its seed** — requires external action
(PSBT roundtrip, source-wallet redirect, multisig ceremony, or "use
TallyKeep on the device where the seed lives"). When the same user
accesses the same TallyKeep instance from both the Capacitor app
(phone) and a browser (laptop), the same TallyKeep-managed Purse is
spendable from the phone and view-only from the browser, because
the seed lives in the phone's Keychain/Keystore — not in the
backend, not in the browser.

**Keys never transit through TallyKeep's backend in any case.** The
backend stores descriptors (public-key data) for observation and
address derivation; signing material lives only on the device that
holds it (hardware wallet, Capacitor app's Keychain/Keystore,
multisig cosigners). Locked per ADR-0002 / ADR-0003 / threat model
§Mobile addendum.

Lightning "Instant" tier visible-but-disabled across all flows with
"coming when the Lightning iteration ships" tooltip.

### Receive

Per Holding, surface a fresh receive address (or the
custodial-provider deposit address for Account):

- **Account:** the deposit address provided by the exchange via
  API. May be reused or rotated per the provider's policy.
- **Purse (external-watch-only):** TallyKeep derives the next
  unused address from the imported descriptor / xpub. Address
  derivation is a public operation; TallyKeep doesn't need keys for
  it. Both TallyKeep and the source wallet observe the chain and
  stay in sync.
- **Purse (TallyKeep-managed):** derive next unused address from
  the descriptor registered at Holding creation. Receive works
  identically on every client (any device viewing the Holding can
  show a fresh receive address — derivation is public).
- **Strongbox:** derive next unused address from the hardware
  wallet's descriptor. **Verify-on-device step required** — prompt
  the user to confirm the address on the hardware wallet's screen
  before sharing. Defends against malware swapping the address
  between display and copy.
- **Vault:** same as Strongbox, with verify-on-device for whichever
  cosigners have screens.

Receive supports BIP 21 payment URIs
(`bitcoin:address?amount=0.5&label=invoice123`) so the sender's
wallet can pre-fill the request. Specific layout — text, QR, copy,
share — designed in the Receive iteration.

Receive uses fresh-per-payment addresses by default. Reuse is
technically possible but flagged by the Blueprint analyzer for
privacy reasons (deferred post-ship per `future_iterations.md`).
The persistent identifier of the wallet is the descriptor / xpub,
which stays internal — only fresh-derived addresses are shared
externally.

Lightning Receive (deferred to the Lightning iteration) generates an
invoice rather than an address — different mechanic, lives behind a
tab visible-disabled today.

### Activity + Categorization

Cross-Holding activity feed. On mobile: a dedicated Activity tab
carries this. Categorization is possible from the per-Holding
detail page and from the Activity tab. Push-driven categorization
prompts and timed in-app popups are captured in
`future_iterations.md` for a later iteration.

### Custodial accounts and sweep policies

The custodial / sweep surface covers two related things:

**Custodial accounts (Account Holdings).** For users who connect a
CustodialProvider (Kraken, Bitstamp): connection status, balance,
whitelist target, recent activity. Specific affordances (panel
layout, controls, kill switches) are designed in the Treasury-view
iteration.

**Sweep policies — generalized.** Per `concerns/sweep_policies.md`, a SweepPolicy
moves funds from any Holding to any Holding, with a safety validator
that warns about risky configurations but never blocks (the user is
the final authority). Specific UI for sweep-policy creation and
listing is designed in the Treasury-view iteration.

**Auto-sweep is only feasible when TallyKeep can sign without
external action.** Practically:

- **Account → anywhere** — provider API, no signing required by
  TallyKeep.
- **TallyKeep-managed Purse → anywhere** (only when scheduled on
  the device that holds the seed) — biometric prompt + native
  signing on that device.
- **Strongbox → anywhere** — not auto. Reduces to a scheduled
  reminder that prepares a PSBT awaiting the user's external
  signature on the hardware wallet.
- **Vault → anywhere** — not auto. Same as Strongbox plus multisig
  coordination.
- **External-watch-only Purse → anywhere** — not possible (no keys
  held by any TallyKeep client).

**Dev-phase scope:** Account-originated sweeps only (the
minimum-exposure-trading use case). Other Holding-to-Holding sweeps
are architecturally supported but their UX is design-deferred to a
future iteration — see `future_iterations.md` "Holding-to-Holding
sweeps beyond Account-originated".

Visible only when the user has at least one Account or has set up
another sweep. **Order placement** (buying / selling Bitcoin through
the connected provider) is explicitly out of scope through the
personal-use phase — current scope is read + withdraw + auto-sweep
only. Adding order placement triggers a regulatory / KYC conversation
captured in `future_iterations.md` ("Order placement on custodial
providers").

### Settings

Configuration surface for the user. Designed in its own iteration
when the time comes; nothing decided cross-platform yet beyond what
naturally surfaces in other sections.

---

## Deferred past ship-gate

These were originally scoped as in-scope-now features in earlier
modules but have been deferred past the public-ship event per
Rémy 2026-05:

- **Blueprint analysis** — the four hygiene flags (address reuse,
  dust UTXOs, round-number outputs, suspected consolidation) plus
  later UTXO clustering graph. Backend logic per `concerns/observation.md` is
  implemented; UI surface deferred. Captured in
  `future_iterations.md` as a public-product differentiator candidate
  to ship as a feature update post-launch.

---

## What this doc does NOT cover

- Screen-by-screen layout, components, and states — see `mobile.md`
  / `desktop.md`.
- Implementation specifics (SvelteKit components, routing, state
  stores) — those are code, not spec.
- Brand identity, copy voice — see `brand/README.md` (mark,
  wordmark, palette locked; voice/about draft; finalized at
  the public-ship event per ADR-0003).
- Future iterations and parked ideas — see `future_iterations.md`.
- The threat-model implications of mobile and the Capacitor build
  — see `concerns/threat_model.md` §Mobile addendum.
