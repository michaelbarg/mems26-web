"""TP-1 clamp tests — the trade-310 geometry must be corrected (2026-07-08).

Anti-tautological: test 1 fails trivially without the new module (import) and
encodes the exact live geometry: LONG on Variation, T2 +46.75 beyond IB-H.
Runnable standalone: python3 test_target_structure_clamp.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.systems.target_structure_clamp import clamp_targets_to_ib  # noqa: E402

IBH, IBL = 7524.75, 7501.75  # the real 07-08 IB


# 1 — the trade-310 geometry: LONG on Variation, targets beyond IB-H → clamped to IB-H.
def test_trade_310_geometry_clamped():
    setup = {"direction": "LONG", "t1": 7530.5, "t2": 7564.5, "t3": None}
    out, notes = clamp_targets_to_ib(setup, day_type="Variation", ib_high=IBH, ib_low=IBL)
    assert out["t1"] == IBH and out["t2"] == IBH, out
    assert len(notes) == 2


# 2 — Neutral day: beyond-IB targets stay (both-side extensions travel there).
def test_neutral_day_untouched():
    setup = {"direction": "LONG", "t1": 7530.5, "t2": 7564.5}
    out, notes = clamp_targets_to_ib(setup, day_type="Neutral_Extreme", ib_high=IBH, ib_low=IBL)
    assert out["t1"] == 7530.5 and out["t2"] == 7564.5 and notes == []


# 3 — Trend day: extension runs — untouched.
def test_trend_day_untouched():
    setup = {"direction": "SHORT", "t1": 7490.0, "t2": 7470.0}
    out, notes = clamp_targets_to_ib(setup, day_type="Trend_DD", ib_high=IBH, ib_low=IBL)
    assert out["t1"] == 7490.0 and notes == []


# 4 — SHORT mirror on Normal: inside-IB target untouched, beyond-IB-L clamped.
def test_short_mirror_clamped():
    setup = {"direction": "SHORT", "t1": 7510.0, "t2": 7460.0}
    out, notes = clamp_targets_to_ib(setup, day_type="Normal", ib_high=IBH, ib_low=IBL)
    assert out["t1"] == 7510.0          # inside IB (7501.75–7524.75) — untouched
    assert out["t2"] == IBL             # beyond IB-L — clamped
    assert len(notes) == 1


# 5 — honest missing: no IB / no day_type → untouched (never synthesize).
def test_missing_inputs_pass_through():
    setup = {"direction": "LONG", "t1": 7530.5}
    out, notes = clamp_targets_to_ib(setup, day_type="Variation", ib_high=None, ib_low=None)
    assert out["t1"] == 7530.5 and notes == []
    out2, notes2 = clamp_targets_to_ib(dict(setup), day_type=None, ib_high=IBH, ib_low=IBL)
    assert out2["t1"] == 7530.5 and notes2 == []


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
    print(f"\ntest_target_structure_clamp.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
