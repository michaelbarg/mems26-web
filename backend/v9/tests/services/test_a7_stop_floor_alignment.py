"""Stop band alignment (Michael 07-02 ratified · re-ruled live 2026-07-08).

The stop is sized by the average candle (ATR) and placed at structure:
band [0.5×ATR .. group-cap×ATR]. Structure inside the band wins untouched;
tighter-than-band anchors (forming-bar artifacts) are pushed to the band floor.
Live incident 07-08: 1pt stops on a 10-15pt-candle day → A7 killed 3 ZLR fires.

Anti-tautological: tests 1+2 FAIL on the old code (fixed 4-tick floor).
Runnable standalone: python3 test_a7_stop_floor_alignment.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.systems.woodies.atr_stop import PatternGroup, compute_stop_v2  # noqa: E402
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire  # noqa: E402


# 1 — big-candle day (ATR=48 ticks=12pt): degenerate 1pt anchor → 0.5×ATR = 6pt stop.
def test_band_floor_scales_with_candle_size():
    os.environ.pop("MEMS_MIN_RISK_POINTS", None)
    v2 = compute_stop_v2("SHORT", 7506.25, 7507.25, PatternGroup.CONT_TIGHT, 48.0)
    risk_pts = v2.risk_ticks * 0.25
    assert risk_pts == 6.0, f"0.5×ATR(12pt)=6pt expected, got {risk_pts}pt"  # old code: 1.0pt
    assert v2.floor_applied is True


# 2 — the resolver's stop always passes the validator (the A7 alignment).
def test_resolver_output_passes_validator():
    os.environ["MEMS_MIN_RISK_POINTS"] = "2"
    try:
        # the exact 07-08 live geometry: struct 1pt, ATR 16 ticks (4pt candles)
        v2 = compute_stop_v2("SHORT", 7506.25, 7507.25, PatternGroup.CONT_TIGHT, 16.0)
        risk_pts = v2.risk_ticks * 0.25
        assert risk_pts >= 2.0, f"got {risk_pts}pt"  # band 0.5×4pt=2pt == env min
        resp = validate_fire(FireRequest(
            system_id="T2_WOODIES", direction="SHORT", entry_price=7506.25,
            stop_price=v2.stop_price, t1_price=7506.25 - risk_pts,
            time_stop_minutes=90, confidence=65))
        assert resp.valid, f"validator must accept the resolver's stop: {resp.fail_reason}"
    finally:
        os.environ.pop("MEMS_MIN_RISK_POINTS", None)


# 3 — a structural stop INSIDE the band stays untouched (structure wins).
def test_structural_stop_inside_band_untouched():
    os.environ.pop("MEMS_MIN_RISK_POINTS", None)
    # ATR 16 ticks → band floor 8 ticks (2pt); struct at 3pt (12 ticks) — inside band
    v2 = compute_stop_v2("SHORT", 7506.25, 7509.25, PatternGroup.CONT_TIGHT, 16.0)
    assert v2.stop_price == 7509.25, v2.stop_price
    assert v2.floor_applied is False


# 4 — wide structural stop beyond the cap: kept, cap reported to the size gate.
def test_wide_struct_reports_cap():
    os.environ.pop("MEMS_MIN_RISK_POINTS", None)
    v2 = compute_stop_v2("SHORT", 7506.25, 7513.50, PatternGroup.CONT_TIGHT, 16.0)
    assert v2.stop_price == 7513.50  # structural wins (29 ticks)
    assert v2.cap_exceeded is True   # 29 > 1.0×16 → size gate handles


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok - {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL - {t.__name__}: {e!r}")
    print(f"\ntest_a7_stop_floor_alignment.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
