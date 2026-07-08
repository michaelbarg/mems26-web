"""Entry-confirm tolerance (Michael ruling 2026-07-08) — counter-close within
frac×ATR is noise, not rejection.

Live incident: 18:00 REACTIVE SHORT blocked because the signal bar closed
0.75pt (3 ticks) ABOVE open on a ~10pt-candle day. Ruling: everything is
measured relative to the average candle.

Anti-tautological: test 1 FAILS on the old code (no tol_points param / strict c<o).
Runnable standalone: python3 test_entry_confirm_tolerance.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.systems.entry_confirm import entry_confirmed  # noqa: E402


# 1 — the exact 18:00 live geometry: SHORT, counter-close 0.75pt, tol 1.0pt → confirmed.
def test_short_counter_close_within_tol_confirms():
    ok, reason = entry_confirmed(direction="SHORT",
                                 bars=[{"o": 7493.5, "c": 7494.25}],
                                 tol_points=1.0)
    assert ok, f"0.75pt counter-close within 1.0pt tol must confirm: {reason}"


# 2 — a REAL counter-bar (beyond tol) still blocks.
def test_short_counter_close_beyond_tol_blocks():
    ok, reason = entry_confirmed(direction="SHORT",
                                 bars=[{"o": 7493.5, "c": 7496.0}],
                                 tol_points=1.0)
    assert not ok and "no bearish confirm" in reason


# 3 — tol=0 (default) keeps the original strict behavior.
def test_default_zero_tol_is_strict():
    ok, _ = entry_confirmed(direction="SHORT", bars=[{"o": 7493.5, "c": 7494.25}])
    assert not ok
    ok2, _ = entry_confirmed(direction="SHORT", bars=[{"o": 7493.5, "c": 7493.0}])
    assert ok2


# 4 — LONG mirror.
def test_long_mirror():
    ok, _ = entry_confirmed(direction="LONG", bars=[{"o": 7500.0, "c": 7499.5}],
                            tol_points=1.0)
    assert ok  # 0.5pt against, within tol
    ok2, _ = entry_confirmed(direction="LONG", bars=[{"o": 7500.0, "c": 7498.0}],
                             tol_points=1.0)
    assert not ok2


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
    print(f"\ntest_entry_confirm_tolerance.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
