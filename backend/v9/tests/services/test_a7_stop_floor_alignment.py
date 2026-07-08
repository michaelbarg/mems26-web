"""A7 stop-floor alignment (2026-07-08 live incident) — the resolver must never
emit a stop the validator always rejects.

Live repro: MEMS_MIN_RISK_POINTS=2 (.env) but compute_stop_v2 floor = 4 ticks
(1.0pt) → ZLR structural stop 1.0pt → validate_fire "degenerate stop" → A7 FAIL
→ 3 ZLR fires dropped on the 07-08 Trend_DD morning.

Anti-tautological: test 1 FAILS on the old code (risk stayed 4 ticks).
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


# 1 — env floor lifts a doomed 1pt structural stop to the validator minimum.
def test_env_floor_lifts_degenerate_stop():
    os.environ["MEMS_MIN_RISK_POINTS"] = "2"
    try:
        # struct 4 ticks (1.0pt) below entry — the exact 07-08 live geometry
        v2 = compute_stop_v2("SHORT", 7506.25, 7507.25, PatternGroup.CONT_TIGHT, 16.0)
        risk_pts = v2.risk_ticks * 0.25
        assert risk_pts >= 2.0, f"stop floor must respect env min, got {risk_pts}pt"
        # and the validator now ACCEPTS what the resolver emits (the alignment)
        resp = validate_fire(FireRequest(
            system_id="T2_WOODIES", direction="SHORT", entry_price=7506.25,
            stop_price=v2.stop_price, t1_price=7506.25 - risk_pts,
            time_stop_minutes=90, confidence=65))
        assert resp.valid, f"validator must accept the resolver's stop: {resp.fail_reason}"
    finally:
        os.environ.pop("MEMS_MIN_RISK_POINTS", None)


# 2 — env unset → behavior unchanged (legacy 4-tick floor).
def test_no_env_keeps_legacy_floor():
    os.environ.pop("MEMS_MIN_RISK_POINTS", None)
    v2 = compute_stop_v2("SHORT", 7506.25, 7507.25, PatternGroup.CONT_TIGHT, 16.0)
    assert v2.risk_ticks == 4, v2.risk_ticks  # legacy DEFAULT_FLOOR_TICKS


# 3 — a real structural stop (wider than the floor) stays UNTOUCHED.
def test_structural_stop_untouched():
    os.environ["MEMS_MIN_RISK_POINTS"] = "2"
    try:
        v2 = compute_stop_v2("SHORT", 7506.25, 7513.50, PatternGroup.CONT_TIGHT, 16.0)
        assert v2.stop_price == 7513.50, v2.stop_price  # structural wins
        assert v2.floor_applied is False
    finally:
        os.environ.pop("MEMS_MIN_RISK_POINTS", None)


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
