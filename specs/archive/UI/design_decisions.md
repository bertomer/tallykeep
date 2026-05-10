# TallyKeep — Design Decisions

Consolidated as of May 2026. This is the *positive* statement of design decisions emerging from the wireframe iteration phase. It supersedes the earlier `spec_amendments.md` deltas-against-spec file and should be read alongside the v1 spec modules 00–14 (which still hold for everything not covered here).

When this doc contradicts a spec module, **this doc wins for UI/UX matters**. The spec modules will be amended in a subsequent pass.

---

## 1. Product positioning

**TallyKeep is for users who want banking ergonomics on Bitcoin.**

The user we are designing for is someone who understands checking accounts, savings accounts, and safety-deposit boxes — and wants the same mental model for their Bitcoin without the crypto-native friction. They are *not*:

- A Bitcoin power-user who wants UTXO control as the primary interface (Sparrow, Specter, and Electrum exist for them)
- A trader looking for price charts and percentage moves
- A fintech-native who wants their bank to also speculate

We will not bend the design to also serve those users. The sophisticated user who values both can use TallyKeep when they want banking ergonomics and switch to Sparrow when they need descriptor surgery. That's a feature.

This positioning informs every decision below.

---

## 2. Tech stack and architecture

| | |
|---|---|
| Frontend | SvelteKit, served as PWA |
| Backend | Python / FastAPI, deployed via Docker Compose |
| Bitcoin layer | bitcoind (full node) |
| Database | Postgres |
| Cache / queue | Redis |
| Persistence model | Self-hosted in v1; hosted-tier service in v1.5+ |

**Custody commitment (locked):** TallyKeep never holds Bitcoin keys. On-chain: backend is watch-only, descriptors only, all signing happens externally via PSBT export. Lightning: keys live in user's own wallet (own LN node for self-hosted; mobile wallet via Breez SDK or similar for hosted users). The hosted tier preserves this — we run infrastructure, not custody.

**Frontend distribution paths:**
- v1: PWA in browser
- v3: Capacitor wrapper for iOS/Android app stores

These are independent of where the backend lives. Either frontend can connect to either backend deployment (self-hosted or our infrastructure).

---

## 3. Onboarding (validated, parked)

Five screens in this order, **frozen** until we have reason to revisit:

1. **Welcome** — placeholder copy, will evolve with brand voice
2. **Passphrase** + biometric daily-unlock toggle (passphrase stays for setup and recovery; biometric for daily unlock thereafter via WebAuthn)
3. **Hosting choice** — self-hosted vs hosted by us, side-by-side with honest trade-offs surfaced. Hosted greyed-out in v1 with "Coming soon — join waitlist."
4a. **Connection** (self-hosted variant) — bitcoind RPC + ZMQ as today
4b. **Hosted welcome** (hosted variant) — privacy notice + acknowledgment toggle

After step 4, the user lands on the home page. **No "first Holding" wizard step.** The home page itself in its empty state is where the user begins adding Holdings.

**Reference:** `tallykeep_onboarding_validated.html`

### Decisions baked in to onboarding

- Passphrase before hosting choice (cryptography setup is foundational; hosting is a deployment choice)
- Biometric is optional convenience, not replacement; passphrase remains the recovery anchor
- Hosting choice is the most consequential single onboarding question and gets a full screen
- Self-hosted gets a "Recommended for sovereignty" badge — we have a doctrine and surface it
- Privacy notice on hosted welcome requires active toggle acknowledgment, not just a click-through

### Things we will NOT ask at onboarding

- "Are you a beginner / intermediate / sovereign user?" (offensive labels, conflated dimensions)
- "How much detail do you want to see?" (defaults to banking-first, settings-toggle for power users)
- "Where is your Bitcoin currently?" (the home page will handle Holding addition organically)
- "Do you care about privacy?" (contextual prompt on first Strongbox, not upfront quiz)

---

## 4. Home page

The home page is the daily landing. **It is the same page in empty and populated states** — not a separate onboarding artifact. Empty state = first visit; once any Holding is added, populated state takes over.

### Locked design decisions

**Sats are the default unit.** BTC and (optionally) fiat are alternative views toggled by the user. The reason: sats make small amounts feel real (21,000 sats > 0.00021 BTC psychologically) and they're the native Bitcoin unit; fiat is a translation layer.

**Currency consolidation is opt-in via a single dropdown.** Empty selection = no consolidation, sats only. Selected currency = consolidated across all Holdings in that currency. No separate on/off toggle; the dropdown's empty state IS the off state. Default: empty (no consolidation).

**No performance metrics on home.** No "↑ 1.2% today," no daily change indicators, no portfolio-up/down vocabulary. TallyKeep's user is *holding*, not trading. Performance / cost-basis lives on Holding detail pages, especially long-term ones (Vault) — not on the landing.

**Empty state is minimalist, not guided.** A quiet line of text and the four Add affordances. No "Getting Started" checklist. Banking primitives are familiar — the user knows what "add an exchange account" means without a checklist explaining it.

**Rate source surfaced honestly when fiat is on.** Small "via [source] · 2m ago" attribution next to the consolidated value. Not authoritative, transparent about its origin.

### What's on the page (populated)

1. **Unit + currency controls** — small bar above the balance hero (sats by default, dropdown for fiat consolidation, source attribution when on)
2. **Total balance hero** — primary unit large, fiat consolidation as small secondary line if enabled, "across N places" structural meta
3. **Send / Receive** primary actions next to the hero
4. **Holdings table** — type badge, name, balance (sats column always; fiat column shown only when fiat consolidation is on), status indicator
5. **Pending categorization queue** + **Recent activity** as a 2-column section
6. **Security discrepancy banner** — surfaces only when the analyzer finds something

### What's on the page (empty)

1. Same unit + currency controls (visible from start so user knows they exist)
2. Quiet hero text: *"Your stack, all in one place. Add somewhere you keep BTC to begin."*
3. The four Add affordances (same component as populated state's "Add Holding" section)

**Reference:** `tallykeep_home.html` (final version reflects all decisions above)

---

## 5. Profile system

**No named presets.** No "Beginner / Intermediate / Sovereign," no "Simple / Standard / Detailed." Configuration is just configuration; the user never identifies as a preset.

**Banking-first defaults across the board:**
- UTXO views, descriptor expressions, raw transaction hex, hygiene flags: hidden
- Coin control, custom fee rates, RBF, replace-by-fee: hidden
- Trading section: hidden until first Account is added (then auto-enabled)
- Blueprint section: hidden by default, surfaced on first Strongbox/Vault creation via contextual prompt

**One Settings master toggle: "Show technical details."** Exposes the cluster of advanced flags as a group. Power features (custom fees, coin control) remain individual toggles below.

**Contextual feature surfacing replaces the questionnaire:**
- Privacy/Blueprint prompt fires on first Strongbox or Vault creation (skipped for Account-only users)
- Auto-sweep prompt fires on first Account added
- Lightning prompts fire when v1.5 ships

---

## 6. Holding types (locked from spec)

Vocabulary stays as in spec module 02. User-facing descriptions use banking analogies:

| Type | Banking analogy | Description shown to user |
|---|---|---|
| Account | Like an exchange account | Money you've got at a custodial provider that you want to manage from here |
| Purse | Like a checking account | An everyday wallet for spending and small amounts |
| Strongbox | Like a savings account, but you hold the key | A safer spot for medium-term holdings, usually on a hardware wallet |
| Vault | Like a safety-deposit box | A heavily-protected long-term holding, multi-key, used rarely |

The spec vocabulary (Account, Purse, Strongbox, Vault) is preserved everywhere in the UI. Only the *descriptions* in pickers and tooltips use banking analogies for clarity.

---

## 7. Send flow

5-step PSBT flow as specified in module 11:

1. Compose (from-Holding picker, paste/scan address, amount, fee tier, optional description)
2. Review (read-only summary of what's about to happen)
3. Sign externally (export PSBT as file/QR/base64; upload signed PSBT back; "verify destination on signing device" warning)
4. Broadcast
5. Confirmed

Lightning "Instant" tier visible-but-disabled with "coming v1.5" tooltip — honest disclosure of what's coming.

**Reference:** `tallykeep_wireframes_v3.html` screens 5–7 (still valid)

---

## 8. Trading and sweeps

Trading view per spec module 07:

- Per-CustodialProvider panel (connection status, BTC balance, whitelist target)
- Sweep policies as a sub-table (name, trigger, destination, status, edit)
- Recent sweep executions table
- Big "Pause all sweeps" kill switch top-right
- New-sweep-policy creation flow with safety validator (warns but never blocks; user is final authority)

**Reference:** `tallykeep_wireframes_v3.html` screens 10–11 (still valid)

---

## 9. Blueprint analysis

Privacy / hygiene analyzer per spec module 05:

- Three summary tiles (address reuse, dust UTXOs, round-number outputs)
- Severity-tagged recommendations with concrete actions and per-finding dismissal
- v1 ships the four hygiene flags from module 05; v2 adds UTXO clustering graph

Surfaced contextually after first Strongbox/Vault creation. Not in nav by default unless the user opts in (contextual prompt, or Settings toggle later).

---

## 10. Mobile vs desktop philosophy

**These are two different products serving different jobs, sharing a backend.** Not "the same SvelteKit app reflowed."

| Desktop / web | Mobile |
|---|---|
| Operations console | Daily-use surface |
| Setup, configuration, blueprint, sweep policies | Balance summary, send Lightning, receive QR |
| PSBT export to hardware wallets | Notifications, biometric unlock |
| Deep transaction history, accounting export | Quick categorization, in-store payment |
| Things done occasionally and carefully | Things done often and quickly |

### Implications

- **Different feature sets**, not just different layouts. Some features only make sense on one surface.
- **Mobile is a client of the desktop or hosted instance.** Pairing model: phone has read access to all Holdings, spend access only to Purse and the Lightning wallet on the device.
- **Lightning keys live on the phone** for non-sovereign users. Desktop can VIEW Lightning balance and history (via state published to backend) but cannot initiate sends without phone approval (NWC pattern).
- **Empty state on desktop is minimalist**; mobile empty state needs revisiting in mobile context (likely more guided).

**Decision: mobile design is its own track, started later.** The home page and other desktop screens are designed for desktop first. We don't try to make any single decision serve both.

---

## 11. Hosted tier (v1.5+)

Architecturally clean: backend runs on our infrastructure; user's keys remain on their hardware (or in a mobile wallet for Lightning). Privacy trade-off explicitly surfaced at onboarding ("we see descriptors, balances, labels; we never see your keys").

30-day free trial, then $7-12/mo. Pricing tentative.

This is the primary path for the LatAm/Africa target market — phone-only users without a home lab.

**Stub in v1:** "Coming soon — join waitlist."

---

## 12. Lightning (v1.5+)

**Approach: Breez SDK first, evaluate own LSP later.**

- Keys generated and held on the user's device (mobile app)
- Breez (the company) provides LSP infrastructure initially
- We evaluate building our own LSP using LSPS standards (LSPS0/1/2) once volume justifies the operational complexity and capital requirement

For self-hosted users running their own LN node (CLN/LND), backend connects via macaroon/rune. Both desktop and mobile can spend from the user's own LN node.

For hosted-tier users on the LSP path, Lightning is mobile-only for spending; desktop is read-only.

**Stub in v1:** Send screen has "Instant (Lightning)" fee tier visible but disabled with tooltip.

---

## 13. v1 reality status table

| Screen / feature | Status | Notes |
|---|---|---|
| Onboarding (Welcome → Passphrase → Hosting → Connection) | ✅ v1 | hosted choice greyed-out |
| Biometric daily unlock | ✅ v1 | pulled forward from v2 spec; WebAuthn |
| Home page (empty + populated states) | ✅ v1 | |
| Holding types — Account, Purse, Strongbox | ✅ v1 | |
| Holding type — Vault | 🟡 v1-stubbed | metadata stored; only single-key descriptors accepted; analyzer surfaces discrepancy honestly |
| Send (5-step PSBT flow) | ✅ v1 | Lightning "Instant" tier visible-disabled |
| Receive | ✅ v1 | Lightning tab visible-disabled |
| Trading view + sweep policies | ✅ v1 | full functionality |
| Blueprint analysis | ✅ v1 | four hygiene flags from spec module 05 |
| Security analyzer (declared vs observable) | ✅ v1 | five discrepancy kinds from spec module 02 |
| Categorization queue | ✅ v1 | with auto-suggestion when address matches CustodialProvider whitelist |
| Lightning send/receive | ⏳ v1.5 | stubbed throughout v1 UI |
| Hosted tier infrastructure | ⏳ v1.5+ | onboarding choice screen exists; signs say "Coming soon" |
| Mobile companion app | ⏳ v1.5+ | designed track of its own, not started |
| DCA orders | ⏳ v2+ | |
| UTXO clustering graph in Blueprint | ⏳ v2+ | |
| Capacitor native wrapper | ⏳ v3 | |

---

## 14. Parked ideas (not v1, not forgotten)

These came up during iteration. Worth tracking so they're not lost.

- **Equity reference unit** — show stack value in shares of AAPL, gold ounces, etc. Pushes "fiat is a bet on an economy" framing. Flag candidate: `display.unit.equity_reference`. v3+.
- **Inflation-adjusted graphs** — show real value evolution agnostic of currency inflation. Differentiator. v3+.
- **Retirement plan with timelock** — Bitcoin script-enforced lock period for long-term holdings. Touched briefly, deferred to spec's v5 investment layer.
- **DCA primitive** — recurring auto-buy via connected exchange. Spec module 12 puts it in v2; we don't pull it forward unless real-user feedback shows the no-Bitcoin-yet onboarding friction is a launch blocker.
- **Mobile-first design pass** — full second design track, separate from desktop. To be started after desktop is more stable.

---

## 15. Files in this iteration

| File | Purpose | Status |
|---|---|---|
| `tallykeep_onboarding_validated.html` | Five onboarding screens | Frozen |
| `tallykeep_home.html` | Home page — empty + populated states | Final pending one redraw with corrections from this doc |
| `tallykeep_wireframes_v3.html` | Original 12-screen reference (Send, Trading, Blueprint, etc.) | Reference for screens not yet redrawn |
| `tallykeep_wireframes_v4.html` | Onboarding questionnaire experiment | Superseded |
| `tallykeep_wireframes_v5.html` | Banking-first onboarding without questionnaire | Superseded |
| `tallykeep_wireframes_v6.html` | Three-act onboarding | Superseded by validated doc |
| `design_decisions.md` | This file | Authoritative |
| `spec_amendments.md` | Earlier deltas against spec | Superseded by this file |

The v4/v5/v6 superseded files are kept for traceability of the iteration but are not the source of truth.

---

## 16. Open questions

Not blocking, but worth deciding before implementation.

- **Welcome screen voice and brand.** Currently placeholder copy. Needs a brand voice doc.
- **The "no BTC yet" onboarding path.** Spec says no order placement in v1, so the user has to go to Lemon Cash / Bitso / Yellow Card / etc. and come back. Friction for new users in target markets. Decision: accept v1 friction, revisit if launch feedback shows it's a real blocker.
- **Brand colors and visual identity.** Currently using a placeholder amber/orange (#f59e0b). Needs a brand pass.
- **Specific Lightning wallet integrations.** Phoenix? Bitkit? Custom Breez-SDK-embedded? Decision deferred to v1.5 design phase.
- **Pricing for hosted tier.** $7-12/mo placeholder. Needs market sizing against benchmarks (Umbrel, Start9, Casa subscription tiers).
