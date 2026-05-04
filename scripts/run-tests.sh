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

# `docker compose run --rm --build` spins up a fresh, ephemeral container and
# rebuilds the backend image when pyproject.toml or the Dockerfile changed
# (BuildKit cache makes the no-op case nearly instant). Service deps (postgres,
# redis, bitcoind) are not started by --no-deps; integration tests check
# os.environ + connectivity via session-scoped fixtures and skip when not
# reachable.
exec docker compose run --rm --build --no-deps -T backend pytest "$@"
