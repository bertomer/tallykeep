# Pre-implementation arbitration

Items requiring a dedicated arbitration session before they can be
folded into `next_iteration.md`. Different tone (Rémy's decision, with
reasoning), different autonomy (no coding agent should guess these).

Each has a recommendation. Rémy decides, dates, and moves resolved
items to the "Decided" section.

When an item is decided:

- Foundational decisions get an ADR in `decisions/`.
- Implementation work moves to `next_iteration.md` (if it affects the
  active iteration) or `future_iterations.md` (if not).
- The relevant canonical doc is edited to reflect the decision.

## Item identifier convention

Items are identified by **stable slugs**, not letters. Slugs do not
get reassigned when items are added or removed. References from
canonical specs (`per pre-implementation item \`purse-flavors\``) stay
correct as the file evolves.

Format per item: status, item, recommendation, reasoning, decision slot.

---

## Open

### `seed-backup-disclosure`

**Status:** open (leading direction; full session pending to specify
the security-health system)

**Item:** When the Capacitor build generates an on-device Purse seed,
how is the user warned about backup responsibility? Phone loss + no
seed backup = funds gone.

**Leading direction (Rémy):** Generate the seed; show it to the
user; show a strong warning explaining the loss-of-funds consequence;
attach a persistent warning to the home page or security-health
section that stays visible until the user explicitly checks "I backed
up my keys safely, I understand the consequences."

This persistent warning lives in a broader **security-health system**
alongside other persistent warnings:

- Privacy / Blueprint warnings (address reuse, etc.)
- Strongbox frequent-usage warning (large amounts on a Strongbox
  used for daily spending)
- Vault declared-vs-observable mismatch
- Hosted-tier privacy-boundary acknowledgment

**Why this is preferable to a hard gate:** the hard gate forces the
user to act at an inconvenient moment (just generated the seed, hasn't
yet opened the password manager / safe / paper-backup process). The
persistent-warning model lets the user dismiss the modal but does not
let them forget. It is also more honest — it admits the responsibility
is ongoing, not a one-time confirmation.

**Open part — full session needed:**

- Specify the security-health system (what items, what severity, what
  presentation).
- Define the warning-acknowledgment lifecycle (checkbox only, or some
  periodic re-confirm?).
- Decide where on home page / settings / dedicated tab the
  security-health view lives.
- Wording of the warning at seed-generation time.

The security-health system is also captured in `future_iterations.md`
as a feature item, since several items contribute to it.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `multi-asset-aggregation`

**Status:** open

**Item:** The "no multi-asset" line in the canonical out-of-scope
list rejects custody of stablecoins, Monero, and non-Bitcoin chains —
that part is firm and tied to regulatory surface. But Account
aggregation is read-only: TallyKeep observes balances at connected
providers, never holds keys, never moves non-BTC funds. Pulling
read-only USDT, USDC, or other balances at the same connected
exchanges is structurally identical to BTC Account aggregation. The
question: should TallyKeep surface non-BTC balances on connected
Accounts in the aggregated view?

**Why this matters now.** The target markets (Argentina especially)
hold significant value in stablecoins as an inflation hedge. A
sovereignty-minded user with both BTC and USDT at Lemon, Buenbit, or
Belo currently has to look in two places to see their full
exchange-side picture. TallyKeep's banking-ergonomics premise loses
some of its bite if the consolidated view stops at the BTC line.

**Tensions.**

- **Honest abstraction.** If we surface non-BTC balances, the home
  page's "Total: 0.52 BTC" becomes ambiguous — does it include the
  USDT? If it does, in what unit and at what rate? If it doesn't,
  the user has to do the math themselves.
- **Vocabulary.** TallyKeep's locked vocabulary (Holdings, Account,
  Purse, Strongbox, Vault) is BTC-centric. Multi-asset Holdings
  would either fragment the vocabulary or force a new "asset" axis
  on every Holding type.
- **Custodial-only.** Non-BTC aggregation is *only* possible at the
  Account level — Purse / Strongbox / Vault don't apply outside of
  Bitcoin. So the asymmetry is structurally enforced, but the home
  page may need to acknowledge it.
- **Scope creep.** Once we surface non-BTC balances, requests for
  "let me move USDT through TallyKeep too" become predictable. The
  no-custody line stays firm regardless, but the UX pressure
  compounds.
- **Regulatory.** Read-only aggregation does not trigger custody or
  money-transmitter regimes. The line stays clean as long as we
  never quote, route, swap, or hold non-BTC value.

**Possible shapes (for discussion, not decision).**

1. *BTC-only view stays the home, non-BTC available on Account
   detail page only.* Aggregated total is a clean BTC number; the
   user sees their stablecoin exposure when they tap into the
   Account. Honest about the BTC-centric design without losing the
   information.
2. *Multi-currency consolidated total, BTC primary.* Home shows BTC
   plus a secondary "+ $X stablecoins at Lemon" line. Surface, not
   merge.
3. *Reject — stay strict BTC-only.* Maintains vocabulary purity at
   the cost of practical visibility for the target market.

**Leading direction:** None yet. Rémy explicitly opened the question
during the consolidation merge after pushing back on a proposed ADR
that would have locked the rejection.

**Decision:** ___ (pending session)
**Decided on:** ___

---

## Decided

### `api-surface-canonical-source`

**Decided:** 2026-05. Option 1 — retire module 04 to a thin
conventions doc.

**Rationale:** parallel hand-written endpoint listings duplicate the
OpenAPI surface and rot silently — exactly the failure mode the
consolidation merge was supposed to end.

**Resolution:**

- `04_api_surface.md` archived to `archive/04_api_surface.md`.
- Replaced by `04_api_conventions.md`: cross-cutting rules only
  (auth posture, error format, pagination, idempotency, locked
  state, SSE stream pattern, async-job pattern, URI versioning).
- `api/openapi.yaml` is the source of truth for endpoint shapes
  (paths, methods, request/response schemas).
- `PROCESS.md` §2.2 sharpened: any iteration whose code touches
  endpoints, schemas, SSE events, error types, or locked-state
  behavior **must** regenerate `api/openapi.yaml` as part of the
  iteration's acceptance. Drift is a bug, not a chore.
- `00_README.md` module map row 04 updated.

---

### `profile-presets-vs-contextual`

**Decided:** 2026-05. Drop the named presets entirely. Replace with
onboarding-question-driven feature-flag defaults — the user never
identifies as a tier; the configuration is just the configuration.

**Rationale:** named presets compress independent dimensions
(expertise, assets-under-self-custody, anticipated usage,
information-density preference) into a single label that fits
nobody well. "Beginner" reads as deficient-to-be-overcome;
"Sovereign" carries ideological framing. The "banking ergonomics"
positioning makes user-tier identity an actively wrong abstraction.

**Resolution:**

- `02_domain_model.md` `UserProfile` no longer has `preset` or
  `ProfilePreset`. The class has `feature_flags`, `base_currency`,
  `locale` only.
- `03_data_model.md` `user_profile` table no longer has the
  `preset` column.
- Module 09 renamed `09_profiles_and_flags.md` →
  `09_feature_flags.md` and rewritten end-to-end:
  - Flag catalog (no preset columns).
  - Onboarding-question-driven default seeding (architectural
    contract; specific question wording is UX-iteration design).
  - `DEFAULT_FLAG_VALUES` fallback if onboarding is skipped.
  - Flag resolution: lookup-with-fallback, no preset layer.
- `00_README.md` "Currently in scope" updated.
- Per-flag references in modules 05/06/07 updated to drop
  Beginner/Intermediate/Sovereign mentions; new flag
  `banking.coin_selection_per_payment_override` introduced for
  what was previously "Sovereign-profile per-payment override."
- Backend delta tracked in `next_iteration.md`
  (drop `preset` field from API and DB; regenerate OpenAPI).

---

### `purse-flavors`

**Status:** Resolved — architecture and UX-per-origin decided;
specific gating copy deferred to the send-flow mockup session (design
decision, not arbitration).

**Item:** What is the Purse type's architecture given that browser
builds cannot hold spending keys, and what is the operational UX
when the same backend is reached from multiple devices with different
local capabilities?

**Architectural resolution (2026-05, refined 2026-05).** The Purse
type has a `seed_origin` field with two values, capturing the
**intent** of the wallet at creation. Where the seed actually lives
is **not** a domain field — it is per-client runtime state.

- **External-watch-only** (`seed_origin=external_watch_only`).
  Onboarded via **xpub or descriptor only**. Single-address import
  is not supported (a wallet's activity rotates across many
  addresses; observing one address shows a misleading slice). Source
  of keys is in another hot wallet (Phoenix, BlueWallet, Mutiny,
  Sparrow's hot mode, etc.). Available on any client; spending
  always points back to the source wallet.
- **TallyKeep-managed** (`seed_origin=tallykeep_managed`). TallyKeep
  generates a fresh seed during Add-Holding and stores it in **the
  current client device's secure local storage** (iOS Keychain /
  Android Keystore on Capacitor; biometric-gated). The descriptor
  derived from that seed is registered with the backend; the seed
  itself never crosses to the backend. From any other client
  reaching the same backend, the same Holding appears as view-only
  with a "go sign on the device that holds the seed" gate.

**Critical architectural point — do not regress:** the backend
**never** holds a reference to the seed, encrypted or otherwise.
There is no `on_device_seed_reference` field, no flavor distinction
encoded as where-the-seed-lives. The locked principle "no signing
keys to backend" is preserved.

**Per-client signing-capability check.** Whether a given client can
sign for a TallyKeep-managed Purse is a runtime question, answered
locally by checking that client's secure-storage backend for an
entry keyed by the Holding's `id`. The check has three outcomes:

- *Capacitor on the device that generated (or restored) the seed:*
  entry present → Send is enabled, biometric, sign in-app, broadcast.
- *Capacitor on a different device (or browser PWA on any device):*
  no entry → Send shows the "go sign on the device that holds the
  seed" gate. No PSBT export, no pretend-to-sign.
- *External-watch-only Purse, any client:* always view-only; Send
  always points to the source wallet.

**Affordance gating is client-side, not backend-side.** The
"Create a TallyKeep wallet" option in Add-Holding is shown only on
clients with the capability to generate and securely store a seed
(Capacitor on phone). Browser PWA hides it with a "this requires
the TallyKeep app" message. The backend does **not** validate the
client build type; it accepts any Purse-creation request. The
trade-off is that an attacker calling the API directly could
register a `tallykeep_managed` Purse with no client actually
holding a seed — the result is a Holding nobody can spend from,
which is a UX nuisance, not a security risk.

**Pairing-based PSBT roundtrip between TallyKeep instances** (e.g.,
"send a PSBT from desktop to my paired phone for signing") is
explicitly **not** in current scope. Strict shape now: Send on a
device-without-seed redirects to the device-with-seed and stops
there. Pairing is captured for post-personal-shipping in
`future_iterations.md`.

**Open: specific gating copy.** Exact wording at gates ("Install
the app", "Spend in [wallet]", "Open TallyKeep on the device that
holds this key", deep-link button copy) is a design decision
evaluated alongside the send-flow mockup, not arbitration. Resolved
during the send-flow iteration.

These resolutions are reflected in `02_domain_model.md` §"Purse
seed origin" and §"Signing capability is per-client",
`UI/README.md` (Add-Holding, Send, Receive sections per Holding
type), and the threat model (`10_threat_model.md` §Mobile addendum).

**Decided on:** 2026-05

---

### `native-secp256k1-signing`

**Decided:** 2026-05. Defer native signing to the public-ship event
(see ADR-0003 — Project phases and shipping milestones).

**Rationale:** Per ADR-0003, the project moves through three phases
separated by two events (private-ship, public-ship). JS-side signing
via `@noble/secp256k1` after retrieving from Keychain/Keystore is
acceptable through the personal-use phase — Rémy on his own devices
with small amounts. Native signing is bundled into the ship-gate
work that gates the public-ship event, alongside authentication-layer
hardening, third-party security audit, reproducible builds, and
brand finalization.

The ship-gate meta-iteration is captured in `future_iterations.md`.

---

### `browser-vs-capacitor-fine-tuning`

**Decided:** 2026-05. Yes — build the mobile UI in SvelteKit, run in
browser at mobile viewport against the real backend, stub native
plugins behind a `NativeBridge` interface. Capacitor build, app-store
packaging, and physical-device validation come as a separate phase
after the UI is fine-tuned.

---

### `brand-tokens-placeholder`

**Decided:** 2026-05. Yes — token-system approach with placeholder
values (amber `#f59e0b` primary, slate palette inherited from existing
wireframes). Brand voice and identity decided later (public-ship event)
as a one-file swap.

Tokens seeded in `UI/mockups/_shared/tokens.css`.

---

### `mobile-spec-authoring-path`

**Decided:** 2026-05. Build screen-by-screen alongside the mockups —
each session produces both the mockup and the corresponding section of
`UI/mobile.md`, with the gauntlet answers attached.

**Bonus addition:** A meta visual index at `UI/mockups/index.html`
loads all mockups in a contact-sheet view, to spot drift across
screens (look-and-feel, navigation, conventions). Updated as mockups
land.

---

### `psbt-by-qr-mobile`

**Decided:** 2026-05. Hold for a later iteration. Promoted to
`future_iterations.md` so it can be picked up after the mobile UI is
ready.

---

### `categorization-queue-mobile`

**Decided (partial):** 2026-05.

- **Home / consolidated landing page:** no pending-categorization
  list. Stays minimalist.
- **Activity menu:** stays. That's where the user can see recent
  activity across all holdings and create / manage categories.
- **Per-holding detail page:** shows that holding's transactions, with
  categorization possible there.

**Deferred to future iteration:** richer categorization mechanism —
push notifications / event-driven popups encouraging categorization
when the bitcoin node detects new on-chain activity. Captured in
`future_iterations.md` as "Push-driven categorization workflow."
