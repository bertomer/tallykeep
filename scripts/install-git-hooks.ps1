# Install the project's git hooks. Windows equivalent.

$ErrorActionPreference = "Stop"

$RepoRoot = git rev-parse --show-toplevel
Set-Location $RepoRoot

git config core.hooksPath .githooks
Write-Host "Git hooks installed: core.hooksPath -> .githooks"
Write-Host "Tests will run inside the backend container on every commit."
