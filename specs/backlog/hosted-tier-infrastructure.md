# Hosted tier infrastructure

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
