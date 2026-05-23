# ADR-0018 — Vault is long-term by type; `Purpose.LONG_TERM` retires

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during the Vault-detail-page brainstorm session
- **Extends:** ADR-0010 (Vault type definition + Vault Send deferral)

## Context

ADR-0010 redefined Vault as the friction-bearing Holding — a wallet
whose spending requires intentional friction (script-enforced
timelock, multisig coordination, or both). Under that definition,
"Vault" already encodes the long-term-storage intent at the type
level: every Vault is, by construction, a wallet the user has
deliberately put away.

The pre-existing `Purpose.LONG_TERM` enum value carried the same
intent at the per-Holding tag level, separately from type. Its
load-bearing use was the **outgoing-payment guardrail** in
`concerns/outflow.md`: Vault PaymentRequests with `purpose=long_term`
returned `requires_confirmation=true` and forced an explicit "yes, I
intend this" modal before the PSBT path proceeded. Vaults without
the `long_term` tag bypassed the guardrail.

The Vault-detail brainstorm surfaced the redundancy. If Vault is
defined as friction-bearing storage, every Vault is long-term by
type; the `LONG_TERM` tag is a flag the user sets to mark something
the type already declares. Carrying both is duplication, with two
failure modes:

- The user creates a Vault but forgets to set `purpose=long_term`,
  and the guardrail silently does not fire on the very Holdings it
  was designed to protect.
- Some Vaults have the tag and others do not, and the user-mental-
  model contract ("Vaults warn you before you spend from them")
  becomes unreliable.

Both are symptoms of "the type already says this; the tag is
redundant."

## Decision

**Three-part decision:**

1. **`Purpose.LONG_TERM` is retired.** The enum value is removed
   from `02_domain_model.md`. The `purpose` column CHECK
   constraint in `03_data_model.md` drops `'long_term'`. The
   `purpose` field itself stays on `Holding` — the other four
   values (`SPENDING`, `RESERVE`, `TRANSIT`, `UNDECLARED`) remain
   live for the Fortune-view breakdown by purpose
   (`concerns/observation.md`) and any future per-purpose
   slicing.

2. **The Vault outgoing-payment guardrail fires on every Vault
   Send.** The `purpose=long_term` precondition is removed in
   `concerns/outflow.md` and `holdings/04_vault.md`. Vault
   `PaymentRequest` creation returns `requires_confirmation=true`
   unconditionally for any Vault source Holding. The user-final-
   authority feature flag `banking.vault_outgoing_warns` still
   governs whether the warning fires at all (default `true`;
   users can opt out from Settings). Currently unreachable
   because Vault Send is deferred (ADR-0010 §pre-shipping); becomes
   reachable when Send ships.

3. **Treasury-style Vaults are an escape-hatch user story, not a
   default.** A 2-of-3 multisig used as a family business
   treasury (frequent outflows, no timelock) is technically a
   Vault under ADR-0010's friction-as-type definition. For that
   user the always-on guardrail is annoying. The escape hatch is
   the existing user-final-authority feature flag — they disable
   `banking.vault_outgoing_warns` from Settings. A per-Vault
   "disable guardrail" toggle is **not** built proactively; if a
   real user surfaces the use case post-shipping, it lands as a
   small per-Holding setting and an opt-out marker.

## Reasoning

### Why retire the flag rather than keep it

1. **Type definition is the right home for "this is long-term."**
   ADR-0010 made friction-as-type-axis the substantive call;
   `purpose=long_term` is a parallel tag that re-declares what
   the type already says. Two declarations for one fact is the
   shape of bugs.

2. **The guardrail is most valuable when the user is least
   expecting to spend from a Vault.** A user who never set the
   tag is exactly the user who needs the warning to fire — they
   built a Vault for long-term storage but never thought to tag
   it. Conditional firing optimises for the wrong case.

3. **No vocabulary cost.** Removing one enum value is a smaller
   surface change than introducing a new field would be. The
   broader `purpose` field stays for the legitimately
   cross-cutting uses (Fortune view by purpose, possibly future
   per-purpose UI).

4. **The brainstorm's anchoring instinct.** Rémy's read at the
   moment of arbitration was "not sure we'll keep this long-term
   purpose anyway, but Vault is clearly a long-term Holding."
   That instinct is the spec-side signal that the tag was
   carrying weight the type should own.

### Why fire the guardrail on every Vault Send

1. **User mental model is "Vault = the safe."** Banking
   ergonomics: when the user moves money out of the safe, the
   teller asks "are you sure?". Conditional firing breaks the
   contract.

2. **User-final-authority is preserved.** `banking.vault_outgoing_warns`
   is a feature flag the user can disable from Settings (per the
   warn-don't-block discipline TallyKeep uses for all
   final-authority decisions). Disabling is a deliberate act,
   not a default-off blind spot.

3. **The corner case (treasury Vault) has a clean opt-out.** The
   feature flag is the right surface. Adding a per-Vault toggle
   before the corner case surfaces is YAGNI.

### Why narrower options were rejected

- **Keep the flag, default to ON for new Vaults.** Half-measure;
  still leaves "did I tag this right?" anxiety surface and still
  two declarations for one fact.
- **Retire the whole `purpose` field.** Too broad; `purpose` is
  used by the Fortune-view breakdown across all Holdings, which
  is a legitimate cross-type display feature. Surgical cut is
  better.
- **Retire the guardrail entirely.** Loses the user-discipline
  mechanism. The point of a friction-bearing type is that the
  app reinforces the friction at decision time.

## Consequences

- `02_domain_model.md` — `Purpose.LONG_TERM` removed from the
  enum; the surrounding prose updated.
- `03_data_model.md` — `purpose` column CHECK constraint drops
  `'long_term'`. `idx_holding_purpose` index stays (column stays;
  one fewer value). Migration is a CHECK-constraint redefinition;
  per ADR-0017's precedent and ADR-0003's personal-use phase,
  Rémy will reset the dev DB rather than write a data migration
  for the single `LONG_TERM` row that may exist.
- `concerns/outflow.md` — guardrail precondition rewritten:
  Vault `PaymentRequest` returns `requires_confirmation=true`
  for any Vault, governed by `banking.vault_outgoing_warns`
  alone.
- `holdings/04_vault.md` — `purpose` removed from Vocabulary
  detail; the "Outgoing-payment guardrail" section rewritten to
  fire on every Vault Send; the `purpose=long_term` references
  in Send-flow prose stripped; the soft-declaration-rejection
  paragraph rewritten to no longer reference `purpose=long_term`
  as the carrier; the deferred-table row for usage-based-feedback
  rephrased (no declaration to compare against; the analyzer
  watches every Vault's outflow frequency against a type-implied
  baseline of "rare").
- `backlog/usage-based-feedback-for-long-term-vaults.md` —
  reframed: with no `purpose=long_term` tag to compare against,
  the analyzer compares observed outflow frequency against the
  type-implied baseline (Vaults are friction-bearing storage; a
  Vault with weekly outflows is signal to surface as a
  security-health item). Renamed in spirit to "usage-based
  feedback for Vaults"; the filename stays for now (per
  PROCESS.md §4.5: not a vocabulary axis worth renaming
  filenames around).
- `api/openapi.yaml` — `Purpose` enum schema regenerates on the
  next coding iteration that touches `purpose`. No URL or path
  changes; an enum-value removal is a schema delta. Will appear
  in the Send + Receive iteration's OpenAPI regen.
- The Vault-detail iteration sharpened in
  the Vault-detail-page iteration (active in `next_iteration.md`
  from 2026-05-22) ships **without** a
  `purpose=long_term` Setting affordance on Vault detail. The
  Settings card that would have hosted it is not built. The
  Vault detail Settings tab follows the current flat-list
  pattern (Bucket A cross-type restructure is parked
  indefinitely per the same brainstorm).
- The `banking.vault_outgoing_warns` feature flag and its
  Settings exposure stay as-is (already locked per
  `holdings/04_vault.md`'s "configurable via" clause).
- **No frontend cleanup is needed today.** The Vault detail page
  doesn't ship until the next iteration; nothing currently
  reads `purpose=long_term` in the live UI.

## What this ADR does not decide

- The exact Settings-card layout for the `banking.vault_outgoing_warns`
  opt-out toggle on Vault detail. Designed in the
  Vault-detail-page iteration's mockup pass.
- Whether a future per-Vault opt-out toggle joins the global
  feature flag. Out of scope until a real user surfaces the
  treasury-Vault case.

## Affected files

- `02_domain_model.md` — `Purpose.LONG_TERM` removed; surrounding
  prose updated
- `03_data_model.md` — `holding.purpose` CHECK constraint drops
  `'long_term'`
- `concerns/outflow.md` — guardrail unconditional on Vault Send
- `holdings/04_vault.md` — `purpose` removed from Vocabulary;
  guardrail section rewritten; usage-based-feedback deferred-row
  rephrased
- `backlog/usage-based-feedback-for-long-term-vaults.md` —
  reframed (no declaration; observed-against-type-baseline)
- `decisions/README.md` — ADR-0018 indexed
- `api/openapi.yaml` — regenerated at the next iteration that
  touches `purpose` (not this design pass; coding iteration
  closeout regenerates per ADR-0004)
