# Web admin — Tier 2 (rotation, version, logs)

- **Captured:** 2026-05-27, during the unlock-flow-cleanup design
  session (Rémy + Claude). The web admin Tier 1 (login + install
  wizard + pairing + paired-devices view + revoke) is carving out
  into its own iteration; Tier 2 is the follow-up scope.
- **Motivation:** Tier 1 ships the bug fixes that block daily-use
  friction (refresh-redirects, server-reboot-no-relock) and the
  setup surface mobile pairing depends on. Rotation, version
  visibility, and log access are admin conveniences that are not
  load-bearing for daily use — splitting them lets Tier 1 ship
  faster and unblock mobile-side pairing work.

## Scope sketch

Three admin operations, all hosted on the web admin per ADR-0020:

1. **Passphrase rotation.** Per ADR-0008 Addendum 2026-05-27. Flow:
   operator confirms current passphrase, types new passphrase
   (twice), backend re-encrypts the secrets store under the new
   passphrase atomically, emits `system.passphrase_rotated` SSE,
   invalidates all active session tokens and per-device credentials
   (or marks them re-confirm-required), forces re-login on web
   admin and re-prompt-on-next-decryption on mobile. The
   re-encryption step is the load-bearing transaction — all-or-
   nothing, audited.
2. **Version status surface.** Display-only screen showing backend
   version, frontend version, bitcoind version, last upgrade
   timestamp, "update available" indicator (sourced from a
   release-feed the operator can configure; out of scope for v1 if
   it requires phone-home). The "no telemetry, ever" line from
   `00_README.md` holds — update checks are pull-from-feed, not
   phone-home, and probably opt-in.
3. **Log access.** Tail / search interface for the last N hours of
   structured JSON logs (per `01_architecture.md §Observability`).
   Sensitive-field redaction already happens at the log layer; the
   web admin just renders what's there. Useful for the operator to
   diagnose "what's happening" without SSHing into the host.

## Open design questions for the Tier 2 brainstorm

- **Rotation atomicity.** What happens if the re-encryption is
  interrupted (host crashes, container restart) mid-transaction?
  The locked principle is "no half-rotated state" — either the
  new passphrase is the active one and all secrets are
  re-encrypted, or the old one is. Two-phase commit on the
  secrets table, or write-new-encrypted-blob-then-swap?
  Implementation detail but worth thinking through before
  sharpening.
- **Session-token invalidation on rotation.** Wipe all sessions
  (including the rotating session itself; operator re-logs after
  rotation) is the conservative call. Re-issue the rotating
  session's token under the new passphrase is the convenience
  call but adds a state machine. Recommendation: wipe all,
  including current; re-login after rotation. Friction is
  acceptable for a once-a-year-at-most operation.
- **Per-device credential behavior on rotation.** Two options:
  (a) credentials survive rotation (the credential is independent
  of the passphrase; rotation doesn't invalidate it); (b)
  credentials are marked re-confirm-required (next mobile op
  that requires decryption prompts the user to re-enter the new
  passphrase before the credential is reaffirmed). (b) matches
  the banking-app model ("change your bank password and we'll
  ask you to re-confirm on each device next time"). (a) is
  simpler but means a stolen phone after rotation still works
  if the thief never needs decryption — which they don't for
  pure observation. Recommendation: (b).
- **Update-feed source for version status.** Anthropic's
  Anthropic update mechanism, GitHub releases, a TallyKeep-
  hosted feed, or operator-supplied URL. The phone-home
  prohibition applies. Probably: opt-in feed, default off, with
  GitHub releases as the suggested URL when the operator opts
  in.
- **Log retention and rotation.** The web admin's "tail logs"
  view should not encourage indefinite retention; default is
  whatever the host's log driver provides. Probably no UI for
  log-retention configuration — that's the host's job.

## Dependencies

- Web admin Tier 1 must ship first (login + session-token + admin
  routes scaffolded).
- ADR-0008 Addendum 2026-05-27 already pre-locks the architectural
  call (rotation lives in web admin, not mobile); this iteration
  is the implementation pass.

## Milestone

**Pre-shipping (private-ship gate, post Tier 1).** Rotation
visibility raises the daily-use security posture; version + logs
are operator-quality-of-life. None of the three blocks daily
mobile use directly, so this can ship after Strongbox Send + Receive
and the Tier 1 web admin if either of those needs the calendar.

## Notes

- The "no telemetry, ever" line from `00_README.md` constrains the
  version-update flow shape — pull-from-feed, never phone-home.
- The log surface might reuse the existing structured-JSON output
  rather than introduce a new logging layer.
