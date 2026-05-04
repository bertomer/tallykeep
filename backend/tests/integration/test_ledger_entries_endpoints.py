"""Integration tests for /api/v1/ledger-entries.

Covers the four real endpoints (list / get / patch / pending-categorization)
plus a quick exercise of the categorizer suggestion subscriber.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tallykeep.domain.enums import (
    Direction,
    LedgerCategory,
    LedgerEntrySource,
)
from tallykeep.domain.ledger_entry import LedgerEntry, LedgerEntryHoldingLink
from tallykeep.repositories import ledger_entry as ledger_repo


pytestmark = pytest.mark.integration


WPKH_REGTEST = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)


_BRANCH_INDEX = {"next": 0}
_BASE_XPUB = (
    "tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK"
)


def _next_descriptor() -> str:
    """Each call returns a fresh, unique descriptor expression by walking the
    branch index up. Two purses in the same test must NOT share an
    expression — the unique constraint on `descriptor.expression` would
    otherwise reject the second insert with 409."""
    idx = _BRANCH_INDEX["next"]
    _BRANCH_INDEX["next"] += 1
    return f"wpkh({_BASE_XPUB}/{idx}/*)"


def _purse_body(*, expression: str | None = None) -> dict:
    expr = expression or _next_descriptor()
    return {
        "name": f"Ledger test {secrets.token_hex(2)}",
        "purpose": "spending",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": expr,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def _make_entry(
    factory,  # type: ignore[no-untyped-def]
    *,
    holding_id,  # type: ignore[no-untyped-def]
    direction: Direction,
    net_amount_sats: int,
    txid: str,
    suggested: LedgerCategory | None = None,
):
    entry_id = uuid4()
    entry = LedgerEntry(
        id=entry_id,
        direction=direction,
        net_amount_sats=net_amount_sats,
        fee_sats=None,
        timestamp=datetime.now(UTC),
        source=LedgerEntrySource.ONCHAIN_TRANSACTION,
        source_reference=txid,
        category=None,
        counterparty_label=None,
        note=None,
        suggested_category=suggested,
        categorized_at=None,
        created_at=datetime.now(UTC),
    )
    with factory() as session:
        ledger_repo.insert(
            session,
            entry,
            holding_links=[
                LedgerEntryHoldingLink(
                    ledger_entry_id=entry_id,
                    holding_id=holding_id,
                    holding_amount_sats=net_amount_sats,
                )
            ],
        )
        session.commit()
    return entry_id


def _holding_id(client) -> str:  # type: ignore[no-untyped-def]
    return client.post("/api/v1/holdings/purse", json=_purse_body()).json()["id"]


# --- list / get / pending --------------------------------------------------


def test_list_returns_recent_entries(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    _make_entry(
        factory,
        holding_id=holding_id,
        direction=Direction.INCOMING,
        net_amount_sats=10_000,
        txid="a" * 64,
    )
    res = client.get("/api/v1/ledger-entries").json()
    assert any(
        e["source_reference"] == "a" * 64 and e["net_amount_sats"] == 10_000
        for e in res["entries"]
    )


def test_list_filters_by_holding(app_with_db) -> None:
    client, factory = app_with_db
    h1 = _holding_id(client)
    h2 = _holding_id(client)
    _make_entry(
        factory, holding_id=h1, direction=Direction.INCOMING,
        net_amount_sats=1_000, txid="b" * 64,
    )
    _make_entry(
        factory, holding_id=h2, direction=Direction.INCOMING,
        net_amount_sats=2_000, txid="c" * 64,
    )
    res = client.get(f"/api/v1/ledger-entries?holding_id={h1}").json()
    txids = {e["source_reference"] for e in res["entries"]}
    assert "b" * 64 in txids
    assert "c" * 64 not in txids


def test_list_filters_by_direction(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    _make_entry(
        factory, holding_id=holding_id, direction=Direction.INCOMING,
        net_amount_sats=1, txid="d" * 64,
    )
    _make_entry(
        factory, holding_id=holding_id, direction=Direction.OUTGOING,
        net_amount_sats=-1, txid="e" * 64,
    )
    res = client.get("/api/v1/ledger-entries?direction=outgoing").json()
    assert all(e["direction"] == "outgoing" for e in res["entries"])
    refs = {e["source_reference"] for e in res["entries"]}
    assert "e" * 64 in refs


def test_list_filters_uncategorized_only(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    pending_id = _make_entry(
        factory, holding_id=holding_id, direction=Direction.INCOMING,
        net_amount_sats=100, txid="f" * 64,
    )
    categorized_id = _make_entry(
        factory, holding_id=holding_id, direction=Direction.INCOMING,
        net_amount_sats=200, txid="9" * 64,
    )
    # Categorize the second one through the API.
    resp = client.patch(
        f"/api/v1/ledger-entries/{categorized_id}",
        json={"category": "salary"},
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "salary"
    assert resp.json()["categorized_at"] is not None

    res = client.get("/api/v1/ledger-entries?uncategorized=true").json()
    ids = {e["id"] for e in res["entries"]}
    assert str(pending_id) in ids
    assert str(categorized_id) not in ids


def test_pending_categorization_endpoint(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    eid = _make_entry(
        factory, holding_id=holding_id, direction=Direction.INCOMING,
        net_amount_sats=42, txid="1" * 64,
    )
    res = client.get("/api/v1/ledger-entries/pending-categorization").json()
    assert any(e["id"] == str(eid) for e in res["entries"])


def test_get_entry_returns_holdings_links(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    eid = _make_entry(
        factory, holding_id=holding_id, direction=Direction.INCOMING,
        net_amount_sats=500, txid="2" * 64,
    )
    res = client.get(f"/api/v1/ledger-entries/{eid}").json()
    assert res["holdings"][0]["holding_id"] == holding_id
    assert res["holdings"][0]["holding_amount_sats"] == 500


def test_get_entry_404(app_with_db) -> None:
    client, _ = app_with_db
    response = client.get(
        "/api/v1/ledger-entries/00000000-0000-0000-0000-0000000000ff"
    )
    assert response.status_code == 404


# --- patch ------------------------------------------------------------------


def test_patch_sets_category_and_categorized_at(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    eid = _make_entry(
        factory, holding_id=holding_id, direction=Direction.OUTGOING,
        net_amount_sats=-12_345, txid="3" * 64,
    )
    res = client.patch(
        f"/api/v1/ledger-entries/{eid}",
        json={"category": "merchant_payment", "note": "Coffee"},
    ).json()
    assert res["category"] == "merchant_payment"
    assert res["note"] == "Coffee"
    assert res["categorized_at"] is not None


def test_patch_with_invalid_category_returns_400(app_with_db) -> None:
    client, factory = app_with_db
    holding_id = _holding_id(client)
    eid = _make_entry(
        factory, holding_id=holding_id, direction=Direction.OUTGOING,
        net_amount_sats=-1, txid="4" * 64,
    )
    response = client.patch(
        f"/api/v1/ledger-entries/{eid}",
        json={"category": "not_a_real_category"},
    )
    assert response.status_code == 400


def test_patch_404_when_entry_missing(app_with_db) -> None:
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/ledger-entries/00000000-0000-0000-0000-0000000000fe",
        json={"category": "salary"},
    )
    assert response.status_code == 404


# --- categorizer suggestions -----------------------------------------------


def test_categorizer_suggests_internal_transfer_for_internal_entry(
    app_with_db,
) -> None:
    """Spec heuristic 1: direction == INTERNAL → suggest INTERNAL_TRANSFER."""
    from tallykeep.services.categorizer_service import suggest_category

    client, factory = app_with_db
    h1 = _holding_id(client)
    h2 = _holding_id(client)

    # An INTERNAL entry must touch ≥2 holdings to be valid (spec invariant 3),
    # so we link both.
    entry_id = uuid4()
    entry = LedgerEntry(
        id=entry_id,
        direction=Direction.INTERNAL,
        net_amount_sats=0,
        fee_sats=300,
        timestamp=datetime.now(UTC),
        source=LedgerEntrySource.ONCHAIN_TRANSACTION,
        source_reference="cafe" + "0" * 60,
        category=None,
        counterparty_label=None,
        note=None,
        suggested_category=None,
        categorized_at=None,
        created_at=datetime.now(UTC),
    )
    with factory() as session:
        ledger_repo.insert(
            session,
            entry,
            holding_links=[
                LedgerEntryHoldingLink(
                    ledger_entry_id=entry_id,
                    holding_id=h1,
                    holding_amount_sats=-1_000,
                ),
                LedgerEntryHoldingLink(
                    ledger_entry_id=entry_id,
                    holding_id=h2,
                    holding_amount_sats=900,
                ),
            ],
        )
        session.commit()

        suggestion = suggest_category(session, entry_id)
        session.commit()

    assert suggestion == LedgerCategory.INTERNAL_TRANSFER

    # And the suggestion is now visible via the API.
    res = client.get(f"/api/v1/ledger-entries/{entry_id}").json()
    assert res["suggested_category"] == "internal_transfer"


def test_categorizer_is_idempotent(app_with_db) -> None:
    """A second call doesn't overwrite the suggestion."""
    from tallykeep.services.categorizer_service import suggest_category

    client, factory = app_with_db
    holding_id = _holding_id(client)
    eid = _make_entry(
        factory, holding_id=holding_id, direction=Direction.INTERNAL,
        net_amount_sats=0, txid="5" * 64,
    )

    # First run sets the suggestion (note: this test entry has only one
    # holding link, but the categorizer doesn't enforce the >=2 invariant —
    # it only cares about the direction enum).
    with factory() as session:
        first = suggest_category(session, eid)
        session.commit()
    assert first == LedgerCategory.INTERNAL_TRANSFER

    # Second run is a no-op.
    with factory() as session:
        second = suggest_category(session, eid)
        session.commit()
    assert second == LedgerCategory.INTERNAL_TRANSFER
