# BLE / NFC transport for payment payloads

- **Captured:** 2026-05 (from module 12 v3, pre-retirement)
- **Motivation:** "Tap-to-pay between two app instances on the same
  LAN" is a UX expectation set by fiat banking apps. Bitcoin doesn't
  need a new protocol — BLE / NFC just transports BIP21 (on-chain)
  or BOLT11 / BOLT12 (Lightning) payloads instead of QR.
- **Sketch:** Capacitor plugins for BLE and NFC. Send flow gets a
  "Tap to send" affordance for nearby TallyKeep instances; receive
  flow can broadcast a payment URI over BLE / NFC. Falls back to
  QR cleanly.
- **Touches:** Capacitor build, send / receive flows, native
  plugin layer
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** Capacitor-only (browser builds can't access BLE / NFC
  reliably). Honest disclosure: it's a transport upgrade, not a new
  protocol — the underlying Bitcoin transaction is identical.
