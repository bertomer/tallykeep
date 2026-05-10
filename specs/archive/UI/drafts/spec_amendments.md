# TallyKeep — Spec Amendments

This document captures design decisions and refinements emerging from the wireframe-and-feedback iteration phase. It supplements modules 00–14 of the v1 spec without overwriting them. When a section here contradicts the original spec, *this document wins for UI/UX matters* and the spec module should be updated in a subsequent pass.

Format: each entry is dated, scoped to a module, and has *Concern → Decision → Implications*.

---

## 2026-05 — Onboarding profile model

**Affects:** module 09 (Profiles and feature flags), module 11 (UX flows)

### Concern

The current three-tier preset model (`Beginner` / `Intermediate` / `Sovereign`) has two problems:

1. **The names are off.** "Beginner" implies deficiency-to-be-overcome, which insults users who simply want a streamlined view permanently — including sophisticated users running TallyKeep on their phone for daily-use only. "Sovereign" carries ideological baggage and excludes users who want the full feature set without the political identity.

2. **A single label compresses multiple dimensions.** What the user is actually expressing when picking a preset is a combination of *expertise* + *assets-under-self-custody* + *anticipated usage* + *information-density preference*. These are independent. A user with $100 of BTC who's been a Bitcoin developer for years doesn't need sweep policies (low assets) but does want UTXO visibility (high expertise). The current preset system can't express that combination cleanly.

### Decision

**Drop named presets in favor of a 2- or 3-question onboarding questionnaire** whose answers configure feature flags directly. The "preset" emerges from the answers; the user never identifies as a preset.

#### Question 1 — "Where is your Bitcoin currently?" (multi-select)

Options the user can check in any combination:
- A custodial exchange (Kraken, Bitstamp, Coinbase, etc.)
- A software wallet on my phone or laptop
- A hardware wallet (Coldcard, Trezor, Ledger, Jade, etc.)
- A multisig setup
- I don't have any yet

**Flag derivations:**

| Selection | Flags set to true |
|---|---|
| Custodial exchange | `holding.account.enabled`, `trading.enabled`, `trading.sweep_policy.enabled` |
| Software wallet | `holding.purse.enabled` (default true regardless) |
| Hardware wallet | `holding.strongbox.enabled`, `banking.psbt_qr.enabled` |
| Multisig | `holding.vault.enabled` |
| "I don't have any yet" | `trading.enabled`, plus a "first buy" wizard surfaces the acquisition path. `holding.purse.enabled` to receive once acquired. |

#### Question 2 — "How much detail do you want to see?" (single-select)

- **Just the essentials** — hide the technical bits
- **Standard view** — balanced detail *(default selected)*
- **Show me everything** — UTXOs, derivation paths, raw transactions

**Flag derivations:**

| Answer | UTXO visibility | Coin control | Raw tx | Descriptors | Hygiene flags |
|---|---|---|---|---|---|
| Just the essentials | hidden | off | off | off | off |
| Standard view | shown | off | off | shown | shown |
| Show me everything | shown | on | on | shown | shown |

This is the only question about *taste* — about the UI, not about the user's identity.

#### Optional Question 3 — "Do you care about chain-analysis privacy?" (single-select)

- Yes — flag privacy issues actively
- Show me if I ask
- Don't bother me about it

Drives whether Blueprint is foregrounded in nav, surfaces hygiene warnings in line, etc. **Skippable** — defaults to "Show me if I ask" if not answered.

#### Setup review screen

After the questions, the user sees a "Here's your setup" screen listing the resulting feature flags grouped by category, each with a checkbox. They can toggle individual items, save, and proceed.

The design choice: **no preset name, no preset identity.** The configuration is just the configuration. Users adjusting flags later don't transition to a "Custom" preset (which the original spec triggered) — they just have *their setup*.

### Implications

- Module 09's `PROFILE_PRESETS` constant either disappears, or becomes three named bundles for users who skip the questionnaire and want a quick default. If kept, rename to **`Simple` / `Standard` / `Detailed`** — names that describe the UI, not the user.
- Module 11's onboarding flow gains 2–3 short screens replacing the single "Profile selection" screen.
- Module 09's "preset switching" semantics simplify: there's no preset to switch *from* by default. Users adjust flags in Settings; the system stores whatever set they've chosen.
- The API endpoint `PATCH /api/v1/profile` now takes individual flag overrides as the primary input rather than a preset name. If named bundles are kept, they become a "load these defaults" convenience, not the central abstraction.
- The "Welcome → Pick a profile → Continue" path of the old onboarding becomes "Welcome → Question 1 → Question 2 → (Question 3) → Setup review → Continue."

### Open questions raised by this decision — resolved

- **Should Question 1 also ask about *amount* in some way?** **Resolved: no.** Asking about asset size at onboarding is intrusive. Surface sweep policies always; let small-balance users ignore them.
- **Should "I don't have any yet" force trading to be enabled?** **Resolved: design the ideal flow now, accept the v1 limitation honestly.** See "UX-vs-backend stance" entry below.

---

## 2026-05 — Banking-first onboarding (supersedes onboarding redesign above)

**Affects:** module 09, module 11

### Concern

The 2- or 3-question onboarding from the previous entry was an improvement over the named presets, but it still violates the central product positioning: **TallyKeep is a banking-style interface for Bitcoin, for users who want banking ergonomics, not for users who want a crypto power-tool**. Any onboarding question that quizzes the user about their crypto sophistication contradicts that positioning. The user is here precisely so they don't have to think about UTXOs and privacy and detail levels — at least not at first.

### Decision

**Eliminate the onboarding questionnaire entirely.** Onboarding becomes:

1. Welcome
2. Cryptography passphrase
3. Node connection
4. Set up your first Holding (banking-language picker, then the per-type wizard from spec module 11)

Everything that was a "profile setting" defaults to **banking-first**: technical details hidden, surfaced contextually when the user encounters them, available always via Settings for the user who later wants more.

### Banking-language Holding picker

The four spec types are described in plain banking-flavored language:

| Type | Description shown in picker |
|---|---|
| **Account** | Money you've got at an exchange (Kraken, Bitstamp, Coinbase…) that you want to manage from here. We connect via API to read your balance and trigger withdrawals to your own wallets. |
| **Purse** | An everyday wallet for spending and small amounts. The checking-account equivalent. |
| **Strongbox** | A safer spot for medium-term holdings, usually on a hardware wallet. The savings-account equivalent. |
| **Vault** | A heavily-protected long-term holding, multi-key, used rarely. The safety-deposit-box equivalent. |
| *(special)* I don't have any Bitcoin yet | We'll guide you to acquiring some. *Note: TallyKeep manages BTC you have somewhere; we don't broker the buy.* |

The spec vocabulary (Account, Purse, Strongbox, Vault) is preserved everywhere in the UI. Only the *descriptions* in the picker use banking analogies for clarity.

### Contextual feature surfacing

Features that the questionnaire was going to gate become contextual:

- **Privacy / Blueprint analysis** — surfaced the first time the user creates a Strongbox or Vault. Prompt: *"Strongbox usually holds amounts worth protecting from chain analysis. Want TallyKeep to flag privacy issues automatically?"* Skipped entirely for Account-only users (the exchange has KYC; chain-analysis privacy is moot).
- **UTXO views, raw transaction hex, descriptors, hygiene flags** — all default off. A single Settings master toggle "Show technical details" exposes them as a cluster.
- **Custom fee rate, RBF, coin control** — Settings toggles, off by default.
- **Trading section in nav** — auto-enabled when the user creates an Account; hidden otherwise.

### Implications for module 11

The onboarding flow shortens from "Welcome → Encryption → Profile selection → Node → First Holding" (5 steps) to "Welcome → Encryption → Node → First Holding" (4 steps). The "Profile selection" screen is removed entirely. The "Add your first Holding" wizard gains the banking-flavored descriptions.

### Implications for module 09

`PROFILE_PRESETS` is reduced to a single hidden default applied at first launch — call it `PROFILE_DEFAULT`, banking-first values across the board. Users adjust individual flags in Settings; there is no preset switching. The `CUSTOM` preset concept also disappears, since there's nothing to be "custom" relative to.

### Positioning principle (capture for the marketing/onboarding voice)

> TallyKeep is for users who want banking ergonomics on Bitcoin. The Bitcoin power-user who wants UTXO control, descriptor management, and chain analysis as the primary view is already well-served by Sparrow, Specter, Electrum, and Bitcoin Core's GUI. TallyKeep doesn't try to compete in that space. The sophisticated user who values both is welcome — they can use TallyKeep when they want banking ergonomics, and switch to Sparrow when they need descriptor surgery. That's a feature, not a bug.

This belongs in whatever positioning document gets written before the Argentine community launch.

---

## 2026-05 — UX-vs-backend stance for the iteration phase

**Affects:** wireframe and spec process generally

### Concern

The wireframes are evolving faster than the v1 backend can deliver. The user wants to show the full vision to colleagues and prospective Argentine users without waiting for v1.5 (Lightning), v2 (DCA orders, mobile companion), v3 (native mobile). Question raised: should the UI be perfectly aligned with v1 backend capacity, or should we design the ideal UX and stub out unbuilt parts?

### Decision

**Design the ideal UX. Ship with honest stubs.**

This matches the precedent set in module 11 already — Lightning's "Instant" fee tier is *visible but disabled* with a "coming v1.5" tooltip. Extend that pattern to all unbuilt features.

### Rules for stubs in the shipped product

1. **Visibly disabled, not silently broken.** Greyed-out controls, not regular controls that fail.
2. **Tooltips explain the gate.** "Coming v1.5", "Available when you connect a CustodialProvider", "Requires hardware wallet."
3. **No fake data in the shipped product.** Stub screens show "—" or empty states, not example numbers.
4. **Demo mode is separate.** When showing the wireframes to colleagues or prospects, mark the file as "design preview, some features simulated." When a real user opens v1, every disabled control is honest.

### v1-real vs v1-designed-ahead tracking

A table maintained as wireframes evolve. Each screen / feature has a status:

- ✅ **v1-implemented**: works in shipped v1
- 🟡 **v1-stubbed**: visible in v1 with "coming soon" disabled state
- ⏳ **v1.5+**: not in v1 wireframes-as-shipped, only in design preview

| Screen / feature | Status | Notes |
|---|---|---|
| Onboarding (welcome → encryption → node → first Holding) | ✅ v1 | per spec module 11 |
| Add Holding wizard — Account, Purse, Strongbox | ✅ v1 | |
| Add Holding wizard — Vault | 🟡 v1-stubbed | metadata stored but multisig descriptors v2; analyzer surfaces discrepancy |
| Home screen | ✅ v1 | |
| Send (5-step PSBT flow) | ✅ v1 | Lightning option visible-disabled |
| Receive | ✅ v1 | Lightning tab visible-disabled |
| Trading view (Account + sweep policies) | ✅ v1 | sweep policies fully functional |
| Sweep policy creation | ✅ v1 | with safety validator |
| Blueprint analysis | ✅ v1 | four hygiene flags from module 05 |
| Security analyzer (declared vs observable) | ✅ v1 | five discrepancy kinds from module 02 |
| Categorization queue | ✅ v1 | |
| Lightning section on Purse | 🟡 v1-stubbed | "Not configured · coming v1.5" |
| "Buy first BTC" wizard | 🟡 v1-stubbed | guides user to connect exchange and acquire there |
| Mobile companion app | ⏳ v1.5+ | designed in wireframes, not in v1 build |
| DCA order primitive | ⏳ v2+ | not in wireframes yet |
| Hosted-tier onboarding path | 🟡 v1-stubbed | choice screen exists; "hosted" option greyed with "Coming soon — join waitlist" until v1.5+ infrastructure built |
| Biometric daily-unlock | 🟡 v1-stubbed → ✅ v1.x | spec planned for v2; pull into v1.x since WebAuthn well-supported. Passphrase remains required at setup. |

This table grows as new screens are designed.

---

## 2026-05 — Three-act onboarding (supersedes banking-first onboarding above)

**Affects:** module 09, module 11

### Concern

The "banking-first" onboarding from the previous entry was correct in philosophy but the *structure* still implicitly forced self-hosted mode (asking for bitcoind RPC details right after encryption setup, with no opportunity to choose hosted instead). It also treated Holding addition as a single step, when the actual onboarding goal — borrowed from UBS-style "consolidate your fortune" framing — is to bring in *everything* the user already has so they see their full Bitcoin position in one place.

### Decision

Restructure onboarding into a clean **three-act narrative**:

#### Act 1 — Setup

1. **Welcome**
2. **Hosted or self-hosted?** — the most consequential single question in the product. Trade-offs surfaced honestly.
3. **Encryption** — passphrase required, biometric daily-unlock optional toggle.
4. **(If self-hosted)** Bitcoin node connection — bitcoind RPC + ZMQ as today.
   **(If hosted)** "Your hosted instance is ready" — privacy notice (we see descriptors and metadata; we never see keys), trial info.

#### Act 2 — Consolidation

5. **"Let's see your full picture"** — Holding wizard reframed as a multi-add experience. Encourage adding *every* place the user has BTC: exchanges, wallets, hardware. Running tally shows total as Holdings are added. "I'll add more later" exit available, with an honest "your total only reflects what you've connected" caveat.

#### Act 3 — Optimization (deferred to contextual prompts, not part of onboarding)

6. **Auto-sweep prompts** — surface the first time the user adds an Account. "You've connected Kraken. Auto-sweep keeps the balance moving to your own wallets — want to set one up?"
7. **Privacy / Blueprint** — surface the first time the user adds a Strongbox or Vault. (Already designed in v5.)

### The hosted vs self-hosted question

The choice screen surfaces four real trade-offs honestly:

| | Self-hosted | Hosted by us |
|---|---|---|
| Cost | Free forever | 30-day trial, then $7-12/mo |
| Setup | Run Docker, configure bitcoind | Sign in, done |
| Privacy | Perfect — your data never leaves your machine | We see descriptors, transaction labels, balances. Never your keys. |
| Lightning | You run your own LN node | We run the LSP infrastructure |
| Geographic fit | Wealthy users with home labs | Mobile-first users in any market |

The screen does **not** flatter either option. Self-hosted is harder; hosted is less private. The user picks based on what they value.

### Biometric daily-unlock

Pulled forward from v2 to v1.x. Pattern:

- **Setup**: passphrase required (Argon2id key derivation as today). Toggle: *"Use [Touch ID / Face ID / Windows Hello] for daily unlock?"* Default: on if available.
- **Daily use**: biometric unlocks the in-memory key (the encryption key is stored in OS secure hardware, accessed via WebAuthn). No passphrase typing.
- **Recovery**: passphrase remains the only path. Biometric stops working on device change, OS reset, or repeated failures.

Implemented via the WebAuthn API (built into modern browsers; works in Capacitor wrappers; supported on Linux via fido2-l). Implementation work isn't large; it's a v1.x candidate.

### Consolidation framing

The Holding wizard pivots from "add your first" to "add what you have." UI changes:

- Header: *"Let's bring everything together"* with a running tally (currently 0.00000000 BTC across 0 places).
- Each Holding type is presented as an "Add" action, not a one-time pick. After adding one, the user lands back on a "Add another?" screen showing what they've connected so far.
- The exit button is *"I'll add more later — show me what I've got"*, not "Skip." Honest about what they're trading away.
- After at least one Holding is added, a "Done" button takes them to the Home screen with their full picture surfaced as the centerpiece.

This matches how people actually onboard to wealth-management apps. UBS, Empower, Mint, Personal Capital all use this pattern: *"connect everything you have, then we'll show you the consolidated view."*

### Implications for module 11

Onboarding flow grows from 4 steps to 5 (with branching on step 4):

- Welcome → Hosted/Self-hosted → Encryption → Node-or-hosted-welcome → Consolidate Holdings

Step count is the same as the original spec but the structure is meaningfully different.

### v1 reality

- Hosted option in step 2 is greyed-out with "Coming soon — join waitlist" until hosted infrastructure ships.
- Self-hosted is the only working path in v1 personal-use phase.
- The *choice screen exists* from day one so the structure communicates what's coming.
