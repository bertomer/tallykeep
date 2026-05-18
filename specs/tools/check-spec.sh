#!/usr/bin/env bash
# check-spec.sh -- iteration-done sanity sweep for the specs/ tree
# (per PROCESS.md section 4.6).
#
# Runs in seconds. Catches the drift that the consolidation merge
# was supposed to end: stale ADR index, stale mockup index, broken
# cross-references, "Decided" sections sneaking back in, OpenAPI
# missing.
#
# Usage:
#   ./tools/check-spec.sh           # run from specs/ root
#   bash tools/check-spec.sh        # explicit
#   tools/check-spec.sh --quiet     # only print failures
#
# Exit codes:
#   0  all checks pass
#   1  one or more checks failed (drift to fix in the same commit)
#   2  invocation error (run from wrong directory, missing tool)

# Note: not using `set -u` -- the file-ref loop reads from a process
# substitution and a tripped unset-var aborts the whole script
# silently mid-loop. The script is short enough that strict mode
# isn't worth the brittleness.

# ---- locate ourselves ----
script_dir="$(cd "$(dirname "$0")" && pwd)"
specs_dir="$(cd "${script_dir}/.." && pwd)"
cd "${specs_dir}" || { echo "cannot cd to specs/"; exit 2; }

# ---- output helpers ----
quiet=0
[ "${1:-}" = "--quiet" ] && quiet=1
fail_count=0
section() { [ $quiet -eq 0 ] && echo; [ $quiet -eq 0 ] && echo "=== $* ==="; }
ok()      { [ $quiet -eq 0 ] && echo "  ok  $*"; }
fail()    { echo "  FAIL  $*"; fail_count=$((fail_count + 1)); }

# ---- 1. OpenAPI present ----
section "OpenAPI present"
if [ -f api/openapi.yaml ]; then
  size=$(wc -c < api/openapi.yaml)
  if [ "$size" -lt 100 ]; then
    fail "api/openapi.yaml is suspiciously small ($size bytes)"
  else
    ok "api/openapi.yaml exists (${size} bytes)"
  fi
else
  fail "api/openapi.yaml is missing - regenerate from the running backend (see api/README.md)"
fi

# ---- 2. ADR index in decisions/README.md matches files ----
section "ADR index <-> files"
adr_files=$(find decisions -maxdepth 1 -name '[0-9][0-9][0-9][0-9]-*.md' -printf '%f\n' | sort)
listed_adrs=$(grep -oE '\]\(([0-9]{4}-[A-Za-z0-9._-]+\.md)\)' decisions/README.md \
              | sed -E 's/^\]\(//; s/\)$//' | sort -u)
missing_in_index=$(comm -23 <(echo "$adr_files") <(echo "$listed_adrs"))
missing_files=$(comm -13 <(echo "$adr_files") <(echo "$listed_adrs"))
if [ -n "$missing_in_index" ]; then
  while IFS= read -r f; do
    [ -n "$f" ] && fail "ADR file $f is not listed in decisions/README.md"
  done <<<"$missing_in_index"
fi
if [ -n "$missing_files" ]; then
  while IFS= read -r f; do
    [ -n "$f" ] && fail "decisions/README.md references missing file $f"
  done <<<"$missing_files"
fi
[ -z "$missing_in_index" ] && [ -z "$missing_files" ] \
  && ok "$(echo "$adr_files" | grep -c .) ADR(s) indexed and present"

# ---- 3. Mockup index in UI/mockups/index.html matches files ----
section "Mockup index <-> files"
if [ -f UI/mockups/index.html ]; then
  mockup_files=$(find UI/mockups -maxdepth 1 -name 'mobile_*.html' -printf '%f\n' | sort)
  listed_mockups=$(awk '
      BEGIN { in_block = 0 }
      {
        line = $0
        while (in_block && (idx = index(line, "*/"))) {
          line = substr(line, idx + 2); in_block = 0
        }
        if (in_block) next
        while ((idx = index(line, "/*"))) {
          end = index(substr(line, idx), "*/")
          if (end) { line = substr(line, 1, idx - 1) substr(line, idx + end + 1) }
          else     { line = substr(line, 1, idx - 1); in_block = 1; break }
        }
        sub(/\/\/.*$/, "", line)
        print line
      }
    ' UI/mockups/index.html \
    | grep -oE 'mobile_[a-zA-Z0-9_]+\.html' | sort -u)
  missing_in_idx=$(comm -23 <(echo "$mockup_files") <(echo "$listed_mockups"))
  missing_in_fs=$(comm -13 <(echo "$mockup_files") <(echo "$listed_mockups"))
  if [ -n "$missing_in_idx" ]; then
    while IFS= read -r f; do
      [ -n "$f" ] && fail "mockup $f is not listed in UI/mockups/index.html"
    done <<<"$missing_in_idx"
  fi
  if [ -n "$missing_in_fs" ]; then
    while IFS= read -r f; do
      [ -n "$f" ] && fail "UI/mockups/index.html references missing mockup $f"
    done <<<"$missing_in_fs"
  fi
  count=$(echo "$mockup_files" | grep -c . || true)
  [ -z "$missing_in_idx" ] && [ -z "$missing_in_fs" ] \
    && ok "${count} mockup(s) indexed and present"
else
  fail "UI/mockups/index.html is missing"
fi

# ---- 4. No broken backtick file refs in non-archive docs ----
section "Backtick file refs resolve"
broken=0
# Tier 1: always-allowed placeholders (illustrative naming examples).
allow_anywhere='^(\.\.\._v([0-9]+|N)_lock\.html|\.\.\._fiat_(off|on)\.html|colors\.md|typography\.md|tallykeep_<.+>_v<N>_<status>\.(html|md)|<artifact>_v<N>_<status>\.(html|md)|<voice-piece>_v<N>_<status>\.md|mobile_<flow>_<state>\.html|NNNN-title\.md|NNNN-short-title\.md)$'
# Tier 2: retired filenames - acceptable only inside decisions/ where
# ADRs preserve them as historical record. Same name in a current
# canonical doc is drift.
allow_decisions_only='^(specs/)?(09_profiles_and_flags\.md|09_feature_flags\.md|11_ux_flows\.md|12_roadmap\.md|13_open_questions\.md|14_context_handoff\.md|04_api_surface\.md|05_savings_layer\.md|06_banking_layer\.md|07_trading_layer\.md|08_lightning_placeholder\.md|10_threat_model\.md|design_decisions\.md|mobile_form_factor_decision\.md|spec_amendments\.md|handoff\.md|mobile_v1\.md|UI/design_decisions\.md|UI/handoff\.md|UI/mobile_form_factor_decision\.md|UI/drafts/spec_amendments\.md|drafts/spec_amendments\.md|UI/backend_deltas\.md|backend_deltas\.md|backlog\.md|future_iterations\.md)$'
while IFS= read -r f; do
  in_decisions=0
  case "$f" in
    ./decisions/*|decisions/*) in_decisions=1 ;;
  esac
  while IFS= read -r ref; do
    target="${ref//\`/}"
    if echo "$target" | grep -qE "$allow_anywhere"; then
      continue
    fi
    if [ "$in_decisions" -eq 1 ] && echo "$target" | grep -qE "$allow_decisions_only"; then
      continue
    fi
    dir="$(dirname "$f")"
    if [ -e "${dir}/${target}" ] || [ -e "./${target}" ]; then
      continue
    fi
    # basename-anywhere fallback, EXCLUDING archive/ so retired-only
    # filenames fail here. ADRs that legitimately reference retired
    # names go through the decisions-only allow-list above.
    basename_match=$(find . -path ./archive -prune -o -name "$(basename "$target")" -print 2>/dev/null | head -1)
    if [ -z "$basename_match" ]; then
      fail "$f references missing \`$target\`"
      broken=$((broken + 1))
    fi
  done < <(grep -oE '`[A-Za-z0-9_./-]+\.(md|yaml|yml|css|html|svg|sh)`' "$f" 2>/dev/null | sort -u)
done < <(find . -path ./archive -prune -o \( -name '*.md' -o -name 'README.md' \) -print 2>/dev/null)
[ "$broken" -eq 0 ] && ok "no broken refs in non-archive docs"

# ---- 5. pre-implementation.md has no "Decided" section ----
section "pre-implementation.md hygiene"
if grep -qE '^## Decided\b' pre-implementation.md 2>/dev/null; then
  fail "pre-implementation.md has a '## Decided' section - closed items should leave the file (per PROCESS.md section 4.7)"
else
  ok "no 'Decided' section in pre-implementation.md"
fi

# ---- 6. Brand -> tokens lockstep (heuristic) ----
section "Brand -> tokens (heuristic)"
if [ -f UI/mockups/_shared/tokens.css ]; then
  tokens_mtime=$(stat -c %Y UI/mockups/_shared/tokens.css 2>/dev/null || stat -f %m UI/mockups/_shared/tokens.css)
  for lock in brand/tallykeep_*_v*_lock.html; do
    [ -e "$lock" ] || continue
    lock_mtime=$(stat -c %Y "$lock" 2>/dev/null || stat -f %m "$lock")
    if [ "$lock_mtime" -gt "$tokens_mtime" ]; then
      fail "$lock is newer than tokens.css - verify color/typography lockstep (brand/README.md Brand -> tokens propagation)"
    fi
  done
  ok "tokens.css timestamps not behind any locked brand artifact"
else
  fail "UI/mockups/_shared/tokens.css is missing"
fi

# ---- 7. Tail well-formedness (post-edit truncation detection) ----
# Catches the failure mode PROCESS.md 4.6 calls out: an agent edit
# silently truncates the end of a file mid-word or ends with a
# dangling header. Heuristic; false positives are easier to whitelist
# than truncations are to spot by eye.
section "Tail well-formedness"
tail_issues=0
while IFS= read -r f; do
  # last non-blank line, trimmed
  last_line=$(awk 'NF { line = $0 } END { print line }' "$f")
  # bash-portable trim
  last_trim="${last_line#"${last_line%%[![:space:]]*}"}"
  last_trim="${last_trim%"${last_trim##*[![:space:]]}"}"
  [ -z "$last_trim" ] && continue

  rel="${f#./}"

  # Signal 1: file ends on a markdown header (heading without body)
  if echo "$last_trim" | grep -qE '^#+[[:space:]]'; then
    fail "$rel ends with a header (no body after it): '$last_trim'"
    tail_issues=$((tail_issues + 1))
    continue
  fi

  # Signal 2: ends with a hyphenated word cut to 1-3 letters
  if echo "$last_trim" | grep -qE -- '-[A-Za-z]{1,3}$'; then
    fail "$rel last line ends mid-hyphenated-word: '$last_trim'"
    tail_issues=$((tail_issues + 1))
    continue
  fi

  # Signal 3: short line (<40 chars) ending in alpha with no terminator
  if [ "${#last_trim}" -lt 40 ] && echo "$last_trim" | grep -qE '[A-Za-z]$'; then
    fail "$rel last line looks truncated (short, no terminator): '$last_trim'"
    tail_issues=$((tail_issues + 1))
    continue
  fi
done < <(find . -path ./archive -prune -o -name '*.md' -print 2>/dev/null)
[ "$tail_issues" -eq 0 ] && ok "no truncated tails in non-archive docs"

# ---- 8. Edit sync (mtime against current iteration) ----
# Catches the buffering failure PROCESS.md section 4.6 + 4.8 describe:
# the Cowork file tool reports a successful Edit but the bytes don't
# reach the bash mount. Files listed in next_iteration.md as affected
# should have been touched recently; stale mtime = un-flushed edit.
section "Edit sync (mtime)"
if [ ! -f next_iteration.md ]; then
  ok "next_iteration.md missing; skipping sync check"
else
  ni_mtime=$(stat -c %Y next_iteration.md 2>/dev/null || stat -f %m next_iteration.md 2>/dev/null)
  if [ -z "$ni_mtime" ]; then
    ok "could not read next_iteration.md mtime; skipping"
  else
    # 7-day window in seconds
    threshold=$((ni_mtime - 604800))
    # Extract backtick-quoted file paths under "#### Affected canonical docs"
    # until the next "#### " or "## " or "---" or EOF.
    affected=$(awk '
      /^#### Affected canonical docs/ { in_block = 1; next }
      in_block && /^#### / { in_block = 0 }
      in_block && /^## / { in_block = 0 }
      in_block && /^---/ { in_block = 0 }
      in_block { print }
    ' next_iteration.md | grep -oE '`[A-Za-z0-9_./-]+\.(md|yaml|yml)`' | tr -d '`' | sort -u)
    sync_issues=0
    checked=0
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [ ! -f "$f" ] && continue
      # skip mockup files (covered by check #3)
      case "$f" in
        UI/mockups/*) continue ;;
      esac
      file_mtime=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
      [ -z "$file_mtime" ] && continue
      checked=$((checked + 1))
      if [ "$file_mtime" -lt "$threshold" ]; then
        days_old=$(( (ni_mtime - file_mtime) / 86400 ))
        fail "$f mtime is ${days_old} days older than next_iteration.md - possible un-flushed edit (per PROCESS.md 4.8, recover via bash heredoc)"
        sync_issues=$((sync_issues + 1))
      fi
    done <<<"$affected"
    [ $sync_issues -eq 0 ] && ok "${checked} canonical doc(s) checked, all in sync with current iteration"
  fi
fi

# ---- summary ----
echo
if [ "$fail_count" -eq 0 ]; then
  echo "PASS - sanity sweep clean."
  exit 0
else
  echo "FAIL - ${fail_count} check(s) failed. Fix in the same commit (PROCESS.md section 4.6)."
  exit 1
fi
