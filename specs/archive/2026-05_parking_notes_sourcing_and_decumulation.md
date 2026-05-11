# Archive — Source parking notes, May 2026

**Status:** archived source material — **not canonical**, not source of truth.

This file is the verbatim parking-notes output from a sparring session
Rémy ran with another agent (isolated from this project) in May 2026.
The session covered non-custodial sourcing, atomic settlement, and
decumulation — far-future TallyKeep architecture, explicitly v1.5+
thinking.

The actionable ideas from this document were captured as entries in
`future_iterations.md` in May 2026. Several candidate locked-principle
items were flagged for separate Rémy decisions (see the integration
summary in the conversation log; not silently folded into canonical
specs per `PROCESS.md` §7).

Kept here for traceability so future agents reading the matching
`future_iterations.md` entries can see the full reasoning their
"Captured" reference points at.

---

# Non-custodial sourcing, atomic settlement & decumulation — parking notes

_Captured from sparring session, May 2026. Far-future exploration for TallyKeep architecture — v1.5+ thinking. **Not v1 implementation.** Verify ecosystem state before relying — Bitcoin space moves fast._

---

## 1. Why atomic fiat ↔ BTC is impossible

The asymmetry: BTC lives in a script the network verifies. Fiat lives in a banking system the Bitcoin protocol can't see. No timelock, no multisig, no "atomic pot" can cryptographically verify a SEPA transfer landed. Atomicity requires both legs to be verifiable in the same trust system.

All "P2P BTC-fiat" systems converge on one of three patterns — variants of _"lock the BTC leg cryptographically + manage the fiat leg socially"_:

1. **Multisig escrow + arbitrator** (Bisq, HodlHodl, Peach). 2-of-2 or 2-of-3 multisig. Fiat dispute → arbitrator breaks tie. The arbitrator IS the trusted third party for the fiat leg.
2. **Lightning hold invoices** (Mostro, RoboSats, lnp2pBot). Seller's BTC locked in a hold invoice. Coordinator acts as dispute referee.
3. **Reputation + collateral** (Bisq DAO model). Make cheating economically expensive via security deposits.

### Current ecosystem (verify before relying)

- **Peach Bitcoin** — mobile-first, Swiss, EU/LatAm/Africa coverage. **Direct competitor in TallyKeep's stated markets.** Study closely.
- **Bisq / Bisq Easy** — desktop + Android (Bisq Easy added simpler UX in 2026). Gold standard for decentralized BTC trading, but liquidity thin outside major pairs.
- **Mostro** — Nostr-based protocol, Lightning-only, federated community model. Protocol-not-app framing is strategically interesting.
- **HodlHodl, RoboSats, AgoraDesk, lnp2pBot, RetoSwap** — variants on the same patterns.

### EU-specific angle: PSD2 + Open Banking

AIS (Account Information Service) APIs under PSD2 let a regulated entity programmatically verify "yes, €X landed in this IBAN from that IBAN at this timestamp." Not trustless — bank and AISP are trust anchors — but collapses ~95% of fiat-receipt disputes into automated resolution. **No P2P platform has built this properly.** If TallyKeep is EU-domiciled and partners with an AISP (Tink, TrueLayer, Bridge by Bud) or gets AISP-licensed, there's a real wedge here. Not v1 work, but worth understanding the regulatory cost before discarding.

---

## 2. Crypto ↔ crypto atomicity actually works

The cryptographic asymmetry vanishes when both legs live in verifiable containers. Production-deployed mechanisms:

- **HTLCs** — hash time-locked contracts, classic primitive
- **PTLCs / adaptor signatures** — Schnorr-based, more private, enables cross-curve swaps (BTC ↔ Monero)
- **PSBT-based offline swaps** — orderbook passes messages, settlement bilateral
- **Lightning hold invoices** — instant settlement

### Current production implementations

- **SideSwap on Liquid** — closest match to "atomic P2P orderbook." Live for years. CLOB structure (bid/offer, maker-taker fees: 0% / 0.2%). Supports L-BTC ↔ L-USDt, L-BTC ↔ L-BTC cross-layer, security tokens. Offline swaps default since 2024 (makers sign once, can go offline). JSON-RPC + WebSocket API for integration. Repo includes a headless Rust "dealer" daemon for automated MM.
- **Taproot Assets on Lightning** — USDT went live on Lightning mainnet March 21, 2026 via Taproot Assets. RFQ-based atomic conversion at edge nodes — sender pays USDT, receiver gets BTC (or any combination). Still alpha; production-ready for orderbook-style trading flows ~12–24 months out. This is the future BTC-native trading infrastructure.
- **Boltz** — atomic BTC ↔ Lightning, BTC ↔ Liquid, Lightning ↔ Liquid. Production. Not an orderbook — quote service. Useful as a sourcing API.
- **AtomicDEX / Komodo** — cross-chain atomic orderbook since ~2018. Marginal volume. Lesson: **atomicity solved, liquidity not.**
- **THORChain / Maya / Chainflip** — NOT atomic. Threshold-signature validator vaults holding pooled assets. Much better liquidity, fundamentally different trust model (trust the validator set). Worth knowing as the alternative design school.

### Trust assumptions you inherit by going crypto-crypto

1. **Stablecoin issuer risk** — atomic swap into USDT gives you USDT. Tether can freeze the address (see §5).
2. **MiCA regulatory exposure** in EU — USDT had a rough 2024-2025 in EU markets. EURC is MiCA-compliant. Argentine market wants USDT specifically. **Two stablecoins for two markets = operational complexity.**
3. **Liquidity is unchanged** — atomicity doesn't summon makers. Same chicken/egg as fiat-BTC books.

---

## 3. Vocabulary discipline ("swap" is doing three jobs)

Crypto uses "swap" for three completely different things. Keep these separate in TallyKeep design language:

1. **Atomic swap (the primitive)** — HTLC/PTLC. Proper finance term: **DvP with simultaneous bilateral settlement.**
2. **CLOB trading with atomic settlement** — SideSwap, AtomicDEX, Bisq. A normal exchange (bids, offers, price-time priority, maker-taker fees). The only difference vs Kraken is that settlement is bilateral on-chain instead of internal-ledger. **It's a trade.**
3. **AMM "swap"** — Uniswap, Curve, Balancer. NOT an orderbook. Trading against a liquidity pool via constant-product formula (x·y=k). No bids, no offers, no spreads. Design school born from on-chain matching being too expensive. Vocabulary collision is unfortunate.

For TallyKeep purposes: integrate CLOB-style atomic-settlement venues. AMMs have a different risk profile (impermanent loss for LPs, slippage on size, MEV/sandwich attacks) and don't fit the wedge.

---

## 4. SideSwap architecture (the venue, not the infrastructure)

Important distinction. SideSwap is NOT a blockchain or open infrastructure. It's:

- **Asset custody**: trustless (your keys, Liquid wallet)
- **Settlement**: trustless (atomic via PSBT on Liquid)
- **Orderbook + matching**: **trusted** — SideSwap's server. If SideSwap goes offline, matching stops. Funds safe, venue dead.
- **Underlying chain**: federated (Liquid Federation, ~70 entities including Blockstream, Bitfinex)

So:
> Lightning : Bitcoin payment infrastructure :: **Liquid + PSBT atomic swap primitives : Bitcoin trading infrastructure**
> SideSwap : a venue on that infrastructure :: Strike : a wallet on Lightning

If TallyKeep wants atomic-swap sourcing without single-vendor dependency on SideSwap, the open layer to build on is **Liquid's PSBT swap protocol** (`docs.liquid.net/docs/swaps-and-smart-contracts`) plus alternative protocols on the same chain (LiquiDEX, TDEX).

Future BTC-native trading infrastructure = **Taproot Assets on Lightning** — open protocol, multiple implementations possible, no federation, settlement on actual Bitcoin. Wait for it to mature.

---

## 5. Stablecoin custody taxonomy (lock into the domain model)

"Non-custodial" is a spectrum, not a binary. Industry conflates this constantly. Load-bearing for TallyKeep design language:

| Tier | Examples | Trust model |
|------|----------|-------------|
| **Bearer asset** | BTC on-chain, Lightning channel funds (with operational caveats) | No issuer, no counterparty — true self-custody |
| **Federated asset** | L-BTC | Consortium custody of the peg by ~70 Liquid Federation members |
| **Issued asset** | USDT, USDC, EURC | Single-issuer custody, freeze powers, regulatory exposure on issuer |
| **Institutional custody** | Kraken / exchange balance | Single-counterparty custody, varying insurance/regulation |

Key insight: **stablecoins have algorithmic freeze powers that regulated banks lack.** Tether/Circle can blacklist your address globally in seconds without due process. Banks need court orders. In the counterparty-risk dimension, USDT is **worse** than a regulated EU bank deposit (which has FGDR insurance to €100k and prudential oversight).

### TallyKeep design rule (proposed lock-in)

> **Stablecoins are transit, never destination.**

Use them to cross from fiat to BTC, sweep out immediately, never present them as a holding the user can rest in. Brief exposure windows (seconds during atomic swap) acceptable. Multi-day/week parking not acceptable. Keeps the "banking-grade self-custody" promise honest. Worth writing into the design principles document next to the locked vocabulary.

---

## 6. Should TallyKeep build trading? — No.

State of the space (verify periodically):
- **Settlement primitives**: solved (TCP/IP-level done — HTLC, PTLC, PSBT swap, Taproot Assets HTLCs)
- **Trading infra maturity**: roughly Lightning circa 2018 — primitives work, network forming, UX bad, liquidity thin
- **Real gaps**: liquidity aggregation across venues, maker tooling (no Hummingbot for atomic swaps), orderbook discovery standards, edge node economics on Taproot Assets, uniformly bad UX
- **Who's closing them**: Lightning Labs, Blockstream, Tether/Bitfinex consortium — multi-year teams, direct stablecoin issuer relationships. Production-grade infrastructure 2–4 years out.

**TallyKeep's wedge is banking-grade ergonomics for self-custody.** P2P atomic trading is structurally the opposite — order placement, fill waiting, prefunding economics, slippage, partial fills. None of that compresses into "credit card UX." Building an orderbook fragments scope across two unrelated hard problems with a solo builder. **Don't do it.**

### Recommended positioning: best-execution sourcing router

Treat atomic-swap venues as one more input alongside custodial Accounts:

- User says "swap 1M ARS worth of USDT to BTC into my Strongbox"
- TallyKeep evaluates: SideSwap depth, Mostro offers, Boltz quote, custodial Kraken route
- Picks best execution given size, time tolerance, counterparty preferences
- Orchestrates PSBTs / Lightning hold invoices / API calls behind a single banking-style "transfer" UI
- **User never sees the word "swap"**

This is **Smart Order Routing applied to Bitcoin sourcing.** TradFi precedent (Reg NMS-era SOR algos in equities). Nobody is doing it well for self-custody Bitcoin. Reinforces the wedge, doesn't fight Lightning Labs / Blockstream on protocol.

### Architectural slot for v1.5+

Leave a "non-custodial sourcing" slot in the architecture next to Accounts. Don't fill for v1 (Account + Kraken sufficient to launch). Slot for v1.5 with:

1. SideSwap as first integration
2. Mostro as second
3. Taproot Assets edge-node integration when production-ready

The router is the moat; protocols underneath are commodity infrastructure to ride on. Each integration is a sourcing path, not a venue.

### Honest framing on compliance

Atomic swap sourcing value is **"never recustody," not "no KYC."** Most realistic users KYC at the on-ramp anyway (Kraken, Lemon, Belo, Ripio, Bitnob). The wedge is _identity proven once at the on-ramp, funds stay sovereign forever_. **Don't sell trustlessness; sell sovereignty after onboarding.** Cleaner, more defensible, and probably truer for the target user.

---

## 7. Market making vs target-price accumulation

Important distinction crypto vocabulary obscures:

**Market making (real sense):** post both sides, capture spread, manage inventory, face adverse selection. Banks have prop desks for a reason. On thin atomic-swap books, retail makers get filled when market runs against them, not filled when it runs with them. The math grinds them down. **Do not build this.** Onboarding clients into a structurally losing game dressed up as "earn the maker fee" = reputational damage waiting.

**Target-price accumulation:** post passive limit bid at the price you're happy to buy at, one-sided, aligned with directional view. The fill IS the goal. No adverse-selection problem. Legitimate banking-grade product. Real precedents (Strike's "buy the dip," Swan's limit orders). Thickens book on bid side as side effect.

### TallyKeep product framing

> **"Set the price you want to buy at. We route your bid to the best venue. Fill auto-sweeps to Strongbox."**

Same liquidity contribution effect as makers, totally different risk story for the client. Sequenceable: instant-execution sourcing v1 → limit-price sourcing v1.5.

### Vocabulary rules (lock into copy)

- ❌ "Earn the spread" — misleading. Would trip AMF/CSSF marketing rules in EU. Real spread (50–200 bps on thin books) requires posting both sides and getting filled on both = market making.
- ✅ "Skip the taker fee" — honest. You save the 0.2% (or whatever the venue charges) by being a maker. That's a fee saving, not spread capture.

The maker-rebate sense and spread-capture sense get conflated by exchange marketing. Don't carry that confusion into UI strings.

### Real costs of single-sided passive orders

Not adverse selection — **execution uncertainty + opportunity cost on locked capital.** Bid at X, BTC rallies past X without touching it, you watched from sidelines with capital locked. Or fills at X then drops further. These are costs of being a patient buyer, which is what the target user signed up for anyway.

---

## 8. Vault-as-pension and the missing fourth layer

User insight (sharp, partly right, segment-dependent): traditional pension plans exist partly to combat fiat decay. If your reserve is BTC and BTC holds purchasing power, the "pension function" may already be accomplished by holding.

### Segmentation

**High-inflation economies (Argentina, Turkey, Nigeria, Lebanon, similar):** Vault IS the pension. The "risk-free fiat asset" doesn't exist for these users. Local pension layer untrusted or destroyed by inflation. BTC volatility may be lower than peso volatility on a multi-year horizon. **Nothing meaningful to add at the investment layer.** Product is "your vault is your future."

**EU/stable economies:** Vault complements but doesn't replace traditional pension infrastructure. Three irreducible gaps:
- **Tax wrapping** — PEA, PER, assurance-vie in France give significant tax advantages on fiat investment. BTC vault doesn't replicate these. Replicating would require PSAN/CASP licenses with custodian status — destroys the self-custody thesis.
- **Cash flow / consumption planning** — pensions provide income. BTC holdings don't unless you sell (CGT events) or earn Lightning routing fees (small).
- **Smoothing** — 60/40 portfolios exist because bonds smooth equity drawdowns. BTC has no native smoothing primitive. "Hold through the drawdown" works mathematically over long horizons but fails behaviorally for most people.

### Honest correction on framing (regulatory)

"Protecting the vault has the same effect _without any risk_" — careful. BTC has volatility risk (60–80% drawdowns are normal), regulatory risk, technical/operational risk (lost keys, multisig coordination). The "no risk" framing trips MiCA marketing rules in EU and is the kind of thing AMF actively polices. **"Without any risk" doesn't appear anywhere in user-facing copy.**

### The actual fourth layer: decumulation + planning (not investment)

Pensions are 70% _"how do I spend this when I retire"_ and 30% _"how do I grow it while working."_ TallyKeep currently has nothing for the spending phase.

**Mechanism: SweepPolicy in reverse, same primitive.** Vault/Strongbox as source, Account/Purse as sink, run on schedule or trigger. Off-ramp path is default; direct-BTC-payment path is bonus for the share that works (still <5% of normal household spend even in target markets, foreseeable future). Architecture rhymes with accumulation — load-bearing primitive already exists.

### Three real additions beyond raw sweep

1. **Buffer layer.** Bucket strategy from CFP literature: keep 12–24 months of expenses in stable form (Purse + small stablecoin sleeve given transit-not-destination rule). Replenish when BTC up. Prevents force-selling stack at the bottom in drawdowns. Sequence-of-returns risk is THE classic retirement problem; this is the validated fix.

2. **Dynamic withdrawal rate.** Fixed-EUR/month fails at extremes. Better: Guyton-Klinger guardrails or variable percentage withdrawal. Even the simplest version ("draw 4% of vault annually, recalculate yearly") is dramatically better than fixed-amount. Policy layer, same SweepPolicy mechanism.

3. **Tax-aware projection.** France: 30% PFU on crypto capital gains. Real retirees should consolidate gains in low-spend years or spread based on tax-band positioning. Don't be a fiscalist — just **show** projected tax events alongside projected purchasing power. More planning than 95% of French households get.

### Regulatory framing

Frame as **calculator + automation that the user drives themselves.** Configurable simulator = much safer ground than "we recommend you draw X% per year," which falls under AMF rules on personalized financial advice. Same regulatory caution as the deflation/risk language.

---

## 9. Open items to revisit

- Verify **Peach Bitcoin's** exact feature set, target-market posture, and traction in Argentina/Africa — most direct competitor on the P2P sourcing side, even if TallyKeep's wedge is different.
- Check **MiCA stablecoin regime** current state before committing to USDT vs EURC in EU offering. Status as of Q1 2026 needs re-verification.
- **PSD2/AISP integration** cost and licensing requirements — viable wedge if operating from France?
- **Mostro integration spec** — what does "TallyKeep as Mostro consumer" actually look like given Nostr relay assumptions?
- **Taproot Assets edge-node economics** — when does this become viable to integrate, and as consumer or operator?
- **Decumulation calculator UX** exploration (no implementation, just shape) — what does the planning view look like for an Argentine schoolteacher vs a French employee with a PER?

---

## 10. Locked principles from this session

- **Stablecoins are transit, never destination.**
- Atomic swap sourcing value is **"never recustody," not "no KYC."**
- "Non-custodial" is a spectrum — bearer / federated / issued / institutional.
- ❌ "Earn the spread" — misleading. ✅ **"Skip the taker fee"** — honest.
- Target-price accumulation ≠ market making. Build the former, never the latter.
- **Don't build a P2P orderbook.** Integrate as a sourcing path.
- Fourth layer = **decumulation + planning, not investment yield.**
- Vault-as-pension is segment-dependent (true in inflation economies, partial in EU).
- **"Without any risk"** doesn't appear anywhere in user-facing copy.
- Trading positioning if pursued: **best-execution sourcing router**, not venue.
