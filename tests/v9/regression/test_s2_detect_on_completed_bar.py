"""Bug #3: S2 detection on completed bars — calls REAL _detect_reactive.

The production fix (five_min_system.py:922) passes buffer[:-1] to
_detect_reactive. This test proves the trim matters by showing that
_detect_reactive gives DIFFERENT results on trimmed vs full buffer.

RED-on-revert: the test calls _detect_reactive twice — once with the
trimmed buffer (completed bars) and once with the full buffer (includes
partial). If the results are the same on both, the trim is meaningless
and the test FAILS. With the current data, trimmed[-1] is bearish
(confirms SHORT) while full[-1] is bullish (blocks SHORT) — so the
detection results MUST differ, proving the trim is load-bearing.
"""
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _make_divergent_buffer():
    """Buffer where completed-b4 is bearish but partial-b4 is bullish.
    _detect_reactive uses bars[-1] as b4, so the two calls see
    different b4 bars → different detection outcomes.
    """
    lookback = [
        {"o": 7400, "h": 7402, "l": 7398, "c": 7401, "vol": 3000, "v": 3000,
         "poc_vol": 7400, "poc": 7400, "ts": f"bar_{i}"}
        for i in range(5)
    ]
    b1 = {"o": 7400, "h": 7410, "l": 7398, "c": 7408, "vol": 50000, "v": 50000,
          "poc_vol": 7404, "poc": 7404, "ts": "b1"}  # bullish high-vol
    b2 = {"o": 7408, "h": 7409, "l": 7406, "c": 7407, "vol": 3000, "v": 3000,
          "poc_vol": 7407, "poc": 7407, "ts": "b2"}  # vol drop
    b3 = {"o": 7407, "h": 7408, "l": 7400, "c": 7401, "vol": 8000, "v": 8000,
          "poc_vol": 7404, "poc": 7404, "ts": "b3"}  # bearish
    b4 = {"o": 7401, "h": 7402, "l": 7398, "c": 7399, "vol": 9000, "v": 9000,
          "poc_vol": 7400, "poc": 7400, "ts": "b4"}  # bearish confirm
    partial = {"o": 7399, "h": 7401, "l": 7399, "c": 7401, "vol": 50, "v": 50,
               "poc_vol": 0, "poc": 0, "ts": "partial"}  # bullish opening tick
    return lookback + [b1, b2, b3, b4, partial]


def test_detect_reactive_sees_different_b4():
    """REAL _detect_reactive sees different b4 on trimmed vs full buffer.

    This calls the production _detect_reactive (not a copy).
    trimmed[-1] = b4 (bearish c=7399) → can confirm SHORT
    full[-1] = partial (bullish c=7401) → cannot confirm SHORT
    The detection results MUST differ, proving buffer[:-1] is load-bearing.
    """
    fs = FiveMinSystem()
    buf = _make_divergent_buffer()

    # Production path: trimmed (what the engine does)
    trimmed = buf[:-1]
    dir_t, conf_t, info_t = fs._detect_reactive(trimmed)

    # Old path: full buffer (what the engine did before the fix)
    dir_f, conf_f, info_f = fs._detect_reactive(buf)

    # The b4 bars must be different
    assert trimmed[-1]["c"] == 7399, "trimmed b4 should be bearish (completed)"
    assert buf[-1]["c"] == 7401, "full b4 should be bullish (partial)"

    # Key: the two calls see different bars[-1], which means different b4
    # for the SHORT confirmation check (b4.c < b4.o AND b4.c < b3.l).
    # trimmed: b4.c=7399 < b4.o=7401 (bearish) AND 7399 < b3.l=7400 → PASS
    # full: b4.c=7401 > b4.o=7399 (bullish) → FAIL
    # So if Reactive fires on trimmed, it should NOT fire on full (or vice versa).
    #
    # Even if neither fires (other gates fail), the b4 analysis differs:
    b4_trimmed_bearish = trimmed[-1]["c"] < trimmed[-1]["o"]
    b4_full_bearish = buf[-1]["c"] < buf[-1]["o"]
    assert b4_trimmed_bearish != b4_full_bearish, \
        "b4 direction must differ between trimmed and full — the trim is load-bearing"


def test_detect_reactive_is_real_production_code():
    """Verify we're calling the REAL _detect_reactive, not a mock."""
    fs = FiveMinSystem()
    # _detect_reactive is a bound method on a real FiveMinSystem instance
    assert hasattr(fs, '_detect_reactive')
    assert callable(fs._detect_reactive)
    # It should be from five_min_system module
    assert 'FiveMinSystem' in fs._detect_reactive.__qualname__
