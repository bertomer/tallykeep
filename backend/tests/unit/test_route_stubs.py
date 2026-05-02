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
    ("GET", "/api/v1/holdings", "M5"),
    ("GET", "/api/v1/holdings/summary/global", "M5"),
    ("GET", "/api/v1/holdings/{holding_id}", "M5"),
    ("PATCH", "/api/v1/holdings/{holding_id}", "M5"),
    ("POST", "/api/v1/holdings/{holding_id}/archive", "M5"),
    ("POST", "/api/v1/holdings/{holding_id}/change-type", "M5"),
    ("GET", "/api/v1/holdings/{holding_id}/summary", "M5"),
    ("POST", "/api/v1/holdings/account", "M4"),
    ("POST", "/api/v1/holdings/purse", "M4"),
    ("POST", "/api/v1/holdings/strongbox", "M4"),
    ("POST", "/api/v1/holdings/vault", "M4"),
    # --- Descriptors ---
    ("GET", "/api/v1/descriptors", "M4"),
    ("POST", "/api/v1/descriptors", "M4"),
    ("GET", "/api/v1/descriptors/{descriptor_id}", "M4"),
    ("PATCH", "/api/v1/descriptors/{descriptor_id}", "M4"),
    ("DELETE", "/api/v1/descriptors/{descriptor_id}", "M4"),
    ("POST", "/api/v1/descriptors/{descriptor_id}/rescan", "M5"),
    ("GET", "/api/v1/descriptors/{descriptor_id}/addresses", "M4"),
    (
        "POST",
        "/api/v1/descriptors/{descriptor_id}/addresses/next-receiving",
        "M4",
    ),
    ("GET", "/api/v1/descriptors/{descriptor_id}/utxos", "M5"),
    ("GET", "/api/v1/descriptors/{descriptor_id}/balance", "M5"),
    # --- Custodial providers ---
    ("GET", "/api/v1/custodial-providers/supported", "M8"),
    ("GET", "/api/v1/custodial-providers/{provider_id}", "M8"),
    ("PATCH", "/api/v1/custodial-providers/{provider_id}", "M8"),
    ("POST", "/api/v1/custodial-providers/{provider_id}/refresh", "M8"),
    ("GET", "/api/v1/custodial-providers/{provider_id}/balance", "M8"),
    (
        "GET",
        "/api/v1/custodial-providers/{provider_id}/verify-whitelist",
        "M8",
    ),
    # --- Addresses + UTXOs + Ledger entries ---
    ("PATCH", "/api/v1/addresses/{address_id}", "M5"),
    ("GET", "/api/v1/utxos", "M5"),
    ("POST", "/api/v1/utxos/{utxo_id}/freeze", "M5"),
    ("POST", "/api/v1/utxos/{utxo_id}/unfreeze", "M5"),
    ("GET", "/api/v1/utxos/{utxo_id}/hygiene", "M5"),
    ("GET", "/api/v1/ledger-entries", "M5"),
    ("GET", "/api/v1/ledger-entries/pending-categorization", "M5"),
    ("GET", "/api/v1/ledger-entries/{entry_id}", "M5"),
    ("PATCH", "/api/v1/ledger-entries/{entry_id}", "M5"),
    # --- Banking ---
    ("GET", "/api/v1/banking/payment-requests", "M6"),
    ("POST", "/api/v1/banking/payment-requests", "M6"),
    ("GET", "/api/v1/banking/payment-requests/{request_id}", "M6"),
    ("GET", "/api/v1/banking/payment-requests/{request_id}/psbt", "M6"),
    ("GET", "/api/v1/banking/payment-requests/{request_id}/psbt.qr", "M6"),
    (
        "POST",
        "/api/v1/banking/payment-requests/{request_id}/submit-signed",
        "M6",
    ),
    ("POST", "/api/v1/banking/payment-requests/{request_id}/broadcast", "M6"),
    ("POST", "/api/v1/banking/payment-requests/{request_id}/cancel", "M6"),
    ("POST", "/api/v1/banking/fee-estimate", "M6"),
    ("GET", "/api/v1/banking/invoices", "M6"),
    ("POST", "/api/v1/banking/invoices", "M6"),
    ("GET", "/api/v1/banking/invoices/{invoice_id}", "M6"),
    ("GET", "/api/v1/banking/invoices/{invoice_id}/qr", "M6"),
    ("POST", "/api/v1/banking/invoices/{invoice_id}/cancel", "M6"),
    # --- Trading: sweep policies ---
    ("GET", "/api/v1/sweep-policies", "M8"),
    ("POST", "/api/v1/sweep-policies", "M8"),
    ("POST", "/api/v1/sweep-policies/pause-all", "M8"),
    ("POST", "/api/v1/sweep-policies/resume-all", "M8"),
    ("GET", "/api/v1/sweep-policies/{policy_id}", "M8"),
    ("PATCH", "/api/v1/sweep-policies/{policy_id}", "M8"),
    ("DELETE", "/api/v1/sweep-policies/{policy_id}", "M8"),
    (
        "POST",
        "/api/v1/sweep-policies/{policy_id}/acknowledge-warnings",
        "M8",
    ),
    ("POST", "/api/v1/sweep-policies/{policy_id}/enable", "M8"),
    ("POST", "/api/v1/sweep-policies/{policy_id}/disable", "M8"),
    ("POST", "/api/v1/sweep-policies/{policy_id}/execute-now", "M8"),
    ("GET", "/api/v1/sweep-policies/{policy_id}/executions", "M8"),
    ("GET", "/api/v1/sweep-executions", "M8"),
    ("GET", "/api/v1/sweep-executions/{execution_id}", "M8"),
    ("POST", "/api/v1/sweep-executions/{execution_id}/confirm", "M8"),
    # --- Analysis + Jobs + Export ---
    ("GET", "/api/v1/analysis/holding/{holding_id}/security", "M5"),
    ("GET", "/api/v1/analysis/holding/{holding_id}/blueprint", "M5"),
    ("GET", "/api/v1/analysis/utxo/{utxo_id}", "M5"),
    ("POST", "/api/v1/analysis/recompute", "M5"),
    ("GET", "/api/v1/jobs", "M5"),
    ("GET", "/api/v1/jobs/{job_id}", "M5"),
    ("DELETE", "/api/v1/jobs/{job_id}", "M5"),
    ("GET", "/api/v1/export/configuration", "M14"),
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
