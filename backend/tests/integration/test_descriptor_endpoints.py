"""Integration tests for /api/v1/descriptors."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


WPKH_MAINNET = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
)
WPKH_MAINNET_CHANGE = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)"
)


def _purse_body(
    *,
    expression: str = WPKH_MAINNET,
    change_expression: str | None = None,
    gap_limit: int = 5,
) -> dict:
    return {
        "name": "main wallet",
        "purpose": "spending",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": expression,
                "change_expression": change_expression,
                "network": "mainnet",
                "gap_limit": gap_limit,
            }
        ],
    }


# --- list / get ---------------------------------------------------------------


def test_list_descriptors_filters_by_holding(app_with_db) -> None:
    client, _ = app_with_db
    h1 = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    # Second holding with a different (change-branch) descriptor expression so
    # uq_descriptor_expression doesn't trip.
    body2 = _purse_body(expression=WPKH_MAINNET_CHANGE)
    body2["name"] = "second wallet"
    h2 = client.post("/api/v1/holdings/purse", json=body2).json()

    all_desc = client.get("/api/v1/descriptors").json()
    assert len(all_desc) == 2

    just_h1 = client.get(
        "/api/v1/descriptors", params={"holding_id": h1["id"]}
    ).json()
    assert len(just_h1) == 1
    assert just_h1[0]["holding_id"] == h1["id"]


def test_get_descriptor_returns_full_payload(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = h["descriptor_ids"][0]

    response = client.get(f"/api/v1/descriptors/{descriptor_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == descriptor_id
    assert body["holding_id"] == h["id"]
    assert body["network"] == "mainnet"
    assert body["address_type"] == "native_segwit"
    assert body["is_watch_only"] is True


def test_get_unknown_descriptor_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    response = client.get(
        "/api/v1/descriptors/00000000-0000-0000-0000-0000000000ff"
    )
    assert response.status_code == 404


# --- attach ------------------------------------------------------------------


def test_attach_descriptor_to_existing_purse(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post("/api/v1/holdings/purse", json=_purse_body()).json()

    # Attach a second descriptor (the change branch) to the same holding.
    response = client.post(
        "/api/v1/descriptors",
        json={
            "holding_id": h["id"],
            "descriptor": {
                "name": "secondary",
                "expression": WPKH_MAINNET_CHANGE,
                "change_expression": None,
                "network": "mainnet",
                "gap_limit": 3,
            },
        },
    )
    assert response.status_code == 201, response.text

    # Holding now has two descriptors.
    descriptors = client.get(
        "/api/v1/descriptors", params={"holding_id": h["id"]}
    ).json()
    assert len(descriptors) == 2


def test_attach_to_unknown_holding_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/descriptors",
        json={
            "holding_id": "00000000-0000-0000-0000-0000000000ff",
            "descriptor": {
                "name": "x",
                "expression": WPKH_MAINNET,
                "change_expression": None,
                "network": "mainnet",
                "gap_limit": 5,
            },
        },
    )
    assert response.status_code == 404


def test_attach_duplicate_expression_returns_409(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    # Same expression — uq_descriptor_expression should trip.
    response = client.post(
        "/api/v1/descriptors",
        json={
            "holding_id": h["id"],
            "descriptor": {
                "name": "duplicate",
                "expression": WPKH_MAINNET,
                "change_expression": None,
                "network": "mainnet",
                "gap_limit": 5,
            },
        },
    )
    assert response.status_code == 409


# --- patch / delete ----------------------------------------------------------


def test_patch_descriptor_renames_and_updates_gap_limit(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = h["descriptor_ids"][0]

    response = client.patch(
        f"/api/v1/descriptors/{descriptor_id}",
        json={"name": "renamed", "gap_limit": 50},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "renamed"
    assert body["gap_limit"] == 50


def test_patch_empty_body_rejected(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = h["descriptor_ids"][0]
    response = client.patch(
        f"/api/v1/descriptors/{descriptor_id}", json={}
    )
    assert response.status_code == 422


def test_delete_descriptor_with_addresses_returns_409(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = h["descriptor_ids"][0]

    response = client.delete(f"/api/v1/descriptors/{descriptor_id}")
    assert response.status_code == 409
    assert "addresses" in response.text.lower()


# --- addresses ---------------------------------------------------------------


def test_list_addresses_returns_pre_derived_set(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=10)
    ).json()
    descriptor_id = h["descriptor_ids"][0]

    response = client.get(f"/api/v1/descriptors/{descriptor_id}/addresses")
    assert response.status_code == 200
    addresses = response.json()["addresses"]
    assert len(addresses) == 10
    # Every address starts with bc1q (native segwit on mainnet) and is
    # is_change=False since this purse has no change descriptor.
    for a in addresses:
        assert a["address"].startswith("bc1q")
        assert a["is_change"] is False
    # derivation_index is monotonically increasing.
    indices = [a["derivation_index"] for a in addresses]
    assert indices == sorted(indices)


def test_list_addresses_filtered_by_is_change(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post(
        "/api/v1/holdings/purse",
        json=_purse_body(
            change_expression=WPKH_MAINNET_CHANGE, gap_limit=3
        ),
    ).json()
    descriptor_id = h["descriptor_ids"][0]

    external = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses",
        params={"is_change": False},
    ).json()["addresses"]
    change = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses",
        params={"is_change": True},
    ).json()["addresses"]
    assert len(external) == 3
    assert len(change) == 3
    # Different addresses on each branch.
    assert {a["address"] for a in external} & {a["address"] for a in change} == set()


def test_next_receiving_returns_first_unused(app_with_db) -> None:
    client, _ = app_with_db
    h = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=5)
    ).json()
    descriptor_id = h["descriptor_ids"][0]

    response = client.post(
        f"/api/v1/descriptors/{descriptor_id}/addresses/next-receiving"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["derivation_index"] == 0
    assert body["address"].startswith("bc1q")


def test_next_receiving_unknown_descriptor_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/descriptors/00000000-0000-0000-0000-0000000000ff/addresses/next-receiving"
    )
    assert response.status_code == 404
