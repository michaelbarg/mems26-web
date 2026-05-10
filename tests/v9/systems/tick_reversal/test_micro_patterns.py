"""Tests for tick_reversal micro-pattern detectors.

Coverage targets: >85% for all 5 micro-patterns.
Tests use mock footprint data with bid/ask levels, delta, volume.
"""

import pytest
from backend.v9.systems.tick_reversal.schemas import (
    BarInput, ContextResult, MicroPatternResult,
)
from backend.v9.systems.tick_reversal.micro_patterns import (
    detect_accumulation_breakout,
    detect_v_shape_reversal,
    detect_failed_test,
    detect_stair_step,
    detect_compression_pop,
    detect_all_micro_patterns,
    ALL_MICRO_PATTERNS,
)


# ── Helpers ──────────────────────────────────────────────────────

def make_bar(
    o=5246.0, h=5248.0, l=5245.0, c=5247.0, vol=1000,
    ask_vol=600, bid_vol=400, delta=200, ts="2026-05-09T13:42:30Z",
    tick_size=15, footprint=None,
) -> BarInput:
    return BarInput(
        ts=ts, o=o, h=h, l=l, c=c, vol=vol,
        ask_vol=ask_vol, bid_vol=bid_vol, delta=delta,
        tick_size=tick_size, footprint=footprint,
    )


def make_up_bar(base=5246.0, spread=2.0, vol=1000, idx=0) -> BarInput:
    o = base + idx * spread * 0.3
    c = o + spread
    return make_bar(
        o=o, h=c + 0.25, l=o - 0.25, c=c, vol=vol,
        ask_vol=int(vol * 0.7), bid_vol=int(vol * 0.3),
        delta=int(vol * 0.4), ts=f"2026-05-09T13:{40 + idx}:00Z",
    )


def make_down_bar(base=5248.0, spread=2.0, vol=1000, idx=0) -> BarInput:
    o = base - idx * spread * 0.3
    c = o - spread
    return make_bar(
        o=o, h=o + 0.25, l=c - 0.25, c=c, vol=vol,
        ask_vol=int(vol * 0.3), bid_vol=int(vol * 0.7),
        delta=-int(vol * 0.4), ts=f"2026-05-09T13:{40 + idx}:00Z",
    )


def make_flat_bar(base=5247.0, idx=0) -> BarInput:
    return make_bar(
        o=base - 0.25, h=base + 0.5, l=base - 0.5, c=base + 0.25,
        vol=500, ask_vol=260, bid_vol=240, delta=20,
        ts=f"2026-05-09T13:{30 + idx}:00Z",
    )


# ════════════════════════════════════════════════════════════
# REGISTRY
# ════════════════════════════════════════════════════════════

class TestRegistry:
    def test_5_patterns_registered(self):
        assert len(ALL_MICRO_PATTERNS) == 5

    def test_pattern_ids(self):
        ids = [name for name, _ in ALL_MICRO_PATTERNS]
        assert "accumulation_breakout" in ids
        assert "v_shape_reversal" in ids
        assert "failed_test" in ids
        assert "stair_step" in ids
        assert "compression_pop" in ids

    def test_detect_all_returns_5(self):
        bar = make_bar()
        bars = [make_bar(ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        bars.append(bar)
        ctx = ContextResult()
        results = detect_all_micro_patterns(bar, bars, ctx)
        assert len(results) == 5
        assert all(isinstance(r, MicroPatternResult) for r in results)


# ════════════════════════════════════════════════════════════
# PATTERN 1: ACCUMULATION + BREAKOUT
# ════════════════════════════════════════════════════════════

class TestAccumulationBreakout:
    def test_breakout_up_detected(self):
        bars = [make_flat_bar(idx=i) for i in range(7)]
        breakout = make_bar(o=5247.0, h=5250.0, l=5247.0, c=5249.5)
        bars.append(breakout)
        ctx = ContextResult(accumulation_active=True, accumulation_bars=7, accumulation_range_ticks=4)
        result = detect_accumulation_breakout(breakout, bars, ctx)
        assert result.detected is True
        assert result.direction == "LONG"
        assert result.strength > 0
        assert result.trigger_price is not None
        assert result.invalidation_price is not None

    def test_breakout_down_detected(self):
        bars = [make_flat_bar(idx=i) for i in range(7)]
        breakout = make_bar(o=5247.0, h=5247.5, l=5244.0, c=5244.5)
        bars.append(breakout)
        ctx = ContextResult(accumulation_active=True, accumulation_bars=7, accumulation_range_ticks=4)
        result = detect_accumulation_breakout(breakout, bars, ctx)
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_no_accumulation(self):
        bars = [make_up_bar(idx=i) for i in range(5)]
        bar = make_up_bar(idx=5)
        bars.append(bar)
        ctx = ContextResult(accumulation_active=False)
        result = detect_accumulation_breakout(bar, bars, ctx)
        assert result.detected is False

    def test_too_few_bars(self):
        bars = [make_flat_bar(idx=0)]
        bar = make_bar()
        bars.append(bar)
        ctx = ContextResult(accumulation_active=True, accumulation_bars=7)
        result = detect_accumulation_breakout(bar, bars, ctx)
        assert result.detected is False

    def test_no_breakout_inside_range(self):
        bars = [make_flat_bar(idx=i) for i in range(7)]
        # Close inside accumulation range
        inside_bar = make_bar(o=5247.0, h=5247.5, l=5246.5, c=5247.25)
        bars.append(inside_bar)
        ctx = ContextResult(accumulation_active=True, accumulation_bars=7, accumulation_range_ticks=4)
        result = detect_accumulation_breakout(inside_bar, bars, ctx)
        assert result.detected is False

    def test_pattern_id(self):
        bars = [make_flat_bar(idx=0)]
        bar = make_bar()
        bars.append(bar)
        ctx = ContextResult()
        result = detect_accumulation_breakout(bar, bars, ctx)
        assert result.pattern_id == "accumulation_breakout"

    def test_metadata_present(self):
        bars = [make_flat_bar(idx=i) for i in range(7)]
        breakout = make_bar(o=5247.0, h=5250.0, l=5247.0, c=5249.5)
        bars.append(breakout)
        ctx = ContextResult(accumulation_active=True, accumulation_bars=7, accumulation_range_ticks=4)
        result = detect_accumulation_breakout(breakout, bars, ctx)
        assert result.metadata is not None
        assert "accum_bars" in result.metadata


# ════════════════════════════════════════════════════════════
# PATTERN 2: V-SHAPE REVERSAL
# ════════════════════════════════════════════════════════════

class TestVShapeReversal:
    def test_v_bottom_detected(self):
        bars = [
            make_down_bar(idx=0),
            make_down_bar(idx=1),
            make_bar(o=5244.0, h=5244.5, l=5243.5, c=5243.5),
            make_up_bar(base=5243.5, idx=0),
            make_up_bar(base=5244.5, idx=1),
        ]
        result = detect_v_shape_reversal(bars[-1], bars, ContextResult())
        assert result.detected is True
        assert result.direction == "LONG"
        assert result.trigger_price is not None
        assert result.invalidation_price is not None

    def test_inverted_v_detected(self):
        bars = [
            make_up_bar(idx=0),
            make_up_bar(idx=1),
            make_bar(o=5250.0, h=5250.5, l=5249.5, c=5250.0),
            make_down_bar(base=5250.0, idx=0),
            make_down_bar(base=5249.0, idx=1),
        ]
        result = detect_v_shape_reversal(bars[-1], bars, ContextResult())
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_no_v_shape(self):
        bars = [make_flat_bar(idx=i) for i in range(5)]
        result = detect_v_shape_reversal(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_too_few_bars(self):
        bars = [make_up_bar(idx=0), make_down_bar(idx=1)]
        result = detect_v_shape_reversal(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_pattern_id(self):
        bars = [make_flat_bar(idx=i) for i in range(5)]
        result = detect_v_shape_reversal(bars[-1], bars, ContextResult())
        assert result.pattern_id == "v_shape_reversal"


# ════════════════════════════════════════════════════════════
# PATTERN 3: FAILED TEST
# ════════════════════════════════════════════════════════════

class TestFailedTest:
    def test_failed_test_high(self):
        lookback = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5247.0, h=5248.0, l=5246.5, c=5247.5),
            make_bar(o=5247.0, h=5247.5, l=5246.0, c=5246.5),
        ]
        test_bar = make_bar(o=5247.5, h=5249.0, l=5246.0, c=5246.5)
        bars = lookback + [test_bar]
        result = detect_failed_test(test_bar, bars, ContextResult())
        assert result.detected is True
        assert result.direction == "SHORT"
        assert result.invalidation_price == round(test_bar.h, 2)

    def test_failed_test_low(self):
        lookback = [
            make_bar(o=5248.0, h=5249.0, l=5246.0, c=5247.0),
            make_bar(o=5247.0, h=5248.0, l=5246.0, c=5247.5),
            make_bar(o=5247.5, h=5248.0, l=5246.5, c=5247.0),
        ]
        test_bar = make_bar(o=5246.5, h=5248.0, l=5244.5, c=5247.5)
        bars = lookback + [test_bar]
        result = detect_failed_test(test_bar, bars, ContextResult())
        assert result.detected is True
        assert result.direction == "LONG"
        assert result.invalidation_price == round(test_bar.l, 2)

    def test_no_failed_test(self):
        bars = [make_bar(ts=f"2026-05-09T13:{i}:00Z") for i in range(4)]
        result = detect_failed_test(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_too_few_bars(self):
        bars = [make_bar(), make_bar()]
        result = detect_failed_test(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_metadata_has_test_level(self):
        lookback = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5247.0, h=5248.0, l=5246.5, c=5247.5),
            make_bar(o=5247.0, h=5247.5, l=5246.0, c=5246.5),
        ]
        test_bar = make_bar(o=5247.5, h=5249.0, l=5246.0, c=5246.5)
        bars = lookback + [test_bar]
        result = detect_failed_test(test_bar, bars, ContextResult())
        assert result.metadata is not None
        assert "test_level" in result.metadata


# ════════════════════════════════════════════════════════════
# PATTERN 4: STAIR-STEP
# ════════════════════════════════════════════════════════════

class TestStairStep:
    def test_bullish_stair_step(self):
        bars = [
            make_bar(o=5244.0, h=5245.0, l=5243.0, c=5244.5),
            make_bar(o=5244.5, h=5246.0, l=5244.0, c=5245.5),
            make_bar(o=5245.5, h=5247.0, l=5245.0, c=5246.5),
            make_bar(o=5246.5, h=5248.0, l=5246.0, c=5247.5),
        ]
        result = detect_stair_step(bars[-1], bars, ContextResult())
        assert result.detected is True
        assert result.direction == "LONG"

    def test_bearish_stair_step(self):
        bars = [
            make_bar(o=5248.0, h=5249.0, l=5247.0, c=5247.5),
            make_bar(o=5247.5, h=5248.0, l=5246.0, c=5246.5),
            make_bar(o=5246.5, h=5247.0, l=5245.0, c=5245.5),
            make_bar(o=5245.5, h=5246.0, l=5244.0, c=5244.5),
        ]
        result = detect_stair_step(bars[-1], bars, ContextResult())
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_no_stair_step(self):
        bars = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5247.0, h=5248.0, l=5244.0, c=5245.0),
            make_bar(o=5245.0, h=5247.0, l=5244.0, c=5246.5),
            make_bar(o=5246.5, h=5248.0, l=5243.0, c=5244.0),
        ]
        result = detect_stair_step(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_too_few_bars(self):
        bars = [make_bar(), make_bar()]
        result = detect_stair_step(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_invalidation_price_long(self):
        bars = [
            make_bar(o=5244.0, h=5245.0, l=5243.0, c=5244.5),
            make_bar(o=5244.5, h=5246.0, l=5244.0, c=5245.5),
            make_bar(o=5245.5, h=5247.0, l=5245.0, c=5246.5),
            make_bar(o=5246.5, h=5248.0, l=5246.0, c=5247.5),
        ]
        result = detect_stair_step(bars[-1], bars, ContextResult())
        assert result.invalidation_price is not None
        assert result.invalidation_price <= min(b.l for b in bars)


# ════════════════════════════════════════════════════════════
# PATTERN 5: COMPRESSION + POP
# ════════════════════════════════════════════════════════════

class TestCompressionPop:
    def test_compression_pop_up(self):
        bars = [
            make_bar(o=5246.0, h=5249.0, l=5244.0, c=5247.0),
            make_bar(o=5246.5, h=5248.0, l=5245.5, c=5247.0),
            make_bar(o=5246.5, h=5247.5, l=5246.0, c=5247.0),
            make_bar(o=5247.0, h=5252.0, l=5246.5, c=5251.0),
        ]
        result = detect_compression_pop(bars[-1], bars, ContextResult())
        assert result.detected is True
        assert result.direction == "LONG"

    def test_compression_pop_down(self):
        bars = [
            make_bar(o=5247.0, h=5249.0, l=5244.0, c=5246.0),
            make_bar(o=5247.0, h=5248.0, l=5245.5, c=5246.5),
            make_bar(o=5247.0, h=5247.5, l=5246.0, c=5246.5),
            make_bar(o=5246.5, h=5247.0, l=5241.0, c=5241.5),
        ]
        result = detect_compression_pop(bars[-1], bars, ContextResult())
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_no_compression(self):
        bars = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5246.0, h=5249.0, l=5244.0, c=5248.0),
            make_bar(o=5248.0, h=5251.0, l=5247.0, c=5250.0),
            make_bar(o=5250.0, h=5252.0, l=5249.0, c=5251.0),
        ]
        result = detect_compression_pop(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_too_few_bars(self):
        bars = [make_bar(), make_bar()]
        result = detect_compression_pop(bars[-1], bars, ContextResult())
        assert result.detected is False

    def test_expansion_ratio_in_metadata(self):
        bars = [
            make_bar(o=5246.0, h=5249.0, l=5244.0, c=5247.0),
            make_bar(o=5246.5, h=5248.0, l=5245.5, c=5247.0),
            make_bar(o=5246.5, h=5247.5, l=5246.0, c=5247.0),
            make_bar(o=5247.0, h=5252.0, l=5246.5, c=5251.0),
        ]
        result = detect_compression_pop(bars[-1], bars, ContextResult())
        assert result.metadata is not None
        assert "expansion_ratio" in result.metadata

    def test_pop_too_small(self):
        bars = [
            make_bar(o=5246.0, h=5249.0, l=5244.0, c=5247.0),
            make_bar(o=5246.5, h=5248.0, l=5245.5, c=5247.0),
            make_bar(o=5246.5, h=5247.5, l=5246.0, c=5247.0),
            make_bar(o=5246.5, h=5247.75, l=5246.0, c=5247.25),  # too small pop
        ]
        result = detect_compression_pop(bars[-1], bars, ContextResult())
        assert result.detected is False


# ════════════════════════════════════════════════════════════
# MICRO-PATTERN RESULT SCHEMA
# ════════════════════════════════════════════════════════════

class TestMicroPatternResult:
    def test_default_values(self):
        r = MicroPatternResult(pattern_id="test")
        assert r.detected is False
        assert r.direction is None
        assert r.strength == 0.0
        assert r.trigger_price is None
        assert r.invalidation_price is None

    def test_detected_result(self):
        r = MicroPatternResult(
            pattern_id="test",
            detected=True,
            direction="LONG",
            strength=0.8,
            trigger_price=5247.0,
            invalidation_price=5245.0,
        )
        assert r.detected is True
        assert r.direction == "LONG"
        assert r.strength == 0.8
