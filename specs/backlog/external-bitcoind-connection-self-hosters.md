# External bitcoind connection (self-hosters)

- **Captured:** 2026-05 (Rémy, module 03 review).
- **Motivation:** Self-hosters who already run a Bitcoin Core
  node shouldn't be forced to run a second `bitcoind` in the
  TallyKeep Docker stack. Today's stack ships its own `bitcoind`
  service; users with an existing node end up with two running.
  This costs disk (pruned or not), bandwidth (two IBDs if
  someone's not careful), and operational complexity.
- **Sketch:** A configuration option in `configuration.toml`
  that points TallyKeep at an external `bitcoind` — RPC host /
  port / cookie / user-password, plus ZMQ endpoints — instead of
  spinning up the Docker-internal one. The Docker Compose file
  needs a profile or override that excludes the internal
  bitcoind service. Onboarding-time check verifies the external
  node has the required RPC methods + ZMQ topics enabled
  (`zmqpubrawblock`, `zmqpubrawtx`, `zmqpubhashblock` — already
  documented in `concerns/observation.md`); if missing, surfaces
  the exact `bitcoin.conf` lines to add and refuses to start
  until they're present.
- **Touches:** `01_architecture.md` service topology (becomes
  optional), `configuration.toml` schema, install guide,
  `concerns/observation.md` "Configuration requirement" section.
- **Status:** sketched
- **Milestone:** pre-shipping (private-ship enabler for
  self-hosters who already run bitcoind; can land anytime once
  Rémy hits the case in his own setup or another self-hoster
  asks for it).
- **Notes:** Hosted-tier users don't touch this — the hosted
  backend manages bitcoind centrally.
