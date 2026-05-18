# Push-driven categorization workflow

- **Captured:** 2026-05 (pre-implementation item
  `categorization-queue-mobile`, deferred parts)
- **Motivation:** When the bitcoin node detects new on-chain activity
  for a watched Holding, prompt the user to categorize it without
  forcing them to dig into a queue.
- **Sketch:** Backend SSE event when a new transaction matches a
  watched descriptor → mobile push notification (Capacitor) → tap
  opens an in-app timed popup with the transaction details and quick
  categorization affordances. Holding-detail page also shows
  uncategorized transactions inline with categorize-here affordances.
- **Touches:** backend SSE, push notification adapter, mobile UI
  notification handler, holding-detail page
- **Status:** idea
- **Milestone:** TBD — best guess: post-shipping (nice-to-have
  enhancement; not critical for launch).
- **Notes:** Hosted-tier requires push relay through TallyKeep
  infrastructure; self-hosted does it via the user's own backend.
  Privacy implications worth surfacing in onboarding for hosted-tier.
