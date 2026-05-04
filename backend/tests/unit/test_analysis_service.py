"""Unit tests for the descriptor parser used by the analysis service.

The parser is regex-based and pure — these tests don't need a database.
The full analyze_holding integration is covered in
tests/integration/test_analysis_endpoints.py.
"""

from __future__ import annotations

import pytest

from tallykeep.services.analysis_service import _parse_descriptor


pytestmark = pytest.mark.unit


def test_parse_singlesig_wpkh_is_not_multisig() -> None:
    parsed = _parse_descriptor("wpkh(tpubD6.../0/*)#chk")
    assert parsed.is_multisig is False
    assert parsed.multisig_required is None
    assert parsed.multisig_total is None
    assert parsed.timelock_blocks is None


def test_parse_2_of_3_multi() -> None:
    expr = "wsh(multi(2,xpub_a,xpub_b,xpub_c))#chk"
    parsed = _parse_descriptor(expr)
    assert parsed.is_multisig is True
    assert parsed.multisig_required == 2
    assert parsed.multisig_total == 3


def test_parse_3_of_5_sortedmulti() -> None:
    expr = "wsh(sortedmulti(3,xpub_a,xpub_b,xpub_c,xpub_d,xpub_e))#chk"
    parsed = _parse_descriptor(expr)
    assert parsed.is_multisig is True
    assert parsed.multisig_required == 3
    assert parsed.multisig_total == 5


def test_parse_taproot_multi_a() -> None:
    expr = "tr(internal,{multi_a(2,xpub_a,xpub_b,xpub_c)})"
    parsed = _parse_descriptor(expr)
    assert parsed.is_multisig is True
    assert parsed.multisig_required == 2
    assert parsed.multisig_total == 3


def test_parse_older_timelock() -> None:
    expr = "wsh(and_v(v:older(144),pk(xpub_a)))"
    parsed = _parse_descriptor(expr)
    assert parsed.timelock_blocks == 144


def test_parse_after_timelock() -> None:
    expr = "wsh(and_v(v:pk(xpub_a),after(700000)))"
    parsed = _parse_descriptor(expr)
    assert parsed.timelock_blocks == 700_000


def test_parse_no_timelock_when_no_fragment() -> None:
    parsed = _parse_descriptor("wpkh(xpub_a/0/*)")
    assert parsed.timelock_blocks is None
