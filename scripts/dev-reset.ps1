# Wipe and rebuild the local development stack.
#
# DESTRUCTIVE: removes the Postgres database, Redis state, and bitcoind regtest
# chain data. Survives: your code edits, docker-compose.yml, .env, anything
# outside this project.
#
# Usage:
#   .\scripts\dev-reset.ps1                          # full wipe — DB + Redis + chain
#   .\scripts\dev-reset.ps1 -KeepDb                  # keep DB; wipe Redis + chain only
#   .\scripts\dev-reset.ps1 -KeepDown                # full wipe, leave stack down after
#   .\scripts\dev-reset.ps1 -ResetPassphrase         # clear secret store only (stack stays up)

[CmdletBinding()]
param(
    [switch]$KeepDown,
    [switch]$KeepDb,
    [switch]$ResetPassphrase
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

# -ResetPassphrase: clear crypto_parameters + canary so you can re-initialize.
# Does not touch the stack or any other data.
if ($ResetPassphrase) {
    Write-Host "==> Clearing secret store (crypto_parameters + canary)"
    docker exec tallykeep-postgres psql -U tallykeep -d tallykeep `
        -c "DELETE FROM crypto_parameters; DELETE FROM secret WHERE reference = '__canary__';"
    Write-Host "==> Done. Call POST /api/v1/unlock/initialize to set a new passphrase."
    exit 0
}

# Derive the compose project name so volume names don't need to be hardcoded.
$ProjectName = (docker-compose config 2>$null |
    Select-String '^\s*name\s*:' |
    Select-Object -First 1) -replace '.*:\s*', ''
if (-not $ProjectName) { $ProjectName = 'tallykeep' }

if ($KeepDb) {
    Write-Host "==> Bringing the stack down (postgres-data kept)"
    docker-compose down --remove-orphans
    Write-Host "==> Removing Redis and bitcoind volumes"
    docker volume rm "${ProjectName}_redis-data" "${ProjectName}_bitcoind-data"
} else {
    Write-Host "==> Bringing the stack down with all volumes (DESTRUCTIVE)"
    docker-compose down -v --remove-orphans
}

if ($KeepDown) {
    Write-Host "==> Done. Stack is down."
    exit 0
}

Write-Host "==> Bringing the stack back up"
docker-compose up -d

Write-Host "==> Waiting for backend to be healthy"
$deadline = (Get-Date).AddSeconds(60)
while ($true) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2 | Out-Null
        break
    } catch {
        if ((Get-Date) -ge $deadline) {
            Write-Error "Backend did not become healthy within 60s."
            docker-compose ps
            exit 1
        }
        Start-Sleep -Seconds 1
    }
}

if ($KeepDb) {
    Write-Host "==> Done. Stack is up with your existing data."
    Write-Host "    Unlock with your passphrase, then re-mine some regtest blocks if needed."
} else {
    Write-Host "==> Done. Fresh stack is up at http://127.0.0.1:8000"
    Write-Host "    Initialize the secret store with:"
    Write-Host "      Invoke-RestMethod -Method Post ``"
    Write-Host "        -Uri http://127.0.0.1:8000/api/v1/unlock/initialize ``"
    Write-Host "        -ContentType 'application/json' ``"
    Write-Host "        -Body '{`"passphrase`":`"YOUR_PASSPHRASE`"}'"
}
