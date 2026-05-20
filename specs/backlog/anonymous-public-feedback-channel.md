# Anonymous public-feedback channel

- **Captured:** 2026-05-20 (Forget-vs-archive brainstorm session;
  raised by Rémy as a tangent — *"worst case, this can re-appear
  if the product ever ship to public, we'll need an anonymous
  way to get feedback from user without them being suspicious
  we'll connect the dots with their holdings"*. Flagged
  explicitly as "not the topic here" — captured here for
  re-evaluation when public-ship gets closer.)
- **Motivation:** Once TallyKeep ships publicly, two pressures
  collide:
    1. **The product needs real user signal** to evolve. Which
       flows confuse people? Which features get used? Which
       deferred ideas (Archive-as-hide, automatic
       categorization, multi-device sync, …) do real users
       actually ask for? Without a feedback path, the spec
       drifts on founder intuition alone.
    2. **The privacy posture forbids the obvious answer.**
       The frontend can't ship "send us your Holdings list
       and we'll see what you're using" — that's exactly the
       trust break the banking-ergonomics + self-hosted
       framing exists to prevent. Even an opt-in
       "share telemetry" toggle is suspect: users who decline
       still want to know that *the people who accepted* aren't
       letting TK correlate feedback messages with their
       Account API keys, descriptor xpubs, or balance
       histories.
   So the channel needs to be **structurally** anonymous, not
   just policy-anonymous. The user has to be able to verify
   from the architecture that TK cannot link a feedback
   message to a Holdings inventory, even if it wanted to.
- **Sketch:** Likely shapes (none committed):
    - **Hosted-only.** Feedback channel is a TK-operated
      endpoint that self-hosted backends don't touch.
      Self-hosters who want to contribute pick their own
      delivery mechanism (GitHub, email, anonymous Tor form).
    - **Blind-relay submission.** Frontend POSTs feedback
      directly to a TK-operated relay, no backend
      pass-through. Backend (self-hosted or TK-hosted) never
      sees the message. Body carries only what the user
      typed plus a coarse install-fingerprint (TK version,
      OS, locale) — no user_id, no holdings_count, no
      feature-flag bundle.
    - **Onion or mixnet** for the submission to break IP
      correlation (cost: complexity, dependency on
      external infra).
    - **No client-side telemetry at all** in v1; rely
      purely on user-initiated feedback messages. Cleaner
      privacy story, weaker signal.
    - **Aggregate-only telemetry as an opt-in second
      channel** (separate from feedback). Anonymised counts
      of feature usage with k-anonymity guarantees. Different
      threat model than the message channel; should be
      designed separately if at all.
- **Touches:** frontend (feedback UI surface, submission
  client), TK-operated relay infra, threat model (`concerns/threat_model.md`
  privacy section), legal posture (GDPR — even structurally
  anonymous channels need a privacy notice), marketing
  posture (banking-ergonomics trust contract).
- **Status:** parked idea
- **Milestone:** **public-ship-adjacent** — irrelevant
  pre-private-ship (no public users to hear from); becomes
  load-bearing the moment the project has external users
  and wants to evolve the product based on their input.
  Critique mode applies (per project instructions, this is
  a decision expensive to reverse — the privacy posture
  baked into the first feedback channel is the one users
  will judge the product on).
- **Notes:**
    - This is the channel through which the Archive-as-hide
      need (parked in ADR-0017) would surface, if it surfaces.
      If real users start asking for a "shelf this Holding
      without forgetting it" affordance, that's the signal
      to revisit. Without this channel, the signal can't
      reach the spec.
    - Adjacent to (but distinct from) the security-disclosure
      / bug-report channel a sovereign-tech product needs
      anyway. Worth considering whether the two share infra
      or stay separate; bug reports may want reply-able
      addresses, feedback wants strict anonymity.
    - Adjacent to the "usage-based feedback for long-term
      vaults" idea (`backlog/usage-based-feedback-for-long-term-vaults.md`),
      but that one is about TK→user nudges, not user→TK
      feedback. Different direction; mention here only
      because the name collides.
    - Worth a session of its own before sharpening — the
      design space is large and the choice of submission
      shape is load-bearing for trust.
