"""Integration tests for UTXO hygiene flag computation.

Uses a real Postgres database (the JSONB column for hygiene_flags doesn't
round-trip cleanly on SQLite, and the AddressRow / DescriptorRow / UTXORow
all have FK relations we want to exercise the same way the service runs in
production).

Each test creates a single Holding + Descriptor + Address scaffold via the
HTTP API on `app_with_db`, then constructs UTXORow objects directly and
asks the hygiene service to compute / apply flags.
"""

from __future__ import annotations

import secrets
from uuid import UUID, uuid4

import pytest

from tallykeep.domain.enums import AddressType, HygieneFlag


pytestmark = pytest.mark.integration


WPKH_REGTEST = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)


def _purse_body(*, expression: str = WPKH_REGTEST) -> dict:
    return {
        "name": f"Hygiene test {secrets.token_hex(2)}",
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
                "name": "main",
                "expression": expression,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def _seed(client) -> tuple[UUID, UUID]:  # type: ignore[no-untyped-def]
    """Return (descriptor_id, address_id) for a freshly created holding."""
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = UUID(purse["descriptor_ids"][0])
    addresses = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"]
    address_id = UUID(addresses[0]["id"])
    return descriptor_id, address_id


def _make_utxo_row(
    factory,  # type: ignore[no-untyped-def]
    *,
    descriptor_id: UUID,
    address_id: UUID,
    txid: str,
    vout: int = 0,
    value_sats: int = 100_000,
):
    from tallykeep.models import UTXORow

    with factory() as session:
        row = UTXORow(
            id=uuid4(),
            descriptor_id=descriptor_id,
            address_id=address_id,
            txid=txid,
            vout=vout,
            value_sats=value_sats,
            confirmation_height=100,
            is_frozen=False,
            is_spent=False,
            spent_in_txid=None,
            hygiene_flags=[],
        )
        session.add(row)
        session.commit()
        return row.id


# --- DUST -------------------------------------------------------------------


def test_dust_flag_set_when_value_below_threshold(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)

    utxo_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="a" * 64,
        value_sats=2_000,  # below 2040-sat threshold at 10 sat/vB, P2WPKH
    )
    with factory() as session:
        utxo = session.get(UTXORow, utxo_id)
        ctx = HygieneContext(
            address_type=AddressType.NATIVE_SEGWIT, fee_rate_sat_per_vbyte=10.0
        )
        flags = compute_flags(session, utxo=utxo, context=ctx)
    assert HygieneFlag.DUST in flags


def test_dust_flag_absent_when_value_above_threshold(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)
    utxo_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="a" * 64,
        value_sats=10_000,
    )
    with factory() as session:
        utxo = session.get(UTXORow, utxo_id)
        ctx = HygieneContext(
            address_type=AddressType.NATIVE_SEGWIT, fee_rate_sat_per_vbyte=10.0
        )
        flags = compute_flags(session, utxo=utxo, context=ctx)
    assert HygieneFlag.DUST not in flags


# --- ADDRESS_REUSED ---------------------------------------------------------


def test_no_reuse_for_first_utxo_at_address(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)
    utxo_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="a" * 64,
    )
    with factory() as session:
        utxo = session.get(UTXORow, utxo_id)
        flags = compute_flags(session, utxo=utxo, context=HygieneContext())
    assert HygieneFlag.ADDRESS_REUSED not in flags


def test_reuse_flag_when_two_txids_share_an_address(app_with_db) -> None:
    """Two distinct txids paying the same address → both UTXOs flagged
    ADDRESS_REUSED, address row is_reused = True."""
    from tallykeep.models import AddressRow, UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        apply_flags_and_propagate_reuse,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)
    first_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="a" * 64,
    )
    second_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="b" * 64,
    )
    with factory() as session:
        utxo2 = session.get(UTXORow, second_id)
        applied = apply_flags_and_propagate_reuse(
            session, utxo=utxo2, context=HygieneContext()
        )
        session.commit()

    assert HygieneFlag.ADDRESS_REUSED in applied

    with factory() as session:
        utxo1 = session.get(UTXORow, first_id)
        utxo2 = session.get(UTXORow, second_id)
        addr = session.get(AddressRow, address_id)

        assert HygieneFlag.ADDRESS_REUSED.value in (utxo1.hygiene_flags or [])
        assert HygieneFlag.ADDRESS_REUSED.value in (utxo2.hygiene_flags or [])
        assert addr.is_reused is True


def test_no_reuse_when_one_tx_pays_address_twice(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)
    same_txid = "c" * 64
    _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid=same_txid,
        vout=0,
    )
    second_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid=same_txid,
        vout=1,
    )
    with factory() as session:
        utxo2 = session.get(UTXORow, second_id)
        flags = compute_flags(session, utxo=utxo2, context=HygieneContext())
    assert HygieneFlag.ADDRESS_REUSED not in flags


# --- ROUND_NUMBER -----------------------------------------------------------


def test_round_number_for_multiples_of_100k_sats(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)
    utxo_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="d" * 64,
        value_sats=500_000,
    )
    with factory() as session:
        utxo = session.get(UTXORow, utxo_id)
        ctx = HygieneContext(decoded_tx={"vin": [], "vout": []})
        flags = compute_flags(session, utxo=utxo, context=ctx)
    assert HygieneFlag.ROUND_NUMBER in flags


def test_round_number_absent_for_non_round_values(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)
    utxo_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="d" * 64,
        value_sats=512_345,
    )
    with factory() as session:
        utxo = session.get(UTXORow, utxo_id)
        ctx = HygieneContext(decoded_tx={"vin": [], "vout": []})
        flags = compute_flags(session, utxo=utxo, context=ctx)
    assert HygieneFlag.ROUND_NUMBER not in flags


# --- SUSPECTED_CONSOLIDATION ------------------------------------------------


def test_consolidation_when_5_inputs_2_outputs_majority_ours(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)

    prev_outpoints: list[tuple[str, int]] = []
    for i in range(5):
        _make_utxo_row(
            factory,
            descriptor_id=descriptor_id,
            address_id=address_id,
            txid=f"prev{i:02d}" + "0" * 56,
            vout=0,
        )
        prev_outpoints.append((f"prev{i:02d}" + "0" * 56, 0))

    new_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="cons" + "0" * 60,
        value_sats=500_000,
    )
    consolidation_tx = {
        "vin": [{"txid": t, "vout": v} for t, v in prev_outpoints],
        "vout": [{"n": 0, "value": 0.005, "scriptPubKey": {"address": "x"}}],
    }
    with factory() as session:
        utxo = session.get(UTXORow, new_id)
        ctx = HygieneContext(decoded_tx=consolidation_tx)
        flags = compute_flags(session, utxo=utxo, context=ctx)
    assert HygieneFlag.SUSPECTED_CONSOLIDATION in flags


def test_consolidation_absent_when_inputs_not_majority_ours(app_with_db) -> None:
    from tallykeep.models import UTXORow
    from tallykeep.services.utxo_hygiene_service import (
        HygieneContext,
        compute_flags,
    )

    client, factory = app_with_db
    descriptor_id, address_id = _seed(client)

    prev_outpoints: list[tuple[str, int]] = []
    for i in range(2):
        _make_utxo_row(
            factory,
            descriptor_id=descriptor_id,
            address_id=address_id,
            txid=f"ours{i:02d}" + "0" * 56,
            vout=0,
        )
        prev_outpoints.append((f"ours{i:02d}" + "0" * 56, 0))
    for i in range(3):
        prev_outpoints.append((f"theirs{i:02d}" + "0" * 54, 0))

    new_id = _make_utxo_row(
        factory,
        descriptor_id=descriptor_id,
        address_id=address_id,
        txid="mixed" + "0" * 59,
        value_sats=500_000,
    )
    tx = {
        "vin": [{"txid": t, "vout": v} for t, v in prev_outpoints],
        "vout": [{"n": 0, "value": 0.005, "scriptPubKey": {"address": "x"}}],
    }
    with factory() as session:
        utxo = session.get(UTXORow, new_id)
        ctx = HygieneContext(decoded_tx=tx)
        flags = compute_flags(session, utxo=utxo, context=ctx)
    assert HygieneFlag.SUSPECTED_CONSOLIDATION not in flags


# --- end-to-end via the chain-scan path -------------------------------------


def test_chain_scan_applies_hygiene_flags_to_freshly_discovered_utxos(
    app_with_db_and_node,
) -> None:
    """The M5.2 rescan path attaches hygiene flags at scan time. We fund a
    watched address with a deliberately small amount so DUST triggers, run
    /rescan, and assert the persisted row carries the flag.
    """
    import time

    from tallykeep.models import UTXORow

    client, factory, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    funding_name = f"hygiene_{secrets.token_hex(4)}"
    node.create_wallet(funding_name)
    funding_addr = node.get_new_address(wallet=funding_name)
    node.generate_to_address(150, funding_addr)
    deadline = time.time() + 10.0
    while time.time() < deadline:
        previous_url = node._rpc_url
        node._rpc_url = previous_url.rstrip("/") + f"/wallet/{funding_name}"
        try:
            balance = node._call("getbalance")
        finally:
            node._rpc_url = previous_url
        if float(balance) > 0:
            break
        time.sleep(0.3)

    txid = node.send_to_address_from_wallet(funding_name, target, 1_500)
    miner = node.get_new_address(wallet=funding_name)
    node.generate_to_address(1, miner)

    rescan = client.post(f"/api/v1/descriptors/{descriptor_id}/rescan").json()
    assert rescan["utxos_discovered"] >= 1

    with factory() as session:
        rows = (
            session.query(UTXORow).filter_by(txid=txid, value_sats=1_500).all()
        )
        assert len(rows) == 1, f"expected 1 UTXO for our spend, got {rows}"
        flags = rows[0].hygiene_flags or []
        assert "dust" in flags, f"expected DUST flag, got {flags}"
