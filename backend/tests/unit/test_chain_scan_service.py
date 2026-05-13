"""Unit tests for ChainScanService resilience added in the Purse-wizard iteration.

Covers two new behaviours:

  1. NodeRpcError (descriptor rejected by the node — e.g. a mainnet xpub
     submitted to a regtest bitcoind) is caught per-branch and does not
     propagate as a 503. The scan settles with height ≥ 1 so that
     scan_status in the global summary transitions from "scanning" to
     "scanned".

  2. height_at_scan = 0 (genesis / node returns no blocks yet) still
     marks last_scanned_height ≥ 1 via the max(..., 1) sentinel so
     descriptors on a brand-new regtest node are not stuck "scanning".

  NodeUnavailable (actual connectivity failure) must still propagate to
  the endpoint layer so the caller gets a proper 503.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from tallykeep.adapters.node_adapter import NodeRpcError, NodeUnavailable, ScanResult
from tallykeep.services.chain_scan_service import ChainScanService


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _descriptor(*, change_expression: str | None = None) -> MagicMock:
    """Minimal descriptor mock — only the attributes accessed by initial_scan."""
    d = MagicMock()
    d.id = uuid4()
    d.holding_id = uuid4()
    d.expression = "wpkh(tpub.../0/*)"
    d.change_expression = change_expression
    return d


def _session(initial_height: int = 0) -> tuple[MagicMock, MagicMock]:
    """Return (session, descriptor_row_stub).

    Address query returns an empty list (tests focus on scan-level logic,
    not UTXO persistence — that's covered by test_chain_scan.py integration
    tests).
    """
    session = MagicMock()
    session.execute.return_value.scalars.return_value = []
    desc_row = MagicMock()
    desc_row.last_scanned_height = initial_height
    session.get.return_value = desc_row
    return session, desc_row


def _scan_empty(height: int = 105) -> ScanResult:
    return ScanResult(success=True, height_at_scan=height, total_amount_sats=0, utxos=[])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNodeRpcErrorHandling:
    """NodeRpcError per-branch: swallowed, scan_status settles to 'scanned'."""

    def test_does_not_propagate(self) -> None:
        node = MagicMock()
        node.scan_descriptors.side_effect = NodeRpcError(
            code=-5, message="Invalid descriptor"
        )
        session, _ = _session()

        # Must not raise.
        report = ChainScanService(node).initial_scan(session, _descriptor())
        assert report.utxos_discovered == 0

    def test_marks_descriptor_scanned(self) -> None:
        node = MagicMock()
        node.scan_descriptors.side_effect = NodeRpcError(
            code=-5, message="Invalid descriptor"
        )
        session, desc_row = _session(initial_height=0)

        ChainScanService(node).initial_scan(session, _descriptor())

        assert desc_row.last_scanned_height >= 1

    def test_report_height_is_positive(self) -> None:
        node = MagicMock()
        node.scan_descriptors.side_effect = NodeRpcError(
            code=-5, message="Invalid descriptor"
        )
        session, _ = _session()

        report = ChainScanService(node).initial_scan(session, _descriptor())

        assert report.height_at_scan >= 1

    def test_change_branch_rpc_error_also_handled(self) -> None:
        """NodeRpcError on the change branch (second call) is also swallowed."""
        node = MagicMock()
        # External branch succeeds; change branch raises.
        node.scan_descriptors.side_effect = [
            _scan_empty(50),
            NodeRpcError(code=-5, message="change branch invalid"),
        ]
        session, desc_row = _session(initial_height=0)
        d = _descriptor(change_expression="wpkh(xpub.../1/*)")

        report = ChainScanService(node).initial_scan(session, d)

        assert report.height_at_scan >= 50
        assert desc_row.last_scanned_height >= 50


class TestGenesisSentinel:
    """height_at_scan=0 (genesis) must still mark the descriptor as scanned."""

    def test_genesis_height_sets_sentinel(self) -> None:
        node = MagicMock()
        node.scan_descriptors.return_value = _scan_empty(height=0)
        session, desc_row = _session(initial_height=0)

        report = ChainScanService(node).initial_scan(session, _descriptor())

        assert report.height_at_scan >= 1
        assert desc_row.last_scanned_height >= 1

    def test_normal_height_recorded_faithfully(self) -> None:
        """When the node reports a real height, that height is stored as-is."""
        node = MagicMock()
        node.scan_descriptors.return_value = _scan_empty(height=105)
        session, desc_row = _session(initial_height=0)

        report = ChainScanService(node).initial_scan(session, _descriptor())

        assert report.height_at_scan == 105
        assert desc_row.last_scanned_height == 105


class TestNodeUnavailableStillPropagates:
    """Real connectivity failures must reach the endpoint layer."""

    def test_unavailable_raises(self) -> None:
        node = MagicMock()
        node.scan_descriptors.side_effect = NodeUnavailable("connection refused")
        session, _ = _session()

        with pytest.raises(NodeUnavailable):
            ChainScanService(node).initial_scan(session, _descriptor())
