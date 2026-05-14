# Pre-implementation arbitration

Items requiring a dedicated arbitration session before they can be
folded into `next_iteration.md`. Different tone (Rémy's decision,
with reasoning), different autonomy (no coding agent should guess
these).

Each has a recommendation. Rémy decides, dates, and the item
**leaves this file**:

- Foundational decisions land as ADRs in `decisions/`.
- Implementation work moves to `next_iteration.md` (if active) or
  `future_iterations.md` (if deferred).
- The relevant canonical doc is edited to reflect the decision.

There is no "Decided" section in this file. Closed items leave;
the decision history lives in `decisions/` (foundational) and in
git history of the canonical docs (everything else). This is the
single-source-of-truth rule (PROCESS.md §1) applied to decisions.

## Item identifier convention

Items are identified by **stable slugs**, not letters. Slugs do
not get reassigned when items are added or removed. References
from canonical specs (`per pre-implementation item
\`purse-flavors\``) stay correct as the file evolves. When an
item leaves this file, the slug is preserved in the migrating
ADR's "Migrated from" header so back-references still resolve.

Format per item: status, item, recommendation, reasoning,
decision slot.

---

## Open

### `vault-pre-multisig-shape`

**Status:** open (resolved in the brainstorm session that
sharpens the Vault wizard iteration).

**Item:** A Vault is multisig by definition (per
`holdings/04_vault.md`: "A single-key Holding is not a Vault —
that's a Strongbox"). Target-state implementation supports
multisig descriptors. **What does the product do *before*
multisig descriptor support ships?**

Two shapes, both consistent with the target definition:

- **Block.** Add-Vault is disabled with: *"Vault Holdings
  require multisig descriptor support, which ships in a later
  iteration. To track Bitcoin held with a hardware wallet
  today, use Strongbox. Your Strongbox can be promoted to a
  Vault when multisig support arrives."* Cleanest match to the
  definition. No half-state. Cost: a user who wants the Vault
  semantic identity (long-term storage, ceremonial spending
  guardrail) can't have it yet.
- **Accept single-key as a temporary placeholder.** Add-Vault
  accepts a single-key descriptor; the
  `claimed_multisig_but_single_key` discrepancy fires at high
  severity, the user dismisses with "yes, multisig setup in
  progress". Lets users carve out the Vault slot now, get the
  long-term-purpose framing + outgoing-payment guardrail, and
  migrate the descriptor when multisig ships. Cost: a Vault
  Holding that's structurally indistinguishable from a Strongbox
  for some time, papered over by a discrepancy warning.

**Tensions worth surfacing in the session:**

- The declared-vs-observable principle accommodates option B
  cleanly (the discrepancy is *exactly* what that system is
  for). Option A says "the type system shouldn't tolerate
  obviously-wrong configurations even with a discrepancy".
- The Vault outgoing-payment guardrail (warn before sending
  from `purpose=long_term` Vault) only triggers on Vault-typed
  Holdings. Option A delays that guardrail availability.
  Option B lets the user have it now, even on a single-key
  setup.
- Multisig setup is genuinely a process — collecting xpubs from
  multiple hardware wallets, coordinating across signers,
  testing the spend ceremony. Option B accepts that a user
  partway through that process has a temporarily-single-key
  Vault. Option A says: don't create the Holding until the
  process is complete.

**Leading direction:** None — Rémy explicitly left this open
2026-05-14 ("I don't know what to do"). Resolve before the
Vault-wizard iteration sharpens.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `sweep-validator-extended-rules`

**Status:** open (deferred to brainstorm after the four Holding
types are working end-to-end in code)

**Item:** What additional warnings — beyond `no_maximum_cap_set`
and `unverified_whitelist_on_provider` — should the SweepPolicy
safety validator surface? Earlier drafts had
`destination_is_custodial`, `destination_keys_on_host`, and
`same_security_tier` rated `high` / `medium`; those have been
pulled because they opinionate about user intent in ways that
don't survive contact with real use cases (decumulation toward
custodian is legitimate; on-device-keys Purses aren't inherently
riskier destinations; same-tier sweeps can be legitimate rotation
flows).

**Why deferred:** real validator design needs the four-Holding
infrastructure working first. Without seeing the actual sweep
flows for each (Account → Strongbox, Purse-on-device → Strongbox,
Strongbox → anywhere, Vault → anywhere), the warning categories
will be either over-specified or wrong.

**Direction to keep in mind for the brainstorm:**

- The locked discipline is **warn don't block** — the validator
  makes sure the user knows what they're doing; it does not
  second-guess.
- Two patterns Rémy named worth designing against: *saving while
  working* (income → Account → auto-sweep → Strongbox; Strongbox
  → Purse top-up) and *spending while retiring* (Strongbox →
  Account → manual sell). The validator shouldn't treat one as
  more legitimate than the other.
- A potential third pattern: *static address reuse for recurring
  payments* (rent recipient, family, etc.) — a banking-IBAN
  analogue. Touches `future_iterations.md` "Receive in static /
  merchant mode" and "Contact book / saved counterparties".
  Worth thinking about whether sweep-policy destinations should
  be addresses-not-Holdings for those flows.

**Decision:** ___ (pending session after four-Holding scaffold)
**Decided on:** ___

---

### `purse-upgrade-path`

**Status:** open (sharpened 2026-05-13 during the Purse-wizard
design pass; resolution feeds the next Purse-detail iteration
and informs the Capacitor-wrap iteration)

**Item:** When a Purse is added watch-only
(`purse_mode=WATCH_ONLY`, the user pasted a descriptor
from another wallet), can the user later add the seed phrase /
master xprv from that same source wallet to TallyKeep to make
this existing Purse spendable from TallyKeep? Or is "spending
from TallyKeep" only available by creating a fresh, separate
`ON_DEVICE_TK_GENERATED` Purse and migrating funds?

The domain already reserves the third mode for this:
**`ON_DEVICE_USER_IMPORTED`** — TallyKeep holds the spending key
(stored in Capacitor secure storage on a specific device, same
mechanic as `ON_DEVICE_TK_GENERATED`) but **TallyKeep is not the
original creator of the seed**. The user already has a backup
elsewhere (from the source wallet); the disclosure copy and
the security-health surface differ accordingly.

**Why this matters now.** Surfaced during the Purse-wizard
brainstorm 2026-05-13. Rémy's framing: "if a user wants to
load their Mutiny / Phoenix seed into TallyKeep to keep
spending after the source wallet's service degrades, that
should work — it's even better for the brand." The wizard
deliberately ships watch-only-only on step 1 (paste descriptor)
plus generate-only on step 1's alt path; the seed-import path
lives elsewhere because it doesn't fit "add Purse" — it fits
"upgrade an existing watch-only Purse to spendable."

**Leading direction:** the affordance lives on the **Purse
Detail page**, not in the Add wizard. Watch-only Purses surface
a discoverable but greyed-out Send control on their detail
page; tapping it presents the upgrade flow ("Add the keys to
this Purse so you can spend from TallyKeep"). That flow is its
own micro-iteration with:

- A textarea accepting BIP39 mnemonic (12 / 24 words) or master
  xprv. Inline validation against the wallet whose descriptor
  is already imported — refuses pastes that don't derive to the
  same descriptor.
- Capacitor-only at ship; browser-fallback gating per ADR-0007
  (the DEV MODE localStorage stub from the Purse-wizard
  iteration is reusable here).
- Disclosure copy specific to the imported-seed case:
  "TallyKeep now stores a copy of these keys on this device.
  You already have a backup from where you exported the seed —
  keep it safe. Spending from both apps on the same wallet
  without coordinating can cause failed broadcasts (the
  protocol prevents double-spend; the UX gets confusing)."
- Security-health surface registers the imported Purse with
  copy distinct from generated Purses (no "TallyKeep gave you
  this seed" framing — the user got it elsewhere).

**Open part — full session needed:**

- Domain model: is `purse_mode` a mutable field (a watch-only
  Purse becomes `ON_DEVICE_USER_IMPORTED` on upgrade)? Or do we
  preserve the original mode and add a separate
  `spending_capability` flag on the Holding? ADR-0006
  preceded this discussion; revisit.
- Disclosure copy lockstep with `seed-backup-disclosure`
  — the imported-seed case is a meaningful variant.
- Double-spend UX disclosure — text + when it surfaces (only
  at upgrade time, or also at first Send on an imported
  wallet?).
- Capacitor gate posture: is the upgrade affordance hidden
  in the browser build (gauntlet 5 absence-of-affordance) or
  shown-with-banner (gauntlet 5 honest gate)? Probably the
  former — the localStorage stub is acceptable for
  Rémy-only personal-shipping but not the right shape for a
  user-facing affordance.

**Why this is preferable to baking the upgrade into the Add
wizard:** the wizard's job is registering a new Purse. The
upgrade is a transformation of an existing Purse. Different
verbs, different mental model, different navigational entry
point ("I'm here on this Purse's page" vs. "I'm here adding a
Holding"). Forcing both verbs through the same wizard would
either (a) make the wizard's step 1 a three-way fork (paste
descriptor / paste seed / generate), which fragments the
"name + source" step 3 because the source semantics differ
across modes, or (b) require a fourth step asking "are you
upgrading or registering?", which is a bizarre question to
the user.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `seed-backup-disclosure`

**Status:** open (leading direction; full session pending to
specify the security-health system)

**Item:** When the Capacitor build generates an on-device Purse
seed, how is the user warned about backup responsibility? Phone
loss + no seed backup = funds gone.

**Leading direction (Rémy):** Generate the seed; show it to the
user; show a strong warning explaining the loss-of-funds
consequence; attach a persistent warning to the home page or
security-health section that stays visible until the user
explicitly checks "I backed up my keys safely, I understand the
consequences."

This persistent warning lives in a broader **security-health
system** (user-visible heading on Home: "Security health")
alongside other persistent items:

- Privacy / Blueprint warnings (address reuse, etc.)
- Strongbox frequent-usage warning (large amounts on a Strongbox
  used for daily spending)
- Vault declared-vs-observable mismatch
- Hosted-tier privacy-boundary acknowledgment
- Principles acknowledgment not yet given — surfaces here if the
  user reached Home without clicking `[I understand]` on the
  Onboarding 01 Connect screen's principles card. Item copy
  invites the user to re-read the principles (open source / no
  accounts / your keys stay yours) and acknowledge. Per
  `UI/mobile.md` Onboarding Notes.

**Why this is preferable to a hard gate:** the hard gate forces
the user to act at an inconvenient moment (just generated the
seed, hasn't yet opened the password manager / safe / paper-backup
process). The persistent-warning model lets the user dismiss the
modal but does not let them forget. It is also more honest — it
admits the responsibility is ongoing, not a one-time confirmation.

**Open part — full session needed:**

- Specify the security-health system (what items, what severity,
  what presentation).
- Define the warning-acknowledgment lifecycle (checkbox only, or
  some periodic re-confirm?).
- Decide where on home page / settings / dedicated tab the
  security-health view lives.
- Wording of the warning at seed-generation time.

The security-health system is also captured in
`future_iterations.md` as a feature item, since several items
contribute to it.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `multi-asset-aggregation`

**Status:** open

**Item:** The "no multi-asset" line in the canonical out-of-scope
list rejects custody of stablecoins, Monero, and non-Bitcoin
chains — that part is firm and tied to regulatory surface. But
Account aggregation is read-only: TallyKeep observes balances at
connected providers, never holds keys, never moves non-BTC funds.
Pulling read-only USDT, USDC, or other balances at the same
connected exchanges is structurally identical to BTC Account
aggregation. The question: should TallyKeep surface non-BTC
balances on connected Accounts in the aggregated view?

**Why this matters now.** The target markets (Argentina
especially) hold significant value in stablecoins as an inflation
hedge. A sovereignty-minded user with both BTC and USDT at Lemon,
Buenbit, or Belo currently has to look in two places to see their
full exchange-side picture. TallyKeep's banking-ergonomics premise
loses some of its bite if the consolidated view stops at the BTC
line.

**Tensions.**

- **Honest abstraction.** If we surface non-BTC balances, the
  home page's "Total: 0.52 BTC" becomes ambiguous — does it
  include the USDT? If it does, in what unit and at what rate? If
  it doesn't, the user has to do the math themselves.
- **Vocabulary.** TallyKeep's locked vocabulary (Holdings,
  Account, Purse, Strongbox, Vault) is BTC-centric. Multi-asset
  Holdings would either fragment the vocabulary or force a new
  "asset" axis on every Holding type.
- **Custodial-only.** Non-BTC aggregation is *only* possible at
  the Account level — Purse / Strongbox / Vault don't apply
  outside of Bitcoin. So the asymmetry is structurally enforced,
  but the home page may need to acknowledge it.
- **Scope creep.** Once we surface non-BTC balances, requests for
  "let me move USDT through TallyKeep too" become predictable.
  The no-custody line stays firm regardless, but the UX pressure
  compounds.
- **Regulatory.** Read-only aggregation does not trigger custody
  or money-transmitter regimes. The line stays clean as long as
  we never quote, route, swap, or hold non-BTC value.

**Possible shapes (for discussion, not decision).**

1. *BTC-only view stays the home, non-BTC available on Account
   detail page only.* Aggregated total is a clean BTC number; the
   user sees their stablecoin exposure when they tap into the
   Account. Honest about the BTC-centric design without losing
   the information.
2. *Multi-currency consolidated total, BTC primary.* Home shows
   BTC plus a secondary "+ $X stablecoins at Lemon" line.
   Surface, not merge.
3. *Reject — stay strict BTC-only.* Maintains vocabulary purity
   at the cost of practical visibility for the target market.

**Leading direction:** None yet. Rémy explicitly opened the
question during the consolidation merge after pushing back on a
proposed ADR that would have locked the rejection.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `pairing-handshake-crypto`

**Status:** open (sharpens at private-ship gate)

**Item:** When the mobile client scans a QR generated by the user's
TallyKeep stack to pair, what does the QR carry and what crypto secures
the handshake? Plain bearer token + endpoint URL is the simple
baseline; PAKE/Noise-style ephemeral-key handshake is the robust
alternative.

**Leading direction (Rémy + Claude, sharpened during onboarding-screen
session 2026-05):** plain endpoint URL + single-use ephemeral pairing
token (~60 second TTL, displayed by the desktop, redeemed once over
TLS or local-network HTTP). Phone POSTs the token to the endpoint;
backend validates and returns a long-lived per-device credential. The
phone stores that credential in its Keychain/Keystore
(biometric-protected). Per-device credentials are revocable from the
desktop's "Paired devices" list.

**Why this direction (and what it gives up):** matches the WhatsApp
Web / Signal device-link pattern users already understand. The
"QR display = proof of possession" argument makes the adversary
model small — physical access to the desktop is required to scan
the QR, and the same-LAN constraint per `01_architecture.md`
§"Network security posture" narrows the window further. PAKE/Noise
add ceremonial cost (mutual-auth handshake, ephemeral key
generation, replay protection) for a threat largely mitigated by
the deployment posture. Worth revisiting if remote pairing (post
`Remote access for self-hosters` in `future_iterations.md`) lands
and the same-LAN constraint goes away.

**Open part — full session needed:**

- Token format (UUID? base32 + checksum? something more compact for
  QR density?), TTL precise value, single-use vs N-use, server-side
  rate limit on pairing attempts.
- Per-device credential format (opaque bearer? signed JWT?).
  Rotation policy.
- Revocation UX on the desktop side ("Paired devices" list with
  last-seen timestamps and "Forget this device" affordance).
- Confirmation UX after a successful pair (does the desktop show
  "phone paired at HH:MM" so the user can verify they're the one
  who scanned?).
- Whether an additional confirmation step on the desktop ("approve
  pairing from phone XYZ?") is worth the friction, or if QR
  possession alone is enough.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `brand-canvas-vs-narrative-split`

**Status:** open (deferred — depends on palette stabilising)

**Item:** PROCESS.md §2.4 currently bundles narrative and live data
into a single lock-doc per brand artifact. During the May 2026
palette iteration sweep, this surfaced as friction: editing tokens
to find the right palette was easier in `tokens.css` than in the
lock docs, because the lock docs interleave hex values with prose,
anatomy, decisions log, and geometry.

A new artifact was introduced as the iteration view:
`brand/tallykeep_palette_canvas.html`. It links `tokens.css`
directly, inlines the wordmark/icon SVGs with `.mark-*` class
hooks, and shows the full brand surface (mark sizes, wordmark
variants, primary palette, surfaces, text, borders, semantic
states, holding accents, dark-mode placeholder, visible tensions).
Zero prose, zero duplication.

The existing lock docs
(`tallykeep_brand_mark_v1_lock.html`,
`tallykeep_wordmark_v1_lock.html`,
`tallykeep_palette_v1_superseded.html`,
`tallykeep_palette_v2_lock.html`) remain unchanged for now.

**Leading direction:** once the palette stabilises (verdigris UI
on cool-white surfaces + olive-tan aged-tally mark looks like the
direction as of 2026-05), file an ADR formalising the
canvas-vs-narrative split:

- Canvas (`tallykeep_palette_canvas.html`) is the live data view;
  consumed by mockups and (later) frontend code via `tokens.css`.
- Lock docs become narrative + anatomy + decisions log only —
  prose about why the brand is what it is, without re-stating
  the data. They reference the canvas for "what does it look like
  right now".
- New brand-artifact pattern: each canonical artifact (mark,
  wordmark, future lockup) gets a markdown narrative doc; the
  canvas is the cross-artifact data view.

**Why deferred:** premature to restructure while the palette is
still in flux. If the verdigris direction reverses or shifts, the
restructure work would partly redo itself. Lock-step the ADR with
the brand v1 → v2 bump if/when verdigris-on-cool is adopted.

**Open part — full session needed:**

- ADR copy: rules for what goes in canvas vs. narrative.
- Migration plan for the four existing v1 lock docs (rewrite as
  narrative-only, or keep as v1 historical and start fresh
  narrative for v2).
- Identity SVG question (`brand/identity/*.svg` currently hardcode
  Aged Oak; only inline SVGs with class hooks follow tokens.css).
  Decision: rewrite identity SVGs to use class-based fills (more
  flexible, requires consumers to inline rather than `<img>`), or
  keep hex-baked and regenerate per brand version (matches §2.4
  lockstep more cleanly).
- Whether the canvas should additionally expose non-color tokens
  (type, spacing, radius, shadow) in v2.

**Recommendation:** keep the canvas + lock docs coexisting until
brand v2 ships; do the restructure ADR as part of the brand v1 →
v2 bump iteration. Do not redo the canvas-vs-lock-doc split as a
standalone iteration — fold it into a "brand stabilises" iteration.

**Decision:** ___ (pending session, blocked by palette adoption)
**Decided on:** ___

---

### `browser-pwa-auth-model`

**Status:** open (must resolve before the Capacitor-mobile-wrapper
iteration finishes; private-ship-event blocker per ADR-0003)

**Item:** ADR-0007 establishes browser-first development with
NativeBridge stubs and the "honest gates" principle ("the browser
does not pretend to have capabilities it doesn't"). But the
long-term auth model for the shipped browser PWA isn't fully
specified. Current dev-mode practice: the NativeBridge browser
branch implements `secureStorage` via a `localStorage` fallback so
pairing + device-credential persistence + unlock flow can be
iterated against in browser without a Capacitor build. **This is
a dev crutch, not a shipped behavior** — `localStorage` is not a
secure store, browsers do not have Keychain. The Capacitor-wrap
iteration must remove this crutch and replace the browser branch
with the long-term model. This item is what that long-term model
needs to be.

**Leading direction (Claude + Rémy, sharpened during
onboarding-implementation feedback 2026-05-10):** browser PWA is a
**per-session client**, not a paired device. Concretely:

- No pairing concept in browser PWA. The Connect / Paired
  onboarding screens are Capacitor-only flows. Browser PWA does
  not show them.
- No persistent device credential. No biometric. (Browser cannot
  reliably integrate with platform biometric; WebAuthn is its own
  separate decision.)
- Each session: user enters the **server passphrase** at app
  open → backend validates via the existing
  `passphrase-validate` endpoint → backend issues a
  **short-lived session token** held in browser memory only.
  Token expires when the tab closes or its TTL elapses; next
  visit, user re-authenticates.
- Browser PWA's entry screen is a simplified
  "Enter server URL + passphrase" form, not the Connect → Paired
  flow.
- All other flows (Home, Holding detail, Activity, etc.) work
  the same as Capacitor against the same backend, authenticated
  via the session token instead of the long-lived device
  credential. Read-only operations are full-functional; write
  operations that require signing (PSBT signing for Strongbox /
  Vault, TallyKeep-managed Purse spends) remain Capacitor-only
  per ADR-0006 / ADR-0007 gating.

**Why this needs arbitration before the Capacitor-wrap iteration
finishes:**

- The Capacitor-wrap iteration swaps NativeBridge stubs for real
  implementations on the Capacitor side. The browser branch must
  also change, but to **what** depends on this decision.
- If per-session-passphrase-login is the model, the browser
  PWA's onboarding flow diverges from Capacitor's. Routing logic
  in the SvelteKit build needs to know which client it's serving
  and gate the Connect / Paired screens accordingly.
- If we hard-gate the browser PWA out of secure operations
  entirely (read-only viewing or nothing), the model is simpler
  but the browser PWA becomes a very narrow surface — probably
  too narrow for the LatAm/Africa target market that includes
  users without a Capacitor-app distribution path.

**Open part — full session needed:**

- Confirm per-session-passphrase-login as the model, or consider
  stronger gates (read-only browser PWA; no-browser-PWA-at-all
  hardening; WebAuthn as a complementary mechanism).
- Session token format + TTL + refresh policy.
- Cross-cutting impact on `UI/README.md` flow inventory: which
  flows are full-functional in browser PWA vs Capacitor-only? A
  comprehensive matrix would help future-iteration scoping.
- Coding-side hygiene: the dev-mode `localStorage` fallback in
  the current iteration's NativeBridge implementation must
  carry a `// TODO(browser-pwa-auth-model)` comment so this
  slug is back-referenced from code. The Capacitor-wrap
  iteration grep-audits these TODOs as part of its cleanup.

**Decision:** ___ (pending session)
**Decided on:** ___

---

## Migration log (one-time, 2026-05)

The previous "Decided" section of this file is removed under the
single-source-of-truth rule. Items closed during the consolidation
merge migrated as follows:

| Slug | Migrated to | Note |
|---|---|---|
| `api-surface-canonical-source` | [ADR-0004](decisions/0004-api-as-contract.md) | Foundational |
| `profile-presets-vs-contextual` | [ADR-0005](decisions/0005-feature-flags-replace-presets.md) | Foundational |
| `purse-flavors` | [ADR-0006](decisions/0006-purse-seed-origin.md) | Foundational |
| `browser-vs-capacitor-fine-tuning` | [ADR-0007](decisions/0007-browser-first-with-nativebridge.md) | Foundational |
| `native-secp256k1-signing` | [ADR-0003](decisions/0003-personal-use-phase.md) §"What relaxes during the personal-use phase" | Captured by the phase model |
| `brand-tokens-placeholder` | `brand/README.md` and brand v1 lock docs | Brand v1 is now locked; the placeholder phase is over |
| `mobile-spec-authoring-path` | `PROCESS.md §6` working agreement, `UI/mobile.md` status section | Process choice |
| `psbt-by-qr-mobile` | `future_iterations.md` "PSBT-by-QR roundtrip on mobile" | Deferred; no foundational decision |
| `categorization-queue-mobile` | `UI/README.md` Activity section, `future_iterations.md` "Push-driven categorization workflow" | Decided + deferred parts each found their canonical home |

Slugs are preserved by the receiving ADR's "Migrated from" header
so existing back-references in canonical docs still resolve.

This log is one-time. Future closed items leave the file directly;
no log accumulates.
