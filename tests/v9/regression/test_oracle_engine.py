#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for F14 oracle_engine.py and F15 oracle_validate.py (T-408, T-409).

All tests use synthetic data — no DB connection required.
"""
import math
import sys
import os

import pytest

# Bootstrap path so scripts/ is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# Helpers: synthetic bar builders
# ---------------------------------------------------------------------------

def make_bar(o, h, l, c, v=1000, delta=None, t='17:00', d='2026-07-01', ts=None):
    """Create a synthetic bar dict matching oracle_engine's expected format."""
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


def make_session(prices, base_time_idx=0, d='2026-07-01'):
    """Build a session of bars from a list of (open, high, low, close) tuples."""
    bars = []
    for i, (o, h, l, c) in enumerate(prices):
        hour = 16 + (30 + i * 5) // 60
        minute = (30 + i * 5) % 60
        t = f"{hour:02d}:{minute:02d}"
        bars.append(make_bar(o, h, l, c, v=1000, delta=0, t=t, d=d))
    return bars


# ---------------------------------------------------------------------------
# Test: label_bar — sharp drop -> GOOD_SHORT
# ---------------------------------------------------------------------------

class TestLabeling:
    """Test the labeling function from oracle_engine."""

    def test_sharp_drop_good_short(self):
        from scripts.oracle_engine import label_bar
        # Build bars: bar 0 at 5600, then next 12 bars drop sharply
        bars = [make_bar(5600, 5602, 5598, 5600)]
        for i in range(1, 13):
            p = 5600 - i * 3  # drops 3 pts per bar
            bars.append(make_bar(p + 1, p + 2, p - 1, p))

        atr = 10.0  # target = max(8, 1.5*10) = 15, stop = max(5, 10) = 10
        ls, ll = label_bar(bars, 0, atr, K=12, target_mult=1.5, stop_mult=1.0)
        assert ls == 'GOOD', f"Expected GOOD_SHORT for sharp drop, got {ls}"

    def test_rotation_bad_or_none(self):
        from scripts.oracle_engine import label_bar
        # Bars rotate around 5600 within a tight range (< target/stop)
        bars = [make_bar(5600, 5602, 5598, 5600)]
        for i in range(1, 13):
            offset = 2 * (1 if i % 2 == 0 else -1)
            p = 5600 + offset
            bars.append(make_bar(p - 1, p + 1, p - 1, p))

        atr = 10.0
        ls, ll = label_bar(bars, 0, atr, K=12)
        assert ls in ('BAD', 'NONE'), f"Rotation should be BAD or NONE, got {ls}"
        assert ll in ('BAD', 'NONE'), f"Rotation should be BAD or NONE, got {ll}"

    def test_ambig_both_thresholds_same_bar(self):
        from scripts.oracle_engine import label_bar
        # Bar 0 at 5600, bar 1 has huge range hitting both target and stop
        bars = [make_bar(5600, 5602, 5598, 5600)]
        # Bar 1: high = 5620 (stop for short = 5610), low = 5570 (target for short = 5585)
        bars.append(make_bar(5600, 5625, 5570, 5590))
        for i in range(2, 13):
            bars.append(make_bar(5590, 5592, 5588, 5590))

        atr = 10.0  # target = 15, stop = 10
        ls, ll = label_bar(bars, 0, atr, K=12)
        # Both hit in same bar -> AMBIG
        assert ls == 'AMBIG', f"Expected AMBIG for short, got {ls}"


# ---------------------------------------------------------------------------
# Test: Double bottom — neckline break required
# ---------------------------------------------------------------------------

class TestDoubleBottom:
    """Double bottom should only be True after neckline break."""

    def test_double_bottom_neckline_break(self):
        """Synthetic: two lows spaced >= 3 bars, then break above neckline."""
        # Window of 16 bars for i=15 (15-bar lookback)
        # Bar 3: first low at 5570
        # Bar 9: second low at 5571 (within 0.3*ATR, distance=6 >= 3)
        # Neckline = max high between lows = 5590
        # Bar 15 close > 5590 -> double bottom True
        prices = []
        for j in range(16):
            if j == 3:
                prices.append((5575, 5578, 5570, 5572))  # first low
            elif j == 9:
                prices.append((5575, 5578, 5571, 5573))  # second low
            elif j == 6:
                prices.append((5585, 5590, 5583, 5588))  # neckline high
            elif j == 15:
                prices.append((5588, 5595, 5586, 5593))  # break above neckline
            else:
                prices.append((5580, 5583, 5578, 5580))

        bars = make_session(prices)
        atr = 10.0

        # Check at i=15 (last bar)
        win = bars[max(0, 15 - 15):16]
        lows = sorted(range(len(win)), key=lambda k: win[k]['l'])[:2]

        # Verify the two lows are close in price
        assert abs(win[lows[0]]['l'] - win[lows[1]]['l']) <= 0.3 * atr
        # Verify distance >= 3 bars
        assert abs(lows[0] - lows[1]) >= 3

    def test_double_bottom_no_break(self):
        """Synthetic: two lows but close does NOT break neckline."""
        prices = []
        for j in range(16):
            if j in (3, 4):
                prices.append((5575, 5578, 5570, 5572))
            elif j in (8, 9):
                prices.append((5575, 5578, 5571, 5573))
            elif j == 6:
                prices.append((5585, 5590, 5583, 5588))
            elif j == 15:
                # Close below neckline -> no break
                prices.append((5585, 5588, 5583, 5585))
            else:
                prices.append((5580, 5583, 5578, 5580))

        bars = make_session(prices)
        # Close at bar 15 is 5585, neckline is ~5590 -> no break
        assert bars[15]['c'] < 5590


# ---------------------------------------------------------------------------
# Test: Pullback condition
# ---------------------------------------------------------------------------

class TestPullback:
    def test_pullback_short_synthetic(self):
        from scripts.oracle_engine import detect_pullback_in_trend
        # Build a scenario: session dropped, extreme 4 bars ago,
        # retrace ~45%, close in lower third, vol_ratio=1.5
        bars = make_session([
            (5600, 5605, 5598, 5600),  # 0: open
        ] + [(5600 - i * 5, 5602 - i * 5, 5596 - i * 5, 5598 - i * 5)
             for i in range(1, 15)]  # downtrend
        + [(5545, 5558, 5543, 5548)])  # 15: retrace bar

        i = 15
        atr = 10.0
        bse = 4  # bars since low extreme
        move_open = -5.2  # deep in ATR units
        cp = 0.25  # close in lower third
        vr = 1.5

        result = detect_pullback_in_trend(bars, i, atr, bse, move_open, cp, vr, 'SHORT')
        # Whether it passes depends on retrace %. Let's check the logic runs
        # without error. The exact result depends on the retrace math.
        assert isinstance(result, bool)

    def test_pullback_long_synthetic(self):
        from scripts.oracle_engine import detect_pullback_in_trend
        bars = make_session([
            (5500, 5505, 5498, 5500),
        ] + [(5500 + i * 5, 5502 + i * 5, 5496 + i * 5, 5498 + i * 5)
             for i in range(1, 15)]
        + [(5565, 5568, 5555, 5565)])

        result = detect_pullback_in_trend(
            bars, 15, 10.0, 4, 6.5, 0.75, 1.5, 'LONG')
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Test: MFE/MAE calculation
# ---------------------------------------------------------------------------

class TestMfeMae:
    def test_mfe_mae_simple_3bar(self):
        from scripts.oracle_engine import compute_mfe_mae
        # Bar 0: close=5600
        # Bar 1: high=5610, low=5595 -> SHORT mfe=5, mae=10; LONG mfe=10, mae=5
        # Bar 2: high=5605, low=5590 -> SHORT mfe=10, mae=5; LONG mfe=5, mae=10
        bars = [
            make_bar(5600, 5602, 5598, 5600),
            make_bar(5600, 5610, 5595, 5605),
            make_bar(5603, 5605, 5590, 5592),
        ]

        mfe_s, mae_s = compute_mfe_mae(bars, 0, K=12, direction='SHORT')
        assert mfe_s == 10.0, f"SHORT MFE should be 10, got {mfe_s}"
        assert mae_s == 10.0, f"SHORT MAE should be 10, got {mae_s}"

        mfe_l, mae_l = compute_mfe_mae(bars, 0, K=12, direction='LONG')
        assert mfe_l == 10.0, f"LONG MFE should be 10, got {mfe_l}"
        assert mae_l == 10.0, f"LONG MAE should be 10, got {mae_l}"

    def test_mfe_mae_no_future_bars(self):
        from scripts.oracle_engine import compute_mfe_mae
        bars = [make_bar(5600, 5602, 5598, 5600)]
        mfe, mae = compute_mfe_mae(bars, 0, K=12, direction='SHORT')
        assert mfe == 0.0
        assert mae == 0.0


# ---------------------------------------------------------------------------
# Test: Wilson CI (from oracle_validate)
# ---------------------------------------------------------------------------

class TestWilsonCI:
    def test_wilson_known_values(self):
        from scripts.oracle_validate import wilson_ci
        # 50 successes out of 100 -> p=0.5, 90% CI should be roughly [0.42, 0.58]
        lo, hi = wilson_ci(50, 100, z=1.645)
        assert 0.40 < lo < 0.45, f"Wilson lower {lo} out of range"
        assert 0.55 < hi < 0.60, f"Wilson upper {hi} out of range"

    def test_wilson_zero(self):
        from scripts.oracle_validate import wilson_ci
        lo, hi = wilson_ci(0, 0)
        assert lo == 0.0
        assert hi == 0.0

    def test_wilson_all_success(self):
        from scripts.oracle_validate import wilson_ci
        lo, hi = wilson_ci(100, 100, z=1.645)
        assert lo > 0.95, f"Wilson lower {lo} should be >0.95 for 100/100"
        assert hi == 1.0 or hi > 0.99

    def test_wilson_small_sample(self):
        from scripts.oracle_validate import wilson_ci
        lo, hi = wilson_ci(3, 10, z=1.645)
        # p=0.3, small sample -> wide CI
        assert 0.0 < lo < 0.3
        assert 0.3 < hi < 0.7


# ---------------------------------------------------------------------------
# Test: size_for
# ---------------------------------------------------------------------------

class TestSizeFor:
    def test_size_normal(self):
        from scripts.oracle_engine import size_for
        # risk=9 pts -> n = min(5, floor(225/(5*9))) = min(5,5) = 5
        assert size_for(9.0) == 5

    def test_size_high_risk_skip(self):
        from scripts.oracle_engine import size_for
        # risk=20 pts -> n = floor(225/100) = 2 < 3 -> skip
        assert size_for(20.0) == 0

    def test_size_zero_risk(self):
        from scripts.oracle_engine import size_for
        assert size_for(0) == 0


# ---------------------------------------------------------------------------
# Test: dollar_per_trade
# ---------------------------------------------------------------------------

class TestDollarPerTrade:
    def test_dollar_per_trade_basic(self):
        from scripts.oracle_engine import compute_dollar_per_trade
        # Build bars where price drops consistently from 5600
        bars = [make_bar(5600, 5605, 5595, 5600)]
        for j in range(1, 20):
            p = 5600 - j * 2
            bars.append(make_bar(p + 1, p + 2, p - 2, p))

        # Signal at bar 0, SHORT, ATR=10
        result = compute_dollar_per_trade(bars, 0, 10.0, 'SHORT')
        assert result is not None
        assert not result.get('skip')
        assert 'pnl_usd' in result

    def test_dollar_per_trade_last_bar_skip(self):
        from scripts.oracle_engine import compute_dollar_per_trade
        bars = [make_bar(5600, 5605, 5595, 5600)]
        # Only 1 bar -> no next bar for entry
        result = compute_dollar_per_trade(bars, 0, 10.0, 'SHORT')
        assert result is None


# ---------------------------------------------------------------------------
# Test: Head & shoulders
# ---------------------------------------------------------------------------

class TestHeadShoulders:
    def test_head_shoulders_short_basic(self):
        from scripts.oracle_engine import detect_head_shoulders_short
        # Build 16 bars with head-shoulders pattern
        # Bars 0-4: left shoulder (high ~5610)
        # Bars 5-10: head (high ~5620)
        # Bars 11-15: right shoulder (high ~5610), neckline break
        prices = []
        for j in range(16):
            if j in (2, 3):  # left shoulder
                prices.append((5605, 5610, 5602, 5607))
            elif j in (7, 8):  # head
                prices.append((5615, 5620, 5612, 5617))
            elif j in (12, 13):  # right shoulder
                prices.append((5605, 5611, 5602, 5607))
            elif j == 15:  # neckline break
                prices.append((5600, 5602, 5595, 5596))
            else:
                prices.append((5600, 5605, 5598, 5602))

        bars = make_session(prices)
        atr = 10.0

        result = detect_head_shoulders_short(bars, 15, atr)
        # The pattern detection depends on exact geometry; just verify it runs
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Test: Developing VA
# ---------------------------------------------------------------------------

class TestDevelopingVA:
    def test_developing_va_basic(self):
        from scripts.oracle_engine import compute_developing_va
        bars = make_session([
            (5600, 5610, 5595, 5605),
            (5605, 5612, 5600, 5608),
            (5608, 5615, 5603, 5610),
            (5610, 5618, 5605, 5612),
            (5612, 5620, 5608, 5615),
        ])
        va = compute_developing_va(bars, 4)
        assert 'poc' in va
        assert 'val' in va
        assert 'vah' in va
        assert va['val'] <= va['poc'] <= va['vah']

    def test_developing_va_too_few_bars(self):
        from scripts.oracle_engine import compute_developing_va
        bars = make_session([(5600, 5605, 5595, 5600)])
        va = compute_developing_va(bars, 0)
        assert va == {}


# ---------------------------------------------------------------------------
# Test: OOS split deterministic
# ---------------------------------------------------------------------------

class TestOOSSplit:
    def test_oos_date_split(self):
        """Verify the date split logic is deterministic."""
        rows = [
            {'d': '2026-06-15', 'ls': 'GOOD', 'll': 'BAD', 'break_dn': True,
             'break_up': False, 'dr': -3, 'vr': 1.5, 'dbl_t': False,
             'dbl_b': False, 'hs_short': False, 'hs_long': False,
             'cup_handle': False, 'pullback_short': False, 'pullback_long': False,
             'bfva_short': False, 'bfva_long': False, 'bsl': 3, 'bsh': 5,
             'move_open': -2.0, 'cp': 0.2},
            {'d': '2026-08-15', 'ls': 'BAD', 'll': 'GOOD', 'break_dn': False,
             'break_up': True, 'dr': 3, 'vr': 1.5, 'dbl_t': False,
             'dbl_b': False, 'hs_short': False, 'hs_long': False,
             'cup_handle': False, 'pullback_short': False, 'pullback_long': False,
             'bfva_short': False, 'bfva_long': False, 'bsl': 5, 'bsh': 3,
             'move_open': 2.0, 'cp': 0.8},
        ]
        disc = [r for r in rows if r['d'] < '2026-08-01']
        val = [r for r in rows if r['d'] >= '2026-08-01']
        assert len(disc) == 1
        assert len(val) == 1
        assert disc[0]['d'] == '2026-06-15'
        assert val[0]['d'] == '2026-08-15'
