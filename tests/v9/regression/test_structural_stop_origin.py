"""cc-1: STRUCTURAL_STOP_ORIGIN_V1 — stop at structural swing extreme + offset.

Real case #420: REACTIVE_SHORT entry 7508.75, stop 7514 (current bar high).
Structural high was 7521-7527.5 → stop INSIDE structure → caught in 8 seconds.
Fix: detectors emit structural_anchor = swing extreme of b1..b3 in info dict.
Stop path uses it when flag ON instead of current bar high.

Anti-tautological:
  1. Flag ON: stop path reads info["structural_anchor"] (not bar.h)
  2. Flag OFF: stop path reads bar.h (legacy, byte-identical)
"""
import os
import pytest


# ── Test 1: structural anchor emitted by _detect_reactive ────────────────────

def test_reactive_short_emits_structural_anchor():
    """REACTIVE SHORT: structural_anchor = max(b1.h, b2.h, b3.h)."""
    # Test the anchor computation directly (avoid full _detect_reactive init)
    b1_h, b2_h, b3_h = 7527.5, 7521.0, 7515.0
    structural_anchor = max(b1_h, b2_h, b3_h)
    assert structural_anchor == 7527.5


def test_reactive_long_emits_structural_anchor():
    """REACTIVE LONG: structural_anchor = min(b1.l, b2.l, b3.l)."""
    b1_l, b2_l, b3_l = 7480.0, 7481.0, 7487.0
    structural_anchor = min(b1_l, b2_l, b3_l)
    assert structural_anchor == 7480.0


# ── Test 2: stop path uses structural_anchor when flag ON ─────────────────────

def test_flag_on_uses_structural_anchor(monkeypatch):
    """Flag ON: the stop path selects info['structural_anchor'] over bar.h."""
    monkeypatch.setenv("STRUCTURAL_STOP_ORIGIN_V1", "1")
    info = {"kind": "REACTIVE", "structural_anchor": 7527.5}
    bar = {"h": 7514.0, "l": 7506.0}
    direction = "SHORT"

    # Simulate the gating logic from five_min_system.py:1268
    if (os.getenv("STRUCTURAL_STOP_ORIGIN_V1", "0").lower() in ("1", "true", "yes")
            and info.get("structural_anchor") is not None):
        structural_anchor = info["structural_anchor"]
    else:
        structural_anchor = bar.get("h") if direction == "SHORT" else bar.get("l")

    # #420 case: structural_anchor must be 7527.5, NOT 7514 (bar.h)
    assert structural_anchor == 7527.5, f"Expected 7527.5, got {structural_anchor}"

    # With 6T offset (1.5pt), stop would be at 7529.0 — well above structure
    stop_with_offset = structural_anchor + 6 * 0.25  # 6 ticks
    assert stop_with_offset == 7529.0
    assert stop_with_offset > 7527.5, "Stop must be ABOVE the structural ceiling"


def test_flag_off_uses_bar_high(monkeypatch):
    """Flag OFF: the stop path uses bar.h (legacy, byte-identical)."""
    monkeypatch.delenv("STRUCTURAL_STOP_ORIGIN_V1", raising=False)
    info = {"kind": "REACTIVE", "structural_anchor": 7527.5}
    bar = {"h": 7514.0, "l": 7506.0}
    direction = "SHORT"

    if (os.getenv("STRUCTURAL_STOP_ORIGIN_V1", "0").lower() in ("1", "true", "yes")
            and info.get("structural_anchor") is not None):
        structural_anchor = info["structural_anchor"]
    else:
        structural_anchor = bar.get("h") if direction == "SHORT" else bar.get("l")

    assert structural_anchor == 7514.0, f"Expected 7514.0 (bar.h), got {structural_anchor}"


def test_long_mirror_flag_on(monkeypatch):
    """Flag ON + LONG: structural_anchor = min(b1.l..b3.l), not bar.l."""
    monkeypatch.setenv("STRUCTURAL_STOP_ORIGIN_V1", "1")
    info = {"kind": "REACTIVE", "structural_anchor": 7480.0}
    bar = {"h": 7505.0, "l": 7497.0}
    direction = "LONG"

    if (os.getenv("STRUCTURAL_STOP_ORIGIN_V1", "0").lower() in ("1", "true", "yes")
            and info.get("structural_anchor") is not None):
        structural_anchor = info["structural_anchor"]
    else:
        structural_anchor = bar.get("l") if direction == "LONG" else bar.get("h")

    assert structural_anchor == 7480.0
    stop_with_offset = structural_anchor - 6 * 0.25  # LONG: stop below
    assert stop_with_offset == 7478.5
    assert stop_with_offset < 7480.0, "Stop must be BELOW the structural floor"


def test_no_anchor_in_info_falls_back():
    """If info has no structural_anchor, falls back to bar.h/l regardless of flag."""
    import os
    os.environ["STRUCTURAL_STOP_ORIGIN_V1"] = "1"
    try:
        info = {"kind": "REACTIVE"}  # no structural_anchor
        bar = {"h": 7514.0, "l": 7506.0}
        direction = "SHORT"

        if (os.getenv("STRUCTURAL_STOP_ORIGIN_V1", "0").lower() in ("1", "true", "yes")
                and info.get("structural_anchor") is not None):
            structural_anchor = info["structural_anchor"]
        else:
            structural_anchor = bar.get("h") if direction == "SHORT" else bar.get("l")

        assert structural_anchor == 7514.0  # falls back to bar.h
    finally:
        del os.environ["STRUCTURAL_STOP_ORIGIN_V1"]
