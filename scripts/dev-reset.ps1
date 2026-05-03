# Wipe and rebuild the local development stack.
#
# DESTRUCTIVE: removes the Postgres database, Redis state, and bitcoind regtest
# chain data. Survives: your code edits, docker-compose.yml, .env, anything
# outside this project.
#
# Usage:
#   .\scripts\dev-reset.ps1               # reset and bring stack back up
#   .\scripts\dev-reset.ps1 -KeepDown     # reset and leave the stack down

[CmdletBinding()]
param(
    [switch]$KeepDown
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

Write-Host "==> Bringing the stack down with volumes (DESTRUCTIVE)"
docker compose down -v --remove-orphans

if ($KeepDown) {
    Write-Host "==> Done. Stack is down; volumes were wiped."
    exit 0
}

Write-Host "==> Bringing the stack back up"
docker compose up -d

Write-Host "==> Waiting for backend to be healthy"
$deadline = (Get-Date).AddSeconds(60)
while ($true) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2 | Out-Null
        break
    } catch {
        if ((Get-Date) -ge $deadline) {
            Write-Error "Backend did not become healthy within 60s."
            docker compose ps
            exit 1
        }
        Start-Sleep -Seconds 1
    }
}

Write-Host "==> Done. Fresh stack is up at http://127.0.0.1:8000"
Write-Host "    Initialize the secret store with:"
Write-Host "      Invoke-RestMethod -Method Post ``"
Write-Host "        -Uri http://127.0.0.1:8000/api/v1/unlock/initialize ``"
Write-Host "        -ContentType 'application/json' ``"
Write-Host "        -Body '{`"passphrase`":`"YOUR_PASSPHRASE`"}'"
