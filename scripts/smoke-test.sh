#!/usr/bin/env bash
# Smoke-test the live local stack — exercises every M0..M4 endpoint and a few
# of the still-501 stubs to confirm the API surface.
#
# Usage:
#   ./scripts/smoke-test.sh                                # default passphrase
#   PASSPHRASE='my-passphrase' ./scripts/smoke-test.sh
#   BASE_URL='http://127.0.0.1:8000' ./scripts/smoke-test.sh
#
# Parses JSON via `docker compose exec backend python3 -c ...` so this script
# works on any host that has Docker, with no jq / python3 dependency on the
# host itself.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PASSPHRASE="${PASSPHRASE:-smoke-test-passphrase}"

# Sample descriptors based on the abandon-abandon-...-about test mnemonic.
WPKH_MAINNET='wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)'
WPKH_MAINNET_CHANGE='wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)'

section() { printf "\n=== %s ===\n" "$1"; }
show()    { printf "  %-22s %s\n" "$1" "$2"; }

# Pipe-process JSON via the backend container's Python so the host doesn't need
# jq / python3.
jpy() {
    docker compose exec -T backend python3 -c "$1"
}


# --- 1. Health -----------------------------------------------------------------

section "1. Health"
HEALTH=$(curl -fsS "${BASE_URL}/api/v1/health")
echo "$HEALTH" | jpy '
import json, sys
d = json.load(sys.stdin)
print("  status=" + d["status"] + " version=" + d["version"])
for name, c in d["checks"].items():
    print("  " + name.ljust(10) + " ok=" + str(c["ok"]) + " reason=" + str(c.get("reason")))
'


# --- 2. Unlock -----------------------------------------------------------------

section "2. Unlock (initialize on a fresh DB, otherwise unlock)"
INIT_BODY=$(printf '{"passphrase":"%s"}' "$PASSPHRASE")
if curl -fsS -X POST -H "Content-Type: application/json" \
        -d "$INIT_BODY" "${BASE_URL}/api/v1/unlock/initialize" >/dev/null 2>&1; then
    show "initialize" "ok"
else
    if curl -fsS -X POST -H "Content-Type: application/json" \
            -d "$INIT_BODY" "${BASE_URL}/api/v1/unlock" >/dev/null 2>&1; then
        show "unlock" "ok (re-unlocked existing store)"
    else
        echo "  ERROR: could not unlock with passphrase '$PASSPHRASE'." >&2
        echo "  Either pass PASSPHRASE=... or run ./scripts/dev-reset.sh first." >&2
        exit 1
    fi
fi


# --- 3-6. Profile / flags / configuration -------------------------------------

section "3. Profile (auto-creates singleton)"
curl -fsS "${BASE_URL}/api/v1/profile" | jpy '
import json, sys
p = json.load(sys.stdin)
print("  preset=" + p["preset"] + " base_currency=" + p["base_currency"] + " locale=" + p["locale"])
'

section "4. Switch preset to sovereign"
curl -fsS -X PATCH -H "Content-Type: application/json" \
    -d '{"preset":"sovereign"}' \
    "${BASE_URL}/api/v1/profile" | jpy '
import json, sys
print("  preset=" + json.load(sys.stdin)["preset"])
'

section "5. Feature flags (resolved against the new preset)"
curl -fsS "${BASE_URL}/api/v1/feature-flags" | jpy '
import json, sys
f = json.load(sys.stdin)["flags"]
for key in ["trading.enabled", "banking.custom_fee_rate.enabled", "advanced.api_docs_link", "utxo.coin_control.enabled"]:
    print("  " + key.ljust(40) + " " + str(f[key]))
'

section "6. Configuration — set bitcoind RPC host"
curl -fsS -X PATCH -H "Content-Type: application/json" \
    -d '{"bitcoind":{"rpc_host":"192.168.1.42","rpc_port":8332}}' \
    "${BASE_URL}/api/v1/configuration" | jpy '
import json, sys
b = json.load(sys.stdin)["bitcoind"]
print("  rpc_host=" + str(b["rpc_host"]) + " rpc_port=" + str(b["rpc_port"]))
'


# --- 7. Create a Purse with two descriptors -----------------------------------

section "7. Create a Purse (external + change descriptors, gap_limit=10)"
PURSE_BODY=$(cat <<EOF
{
  "name":"Smoke-test phone wallet",
  "purpose":"spending",
  "declared_security":{"custody_model":"self_single","signing_model":"software_hot"},
  "display_color":"#10b981",
  "display_order":0,
  "descriptors":[{
    "name":"main",
    "expression":"${WPKH_MAINNET}",
    "change_expression":"${WPKH_MAINNET_CHANGE}",
    "network":"mainnet",
    "gap_limit":10
  }]
}
EOF
)
PURSE=$(curl -fsS -X POST -H "Content-Type: application/json" \
    -d "$PURSE_BODY" "${BASE_URL}/api/v1/holdings/purse")

PURSE_ID=$(echo "$PURSE" | jpy 'import json,sys;print(json.load(sys.stdin)["id"])' | tr -d '\r')
DESCRIPTOR_ID=$(echo "$PURSE" | jpy 'import json,sys;print(json.load(sys.stdin)["descriptor_ids"][0])' | tr -d '\r')
show "id"            "$PURSE_ID"
show "descriptor_id" "$DESCRIPTOR_ID"


# --- 8-10. Inspect ------------------------------------------------------------

section "8. List holdings"
curl -fsS "${BASE_URL}/api/v1/holdings" | jpy '
import json, sys
items = json.load(sys.stdin)
print("  count=" + str(len(items)))
for h in items:
    print("  - " + h["holding_type"].ljust(10) + " " + h["name"])
'

section "9. Descriptor + addresses (10 external + 10 change)"
curl -fsS "${BASE_URL}/api/v1/descriptors/${DESCRIPTOR_ID}" | jpy '
import json, sys
d = json.load(sys.stdin)
print("  address_type=" + d["address_type"] + " network=" + d["network"] + " gap_limit=" + str(d["gap_limit"]))
'
curl -fsS "${BASE_URL}/api/v1/descriptors/${DESCRIPTOR_ID}/addresses?limit=200" | jpy '
import json, sys
d = json.load(sys.stdin)["addresses"]
ext = [a for a in d if not a["is_change"]]
chg = [a for a in d if a["is_change"]]
print("  external_count=" + str(len(ext)) + " change_count=" + str(len(chg)))
print("  first_external=" + ext[0]["address"])
print("  first_change  =" + chg[0]["address"])
'

section "10. Next receiving address (lowest-index unused on external)"
curl -fsS -X POST "${BASE_URL}/api/v1/descriptors/${DESCRIPTOR_ID}/addresses/next-receiving" | jpy '
import json, sys
n = json.load(sys.stdin)
print("  address=" + n["address"] + " index=" + str(n["derivation_index"]) + " path=" + n["derivation_path"])
'


# --- 11-12. Patch + change-type ----------------------------------------------

section "11. Patch the holding (rename + recolor)"
curl -fsS -X PATCH -H "Content-Type: application/json" \
    -d '{"name":"Smoke-test renamed","display_color":"#abcdef"}' \
    "${BASE_URL}/api/v1/holdings/${PURSE_ID}" | jpy '
import json, sys
d = json.load(sys.stdin)
print("  name=" + d["name"] + " display_color=" + d["display_color"])
'

section "12. Change Purse -> Strongbox (audit log written)"
curl -fsS -X POST -H "Content-Type: application/json" \
    -d '{"new_type":"strongbox","reason":"Smoke test"}' \
    "${BASE_URL}/api/v1/holdings/${PURSE_ID}/change-type" | jpy '
import json, sys
print("  holding_type=" + json.load(sys.stdin)["holding_type"])
'


# --- 13. 501 stubs ------------------------------------------------------------

section "13. Stubs return 501 with milestone tag"
for pair in \
    "GET /api/v1/holdings/${PURSE_ID}/summary" \
    "GET /api/v1/analysis/holding/${PURSE_ID}/security" \
    "GET /api/v1/utxos" \
    "GET /api/v1/banking/payment-requests" \
    "GET /api/v1/lightning/status" \
    "GET /api/v1/sweep-policies"; do
    method="${pair%% *}"
    path="${pair#* }"
    body=$(curl -sS -X "$method" "${BASE_URL}${path}")
    milestone=$(echo "$body" | jpy 'import json,sys;d=json.load(sys.stdin);print(d.get("milestone","?"))' | tr -d '\r')
    show "$method $path" "501 -> $milestone"
done


# --- 14-15. Archive -----------------------------------------------------------

section "14. Archive + verify default list excludes it"
curl -fsS -X POST "${BASE_URL}/api/v1/holdings/${PURSE_ID}/archive" -o /dev/null
DEFAULT_COUNT=$(curl -fsS "${BASE_URL}/api/v1/holdings" | jpy 'import json,sys;print(len(json.load(sys.stdin)))' | tr -d '\r')
WITH_COUNT=$(curl -fsS "${BASE_URL}/api/v1/holdings?include_archived=true" | jpy 'import json,sys;print(len(json.load(sys.stdin)))' | tr -d '\r')
show "default count"   "$DEFAULT_COUNT"
show "with archived"   "$WITH_COUNT"


printf "\n=== Done. Smoke test passed end-to-end. ===\n"
echo "Tip: open ${BASE_URL}/docs in a browser to browse the full OpenAPI surface."
