# Classification — descriptor → Holding-type routing

The single source of truth for the decision *"given a pasted
descriptor or bare xpub, which Holding type does it belong to?"*
This concern owns the routing taxonomy, the accept-set per
Holding type, and the rejection categories that surface as
inline-error copy in the Add-Holding wizards.

**Scope of this concern.** Pure descriptor-shape analysis. No
chain calls (no bitcoind, no address-history lookup), no node
roundtrip. Pure CPU on the descriptor string and the parser
metadata it produces. The chain-side mechanics of monitoring an
imported descriptor live in `observation.md`; the per-type
acceptance details live in `holdings/<type>.md`.

## Why this is a cross-cutting concern

Before this concern existed, the "is this descriptor for this
wizard?" decision was scattered: structural checks in the
backend `POST /api/v1/descriptors/validate` endpoint, accept-set
filters and redirect-routing in each wizard's frontend code,
bare-xpub auto-wrap inline in two wizards, single-address
rejection inline in three. By the time the Vault wizard shipped
(2026-05-16) the routing-error branching existed in three
copies; the Send-from-Account flow and the Purse upgrade path
would each have hit the same decision surface again.

The classification concern collapses that into one server-side
surface. Wizards become thin: paste-time call to the
classification endpoint → compare `best_fit` to the wizard's own
type → match continues to parseback, mismatch shows the redirect
popup, `null` shows the inline-error variant for the returned
`rejection_category`. The same call runs from any future flow
that ingests a descriptor (Send-from-Account source picker,
Purse upgrade path, descriptor-import audit tooling).

## Where it lives

`POST /api/v1/descriptors/validate` (extended from its pre-2026-06
shape) carries the classification surface. Endpoint shape — request
body, response schema, status codes — is in `api/openapi.yaml` per
ADR-0004. This file describes the **role** of the endpoint, not its
wire shape.

**No second endpoint.** The pre-classification `descriptor-validate`
already returned `parse_category` (added in the 2026-05-16 Vault
iteration); `best_fit` and a richer `rejection_category` are the
natural next layer of the same call. Splitting into a separate
`/descriptors/classify` would reintroduce the very surface area
this concern is consolidating.

**No frontend classification logic.** The acceptance bar for this
concern's iteration is explicit: *no caller in the frontend
computes Holding-type fit from descriptor shape itself; all fit
decisions come from the endpoint.* Inline classification logic in
wizard pages — bare-xpub auto-wrap, single-address rejection,
miniscript-fragment detection — disappears.

## Accept set per Holding type

The classifier returns `best_fit: "purse" | "strongbox" | "vault" | null`.
Per-type detail lives in the Holding chapters; this section is the
routing table at a glance.

- **`purse`** — single-key descriptors that derive a wallet-shaped
  address set. `wpkh(...)`, `sh(wpkh(...))`, `tr(...)`, `pkh(...)`.
  Bare xpub / zpub / ypub / tpub auto-wrap into the canonical
  single-key wpkh / sh(wpkh) form before classification. No
  signing-metadata requirement (Purse can be watch-only;
  on-device modes carry their own seed-origin metadata in
  `subtype_data`).

- **`strongbox`** — single-key descriptors that derive a
  wallet-shaped address set **with** `[fingerprint/path]`
  key-origin brackets present (i.e. signing-metadata-bearing).
  Same script-type set as Purse, distinguished by the presence of
  origin metadata. Bare xpub / zpub also accepted; the
  `signing_metadata_present: false` flag rides along on the
  parser metadata so the wizard advisory fires. Same descriptor
  shape can technically classify as Purse or Strongbox; the
  classifier returns the most-specific fit (Strongbox if metadata
  is present and the user routes via a Strongbox wizard; Purse
  default otherwise — the per-wizard match check resolves the
  tie since each wizard knows its own type).

- **`vault`** — multisig or timelock-carrying descriptors per the
  ADR-0010 β accept set: single-key + CLTV (`wsh(and_v(v:after(N),pk(K)))`),
  single-key + CSV (`wsh(and_v(v:older(N),pk(K)))`), pure multisig
  (`sh(multi)`, `wsh(multi/sortedmulti)`, `tr(multi_a)`),
  multisig + single CLTV, multisig + single CSV. Multi-path
  miniscript constructs (any `or_i / or_d / or_c / or_b /
  thresh / sha256 / hash256 / ripemd160 / hash160` fragment)
  are **not** Vault — they route to a structural rejection
  category, not to Vault parseback.

- **`null`** (no fit) — none of the above. Pair with a
  `rejection_category` value from the taxonomy below.

## Rejection taxonomy

When `best_fit = null`, the response carries a `rejection_category`
string that drives the wizard's inline-error copy. Categories are
locked here so all three Add-Holding wizards render identical
copy for the same rejection.

| `rejection_category` | When it fires | User-facing copy |
|---|---|---|
| `single_address_input` | Pasted text is a bare Bitcoin address (P2PKH / P2SH / bech32 / bech32m), not a descriptor or xpub. | **Title:** *That looks like an address.* **Body:** *To watch a wallet, TallyKeep needs the wallet's descriptor or extended public key, not a single receive address. Look for "Export descriptor", "Show extended public key", or "Account public key" in your wallet's settings.* |
| `lsp_coordinated_wallet` | Multi-path miniscript that matches a known LSP-coordinated wallet pattern (Phoenix swap-in-potentiam, similar). | **Title:** *This looks like a Lightning-coordinated wallet.* **Body:** *Wallets like Phoenix hold their on-chain balance jointly with a Lightning service provider, using a script TallyKeep can't watch independently yet. We don't support these wallets today.* |
| `multi_path_miniscript` | Multi-path miniscript that doesn't match the LSP pattern (generic `or_*` / `thresh` / hash-based fragments). | **Title:** *This descriptor has multiple spending paths.* **Body:** *TallyKeep currently supports single-path descriptors (one spending route per wallet). Descriptors with branching script logic such as recovery paths, conditional spends, or hash preimage gates aren't supported yet.* |
| `unsupported_form` | Structurally invalid for any current accept set, not matching the more-specific categories above. Catch-all for the residual cases — exotic script types, unsupported wraps, malformed-but-parseable. | **Title:** *Unsupported descriptor.* **Body:** *Supported forms are listed in each wizard's input help text. If you're sure this descriptor describes a single-key wallet, a multisig, or a timelocked vault, double-check the export format from your wallet.* (Wizard-specific accept-set list rendered below.) |
| `unparseable` | BIP 380 parser rejects the input outright (malformed brackets, invalid checksum, unrecognised script function). | **Title:** *TallyKeep can't read this.* **Body:** *This doesn't parse as a Bitcoin descriptor or an extended public key. Check for missing characters, copy errors, or paste truncation.* |

The categories are not mutually exclusive in the abstract but the
classifier returns the **most-specific** category that matches.
`lsp_coordinated_wallet` is checked before `multi_path_miniscript`
(LSP-coordinated outputs *are* multi-path, but the more specific
label gives better copy). Both are checked before
`unsupported_form` (which is the catch-all). `unparseable` short-
circuits everything else when BIP 380 parsing fails outright.

Wizard-side rendering: the `rejection_category` string drives the
choice of body text and title from the table above. Visual
treatment is identical across categories — danger palette, source
hint banner hidden, primary CTA disabled, error region above the
CTA. The visual contract is the existing per-wizard
`*_input_error_inline.html` mockups; copy variants for the new
categories are demonstrated in
`UI/mockups/mobile_add_holding_vault_input_error_inline_lsp_wallet.html`
(landed with the iteration that introduces this concern).

## Paste-time invocation, not click-time

The classification endpoint is called as the user pastes or
types in the wizard's descriptor textarea, debounced (~300ms
after last keystroke), not on the wizard's Next-button click.
This preserves the pattern the Strongbox and Vault wizards
shipped with: parseback card populates immediately on a valid
descriptor, inline error fires immediately on a rejected one,
the redirect popup is ready to show on Next-click when
`best_fit` doesn't match the wizard's own type.

**Implication for the endpoint design.** The call must be cheap
enough that paste-time invocation is fine — sub-millisecond,
idempotent, no node roundtrip, no DB write. This is a *constraint*,
not an arbitration: it argues against any future creep that would
add slow work (chain-side address-history lookups, deep miniscript
satisfiability proving, fee-rate-aware checks) to this endpoint.
If a slow component ever becomes necessary, split it into a
separate endpoint and apply the cache-and-token pattern from the
Account wizard (`shipped.md` 2026-05-22 entry — `setup_token`
TTL-cache surviving from `validate` to `create`).

## Caching posture

**No caching today.** Descriptor classification is pure CPU on a
string — parse the miniscript / wpkh / multi() tree, derive a
handful of addresses to confirm shape, return. Sub-millisecond,
no network, no node call. The complexity of caching (token TTL,
cache invalidation, single-use semantics) is not pulling weight.

**Revisit condition.** If any classification step ever grows a
slow component, apply the `setup_token` cache-and-token pattern
from the Account wizard. The frontend `validate` call returns
the token; `Holding-create` accepts the token and skips
re-classification when the token is valid (default 15 min TTL,
single-use per the Account wizard precedent). Today, the cost is
microseconds; not worth the machinery.

## Touches / consumers

- **Backend.** `POST /api/v1/descriptors/validate` (extended);
  the descriptor-adapter module that consolidates today's
  per-type `Holding-create` validation logic into one
  classification surface.
- **Frontend.** All three Add-Holding wizard pages — Purse,
  Strongbox, Vault. Each becomes a thin client of the endpoint;
  per-wizard inline classification logic is removed (acceptance
  criterion above).
- **Mockups.** `UI/mockups/mobile_add_holding_*_input_error_inline.html`
  (existing three, copy unchanged for their categories);
  `UI/mockups/mobile_add_holding_vault_input_error_inline_lsp_wallet.html`
  (new — demonstrates the LSP-wallet rejection copy in the Vault
  wizard). The visual contract for the other new copy variants
  (`multi_path_miniscript` in any wizard, `lsp_coordinated_wallet`
  in Purse / Strongbox) is the same pattern with body text from
  the rejection-taxonomy table above.
- **Future flows.** Send-from-Account source picker (filters by
  classified Holding type for the source list); Purse upgrade
  path (imported seed-or-xprv must classify as `purse`);
  descriptor-import audit tooling. Each builds on the
  consolidated surface; none re-implements the classification.
