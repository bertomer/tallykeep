"""Kraken CustodialProviderAdapter — spec module 07 first-class provider.

Uses ccxt's synchronous Kraken exchange class. Credentials are the ccxt
standard (api_key + secret). Kraken does not use a passphrase.

Permission detection: Kraken's API doesn't expose a "list my key scopes"
endpoint. We infer:
  - can_read=True  by successfully calling fetch_balance (requires Query Funds).
  - can_trade=True by successfully calling privateGetOpenOrders (requires
    Query Open Orders & Trades — typically paired with Create & Modify Orders).
  - can_withdraw=True assumed if read succeeds (caller creates key with withdraw
    scope and we trust their intent; a failed withdraw() call surfaces the error).

Whitelist verification: Kraken exposes privateGetWithdrawAddresses (XBT asset).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import ccxt

from tallykeep.adapters.custodial_provider_adapter import (
    CustodialProviderAdapter,
    Deposit,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    WhitelistVerification,
    Withdrawal,
    WithdrawalResult,
)
from tallykeep.domain.custodial_provider import ProviderPermissions


logger = logging.getLogger(__name__)

_BTC_SATS = 100_000_000


def _btc_to_sats(btc: float | str | None) -> int:
    if btc is None:
        return 0
    return round(float(btc) * _BTC_SATS)


def _ts_to_dt(ts_ms: int | None, fallback: datetime) -> datetime:
    if ts_ms is None:
        return fallback
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC)


class KrakenAdapter(CustodialProviderAdapter):
    """ccxt-backed Kraken adapter (spec module 07)."""

    def __init__(self, api_key: str, api_secret: str, api_passphrase: str | None = None) -> None:
        self._exchange: ccxt.kraken = ccxt.kraken(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )

    def _call(self, fn, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return fn(*args, **kwargs)
        except ccxt.AuthenticationError as exc:
            raise ProviderAuthError(str(exc)) from exc
        except ccxt.RateLimitExceeded as exc:
            raise ProviderRateLimitError(str(exc)) from exc
        except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
            raise ProviderError(str(exc)) from exc

    def get_permissions(self) -> ProviderPermissions:
        # Verify read access — raises ProviderAuthError if the key is invalid.
        self._call(self._exchange.fetch_balance)

        # Infer trade scope: Kraken pairs "Query Open Orders" with trade permissions.
        # If this succeeds, the key almost certainly has Create & Modify Orders too.
        can_trade = False
        try:
            self._exchange.privateGetOpenOrders()
            can_trade = True
        except ccxt.AuthenticationError:
            can_trade = False
        except Exception:  # noqa: BLE001 — network errors mean we can't confirm
            can_trade = False

        return ProviderPermissions(can_read=True, can_trade=can_trade, can_withdraw=True)

    def get_balance(self) -> int:
        balances = self._call(self._exchange.fetch_balance)
        free = (balances.get("BTC") or {}).get("free") or 0.0
        return _btc_to_sats(free)

    def get_other_balances(self) -> dict[str, str]:
        balances = self._call(self._exchange.fetch_balance)
        totals: dict = balances.get("total") or {}
        return {
            asset: str(amount)
            for asset, amount in totals.items()
            if asset != "BTC" and amount and float(amount) > 0
        }

    def get_recent_withdrawals(self, since: datetime) -> list[Withdrawal]:
        since_ms = int(since.timestamp() * 1000)
        txs = self._call(
            self._exchange.fetch_transactions, "BTC", since_ms, 50, {"type": "withdrawal"}
        ) or []
        return [
            Withdrawal(
                id=tx.get("id", ""),
                amount_sats=_btc_to_sats(tx.get("amount")),
                address=tx.get("address", ""),
                txid=tx.get("txid"),
                status=tx.get("status", "unknown"),
                created_at=_ts_to_dt(tx.get("timestamp"), since),
            )
            for tx in txs
        ]

    def get_recent_deposits(self, since: datetime) -> list[Deposit]:
        since_ms = int(since.timestamp() * 1000)
        txs = self._call(
            self._exchange.fetch_transactions, "BTC", since_ms, 50, {"type": "deposit"}
        ) or []
        return [
            Deposit(
                id=tx.get("id", ""),
                amount_sats=_btc_to_sats(tx.get("amount")),
                txid=tx.get("txid"),
                status=tx.get("status", "unknown"),
                created_at=_ts_to_dt(tx.get("timestamp"), since),
            )
            for tx in txs
        ]

    def withdraw(self, amount_sats: int, address: str) -> WithdrawalResult:
        amount_btc = amount_sats / _BTC_SATS
        result = self._call(self._exchange.withdraw, "BTC", amount_btc, address)
        return WithdrawalResult(
            withdrawal_id=result.get("id", ""),
            status=result.get("status", "pending"),
        )

    def verify_whitelist(self, address: str) -> WhitelistVerification:
        """Check Kraken's withdrawal address book (XBT asset).

        Kraken exposes privateGetWithdrawAddresses which lists saved addresses.
        """
        try:
            data = self._exchange.privateGetWithdrawAddresses({"asset": "XBT"})
            entries = data.get("result") or []
            for entry in entries:
                if entry.get("address") == address:
                    return WhitelistVerification(
                        is_whitelisted=True,
                        provider_label=entry.get("key"),
                    )
            return WhitelistVerification(is_whitelisted=False)
        except (ccxt.AuthenticationError, ccxt.ExchangeError) as exc:
            return WhitelistVerification(is_whitelisted=False, error=str(exc))
