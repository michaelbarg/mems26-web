"""Bug #3: S2 detection on completed bars via process_bar (line 928).

Feeds bars through REAL process_bar and intercepts what buffer is passed
to _detect_reactive. Proves line 928 trims to buffer[:-1].

RED-on-revert: reverting line 928 from buffer[:-1] to buffer means
_detect_reactive receives the partial bar as bars[-1] → test FAILS
because the last bar's close differs from the completed bar.
"""
import asyncio
from unittest.mock import patch
from backend.v9.systems.five_min.five_min_system import FiveMinSystem, FiveMinMode


def _make_bars():
    """10 completed bars + 1 partial with distinct close values."""
    base_ts = 1781114400
    bars = []
    for i in range(10):
        bars.append({
            "ts": base_ts + i * 300,
            "o": 7400.0 + i, "h": 7405.0 + i, "l": 7395.0 + i,
            "c": 7402.0 + i,  # completed: c = 7402..7411
            "vol": 5000, "v": 5000, "volume": 5000,
            "open": 7400.0 + i, "high": 7405.0 + i, "low": 7395.0 + i,
            "close": 7402.0 + i,
            "poc_vol": 7400.0, "poc": 7400.0,
        })
    # Partial bar: c=9999 (impossible price, easy to detect)
    partial = {
        "ts": base_ts + 10 * 300,
        "o": 7412.0, "h": 7412.25, "l": 7411.75, "c": 9999.0,
        "vol": 1, "v": 1, "volume": 1,
        "open": 7412.0, "high": 7412.25, "low": 7411.75, "close": 9999.0,
        "poc_vol": 0, "poc": 0,
    }
    return bars, partial


def test_process_bar_passes_trimmed_buffer_to_detect():
    """process_bar passes buffer[:-1] to _detect_reactive (line 928).

    We intercept _detect_reactive to see what buffer it receives.
    With the fix: bars[-1].c should be 7411 (last completed bar).
    Without the fix: bars[-1].c would be 9999 (partial bar).
    """
    fs = FiveMinSystem()
    fs.mode = FiveMinMode.DAY_TYPE_MODE
    fs.current_day_type = "Normal"
    fs._hydrated = True
    # 2026-08-12 flake fix (pre-existing, exposed by the F2 suite run): when the
    # suite runs OUTSIDE RTH and session_gate was already imported by an earlier
    # test, process_bar flips DAY_TYPE→OVERNIGHT via is_after_firing_close() and
    # detection never runs (alone, the lazy import fails → except: pass → green).
    # Pin the gate so the test exercises the RTH path at any wall-clock.
    import backend.v9.gateway.session_gate as _sg
    _orig_iafc = _sg.is_after_firing_close
    _sg.is_after_firing_close = lambda *a, **k: False

    completed_bars, partial_bar = _make_bars()
    loop = asyncio.new_event_loop()

    class Evt:
        def __init__(self, d): self.payload = d

    # Feed completed bars
    for b in completed_bars:
        loop.run_until_complete(fs.process_bar(Evt(b)))

    # Intercept _detect_reactive to capture the buffer it receives
    captured_last_close = [None]
    original = fs._detect_reactive

    def spy(bars_5m):
        captured_last_close[0] = bars_5m[-1]["c"] if bars_5m else None
        return original(bars_5m)

    fs._detect_reactive = spy

    try:
        # Feed partial bar (triggers is_new_bar → detection)
        loop.run_until_complete(fs.process_bar(Evt(partial_bar)))
    finally:
        fs._detect_reactive = original
        _sg.is_after_firing_close = _orig_iafc
        loop.close()

    # With fix (buffer[:-1]): last bar in detection = completed (c=7411)
    # Without fix (buffer): last bar = partial (c=9999)
    assert captured_last_close[0] is not None, \
        "_detect_reactive was not called"
    assert captured_last_close[0] == 7411.0, \
        f"Expected last bar c=7411 (completed), got {captured_last_close[0]} — " \
        f"if 9999, the partial bar leaked into detection (line 928 reverted?)"
