# Fiat display

- **Captured:** 2026-05 (from module 12 v1.1, pre-retirement)
- **Motivation:** Sats are the locked default unit (per `UI/README.md`),
  but optional fiat display is useful for a normal user comparing
  against everyday prices. Translation layer, not the home unit.
- **Sketch:** Behind a `display.fiat_conversion.enabled` flag. Rate
  source: the first connected CustodialProvider, with attribution
  ("via [source] · 2m ago") shown next to the consolidated value.
  Already partly described in `UI/README.md` §"Currency consolidation
  is opt-in via a single dropdown".
- **Touches:** UI mobile + desktop, settings, possibly a rate-feed
  abstraction
- **Status:** sketched
- **Milestone:** post-shipping
- **Notes:** The cross-platform decision in `UI/README.md` already
  picks the dropdown UX. What remains is the rate-source plumbing
  and the staleness display.
