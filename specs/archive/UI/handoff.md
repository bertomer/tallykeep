# TallyKeep — Chat Handoff

For starting a fresh conversation with compact context. Read this, then load the linked files only as needed.

---

## What we're building

**TallyKeep** — a self-hosted Bitcoin banking app. Banking ergonomics for users who want sovereignty without crypto-native UX friction. Tech stack: SvelteKit PWA + Python/FastAPI backend + bitcoind + Postgres + Redis. Solo project.

**Target markets**: Argentina and select African countries first; EU as regulatory base. **Not** for Bitcoin power-users — they have Sparrow, Specter, Electrum.

---

## Where we are

We just finished an iteration phase on the **desktop UI**. The design decisions are consolidated and clean. We're at a natural pause point.

### Files

Three files matter:

1. **`design_decisions.md`** — authoritative source of truth. Read this first.
2. **`tallykeep_onboarding_validated.html`** — the five onboarding screens, frozen.
3. **`tallykeep_home_final.html`** — the home page, three states (empty, populated-fiat-off, populated-fiat-on).

Other files (v1–v6 wireframes, `spec_amendments.md`) are superseded historical iterations. Skip unless you need traceability.

### Project knowledge files

These are the original spec modules, still relevant for everything not yet redrawn:

```
00_README.md                09_profiles_and_flags.md
01_architecture.md          10_threat_model.md
02_domain_model.md          11_ux_flows.md
03_data_model.md            12_roadmap.md
04_api_surface.md           13_open_questions.md
05_savings_layer.md         14_context_handoff.md
06_banking_layer.md
07_trading_layer.md
08_lightning_placeholder.md
```

When `design_decisions.md` contradicts a spec module, the design decisions win for UI/UX. Spec modules will be amended in a later pass.

---

## What's done

- **Onboarding** — 5 screens, frozen. Welcome → Passphrase + biometric → Hosting choice → Connection (or Hosted welcome alternative).
- **Home page** — empty + populated states. Sats by default. Fiat consolidation as opt-in dropdown. No performance metrics. Banking-first defaults.
- **Positioning** — clear and locked. Not a crypto power tool. Not a trader app. A banking abstraction over Bitcoin.
- **Custody commitment** — locked. Backend never holds keys, on-chain or Lightning. Hosted tier preserves this (we run infrastructure, not custody).
- **Mobile vs desktop philosophy** — established. They're two products sharing a backend. Mobile is its own design track, started later.

---

## What's next — natural options

Pick one. Each is a self-contained chunk.

1. **Add Holding wizards** (the "+" flows behind the home page). Four flows: Account, Purse, Strongbox, Vault. Likely the most natural next step since the home page assumes they exist but we haven't drawn them.

2. **Holding detail page** redraw. v3 had a version; needs to align with banking-first defaults and the fiat-consolidation toggle.

3. **Send flow** review. v3 had the 5-step PSBT flow; works structurally but the labels could be friendlier (e.g. "Sign on your hardware wallet" instead of "Sign externally").

4. **Mobile design pass** — start fresh. The conversation established it's its own product; needs its own wireframes and decisions.

5. **Spec module amendments** — fold `design_decisions.md` back into the formal spec modules so the project knowledge stays canonical.

6. **Brand voice and welcome copy** — currently placeholder. Needs work before a public showing.

7. Something else entirely.

---

## Working agreement

The user wants:
- A sharp sparring partner, not a demolition crew
- Default mode is build mode (draft, design, code) — don't preface every action with skepticism
- Critique mode activates on decisions expensive to reverse — push back even unprompted
- Distinguish *interesting to build* / *should exist* / *viable as product* / *viable as business*
- Numbers, not vibes, when doing market or pricing work
- Honesty over flattery; truth over comfort

The user is French, lives in Pays de Gex, has a finance + software engineering background. Communication in English by default; switch to French if the user does first.

---

## Parked ideas (not v1, not forgotten)

- Equity reference unit (show stack value in shares of AAPL) — v3+
- Inflation-adjusted graphs — v3+
- Retirement plan with Bitcoin script timelocks — spec v5
- DCA primitive — spec v2
- Mobile companion app — design track of its own
- Hosted tier infrastructure — v1.5+
- Lightning (Breez SDK first, evaluate own LSP later) — v1.5+

---

## Open questions worth deciding before implementation

- Welcome screen voice and brand
- Brand colors and visual identity (currently placeholder amber #f59e0b)
- Specific Lightning wallet integrations for v1.5
- Pricing for hosted tier ($7-12/mo placeholder, needs market sizing)
- "No BTC yet" onboarding path — accept v1 friction or pull DCA forward

---

## How to start the next chat

Open a new chat in this project. Paste:

> Continuing TallyKeep design work from previous chat. Please read `design_decisions.md`, `tallykeep_onboarding_validated.html`, and `tallykeep_home_final.html` from outputs. Then we'll pick up with [option from above].

Memory should already carry the basics (project, stack, target markets, positioning) so you don't need to re-explain.
