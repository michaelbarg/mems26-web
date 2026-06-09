"""FIX 7: Flag stop = breakout bar + relative T1.

Calls REAL detect_bear_flag on bars that reproduce trade #22.
Verifies anchor = breakout_high + TICK (not flag_high).

RED-on-revert: reverting flags.py:249 to flag_high → anchor=7349.25 → FAILS.
"""
from backend.v9.systems.five_min.patterns.flags import detect_bear_flag, TICK_SIZE


def _trade22_bars():
    """Bars that trigger BEAR_FLAG_SHORT with breakout at 7334.50."""
    lookback = [
        {"o": 7420, "h": 7425, "l": 7415, "c": 7418, "vol": 5000, "v": 5000}
        for _ in range(10)
    ]
    pole = [
        {"o": 7415, "h": 7416, "l": 7390, "c": 7392, "vol": 15000, "v": 15000},
        {"o": 7392, "h": 7393, "l": 7370, "c": 7372, "vol": 14000, "v": 14000},
        {"o": 7372, "h": 7373, "l": 7350, "c": 7352, "vol": 13000, "v": 13000},
        {"o": 7352, "h": 7353, "l": 7335, "c": 7337, "vol": 12000, "v": 12000},
        {"o": 7337, "h": 7338, "l": 7320, "c": 7322, "vol": 11000, "v": 11000},
    ]
    flag = [
        {"o": 7325, "h": 7340, "l": 7320, "c": 7335, "vol": 4000, "v": 4000},
        {"o": 7335, "h": 7349, "l": 7328, "c": 7330, "vol": 3500, "v": 3500},
        {"o": 7330, "h": 7338, "l": 7325, "c": 7332, "vol": 3000, "v": 3000},
    ]
    breakout = {"o": 7330, "h": 7334.50, "l": 7305, "c": 7308, "vol": 10000, "v": 10000}
    return lookback + pole + flag + [breakout]


def test_bear_flag_stop_is_breakout_bar():
    """7A: detect_bear_flag anchor = breakout_high + TICK, NOT flag_high."""
    bars = _trade22_bars()
    direction, conf, info = detect_bear_flag(bars)

    assert direction == "SHORT", f"Expected SHORT, got {direction}"
    anchor = info["structural_anchor"]
    breakout_high = bars[-1]["h"]   # 7334.50
    flag_high = info["flag_high"]   # 7349

    expected_breakout = breakout_high + TICK_SIZE   # 7334.75
    expected_old = flag_high + TICK_SIZE            # 7349.25

    assert abs(anchor - expected_breakout) < 0.01, \
        f"Anchor={anchor}, expected breakout+T={expected_breakout}. " \
        f"Got flag_high+T={expected_old}? FIX 7A reverted!"


def test_relative_t1_on_trade22_risk():
    """7B: T1 relative from YAML. Risk 21.75pt → t1_r ≈ 0.53."""
    from backend.v9.config_loader import load_stop_anchors
    cfg = load_stop_anchors()
    ft = cfg["flag_relative_t1"]

    entry = 7313.5
    stop = 7335.25
    risk = stop - entry  # 21.75

    t1_r = ft["t1_r_max"] - (risk - ft["dist_tight_pts"]) / \
        (ft["dist_wide_pts"] - ft["dist_tight_pts"]) * (ft["t1_r_max"] - ft["t1_r_min"])
    t1_r = max(ft["t1_r_min"], min(ft["t1_r_max"], t1_r))

    assert 0.52 < t1_r < 0.54, f"t1_r={t1_r}, expected ≈0.53"
    t1 = entry - t1_r * risk
    assert 7301 < t1 < 7303, f"T1={t1}, expected ≈7302"


def test_relative_t1_clamps():
    """T1 clamps at boundaries (YAML values)."""
    from backend.v9.config_loader import load_stop_anchors
    cfg = load_stop_anchors()
    ft = cfg["flag_relative_t1"]
    assert ft["t1_r_max"] == 0.8
    assert ft["t1_r_min"] == 0.4
    assert ft["dist_tight_pts"] == 15
    assert ft["dist_wide_pts"] == 25
