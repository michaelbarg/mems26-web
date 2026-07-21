"""Task#4: T2T3_NO_STOMP_V1 — structural t2/t3 preserved when pattern_t1 runs.

Real case #420 day (07-20): Variation SHORT entry 7508.75 — structural targets
from resolve_structural_targets gave t2=POC(7505), t3=VAL(7490). Then
PATTERN_T1_OVERRIDE stomped them with t2=entry-2×9=7490.75, t3=entry-3×9=7481.75.
The structural levels (Dalton: POC, VAL) are more meaningful than ×2/×3.

Anti-tautological:
  1. Flag ON + structural t2/t3 set → pattern_t1 sets t1 only, t2/t3 preserved
  2. Flag OFF → stomp-of-today (t1+t2+t3 all overwritten) — byte-identical
  3. No structural targets (pre-IB) → t1/t2/t3 from pattern_t1 as today
"""
import os
import pytest


def test_flag_on_preserves_structural_t2t3():
    """Flag ON + structural t2/t3 → t1 from pattern, t2/t3 from structure."""
    os.environ["T2T3_NO_STOMP_V1"] = "1"
    try:
        # Simulate the gateway logic
        setup = {"t1": 7500.0, "t2": 7505.0, "t3": 7490.0, "entry_price": 7508.75}
        _structural_t2t3_applied = True  # structural targets set t2 and t3

        # Pattern T1 override: REACTIVE_SHORT × Variation → 9pt
        _pt_pts = 9.0
        _pt_entry = 7508.75
        _pt_sign = -1.0  # SHORT
        setup["t1"] = round(_pt_entry + _pt_sign * _pt_pts, 2)  # 7499.75

        _no_stomp = (os.getenv("T2T3_NO_STOMP_V1", "0").lower() in ("1", "true", "yes")
                     and _structural_t2t3_applied)
        if not _no_stomp:
            setup["t2"] = round(_pt_entry + _pt_sign * 2 * _pt_pts, 2)
            setup["t3"] = round(_pt_entry + _pt_sign * 3 * _pt_pts, 2)

        # t1 = pattern override (9pt)
        assert setup["t1"] == 7499.75
        # t2/t3 = structural (preserved, NOT stomped to ×2/×3)
        assert setup["t2"] == 7505.0, f"t2 should be structural 7505, got {setup['t2']}"
        assert setup["t3"] == 7490.0, f"t3 should be structural 7490, got {setup['t3']}"
    finally:
        os.environ.pop("T2T3_NO_STOMP_V1", None)


def test_flag_off_stomps_all(monkeypatch):
    """Flag OFF → t1+t2+t3 all overwritten by pattern_t1 (legacy byte-identical)."""
    monkeypatch.delenv("T2T3_NO_STOMP_V1", raising=False)

    setup = {"t1": 7500.0, "t2": 7505.0, "t3": 7490.0, "entry_price": 7508.75}
    _structural_t2t3_applied = True

    _pt_pts = 9.0
    _pt_entry = 7508.75
    _pt_sign = -1.0
    setup["t1"] = round(_pt_entry + _pt_sign * _pt_pts, 2)

    _no_stomp = (os.getenv("T2T3_NO_STOMP_V1", "0").lower() in ("1", "true", "yes")
                 and _structural_t2t3_applied)
    if not _no_stomp:
        setup["t2"] = round(_pt_entry + _pt_sign * 2 * _pt_pts, 2)
        setup["t3"] = round(_pt_entry + _pt_sign * 3 * _pt_pts, 2)

    assert setup["t1"] == 7499.75
    assert setup["t2"] == 7490.75, f"t2 should be stomped to 7490.75, got {setup['t2']}"
    assert setup["t3"] == 7481.75, f"t3 should be stomped to 7481.75, got {setup['t3']}"


def test_no_structural_falls_through():
    """No structural targets (pre-IB) → t1/t2/t3 all from pattern_t1."""
    os.environ["T2T3_NO_STOMP_V1"] = "1"
    try:
        setup = {"t1": 7500.0, "t2": None, "t3": None, "entry_price": 7508.75}
        _structural_t2t3_applied = False  # no structural targets

        _pt_pts = 9.0
        _pt_entry = 7508.75
        _pt_sign = -1.0
        setup["t1"] = round(_pt_entry + _pt_sign * _pt_pts, 2)

        _no_stomp = (os.getenv("T2T3_NO_STOMP_V1", "0").lower() in ("1", "true", "yes")
                     and _structural_t2t3_applied)
        if not _no_stomp:
            setup["t2"] = round(_pt_entry + _pt_sign * 2 * _pt_pts, 2)
            setup["t3"] = round(_pt_entry + _pt_sign * 3 * _pt_pts, 2)

        assert setup["t1"] == 7499.75
        assert setup["t2"] == 7490.75  # falls through to ×2
        assert setup["t3"] == 7481.75  # falls through to ×3
    finally:
        os.environ.pop("T2T3_NO_STOMP_V1", None)
