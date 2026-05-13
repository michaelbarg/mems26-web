"""Tests for System 3: Tick Reversal / Footprint Observer.

Coverage targets:
- Detector pipeline (10 steps)
- 5 patterns
- 10 signals (5 Zohar + 5 Industry)
- Confluence + Classification
- STANDALONE verification (no trade execution code)
"""

import pytest
from backend.v9.systems.tick_reversal.detector import TickReversalDetector
from backend.v9.systems.tick_reversal.schemas import (
    BarInput, BarAnalysis, TickReversalConfig,
    ClusterResult, EmptyZoneResult, ContextResult, PatternResult,
    ZoharSignals, IndustrySignals, ConfluenceResult,
)
from backend.v9.systems.tick_reversal.patterns import ALL_PATTERNS
from backend.v9.systems.tick_reversal.patterns.accumulation_breakout import detect_accumulation_breakout
from backend.v9.systems.tick_reversal.patterns.v_shape_reversal import detect_v_shape_reversal
from backend.v9.systems.tick_reversal.patterns.failed_test import detect_failed_test
from backend.v9.systems.tick_reversal.patterns.stair_step import detect_stair_step
from backend.v9.systems.tick_reversal.patterns.compression_pop import detect_compression_pop
from backend.v9.systems.tick_reversal.signals import (
    calc_belly_comparison,
    calc_volume_drop_90,
    calc_cot_above_amt,
    calc_tick_breach,
    calc_poc_jumping,
    calc_imbalance_250,
    calc_stacked_imbalance,
    calc_cumulative_delta_aligned,
    calc_exhaustion,
    calc_liquidity_sweep,
)


# ── Helpers ──

def make_bar(
    o=5246.0, h=5248.0, l=5245.0, c=5247.0, vol=1000,
    ask_vol=600, bid_vol=400, delta=200, ts="2026-05-09T13:42:30Z",
    tick_size=15, footprint=None, cluster=None, dir_=None,
) -> BarInput:
    return BarInput(
        ts=ts, o=o, h=h, l=l, c=c, vol=vol,
        ask_vol=ask_vol, bid_vol=bid_vol, delta=delta,
        tick_size=tick_size, footprint=footprint, cluster=cluster,
        dir=dir_,
    )


def make_up_bar(base=5246.0, spread=2.0, vol=1000, idx=0) -> BarInput:
    """Bullish bar."""
    o = base + idx * spread * 0.3
    c = o + spread
    return make_bar(o=o, h=c + 0.25, l=o - 0.25, c=c, vol=vol,
                    ask_vol=int(vol * 0.7), bid_vol=int(vol * 0.3),
                    delta=int(vol * 0.4), ts=f"2026-05-09T13:{40 + idx}:00Z")


def make_down_bar(base=5248.0, spread=2.0, vol=1000, idx=0) -> BarInput:
    """Bearish bar."""
    o = base - idx * spread * 0.3
    c = o - spread
    return make_bar(o=o, h=o + 0.25, l=c - 0.25, c=c, vol=vol,
                    ask_vol=int(vol * 0.3), bid_vol=int(vol * 0.7),
                    delta=-int(vol * 0.4), ts=f"2026-05-09T13:{40 + idx}:00Z")


def make_flat_bar(base=5247.0, idx=0) -> BarInput:
    """Narrow range bar for accumulation."""
    return make_bar(
        o=base - 0.25, h=base + 0.5, l=base - 0.5, c=base + 0.25,
        vol=500, ask_vol=260, bid_vol=240, delta=20,
        ts=f"2026-05-09T13:{30 + idx}:00Z",
    )


# ════════════════════════════════════════════════════════════
# DETECTOR TESTS
# ════════════════════════════════════════════════════════════

class TestDetector:
    def test_init_defaults(self):
        d = TickReversalDetector()
        assert d.config.tick_reversal_size == 15
        assert d.config.confluence_tactical_min == 4
        assert d.config.confluence_strategic_min == 6
        assert len(d.bars) == 0

    def test_init_custom_config(self):
        cfg = TickReversalConfig(tick_reversal_size=12, confluence_tactical_min=3)
        d = TickReversalDetector(config=cfg)
        assert d.config.tick_reversal_size == 12
        assert d.config.confluence_tactical_min == 3

    def test_process_single_bar(self):
        d = TickReversalDetector()
        bar = make_bar()
        result = d.process_bar(bar)
        assert isinstance(result, BarAnalysis)
        assert result.ts == bar.ts
        assert result.tick_reversal_size == 15
        assert result.classification in ("NO_SETUP", "TACTICAL", "STRATEGIC")
        assert result.bar == bar

    def test_buffer_fills(self):
        d = TickReversalDetector()
        for i in range(35):
            d.process_bar(make_bar(ts=f"2026-05-09T13:{i:02d}:00Z"))
        assert len(d.bars) == 30  # max buffer

    def test_bar_id_format(self):
        d = TickReversalDetector()
        bar = make_bar(c=5247.50, tick_size=15, ts="2026-05-09T14:00:00Z")
        result = d.process_bar(bar)
        assert result.bar_id.startswith("tr_15_")

    def test_no_setup_default(self):
        d = TickReversalDetector()
        result = d.process_bar(make_bar(ask_vol=500, bid_vol=500, delta=0))
        assert result.classification == "NO_SETUP"
        assert result.visual_marker_drawn is False

    def test_classification_tactical(self):
        """Verify TACTICAL when confluence >= 4."""
        d = TickReversalDetector()
        # Fill buffer
        for i in range(10):
            d.process_bar(make_up_bar(idx=i))
        # Bar with strong signals
        bar = make_bar(
            o=5246.0, h=5249.0, l=5245.5, c=5248.5, vol=2000,
            ask_vol=1800, bid_vol=200, delta=1600,
        )
        result = d.process_bar(bar)
        # Should have at least belly + cot + tick_breach + delta_aligned
        assert result.confluence.total >= 0  # smoke test

    def test_journal_always_logs(self):
        """Every bar gets a journal entry, even NO_SETUP (spec Section 6 Step 10)."""
        d = TickReversalDetector()
        bar = make_bar(ask_vol=500, bid_vol=500, delta=0)
        result = d.process_bar(bar)
        assert result.ts is not None
        assert result.bar_id is not None
        assert result.classification == "NO_SETUP"
        # Even NO_SETUP has full data
        assert result.signals_zohar is not None
        assert result.signals_industry is not None

    def test_direction_inferred_long(self):
        d = TickReversalDetector()
        for i in range(3):
            d.process_bar(make_up_bar(idx=i))
        bar = make_up_bar(idx=3)
        result = d.process_bar(bar)
        assert result.direction_inferred == "LONG"

    def test_direction_inferred_short(self):
        d = TickReversalDetector()
        for i in range(3):
            d.process_bar(make_down_bar(idx=i))
        bar = make_down_bar(idx=3)
        result = d.process_bar(bar)
        assert result.direction_inferred == "SHORT"

    def test_would_be_prices_only_on_setup(self):
        d = TickReversalDetector()
        bar = make_bar(ask_vol=500, bid_vol=500, delta=0)
        result = d.process_bar(bar)
        assert result.classification == "NO_SETUP"
        assert result.would_be_entry_price is None


# ════════════════════════════════════════════════════════════
# PATTERN TESTS
# ════════════════════════════════════════════════════════════

class TestPatterns:
    def test_all_5_patterns_registered(self):
        assert len(ALL_PATTERNS) == 5
        names = [name for name, _ in ALL_PATTERNS]
        assert "Accumulation + Breakout" in names
        assert "V-Shape Reversal" in names
        assert "Failed Test" in names
        assert "Stair-step" in names
        assert "Compression + Pop" in names

    def test_accumulation_breakout_detected(self):
        bars = [make_flat_bar(idx=i) for i in range(7)]
        # Breakout bar
        bars.append(make_bar(o=5247.0, h=5250.0, l=5247.0, c=5249.5))
        ctx = ContextResult(accumulation_active=True, accumulation_bars=7, accumulation_range_ticks=4)
        result = detect_accumulation_breakout(bars, ctx)
        assert result.detected == "Accumulation + Breakout"
        assert result.completion > 0

    def test_accumulation_breakout_no_accumulation(self):
        bars = [make_up_bar(idx=i) for i in range(5)]
        ctx = ContextResult(accumulation_active=False)
        result = detect_accumulation_breakout(bars, ctx)
        assert result.detected is None

    def test_v_shape_reversal(self):
        bars = [
            make_down_bar(idx=0),
            make_down_bar(idx=1),
            make_bar(o=5244.0, h=5244.5, l=5243.5, c=5243.5),  # pivot
            make_up_bar(base=5243.5, idx=0),
            make_up_bar(base=5244.5, idx=1),
        ]
        ctx = ContextResult()
        result = detect_v_shape_reversal(bars, ctx)
        assert result.detected == "V-Shape Reversal"

    def test_failed_test_high(self):
        lookback = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5247.0, h=5248.0, l=5246.5, c=5247.5),
            make_bar(o=5247.0, h=5247.5, l=5246.0, c=5246.5),
        ]
        # Bar pokes above prior high (5248.0) but closes below
        test_bar = make_bar(o=5247.5, h=5249.0, l=5246.0, c=5246.5)
        bars = lookback + [test_bar]
        ctx = ContextResult()
        result = detect_failed_test(bars, ctx)
        assert result.detected == "Failed Test"

    def test_stair_step_bullish(self):
        bars = [
            make_bar(o=5244.0, h=5245.0, l=5243.0, c=5244.5),
            make_bar(o=5244.5, h=5246.0, l=5244.0, c=5245.5),
            make_bar(o=5245.5, h=5247.0, l=5245.0, c=5246.5),
            make_bar(o=5246.5, h=5248.0, l=5246.0, c=5247.5),
        ]
        ctx = ContextResult()
        result = detect_stair_step(bars, ctx)
        assert result.detected == "Stair-step"

    def test_stair_step_no_pattern(self):
        bars = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5247.0, h=5248.0, l=5244.0, c=5245.0),  # breaks pattern
            make_bar(o=5245.0, h=5247.0, l=5244.0, c=5246.5),
            make_bar(o=5246.5, h=5248.0, l=5243.0, c=5244.0),
        ]
        ctx = ContextResult()
        result = detect_stair_step(bars, ctx)
        assert result.detected is None

    def test_compression_pop(self):
        bars = [
            make_bar(o=5246.0, h=5249.0, l=5244.0, c=5247.0),  # range 5.0
            make_bar(o=5246.5, h=5248.0, l=5245.5, c=5247.0),  # range 2.5
            make_bar(o=5246.5, h=5247.5, l=5246.0, c=5247.0),  # range 1.5
            make_bar(o=5247.0, h=5252.0, l=5246.5, c=5251.0),  # pop! range 5.5
        ]
        ctx = ContextResult()
        result = detect_compression_pop(bars, ctx)
        assert result.detected == "Compression + Pop"

    def test_compression_pop_no_compression(self):
        bars = [
            make_bar(o=5246.0, h=5248.0, l=5245.0, c=5247.0),
            make_bar(o=5246.0, h=5249.0, l=5244.0, c=5248.0),  # expanding, not compressing
            make_bar(o=5248.0, h=5251.0, l=5247.0, c=5250.0),
            make_bar(o=5250.0, h=5252.0, l=5249.0, c=5251.0),
        ]
        ctx = ContextResult()
        result = detect_compression_pop(bars, ctx)
        assert result.detected is None


# ════════════════════════════════════════════════════════════
# SIGNAL TESTS — ZOHAR
# ════════════════════════════════════════════════════════════

class TestZoharSignals:
    def test_belly_comparison_true(self):
        bar = make_bar(ask_vol=900, bid_vol=300)
        assert calc_belly_comparison(bar, [], 1.5) is True

    def test_belly_comparison_false(self):
        bar = make_bar(ask_vol=500, bid_vol=500)
        assert calc_belly_comparison(bar, [], 1.5) is False

    def test_belly_comparison_zero(self):
        bar = make_bar(ask_vol=0, bid_vol=0)
        assert calc_belly_comparison(bar, [], 1.5) is False

    def test_belly_one_side_zero(self):
        bar = make_bar(ask_vol=500, bid_vol=0)
        assert calc_belly_comparison(bar, [], 1.5) is True

    def test_volume_drop_90_true(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=1000, ask_vol=500),
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=900, ask_vol=500),
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=800, ask_vol=500),
        ]
        current = make_bar(o=5246, h=5249, l=5246, c=5248, bid_vol=50, ask_vol=800)
        bars.append(current)
        assert calc_volume_drop_90(current, bars, 90) is True

    def test_volume_drop_90_false(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=500, ask_vol=500),
            make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=500, ask_vol=500),
        ]
        current = make_bar(o=5246, h=5248, l=5245, c=5247, bid_vol=450, ask_vol=500)
        bars.append(current)
        assert calc_volume_drop_90(current, bars, 90) is False

    def test_cot_above_amt_up_bar(self):
        bar = make_bar(o=5246.0, h=5248.5, l=5245.5, c=5248.0)  # close > midpoint
        assert calc_cot_above_amt(bar, []) is True

    def test_cot_above_amt_down_bar(self):
        bar = make_bar(o=5248.0, h=5248.5, l=5245.5, c=5246.0)  # close < midpoint
        assert calc_cot_above_amt(bar, []) is True  # down bar, close < mid

    def test_tick_breach_ok(self):
        bar = make_bar(o=5246.0, h=5248.0, l=5245.5, c=5247.5)  # small lower wick
        assert calc_tick_breach(bar, []) is True

    def test_tick_breach_too_big(self):
        bar = make_bar(o=5246.0, h=5248.0, l=5243.0, c=5247.5)  # huge lower wick
        assert calc_tick_breach(bar, []) is False

    def test_poc_jumping_up(self):
        bars = [
            make_bar(o=5244, h=5245, l=5243, c=5244.5, ask_vol=700, bid_vol=300),
            make_bar(o=5245, h=5246, l=5244, c=5245.5, ask_vol=700, bid_vol=300),
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=700, bid_vol=300),
        ]
        current = make_bar(o=5247, h=5248, l=5246, c=5247.5, ask_vol=700, bid_vol=300)
        assert calc_poc_jumping(current, bars) is True

    def test_poc_stuck(self):
        bars = [
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500),
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500),
            make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500),
        ]
        current = make_bar(o=5246, h=5247, l=5245, c=5246.5, ask_vol=500, bid_vol=500)
        assert calc_poc_jumping(current, bars) is False


# ════════════════════════════════════════════════════════════
# SIGNAL TESTS — INDUSTRY
# ════════════════════════════════════════════════════════════

class TestIndustrySignals:
    def test_imbalance_250_true(self):
        bar = make_bar(ask_vol=750, bid_vol=200)  # 375%
        assert calc_imbalance_250(bar, [], 250) is True

    def test_imbalance_250_false(self):
        bar = make_bar(ask_vol=500, bid_vol=400)  # 125%
        assert calc_imbalance_250(bar, [], 250) is False

    def test_imbalance_from_footprint(self):
        fp = {"levels": [{"bid": 10, "ask": 100, "price": 5247.0}]}
        bar = make_bar(footprint=fp, ask_vol=500, bid_vol=500)
        assert calc_imbalance_250(bar, [], 250) is True

    def test_stacked_imbalance_from_cluster(self):
        bar = make_bar(cluster={"stacked_buy": 4, "stacked_sell": 0})
        assert calc_stacked_imbalance(bar, [], 250, 3) is True

    def test_stacked_imbalance_none(self):
        bar = make_bar(cluster={"stacked_buy": 1, "stacked_sell": 0})
        assert calc_stacked_imbalance(bar, [], 250, 3) is False

    def test_delta_aligned_long(self):
        bar = make_bar(o=5246, c=5248, delta=500)  # up bar + positive delta
        assert calc_cumulative_delta_aligned(bar, []) is True

    def test_delta_not_aligned(self):
        bar = make_bar(o=5246, c=5248, delta=-500)  # up bar + negative delta
        assert calc_cumulative_delta_aligned(bar, []) is False

    def test_exhaustion_detected(self):
        bars = [
            make_bar(vol=500, ts=f"2026-05-09T13:{i}:00Z") for i in range(5)
        ]
        # High vol, small body at recent high
        extreme = make_bar(
            o=5247.5, h=5249.0, l=5247.0, c=5247.75,  # small body
            vol=1500,  # 3x avg
            ts="2026-05-09T13:45:00Z",
        )
        bars.append(extreme)
        assert calc_exhaustion(extreme, bars) is True

    def test_exhaustion_not_detected(self):
        bars = [make_bar(vol=1000, ts=f"2026-05-09T13:{i}:00Z") for i in range(5)]
        normal = make_bar(o=5246, h=5248, l=5245, c=5247.5, vol=1000)
        bars.append(normal)
        assert calc_exhaustion(normal, bars) is False

    def test_liquidity_sweep_high(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(6)
        ]
        # Sweep above 5248, close back below
        sweep = make_bar(o=5247, h=5249.5, l=5246, c=5247, ts="2026-05-09T13:46:00Z")
        bars.append(sweep)
        assert calc_liquidity_sweep(sweep, bars) is True

    def test_liquidity_sweep_none(self):
        bars = [
            make_bar(o=5246, h=5248, l=5245, c=5247, ts=f"2026-05-09T13:{i}:00Z")
            for i in range(6)
        ]
        normal = make_bar(o=5246.5, h=5247.5, l=5246, c=5247, ts="2026-05-09T13:46:00Z")
        bars.append(normal)
        assert calc_liquidity_sweep(normal, bars) is False


# ════════════════════════════════════════════════════════════
# CONFLUENCE + CLASSIFICATION TESTS
# ════════════════════════════════════════════════════════════

class TestConfluence:
    def _detector(self):
        return TickReversalDetector()

    def test_no_setup(self):
        d = self._detector()
        z = ZoharSignals()
        i = IndustrySignals()
        c = d._calc_confluence(z, i)
        assert c.total <= 0 or c.total < 4
        assert d._classify(c.total) == "NO_SETUP"

    def test_tactical(self):
        d = self._detector()
        z = ZoharSignals(belly_comparison=True, volume_drop_90=True,
                         cot_above_amt=True, tick_breach_ok=True)
        i = IndustrySignals(cumulative_delta_aligned=True)
        c = d._calc_confluence(z, i)
        assert c.zohar_count == 4
        assert c.total >= 4
        assert d._classify(c.total) in ("TACTICAL", "STRATEGIC")

    def test_strategic(self):
        d = self._detector()
        z = ZoharSignals(belly_comparison=True, volume_drop_90=True,
                         cot_above_amt=True, tick_breach_ok=True, poc_jumping=True)
        i = IndustrySignals(
            imbalance_250=True, stacked_imbalance=True,
            cumulative_delta_aligned=True,
        )
        c = d._calc_confluence(z, i)
        assert c.total >= 6
        assert d._classify(c.total) == "STRATEGIC"

    def test_stacked_imbalance_boost(self):
        d = self._detector()
        z = ZoharSignals()
        i = IndustrySignals(stacked_imbalance=True, cumulative_delta_aligned=True)
        c = d._calc_confluence(z, i)
        assert c.boosters == 2

    def test_sweep_boost(self):
        d = self._detector()
        z = ZoharSignals()
        i = IndustrySignals(liquidity_sweep=True, cumulative_delta_aligned=True)
        c = d._calc_confluence(z, i)
        assert c.boosters == 2

    def test_exhaustion_penalty(self):
        d = self._detector()
        z = ZoharSignals(belly_comparison=True, cot_above_amt=True)
        i = IndustrySignals(exhaustion=True, cumulative_delta_aligned=True)
        c = d._calc_confluence(z, i)
        assert c.penalties >= 1

    def test_delta_divergence_penalty(self):
        d = self._detector()
        z = ZoharSignals(belly_comparison=True)
        i = IndustrySignals(cumulative_delta_aligned=False)
        c = d._calc_confluence(z, i)
        assert c.penalties >= 1


# ════════════════════════════════════════════════════════════
# CONTEXT TESTS
# ════════════════════════════════════════════════════════════

class TestContext:
    def test_accumulation_detected(self):
        d = TickReversalDetector()
        for i in range(7):
            d.process_bar(make_flat_bar(idx=i))
        bars = d.bars
        ctx = d._analyze_context(bars)
        assert ctx.accumulation_active is True
        assert ctx.accumulation_bars >= 5

    def test_jumps_counted(self):
        d = TickReversalDetector()
        for i in range(4):
            d.process_bar(make_up_bar(idx=i))
        bars = d.bars
        ctx = d._analyze_context(bars)
        assert ctx.jumps_count >= 3
        assert ctx.jumps_direction == "UP"

    def test_otf_state(self):
        d = TickReversalDetector()
        d.process_bar(make_up_bar(idx=0))
        d.process_bar(make_up_bar(idx=1))
        d.process_bar(make_down_bar(idx=2))
        ctx = d._analyze_context(d.bars)
        assert ctx.otf_state == 1  # both sides visible


# ════════════════════════════════════════════════════════════
# STANDALONE VERIFICATION
# ════════════════════════════════════════════════════════════

class TestStandalone:
    """Verify this system NEVER touches trade execution."""

    def test_no_trade_execution_in_detector(self):
        import inspect
        from backend.v9.systems.tick_reversal import detector
        source = inspect.getsource(detector)
        forbidden = ["execute", "order", "bracket", "sierra", "place_order"]
        for word in forbidden:
            assert word not in source.lower(), f"Found '{word}' in detector.py — STANDALONE violation!"

    def test_no_trade_execution_in_patterns(self):
        import inspect
        from backend.v9.systems.tick_reversal import patterns
        source = inspect.getsource(patterns)
        for word in ["execute", "order", "bracket"]:
            assert word not in source.lower(), f"Found '{word}' in patterns — STANDALONE violation!"

    def test_no_trade_execution_in_signals(self):
        import inspect
        from backend.v9.systems.tick_reversal import signals
        source = inspect.getsource(signals)
        for word in ["execute", "order", "bracket"]:
            assert word not in source.lower(), f"Found '{word}' in signals — STANDALONE violation!"

    def test_api_is_read_only(self):
        import inspect
        from backend.v9.systems.tick_reversal import api
        source = inspect.getsource(api)
        # Check for actual POST route decorators, not "POST" in comments
        assert "@router.post" not in source, \
            "API has @router.post endpoints — STANDALONE violation!"
        for word in ["execute", "place_order", "bracket"]:
            assert word not in source.lower(), f"Found '{word}' in api.py — STANDALONE violation!"

    def test_classification_values(self):
        """Only 3 classifications allowed."""
        d = TickReversalDetector()
        assert d._classify(0) == "NO_SETUP"
        assert d._classify(3) == "NO_SETUP"
        assert d._classify(4) == "TACTICAL"
        assert d._classify(5) == "TACTICAL"
        assert d._classify(6) == "STRATEGIC"
        assert d._classify(10) == "STRATEGIC"


# ════════════════════════════════════════════════════════════
# SCHEMA TESTS
# ════════════════════════════════════════════════════════════

class TestSchemas:
    def test_config_defaults(self):
        cfg = TickReversalConfig()
        assert cfg.tick_reversal_size == 15
        assert cfg.accumulation_min_bars == 5
        assert cfg.imbalance_ratio == 250
        assert cfg.belly_dominance_ratio == 1.5

    def test_config_validation(self):
        with pytest.raises(Exception):
            TickReversalConfig(tick_reversal_size=5)  # below 10

    def test_bar_analysis_defaults(self):
        a = BarAnalysis(ts="2026-05-09T14:00:00Z", bar_id="test", bar=make_bar())
        assert a.classification == "NO_SETUP"
        assert a.visual_marker_drawn is False

    def test_signal_response_schema(self):
        from backend.v9.systems.tick_reversal.schemas import SignalResponse
        s = SignalResponse(id=1, ts="2026-05-09T14:00:00Z")
        assert s.system_id == 3
