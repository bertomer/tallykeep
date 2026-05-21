"""Integration tests for Account-detail endpoints (Account-detail iteration).

Covers:
  - GET /holdings/{id} — Account snapshot with account_detail sub-object
  - PATCH /holdings/{id} — Account rename (name) + polling_interval_seconds
  - DELETE /holdings/{id} — Account removal (cascade)
  - Invalid polling_interval_seconds values (422)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from tallykeep.models.custodial_ledger_entry import CustodialLedgerEntryRow


pytestmark = pytest.mark.integration


_ACCOUNT_BODY = {
    "name": "Kraken main",
    "purpose": "transit",
    "declared_security": {
        "custody_model": "third_party",
        "signing_model": "not_applicable",
    },
    "display_color": "#f59e0b",
    "display_order": 0,
    "custodial_provider": {
        "provider_kind": "exchange",
        "display_name": "Kraken",
        "adapter_id": "kraken",
        "api_key": "testkey1234",
        "api_secret": "testsecret",
    },
}


def _clean_perms() -> MagicMock:
    return MagicMock(
        can_read=True, can_trade=False, can_withdraw=False,
        overage=[], underage=[],
    )


def _mock_adapter(
    *,
    balance: int = 1_000_000,
    other: dict | None = None,
    entries=None,
) -> MagicMock:
    mock = MagicMock()
    mock.get_permissions.return_value = _clean_perms()
    mock.get_balance.return_value = balance
    mock.get_other_balances.return_value = other or {"ETH": "2.5", "USDC": "1000"}
    mock.fetch_ledger_since.return_value = (entries or [], None)
    return mock


def _create_account(client) -> dict:  # type: ignore[no-untyped-def]
    with patch(
        "tallykeep.services.treasury_service.build_adapter",
        return_value=_mock_adapter(),
    ):
        resp = client.post("/api/v1/holdings/account", json=_ACCOUNT_BODY)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_ledger_entry(factory, provider_id: str, holding_id: str) -> None:  # type: ignore[no-untyped-def]
    row = CustodialLedgerEntryRow(
        id=uuid4(),
        holding_id=holding_id,
        custodial_provider_id=provider_id,
        provider_entry_id="entry-001",
        kind="deposit",
        asset="BTC",
        amount_sats=50_000,
        status="success",
        timestamp=datetime.now(UTC),
        raw_payload={"raw": True},
    )
    with factory() as session:
        session.add(row)
        session.commit()


# ---------------------------------------------------------------------------
# GET /holdings/{id} — Account detail snapshot
# ---------------------------------------------------------------------------


class TestGetAccountDetail:
    def test_snapshot_includes_account_detail(self, app_with_db) -> None:
        client, _ = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]

        resp = client.get(f"/api/v1/holdings/{holding_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["holding_type"] == "account"
        assert body["account_detail"] is not None
        detail = body["account_detail"]
        assert detail["provider_id"] == created["provider_id"]
        assert detail["adapter_id"] == "kraken"
        assert detail["last_known_balance_sats"] == 1_000_000
        assert detail["polling_interval_seconds"] == 600
        assert detail["non_btc_balances"] == {"ETH": "2.5", "USDC": "1000"}
        assert isinstance(detail["ledger_entries"], list)
        assert detail["ledger_has_more"] is False

    def test_snapshot_observation_key_last_four(self, app_with_db) -> None:
        client, _ = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]

        resp = client.get(f"/api/v1/holdings/{holding_id}")
        assert resp.status_code == 200, resp.text
        detail = resp.json()["account_detail"]
        # "testkey1234"[-4:] == "1234"
        assert detail["observation_key_last_four"] == "1234"

    def test_snapshot_includes_seeded_ledger_entries(self, app_with_db) -> None:
        client, factory = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]
        provider_id = created["provider_id"]
        _seed_ledger_entry(factory, provider_id, holding_id)

        resp = client.get(f"/api/v1/holdings/{holding_id}")
        assert resp.status_code == 200, resp.text
        entries = resp.json()["account_detail"]["ledger_entries"]
        assert len(entries) == 1
        assert entries[0]["kind"] == "deposit"
        assert entries[0]["amount_sats"] == 50_000
        assert entries[0]["status"] == "success"

    def test_snapshot_returns_basic_response_for_non_account(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.post(
            "/api/v1/holdings/purse",
            json={
                "name": "My Purse",
                "purpose": "reserve",
                "purse_mode": "watch_only",
                "declared_security": {
                    "custody_model": "self_single",
                    "signing_model": "hardware_offline",
                },
                "display_color": "#000000",
                "display_order": 0,
                "descriptors": [
                    {
                        "name": "main",
                        "expression": "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)",
                        "network": "mainnet",
                        "gap_limit": 5,
                    }
                ],
            },
        )
        assert resp.status_code == 201
        holding_id = resp.json()["id"]

        detail_resp = client.get(f"/api/v1/holdings/{holding_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["account_detail"] is None

    def test_snapshot_404_for_missing_holding(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.get(f"/api/v1/holdings/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /holdings/{id} — rename + polling interval
# ---------------------------------------------------------------------------


class TestPatchAccount:
    def test_rename_updates_holding_name(self, app_with_db) -> None:
        client, _ = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]

        resp = client.patch(
            f"/api/v1/holdings/{holding_id}",
            json={"name": "Renamed Kraken"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Renamed Kraken"

    def test_polling_interval_valid_updates(self, app_with_db) -> None:
        client, _ = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]

        for interval in (60, 300, 1800, 3600):
            resp = client.patch(
                f"/api/v1/holdings/{holding_id}",
                json={"polling_interval_seconds": interval},
            )
            assert resp.status_code == 200, f"Failed for interval {interval}: {resp.text}"

        # Verify the last set value is persisted in the snapshot.
        snapshot = client.get(f"/api/v1/holdings/{holding_id}").json()
        assert snapshot["account_detail"]["polling_interval_seconds"] == 3600

    def test_polling_interval_invalid_returns_422(self, app_with_db) -> None:
        client, _ = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]

        for invalid in (0, 30, 120, 900, 7200):
            resp = client.patch(
                f"/api/v1/holdings/{holding_id}",
                json={"polling_interval_seconds": invalid},
            )
            assert resp.status_code == 422, f"Expected 422 for {invalid}, got {resp.status_code}"

    def test_polling_interval_on_non_account_returns_422(self, app_with_db) -> None:
        client, _ = app_with_db
        purse = client.post(
            "/api/v1/holdings/purse",
            json={
                "name": "Purse",
                "purpose": "reserve",
                "purse_mode": "watch_only",
                "declared_security": {
                    "custody_model": "self_single",
                    "signing_model": "hardware_offline",
                },
                "display_color": "#000000",
                "display_order": 0,
                "descriptors": [
                    {
                        "name": "main",
                        "expression": "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/2/*)",
                        "network": "mainnet",
                        "gap_limit": 5,
                    }
                ],
            },
        )
        assert purse.status_code == 201
        purse_id = purse.json()["id"]

        resp = client.patch(
            f"/api/v1/holdings/{purse_id}",
            json={"polling_interval_seconds": 600},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /holdings/{id} — Account removal
# ---------------------------------------------------------------------------


class TestDeleteAccount:
    def test_delete_removes_holding_and_provider(self, app_with_db) -> None:
        client, _ = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]

        resp = client.delete(f"/api/v1/holdings/{holding_id}")
        assert resp.status_code == 204, resp.text

        # GET should now return 404.
        assert client.get(f"/api/v1/holdings/{holding_id}").status_code == 404

    def test_delete_with_ledger_entries_cascades(self, app_with_db) -> None:
        client, factory = app_with_db
        created = _create_account(client)
        holding_id = created["holding_id"]
        provider_id = created["provider_id"]
        _seed_ledger_entry(factory, provider_id, holding_id)

        resp = client.delete(f"/api/v1/holdings/{holding_id}")
        assert resp.status_code == 204, resp.text

        assert client.get(f"/api/v1/holdings/{holding_id}").status_code == 404

    def test_delete_missing_holding_returns_404(self, app_with_db) -> None:
        client, _ = app_with_db
        resp = client.delete(f"/api/v1/holdings/{uuid4()}")
        assert resp.status_code == 404

    def test_delete_purse_holding_succeeds(self, app_with_db) -> None:
        # ADR-0017: DELETE accepts all 4 Holding types, not just Account
        client, _ = app_with_db
        purse = client.post(
            "/api/v1/holdings/purse",
            json={
                "name": "Purse",
                "purpose": "reserve",
                "purse_mode": "watch_only",
                "declared_security": {
                    "custody_model": "self_single",
                    "signing_model": "hardware_offline",
                },
                "display_color": "#000000",
                "display_order": 0,
                "descriptors": [
                    {
                        "name": "main",
                        "expression": "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/3/*)",
                        "network": "mainnet",
                        "gap_limit": 5,
                    }
                ],
            },
        )
        assert purse.status_code == 201
        purse_id = purse.json()["id"]

        resp = client.delete(f"/api/v1/holdings/{purse_id}")
        assert resp.status_code == 204
        assert client.get(f"/api/v1/holdings/{purse_id}").status_code == 404
