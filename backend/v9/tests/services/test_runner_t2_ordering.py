"""RUNNER_T2 ordering — with band-floored risk the S4 ladder is monotonic
(2026-07-09; closes board item S4-RUNNER-T2-SIGN).

Live 07-08 17:30: ZLR SHORT with DEGENERATE risk=1.0pt produced t2 (2R=2pt)
closer than t1 (ladder floor 3pt) → I-59 sanitized t2 away → the short lost its
runner target. Root = the degenerate risk, not a sign error; the 0.5×ATR band
floor (0107a12) makes it structurally impossible. This test pins that:
with any band-floored risk, SHORT: entry > t1 > t2 and LONG: entry < t1 < t2.
Runnable standalone: python3 test_runner_t2_ordering.py
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.systems.stop_anchors import resolver as SA  # noqa: E402
from backend.v9.config_loader import load_stop_anchors  # noqa: E402

T1_FLOOR = 3.0  # t1_floor_points (stop_anchors.yaml default)


def _ladder_cfg():
    cfg = load_stop_anchors()
    assert cfg, "stop_anchors.yaml must load"
    return cfg


# For every ATR regime, band-floored risk keeps the ladder monotonic per side.
def test_ladder_monotonic_across_atr_regimes():
    cfg = _ladder_cfg()
    ladder = cfg.get("t1_ladder_continuation_v2", cfg["t1_ladder_continuation"])
    for atr_ticks in (8, 16, 32, 48, 64):  # 2pt .. 16pt average candles
        risk = max(2.0, math.ceil(0.5 * atr_ticks) * 0.25)  # band floor ∨ env min
        for direction, sign in (("SHORT", -1), ("LONG", 1)):
            entry = 7500.0
            t1 = SA.t1_price(entry, entry - sign * risk, direction,
                             t1_ladder_cont=ladder, reversal=False,
                             reversal_mult=0.8, t1_floor_points=T1_FLOOR,
                             ladder_shift=0)
            t2 = entry + sign * 2.0 * risk  # RUNNER_T2 R-multiple path
            t1_dist = abs(t1 - entry)
            t2_dist = abs(t2 - entry)
            assert t2_dist > t1_dist, (
                f"atr={atr_ticks}t risk={risk}pt {direction}: "
                f"t2 ({t2_dist:.2f}) must be beyond t1 ({t1_dist:.2f})")
            if direction == "SHORT":
                assert entry > t1 > t2
            else:
                assert entry < t1 < t2


# The 07-08 degenerate geometry (risk=1pt) DOES break ordering — proving the
# band floor is what protects us (this documents the incident).
def test_degenerate_risk_breaks_ordering_documented():
    cfg = _ladder_cfg()
    ladder = cfg.get("t1_ladder_continuation_v2", cfg["t1_ladder_continuation"])
    entry, risk = 7508.25, 1.0  # pre-band live geometry
    t1 = SA.t1_price(entry, entry + risk, "SHORT", t1_ladder_cont=ladder,
                     reversal=False, reversal_mult=0.8,
                     t1_floor_points=T1_FLOOR, ladder_shift=0)
    t2 = entry - 2.0 * risk
    assert abs(t2 - entry) < abs(t1 - entry)  # the incident: t2 inside t1


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
    print(f"\ntest_runner_t2_ordering.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
