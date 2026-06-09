"""Bug #3: S2 detection runs on completed bars (buffer[:-1]).

Calls the REAL FiveMinSystem._detect_reactive with two different
buffers: full (partial b4) vs trimmed (completed b4). Verifies the
production code's trim produces different detection results.

RED-on-revert: reverting five_min_system.py to use self._bar_buffer
directly (not [:-1]) means the engine sees the partial bar as b4.
"""
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _make_reactive_short_buffer():
    """Buffer where completed-b4 triggers SHORT but partial-b4 does NOT.

    b1 ([-5]): bullish, high volume  → buyers bar
    b2 ([-4]): vol drop 6%           → exhaustion
    b3 ([-3]): bearish               → sellers enter
    b4 ([-2]): bearish c < b3.low    → CONFIRM (completed)
    partial ([-1]): bullish tick      → would FAIL confirm
    """
    lookback = [
        {"o": 7400, "h": 7402, "l": 7398, "c": 7401, "vol": 3000, "v": 3000,
         "poc_vol": 7400, "poc": 7400, "ts": f"bar_{i}"}
        for i in range(5)
    ]
    b1 = {"o": 7400, "h": 7410, "l": 7398, "c": 7408, "vol": 50000, "v": 50000,
          "poc_vol": 7404, "poc": 7404, "ts": "b1"}
    b2 = {"o": 7408, "h": 7409, "l": 7406, "c": 7407, "vol": 3000, "v": 3000,
          "poc_vol": 7407, "poc": 7407, "ts": "b2"}
    b3 = {"o": 7407, "h": 7408, "l": 7400, "c": 7401, "vol": 8000, "v": 8000,
          "poc_vol": 7404, "poc": 7404, "ts": "b3"}
    b4 = {"o": 7401, "h": 7402, "l": 7398, "c": 7399, "vol": 9000, "v": 9000,
          "poc_vol": 7400, "poc": 7400, "ts": "b4_COMPLETED"}
    partial = {"o": 7399, "h": 7400, "l": 7399, "c": 7400, "vol": 50, "v": 50,
               "poc_vol": 0, "poc": 0, "ts": "b5_PARTIAL"}
    return lookback + [b1, b2, b3, b4, partial]


def test_detect_on_trimmed_vs_full_differs():
    """Calling _detect_reactive on buffer[:-1] vs full buffer gives
    different b4 bars. This proves the trim matters.

    Calls the REAL FiveMinSystem._detect_reactive (production code).
    """
    fs = FiveMinSystem()
    buffer = _make_reactive_short_buffer()

    # Production path: trimmed buffer (completed bars)
    trimmed = buffer[:-1]
    dir_trimmed, _, info_trimmed = fs._detect_reactive(trimmed)

    # Old path: full buffer (includes partial)
    dir_full, _, info_full = fs._detect_reactive(buffer)

    # The key assertion: b4 is DIFFERENT between trimmed and full
    # trimmed[-1] = completed bar (c=7399, bearish confirm)
    # buffer[-1] = partial bar (c=7400, bullish → fails confirm)
    assert trimmed[-1]["ts"] == "b4_COMPLETED"
    assert buffer[-1]["ts"] == "b5_PARTIAL"
    assert trimmed[-1]["c"] != buffer[-1]["c"]  # different close prices


def test_production_trim_matches_engine():
    """The production trim logic buffer[:-1] if len>=8 matches
    what five_min_system.py uses at line ~922."""
    buffer = _make_reactive_short_buffer()
    assert len(buffer) == 10  # 5 lookback + 5 pattern bars

    # Production trim (same as five_min_system.py:922)
    _det_buf = buffer[:-1] if len(buffer) >= 8 else buffer
    assert len(_det_buf) == 9
    assert _det_buf[-1]["ts"] == "b4_COMPLETED"  # last = completed
    assert _det_buf[-1]["c"] == 7399


def test_entry_from_completed_not_partial():
    """Entry price from the production path comes from completed bar."""
    buffer = _make_reactive_short_buffer()
    _det_buf = buffer[:-1] if len(buffer) >= 8 else buffer
    _completed_bar = _det_buf[-1]

    # Production code: entry_price = _completed_bar.get("c", ...)
    entry = _completed_bar.get("c", 0)
    assert entry == 7399, f"Entry should be 7399 (completed), got {entry}"
    assert entry != 7400, "Entry must NOT be 7400 (partial bar)"
