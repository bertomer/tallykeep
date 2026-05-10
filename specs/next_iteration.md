# Next iteration

The sharpened, fully-detailed scope of work the coding agent is
working on (or about to start). Updated in lockstep with the canonical
specs whenever the spec evolves.

When this iteration completes:
- Items shipped → removed from this file
- Canonical specs already reflect the target (no extra "merge" work)
- One item from `future_iterations.md` is promoted, sharpened, and
  becomes the new "Next iteration"

If you're a coding agent reading this: this file is your scope. Other
docs in `specs/` are reference; this file is the assignment.

---

## Iteration template

Use this shape when sharpening an iteration. Sections marked (required)
must be filled before the iteration is given to a coding agent.

### Iteration: <short name>

**Started:** YYYY-MM
**Goal:** <single sentence — what we want to be true at the end>

#### Scope (in) — required

<bullet list of features / changes — sharp, small, fully detailed.
Each item references the canonical doc(s) and mockup file(s) that
define it. The coding agent should not need to invent anything from
this list.>

#### Scope (out) — required

<things considered for this iteration and explicitly cut. Prevents
scope creep.>

#### Affected canonical docs

<list of canonical spec files this iteration touches. Already updated
to reflect target before iteration starts.>

#### Affected mockups

<list of validated mockup files referenced by the iteration.>

#### Tasks — required

<concrete, ordered tasks for the coding agent. Each task should map to
a definition-of-done.>

#### Acceptance / done-when — required

<observable conditions: this curl returns this; this screen matches
this mockup at this viewport; this gauntlet step passes.>

#### Dependencies

<what blocks this iteration: pre-implementation items needing
arbitration, prior iterations not yet shipped, third-party things.>

---

## Active iteration

### Iteration: spec-cleanup-backend-deltas

**Started:** 2026-05
**Goal:** Bring the running backend into alignment with the canonical
spec edits made during the consolidation cleanup pass. Three concrete
deltas: add Purse `seed_origin`; verify SweepPolicy `is_dry_run` SQL
column; drop the `preset` user-tier concept (resolution of
`profile-presets-vs-contextual` arbitration). After this iteration,
the OpenAPI contract matches the canonical specs again.

This is a janitorial iteration that exists because the cleanup pass
edited canonical docs (`02_domain_model.md`, `03_data_model.md`,
`09_feature_flags.md`, `04_api_conventions.md`, the OpenAPI contract)
in ways that imply backend code/schema changes.
Per PROCESS.md §2.7, spec edits with backend impact land in lockstep
with iteration scope. This entry is that scope.

#### Scope (in) — required

1. **Add Purse `seed_origin` field.** Implement the canonical
   `purse-flavors` resolution in the backend, in its corrected form
   (the backend records *intent* only; it never holds a reference
   to a seed).

   - `02_domain_model.md` §"Core entities" → Purse class now has a
     `seed_origin: PurseSeedOrigin` field (no `flavor`, no
     `on_device_seed_reference`).
   - `02_domain_model.md` §"Purse seed origin" defines the two
     values (`EXTERNAL_WATCH_ONLY`, `TALLYKEEP_MANAGED`) and their
     semantics.
   - `02_domain_model.md` §"Signing capability is per-client"
     clarifies that *which device holds the seed* is per-client
     runtime state, not a backend field — and the backend never
     enforces client build type.
   - `02_domain_model.md` §"Invariants summarized" adds invariants
     10 (`seed_origin` immutable) and 11 (no backend build-type
     validation).
   - `03_data_model.md` §"`holding`" updates `subtype_data` for
     `holding_type='purse'` to `{ "seed_origin": "external_watch_only"
     | "tallykeep_managed" }`.
   - `POST /api/v1/holdings/purse` request schema in `api/openapi.yaml`
     gains `seed_origin`; validation rules: `seed_origin` required;
     at least one descriptor required; single-address-only descriptors
     rejected; **no** build-type detection. Reference rules live in
     `04_api_conventions.md` (errors, validation posture); the
     endpoint shape itself lives in OpenAPI after regeneration.

2. **Verify SweepPolicy `is_dry_run` SQL column.** Module 03 now
   documents `is_dry_run BOOLEAN NOT NULL DEFAULT FALSE` on
   `sweep_policy`. The running OpenAPI already exposes the field on
   the SweepPolicy schemas (suggesting the backend has it), but the
   SQL column was not previously documented. Verify the column
   exists; if not, add an Alembic migration to land it.

3. **Drop `preset` from UserProfile.** Implement the canonical
   `profile-presets-vs-contextual` resolution: there is no
   user-tier identity; the configuration is just feature flags.

   - `02_domain_model.md` UserProfile no longer has `preset` or the
     `ProfilePreset` enum.
   - `03_data_model.md` `user_profile` no longer has the `preset`
     column.
   - `09_feature_flags.md` (renamed from `09_profiles_and_flags.md`)
     rebuilt around the flag catalog, onboarding-driven defaults,
     and per-flag override.
   - `04_api_conventions.md` and OpenAPI: `PATCH /api/v1/profile`
     no longer accepts `preset`; the `UserProfile` response schema
     no longer exposes it. Resetting to defaults is done by setting
     `feature_flags: {}`.

   Backend tasks:
   - Remove the `preset` field from the Pydantic `UserProfile`
     schemas (request and response).
   - Remove the `ProfilePreset` enum from the codebase.
   - Add an Alembic migration to drop the `preset` column from
     `user_profile`.
   - Update flag-resolution logic: lookup `user_profile.feature_flags`
     with fallback to `DEFAULT_FLAG_VALUES`. Remove preset-bundle
     resolution.
   - Add the new flag `banking.coin_selection_per_payment_override`
     to the registry (used by module 06's per-payment override
     gate, replacing the implicit "Sovereign profile" gate).

   Out of scope (UX iteration territory): the actual onboarding
   question wording, the answer-to-flag-bundle mapping. Backend
   accepts whatever `feature_flags` the client posts after
   onboarding; the question UI lives in mobile mockups.

4. **Regenerate `api/openapi.yaml`** so it matches the code after
   all the changes above.

#### Scope (out) — required

- UI work. `UI/README.md` and `10_threat_model.md` already describe
  the seed-origin semantics; rendering them in mobile mockups is
  part of the Add-Holding mobile iteration, not this one.
- The Capacitor-side seed-generation flow (creating a seed in
  Keychain/Keystore, indexing by `holding_id`). That's client work
  that lands with the Add-Holding mobile iteration.
- The per-client signing-capability check on the frontend. Same —
  client work, lands with Send-flow iterations.
- Backend build-type detection. Explicitly **not** in scope: the
  backend does not gate on client build type; the affordance gate
  is client-side only.
- The `seed-backup-disclosure` and `multi-asset-aggregation`
  arbitration items remain open in `pre-implementation.md`; they
  are not part of this iteration.

#### Affected canonical docs

- `02_domain_model.md` (Purse class with `seed_origin`,
  `PurseSeedOrigin` enum, "Purse seed origin" section, "Signing
  capability is per-client" section, invariants 10–11, SweepPolicy
  `is_dry_run`, UserProfile without `preset`)
- `03_data_model.md` (`holding.subtype_data` purse shape;
  `sweep_policy.is_dry_run`; `user_profile` without `preset` column)
- `09_feature_flags.md` (rebuilt; flag catalog, onboarding-driven
  defaults, per-flag override; new flag
  `banking.coin_selection_per_payment_override`)
- `04_api_conventions.md` (cross-cutting rules unchanged; actual
  request/response shapes land in `api/openapi.yaml` after backend
  changes + regeneration)
- `05_savings_layer.md`, `06_banking_layer.md`, `07_trading_layer.md`
  (per-flag references no longer mention Beginner/Intermediate/
  Sovereign — already updated)

All three canonical docs already reflect the target. The iteration's
job is to make the code match.

#### Affected mockups

None. Out of scope per above.

#### Tasks — required

**Purse seed_origin:**

1. Add `seed_origin` (and the `PurseSeedOrigin` enum) to the Purse
   domain model (Pydantic / dataclass + ORM model). Make it required
   at creation, immutable thereafter.
2. Update the `holding.subtype_data` write/read paths for
   `holding_type='purse'` to round-trip `seed_origin`.
3. Add validation to `POST /api/v1/holdings/purse`:
   - `seed_origin` is required.
   - At least one descriptor is required (regardless of
     `seed_origin`).
   - Single-address-only descriptors are rejected (this rule may
     already exist; confirm).
   - **No** build-type detection. **No**
     `/errors/build-cannot-hold-spending-keys`.

**SweepPolicy is_dry_run:**

4. Verify `sweep_policy.is_dry_run` column existence; add an
   Alembic migration if missing.

**Drop presets:**

5. Remove the `preset` field from the `UserProfile` Pydantic
   schemas (request and response).
6. Remove the `ProfilePreset` enum from the codebase.
7. Add an Alembic migration to drop `user_profile.preset`.
8. Update flag-resolution logic: lookup
   `user_profile.feature_flags` with fallback to
   `DEFAULT_FLAG_VALUES`. Delete preset-bundle resolution code.
9. Add `banking.coin_selection_per_payment_override` to the flag
   registry (gates the per-payment override path in module 06).

**OpenAPI:**

10. Regenerate `api/openapi.yaml` from the running backend.

#### Acceptance / done-when — required

**Purse seed_origin:**

- `POST /api/v1/holdings/purse` with `seed_origin='external_watch_only'`
  and a valid xpub-or-descriptor returns 201; the response includes
  `seed_origin: 'external_watch_only'`.
- `POST /api/v1/holdings/purse` with `seed_origin='tallykeep_managed'`
  and a valid descriptor returns 201; the response includes
  `seed_origin: 'tallykeep_managed'`. (The backend does not
  distinguish based on which client made the request.)
- `POST /api/v1/holdings/purse` without `seed_origin` returns 422.
- `POST /api/v1/holdings/purse` with a single-address-only descriptor
  returns 400.

**SweepPolicy is_dry_run:**

- `SELECT column_name FROM information_schema.columns WHERE
  table_name='sweep_policy' AND column_name='is_dry_run'` returns
  a row.

**Drop presets:**

- `GET /api/v1/profile` response no longer includes `preset`.
- `PATCH /api/v1/profile` rejects requests that include `preset`
  (422 validation).
- `PATCH /api/v1/profile` with `feature_flags: {}` resets the
  user's overrides; subsequent `GET /api/v1/feature-flags` returns
  the values from `DEFAULT_FLAG_VALUES`.
- `SELECT column_name FROM information_schema.columns WHERE
  table_name='user_profile' AND column_name='preset'` returns
  zero rows.
- `GET /api/v1/feature-flags` includes
  `banking.coin_selection_per_payment_override` in its response.

**OpenAPI:**

- `api/openapi.yaml` regenerated. The `PurseCreate` schema includes
  `seed_origin` and does **not** include `flavor` or
  `on_device_seed_reference`. The `UserProfile` and
  `UserProfileUpdate` schemas no longer reference `ProfilePreset`
  or include a `preset` field. The `ProfilePreset` schema is gone.
  The SweepPolicy schemas continue to include `is_dry_run`.

#### Dependencies

- None blocking. The two arbitration items resolved during the
  cleanup pass (`api-surface-canonical-source`,
  `profile-presets-vs-contextual`) are now reflected in the
  canonical specs and folded into this iteration's scope. The
  remaining open items in `pre-implementation.md`
  (`seed-backup-disclosure`, `multi-asset-aggregation`) are
  unrelated to these deltas.

---

### Current bottleneck — design iteration with Rémy

If you are an agent landing here expecting code work: there is none
ready. The current bottleneck is **design conversations between Rémy
and the agent**, screen by screen, that produce sharpened iteration
scope plus mockups under `UI/mockups/`. Only after that does coding
work appear in this file.

The previous Welcome + Home-empty draft was pulled back: sharpening
individual screens before walking through the existing wireframes
together would have skipped a step. Each iteration's scope is
co-sharpened in conversation against the existing wireframes (bulked
into multi-screen HTMLs in `archive/UI/`, with unclear validated
state). The next session is that walk-through, not a pre-spec'd
iteration.

### What an arriving agent should do

1. Read `00_README.md`, `PROCESS.md`, this file.
2. If Rémy is in the conversation, say so and ask which screen-flow
   he wants to sharpen first (the roadmap below is the candidate
   list).
3. If Rémy is not in the conversation, do not invent scope. Report
   the current state and stop.

### Decisions already pre-bagged for the first iterations

- Home empty's four Add affordances are a popup on Add-Holding tap,
  not directly inline on the empty state.
- Watch-only Purse onboarding accepts xpub or descriptor only, not
  single addresses (per pre-implementation item `purse-flavors`).
- TallyKeep-managed Purse creation: the "Create a TallyKeep wallet"
  affordance is gated client-side on the device's capability to
  generate and securely store a seed; browser builds hide it with
  an install-the-app message (per `purse-flavors`).
- Mobile baseline viewport: 360 × 800 (per `UI/mockups/README.md`).

When the next iteration is sharpened, this section gets filled in
using the template above.

---

## Iteration roadmap (rough sketch — not commitment)

For Rémy's mental model, not for the coding agent. Sequence and
scope will adjust as we learn. The roadmap targets the public-ship
event (per ADR-0003); private-ship is reached when the relevant
mobile UI iterations are stable enough and the Capacitor + auth +
security-health work lands.

### Pre-shipping iterations

**Mobile UI design and dev-phase build:**
1. **Onboarding + Home (empty + populated states)** — first-touch
   flow plus landing
2. **Add Holding** — chooser + four type-specific flows
3. **Holding Detail** — per-type detail pages
4. **Send + Receive** — per Holding type, including PSBT roundtrip
   for Strongbox and native sign for TallyKeep-managed Purse on the
   device that holds the seed
5. **Activity + Categorization** — cross-Holding feed plus
   per-Holding categorization
6. **Sweep Policy + Trading view** — Account-originated sweeps in
   v1 dev-phase scope
7. **Settings** — including the security-health system at least
   for seed-backup warnings (private-ship gate)

**Private-ship gate:**
- Capacitor wrap + native plugins
- Authentication layer
- Security-health (seed-backup recovery flow per pre-implementation item `seed-backup-disclosure`)
- Self-review

**Pre-public-ship enhancements** (in personal-use phase, before
public-ship):
- Iterations driven by Rémy's own daily-use feedback
- Possible candidates: settlement-rails confirmation probability,
  "tap to see under the hood" UI spine, others (see
  `future_iterations.md`)

### Public-ship event (ship-gate work bundle)

See `future_iterations.md` "Ship-gate meta-iteration" entry. Bundles
native signing, reproducible builds, app stores, F-Droid, brand,
third-party audit, and (optionally) hosted-tier launch.

### Post-shipping

Feature updates per `future_iterations.md` post-shipping entries
(Blueprint, Lightning, DCA, equity-reference, etc., depending on
user feedback and roadmap priorities).
