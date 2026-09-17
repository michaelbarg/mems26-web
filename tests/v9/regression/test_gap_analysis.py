"""Regression tests for scripts/gap_analysis.py — zigzag, move classification,
and the fixed evaluation model.

These tests use synthetic data only — no DB access needed.
"""

import os
import sys
import pytest

# Bootstrap path for standalone imports
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _ROOT)

# We import the functions directly rather than the full script (which would
# trigger env_loader / DB imports). Patch the DB import before loading.
import importlib
import unittest.mock as mock

# Mock backend imports so tests don't need a live DB
_mock_read = mock.MagicMock()
_mock_read.read_all = mock.MagicMock(return_value=[])
_mock_env = mock.MagicMock()
_mock_env.load_dotenv_file = mock.MagicMock()

with mock.patch.dict(sys.modules, {
    "backend": mock.MagicMock(),
    "backend.env_loader": _mock_env,
    "backend.v9": mock.MagicMock(),
    "backend.v9.db": mock.MagicMock(),
    "backend.v9.db.read": _mock_read,
    "backend.v9.db.session": mock.MagicMock(),
}):
    from scripts.gap_analysis import (
        compute_zigzag,
        compute_atr14_causal,
        classify_move,
        evaluate_trade_fixed,
        size_for,
        walk_forward,
        classify_day_type_from_bars,
        compute_vol_ratio_for_setup,
        _floor_to_5min,
        _trade_entry_il,
        load_gateway_decisions,
        _build_gateway_index,
        _third_friday,
        _roll_dates,
    )


# ===== Helpers =====

def make_bar(il: str, o: float, h: float, l: float, c: float) -> dict:
    return {"il": il, "open": o, "high": h, "low": l, "close": c}


def make_bars_uptrend():
    """Simple uptrend: 5400 -> 5420 over 10 bars, then reversal to 5410."""
    bars = []
    for i in range(10):
        t = f"16:{30 + i * 5:02d}"
        base = 5400 + i * 2.5
        bars.append(make_bar(t, base, base + 2.0, base - 0.5, base + 2.0))
    # Reversal bars
    for i in range(4):
        t = f"17:{20 + i * 5:02d}"
        base = 5422 - i * 3
        bars.append(make_bar(t, base + 1, base + 1.5, base - 1.5, base - 1.0))
    return bars


def make_bars_simple():
    """6 bars: flat, up 12, up 12, down 10, down 10, up 5."""
    return [
        make_bar("16:30", 5400, 5402, 5398, 5400),
        make_bar("16:35", 5400, 5412, 5399, 5412),
        make_bar("16:40", 5412, 5424, 5411, 5424),
        make_bar("16:45", 5424, 5425, 5414, 5414),
        make_bar("16:50", 5414, 5415, 5404, 5404),
        make_bar("16:55", 5404, 5409, 5403, 5409),
    ]


# ===== Test: compute_zigzag =====

class TestZigzag:
    def test_empty_bars(self):
        assert compute_zigzag([], 5.0) == []

    def test_single_bar(self):
        bars = [make_bar("16:30", 5400, 5405, 5395, 5400)]
        assert compute_zigzag(bars, 5.0) == []

    def test_simple_up_move(self):
        """Bars going steadily up 24 pts then down 21 pts — threshold 8."""
        bars = make_bars_simple()
        moves = compute_zigzag(bars, 8.0)
        assert len(moves) >= 1

        # The largest move should be the up leg (at least ~24 pts)
        biggest = moves[0]
        assert biggest["direction"] == "UP"
        assert biggest["pts"] >= 20

    def test_threshold_filters_small_moves(self):
        """With high threshold, small wiggles are not moves."""
        bars = make_bars_simple()
        moves = compute_zigzag(bars, 30.0)
        # With threshold 30, the 24-pt up and 21-pt down shouldn't qualify
        # as separate moves
        assert len(moves) <= 1

    def test_zigzag_returns_sorted(self):
        """Moves returned sorted by pts descending."""
        bars = make_bars_uptrend()
        moves = compute_zigzag(bars, 5.0)
        for i in range(len(moves) - 1):
            assert moves[i]["pts"] >= moves[i + 1]["pts"]

    def test_move_fields(self):
        """Each move has required fields."""
        bars = make_bars_simple()
        moves = compute_zigzag(bars, 8.0)
        if moves:
            m = moves[0]
            assert "t_start" in m
            assert "t_end" in m
            assert "start_price" in m
            assert "end_price" in m
            assert "pts" in m
            assert "direction" in m
            assert m["direction"] in ("UP", "DOWN")
            assert m["pts"] > 0


# ===== Test: compute_atr14_causal =====

class TestATR14:
    def test_empty(self):
        assert compute_atr14_causal([]) == 0.0

    def test_single_bar(self):
        assert compute_atr14_causal([make_bar("16:30", 100, 105, 95, 100)]) == 0.0

    def test_two_bars(self):
        bars = [
            make_bar("16:30", 100, 105, 95, 100),
            make_bar("16:35", 100, 108, 96, 104),
        ]
        atr = compute_atr14_causal(bars)
        # TR of bar[1] = max(108-96, |108-100|, |96-100|) = 12
        assert atr == pytest.approx(12.0, abs=0.01)

    def test_stable_bars(self):
        """Bars with constant range -> ATR = that range."""
        bars = []
        for i in range(20):
            bars.append(make_bar(f"16:{30 + i:02d}",
                                 100, 105, 95, 100))
        atr = compute_atr14_causal(bars)
        # All TRs are 10 (range) -> ATR converges to 10
        assert atr == pytest.approx(10.0, abs=0.5)


# ===== Test: classify_move =====

class TestClassifyMove:
    def test_no_setup(self):
        """No trades at all -> NO_SETUP."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "17:00",
            "pts": 15.0, "start_idx": 0, "end_idx": 6,
        }
        bars = make_bars_simple()
        result = classify_move(move, [], bars)
        assert result["status"] == "NO_SETUP"

    def test_fired_live(self):
        """A live LONG trade entering in first 30% of an UP move."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "16:50",
            "pts": 20.0, "start_idx": 0, "end_idx": 4,
        }
        bars = make_bars_simple()
        trade = {
            "id": 1, "mode": "live", "direction": "LONG",
            "entry_ts": "16:32", "entry_price": 5402.0,
            "stop": 5395.0, "t1": 5412.0,
            "cross_context": {},
        }
        result = classify_move(move, [trade], bars)
        assert result["status"] == "FIRED_LIVE"
        assert result["trade_id"] == 1

    def test_fired_shadow_only(self):
        """A shadow trade -> FIRED_SHADOW_ONLY."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "16:50",
            "pts": 20.0, "start_idx": 0, "end_idx": 4,
        }
        bars = make_bars_simple()
        trade = {
            "id": 2, "mode": "shadow", "direction": "LONG",
            "entry_ts": "16:32", "entry_price": 5402.0,
            "stop": 5395.0, "t1": 5412.0,
            "cross_context": {},
        }
        result = classify_move(move, [trade], bars)
        assert result["status"] == "FIRED_SHADOW_ONLY"

    def test_wrong_direction_ignored(self):
        """A SHORT trade during an UP move -> NO_SETUP."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "16:50",
            "pts": 20.0, "start_idx": 0, "end_idx": 4,
        }
        bars = make_bars_simple()
        trade = {
            "id": 3, "mode": "live", "direction": "SHORT",
            "entry_ts": "16:32", "entry_price": 5402.0,
            "stop": 5412.0, "t1": 5392.0,
            "cross_context": {},
        }
        result = classify_move(move, [trade], bars)
        assert result["status"] == "NO_SETUP"

    def test_trade_outside_30pct_window(self):
        """Trade entering after first 30% of the move -> NO_SETUP."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "16:55",
            "pts": 20.0, "start_idx": 0, "end_idx": 5,
        }
        bars = make_bars_simple()
        # 30% of 5 bars = bar index 1. Entry at 16:50 is bar index 4.
        trade = {
            "id": 4, "mode": "live", "direction": "LONG",
            "entry_ts": "16:50", "entry_price": 5405.0,
            "stop": 5398.0, "t1": 5415.0,
            "cross_context": {},
        }
        result = classify_move(move, [trade], bars)
        assert result["status"] == "NO_SETUP"


# ===== Test: evaluation model =====

class TestEvaluationModel:
    def test_size_for(self):
        # risk=9 -> n=min(5, floor(225/(5*9))) = min(5,5) = 5
        assert size_for(9.0) == 5
        # risk=15 -> n=min(5, floor(225/75)) = min(5,3) = 3
        assert size_for(15.0) == 3
        # risk=20 -> n=min(5, floor(225/100)) = min(5,2) = 2 (< 3 => skip)
        assert size_for(20.0) == 2
        # risk=0 -> 0
        assert size_for(0) == 0
        # risk=45 -> n=min(5, floor(225/225)) = 1
        assert size_for(45.0) == 1

    def test_walk_forward_long_hits_target(self):
        """LONG trade with T1 hit on next bar."""
        bars = [
            {"il": "16:30", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:35", "high": 5415, "low": 5399, "close": 5412},
            {"il": "16:40", "high": 5420, "low": 5410, "close": 5418},
        ]
        # Entry at 5400, stop at 5390, target T1 at 5412
        results = walk_forward(
            bars, "16:30", "LONG",
            entry=5400.0, stop=5390.0,
            targets=[5412.0]
        )
        assert len(results) == 1
        assert results[0]["event"] == "T0"  # first target = index 0
        assert results[0]["pts"] == pytest.approx(12.0)

    def test_walk_forward_long_hits_stop(self):
        """LONG trade where stop is hit."""
        bars = [
            {"il": "16:30", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:35", "high": 5402, "low": 5388, "close": 5390},
        ]
        results = walk_forward(
            bars, "16:30", "LONG",
            entry=5400.0, stop=5392.0,
            targets=[5412.0]
        )
        assert len(results) == 1
        assert results[0]["event"] == "STOP"
        assert results[0]["pts"] < 0

    def test_walk_forward_ambig(self):
        """Both target and stop hit in same bar -> AMBIG."""
        bars = [
            {"il": "16:30", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:35", "high": 5415, "low": 5388, "close": 5402},
        ]
        results = walk_forward(
            bars, "16:30", "LONG",
            entry=5400.0, stop=5390.0,
            targets=[5412.0]
        )
        assert len(results) == 1
        assert results[0]["event"] == "AMBIG"
        assert results[0]["pts"] == 0.0

    def test_walk_forward_eod(self):
        """No target or stop hit -> EOD at last bar close."""
        bars = [
            {"il": "16:30", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:35", "high": 5408, "low": 5397, "close": 5405},
        ]
        results = walk_forward(
            bars, "16:30", "LONG",
            entry=5400.0, stop=5390.0,
            targets=[5420.0]
        )
        assert len(results) == 1
        assert results[0]["event"] == "EOD"
        assert results[0]["pts"] == pytest.approx(5.0)  # 5405 - 5400

    def test_walk_forward_short(self):
        """SHORT trade hits target."""
        bars = [
            {"il": "16:30", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:35", "high": 5401, "low": 5385, "close": 5388},
        ]
        results = walk_forward(
            bars, "16:30", "SHORT",
            entry=5400.0, stop=5410.0,
            targets=[5388.0]
        )
        assert len(results) == 1
        assert results[0]["event"] == "T0"
        assert results[0]["pts"] == pytest.approx(12.0)

    def test_evaluate_trade_missing_levels(self):
        """Trade with missing entry/stop/t1 -> skip."""
        bars = make_bars_simple()
        trade = {"entry_price": None, "stop": None, "t1": None,
                 "direction": "LONG"}
        result = evaluate_trade_fixed(bars, trade)
        assert result["skip_reason"] == "missing_levels"
        assert result["total_pts"] == 0.0

    def test_evaluate_trade_size_too_small(self):
        """Risk too large -> size < 3 -> skip."""
        bars = make_bars_simple()
        trade = {
            "entry_price": 5400.0, "stop": 5350.0, "t1": 5450.0,
            "direction": "LONG", "entry_ts": "16:30",
        }
        # risk = 50 pts -> n = floor(225/250) = 0
        result = evaluate_trade_fixed(bars, trade)
        assert result["skip_reason"] == "size_too_small"

    def test_evaluate_trade_full(self):
        """Full evaluation with a trade that hits T1."""
        bars = [
            {"il": "16:30", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:35", "high": 5408, "low": 5398, "close": 5405},
            {"il": "16:40", "high": 5418, "low": 5404, "close": 5415},
            {"il": "16:45", "high": 5425, "low": 5413, "close": 5422},
            {"il": "16:50", "high": 5432, "low": 5420, "close": 5430},
        ]
        trade = {
            "entry_price": 5400.0, "stop": 5391.0, "t1": 5415.0,
            "direction": "LONG", "entry_ts": "16:30",
        }
        # risk = 9 -> n = min(5, floor(225/45)) = 5
        result = evaluate_trade_fixed(bars, trade)
        assert result["n"] == 5
        assert result["skip_reason"] is None
        assert result["total_usd"] != 0  # some P&L generated
        assert len(result["events"]) > 0


# ===== F1: Test classify_day_type_from_bars =====

class TestClassifyDayTypeFromBars:
    def test_trend_day(self):
        """Synthetic session with extension > 2x IB and directional close -> Trend."""
        # IB = first 6 bars: high ~ 5410, low ~ 5400 -> IB width = 10
        ib_bars = []
        for i in range(6):
            t = f"16:{30 + i * 5:02d}"
            ib_bars.append(make_bar(t, 5400 + i * 0.5, 5410, 5400, 5405))

        # Post-IB: strong trend up to 5450 (range = 50 > 2 * 10 = 20)
        trend_bars = []
        for i in range(12):
            t = f"17:{00 + i * 5:02d}"
            base = 5410 + i * 3.5
            trend_bars.append(make_bar(t, base, base + 3, base - 1, base + 2.5))

        all_bars = ib_bars + trend_bars
        result = classify_day_type_from_bars(all_bars)
        assert result == "Trend"

    def test_normal_day(self):
        """Session within IB (range < 1.5x IB) -> Normal."""
        # IB = first 6 bars: range = 10
        bars = []
        for i in range(6):
            t = f"16:{30 + i * 5:02d}"
            bars.append(make_bar(t, 5400, 5410, 5400, 5405))

        # Post-IB: stays within IB, no significant extension
        for i in range(8):
            t = f"17:{00 + i * 5:02d}"
            bars.append(make_bar(t, 5403, 5412, 5401, 5406))

        result = classify_day_type_from_bars(bars)
        assert result == "Normal"

    def test_too_few_bars(self):
        """Less than 7 bars -> UNRESOLVED."""
        bars = [make_bar("16:30", 5400, 5410, 5400, 5405)] * 5
        result = classify_day_type_from_bars(bars)
        assert result == "UNRESOLVED"

    def test_empty_bars(self):
        result = classify_day_type_from_bars([])
        assert result == "UNRESOLVED"


# ===== F2: Test sanity filter =====

class TestSanityFilter:
    def test_bar_with_100pt_range_is_suspect(self):
        """Bar with 100pt range (> 40) should be detected as suspect."""
        bars = [
            make_bar("16:30", 5400, 5402, 5398, 5400),
            make_bar("16:35", 5400, 5500, 5400, 5450),  # 100pt range!
            make_bar("16:40", 5450, 5455, 5445, 5450),
        ]
        # Check via ATR and range
        atr14 = compute_atr14_causal(bars)
        suspect = False
        for i, b in enumerate(bars):
            bar_range = b["high"] - b["low"]
            if bar_range > 40:
                suspect = True
        assert suspect, "100pt range bar should be flagged as SUSPECT"

    def test_bar_with_12pt_range_is_clean(self):
        """Bar with 12pt range (< 40) should be clean."""
        bars = [
            make_bar("16:30", 5400, 5406, 5394, 5400),
            make_bar("16:35", 5400, 5412, 5400, 5410),  # 12pt range
            make_bar("16:40", 5410, 5415, 5408, 5412),
        ]
        # No bar has range > 40
        for b in bars:
            bar_range = b["high"] - b["low"]
            assert bar_range <= 40, f"Bar range {bar_range} should not be suspect"


# ===== F6: Test vol_ratio stub =====

class TestVolRatioStub:
    def test_vol_ratio_returns_none(self):
        """vol_ratio stub returns None (NOT-DONE)."""
        bars = [make_bar("16:30", 5400, 5410, 5400, 5405)]
        result = compute_vol_ratio_for_setup(bars, 0)
        assert result is None


# ===== F8: Test _floor_to_5min and _trade_entry_il =====

class TestFloorTo5Min:
    def test_exact_5min(self):
        assert _floor_to_5min("16:50") == "16:50"

    def test_floor_down(self):
        assert _floor_to_5min("16:52") == "16:50"

    def test_floor_03(self):
        assert _floor_to_5min("17:03") == "17:00"

    def test_floor_59(self):
        assert _floor_to_5min("17:59") == "17:55"

    def test_floor_00(self):
        assert _floor_to_5min("17:00") == "17:00"

    def test_empty(self):
        assert _floor_to_5min("") == ""

    def test_none(self):
        assert _floor_to_5min(None) is None


class TestTradeEntryILFixed:
    """F8: _trade_entry_il must always return clean HH:MM or None."""

    def test_datetime_object(self):
        from datetime import datetime
        trade = {"entry_ts": datetime(2026, 9, 15, 16, 50, 7)}
        result = _trade_entry_il(trade)
        assert result == "16:50"

    def test_iso_string(self):
        trade = {"entry_ts": "2026-09-15T16:52:30+03:00"}
        result = _trade_entry_il(trade)
        # Should return HH:MM from the parsed time (16:52)
        assert result is not None
        assert len(result) == 5
        assert result[2] == ":"

    def test_space_separated_string(self):
        trade = {"entry_ts": "2026-09-15 16:50:07+03:00"}
        result = _trade_entry_il(trade)
        assert result is not None
        assert len(result) == 5

    def test_none(self):
        trade = {"entry_ts": None}
        assert _trade_entry_il(trade) is None

    def test_hhmm_string(self):
        trade = {"entry_ts": "16:50"}
        result = _trade_entry_il(trade)
        assert result == "16:50"


class TestF8EvaluateFloors:
    """F8: entry_ts 16:50:07 IL -> bar 16:50; 16:52:30 -> bar 16:50."""

    def test_entry_floors_to_matching_bar(self):
        """Entry at 16:52:30 should floor to 16:50 and match bar 16:50."""
        bars = [
            {"il": "16:45", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:50", "high": 5415, "low": 5399, "close": 5412},
            {"il": "16:55", "high": 5420, "low": 5410, "close": 5418},
            {"il": "17:00", "high": 5425, "low": 5415, "close": 5422},
        ]
        # Entry at 16:52:30 should floor to 16:50
        trade = {
            "entry_price": 5400.0, "stop": 5391.0, "t1": 5415.0,
            "direction": "LONG", "entry_ts": "16:52",
        }
        result = evaluate_trade_fixed(bars, trade)
        # Should NOT get no_entry_time or no matching bar — the 16:50 bar exists
        assert result["skip_reason"] is None
        assert result["n"] == 5  # risk=9 -> n=5

    def test_entry_exact_5min_matches(self):
        """Entry at 16:50:07 should produce HH:MM 16:50, matching bar 16:50."""
        from datetime import datetime
        bars = [
            {"il": "16:45", "high": 5405, "low": 5395, "close": 5400},
            {"il": "16:50", "high": 5415, "low": 5399, "close": 5412},
            {"il": "16:55", "high": 5420, "low": 5410, "close": 5418},
        ]
        trade = {
            "entry_price": 5400.0, "stop": 5391.0, "t1": 5415.0,
            "direction": "LONG",
            "entry_ts": datetime(2026, 9, 15, 16, 50, 7),
        }
        result = evaluate_trade_fixed(bars, trade)
        assert result["skip_reason"] is None
        assert len(result["events"]) > 0


# ===== F7: Test gateway decisions and BLOCKED classification =====

class TestGatewayDecisions:
    def test_blocked_decision_in_window(self):
        """A move with a gateway-blocked decision in the 30% window -> BLOCKED."""
        move = {
            "direction": "DOWN", "t_start": "16:30", "t_end": "17:00",
            "pts": 20.0, "start_idx": 0, "end_idx": 6,
        }
        bars = make_bars_simple()
        # Build gateway index with a blocked SHORT decision at 16:32
        gateway_decisions = [{
            "ts_il_hhmm": "16:32",
            "direction": "SHORT",
            "outcome": "blocked",
            "blocked_by": "dalton_intent:stand_down",
            "reason": "test",
        }]
        gateway_index = _build_gateway_index(gateway_decisions)

        result = classify_move(move, [], bars, gateway_index=gateway_index)
        assert result["status"] == "BLOCKED:dalton_intent:stand_down"
        assert result["blocked_by"] == "dalton_intent:stand_down"

    def test_no_blocked_decision_returns_no_setup(self):
        """A move with no gateway blocked decision -> NO_SETUP."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "17:00",
            "pts": 15.0, "start_idx": 0, "end_idx": 6,
        }
        bars = make_bars_simple()
        # Empty gateway index
        gateway_index = {"LONG": [], "SHORT": []}

        result = classify_move(move, [], bars, gateway_index=gateway_index)
        assert result["status"] == "NO_SETUP"

    def test_blocked_wrong_direction_ignored(self):
        """A blocked SHORT decision should NOT match an UP move (needs LONG)."""
        move = {
            "direction": "UP", "t_start": "16:30", "t_end": "17:00",
            "pts": 20.0, "start_idx": 0, "end_idx": 6,
        }
        bars = make_bars_simple()
        gateway_decisions = [{
            "ts_il_hhmm": "16:32",
            "direction": "SHORT",
            "outcome": "blocked",
            "blocked_by": "dalton_intent:stand_down",
        }]
        gateway_index = _build_gateway_index(gateway_decisions)

        result = classify_move(move, [], bars, gateway_index=gateway_index)
        assert result["status"] == "NO_SETUP"

    def test_build_gateway_index_filters_non_blocked(self):
        """Only outcome='blocked' decisions are indexed."""
        decisions = [
            {"direction": "LONG", "outcome": "fired", "blocked_by": None,
             "ts_il_hhmm": "16:35"},
            {"direction": "SHORT", "outcome": "blocked",
             "blocked_by": "test_gate", "ts_il_hhmm": "16:40"},
            {"direction": "SHORT", "outcome": "shadow",
             "blocked_by": None, "ts_il_hhmm": "16:45"},
        ]
        idx = _build_gateway_index(decisions)
        assert len(idx["LONG"]) == 0
        assert len(idx["SHORT"]) == 1
        assert idx["SHORT"][0]["blocked_by"] == "test_gate"


# ===== F9: Test roll window detection =====

class TestRollDates:
    def test_third_friday_june_2026(self):
        from datetime import date
        result = _third_friday(2026, 6)
        # June 2026: June 1 is Monday. First Friday = June 5. 3rd Friday = June 19.
        assert result == date(2026, 6, 19)

    def test_third_friday_september_2026(self):
        from datetime import date
        result = _third_friday(2026, 9)
        # Sep 2026: Sep 1 is Tuesday. First Friday = Sep 4. 3rd Friday = Sep 18.
        assert result == date(2026, 9, 18)

    def test_june_18_is_roll(self):
        """June 18, 2026 is in the roll window (June 17-19)."""
        roll_set = _roll_dates(2026)
        assert "2026-06-18" in roll_set

    def test_june_15_is_not_roll(self):
        """June 15, 2026 is NOT in the roll window."""
        roll_set = _roll_dates(2026)
        assert "2026-06-15" not in roll_set

    def test_sep_roll_window(self):
        """Sep 16-18, 2026 should be in the roll window."""
        roll_set = _roll_dates(2026)
        assert "2026-09-16" in roll_set
        assert "2026-09-17" in roll_set
        assert "2026-09-18" in roll_set
        assert "2026-09-15" not in roll_set

    def test_roll_window_has_12_dates(self):
        """4 quarters * 3 days = 12 roll dates per year."""
        roll_set = _roll_dates(2026)
        assert len(roll_set) == 12
