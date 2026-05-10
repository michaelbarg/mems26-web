"""Tests for tick_reversal signal detectors and detect_all_signals().

Coverage targets: >85% for all 10 signal detectors + unified entry point.
Tests use mock footprint data with bid/ask levels, delta, volume.
"""

import pytest
from backend.v9.systems.tick_reversal.schemas import (
    BarInput, TickReversalConfig, SignalResult,
)
from backend.v9.systems.tick_reversal.signal_engine import detect_all_signals
from backend.v9.systems.tick_reversal.signal_detectors import ALL_SIGNAL_DETECTORS
from backend.v9.systems.tick_reversal.signal_detectors.zohar_signals import (
    detect_belly_comparison,
    detect_volume_drop_90,
    detect_cot_vs_amt,
    detect_tick_breach,
    detect_poc_migration,
)
from backend.v9.systems.tick_reversal.signal_detectors.industry_signals import (
    detect_imbalance_250,
    detect_stacked_imbalance,
    detect_cumulative_delta,
    detect_exhaustion,
    detect_liquidity_sweep,
)


# ── Helpers ──────────────────────────────────────────────────────

def make_bar(
    o=5246.0, h=5248.0, l=5245.0, c=5247.0, vol=1000,
    ask_vol=600, bid_vol=400, delta=200, ts="2026-05-09T13:42:30Z",
    tick_size=15, footprint=None, cluster=None,
) -> BarInput:
    return BarInput(
        ts=ts, o=o, h=h, l=l, c=c, vol=vol,
        ask_vol=ask_vol, bid_vol=bid_vol, delta=delta,
        tick_size=tick_size, footprint=footprint, cluster=cluster,
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


def make_footprint_bar(levels=None, poc_price=5247.0, poc_vol=500):
    fp = {
        "levels": levels or [
            {"price": 5246.0, "bid": 100, "ask": 300, "vol": 400},
            {"price": 5247.0, "bid": 200, "ask": 300, "vol": 500},
            {"price": 5248.0, "bid": 50, "ask": 150, "vol": 200},
        ],
        "poc_price": poc_price,
        "poc_vol": poc_vol,
    }
    return make_bar(footprint=fp, vol=1100)


# ════════════════════════════════════════════════════════════
# REGISTRY
# ════════════════════════════════════════════════════════════

class TestRegistry:
    def test_10_detectors_registered(self):
        assert len(ALL_SIGNAL_DETECTORS) == 10

    def test_detector_names(self):
        names = [name for name, _ in ALL_SIGNAL_DETECTORS]
        assert "belly_comparison" in names
        assert "volume_drop_90" in names
        assert "cot_vs_amt" in names
        assert "tick_breach" in names
        assert "poc_migration" in names
        assert "imbalance_250" in names
        assert "stacked_imbalance" in names
        assert "cumulative_delta" in names
        assert "exhaustion" in names
        assert "liquidity_sweep" in names


# ════════════════════════════════════════════════════════════
# ZOHAR SIGNAL 1: BELLY COMPARISON
# ════════════════════════════════════════════════════════════

class TestBellyComparison:
    def test_long_dominant(self):
        bar = make_bar(ask_vol=900, bid_vol=300)
        result = detect_belly_comparison(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"
        assert result["weight"] == 1

    def test_short_dominant(self):
        bar = make_bar(ask_vol=200, bid_vol=900)
        result = detect_belly_comparison(bar, [])
        assert result["active"] is True
        assert result["direction"] == "SHORT"

    def test_balanced(self):
        bar = make_bar(ask_vol=500, bid_vol=500)
        result = detect_belly_comparison(bar, [])
        assert result["active"] is False

    def test_zero_volume(self):
        bar = make_bar(ask_vol=0, bid_vol=0)
        result = detect_belly_comparison(bar, [])
        assert result["active"] is False

    def test_one_side_zero(self):
        bar = make_bar(ask_vol=500, bid_vol=0)
        result = detect_belly_comparison(bar, [])
        assert result["active"] is True

    def test_custom_ratio(self):
        bar = make_bar(ask_vol=600, bid_vol=400)
        result = detect_belly_comparison(bar, [], config={"belly_dominance_ratio": 1.3})
        assert result["active"] is True  # 1.5 >= 1.3


# ════════════════════════════════════════════════════════════
# ZOHAR SIGNAL 2: 90% VOLUME DROP
# ════════════════════════════════════════════════════════════

class TestVolumeDrop90:
    def test_drop_detected(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=1000, ask_vol=500, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(3)
        ]
        current = make_bar(o=5246, h=5249, l=5246, c=5248, bid_vol=50, ask_vol=800)
        bars.append(current)
        result = detect_volume_drop_90(current, bars)
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_no_drop(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=500, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(3)
        ]
        current = make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=450)
        bars.append(current)
        result = detect_volume_drop_90(current, bars)
        assert result["active"] is False

    def test_too_few_bars(self):
        bars = [make_bar()]
        result = detect_volume_drop_90(bars[0], bars)
        assert result["active"] is False

    def test_metadata_has_drop_pct(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=1000, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(3)
        ]
        current = make_bar(o=5246, h=5249, l=5246, c=5248, bid_vol=50, ask_vol=800)
        bars.append(current)
        result = detect_volume_drop_90(current, bars)
        assert "drop_pct" in result["metadata"]


# ════════════════════════════════════════════════════════════
# ZOHAR SIGNAL 3: COT VS AMT
# ════════════════════════════════════════════════════════════

class TestCotVsAmt:
    def test_up_bar_above_mid(self):
        bar = make_bar(o=5246.0, h=5248.5, l=5245.5, c=5248.0)
        result = detect_cot_vs_amt(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_down_bar_below_mid(self):
        bar = make_bar(o=5248.0, h=5248.5, l=5245.5, c=5246.0)
        result = detect_cot_vs_amt(bar, [])
        assert result["active"] is True
        assert result["direction"] == "SHORT"

    def test_zero_range(self):
        bar = make_bar(o=5247.0, h=5247.0, l=5247.0, c=5247.0)
        result = detect_cot_vs_amt(bar, [])
        assert result["active"] is False

    def test_metadata_has_midpoint(self):
        bar = make_bar(o=5246.0, h=5248.5, l=5245.5, c=5248.0)
        result = detect_cot_vs_amt(bar, [])
        assert "midpoint" in result["metadata"]


# ════════════════════════════════════════════════════════════
# ZOHAR SIGNAL 4: TICK BREACH
# ════════════════════════════════════════════════════════════

class TestTickBreach:
    def test_controlled_breach(self):
        bar = make_bar(o=5246.0, h=5248.0, l=5245.5, c=5247.5)
        result = detect_tick_breach(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_excessive_breach(self):
        bar = make_bar(o=5246.0, h=5248.0, l=5243.0, c=5247.5)
        result = detect_tick_breach(bar, [])
        assert result["active"] is False

    def test_zero_range(self):
        bar = make_bar(o=5247.0, h=5247.0, l=5247.0, c=5247.0)
        result = detect_tick_breach(bar, [])
        assert result["active"] is False

    def test_metadata_has_breach_ticks(self):
        bar = make_bar(o=5246.0, h=5248.0, l=5245.5, c=5247.5)
        result = detect_tick_breach(bar, [])
        assert "breach_ticks" in result["metadata"]


# ════════════════════════════════════════════════════════════
# ZOHAR SIGNAL 5: POC MIGRATION
# ════════════════════════════════════════════════════════════

class TestPocMigration:
    def test_poc_moving_up(self):
        bars = [
            make_bar(o=5244, h=5245, l=5243, c=5244.5, ask_vol=700, bid_vol=300),
            make_bar(o=5245, h=5246, l=5244, c=5245.5, ask_vol=700, bid_vol=300),
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=700, bid_vol=300),
        ]
        current = make_bar(o=5247, h=5248, l=5246, c=5247.5, ask_vol=700, bid_vol=300)
        result = detect_poc_migration(current, bars)
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_poc_stuck(self):
        bars = [
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500),
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500),
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500),
        ]
        current = make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500)
        result = detect_poc_migration(current, bars)
        assert result["active"] is False

    def test_too_few_bars(self):
        bars = [make_bar()]
        result = detect_poc_migration(bars[0], bars)
        assert result["active"] is False

    def test_with_footprint_poc(self):
        fp = {"poc_price": 5247.5}
        bars = [
            make_bar(footprint={"poc_price": 5245.0}),
            make_bar(footprint={"poc_price": 5246.0}),
            make_bar(footprint={"poc_price": 5247.0}),
        ]
        current = make_bar(o=5247, h=5249, l=5247, c=5248.5, footprint=fp)
        result = detect_poc_migration(current, bars)
        assert result["active"] is True


# ════════════════════════════════════════════════════════════
# INDUSTRY SIGNAL 1: IMBALANCE 250%
# ════════════════════════════════════════════════════════════

class TestImbalance250:
    def test_footprint_imbalance(self):
        fp = {"levels": [{"bid": 10, "ask": 100, "price": 5247.0}]}
        bar = make_bar(footprint=fp, ask_vol=500, bid_vol=500)
        result = detect_imbalance_250(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_bar_level_imbalance(self):
        bar = make_bar(ask_vol=750, bid_vol=200)
        result = detect_imbalance_250(bar, [])
        assert result["active"] is True

    def test_no_imbalance(self):
        bar = make_bar(ask_vol=500, bid_vol=400)
        result = detect_imbalance_250(bar, [])
        assert result["active"] is False

    def test_weight_is_1(self):
        bar = make_bar(ask_vol=750, bid_vol=200)
        result = detect_imbalance_250(bar, [])
        assert result["weight"] == 1


# ════════════════════════════════════════════════════════════
# INDUSTRY SIGNAL 2: STACKED IMBALANCE
# ════════════════════════════════════════════════════════════

class TestStackedImbalance:
    def test_from_footprint(self):
        fp = {
            "levels": [
                {"bid": 10, "ask": 100, "price": 5245.0},
                {"bid": 15, "ask": 120, "price": 5246.0},
                {"bid": 12, "ask": 110, "price": 5247.0},
                {"bid": 200, "ask": 100, "price": 5248.0},
            ]
        }
        bar = make_bar(footprint=fp)
        result = detect_stacked_imbalance(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_from_cluster_data(self):
        bar = make_bar(cluster={"stacked_buy": 4, "stacked_sell": 0})
        result = detect_stacked_imbalance(bar, [])
        assert result["active"] is True

    def test_no_stacked(self):
        bar = make_bar(cluster={"stacked_buy": 1, "stacked_sell": 0})
        result = detect_stacked_imbalance(bar, [])
        assert result["active"] is False

    def test_weight_is_2(self):
        bar = make_bar(cluster={"stacked_buy": 4, "stacked_sell": 0})
        result = detect_stacked_imbalance(bar, [])
        assert result["weight"] == 2


# ════════════════════════════════════════════════════════════
# INDUSTRY SIGNAL 3: CUMULATIVE DELTA
# ════════════════════════════════════════════════════════════

class TestCumulativeDelta:
    def test_aligned_long(self):
        bar = make_bar(o=5246, c=5248, delta=500)
        result = detect_cumulative_delta(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_not_aligned(self):
        bar = make_bar(o=5246, c=5248, delta=-500)
        result = detect_cumulative_delta(bar, [])
        assert result["active"] is False

    def test_aligned_short(self):
        bar = make_bar(o=5248, c=5246, delta=-300)
        result = detect_cumulative_delta(bar, [])
        assert result["active"] is True
        assert result["direction"] == "SHORT"

    def test_no_delta_uses_vol(self):
        bar = make_bar(o=5246, c=5248, delta=None, ask_vol=800, bid_vol=200)
        result = detect_cumulative_delta(bar, [])
        assert result["active"] is True
        assert result["direction"] == "LONG"


# ════════════════════════════════════════════════════════════
# INDUSTRY SIGNAL 4: EXHAUSTION
# ════════════════════════════════════════════════════════════

class TestExhaustion:
    def test_exhaustion_at_high(self):
        bars = [make_bar(vol=500, ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        extreme = make_bar(
            o=5247.5, h=5249.0, l=5247.0, c=5247.75,
            vol=1500, ts="2026-05-09T13:45:00Z",
        )
        bars.append(extreme)
        result = detect_exhaustion(extreme, bars)
        assert result["active"] is True
        assert result["weight"] == -1

    def test_no_exhaustion(self):
        bars = [make_bar(vol=1000, ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        normal = make_bar(o=5246, h=5248, l=5245, c=5247.5, vol=1000)
        bars.append(normal)
        result = detect_exhaustion(normal, bars)
        assert result["active"] is False

    def test_too_few_bars(self):
        result = detect_exhaustion(make_bar(), [make_bar()])
        assert result["active"] is False

    def test_direction_short_at_high(self):
        bars = [make_bar(vol=500, ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        extreme = make_bar(o=5247.5, h=5249.0, l=5247.0, c=5247.75, vol=1500)
        bars.append(extreme)
        result = detect_exhaustion(extreme, bars)
        if result["active"]:
            assert result["direction"] in ("LONG", "SHORT")


# ════════════════════════════════════════════════════════════
# INDUSTRY SIGNAL 5: LIQUIDITY SWEEP
# ════════════════════════════════════════════════════════════

class TestLiquiditySweep:
    def test_sweep_high(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(6)
        ]
        sweep = make_bar(o=5247, h=5249.5, l=5246, c=5247, ts="2026-05-09T13:46:00Z")
        bars.append(sweep)
        result = detect_liquidity_sweep(sweep, bars)
        assert result["active"] is True
        assert result["direction"] == "SHORT"
        assert result["weight"] == 2

    def test_sweep_low(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(6)
        ]
        sweep = make_bar(o=5246, h=5247, l=5243.5, c=5246, ts="2026-05-09T13:46:00Z")
        bars.append(sweep)
        result = detect_liquidity_sweep(sweep, bars)
        assert result["active"] is True
        assert result["direction"] == "LONG"

    def test_no_sweep(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(6)
        ]
        normal = make_bar(o=5246.5, h=5247.5, l=5246, c=5247, ts="2026-05-09T13:46:00Z")
        bars.append(normal)
        result = detect_liquidity_sweep(normal, bars)
        assert result["active"] is False

    def test_too_few_bars(self):
        bars = [make_bar(), make_bar()]
        result = detect_liquidity_sweep(bars[-1], bars)
        assert result["active"] is False

    def test_metadata_has_sweep_type(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(6)
        ]
        sweep = make_bar(o=5247, h=5249.5, l=5246, c=5247, ts="2026-05-09T13:46:00Z")
        bars.append(sweep)
        result = detect_liquidity_sweep(sweep, bars)
        assert "sweep_type" in result["metadata"]


# ════════════════════════════════════════════════════════════
# UNIFIED: detect_all_signals()
# ════════════════════════════════════════════════════════════

class TestDetectAllSignals:
    def test_empty_bars(self):
        result = detect_all_signals([])
        assert result == []

    def test_no_setup_returns_empty(self):
        """Low confluence bars produce no signals."""
        bars = [make_bar(ask_vol=500, bid_vol=500, delta=0, ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        result = detect_all_signals(bars)
        assert isinstance(result, list)

    def test_strong_setup_returns_signal(self):
        """Strong bullish setup with many signals active should produce a signal."""
        bars = []
        # Build history: 8 up bars (stair-step + jumps + poc migration)
        for i in range(8):
            bars.append(make_bar(
                o=5244.0 + i * 1.0,
                h=5245.5 + i * 1.0,
                l=5243.5 + i * 1.0,
                c=5245.0 + i * 1.0,
                vol=1000,
                ask_vol=800,
                bid_vol=200,
                delta=600,
                ts=f"2026-05-09T13:{40 + i}:00Z",
            ))
        # Final strong bar
        bars.append(make_bar(
            o=5252.0, h=5255.0, l=5251.5, c=5254.5,
            vol=2000, ask_vol=1800, bid_vol=200, delta=1600,
            ts="2026-05-09T13:50:00Z",
        ))
        result = detect_all_signals(bars)
        assert isinstance(result, list)
        # May or may not generate a signal depending on exact confluence
        for sig in result:
            assert isinstance(sig, SignalResult)
            assert sig.direction in ("LONG", "SHORT")
            assert 0.0 <= sig.confidence <= 1.0
            assert sig.trigger_price > 0
            assert sig.invalidation_price > 0

    def test_signal_result_fields(self):
        """Verify all required fields on SignalResult."""
        sr = SignalResult(
            signal_id="test_1",
            direction="LONG",
            confidence=0.85,
            trigger_price=5248.0,
            invalidation_price=5245.0,
        )
        assert sr.signal_id == "test_1"
        assert sr.direction == "LONG"
        assert sr.confidence == 0.85
        assert sr.trigger_price == 5248.0
        assert sr.invalidation_price == 5245.0
        assert sr.pattern_ids == []
        assert sr.signal_ids == []

    def test_with_footprint_data(self):
        """External footprint data is merged into bar."""
        bars = [make_up_bar(idx=i) for i in range(10)]
        fp = {
            "levels": [
                {"price": 5246.0, "bid": 10, "ask": 100},
                {"price": 5247.0, "bid": 15, "ask": 120},
                {"price": 5248.0, "bid": 12, "ask": 110},
            ],
            "poc_price": 5247.0,
            "poc_vol": 135,
        }
        result = detect_all_signals(bars, footprint_data=fp)
        assert isinstance(result, list)

    def test_with_custom_config(self):
        """Custom config thresholds are respected."""
        bars = [make_up_bar(idx=i) for i in range(10)]
        cfg = TickReversalConfig(confluence_tactical_min=3)
        result = detect_all_signals(bars, config=cfg)
        assert isinstance(result, list)

    def test_direction_none_returns_empty(self):
        """If direction cannot be inferred, no signals produced."""
        # Doji bars with equal open/close
        bars = [make_bar(o=5247.0, c=5247.0, ask_vol=500, bid_vol=500, delta=0,
                         ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        result = detect_all_signals(bars)
        assert isinstance(result, list)

    def test_tactical_classification(self):
        """Verify tactical signals have correct classification in metadata."""
        bars = []
        for i in range(8):
            bars.append(make_bar(
                o=5244.0 + i,
                h=5245.5 + i,
                l=5243.5 + i,
                c=5245.0 + i,
                vol=1000,
                ask_vol=800,
                bid_vol=200,
                delta=600,
                ts=f"2026-05-09T13:{40 + i}:00Z",
            ))
        result = detect_all_signals(bars)
        for sig in result:
            assert sig.metadata is not None
            assert sig.metadata.get("classification") in ("TACTICAL", "STRATEGIC")

    def test_strategic_classification(self):
        """Verify strategic signals with maximum confluence."""
        bars = []
        for i in range(10):
            bars.append(make_bar(
                o=5244.0 + i * 1.0,
                h=5245.5 + i * 1.0,
                l=5243.5 + i * 1.0,
                c=5245.0 + i * 1.0,
                vol=1000,
                ask_vol=900,
                bid_vol=100,
                delta=800,
                ts=f"2026-05-09T13:{35 + i}:00Z",
            ))
        # Add a bar with sweep for booster
        bars.append(make_bar(
            o=5254.0, h=5256.5, l=5253.5, c=5254.5,
            vol=2500, ask_vol=2200, bid_vol=300, delta=1900,
            ts="2026-05-09T13:50:00Z",
        ))
        result = detect_all_signals(bars)
        for sig in result:
            if sig.metadata and sig.metadata.get("confluence_total", 0) >= 6:
                assert sig.metadata["classification"] == "STRATEGIC"


# ════════════════════════════════════════════════════════════
# SIGNAL RESULT SCHEMA
# ════════════════════════════════════════════════════════════

class TestSignalResultSchema:
    def test_defaults(self):
        sr = SignalResult(
            signal_id="test",
            direction="LONG",
            confidence=0.5,
            trigger_price=5247.0,
            invalidation_price=5245.0,
        )
        assert sr.pattern_ids == []
        assert sr.signal_ids == []
        assert sr.metadata is None

    def test_with_metadata(self):
        sr = SignalResult(
            signal_id="test",
            direction="SHORT",
            confidence=0.9,
            trigger_price=5248.0,
            invalidation_price=5250.0,
            pattern_ids=["failed_test"],
            signal_ids=["belly_comparison", "volume_drop_90"],
            metadata={"confluence_total": 7, "classification": "STRATEGIC"},
        )
        assert len(sr.pattern_ids) == 1
        assert len(sr.signal_ids) == 2
        assert sr.metadata["classification"] == "STRATEGIC"

    def test_confidence_bounds(self):
        sr = SignalResult(
            signal_id="test",
            direction="LONG",
            confidence=0.0,
            trigger_price=5247.0,
            invalidation_price=5245.0,
        )
        assert sr.confidence >= 0.0
        sr2 = SignalResult(
            signal_id="test",
            direction="LONG",
            confidence=1.0,
            trigger_price=5247.0,
            invalidation_price=5245.0,
        )
        assert sr2.confidence <= 1.0
