"""Anti-tautological tests for dd_features.detect_double_distribution.

A Double-Distribution = narrow IB + two SUBSTANTIAL distributions separated by a
single-print neck + new value HELD (close at the new extreme). Each `*_is_not_dd`
removes ONE defining behavior and proves the detector flips off → not tautological.
Mirrors the real days: 06-16/17 = DD, 06-10 = wide-IB Variation, 06-09/15 = came-back.
"""
from backend.v9.systems.day_type.dd_features import detect_double_distribution


def _bar(p, v):
    return {"h": p + 0.5, "l": p - 0.5, "c": p, "v": v}


def _dd_session(last_close=180.0):
    """Narrow IB ~200-203, fast break through single prints ~186-198, 2nd distribution ~180-183."""
    bars = [_bar(200 + (i % 4), 300) for i in range(12)]            # narrow IB / distribution 1
    bars += [_bar(p, 20) for p in (198, 196, 194, 192, 190, 188, 186)]  # fast break = single prints (low vol)
    bars += [_bar(180 + (i % 4), 350) for i in range(12)]          # distribution 2 (new value)
    bars += [_bar(last_close, 350)]                                # close
    return bars


IB_W, IB_MED = 3.0, 20.0   # narrow: 3 <= 0.7*20


def test_double_distribution_detected():
    r = detect_double_distribution(_dd_session(), IB_W, IB_MED)
    assert r["detected"] and r["narrow_ib"] and r["bimodal"], r


def test_wide_ib_is_not_dd():
    # 06-10: identical structure but a WIDE IB → one-sided Variation, not DD.
    r = detect_double_distribution(_dd_session(), 18.0, IB_MED)
    assert not r["detected"] and not r["narrow_ib"], r


def test_close_in_middle_is_not_dd():
    # 06-09/06-15: two distributions, but closed back in the MIDDLE → new value NOT held.
    r = detect_double_distribution(_dd_session(last_close=192.0), IB_W, IB_MED)
    assert not r["detected"], r


def test_single_distribution_is_not_dd():
    # One connected distribution (no neck) → not DD even with a narrow IB.
    bars = [_bar(202 if i % 2 else 201, 300) for i in range(26)]
    r = detect_double_distribution(bars, IB_W, IB_MED)
    assert not r["detected"] and not r["bimodal"], r
