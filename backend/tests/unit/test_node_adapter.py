"""NodeAdapter unit tests.

Covers the JSON-RPC client behavior with a mocked transport: error translation,
sats conversion, scan-result shape. Real bitcoind interaction is in the
integration suite.
"""

from __future__ import annotations

import httpx
import pytest

from tallykeep.adapters.node_adapter import (
    NodeAdapter,
    NodeAuthError,
    NodeMethodNotFound,
    NodeRpcError,
    NodeUnavailable,
    _btc_to_sats,
)


pytestmark = pytest.mark.unit


# --- _btc_to_sats helper -------------------------------------------------------


class TestBtcToSats:
    @pytest.mark.parametrize(
        ("btc", "expected"),
        [
            (0, 0),
            (1, 100_000_000),
            (0.5, 50_000_000),
            (0.00000001, 1),     # 1 sat
            (1.23456789, 123_456_789),
            (21_000_000, 2_100_000_000_000_000),  # supply cap
            ("0.00012345", 12_345),
        ],
    )
    def test_round_trip_known_values(self, btc, expected: int) -> None:
        assert _btc_to_sats(btc) == expected

    def test_negative_amount(self) -> None:
        assert _btc_to_sats(-0.5) == -50_000_000


# --- NodeAdapter behavior with mocked transport --------------------------------


def _make_adapter(handler) -> NodeAdapter:  # type: ignore[no-untyped-def]
    """Build a NodeAdapter whose underlying httpx.Client uses MockTransport.

    The handler is a function that receives `httpx.Request` and returns
    `httpx.Response`.
    """
    transport = httpx.MockTransport(handler)
    adapter = NodeAdapter("http://test/", timeout_seconds=1.0)
    adapter._client.close()  # discard the real client
    adapter._client = httpx.Client(transport=transport, timeout=1.0)
    return adapter


def _ok_response(result):  # type: ignore[no-untyped-def]
    return httpx.Response(200, json={"id": "x", "error": None, "result": result})


def _error_response(code: int, message: str):  # type: ignore[no-untyped-def]
    return httpx.Response(
        200, json={"id": "x", "error": {"code": code, "message": message}, "result": None}
    )


class TestRpcCall:
    def test_successful_call_returns_result(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _ok_response({"chain": "regtest", "blocks": 0, "headers": 0,
                                 "bestblockhash": "00", "initialblockdownload": False})

        with _make_adapter(handler) as node:
            info = node.get_blockchain_info()

        assert info.chain == "regtest"
        assert info.blocks == 0

    def test_method_not_found_translates_to_typed_exception(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _error_response(-32601, "Method not found")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeMethodNotFound):
                node.get_blockchain_info()

    def test_other_rpc_errors_translate_to_typed_exception(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _error_response(-5, "Transaction not in mempool")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeRpcError) as exc_info:
                node.get_raw_transaction("aa" * 32)

        assert exc_info.value.code == -5
        assert "not in mempool" in exc_info.value.message

    def test_http_401_translates_to_auth_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="unauthorized")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeAuthError):
                node.get_blockchain_info()

    def test_http_5xx_translates_to_unavailable(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="service unavailable")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeUnavailable):
                node.get_blockchain_info()

    def test_connection_error_translates_to_unavailable(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeUnavailable):
                node.get_blockchain_info()

    def test_non_json_body_translates_to_unavailable(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeUnavailable):
                node.get_blockchain_info()


class TestIsHealthy:
    def test_healthy_when_call_succeeds(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _ok_response({"chain": "regtest", "blocks": 0, "headers": 0,
                                 "bestblockhash": "00", "initialblockdownload": False})

        with _make_adapter(handler) as node:
            assert node.is_healthy() is True

    def test_unhealthy_when_call_fails(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="down")

        with _make_adapter(handler) as node:
            assert node.is_healthy() is False

    def test_unhealthy_when_credentials_rejected(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="bad creds")

        with _make_adapter(handler) as node:
            assert node.is_healthy() is False

    def test_unhealthy_never_raises(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom")

        with _make_adapter(handler) as node:
            # Must return False, never raise.
            assert node.is_healthy() is False


class TestScanDescriptors:
    def test_translates_btc_amounts_to_sats(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _ok_response({
                "success": True,
                "height": 100,
                "total_amount": 1.5,
                "unspents": [
                    {
                        "txid": "aa" * 32,
                        "vout": 0,
                        "amount": 1.0,
                        "height": 100,
                        "address": "bcrt1qxyz",
                        "desc": "wpkh(...)",
                    },
                    {
                        "txid": "bb" * 32,
                        "vout": 1,
                        "amount": 0.5,
                        "height": 99,
                        "address": "bcrt1qabc",
                        "desc": "wpkh(...)",
                    },
                ],
            })

        with _make_adapter(handler) as node:
            result = node.scan_descriptors(["wpkh(xpub.../0/*)"])

        assert result.success is True
        assert result.height_at_scan == 100
        assert result.total_amount_sats == 150_000_000
        assert len(result.utxos) == 2
        assert result.utxos[0].amount_sats == 100_000_000
        assert result.utxos[1].amount_sats == 50_000_000

    def test_empty_unspents_yields_empty_list(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _ok_response({
                "success": True,
                "height": 50,
                "total_amount": 0,
                "unspents": [],
            })

        with _make_adapter(handler) as node:
            result = node.scan_descriptors(["wpkh(xpub.../0/*)"])

        assert result.utxos == []
        assert result.total_amount_sats == 0


class TestGetMempoolEntry:
    def test_returns_none_when_not_in_mempool(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _error_response(-5, "Transaction not in mempool")

        with _make_adapter(handler) as node:
            assert node.get_mempool_entry("aa" * 32) is None

    def test_returns_entry_when_present(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _ok_response({"vsize": 141, "fees": {"base": 0.00001}})

        with _make_adapter(handler) as node:
            entry = node.get_mempool_entry("aa" * 32)

        assert entry is not None
        assert entry["vsize"] == 141

    def test_other_rpc_errors_propagate(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _error_response(-99, "something else")

        with _make_adapter(handler) as node:
            with pytest.raises(NodeRpcError):
                node.get_mempool_entry("aa" * 32)


class TestSatsToBtcString:
    @pytest.mark.parametrize(
        ("sats", "expected"),
        [
            (0, "0.00000000"),
            (1, "0.00000001"),
            (100_000_000, "1.00000000"),
            (123_456_789, "1.23456789"),
            (-50_000_000, "-0.50000000"),
        ],
    )
    def test_format(self, sats: int, expected: str) -> None:
        assert NodeAdapter._sats_to_btc_string(sats) == expected
