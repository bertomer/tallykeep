# Pre-implementation arbitration

Items requiring a dedicated arbitration session before they can be
folded into `next_iteration.md`. Different tone (Rémy's decision,
with reasoning), different autonomy (no coding agent should guess
these).

Each has a recommendation. Rémy decides, dates, and the item
**leaves this file**:

- Foundational decisions land as ADRs in `decisions/`.
- Implementation work moves to `next_iteration.md` (if active) or
  a new file in `backlog/` (if deferred; per ADR-0014).
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

### `sweep-validator-extended-rules`

**Status:** open (deferred to brainstorm after the four Holding
types are working end-to-end in code)

**Item:** What additional warnings, beyond `no_maximum_cap_set`
and `unverified_whitelist_on_provider`, should the SweepPolicy
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
flows for each (Account to Strongbox, Purse-on-device to Strongbox,
Strongbox to anywhere, Vault to anywhere), the warning categories
will be either over-specified or wrong.

**Direction to keep in mind for the brainstorm:**

- The locked discipline is **warn don't block**, the validator
  makes sure the user knows what they're doing; it does not
  second-guess.
- Two patterns Rémy named worth designing against: *saving while
  working* (income to Account to auto-sweep to Strongbox; Strongbox
  to Purse top-up) and *spending while retiring* (Strongbox to
  Account to manual sell). The validator shouldn't treat one as
  more legitimate than the other.
- A potential third pattern: *static address reuse for recurring
  payments* (rent recipient, family, etc.), a banking-IBAN
  analogue. Touches `backlog/receive-in-static-merchant-mode.md`
  and `backlog/contact-book-saved-counterparties.md`.
  Worth thinking about whether sweep-policy destinations should
  be addresses-not-Holdings for those flows.

**Decision:** ___ (pending session after four-Holding scaffold)
**Decided on:** ___

---

### `purse-upgrade-path`

**Status:** open (structural question only; design work
captured in `backlog/purse-upgrade-path-watch-only-on-device-imported.md`)

**Item:** When upgrading a `WATCH_ONLY` Purse to spendable by
importing the source wallet's seed, is `purse_mode` mutable in
place (`WATCH_ONLY` to `ON_DEVICE_USER_IMPORTED`), or do we
preserve the original mode and add a separate
`spending_capability` flag on the Holding?

This is structural: it shapes domain invariants (rule 10 in
`02_domain_model.md` summary; ADR-0006 preceded this
discussion and implicitly assumed `purse_mode` immutability).
The two paths have different consequences for migration,
analyzer logic, and the security-health framing of upgraded
Purses.

**Leading direction:** `purse_mode` mutable along the
`WATCH_ONLY to ON_DEVICE_USER_IMPORTED` axis only, already
encoded as target shape in `02_domain_model.md` invariant rule
10, pending this arbitration's formal close. The alternative
(separate `spending_capability` flag) adds a second axis the
analyzer and UI must reconcile; the supposed benefit
(preserving original-mode-as-history) isn't load-bearing
because git already preserves history.

If `purse_mode` is mutable, ADR-0006 needs an editorial note
or amendment recording the relaxation.

The downstream design work (upgrade-flow UX, disclosure copy,
double-spend UX timing, Capacitor gate posture) lives in
`backlog/purse-upgrade-path-watch-only-on-device-imported.md`
and sharpens once this arbitration closes.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `multi-asset-aggregation`

**Status:** open

**Item:** The "no multi-asset" line in the canonical out-of-scope
list rejects custody of stablecoins, Monero, and non-Bitcoin
chains, that part is firm and tied to regulatory surface. But
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
  home page's "Total: 0.52 BTC" becomes ambiguous, does it
  include the USDT? If it does, in what unit and at what rate? If
  it doesn't, the user has to do the math themselves.
- **Vocabulary.** TallyKeep's locked vocabulary (Holdings,
  Account, Purse, Strongbox, Vault) is BTC-centric. Multi-asset
  Holdings would either fragment the vocabulary or force a new
  "asset" axis on every Holding type.
- **Custodial-only.** Non-BTC aggregation is *only* possible at
  the Account level, Purse / Strongbox / Vault don't apply
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
3. *Reject, stay strict BTC-only.* Maintains vocabulary purity
   at the cost of practical visibility for the target market.

**Leading direction:** None yet. Rémy explicitly opened the
question during the consolidation merge after pushing back on a
proposed ADR that would have locked the rejection.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `brand-canvas-vs-narrative-split`

**Status:** open (deferred, depends on palette stabilising)

**Item:** `brand/README.md` "Lock-doc pattern" currently bundles
narrative and live data into a single lock-doc per brand artifact. During the May 2026
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
- Lock docs become narrative + anatomy + decisions log only,
  prose about why the brand is what it is, without re-stating
  the data. They reference the canvas for "what does it look like
  right now".
- New brand-artifact pattern: each canonical artifact (mark,
  wordmark, future lockup) gets a markdown narrative doc; the
  canvas is the cross-artifact data view.

**Why deferred:** premature to restructure while the palette is
still in flux. If the verdigris direction reverses or shifts, the
restructure work would partly redo itself. Lock-step the ADR with
the brand v1 to v2 bump if/when verdigris-on-cool is adopted.

**Open part, full session needed:**

- ADR copy: rules for what goes in canvas vs. narrative.
- Migration plan for the four existing v1 lock docs (rewrite as
  narrative-only, or keep as v1 historical and start fresh
  narrative for v2).
- Identity SVG question (`brand/identity/*.svg` currently hardcode
  Aged Oak; only inline SVGs with class hooks follow tokens.css).
  Decision: rewrite identity SVGs to use class-based fills (more
  flexible, requires consumers to inline rather than `<img>`), or
  keep hex-baked and regenerate per brand version (matches
  `brand/README.md` brand to tokens lockstep more cleanly).
- Whether the canvas should additionally expose non-color tokens
  (type, spacing, radius, shadow) in v2.

**Recommendation:** keep the canvas + lock docs coexisting until
brand v2 ships; do the restructure ADR as part of the brand v1 to
v2 bump iteration. Do not redo the canvas-vs-lock-doc split as a
standalone iteration, fold it into a "brand stabilises" iteration.

**Decision:** ___ (pending session, blocked by palette adoption)
**Decided on:** ___

---

### `per-pod-stack-architecture`

**Status:** open (decision deadline: before the public-ship event
ships; a Postgres to SQLite move after running self-hosted instances
exist is significantly more painful than before)

**Item:** Single-tenant single-user pods are the locked deployment
shape, one pod per user, both self-hosted and hosted-tier, never
multi-tenant. Given that shape, should the per-pod stack stay on
Postgres + RQ worker + Redis (current) or migrate to SQLite +
in-process background tasks + no Redis (lighter)?

The current stack was proposed early in the project and has shipped
through every iteration so far. The single-tenant-pod commitment +
the locked banking-grade reliability principle make the lighter
alternative a coherent optimization for both deployment modes
simultaneously, denser hosted-tier pods (lower per-user cost at
scale) AND lighter self-hosted footprint (better fit for Pi-class
hardware, fewer processes to fail).

**Best-guess footprint comparison (must be validated by benchmark,
not source-cited):**

- Current stack per pod: ~800 MB - 1.2 GB
- Lightened stack per pod: ~150-300 MB
- 3-5x density improvement on hosted-tier; comfortable headroom
  on a Pi 4 instead of constrained
- bitcoind / indexer is external in both cases and not counted in
  per-pod weight

**Tensions:**

- *Postgres to SQLite migration:* shipped schema uses JSONB for
  `subtype_data`, partial indexes for filtered queries, the
  `MISSING` sentinel for partial JSONB updates, Alembic migrations.
  SQLite has approximations, JSON1 extension, partial indexes since
  3.8, but not drop-in. Real refactor work, best-guess 1-3 weeks of
  focused effort depending on how entrenched the patterns are at
  migration time.
- *Worker collapse:* moving custodial polling from RQ to FastAPI
  in-process background tasks loses RQ's job retry semantics and
  process isolation between web requests and polling cycles.
  Single-tenant single-user means the polling load is bounded (1-3
  custodial accounts, 60s interval) so this is acceptable but the
  failure modes need conscious design (in-flight cycle on restart,
  exception isolation, slow custodial API affecting web latency).
- *Redis removal:* SSE pub/sub moves to in-process asyncio channels;
  queue infrastructure disappears entirely. Cleaner, but a single
  failed FastAPI process drops all SSE consumers for that pod.
  Tolerable for single-user-per-pod.
- *Operational tooling regression:* Postgres has
  `pg_stat_statements`, `EXPLAIN ANALYZE`, mature query-plan
  inspection. SQLite has less. Debugging a perf issue on a Pi pod
  under SQLite is harder. Trade-off, not a blocker.

**Cost trajectory of continuing on current stack:**

- Frontend / UI iterations: zero migration cost.
- Pure business-logic iterations: minimal cost.
- Backend-schema iterations (new tables, JSONB columns,
  Postgres-specific patterns): real but bounded cost, best guess
  1-3 days of additional migration work per iteration. Compounds
  linearly with backend-schema additions.
- After public-ship: cost crosses from "engineering work" into
  "support disaster" (data migration on running self-hosted
  instances). This is why the deadline is the public-ship event.

**Leading direction:** migrate to the lighter stack before the
public-ship event. Sequence the migration AFTER a benchmark
iteration that (a) validates the density estimate isn't optimistic,
(b) surfaces failure modes theoretical analysis misses, and (c)
produces the metrics infrastructure that
`backlog/self-hosted-operational-reliability.md` dimension 2
(mobile-app server-health view) needs anyway. The benchmark serves
three purposes simultaneously, one investment, three payoffs.

**Open part, full session needed:**

- Whether the migration is the next backend iteration (minimizes
  future migration debt, delays Send/Receive feature work by ~2-3
  weeks) or runs after Strongbox Send + Receive (lets the
  immediate-value iteration ship first; accepts the ~1-3 days of
  additional migration cost from that iteration).
- Whether SQLite WAL-mode performance under SSE-heavy workload is
  acceptable for the pod's actual workload, needs measurement, not
  theoretical reasoning.
- How the migration handles the Postgres-specific patterns:
  refactor schema access patterns directly to SQLite-compatible
  shapes, or extract a thin storage-adapter layer that supports
  both backends (the latter preserves optionality but doubles test
  surface for every write path).
- Whether the lightened stack is the choice for hosted-tier too,
  or whether hosted-tier diverges back to Postgres for
  operational-tooling reasons. The "two stacks behind one codebase"
  cost is real; one stack across both is the simpler commitment.
- Benchmark scope: which metrics matter most (RAM peak +
  steady-state, query latency p50/p99, SSE message latency, restart
  time, disk usage growth, cold-start time on Pi-class hardware),
  what represents a "real" workload (synthetic enough to be
  reproducible, realistic enough to catch issues), and where the
  metrics endpoints land (these are the same endpoints the
  operational reliability layer's health-view needs, per cross-ref
  above).

**Decision:** ___ (pending session, deadline: before public-ship
event commits)
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
| `psbt-by-qr-mobile` | `backlog/psbt-by-qr-roundtrip-on-mobile.md` | Deferred; no foundational decision |
| `categorization-queue-mobile` | `UI/README.md` Activity section, `backlog/push-driven-categorization-workflow.md` | Decided + deferred parts each found their canonical home |

Slugs are preserved by the receiving ADR's "Migrated from" header
so existing back-references in canonical docs still resolve.

This log is one-time. Future closed items leave the file directly;
no log accumulates.
