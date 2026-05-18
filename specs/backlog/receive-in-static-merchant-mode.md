# Receive in static / merchant mode

- **Captured:** 2026-05 (fresh-address discussion)
- **Motivation:** Default is fresh-per-payment (privacy best
  practice; the Blueprint analyzer flags reuse). Some legitimate
  use cases prefer a reused / static address: tip jars, donation
  addresses, simple merchant flows where invoice-matching happens
  out-of-band, or printed addresses on physical signs.
- **Sketch:** Per-Holding "static address mode" toggle in receive
  settings. When on, Receive always returns the same address.
  Privacy implications surfaced via a clear warning; the Blueprint
  analyzer continues to flag the reuse honestly when that feature
  ships.
- **Touches:** UI receive flow, Blueprint analyzer interaction
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Most TallyKeep users won't need this — power-user /
  specific-use-case territory. Worth recognizing as a legitimate
  need rather than treating address reuse as universally bad. Even
  most merchants prefer fresh-per-invoice (BTCPay, OpenNode,
  similar do this), but static-address has its place. Low priority;
  surface only if real users ask. Note: address reuse has no
  direct impact on transaction fees (fees are a function of tx size
  in vbytes, not addresses); the impact is on privacy / clustering
  and indirect UTXO-management complexity.
