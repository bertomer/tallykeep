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
#   ./scripts/dev-reset.sh                       # full wipe — DB + Redis + chain
#   ./scripts/dev-reset.sh --keep-db             # keep DB; wipe Redis + chain only
#   ./scripts/dev-reset.sh --keep-down           # full wipe, leave stack down after
#   ./scripts/dev-reset.sh --reset-passphrase    # clear secret store only (stack stays up)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

KEEP_DOWN=0
KEEP_DB=0
RESET_PASSPHRASE=0
for arg in "$@"; do
  case "$arg" in
    --keep-down)        KEEP_DOWN=1 ;;
    --keep-db)          KEEP_DB=1 ;;
    --reset-passphrase) RESET_PASSPHRASE=1 ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: $0 [--keep-db] [--keep-down] [--reset-passphrase]" >&2
      exit 2
      ;;
  esac
done

# --reset-passphrase: clear crypto_parameters + canary so you can re-initialize.
# Does not touch the stack or any other data.
if [ "$RESET_PASSPHRASE" -eq 1 ]; then
  echo "==> Clearing secret store (crypto_parameters + canary)"
  docker exec tallykeep-postgres psql -U tallykeep -d tallykeep \
    -c "DELETE FROM crypto_parameters; DELETE FROM secret WHERE reference = '__canary__';"
  echo "==> Done. Call POST /api/v1/unlock/initialize to set a new passphrase."
  exit 0
fi

# Derive the compose project name so volume names don't need to be hardcoded.
PROJECT=$(docker compose config 2>/dev/null | awk '/^\s*name\s*:/{gsub(/.*:\s*/,""); print; exit}')
PROJECT=${PROJECT:-tallykeep}

if [ "$KEEP_DB" -eq 1 ]; then
  echo "==> Bringing the stack down (postgres-data kept)"
  docker compose down --remove-orphans
  echo "==> Removing Redis and bitcoind volumes"
  docker volume rm "${PROJECT}_redis-data" "${PROJECT}_bitcoind-data"
else
  echo "==> Bringing the stack down with all volumes (DESTRUCTIVE)"
  docker compose down -v --remove-orphans
fi

if [ "$KEEP_DOWN" -eq 1 ]; then
  echo "==> Done. Stack is down."
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

if [ "$KEEP_DB" -eq 1 ]; then
  echo "==> Done. Stack is up with your existing data."
  echo "    Unlock with your passphrase, then re-mine some regtest blocks if needed."
else
  echo "==> Done. Fresh stack is up at http://127.0.0.1:8000"
  echo "    Initialize the secret store with:"
  echo "      curl.exe --% -X POST -H \"Content-Type: application/json\" \\"
  echo "        -d \"{\\\"passphrase\\\":\\\"YOUR_PASSPHRASE\\\"}\" \\"
  echo "        http://127.0.0.1:8000/api/v1/unlock/initialize"
fi
