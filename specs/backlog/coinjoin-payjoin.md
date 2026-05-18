# CoinJoin / PayJoin

- **Captured:** 2026-05 (from module 12 v3, pre-retirement)
- **Motivation:** Privacy-preserving collaborative transactions.
  PayJoin (BIP 78) breaks the common-input-ownership heuristic by
  having the receiver contribute inputs. CoinJoin (Wabisabi or
  similar) lets multiple parties combine into one tx with no shared
  ownership inference.
- **Sketch:** PayJoin first as initiator and responder (smaller
  scope, doesn't require coordinator infrastructure). CoinJoin
  later, likely via integration with an existing coordinator
  (Wasabi, JoinMarket) rather than running our own.
- **Touches:** banking layer, send / receive flows, threat model,
  Blueprint analyzer (CoinJoin output classification)
- **Status:** idea
- **Milestone:** post-shipping
- **Notes:** This entry covers TallyKeep *initiating* CoinJoin /
  PayJoin. The complementary "Mixed-input transaction flagging"
  entry covers *detecting* collaborative transactions initiated by
  the user's other wallets — both should land coherently so the
  Blueprint analyzer surfaces collaborative-tx outputs distinctly
  rather than mis-classifying them.
