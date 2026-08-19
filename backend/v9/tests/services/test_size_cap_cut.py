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
    for k in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "SIZE_CAP_CUT_V1",
              "SIZE_CAP_FLOOR_CONTRACTS"):
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
        for k in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "SIZE_CAP_CUT_V1",
                  "SIZE_CAP_FLOOR_CONTRACTS"):
            os.environ.pop(k, None)


# 1 — the 07-08 geometry: 12.5pt stop, cap 9.45pt (1.5×ATR 6.3) → cut 3→2.
def test_cut_to_two_above_cap():
    c = _size(7500.0, 7487.5, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1")
    assert c == 2, f"12.5pt > cap 9.45 must cut 3→2, got {c}"  # old code: 3


# 2 — beyond 1.5×cap: was 1 before floor, now 2 (floor default).
# Michael 2026-08-19: "במקום 1 עם אותה תקרה תעשה 2 או 3 חוזים".
def test_cut_to_one_far_beyond_cap():
    c = _size(7500.0, 7485.0, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1")
    assert c == 2, f"floor=2 (default) prevents cut to 1, got {c}"  # 15pt > 1.5×9.45=14.2


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


# ── SIZE_CAP_FLOOR_CONTRACTS (Michael 2026-08-19) ──

# 6 — 15pt > 1.5×9.45 used to cut to 1; floor=2 lifts it to 2.
def test_floor_lifts_one_to_two():
    c = _size(7500.0, 7485.0, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1",
              SIZE_CAP_FLOOR_CONTRACTS="2")
    assert c == 2, f"floor=2 must lift 1→2, got {c}"


# 7 — floor=3: far-beyond-cap → 3 instead of 1.
def test_floor_three():
    c = _size(7500.0, 7485.0, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1",
              SIZE_CAP_FLOOR_CONTRACTS="3")
    assert c == 3, f"floor=3 must keep 3, got {c}"


# 8 — floor does NOT inflate below-floor original size.
#     If requested is 2 (via FIXED_CONTRACTS_2), floor=2 must NOT push to 3.
def test_floor_does_not_inflate():
    c = _size(7500.0, 7485.0, 9.45, FIXED_CONTRACTS_2="1", SIZE_CAP_CUT_V1="1",
              SIZE_CAP_FLOOR_CONTRACTS="3")
    # Original request is 2; floor=3 would try to lift, but min(cut, contracts)
    # prevents inflation. The cut-with-floor = max(1, 3) = 3, then
    # min(3, 2) = 2. Original 2 contracts, untouched.
    assert c == 2, f"floor must not inflate 2→3, got {c}"


# 9 — inside-cap: floor is irrelevant, contracts stay at requested.
def test_floor_irrelevant_inside_cap():
    c = _size(7500.0, 7493.0, 9.45, FIXED_CONTRACTS_3="1", SIZE_CAP_CUT_V1="1",
              SIZE_CAP_FLOOR_CONTRACTS="2")
    assert c == 3, f"inside cap, floor is a no-op, got {c}"


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
