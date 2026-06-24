"""Anti-tautological tests for relative_features.compute_relative_features.

Each synthetic session is built to a day-type signature, and we assert the
relative features fall out correctly. The `*_reverted` checks prove the
assertions are NOT tautological: remove the defining behavior → the feature flips.
"""
from backend.v9.systems.day_type.relative_features import compute_relative_features


def _bar(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


def _ib_bars(lo=100.0, hi=105.0, n=12):
    """n IB bars oscillating inside [lo, hi]."""
    out = []
    for i in range(n):
        if i % 2 == 0:
            out.append(_bar(lo + 1, hi, lo, hi - 1))
        else:
            out.append(_bar(hi - 1, hi, lo, lo + 1))
    return out


IB_LO, IB_HI = 100.0, 105.0


def test_trend_up_signature():
    """One-sided up-trend that breaks & holds above IB: sides=1, rib high, one_tf=UP."""
    bars = _ib_bars()
    # 12 post-IB bars stepping up, each closing above IB high, higher-lows
    for k in range(1, 13):
        base = 105.0 + k  # 106..117
        bars.append(_bar(base - 0.5, base + 0.75, base - 0.75, base))
    f = compute_relative_features(bars, IB_HI, IB_LO)
    assert f.sides == 1, f.as_dict()
    assert f.ext_up_hold and not f.ext_dn_hold, f.as_dict()
    assert f.rib is not None and f.rib >= 2.5, f.as_dict()
    assert f.one_tf == "UP", f.as_dict()
    assert f.close_pos is not None and f.close_pos >= 0.8, f.as_dict()


def test_trend_up_reverted_no_breakout():
    """ANTI-TAUTOLOGY: same shape but capped inside IB → sides=0, not a trend."""
    bars = _ib_bars()
    for _ in range(12):
        bars.append(_bar(102, 104, 101, 103))  # stays inside IB
    f = compute_relative_features(bars, IB_HI, IB_LO)
    assert f.sides == 0, f.as_dict()
    assert f.rib is not None and f.rib < 1.3, f.as_dict()


def test_two_sided_neutral_signature():
    """Breaks above IB then below IB (both closed beyond) → sides=2, one_tf=None."""
    bars = _ib_bars()
    # break up
    for c in (107.0, 108.5):
        bars.append(_bar(c - 0.5, c + 0.5, c - 1, c))
    # reverse and break down (>=0.3*IB beyond, 2 consecutive)
    for c in (98.0, 96.5):
        bars.append(_bar(c + 1, c + 1.5, c - 0.5, c))
    f = compute_relative_features(bars, IB_HI, IB_LO)
    assert f.sides == 2, f.as_dict()
    assert f.ext_up_hold and f.ext_dn_hold, f.as_dict()
    assert f.one_tf is None, f.as_dict()


def test_marginal_drift_is_not_extension():
    """06-19 fix: a drift just beyond a narrow IB does NOT count as an extension —
    it needs >=0.3*IB beyond AND >=2 CONSECUTIVE bars. Non-consecutive spikes → sides=0."""
    bars = _ib_bars(lo=100.0, hi=109.75, n=12)  # IB ~9.75pt like 06-19
    for c in (113.0, 110.0, 113.0, 110.0):       # spikes >=0.3*IB beyond, but never 2 in a row
        bars.append(_bar(c - 0.3, c + 0.4, c - 0.5, c))
    assert compute_relative_features(bars, 109.75, 100.0).sides == 0
    # contrast: 2 CONSECUTIVE bars >=0.3*IB beyond = a REAL extension → sides=1
    bars2 = _ib_bars(lo=100.0, hi=109.75, n=12)
    for c in (113.0, 113.5):
        bars2.append(_bar(c - 0.3, c + 0.4, c - 0.5, c))
    assert compute_relative_features(bars2, 109.75, 100.0).sides == 1


def test_dead_nontrend_signature():
    """All bars inside a tight IB → sides=0, rib≈1, no clean one_tf."""
    bars = _ib_bars(lo=100.0, hi=103.0, n=24)
    f = compute_relative_features(bars, 103.0, 100.0)
    assert f.sides == 0, f.as_dict()
    assert f.rib is not None and f.rib <= 1.15, f.as_dict()


def test_returned_through_open_down_after_up_drive():
    """Up-drive open that closes back below the open → returned_through_open True."""
    bars = [_bar(100, 101, 100, 100.8)]            # open 100, first close up
    for c in (101.5, 102.0):
        bars.append(_bar(c - 0.5, c + 0.4, c - 0.6, c))
    for c in (99.0, 98.0):                          # reversal back through open
        bars.append(_bar(c + 1, c + 1.2, c - 0.4, c))
    f = compute_relative_features(bars, 102.0, 99.5, open_price=100.0)
    assert f.returned_through_open is True, f.as_dict()


def test_no_bars_is_safe():
    f = compute_relative_features([], None, None)
    assert f.sides == 0 and f.rib is None and f.one_tf is None
