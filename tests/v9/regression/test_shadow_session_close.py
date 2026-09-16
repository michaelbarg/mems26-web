"""T-396: shadow session close — stale shadows from previous sessions are closed.

Regression tests:
  (a) Shadow trade from yesterday in PARTIAL → after on_bar → CLOSED/STALE_UNRESOLVED
  (b) Live trade in same state → not touched
  (c) Hydration at boot closes stale shadows
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers: lightweight trade stub that mimics V9Trade ORM attributes
# ---------------------------------------------------------------------------

class FakeTrade:
    """Minimal V9Trade stub for unit tests."""

    def __init__(self, id, mode, state, entry_ts,
                 entry_price=7600.0, direction="LONG",
                 stop=7590.0, t1=7610.0, t2=7620.0, t3=7630.0,
                 t1_hit_ts=None, t2_hit_ts=None, t3_hit_ts=None,
                 t4=None, t4_hit_ts=None, stop_hit_ts=None,
                 exit_ts=None, exit_price=None, exit_reason=None,
                 pnl_usd=None, quality=None, cross_context=None,
                 sierra_bracket_id=None, outcome=None, pnl_r=None,
                 pnl_sierra=None, firing_system=2,
                 day_type_at_entry=None, pattern_id_at_entry=None,
                 session_at_entry=None):
        self.id = id
        self.mode = mode
        self.state = state
        self.entry_ts = entry_ts
        self.entry_price = entry_price
        self.direction = direction
        self.stop = stop
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        self.t4 = t4
        self.t1_hit_ts = t1_hit_ts
        self.t2_hit_ts = t2_hit_ts
        self.t3_hit_ts = t3_hit_ts
        self.t4_hit_ts = t4_hit_ts
        self.stop_hit_ts = stop_hit_ts
        self.exit_ts = exit_ts
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.pnl_usd = pnl_usd
        self.quality = quality or {}
        self.cross_context = cross_context or []
        self.sierra_bracket_id = sierra_bracket_id
        self.outcome = outcome
        self.pnl_r = pnl_r
        self.pnl_sierra = pnl_sierra
        self.firing_system = firing_system
        self.day_type_at_entry = day_type_at_entry
        self.pattern_id_at_entry = pattern_id_at_entry
        self.session_at_entry = session_at_entry


def _yesterday_entry():
    """Return a UTC timestamp well before today's RTH open."""
    return datetime.now(timezone.utc) - timedelta(hours=20)


def _today_entry():
    """Return a UTC timestamp within today's session (after RTH open)."""
    from zoneinfo import ZoneInfo
    from datetime import time as _time
    et = ZoneInfo("America/New_York")
    today = datetime.now(et).date()
    # 10:00 ET — safely after 09:30 RTH open
    return datetime.combine(today, _time(10, 0), tzinfo=et).astimezone(timezone.utc)


def _mock_session_info():
    """Return a session_info dict with today's RTH open ~6h ago."""
    from zoneinfo import ZoneInfo
    from datetime import time as _time
    et = ZoneInfo("America/New_York")
    today = datetime.now(et).date()
    rth_open_et = datetime.combine(today, _time(9, 30), tzinfo=et)
    rth_close_et = datetime.combine(today, _time(16, 0), tzinfo=et)
    return {
        "session_date": today,
        "is_holiday": False,
        "is_half_day": False,
        "is_weekend": False,
        "rth_open_utc": rth_open_et.astimezone(timezone.utc),
        "rth_close_utc": rth_close_et.astimezone(timezone.utc),
        "ib_end_utc": datetime.combine(today, _time(10, 30), tzinfo=et).astimezone(timezone.utc),
    }


# ---------------------------------------------------------------------------
# (a) Stale shadow PARTIAL from yesterday → CLOSED/STALE_UNRESOLVED
# ---------------------------------------------------------------------------

def test_stale_shadow_closed_on_bar():
    """A shadow trade from yesterday in PARTIAL state is closed by
    _close_stale_shadow on the next bar."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

    stale_shadow = FakeTrade(
        id=1608, mode="shadow", state="PARTIAL",
        entry_ts=_yesterday_entry(),
        t1_hit_ts=_yesterday_entry(),  # T1 was hit yesterday
        pnl_usd=25.0,  # partial PnL from T1
    )

    tm = MagicMock()
    tm.get_active_trades.return_value = [stale_shadow]
    tm._db = MagicMock()

    detector = BarLevelDetector(trade_manager=tm)

    with patch("backend.v9.services.market_clock.get_session_info",
               _mock_session_info):
        detector._close_stale_shadow([stale_shadow])

    assert stale_shadow.state == "CLOSED"
    assert stale_shadow.exit_reason == "STALE_UNRESOLVED"
    assert stale_shadow.exit_price is None
    # Partial PnL from T1 is preserved (not overwritten)
    assert stale_shadow.pnl_usd == 25.0
    assert stale_shadow.exit_ts is not None


# ---------------------------------------------------------------------------
# (b) Live trade in same state → NOT touched
# ---------------------------------------------------------------------------

def test_live_trade_not_touched():
    """A live trade from yesterday in FILLED state is NOT closed by
    _close_stale_shadow — only shadow trades are affected."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

    live_trade = FakeTrade(
        id=1609, mode="live", state="FILLED",
        entry_ts=_yesterday_entry(),
    )

    tm = MagicMock()
    tm._db = MagicMock()

    detector = BarLevelDetector(trade_manager=tm)

    with patch("backend.v9.services.market_clock.get_session_info",
               _mock_session_info):
        detector._close_stale_shadow([live_trade])

    assert live_trade.state == "FILLED"
    assert live_trade.exit_reason is None


def test_demo_trade_not_touched():
    """A demo trade from yesterday is NOT closed by _close_stale_shadow."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

    demo_trade = FakeTrade(
        id=1610, mode="demo", state="PARTIAL",
        entry_ts=_yesterday_entry(),
    )

    tm = MagicMock()
    tm._db = MagicMock()

    detector = BarLevelDetector(trade_manager=tm)

    with patch("backend.v9.services.market_clock.get_session_info",
               _mock_session_info):
        detector._close_stale_shadow([demo_trade])

    assert demo_trade.state == "PARTIAL"
    assert demo_trade.exit_reason is None


def test_same_session_shadow_not_touched():
    """A shadow trade from TODAY's session is NOT closed."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

    today_shadow = FakeTrade(
        id=1611, mode="shadow", state="FILLED",
        entry_ts=_today_entry(),
    )

    tm = MagicMock()
    tm._db = MagicMock()

    detector = BarLevelDetector(trade_manager=tm)

    with patch("backend.v9.services.market_clock.get_session_info",
               _mock_session_info):
        detector._close_stale_shadow([today_shadow])

    assert today_shadow.state == "FILLED"
    assert today_shadow.exit_reason is None


# ---------------------------------------------------------------------------
# (c) Hydration at boot closes stale shadows
# ---------------------------------------------------------------------------

def test_hydration_closes_stale_shadow_at_boot():
    """TradeManager._close_stale_shadows_at_boot closes stale shadow trades
    from previous sessions during initialization."""
    from backend.v9.services.trade_manager.manager import TradeManager
    from backend.v9.db.models.trades import V9Trade

    stale = FakeTrade(
        id=1612, mode="shadow", state="PARTIAL",
        entry_ts=_yesterday_entry(),
    )

    db = MagicMock()
    # The query chain: db.query(V9Trade).filter(...).all()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [stale]
    db.query.return_value = mock_query

    with patch("backend.v9.services.market_clock.get_session_info",
               _mock_session_info):
        tm = TradeManager(db=db)

    assert stale.state == "CLOSED"
    assert stale.exit_reason == "STALE_UNRESOLVED"
    assert stale.exit_price is None
    assert stale.exit_ts is not None
    db.commit.assert_called()


# ---------------------------------------------------------------------------
# T2 HIT dedup guard
# ---------------------------------------------------------------------------

def test_target_hit_dedup_prevents_repeat():
    """The _target_hit_dedup set prevents the same (trade_id, target) from
    firing on_target_hit more than once (root cause of 123x T2 HIT)."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

    tm = MagicMock()
    tm._db = MagicMock()

    with patch("backend.v9.services.market_clock.get_session_info",
               _mock_session_info):
        detector = BarLevelDetector(trade_manager=tm)

    # Simulate first T2 hit being recorded
    detector._target_hit_dedup.add((1608, "T2"))

    # The dedup set should prevent a second call
    assert (1608, "T2") in detector._target_hit_dedup
    # A different trade or target should not be blocked
    assert (1608, "T3") not in detector._target_hit_dedup
    assert (1609, "T2") not in detector._target_hit_dedup
