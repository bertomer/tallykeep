"""Kraken CustodialProviderAdapter — spec module 07 first-class provider.

Uses ccxt's synchronous Kraken exchange class. Credentials are the ccxt
standard (api_key + secret). Kraken does not use a passphrase.

Permission detection: primary path is privatePostGetApiKeyInfo (ccxt 4.5+),
which returns the key's permission set directly without probing.
Fallback path (unrecognised schema): probe read-only endpoints per category.
All Kraken private endpoints use HTTP POST → ccxt privatePost* prefix.
Fails closed: any ambiguous result raises ProviderError → 502.

Whitelist verification: privatePostWithdrawAddresses (XBT asset).
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

    adapter_slug = "kraken"
    display_name = "Kraken"
    supports_withdrawal_keys = True
    whitelist_read_api = True  # Kraken exposes privatePostWithdrawAddresses

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
        except ValueError as exc:
            # Covers binascii.Error (invalid base64 secret), etc. — treat as bad credentials.
            raise ProviderAuthError(f"Invalid credentials format: {exc}") from exc

    @staticmethod
    def _is_read_scope(name: str) -> bool:
        """True for the Query Funds scope (the only one we accept)."""
        n = name.lower().replace("-", "").replace(" ", "").replace("_", "")
        return n in {"queryfunds", "funds", "querybalance"}

    def _parse_permissions_from_key_info(self, response: dict) -> list[str]:
        """Return raw Kraken permission strings from a GetApiKeyInfo response.

        Returns ALL permissions except Query Funds verbatim — no label mapping.
        This ensures the danger band shows every permission the key has, even
        ones we don't recognise, and avoids collapsing many permissions to one.

        Handles three formats Kraken may return:
          Format A: list         ["query-funds", "create-orders", "cancel-orders"]
          Format B: flat dict    {"query-funds": True, "create-orders": True}
          Format C: nested dict  {"funds": {"query": True}, "orders": {"create": True}}

        Raises ValueError if the structure is unrecognised → caller falls back
        to endpoint probing.
        """
        result = response.get("result", response)
        if not isinstance(result, dict):
            raise ValueError(f"Unexpected GetApiKeyInfo result type: {type(result)}")

        raw_perms = result.get("permissions")
        if raw_perms is None:
            raise ValueError("No 'permissions' key in GetApiKeyInfo result")

        logger.debug("GetApiKeyInfo raw permissions: %r", raw_perms)

        def _flag(obj: object) -> bool:
            if isinstance(obj, bool):
                return obj
            if isinstance(obj, dict):
                return any(_flag(v) for v in obj.values())
            return False

        extra: list[str] = []

        if isinstance(raw_perms, list):
            extra = [str(p) for p in raw_perms if not self._is_read_scope(str(p))]

        elif isinstance(raw_perms, dict):
            for key, val in raw_perms.items():
                if not self._is_read_scope(key) and _flag(val):
                    extra.append(key)

        else:
            raise ValueError(f"Unrecognised permissions format: {type(raw_perms)}")

        return extra

    def _probe(self, fn, permission_name: str, extra: list[str]) -> None:
        """Fail-closed permission probe: success → present, AuthenticationError
        → absent, anything else → ProviderError (caller surfaces as 502).

        All Kraken private endpoints use HTTP POST; ccxt method names therefore
        use the privatePost* prefix (not privateGet*).
        """
        try:
            fn()
            extra.append(permission_name)
        except ccxt.AuthenticationError:
            pass
        except (ccxt.NetworkError, ccxt.RateLimitExceeded) as exc:
            raise ProviderError(
                f"Could not verify '{permission_name}' permission (network error): {exc}"
            ) from exc
        except ccxt.ExchangeError as exc:
            raise ProviderError(
                f"Could not verify '{permission_name}' permission (exchange error): {exc}"
            ) from exc

    def get_permissions(self) -> ProviderPermissions:
        """Detect Kraken API key permissions (2-key model, ADR-0011).

        Primary path: GetApiKeyInfo — direct query, no side effects.
        Fallback (unrecognised response schema): read-only endpoint probing.
        Fails closed throughout: ambiguous results raise ProviderError → 502.
        """
        # Confirm read access first (Query Funds — minimum required).
        self._call(self._exchange.fetch_balance)

        # Primary: ask Kraken directly what this key can do.
        try:
            response = self._exchange.privatePostGetApiKeyInfo({})
            extra = self._parse_permissions_from_key_info(response)
            logger.debug("GetApiKeyInfo detected extra permissions: %r", extra)
        except (ccxt.AuthenticationError, ccxt.NetworkError, ccxt.ExchangeError) as exc:
            raise ProviderError(f"Could not retrieve API key permissions: {exc}") from exc
        except ValueError:
            # Unrecognised response schema — fall back to endpoint probing.
            logger.warning("GetApiKeyInfo returned unrecognised schema; falling back to probes")
            extra = []
            self._probe(self._exchange.privatePostWithdrawStatus, "Withdraw funds", extra)
            self._probe(self._exchange.privatePostOpenOrders, "Trade", extra)
            self._probe(self._exchange.privatePostTradeBalance, "Margin", extra)
            self._probe(
                lambda: self._exchange.privatePostEarnStrategies({"limit": 1}),
                "Earn / Staking",
                extra,
            )

        return ProviderPermissions(
            can_read=True,
            can_trade=False,
            can_withdraw=False,
            detected_extra_permissions=extra,
        )

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
        """Check Kraken's withdrawal address book (XBT asset)."""
        try:
            data = self._exchange.privatePostWithdrawAddresses({"asset": "XBT"})
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
