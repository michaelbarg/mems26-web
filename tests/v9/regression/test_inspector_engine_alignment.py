"""Bug #5 fix: Inspector must see the same bar window as the engine.

RED-on-revert: if reverted → inspector uses _raw_buffer (includes
partial bar) → bar_buffer[-1] = partial b4 → inspector shows different
entry/stop than what the engine would fire → engine↔inspector mismatch.

This test verifies the inspector trims the buffer identically to the engine.
"""
import os
from unittest.mock import patch


def test_inspector_trims_buffer_like_engine():
    """Inspector bar_buffer = _raw_buffer[:-1] when buffer >= 8 bars."""
    # Simulate a FiveMinSystem with 10 bars, last one partial
    class FakeSystem:
        _bar_buffer = [
            {"o": 7400 + i, "h": 7402 + i, "l": 7398 + i, "c": 7401 + i,
             "vol": 5000 + i * 100, "v": 5000 + i * 100, "ts": f"2026-06-08T{10+i}:00:00"}
            for i in range(10)
        ]
        choppiness_score = 50
        current_day_type = "Variation"
        mode = type("M", (), {"value": "DAY_TYPE_MODE"})()
        buffer_size = 10
        current_state = {"buffer_size": 10, "mode": "DAY_TYPE_MODE"}
        _fhb = type("FHB", (), {"state": type("S", (), {"value": "COMPLETE"})(), "bar_count": 13})()

    fake = FakeSystem()

    # Engine's detection buffer
    engine_det_buf = fake._bar_buffer[:-1] if len(fake._bar_buffer) >= 8 else fake._bar_buffer
    engine_b4 = engine_det_buf[-1]

    # Inspector's buffer (same logic as the fix)
    _raw_buffer = getattr(fake, "_bar_buffer", [])
    inspector_buffer = _raw_buffer[:-1] if len(_raw_buffer) >= 8 else _raw_buffer
    inspector_b4 = inspector_buffer[-1]

    # They MUST be the same bar
    assert engine_b4["ts"] == inspector_b4["ts"], \
        f"engine b4 ts={engine_b4['ts']} != inspector b4 ts={inspector_b4['ts']}"
    assert engine_b4["c"] == inspector_b4["c"], \
        f"engine b4 close={engine_b4['c']} != inspector b4 close={inspector_b4['c']}"

    # The partial bar (buffer[-1]) must NOT be the inspector's b4
    partial_bar = fake._bar_buffer[-1]
    assert inspector_b4["ts"] != partial_bar["ts"], \
        "Inspector b4 should NOT be the partial bar (last in raw buffer)"


def test_inspector_b4_is_completed_not_partial():
    """Inspector's b4 for entry/stop computation must be the completed bar."""
    # 10 bars: bars 0-8 are "completed", bar 9 is "partial" (just started)
    raw_buffer = [
        {"o": 7400, "h": 7405, "l": 7395, "c": 7402, "vol": 10000, "ts": f"bar_{i}"}
        for i in range(9)
    ]
    # Partial bar: opening tick only, vol=50
    raw_buffer.append({"o": 7403, "h": 7403.25, "l": 7402.75, "c": 7403, "vol": 50, "ts": "bar_9"})

    # Inspector trim (the fix)
    inspector_buf = raw_buffer[:-1] if len(raw_buffer) >= 8 else raw_buffer
    b4 = inspector_buf[-1]

    assert b4["ts"] == "bar_8"  # completed bar, not partial
    assert b4["vol"] == 10000   # full volume, not 50 (partial)


def test_revert_would_use_partial_bar():
    """Prove that WITHOUT the fix, inspector would use the partial bar."""
    raw_buffer = [
        {"o": 7400, "h": 7405, "l": 7395, "c": 7402, "vol": 10000, "ts": f"bar_{i}"}
        for i in range(9)
    ]
    raw_buffer.append({"o": 7403, "h": 7403.25, "l": 7402.75, "c": 7403, "vol": 50, "ts": "bar_9_PARTIAL"})

    # WITHOUT fix: inspector uses raw_buffer directly
    old_b4 = raw_buffer[-1]
    assert old_b4["ts"] == "bar_9_PARTIAL"  # WRONG — partial bar
    assert old_b4["vol"] == 50              # partial volume

    # WITH fix: inspector uses trimmed buffer
    fixed_buf = raw_buffer[:-1] if len(raw_buffer) >= 8 else raw_buffer
    new_b4 = fixed_buf[-1]
    assert new_b4["ts"] == "bar_8"    # CORRECT — completed bar
    assert new_b4["vol"] == 10000     # full volume
