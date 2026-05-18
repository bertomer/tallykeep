# Lightning — bitcoind sharing with self-hoster

- **Captured:** 2026-05 (Rémy, observation review — flagged
  that Lightning iteration should consider the same
  bring-your-own-bitcoind shape).
- **Motivation:** The Lightning provider options (CoreLightning,
  LND, Phoenix per `concerns/lightning_placeholder.md`) all
  depend on a Bitcoin node. Self-hosters running TallyKeep with
  an external bitcoind should be able to point their Lightning
  daemon at the same node — otherwise we end up recommending
  two parallel Bitcoin nodes for a single user.
- **Sketch:** When the Lightning iteration designs the
  CLN/LND provider configuration, the option to share the
  external bitcoind (per "External bitcoind connection" above)
  is a first-class choice. Phoenix is custodial-mode for the
  LSP-managed channel layer, so it doesn't need a node — that
  case is unchanged.
- **Touches:** Lightning iteration design (when it lands), install
  guide.
- **Status:** captured for the Lightning-iteration design
  session (this entry is just a flag, not a separate iteration).
- **Milestone:** TBD — moves with the Lightning iteration.
