"""STOP_STRUCTURE_TRAIL_V1 — after T1 the stop parks at STRUCTURE, not BE
(Michael ruling 2026-07-08). Flag-OFF default = byte-identical BE+1T.

Anti-tautological: test 1 fails on the old code (no structure path existed).
Runnable standalone: python3 test_stop_structure_trail.py
"""
import os
import sys
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

for _f in ("STOP_STRUCTURE_TRAIL_V1",):
    os.environ.pop(_f, None)

from backend.v9.services.trade_manager.manager import TradeManager  # noqa: E402


class FakeDB:
    def add(self, *a, **k):
        pass

    def flush(self):
        pass


def _trade(**over):
    base = dict(id=330, mode="shadow", direction="LONG", state="PARTIAL",
                entry_price=7500.0, stop=7492.0, t1=7504.0, t2=7508.0, t3=None,
                quality={"initial_stop": 7492.0, "contracts": 2},
                cross_context=[], t1_hit_ts=None)
    base.update(over)
    return SimpleNamespace(**base)


def _tm(struct_value):
    tm = TradeManager(db=FakeDB())
    tm._structure_stop_after_t1 = lambda direction: struct_value
    return tm


# 1 — flag ON + structure available: stop parks at the anchor (NOT entry+tick).
def test_structure_wins_over_be():
    os.environ["STOP_STRUCTURE_TRAIL_V1"] = "1"
    try:
        t = _trade()
        _tm(7497.5)._apply_smart_be_after_t1(t)   # anchor below BE — room for expansion
        assert t.stop == 7497.5, t.stop            # old code: 7500.25 (BE+1T)
        assert t.cross_context[-1]["reason"] == "structure-trail after T1"
    finally:
        os.environ.pop("STOP_STRUCTURE_TRAIL_V1", None)


# 2 — flag OFF: BE+1T exactly as before.
def test_flag_off_keeps_be():
    t = _trade()
    _tm(7497.5)._apply_smart_be_after_t1(t)
    assert t.stop == 7500.25  # entry + 1 tick


# 3 — structure unavailable (None): falls back to BE+1T even with flag ON.
def test_structure_missing_falls_back():
    os.environ["STOP_STRUCTURE_TRAIL_V1"] = "1"
    try:
        t = _trade()
        _tm(None)._apply_smart_be_after_t1(t)
        assert t.stop == 7500.25
    finally:
        os.environ.pop("STOP_STRUCTURE_TRAIL_V1", None)


# 4 — never widen: current stop already tighter than the anchor → untouched.
def test_never_widen():
    os.environ["STOP_STRUCTURE_TRAIL_V1"] = "1"
    try:
        t = _trade(stop=7499.0)                    # already tighter than anchor
        _tm(7497.5)._apply_smart_be_after_t1(t)
        assert t.stop == 7499.0
    finally:
        os.environ.pop("STOP_STRUCTURE_TRAIL_V1", None)


# 5 — SHORT mirror: anchor above entry-tick wins; never widen respected.
def test_short_mirror():
    os.environ["STOP_STRUCTURE_TRAIL_V1"] = "1"
    try:
        t = _trade(direction="SHORT", entry_price=7500.0, stop=7508.0,
                   quality={"initial_stop": 7508.0, "contracts": 2})
        _tm(7503.25)._apply_smart_be_after_t1(t)
        assert t.stop == 7503.25
    finally:
        os.environ.pop("STOP_STRUCTURE_TRAIL_V1", None)


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
    print(f"\ntest_stop_structure_trail.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
