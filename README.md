# TallyKeep

A self-hosted, Bitcoin-first application that integrates **Savings**, **Banking**, and
**Trading** under one user interface and one internal API. The full v1 specification
lives in [`specs/`](./specs/) — read [`specs/00_README.md`](./specs/00_README.md) first.

> **Status:** under active development. M0 (project scaffold) is complete.
> See `CONTEXT.md` for decisions made during planning, and
> [the milestone plan](#development-plan) below for what is in flight.

## Doctrine (locked, see `specs/00_README.md`)

- The app does **not** custody keys, hold funds, create user accounts, or expose any
  public network surface in v1.
- Holdings are first-class typed entities: **Account**, **Purse**, **Strongbox**, **Vault**.
- Declared security vs observable security: the user states what each Holding *should*
  be; the analyzer continuously checks whether the on-chain reality matches.
- Minimum-exposure trading: custodial providers are pass-through liquidity, not storage.
- No regulatory surface: no order placement, no lending, no token issuance.

## Repository layout

```
tallykeep/
├── backend/               FastAPI + worker (single Python codebase, two entry points)
│   ├── tallykeep/         Source — see spec module 01 for the package map
│   └── tests/             pytest suite (unit + integration)
├── frontend/              SvelteKit PWA (M10 onwards; M0 ships a static placeholder)
├── docker/                Compose-related extras (mostly empty for now)
├── specs/                 v1 specification, 13 modules
├── scripts/               run-tests.sh, install-git-hooks.sh
├── .githooks/             versioned git hooks (pre-commit runs the NRT)
├── .github/workflows/     GitHub Actions CI (mirrors local hook)
├── docker-compose.yml     Local development stack
├── CONTEXT.md             Decisions log from planning sessions
└── README.md              this file
```

## Quickstart

Prerequisites: **Docker Desktop** (Linux containers) and **git**. Nothing else is needed
on the host — Python, Node, and bitcoind all run inside the Compose stack.

```bash
# 1. Bring the stack up.
docker compose up -d

# 2. Verify the backend is healthy.
curl http://127.0.0.1:8000/api/v1/health

# 3. Open the placeholder frontend.
#    http://127.0.0.1:8080
```

> **Windows note.** PowerShell aliases `curl` to `Invoke-WebRequest`, which uses
> different flag syntax. Either call the real curl explicitly via `curl.exe ...`
> (shipped with Windows 10+), or use the PowerShell-native command:
>
> ```powershell
> Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/health
> ```
>
> For commands with a JSON body:
>
> ```powershell
> Invoke-RestMethod -Method Post `
>   -Uri http://127.0.0.1:8000/api/v1/unlock/initialize `
>   -ContentType 'application/json' `
>   -Body '{"passphrase":"hunter2"}'
> ```

Services and their localhost ports (per spec module 01: localhost-only):

| Service     | Port (host)  | Purpose                          |
|-------------|--------------|----------------------------------|
| frontend    | `8080`       | nginx + static placeholder       |
| backend     | `8000`       | FastAPI + SSE                    |
| postgres    | `5432`       | Persistent state                 |
| redis       | `6379`       | Event bus + RQ                   |
| bitcoind    | `18443`      | regtest RPC                      |
| bitcoind    | `28332-4`    | ZeroMQ                           |

## Development workflow

After cloning, install the git hooks once:

```bash
./scripts/install-git-hooks.sh   # or .ps1 on Windows PowerShell
```

The pre-commit hook runs the full non-regression suite inside the backend container.
GitHub Actions runs the same script on push and pull request.

Run tests manually:

```bash
./scripts/run-tests.sh                  # full suite
./scripts/run-tests.sh tests/unit       # just unit tests
./scripts/run-tests.sh -k health        # filter by name
```

Integration tests need infrastructure running. Bring just what's needed and the
suite picks it up automatically (skips integration tests when nothing is up):

```bash
docker compose up -d postgres redis     # bring up just what's needed
./scripts/run-tests.sh                  # full suite, integration tests now run
```

## Inspecting the live stack

```bash
# Backend health (database / bitcoind / redis / event_bus / unlocked probes)
curl.exe http://127.0.0.1:8000/api/v1/health

# Initialize the secret store (one time per fresh Postgres volume)
curl.exe --% -X POST -H "Content-Type: application/json" \
  -d "{\"passphrase\":\"your_passphrase_here\"}" \
  http://127.0.0.1:8000/api/v1/unlock/initialize

# Re-unlock after a container restart
curl.exe --% -X POST -H "Content-Type: application/json" \
  -d "{\"passphrase\":\"your_passphrase_here\"}" \
  http://127.0.0.1:8000/api/v1/unlock

# User profile (auto-created on first call)
curl.exe http://127.0.0.1:8000/api/v1/profile

# Switch profile preset (beginner | intermediate | sovereign | custom)
curl.exe --% -X PATCH -H "Content-Type: application/json" \
  -d "{\"preset\":\"sovereign\"}" \
  http://127.0.0.1:8000/api/v1/profile

# Resolved feature flags (preset + overrides)
curl.exe http://127.0.0.1:8000/api/v1/feature-flags

# Runtime configuration (full nested object, fields default to null)
curl.exe http://127.0.0.1:8000/api/v1/configuration

# Persist a configuration value
curl.exe --% -X PATCH -H "Content-Type: application/json" \
  -d "{\"custodial_polling\":{\"interval_seconds\":600}}" \
  http://127.0.0.1:8000/api/v1/configuration

# Subscribe to the live event stream (text/event-stream).
# Default subscribes to all topics. Use ?topics=chain.*,banking.* to filter.
curl.exe -N http://127.0.0.1:8000/api/v1/events/stream

# Browse the full OpenAPI surface (every spec-module-04 route, real or stub)
# in a browser:
#   http://127.0.0.1:8000/docs

# Worker output (event bus + audit reconciler activity)
docker compose logs -f worker

# Tail backend logs
docker compose logs -f backend

# Inspect the Postgres schema or query the database
docker compose exec postgres psql -U tallykeep -d tallykeep
docker compose exec postgres psql -U tallykeep -d tallykeep -c "\dt"
docker compose exec postgres psql -U tallykeep -d tallykeep -c "TABLE event_emission_log;"

# Inspect Redis (event-bus channels, RQ queues)
docker compose exec redis redis-cli
docker compose exec redis redis-cli PUBSUB CHANNELS
docker compose exec redis redis-cli LRANGE rq:queue:tallykeep 0 -1

# Reset state — DESTRUCTIVE. Wipes Postgres, Redis, and bitcoind volumes,
# then brings the stack back up healthy.
./scripts/dev-reset.sh                  # Bash
.\scripts\dev-reset.ps1                 # PowerShell

# Reset and leave the stack down (e.g. before a long break)
./scripts/dev-reset.sh --keep-down
.\scripts\dev-reset.ps1 -KeepDown
```

## Frontend

Static placeholder served by nginx at [http://127.0.0.1:8080](http://127.0.0.1:8080).
The real SvelteKit PWA lands in M10.

## Development plan

We implement v1 in horizontal layers (per spec module 00 ordering). Each milestone
lands with its own non-regression tests; the suite must stay green forever.

| #   | Milestone                                                           | Status  |
|-----|---------------------------------------------------------------------|---------|
| M0  | Scaffold & Docker stack, /health endpoint, pytest, pre-commit, CI   | done    |
| M1  | Domain types, DB schema, secrets module, unlock flow                | done    |
| M2  | Event bus + job queue + persist-first audit                         | done    |
| M3  | API skeleton (all module-04 routes registered)                      | done    |
| M4  | Savings layer — Holdings & Descriptors (BDK address derivation)     | next    |
| M5  | Savings layer — chain scan, UTXOs, LedgerEntry, hygiene, security   | pending |
| M6  | Banking layer — outgoing PSBT + incoming Invoice (regtest)          | pending |
| M7  | Profiles & feature flags                                            | pending |
| M8  | Trading layer — adapters, sweeps, validators                        | pending |
| M9  | Live updates end-to-end (SSE)                                       | pending |
| M10 | Frontend skeleton (SvelteKit + Tailwind)                            | pending |
| M11 | Frontend onboarding + home                                          | pending |
| M12 | Frontend Holdings + Send + Receive + Categorize                     | pending |
| M13 | Frontend Trading + Blueprint + Settings                             | pending |
| M14 | Lightning placeholder + v1 polish                                   | pending |

After M14: testnet + mainnet promotion as a separate work item.

## Threat model summary

The full threat model is `specs/10_threat_model.md`. The single-line property:

> An attacker who fully compromises the host can drain operational balances (Account
> funds via withdrawal-to-whitelisted-only, plus future Lightning balance) and read the
> user's complete transaction history, but **cannot drain Strongbox or Vault funds**.

Bitcoin signing material is never on the host machine in any form. Encrypted secrets
are limited to third-party access credentials.

## License

Proprietary, all rights reserved (subject to change once a license is selected).
