"""Configuration service.

Translates between the flat dotted-key storage in `runtime_configuration` and the
nested API shape defined by `ConfigurationResponse` / `ConfigurationUpdate`. Only
the sections defined in `ConfigurationResponse` are accepted; unknown sections
are rejected by Pydantic at the API boundary.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from tallykeep.repositories import runtime_configuration as repo
from tallykeep.schemas.configuration import (
    AnalysisConfiguration,
    BitcoindConfiguration,
    ConfigurationResponse,
    ConfigurationUpdate,
    CustodialPollingConfiguration,
    FeeEstimationConfiguration,
    NotificationsConfiguration,
)


# Reverse map: section name → Pydantic model class. Iterated when reading and
# writing so adding a new section needs only a single line here.
_SECTION_MODELS: dict[str, type] = {
    "bitcoind": BitcoindConfiguration,
    "fee_estimation": FeeEstimationConfiguration,
    "custodial_polling": CustodialPollingConfiguration,
    "analysis": AnalysisConfiguration,
    "notifications": NotificationsConfiguration,
}


def _flat_to_section_dict(flat: dict[str, Any], section: str) -> dict[str, Any]:
    """Pull `<section>.<field>` keys out of `flat` and return them as `{field: value}`."""
    prefix = f"{section}."
    result: dict[str, Any] = {}
    for key, value in flat.items():
        if key.startswith(prefix):
            result[key[len(prefix):]] = value
    return result


def get_configuration(session: Session) -> ConfigurationResponse:
    """Build the full nested response from whatever's persisted."""
    flat = repo.list_all(session)
    sections: dict[str, Any] = {}
    for section, model_cls in _SECTION_MODELS.items():
        section_data = _flat_to_section_dict(flat, section)
        # model_cls(**{}) is a model with all-None fields by construction.
        sections[section] = model_cls(**section_data)
    return ConfigurationResponse(**sections)


def patch_configuration(
    session: Session, update: ConfigurationUpdate
) -> ConfigurationResponse:
    """Apply a partial update and return the new full configuration.

    Spec module 04 PATCH semantics: only the keys present in the body change.
    Setting a field to None inside an explicit section is currently treated as
    "no change" — explicit deletion is a v1.x concern (no DELETE endpoint yet).
    """
    items_to_upsert: dict[str, Any] = {}
    update_dict = update.model_dump(exclude_unset=True)

    for section, model_cls in _SECTION_MODELS.items():
        if section not in update_dict:
            continue
        section_payload = update_dict[section] or {}
        # Only persist fields the caller explicitly set in the section payload.
        for field, value in section_payload.items():
            if value is None:
                continue
            items_to_upsert[f"{section}.{field}"] = value

    if items_to_upsert:
        repo.upsert_many(session, items_to_upsert)

    return get_configuration(session)


__all__ = ["get_configuration", "patch_configuration"]
