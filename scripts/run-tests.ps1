# Run the full non-regression suite inside the backend container.
#
# Usage:
#   .\scripts\run-tests.ps1             # run all tests
#   .\scripts\run-tests.ps1 tests/unit  # run a subset
#
# Windows-friendly equivalent of run-tests.sh.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

docker-compose run --rm --build --no-deps -T backend pytest @args
exit $LASTEXITCODE
