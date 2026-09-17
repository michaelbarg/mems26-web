#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for F17 setup_engine.py (T-411) — multi-bar setup detection.

All tests use synthetic data — no DB connection required.
Golden session tests tagged with 'db' marker for integration runs.
"""
import math
import sys
import os
import statistics

import pytest

# Bootstrap path so scripts/ is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, _ROOT)

from scripts.setup_engine import (
    detect_setups, compute_atr, compute_developing_va, compute_ib,
    DEFAULT_PARAMS, TICK_SIZE,
)


# ---------------------------------------------------------------------------
# Helpers: synthetic bar builders
# ---------------------------------------------------------------------------
def make_bar(o, h, l, c, v=1000, delta=None, t='17:00', d='2026-07-01', ts=None):
    """Create a synthetic bar dict matching setup_engine's expected format."""
    return {
        'ts': ts or f'{d} {t}:00+03',
        'd': d,
        't': t + ':00',
        'o': float(o),
        'h': float(h),
        'l': float(l),
        'c': float(c),
        'v': v,
        'delta': delta,
    }


def make_time(bar_idx):
    """Generate HH:MM from bar index (starting at 16:30)."""
    hour = 16 + (30 + bar_idx * 5) // 60
    minute = (30 + bar_idx * 5) % 60
    return f"{hour:02d}:{minute:02d}"


def build_golden_17_09():
    """Build the golden 17.09 session bars from the spec.

    Bars from SETUP_GRAMMAR_2026-09-17.md:
    16:30  7713.5->7695.75   v=30k  delta=-1348   (Open-Drive down)
    16:35  ...               v=25k  delta=-800     (continued drive)
    16:40  low 7688.25       v=21k  delta=+144     (first touch)
    16:45  low 7688.25       v=21k  delta=+834     (positive delta on low = absorption)
    16:50  ...               v=15k  delta=+200     (bounce, NOT a trigger — no absorption yet)
    16:55  low 7688.25       v=13k  delta=-333
    17:00  low 7683.75       v=19k  delta=-2855    (second push, heavy delta)
    17:05  low 7680.5        v=15k  delta=-1372    (second push cont, progress limited)
    17:10  7683.25->7692.25  v=17k  delta=+3319    (TRIGGER: closes above prev high, top 30%)
    17:15  ->7695.75         v=14k  delta=+2159    (entry bar for DBL_BOTTOM_ABS)
    17:20  ->7700.75         v=12k  delta=+1500
    17:25  high 7704.0       v=11k  delta=+900
    17:30  7703.0->7700.0    v=10k  delta=-200
    17:35  7700.0->7698.0    v=10k  delta=-150
    17:40  7698.0->7696.25   v=10k  delta=-180     (rotation start)
    17:45  7696.0->7693.25   v=16.8k delta=-3093   (TRIGGER: rotation break SHORT)
    17:50  7693.0->7685.5    v=18k  delta=-2500    (entry bar for ROTATION_BREAK)
    """
    # We need at least 14 bars before index to compute ATR.
    # Build pre-session bars for ATR warmup (bars 0-13) then the real bars.
    bars = []
    d = '2026-09-17'

    # Pre-warmup bars (0-13): steady around 7713-7720, typical range ~7pts
    for i in range(14):
        base = 7715 + (i % 3) * 2
        t = make_time(i)
        bars.append(make_bar(
            base, base + 4, base - 3, base + 1,
            v=15000, delta=100 * ((-1) ** i), t=t, d=d
        ))

    # Overwrite bars at the right positions with the golden data.
    # bar idx 0 = 16:30 in the golden spec
    # We use absolute indices, adding the warmup.

    # Actually, let's build a clean session. ATR needs 14 prior bars.
    # We'll put the meaningful bars starting at idx 14 so ATR is computed from 0-13.
    # But the spec times start at 16:30 = idx 0 in real trading.
    # The simplest approach: build 14 warmup bars, then append the golden bars.

    bars = []
    # Warmup: bars 0-13, times 16:30 - 17:35
    # To avoid conflicting with the golden bars, let's use a different approach:
    # Build the FULL session as it would be, starting from 16:30.
    # The golden bars are at 16:30 (idx 0) through 17:50 (idx 16).
    # ATR needs 14 bars, so the first bar where ATR is available = idx 14 = 17:40.
    # But our trigger at 17:10 = idx 8 needs ATR.
    # Solution: we need to prepend extra bars OR lower the ATR period.
    #
    # For testing, we'll build a long enough session that ATR is available at the
    # golden trigger bars. We'll prepend 14 "pre-open" bars before 16:30.

    bars = []
    # 14 pre-warmup bars (indices 0-13), these are just for ATR computation.
    # Use wider ranges (~10 pts) to produce a realistic ATR (~8-9) that
    # matches a real session with an open-drive bar.
    for i in range(14):
        base = 7720 - i * 0.5
        bars.append(make_bar(
            base, base + 5.0, base - 5.0, base - 0.5,
            v=12000, delta=None, t=f"15:{30+i:02d}", d=d
        ))

    # Now the golden session bars (indices 14+)
    golden = [
        # idx 14 = 16:30: open drive down
        (7713.5, 7713.5, 7695.75, 7695.75, 30000, -1348, '16:30'),
        # idx 15 = 16:35: continued drive
        (7695.75, 7696.0, 7690.0, 7692.0, 25000, -800, '16:35'),
        # idx 16 = 16:40: first touch near VAL (low 7688.25)
        (7692.0, 7693.0, 7688.25, 7690.0, 21000, 144, '16:40'),
        # idx 17 = 16:45: absorption at first low
        (7690.0, 7691.0, 7688.25, 7690.5, 21000, 834, '16:45'),
        # idx 18 = 16:50: small bounce (NOT trigger — no full absorption sequence yet)
        (7690.5, 7692.0, 7689.0, 7691.5, 15000, 200, '16:50'),
        # idx 19 = 16:55: retest
        (7691.5, 7691.5, 7688.25, 7689.0, 13000, -333, '16:55'),
        # idx 20 = 17:00: second push down, heavy delta
        (7689.0, 7689.5, 7683.75, 7685.0, 19000, -2855, '17:00'),
        # idx 21 = 17:05: second push continued, limited progress below first low
        (7685.0, 7687.5, 7680.5, 7683.5, 15000, -1372, '17:05'),
        # idx 22 = 17:10: TRIGGER — closes above prev high (7687.5), top 30%, huge +delta
        (7683.25, 7692.25, 7682.0, 7692.25, 17000, 3319, '17:10'),
        # idx 23 = 17:15: entry bar for DBL_BOTTOM_ABS LONG
        (7692.25, 7695.75, 7691.0, 7695.75, 14000, 2159, '17:15'),
        # idx 24 = 17:20
        (7695.75, 7700.75, 7695.0, 7700.75, 12000, 1500, '17:20'),
        # idx 25 = 17:25
        (7700.75, 7704.0, 7700.0, 7703.0, 11000, 900, '17:25'),
        # idx 26 = 17:30
        (7703.0, 7703.5, 7699.0, 7700.0, 10000, -200, '17:30'),
        # idx 27 = 17:35
        (7700.0, 7700.5, 7697.0, 7698.0, 10000, -150, '17:35'),
        # idx 28 = 17:40: rotation start
        (7698.0, 7699.0, 7696.25, 7696.25, 10000, -180, '17:40'),
        # idx 29 = 17:45: TRIGGER for rotation break SHORT
        (7696.25, 7696.5, 7693.0, 7693.25, 16800, -3093, '17:45'),
        # idx 30 = 17:50: entry bar for ROTATION_BREAK SHORT
        (7693.25, 7693.5, 7685.5, 7685.5, 18000, -2500, '17:50'),
        # idx 31 = 17:55: continuation
        (7685.5, 7686.0, 7680.0, 7681.0, 15000, -1800, '17:55'),
    ]

    for o, h, l, c, v, delta, t in golden:
        bars.append(make_bar(o, h, l, c, v=v, delta=delta, t=t, d=d))

    return bars


def build_levels_17_09():
    """Levels for the golden 17.09 session."""
    return {
        'pd_vah': 7680.75,   # previous session VAH
        'pd_val': 7660.0,    # previous session VAL
        'pd_poc': 7670.0,    # previous session POC
        'ib_high': 7713.5,   # from bar 16:30 (the open)
        'ib_low': 7688.25,   # from the first touch area
        'developing_vah': 7703.75,
        'developing_val': 7687.5,
    }


# ---------------------------------------------------------------------------
# Test DBL_BOTTOM_ABS
# ---------------------------------------------------------------------------
class TestDblBottomAbs:
    """Test double bottom at value edge with absorption."""

    def test_golden_17_10_long_fires(self):
        """Golden 17.09: DBL_BOTTOM_ABS LONG fires at 17:10."""
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        hits = detect_setups(bars, levels, {})

        dbl_longs = [h for h in hits
                     if h['setup_id'] == 'DBL_BOTTOM_ABS'
                     and h['direction'] == 'LONG']
        assert len(dbl_longs) >= 1, (
            f"Expected DBL_BOTTOM_ABS LONG, got: "
            f"{[(h['setup_id'], h['direction'], h['trigger_il']) for h in hits]}"
        )

        # The trigger should be at 17:10 (bar index 22)
        trigger_17_10 = [h for h in dbl_longs if h['trigger_il'] == '17:10']
        assert len(trigger_17_10) == 1, (
            f"Expected trigger at 17:10, got triggers at: "
            f"{[h['trigger_il'] for h in dbl_longs]}"
        )

        hit = trigger_17_10[0]
        # Entry should be open of 17:15 bar (~7692.25)
        assert abs(hit['entry'] - 7692.25) < 1.0, f"Entry {hit['entry']} not near 7692.25"
        # Stop should be below the second low
        assert hit['stop'] < 7681.0, f"Stop {hit['stop']} should be below 7681"
        # Evidence
        assert hit['evidence']['absorption'] is True
        assert hit['evidence']['delta_trigger'] > 0

    def test_must_not_fire_long_at_16_50(self):
        """Golden 17.09: MUST NOT fire LONG at 16:50 (only first touch, no absorption)."""
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        hits = detect_setups(bars, levels, {})

        # No DBL_BOTTOM_ABS LONG at 16:50
        bad = [h for h in hits
               if h['setup_id'] == 'DBL_BOTTOM_ABS'
               and h['direction'] == 'LONG'
               and h['trigger_il'] == '16:50']
        assert len(bad) == 0, (
            f"MUST NOT fire DBL_BOTTOM_ABS LONG at 16:50 (no absorption yet), "
            f"but found: {bad}"
        )

    def test_must_not_fire_short_at_17_10(self):
        """Golden 17.09: MUST NOT fire SHORT at 17:10 (opposite direction of setup #1)."""
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        hits = detect_setups(bars, levels, {})

        bad = [h for h in hits
               if h['setup_id'] in ('DBL_BOTTOM_ABS', 'ROTATION_BREAK')
               and h['direction'] == 'SHORT'
               and h['trigger_il'] == '17:10']
        assert len(bad) == 0, (
            f"MUST NOT fire SHORT at 17:10, but found: {bad}"
        )

    def test_synthetic_no_absorption_no_hit(self):
        """Synthetic double bottom WITHOUT absorption -> no hit."""
        bars = []
        d = '2026-08-01'

        # 14 warmup bars for ATR
        for i in range(14):
            base = 5600
            bars.append(make_bar(base, base + 4, base - 3, base + 1,
                                 v=10000, delta=100, t=make_time(i), d=d))

        # Drive down (bar 14-15)
        bars.append(make_bar(5600, 5601, 5580, 5582, v=20000, delta=-1000,
                             t=make_time(14), d=d))
        bars.append(make_bar(5582, 5583, 5575, 5577, v=18000, delta=-800,
                             t=make_time(15), d=d))
        # First low (bar 16)
        bars.append(make_bar(5577, 5578, 5570, 5575, v=12000, delta=-100,
                             t=make_time(16), d=d))
        # Bounce bars (17-19)
        bars.append(make_bar(5575, 5580, 5574, 5579, v=10000, delta=50,
                             t=make_time(17), d=d))
        bars.append(make_bar(5579, 5582, 5578, 5581, v=9000, delta=30,
                             t=make_time(18), d=d))
        bars.append(make_bar(5581, 5582, 5577, 5578, v=8000, delta=-20,
                             t=make_time(19), d=d))
        # Second low (bar 20) — but NO absorption: delta is tiny
        bars.append(make_bar(5578, 5578, 5571, 5573, v=8000, delta=-50,
                             t=make_time(20), d=d))
        # "Trigger" bar (21) — closes above prev high
        bars.append(make_bar(5573, 5585, 5572, 5584, v=12000, delta=200,
                             t=make_time(21), d=d))
        # Next bar (22) for entry
        bars.append(make_bar(5584, 5590, 5583, 5589, v=10000, delta=150,
                             t=make_time(22), d=d))

        levels = {
            'pd_val': 5572.0,
            'pd_vah': 5620.0,
            'pd_poc': 5595.0,
            'ib_high': 5605.0,
            'ib_low': 5570.0,
            'developing_val': 5570.0,
            'developing_vah': 5610.0,
        }

        hits = detect_setups(bars, levels, {})
        dbl_hits = [h for h in hits if h['setup_id'] == 'DBL_BOTTOM_ABS']
        assert len(dbl_hits) == 0, (
            f"No absorption => no DBL_BOTTOM_ABS hit, but got: {dbl_hits}"
        )

    def test_trigger_without_close_in_extreme_no_hit(self):
        """Trigger bar that closes in the middle (not top 30%) -> no hit."""
        bars = []
        d = '2026-08-01'

        for i in range(14):
            base = 5600
            bars.append(make_bar(base, base + 4, base - 3, base + 1,
                                 v=10000, delta=100, t=make_time(i), d=d))

        # Drive down
        bars.append(make_bar(5600, 5601, 5580, 5582, v=20000, delta=-1500,
                             t=make_time(14), d=d))
        bars.append(make_bar(5582, 5583, 5575, 5577, v=18000, delta=-1200,
                             t=make_time(15), d=d))
        # First low near level
        bars.append(make_bar(5577, 5578, 5570, 5575, v=15000, delta=-100,
                             t=make_time(16), d=d))
        # Bounce
        bars.append(make_bar(5575, 5582, 5574, 5580, v=12000, delta=200,
                             t=make_time(17), d=d))
        bars.append(make_bar(5580, 5583, 5579, 5582, v=11000, delta=100,
                             t=make_time(18), d=d))
        bars.append(make_bar(5582, 5583, 5578, 5579, v=10000, delta=-50,
                             t=make_time(19), d=d))
        # Second low with heavy delta (absorption)
        bars.append(make_bar(5579, 5580, 5571, 5573, v=18000, delta=-2000,
                             t=make_time(20), d=d))
        # "Trigger" bar: closes in MIDDLE of range (50%), not top 30%
        bars.append(make_bar(5573, 5585, 5572, 5578.5, v=15000, delta=1500,
                             t=make_time(21), d=d))
        # Next bar
        bars.append(make_bar(5578.5, 5585, 5577, 5584, v=12000, delta=500,
                             t=make_time(22), d=d))

        levels = {
            'pd_val': 5572.0,
            'pd_vah': 5620.0,
            'pd_poc': 5595.0,
            'ib_high': 5605.0,
            'ib_low': 5570.0,
            'developing_val': 5570.0,
            'developing_vah': 5610.0,
        }

        hits = detect_setups(bars, levels, {})
        dbl_hits = [h for h in hits
                    if h['setup_id'] == 'DBL_BOTTOM_ABS'
                    and h['trigger_il'] == make_time(21)]
        assert len(dbl_hits) == 0, (
            f"Trigger not in top 30% => no hit, but got: {dbl_hits}"
        )


# ---------------------------------------------------------------------------
# Test ROTATION_BREAK
# ---------------------------------------------------------------------------
class TestRotationBreak:
    """Test rotation break after drive."""

    def test_golden_17_45_short_fires(self):
        """Golden 17.09: ROTATION_BREAK SHORT fires at 17:45."""
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        hits = detect_setups(bars, levels, {})

        rot_shorts = [h for h in hits
                      if h['setup_id'] == 'ROTATION_BREAK'
                      and h['direction'] == 'SHORT']
        assert len(rot_shorts) >= 1, (
            f"Expected ROTATION_BREAK SHORT, got: "
            f"{[(h['setup_id'], h['direction'], h['trigger_il']) for h in hits]}"
        )

        trigger_17_45 = [h for h in rot_shorts if h['trigger_il'] == '17:45']
        assert len(trigger_17_45) == 1, (
            f"Expected trigger at 17:45, got: "
            f"{[h['trigger_il'] for h in rot_shorts]}"
        )

        hit = trigger_17_45[0]
        # Entry should be open of 17:50 bar (~7693.25)
        assert abs(hit['entry'] - 7693.25) < 1.0, f"Entry {hit['entry']} not near 7693.25"
        # Evidence
        assert hit['evidence']['delta_trigger'] < 0

    def test_synthetic_no_volume_decay_no_hit(self):
        """Synthetic rotation without volume decay -> no hit."""
        bars = []
        d = '2026-08-02'

        # 14 warmup bars
        for i in range(14):
            base = 5600
            bars.append(make_bar(base, base + 4, base - 3, base + 1,
                                 v=10000, delta=100, t=make_time(i), d=d))

        # Drive up (bars 14-16) — creates the pre-rotation drive
        bars.append(make_bar(5600, 5620, 5599, 5618, v=20000, delta=1500,
                             t=make_time(14), d=d))
        bars.append(make_bar(5618, 5635, 5617, 5633, v=18000, delta=1200,
                             t=make_time(15), d=d))
        bars.append(make_bar(5633, 5650, 5632, 5648, v=16000, delta=1000,
                             t=make_time(16), d=d))

        # Rotation bars (17-21): INCREASING volume (no decay)
        for ri in range(5):
            bars.append(make_bar(
                5648 - ri * 0.5, 5650 + ri * 0.3, 5645, 5647,
                v=10000 + ri * 3000,  # INCREASING volume
                delta=(-1)**ri * 100,
                t=make_time(17 + ri), d=d
            ))

        # "Trigger" bar — breaks below rotation with big volume + delta
        bars.append(make_bar(5647, 5648, 5640, 5641, v=25000, delta=-3000,
                             t=make_time(22), d=d))
        # Next bar (entry)
        bars.append(make_bar(5641, 5642, 5635, 5636, v=15000, delta=-1500,
                             t=make_time(23), d=d))

        levels = {
            'pd_val': 5580.0,
            'pd_vah': 5640.0,
            'pd_poc': 5610.0,
            'ib_high': 5625.0,
            'ib_low': 5580.0,
            'developing_val': 5640.0,
            'developing_vah': 5660.0,
        }

        hits = detect_setups(bars, levels, {})
        rot_hits = [h for h in hits if h['setup_id'] == 'ROTATION_BREAK']
        assert len(rot_hits) == 0, (
            f"No volume decay => no ROTATION_BREAK, but got: {rot_hits}"
        )


# ---------------------------------------------------------------------------
# Test: parameters are from dict, not hardcoded
# ---------------------------------------------------------------------------
class TestParameterOverride:
    """Verify that params dict controls detection."""

    def test_stricter_absorption_blocks_hit(self):
        """With absorption_mult=100, nothing should fire."""
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        # Unreasonably high absorption requirement
        hits = detect_setups(bars, levels, {"dbl_absorption_mult": 100.0})
        dbl_hits = [h for h in hits if h['setup_id'] == 'DBL_BOTTOM_ABS']
        assert len(dbl_hits) == 0, (
            f"With absorption_mult=100, no DBL_BOTTOM_ABS should fire: {dbl_hits}"
        )

    def test_stricter_rot_vol_blocks_hit(self):
        """With rot_trigger_vol_mult=100, nothing should fire."""
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        hits = detect_setups(bars, levels, {"rot_trigger_vol_mult": 100.0})
        rot_hits = [h for h in hits if h['setup_id'] == 'ROTATION_BREAK']
        assert len(rot_hits) == 0, (
            f"With rot_trigger_vol_mult=100, no ROTATION_BREAK should fire: {rot_hits}"
        )


# ---------------------------------------------------------------------------
# Test: detect_setups is importable and returns correct shape
# ---------------------------------------------------------------------------
class TestDetectSetupsAPI:
    """Verify the public API contract."""

    def test_returns_list(self):
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        result = detect_setups(bars, levels, {})
        assert isinstance(result, list)

    def test_hit_shape(self):
        bars = build_golden_17_09()
        levels = build_levels_17_09()
        result = detect_setups(bars, levels, {})
        assert len(result) > 0, "Expected at least one hit on golden session"
        hit = result[0]
        required_keys = {
            'setup_id', 'direction', 'trigger_idx', 'trigger_il',
            'entry', 'stop', 't1', 't2', 'sequence_bars', 'location',
            'evidence',
        }
        assert required_keys.issubset(hit.keys()), (
            f"Missing keys: {required_keys - hit.keys()}"
        )
        assert hit['direction'] in ('LONG', 'SHORT')
        assert isinstance(hit['sequence_bars'], list)
        assert isinstance(hit['evidence'], dict)

    def test_accepts_full_key_names(self):
        """detect_setups should accept bars with 'open'/'high'/'low'/'close' keys."""
        bar = {
            'open': 100.0, 'high': 102.0, 'low': 99.0, 'close': 101.0,
            'volume': 1000, 'delta': 50, 'il': '17:00',
            'd': '2026-07-01',
        }
        # Just verifying it doesn't crash
        result = detect_setups([bar] * 30, {'pd_val': 99.0}, {})
        assert isinstance(result, list)
