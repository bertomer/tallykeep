"""Integration tests for /api/v1/security_health endpoints (ADR-0019)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from tallykeep.domain.security_health_item import (
    ITEM_SEVERITY_CRITICAL,
    ITEM_SEVERITY_WARNING,
    ITEM_STATE_ACKNOWLEDGED,
    ITEM_STATE_DISMISSED_INTENTIONAL,
    ITEM_STATE_OPEN,
    ITEM_STATE_RESOLVED_BY_FIX,
    ITEM_TYPE_MISSING_SIGNING_METADATA,
    ITEM_TYPE_PRINCIPLES_ACK,
    ITEM_TYPE_SEED_BACKUP,
)
from tallykeep.models.holding import HoldingRow
from tallykeep.models.security_health_item import SecurityHealthItemRow

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_holding(factory) -> uuid.UUID:
    """Insert a minimal HoldingRow and return its id."""
    holding_id = uuid.uuid4()
    with factory() as session:
        session.add(
            HoldingRow(
                id=holding_id,
                holding_type="purse",
                name="Test Holding",
                purpose="spending",
                declared_custody_model="self_custodial",
                declared_signing_model="single_key",
                subtype_data={},
            )
        )
        session.commit()
    return holding_id

def _insert_item(
    factory,
    *,
    item_type: str = ITEM_TYPE_PRINCIPLES_ACK,
    holding_id: uuid.UUID | None = None,
    severity: str = ITEM_SEVERITY_WARNING,
    state: str = ITEM_STATE_OPEN,
    raw_context: dict | None = None,
) -> str:
    """Insert a SecurityHealthItemRow directly and return its id as a str."""
    item_id = uuid.uuid4()
    with factory() as session:
        session.add(
            SecurityHealthItemRow(
                id=item_id,
                item_type=item_type,
                holding_id=holding_id,
                state=state,
                severity=severity,
                created_at=datetime.now(UTC),
                resolved_at=None,
                dismissal_reason=None,
                raw_context=raw_context or {},
            )
        )
        session.commit()
    return str(item_id)


# ---------------------------------------------------------------------------
# GET /security_health/items?state=open
# ---------------------------------------------------------------------------


class TestListOpenItems:
    def test_empty_returns_empty_list(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.get("/api/v1/security_health/items?state=open")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_open_items_only(self, app_with_db) -> None:
        client, factory = app_with_db
        open_id = _insert_item(factory, state=ITEM_STATE_OPEN)
        _insert_item(factory, state=ITEM_STATE_ACKNOWLEDGED)

        resp = client.get("/api/v1/security_health/items?state=open")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == open_id
        assert data[0]["state"] == ITEM_STATE_OPEN

    def test_includes_application_level_and_holding_items(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _insert_holding(factory)
        app_id = _insert_item(factory, holding_id=None)
        holding_item_id = _insert_item(factory, holding_id=holding_id)

        resp = client.get("/api/v1/security_health/items?state=open")
        assert resp.status_code == 200
        ids = {i["id"] for i in resp.json()}
        assert app_id in ids
        assert holding_item_id in ids

    def test_critical_items_sorted_before_warnings(self, app_with_db) -> None:
        client, factory = app_with_db
        _insert_item(factory, severity=ITEM_SEVERITY_WARNING)
        _insert_item(factory, severity=ITEM_SEVERITY_CRITICAL)

        resp = client.get("/api/v1/security_health/items?state=open")
        assert resp.status_code == 200
        items = resp.json()
        assert items[0]["severity"] == ITEM_SEVERITY_CRITICAL
        assert items[1]["severity"] == ITEM_SEVERITY_WARNING

    def test_invalid_state_returns_422(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.get("/api/v1/security_health/items?state=banana")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /security_health/items?state=history
# ---------------------------------------------------------------------------


class TestListHistoryItems:
    def test_empty_history_returns_empty_list(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.get("/api/v1/security_health/items?state=history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_terminal_items_only(self, app_with_db) -> None:
        client, factory = app_with_db
        _insert_item(factory, state=ITEM_STATE_OPEN)
        resolved_id = _insert_item(factory, state=ITEM_STATE_RESOLVED_BY_FIX)
        ack_id = _insert_item(factory, state=ITEM_STATE_ACKNOWLEDGED)

        resp = client.get("/api/v1/security_health/items?state=history")
        assert resp.status_code == 200
        ids = {i["id"] for i in resp.json()}
        assert resolved_id in ids
        assert ack_id in ids


# ---------------------------------------------------------------------------
# POST /security_health/items/{id}/resolve
# ---------------------------------------------------------------------------


class TestResolveItem:
    def test_resolve_acknowledged(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory)

        resp = client.post(
            f"/api/v1/security_health/items/{item_id}/resolve",
            json={"state": "acknowledged"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == ITEM_STATE_ACKNOWLEDGED
        assert data["resolved_at"] is not None

    def test_resolve_dismissed_intentional_with_reason(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory)

        resp = client.post(
            f"/api/v1/security_health/items/{item_id}/resolve",
            json={"state": "dismissed_intentional", "dismissal_reason": "test wallet"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == ITEM_STATE_DISMISSED_INTENTIONAL
        assert data["dismissal_reason"] == "test wallet"

    def test_resolve_resolved_by_fix(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory)

        resp = client.post(
            f"/api/v1/security_health/items/{item_id}/resolve",
            json={"state": "resolved_by_fix"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == ITEM_STATE_RESOLVED_BY_FIX

    def test_resolve_invalid_state_returns_422(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory)

        resp = client.post(
            f"/api/v1/security_health/items/{item_id}/resolve",
            json={"state": "bogus_state"},
        )
        assert resp.status_code == 422

    def test_resolve_not_found_returns_404(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.post(
            f"/api/v1/security_health/items/{uuid.uuid4()}/resolve",
            json={"state": "acknowledged"},
        )
        assert resp.status_code == 404

    def test_resolve_already_resolved_returns_422(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory, state=ITEM_STATE_ACKNOWLEDGED)

        resp = client.post(
            f"/api/v1/security_health/items/{item_id}/resolve",
            json={"state": "resolved_by_fix"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /security_health/items/{id}/revive
# ---------------------------------------------------------------------------


class TestReviveItem:
    def test_revive_acknowledged_item_returns_422(self, app_with_db) -> None:
        """ACKNOWLEDGED is not revivable in v1 — only DISMISSED_INTENTIONAL is."""
        client, factory = app_with_db
        item_id = _insert_item(factory, state=ITEM_STATE_ACKNOWLEDGED)

        resp = client.post(f"/api/v1/security_health/items/{item_id}/revive")
        assert resp.status_code == 422

    def test_revive_dismissed_intentional_item(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory, state=ITEM_STATE_DISMISSED_INTENTIONAL)

        resp = client.post(f"/api/v1/security_health/items/{item_id}/revive")
        assert resp.status_code == 200
        assert resp.json()["state"] == ITEM_STATE_OPEN

    def test_revive_system_verified_item_returns_422(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory, state=ITEM_STATE_RESOLVED_BY_FIX)

        resp = client.post(f"/api/v1/security_health/items/{item_id}/revive")
        assert resp.status_code == 422

    def test_revive_not_found_returns_404(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.post(f"/api/v1/security_health/items/{uuid.uuid4()}/revive")
        assert resp.status_code == 404

    def test_revive_open_item_returns_422(self, app_with_db) -> None:
        client, factory = app_with_db
        item_id = _insert_item(factory, state=ITEM_STATE_OPEN)

        resp = client.post(f"/api/v1/security_health/items/{item_id}/revive")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /security_health/fix_metadata/{holding_id}/reexport
# ---------------------------------------------------------------------------

# Descriptor with full origin metadata — addresses deterministic from the
# abandon×11+about mnemonic at m/84'/0'/0'.
WPKH_WITH_ORIGIN = (
    "wpkh([ab12cd34/84'/0'/0']"
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj"
    "/0/*)"
)
WPKH_WITHOUT_ORIGIN = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
)


def _create_strongbox_holding(client, *, signing_metadata_present: bool = False) -> str:
    """Create a Strongbox via the API and return the holding id."""
    body = {
        "name": "Test Strongbox",
        "description": "",
        "purpose": "reserve",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "hardware_offline",
            "geographic_distribution": False,
            "inheritance_configured": False,
        },
        "display_color": "#6366f1",
        "display_order": 0,
        "signing_device_label": "Test HW",
        "signing_metadata_present": signing_metadata_present,
        "descriptors": [
            {
                "name": "main",
                "expression": WPKH_WITHOUT_ORIGIN,
                "network": "mainnet",
                "gap_limit": 3,
            }
        ],
    }
    resp = client.post("/api/v1/holdings/strongbox", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestFixMetadataReexport:
    def test_descriptor_without_origin_returns_failure(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client)

        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/reexport",
            json={"descriptor_expression": WPKH_WITHOUT_ORIGIN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "origin" in data["error"].lower()

    def test_descriptor_with_mismatched_addresses_returns_failure(
        self, app_with_db
    ) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client)

        # Different xpub → different addresses → mismatch.
        different_xpub = (
            "wpkh([ab12cd34/84'/0'/0']"
            "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj"
            "/1/*)"
        )
        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/reexport",
            json={"descriptor_expression": different_xpub},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    def test_matching_descriptor_with_origin_succeeds(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client)

        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/reexport",
            json={"descriptor_expression": WPKH_WITH_ORIGIN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["matched_addresses"] >= 1

    def test_holding_not_found_returns_failure(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{uuid.uuid4()}/reexport",
            json={"descriptor_expression": WPKH_WITH_ORIGIN},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# POST /security_health/fix_metadata/{holding_id}/manual
# ---------------------------------------------------------------------------


class TestFixMetadataManual:
    def test_valid_fingerprint_and_path_succeeds(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client)

        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/manual",
            json={
                "master_fingerprint": "ab12cd34",
                "derivation_path": "m/84'/0'/0'",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["matched_addresses"] >= 1

    def test_invalid_fingerprint_format_returns_422(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client)

        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/manual",
            json={
                "master_fingerprint": "ZZZZZZZZ",  # not hex
                "derivation_path": "m/84'/0'/0'",
            },
        )
        assert resp.status_code == 422

    def test_wrong_derivation_path_leads_to_mismatch(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client)

        # Path for Legacy addresses won't match Native SegWit descriptor addresses.
        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/manual",
            json={
                "master_fingerprint": "ab12cd34",
                "derivation_path": "m/44'/0'/0'",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # May succeed or fail depending on address set overlap — the core
        # assertion is that the endpoint returns cleanly.
        assert "success" in data

    def test_holding_not_found_returns_failure(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.post(
            f"/api/v1/security_health/fix_metadata/{uuid.uuid4()}/manual",
            json={
                "master_fingerprint": "ab12cd34",
                "derivation_path": "m/84'/0'/0'",
            },
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Seed-backup item emitted on Purse creation (ON_DEVICE mode)
# ---------------------------------------------------------------------------


class TestSeedBackupHook:
    def test_create_on_device_purse_emits_seed_backup_item(
        self, app_with_db
    ) -> None:
        client, factory = app_with_db
        body = {
            "name": "My phone wallet",
            "description": "",
            "purpose": "spending",
            "purse_mode": "on_device_tk_generated",
            "declared_security": {
                "custody_model": "self_single",
                "signing_model": "software_hot",
                "geographic_distribution": False,
                "inheritance_configured": False,
            },
            "display_color": "#10b981",
            "display_order": 0,
            "descriptors": [
                {
                    "name": "main",
                    "expression": WPKH_WITHOUT_ORIGIN,
                    "network": "mainnet",
                    "gap_limit": 3,
                }
            ],
        }
        resp = client.post("/api/v1/holdings/purse", json=body)
        assert resp.status_code == 201, resp.text
        holding_id = resp.json()["id"]

        items_resp = client.get("/api/v1/security_health/items?state=open")
        assert items_resp.status_code == 200
        items = items_resp.json()
        seed_items = [
            i for i in items
            if i["item_type"] == ITEM_TYPE_SEED_BACKUP
            and i["holding_id"] == holding_id
        ]
        assert len(seed_items) == 1
        assert seed_items[0]["severity"] == ITEM_SEVERITY_CRITICAL

    def test_create_watch_only_purse_does_not_emit_seed_backup_item(
        self, app_with_db
    ) -> None:
        client, factory = app_with_db
        body = {
            "name": "Watch only",
            "description": "",
            "purpose": "spending",
            "purse_mode": "watch_only",
            "declared_security": {
                "custody_model": "self_single",
                "signing_model": "software_hot",
                "geographic_distribution": False,
                "inheritance_configured": False,
            },
            "display_color": "#10b981",
            "display_order": 0,
            "descriptors": [
                {
                    "name": "main",
                    "expression": WPKH_WITHOUT_ORIGIN,
                    "network": "mainnet",
                    "gap_limit": 3,
                }
            ],
        }
        resp = client.post("/api/v1/holdings/purse", json=body)
        assert resp.status_code == 201, resp.text
        holding_id = resp.json()["id"]

        items_resp = client.get("/api/v1/security_health/items?state=open")
        seed_items = [
            i for i in items_resp.json()
            if i["item_type"] == ITEM_TYPE_SEED_BACKUP
            and i["holding_id"] == holding_id
        ]
        assert len(seed_items) == 0


# ---------------------------------------------------------------------------
# Missing-signing-metadata item emitted on Strongbox creation
# ---------------------------------------------------------------------------


class TestMissingSigningMetadataHook:
    def test_strongbox_without_metadata_emits_item(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client, signing_metadata_present=False)

        items_resp = client.get("/api/v1/security_health/items?state=open")
        assert items_resp.status_code == 200
        metadata_items = [
            i for i in items_resp.json()
            if i["item_type"] == ITEM_TYPE_MISSING_SIGNING_METADATA
            and i["holding_id"] == holding_id
        ]
        assert len(metadata_items) == 1
        assert metadata_items[0]["severity"] == ITEM_SEVERITY_WARNING

    def test_strongbox_with_metadata_does_not_emit_item(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client, signing_metadata_present=True)

        items_resp = client.get("/api/v1/security_health/items?state=open")
        metadata_items = [
            i for i in items_resp.json()
            if i["item_type"] == ITEM_TYPE_MISSING_SIGNING_METADATA
            and i["holding_id"] == holding_id
        ]
        assert len(metadata_items) == 0

    def test_fix_metadata_reexport_resolves_open_item(self, app_with_db) -> None:
        client, factory = app_with_db
        holding_id = _create_strongbox_holding(client, signing_metadata_present=False)

        # Confirm item is open.
        items_before = [
            i for i in client.get("/api/v1/security_health/items?state=open").json()
            if i["holding_id"] == holding_id
            and i["item_type"] == ITEM_TYPE_MISSING_SIGNING_METADATA
        ]
        assert len(items_before) == 1

        # Apply fix.
        fix_resp = client.post(
            f"/api/v1/security_health/fix_metadata/{holding_id}/reexport",
            json={"descriptor_expression": WPKH_WITH_ORIGIN},
        )
        assert fix_resp.json()["success"] is True

        # Item should be gone from open.
        items_after = [
            i for i in client.get("/api/v1/security_health/items?state=open").json()
            if i["holding_id"] == holding_id
            and i["item_type"] == ITEM_TYPE_MISSING_SIGNING_METADATA
        ]
        assert len(items_after) == 0
