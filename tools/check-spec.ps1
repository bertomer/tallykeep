# Iteration-done sanity sweep -- PROCESS.md section 2.9
# Run before stage-3 handoff and again before the closeout commit.
# Exit 0 = all checks pass. Exit 1 = one or more failures.

[CmdletBinding()]
param()

$Root  = Split-Path $PSScriptRoot -Parent
$Specs = Join-Path $Root "specs"
$Failed = 0

function Pass($msg)  { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Fail($msg)  { Write-Host "  [FAIL] $msg" -ForegroundColor Red; $script:Failed++ }
function Skip($msg)  { Write-Host "  [SKIP] $msg" -ForegroundColor Yellow }
function Section($t) { Write-Host ""; Write-Host "=== $t ===" -ForegroundColor Cyan }


# ---------------------------------------------------------------------------
# 1. api/openapi.yaml exists and is non-trivial
# ---------------------------------------------------------------------------
Section "1. OpenAPI spec file"
$openapiPath = Join-Path $Root "api\openapi.yaml"
if (Test-Path $openapiPath) {
    $lines = (Get-Content $openapiPath | Measure-Object -Line).Lines
    if ($lines -gt 50) {
        Pass "api/openapi.yaml exists ($lines lines)"
    } else {
        Fail "api/openapi.yaml exists but is suspiciously small ($lines lines)"
    }
} else {
    Fail "api/openapi.yaml missing -- regenerate from the running backend"
}


# ---------------------------------------------------------------------------
# 2. ADR index is current
# ---------------------------------------------------------------------------
Section "2. ADR index"
$adrDir   = Join-Path $Specs "decisions"
$adrIndex = Join-Path $adrDir "README.md"

if (-not (Test-Path $adrIndex)) {
    Fail "decisions/README.md missing"
} else {
    # PowerShell -Filter does not support character-class globs; use Where-Object + regex.
    $adrFiles = Get-ChildItem $adrDir -Filter "*.md" |
                Where-Object { $_.Name -match '^\d{4}-' } |
                Select-Object -ExpandProperty Name

    $indexContent = Get-Content $adrIndex -Raw

    $missingFromIndex = @()
    $brokenInIndex    = @()

    foreach ($file in $adrFiles) {
        if ($indexContent -notmatch [regex]::Escape($file)) {
            $missingFromIndex += $file
        }
    }

    $refs = [regex]::Matches($indexContent, '\b(\d{4}-[a-z0-9-]+\.md)\b') |
            ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
    foreach ($ref in $refs) {
        if (-not (Test-Path (Join-Path $adrDir $ref))) {
            $brokenInIndex += $ref
        }
    }

    $n = $adrFiles.Count
    if ($missingFromIndex.Count -eq 0 -and $brokenInIndex.Count -eq 0) {
        Pass "ADR index is current ($n ADRs)"
    } else {
        foreach ($f in $missingFromIndex) { Fail "ADR file not in index: $f" }
        foreach ($f in $brokenInIndex)    { Fail "Index references missing file: $f" }
    }
}


# ---------------------------------------------------------------------------
# 3. Mockup index is current
# ---------------------------------------------------------------------------
Section "3. Mockup index"
$mockupDir   = Join-Path $Specs "UI\mockups"
$mockupIndex = Join-Path $mockupDir "index.html"

if (-not (Test-Path $mockupIndex)) {
    Skip "UI/mockups/index.html not found -- skipping mockup index check"
} else {
    $htmlFiles = Get-ChildItem $mockupDir -Filter "mobile_*.html" |
                 Select-Object -ExpandProperty Name | Sort-Object

    $indexContent = Get-Content $mockupIndex -Raw

    $missingFromIndex = $htmlFiles | Where-Object { $indexContent -notmatch [regex]::Escape($_) }
    $refs = [regex]::Matches($indexContent, 'mobile_[a-z0-9_]+\.html') |
            ForEach-Object { $_.Value } | Sort-Object -Unique
    $danglingInIndex = $refs | Where-Object { -not (Test-Path (Join-Path $mockupDir $_)) }

    $n = $htmlFiles.Count
    if ($missingFromIndex.Count -eq 0 -and $danglingInIndex.Count -eq 0) {
        Pass "Mockup index is current ($n mockups)"
    } else {
        foreach ($f in $missingFromIndex) { Fail "Mockup not in index: $f" }
        foreach ($f in $danglingInIndex)  { Fail "Index references missing mockup: $f" }
    }
}


# ---------------------------------------------------------------------------
# 4. No broken backtick cross-references to spec .md files
#
# Only checks references to .md files that look like spec-internal paths
# (start with a known spec-scoped prefix). Excludes:
#   - ADR files (historical refs to retired names, per PROCESS.md allow-list)
#   - archive/ directory
#   - Code-path references (backend/, frontend/) -- these are illustrative prose
#   - API endpoint paths (no file extension)
#   - _shared/ relative paths (resolve within mockups subtree)
# ---------------------------------------------------------------------------
Section "4. Backtick file references"
$mdFiles = Get-ChildItem $Specs -Filter "*.md" -Recurse |
           Where-Object {
               $_.FullName -notlike "*\archive\*" -and
               $_.FullName -notlike "*\decisions\*"
           }

# Spec-scoped path prefixes we actually want to validate.
$specPrefixes = @('specs/', 'UI/', 'brand/', 'api/', 'decisions/', 'tools/')

$broken = @()
foreach ($md in $mdFiles) {
    $content = Get-Content $md.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }

    # Only match backtick refs that end in .md and contain a directory separator.
    $pattern = '`((?:[a-zA-Z0-9_.-]+[/\\])+[a-zA-Z0-9_.-]+\.md)`'
    $backtickRefs = [regex]::Matches($content, $pattern) |
                    ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique

    foreach ($ref in $backtickRefs) {
        # Only validate refs that start with a known spec-scoped prefix.
        $isSpecRef = $specPrefixes | Where-Object { $ref -like "$_*" }
        if (-not $isSpecRef) { continue }

        # Allow-list: refs that are intentional prose references to proposals or
        # ideas that were never actual files in the spec tree.
        $allowList = @('UI/backend_deltas.md')
        if ($allowList -contains $ref) { continue }

        $candidates = @(
            (Join-Path $Specs $ref),
            (Join-Path (Split-Path $md.FullName) $ref),
            (Join-Path $Root $ref),
            # Retired files may live in archive/ -- check there too.
            (Join-Path $Specs "archive\$ref")
        )
        $found = $candidates | Where-Object { Test-Path $_ }
        if ($found.Count -eq 0) {
            $broken += "$($md.Name): ``$ref``"
        }
    }
}

if ($broken.Count -eq 0) {
    Pass "No broken spec-internal .md cross-references"
} else {
    foreach ($b in $broken) { Fail $b }
}


# ---------------------------------------------------------------------------
# 5. Brand lockstep: no brand lock doc newer than tokens.css
# ---------------------------------------------------------------------------
Section "5. Brand lockstep"
$tokensCss  = Join-Path $Specs "UI\mockups\_shared\tokens.css"
$brandLocks = Get-ChildItem (Join-Path $Specs "brand") -Filter "*_lock.html" -Recurse -ErrorAction SilentlyContinue

if (-not (Test-Path $tokensCss)) {
    Fail "UI/mockups/_shared/tokens.css missing"
} else {
    $tokensTime = (Get-Item $tokensCss).LastWriteTime
    $stale = @()
    foreach ($lock in $brandLocks) {
        if ($lock.LastWriteTime -gt $tokensTime) {
            $stale += $lock.Name
        }
    }
    if ($stale.Count -eq 0) {
        Pass "tokens.css is at least as recent as all brand lock docs"
    } else {
        foreach ($s in $stale) {
            Fail "Brand lock doc newer than tokens.css -- check lockstep: $s"
        }
    }
}


# ---------------------------------------------------------------------------
# 6. pre-implementation.md contains no decided/closed items
# ---------------------------------------------------------------------------
Section "6. pre-implementation.md open items only"
$preImpl = Join-Path $Specs "pre-implementation.md"
if (-not (Test-Path $preImpl)) {
    Skip "pre-implementation.md not found"
} else {
    $content = Get-Content $preImpl -Raw
    $decidedMatches = [regex]::Matches($content, '(?im)^#{1,4}\s.*(decided|closed|resolved|shipped)\b')
    if ($decidedMatches.Count -eq 0) {
        Pass "No decided/closed items in pre-implementation.md"
    } else {
        foreach ($m in $decidedMatches) {
            Fail "Decided item still in pre-implementation.md: $($m.Value.Trim())"
        }
    }
}


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
Write-Host ""
if ($Failed -eq 0) {
    Write-Host "=== Sanity sweep PASSED ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== Sanity sweep FAILED -- $Failed check(s) failed ===" -ForegroundColor Red
    exit 1
}
