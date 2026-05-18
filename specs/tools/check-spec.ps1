#!/usr/bin/env pwsh
# check-spec.ps1 — iteration-done sanity sweep for the specs/ tree
# (per PROCESS.md §4.6). PowerShell mirror of tools/check-spec.sh,
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
Push-Location $specsDir

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

# Two allow-list tiers:
#
# 1. Always-allow: documented placeholder / illustrative names that
#    intentionally don't resolve (template naming examples).
#    Legitimate in any doc.
$allowAnywhereList = @(
    # naming-convention placeholders
    '\.\.\._v(\d+|N)_lock\.html',           # "..._v1_lock.html" patterns
    '\.\.\._fiat_(off|on)\.html',           # "..._fiat_off.html" patterns
    'colors\.md',                            # illustrative ("a colors.md")
    'typography\.md',                        # illustrative
    'tallykeep_<.+>_v<N>_<status>\.(html|md)',
    '<artifact>_v<N>_<status>\.(html|md)',
    '<voice-piece>_v<N>_<status>\.md',
    'mobile_<flow>_<state>\.html',
    'NNNN-title\.md',
    'NNNN-short-title\.md'
) -join '|'
$allowAnywhereRegex = "^($allowAnywhereList)`$"

# 2. Decisions-only-allow: retired filenames that ADRs legitimately
#    reference as historical record. NOT acceptable in current
#    canonical docs (00-04, holdings/, concerns/, UI/, brand/) —
#    those should reference the current name. Scoped to decisions/
#    only to surface drift in canonical docs.
$allowDecisionsOnlyList = @(
    # retired module filenames (the 2026-05 spec reshape)
    '09_profiles_and_flags\.md',
    '09_feature_flags\.md',                  # renamed to concerns/feature_flags.md
    '11_ux_flows\.md',
    '12_roadmap\.md',
    '13_open_questions\.md',
    '14_context_handoff\.md',
    '04_api_surface\.md',
    '05_savings_layer\.md',
    '06_banking_layer\.md',
    '07_trading_layer\.md',
    '08_lightning_placeholder\.md',
    '10_threat_model\.md',
    # retired UI files (consolidation merge)
    'design_decisions\.md',
    'mobile_form_factor_decision\.md',
    'spec_amendments\.md',
    'handoff\.md',
    'mobile_v1\.md',
    'UI/design_decisions\.md',
    'UI/handoff\.md',
    'UI/mobile_form_factor_decision\.md',
    'UI/drafts/spec_amendments\.md',
    'drafts/spec_amendments\.md',
    # planned-then-rejected proposals
    'UI/backend_deltas\.md',                 # ADR-0001 §4 proposal, retired per ADR-0002
    'backend_deltas\.md',
    'backlog\.md',                           # ADR-0002 alternative, not adopted
    'future_iterations\.md'                  # flat backlog file, retired per ADR-0014 in favor of backlog/
) -join '|'
$allowDecisionsOnlyRegex = "^(?:specs/)?($allowDecisionsOnlyList)`$"

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
    $inDecisions = $file.FullName -match '[\\/]decisions[\\/]'

    foreach ($ref in $refs) {
        # tier 1: always-allowed placeholders
        if ($ref -match $allowAnywhereRegex) { continue }

        # tier 2: retired names — only acceptable inside decisions/
        if ($inDecisions -and $ref -match $allowDecisionsOnlyRegex) { continue }

        # try relative to file dir, then to specs root
        $candA = Join-Path $fileDir $ref
        $candB = Join-Path $specsDir $ref
        if ((Test-Path $candA) -or (Test-Path $candB)) { continue }

        # try basename anywhere NON-archive — covers refs that name
        # a file by basename only when it lives elsewhere in the tree.
        # archive/ is excluded so retired-only filenames fail here;
        # ADRs that legitimately reference retired names go through
        # the decisions-only allow-list above.
        $basename = Split-Path -Leaf $ref
        $matchedFile = Get-ChildItem -Path $specsDir -Recurse -File -Filter $basename -ErrorAction SilentlyContinue |
                       Where-Object { $_.FullName -notmatch '[\\/]archive[\\/]' } |
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

# ---- 7. Tail well-formedness (post-edit truncation detection) ----
# Catches the failure mode PROCESS.md 4.6 calls out: an agent edit
# silently truncates the end of a file mid-word, or duplicates a tail.
# Heuristics catch the obvious shapes; manual review is the final
# guard. False positives are easier to whitelist than truncations are
# to spot by eye.
Section "Tail well-formedness"
$tailIssues = 0
$mdFilesForTail = Get-ChildItem -Path . -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '[\\/]archive[\\/]' }

foreach ($file in $mdFilesForTail) {
    $lines = Get-Content $file.FullName
    if (-not $lines -or $lines.Count -eq 0) { continue }

    # Walk from the end; find the last non-blank line.
    $lastLine = $null
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $candidate = $lines[$i]
        if ($null -ne $candidate -and $candidate.Trim() -ne '') {
            $lastLine = $candidate
            break
        }
    }
    if ($null -eq $lastLine) { continue }
    $lastTrim = $lastLine.Trim()
    $relFile = Get-RelPath $file.FullName

    # Signal 1: file ends with a markdown header (heading with no body).
    # A complete doc almost never ends on a heading.
    if ($lastTrim -match '^#+\s') {
        Fail "$relFile ends with a header (no body after it): '$lastTrim'"
        $tailIssues++
        continue
    }

    # Signal 2: ends with a hyphenated word cut after 1-3 letters,
    # e.g. "LSP-m", "co-s". Strong truncation signature.
    if ($lastTrim -match '-[A-Za-z]{1,3}$') {
        Fail "$relFile last line ends mid-hyphenated-word: '$lastTrim'"
        $tailIssues++
        continue
    }

    # Signal 3: short line (<40 chars) ending in an alphabetic char
    # with no terminator. Catches abrupt single-word truncations
    # like "Capacitor f" or "behavi".
    if ($lastTrim.Length -lt 40 -and $lastTrim -match '[A-Za-z]$') {
        Fail "$relFile last line looks truncated (short, no terminator): '$lastTrim'"
        $tailIssues++
        continue
    }
}
if ($tailIssues -eq 0) {
    Ok "no truncated tails in non-archive docs"
}

# ---- 8. Edit sync (mtime against current iteration) ----
# Catches the buffering failure PROCESS.md sections 4.6 + 4.8 describe:
# the Cowork file tool reports a successful Edit but the bytes do not
# reach the bash mount. Files listed in next_iteration.md as affected
# should have been touched recently; stale mtime = un-flushed edit.
Section "Edit sync (mtime)"
$nextIter = "next_iteration.md"
if (-not (Test-Path $nextIter)) {
    Ok "$nextIter missing; skipping sync check"
} else {
    $niMtime = (Get-Item $nextIter).LastWriteTime
    $thresholdMtime = $niMtime.AddDays(-7)

    # Extract files listed under "#### Affected canonical docs" block
    # until next "#### " or "## " or "---" or EOF.
    $lines = Get-Content $nextIter
    $inBlock = $false
    $affectedRefs = @()
    foreach ($line in $lines) {
        if ($line -match '^#### Affected canonical docs') {
            $inBlock = $true
            continue
        }
        if ($inBlock) {
            if ($line -match '^#### ' -or $line -match '^## ' -or $line -match '^---') {
                $inBlock = $false
                continue
            }
            $refMatches = [regex]::Matches($line, '`([A-Za-z0-9_./-]+\.(?:md|yaml|yml))`')
            foreach ($m in $refMatches) {
                $affectedRefs += $m.Groups[1].Value
            }
        }
    }
    $affectedRefs = $affectedRefs | Sort-Object -Unique

    $syncIssues = 0
    $checked = 0
    foreach ($ref in $affectedRefs) {
        if ($ref -like 'UI/mockups/*') { continue }
        if (-not (Test-Path $ref)) { continue }
        $fileMtime = (Get-Item $ref).LastWriteTime
        $checked++
        if ($fileMtime -lt $thresholdMtime) {
            $daysOld = [int]($niMtime - $fileMtime).TotalDays
            Fail "$ref mtime is $daysOld days older than next_iteration.md - possible un-flushed edit (per PROCESS.md section 4.8, recover via bash heredoc)"
            $syncIssues++
        }
    }
    if ($syncIssues -eq 0) {
        Ok "$checked canonical doc(s) checked, all in sync with current iteration"
    }
}

# ---- summary ----
Write-Host ""
if ($script:failCount -eq 0) {
    Write-Host "PASS - sanity sweep clean."
    Pop-Location
    exit 0
} else {
    Write-Host "FAIL - $($script:failCount) check(s) failed. Fix in the same commit (PROCESS.md §4.6)."
    Pop-Location
    exit 1
}
