# Future iterations

The pot. Ideas captured during brainstorm sessions but flagged as
later. Sharpening happens when an item is promoted to "Next iteration."

Each entry is intentionally rougher than a `next_iteration.md` entry —
just enough to remember the idea, the motivation, and where it came
up. Sharpening is a deliberate session, not done in-pot.

If you're a coding agent reading this: this is reference, not work.
Do not implement from here.

---

## Format

Every entry uses this shape:

```
### <short title>

- Captured: YYYY-MM (session reference if any)
- Motivation: <why this matters>
- Sketch: <broad strokes of what it might look like>
- Touches: <which canonical modules / UI sections / external deps>
- Status: idea | sketched | sharpened-ready-to-promote
- Milestone: pre-shipping | post-shipping | TBD
- Notes: <anything else worth keeping>
```

**Milestone tag.** Per ADR-0003, "v1 / v1.5 / v2 / v3" is dropped
in favor of two events:

- **private-ship event** — Rémy's Capacitor app on his own phone,
  sideloaded, real value at small amounts. No public users.
- **public-ship event** — app stores + brand + audit + reproducible
  builds, for public users.

Items are tagged:

- `pre-shipping` — needed before the public-ship event. May be
  required for the private-ship event specifically (noted in entry)
  or more generally for public-ship.
- `post-shipping` — to land after the public-ship event.
- `TBD` — Rémy hasn't decided yet; my best guess (if any) is in
  the entry's notes.

When an item is promoted to `next_iteration.md`, it can stay here in
a "Promoted" section as a breadcrumb until the iteration ships, then
removed.

---

## Iteration roadmap (rough sketch — not commitment)

For Rémy's mental model, not for the coding agent. Sequence and
scope will adjust as we learn. The roadmap targets the
public-ship event (per ADR-0003); private-ship is reached when
the relevant mobile UI iterations are stable enough and the
Capacitor + auth + security-health work lands.

### Pre-shipping iterations

**Mobile UI design and dev-phase build:**
1. **Onboarding + Home (empty + populated states)** — first-touch
   flow plus landing.
2. **Add Holding** — chooser + four type-specific flows.
3. **Holding Detail** — per-type detail pages.
4. **Send + Receive** — per Holding type, including PSBT
   roundtrip for Strongbox and native sign for TallyKeep-managed
   Purse on the device that holds the seed.
5. **Activity + Categorization** — cross-Holding feed plus
   per-Holding categorization.
6. **Sweep Policy + Treasury view** — Account-originated sweeps
   in the dev-phase scope.
7. **Settings** — including the security-health system at least
   for seed-backup warnings (private-ship gate).

**Private-ship gate:**

- Capacitor wrap + native plugins.
- Authentication layer.
- Security-health (seed-backup recovery flow per
  `pre-implementation.md` item `seed-backup-disclosure`).
- Self-review.

**Pre-public-ship enhancements** (in personal-use phase, before
public-ship):

- Iterations driven by Rémy's own daily-use feedback.
- Possible candidates: settlement-rails confirmation probability,
  "tap to see under the hood" UI spine, others (see entries
  below).

### Public-ship event (ship-gate work bundle)

See "Ship-gate meta-iteration" entry below. Bundles native
signing, reproducible builds, app stores, F-Droid, brand,
third-party audit, and (optionally) hosted-tier launch.

### Post-shipping

Feature updates per the post-shipping entries below (Blueprint,
Lightning, DCA, equity-reference, etc., depending on user
feedback and roadmap priorities).

---

## Promoted

Brief breadcrumbs for iterations whose full entries have moved
to `next_iteration.md`. Removed from this file when the iteration
ships and the next_iteration block becomes a `## Shipped <date>`
record.

### Add Holding — Purse wizard

- **Promoted:** 2026-05-13 (after the design-pass close).
- **Full entry:** see `next_iteration.md` "Active iteration ·
  Add Holding — Purse wizard". 8 validated mockups in
  `UI/mockups/`, `UI/mobile.md` Purse-wizard section locked,
  `pre-implementation.md` `purse-upgrade-path` arbitration
  drafted as the related future-feature breadcrumb.
- **Next in the wizard lineup after this ships:** Strongbox
  wizard (copy + framing variant on the Purse pattern,
  reuses the shared wizard-shell that lands here), then
  Vault wizard, then Account wizard. (Account wizard
  promoted 2026-05-16 — see `next_iteration.md`.)

### Add Holding — Strongbox wizard

- **Promoted:** 2026-05-14 (after the design-pass close —
  Rémy greenlight on all 7 validated mockups).
- **Full entry:** see `next_iteration.md` "Active iteration ·
  Add Holding — Strongbox wizard". 7 validated mockups in
  `UI/mockups/` (input default + two error states + advisory +
  parse-back default + parse-back no-metadata + success);
  `UI/mobile.md` Strongbox-wizard section locked; new
  *advisory* footer-banner shape locked across sibling wizards
  (warning palette, CTA enabled, lighter than redirect-error
  band); a Strongbox-missing-signing-metadata item drafted under
  the security-health entry in this file pending the surface
  framing review Rémy opened 2026-05-14.
- **Next in the wizard lineup after this ships:** Vault wizard
  (framing pre-card + multisig-only validation, then the same
  3-step shape), then Account wizard (different surface, ccxt
  provider integration, no descriptor parser). The Account
  wizard was promoted 2026-05-16 — see `next_iteration.md`.

### Add Holding — Account wizard

- **Promoted:** 2026-05-16 (after the design-pass close — Rémy
  greenlight on all four validated mockups).
- **Full entry:** see `next_iteration.md` "Active iteration ·
  Add Holding — Account wizard". Four validated mockups in
  `UI/mockups/` (the `mobile_add_holding_account_*.html` set:
  connect default, connect overage error, parseback, success);
  `UI/mobile.md` Account-wizard section locked;
  `decisions/0011-account-two-key-model.md` recording the
  foundational shift.
- **Scope shift from the rough sketch:** the v1 list cut from
  {Kraken, Bitstamp} to {Kraken} only (Bitstamp moves to the
  "Additional CustodialProvider adapters" entry above). The
  wizard captures only the read-only credential; the withdrawal
  credential is its own sub-flow ("Account withdrawal-key
  sub-flow" entry below) reachable from Account detail.

---

## Open

### Add Holding — Vault wizard

- **Captured:** 2026-05 (split 2026-05-13, see Purse-wizard
  entry above).
- **Motivation:** Long-term ceremonial multi-key hold. Designed
  as the default destination for auto-sweep policies once the
  SweepPolicy iteration lands. Completes the four-Holding-type
  onboarding surface in dev phase.
- **Sketch:** 5-step wizard. Same parser as Purse / Strongbox
  but with multisig-only validation and a pre-card framing.
    1. *Framing pre-card* — "Vault is for amounts you rarely
       touch — long-term reserve, family savings, future income.
       Several keys are required to move funds. Vault will become
       the default destination for auto-sweeps from your other
       Holdings. Today, you can import the descriptor; spending
       and auto-sweep land in later iterations." Primary CTA:
       "Continue".
    2. *Descriptor input* — multisig only. Bare xpubs and
       single-key descriptors rejected with "Vault requires a
       multisig descriptor — `wsh(multi(...))` or similar."
    3. *Parse-back* — M-of-N, co-signer count, any timelocks
       present, first three derived addresses.
    4. *Label* — default suggestion "My Vault".
    5. *Success* — "Vault is set up. Spending ceremony and the
       auto-sweep destination feature ship in later iterations."
  Reuses the shared wizard shell.
- **Touches:** `UI/mobile.md` Add-Holding Vault section, five new
  mockup files, frontend wizard implementation. Backend already
  shipped. No new shell or bridge work.
- **Status:** sharpened-ready-to-promote
- **Milestone:** pre-shipping
- **Notes:** Promote **third**. Vault's framing pre-card is the
  key design difference from Purse / Strongbox; the rest of the
  wizard reuses the pattern. Operational features (signing
  ceremony, blueprint analysis, declared-vs-observable mismatch
  warnings) stay deferred to the Vault-detail iteration.

### Descriptor → Holding-type classification cleanup

- **Captured:** 2026-05-15 (surfaced by the coding agent during
  the Vault-wizard iteration; Rémy flagged the same friction
  from his own read of the wizard codebase).
- **Motivation:** The "given this descriptor, which Holding type
  does it belong to?" decision is currently scattered. Some
  classification runs in the backend (`descriptor-validate`
  endpoint, structural-shape checks per `next_iteration.md`
  Task 1), some in the frontend wizards (per-wizard accept-set
  filters, bare-xpub auto-wrap, single-address rejection, redirect
  routing). Logic is in places duplicated across wizards, in
  places sharedly imported, in places re-implemented inline. The
  coding agent reported this as "non-trivial" and a source of
  drift when wizards' accept sets evolve. The Vault wizard
  iteration added a third copy of the routing-error branching;
  the Send-from-Account flow and the Purse upgrade path will
  each touch the same decision surface again.
- **Sketch:** Single backend endpoint — *"guess best Holding fit"*
  (working name; e.g. `POST /api/v1/descriptors/classify` or a
  shape extension of the existing `descriptor-validate`) — that
  takes a pasted descriptor (or bare xpub) and returns a tagged
  outcome:
    - `best_fit: "purse" | "strongbox" | "vault" | null`
    - the parser metadata already produced today
      (`script_type`, `derivation_path`, `key_fingerprints`,
      `required_signers`, `total_signers`, `timelock_kind`,
      `timelock_value`, `signing_metadata_present`, …)
    - rejection category when nothing fits
      (`single_address_input`, `unsupported_form`,
      `unparseable`).
  Frontend wizards become **thin**: each wizard calls the
  endpoint on paste / parse, compares `best_fit` to its own
  type — match ⇒ continue to parseback; mismatch ⇒ redirect
  popup to the correct wizard (single redirect-error pattern,
  not three); `null` ⇒ inline unsupported-form error. The
  per-wizard "is this descriptor for me?" branching disappears.
  Bare-xpub auto-wrap, single-address rejection, miniscript
  fragment detection — all collapse into the backend endpoint
  and become testable in one place. The classification rules
  in `next_iteration.md §Vault wizard Task 1` (structurally
  aware: `or_i` / `or_d` / `thresh()` / hash fragments route
  to `unsupported_form` regardless of timelock presence) become
  the spec for this endpoint, not three wizards' worth of
  parallel implementations.
- **Touches:** `concerns/observation.md` or a new
  concerns/classification.md module; `04_api_conventions.md` if a new
  endpoint family is introduced; backend descriptor parser
  (consolidates today's `descriptor-validate` + per-type
  `Holding-create` validation into one classification surface);
  three wizard frontend implementations (Purse / Strongbox /
  Vault) get slimmer; `api/openapi.yaml` regenerates.
- **Status:** idea
- **Milestone:** pre-shipping (post-Vault-wizard, before the
  Send / Receive iteration touches the same surface from the
  Account side)
- **Notes:** Worth pairing with a janitorial pass that grep-audits
  the frontend for inline descriptor parsing / classification
  logic and replaces each site with a call to the endpoint. The
  audit is part of the iteration's acceptance — "no caller in
  the frontend computes Holding-type fit from descriptor shape
  itself; all fit decisions come from the endpoint." Worth doing
  before the Purse upgrade path ships because that flow re-uses
  the same classification (an imported seed-or-xprv must still
  classify as Purse, not as a different type). If we add it
  after, we eat the cost twice.

### Purse upgrade path (watch-only → on-device-imported)

- **Captured:** 2026-05-13 (Purse-wizard design pass; sharpened
  out of the original `pre-implementation.md` `purse-upgrade-path`
  entry on 2026-05-14 once the design parts stabilised)
- **Motivation:** When a `WATCH_ONLY` Purse becomes degraded —
  source wallet shutting down (Mutiny), service deprecating
  (Phoenix on some platforms), or the user just wants to spend
  from TallyKeep — let the user import the source wallet's seed
  so the *same* Purse becomes spendable. Better for the brand
  than forcing a fresh `ON_DEVICE_TK_GENERATED` Purse + funds
  migration.
- **Sketch:**
    - **Where it lives.** Affordance on the **Purse Detail
      page**, not in the Add wizard. Watch-only Purses surface
      a discoverable but greyed-out Send control; tapping
      presents the upgrade flow ("Add the keys to this Purse
      so you can spend from TallyKeep"). The wizard's job is
      *registering* a new Purse; the upgrade is *transforming*
      an existing one. Forcing both verbs through the same
      wizard would either fork step 1 three ways or require a
      bizarre "are you upgrading or registering?" step.
    - **Input.** Textarea accepting BIP39 mnemonic (12 / 24
      words) or master xprv. Inline validation against the
      wallet whose descriptor is already imported — refuses
      pastes that don't derive to the same descriptor.
    - **Capacitor-only at ship**, with browser-fallback gating
      per ADR-0007. The dev-mode `localStorage` stub from the
      Purse-wizard iteration is acceptable for Rémy-only
      personal-shipping but not the right shape for a
      user-facing affordance.
    - **Disclosure copy** (imported-seed case): *"TallyKeep
      now stores a copy of these keys on this device. You
      already have a backup from where you exported the seed
      — keep it safe. Spending from both apps on the same
      wallet without coordinating can cause failed broadcasts
      (the protocol prevents double-spend; the UX gets
      confusing)."*
    - **Security-health surface** registers the imported Purse
      with copy distinct from generated Purses (no "TallyKeep
      gave you this seed" framing — the user got it
      elsewhere).
- **Touches:** `holdings/02_purse.md` (Add-Holding —
  `ON_DEVICE_USER_IMPORTED` section), `UI/mobile.md` Purse
  Detail section, `concerns/threat_model.md` Mobile addendum,
  Capacitor NativeBridge `secureStorage` write path,
  `seed-backup-disclosure` security-health item lockstep.
- **Status:** sketched
- **Milestone:** pre-shipping — lands during personal-use
  phase, after Capacitor wrap. Sharpens once
  `pre-implementation.md` `purse-upgrade-path` closes (the
  structural question: mutable `purse_mode` vs separate
  `spending_capability` flag).
- **Open at sharpen time:**
    - Disclosure copy lockstep with `seed-backup-disclosure`
      — the imported-seed variant differs from the
      TallyKeep-generated case.
    - Double-spend UX timing — surface text only at upgrade
      time, or also at first Send on an imported wallet?
    - Capacitor gate posture: hide the upgrade affordance on
      browser builds (gauntlet 5 absence-of-affordance) or
      show with banner (gauntlet 5 honest gate)? Probably the
      former.
- **Notes:** ADR-0006 may need an editorial note or
  amendment recording the `purse_mode` mutability relaxation
  if the structural arbitration goes that way.

### Unlock flow cleanup

- **Captured:** 2026-05 (Rémy, during module 03 review). Surfaced
  by an hour of manual UI testing.
- **Motivation:** The unlock flow has several real bugs and
  unclear semantics that need a dedicated design + implementation
  pass. Rémy's observed symptoms in ~1 hour of testing:
  - Pairing succeeds but passphrase remains locked.
  - Passphrase unlocked but pairing reported as lost.
  - Refreshing the home page with unlocked passphrase redirects to
    the passphrase prompt anyway.
  - Server reboot loses the passphrase but the home page is still
    refreshable (no relock).
  - Passphrase-rotation flow undocumented and unclear how a
    compromised passphrase is rotated.
  - No clear path to set up the server **without a UI** — install
    wizard happens through the web app; CLI-only setup is unclear /
    unsupported.
  - Pairing direction question: should the device-ID flow run the
    other way (server-knows-device, not device-knows-server) to
    avoid needing a desktop / web client during initial setup?
- **Sketch:** Design pass first — state machine for unlock + pair
  with all edge cases (cold boot, mid-session reboot, network
  partition, refresh, passphrase rotation, server-side rotation
  while device is paired). Then implementation pass to fix the
  state-management bugs and add the missing flows (CLI setup,
  passphrase rotation).
- **Touches:** `01_architecture.md` §"Configuration model" + the
  surfaces/trust-zones section; ADR-0008 (passphrase + recovery
  model) likely needs an addendum or supersede entry for any
  decisions taken; `concerns/threat_model.md` Mobile addendum;
  `UI/mobile.md` onboarding screens; possibly the pairing-handshake
  arbitration in `pre-implementation.md`.
- **Status:** sketched
- **Milestone:** pre-shipping — gating concern for the
  personal-use phase. Worth scheduling soon since each daily-use
  test multiplies the friction.
- **Notes:** Sequencing — the design pass is a brainstorm with
  Rémy first (spec-agent work), then iteration to fix the bugs and
  ship the missing surfaces. Probably 2 iterations end-to-end.

### External bitcoind connection (self-hosters)

- **Captured:** 2026-05 (Rémy, module 03 review).
- **Motivation:** Self-hosters who already run a Bitcoin Core
  node shouldn't be forced to run a second `bitcoind` in the
  TallyKeep Docker stack. Today's stack ships its own `bitcoind`
  service; users with an existing node end up with two running.
  This costs disk (pruned or not), bandwidth (two IBDs if
  someone's not careful), and operational complexity.
- **Sketch:** A configuration option in `configuration.toml`
  that points TallyKeep at an external `bitcoind` — RPC host /
  port / cookie / user-password, plus ZMQ endpoints — instead of
  spinning up the Docker-internal one. The Docker Compose file
  needs a profile or override that excludes the internal
  bitcoind service. Onboarding-time check verifies the external
  node has the required RPC methods + ZMQ topics enabled
  (`zmqpubrawblock`, `zmqpubrawtx`, `zmqpubhashblock` — already
  documented in `concerns/observation.md`); if missing, surfaces
  the exact `bitcoin.conf` lines to add and refuses to start
  until they're present.
- **Touches:** `01_architecture.md` service topology (becomes
  optional), `configuration.toml` schema, install guide,
  `concerns/observation.md` "Configuration requirement" section.
- **Status:** sketched
- **Milestone:** pre-shipping (private-ship enabler for
  self-hosters who already run bitcoind; can land anytime once
  Rémy hits the case in his own setup or another self-hoster
  asks for it).
- **Notes:** Hosted-tier users don't touch this — the hosted
  backend manages bitcoind centrally.

### Self-host upgrade mechanism

- **Captured:** 2026-05 (Rémy, module 03 review).
- **Motivation:** When TallyKeep ships a new version, self-hosted
  users need a way to upgrade their stack cleanly — pull new
  Docker images, run Alembic migrations, restart, verify, roll
  back if needed. Today there's no documented upgrade path; an
  agent landing on this question has to invent one.
- **Sketch:**
  - Versioned Docker images (semver, tagged per release).
  - Release notes (changelog) per version, including any manual
    pre-upgrade or post-upgrade steps (e.g. "this version drops
    `feature_flags.holding.*` keys — run the bundled
    migration").
  - A simple upgrade script (`./tk upgrade` or similar) that
    pulls images, runs migrations inside the backend container
    (`alembic upgrade head`), bumps the stack, and runs a
    health-check.
  - Rollback path: pinning to the previous image tag if the
    health-check fails. Database backups before migration are
    user responsibility (documented in install guide).
  - Notification surface: TallyKeep periodically checks GitHub
    releases (or a configurable update channel) and shows the
    user "v0.X.Y available — release notes / changelog link" on
    the home page. Opt-out for users who don't want
    network-checks (config flag).
- **Touches:** release pipeline, install guide, configuration
  model, UI (update notification surface), backend (`/health`
  + version reporting endpoint).
- **Status:** sketched
- **Milestone:** **pre-shipping** for the public-ship event
  alongside signed releases and reproducible builds (per the
  ship-gate meta-iteration).
- **Notes:** App-store builds (Capacitor) have store-managed
  updates; this entry is the self-hosted backend equivalent.
  Hosted-tier users update transparently as the operator pushes
  releases — separate mechanism.

### Onboarding-driven feature-flag picker

- **Captured:** 2026-05 (Rémy, module 03/04 review — flagged
  that the onboarding iteration shipped without the
  feature-flag selection step that the spec assumes seeds
  initial flag values).
- **Motivation:** `concerns/feature_flags.md` describes a small
  set of onboarding questions that seed initial flag values (2–3
  questions, mapping answers to a flag bundle). The onboarding
  iteration (`mobile_onboarding_*`) shipped without those
  questions — the user lands on Home with `DEFAULT_FLAG_VALUES`
  applied, and tunes individual flags from Settings later. The
  spec's "Onboarding UI contract" section is therefore not yet
  implemented.
- **Sketch:** A 2–3 screen onboarding sub-flow inserted between
  the existing paired / biometric / passphrase screens and the
  Home page. Question shape (per `concerns/feature_flags.md`
  "Onboarding-driven defaults"):
  - *Bitcoin holding posture* — exchange, phone wallet, hardware
    wallet, multiple, none yet.
  - *Detail-density preference* — technical details visible by
    default, or surfaced on demand.
  - *Custodial connection* — will the user connect an exchange
    / broker account, or use TallyKeep purely for self-custody.
  - The mapping from answers to flag bundles is implementation
    detail (not domain — refining later doesn't require an ADR).
- **Touches:** `UI/mobile.md` onboarding section, new mockups in
  `UI/mockups/` (`mobile_onboarding_03_questions_*.html`),
  `concerns/feature_flags.md` onboarding-UI-contract section
  becomes implemented rather than aspirational, frontend
  onboarding state machine.
- **Status:** sketched
- **Milestone:** pre-shipping (private-ship). The fact that
  it shipped without these questions is a spec-vs-code gap
  worth closing before the private-ship event.
- **Notes:** Skip-onboarding fallback (per existing spec) means
  this can ship without breaking the current code path —
  questions are additive; if the user skips them, `DEFAULT_FLAG_VALUES`
  apply as today.

### Strongbox geolocation correlation (idea, low priority)

- **Captured:** 2026-05 (Rémy, holdings review — "just an idea
  to brainstorm completely, probably to discard").
- **Motivation:** Strongbox spending requires the user to be
  physically near the hardware wallet to sign. The app could, in
  principle, verify the user's device is near the location
  associated with the Strongbox at signing time and warn if not
  ("you're spending from your Coldcard, but your phone is 500km
  from the address you tagged as its location — is this
  intentional?"). Could catch a remote-control attack scenario.
- **Sketch:**
  - Optional per-Strongbox `expected_location` (lat/lon +
    radius) set by the user during Add-Holding.
  - At PSBT-export time, the Capacitor app reads device location
    (with permission) and compares against the expected
    location.
  - Mismatch → soft warning, "warn don't block" discipline.
- **Touches:** domain (new optional field on Strongbox),
  Capacitor location plugin, send-flow UI.
- **Status:** idea (likely discard)
- **Milestone:** TBD — low priority. Rémy's own framing: "probably
  to discard". Kept here as a breadcrumb so it doesn't resurface
  cold later.
- **Notes:** Privacy implications worth a dedicated session if
  pursued — location data on a Holding row is sensitive. Could
  also be implemented client-only (location never leaves the
  device, comparison happens locally). The "remote-control
  attack" mitigation is the only real value; if that attack
  vector isn't on the threat model's top list, this feature is
  noise. Probably stays as a captured idea unless the threat
  model evolves.

### Lightning — bitcoind sharing with self-hoster

- **Captured:** 2026-05 (Rémy, observation review — flagged
  that Lightning iteration should consider the same
  bring-your-own-bitcoind shape).
- **Motivation:** The Lightning provider options (CoreLightning,
  LND, Phoenix per `concerns/lightning_placeholder.md`) all
  depend on a Bitcoin node. Self-hosters running TallyKeep with
  an external bitcoind should be able to point their Lightning
  daemon at the same node — otherwise we end up recommending
  two parallel Bitcoin nodes for a single user.
- **Sketch:** When the Lightning iteration designs the
  CLN/LND provider configuration, the option to share the
  external bitcoind (per "External bitcoind connection" above)
  is a first-class choice. Phoenix is custodial-mode for the
  LSP-managed channel layer, so it doesn't need a node — that
  case is unchanged.
- **Touches:** Lightning iteration design (when it lands), install
  guide.
- **Status:** captured for the Lightning-iteration design
  session (this entry is just a flag, not a separate iteration).
- **Milestone:** TBD — moves with the Lightning iteration.

### Hosted tier infrastructure

- **Captured:** 2026-05 (from design_decisions.md §11, pre-merge);
  sharpened during onboarding-screen-1 session 2026-05.
- **Motivation:** Phone-only LatAm/Africa users without home labs.
  Primary growth path beyond personal use.
- **Sketch:**
    - **Auth model — connection-ID + passphrase, no email, no
      account.** User declares they want hosted infrastructure;
      system generates an opaque connection-ID; user sets a
      passphrase on their hosted instance (the same server-side
      passphrase that encrypts secrets at rest per
      `01_architecture.md` §"Configuration model" — one passphrase
      per stack). No email, no identity, no KYC. Preserves
      design principle #6 in `00_README.md` ("no accounts in our
      app") cleanly.
    - **Connection-ID format — non-predictable AND memorable.**
      Sharpened during onboarding-screen-2 session 2026-05.
      Favor word-pair-encoded format like `crisp-river-7842` over
      raw UUID. Two requirements: (a) UUID-grade entropy
      (≥128 bits) so it can't be guessed, brute-forced, or
      enumerated; (b) human-handleable so users can write it down,
      type it, read it aloud over a phone call to recover access.
      Reference encoding: WordSafe / Diceware-style pairs of
      adjective + noun + 4-digit suffix. The 4-digit suffix
      preserves entropy when the wordlist is small. EFF short
      wordlist (~1300 words) gives ~10 bits per word; two words
      + 13-bit suffix ≈ 33 bits → not enough alone. Stretch with
      Argon2id-derived authentication or pair the connection-ID
      with the user's passphrase as a two-factor primitive.
      Cryptography decision pending in dedicated session when
      hosted-tier promotes.
    - **Per-user instance, shared bitcoind/LN nodes.** Each user
      gets their own backend + DB + Redis + worker; bitcoind and
      Lightning nodes are shared infrastructure (not duplicated
      per user — that's the topology decision). Cost-model
      pending: dedicated-DB-per-user vs shared-DB-with-tenant-
      isolation may be necessary at scale.
    - **30-day free trial → soft-degradation → 10-day grace →
      deletion.** At trial expiry, the instance switches to
      read-only (user can connect, view balances, but can't
      create Holdings, run sweeps, or send/receive). After 10
      additional days without payment, the instance is deleted.
      Behavioral hypothesis: lazy human flesh stays paying.
    - **Privacy boundary disclosure (mandatory).** Self-hosted
      gives true privacy; hosted-tier trades some for convenience.
      What TallyKeep-the-operator can theoretically see on
      hosted-tier:
        - **Descriptors** (xpubs / output descriptors) — anyone
          with read access can reconstruct the wallet's full
          transaction history, balances over time, and counterparty
          patterns. Public-key data, but a meaningful privacy
          leak. *Structurally cannot be E2E-encrypted* — the chain
          analyzer needs descriptors in plaintext to do its job.
        - **Categorization labels** (counterparty names, purposes)
          — sensitive personal financial data. *Could later be
          E2E-encrypted blobs* (server stores, never reads).
        - **Custodial provider API keys** — encrypted at rest with
          the user's passphrase but pass through plaintext briefly
          during a provider call. Same as self-host.
      Disclosure surfaced at the onboarding hosted-tier choice
      AND as a security-health item users acknowledge with the
      same lifecycle as `seed-backup-disclosure`. Comparison
      reference: Bitwarden's hosted vault (zero-knowledge for
      most data, but the model has its limits).
    - **No email = no recovery.** Lose your connection-ID and your
      hosted instance is gone (Bitcoin is fine — re-importable
      from hardware-wallet/seed backup — but TallyKeep state,
      categorizations, sweep policies, history, gone). Disclosed
      explicitly at hosted-tier signup with a "save this
      somewhere safe" warning treated like the BTC stack /
      privacy / UTXO warnings (security-health system,
      acknowledgment-required).
    - **Abuse mitigation.** Without email-based identity, scripted
      attackers can spin up infinite trial instances. Friction
      options to evaluate: small Lightning sat-payment to claim
      an instance (fits the brand); proof-of-work challenge;
      CAPTCHA; rate-limit by IP. Decision pending.
    - **Operational support — no email = no out-of-band reach.**
      User-side break-glass (server outage, security advisory)
      cannot be pushed via email. Fallback options: in-app
      banner system, public status page checked at app launch,
      announce-only Lightning address publishing key updates.
      Decision pending; needs to be designed before public-ship.
    - **Billing.** $7-12/mo placeholder. Payment options to
      evaluate: Lightning (fits the brand), credit card (defeats
      the no-account principle if Stripe-CustomerID is required).
      Lightning-first feels right.
- **Touches:** architecture, threat model, deployment, billing,
  privacy notice in onboarding, security-health system
  (acknowledgment lifecycle), abuse mitigation, support
  infrastructure
- **Status:** sketched
- **Milestone:** TBD — Rémy to decide whether hosted tier launches
  with public-ship (in the ship-gate bundle) or follows in
  post-shipping. Self-host launch first is defensible (smaller
  initial blast radius); hosted-tier-from-day-one captures more of
  the LatAm/Africa target market faster.
- **Notes:** Onboarding screen-1 (`mobile_onboarding_01_connect.html`)
  is drafted to anticipate this — "Connect to your TallyKeep" works
  for both self-hosted (scan QR / enter URL) and hosted-tier (claim
  connection-ID) without changing structure. Hosted-tier specifics
  (claim flow UI, payment page, soft-degradation banners) are a
  separate iteration when this entry promotes.

  **Hosted-tier onboarding screens that materially differ from the
  self-hosted flow** (sharpened during the onboarding-screen-2
  review 2026-05-10, kept here so the hosted-tier iteration starts
  from a defined gap-list):

  - *Hosted-tier signup* — likely lives in a web browser (TBD —
    could be app-internal too). Generates the connection-ID,
    user sets a server passphrase. The current Screen 01's
    "Don't have a TallyKeep yet? → see docs" ghost CTA is the
    bridge: docs explain how to spin up either self-hosted
    (Docker / Umbrel / Start9) OR claim a hosted instance.
  - *Backup-credentials screen* (new, app-side). Critical step
    after first hosted-tier pairing: user must save their
    connection-ID + passphrase somewhere safe. Without
    email-based recovery (the no-email-no-account principle),
    losing both = instance is gone (Bitcoin recoverable via
    hardware backup; TallyKeep state — categorizations, sweep
    policies, history — gone). Acknowledgment-required pattern,
    same lifecycle as `seed-backup-disclosure` in the
    security-health system.
  - *Paired-confirmation server identifier* — surfaces the
    connection-ID alongside the label, e.g.
    `crisp-river-7842 · TallyKeep hosted`; endpoint is the
    hosted URL (`https://app.tallykeep.io/...`).
  - *Deep-recovery copy* — differs from self-hosted. Self-hosted
    says "Re-pair from desktop"; hosted-tier says "Re-pair from
    your hosted dashboard" (and the dashboard URL is part of
    the saved-credentials acknowledgment screen).
  - *Traveling-hosted-tier-user-without-second-device.* Open
    design question for this iteration: if the user is on their
    only phone, has lost their device credential, and needs to
    re-pair, how do they display a QR? Candidate solutions
    include: hosted dashboard accessible from the same phone's
    web browser, recovery codes set during signup, Lightning
    sat-payment as a friction-attached recovery affordance.
  - *Passphrase-fallback unlock* — same mechanism as self-hosted
    (per ADR-0008). Phone forwards passphrase to hosted backend
    for validation. No app-side difference.

### Lightning support

- **Captured:** 2026-05 (from design_decisions.md §12, pre-merge)
- **Motivation:** Instant low-value spending. Mobile-first feature
  for daily-use markets where on-chain fees price out small payments.
- **Sketch:** Breez SDK first; evaluate own LSP later (LSPS0/1/2).
  Mobile-only spending path (Capacitor); desktop read-only for
  hosted-tier users; both surfaces for self-hosted users running
  CLN/LND.
- **Touches:** `concerns/lightning_placeholder.md`, mobile spec, UI send/receive,
  threat model
- **Status:** sketched
- **Milestone:** TBD — Rémy explicitly flagged this as needing
  re-analysis. Lightning may be a public-shipping differentiator
  (instant low-value spending is a real target-market need) or a
  post-shipping enhancement. Breez SDK license terms also need
  verification before commit.
- **Notes:** Capacitor-only for spending per
  mobile_form_factor_decision.md. If pre-shipping, increases the
  ship-gate scope significantly.

### DCA primitive

- **Captured:** 2026-05 (from design_decisions.md §14, pre-merge)
- **Motivation:** **Dollar-Cost Averaging** — recurring scheduled
  purchases at fixed intervals regardless of price, to average out
  timing risk. Removes the no-Bitcoin-yet onboarding friction in
  target markets where users haven't accumulated yet and want a
  set-and-forget acquisition path.
- **Sketch:** Schedule + connected Account + sweep policy.
- **Touches:** treasury layer, scheduler, UI
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Pull forward only if real user feedback shows
  acquisition friction is a launch blocker. Touches the deferred
  "order placement on custodial providers" zone — likely needs that
  feature first.

### Equity reference unit

- **Captured:** 2026-05 (from design_decisions.md §14, pre-merge)
- **Motivation:** Reframe "fiat is a bet on an economy" by displaying
  stack value in shares (AAPL, gold ounces). Differentiator vs other
  Bitcoin apps.
- **Sketch:** Add unit-toggle option (sats / BTC / fiat / equity ref)
  with user-selectable reference asset.
- **Touches:** UI home page, possibly a new module for reference
  rates
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Flag candidate `display.unit.equity_reference`.

### Inflation-adjusted graphs

- **Captured:** 2026-05 (from design_decisions.md §14, pre-merge)
- **Motivation:** Show real value evolution agnostic of currency
  inflation. Differentiator.
- **Sketch:** Holding detail page graph offers an
  "inflation-adjusted" toggle that uses a CPI feed.
- **Touches:** UI holding-detail, new external CPI feed
- **Status:** idea
- **Milestone:** post-shipping

### Retirement plan with timelock

- **Captured:** 2026-05 (from design_decisions.md §14, pre-merge)
- **Motivation:** Bitcoin script-enforced lock period for long-term
  holdings, supporting structured retirement planning.
- **Sketch:** New Holding sub-type or Vault variant with CSV/CLTV
  timelock.
- **Touches:** domain model, banking layer, UI vault flows, threat
  model
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Touches the rejected "yield" zone if not careful —
  strictly self-custodial timelock, no collateralization. Needs
  legal review before commit.

### Blueprint analysis

- **Captured:** 2026-05 (Rémy decision — refines original module 05
  scope which originally had Blueprint as v1)
- **Motivation:** Privacy / hygiene analyzer surfacing address reuse,
  dust UTXOs, round-number outputs, suspected consolidation. Strong
  public-product differentiator (most Bitcoin apps don't help users
  see these patterns). Backend logic per `concerns/observation.md` is already
  implemented; what's deferred is the UI surface.
- **Sketch:**
    - Three summary tiles (address reuse, dust UTXOs,
      round-number outputs)
    - Severity-tagged recommendations with concrete actions and
      per-finding dismissal
    - Surfaced contextually after first Strongbox or Vault creation,
      and via Settings for opt-in users
    - Plus (further out) UTXO clustering graph for visualizing
      transaction history privacy
- **Touches:** UI mobile + desktop, possibly a dedicated Privacy /
  Blueprint section in nav
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Backend logic per `concerns/observation.md` implemented and stays. UI
  surface deferred. The clustering graph is further deferred and
  likely desktop-only when it lands. During pre-shipping Rémy works
  without Blueprint surfaced; post-shipping users get it as a
  feature update — credible reason to keep the app updated and a
  differentiator against most Bitcoin wallets.

### Vault Send for all shapes

- **Captured:** 2026-05 (from module 12, pre-retirement). Re-scoped
  2026-05-15 under ADR-0010 β: v1 ships Vault onboarding for both
  shapes (single-sig + timelock; multisig with or without timelock)
  via the Vault wizard. This iteration is now narrowly about Vault
  Send — the genuinely hard surface — plus the Vault detail page
  that hosts the Send affordance.
- **Motivation:** Per ADR-0010 β, Vault Send is deferred
  shape-agnostic because the multi-signer PSBT coordination,
  cosigner-status UI, partial-signature collection, and
  chain-side timelock-check display deserve their own design
  pass. Shipping Send for both shapes together preserves Vault
  detail UX uniformity — one detail page across shapes; Send
  greyed-out in v1 lifts for both at the same time when this
  iteration ships.
- **Touches:** banking layer (PSBT construction + multi-signer
  coordination + timelock-check at broadcast), UI Vault detail
  page (full design lands here — currently a v1 placeholder),
  UI Vault Send flow (compose / review / export / re-import /
  broadcast across all five Vault shape variants), threat model
  (PSBT roundtrip with chain-side timelock check; cosigner
  coordination ceremony), brand / mockups (cosigner annotation
  UI, per-signer-status UI, per-UTXO unlock ledger for CSV
  shapes).
- **Status:** sketched. v1 ships descriptor onboarding for all
  five Vault shapes; this iteration picks up Vault detail + Send
  for the same five shapes.
- **Milestone:** post-shipping
- **Notes:** "Promote a Strongbox to a Vault" migration lands here
  too — a single-Holding type-relabel when the user adds multisig
  to the descriptor (no on-chain action, the chain sees the same
  descriptor before and after). Single-sig + timelock cannot be
  promoted from Strongbox the same way (would require an on-chain
  send to a new script).

### Tap-anything-for-detail help affordance

- **Captured:** 2026-05-15 (during Vault-wizard review, Rémy
  flagged that ad-hoc info banners shouldn't be wizard-specific).
- **Motivation:** New users encountering Bitcoin / TallyKeep
  vocabulary (descriptor, miniscript, CLTV / CSV, xpub
  fingerprint, etc.) benefit from contextual help — but
  per-wizard inline hint banners create inconsistency and visual
  noise. A product-wide pattern would let any noun, parameter
  row, or field label expose a small ⓘ icon that, on tap,
  reveals a short definition + "learn more" link. Lands once,
  reused everywhere.
- **Touches:** UI shell (new ⓘ icon component, expandable
  inline panel or bottom-sheet), copy library (definitions per
  concept), every wizard and detail page that surfaces
  Bitcoin-native vocabulary.
- **Status:** idea
- **Milestone:** post-shipping. Worth surfacing once core
  flows are validated and we know which concepts users
  genuinely stall on.

### Multi-path Vault descriptors (hot path + recovery path)

- **Captured:** 2026-05-15 (during Vault-wizard brainstorm, ADR-0010
  β).
- **Motivation:** Real inheritance / anti-loss designs combine
  multiple spending paths: e.g. `or(2-of-3 hot keys with short
  CSV, 1-of-3 recovery key with longer CSV)`. v1 Vault accept set
  is deliberately narrow — `m-of-n` optionally + a single
  timelock — and rejects multi-path miniscript constructs
  (or-trees, decaying multisig, hashlocks) with an explicit
  "contact us" message. The use case is real; the design surface
  is bigger than the v1 wizard's parseback shape supports.
- **Touches:** Vault wizard accept set, parseback (multi-row
  spending-path display), Vault detail (per-path unlock countdown,
  per-path UTXO classification), threat model (recovery key
  custody, alternate signer coordination), holdings/04_vault.md
  vocabulary (`spending_paths` would replace the single
  `timelock_kind` / `timelock_value` pair).
- **Status:** idea
- **Milestone:** post-shipping (after the multisig-descriptor +
  Vault Send iteration; the cosigner-coordination UX from that
  iteration is a dependency)

### Usage-based feedback for long-term Vaults

- **Captured:** 2026-05-15 (during Vault-wizard brainstorm, ADR-0010
  β).
- **Motivation:** A `purpose=long_term` Vault whose observed
  outflow frequency contradicts the declared long-term intent is
  a real declared-vs-observable mismatch — declaration is the
  flag, observable is the spend frequency, the analyzer has
  substance to flag. Surface as a security-health item suggesting
  an on-chain timelock upgrade or migration to Strongbox when the
  gap is wide enough. Honest variant of the rejected
  soft-timelock-declaration idea.
- **Touches:** security-health system (pending `seed-backup-
  disclosure` arbitration), Vault detail (where the user sees the
  warning), holdings/04_vault.md type-specific safeguards (already
  captures this as deferred).
- **Status:** idea
- **Milestone:** post-shipping. Folds into the broader
  security-health system iteration when that arbitration closes.

### Order placement on custodial providers

- **Captured:** 2026-05 (from module 07 + 12, pre-retirement)
- **Motivation:** Pre-shipping is read + withdraw only. Order
  placement enables buying / selling Bitcoin through the connected
  provider directly from TallyKeep.
- **Touches:** treasury layer, threat model, regulatory posture
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Requires fresh regulatory evaluation before commit.
  Custody-adjacent territory; the rationale for keeping it out of
  pre-shipping is in `holdings/01_account.md` §"Regulatory posture (locked)".

### Capacitor mobile wrapper

- **Captured:** 2026-05 (originally module 12 v3, moved by
  mobile_form_factor_decision.md)
- **Motivation:** Native plugin access (Keychain, biometric, camera,
  push). Required for TallyKeep-managed Purses (whose seeds live in
  the device's Keychain/Keystore) and for the private-ship event
  per ADR-0003.
- **Touches:** build pipeline, UI mobile (NativeBridge implementation),
  threat model
- **Status:** sharpened-ready-to-promote
- **Milestone:** **pre-shipping (private-ship enabler).** Promotes
  to `next_iteration.md` once the mobile UI is fine-tuned in browser
  to Rémy's satisfaction. Concrete iteration includes:
    - Integrate Capacitor; build pipeline for the wrapped app.
    - Swap NativeBridge stubs for real plugin calls on the
      Capacitor branch (Keychain/Keystore, biometric, camera,
      share, clipboard).
    - **Remove the dev-mode `localStorage` fallback for
      `secureStorage`** that the Onboarding + Daily Unlock + Home
      iteration's NativeBridge browser branch ships as a dev
      crutch. Grep the codebase for
      `// TODO(browser-pwa-auth-model)` markers and resolve each.
    - **Implement the browser-PWA long-term auth model** per the
      resolution of `pre-implementation.md` `browser-pwa-auth-model`
      (leading direction: per-session passphrase login, no
      pairing, no persistent credential, session token in memory
      only). This includes simplifying or removing the Connect /
      Paired flow from browser PWA routing and adding a
      browser-PWA-specific entry screen.
    - Build the authentication layer hardening for the
      Capacitor side (the dev-phase auth layer shipped in the
      Onboarding iteration is sufficient for personal-use; review
      and harden as needed for sideload).
    - Build the security-health seed-backup minimum for
      `seed-backup-disclosure`.
    - Sideload to Rémy's phone for private-ship.
  Blocked by: arbitration on `browser-pwa-auth-model` in
  `pre-implementation.md` (gates the browser-branch cleanup).

---

### Ship-gate meta-iteration (the public-ship event)

- **Captured:** 2026-05 (ADR-0003 — Project phases and shipping
  milestones)
- **Motivation:** This entry IS the public-ship event in
  `future_iterations.md` form. Once Rémy is satisfied with the
  product (after iterating on his own phone post-private-ship), the
  ship-gate is the dedicated session bundle that finalizes
  everything before going public. Reaching it is Rémy's explicit
  call ("I'm satisfied; finalize and ship"), not a tech checklist.
- **Sketch:** A meta-iteration bundling the items below. Some need
  their own dedicated arbitration when the ship-gate approaches
  (notably authentication-layer hardening and the third-party
  security audit scope).
- **Touches:** auth, signing, build pipeline, distribution, threat
  model, brand
- **Status:** sketched
- **Milestone:** **pre-shipping** (this entry's items collectively
  constitute the public-ship event itself).
- **Notes:** Items bundled into the ship-gate:
    - **Native secp256k1 signing** — replaces JS @noble/secp256k1
      from the personal-use phase (was pre-implementation item
      `native-secp256k1-signing`).
    - **Authentication layer hardening** — passphrase + biometric
      requirements tightened for public users (the private-ship
      version is enough for Rémy's own daily use).
    - **End-to-end third-party security audit** — verify no security
      breaks, no leaks, no inadvertent custody surface.
    - **Reproducible build pipeline** (CI).
    - **App Store / Play Store distribution** + listing assets.
    - **F-Droid licensing audit** — Capacitor licence chain, any
      Lightning SDK if Lightning is in scope.
    - **Brand voice and identity finalization**.
    - **Public privacy policy + terms of service**.
    - **Customer support infrastructure** — triage, response
      expectations.

### PSBT-by-QR roundtrip on mobile

- **Captured:** 2026-05 (pre-implementation item `psbt-by-qr-mobile`)
- **Motivation:** Lets mobile send from Strongbox to QR-PSBT-capable
  hardware wallets (Coldcard, Jade) without round-tripping through
  desktop.
- **Sketch:** Capacitor camera scans QR PSBT (signed by HW wallet);
  Capacitor displays QR PSBT (unsigned, for HW wallet to scan).
  Multi-frame for large PSBTs.
- **Touches:** UI mobile send-from-Strongbox flow, QR plugin, PSBT
  serializer
- **Status:** sketched
- **Milestone:** post-shipping
- **Notes:** Per-vendor QR PSBT specifics (UR, BBQR) need a small
  compatibility matrix. Could alternatively land pre-shipping if
  mobile-only Strongbox flow becomes a launch priority — Rémy's
  call when the time comes.

### Push-driven categorization workflow

- **Captured:** 2026-05 (pre-implementation item
  `categorization-queue-mobile`, deferred parts)
- **Motivation:** When the bitcoin node detects new on-chain activity
  for a watched Holding, prompt the user to categorize it without
  forcing them to dig into a queue.
- **Sketch:** Backend SSE event when a new transaction matches a
  watched descriptor → mobile push notification (Capacitor) → tap
  opens an in-app timed popup with the transaction details and quick
  categorization affordances. Holding-detail page also shows
  uncategorized transactions inline with categorize-here affordances.
- **Touches:** backend SSE, push notification adapter, mobile UI
  notification handler, holding-detail page
- **Status:** idea
- **Milestone:** TBD — best guess: post-shipping (nice-to-have
  enhancement; not critical for launch).
- **Notes:** Hosted-tier requires push relay through TallyKeep
  infrastructure; self-hosted does it via the user's own backend.
  Privacy implications worth surfacing in onboarding for hosted-tier.

### Live scan-status push (Redis → SSE → frontend)

- **Captured:** 2026-05-14 (surfaced during Purse wizard hand-test — home page
  showed "Scanning…" indefinitely because the frontend only fetches once on mount
  and the backend never pushes the completed state).
- **Motivation:** The backend already has Redis and an async worker stack.
  Descriptor imports trigger a background chain scan; when the scan completes the
  `scan_status` field updates in the DB. The frontend has no way to know this
  happened — it has to be told. A one-shot page-load fetch is not enough.
- **Sketch:**
    - Backend emits a Redis pub/sub event when scan_status transitions
      (`scanning → synced`, `scanning → error`).
    - A thin SSE endpoint (`GET /api/v1/events/holdings`) streams those events
      to the connected client (same auth as REST calls).
    - Frontend `home/+page.svelte` subscribes to the SSE stream after mount;
      on a `holding.scan_status_changed` event, updates the matching holding in
      the local list reactively without a full refetch.
    - Graceful degradation: if SSE is unavailable (offline, proxy strips
      keep-alive), the page shows the last-known state. A manual pull-to-refresh
      is acceptable fallback.
- **Touches:** backend event emitter (Redis pub/sub hook in the scan worker),
  new SSE endpoint, frontend home page reactive state, auth middleware (SSE
  needs the same Bearer-token guard as REST)
- **Status:** sketched
- **Milestone:** pre-shipping — "Scanning…" that never resolves is a confusing
  UX for any user who imports a wallet and waits for their balance to appear.
  Low implementation cost given Redis is already running.
- **Notes:** The broader "Push-driven categorization workflow" entry (below)
  uses the same SSE channel — coordinate so both events flow through one
  `EventSource` connection, not two. This entry is the simpler first step:
  no push notification, no Capacitor plugin — just a browser SSE stream to
  the already-connected backend.

### Security-health system

- **Captured:** 2026-05 (pre-implementation item
  `seed-backup-disclosure`, plus broader scope from the original
  design_decisions.md §9 Blueprint analysis)
- **Framing review needed before sharpening** (Rémy 2026-05-14,
  during the Strongbox-wizard advisory copy pass). "Security
  health" as a product-design concept the user encounters
  directly — a dedicated Home section / tab grouping these items
  under that heading — is **not yet committed**. The current
  entry assumes that surface; revisit whether the right model is
  (a) the centralised "Security health" surface as sketched, or
  (b) per-Holding inline surfacing (warnings live on the relevant
  Holding's detail page, not in a generic dashboard), or
  (c) some hybrid. Items themselves (missing signing metadata,
  seed-backup-disclosure ack, declared-vs-observable mismatch,
  Blueprint findings, hosted-tier privacy ack) all still need a
  persistence home and a resolution path — that part is firm.
  The user-facing taxonomy is the open question. Wizard-side
  copy in the Strongbox-wizard iteration (`UI/mobile.md` Add
  Holding — Strongbox wizard, Step 1 advisory) deliberately
  avoids forward-referencing any specific surface until this
  resolves.
- **Motivation:** Several persistent items need a shared home so
  the user has one place to see ongoing security concerns, without
  any of them being silently hidden. Includes:
    - Purse seed not backed up (`seed-backup-disclosure`)
    - Strongbox used too frequently for spending (declared vs observable)
    - **Strongbox missing signing metadata** — captured 2026-05-14
      during the Strongbox-wizard design pass. Triggered when a
      Strongbox is imported from a bare xpub (no `[fingerprint/path]`
      brackets — typical of Trezor Suite "Show xpub", Ledger Live,
      Phoenix "Wallet final", BlueWallet xpub export). Receiving
      works; spending may need extra setup at the hardware-wallet
      side because the PSBT `bip32_derivation` field can't be
      populated cleanly. Item copy: *"Your '{vendor} Strongbox' is
      missing signing metadata. Spending later may need an extra
      step on your hardware wallet."* Item has a **"Fix this"**
      affordance opening a small remediation sub-flow with two
      paths: (a) **re-export from your HW wallet** with full
      origin metadata (Coldcard Generic JSON / Sparrow descriptor
      export / Trezor Suite Advanced → Descriptor / Ledger Live
      equivalent / etc.) — user pastes or uploads; backend verifies
      derived addresses still match the existing watched ones; same
      Strongbox record updated in place. (b) **Manual entry**
      (advanced): master fingerprint freetext input (8 hex chars,
      validated case-insensitive), derivation path dropdown
      (BIP 84 `m/84'/0'/0'` default + BIP 49 / BIP 44 / BIP 86 /
      Custom escape hatch). Backend verifies derived addresses
      match before persisting. Most users will pick re-export.
      Strongbox-only — Purse doesn't surface this because TallyKeep
      never signs for a watch-only Purse. The wizard-side
      detection lands with the Strongbox-wizard iteration (parse-
      back warning variant already mocked); the security-health
      surface + the Fix-this sub-flow are this iteration's scope.
    - Vault metadata mismatch
    - Address reuse / dust / round-number outputs (Blueprint findings)
    - Hosted-tier privacy boundary not acknowledged
    - Principles acknowledgment not yet given — informational,
      joins after Onboarding screen 01 skip (per `UI/mobile.md`
      Onboarding Notes 2026-05-10). **This iteration is the
      first to need persistent stack-bound state for unack'd
      items** — the Onboarding + Daily Unlock + Home (empty)
      iteration deliberately deferred the persistence question
      to here. Decide the model when sharpening: a generic
      backend preferences endpoint
      (`GET /api/v1/preferences` + `PUT /api/v1/preferences/{key}`)
      vs an open-items table keyed by item-type (more aligned
      with the Security-health surface). Latter is probably
      cleaner because the items are heterogeneous (acks,
      warnings, dismissals) and benefit from a uniform
      schema.
- **Sketch:** A dedicated section on Home (heading: **"Security
  health"**) and/or a dedicated tab showing all open security and
  acknowledgment items, severity-tagged where applicable,
  dismissible-with-acknowledgment, never silently hidden.
  User-visible heading "Security health" matches banking-grade
  norms (Apple Health "Health checks", "Account health" in retail
  banking). Item copy stays calm; the heading carries the
  seriousness register.
- **Touches:** UI mobile + desktop, backend events, threat model
- **Status:** sketched
- **Milestone:** **pre-shipping** — at least the seed-backup warning
  part is a private-ship requirement (per ADR-0003); broader
  security-health (Strongbox usage, Vault mismatch, hosted-tier
  acknowledgment) can land progressively. Blueprint findings are
  themselves post-shipping, so that part of the security-health
  system follows Blueprint.
- **Notes:** Specify in the dedicated session for pre-implementation
  pre-implementation item `seed-backup-disclosure`. Touches the
  Blueprint feature spec (originally module 05).

### Settlement-rails payment status with confirmation probability

- **Captured:** 2026-05 (mid-conversation, during gauntlet reframe)
- **Motivation:** Bitcoin confirmation is a statistical finality
  function, not binary. Most apps treat either 0-conf or 1-conf as
  "done." TallyKeep's locked "honest abstraction" principle turns
  this into a differentiator: show the truth in the vocabulary
  institutions already use for settlement (T+0, T+2, settlement-risk
  windows). Strong candidate for the product's single most
  distinctive feature, on two axes: vs other Bitcoin apps (which
  hide settlement reality behind binary "sent"/"confirmed"
  language), and vs retail banking apps (which often cannot show
  in-transit states at all, because their settlement infrastructure
  doesn't expose them to the customer-facing layer). Bitcoin's
  on-chain transparency makes the in-transit visible by default;
  TallyKeep is the surface that does it justice.
- **Sketch:** Each transaction surfaces a status flow modeled on
  institutional payment rails:
    1. Instruction composed (PSBT created, not signed)
    2. Instruction signed (PSBT signed, not broadcast)
    3. Instruction acknowledged (broadcast, in mempool)
    4. Settlement (on-chain inclusion + depth)
  At each step, surface a finality probability:
    - In mempool: probability of inclusion in next N blocks, computed
      from fee rate vs current mempool dynamics
    - At depth k: reversal probability under a stated adversary model
    - At depth ≥ 6: ~99.99% finality, "settled" (assumptions visible)
- **Touches:** UI tx detail page, new `confirmation_probability`
  service in backend (mempool dynamics + reorg modeling), threat
  model nuance
- **Status:** sketched
- **Milestone:** TBD — best guess: pre-shipping if the pattern
  validates as a defining feature during the personal-use phase.
  Strong differentiator candidate; if Rémy decides this is what
  TallyKeep's distinctive UI surface should be, it ships at
  public-ship. A lighter version could be a post-shipping
  enhancement.
- **Notes:** Probability math has well-known formulas (Nakamoto's
  original paper; Wuille and others have refined them). Care needed
  to avoid false precision: showing "99.99%" requires the user to
  see the assumed adversary hashpower and the natural-orphan
  baseline, otherwise the number is meaningless. Mempool.space
  surfaces fee-based inclusion estimates already; the novel part
  here is the institutional payment-rails framing and the
  integration as a first-class transaction status. Aligns naturally
  with the banking vocabulary the product already uses.

### Holding-to-Holding sweeps beyond Account-originated

- **Captured:** 2026-05 (custodial-and-sweeps review)
- **Motivation:** Per `concerns/sweep_policies.md`, SweepPolicy is generalized:
  any Holding to any Holding with a safety validator. Pre-shipping
  surfaces Account-originated sweeps (minimum-exposure trading
  pattern). Other Holding-to-Holding sweeps are architecturally
  supported but their UX hasn't been designed.
- **Sketch:** Surface sweep-policy creation for non-Account sources:
    - **TallyKeep-managed Purse → Strongbox/Vault** — auto-sweep
      with biometric prompt or background signing on the Capacitor
      device that holds the seed. Use case: keep daily-spending
      balance bounded; push excess to cold storage automatically.
    - **Strongbox → anywhere** — not auto; reduces to a scheduled
      reminder that prepares a PSBT awaiting the user's external
      signature on the hardware wallet.
    - **Vault → anywhere** — not auto; same as Strongbox plus
      multisig coordination.
- **Touches:** UI sweep-policy creation flow, scheduler / reminder
  system, threat model
- **Status:** idea
- **Milestone:** TBD — best guess: post-shipping. Architecture is in
  place per `concerns/sweep_policies.md`; only UI surface and reminder workflow are
  deferred. Pick up after primary sweep flows are stable.

### Receive in static / merchant mode

- **Captured:** 2026-05 (fresh-address discussion)
- **Motivation:** Default is fresh-per-payment (privacy best
  practice; the Blueprint analyzer flags reuse). Some legitimate
  use cases prefer a reused / static address: tip jars, donation
  addresses, simple merchant flows where invoice-matching happens
  out-of-band, or printed addresses on physical signs.
- **Sketch:** Per-Holding "static address mode" toggle in receive
  settings. When on, Receive always returns the same address.
  Privacy implications surfaced via a clear warning; the Blueprint
  analyzer continues to flag the reuse honestly when that feature
  ships.
- **Touches:** UI receive flow, Blueprint analyzer interaction
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Most TallyKeep users won't need this — power-user /
  specific-use-case territory. Worth recognizing as a legitimate
  need rather than treating address reuse as universally bad. Even
  most merchants prefer fresh-per-invoice (BTCPay, OpenNode,
  similar do this), but static-address has its place. Low priority;
  surface only if real users ask. Note: address reuse has no
  direct impact on transaction fees (fees are a function of tx size
  in vbytes, not addresses); the impact is on privacy / clustering
  and indirect UTXO-management complexity.

### Fiat display

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Sats are the locked default unit (per `UI/README.md`),
  but optional fiat display is useful for a normal user comparing
  against everyday prices. Translation layer, not the home unit.
- **Sketch:** Behind a `display.fiat_conversion.enabled` flag. Rate
  source: the first connected CustodialProvider, with attribution
  ("via [source] · 2m ago") shown next to the consolidated value.
  Already partly described in `UI/README.md` §"Currency consolidation
  is opt-in via a single dropdown".
- **Touches:** UI mobile + desktop, settings, possibly a rate-feed
  abstraction
- **Status:** sketched
- **Milestone:** post-shipping
- **Notes:** The cross-platform decision in `UI/README.md` already
  picks the dropdown UX. What remains is the rate-source plumbing
  and the staleness display.

### LedgerEntry CSV export

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Tax filing and accounting integration. Self-hosted
  users in particular need to produce reports for their tax
  authorities; exports let them feed into existing tools without
  TallyKeep having to grow into an accounting suite.
- **Sketch:** Settings → Export → CSV of LedgerEntries with all
  available fields (txid, direction, amount, fee, counterparty if
  categorized, label, timestamp, confirmation depth at export time).
  Per-Holding or whole-portfolio. Per-year filter.
- **Touches:** API (new export endpoint), UI settings, accounting
  format conventions (probably plain CSV + a sidecar JSON for
  schema)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Hosted-tier privacy implications worth surfacing — the
  exporter sees everything regardless of who runs it.

### Replace-By-Fee (RBF) support

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Lets the user bump a stuck transaction's fee
  without composing from scratch. Standard wallet feature.
- **Sketch:** Behind a `banking.rbf.enabled` flag. On a broadcast-
  but-unconfirmed tx, surface a "Bump fee" affordance. Compose a
  replacement PSBT signaling RBF, sign externally, broadcast.
- **Touches:** banking layer, send flow, UI tx detail page, threat
  model (RBF can be confusing; settlement-rails framing helps)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Pairs naturally with the settlement-rails / confirmation-
  probability entry. RBF visibility makes the "not yet final" state
  legible.

### Additional CustodialProvider adapters

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement);
  revised 2026-05-16 (Account-wizard iteration cut Bitstamp from
  v1 to focus on Kraken-first ship).
- **Motivation:** Pre-shipping currently ships Kraken only. Broader
  coverage matters for target markets — Bitstamp's whitelist-via-
  web-UI shape needs the withdrawal sub-flow's manual-attestation
  branch; Bitfinex has Argentine users; Coinbase Advanced has US /
  EU coverage; LatAm-native venues (Lemon, Buenbit, Belo, Ripio)
  are higher priority for the Argentina launch than Coinbase.
- **Sketch:** Each adapter is a ccxt wrapper (or custom client for
  non-ccxt venues — see the separate Swissquote entry) with
  adapter-specific fixtures, integration tests, and a per-provider
  helper-banner copy block (Step 1 of the Add Account wizard
  swaps banner content based on the picked adapter). Each adapter
  declares its `supports_withdrawal_keys` and `whitelist_read_api`
  capabilities at registration; the wizard reads them to gate
  Step 3's suggestion card and the withdrawal sub-flow's UX.
- **Touches:** treasury layer adapters, integration test harness,
  Add Account wizard provider dropdown, per-provider helper-banner
  copy registry.
- **Status:** idea
- **Milestone:** post-shipping (Bitstamp specifically: pre-public-
  ship if user demand surfaces; the v1 cut was scope-tightening,
  not architectural).
- **Notes:** Priority order is market-driven. Argentine launch
  → Lemon, Buenbit, Ripio, Belo first. Bitstamp is the lowest-
  friction next addition because the adapter is already
  contract-compatible with the treasury layer; it just lost the
  dropdown slot in v1. Bitfinex / Coinbase Advanced if user
  demand surfaces.

### Account withdrawal-key sub-flow

- **Captured:** 2026-05-16 (deferred during the Account-wizard
  design pass; design pass close locked the wizard's read-only-
  only scope, but the withdrawal capability still needs its own
  design pass to ship before SweepPolicy-on-Account work begins).
- **Motivation:** Per ADR-0011, the Account Holding type carries
  a separate withdrawal credential and provider-side whitelist
  configuration. The Add Account wizard does not capture these
  (its read-only-only scope is deliberate). The Account detail
  page's Withdraw affordance is the canonical discovery surface
  but routes to a sub-flow that doesn't exist yet — until it
  ships, the Withdraw button is greyed-out with a tap-prompt
  ("coming in a later iteration"), and SweepPolicies on Account
  Holdings run in watch-and-advise mode only.
- **Sketch:** Likely 3–4 steps, reachable from Account detail OR
  from the Add Account wizard's Step 3 capability-gated
  suggestion card:
  1. **Whitelist destination.** Cross-reference UI: list the
     user's existing TK Holdings (Strongbox / Vault / Purse) as
     candidate destinations with verification badges, plus a
     "paste external address" affordance, plus the provider's
     fetched whitelist (when `whitelist_read_api = true` — Kraken)
     OR a manual attestation checkbox (when
     `whitelist_read_api = false` — Bitstamp). Picking a TK
     Holding derives its next-unused address; pasting external
     accepts any address the user has whitelisted on the
     provider's side.
  2. **Withdrawal credential paste.** API Key + Private Key
     fields, paste pattern parity with the Add Account wizard's
     Step 1. Backend validates the credential has *only* the
     provider's withdraw permission (plus the provider-required
     balance-query scope where applicable — Kraken needs both).
     Overage rejected with the same locked-copy pattern as the
     read-only credential's overage error.
  3. **Confirmation / parseback.** Recap the destination, the
     credential's permission scope, and the activation conditions.
  4. **Success.** Withdraw becomes active on Account detail;
     SweepPolicy creation surfaces full act-mode options.
- **Touches:** new sub-flow design + mockups, `holdings/01_account.md`
  withdrawal-credential and outflow sections (reference the
  shipped sub-flow), `concerns/sweep_policies.md` Account-source
  branch (act-mode unlocked when `withdraw_credential_id` is
  non-null), Account detail page (Withdraw button activation
  logic), Treasury-view iteration's SweepPolicy creation flow.
- **Status:** sketched (the design discussion in the 2026-05-16
  brainstorm produced the decision-tree; sharpening needs its own
  session covering Holdings cross-reference UI, Bitstamp manual-
  attestation branch, withdrawal-key tap-to-clear coding rule).
- **Milestone:** pre-shipping (private-ship gate — Rémy needs
  this to actually use auto-sweep on his own Kraken Account).
- **Notes:** Touches the `concerns/sweep_policies.md` open
  arbitration `sweep-validator-extended-rules` indirectly (the
  validator can ground its warnings against this sub-flow's
  output — confirmed whitelisted destination, scoped credential
  presence). The "Bitstamp can't verify whitelists via API"
  asymmetry is real and lives in this sub-flow's design pass;
  the wizard does not touch it.

### Deposit Send-to-Account flow

- **Captured:** 2026-05-17 (Account-detail-page brainstorm, after
  Rémy reframed deposit as the decumulation pathway — sending BTC
  from a TK Holding *to* the custodial Account, so the user can
  sell on the provider's site and exit to fiat).
- **Motivation:** Decumulation symmetry. The accumulation flow
  (provider → TK Holding via Withdraw / SweepPolicy) is locked.
  The reverse — TK Holding → provider for selling — currently has
  no in-app path. The user has to copy their Kraken deposit
  address manually from kraken.com, paste it into a Send flow
  from a separate Holding, and remember to use it. The product
  narrative reads cleaner with TK as the **outflow / inflow
  controller** between TK Holdings and the custodial venue:
  pass-through liquidity in both directions, BTC never sitting at
  the venue longer than the user's trading window.
- **Sketch:** Reached from the Account detail page's **Deposit**
  action button. Likely 3 steps:
  1. **Source picker.** List the user's other TK Holdings
     (Strongbox / Vault / Purse) with their available balances.
     Tap to pick. (Single source per deposit; multi-source split
     is out of scope.)
  2. **Amount + fee.** Amount field with max-balance affordance
     (minus an unspent-buffer per the source Holding's policy),
     fee selection per the standard Send pattern (fast / normal /
     economy + custom). Show the pinned destination address read-
     only ("Sending to your Kraken deposit address — set in
     Account → Settings").
  3. **Review + sign.** Standard PSBT review for the source
     Holding type. Strongbox / Vault → export PSBT for signing
     elsewhere. Purse → in-app sign on the device that holds the
     seed. Broadcast on user confirmation; activity row lands on
     both the source Holding's detail page and the destination
     Account's Operations tab (as a `deposit` ledger entry once
     Kraken polls it).
- **Pinned destination address pattern:** the user pastes their
  Kraken BTC deposit address into TK once, stored in the Account
  row as `deposit_address` (nullable; configurable from the
  Account Settings tab's "Deposit address" section). TK does not
  fetch the address via API — that would require
  `Funds: Deposit` scope on Kraken, which also unlocks
  `DepositCancel` (fund-state-changing), breaking the
  observation-credential's "no fund movement" property per
  ADR-0012. The user-pasted pattern is the mirror image of the
  withdrawal whitelist — TK-side pinned destination instead of
  provider-side pinned destination. No new credential scope.
- **SweepPolicy extension for scheduled decumulation:** the
  SweepPolicy model is currently directional (Account →
  Holding). The deposit flow extends it to bi-directional
  (Holding → Account also supported). Scheduled decumulation
  becomes a SweepPolicy with `source_holding_type ≠ account`,
  `destination_holding_type = account`. Fires on schedule or
  threshold, composes a PSBT on the source side, broadcasts.
  Belongs in `concerns/sweep_policies.md` scope when this
  iteration is sharpened.
- **Touches:** Account detail page (Deposit button + Settings tab
  "Deposit address" affordance — both forward-reference this
  sub-flow until it ships), `concerns/sweep_policies.md` (bi-
  directional SweepPolicy model), source-Holding Send-flow code
  paths (PSBT compose / sign / broadcast already exist for
  Strongbox + Vault + Purse — this iteration may or may not
  reuse them depending on how deeply the new flow integrates),
  domain model (`Account.deposit_address` column).
- **Status:** sketched (the 2026-05-17 brainstorm produced the
  shape and the pinned-address rationale; sharpening needs its
  own design pass covering: the source picker's filtering rules
  for available balance, the activity-row reconciliation on
  arrival, the SweepPolicy bi-directional UI, and the empty-
  state when no source Holding has a sufficient balance).
- **Milestone:** post-shipping (good post-public-ship feature
  enhancement — proves the bi-directional pass-through narrative
  and unlocks scheduled decumulation as a differentiator).
  Pre-shipping is conceivable if Rémy's own daily-use feedback
  flags it as a friction point during the personal-use phase.
- **Notes:** Until this ships, the Account detail page's Deposit
  button routes to a coming-soon stub (mirror of
  `mobile_add_holding_coming_soon.html`). The Settings tab's
  "Deposit address" section likewise — capture the field but
  forward-reference the sub-flow that consumes it. Honest
  absence-of-affordance for the actual deposit action.

### Custom adapter for non-ccxt venues (Swissquote and similar)

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Proves the adapter abstraction works for non-ccxt
  venues. Swissquote in particular matters for Swiss / EU users
  with traditional broker accounts that hold Bitcoin positions.
- **Sketch:** Implement the same `CustodialProvider` interface
  ccxt adapters use, but against Swissquote's REST API directly.
- **Touches:** treasury layer adapter abstraction
- **Status:** idea
- **Milestone:** post-shipping

### Signed releases for self-hosters

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Self-hosters running TallyKeep via Docker Compose
  or git checkout need supply-chain credibility independent of the
  app stores. Without signed releases + checksums, "self-hosted"
  becomes a trust-the-pull-from-Docker-Hub story.
- **Sketch:** Signed git tags (developer key), signed Docker images
  (cosign or similar), published checksums alongside each release,
  documented verification steps in the install guide.
- **Touches:** release pipeline, install documentation, trust model
- **Status:** idea
- **Milestone:** **pre-shipping** — needs to land before public-ship
  alongside the reproducible-build pipeline. Self-hosters who pulled
  through the personal-use phase get this as a confidence signal.
- **Notes:** Distinct from app-store distribution. Reproducible
  builds in the ship-gate entry let third parties verify; signed
  releases let users verify against the developer key.

### Remote access for self-hosters

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** Localhost-only is the locked dev / personal-use
  posture. Self-hosters who want their TallyKeep available from
  outside their LAN need a way that doesn't require flipping the
  app's auth posture.
- **Sketch:** Recommended path is WireGuard or Tailscale — the user
  brings their own VPN, TallyKeep stays localhost-bound on the
  remote network. For users who want direct exposure, an API-layer
  auth (bearer token + TLS at minimum) gates the localhost-only
  policy.
- **Touches:** API surface, threat model, settings, install guide
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Touches the locked "Internal API-first" principle —
  any change to the localhost-only posture deserves an ADR. The
  default stays localhost; remote access is opt-in with a clear
  hardening path.

### BOLT12 offers

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** BOLT11 invoices are single-use; BOLT12 offers are
  reusable, smaller, and avoid the "regenerate the invoice every
  time" flow. Where supported, they are a better default for
  Lightning receive.
- **Sketch:** Default to BOLT12 on Purse-with-Lightning where the
  LightningProvider supports it (CLN: yes; LND: experimental;
  Phoenix: depends on version). Fall back to BOLT11 otherwise.
- **Touches:** Lightning placeholder module, LightningProvider
  interface, receive flow
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Lightning-dependent — only relevant once the Lightning
  iteration ships.

### Contact book / saved counterparties

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** Recurring counterparties (rent recipient, family
  member, regular vendor) currently require pasting an address each
  time. A saved-counterparty model with metadata makes recurring
  payments faster and harder to misdirect.
- **Sketch:** Per-counterparty record with a name, one or more
  addresses (or a static address for vendors who use it), notes,
  preferred fee tier. Send flow gets a "From contact" affordance.
  Categorization can auto-populate counterparty when a saved
  address matches.
- **Touches:** domain model (new entity), send flow, categorization,
  receive flow (sharing your address as a contact)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Privacy implications: a contact book on a hosted-tier
  backend is a higher-value target. Consider client-side encryption
  or self-hosted-only at first.

### Budgeting and allocation

- **Captured:** 2026-05 (from module 12 v2, pre-retirement)
- **Motivation:** Banking-ergonomics promise extends to "where is
  my money going." Per-month spending categories, runway tracking
  (how many months of declared monthly spend at current balance),
  Holding-level allocation targets.
- **Sketch:** Categories already exist (categorization is in
  pre-shipping scope). Budgeting is the layer above: monthly limits
  per category, runway computed from declared monthly spend, alerts
  when categories cross thresholds.
- **Touches:** UI (new section), domain model (Budget entity),
  alerts/notifications system
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Touches the rejected "trading terminal" zone if not
  careful — budgeting is about consumption planning, not portfolio
  performance. Stay on the consumption side.

### BLE / NFC transport for payment payloads

- **Captured:** 2026-05 (from module 12 v3, pre-retirement)
- **Motivation:** "Tap-to-pay between two app instances on the same
  LAN" is a UX expectation set by fiat banking apps. Bitcoin doesn't
  need a new protocol — BLE / NFC just transports BIP21 (on-chain)
  or BOLT11 / BOLT12 (Lightning) payloads instead of QR.
- **Sketch:** Capacitor plugins for BLE and NFC. Send flow gets a
  "Tap to send" affordance for nearby TallyKeep instances; receive
  flow can broadcast a payment URI over BLE / NFC. Falls back to
  QR cleanly.
- **Touches:** Capacitor build, send / receive flows, native
  plugin layer
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Capacitor-only (browser builds can't access BLE / NFC
  reliably). Honest disclosure: it's a transport upgrade, not a new
  protocol — the underlying Bitcoin transaction is identical.

### CoinJoin / PayJoin

- **Captured:** 2026-05 (from module 12 v3, pre-retirement)
- **Motivation:** Privacy-preserving collaborative transactions.
  PayJoin (BIP 78) breaks the common-input-ownership heuristic by
  having the receiver contribute inputs. CoinJoin (Wabisabi or
  similar) lets multiple parties combine into one tx with no shared
  ownership inference.
- **Sketch:** PayJoin first as initiator and responder (smaller
  scope, doesn't require coordinator infrastructure). CoinJoin
  later, likely via integration with an existing coordinator
  (Wasabi, JoinMarket) rather than running our own.
- **Touches:** banking layer, send / receive flows, threat model,
  Blueprint analyzer (CoinJoin output classification)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** This entry covers TallyKeep *initiating* CoinJoin /
  PayJoin. The complementary "Mixed-input transaction flagging"
  entry covers *detecting* collaborative transactions initiated by
  the user's other wallets — both should land coherently so the
  Blueprint analyzer surfaces collaborative-tx outputs distinctly
  rather than mis-classifying them.

### P2P swap routes (RoboSats and similar)

- **Captured:** 2026-05 (from module 12 v3, pre-retirement)
- **Motivation:** P2P venues let users swap fiat for Bitcoin without
  KYC. RoboSats specifically targets the "no exchange account, no
  custody" path that aligns with TallyKeep's posture. As an
  optional swap route alongside CustodialProvider integration, it
  expands acquisition options.
- **Sketch:** New CustodialProvider-shaped adapter pointing at
  RoboSats (or similar) where their API permits. UX-wise more
  ceremonial than an exchange — order matching, escrow lifecycle,
  reputation scores. Likely a separate sub-flow rather than a
  dropdown option.
- **Touches:** treasury layer, adapter abstraction, threat model
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Liquidity at any P2P venue is variable; integration
  has to fail gracefully when no orders match. Regulatory implication:
  KYC-free swap routes vary by jurisdiction.

### Mixed-input transaction flagging

- **Captured:** 2026-05 (from module 13 Q6, pre-retirement; Rémy
  flagged for explicit follow-up so it doesn't fold silently into
  the broader Blueprint / CoinJoin work)
- **Motivation:** When an on-chain transaction has some inputs from
  user-controlled Holdings and some from external sources, the
  default LedgerEntry classification is net-effect-only (OUTGOING
  if balance goes down, INCOMING if up). That hides a meaningful
  pattern: the transaction is likely a CoinJoin, a PayJoin (receiver
  contributing inputs for privacy), or a multi-party split payment.
  The user's categorization options for a "real" outgoing payment
  versus a collaborative transaction differ; squashing them looks
  fine until the distinction matters.
- **Sketch:** Detect mixed-input transactions during chain scan.
  Surface a tag on the LedgerEntry — "collaborative transaction" or
  similar — without changing the LedgerEntry's direction (net
  effect is still net effect). Categorization UI offers
  collaborative-transaction-specific labels alongside the standard
  set. Blueprint analyzer surfaces the count of such transactions
  per Holding.
- **Touches:** chain scanner, LedgerEntry schema (new tag field
  or flag), categorization UI, Blueprint analyzer
- **Status:** sketched (lean from original Q6: don't change
  direction, flag distinctly)
- **Milestone:** **pre-shipping**, after private-ship — sits in the
  personal-use phase, between private-ship and public-ship. Can
  defer to post-shipping if it doesn't surface as friction during
  Rémy's daily-use period.
- **Notes:** Distinct from the CoinJoin / PayJoin entry, which
  covers TallyKeep *initiating* collaborative transactions. This
  entry is about *detecting* them when they happen — including
  cases where the user's other wallet (Sparrow, Wasabi, Phoenix)
  was the one initiating. The detection logic doesn't depend on
  TallyKeep supporting CoinJoin / PayJoin natively.

### Coin selection algorithm review session

- **Captured:** 2026-05 (from module 13 Q7, pre-retirement; Rémy
  flagged for explicit re-review during the consolidation merge)
- **Motivation:** The current default is `BranchAndBound`
  (privacy-preferring), with per-payment override gated by the
  `banking.coin_selection_per_payment_override` feature flag. That
  default was set early in the spec and hasn't been revisited with
  current understanding of fee dynamics, privacy practice, and
  target-market behaviour. Worth a dedicated session before
  public-ship to confirm or change.
- **Sketch:** Walk through the trade-offs across the standard
  algorithms (BranchAndBound, Single Random Draw, Knapsack, Largest
  First) with current data — fee landscape, privacy implications,
  expected wallet sizes for target users. Decide the default plus
  per-profile overrides. If the default changes, document with an
  ADR and update module 06.
- **Touches:** banking layer (coin selection), profiles + flags,
  threat model (privacy implications), tx composition tests
- **Status:** sketched
- **Milestone:** **pre-shipping** — between the private-ship event
  and the public-ship event, during the personal-use phase. Rémy's
  explicit ask: dedicated session in that window.
- **Notes:** Per-payment override is gated behind the
  `banking.coin_selection_per_payment_override` flag — power-user
  territory. The question is whether the *default algorithm* is
  right. Privacy-preferring defaults age well; fee-minimizing
  defaults age noisily.

### Possible Purse / Strongbox collapse

- **Captured:** 2026-05 (from module 13 Q8, pre-retirement)
- **Motivation:** The four-Holding-type model bets that the Purse vs
  Strongbox distinction matters to a real user. The fiat-banking
  parallel — where "checking" and "card balance" collapsed into one
  account view long ago — suggests the bet might be wrong. If during
  the personal-use phase Rémy finds himself choosing one over the
  other arbitrarily, collapsing to a single "user-keys Holding" type
  with a `signing_method` attribute (light vs ceremonial) reduces
  the model to three types and may match how users actually think.
- **Sketch:** Track during personal-use phase. If the distinction
  feels artificial, draft a domain-model migration: collapse Purse
  and Strongbox into a single Holding type with a `signing_method`
  enum. Vocabulary lock means the rename is non-trivial — this would
  need an ADR.
- **Touches:** `02_domain_model.md`, `UI/README.md` Holding
  vocabulary table, every iteration that referenced Purse / Strongbox
  separately
- **Status:** observation-mode (not active work)
- **Milestone:** TBD — only acted on if the personal-use phase
  signals duplication. Likely never; flagged anyway because the
  vocabulary lock is foundational and worth re-examining once.
- **Notes:** Touches the locked "Holdings are first-class and typed"
  principle. Reducing four to three types is itself a re-litigation
  of vocabulary; deserves an ADR if pursued.

### Tor integration

- **Captured:** 2026-05 (from module 13 Q15, pre-retirement)
- **Motivation:** Privacy posture. Self-hosted users running their
  own bitcoind already have the option of Tor-routed RPC; TallyKeep
  itself doesn't currently route its outbound traffic (provider APIs,
  rate feeds) through Tor.
- **Sketch:** Optional, off by default. When enabled, all outbound
  HTTPS requests (CustodialProvider APIs, optional rate feeds) route
  through a configured Tor SOCKS proxy. Recommended in the hardening
  guide; surfaced as a settings toggle.
- **Touches:** networking layer, settings, hardening guide
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Some provider APIs block Tor exit nodes; UX needs to
  fail gracefully and tell the user which provider blocked them.

### Investment layer with structured yield (the "v5" sketch)

- **Captured:** 2026-05 (from module 12 v5, pre-retirement)
- **Motivation:** A constrained, contract-defined alternative to
  the lending / yield zone the spec rejects by default. Multisig
  vaults with discreet log contracts (DLCs) or LSP-mediated
  structures, where the user always retains at least one key and a
  clear unilateral exit path. Distinct from the simpler "Retirement
  plan with timelock" entry — this is yield-bearing under a contract,
  not just a CSV/CLTV lock.
- **Sketch:** A sibling product to TallyKeep's banking app, sharing
  deployment shell and possibly auth (post-public-ship). Own
  database, own threat model, own regulatory analysis. Not a
  generalization of the current banking-app domain.
- **Touches:** new product surface, regulatory analysis,
  legal counsel
- **Status:** idea
- **Milestone:** post-shipping (likely far post)
- **Notes:** Requires legal review before scoping. The question is
  whether enabling these structures from within the app makes us a
  broker / arranger / custodian by some jurisdiction's reading. The
  default reflexive answer is "no"; this entry forces that question
  to be re-asked carefully if pursued. Rejected adjacent: lending,
  borrowing, yield without contract-bound user-key retention.

### Multi-server per single client

- **Captured:** 2026-05 (during onboarding-screen-2 session, when
  Rémy considered whether the server identifier needed to be
  prominent on the paired-confirmation screen)
- **Motivation:** Power-user case for the sovereignty audience.
  Examples: home stack + parents' Umbrel for inheritance management,
  home stack + work-pseudonym stack, home stack + traveling test
  instance. Currently the architecture and onboarding assume
  single-server-per-client (one paired stack, one device credential
  in the Keychain). Extending to multi-server adds non-trivial UX
  surface.
- **Sketch:**
    - **Connect screen extension.** Currently terminal — once paired,
      the user lands on Home. Multi-server adds a Settings → "Paired
      stacks" view + an "Add another stack" affordance that
      re-runs the Connect flow without unpairing the existing one.
    - **Switch-server affordance.** Top-level UI element (likely the
      app bar or a Settings-rooted toggle) for moving between paired
      stacks. Active stack's identifier prominent; inactive stacks
      one tap away.
    - **Per-stack data isolation.** Each paired stack has its own
      device credential, its own observable Holdings, its own
      cached state. The phone holds N credentials; the user picks
      which is active.
    - **Notification routing.** When push notifications land
      (post-Lightning iteration), the notification has to indicate
      which stack it's about — otherwise tapping a notification
      lands on the wrong active context.
    - **Paired stacks server-side.** The inverse problem: the
      server's "paired devices" list shows N devices for the user.
      That part already needs to exist for single-stack
      revocation; multi-server doesn't change the server side.
- **Touches:** mobile UI (Connect, Settings, app bar, Home),
  device-credential storage shape (Keychain entry per stack vs
  array), backend (no change — multi-server is a client-side
  concern, the server doesn't know about other stacks the device
  is paired with), `UI/mobile.md` Onboarding section, future
  notification handler.
- **Status:** idea
- **Milestone:** **post-public-ship** (Rémy's call: "defers to after
  public shipping for sure"). Not blocking for personal-use phase
  or public-ship event. The single-server-per-client model is the
  default and will likely cover the majority of public-ship users;
  multi-server is power-user expansion.
- **Notes:** Onboarding-screen-2 design assumes single-server when
  rendering the paired-server identifier. If multi-server lands,
  the paired-confirmation screen gains an "and your existing
  stack(s)" line, or the Add-stack flow is folded into Settings
  rather than re-running through Onboarding. Defer the design.

---

### Dynamic brand mark on first-touch surfaces

- **Captured:** 2026-05 (during onboarding-screen-1 session, after
  Rémy noted excitement about showcasing the dynamic mark)
- **Motivation:** The brand v1 mark lock doc
  (`brand/tallykeep_brand_mark_v1_lock.html` §5) already implements
  a working tap-to-regenerate-grain interaction (~80 LOC, seeded
  xorshift32 PRNG, both halves regenerate matching stripes — the
  verification metaphor of split tally sticks made tactile, the
  pedagogical heart of the brand). v1 sanctions it for the
  **landing-page hero only**; everywhere else uses the locked
  static seed. Extending the sanction to one or more first-touch
  surfaces in the app would let new users experience the verification
  metaphor at the moment of first arrival, which is structurally
  the same shape of moment as a landing-page hero.
- **Sketch:**
    - **Connect screen (primary candidate, `mobile_onboarding_01_connect.html`).**
      The screen's brand surface is `wordmark-icony` (the wordmark
      with the canonical Y embedded between "tall" and "keep"),
      not the bare icon. Make the whole wordmark area the tap
      target; on tap, only the embedded Y's grain regenerates
      (the "tall" and "keep" text stays static). This is a small
      extension of brand v1 §5, which demoed the dynamic
      interaction on the bare canonical icon — the same seeded
      PRNG and rendering function applies, only the surrounding
      typography changes. v1 → v2 lock-doc bump should explicitly
      sanction the wordmark-icony embedded Y as a dynamic surface
      alongside the bare icon. This is the user's first-touch
      moment in the app; the metaphor lands hardest here, and zero
      additional screen real estate is consumed (the brand mark
      was already going to be there).
    - **Settings → About / How it works (secondary candidate).**
      A dedicated explainer page where the mark is the visual
      anchor for "what tallykeep means as a verification primitive."
      Less time-pressured than the Connect screen, more room for
      the full caption ("The grain matches. A tally stick is split
      from a single piece of wood. The pattern on both halves is
      the proof — that's how you knew it was real.").
    - **Other surfaces** (home page, Holding detail, etc.) stay
      static-mark-with-locked-seed per the current brand rule.
- **Touches:**
    - **Brand:** v1 → v2 lock-doc bump for the mark, updating §5
      "Landing-page interaction" to extend the sanction list. Per
      `PROCESS.md §2.4`, pre-public-ship lock-doc edits are
      allowed without an ADR; v1 → v2 is the convention. Update
      the canonical SVG export in `brand/identity/` if any visual
      detail changes (probably not — the dynamic component reuses
      the canonical geometry).
    - **Frontend:** SvelteKit component implementing the demo from
      §5 of the lock doc. Mockups are static (per
      `UI/mockups/README.md`); the dynamic version lands in code.
    - **`UI/mobile.md` Onboarding section:** note that the Connect
      screen's brand mark is the dynamic variant (when this
      iteration ships).
- **Status:** sketched
- **Milestone:** **TBD** — best guess: pre-shipping (between
  private-ship and public-ship), since the personal-use phase is
  exactly when defining UX patterns get tested against daily use.
  Could also pull forward into the Capacitor / private-ship
  iteration if the wrapping work is touching this screen anyway.
- **Notes:**
    - Discoverability: the demo-hint text ("Tap to verify a new
      pair") in the lock doc is for a documentation context; the
      Connect screen probably wants a subtler hint (a one-time
      pulse on first launch? no hint and trust the affordance is
      noticed?). Sharpen during the iteration.
    - Accessibility: keyboard-activate (`Enter` / `Space`) already
      implemented in the lock doc demo. Carry forward.
    - Animation budget: the lock doc uses an 180ms opacity
      crossfade. Cheap enough on any phone. No perf concern.
    - Content of the seed display ("seed · 7777" in the lock doc
      demo) does not belong on the Connect screen — that's a
      doc-context affordance for the lock doc only.

---

### "Tap to see under the hood" — UI spine pattern

- **Captured:** 2026-05 (mid-conversation, exploring TallyKeep's
  distinctive UI behavior)
- **Motivation:** Bitcoin makes nearly every number a value with
  nuance behind it (balance = pending + confirmed UTXOs;
  confirmation count = probabilistic finality; fee = mempool
  dynamics; rate = source + staleness). Most apps hide this nuance
  to feel clean. TallyKeep's honest-abstraction principle says
  don't hide; this pattern says surface on demand. Strong candidate
  for the product's spine behavior — a behavior flowing through
  every screen rather than a separate feature module. Aligns
  directly with the settlement-rails / confirmation-probability
  idea.
- **Sketch:** every numeric or stateful element is tappable; tap
  surfaces what's behind it.
    - Tap a balance → UTXO breakdown, pending vs confirmed split
    - Tap a confirmation count → probability framing with assumed
      adversary hashpower and natural-orphan baseline visible
    - Tap a fee tier → mempool dynamics, fee distribution,
      expected time-to-confirm
    - Tap a "via [source]" rate attribution → fetch timestamp,
      last N quotes, divergence from another source
    - Tap a security indicator (declared-vs-observable) → the chain
      observation that produced the verdict
    - Tap a Holding type badge → the banking analogy expanded
- **Touches:** every UI surface (this is a spine pattern, not a
  feature module)
- **Status:** sketched — candidate for a defining UX pattern
- **Milestone:** TBD — decision path is mockup iteration. If the
  pattern feels natural after a few screens, becomes pre-shipping
  (defining UX); if forced, drops or scopes down.
- **Open questions (block commit-as-direction):**
    - **Mobile friendliness.** Tap targets are premium on small
      screens; "everything is tappable" risks accidental taps and
      conflicts with scroll/swipe gestures. Maybe restricted to
      specific element types only.
    - **Visual signaling.** How do users know what's tappable
      without cluttering every screen? Options to evaluate in
      mockups: subtle dotted underline on tappable values; a
      consistent color tint on tappable numbers; a single info
      icon adjacent to tappable groups; long-press instead of tap;
      a dedicated "explain mode" toggle that highlights everything
      at once. None is obviously right; each has trade-offs.
    - **Consistency of disclosure.** Every tappable should reveal
      the same SHAPE of info (popover? bottom sheet? inline
      expand?). Inconsistency would feel chaotic.
    - **Discoverability.** If it's the spine, users need to know
      about it. Onboarding mention? First-run hint? Or let them
      discover by accident?

---

### Non-custodial sourcing router (best-execution for Bitcoin acquisition)

- **Captured:** 2026-05 (sparring session captured verbatim in
  `archive/2026-05_parking_notes_sourcing_and_decumulation.md`)
- **Motivation:** Atomic-swap venues (SideSwap, Mostro, Boltz) and
  custodial Accounts are paths to the same outcome — sats into a
  Holding. Building a venue forks scope into protocol territory
  currently being closed by Lightning Labs / Blockstream / Tether-
  Bitfinex multi-year teams. Building a **router** that picks the
  best path per transfer is the wedge: Smart Order Routing applied
  to self-custody Bitcoin acquisition. Reinforces banking-grade
  ergonomics; never asks the user the word "swap."
- **Sketch:**
    - Sourcing path becomes a first-class concept alongside
      `CustodialProvider` Accounts. User sees a single banking-style
      "transfer" UI; routing happens behind it.
    - Evaluator inputs: amount, time tolerance, counterparty
      preferences, depth, current quotes, user's connected providers.
    - Suggested integration order: SideSwap (Liquid PSBT atomic
      swaps — most production-ready) → Mostro (Nostr-based LN P2P)
      → Boltz (quote service for BTC ↔ LN ↔ Liquid) → custodial
      route + immediate sweep (the dev-phase path, becomes one
      input among many).
    - Compliance framing: **"never recustody," not "no KYC."** Most
      realistic users KYC at the on-ramp anyway. The wedge is
      "identity proven once at the on-ramp, funds stay sovereign
      forever."
- **Touches:** treasury layer, domain model (sourcing path
  concept — possibly a new entity), UI sourcing flow, threat
  model, regulatory posture
- **Status:** sketched
- **Milestone:** post-shipping (source notes explicitly v1.5+)
- **Notes:**
    - **Direct competitor on the sourcing side: Peach Bitcoin** —
      mobile-first, Swiss, EU/LatAm/Africa coverage. Different
      wedge (Peach is a venue; TallyKeep would be a router across
      venues + custodial), but the closest market overlap. Study
      feature set and traction before sharpening.
    - **SideSwap caveat:** venue (matching server) is trusted; chain
      (Liquid Federation, ~70 entities) is federated. If single-
      vendor risk matters, build on the open Liquid PSBT swap
      protocol itself (`docs.liquid.net/docs/swaps-and-smart-contracts`),
      with LiquiDEX / TDEX as alternative consumers.
    - **Vocabulary discipline.** "Swap" overloads three different
      things in crypto: (1) atomic-swap primitive (HTLC/PTLC,
      proper finance: DvP with simultaneous bilateral settlement);
      (2) CLOB trading with atomic settlement (SideSwap, Bisq —
      these are *trades*, not swaps); (3) AMM "swaps" (Uniswap-
      style, different design school, doesn't fit the wedge —
      impermanent loss, slippage on size, MEV). Integrate (2);
      skip (3). Worth a vocabulary ADR when this entry sharpens.
    - **Don't build a venue.** Source notes are emphatic — building
      an orderbook fragments solo-builder scope across two
      unrelated hard problems with no compounding leverage. The
      router is the moat; protocols underneath are commodity
      infrastructure to ride on.

### Target-price accumulation (limit-bid sourcing)

- **Captured:** 2026-05 (same sparring session as the sourcing-
  router entry; archive file as above)
- **Motivation:** Once instant-execution sourcing exists, the
  natural follow-on is letting the user post a passive limit bid
  at the price they're happy to buy at, routed to the best venue.
  The fill IS the goal — no adverse-selection problem, no market-
  making risk. Banking-grade framing: **"Set the price you want
  to buy at. We route your bid to the best venue. Fill auto-sweeps
  to Strongbox."** Same liquidity-contribution effect as market-
  makers without the structural risk story.
- **Sketch:** New SourcingPolicy variant (sibling to instant-
  sourcing): limit-price bid posted to the routed venue, listening
  for fill, on-fill triggers auto-sweep to the destination Holding.
  Cancel / amend affordances. Execution-uncertainty disclosure
  honest — bid at X, BTC rallies past X without touching it →
  user watched from sidelines, capital locked. That's the cost of
  being a patient buyer, which is what the target user signed up
  for.
- **Touches:** treasury layer, sourcing-router (blocks on the entry
  above), UI sourcing flow, threat model
- **Status:** sketched
- **Milestone:** post-shipping (sequencable: instant-execution
  router first, limit-price router after — source notes frame as
  v1 → v1.5)
- **Notes:**
    - **Vocabulary lock candidates (sharpen alongside brand voice
      work):**
        - ❌ "Earn the spread" — misleading. Real spread capture
          (50–200 bps on thin books) requires posting both sides
          and getting filled on both = market making. Likely trips
          AMF/CSSF marketing rules in EU.
        - ✅ "Skip the taker fee" — honest. User saves the venue's
          taker fee (typically 0.2%) by being a maker. Fee saving,
          not spread capture.
    - **Do not build market-making.** Onboarding clients into a
      structurally losing game dressed as "earn the maker fee" =
      reputational damage. Strict distinction in source notes:
      target-price accumulation is single-sided and aligned with
      directional view; market-making is two-sided and faces
      adverse selection on thin books.
    - Reference precedents: Strike's "buy the dip," Swan's limit
      orders. Neither does this well in a self-custody, route-
      across-venues shape.

### Decumulation + planning layer (the fourth product layer)

- **Captured:** 2026-05 (same sparring session; archive file as above)
- **Motivation:** TallyKeep's three current layers (savings /
  banking / trading) cover accumulation and current spending.
  They don't cover decumulation — "how do I spend this when I no
  longer earn." Pensions are roughly 70% decumulation, 30% growth;
  current spec is the opposite. Vault-as-pension is **segment-
  dependent**: in high-inflation economies (Argentina, Turkey,
  Nigeria, Lebanon) the Vault IS the pension because the local
  "risk-free fiat asset" doesn't exist; in EU the Vault
  *complements* traditional pension infrastructure (PEA / PER /
  assurance-vie give tax wrappers self-custody can't replicate
  without becoming a PSAN/CASP custodian — which would destroy
  the self-custody thesis).
- **Sketch:** SweepPolicy in reverse, same primitive. Vault /
  Strongbox as source, Account / Purse as sink, scheduled or
  trigger-driven. Three additions beyond raw periodic sweep:
    1. **Buffer layer (bucket strategy from CFP literature).**
       12–24 months of declared monthly spend in stable form
       (Purse, plus possibly a small stablecoin sleeve depending
       on resolution of the "stablecoins as transit" candidate
       principle below). Replenish when BTC is up. Textbook fix
       for **sequence-of-returns risk** — the classic retirement-
       finance failure mode (force-selling stack at the bottom
       during drawdowns).
    2. **Dynamic withdrawal rate.** Even the simple "draw 4% of
       vault annually, recalculate yearly" beats fixed-EUR/month
       substantially. Guyton-Klinger guardrails or variable-
       percentage-withdrawal as a policy layer on top of
       SweepPolicy.
    3. **Tax-aware projection.** France: 30% PFU on crypto capital
       gains. **Show** projected tax events alongside projected
       purchasing power; do not **advise** (configurable
       simulator, not "we recommend X% per year" — that crosses
       AMF rules on personalized financial advice).
- **Touches:** new product layer (significant enough to warrant
  its own spec scope — likely a new top-level concern, e.g.
  concerns/decumulation.md, or a sibling subdirectory to
  `holdings/` / `concerns/` if it grows multi-file; exact module
  shape decided at sharpen time), domain model (SweepPolicy
  direction + new Buffer / WithdrawalRate entities), treasury
  layer (cap-gains tagging in LedgerEntry), UI (calculator +
  planning view), threat model, regulatory framing
- **Status:** sketched
- **Milestone:** post-shipping (far post — needs a population of
  users who have accumulated enough to plan decumulation)
- **Notes:**
    - **Regulatory framing locked in source notes:** frame as
      **configurable calculator + automation the user drives**,
      never as personalized advice. AMF actively polices
      personalized financial advice in France.
    - **"Without any risk" doesn't appear in user-facing copy.**
      BTC has volatility (60–80% drawdowns are historically
      normal), regulatory, and operational risk (lost keys,
      multisig coordination). Source notes flag the language as
      trip-wire for MiCA marketing rules in EU. Candidate brand-
      voice guardrail.
    - Segment-driven UX: Argentine schoolteacher vs French
      employee with a PER have different decumulation needs. The
      planning view exploration for each is itself a sharpening-
      session when this entry promotes.
    - Direct-BTC-payment as a withdrawal path is bonus; off-ramp
      is the realistic default for the foreseeable future (BTC
      direct-pay still <5% of normal household spend even in
      target markets, per source notes).
    - Adjacent to but distinct from the existing "Retirement plan
      with timelock" entry. Timelock is the script-enforced
      lock-period mechanic on a Holding; this entry is the
      consumption-planning layer on top of accumulated Holdings.
      They compose.

### PSD2 / Open Banking integration for fiat-leg verification

- **Captured:** 2026-05 (same sparring session — EU-specific angle
  on the non-custodial sourcing question; archive file as above)
- **Motivation:** Every "P2P BTC-fiat" platform (Bisq, HodlHodl,
  Peach, Mostro) faces the same asymmetry: BTC leg is verifiable
  on-chain, fiat leg isn't — atomicity is cryptographically
  impossible, so they all bolt on a multisig + arbitrator pattern
  resolving fiat disputes socially. **PSD2 Access-to-Account (AIS)
  APIs** let a regulated entity programmatically verify "€X landed
  in this IBAN from that IBAN at this timestamp." Not trustless —
  bank and AISP are trust anchors — but **collapses ~95% of fiat-
  receipt disputes into automated resolution.** No existing P2P
  platform has built this properly. If TallyKeep is EU-domiciled
  and partners with an AISP (Tink, TrueLayer, Bridge by Bud) or
  holds an AISP license itself, there's a real wedge for the
  sourcing-router's EU-fiat-input path.
- **Sketch:**
    - For the EU sourcing-router path on P2P venues: when the user
      receives fiat into their connected IBAN as part of a P2P
      sell-side leg, the AISP integration verifies receipt
      automatically and releases the BTC leg from escrow without
      arbitrator involvement.
    - Two licensing paths: (a) partner with an existing AISP —
      lower regulatory cost, dependency on the partner; (b) become
      AISP-licensed under ACPR — higher cost, fewer dependencies,
      real moat.
    - Honest disclosure: AISP + bank are trust anchors; the
      "atomicity" here is regulatory-grade, not cryptographic.
- **Touches:** treasury layer, sourcing-router (blocks on the
  router entry above), regulatory posture (AISP licensing is a
  real regime change), threat model, new external dependency
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:**
    - **Hostage to the sourcing-router entry sharpening + a
      separate regulatory analysis** of AISP licensing cost (PSD2
      AIS under ACPR in France — the lighter end of the payment-
      services regime; PSP authorization is heavier and not the
      target here). Verify current ACPR / PSD2 framework before
      committing.
    - Why no P2P platform has built it: most are non-EU or pre-
      EU-presence, and the AISP path is real work. This entry is
      what "EU domicile is a wedge instead of a tax" looks like
      for TallyKeep on the sourcing side.

### Taproot Assets on Lightning sourcing (wait-and-watch)

- **Captured:** 2026-05 (same sparring session; archive file as above)
- **Motivation:** Per source notes (verify before relying), USDT
  went live on Lightning mainnet Q1 2026 via Taproot Assets. RFQ-
  based atomic conversion at edge nodes — sender pays USDT,
  receiver gets BTC (or any combination). Settlement on actual
  Bitcoin, open protocol, multiple implementations possible, no
  federation (vs Liquid). Plausibly the future BTC-native trading
  infrastructure; production-grade infrastructure estimated 2–4 years out
  from capture time.
- **Touches:** sourcing layer (eventual), Lightning integration,
  threat model (Lightning custody concerns)
- **Status:** watch-and-wait
- **Milestone:** post-shipping
- **Notes:** Source claim from May 2026 sparring notes; re-verify
  before any commit.
