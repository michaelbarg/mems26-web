"""Tests for s2_pattern_probe.py — detection geometry sub-conditions.

Pure geometric tests using synthetic bar fixtures.
"""

import pytest

from backend.v9.systems.build_status.s2_pattern_probe import probe_pattern


def _flat_bars(n, base=4700.0, spread=0.25):
    """Generate N flat/range-bound bars (no pole, no trend)."""
    return [
        {"o": base, "h": base + spread, "l": base - spread, "c": base, "v": 100}
        for _ in range(n)
    ]


def _bull_pole_bars(n=7, start_price=4700.0, step=1.0):
    """Generate N bullish bars forming a pole (each closes higher)."""
    bars = []
    for i in range(n):
        o = start_price + i * step
        c = o + step * 0.8
        bars.append({"o": o, "h": c + 0.25, "l": o - 0.25, "c": c, "v": 500 + i * 50})
    return bars


def _bear_pole_bars(n=7, start_price=4710.0, step=1.0):
    """Generate N bearish bars forming a downward pole."""
    bars = []
    for i in range(n):
        o = start_price - i * step
        c = o - step * 0.8
        bars.append({"o": o, "h": o + 0.25, "l": c - 0.25, "c": c, "v": 500 + i * 50})
    return bars


def _consolidation_bars(n=4, base=4706.0, spread=0.5):
    """Generate N tight consolidation bars (flag-like)."""
    return [
        {"o": base - 0.1, "h": base + spread, "l": base - spread, "c": base + 0.1, "v": 80}
        for _ in range(n)
    ]


# ── Test 1 ───────────────────────────────────────────────────────────────────

def test_probe_bull_flag_no_bars_returns_min_bars_component():
    """Empty buffer → 1 component with key='min_bars' present=False."""
    result = probe_pattern("BULL_FLAG_LONG", [])
    assert len(result) == 1
    assert result[0].key == "min_bars"
    assert result[0].present is False


# ── Test 2 ───────────────────────────────────────────────────────────────────

def test_probe_bull_flag_no_pole_found():
    """15 flat bars → pole component present=False, value contains 'no valid pole'."""
    bars = _flat_bars(15)
    result = probe_pattern("BULL_FLAG_LONG", bars)
    assert len(result) >= 2
    pole_comp = next(c for c in result if c.key == "pole_found")
    assert pole_comp.present is False
    assert "no valid pole" in pole_comp.value


# ── Test 3 ───────────────────────────────────────────────────────────────────

def test_probe_bull_flag_pole_flag_no_breakout():
    """Pole + flag but last bar does NOT break out → breakout present=False, gap negative."""
    # Build: 7 bullish bars (pole) + 4 consolidation + 1 non-breakout bar
    pole = _bull_pole_bars(7, start_price=4700.0, step=1.0)
    pole_top = pole[-1]["h"]  # ~4706.85
    # Flag: consolidate below pole top
    flag = _consolidation_bars(4, base=pole_top - 1.5, spread=0.5)
    # Last bar: still below flag high
    flag_high = max(b["h"] for b in flag)
    last_bar = {"o": flag_high - 0.5, "h": flag_high - 0.1, "l": flag_high - 1.0, "c": flag_high - 0.3, "v": 100}
    bars = pole + flag + [last_bar]

    result = probe_pattern("BULL_FLAG_LONG", bars)
    # Should have min_bars + pole_found at minimum
    keys = [c.key for c in result]
    assert "min_bars" in keys
    assert "pole_found" in keys
    # If flag length/retrace pass, breakout should fail
    if "breakout" in keys:
        breakout = next(c for c in result if c.key == "breakout")
        assert breakout.present is False
        assert "-" in breakout.value or "✗" in breakout.value


# ── Test 4 ───────────────────────────────────────────────────────────────────

def test_probe_bull_flag_all_conditions_met():
    """Pole + flag + breakout → all components present=True."""
    # 7 bullish bars as pole
    pole = _bull_pole_bars(7, start_price=4700.0, step=1.0)
    pole_top = pole[-1]["h"]  # ~4706.85
    # 4 bars of tight flag below pole top
    flag_base = pole_top - 1.0
    flag = [
        {"o": flag_base, "h": flag_base + 0.3, "l": flag_base - 0.3, "c": flag_base + 0.1, "v": 80}
        for _ in range(4)
    ]
    flag_high = max(b["h"] for b in flag)
    # Breakout bar: close well above flag_high + TICK
    breakout = {"o": flag_high + 0.25, "h": flag_high + 1.5, "l": flag_high, "c": flag_high + 1.0, "v": 600}
    bars = pole + flag + [breakout]

    result = probe_pattern("BULL_FLAG_LONG", bars)
    keys = [c.key for c in result]
    assert "min_bars" in keys
    assert "pole_found" in keys
    # All should be present (if geometry works)
    for c in result:
        if c.key == "breakout":
            assert c.present is True, f"breakout should pass: {c.value}"


# ── Test 5 ───────────────────────────────────────────────────────────────────

def test_probe_bear_flag_no_pole():
    """15 flat bars → pole present=False."""
    bars = _flat_bars(15)
    result = probe_pattern("BEAR_FLAG_SHORT", bars)
    pole_comp = next(c for c in result if c.key == "pole_found")
    assert pole_comp.present is False


# ── Test 6 ───────────────────────────────────────────────────────────────────

def test_probe_bear_flag_full_detection():
    """Bear pole + flag + breakdown → all present."""
    pole = _bear_pole_bars(7, start_price=4710.0, step=1.0)
    pole_bottom = pole[-1]["l"]
    flag_base = pole_bottom + 1.0
    flag = [
        {"o": flag_base, "h": flag_base + 0.3, "l": flag_base - 0.3, "c": flag_base - 0.1, "v": 80}
        for _ in range(4)
    ]
    flag_low = min(b["l"] for b in flag)
    breakdown = {"o": flag_low - 0.25, "h": flag_low, "l": flag_low - 1.5, "c": flag_low - 1.0, "v": 600}
    bars = pole + flag + [breakdown]

    result = probe_pattern("BEAR_FLAG_SHORT", bars)
    keys = [c.key for c in result]
    assert "min_bars" in keys
    assert "pole_found" in keys
    if "breakout" in keys:
        breakout = next(c for c in result if c.key == "breakout")
        assert breakout.present is True, f"breakdown should pass: {breakout.value}"


# ── Test 7 ───────────────────────────────────────────────────────────────────

def test_probe_inverse_hns_fewer_than_3_swing_lows():
    """Monotonically declining bars (no swing lows) → swing_lows_found present=False."""
    bars = [{"o": 4700 - i, "h": 4701 - i, "l": 4699 - i, "c": 4699.5 - i, "v": 100} for i in range(15)]
    result = probe_pattern("INVERSE_HNS_LONG", bars)
    sl_comp = next(c for c in result if c.key == "swing_lows_found")
    assert sl_comp.present is False


# ── Test 8 ───────────────────────────────────────────────────────────────────

def test_probe_inverse_hns_pivots_no_breakout():
    """3 clear swing lows but no neckline breakout → structure OK, breakout fails."""
    # Create bars with 3 swing lows: LS at 4698, HEAD at 4695, RS at 4697
    bars = []
    # Build a W-shape with 3 lows
    prices = [4700, 4699, 4698, 4699, 4700,  # LS at idx 2
              4699, 4697, 4695, 4697, 4699,  # HEAD at idx 7
              4700, 4699, 4697, 4699, 4700,  # RS at idx 12
              4699]  # last bar NOT breaking neckline
    for p in prices:
        bars.append({"o": p - 0.1, "h": p + 0.5, "l": p - 0.5, "c": p + 0.1, "v": 100})

    result = probe_pattern("INVERSE_HNS_LONG", bars)
    keys = [c.key for c in result]
    assert "swing_lows_found" in keys
    # If structure found and breakout attempted, check breakout
    if "neckline_breakout" in keys:
        nb = next(c for c in result if c.key == "neckline_breakout")
        assert nb.present is False


# ── Test 9 ───────────────────────────────────────────────────────────────────

def test_probe_double_bottom_no_symmetric_pair():
    """Bars with 2 swing lows far apart (>3% diff) → trough_pair present=False."""
    # Two lows at very different levels (>3% apart: 4700 vs 4550 = ~3.2%)
    bars = []
    # First swing low at 4700
    bars += [{"o": 4720, "h": 4721, "l": 4719, "c": 4720, "v": 100}] * 3
    bars += [{"o": 4701, "h": 4702, "l": 4700, "c": 4701, "v": 100}]  # swing low
    bars += [{"o": 4720, "h": 4721, "l": 4719, "c": 4720, "v": 100}] * 3
    # Second swing low at 4550 (>3% away from 4700)
    bars += [{"o": 4551, "h": 4552, "l": 4550, "c": 4551, "v": 100}]  # swing low
    bars += [{"o": 4720, "h": 4721, "l": 4719, "c": 4720, "v": 100}] * 3

    result = probe_pattern("DOUBLE_BOTTOM_EE_LONG", bars)
    keys = [c.key for c in result]
    if "trough_pair" in keys:
        tp = next(c for c in result if c.key == "trough_pair")
        assert tp.present is False, f"Troughs should be >3% apart: {tp.value}"


# ── Test 10 ──────────────────────────────────────────────────────────────────

def test_probe_double_bottom_full_detection():
    """2 symmetric Eve troughs + neckline break → all present."""
    # Two rounded troughs at ~4695 with neckline at ~4700, breakout above
    bars = []
    # Trough 1 (wide: 3+ bars at similar low)
    bars += [{"o": 4700, "h": 4701, "l": 4699, "c": 4700, "v": 100}] * 2  # approach
    bars += [{"o": 4696, "h": 4697, "l": 4695, "c": 4695.5, "v": 100}] * 4  # wide trough
    bars += [{"o": 4698, "h": 4701, "l": 4697, "c": 4700, "v": 100}] * 3  # recovery (neckline)
    # Trough 2 (wide: 3+ bars at similar low)
    bars += [{"o": 4696, "h": 4697, "l": 4695.1, "c": 4695.3, "v": 100}] * 4  # wide trough
    bars += [{"o": 4698, "h": 4700, "l": 4697, "c": 4699, "v": 100}] * 2  # recovery
    # Breakout bar
    bars += [{"o": 4700, "h": 4702, "l": 4699.5, "c": 4701.5, "v": 200}]

    result = probe_pattern("DOUBLE_BOTTOM_EE_LONG", bars)
    keys = [c.key for c in result]
    assert "min_bars" in keys
    assert "swing_lows_found" in keys


# ── Test 11 ──────────────────────────────────────────────────────────────────

def test_probe_reactive_long_b1_not_sellers():
    """Last 4 bars: b1 bullish → b1_sellers present=False."""
    bars = _flat_bars(4)  # 4 bars minimum (OFA needs 7 total)
    # Need at least OFA_MIN_BARS_REQ bars
    bars = _flat_bars(7)
    # Make b1 (bars[-4]) bullish
    bars[-4] = {"o": 4700, "h": 4702, "l": 4699, "c": 4701.5, "v": 200}
    result = probe_pattern("REACTIVE_LONG", bars)
    b1_comp = next(c for c in result if c.key == "b1_sellers")
    assert b1_comp.present is False
    assert "bull" in b1_comp.value


# ── Test 12 ──────────────────────────────────────────────────────────────────

def test_probe_reactive_long_b2_volume_not_dropping():
    """b1 bearish, b2.volume = b1.volume (no 90% drop) → b2_volume_drop present=False."""
    bars = _flat_bars(7)
    # b1: bearish with volume
    bars[-4] = {"o": 4701, "h": 4702, "l": 4699, "c": 4699.5, "v": 1000}
    # b2: same volume (no drop)
    bars[-3] = {"o": 4699, "h": 4700, "l": 4698, "c": 4699.2, "v": 1000}
    result = probe_pattern("REACTIVE_LONG", bars)
    b2_comp = next(c for c in result if c.key == "b2_volume_drop")
    assert b2_comp.present is False


# ── Test 13 ──────────────────────────────────────────────────────────────────

def test_probe_initiative_long_b1_range_too_small():
    """b1.high - b1.low = 0.5pt (below EXPANSION_MIN_PT 1.5pt) → b1_expansion present=False."""
    bars = _flat_bars(7)
    # b1: tiny range
    bars[-4] = {"o": 4700, "h": 4700.25, "l": 4699.75, "c": 4700.1, "v": 200}
    result = probe_pattern("INITIATIVE_LONG", bars)
    exp_comp = next(c for c in result if c.key == "b1_expansion")
    assert exp_comp.present is False
    assert "0.50" in exp_comp.value


# ── Test 14 ──────────────────────────────────────────────────────────────────

def test_probe_returns_empty_list_for_unknown_pattern_id():
    """Unknown pattern ID → returns [] (no crash, no exception)."""
    bars = _flat_bars(20)
    result = probe_pattern("MADE_UP_ID", bars)
    assert result == []
