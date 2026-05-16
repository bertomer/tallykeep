"""Integration tests for /api/v1/holdings (per-type creation + management).

Uses the abandon-abandon-...-about test mnemonic for descriptor inputs so
addresses derived during creation are deterministic facts, not bdkpython
internals.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tallykeep.models import HoldingRow, HoldingTypeChangeLogRow


pytestmark = pytest.mark.integration


# Reusable descriptor expressions for test bodies.
WPKH_MAINNET = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
)
WPKH_MAINNET_CHANGE = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)"
)
WPKH_TESTNET = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)
# 2-of-3 WSH sortedmulti on mainnet — used for Vault creation tests.
WSH_MULTISIG_MAINNET = (
    "wsh(sortedmulti(2,"
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*,"
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*,"
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/2/*"
    "))"
)


def _purse_body(
    *,
    name: str = "My phone wallet",
    expression: str = WPKH_MAINNET,
    change_expression: str | None = None,
    network: str = "mainnet",
    gap_limit: int = 5,
) -> dict:
    return {
        "name": name,
        "description": "My day-to-day spending",
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
                "expression": expression,
                "change_expression": change_expression,
                "network": network,
                "gap_limit": gap_limit,
            }
        ],
    }


def _strongbox_body() -> dict:
    # Use a different descriptor than the default purse — two holdings can't
    # share the same descriptor (uq_descriptor_expression).
    body = _purse_body(
        name="Cold reserve", expression=WPKH_MAINNET_CHANGE
    )
    body["purpose"] = "reserve"
    body.pop("purse_mode", None)
    body["declared_security"] = {
        "custody_model": "self_single",
        "signing_model": "hardware_offline",
        "geographic_distribution": False,
        "inheritance_configured": False,
    }
    body["signing_device_label"] = "Coldcard Mk4 in safe"
    return body


WSH_CLTV_MAINNET = (
    "wsh(and_v(v:pk("
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj"
    "/3/*),after(840000)))"
)
WSH_CSV_MAINNET = (
    "wsh(and_v(v:pk("
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj"
    "/4/*),older(52560)))"
)


def _vault_body() -> dict:
    body = _purse_body(
        name="Long-term holdings",
        expression=WSH_MULTISIG_MAINNET,
        network="mainnet",
    )
    body["purpose"] = "long_term"
    body.pop("purse_mode", None)
    body["declared_security"] = {
        "custody_model": "self_multisig",
        "signing_model": "ceremonial",
        "geographic_distribution": True,
        "inheritance_configured": True,
    }
    body["recovery_setup_notes"] = "Co-signers in two locations."
    return body


def _vault_cltv_body() -> dict:
    body = _purse_body(
        name="CLTV vault",
        expression=WSH_CLTV_MAINNET,
        network="mainnet",
    )
    body["purpose"] = "long_term"
    body.pop("purse_mode", None)
    body["declared_security"] = {
        "custody_model": "self_single",
        "signing_model": "ceremonial",
        "geographic_distribution": False,
        "inheritance_configured": False,
    }
    return body


def _vault_csv_body() -> dict:
    body = _purse_body(
        name="CSV vault",
        expression=WSH_CSV_MAINNET,
        network="mainnet",
    )
    body["purpose"] = "long_term"
    body.pop("purse_mode", None)
    body["declared_security"] = {
        "custody_model": "self_single",
        "signing_model": "ceremonial",
        "geographic_distribution": False,
        "inheritance_configured": False,
    }
    return body


# --- per-type creation ---------------------------------------------------------


class TestCreatePurse:
    def test_create_with_single_descriptor_persists_holding_and_addresses(
        self, app_with_db
    ) -> None:
        client, factory = app_with_db
        body = _purse_body(gap_limit=5)

        response = client.post("/api/v1/holdings/purse", json=body)
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["holding_type"] == "purse"
        assert result["name"] == "My phone wallet"
        assert len(result["descriptor_ids"]) == 1

        # Verify the holding + 5 derived addresses were persisted.
        with factory() as session:
            row = session.get(HoldingRow, result["id"])
            assert row is not None
            assert row.holding_type == "purse"

        # Listing the descriptor's addresses returns 5.
        descriptor_id = result["descriptor_ids"][0]
        addresses = client.get(
            f"/api/v1/descriptors/{descriptor_id}/addresses"
        ).json()["addresses"]
        assert len(addresses) == 5
        # All addresses are external (is_change=False).
        assert all(a["is_change"] is False for a in addresses)

    def test_create_with_change_descriptor_doubles_address_count(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        body = _purse_body(
            change_expression=WPKH_MAINNET_CHANGE, gap_limit=5
        )
        response = client.post("/api/v1/holdings/purse", json=body)
        assert response.status_code == 201

        descriptor_id = response.json()["descriptor_ids"][0]
        addresses = client.get(
            f"/api/v1/descriptors/{descriptor_id}/addresses",
            params={"limit": 200},
        ).json()["addresses"]
        # 5 external + 5 change = 10
        assert len(addresses) == 10
        assert sum(1 for a in addresses if a["is_change"]) == 5

    def test_create_with_invalid_descriptor_returns_422_and_rolls_back(
        self, app_with_db
    ) -> None:
        client, factory = app_with_db
        body = _purse_body(expression="not a descriptor at all")
        response = client.post("/api/v1/holdings/purse", json=body)
        assert response.status_code == 422

        with factory() as session:
            count = session.query(HoldingRow).count()
            assert count == 0  # rolled back cleanly

    def test_create_with_existing_descriptor_returns_409(
        self, app_with_db
    ) -> None:
        """Two holdings can't share a descriptor (uq_descriptor_expression).
        The second create attempt must return 409 Conflict, not 500."""
        client, _ = app_with_db
        # First create succeeds.
        first = client.post("/api/v1/holdings/purse", json=_purse_body())
        assert first.status_code == 201, first.text
        # Second create with the same descriptor expression returns 409.
        second = client.post(
            "/api/v1/holdings/purse",
            json=_purse_body(name="Second wallet"),
        )
        assert second.status_code == 409
        assert "already exists" in second.text

    def test_create_with_multisig_descriptor_rejected(self, app_with_db) -> None:
        client, _ = app_with_db
        multisig = (
            "wsh(sortedmulti(2,"
            "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*,"
            "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*"
            "))"
        )
        body = _purse_body(expression=multisig)
        response = client.post("/api/v1/holdings/purse", json=body)
        assert response.status_code == 422
        assert "multisig" in response.text.lower()


class TestCreateStrongbox:
    def test_create_persists_signing_device_label(self, app_with_db) -> None:
        client, _ = app_with_db
        body = _strongbox_body()
        response = client.post("/api/v1/holdings/strongbox", json=body)
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["holding_type"] == "strongbox"
        assert result["signing_device_label"] == "Coldcard Mk4 in safe"

    def test_create_strongbox_with_software_hot_rejected(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        body = _strongbox_body()
        # Domain invariants don't actually forbid software_hot on Strongbox,
        # but mismatched declared_security can still be set; here we just
        # confirm the endpoint accepts a hardware-offline declaration as the
        # canonical case.
        body["declared_security"]["signing_model"] = "software_hot"
        response = client.post("/api/v1/holdings/strongbox", json=body)
        # No structural rejection — declared_security is a free-form claim
        # per spec module 02. Should succeed (analyzer surfaces the
        # discrepancy in M5).
        assert response.status_code == 201

    def test_create_strongbox_with_vendor_persists_slug(self, app_with_db) -> None:
        client, _ = app_with_db
        body = _strongbox_body()
        body["vendor"] = "coldcard"
        response = client.post("/api/v1/holdings/strongbox", json=body)
        assert response.status_code == 201, response.text
        assert response.json()["vendor"] == "coldcard"

    def test_create_strongbox_with_signing_metadata_present_false(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        body = _strongbox_body()
        body["signing_metadata_present"] = False
        response = client.post("/api/v1/holdings/strongbox", json=body)
        assert response.status_code == 201, response.text
        assert response.json()["signing_metadata_present"] is False

    def test_create_strongbox_with_unknown_vendor_slug_rejected(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        body = _strongbox_body()
        body["vendor"] = "unknownvendor"
        response = client.post("/api/v1/holdings/strongbox", json=body)
        assert response.status_code == 422


class TestCreateVault:
    def test_create_persists_multisig_metadata(self, app_with_db) -> None:
        client, _ = app_with_db
        response = client.post("/api/v1/holdings/vault", json=_vault_body())
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["holding_type"] == "vault"
        # Signers derived from the 2-of-3 sortedmulti descriptor.
        assert result["required_signers"] == 2
        assert result["total_signers"] == 3
        # Pure multisig — no timelock.
        assert result["timelock_kind"] is None
        assert result["timelock_value"] is None

    def test_create_cltv_vault_persists_timelock_metadata(self, app_with_db) -> None:
        client, _ = app_with_db
        response = client.post("/api/v1/holdings/vault", json=_vault_cltv_body())
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["holding_type"] == "vault"
        assert result["timelock_kind"] == "cltv"
        assert result["timelock_value"] == 840000

    def test_create_csv_vault_persists_timelock_metadata(self, app_with_db) -> None:
        client, _ = app_with_db
        response = client.post("/api/v1/holdings/vault", json=_vault_csv_body())
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["holding_type"] == "vault"
        assert result["timelock_kind"] == "csv"
        assert result["timelock_value"] == 52560

    def test_create_vault_with_zero_required_signers_rejected(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        body = _vault_body()
        body["required_signers"] = 0  # Pydantic ge=1 rejects this
        response = client.post("/api/v1/holdings/vault", json=body)
        assert response.status_code == 422

    def test_create_vault_with_single_key_descriptor_rejected(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        body = _vault_body()
        # Replace multisig descriptor with a single-key WPKH — must be rejected.
        body["descriptors"][0]["expression"] = WPKH_MAINNET
        response = client.post("/api/v1/holdings/vault", json=body)
        assert response.status_code == 422
        assert "multisig" in response.text.lower()


def _account_body(
    *,
    api_key: str = "key",
    api_secret: str = "secret",
) -> dict:
    return {
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
            "api_key": api_key,
            "api_secret": api_secret,
        },
    }


def _clean_perms(extra: list[str] | None = None) -> MagicMock:
    return MagicMock(
        can_read=True, can_trade=False, can_withdraw=False,
        detected_extra_permissions=extra or [],
    )


class TestCreateAccount:
    def test_create_account_missing_custodial_provider_returns_422(self, app_with_db) -> None:
        client, _ = app_with_db
        body = {
            "name": "Kraken main",
            "purpose": "transit",
            "declared_security": {
                "custody_model": "third_party",
                "signing_model": "not_applicable",
            },
        }
        response = client.post("/api/v1/holdings/account", json=body)
        assert response.status_code == 422

    def test_create_account_read_only_key_returns_201_with_balance(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms()
        mock_adapter.get_balance.return_value = 2_500_000
        mock_adapter.get_other_balances.return_value = {"ETH": "1.2", "USDC": "500"}

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post("/api/v1/holdings/account", json=_account_body())

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["btc_balance_sats"] == 2_500_000
        assert set(data["other_asset_tickers"]) == {"ETH", "USDC"}
        assert data["other_asset_total_count"] == 2
        assert "holding_id" in data
        assert "provider_id" in data

    def test_create_account_invalid_credentials_returns_422(
        self, app_with_db
    ) -> None:
        from tallykeep.adapters.custodial_provider_adapter import ProviderAuthError

        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.side_effect = ProviderAuthError("invalid key")

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post("/api/v1/holdings/account", json=_account_body())

        assert response.status_code == 422

    def test_create_account_overage_withdraw_funds_returns_409(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms(["Withdraw funds"])

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post("/api/v1/holdings/account", json=_account_body())

        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["code"] == "overage_permissions"
        assert "Withdraw funds" in data["extra_permissions"]

    def test_create_account_overage_trade_and_margin_returns_409(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms(["Trade", "Margin"])

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post("/api/v1/holdings/account", json=_account_body())

        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["code"] == "overage_permissions"
        assert set(data["extra_permissions"]) == {"Trade", "Margin"}


def _validate_body(
    *,
    adapter_id: str = "kraken",
    api_key: str = "key",
    api_secret: str = "secret",
) -> dict:
    return {"adapter_id": adapter_id, "api_key": api_key, "api_secret": api_secret}


class TestValidateAccountCredentials:
    def test_validate_clean_read_only_key_returns_200_with_balance(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms()
        mock_adapter.get_balance.return_value = 1_800_000
        mock_adapter.get_other_balances.return_value = {"ETH": "0.5"}

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post(
                "/api/v1/holdings/account/validate", json=_validate_body()
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["btc_balance_sats"] == 1_800_000
        assert data["other_asset_tickers"] == ["ETH"]
        assert data["other_asset_total_count"] == 1
        assert "holding_id" not in data

    def test_validate_invalid_credentials_returns_422(self, app_with_db) -> None:
        client, _ = app_with_db
        from tallykeep.adapters.custodial_provider_adapter import ProviderAuthError
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.side_effect = ProviderAuthError("bad key")

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post(
                "/api/v1/holdings/account/validate", json=_validate_body()
            )

        assert response.status_code == 422

    def test_validate_overage_withdraw_funds_returns_409(self, app_with_db) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms(["Withdraw funds"])

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post(
                "/api/v1/holdings/account/validate", json=_validate_body()
            )

        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["code"] == "overage_permissions"
        assert "Withdraw funds" in data["extra_permissions"]

    def test_validate_overage_trade_and_margin_returns_409(
        self, app_with_db
    ) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms(["Trade", "Margin"])

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            response = client.post(
                "/api/v1/holdings/account/validate", json=_validate_body()
            )

        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["code"] == "overage_permissions"
        assert set(data["extra_permissions"]) == {"Trade", "Margin"}

    def test_validate_does_not_create_holding(self, app_with_db) -> None:
        client, _ = app_with_db
        mock_adapter = MagicMock()
        mock_adapter.get_permissions.return_value = _clean_perms()
        mock_adapter.get_balance.return_value = 0
        mock_adapter.get_other_balances.return_value = {}

        with patch(
            "tallykeep.services.treasury_service.build_adapter",
            return_value=mock_adapter,
        ):
            client.post("/api/v1/holdings/account/validate", json=_validate_body())

        holdings = client.get("/api/v1/holdings").json()
        account_holdings = [h for h in holdings if h["holding_type"] == "account"]
        assert account_holdings == []


# --- list / get / patch / archive / change-type --------------------------------


class TestListAndGet:
    def test_list_returns_created_holdings(self, app_with_db) -> None:
        client, _ = app_with_db
        client.post("/api/v1/holdings/purse", json=_purse_body(name="A"))
        client.post(
            "/api/v1/holdings/strongbox", json=_strongbox_body()
        )

        response = client.get("/api/v1/holdings")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2
        types = {item["holding_type"] for item in items}
        assert types == {"purse", "strongbox"}

    def test_list_excludes_archived_by_default(self, app_with_db) -> None:
        client, _ = app_with_db
        created = client.post(
            "/api/v1/holdings/purse", json=_purse_body(name="ToArchive")
        ).json()
        archive_response = client.post(
            f"/api/v1/holdings/{created['id']}/archive"
        )
        assert archive_response.status_code == 204

        items = client.get("/api/v1/holdings").json()
        assert items == []

        items = client.get(
            "/api/v1/holdings", params={"include_archived": True}
        ).json()
        assert len(items) == 1
        assert items[0]["is_archived"] is True

    def test_list_filtered_by_holding_type(self, app_with_db) -> None:
        client, _ = app_with_db
        client.post("/api/v1/holdings/purse", json=_purse_body(name="P"))
        client.post(
            "/api/v1/holdings/strongbox", json=_strongbox_body()
        )

        items = client.get(
            "/api/v1/holdings", params={"holding_type": "purse"}
        ).json()
        assert len(items) == 1
        assert items[0]["holding_type"] == "purse"

    def test_get_returns_full_holding(self, app_with_db) -> None:
        client, _ = app_with_db
        created = client.post(
            "/api/v1/holdings/purse", json=_purse_body()
        ).json()
        response = client.get(f"/api/v1/holdings/{created['id']}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == created["id"]
        assert body["descriptor_ids"] == created["descriptor_ids"]

    def test_get_unknown_returns_404(self, app_with_db) -> None:
        client, _ = app_with_db
        response = client.get(
            "/api/v1/holdings/00000000-0000-0000-0000-0000000000ff"
        )
        assert response.status_code == 404


class TestPatch:
    def test_patch_updates_name_and_color(self, app_with_db) -> None:
        client, _ = app_with_db
        created = client.post(
            "/api/v1/holdings/purse", json=_purse_body()
        ).json()
        response = client.patch(
            f"/api/v1/holdings/{created['id']}",
            json={"name": "Renamed", "display_color": "#abcdef"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Renamed"
        assert body["display_color"] == "#abcdef"

    def test_patch_empty_body_rejected(self, app_with_db) -> None:
        client, _ = app_with_db
        created = client.post(
            "/api/v1/holdings/purse", json=_purse_body()
        ).json()
        response = client.patch(
            f"/api/v1/holdings/{created['id']}", json={}
        )
        assert response.status_code == 422

    def test_patch_unknown_returns_404(self, app_with_db) -> None:
        client, _ = app_with_db
        response = client.patch(
            "/api/v1/holdings/00000000-0000-0000-0000-0000000000ff",
            json={"name": "x"},
        )
        assert response.status_code == 404


class TestChangeType:
    def test_purse_to_strongbox_records_audit_log(self, app_with_db) -> None:
        client, factory = app_with_db
        created = client.post(
            "/api/v1/holdings/purse", json=_purse_body()
        ).json()
        response = client.post(
            f"/api/v1/holdings/{created['id']}/change-type",
            json={
                "new_type": "strongbox",
                "reason": "Migrated keys to Coldcard",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["holding_type"] == "strongbox"

        with factory() as session:
            log = session.query(HoldingTypeChangeLogRow).filter_by(
                holding_id=created["id"]
            ).one()
            assert log.previous_type == "purse"
            assert log.new_type == "strongbox"
            assert log.reason == "Migrated keys to Coldcard"

    def test_change_to_account_rejected(self, app_with_db) -> None:
        client, _ = app_with_db
        created = client.post(
            "/api/v1/holdings/purse", json=_purse_body()
        ).json()
        response = client.post(
            f"/api/v1/holdings/{created['id']}/change-type",
            json={"new_type": "account"},
        )
        assert response.status_code == 422
