# PSBT-by-QR roundtrip on mobile

- **Captured:** 2026-05 (pre-implementation item `psbt-by-qr-mobile`)
- **Motivation:** Lets mobile send from Strongbox to QR-PSBT-capable
  hardware wallets (Coldcard, Jade) without round-tripping through
  desktop.
- **Sketch:** Capacitor camera scans QR PSBT (signed by HW wallet);
  Capacitor displays QR PSBT (unsigned, for HW wallet to scan).
  Multi-frame for large PSBTs.
- **Touches:** UI mobile send-from-Strongbox flow, QR plugin, PSBT
  serializer
- **Status:** sketched
- **Milestone:** post-shipping
- **Notes:** Per-vendor QR PSBT specifics (UR, BBQR) need a small
  compatibility matrix. Could alternatively land pre-shipping if
  mobile-only Strongbox flow becomes a launch priority — Rémy's
  call when the time comes.
