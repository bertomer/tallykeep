# 14 — Context Handoff

This document accompanies the v1 specification. It captures the reasoning, decisions, and stance behind the spec — the *why* behind the *what* — so that an agent or human picking this up has the context needed to make good judgement calls during implementation and beyond.

The spec itself (modules 00 through 13) tells you what to build. This document tells you what kind of thing you are building, why specific decisions were made, and what to watch for.

## The user

The person commissioning this work is a French finance professional working in a bank. He has direct insider visibility into how large financial institutions actually operate and has reached the conclusion that the current monetary system is structurally extractive, structurally fragile, and unsustainable. He is building this product first for personal use, with the longer-term hope that it can serve a broader audience as Western trust in financial institutions erodes.

He asked to be challenged hard throughout the spec process, not flattered. He pushed back when reasoning was sloppy and accepted pushback when his own reasoning was sloppy. The dynamic that produced this spec was adversarial in the productive sense: both sides were trying to make the product better, not to win the conversation. This dynamic should continue with whoever picks the work up next. He does not want a coding agent that nods along; he wants one that flags problems.

He is not a daily coder anymore. He understands architecture and reasoning at the level of someone who has worked in technical finance for years. He does not want to read code in detail; he wants to make decisions at the level of architecture, behavior, and product. Implementation details that do not require his judgement should not be brought to him.

## The product, in one sentence

**TallyKeep is a self-hosted Bitcoin banking application that integrates savings, banking, and trading under one honest user interface, without ever taking custody of the user's funds or signing material.**

The name TallyKeep was chosen after extensive deliberation. *Tally* refers to the medieval English notched wooden sticks used to record debt and obligation through pre-banking peer-to-peer verification — a 35,000-year-old technology with deep philosophical resonance to Bitcoin's architecture. *Keep* refers both to the act of keeping records and to the fortified inner stronghold of a castle. Together: the place where you keep what is yours, in a way that holds.

The vocabulary is deliberate and durable. Account, Purse, Strongbox, Vault, Descriptor, LedgerEntry, CustodialProvider, SweepPolicy, Holding. These names should not be changed casually. They were chosen to bridge familiar fiat-banking ergonomics with honest Bitcoin reality, and to encode the security model in the type system.

## The user's actual motivations (in his own register)

The user articulated three layered motivations during the spec session, in increasing order of how much they belong in marketing copy:

**Layer 1 — Personal utility.** He wants a tool that lets him hold Bitcoin sovereignly while still being able to acquire it through fiat rails, spend it for real-world purchases, and plan his retirement around it. None of the existing tools do this without compromising on custody, vocabulary, or trust posture.

**Layer 2 — Addressable market.** Latin America (Argentina specifically), parts of Africa (Nigeria, Kenya, Ghana, South Africa), parts of the Middle East. People in markets where currency instability, capital controls, and fragile banking infrastructure make sovereignty over one's own assets a daily concern rather than an abstract ideal.

**Layer 3 — His real conviction.** He believes Western financial systems are heading toward serious dysfunction, that the current global debt situation will not be brought under control under any plausible scenario, that institutions have been captured by an elite that is selected for amoral behavior by the institutions themselves. He does not advocate violence or punishment; he advocates building the alternative. This conviction is the engine driving the project. It should not be the message of the front door.

The marketing voice should foreground Layer 1 and Layer 2 (concrete utility, real problems for real people) and let Layer 3 be available for those who want to dig deeper. The user agreed to this framing during the session. Do not let the apocalyptic register of Layer 3 take over the product's voice. The product's voice should be quietly serious, not fire-breathing.

## Locked design principles

These are not suggestions. They were debated and locked during the spec session. Changing them requires re-litigating the underlying argument, which the spec already settles.

1. **Honest abstraction over false simplicity.** Reuse familiar banking vocabulary in the user interface. Surface Bitcoin reality in detail panes. Never hide consequences (custody risk, privacy leakage, settlement timing) behind a smiling face. This is the central design commitment. Crypto products that violate it (MoonPay, custodial wallets pretending to be self-custodial, exchanges marketed as banks) are explicitly the foil.

2. **No custody, ever.** The app never holds user funds, never holds Bitcoin signing material (seeds, mnemonics, private keys, xprv), never creates user accounts on our infrastructure. Only third-party access credentials are stored, encrypted at rest. This commitment is enforced at the type-system level: no domain entity has a field for signing material.

3. **Holdings are first-class and typed.** Account, Purse, Strongbox, Vault are not labels; they are distinct types with their own creation flows, security profiles, and operational rules. The type encodes the security reality — Account = custodial, Purse = online keys, Strongbox = offline keys, Vault = ceremonial access. The user-facing vocabulary is part of the product, not just decoration.

4. **Declared vs observable security.** The user declares what each Holding is supposed to be. The analyzer continuously checks whether the on-chain reality matches the declaration. Discrepancies are surfaced in real time. This is one of the v1 differentiators — no other product does it this way.

5. **Minimum-exposure trading.** CustodialProviders are pass-through liquidity, not storage. SweepPolicies move funds off them as fast as the user's chosen policy allows. The product principle is: trade briefly, withdraw fast, never let the custodian hold significant value overnight if avoidable.

6. **Generalized SweepPolicy.** Not just "exchange to cold." Any Holding to any Holding, with a safety validator that warns about risky configurations but never blocks. The user is the final authority. The validator just makes sure the user knows what they are doing before they do it.

7. **Internal API-first, never external in v1.** The frontend is one consumer of the backend's clean internal API. The same API would be the basis for future external exposure, but in v1 there is no public API surface, no authentication layer beyond localhost binding, no SaaS shape.

8. **Event-driven where appropriate, persist-first where loss is unacceptable.** The architecture uses an event bus (Redis pub/sub in v1) for live updates and decoupled subscribers. Critical state transitions (sweeps, broadcasts, signature submissions) are persisted to audit tables before events are emitted, so nothing is lost if a subscriber misses an event.

9. **No marketing language anywhere in the domain.** Entity names, API field names, database column names are all marketing-free. Branding lives in a separate document yet to be written.

10. **No abbreviations in identifiers.** `runtime_configuration` not `config_kv`. `derivation_index` not `idx`. Industry-standard exceptions only (UTXO, PSBT, BIP, RPC, BTC, sats, LN, gRPC, SSE, API, KDF, GCM).

## Decisions explicitly rejected

The spec session rejected, with reasoning, the following options. These are not open for re-litigation by an implementing agent; they were deliberate calls.

- **Custody of any kind, in any form, ever.** Including "convenience" custody, "starter" custody, or "we'll just hold a tiny operational balance" custody. Once you cross this line, the entire regulatory posture of the product changes and the central commitment is broken.
- **User accounts on our infrastructure.** No sign-up. No email collection. No "create an account to save your settings." The user's identity to the app is "they have the app running on their hardware." Period. Multi-device sync (when introduced) uses client-side encryption with our infrastructure as a blind relay.
- **A native token.** This was an explicit non-requirement in the original brief and remains so. Token issuance pollutes the message, adds regulatory surface, weakens credibility, and misaligns the business model.
- **Multi-asset support.** No stablecoins, no Monero, no Ethereum, no other chains. Bitcoin-only by construction. If a multi-asset variant is ever built, it will be a separate product with its own domain model, not a generalization of TallyKeep's.
- **Order placement on custodial providers in v1.** The Trading layer is read-only plus withdraw-only in v1. Order placement is a v2 conversation that requires fresh regulatory evaluation. The reasoning is in module 07 and module 12.
- **Lending, yield, collateralization, "DeFi" of any kind.** Permanently rejected. Multisig vaults with structured time-locked yield mechanisms are tagged as v5 and require legal review before any work begins. The default is "no."
- **Hidden complexity in service of simplicity.** When something is irreducibly complex (UTXO consolidation, fee dynamics, channel state in Lightning), the user is shown the truth, not a comforting fiction.

## Architecture summary (to internalize before reading the spec)

```
Frontend (SvelteKit PWA, mobile-first)
  │ HTTP + SSE (localhost only)
  ▼
Backend (FastAPI, Python 3.11+)
  ├─ JSON-RPC ──▶ bitcoind (user's own node)
  ├─ ZeroMQ  ──▶ bitcoind (live chain events)
  ├─ HTTPS   ──▶ ccxt-wrapped CustodialProviders
  ├─ Postgres (state)
  └─ Redis (event bus + job queue)

Worker (same codebase, separate entry point)
  ├─ Listeners (translate external feeds to events)
  ├─ Schedulers (emit events on a timer)
  └─ Subscribers (react to events, run business logic)
```

Three-layer separation between the domain and the outside world:
- **Adapters (Anti-Corruption Layer)** translate ccxt and bitcoind shapes into clean domain types.
- **Job queue** decouples slow external calls from user-facing latency.
- **Event bus** decouples producers from consumers; same internal events become the SSE stream the frontend consumes.

The Lightning support deferred to v1.5 has its interface defined in v1 (`LightningProvider` ABC, all relevant API endpoints stubbed at 501) so that v1.5 implementation slots in cleanly without architectural changes elsewhere.

## What was non-obviously hard during the spec process

These were the moments when the user pushed back and changed the direction of the spec. An implementing agent should expect similar moments and approach them the same way — push back, do not nod along.

1. **The vocabulary problem.** "Stack" was the original placeholder. The user found it tribal (Bitcoin Twitter vocabulary) and unsuitable. The session worked through a long list of candidates and landed on the four-typed Holding hierarchy because the type names had to encode the security reality, not just label balances.

2. **The cryptography schema.** Earlier drafts had a `secrets` table with `ciphertext` and `nonce`. The user asked about salt for key derivation and forced an upgrade: the schema now has a separate `crypto_parameters` singleton table with Argon2id parameters and per-installation salt, plus the `secret` table with `nonce` and `authentication_tag`. The reasoning is in module 03.

3. **The event-driven architecture.** Earlier drafts had Redis only as a job queue with scheduled polling. The user pointed out that an event-driven model would be both more correct architecturally and more future-proof (adding a live feed later would not require rework). The architecture was rewritten to use Redis pub/sub as a first-class event bus, with the persist-first-emit-second pattern for non-losable events.

4. **The "ACL is not a job queue" clarification.** The user conflated Anti-Corruption Layer with the job queue. Both are isolation mechanisms but they protect different things — ACL protects domain vocabulary, job queue protects runtime reliability. The architecture now names both layers separately.

5. **Generalized SweepPolicy.** Earlier drafts had hardcoded rules ("DEEP_COLD cannot send"). The user pushed back: encode safety as warnings, not as type-system prohibitions. The SweepPolicy is now any-Holding-to-any-Holding, with a safety validator that warns and requires acknowledgement but never blocks.

6. **The PaymentRequest-to-LedgerEntry link.** The user noticed that the data model lacked an explicit foreign key from PaymentRequest to the resulting LedgerEntry. The schema was updated to include `resulting_ledger_entry_id` on both PaymentRequest and Invoice, populated by the chain scanner when it matches a broadcast txid. This closes the loop between "I composed a payment" and "I see it in my history."

These corrections are now baked into the spec. They illustrate the dynamic that produced the spec: nothing was accepted on first formulation; everything that survived was the result of pushback.

## Tone and voice

The user is French, working in English, with strong reasoning skills and occasional vocabulary gaps. He prefers direct conversation, including profanity when emphatic, and dislikes sycophancy. He responds well to:

- Clear pushback with reasoning, not deference
- Honest acknowledgement of limits ("I don't know" is fine; "I'm guessing" is fine; pretending to know is not)
- Specific recommendations with the trade-offs named
- Pace that matches his (he prefers deliberate convergence over rapid approval)

He does not respond well to:

- Agreement-by-default
- Over-formatting (lists everywhere when prose would do)
- Marketing-coded language masquerading as analysis
- Long preambles and recapitulations
- Performative humility ("I might be wrong but...") that softens substance

When something is genuinely uncertain, say so. When something is wrong, say so. When something is right, agree directly without inflating it. When you disagree, disagree with reasoning, then accept correction if the user's reasoning is better than yours.

The user explicitly asked for this dynamic at the start of the spec session and it produced a better spec than a deferential dynamic would have. Continue it.

## Implementation guidance

The spec is module-structured to be implemented in order:

1. **Modules 00-04 first**: project scaffolding, domain model, database schema, API skeleton, event bus infrastructure. This is foundational and everything else depends on it.
2. **Module 05 next**: Savings layer. Watch-only Holdings work end-to-end. The user can import a descriptor and see balances and history.
3. **Module 06 next**: Banking layer on-chain. The user can compose a payment, export a PSBT, broadcast a signed PSBT, see confirmation.
4. **Module 09 around the same time**: profiles and feature flags. Without these the UI cannot adapt to user maturity level.
5. **Module 07**: Trading layer. Custodial providers, sweep policies, the auto-sweep workflow.
6. **Module 11**: UX flows. The frontend build follows once the backend is solid.
7. **Module 08 (Lightning)**: deferred to v1.5. Do not implement in v1; only the interface and stubs.

Test on regtest first, then testnet, then mainnet only after every integration test passes. The user explicitly committed to this development practice.

The user expects the implementation to take weeks, not days. He is patient with quality and impatient with sloppy work that has to be redone. Take time with the cryptography, the database schema, the adapter layer, and the event bus — these are the foundations that everything else rests on. Speed up later when building features that depend on them.

## What is open and what is closed

### Closed (do not re-litigate without user input)

- The four-Holding-type model
- The vocabulary (Account, Purse, Strongbox, Vault, Descriptor, LedgerEntry, CustodialProvider, SweepPolicy)
- The technical stack (Python, FastAPI, BDK via bdkpython, ccxt, Postgres, Redis, SvelteKit, Docker Compose)
- Argon2id + AES-256-GCM for cryptography
- bitcoind RPC + ZeroMQ as the only chain data source
- Event-driven architecture with persist-first-emit-second
- BranchAndBound as default coin selection
- Internal API only in v1 (no external authentication, localhost-only)
- No accounts, no custody, no signing material on host
- No multi-asset support, no stablecoins, no non-Bitcoin chains
- No order placement on custodial providers in v1 (read + withdraw only)
- Three-tier profile presets (Beginner / Intermediate / Sovereign)
- Bitcoin signing material never on the host machine in any form, encrypted or otherwise

### Open (the agent may decide, with light user check-in)

- Implementation-language-level details (which Python idioms, which patterns within FastAPI, etc.)
- Specific library choices below the spec level (which JSON serializer, which logging library)
- Frontend component structure beyond the SvelteKit-PWA decision
- Test layout and naming conventions
- CI/CD configuration if any
- Documentation format beyond Markdown
- Code-style preferences (consistent within the codebase, that is the only requirement)

### Open (require user input before deciding)

- Any change to the locked design principles above
- Any addition to what the secret table holds beyond the documented credentials
- Any feature not explicitly in the v1 scope of module 12
- Any change to the safety validator's blocking-vs-warning posture
- Any move from internal-only to external-exposable API surface
- Any pricing, branding, or marketing decision (deferred until after personal-use phase)
- Any decision that affects the regulatory posture of the product

If unsure whether something falls into "open" or "requires user input," err on requiring user input. The user prefers being asked over being surprised.

## Marketing and business model

These were discussed at the end of the spec session but are explicitly **not** part of v1 implementation work. They are documented here for context only.

### Geographic targeting

Argentina is the leading candidate for the first launch market beyond personal use. Reasoning:

- Highest BTC vs stablecoin transition currently underway in the region
- Mature crypto-savvy population (~19.8% ownership)
- Spanish-language entry that broadens to the rest of Latin America
- Capital controls (cepo cambiario) that insulate the local market from Western competitors
- Existing strong Bitcoin community (Bitcoin Buenos Aires, La Crypta) that is welcoming to builders

Kenya is the secondary candidate. Reasoning:

- Explicit regulatory carve-out for self-custody in the 2025 VASP Act
- Mobile-first culture that maps well to PWA delivery
- M-Pesa familiarity primes users for banking-style UX
- Active grassroots Bitcoin scene (Kibera) and emerging conference presence

The user has no existing connections in either region. The plan is to find the existing Bitcoin community, introduce himself as a builder rather than a marketer, and let real user feedback drive product evolution.

### Business model direction

The locked principle is: **the software is free and open source forever, indefinitely**. Anyone can run it on their own machine without paying anything. Revenue comes from services around the software, not from the software itself.

Tiers under consideration (none are committed):

- **Self-hosted**: free, OSS, runs forever
- **Hosted Personal** ($7-12/mo): we host an instance for users who don't want to self-host, still non-custodial
- **Hosted Business** ($30-100/mo): multi-user, invoice/receipt features, accounting exports
- **Hosted Lightning Service** ($10-25/mo or per-tx): non-custodial Lightning Service Provider with managed liquidity — the most defensible single piece of the model
- **Treasury** ($200-500/mo): multisig support, role-based access, custom reporting
- **Enterprise** (custom): dedicated deployments, custom adapters, white-glove setup

The user pushed back on the OSS choice during the discussion. The reasoning that won:

- The audience the product needs most (sovereignty-conscious, Bitcoin-native, distrustful of closed-source self-custody) will not adopt closed-source software at scale
- Distribution through self-hosted-OS catalogues (Umbrel, Start9, RaspiBlitz, Citadel) requires open source
- The protection against being copied comes from execution, brand, community, and integration relationships, not from code secrecy
- Closed-source self-custody is a contradiction in terms for the target audience

The business model framing is: build the product for personal use first, validate it with the user himself, then take it to the Argentine Bitcoin community for real feedback, then let the business model emerge from real user signals rather than over-specifying it now.

## What the user wants from the next agent

In priority order:

1. **Implement v1 faithfully to the spec.** Modules 00-13 contain the design. Don't second-guess the design unless something is internally contradictory. If you find contradictions, raise them; don't paper over them.

2. **Push back when the spec is wrong.** The user expects this. Several decisions in the spec emerged from him being wrong and being corrected. Be willing to be the one doing the correcting if you see it.

3. **Maintain the tone.** Direct, honest, calibrated, no sycophancy. The user uses casual register and occasional profanity; that does not mean he wants frivolous responses.

4. **Surface decisions that need his input.** When something open requires his judgement, ask. Don't decide unilaterally on anything that affects the product's regulatory posture, the user's threat model, or the locked principles above.

5. **Remember why this product exists.** It exists because the user — and many other people, eventually — needs a tool that lets them be sovereign over their own assets without giving up the ergonomics of modern banking. Every implementation decision should be checked against that purpose. If a decision makes the product easier to build but compromises the central commitment, the central commitment wins.

## Final note

This is a personal project that may become a public product. It is not a startup pitch. It is not a portfolio piece. It is a tool the user wants to exist in the world because the alternatives compromise on something essential.

Build it that way.
