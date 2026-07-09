"""SIZE_CAP_CUT_V1 (Michael ruling 2026-07-09) — judgment beats fixed size:
a stop wider than the group ATR-cap cuts contracts even under FIXED_CONTRACTS_3.

Closes S6-BAND-0708: 12.5pt (≈2×ATR) stops carried 3 contracts ($187/trade);
D-092's "cap becomes a size gate" was never wired.

Anti-tautological: test 1 FAILS on the old code (kept 3).
Runnable standalone: python3 test_size_cap_cut.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.config_loader import load_stop_anchors  # noqa: E402
from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing  # noqa: E402

CFG = load_stop_anchors()


def _size(entry, stop, cap_pts, **env):
    for k in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "SIZE_CAP_CUT_V1"):
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        r = compute_v2_sizing(
            entry_price=entry, stop_price=stop, direction="LONG",
            pattern_key="ZLR", day_type="Trend_Normal", confidence_tier="medium",
            day_has_direction=True, trade_with_trend=True,
            value_area_full_traverse=None, cfg=CFG, auth_matrix=None,
            cap_risk_points=cap_pts)
        return r.contracts if r else None
    finally:
        for k in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "SIZE_CAP_CUT_V1"):
            os.environ.pop(k, None)


# 1 — the 07-08 geometry: 12.5pt stop, cap 9.45pt (1.5×ATR 6.3) → cut 3→2.
def test_cut_to_two_above_cap():
    c = _size(7500.0, 7487.5, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1")
    assert c == 2, f"12.5pt > cap 9.45 must cut 3→2, got {c}"  # old code: 3


# 2 — beyond 1.5×cap → 1 contract.
def test_cut_to_one_far_beyond_cap():
    c = _size(7500.0, 7485.0, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1")
    assert c == 1, c  # 15pt > 1.5×9.45=14.2


# 3 — inside the cap: fixed 3 untouched.
def test_inside_cap_keeps_three():
    c = _size(7500.0, 7493.0, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1")
    assert c == 3, c


# 4 — flag OFF: behavior unchanged (3 even on a wide stop).
def test_flag_off_unchanged():
    c = _size(7500.0, 7487.5, 9.45, FIXED_CONTRACTS_3="1")
    assert c == 3, c


# 5 — cap unknown (None): honest missing → no cut.
def test_missing_cap_no_cut():
    c = _size(7500.0, 7487.5, None, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1")
    assert c == 3, c


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
    print(f"\ntest_size_cap_cut.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
