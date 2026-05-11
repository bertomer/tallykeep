# Pre-implementation arbitration

Items requiring a dedicated arbitration session before they can be
folded into `next_iteration.md`. Different tone (Rémy's decision,
with reasoning), different autonomy (no coding agent should guess
these).

Each has a recommendation. Rémy decides, dates, and the item
**leaves this file**:

- Foundational decisions land as ADRs in `decisions/`.
- Implementation work moves to `next_iteration.md` (if active) or
  `future_iterations.md` (if deferred).
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

### `seed-backup-disclosure`

**Status:** open (leading direction; full session pending to
specify the security-health system)

**Item:** When the Capacitor build generates an on-device Purse
seed, how is the user warned about backup responsibility? Phone
loss + no seed backup = funds gone.

**Leading direction (Rémy):** Generate the seed; show it to the
user; show a strong warning explaining the loss-of-funds
consequence; attach a persistent warning to the home page or
security-health section that stays visible until the user
explicitly checks "I backed up my keys safely, I understand the
consequences."

This persistent warning lives in a broader **security-health
system** alongside other persistent warnings:

- Privacy / Blueprint warnings (address reuse, etc.)
- Strongbox frequent-usage warning (large amounts on a Strongbox
  used for daily spending)
- Vault declared-vs-observable mismatch
- Hosted-tier privacy-boundary acknowledgment

**Why this is preferable to a hard gate:** the hard gate forces
the user to act at an inconvenient moment (just generated the
seed, hasn't yet opened the password manager / safe / paper-backup
process). The persistent-warning model lets the user dismiss the
modal but does not let them forget. It is also more honest — it
admits the responsibility is ongoing, not a one-time confirmation.

**Open part — full session needed:**

- Specify the security-health system (what items, what severity,
  what presentation).
- Define the warning-acknowledgment lifecycle (checkbox only, or
  some periodic re-confirm?).
- Decide where on home page / settings / dedicated tab the
  security-health view lives.
- Wording of the warning at seed-generation time.

The security-health system is also captured in
`future_iterations.md` as a feature item, since several items
contribute to it.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `multi-asset-aggregation`

**Status:** open

**Item:** The "no multi-asset" line in the canonical out-of-scope
list rejects custody of stablecoins, Monero, and non-Bitcoin
chains — that part is firm and tied to regulatory surface. But
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
  home page's "Total: 0.52 BTC" becomes ambiguous — does it
  include the USDT? If it does, in what unit and at what rate? If
  it doesn't, the user has to do the math themselves.
- **Vocabulary.** TallyKeep's locked vocabulary (Holdings,
  Account, Purse, Strongbox, Vault) is BTC-centric. Multi-asset
  Holdings would either fragment the vocabulary or force a new
  "asset" axis on every Holding type.
- **Custodial-only.** Non-BTC aggregation is *only* possible at
  the Account level — Purse / Strongbox / Vault don't apply
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
3. *Reject — stay strict BTC-only.* Maintains vocabulary purity
   at the cost of practical visibility for the target market.

**Leading direction:** None yet. Rémy explicitly opened the
question during the consolidation merge after pushing back on a
proposed ADR that would have locked the rejection.

**Decision:** ___ (pending session)
**Decided on:** ___

---

### `pairing-handshake-crypto`

**Status:** open (sharpens at private-ship gate)

**Item:** When the mobile client scans a QR generated by the user's
TallyKeep stack to pair, what does the QR carry and what crypto secures
the handshake? Plain bearer token + endpoint URL is the simple
baseline; PAKE/Noise-style ephemeral-key handshake is the robust
alternative.

**Leading direction (Rémy + Claude, sharpened during onboarding-screen
session 2026-05):** plain endpoint URL + single-use ephemeral pairing
token (~60 second TTL, displayed by the desktop, redeemed once over
TLS or local-network HTTP). Phone POSTs the token to the endpoint;
backend validates and returns a long-lived per-device credential. The
phone stores that credential in its Keychain/Keystore
(biometric-protected). Per-device credentials are revocable from the
desktop's "Paired devices" list.

**Why this direction (and what it gives up):** matches the WhatsApp
Web / Signal device-link pattern users already understand. The
"QR display = proof of possession" argument makes the adversary
model small — physical access to the desktop is required to scan
the QR, and the same-LAN constraint per `01_architecture.md`
§"Network security posture" narrows the window further. PAKE/Noise
add ceremonial cost (mutual-auth handshake, ephemeral key
generation, replay protection) for a threat largely mitigated by
the deployment posture. Worth revisiting if remote pairing (post
`Remote access for self-hosters` in `future_iterations.md`) lands
and the same-LAN constraint goes away.

**Open part — full session needed:**

- Token format (UUID? base32 + checksum? something more compact for
  QR density?), TTL precise value, single-use vs N-use, server-side
  rate limit on pairing attempts.
- Per-device credential format (opaque bearer? signed JWT?).
  Rotation policy.
- Revocation UX on the desktop side ("Paired devices" list with
  last-seen timestamps and "Forget this device" affordance).
- Confirmation UX after a successful pair (does the desktop show
  "phone paired at HH:MM" so the user can verify they're the one
  who scanned?).
- Whether an additional confirmation step on the desktop ("approve
  pairing from phone XYZ?") is worth the friction, or if QR
  possession alone is enough.

**Decision:** ___ (pending session)
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
| `psbt-by-qr-mobile` | `future_iterations.md` "PSBT-by-QR roundtrip on mobile" | Deferred; no foundational decision |
| `categorization-queue-mobile` | `UI/README.md` Activity section, `future_iterations.md` "Push-driven categorization workflow" | Decided + deferred parts each found their canonical home |

Slugs are preserved by the receiving ADR's "Migrated from" header
so existing back-references in canonical docs still resolve.

This log is one-time. Future closed items leave the file directly;
no log accumulates.
