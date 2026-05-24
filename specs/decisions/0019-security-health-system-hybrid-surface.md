# ADR-0019 — Security-health system: hybrid surface with severity-driven discovery

- **Date:** 2026-05
- **Status:** Accepted
- **Decided by:** Rémy
- **Authored by:** Claude, during the security-health-system framing session
- **Migrated from:** `seed-backup-disclosure` (pre-implementation.md)
- **Related:** ADR-0007 (browser-first NativeBridge), ADR-0009 (key-custody zones),
  ADR-0014 (backlog-as-folder), ADR-0017 (Forget is hard delete)

## Context

TallyKeep accumulates persistent items that need user attention. The
original `seed-backup-disclosure` arbitration scoped the question
narrowly — *how do we warn a user who just generated a Purse seed that
they need to back it up?* — but the answer naturally generalised. A
"persistent warning on Home until acknowledged" is one item type;
several others want the same persistence-and-resolution machinery:

- **Strongbox missing signing-metadata** — surfaces when a Strongbox
  is imported from a bare xpub (no `[fingerprint/path]` brackets).
  Already surfaced inline on Strongbox detail Settings as a
  `warning-soft` card with a coming-soon "Fix this" CTA; the
  resolution sub-flow (re-export, or manual fingerprint + derivation
  entry) is the load-bearing part still to build.
- **Vault per-cosigner missing-metadata** — same shape grouped into
  the Vault descriptor tile.
- **Principles acknowledgment not given** — when a user reaches Home
  without tapping `[I understand]` on the Onboarding 01 principles
  card. Per `UI/mobile.md` Onboarding Notes, this item lands in the
  "Security health" zone on Home.
- **Hosted-tier privacy-boundary acknowledgment** — per
  `backlog/hosted-tier-infrastructure.md`. Disclosure of what
  TallyKeep-the-operator can see (descriptors plaintext, labels,
  brief credential pass-through during a provider call).
- **Hosted-tier credentials-backup acknowledgment** — same source.
  Lose connection-ID + passphrase = instance gone, same shape as
  lose-seed = funds gone.

Three surface models were on the table during the 2026-05-24 framing
session:

- **(a) Centralised dashboard only** — single page listing everything.
- **(b) Per-Holding inline surfacing only** — items live on the page
  where the fix happens; no aggregate.
- **(c) Hybrid** — single source of truth on the page where the fix
  lives, aggregation + audit centrally.

The session settled on **(c) hybrid** with a sharper articulation than
the backlog's vague "and/or" framing: items are not duplicated, they
are *tracked once where the fix lives* and *referenced from the
dashboard*. The dashboard is index + history, not a parallel
source-of-truth.

## Decision

### Surface model — hybrid

Items have **one source of truth** on the page where the fix happens:

- Missing signing-metadata: Strongbox / Vault detail Settings tab.
- Seed-backup ack: Purse detail Settings tab.
- Per-Holding declared-vs-observable kinds: that Holding's detail page
  (currently no kinds actionable for v1 — see "Out of scope" below).

**Application-level items** that have no Holding to attach to
(principles-ack, hosted-tier acks) live natively in the dashboard.
Their resolution flows render as **bottom sheets** inside the
dashboard, not as separate pages or routes.

### Discovery channels — three, severity-driven

1. **Inline card** on the source-of-truth page — always renders while
   the item is in the `OPEN` state. Disappears the moment the item
   resolves. No "dead" placeholder when nothing is open.

2. **Bottom-nav tab "Security Health"** — second tab after Home (per
   the 2026-05-24 framing session), visible on every page that shows
   the bottom nav. The tab's icon is a bell shape; when one or more
   `critical`-severity items are open, the tab carries a **red badge
   with the critical-count**. The badge does **not** count warning-
   severity items (per the no-alarm-fatigue principle: warnings are
   discovered via the dashboard tab itself, the Home section for
   application-level items, or the inline card on the affected
   Holding's detail page). The tab itself stays visible at all times;
   only the badge appears/disappears with count. Tap → dashboard.

   **Bottom-nav restructure: 4 tabs → 3 tabs.** The current 4-tab
   layout (Home / Activity / Holdings / More, per `UI/mobile.md` Home
   notes — explicitly locked as "not yet final, sharpens with Settings
   + Activity iterations") becomes 3 tabs:

   - Tab 1 — **Home**
   - Tab 2 — **Security Health** (new, per this ADR)
   - Tab 3 — **Activity** (transaction categorization center, per the
     existing forward-reference in `UI/mobile.md`)

   Tabs retired:

   - **Holdings** — Holdings are already visible on Home as the
     list-card; a dedicated Holdings tab would duplicate that index.
     Holding detail pages remain reachable via tap-through from the
     Home list (already locked behaviour).
   - **More** — Settings was the only resident of the More tab;
     Settings moves to a **gear icon top-right on the app bar**
     (banking-app standard: Revolut, N26, Wise all use the same
     pattern). Visible on every page that shows the app bar. Tap →
     Settings page (designed as part of the upcoming Settings
     iteration; this iteration adds the entry-point and a minimal
     Settings landing).

   Three tabs gives each slot ~120 px width at the 360 px baseline
   viewport — generous breathing room, no label-truncation risk that
   a 5-tab layout would have introduced.

3. **Home section** headed "Security health" — renders inline on Home
   *only when at least one application-level item is open*. Absent
   when empty (no-dead-capability rule). Per-Holding items do **not**
   surface in this Home section — they have their own inline cards on
   the affected Holding's detail page; surfacing them on Home would
   duplicate and conflict with the source-of-truth rule. This section
   is also the load-bearing surface for **application-level warnings**
   (e.g., principles-ack-on-skip), which the nav-tab red badge does
   not count — the Home section ensures these warnings are seen on
   the first surface the user lands on at app open.

The three channels cover three discovery moments: the nav tab follows
the user across every page (with red badging for criticals only); the
Home section catches the user on first landing (for application-level
items including warnings); the inline cards catch the user on the
page where the fix lives.

### App-bar gear icon (new chrome)

A small gear icon lands top-right on the app bar across every page
that shows the app bar. Tap opens Settings. Replaces the retired
More-tab entry point. Visual treatment:

- 24 px gear glyph, `--color-text-muted` fill, hit target 44 × 44 px.
- Positioned in the existing app-bar's currently-empty right slot
  (the wordmark stays left-aligned).
- No badge / no notification dot — Settings is configuration, not a
  notification surface.

Settings page contents and per-row design are out of scope for this
iteration; the entry point + a stub landing are in scope. The full
Settings design pass lands in the dedicated Settings iteration.

### Severity — two CTA-bearing levels + a notification track

- **Critical** — propagates to the Security Health nav tab as a **red
  bell-icon badge** with critical-count. Top of dashboard, red
  treatment. Reserved for items where failure to act has *catastrophic*
  consequences (loss of funds; instance loss with no recovery). v1
  occupants: unbacked-up Purse seed; (when hosted tier ships)
  hosted-tier credentials backup.

- **Warning** — in dashboard, **does not propagate to the nav badge**,
  amber-neutral treatment. Reserved for items where failure to act has
  *meaningful but bounded* consequences (interop friction; disclosure
  not acknowledged). v1 occupants: missing-derivation-metadata,
  principles-ack-on-skip, (when hosted tier ships) hosted-tier privacy
  disclosure. Discovery surfaces: dashboard Active tab (always), Home
  section (application-level only), inline card on the source-of-truth
  page (per-Holding only).

- **Notification** — no CTA, logged directly to the History tab as a
  "for the record" entry. Used **sparingly**. Per the "no ack theater"
  principle: if an item does not warrant a user nod, we do not
  manufacture a CTA to make the user nod anyway. Reserved for events
  the user benefits from being able to look up later (system milestones,
  one-time disclosures we want auditable but not interruptive).

The two CTA severities feed two different discovery channels (nav-tab
red badge vs. dashboard-only), which is the load-bearing distinction.
A single severity axis would force every CTA into the same channel and
either spam the badge (alarmism) or silently hide critical items
(dilution).

### Lifecycle — three terminal states under the hood, two user-facing categories

Active vs History is what the user sees. Under the hood, items move
from `OPEN` to one of three terminal states, each with a different
verb in the History row:

- **`RESOLVED_BY_FIX`** — system-verified. The condition that triggered
  the item has been observed to no longer hold (descriptor now carries
  metadata; principles card now reads `acknowledged_at != NULL`; etc.).
  History row: "Fixed on YYYY-MM-DD". **Not revivable** — the truth is
  computed; if the underlying condition recurs, a fresh item appears
  with a new row.

- **`DISMISSED_INTENTIONAL`** — user-attested. The user opens the item
  and chooses "this is intentional, leave me alone" (e.g.,
  "yes this Strongbox is currently being used for daily spending and I
  know"). History row: "Acknowledged as intentional on YYYY-MM-DD".
  **Revivable** — the user can flip the item back to `OPEN` from
  History.

- **`ACKNOWLEDGED`** — user-attested. The user confirms a claim that
  resolves the item ("I backed up my seed"; "I understand the
  principles"). History row: "Acknowledged on YYYY-MM-DD". **Revivable**
  — the user can flip back to `OPEN` from History (the honest variant
  of acknowledgment: take back a claim that was not true).

The revive affordance is the honest counter to ack-theater. System-
verified items do not need it (truth is computed); user-attested items
do (the user is the only source of truth on whether they really backed
up their seed).

### Persistence — typed open-items table

A single table holds all items, regardless of type. Shape:

```
security_health_item
  id                 uuid PK
  item_type          text          -- e.g. 'seed_backup', 'missing_signing_metadata',
                                   --     'principles_ack', 'hosted_tier_privacy_ack'
  holding_id         uuid NULL FK  -- NULL for application-level items
  state              text          -- 'open' | 'resolved_by_fix' |
                                   -- 'dismissed_intentional' | 'acknowledged'
  severity           text          -- 'critical' | 'warning' | 'notification'
  created_at         timestamptz
  resolved_at        timestamptz NULL
  dismissal_reason   text NULL     -- free-text user note when DISMISSED_INTENTIONAL
  raw_context        jsonb         -- per-type context payload (vendor name, severity
                                   -- detail, etc.) — readable by the per-type renderer
```

Heterogeneous items, uniform schema. Replaces the
preferences-key-value shape considered in the original
`seed-backup-disclosure` arbitration; that shape cannot support
History timestamps, per-instance context, or the revive affordance.

### SSE topics

Three topics under the `security_health.*` namespace, matching the
existing event-taxonomy conventions:

- `security_health.item_added` — fires when a new row enters `OPEN`.
- `security_health.item_resolved` — fires on `OPEN → terminal-state`
  transition; payload carries the terminal state so the dashboard
  knows the History verb to render.
- `security_health.item_revived` — fires on terminal-state `→ OPEN`
  via the revive affordance (user-attested items only).

The nav-tab red badge subscribes to all three but filters payload by
`severity == 'critical'` for the count. The Home section subscribes to
the application-level subset.

### User-facing vocabulary — locked

The user-facing name for the surface is **"Security health"**.
Locked uses:

- Bottom-nav tab label ("Security health"). At 360 px viewport, if
  layout forces a shorter form, "Security" is the locked abbreviation;
  the dashboard page title remains the full "Security health".
- Page title for the dashboard ("Security health").
- Heading on the Home section when present ("Security health").
- Item-type label in audit ("Security health · seed backup").

Banking-grade register, consistent with Apple Health "Health checks"
and retail-banking "Account health". Item copy stays calm and
descriptive; the heading carries the seriousness register.

## Consequences

### What changes

- **`UI/mobile.md`** — the Onboarding Notes section
  ("Principles card — acknowledgment flow with Security health
  fallback") flips from "Security health zone is its own iteration,
  not yet built" to referencing this ADR + the next-iteration block
  when it sharpens. The Strongbox detail §5 "Missing-signing-metadata
  inline advisory" and Vault detail's missing-metadata grouped
  indicator flip from "centralised surface still under arbitration"
  to "locked per ADR-0019". The Home Notes "Bottom nav present from
  empty state" passage sharpens from 4 tabs to **3 tabs** (Home /
  Security Health / Activity; Holdings + More retired). The app-bar
  gains a gear icon top-right (Settings entry-point) on every page
  that shows the app bar.

- **`holdings/02_purse.md`** — the seed-backup forward-reference
  flips from `pre-implementation.md` to this ADR. The
  `ON_DEVICE_USER_IMPORTED` variant carries the imported-seed copy
  variant per `backlog/purse-upgrade-path-watch-only-on-device-imported.md`.

- **`holdings/03_strongbox.md`** — the missing-signing-metadata item
  and the Strongbox-frequent-usage item references flip from the
  arbitration slug to this ADR. The Strongbox-frequent-usage item is
  explicitly deferred (see "Out of scope" below).

- **`holdings/04_vault.md`** — the usage-based-feedback item
  reference flips. Item is deferred (see "Out of scope").

- **`pre-implementation.md`** — the `seed-backup-disclosure` entry
  leaves the file. The slug is preserved in this ADR's
  `Migrated from:` header so existing back-references in canonical
  docs continue to resolve.

- The previous `backlog/` capture file has been promoted to
  `next_iteration.md` and deleted per ADR-0014. Git history retains
  the captured-idea version.

- **`api/openapi.yaml`** — gains the `/security_health/*` endpoint
  family and the `SecurityHealthItem` schema on the iteration's
  closeout regen (per ADR-0004).

### What this ADR does NOT decide

- **Per-item copy** beyond severity assignment. Wizard-time seed-
  backup copy, bottom-sheet acknowledgment body text, History-row
  phrasing, the principles-ack re-show flow text — all designed
  during the iteration's mockup + copy pass.

- **Bell-icon and gear-icon visual treatment.** Exact bell glyph
  (filled vs. outline), red-badge size, gear glyph weight,
  positioning. Mockup pass.

- **Settings page contents.** The gear-icon target is a Settings
  landing page; the full design of Settings (which rows live there,
  how they group, the "How TallyKeep works" re-read flow) is the
  scope of the dedicated Settings iteration, not this one. This
  iteration ships the gear-icon entry point + a minimal Settings
  landing stub.

- **History-tab prune policy.** Items accumulate without bound in v1.
  If size becomes a real problem (unlikely for a personal-use app
  with low item velocity), revisit. Probably never.

- **Per-item ordering within the Active tab beyond severity.** Sorted
  by severity descending then by `created_at` descending in v1.
  Within-severity sort options (by Holding, by type) deferred to
  user-feedback signal.

### Discovery-rule integration with existing Home

The "no security-discrepancy banner on empty Home" decision (per
`UI/mobile.md` Home empty state notes) is **preserved**. That
decision was specifically about the *analyzer* banner — the
declared-vs-observable kind — which requires Holdings to fire on.
The Home "Security health" section introduced by this ADR is a
different surface:

- The empty-state Home has no application-level items by construction
  (the user just landed; no acks pending unless they skipped Onboarding
  01 principles, in which case the principles-ack item is exactly
  what the Home section should show).
- The populated-state Home renders the section *only when at least one
  application-level item is open*. Same absence-of-affordance rule.

The Security Health bottom-nav tab lands with this iteration's mockup
pass. It appears on every page that shows the bottom nav (so the user
sees the tab even on empty Home). The red badge appears only when
critical-count > 0; the tab itself is always present.

### Frontend Settings hook

The first iteration also introduces a Settings entry "How TallyKeep
works" that re-opens the principles card content (read-only re-read,
not the acknowledgment flow). This already exists as a forward-
reference in `UI/mobile.md` Onboarding Notes ("Re-readable anytime via
Settings → 'How TallyKeep works'"). The acknowledgment flow itself
lives only in the dashboard's bottom-sheet for the principles-ack
item.

## Out of scope (deferred)

The following items were considered for the v1 surface and
deliberately deferred:

- **Strongbox-frequent-usage item** — the warning that a Strongbox is
  being used for daily-spending-frequency outflows. Light case; the
  natural advice ("use a Purse for daily spending") is already covered
  by the Holding-type taxonomy. Defer indefinitely; revisit if a real
  user-feedback case surfaces.

- **Vault outflow frequency item** — captured in
  `backlog/usage-based-feedback-for-long-term-vaults.md`. Per ADR-0018,
  Vault is long-term by type and the outgoing-payment guardrail
  already fires on every Vault Send; a separate "you've been
  spending too often from this Vault" item is redundant in the v1
  scope. Defer indefinitely.

- **Full declared-vs-observable surfacing.** The
  `concerns/observation.md` analyzer produces three kinds today:
  `claimed_offline_but_pattern_suggests_hot` (= Strongbox-frequent-
  usage; deferred above), `claimed_vault_no_timelock` (cannot fire —
  the Vault wizard rejects no-timelock single-sig at descriptor-paste
  time), `claimed_inheritance_no_recovery_path` (needs an
  `inheritance_configured` declaration field that does not exist).
  All three are deferred; the declared-vs-observable surface is
  effectively empty for v1.

- **Blueprint findings UI** — address reuse, dust UTXOs, round-number
  outputs, suspected consolidation. Post-shipping per
  `backlog/blueprint-analysis.md`. The backend logic ships; the
  security-health surface for these items lands when Blueprint does.

- **Vault outgoing-payment guardrail.** A per-action confirmation,
  not a persistent open item — does not fit the security-health
  schema. Already governed by `banking.vault_outgoing_warns`
  (per ADR-0018). Out of scope by shape, not by deferral.

- **Full Settings page design.** The gear-icon entry point + minimal
  Settings landing stub are in scope; full Settings layout, content,
  and per-row design land in the dedicated Settings iteration.

## First iteration scope (the "Security-health system v1" iteration)

When promoted to `next_iteration.md`, the iteration ships:

1. `security_health_item` table + migration; SSE topics.
2. `GET /security_health/items?state=open|history` endpoint.
3. `POST /security_health/items/{id}/resolve` with body
   `{state, dismissal_reason?}`.
4. `POST /security_health/items/{id}/revive` for user-attested items.
5. **Bottom-nav restructure: 4 → 3 tabs.** Home / Security Health /
   Activity. Holdings + More tabs retire. Security Health tab carries
   a bell-icon glyph; red badge with critical-count when count > 0.
   Tab visible on every page that shows the bottom nav.
6. **App-bar gear icon (top-right) → Settings entry point.** Replaces
   the retired More-tab entry. Visible on every page that shows the
   app bar. Minimal Settings landing stub at the tap target.
7. Dashboard page (Active + History tabs, severity-sorted within
   Active).
8. Seed-backup item (critical) — wizard-time copy at Purse seed
   generation, persistent item creation on Holding-create for
   `ON_DEVICE_TK_GENERATED` Purses, inline mirror on Purse detail
   Settings, dashboard entry. Drives the nav-tab red badge.
9. Missing-derivation-metadata item (warning) — server-side creation
   at Strongbox / Vault Holding-create when descriptor has no
   `bip32_derivation` origin. The Strongbox + Vault detail "Fix this"
   CTAs (currently coming-soon stubs) become real, opening the
   remediation sub-flow (re-export or manual fingerprint +
   derivation-path entry with backend address-match verification).
10. Principles-ack-on-skip item (warning) — server-side creation on
    first non-principles-acknowledged Home land. Bottom-sheet re-show
    flow inside the dashboard. Surfaces in the Home section (the
    load-bearing discovery channel for application-level warnings).
11. Revive-from-History affordance for user-attested items.
12. Home section "Security health" — renders inline only when at
    least one application-level item is open.

Hosted-tier items wait for the hosted-tier iteration.
Strongbox-frequent-usage, Vault-frequency, full
declared-vs-observable, Blueprint findings stay deferred.

## Affected files

- `decisions/README.md` — ADR-0019 indexed.
- `pre-implementation.md` — `seed-backup-disclosure` entry removed
  (slug preserved in this ADR's header).
- The previous `backlog/` capture has been promoted to
  `next_iteration.md` and deleted per ADR-0014.
- `UI/mobile.md` — Onboarding Notes "Security health zone"
  paragraph, Strongbox detail §5 missing-metadata advisory, Vault
  detail grouped-missing-metadata block, Strongbox wizard
  parseback advisory references — all flip from arbitration
  forward-reference to ADR-0019 reference. Home Notes "Bottom nav
  present from empty state" passage sharpens from 4 tabs to 3 tabs
  (Holdings + More retire; Settings moves to app-bar gear icon). New
  sections added: "Security health dashboard" (full prose + gauntlet
  answers) and "Security health item resolution flows" (the three
  sub-flows).
- `holdings/02_purse.md` — seed-backup forward-reference flips to
  ADR-0019.
- `holdings/03_strongbox.md` — missing-metadata + frequent-usage
  references flip; frequent-usage explicitly deferred.
- `holdings/04_vault.md` — usage-based-feedback reference flips;
  item explicitly deferred.
- `api/openapi.yaml` — regenerates at the v1 iteration's closeout
  (per ADR-0004); not touched by this ADR's spec-side landing.
