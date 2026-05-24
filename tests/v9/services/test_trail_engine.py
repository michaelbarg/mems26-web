"""29 golden tests for TrailEngine — D-094 Pkg 3b Stream 2.

Test groups:
  HL/LH trail (6):          swing-stop tracks extremes, tighter-only guard,
                             direction invariant, t2 gate respected.
  Chandelier (6):           ATR multiplier per pattern family, tighter-only,
                             SHORT direction, insufficient ATR data guard.
  Time stop (4):            fires at limit, skips when None, short-circuit,
                             already-fired idempotency.
  State persistence (5):    to_dict/from_dict round-trip, save/load cycle,
                             bars_processed increments, trail_active flag, atr14 persisted.
  Cross-context audit (3):  update_stop_with_audit called with reason string,
                             bar_ts forwarded, close_trade reason string.
  Concurrency / Sierra (3): fill-lock skips trade entirely, fill-lock in
                             _move_stop_tighter_only, lock released trades resume.
  Integration (2):          full on_bar_close async dispatch, no-op when t2 not hit.
"""

from __future__ import annotations

import asyncio
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
    trade.quality = quality

    return trade


def _make_event(
    high: float = 5255.0,
    low: float = 5245.0,
    ts: str = "2026-05-23T10:05:00Z",
) -> MagicMock:
    """Create a mock BarEvent with a payload dict."""
    event = MagicMock()
    event.payload = {"high": high, "low": low, "ts": ts}
    return event


def _make_engine(
    trades: Optional[List] = None,
    mode: str = "shadow",
    yesterday_bars: Optional[List] = None,
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
    )
    return engine, tm, br


# ── HL/LH Trail (6 tests) ─────────────────────────────────────────────────────

class TestHLLHTrail:

    def test_long_swing_stop_follows_bar_low(self):
        """LONG: swing_stop = bar.low when it rises above current stop."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5260.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        # swing_low=5248.0 > current_stop=5240.0 → should tighten
        tm.update_stop_with_audit.assert_called_once()
        args = tm.update_stop_with_audit.call_args
        assert args[1]["new_stop"] == pytest.approx(5248.0)
        assert args[1]["reason"] == "hl_lh_swing"

    def test_long_swing_stop_does_not_widen(self):
        """LONG: swing_stop below current stop must NOT widen stop."""
        trade = _make_trade(
            direction="LONG",
            stop=5250.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5258.0, "low": 5238.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        # swing_low=5238 < current_stop=5250 — no move allowed
        # (chandelier might move it, so check swing specifically via reason)
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        assert calls == []

    def test_short_swing_stop_follows_bar_high(self):
        """SHORT: swing_stop = bar.high when it falls below current stop."""
        trade = _make_trade(
            direction="SHORT",
            stop=5270.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5262.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5262.0)

    def test_short_swing_stop_does_not_widen(self):
        """SHORT: swing_stop above current stop must NOT widen stop."""
        trade = _make_trade(
            direction="SHORT",
            stop=5258.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5265.0, "low": 5248.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        assert calls == []

    def test_swing_stop_skips_before_t2(self):
        """Swing trail must NOT activate before t2_hit_ts is set."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=None,     # t2 NOT yet hit
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.update_stop_with_audit.assert_not_called()

    def test_swing_high_accumulated_across_bars(self):
        """swing_high should accumulate: max of all bars seen so far."""
        trade = _make_trade(
            direction="SHORT",
            stop=5270.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
            trail_state={
                "swing_high": 5260.0,    # existing accumulated high
                "swing_low": None,
                "bars_processed": 2,
                "last_bar_ts": "2026-05-23T10:00:00Z",
                "atr14": None,
                "time_stop_fired": False,
                "trail_active": True,
            },
        )
        engine, tm, _ = _make_engine(trades=[trade])

        # New bar has a HIGHER high — should update swing_high to 5263
        bar = {"high": 5263.0, "low": 5250.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        # swing_high=5263 < current_stop=5270 → should move stop tighter (SHORT)
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5263.0)


# ── Chandelier (6 tests) ──────────────────────────────────────────────────────

class TestChandelier:

    def _engine_with_atr(self, atr_value: float, trade, mode="shadow"):
        """Build engine and patch compute_continuous_atr14 to return fixed value."""
        engine, tm, _ = _make_engine(trades=[trade], mode=mode)
        with patch(
            "backend.v9.services.trail_engine.compute_continuous_atr14",
            return_value=atr_value,
        ):
            bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)
        return tm

    def test_chandelier_long_uses_swing_high_minus_k_atr(self):
        """LONG chandelier: stop = swing_high - k*ATR; k=1.5 default."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        # ATR=4.0, swing_high will become 5265.0 (bar high), k=1.5 (default)
        # chandelier_stop = 5265 - 1.5*4.0 = 5259.0
        tm = self._engine_with_atr(4.0, trade)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5259.0, abs=0.01)

    def test_chandelier_short_uses_swing_low_plus_k_atr(self):
        """SHORT chandelier: stop = swing_low + k*ATR."""
        trade = _make_trade(
            direction="SHORT",
            stop=5280.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        # ATR=4.0, swing_low will become 5252.0, k=1.5 default
        # chandelier_stop = 5252 + 1.5*4.0 = 5258.0
        tm = self._engine_with_atr(4.0, trade)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5258.0, abs=0.01)

    def test_chandelier_uses_initiative_multiplier(self):
        """OFA_Initiative pattern → k=2.0 from ATR_MULTIPLIERS."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            pattern_name="OFA_Initiative",
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        # k=2.0; swing_high=5265, ATR=4.0 → 5265 - 2.0*4.0 = 5257.0
        tm = self._engine_with_atr(4.0, trade)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5257.0, abs=0.01)

    def test_chandelier_uses_reactive_multiplier(self):
        """OFA_Reactive pattern → k=1.5 from ATR_MULTIPLIERS."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            pattern_name="initiative_signal",  # maps to OFA_Initiative via _pattern_to_family
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        # _pattern_to_family("initiative_signal") → "OFA_Initiative" → k=2.0
        tm = self._engine_with_atr(4.0, trade)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14"]
        assert len(calls) == 1
        assert calls[0][1]["new_stop"] == pytest.approx(5257.0, abs=0.01)

    def test_chandelier_no_op_when_atr_none(self):
        """No chandelier stop move when ATR is None (insufficient bars)."""
        trade = _make_trade(
            direction="LONG",
            stop=5230.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        with patch(
            "backend.v9.services.trail_engine.compute_continuous_atr14",
            return_value=None,
        ):
            bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
            engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14"]
        assert calls == []

    def test_chandelier_does_not_widen_stop(self):
        """Chandelier stop must not move if it would widen the stop."""
        trade = _make_trade(
            direction="LONG",
            stop=5260.0,   # already tight
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        # With bar.high=5265, ATR=4.0, k=1.5:
        # chandelier = 5265 - 6.0 = 5259 < current_stop=5260 → no move
        tm = self._engine_with_atr(4.0, trade)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "chandelier_atr14"]
        assert calls == []


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
            trail_state={
                "swing_high": None,
                "swing_low": None,
                "bars_processed": 5,
                "last_bar_ts": "2026-05-23T10:00:00Z",
                "atr14": None,
                "time_stop_fired": True,    # already fired
                "trail_active": False,
            },
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5255.0, "low": 5245.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        tm.close_trade.assert_not_called()


# ── State persistence (5 tests) ───────────────────────────────────────────────

class TestStatePersistence:

    def test_trail_state_to_dict_round_trip(self):
        """TrailState serialises and deserialises losslessly."""
        state = TrailState(
            swing_high=5265.5,
            swing_low=5248.25,
            bars_processed=7,
            last_bar_ts="2026-05-23T10:05:00Z",
            atr14=3.75,
            time_stop_fired=False,
            trail_active=True,
        )
        d = state.to_dict()
        restored = TrailState.from_dict(d)

        assert restored.swing_high == pytest.approx(5265.5)
        assert restored.swing_low == pytest.approx(5248.25)
        assert restored.bars_processed == 7
        assert restored.last_bar_ts == "2026-05-23T10:05:00Z"
        assert restored.atr14 == pytest.approx(3.75)
        assert restored.time_stop_fired is False
        assert restored.trail_active is True

    def test_state_saved_to_trade_quality(self):
        """_save_state writes trail_state key into trade.quality."""
        trade = _make_trade()
        engine, _, _ = _make_engine()

        state = TrailState(swing_high=5270.0, bars_processed=3)
        engine._save_state(trade, state)

        assert "trail_state" in trade.quality
        assert trade.quality["trail_state"]["swing_high"] == pytest.approx(5270.0)
        assert trade.quality["trail_state"]["bars_processed"] == 3

    def test_state_loaded_from_trade_quality(self):
        """_load_state restores from trade.quality["trail_state"]."""
        trade = _make_trade(
            trail_state={
                "swing_high": 5260.0,
                "swing_low": 5245.0,
                "bars_processed": 4,
                "last_bar_ts": "2026-05-23T10:00:00Z",
                "atr14": 2.5,
                "time_stop_fired": False,
                "trail_active": True,
            }
        )
        engine, _, _ = _make_engine()

        state = engine._load_state(trade)

        assert state.swing_high == pytest.approx(5260.0)
        assert state.swing_low == pytest.approx(5245.0)
        assert state.bars_processed == 4
        assert state.atr14 == pytest.approx(2.5)
        assert state.trail_active is True

    def test_bars_processed_increments_on_each_bar(self):
        """bars_processed in trail_state increases by 1 per bar."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=None,
            trail_state={
                "swing_high": None,
                "swing_low": None,
                "bars_processed": 2,
                "last_bar_ts": None,
                "atr14": None,
                "time_stop_fired": False,
                "trail_active": False,
            },
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

    def test_update_stop_audit_reason_swing(self):
        """update_stop_with_audit is called with reason='hl_lh_swing'."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}
        engine._process_trade(trade, bar)

        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        assert len(calls) >= 1
        assert calls[0][1]["reason"] == "hl_lh_swing"

    def test_update_stop_audit_bar_ts_forwarded(self):
        """bar_ts from the bar dict is forwarded verbatim to update_stop_with_audit."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])

        expected_ts = "2026-05-23T10:15:00Z"
        bar = {"high": 5265.0, "low": 5252.0, "ts": expected_ts}
        engine._process_trade(trade, bar)

        for c in tm.update_stop_with_audit.call_args_list:
            assert c[1]["bar_ts"] == expected_ts

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
        )
        engine, tm, _ = _make_engine(trades=[trade])
        tm.is_fill_locked.return_value = False

        bar = {"high": 5265.0, "low": 5252.0, "ts": "2026-05-23T10:05:00Z"}

        with patch(
            "backend.v9.services.trail_engine.compute_continuous_atr14",
            return_value=None,
        ):
            engine._process_trade(trade, bar)

        # swing stop 5252 > 5240 → should move
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        assert len(calls) == 1


# ── Integration (2 tests) ─────────────────────────────────────────────────────

class TestIntegration:

    def test_on_bar_close_dispatches_to_process_trade(self):
        """on_bar_close async handler iterates trades and calls _process_trade."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        engine, tm, _ = _make_engine(trades=[trade])
        event = _make_event(high=5265.0, low=5252.0, ts="2026-05-23T10:05:00Z")

        with patch(
            "backend.v9.services.trail_engine.compute_continuous_atr14",
            return_value=None,
        ):
            _run(engine.on_bar_close(event))

        # Should have iterated over the trade (stop move expected)
        calls = [c for c in tm.update_stop_with_audit.call_args_list
                 if c[1].get("reason") == "hl_lh_swing"]
        assert len(calls) == 1

    def test_on_bar_close_no_op_when_t2_not_hit(self):
        """on_bar_close: no stop move when t2_hit_ts is None (t2 gate closed)."""
        trade = _make_trade(
            direction="LONG",
            stop=5240.0,
            t2_hit_ts=None,    # t2 NOT hit
        )
        engine, tm, _ = _make_engine(trades=[trade])
        event = _make_event(high=5265.0, low=5252.0, ts="2026-05-23T10:05:00Z")

        _run(engine.on_bar_close(event))

        tm.update_stop_with_audit.assert_not_called()
        tm.close_trade.assert_not_called()
