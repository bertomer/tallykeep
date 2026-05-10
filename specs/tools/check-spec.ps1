#!/usr/bin/env pwsh
# check-spec.ps1 — iteration-done sanity sweep for the specs/ tree
# (per PROCESS.md §2.9). PowerShell mirror of tools/check-spec.sh,
# kept in sync. Either is sufficient; the .ps1 is the recommended
# entry point on Windows since the backend smoke-tests are .ps1.
#
# Catches the drift the consolidation merge was supposed to end:
# stale ADR index, stale mockup index, broken cross-references,
# "Decided" sections sneaking back in, OpenAPI missing, brand
# lock-doc edits that didn't propagate to tokens.css.
#
# Usage:
#   .\tools\check-spec.ps1               # run from anywhere
#   .\tools\check-spec.ps1 -Quiet        # only print failures
#
# Exit codes:
#   0  all checks pass
#   1  one or more checks failed (drift to fix in the same commit)
#   2  invocation error (specs/ root not resolvable)
#
# Compatible with Windows PowerShell 5.1 and PowerShell 7+.

[CmdletBinding()]
param(
    [switch]$Quiet
)

# We do our own error handling per check; don't blow up on the first
# Get-ChildItem that returns nothing.
$ErrorActionPreference = 'Continue'

# ---- locate ourselves ----
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
try {
    $specsDir = (Resolve-Path (Join-Path $scriptDir '..')).Path
} catch {
    Write-Host "cannot resolve specs/ root from $scriptDir"
    exit 2
}
Set-Location $specsDir

$script:failCount = 0

function Section($name) {
    if (-not $Quiet) {
        Write-Host ""
        Write-Host "=== $name ==="
    }
}
function Ok($msg) {
    if (-not $Quiet) {
        Write-Host "  ok  $msg"
    }
}
function Fail($msg) {
    Write-Host "  FAIL  $msg"
    $script:failCount++
}

function Get-RelPath($fullPath) {
    $rel = $fullPath.Substring($specsDir.Length).TrimStart('\', '/')
    return $rel -replace '\\', '/'
}

# ---- 1. OpenAPI present ----
Section "OpenAPI present"
$openApi = "api/openapi.yaml"
if (Test-Path $openApi) {
    $size = (Get-Item $openApi).Length
    if ($size -lt 100) {
        Fail "$openApi is suspiciously small ($size bytes)"
    } else {
        Ok "$openApi exists ($size bytes)"
    }
} else {
    Fail "$openApi is missing - regenerate from the running backend (see api/README.md)"
}

# ---- 2. ADR index in decisions/README.md matches files ----
Section 'ADR index <-> files'
$adrFiles = Get-ChildItem -Path "decisions" -File -Filter "*.md" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d{4}-' } |
    Select-Object -ExpandProperty Name |
    Sort-Object

if (-not $adrFiles) { $adrFiles = @() }

$adrReadmePath = "decisions/README.md"
$listedAdrs = @()
if (Test-Path $adrReadmePath) {
    $adrReadme = Get-Content $adrReadmePath -Raw
    # Match any markdown link whose target ends in NNNN-*.md.
    $listedAdrs = [regex]::Matches($adrReadme, '\]\((\d{4}-[A-Za-z0-9._-]+\.md)\)') |
                  ForEach-Object { $_.Groups[1].Value } |
                  Sort-Object -Unique
} else {
    Fail "$adrReadmePath is missing"
}
if (-not $listedAdrs) { $listedAdrs = @() }

$missingInIndex = $adrFiles  | Where-Object { $listedAdrs -notcontains $_ }
$missingFiles   = $listedAdrs | Where-Object { $adrFiles  -notcontains $_ }

foreach ($f in $missingInIndex) {
    Fail "ADR file $f is not listed in decisions/README.md"
}
foreach ($f in $missingFiles) {
    Fail "decisions/README.md references missing file $f"
}
if (-not $missingInIndex -and -not $missingFiles -and $adrFiles.Count -gt 0) {
    Ok "$($adrFiles.Count) ADR(s) indexed and present"
}

# ---- 3. Mockup index in UI/mockups/index.html matches files ----
Section 'Mockup index <-> files'
$indexHtml = "UI/mockups/index.html"
if (Test-Path $indexHtml) {
    $mockupFiles = Get-ChildItem -Path "UI/mockups" -File -Filter "mobile_*.html" -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Name |
        Sort-Object
    if (-not $mockupFiles) { $mockupFiles = @() }

    # Strip JS comments so commented-out example entries don't count
    # as listed.
    $raw = Get-Content $indexHtml -Raw
    $raw = $raw -replace '(?s)/\*.*?\*/', ''   # block comments
    $raw = $raw -replace '(?m)//.*$', ''       # line comments

    $listedMockups = [regex]::Matches($raw, 'mobile_[a-zA-Z0-9_]+\.html') |
                     ForEach-Object { $_.Value } |
                     Sort-Object -Unique
    if (-not $listedMockups) { $listedMockups = @() }

    $missingInIdx = $mockupFiles   | Where-Object { $listedMockups -notcontains $_ }
    $missingInFs  = $listedMockups | Where-Object { $mockupFiles   -notcontains $_ }

    foreach ($f in $missingInIdx) {
        Fail "mockup $f is not listed in UI/mockups/index.html"
    }
    foreach ($f in $missingInFs) {
        Fail "UI/mockups/index.html references missing mockup $f"
    }
    if (-not $missingInIdx -and -not $missingInFs) {
        Ok "$($mockupFiles.Count) mockup(s) indexed and present"
    }
} else {
    Fail "$indexHtml is missing"
}

# ---- 4. No broken backtick file refs in non-archive docs ----
Section "Backtick file refs resolve"

# Allow-list: documented placeholder / illustrative names that
# intentionally don't resolve to a file (naming-convention examples,
# template placeholders, retired-file references kept for historical
# context in ADRs).
$allowList = @(
    '\.\.\._v(\d+|N)_lock\.html',
    '\.\.\._fiat_(off|on)\.html',
    'colors\.md',
    'typography\.md',
    'tallykeep_<.+>_v<N>_<status>\.(html|md)',
    '<artifact>_v<N>_<status>\.(html|md)',
    '<voice-piece>_v<N>_<status>\.md',
    'mobile_<flow>_<state>\.html',
    'UI/backend_deltas\.md',
    'backend_deltas\.md',
    'backlog\.md',
    'NNNN-title\.md',
    'NNNN-short-title\.md',
    '09_profiles_and_flags\.md',
    '11_ux_flows\.md',
    '12_roadmap\.md',
    '13_open_questions\.md',
    '14_context_handoff\.md',
    'design_decisions\.md',
    'mobile_form_factor_decision\.md',
    'spec_amendments\.md',
    'handoff\.md',
    'mobile_v1\.md',
    'UI/design_decisions\.md',
    'UI/handoff\.md',
    'UI/mobile_form_factor_decision\.md',
    'UI/drafts/spec_amendments\.md',
    'specs/.+',
    'drafts/spec_amendments\.md',
    '04_api_surface\.md'
) -join '|'
$allowRegex = "^($allowList)`$"

$broken = 0
$mdFiles = Get-ChildItem -Path . -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '[\\/]archive[\\/]' }

foreach ($file in $mdFiles) {
    $content = Get-Content $file.FullName -Raw
    $refs = [regex]::Matches($content, '`([A-Za-z0-9_./-]+\.(?:md|yaml|yml|css|html|svg|sh|ps1))`') |
            ForEach-Object { $_.Groups[1].Value } |
            Sort-Object -Unique
    if (-not $refs) { continue }

    $fileDir = Split-Path -Parent $file.FullName

    foreach ($ref in $refs) {
        # already resolved by allow-list?
        if ($ref -match $allowRegex) { continue }

        # try relative to file dir, then to specs root
        $candA = Join-Path $fileDir $ref
        $candB = Join-Path $specsDir $ref
        if ((Test-Path $candA) -or (Test-Path $candB)) { continue }

        # try basename anywhere INCLUDING archive — historical refs
        # in ADRs are legitimate as long as the file exists somewhere.
        $basename = Split-Path -Leaf $ref
        $matchedFile = Get-ChildItem -Path $specsDir -Recurse -File -Filter $basename -ErrorAction SilentlyContinue |
                       Select-Object -First 1
        if (-not $matchedFile) {
            $relFile = Get-RelPath $file.FullName
            Fail "$relFile references missing ``$ref``"
            $broken++
        }
    }
}
if ($broken -eq 0) {
    Ok "no broken refs in non-archive docs"
}

# ---- 5. pre-implementation.md hygiene ----
Section "pre-implementation.md hygiene"
$preImpl = "pre-implementation.md"
if (Test-Path $preImpl) {
    $hasDecided = $false
    foreach ($line in Get-Content $preImpl) {
        if ($line -match '^## Decided\b') {
            $hasDecided = $true
            break
        }
    }
    if ($hasDecided) {
        Fail "$preImpl has a '## Decided' section - closed items should leave the file (per PROCESS.md 2.6)"
    } else {
        Ok "no 'Decided' section in $preImpl"
    }
} else {
    Fail "$preImpl is missing"
}

# ---- 6. Brand → tokens lockstep (heuristic) ----
Section "Brand -> tokens (heuristic)"
$tokens = "UI/mockups/_shared/tokens.css"
if (Test-Path $tokens) {
    $tokensMtime = (Get-Item $tokens).LastWriteTime
    $locks = Get-ChildItem -Path "brand" -File -Filter "tallykeep_*_v*_lock.html" -ErrorAction SilentlyContinue
    $anyNewer = $false
    foreach ($lock in $locks) {
        if ($lock.LastWriteTime -gt $tokensMtime) {
            Fail "$($lock.Name) is newer than tokens.css - verify color/typography lockstep (PROCESS.md 2.4)"
            $anyNewer = $true
        }
    }
    if (-not $anyNewer) {
        Ok "tokens.css timestamps not behind any locked brand artifact"
    }
} else {
    Fail "$tokens is missing"
}

# ---- summary ----
Write-Host ""
if ($script:failCount -eq 0) {
    Write-Host "PASS - sanity sweep clean."
    exit 0
} else {
    Write-Host "FAIL - $($script:failCount) check(s) failed. Fix in the same commit (PROCESS.md §2.9)."
    exit 1
}
