# Descriptor → Holding-type classification cleanup

- **Captured:** 2026-05-15 (surfaced by the coding agent during
  the Vault-wizard iteration; Rémy flagged the same friction
  from his own read of the wizard codebase).
- **Motivation:** The "given this descriptor, which Holding type
  does it belong to?" decision is currently scattered. Some
  classification runs in the backend (`descriptor-validate`
  endpoint, structural-shape checks per `next_iteration.md`
  Task 1), some in the frontend wizards (per-wizard accept-set
  filters, bare-xpub auto-wrap, single-address rejection, redirect
  routing). Logic is in places duplicated across wizards, in
  places sharedly imported, in places re-implemented inline. The
  coding agent reported this as "non-trivial" and a source of
  drift when wizards' accept sets evolve. The Vault wizard
  iteration added a third copy of the routing-error branching;
  the Send-from-Account flow and the Purse upgrade path will
  each touch the same decision surface again.
- **Sketch:** Single backend endpoint — *"guess best Holding fit"*
  (working name; e.g. `POST /api/v1/descriptors/classify` or a
  shape extension of the existing `descriptor-validate`) — that
  takes a pasted descriptor (or bare xpub) and returns a tagged
  outcome:
    - `best_fit: "purse" | "strongbox" | "vault" | null`
    - the parser metadata already produced today
      (`script_type`, `derivation_path`, `key_fingerprints`,
      `required_signers`, `total_signers`, `timelock_kind`,
      `timelock_value`, `signing_metadata_present`, …)
    - rejection category when nothing fits
      (`single_address_input`, `unsupported_form`,
      `unparseable`).
  Frontend wizards become **thin**: each wizard calls the
  endpoint on paste / parse, compares `best_fit` to its own
  type — match ⇒ continue to parseback; mismatch ⇒ redirect
  popup to the correct wizard (single redirect-error pattern,
  not three); `null` ⇒ inline unsupported-form error. The
  per-wizard "is this descriptor for me?" branching disappears.
  Bare-xpub auto-wrap, single-address rejection, miniscript
  fragment detection — all collapse into the backend endpoint
  and become testable in one place. The classification rules
  in `next_iteration.md §Vault wizard Task 1` (structurally
  aware: `or_i` / `or_d` / `thresh()` / hash fragments route
  to `unsupported_form` regardless of timelock presence) become
  the spec for this endpoint, not three wizards' worth of
  parallel implementations.
- **Touches:** `concerns/observation.md` or a new
  concerns/classification.md module; `04_api_conventions.md` if a new
  endpoint family is introduced; backend descriptor parser
  (consolidates today's `descriptor-validate` + per-type
  `Holding-create` validation into one classification surface);
  three wizard frontend implementations (Purse / Strongbox /
  Vault) get slimmer; `api/openapi.yaml` regenerates.
- **Status:** idea
- **Milestone:** pre-shipping (post-Vault-wizard, before the
  Send / Receive iteration touches the same surface from the
  Account side)
- **Notes:** Worth pairing with a janitorial pass that grep-audits
  the frontend for inline descriptor parsing / classification
  logic and replaces each site with a call to the endpoint. The
  audit is part of the iteration's acceptance — "no caller in
  the frontend computes Holding-type fit from descriptor shape
  itself; all fit decisions come from the endpoint." Worth doing
  before the Purse upgrade path ships because that flow re-uses
  the same classification (an imported seed-or-xprv must still
  classify as Purse, not as a different type). If we add it
  after, we eat the cost twice.
