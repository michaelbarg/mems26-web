"""I-62 FULL — bar-price inference must never drive T-hits on demo/live trades.

Real incident (trade 350, 2026-07-10 22:03:50): BarLevelDetector logged
"T2 HIT: trade 350 at 7622.00" and closed the LIVE trade as a +$112.5 WIN —
while Sierra had already STOPPED the runner at ~7610 a minute earlier (real
outcome +$52.5). The old I-62 guard covered only T3; T1/T2 on demo/live still
fired on_target_hit from bar highs. Same rule as the stop path now: demo/live
→ log INFERRED + wait for the Sierra fill. Shadow stays bar-driven.
"""
import asyncio
from unittest.mock import MagicMock

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def _mk_trade(mode):
    t = MagicMock()
    t.id = 350
    t.direction = "LONG"
    t.entry_price = 7608.5
    t.state = "PARTIAL"
    t.mode = mode
    t.t1 = 7617.5
    t.t1_hit_ts = object()   # T1 already done
    t.t2 = 7622.0
    t.t2_hit_ts = None
    t.t3 = 7622.5
    t.t3_hit_ts = None
    t.stop = 7611.25
    t.stop_hit_ts = None
    t.entry_ts = None
    t.quality = {}
    return t


def _run_bar(detector, high=7622.0, low=7612.0):
    bar = {"ts": 1783707800, "high": high, "low": low,
           "open": 7615.0, "close": 7620.0}
    asyncio.get_event_loop().run_until_complete(detector.on_bar(bar))


def test_live_t2_not_inferred_from_bar():
    """The 350 fixture: live trade, bar_high >= t2 → NO on_target_hit."""
    mock_tm = MagicMock()
    trade = _mk_trade("live")
    mock_tm.get_active_trades.return_value = [trade]
    det = BarLevelDetector(mock_tm)
    _run_bar(det)
    mock_tm.on_target_hit.assert_not_called()


def test_shadow_t2_still_bar_driven():
    """Shadow trades keep bar-driven management (no Sierra fills exist)."""
    mock_tm = MagicMock()
    trade = _mk_trade("shadow")
    mock_tm.get_active_trades.return_value = [trade]
    det = BarLevelDetector(mock_tm)
    _run_bar(det)
    assert mock_tm.on_target_hit.called, "shadow must still infer from bars"
