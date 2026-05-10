"""ChainProcessingService — integration tests against a real Postgres.

We don't need bitcoind here: the service operates on already-decoded
transaction dicts. We hand-craft those to exercise the matrix:

  - external receive (mempool, then confirm)
  - spending one of our UTXOs (OUTGOING)
  - internal transfer between two of our holdings (INTERNAL)
  - re-running on the same tx is a no-op (idempotency)
  - tx that touches no watched address is silently ignored
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import uuid4

import pytest


pytestmark = pytest.mark.integration


WPKH_REGTEST = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)


def _purse_body(*, name: str = "main", gap_limit: int = 5) -> dict:
    return {
        "name": f"Processing test {secrets.token_hex(2)}",
        "purpose": "spending",
        "seed_origin": "external_watch_only",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": name,
                "expression": WPKH_REGTEST,
                "network": "regtest",
                "gap_limit": gap_limit,
            }
        ],
    }


def _decoded_tx(
    *,
    txid: str,
    vins: list[tuple[str, int]] | None = None,
    vouts: list[tuple[int, int, str]] | None = None,
) -> dict:
    """Build a minimal getrawtransaction-style dict.

    `vouts` is a list of (vout_index, value_sats, address) tuples.
    """
    vin_data = [{"txid": prev_txid, "vout": prev_vout} for prev_txid, prev_vout in (vins or [])]
    vout_data = [
        {
            "n": n,
            "value": value_sats / 100_000_000,
            "scriptPubKey": {"address": address},
        }
        for n, value_sats, address in (vouts or [])
    ]
    return {"txid": txid, "hex": "00" * 4, "vin": vin_data, "vout": vout_data}


def _first_address(client, descriptor_id: str) -> str:
    return client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]


def _all_addresses(client, descriptor_id: str) -> list[str]:
    rows = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=200"
    ).json()["addresses"]
    return [r["address"] for r in rows]


def test_incoming_mempool_then_confirm_creates_one_entry(app_with_db) -> None:
    """A mempool receive followed by the same tx confirming must produce a
    single LedgerEntry (with the height filled in after confirmation), not two."""
    from tallykeep.models import (
        LedgerEntryHoldingLinkRow,
        LedgerEntryRow,
        UTXORow,
    )
    from tallykeep.services.chain_processing_service import ChainProcessingService

    client, factory = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = _first_address(client, descriptor_id)

    txid = "a" * 64
    decoded = _decoded_tx(txid=txid, vouts=[(0, 50_000, target)])
    processor = ChainProcessingService()

    with factory() as session:
        result = processor.process_decoded_transaction(
            session, decoded, confirmation_height=None
        )
        session.commit()

    assert result.is_new is True
    assert len(result.discovered_utxo_ids) == 1
    assert len(result.new_ledger_entry_ids) == 1
    assert result.direction.value == "incoming"

    # Re-process the same tx as confirmed at height 200.
    with factory() as session:
        result2 = processor.process_decoded_transaction(
            session,
            decoded,
            confirmation_height=200,
            block_time=datetime(2026, 5, 3, tzinfo=UTC),
        )
        session.commit()

    # is_new=False this time; no new ledger entry; UTXO confirmation_height filled.
    assert result2.is_new is False
    assert result2.new_ledger_entry_ids == []

    with factory() as session:
        entries = session.query(LedgerEntryRow).filter_by(
            source="onchain_transaction", source_reference=txid
        ).all()
        assert len(entries) == 1, f"expected one entry, got {entries}"
        assert entries[0].direction == "incoming"
        assert entries[0].net_amount_sats == 50_000

        utxos = session.query(UTXORow).filter_by(txid=txid).all()
        assert len(utxos) == 1
        assert utxos[0].confirmation_height == 200
        assert utxos[0].is_spent is False

        links = session.query(LedgerEntryHoldingLinkRow).filter_by(
            ledger_entry_id=entries[0].id
        ).all()
        assert len(links) == 1
        assert str(links[0].holding_id) == purse["id"]


def test_outgoing_spends_known_utxo_and_emits_outgoing_entry(app_with_db) -> None:
    """Receive funds, then a follow-up tx spends them. The spend must be
    OUTGOING with the UTXO marked spent."""
    from tallykeep.models import LedgerEntryRow, UTXORow
    from tallykeep.services.chain_processing_service import ChainProcessingService

    client, factory = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = _first_address(client, descriptor_id)

    receive_txid = "b" * 64
    decoded_receive = _decoded_tx(
        txid=receive_txid, vouts=[(0, 80_000, target)]
    )
    processor = ChainProcessingService()
    with factory() as session:
        processor.process_decoded_transaction(
            session, decoded_receive, confirmation_height=100
        )
        session.commit()

    spend_txid = "c" * 64
    decoded_spend = _decoded_tx(
        txid=spend_txid,
        vins=[(receive_txid, 0)],
        vouts=[(0, 75_000, "bcrt1qexternal000000000000000000000000000xxxxxx")],
    )
    with factory() as session:
        result = processor.process_decoded_transaction(
            session, decoded_spend, confirmation_height=101
        )
        session.commit()

    assert result.direction.value == "outgoing"
    assert len(result.spent_utxo_ids) == 1
    assert result.discovered_utxo_ids == []  # external recipient

    with factory() as session:
        spent = session.query(UTXORow).filter_by(txid=receive_txid, vout=0).one()
        assert spent.is_spent is True
        assert spent.spent_in_txid == spend_txid

        entries = session.query(LedgerEntryRow).filter_by(
            source_reference=spend_txid
        ).all()
        assert len(entries) == 1
        assert entries[0].direction == "outgoing"
        assert entries[0].net_amount_sats == -80_000  # full input value left


def test_internal_transfer_between_two_holdings_emits_internal(app_with_db) -> None:
    """A tx whose inputs come from one of our holdings AND whose outputs go to
    another of our holdings is INTERNAL, with one entry per touched holding."""
    from tallykeep.models import LedgerEntryRow
    from tallykeep.services.chain_processing_service import ChainProcessingService

    client, factory = app_with_db

    # Two purses with distinct descriptors so the addresses are distinct.
    body_one = _purse_body(name="one")
    purse_one = client.post("/api/v1/holdings/purse", json=body_one).json()
    descriptor_one = purse_one["descriptor_ids"][0]
    target_one = _first_address(client, descriptor_one)

    # Use a different range of the same xpub for purse_two by varying the
    # branch index. We import a second descriptor with /1/* so addresses don't
    # collide with the first one.
    body_two = _purse_body(name="two")
    body_two["descriptors"][0]["expression"] = (
        "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/1/*)"
    )
    purse_two = client.post("/api/v1/holdings/purse", json=body_two).json()
    descriptor_two = purse_two["descriptor_ids"][0]
    target_two = _first_address(client, descriptor_two)
    assert target_one != target_two

    # 1) Fund purse_one.
    receive_txid = "d" * 64
    processor = ChainProcessingService()
    with factory() as session:
        processor.process_decoded_transaction(
            session,
            _decoded_tx(txid=receive_txid, vouts=[(0, 100_000, target_one)]),
            confirmation_height=100,
        )
        session.commit()

    # 2) Spend that UTXO into purse_two.
    transfer_txid = "e" * 64
    decoded_transfer = _decoded_tx(
        txid=transfer_txid,
        vins=[(receive_txid, 0)],
        vouts=[(0, 95_000, target_two)],
    )
    with factory() as session:
        result = processor.process_decoded_transaction(
            session, decoded_transfer, confirmation_height=101
        )
        session.commit()

    assert result.direction.value == "internal"

    with factory() as session:
        entries = session.query(LedgerEntryRow).filter_by(
            source_reference=transfer_txid
        ).all()
        # One entry per touched holding (sender + receiver).
        assert len(entries) == 2
        assert all(e.direction == "internal" for e in entries)


def test_unwatched_tx_is_a_no_op(app_with_db) -> None:
    """A tx whose inputs and outputs are entirely external must persist no
    UTXO and create no LedgerEntry."""
    from tallykeep.models import LedgerEntryRow, UTXORow
    from tallykeep.services.chain_processing_service import ChainProcessingService

    client, factory = app_with_db
    client.post("/api/v1/holdings/purse", json=_purse_body()).json()

    txid = "f" * 64
    decoded = _decoded_tx(
        txid=txid,
        vouts=[(0, 12_345, "bcrt1qexternal000000000000000000000000000xxxxxx")],
    )
    processor = ChainProcessingService()
    with factory() as session:
        result = processor.process_decoded_transaction(
            session, decoded, confirmation_height=42
        )
        session.commit()

    assert result.discovered_utxo_ids == []
    assert result.new_ledger_entry_ids == []

    with factory() as session:
        assert session.query(UTXORow).filter_by(txid=txid).count() == 0
        assert (
            session.query(LedgerEntryRow).filter_by(source_reference=txid).count() == 0
        )
