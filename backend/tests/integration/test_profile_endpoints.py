"""Integration tests for /api/v1/profile and /api/v1/feature-flags."""

from __future__ import annotations

import pytest

from tallykeep.domain.enums import ProfilePreset
from tallykeep.services.profile_presets import ALL_FEATURE_FLAGS, PROFILE_PRESETS


pytestmark = pytest.mark.integration


# --- /api/v1/profile ------------------------------------------------------------


def test_get_profile_creates_singleton_on_first_call(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    response = client.get("/api/v1/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "00000000-0000-0000-0000-000000000001"
    assert body["preset"] == "intermediate"  # default per spec module 11
    assert body["base_currency"] == "EUR"
    assert body["locale"] == "en"
    assert body["feature_flags"] == {}


def test_get_profile_idempotent(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    first = client.get("/api/v1/profile").json()
    second = client.get("/api/v1/profile").json()
    assert first["id"] == second["id"]
    assert first["preset"] == second["preset"]


def test_patch_profile_updates_preset(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    client.get("/api/v1/profile")  # ensure singleton exists

    response = client.patch("/api/v1/profile", json={"preset": "sovereign"})
    assert response.status_code == 200
    assert response.json()["preset"] == "sovereign"

    # Persists across reads.
    assert client.get("/api/v1/profile").json()["preset"] == "sovereign"


def test_patch_profile_updates_overrides(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/profile",
        json={"feature_flags": {"banking.psbt_qr.enabled": True}},
    )
    assert response.status_code == 200
    assert response.json()["feature_flags"] == {"banking.psbt_qr.enabled": True}


def test_patch_profile_updates_base_currency_and_locale(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/profile", json={"base_currency": "USD", "locale": "en-US"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["base_currency"] == "USD"
    assert body["locale"] == "en-US"


def test_patch_profile_rejects_three_letter_invalid_currency(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    # base_currency length 4 is rejected by the Pydantic schema (max_length=3).
    response = client.patch(
        "/api/v1/profile", json={"base_currency": "EURO"}
    )
    assert response.status_code == 422


def test_patch_profile_rejects_invalid_preset(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/profile", json={"preset": "definitely-not-a-preset"}
    )
    assert response.status_code == 422


def test_patch_profile_rejects_empty_body(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    response = client.patch("/api/v1/profile", json={})
    assert response.status_code == 422


# --- /api/v1/feature-flags ------------------------------------------------------


def test_feature_flags_default_is_intermediate_preset(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.get("/api/v1/feature-flags")
    assert response.status_code == 200
    flags = response.json()["flags"]
    assert flags == PROFILE_PRESETS[ProfilePreset.INTERMEDIATE]


def test_feature_flags_reflect_preset_change(app_with_db) -> None:  # type: ignore[no-untyped-def]
    client, _ = app_with_db
    client.patch("/api/v1/profile", json={"preset": "beginner"})
    flags = client.get("/api/v1/feature-flags").json()["flags"]
    assert flags == PROFILE_PRESETS[ProfilePreset.BEGINNER]


def test_feature_flags_apply_overrides_on_top_of_preset(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    # Override one flag explicitly while staying on Intermediate.
    client.patch(
        "/api/v1/profile",
        json={"feature_flags": {"banking.rbf.enabled": True}},
    )
    flags = client.get("/api/v1/feature-flags").json()["flags"]
    # Intermediate has banking.rbf.enabled = False; override flips it.
    assert flags["banking.rbf.enabled"] is True
    # Other Intermediate-specific flags untouched.
    assert flags["holding.strongbox.enabled"] is True


def test_feature_flags_response_covers_all_known_flags(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    flags = client.get("/api/v1/feature-flags").json()["flags"]
    assert set(flags.keys()) == set(ALL_FEATURE_FLAGS)
