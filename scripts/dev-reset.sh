#!/usr/bin/env bash
# Wipe and rebuild the local development stack.
#
# DESTRUCTIVE: removes the Postgres database (Holdings, Descriptors, Ledger
# entries, secrets, runtime configuration), the Redis state (event bus, RQ
# queues), and the bitcoind regtest chain data. Use this when you want a
# pristine starting point for testing.
#
# Survives this command:
#   - your code edits (mounted into the containers, not part of the volumes)
#   - the .env / docker-compose.yml on disk
#   - any data you have outside this project
#
# Usage:
#   ./scripts/dev-reset.sh                       # reset and bring stack back up
#   ./scripts/dev-reset.sh --keep-down           # reset and leave the stack down

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

KEEP_DOWN=0
for arg in "$@"; do
  case "$arg" in
    --keep-down) KEEP_DOWN=1 ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: $0 [--keep-down]" >&2
      exit 2
      ;;
  esac
done

echo "==> Bringing the stack down with volumes (DESTRUCTIVE)"
docker compose down -v --remove-orphans

if [ "$KEEP_DOWN" -eq 1 ]; then
  echo "==> Done. Stack is down; volumes were wiped."
  exit 0
fi

echo "==> Bringing the stack back up"
docker compose up -d

echo "==> Waiting for backend to be healthy"
deadline=$((SECONDS + 60))
until curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "ERROR: backend did not become healthy within 60s." >&2
    docker compose ps
    exit 1
  fi
  sleep 1
done

echo "==> Done. Fresh stack is up at http://127.0.0.1:8000"
echo "    Initialize the secret store with:"
echo "      curl.exe --% -X POST -H \"Content-Type: application/json\" \\"
echo "        -d \"{\\\"passphrase\\\":\\\"YOUR_PASSPHRASE\\\"}\" \\"
echo "        http://127.0.0.1:8000/api/v1/unlock/initialize"
