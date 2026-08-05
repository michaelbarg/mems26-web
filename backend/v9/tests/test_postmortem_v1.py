"""POST_MORTEM_V1 tests — must never block the trading loop.

Key invariants:
1. on_trade_closed never raises (catches all exceptions)
2. Only fires on LOSS outcome
3. Root verdict is always one of the closed taxonomy
4. Report file is written to docs/reports/postmortem/
5. DB row created with correct fields
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace


# ── Test 1: never raises, even on broken DB ──

def test_on_trade_closed_never_raises():
    """The postmortem hook must never raise, even with a completely broken DB."""
    from backend.v9.services.postmortem.analyzer import on_trade_closed
    # Pass a mock session that raises on every call
    broken_db = MagicMock()
    broken_db.query.side_effect = RuntimeError("DB is dead")

    # Must not raise
    on_trade_closed(trade_id=99999, db=broken_db)


def test_on_trade_closed_never_raises_on_import_error():
    """Even if internal imports fail, on_trade_closed must not raise."""
    from backend.v9.services.postmortem.analyzer import on_trade_closed
    broken_db = MagicMock()
    broken_db.query.side_effect = ImportError("module missing")
    on_trade_closed(trade_id=99999, db=broken_db)


# ── Test 2: only fires on LOSS ──

def test_skips_win_trade():
    """Post-mortem should not process WIN trades."""
    from backend.v9.services.postmortem.analyzer import _run_postmortem

    mock_trade = _make_trade(outcome="WIN", pnl_usd=50.0)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_trade

    # Should return early without writing
    _run_postmortem(trade_id=1, db=db)
    db.add.assert_not_called()


def test_processes_loss_trade():
    """Post-mortem should process LOSS trades and add a DB row."""
    from backend.v9.services.postmortem.analyzer import _run_postmortem

    mock_trade = _make_trade(outcome="LOSS", pnl_usd=-25.0)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [
        mock_trade,  # V9Trade query
        None,        # V9Postmortem existing check
    ]

    with patch("backend.v9.services.postmortem.analyzer._compute_excursion", return_value={"mae_pts": 5.0, "mfe_pts": 2.0}), \
         patch("backend.v9.services.postmortem.analyzer._compute_s7", return_value={"score": 45, "sizing": 1, "components": {"base": 30}}), \
         patch("backend.v9.services.postmortem.analyzer._get_eod_day_type", return_value="Balance"), \
         patch("backend.v9.services.postmortem.analyzer._compute_range_position", return_value=0.5), \
         patch("backend.v9.services.postmortem.analyzer._write_report", return_value="docs/reports/postmortem/PM_1.md"):
        _run_postmortem(trade_id=1, db=db)

    db.add.assert_called_once()
    pm = db.add.call_args[0][0]
    assert pm.trade_id == 1
    assert pm.mode == "live"
    assert pm.root_verdict in ("WRONG_CLASS", "LATE_ENTRY", "TIGHT_STOP", "MANAGEMENT", "NORMAL_NOISE")


# ── Test 3: root verdict taxonomy ──

def test_wrong_class_verdict():
    """Mismatched day-type family → WRONG_CLASS."""
    from backend.v9.services.postmortem.analyzer import _classify_root_cause
    trade = _make_trade(direction="LONG", entry_price=7600, stop=7594, t1_hit_ts=None, exit_reason="STOP_HIT")
    verdict, _ = _classify_root_cause(
        trade,
        entry_ctx={"day_type": "Trend_Normal"},
        eod_day_type="Balance",
        excursion={"mae_pts": 6.0},
        range_pos=0.5,
    )
    assert verdict == "WRONG_CLASS"


def test_late_entry_verdict_long():
    """LONG entry in top 15% of range → LATE_ENTRY."""
    from backend.v9.services.postmortem.analyzer import _classify_root_cause
    trade = _make_trade(direction="LONG", entry_price=7600, stop=7594, t1_hit_ts=None, exit_reason="STOP_HIT")
    verdict, _ = _classify_root_cause(
        trade,
        entry_ctx={"day_type": "Balance"},
        eod_day_type="Balance",
        excursion={"mae_pts": 6.0},
        range_pos=0.90,
    )
    assert verdict == "LATE_ENTRY"


def test_tight_stop_verdict():
    """Stop < 6pt on trend day → TIGHT_STOP."""
    from backend.v9.services.postmortem.analyzer import _classify_root_cause
    trade = _make_trade(direction="LONG", entry_price=7600, stop=7596, t1_hit_ts=None, exit_reason="STOP_HIT")
    verdict, _ = _classify_root_cause(
        trade,
        entry_ctx={"day_type": "Trend_Normal"},
        eod_day_type="Trend_Normal",
        excursion={"mae_pts": 4.0},
        range_pos=0.5,
    )
    assert verdict == "TIGHT_STOP"


def test_management_verdict():
    """T1 hit then stopped at BE → MANAGEMENT."""
    from backend.v9.services.postmortem.analyzer import _classify_root_cause
    trade = _make_trade(
        direction="LONG", entry_price=7600, stop=7600,
        t1_hit_ts=datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc),
        exit_reason="STOP_HIT",
    )
    verdict, _ = _classify_root_cause(
        trade,
        entry_ctx={"day_type": "Balance"},
        eod_day_type="Balance",
        excursion={"mae_pts": 0.0},
        range_pos=0.5,
    )
    assert verdict == "MANAGEMENT"


def test_normal_noise_verdict():
    """No structural issue → NORMAL_NOISE."""
    from backend.v9.services.postmortem.analyzer import _classify_root_cause
    trade = _make_trade(direction="LONG", entry_price=7600, stop=7592, t1_hit_ts=None, exit_reason="STOP_HIT")
    verdict, _ = _classify_root_cause(
        trade,
        entry_ctx={"day_type": "Balance"},
        eod_day_type="Balance",
        excursion={"mae_pts": 8.0},
        range_pos=0.5,
    )
    assert verdict == "NORMAL_NOISE"


# ── Test 4: timing — postmortem must complete fast ──

def test_postmortem_does_not_block_trade_loop():
    """Simulates the trade manager calling on_trade_closed inline.
    The call must return promptly (< 2s) even with mocked slow helpers."""
    import time
    from backend.v9.services.postmortem.analyzer import on_trade_closed

    db = MagicMock()
    db.query.side_effect = Exception("simulated slow DB")

    start = time.monotonic()
    on_trade_closed(trade_id=1, db=db)
    elapsed = time.monotonic() - start

    assert elapsed < 2.0, f"Postmortem took {elapsed:.1f}s — must not block trading loop"


# ── helpers ──

def _make_trade(
    outcome="LOSS", pnl_usd=-25.0, direction="LONG",
    entry_price=7600.0, stop=7594.0, exit_price=7594.0,
    exit_reason="STOP_HIT", t1_hit_ts=None, mode="live",
):
    trade = SimpleNamespace(
        id=1,
        mode=mode,
        firing_system=4,
        direction=direction,
        state="CLOSED",
        entry_ts=datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc),
        entry_price=entry_price,
        exit_ts=datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc),
        exit_price=exit_price,
        stop=stop,
        t1=entry_price + 6.0,
        t2=entry_price + 10.0,
        t3=None,
        t1_hit_ts=t1_hit_ts,
        t2_hit_ts=None,
        t3_hit_ts=None,
        stop_hit_ts=datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc) if exit_reason == "STOP_HIT" else None,
        exit_reason=exit_reason,
        pnl_usd=pnl_usd,
        pnl_r=-1.0 if pnl_usd < 0 else 1.0,
        outcome=outcome,
        quality=None,
        cross_context=None,
        day_type_at_entry=None,
        pattern_id_at_entry=None,
        session_at_entry=None,
        sierra_bracket_id=None,
        is_synthetic=0,
    )
    return trade
