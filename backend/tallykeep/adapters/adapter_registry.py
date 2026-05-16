"""Adapter registry — maps adapter_id to the concrete CustodialProviderAdapter class.

This is the only place that imports concrete adapter classes. The rest of the
code depends on the CustodialProviderAdapter ABC.
"""

from __future__ import annotations

from tallykeep.adapters.bitstamp_adapter import BitstampAdapter
from tallykeep.adapters.custodial_provider_adapter import CustodialProviderAdapter
from tallykeep.adapters.kraken_adapter import KrakenAdapter


_REGISTRY: dict[str, type[CustodialProviderAdapter]] = {
    "kraken": KrakenAdapter,
    "bitstamp": BitstampAdapter,
}

SUPPORTED_ADAPTER_IDS: list[str] = sorted(_REGISTRY.keys())


class UnsupportedAdapterError(ValueError):
    """Raised when an adapter_id is not in the registry."""


def list_provider_capabilities() -> list[dict]:
    """Return the capability matrix for all registered adapters.

    Result is sorted by adapter_slug for stable ordering. Used by
    GET /api/v1/treasury/providers to populate the wizard's provider dropdown
    and gate Step 3's suggestion card.
    """
    return [
        {
            "slug": slug,
            "display_name": cls.display_name,
            "supports_withdrawal_keys": cls.supports_withdrawal_keys,
            "whitelist_read_api": cls.whitelist_read_api,
        }
        for slug, cls in sorted(_REGISTRY.items())
    ]


def build_adapter(
    adapter_id: str,
    *,
    api_key: str,
    api_secret: str,
    api_passphrase: str | None = None,
) -> CustodialProviderAdapter:
    """Instantiate and return the adapter for the given provider.

    Raises UnsupportedAdapterError for unknown adapter_ids.
    """
    cls = _REGISTRY.get(adapter_id)
    if cls is None:
        raise UnsupportedAdapterError(
            f"Unsupported adapter {adapter_id!r}. "
            f"Supported: {', '.join(SUPPORTED_ADAPTER_IDS)}"
        )
    return cls(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)


__all__ = [
    "SUPPORTED_ADAPTER_IDS",
    "UnsupportedAdapterError",
    "build_adapter",
    "list_provider_capabilities",
]
