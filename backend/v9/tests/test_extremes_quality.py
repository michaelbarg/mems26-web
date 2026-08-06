"""Tests for extremes_quality — excess/poor high/low detection.

Invariants:
1. Rule-1: no bars / <3 bars → None (never guess)
2. Excess: tail ≥2pt OR ≥1.5×body, close retreats, no revisit K bars
3. Poor: tail ≤0.5pt, ≥2 touches at extreme
4. Neutral: ambiguous / insufficient evidence
5. High and low classified independently
"""

import pytest
from backend.v9.systems.extremes_quality import (
    classify_session_extremes, classify_extremes_live,
)


def _bar(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c}


class TestRule1:
    def test_empty_bars_returns_none(self):
        assert classify_session_extremes([]) is None

    def test_two_bars_returns_none(self):
        assert classify_session_extremes([_bar(100, 102, 99, 101)] * 2) is None

    def test_three_bars_returns_result(self):
        result = classify_session_extremes([
            _bar(100, 102, 99, 101),
            _bar(101, 103, 100, 102),
            _bar(102, 104, 101, 103),
        ])
        assert result is not None

    def test_live_wrapper_empty_returns_empty_dict(self):
        assert classify_extremes_live([]) == {}


class TestExcessHigh:
    def test_long_upper_wick_excess(self):
        """Bar with 3pt upper tail, close retreats, no revisit → EXCESS."""
        bars = [
            _bar(100, 100.5, 99, 100.25),   # normal
            _bar(100, 105, 99.5, 101),       # high bar: tail=4pt, close retreats
            _bar(101, 102, 100, 101.5),      # no revisit of 105 area
            _bar(101, 101.5, 100, 101),      # no revisit
            _bar(101, 101, 100, 100.5),      # no revisit
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality == "EXCESS"
        assert result.high.tail_pts >= 2.0

    def test_tail_by_body_ratio(self):
        """Tail = 1.8pt but body = 0.5pt → ratio 3.6× ≥ 1.5 → EXCESS."""
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 102.3, 99.8, 100.5),   # tail=1.8, body=0.5 → ratio 3.6
            _bar(100, 100.5, 99, 100),
            _bar(100, 100.5, 99, 100),
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality == "EXCESS"

    def test_revisited_high_not_excess(self):
        """Even with long tail, revisiting the extreme disqualifies excess."""
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 105, 99, 101),          # high bar with tail
            _bar(101, 104.8, 100, 102),       # revisits 105 area (within 0.5)
            _bar(101, 101, 100, 100.5),
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality != "EXCESS"

    def test_close_doesnt_retreat_not_excess(self):
        """Close at the high → not a rejection."""
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 105, 99, 105),          # close AT high — no retreat
            _bar(101, 102, 100, 101),
            _bar(101, 101, 100, 100.5),
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality != "EXCESS"


class TestExcessLow:
    def test_long_lower_wick_excess(self):
        """Bar with 3pt lower tail, close retreats up → EXCESS low."""
        bars = [
            _bar(100, 101, 99, 100.5),
            _bar(100, 101, 96, 99.5),         # low bar: tail=min(100,99.5)-96=3.5pt
            _bar(100, 101, 99, 100),           # no revisit of 96
            _bar(100, 101, 99, 100.5),
        ]
        result = classify_session_extremes(bars)
        assert result.low.quality == "EXCESS"
        assert result.low.tail_pts >= 2.0


class TestPoorHigh:
    def test_flat_top_multiple_touches(self):
        """Tiny tail + multiple bars touching the high → POOR."""
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 103.2, 99, 103),        # high=103.2, tail=0.2, close near high
            _bar(102, 103.2, 101, 102.5),     # touches same high
            _bar(102, 103.1, 101, 102),        # within 0.25 of 103.2
            _bar(101, 102, 100, 101),
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality == "POOR"
        assert result.high.touches >= 2


class TestPoorLow:
    def test_flat_bottom_multiple_touches(self):
        """Tiny tail + multiple bars touching the low → POOR."""
        bars = [
            _bar(100, 101, 99, 100.5),
            _bar(99.5, 101, 97.1, 97.3),     # low=97.1, tail=0.2
            _bar(98, 100, 97.1, 98.5),        # touches same low
            _bar(98, 99, 97.2, 98),            # within 0.25
            _bar(98, 99, 98, 98.5),
        ]
        result = classify_session_extremes(bars)
        assert result.low.quality == "POOR"
        assert result.low.touches >= 2


class TestNeutral:
    def test_moderate_tail_one_touch_neutral(self):
        """1.5pt tail, only 1 touch → NEUTRAL (between excess and poor)."""
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 103, 99.5, 101.5),      # tail=1.5pt (below excess threshold)
            _bar(101, 102, 100, 101),
            _bar(101, 101.5, 100, 101),
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality == "NEUTRAL"

    def test_independent_classification(self):
        """High can be EXCESS while low is NEUTRAL."""
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 106, 99, 101),           # excess high (6pt tail)
            _bar(101, 102, 100, 101.5),
            _bar(101, 101.5, 100, 101),
        ]
        result = classify_session_extremes(bars)
        assert result.high.quality == "EXCESS"
        # Low has no special characteristics
        assert result.low.quality in ("NEUTRAL", "POOR")


class TestLiveWrapper:
    def test_returns_all_fields(self):
        bars = [
            _bar(100, 100.5, 99, 100),
            _bar(100, 105, 96, 101),
            _bar(101, 102, 99, 100.5),
            _bar(100, 101, 99, 100),
        ]
        result = classify_extremes_live(bars)
        assert "high_quality" in result
        assert "low_quality" in result
        assert "session_high" in result
        assert "session_low" in result
        assert "high_tail_pts" in result
        assert "low_tail_pts" in result
        assert result["session_high"] == 105
        assert result["session_low"] == 96
