# Tap-anything-for-detail help affordance

- **Captured:** 2026-05-15 (during Vault-wizard review, Rémy
  flagged that ad-hoc info banners shouldn't be wizard-specific).
- **Motivation:** New users encountering Bitcoin / TallyKeep
  vocabulary (descriptor, miniscript, CLTV / CSV, xpub
  fingerprint, etc.) benefit from contextual help — but
  per-wizard inline hint banners create inconsistency and visual
  noise. A product-wide pattern would let any noun, parameter
  row, or field label expose a small ⓘ icon that, on tap,
  reveals a short definition + "learn more" link. Lands once,
  reused everywhere.
- **Touches:** UI shell (new ⓘ icon component, expandable
  inline panel or bottom-sheet), copy library (definitions per
  concept), every wizard and detail page that surfaces
  Bitcoin-native vocabulary.
- **Status:** idea
- **Milestone:** post-shipping. Worth surfacing once core
  flows are validated and we know which concepts users
  genuinely stall on.
