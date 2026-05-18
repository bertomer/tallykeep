# Strongbox geolocation correlation (idea, low priority)

- **Captured:** 2026-05 (Rémy, holdings review — "just an idea
  to brainstorm completely, probably to discard").
- **Motivation:** Strongbox spending requires the user to be
  physically near the hardware wallet to sign. The app could, in
  principle, verify the user's device is near the location
  associated with the Strongbox at signing time and warn if not
  ("you're spending from your Coldcard, but your phone is 500km
  from the address you tagged as its location — is this
  intentional?"). Could catch a remote-control attack scenario.
- **Sketch:**
  - Optional per-Strongbox `expected_location` (lat/lon +
    radius) set by the user during Add-Holding.
  - At PSBT-export time, the Capacitor app reads device location
    (with permission) and compares against the expected
    location.
  - Mismatch → soft warning, "warn don't block" discipline.
- **Touches:** domain (new optional field on Strongbox),
  Capacitor location plugin, send-flow UI.
- **Status:** idea (likely discard)
- **Milestone:** TBD — low priority. Rémy's own framing: "probably
  to discard". Kept here as a breadcrumb so it doesn't resurface
  cold later.
- **Notes:** Privacy implications worth a dedicated session if
  pursued — location data on a Holding row is sensitive. Could
  also be implemented client-only (location never leaves the
  device, comparison happens locally). The "remote-control
  attack" mitigation is the only real value; if that attack
  vector isn't on the threat model's top list, this feature is
  noise. Probably stays as a captured idea unless the threat
  model evolves.
