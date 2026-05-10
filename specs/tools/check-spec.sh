#!/usr/bin/env bash
# check-spec.sh — iteration-done sanity sweep for the specs/ tree
# (per PROCESS.md §2.9).
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

# Note: not using `set -u` — the file-ref loop reads from a process
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
  fail "api/openapi.yaml is missing — regenerate from the running backend (see api/README.md)"
fi

# ---- 2. ADR index in decisions/README.md matches files ----
section "ADR index ↔ files"
adr_files=$(find decisions -maxdepth 1 -name '[0-9][0-9][0-9][0-9]-*.md' -printf '%f\n' | sort)
# Match any markdown link whose target ends in NNNN-*.md, regardless
# of label characters (em dash etc.). Tolerates locale variance.
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
section "Mockup index ↔ files"
if [ -f UI/mockups/index.html ]; then
  mockup_files=$(find UI/mockups -maxdepth 1 -name 'mobile_*.html' -printf '%f\n' | sort)
  # Strip JS line comments (`//`) and block-comment ranges before
  # searching, so commented-out example entries don't count as listed.
  listed_mockups=$(awk '
      BEGIN { in_block = 0 }
      {
        line = $0
        # remove block comments
        while (in_block && (idx = index(line, "*/"))) {
          line = substr(line, idx + 2); in_block = 0
        }
        if (in_block) next
        while ((idx = index(line, "/*"))) {
          end = index(substr(line, idx), "*/")
          if (end) { line = substr(line, 1, idx - 1) substr(line, idx + end + 1) }
          else     { line = substr(line, 1, idx - 1); in_block = 1; break }
        }
        # remove line comments
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
# allow-list: documented placeholder / illustrative names that
# intentionally don't resolve to a file (naming-convention examples,
# template placeholders, retired-file references kept for historical
# context in ADRs).
allow_list='^(\.\.\._v[0-9]+_lock\.html|\.\.\._fiat_(off|on)\.html|colors\.md|typography\.md|tallykeep_<.+>_v<N>_<status>\.(html|md)|<artifact>_v<N>_<status>\.(html|md)|<voice-piece>_v<N>_<status>\.md|mobile_<flow>_<state>\.html|UI/backend_deltas\.md|backend_deltas\.md|backlog\.md|NNNN-title\.md|NNNN-short-title\.md|09_profiles_and_flags\.md|11_ux_flows\.md|12_roadmap\.md|13_open_questions\.md|14_context_handoff\.md|design_decisions\.md|mobile_form_factor_decision\.md|spec_amendments\.md|handoff\.md|mobile_v1\.md|UI/design_decisions\.md|UI/handoff\.md|UI/mobile_form_factor_decision\.md|UI/drafts/spec_amendments\.md|specs/.+|drafts/spec_amendments\.md|04_api_surface\.md)$'
while IFS= read -r f; do
  while IFS= read -r ref; do
    # strip backticks
    target="${ref//\`/}"
    # already resolved by allow-list?
    if echo "$target" | grep -qE "$allow_list"; then
      continue
    fi
    # try relative to file dir, then to specs root
    dir="$(dirname "$f")"
    if [ -e "${dir}/${target}" ] || [ -e "./${target}" ]; then
      continue
    fi
    # try basename anywhere INCLUDING archive — historical refs in
    # ADRs and changelogs are legitimate as long as the file exists
    # somewhere.
    basename_match=$(find . -name "$(basename "$target")" -print 2>/dev/null | head -1)
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
  fail "pre-implementation.md has a '## Decided' section — closed items should leave the file (per PROCESS.md §2.6)"
else
  ok "no 'Decided' section in pre-implementation.md"
fi

# ---- 6. Brand → tokens lockstep (heuristic) ----
section "Brand → tokens (heuristic)"
# Mechanical color extraction from the lock-doc HTML is non-trivial
# without a parser; instead we surface the timestamps so a human
# can spot mismatch fast.
if [ -f UI/mockups/_shared/tokens.css ]; then
  tokens_mtime=$(stat -c %Y UI/mockups/_shared/tokens.css 2>/dev/null || stat -f %m UI/mockups/_shared/tokens.css)
  for lock in brand/tallykeep_*_v*_lock.html; do
    [ -e "$lock" ] || continue
    lock_mtime=$(stat -c %Y "$lock" 2>/dev/null || stat -f %m "$lock")
    if [ "$lock_mtime" -gt "$tokens_mtime" ]; then
      fail "$lock is newer than tokens.css — verify color/typography lockstep (PROCESS.md §2.4)"
    fi
  done
  ok "tokens.css timestamps not behind any locked brand artifact"
else
  fail "UI/mockups/_shared/tokens.css is missing"
fi

# ---- summary ----
echo
if [ "$fail_count" -eq 0 ]; then
  echo "PASS — sanity sweep clean."
  exit 0
else
  echo "FAIL — ${fail_count} check(s) failed. Fix in the same commit (PROCESS.md §2.9)."
  exit 1
fi
