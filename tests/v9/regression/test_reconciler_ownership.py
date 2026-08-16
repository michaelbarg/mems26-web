"""Phase 7.1 AC — RECONCILER_OWNERSHIP_AWARE_V1: manual positions are not orphans.

Mixed account: Michael trades manually alongside the system. When Sierra shows
a position but TM=0 and the fill_poller order_map is empty (no system orders),
the position is manual → INFO only, not NAKED ORPHAN.

If reverted → RED because the reconciler screams CRITICAL NAKED ORPHAN on every
manual position, triggering alerts + auto-stop attempts on Michael's trades.
"""

import os
import pytest
from unittest.mock import MagicMock, patch


def _make_tm(active_trades=None):
    """Mock TradeManager with no active trades."""
    tm = MagicMock()
    tm.get_active_trades.return_value = active_trades or []
    return tm


def test_manual_position_info_not_orphan(monkeypatch, tmp_path):
    """Sierra=-5 + TM=0 + empty order_map → manual position, ok=True."""
    monkeypatch.setenv("RECONCILER_OWNERSHIP_AWARE_V1", "1")

    import json
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "position_qty": -5, "avg_price": 7500.0,
        "working_orders": 0, "is_sim": 0,
    }))

    import backend.v9.services.sierra_position_reconciler as spr
    monkeypatch.setattr(spr, "STATE_FILE", state_file)

    # Mock fill_poller with empty order_map (no system orders)
    mock_fp = MagicMock()
    mock_fp._order_map = {}

    ok, msg = spr.reconcile_position(_make_tm(), fill_poller=mock_fp)

    assert ok, (
        f"Manual position should be ok=True (not orphan), got: {msg}. "
        "If reverted → RED: reconciler screams NAKED ORPHAN on Michael's manual trades"
    )
    assert "POSITION NOT IN BOOKS" in msg


def _make_tm_with_open(trade_id):
    """A TradeManager whose books still hold `trade_id` (genuine orphan case)."""
    import types
    tm = MagicMock()
    tm.get_active_trades.return_value = [types.SimpleNamespace(id=trade_id)]
    return tm


def test_system_position_is_orphan(monkeypatch, tmp_path):
    """Sierra=-5 + TM=0 + order_map points at an OPEN trade → real orphan.

    T5 (2026-08-15) narrowed ownership from "the map has ANY entry" to "the map
    points at a trade that is still open". The old global test was what produced
    113 false NAKED-ORPHAN alarms on 14.08: the map is a historical
    order_id→trade_id index, so from the system's first trade of the day onward
    every manual position of Michael's was claimed as system-owned.

    A closed trade id in the map therefore no longer proves ownership — this
    fixture now supplies an OPEN one, which is what a genuine orphan looks like.
    (The case "the map points at a CLOSED trade and Sierra still holds" is the
    #682 ghost; T4 prevents it at the source by refusing to close the books
    until Sierra proves flat, and the reconciler now names it as ambiguous
    rather than guessing an owner.)
    """
    monkeypatch.setenv("RECONCILER_OWNERSHIP_AWARE_V1", "1")

    import json
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "position_qty": -5, "avg_price": 7500.0,
        "working_orders": 0, "is_sim": 0,
    }))

    import backend.v9.services.sierra_position_reconciler as spr
    monkeypatch.setattr(spr, "STATE_FILE", state_file)

    # Mock fill_poller WITH orders in map → system placed this
    mock_fp = MagicMock()
    mock_fp._order_map = {12345: 479}
    mock_fp._tm = _make_tm_with_open(479)

    with patch("backend.v9.services.phone_alert.push"):
        ok, msg = spr.reconcile_position(_make_tm(), fill_poller=mock_fp)

    assert not ok, (
        f"System position should be ok=False (real orphan), got: {msg}"
    )
    assert "NAKED ORPHAN" in msg or "ORPHAN" in msg


def test_flag_off_legacy_behavior(monkeypatch, tmp_path):
    """Flag OFF → legacy behavior: manual position is still NAKED ORPHAN."""
    monkeypatch.delenv("RECONCILER_OWNERSHIP_AWARE_V1", raising=False)

    import json
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "position_qty": -5, "avg_price": 7500.0,
        "working_orders": 0, "is_sim": 0,
    }))

    import backend.v9.services.sierra_position_reconciler as spr
    monkeypatch.setattr(spr, "STATE_FILE", state_file)

    with patch("backend.v9.services.phone_alert.push"):
        ok, msg = spr.reconcile_position(_make_tm())

    assert not ok, "Flag OFF → legacy DIVERGENCE behavior"
    assert "DIVERGENCE" in msg


def test_matched_position_ok(monkeypatch, tmp_path):
    """TM=Sierra → MATCH regardless of flag."""
    monkeypatch.setenv("RECONCILER_OWNERSHIP_AWARE_V1", "1")

    import json
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "position_qty": 0, "avg_price": 0,
        "working_orders": 0, "is_sim": 0,
    }))

    import backend.v9.services.sierra_position_reconciler as spr
    monkeypatch.setattr(spr, "STATE_FILE", state_file)

    ok, msg = spr.reconcile_position(_make_tm())
    assert ok
    assert "MATCH" in msg
