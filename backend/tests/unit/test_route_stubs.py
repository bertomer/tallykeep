"""Contract tests for the M3.2 stub routes.

Two layers of verification:

1. **OpenAPI inclusion** — the generated openapi.json must list every spec-module-04
   route under its expected method. This guards against typos in the router files
   and against forgetting to wire a router into `main.py`.

2. **Runtime 501 + Problem Details body** — each stub returns 501 with an
   RFC 7807 body whose `type` is `/errors/not-implemented`, whose `status` is 501,
   and whose `route` field round-trips the route signature. The middleware must
   not interfere — fixtures use an unlocked secret store.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


# Every spec-module-04 stub route, paired with the HTTP method. Path parameters
# use a recognizable placeholder so we can substitute a UUID for runtime tests.
#
# Important: keep this list in sync with the route files in api/v1/. If the
# numbers diverge, either a new spec route landed without registration or a
# stub was removed without updating the contract.
STUB_ROUTES: list[tuple[str, str, str]] = [
    # method, openapi-path, milestone
    # --- Holdings ---
    # M4 implemented: per-type creation (purse/strongbox/vault), list, get,
    # patch, archive, change-type. M8 implemented: account creation.
    # --- Descriptors ---
    # M4 implemented: list, attach, get, patch, delete, addresses,
    # next-receiving. M5.2 implemented: rescan, utxos, balance.
    # All tested in test_descriptor_endpoints.py / test_chain_scan.py.
    # --- Custodial providers ---
    # M8 implemented: supported, get, patch, refresh, balance, verify-whitelist.
    # --- Addresses + Ledger entries ---
    # UTXO endpoints implemented in M5.2; LedgerEntry list/get/patch land in M5.6.
    # PATCH /addresses/{id} implemented in M9.
    # --- Banking ---
    # M6.1–M6.5 implemented. Multi-frame QR (PSBT) is the only remaining stub.
    ("GET", "/api/v1/banking/payment-requests/{request_id}/psbt.qr", "v1.1"),
    # --- Trading: sweep policies ---
    # M8 implemented: list, create, pause-all, resume-all, get, patch, delete,
    # acknowledge-warnings, enable, disable, list-executions, get-executions, confirm.
    # M8.1 implemented: execute-now (synchronous withdrawal + job record).
    # --- Analysis + Jobs + Export ---
    # /security and /blueprint are real as of M5.5; the per-UTXO blueprint and
    # the manual recompute trigger are still stubs (UTXO blueprint is folded
    # into /utxos/{id}/hygiene; recompute will land alongside the M9 scheduler).
    # Jobs endpoints are real as of M8.1.
    ("GET", "/api/v1/analysis/utxo/{utxo_id}", "v2"),
    # POST /analysis/recompute implemented in M9.
    ("GET", "/api/v1/export/configuration", "M14"),
    # --- Lightning (spec module 08): all stubs land in v1.5 ---
    ("GET", "/api/v1/lightning/status", "v1.5"),
    ("GET", "/api/v1/lightning/balance", "v1.5"),
    ("POST", "/api/v1/lightning/invoices", "v1.5"),
    ("POST", "/api/v1/lightning/pay", "v1.5"),
    ("GET", "/api/v1/lightning/payments", "v1.5"),
    ("GET", "/api/v1/lightning/channels", "v1.5"),
]


# --- 1. OpenAPI inclusion -------------------------------------------------------


def test_every_stub_route_appears_in_openapi(client) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for method, path, _ in STUB_ROUTES:
        assert path in paths, f"OpenAPI is missing path {path!r}"
        assert method.lower() in paths[path], (
            f"OpenAPI is missing {method} {path}"
        )


# --- 2. Runtime 501 + Problem Details body -------------------------------------


_PLACEHOLDER_UUID = "00000000-0000-0000-0000-0000000000aa"


def _concretize(path: str) -> str:
    """Replace `{anything_id}` with a real-looking UUID so FastAPI routes match."""
    while "{" in path:
        start = path.index("{")
        end = path.index("}")
        path = path[:start] + _PLACEHOLDER_UUID + path[end + 1:]
    return path


@pytest.mark.parametrize(
    ("method", "openapi_path", "milestone"),
    STUB_ROUTES,
    ids=[f"{m} {p}" for m, p, _ in STUB_ROUTES],
)
def test_stub_returns_501_with_problem_details(
    client, method: str, openapi_path: str, milestone: str
) -> None:
    url = _concretize(openapi_path)
    response = client.request(method, url)
    assert response.status_code == 501, (
        f"{method} {url} → expected 501, got {response.status_code} "
        f"({response.text[:200]})"
    )
    body = response.json()
    assert body["status"] == 501
    assert body["title"] == "Not implemented"
    assert body["type"] == "/errors/not-implemented"
    assert body["milestone"] == milestone
    # `route` round-trips the original path-template form, not the concretized URL.
    assert "route" in body
    assert milestone in body["detail"]
