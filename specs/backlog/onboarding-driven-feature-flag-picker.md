# Onboarding-driven feature-flag picker

- **Captured:** 2026-05 (Rémy, module 03/04 review — flagged
  that the onboarding iteration shipped without the
  feature-flag selection step that the spec assumes seeds
  initial flag values).
- **Motivation:** `concerns/feature_flags.md` describes a small
  set of onboarding questions that seed initial flag values (2–3
  questions, mapping answers to a flag bundle). The onboarding
  iteration (`mobile_onboarding_*`) shipped without those
  questions — the user lands on Home with `DEFAULT_FLAG_VALUES`
  applied, and tunes individual flags from Settings later. The
  spec's "Onboarding UI contract" section is therefore not yet
  implemented.
- **Sketch:** A 2–3 screen onboarding sub-flow inserted between
  the existing paired / biometric / passphrase screens and the
  Home page. Question shape (per `concerns/feature_flags.md`
  "Onboarding-driven defaults"):
  - *Bitcoin holding posture* — exchange, phone wallet, hardware
    wallet, multiple, none yet.
  - *Detail-density preference* — technical details visible by
    default, or surfaced on demand.
  - *Custodial connection* — will the user connect an exchange
    / broker account, or use TallyKeep purely for self-custody.
  - The mapping from answers to flag bundles is implementation
    detail (not domain — refining later doesn't require an ADR).
- **Touches:** `UI/mobile.md` onboarding section, new mockups in
  `UI/mockups/` (`mobile_onboarding_03_questions_*.html`),
  `concerns/feature_flags.md` onboarding-UI-contract section
  becomes implemented rather than aspirational, frontend
  onboarding state machine.
- **Status:** sketched
- **Milestone:** pre-shipping (private-ship). The fact that
  it shipped without these questions is a spec-vs-code gap
  worth closing before the private-ship event.
- **Notes:** Skip-onboarding fallback (per existing spec) means
  this can ship without breaking the current code path —
  questions are additive; if the user skips them, `DEFAULT_FLAG_VALUES`
  apply as today.
