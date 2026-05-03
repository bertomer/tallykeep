"""bitcoind JSON-RPC adapter — spec module 01 / 05.

Anti-corruption layer. Domain code never speaks bitcoind; it goes through
NodeAdapter, which translates raw RPC results into the typed shapes the rest of
the codebase uses.

This module deals with **synchronous** RPC over HTTP. ZeroMQ subscription for
live chain events lives in `chain_event_adapter.py` (M5.3).

v1 surface — only what the savings layer needs:
  - get_blockchain_info()      — height, chain, headers
  - scan_descriptors(...)      — initial scan (`scantxoutset`)
  - get_raw_transaction(txid)  — tx detail + confirmation status
  - get_mempool_entry(txid)    — is this tx in the mempool right now?
  - estimate_smart_fee(...)    — for M6's fee estimator
  - send_raw_transaction(hex)  — M6 broadcast
  - is_healthy()               — `/health` probe target

bitcoind RPC error codes are translated into typed exceptions:
  - NodeUnavailable           — connection refused / timeout / 5xx
  - NodeAuthError             — 401 (wrong rpcuser/rpcpassword)
  - NodeMethodNotFound        — JSON-RPC -32601
  - NodeRpcError              — every other JSON-RPC error
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


# --- exceptions --------------------------------------------------------------


class NodeError(Exception):
    """Base class for bitcoind RPC failures."""


class NodeUnavailable(NodeError):
    """Connection refused, timeout, or transport-level failure."""


class NodeAuthError(NodeError):
    """RPC credentials rejected (HTTP 401)."""


class NodeMethodNotFound(NodeError):
    """The bitcoind build does not support the requested method (-32601).

    Most useful when probing optional methods like `scantxoutset` on builds
    where it has been disabled at compile time.
    """


class NodeRpcError(NodeError):
    """Any other JSON-RPC error returned by bitcoind."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"bitcoind RPC error {code}: {message}")
        self.code = code
        self.message = message


# --- typed result containers --------------------------------------------------


@dataclass(frozen=True)
class BlockchainInfo:
    """Trimmed-down `getblockchaininfo` result. Add fields as features need them."""

    chain: str           # "main" / "test" / "signet" / "regtest"
    blocks: int
    headers: int
    best_block_hash: str
    initial_block_download: bool


@dataclass(frozen=True)
class ScanUtxo:
    """One UTXO returned by `scantxoutset`."""

    txid: str
    vout: int
    address: str
    amount_sats: int   # bitcoind reports `amount` in BTC; we convert
    height: int        # 0 = mempool / unconfirmed (scantxoutset filters out mempool, so this is always > 0)
    descriptor: str    # the descriptor that matched this UTXO


@dataclass(frozen=True)
class ScanResult:
    """Full result of `scantxoutset`."""

    success: bool
    height_at_scan: int  # the chain height when the scan ran
    total_amount_sats: int
    utxos: list[ScanUtxo]


# --- helpers -----------------------------------------------------------------


def _btc_to_sats(btc: float | str | int) -> int:
    """bitcoind returns BTC as a JSON number. Convert to integer sats safely.

    Avoids float-rounding by formatting through a string. 1 BTC = 100_000_000 sats.
    """
    # Path through Decimal would be ideal, but `float -> str -> int` works for
    # the 8-decimal-place range bitcoind emits (it never emits more precision).
    text = f"{float(btc):.8f}"
    integer, _, fractional = text.partition(".")
    fractional = (fractional + "00000000")[:8]
    sign = -1 if integer.startswith("-") else 1
    return sign * (abs(int(integer)) * 100_000_000 + int(fractional))


# --- adapter -----------------------------------------------------------------


class NodeAdapter:
    """Thin synchronous JSON-RPC wrapper around bitcoind.

    One adapter instance per process is fine; the underlying httpx.Client owns a
    connection pool that gets reused across calls. Call `close()` on shutdown
    (or use as a context manager) to release the pool.
    """

    def __init__(
        self,
        rpc_url: str,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not rpc_url:
            raise ValueError("rpc_url is required")
        self._rpc_url = rpc_url
        self._client = httpx.Client(timeout=timeout_seconds)
        self._next_id = 0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "NodeAdapter":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # --- low-level RPC -------------------------------------------------------

    def _call(self, method: str, params: list[Any] | None = None) -> Any:
        self._next_id += 1
        request_id = f"tallykeep-{self._next_id}"
        body = {
            "jsonrpc": "1.0",
            "id": request_id,
            "method": method,
            "params": params or [],
        }
        try:
            response = self._client.post(self._rpc_url, json=body)
        except httpx.RequestError as exc:
            raise NodeUnavailable(f"connection failure: {exc}") from exc

        if response.status_code == 401:
            raise NodeAuthError("bitcoind rejected the RPC credentials (401)")

        # bitcoind frequently returns HTTP 500 for RPC-level errors (e.g. -5
        # "transaction not in mempool"); the body is still a valid JSON-RPC
        # response with the `error` field set. Always try to parse the body
        # first — the `error` field is the source of truth. Only fall back to
        # NodeUnavailable when the body isn't parseable JSON.
        try:
            payload = response.json()
        except ValueError as exc:
            raise NodeUnavailable(
                f"bitcoind returned non-JSON ({response.status_code}): {response.text[:200]}"
            ) from exc

        error = payload.get("error")
        if error:
            code = error.get("code", 0)
            message = error.get("message", "unknown error")
            if code == -32601:
                raise NodeMethodNotFound(message)
            raise NodeRpcError(code=code, message=message)
        return payload.get("result")

    # --- public methods ------------------------------------------------------

    def is_healthy(self) -> bool:
        """Lightweight probe used by /api/v1/health.

        Returns True if bitcoind responds to `getblockchaininfo` within the
        adapter timeout. Never raises.
        """
        try:
            self._call("getblockchaininfo")
            return True
        except NodeError:
            return False
        except Exception:  # noqa: BLE001 — health probe never raises
            return False

    def get_blockchain_info(self) -> BlockchainInfo:
        result = self._call("getblockchaininfo")
        return BlockchainInfo(
            chain=str(result["chain"]),
            blocks=int(result["blocks"]),
            headers=int(result["headers"]),
            best_block_hash=str(result["bestblockhash"]),
            initial_block_download=bool(result.get("initialblockdownload", False)),
        )

    def scan_descriptors(self, descriptors: list[str]) -> ScanResult:
        """Run `scantxoutset` over the given descriptors and translate the result.

        Each entry in `descriptors` is a BIP 380 descriptor string with a
        `range` already substituted (or a `*` wildcard), as bitcoind's
        scantxoutset expects. Callers that want range scans should pass the
        descriptor as a dict — for now we keep the simple case (string only)
        since the savings layer always scans `wpkh(...)/0/*`-style.

        bitcoind returns amounts as BTC; we convert to sats.
        """
        # bitcoind's scantxoutset accepts either a string (descriptor with
        # implicit range) or {"desc": ..., "range": [start, end]}. Pass through
        # whatever the caller gave us; for the v1 savings layer we'll always be
        # passing fully-derived address ranges via {"desc": ..., "range": N}.
        scan_objects: list[Any] = []
        for d in descriptors:
            if "*" in d:
                # Implicit range — bitcoind defaults to 0..1000. Be explicit so
                # the result is predictable: scan the same gap_limit we used
                # during import (defaults at the caller level).
                scan_objects.append({"desc": d, "range": 1000})
            else:
                scan_objects.append(d)

        result = self._call("scantxoutset", ["start", scan_objects])
        utxos: list[ScanUtxo] = []
        for unspent in result.get("unspents", []):
            utxos.append(
                ScanUtxo(
                    txid=str(unspent["txid"]),
                    vout=int(unspent["vout"]),
                    address=str(unspent.get("address") or ""),
                    amount_sats=_btc_to_sats(unspent["amount"]),
                    height=int(unspent.get("height", 0)),
                    descriptor=str(unspent.get("desc") or ""),
                )
            )
        return ScanResult(
            success=bool(result.get("success", False)),
            height_at_scan=int(result.get("height", 0)),
            total_amount_sats=_btc_to_sats(result.get("total_amount", 0)),
            utxos=utxos,
        )

    def get_raw_transaction(
        self, txid: str, *, verbose: bool = True
    ) -> dict[str, Any]:
        """Fetch a transaction. Returns the raw decoded shape from bitcoind.

        Requires `txindex=1` on bitcoind for transactions outside the wallet /
        outside the current mempool. Our regtest container has txindex enabled
        (see docker-compose.yml).
        """
        return self._call("getrawtransaction", [txid, verbose])

    def get_mempool_entry(self, txid: str) -> dict[str, Any] | None:
        """Return the mempool entry for `txid`, or None if it's not in the mempool."""
        try:
            return self._call("getmempoolentry", [txid])
        except NodeRpcError as exc:
            # -5 = transaction not in mempool. Anything else, propagate.
            if exc.code == -5:
                return None
            raise

    def estimate_smart_fee(self, target_blocks: int) -> dict[str, Any]:
        """Wraps `estimatesmartfee`. Result has `feerate` (BTC/kvB) when known."""
        return self._call("estimatesmartfee", [target_blocks])

    def send_raw_transaction(self, hex_tx: str) -> str:
        """Broadcast a fully-signed transaction. Returns the txid."""
        return str(self._call("sendrawtransaction", [hex_tx]))

    # --- regtest test helpers ------------------------------------------------

    def generate_to_address(self, blocks: int, address: str) -> list[str]:
        """Mine `blocks` blocks rewarding `address`. Regtest only.

        bitcoind rejects this on mainnet/testnet/signet; intended for
        deterministic integration tests that need to create on-chain state.
        """
        return self._call("generatetoaddress", [blocks, address])

    def create_wallet(self, name: str, *, descriptors: bool = True) -> dict[str, Any]:
        """Create a bitcoind-side wallet. Used by regtest fixtures to source funds."""
        return self._call(
            "createwallet",
            [name, False, False, "", False, descriptors, True, False],
        )

    def get_new_address(
        self, *, wallet: str | None = None
    ) -> str:
        """Get an address from a bitcoind-side wallet (regtest fixture helper).

        Uses the wallet-aware RPC path `/wallet/<name>` when a wallet name is
        given. Without a wallet, calls the default endpoint which only works
        if exactly one wallet is loaded.
        """
        if wallet is None:
            return str(self._call("getnewaddress"))
        # Wallet-scoped RPC: bitcoind expects POST /wallet/<name>.
        previous_url = self._rpc_url
        self._rpc_url = previous_url.rstrip("/") + f"/wallet/{wallet}"
        try:
            return str(self._call("getnewaddress"))
        finally:
            self._rpc_url = previous_url

    def send_to_address_from_wallet(
        self, wallet: str, address: str, amount_sats: int
    ) -> str:
        """Send sats from a named wallet to an external address. Returns txid.

        Used by the M5.2 integration tests to fund a Holding's address from
        the bitcoind-side faucet wallet.

        bitcoind's sendtoaddress expects a JSON number (not a string) for
        amount, so we serialize sats as a float. Up to ~21M BTC (the supply
        cap, ~2.1e15 sats), the float representation is exact at 8-decimal
        precision because IEEE 754 doubles have ~15-17 significant digits.
        """
        previous_url = self._rpc_url
        self._rpc_url = previous_url.rstrip("/") + f"/wallet/{wallet}"
        try:
            btc_amount = amount_sats / 100_000_000
            return str(self._call("sendtoaddress", [address, btc_amount]))
        finally:
            self._rpc_url = previous_url

    @staticmethod
    def _sats_to_btc_string(sats: int) -> str:
        """Format sats as a BTC string with 8 decimal places.

        bitcoind's RPC expects amounts as JSON numbers but tolerates strings
        when they look like a decimal — we use strings to avoid the float
        precision pitfall in the other direction.
        """
        sign = "-" if sats < 0 else ""
        sats = abs(sats)
        whole, fractional = divmod(sats, 100_000_000)
        return f"{sign}{whole}.{fractional:08d}"


__all__ = [
    "BlockchainInfo",
    "NodeAdapter",
    "NodeAuthError",
    "NodeError",
    "NodeMethodNotFound",
    "NodeRpcError",
    "NodeUnavailable",
    "ScanResult",
    "ScanUtxo",
]
