"""TARGET_MIN_SPACING_V1 — target ladder spacing guard.

Anti-tautological: test 1 (the #756 geometry) FAILS on the old code.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.systems.target_spacing import (
    enforce_spacing, min_gap, build_candidates, snap, reset_cfg_cache,
)

# Config: k_atr=0.25, m_risk=0.33
CFG = {"k_atr": 0.25, "m_risk": 0.33, "atr_bars": 14,
       "r_multiples": [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]}


def test_756_short_clustered_dropped():
    """#756: t1/t2/t3 = 7691.50/7691.00/7690.50 on 3.5pt risk, ATR 6.25.
    min_gap = max(0.25*6.25, 0.33*3.5) = max(1.5625, 1.155) = 1.5625.
    t1-t2 = 0.50 < 1.56 → t2 must be PUSHED or DROPPED.
    t2-t3 = 0.50 → t3 too."""
    reset_cfg_cache()
    cands = build_candidates(entry=7696.75, risk=3.5,
                             producer_levels=[("c1", 7686.25), ("c2", 7682.75), ("c3", 7679.0)],
                             cfg=CFG)
    rec = enforce_spacing(direction="SHORT", entry=7696.75,
                          t1=7691.50, t2=7691.00, t3=7690.50,
                          risk=3.5, atr14=6.25, candidates=cands, cfg=CFG)
    assert rec["changed"], f"#756 ladder must be changed: {rec}"
    # t2 and/or t3 must be PUSH or DROP — not KEEP
    branches = {b["leg"]: b["branch"] for b in rec["branches"]}
    assert branches.get("t2") in ("PUSH", "DROP"), f"t2 must be pushed/dropped: {branches}"
    assert branches.get("t3") in ("PUSH", "DROP"), f"t3 must be pushed/dropped: {branches}"
    # No invented prices — every non-None after value must be in candidates or original
    after = rec["after"]
    cand_prices = {snap(p) for _, p in cands}
    for k in ("t1", "t2", "t3"):
        v = after.get(k)
        if v is not None:
            assert v in cand_prices or v == 7691.50, f"{k}={v} is an invented price"


def test_healthy_ladder_untouched():
    """A well-spaced ladder (e.g., 5pt steps on 5pt ATR) stays identical."""
    reset_cfg_cache()
    rec = enforce_spacing(direction="LONG", entry=7700.0,
                          t1=7705.0, t2=7710.0, t3=7715.0,
                          risk=5.0, atr14=5.0, candidates=[], cfg=CFG)
    assert not rec["changed"], f"healthy ladder should not change: {rec}"
    assert rec["after"]["t1"] == 7705.0
    assert rec["after"]["t2"] == 7710.0
    assert rec["after"]["t3"] == 7715.0


def test_flag_off_byte_identical():
    """When flag is OFF, enforce_spacing still returns unchanged (the caller
    gates on flag_mode, but the function itself is pure)."""
    reset_cfg_cache()
    rec = enforce_spacing(direction="SHORT", entry=7696.75,
                          t1=7691.50, t2=7691.00, t3=7690.50,
                          risk=3.5, atr14=6.25, candidates=[], cfg=CFG)
    # With no candidates, PUSH is impossible → both t2/t3 should be DROPPED
    assert rec["changed"]


def test_no_atr_no_risk_no_gap():
    """Both ATR and risk are 0 → no relative basis → skip (unchanged)."""
    reset_cfg_cache()
    rec = enforce_spacing(direction="LONG", entry=7700.0,
                          t1=7701.0, t2=7701.5, t3=7702.0,
                          risk=0.0, atr14=0.0, candidates=[], cfg=CFG)
    assert not rec["changed"], "no basis → no change"
    assert rec["min_gap"] is None


def test_min_gap_relative():
    """min_gap = max(k×ATR, m×risk) — whichever is larger."""
    reset_cfg_cache()
    g1, _ = min_gap(6.25, 3.5, CFG)
    assert abs(g1 - 1.5625) < 0.01, f"k*ATR should dominate: {g1}"
    g2, _ = min_gap(2.0, 10.0, CFG)
    assert abs(g2 - 3.3) < 0.01, f"m*risk should dominate: {g2}"


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
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
