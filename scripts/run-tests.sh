#!/usr/bin/env bash
# Run the full non-regression suite inside the backend container.
#
# Usage:
#   ./scripts/run-tests.sh              # run all tests
#   ./scripts/run-tests.sh tests/unit   # run a subset
#
# Exit status is the exit status of pytest, so this is safe to use as a pre-commit hook
# and as the inner command of CI.

set -euo pipefail

# Resolve repo root regardless of where the script is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# `docker compose run --rm` spins up a fresh, ephemeral container. We use the existing
# backend image (`build`-on-first-use) and its dev deps. Service deps (postgres, redis,
# bitcoind) are not started for unit tests; integration tests will request them via
# `--with-deps` once they exist (M5+).
exec docker compose run --rm --no-deps -T backend pytest "$@"
