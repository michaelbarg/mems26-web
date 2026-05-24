"""58 tests for TrailEngine — D-094 Pkg 3b Stream 3.

Test groups:
  HL/LH Trail — 5-bar window (6):
        swing-stop tracks min of last_5_lows (LONG) / max of last_5_highs (SHORT),
        fires only when >= 5 bars accumulated, tighter-only guard, direction invariant,
        t2 gate respected, window slides after 5+ bars.
  Chandelier frozen ATR (6):
        engage runs once, ATR frozen at engage, uses max_high/min_low_since_t2,
        multiplier per pattern family, tighter-only guard, dormant before engage.
  Time stop (4):
        fires at limit, skips before limit, no-op without day_type, idempotent.
  State persistence (5):
        to_dict/from_dict round-trip for new fields, save/load cycle,
        bars_processed increments, trail_active flag, chandelier_engaged persisted.
  Cross-context audit (3):
        _append_cross_context validates JSON, chandelier engage writes audit,
        close_trade reason string.
  Concurrency / Sierra (3):
        fill-lock skips trade entirely, fill-lock in _move_stop_tighter_only,
        unlocked trades process normally.
  Integration (2):
        full on_bar_close async wiring order (MFE→process→layer4),
        no-op when t2 not hit.
  Layer 4 — 20 tests:
        TCCI exit fires close, TCCI no-op when no cross,
        MFE peak tighten applied, MFE below threshold no-op,
        CCI flat tighten applied, CCI history too short no-op,
        SWI red tighten applied, SWI non-red no-op,
        day_type WARN logged, day_type EXIT closes trade,
        day_type consistent no-op, tightest stop wins among candidates,
        layer4 fill-lock guard, layer4 skips when bar has no close,
        layer4 multiple services all tighten → tightest wins,
        layer4 EXIT short-circuits remaining services,
        layer4 woodies_provider error is non-fatal,
        layer4 no woodies_provider → empty context,
        layer4 direction SHORT tightest = min candidate,
        layer4 _adapt_trade_for_layer4 keys.
  D-094 Retrofit (10):
        _engage_chandelier idempotent,
        _engage_chandelier dormant when ATR=None,
        _compute_chandelier_stop_v3 raises on corrupt state,
        _reconstruct_state_from_db builds 5-bar windows,
        _bar_attr reads attr and dict,
        _update_mfe tracks mfe_high and mfe_low,
        on_bar_close calls _update_mfe before _process_trade,
        last_5_lows slides after > 5 bars,
        _apply_tightest_stop LONG picks max,
        _apply_tightest_stop SHORT picks min.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure BRIDGE_TOKEN is set before any backend import
os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from backend.v9.services.trail_engine import TrailEngine, TrailState


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    """Run a coroutine synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_trade(
    trade_id: int = 1,
    direction: str = "LONG",
    stop: float = 5240.0,
    entry_price: float = 5250.0,
    t2_hit_ts=None,
    t1_hit_ts=None,
    entry_ts=None,
    day_type: Optional[str] = None,
    pattern_name: Optional[str] = None,
    trail_state: Optional[dict] = None,
    quality_extra: Optional[dict] = None,
) -> MagicMock:
    """Create a mock V9Trade with configurable fields."""
    trade = MagicMock()
    trade.id = trade_id
    trade.direction = direction
    trade.stop = stop
    trade.entry_price = entry_price
    trade.t2_hit_ts = t2_hit_ts
    trade.t1_hit_ts = t1_hit_ts
    trade.entry_ts = entry_ts

    quality: Dict[str, Any] = {}
    if day_type is not None:
        quality["day_type"] = day_type
    if pattern_name is not None:
        quality["pattern_name"] = pattern_name
    if trail_state is not None:
        quality["trail_state"] = trail_state
    if quality_extra:
        quality.update(quality_extra)
    trade.quality = quality

    return trade


def _make_event(
    high: float = 5255.0,
    low: float = 5245.0,
    ts: str = "2026-05-23T10:05:00Z",
    close: float = 5250.0,
) -> MagicMock:
    """Create a mock BarEvent with a payload dict."""
    event = MagicMock()
    event.payload = {"high": high, "low": low, "close": close, "ts": ts}
    return event


def _make_engine(
    trades: Optional[List] = None,
    mode: str = "shadow",
    yesterday_bars: Optional[List] = None,
    woodies_provider=None,
    fetch_bars_since=None,
) -> tuple:
    """Return (engine, tm_mock, br_mock) with list_trades_past_t1 returning trades."""
    tm = MagicMock()
    br = MagicMock()
    tm.list_trades_past_t1.return_value = trades if trades is not None else []
    tm.is_fill_locked.return_value = False

    engine = TrailEngine(
        trade_manager=tm,
        bar_router=br,
        yesterday_bars=yesterday_bars or [],
        mode=mode,
        woodies_provider=woodies_provider,
        fetch_bars_since=fetch_bars_since,
    )
    return engine, tm, br


def _trail_state_5bar(
    lows=None,
    highs=None,
    max_high=None,
    min_low=None,
    bars_processed=5,
    chandelier_engaged=False,
    t2_atr=None,
    time_stop_fired=False,
    trail_active=True,
) -> dict:
    """Helper to build a trail_state dict with 5-bar fields seeded."""
    return {
        "last_5_lows": lows or [],
        "last_5_highs": highs or [],
        "max_high_since_t2": max_high,
        "min_low_since_t2": min_low,
        "chandelier_engaged": chandelier_engaged,
        "t2_bar_ts": None,
        "t2_atr_at_engage": t2_atr,
        "bars_processed": bars_processed,
        "last_bar_ts": "2026-05-23T10:00:00Z",
        "time_stop_fired": time_stop_fired,
        "trail_active": trail_active,
    }


# ── HL/LH Trail — 5-bar window (6 tests) ─────────────────────────────────────

class TestHLLHTrail5Bar:

    def test_long_swing_stop_fires_when_5_lows_accumulated(self):
        """LONG: after 5 bars, min(last_5_lows) > current_stop → stop moved."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                lows=[5244.0, 5245.0, 5246.0, 5247.0, 5248.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                max_high=5264.0,
                min_low=5244.0,
                chandelier_engaged=True,
                t2_atr=None,  # will raise if used; patch ATR
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            bar = {"high": 5265.0, "low": 5249.0, "ts": "2026-05-23T10:05:00Z"}
            # chandelier_engaged=True but t2_atr_at_engage=None → will raise; override
            trade.quality["trail_state"]["t2_atr_at_engage"] = None
            trade.quality["trail_state"]["chandelier_engaged"] = False  # disable chandelier
            engine._process_trade(trade, bar)

        # After adding bar, last_5_lows = [5245,5246,5247,5248,5249], min=5245
        # min(5245) > current_stop(5240) → should move
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_trail_5bar"]
        assert len(calls) == 1
        # min of [5245,5246,5247,5248,5249]
        assert calls[0][1]["new_stop"] == pytest.approx(5245.0)

    def test_long_swing_stop_does_not_widen(self):
        """LONG: min of last_5_lows < current_stop → no move."""
        trade = _make_trade(
            direction="LONG",
            stop=5250.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                lows=[5238.0, 5239.0, 5240.0, 5241.0, 5242.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                max_high=5264.0,
                min_low=5238.0,
                chandelier_engaged=False,
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            bar = {"high": 5265.0, "low": 5238.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_trail_5bar"]
        assert calls == []

    def test_short_swing_stop_fires_when_5_highs_accumulated(self):
        """SHORT: max(last_5_highs) < current_stop → stop tightened."""
        trade = _make_trade(
            direction="SHORT",
            stop=5270.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                lows=[5240.0, 5241.0, 5242.0, 5243.0, 5244.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                max_high=5264.0,
                min_low=5240.0,
                chandelier_engaged=False,
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            bar = {"high": 5262.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_trail_5bar"]
        assert len(calls) == 1
        # max of [5261,5262,5263,5264,5262] = 5264; but 5264 < 5270 → tighter
        assert calls[0][1]["new_stop"] == pytest.approx(5264.0)

    def test_swing_stop_not_fired_before_5_bars(self):
        """Swing trail must NOT fire before 5 bars in window."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                lows=[5245.0, 5246.0, 5247.0],  # only 3 lows
                highs=[5260.0, 5261.0, 5262.0],
                max_high=5262.0,
                min_low=5245.0,
                chandelier_engaged=False,
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            bar = {"high": 5265.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        # Only 4 lows after this bar → should NOT fire
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_trail_5bar"]
        assert calls == []

    def test_swing_stop_skips_before_t2(self):
        """Swing trail must NOT activate before t2_hit_ts is set."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=None,  # t2 NOT yet hit
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.update_stop_with_audit.assert_not_called()

    def test_window_slides_when_more_than_5_bars(self):
        """After 6+ bars, the window keeps only the last 5."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                lows=[5241.0, 5242.0, 5243.0, 5244.0, 5245.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                max_high=5264.0,
                min_low=5241.0,
                chandelier_engaged=False,
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            bar = {"high": 5270.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        saved = trade.quality["trail_state"]
        assert len(saved["last_5_lows"]) == 5
        # first element dropped, 5250 added
        assert saved["last_5_lows"][-1] == pytest.approx(5250.0)
        assert saved["last_5_lows"][0] == pytest.approx(5242.0)


# ── Chandelier frozen ATR (6 tests) ───────────────────────────────────────────

class TestChandelierFrozenATR:

    def test_engage_runs_once_and_freezes_atr(self):
        """_engage_chandelier runs once; subsequent calls are no-ops."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])
        state = TrailState()
        state.max_high_since_t2 = 5265.0

        bar = {"high": 5265.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=4.0):
            engine._engage_chandelier(trade, bar, state)
            first_atr = state.t2_atr_at_engage
            # Second call must be idempotent (ATR not recomputed)
            with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=9.0):
                engine._engage_chandelier(trade, bar, state)

        assert state.chandelier_engaged is True
        assert state.t2_atr_at_engage == pytest.approx(4.0)  # frozen, not 9.0

    def test_engage_dormant_when_atr_none(self):
        """_engage_chandelier does not engage when ATR returns None."""
        trade = _make_trade(direction="LONG", stop=5230.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm, _ = _make_engine(trades=[trade])
        state = TrailState()
        bar = {"high": 5265.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            engine._engage_chandelier(trade, bar, state)

        assert state.chandelier_engaged is False
        assert state.t2_atr_at_engage is None

    def test_chandelier_long_uses_max_high_since_t2(self):
        """LONG chandelier: stop = max_high_since_t2 - k*frozen_ATR."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                max_high=5265.0,
                min_low=5250.0,
                chandelier_engaged=True,
                t2_atr=4.0,
                lows=[5248.0, 5249.0, 5250.0, 5251.0, 5252.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=999.0):
            bar = {"high": 5266.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        # max_high_since_t2 becomes 5266 after bar; frozen ATR=4.0; k=1.5 default
        # chandelier = 5266 - 1.5*4.0 = 5260.0 > 5230 → tightened
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14_frozen"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5260.0, abs=0.01)

    def test_chandelier_short_uses_min_low_since_t2(self):
        """SHORT chandelier: stop = min_low_since_t2 + k*frozen_ATR."""
        trade = _make_trade(
            direction="SHORT",
            stop=5280.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                max_high=5265.0,
                min_low=5250.0,
                chandelier_engaged=True,
                t2_atr=4.0,
                lows=[5245.0, 5246.0, 5247.0, 5248.0, 5249.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=999.0):
            bar = {"high": 5264.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        # min_low_since_t2 becomes 5248 after bar; chandelier = 5248 + 1.5*4.0 = 5254.0 < 5280 → tighter
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14_frozen"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5254.0, abs=0.01)

    def test_chandelier_uses_initiative_multiplier(self):
        """OFA_Initiative pattern → k=2.0 from ATR_MULTIPLIERS."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            pattern_name="OFA_Initiative",
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                max_high=5265.0,
                min_low=5250.0,
                chandelier_engaged=True,
                t2_atr=4.0,
                lows=[5248.0, 5249.0, 5250.0, 5251.0, 5252.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=999.0):
            bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        # max_high stays 5265 (bar.high == existing max); chandelier = 5265 - 2.0*4.0 = 5257.0
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14_frozen"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5257.0, abs=0.01)

    def test_compute_chandelier_stop_v3_raises_on_corrupt_state(self):
        """_compute_chandelier_stop_v3 raises ValueError when engaged but ATR is None."""
        trade = _make_trade(direction="LONG", stop=5230.0)
        engine, _, _ = _make_engine()
        state = TrailState()
        state.chandelier_engaged = True
        state.t2_atr_at_engage = None  # corrupt
        state.max_high_since_t2 = 5265.0

        with pytest.raises(ValueError, match="chandelier_engaged=True but t2_atr_at_engage=None"):
            engine._compute_chandelier_stop_v3(trade, state, "LONG")


# ── Time stop (4 tests) ───────────────────────────────────────────────────────

class TestTimeStop:

    def test_time_stop_fires_when_elapsed(self):
        """close_trade called with TIME_STOP when elapsed >= limit."""
        entry_ts = datetime.now(timezone.utc) - timedelta(minutes=35)
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            day_type="Normal",      # time_stop_minutes = 30
            entry_ts=entry_ts,
            t2_hit_ts=None,
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.close_trade.assert_called_once_with(trade.id, "TIME_STOP")

    def test_time_stop_no_op_before_limit(self):
        """close_trade NOT called when elapsed < limit."""
        entry_ts = datetime.now(timezone.utc) - timedelta(minutes=10)
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            day_type="Normal",      # limit = 30min
            entry_ts=entry_ts,
            t2_hit_ts=None,
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.close_trade.assert_not_called()

    def test_time_stop_none_when_no_day_type(self):
        """No time stop when day_type is missing from quality."""
        entry_ts = datetime.now(timezone.utc) - timedelta(minutes=120)
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            day_type=None,          # missing → no time stop
            entry_ts=entry_ts,
            t2_hit_ts=None,
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.close_trade.assert_not_called()

    def test_time_stop_idempotent_after_fired(self):
        """Time stop does not issue a second close_trade if already fired."""
        entry_ts = datetime.now(timezone.utc) - timedelta(minutes=60)
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            day_type="Normal",
            entry_ts=entry_ts,
            t2_hit_ts=None,
            trail_state=_trail_state_5bar(time_stop_fired=True, trail_active=False),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.close_trade.assert_not_called()


# ── State persistence (5 tests) ───────────────────────────────────────────────

class TestStatePersistence:

    def test_trail_state_to_dict_round_trip(self):
        """TrailState serialises and deserialises losslessly (new fields)."""
        state = TrailState(
            last_5_lows=[5244.0, 5245.0, 5246.0, 5247.0, 5248.0],
            last_5_highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
            max_high_since_t2=5264.0,
            min_low_since_t2=5244.0,
            chandelier_engaged=True,
            t2_bar_ts="2026-05-23T10:00:00Z",
            t2_atr_at_engage=3.75,
            bars_processed=7,
            last_bar_ts="2026-05-23T10:05:00Z",
            time_stop_fired=False,
            trail_active=True,
        )
        d = state.to_dict()
        restored = TrailState.from_dict(d)

        assert restored.last_5_lows == pytest.approx([5244.0, 5245.0, 5246.0, 5247.0, 5248.0])
        assert restored.last_5_highs == pytest.approx([5260.0, 5261.0, 5262.0, 5263.0, 5264.0])
        assert restored.max_high_since_t2 == pytest.approx(5264.0)
        assert restored.min_low_since_t2 == pytest.approx(5244.0)
        assert restored.chandelier_engaged is True
        assert restored.t2_bar_ts == "2026-05-23T10:00:00Z"
        assert restored.t2_atr_at_engage == pytest.approx(3.75)
        assert restored.bars_processed == 7
        assert restored.time_stop_fired is False
        assert restored.trail_active is True

    def test_state_saved_to_trade_quality(self):
        """_save_state writes trail_state key into trade.quality."""
        trade = _make_trade()
        engine, _, _ = _make_engine()

        state = TrailState(
            last_5_highs=[5270.0],
            bars_processed=3,
        )
        engine._save_state(trade, state)

        assert "trail_state" in trade.quality
        assert trade.quality["trail_state"]["last_5_highs"] == [5270.0]
        assert trade.quality["trail_state"]["bars_processed"] == 3

    def test_state_loaded_from_trade_quality(self):
        """_load_state restores from trade.quality["trail_state"]."""
        trade = _make_trade(
            trail_state=_trail_state_5bar(
                lows=[5244.0, 5245.0, 5246.0, 5247.0, 5248.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                max_high=5264.0,
                min_low=5244.0,
                chandelier_engaged=True,
                t2_atr=2.5,
                bars_processed=4,
                trail_active=True,
            )
        )
        engine, _, _ = _make_engine()

        state = engine._load_state(trade)

        assert state.last_5_lows == pytest.approx([5244.0, 5245.0, 5246.0, 5247.0, 5248.0])
        assert state.max_high_since_t2 == pytest.approx(5264.0)
        assert state.chandelier_engaged is True
        assert state.t2_atr_at_engage == pytest.approx(2.5)
        assert state.bars_processed == 4
        assert state.trail_active is True

    def test_bars_processed_increments_on_each_bar(self):
        """bars_processed in trail_state increases by 1 per bar."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=None,
            trail_state=_trail_state_5bar(bars_processed=2, trail_active=False),
        )
        engine, _, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        assert trade.quality["trail_state"]["bars_processed"] == 3

    def test_trail_active_set_after_t2(self):
        """trail_active transitions to True once t2_hit_ts is set."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 45, tzinfo=timezone.utc),
        )
        engine, _, _ = _make_engine(trades=[trade])

        with patch(
            "backend.v9.services.trail_engine.compute_continuous_atr14",
            return_value=None,
        ):
            bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        assert trade.quality["trail_state"]["trail_active"] is True


# ── Cross-context audit (3 tests) ─────────────────────────────────────────────

class TestCrossContextAudit:

    def test_append_cross_context_validates_json(self):
        """_append_cross_context rejects non-JSON-serializable entries."""
        trade = _make_trade()
        engine, _, _ = _make_engine()

        # A datetime is not JSON-serializable by default
        bad_entry = {"event": "test", "ts": datetime.now(timezone.utc)}
        engine._append_cross_context(trade, bad_entry)

        # Should not have been written
        quality = trade.quality if isinstance(trade.quality, dict) else {}
        ctx = quality.get("cross_context") or []
        assert ctx == []

    def test_chandelier_engage_writes_audit(self):
        """_engage_chandelier writes cross_context audit entry."""
        trade = _make_trade(direction="LONG", stop=5230.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, _, _ = _make_engine()
        state = TrailState(max_high_since_t2=5265.0, min_low_since_t2=5250.0)

        bar = {"high": 5265.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}
        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=4.0):
            engine._engage_chandelier(trade, bar, state)

        quality = trade.quality if isinstance(trade.quality, dict) else {}
        ctx = quality.get("cross_context") or []
        assert len(ctx) == 1
        assert ctx[0]["event"] == "chandelier_engaged"
        assert ctx[0]["atr_frozen"] == pytest.approx(4.0)

    def test_close_trade_time_stop_reason(self):
        """close_trade is called with reason='TIME_STOP' on time stop."""
        entry_ts = datetime.now(timezone.utc) - timedelta(minutes=35)
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            day_type="Normal",
            entry_ts=entry_ts,
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.close_trade.assert_called_once()
        assert tm.close_trade.call_args[0][1] == "TIME_STOP"


# ── Concurrency / Sierra fill (3 tests) ───────────────────────────────────────

class TestConcurrencyFillLock:

    def test_fill_locked_trade_skipped_entirely(self):
        """If is_fill_locked returns True, _process_trade skips all layers."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])
        tm.is_fill_locked.return_value = True

        bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.update_stop_with_audit.assert_not_called()
        tm.close_trade.assert_not_called()

    def test_fill_lock_checked_inside_move_stop(self):
        """_move_stop_tighter_only re-checks fill lock before writing."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        # Simulate lock acquired between outer check and _move_stop_tighter_only
        call_count = [0]

        def side_effect(trade_id):
            call_count[0] += 1
            # First call (outer guard) = False; subsequent calls = True
            return call_count[0] > 1

        tm.is_fill_locked.side_effect = side_effect

        bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        # Even though outer guard passed, inner guard should have blocked the write
        tm.update_stop_with_audit.assert_not_called()

    def test_unlocked_trade_processes_normally(self):
        """Unlocked trades are processed and stop is moved when tighter."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state=_trail_state_5bar(
                lows=[5242.0, 5243.0, 5244.0, 5245.0, 5246.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                max_high=5264.0,
                min_low=5242.0,
                chandelier_engaged=False,
            ),
        )
        engine, tm, _ = _make_engine(trades=[trade])
        tm.is_fill_locked.return_value = False

        bar = {"high": 5265.0, "low": 5247.0, "ts": "2026-05-23T10:05:00Z"}

        with patch(
            "backend.v9.services.trail_engine.compute_continuous_atr14",
            return_value=None,
        ):
            engine._process_trade(trade, bar)

        # min of last 5 lows = min(5243,5244,5245,5246,5247) = 5243 > 5240 → should move
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_trail_5bar"]
        assert len(calls) == 1


# ── Integration (2 tests) ─────────────────────────────────────────────────────

class TestIntegration:

    def test_on_bar_close_calls_mfe_then_process_then_layer4(self):
        """on_bar_close calls _update_mfe, _process_trade, _apply_layer4 in order."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])
        event = _make_event(high=5265.0, low=5252.0, ts="2026-05-23T10:05:00Z")

        call_order = []
        orig_mfe = engine._update_mfe
        orig_process = engine._process_trade
        orig_layer4 = engine._apply_layer4

        def track_mfe(t, b):
            call_order.append("mfe")
            return orig_mfe(t, b)

        def track_process(t, b):
            call_order.append("process")
            return orig_process(t, b)

        def track_layer4(t, b, ts):
            call_order.append("layer4")
            return orig_layer4(t, b, ts)

        engine._update_mfe = track_mfe
        engine._process_trade = track_process
        engine._apply_layer4 = track_layer4

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            with patch.object(engine, "_fetch_current_day_type", return_value=None):
                _run(engine.on_bar_close(event))

        assert call_order == ["mfe", "process", "layer4"]

    def test_on_bar_close_no_op_when_t2_not_hit(self):
        """on_bar_close: no stop move when t2_hit_ts is None (t2 gate closed)."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=None,    # t2 NOT hit
        )
        engine, tm, _ = _make_engine(trades=[trade])
        event = _make_event(high=5265.0, low=5252.0, ts="2026-05-23T10:05:00Z")

        with patch.object(engine, "_fetch_current_day_type", return_value=None):
            _run(engine.on_bar_close(event))

        tm.update_stop_with_audit.assert_not_called()
        tm.close_trade.assert_not_called()


# ── Layer 4 — 20 tests ────────────────────────────────────────────────────────

class TestLayer4Services:

    def _engine_with_woodies(self, trade, swi=None, cci_history=None,
                              direction_change=None, day_type=None):
        """Build engine with a mock woodies_provider returning given context."""
        ctx = {
            "swi": swi or {},
            "cci_history": cci_history or [],
            "direction_change_event": direction_change,
        }

        def woodies_provider():
            return ctx

        engine, tm, _ = _make_engine(trades=[trade], woodies_provider=woodies_provider)

        if day_type is not None:
            engine._fetch_current_day_type = lambda: day_type
        else:
            engine._fetch_current_day_type = lambda: None

        return engine, tm

    def test_tcci_exit_fires_close_trade(self):
        """TCCI cross against trade direction → close_trade issued."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        dir_change = {"type": "DIRECTION_CHANGE", "direction": "BEARISH",
                      "reasoning_notes": "TCCI crossed below"}

        from unittest.mock import MagicMock
        from backend.v9.services.layer4 import tcci_cross_exit

        engine, tm = self._engine_with_woodies(trade, direction_change=dir_change)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        with patch.object(tcci_cross_exit, "evaluate",
                          return_value={"action": "EXIT", "rule": "TCCI_CROSS",
                                        "reasoning_notes": "bearish cross"}):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.close_trade.assert_called_once()
        reason = tm.close_trade.call_args[0][1]
        assert "TCCI_CROSS" in reason

    def test_tcci_no_op_when_no_cross(self):
        """No exit when TCCI evaluates to None."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import tcci_cross_exit
        with patch.object(tcci_cross_exit, "evaluate", return_value=None):
            from backend.v9.services.layer4 import mfe_peak_tighten, cci_flat_tighten
            from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
            with patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
                 patch.object(cci_flat_tighten, "evaluate", return_value=None), \
                 patch.object(swi_tighten, "evaluate", return_value=None), \
                 patch.object(day_type_targets_verify, "evaluate", return_value=None):
                engine._apply_layer4(trade, bar, bar["ts"])

        tm.close_trade.assert_not_called()

    def test_mfe_peak_tighten_applied(self):
        """MFE peak 80% T2 tighten moves stop."""
        trade = _make_trade(direction="LONG", stop=5240.0, entry_price=5230.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
                            quality_extra={"mfe_high": 5270.0, "t2_price": 5260.0})
        engine, tm = self._engine_with_woodies(trade)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "MFE_PEAK",
                                        "new_stop": 5250.0, "old_stop": 5240.0,
                                        "reasoning_notes": "mfe test"}), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5250.0)

    def test_mfe_below_threshold_no_op(self):
        """MFE evaluate returns None → no stop movement."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.update_stop_with_audit.assert_not_called()

    def test_cci_flat_tighten_applied(self):
        """CCI flat 3 bars tighten → stop moved."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade, cci_history=[100.0, 102.0, 101.0])
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "CCI_FLAT",
                                        "new_stop": 5245.0, "old_stop": 5240.0,
                                        "reasoning_notes": "cci flat test"}), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5245.0)

    def test_cci_history_too_short_no_op(self):
        """CCI history < 3 bars → evaluate returns None → no tighten."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade, cci_history=[100.0])
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.update_stop_with_audit.assert_not_called()

    def test_swi_red_tighten_applied(self):
        """SWI red → stop tightened."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        swi = {"value": -5.0, "color": "red"}
        engine, tm = self._engine_with_woodies(trade, swi=swi)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "SWI_RED",
                                        "new_stop": 5243.75, "old_stop": 5240.0,
                                        "reasoning_notes": "swi red test"}), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5243.75)

    def test_swi_non_red_no_op(self):
        """SWI non-red → no tighten."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        swi = {"value": 5.0, "color": "green"}
        engine, tm = self._engine_with_woodies(trade, swi=swi)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.update_stop_with_audit.assert_not_called()

    def test_day_type_warn_logged(self):
        """day_type mismatch WARN → _append_cross_context entry written, no close_trade."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade, day_type="Variation")
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate",
                          return_value={"action": "WARN", "rule": "DAY_TYPE_TARGETS_MISMATCH",
                                        "current_day_type": "Variation",
                                        "reasoning_notes": "changed from Normal to Variation"}):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.close_trade.assert_not_called()
        # WARN should have written a cross_context entry (not logger.warning)
        quality = trade.quality if isinstance(trade.quality, dict) else {}
        ctx = quality.get("cross_context") or []
        assert any(e.get("event") == "layer4_warn" for e in ctx)

    def test_day_type_exit_closes_trade(self):
        """day_type WARN with no_trade day type → escalates to close_trade."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade, day_type="Nontrend")
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate",
                          return_value={"action": "WARN", "rule": "DAY_TYPE_TARGETS_MISMATCH",
                                        "current_day_type": "Nontrend",
                                        "reasoning_notes": "Nontrend - no trade"}):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.close_trade.assert_called_once()
        reason = tm.close_trade.call_args[0][1]
        assert reason == "DAY_TYPE_NO_TRADE_RECLASS"

    def test_day_type_consistent_no_op(self):
        """day_type unchanged → no action."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade, day_type="Normal")
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.close_trade.assert_not_called()
        tm.update_stop_with_audit.assert_not_called()

    def test_tightest_stop_wins_among_candidates(self):
        """Multiple TIGHTEN_STOP candidates → max (LONG) selected."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "MFE_PEAK",
                                        "new_stop": 5248.0, "reasoning_notes": "mfe"}), \
             patch.object(cci_flat_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "CCI_FLAT",
                                        "new_stop": 5245.0, "reasoning_notes": "cci flat"}), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        # LONG: tightest = max(5248, 5245) = 5248
        assert calls[0][1]["new_stop"] == pytest.approx(5248.0)

    def test_layer4_fill_lock_guard(self):
        """_apply_layer4 skips if fill-locked."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade)
        tm.is_fill_locked.return_value = True
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        engine._apply_layer4(trade, bar, bar["ts"])

        tm.update_stop_with_audit.assert_not_called()
        tm.close_trade.assert_not_called()

    def test_layer4_skips_when_bar_has_no_close(self):
        """_apply_layer4 skips if bar has no close field."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade)
        bar = {"ts": "2026-05-23T10:05:00Z"}  # no high/low/close

        engine._apply_layer4(trade, bar, bar["ts"])

        # Should not crash, and no calls
        tm.update_stop_with_audit.assert_not_called()

    def test_layer4_multiple_services_all_tighten(self):
        """All 4 TIGHTEN services return values → tightest applied for LONG."""
        trade = _make_trade(direction="LONG", stop=5235.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade)
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "MFE_PEAK",
                                        "new_stop": 5248.0, "reasoning_notes": "x"}), \
             patch.object(cci_flat_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "CCI_FLAT",
                                        "new_stop": 5244.0, "reasoning_notes": "x"}), \
             patch.object(swi_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "SWI_RED",
                                        "new_stop": 5246.0, "reasoning_notes": "x"}), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        # LONG: max(5248, 5244, 5246) = 5248
        assert calls[0][1]["new_stop"] == pytest.approx(5248.0)

    def test_layer4_exit_short_circuits_remaining_services(self):
        """TCCI EXIT → returns immediately; swi and day_type services NOT called."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        dir_change = {"type": "DIRECTION_CHANGE", "direction": "BEARISH"}
        swi = {"value": -5.0, "color": "red"}
        engine, tm = self._engine_with_woodies(
            trade, direction_change=dir_change, swi=swi, day_type="Normal"
        )
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        swi_mock = MagicMock(return_value=None)
        day_type_mock = MagicMock(return_value=None)
        with patch.object(tcci_cross_exit, "evaluate",
                          return_value={"action": "EXIT", "rule": "TCCI_CROSS",
                                        "reasoning_notes": "cross"}), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", swi_mock), \
             patch.object(day_type_targets_verify, "evaluate", day_type_mock):
            engine._apply_layer4(trade, bar, bar["ts"])

        tm.close_trade.assert_called_once()
        # swi_tighten and day_type_targets_verify were NOT called (short-circuit after TCCI EXIT)
        swi_mock.assert_not_called()
        day_type_mock.assert_not_called()

    def test_layer4_woodies_provider_error_nonfatal(self):
        """woodies_provider raising an exception is non-fatal."""
        def bad_provider():
            raise RuntimeError("DB down")

        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm, _ = _make_engine(trades=[trade], woodies_provider=bad_provider)
        engine._fetch_current_day_type = lambda: None
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            # Should not raise
            engine._apply_layer4(trade, bar, bar["ts"])

    def test_layer4_no_woodies_provider_empty_context(self):
        """When woodies_provider is None, context is empty (no crash)."""
        trade = _make_trade(direction="LONG", stop=5240.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm, _ = _make_engine(trades=[trade], woodies_provider=None)
        engine._fetch_current_day_type = lambda: None
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate", return_value=None), \
             patch.object(cci_flat_tighten, "evaluate", return_value=None), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])  # must not raise

    def test_layer4_short_tightest_is_min_candidate(self):
        """SHORT: tightest stop = min of candidates."""
        trade = _make_trade(direction="SHORT", stop=5280.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, tm = self._engine_with_woodies(trade, cci_history=[100.0, 102.0, 101.0])
        bar = {"high": 5265.0, "low": 5252.0, "close": 5255.0, "ts": "2026-05-23T10:05:00Z"}

        from backend.v9.services.layer4 import mfe_peak_tighten, tcci_cross_exit, cci_flat_tighten
        from backend.v9.services.layer4 import swi_tighten, day_type_targets_verify
        with patch.object(tcci_cross_exit, "evaluate", return_value=None), \
             patch.object(mfe_peak_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "MFE_PEAK",
                                        "new_stop": 5268.0, "reasoning_notes": "x"}), \
             patch.object(cci_flat_tighten, "evaluate",
                          return_value={"action": "TIGHTEN_STOP", "rule": "CCI_FLAT",
                                        "new_stop": 5264.0, "reasoning_notes": "x"}), \
             patch.object(swi_tighten, "evaluate", return_value=None), \
             patch.object(day_type_targets_verify, "evaluate", return_value=None):
            engine._apply_layer4(trade, bar, bar["ts"])

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        # SHORT: min(5268, 5264) = 5264 (tighter for SHORT)
        assert calls[0][1]["new_stop"] == pytest.approx(5264.0)

    def test_layer4_adapt_trade_has_both_stop_keys(self):
        """_adapt_trade_for_layer4 returns both 'stop' and 'stop_price' keys."""
        trade = _make_trade(direction="LONG", stop=5240.0, entry_price=5230.0)
        engine, _, _ = _make_engine()

        result = engine._adapt_trade_for_layer4(trade, bar_close=5255.0)

        assert "stop" in result
        assert "stop_price" in result
        assert result["stop"] == result["stop_price"] == 5240.0
        assert result["current_price"] == pytest.approx(5255.0)
        assert result["entry"] == pytest.approx(5230.0)


# ── D-094 Retrofit (10 tests) ─────────────────────────────────────────────────

class TestD094Retrofit:

    def test_engage_chandelier_idempotent(self):
        """_engage_chandelier called twice with different ATR → only first ATR kept."""
        trade = _make_trade(direction="LONG", stop=5230.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, _, _ = _make_engine()
        state = TrailState(max_high_since_t2=5265.0)
        bar = {"high": 5265.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=3.0):
            engine._engage_chandelier(trade, bar, state)
        # Second call with different ATR value
        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=9.9):
            engine._engage_chandelier(trade, bar, state)

        assert state.t2_atr_at_engage == pytest.approx(3.0)  # frozen from first call

    def test_engage_chandelier_dormant_when_atr_none(self):
        """_engage_chandelier leaves state dormant when compute returns None."""
        trade = _make_trade(direction="LONG", stop=5230.0,
                            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, _, _ = _make_engine()
        state = TrailState()
        bar = {"high": 5265.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}

        with patch("backend.v9.services.trail_engine.compute_continuous_atr14", return_value=None):
            engine._engage_chandelier(trade, bar, state)

        assert not state.chandelier_engaged
        assert state.t2_atr_at_engage is None

    def test_compute_chandelier_stop_v3_raises_corrupt(self):
        """_compute_chandelier_stop_v3 raises on engage=True but ATR=None."""
        trade = _make_trade()
        engine, _, _ = _make_engine()
        state = TrailState(chandelier_engaged=True, t2_atr_at_engage=None,
                           max_high_since_t2=5265.0)

        with pytest.raises(ValueError):
            engine._compute_chandelier_stop_v3(trade, state, "LONG")

    def test_reconstruct_state_from_db_builds_windows(self):
        """_reconstruct_state_from_db fills last_5_lows and last_5_highs from bars."""
        bars = [
            {"high": 5260.0 + i, "low": 5248.0 + i, "ts": f"2026-05-23T10:0{i}:00Z"}
            for i in range(7)
        ]
        fetch = MagicMock(return_value=bars)
        trade = _make_trade(entry_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc))
        engine, _, _ = _make_engine(fetch_bars_since=fetch)

        state = engine._reconstruct_state_from_db(trade)

        assert len(state.last_5_lows) == 5   # sliding window keeps last 5
        assert len(state.last_5_highs) == 5
        assert state.bars_processed == 7
        assert not state.chandelier_engaged     # stays dormant

    def test_bar_attr_reads_attr_and_dict(self):
        """_bar_attr reads from attribute-bearing object and plain dict."""
        class Obj:
            high = 5260.0

        assert TrailEngine._bar_attr(Obj(), "high") == pytest.approx(5260.0)
        assert TrailEngine._bar_attr({"high": 5262.0}, "high") == pytest.approx(5262.0)
        assert TrailEngine._bar_attr({}, "high") is None

    def test_update_mfe_tracks_mfe_high_and_low(self):
        """_update_mfe updates mfe_high and mfe_low from bar data."""
        trade = _make_trade(direction="LONG")
        trade.quality = {"mfe_high": 5260.0, "mfe_low": 5245.0}
        engine, _, _ = _make_engine()

        # Bar with new extremes
        bar = {"high": 5270.0, "low": 5240.0, "ts": "2026-05-23T10:05:00Z"}
        engine._update_mfe(trade, bar)

        assert trade.quality["mfe_high"] == pytest.approx(5270.0)
        assert trade.quality["mfe_low"] == pytest.approx(5240.0)

    def test_update_mfe_no_update_when_not_extreme(self):
        """_update_mfe leaves mfe_high/low unchanged when bar is not extreme."""
        trade = _make_trade(direction="LONG")
        trade.quality = {"mfe_high": 5280.0, "mfe_low": 5235.0}
        engine, _, _ = _make_engine()

        bar = {"high": 5265.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
        engine._update_mfe(trade, bar)

        assert trade.quality["mfe_high"] == pytest.approx(5280.0)  # unchanged
        assert trade.quality["mfe_low"] == pytest.approx(5235.0)   # unchanged

    def test_last_5_lows_slides_after_more_than_5(self):
        """After > 5 bars, last_5_lows retains only the most recent 5."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            t2_hit_ts=None,
            trail_state=_trail_state_5bar(
                lows=[5241.0, 5242.0, 5243.0, 5244.0, 5245.0],
                highs=[5260.0, 5261.0, 5262.0, 5263.0, 5264.0],
                bars_processed=5,
                trail_active=False,
            ),
        )
        engine, _, _ = _make_engine(trades=[trade])

        bar = {"high": 5266.0, "low": 5246.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        saved_lows = trade.quality["trail_state"]["last_5_lows"]
        assert len(saved_lows) == 5
        assert saved_lows[-1] == pytest.approx(5246.0)
        assert 5241.0 not in saved_lows   # oldest dropped

    def test_apply_tightest_stop_long_picks_max(self):
        """_apply_tightest_stop picks max candidate for LONG."""
        trade = _make_trade(direction="LONG", stop=5240.0)
        engine, tm, _ = _make_engine()

        candidates = [
            {"new_stop": 5243.0, "rule": "MFE_PEAK", "reasoning_notes": "a"},
            {"new_stop": 5248.0, "rule": "CCI_FLAT", "reasoning_notes": "b"},
            {"new_stop": 5245.0, "rule": "SWI_RED",  "reasoning_notes": "c"},
        ]
        engine._apply_tightest_stop(trade, candidates, "2026-05-23T10:05:00Z")

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5248.0)

    def test_apply_tightest_stop_short_picks_min(self):
        """_apply_tightest_stop picks min candidate for SHORT."""
        trade = _make_trade(direction="SHORT", stop=5280.0)
        engine, tm, _ = _make_engine()

        candidates = [
            {"new_stop": 5273.0, "rule": "MFE_PEAK", "reasoning_notes": "a"},
            {"new_stop": 5268.0, "rule": "CCI_FLAT", "reasoning_notes": "b"},
            {"new_stop": 5275.0, "rule": "SWI_RED",  "reasoning_notes": "c"},
        ]
        engine._apply_tightest_stop(trade, candidates, "2026-05-23T10:05:00Z")

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if "LAYER4" in str(c[1].get("reason", ""))]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5268.0)
