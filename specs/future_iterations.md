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
  Vault wizard, then Account wizard.

---

## Open

### Add Holding — Strongbox wizard

- **Captured:** 2026-05 (split 2026-05-13, see Purse-wizard
  entry above).
- **Motivation:** Buffer layer between hot Purse and ceremonial
  Vault. Required for the declared-vs-observable security
  analysis to operate on real cold-storage Holdings in dev phase.
  Rémy specifically uses one personally, so it lands during
  personal-use phase.
- **Sketch:** 4-step wizard, parser shared with Purse watch-only.
    1. *Descriptor input* — framing copy reads "Export an xpub
       from your hardware wallet (Coldcard / Trezor / Ledger /
       Jade) and paste it here. The hardware wallet keeps the
       spending key." Single-address rejected.
    2. *Parse-back* — same component as Purse.
    3. *Label* — default suggestion + optional device-name
       dropdown (Coldcard Mk4 / Trezor T / Trezor Safe 3 / Ledger
       Nano / Jade / Other → free-text).
    4. *Success* — "Signing happens on your hardware wallet when
       you spend. The spending flow ships in a later iteration."
  Reuses the shared wizard shell brought in by the Purse-wizard
  iteration.
- **Touches:** `UI/mobile.md` Add-Holding Strongbox section,
  four new mockup files derived from Purse with adapted copy,
  frontend wizard implementation. Backend already shipped by
  scaffolding iteration. No new shell or bridge work.
- **Status:** sharpened-ready-to-promote
- **Milestone:** pre-shipping
- **Notes:** Promote **second**. Most of the work is copy +
  framing variants on top of the Purse pattern. Per-device export-
  instruction cards (Coldcard / Trezor / etc. step-by-step guides)
  are nice-to-have but deferred to a post-shipping polish
  iteration — the dev-phase user is assumed to know how to export
  an xpub from their hardware.

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

- **Captured:** 2026-05 (from `design_decisions.md` §11, pre-merge);
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

- **Captured:** 2026-05 (from `design_decisions.md` §12, pre-merge)
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
  `mobile_form_factor_decision.md`. If pre-shipping, increases the
  ship-gate scope significantly.

### DCA primitive

- **Captured:** 2026-05 (from `design_decisions.md` §14, pre-merge)
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

- **Captured:** 2026-05 (from `design_decisions.md` §14, pre-merge)
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

- **Captured:** 2026-05 (from `design_decisions.md` §14, pre-merge)
- **Motivation:** Show real value evolution agnostic of currency
  inflation. Differentiator.
- **Sketch:** Holding detail page graph offers an
  "inflation-adjusted" toggle that uses a CPI feed.
- **Touches:** UI holding-detail, new external CPI feed
- **Status:** idea
- **Milestone:** post-shipping

### Retirement plan with timelock

- **Captured:** 2026-05 (from `design_decisions.md` §14, pre-merge)
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

### Multisig descriptor support

- **Captured:** 2026-05 (from module 12, pre-retirement)
- **Motivation:** Pre-shipping ships single-key only; Vault metadata
  exists but the analyzer surfaces a discrepancy honestly.
  Multisig adds first-class multi-key Vault support.
- **Touches:** domain model, banking layer, UI vault flows, threat
  model
- **Status:** idea
- **Milestone:** post-shipping

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
  `mobile_form_factor_decision.md`)
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
  `design_decisions.md` §9 Blueprint analysis)
- **Motivation:** Several persistent items need a shared home so
  the user has one place to see ongoing security concerns, without
  any of them being silently hidden. Includes:
    - Purse seed not backed up (`seed-backup-disclosure`)
    - Strongbox used too frequently for spending (declared vs observable)
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

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Pre-shipping ships Kraken and Bitstamp. Broader
  coverage matters for target markets — Bitfinex has Argentine
  users; Coinbase Advanced has US/EU coverage; LatAm-native venues
  (Lemon, Buenbit, Belo, Ripio) are higher priority for the
  Argentina launch than Coinbase.
- **Sketch:** Each adapter is a ccxt wrapper with adapter-specific
  fixtures and integration tests. LatAm-native venues likely need
  custom adapters where ccxt doesn't cover them.
- **Touches:** treasury layer adapters, integration test harness
- **Status:** idea
- **Milestone:** post-shipping (some may be pre-shipping if a
  specific target-market launch needs them)
- **Notes:** Priority order is market-driven. Argentine launch
  → Lemon, Buenbit, Ripio, Belo first. Bitfinex / Coinbase Advanced
  if user demand surfaces.

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
  target-market behavi