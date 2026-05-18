# Blueprint analysis

- **Captured:** 2026-05 (Rémy decision — refines original module 05
  scope which originally had Blueprint as v1)
- **Motivation:** Privacy / hygiene analyzer surfacing address reuse,
  dust UTXOs, round-number outputs, suspected consolidation. Strong
  public-product differentiator (most Bitcoin apps don't help users
  see these patterns). Backend logic per `concerns/observation.md` is already
  implemented; what's deferred is the UI surface.
- **Sketch:**
    - Three summary tiles (address reuse, dust UTXOs,
      round-number outputs)
    - Severity-tagged recommendations with concrete actions and
      per-finding dismissal
    - Surfaced contextually after first Strongbox or Vault creation,
      and via Settings for opt-in users
    - Plus (further out) UTXO clustering graph for visualizing
      transaction history privacy
- **Touches:** UI mobile + desktop, possibly a dedicated Privacy /
  Blueprint section in nav
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Backend logic per `concerns/observation.md` implemented and stays. UI
  surface deferred. The clustering graph is further deferred and
  likely desktop-only when it lands. During pre-shipping Rémy works
  without Blueprint surfaced; post-shipping users get it as a
  feature update — credible reason to keep the app updated and a
  differentiator against most Bitcoin wallets.
