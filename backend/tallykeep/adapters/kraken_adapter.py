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
    CustodialLedgerEntry,
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


def _is_btc_currency(asset: str) -> bool:
    """True for any Kraken/ccxt code that represents Bitcoin.

    Kraken native: XXBT / XBT.  ccxt unified: BTC.
    Staking variants append ".S" (e.g. XXBT.S, XBT.S, BTC.S) — still BTC.
    """
    base = asset.split(".")[0].upper()
    return base in ("BTC", "XBT", "XXBT")


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
    observation_permission_set = frozenset({"Query funds", "Query ledger entries"})

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
    def _normalise(name: str) -> str:
        return name.lower().replace("-", "").replace(" ", "").replace("_", "").replace(":", "")

    @staticmethod
    def _is_query_funds_scope(name: str) -> bool:
        n = KrakenAdapter._normalise(name)
        return n in {"queryfunds", "funds", "querybalance"}

    @staticmethod
    def _is_query_ledger_scope(name: str) -> bool:
        n = KrakenAdapter._normalise(name)
        return n in {"queryledger", "queryledgerentries", "ledger", "data", "querydata"}

    def _parse_permissions_from_key_info(
        self, response: dict
    ) -> tuple[list[str], list[str]]:
        """Parse a GetApiKeyInfo response into (overage, underage) permission lists.

        Overage: permissions the key has that are NOT in the observation set.
        Underage: observation-set permissions the key does NOT have.

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

        has_query_funds = False
        has_query_ledger = False
        overage: list[str] = []

        if isinstance(raw_perms, list):
            for p in raw_perms:
                name = str(p)
                if self._is_query_funds_scope(name):
                    has_query_funds = True
                elif self._is_query_ledger_scope(name):
                    has_query_ledger = True
                else:
                    overage.append(name)

        elif isinstance(raw_perms, dict):
            for key, val in raw_perms.items():
                if not _flag(val):
                    continue
                if self._is_query_funds_scope(key):
                    has_query_funds = True
                elif self._is_query_ledger_scope(key):
                    has_query_ledger = True
                else:
                    overage.append(key)

        else:
            raise ValueError(f"Unrecognised permissions format: {type(raw_perms)}")

        underage: list[str] = []
        if not has_query_funds:
            underage.append("Query funds")
        if not has_query_ledger:
            underage.append("Query ledger entries")

        return overage, underage

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
        """Detect Kraken API key permissions (ADR-0011, ADR-0012).

        Returns overage (extra permissions beyond observation set) and underage
        (observation-set permissions the key is missing). Both lists can be
        non-empty simultaneously.

        Primary path: GetApiKeyInfo — direct, no side effects.
        Fallback (unrecognised response schema): endpoint probing.
        Fails closed throughout: ambiguous results raise ProviderError → 502.
        """
        # Primary: ask Kraken directly what this key can do.
        try:
            response = self._exchange.privatePostGetApiKeyInfo({})
            overage, underage = self._parse_permissions_from_key_info(response)
            logger.debug(
                "GetApiKeyInfo: overage=%r underage=%r", overage, underage
            )
        except ccxt.AuthenticationError as exc:
            raise ProviderAuthError(str(exc)) from exc
        except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
            raise ProviderError(f"Could not retrieve API key permissions: {exc}") from exc
        except ValueError:
            # Unrecognised response schema — fall back to endpoint probing.
            logger.warning("GetApiKeyInfo returned unrecognised schema; falling back to probes")
            present: list[str] = []
            self._probe(self._exchange.fetch_balance, "Query funds", present)
            self._probe(
                lambda: self._exchange.fetch_ledger("BTC", limit=1),
                "Query ledger entries",
                present,
            )
            underage = [
                p for p in ("Query funds", "Query ledger entries") if p not in present
            ]

            overage_candidates: list[str] = []
            self._probe(self._exchange.privatePostWithdrawStatus, "Withdraw funds", overage_candidates)
            self._probe(self._exchange.privatePostOpenOrders, "Trade", overage_candidates)
            self._probe(self._exchange.privatePostTradeBalance, "Margin", overage_candidates)
            self._probe(
                lambda: self._exchange.privatePostEarnStrategies({"limit": 1}),
                "Earn / Staking",
                overage_candidates,
            )
            overage = overage_candidates

        return ProviderPermissions(
            can_read="Query funds" not in underage,
            can_trade=False,
            can_withdraw=False,
            overage=overage,
            underage=underage,
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

    # Maps Kraken/ccxt kind strings to TK's CustodialLedgerKind enum values.
    # Unknown kinds fall through to 'other'; the full provider record is always
    # preserved in raw_payload regardless of the normalised kind.
    _KIND_MAP: dict[str, str] = {
        "trade": "trade",
        "deposit": "deposit",
        "withdrawal": "withdrawal",
        "fee": "fee",
        "transfer": "transfer",
        "margin": "trade",
        "rollover": "fee",
        # Staking / earn variants — Kraken uses "earn" in newer API, "staking" in older.
        # ccxt may pass either through unchanged.
        "earn": "reward",
        "staking": "reward",
        "reward": "reward",
        "dividend": "reward",
        # Kraken trade settlement legs. Kraken emits "receive" for the asset
        # credited and "spend" for the asset debited in a trade. These are
        # trade entries, not actual on-chain deposits/withdrawals.
        "receive": "trade",
        "spend": "trade",
    }

    def _normalise_kind(self, raw_kind: str, direction: str = "") -> str:
        if raw_kind == "transaction":
            return "deposit" if direction == "in" else "withdrawal"
        return self._KIND_MAP.get(raw_kind, "other")

    def fetch_ledger_since(
        self, since: datetime | None
    ) -> tuple[list[CustodialLedgerEntry], datetime | None]:
        """Fetch Kraken unified ledger entries via ccxt's fetch_ledger.

        BTC-only v1 surface:
          - Entries for non-BTC assets are dropped entirely.
          - Trade entries (Kraken emits one row per asset leg, paired by refid):
            only the BTC leg is materialised; the fiat/stable leg's raw record is
            merged into raw_payload under the key "fiat_leg_raw" so nothing is lost.
          - Unknown kinds map to 'other'.
        """
        since_ms = int(since.timestamp() * 1000) if since is not None else None
        try:
            raw = self._call(
                self._exchange.fetch_ledger, None, since_ms, 200
            ) or []
        except ProviderError:
            logger.warning("KrakenAdapter.fetch_ledger_since: fetch failed; returning empty")
            return [], since

        # Diagnostic: log currency and type breakdown so we can see what ccxt returned.
        currency_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for item in raw:
            c = str(item.get("currency") or "")
            t = str(item.get("type") or "")
            currency_counts[c] = currency_counts.get(c, 0) + 1
            type_counts[t] = type_counts.get(t, 0) + 1
        logger.info(
            "KrakenAdapter.fetch_ledger_since: %d raw entries, currencies=%s, types=%s",
            len(raw), currency_counts, type_counts,
        )

        # Group all items by refid so we can stash fiat trade legs.
        by_refid: dict[str, list[dict]] = {}
        for item in raw:
            refid = str(item.get("referenceId") or item.get("id") or "")
            by_refid.setdefault(refid, []).append(item)

        entries: list[CustodialLedgerEntry] = []
        newest_ts: datetime | None = None

        seen_refids: set[str] = set()

        for item in raw:
            refid = str(item.get("referenceId") or item.get("id") or "")
            asset = str(item.get("currency") or "")
            raw_kind = (item.get("type") or "").lower()
            direction = str(item.get("direction") or "")
            kind = self._normalise_kind(raw_kind, direction)

            # v1: only BTC entries materialise.
            # Accepts BTC / XBT / XXBT and their staking variants (e.g. XXBT.S).
            if not _is_btc_currency(asset):
                continue
            asset = "BTC"

            # For trade entries paired by refid, deduplicate: only emit once.
            if kind == "trade" and refid in seen_refids:
                continue
            seen_refids.add(refid)

            ts = _ts_to_dt(item.get("timestamp"), since or datetime(2020, 1, 1, tzinfo=UTC))
            amount = float(item.get("amount") or 0.0)
            # Normalize sign: credits are positive, debits are negative.
            # Kraken's own API uses signed amounts, but ccxt may normalise to
            # unsigned + direction="out". Guard against double-negation by only
            # applying when amount is still positive.
            if direction == "out" and amount > 0:
                amount = -amount
            # ccxt unified ledger fee is a dict {"cost": ..., "currency": ...};
            # fall back gracefully if it's a plain float or missing.
            fee_raw = item.get("fee")
            if isinstance(fee_raw, dict):
                fee: float | None = float(fee_raw.get("cost") or 0.0) or None
            elif fee_raw is not None:
                fee = float(fee_raw)
            else:
                fee = None

            # Build enriched raw payload: for trades, stash fiat legs under "fiat_leg_raw".
            enriched_raw = dict(item)
            if kind == "trade":
                fiat_legs = [
                    leg for leg in by_refid.get(refid, [])
                    if not _is_btc_currency(str(leg.get("currency") or ""))
                ]
                if fiat_legs:
                    enriched_raw["fiat_leg_raw"] = fiat_legs

            entries.append(
                CustodialLedgerEntry(
                    provider_entry_id=str(item.get("id") or refid),
                    kind=kind,
                    asset=asset,
                    amount=amount,
                    fee=fee,
                    status=str(item.get("status") or "success"),
                    timestamp=ts,
                    raw=enriched_raw,
                )
            )
            if newest_ts is None or ts > newest_ts:
                newest_ts = ts

        entries.sort(key=lambda e: e.timestamp)
        return entries, newest_ts
