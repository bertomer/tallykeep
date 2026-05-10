# ADR-0005 — Feature flags replace named user profiles

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during consolidation merge
- **Migrated from:** `pre-implementation.md` Decided item
  `profile-presets-vs-contextual` (2026-05).

## Context

The original module 09 was `09_profiles_and_flags.md` and
proposed three named tiers — Beginner / Intermediate / Sovereign
— each bundling expertise, assets-under-self-custody, anticipated
usage, and information-density into a single label. The user
would identify with a tier; flags would derive from it.

Three problems surfaced:

1. The dimensions the tier compressed are independent. A
   long-time Bitcoin developer with one Purse and a newcomer with
   multiple Holdings are both poorly served by any single tier.
2. "Beginner" reads as deficient-to-be-overcome. "Sovereign"
   carries ideological framing that excludes users wanting the
   full feature surface without the political identity.
3. The "banking ergonomics" positioning makes user-tier identity
   an actively wrong abstraction. A bank app does not ask its
   user "are you a beginner or a sovereign person." It exposes
   the right defaults and the right preferences.

## Decision

1. Drop named presets entirely. There is no `ProfilePreset`
   class, no `preset` field, no tier the user belongs to.
2. The `UserProfile` domain entity carries `feature_flags`,
   `base_currency`, `locale` only.
3. Initial flag values are seeded by **onboarding answers** — a
   small set of questions asked once at first launch, mapping
   answers to a default flag bundle. Specific question wording is
   UX-iteration design, not a domain decision.
4. A `DEFAULT_FLAG_VALUES` fallback applies if onboarding is
   skipped.
5. Flag resolution is lookup-with-fallback. No preset layer.
6. Module 09 is renamed `09_feature_flags.md` and rewritten
   end-to-end under this shape.
7. The previous "Sovereign-profile per-payment override" feature
   is replaced by flag
   `banking.coin_selection_per_payment_override`.

## Consequences

- The user tunes their setup one flag at a time. There is nothing
  to "switch back to" because there is no concept the user
  belongs to.
- Onboarding becomes the seam for opinionated defaults without
  forcing a tier identity on the user.
- API surface drops the `preset` field; `user_profile` table drops
  the `preset` column. Migration was tracked through the
  `spec-cleanup-backend-deltas` iteration (shipped 2026-05-10).

## Affected files

- `02_domain_model.md` — `UserProfile` rewritten
- `03_data_model.md` — `user_profile` table updated
- `09_feature_flags.md` — renamed and rewritten
- `00_README.md` — "Currently in scope" updated
- `05_savings_layer.md`, `06_banking_layer.md`,
  `07_trading_layer.md` — Beginner/Intermediate/Sovereign mentions
  removed
- `archive/` — historical material if any
