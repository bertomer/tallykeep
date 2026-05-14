"""Integration tests for M9 endpoints: address labelling and analysis recompute."""

from __future__ import annotations

import pytest

from tallykeep.infrastructure.job_queue import InMemoryJobQueue


pytestmark = pytest.mark.integration


WPKH = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
)


def _purse_body(name: str = "wallet") -> dict:
    return {
        "name": name,
        "purpose": "spending",
        "purse_mode": "watch_only",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": WPKH,
                "change_expression": None,
                "network": "mainnet",
                "gap_limit": 3,
            }
        ],
    }


@pytest.fixture()
def app_with_queue(app_with_db):  # type: ignore[no-untyped-def]
    client, factory = app_with_db
    queue = InMemoryJobQueue()
    client.app.state.job_queue = queue
    return client, factory, queue


# ---------------------------------------------------------------------------
# PATCH /addresses/{id}
# ---------------------------------------------------------------------------


class TestAddressLabel:
    def test_patch_sets_label(self, app_with_db) -> None:
        client, factory = app_with_db
        # Create a purse (generates gap-limit addresses)
        holding = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
        desc_id = holding["descriptor_ids"][0]

        # Fetch an address for this descriptor
        addr_resp = client.get(f"/api/v1/descriptors/{desc_id}/addresses")
        assert addr_resp.status_code == 200
        addresses = addr_resp.json()["addresses"]
        assert len(addresses) > 0
        addr_id = addresses[0]["id"]

        # Patch the label
        resp = client.patch(
            f"/api/v1/addresses/{addr_id}", json={"label": "my label"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == addr_id
        assert body["label"] == "my label"
        assert "address" in body

    def test_patch_clears_label(self, app_with_db) -> None:
        client, factory = app_with_db
        holding = client.post("/api/v1/holdings/purse", json=_purse_body("w2")).json()
        desc_id = holding["descriptor_ids"][0]
        addresses = client.get(f"/api/v1/descriptors/{desc_id}/addresses").json()["addresses"]
        addr_id = addresses[0]["id"]

        # Set then clear
        client.patch(f"/api/v1/addresses/{addr_id}", json={"label": "temp"})
        resp = client.patch(f"/api/v1/addresses/{addr_id}", json={"label": None})
        assert resp.status_code == 200
        assert resp.json()["label"] is None

    def test_patch_unknown_address_returns_404(self, app_with_db) -> None:
        client, _ = app_with_db
        from uuid import uuid4
        resp = client.patch(
            f"/api/v1/addresses/{uuid4()}", json={"label": "x"}
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /analysis/recompute
# ---------------------------------------------------------------------------


class TestAnalysisRecompute:
    def test_recompute_all_returns_202(self, app_with_queue) -> None:
        client, factory, queue = app_with_queue
        resp = client.post("/api/v1/analysis/recompute", json={})
        assert resp.status_code == 202
        body = resp.json()
        assert "job_id" in body
        assert "holding_count" in body

    def test_recompute_counts_active_holdings(self, app_with_queue) -> None:
        client, factory, queue = app_with_queue
        # Seed two holdings
        client.post("/api/v1/holdings/purse", json=_purse_body("a"))
        WPKH2 = WPKH.replace("/0/*", "/1/*")
        body2 = _purse_body("b")
        body2["descriptors"][0]["expression"] = WPKH2
        client.post("/api/v1/holdings/purse", json=body2)

        resp = client.post("/api/v1/analysis/recompute", json={})
        assert resp.status_code == 202
        assert resp.json()["holding_count"] == 2

    def test_recompute_specific_holding(self, app_with_queue) -> None:
        client, factory, queue = app_with_queue
        holding = client.post("/api/v1/holdings/purse", json=_purse_body("solo")).json()
        resp = client.post(
            "/api/v1/analysis/recompute", json={"holding_id": holding["id"]}
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["holding_count"] == 1

    def test_recompute_unknown_holding_returns_404(self, app_with_queue) -> None:
        from uuid import uuid4
        client, factory, queue = app_with_queue
        resp = client.post(
            "/api/v1/analysis/recompute", json={"holding_id": str(uuid4())}
        )
        assert resp.status_code == 404

    def test_recompute_enqueues_job(self, app_with_queue) -> None:
        from uuid import UUID
        client, factory, queue = app_with_queue
        resp = client.post("/api/v1/analysis/recompute", json={})
        assert resp.status_code == 202
        job_id = UUID(resp.json()["job_id"])

        # Job should appear in the queue
        info = queue.get(job_id)
        assert info is not None
        assert info.job_type == "analysis_recompute"
