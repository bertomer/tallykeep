#!/usr/bin/env bash
# Install the project's git hooks. Idempotent.
#
# We point `core.hooksPath` at the in-repo `.githooks/` directory so hooks are versioned
# alongside the code. Run this once after cloning.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

echo "Git hooks installed: core.hooksPath -> .githooks"
echo "Tests will run inside the backend container on every commit."
