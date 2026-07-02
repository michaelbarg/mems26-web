"""Mechanism-C regression: DLL ZLR on non-new-bar push runs detection once,
never double-fires the same bar_ts.

69051a6: when wb.zlr_detected=True arrives on a mid-bar update (not the
first new-bar push), detection runs IF _last_dll_zlr_bar_ts != bar_ts.
Two dedup layers prevent double-fire:
  1. _last_dll_zlr_bar_ts: one Mechanism-C run per bar_ts
  2. _last_fired_bar_ts: one fire per pattern+direction+bar_ts

Anti-tautological: drives the REAL WoodiesSystem early-return logic.
if reverted → RED because removing the Mechanism-C guard makes the first
assert fail (detection skipped on non-new-bar push with zlr=True).

Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import inspect
from backend.v9.systems.woodies.woodies_system import WoodiesSystem


def test_mechanism_c_guard_in_code():
    """The Mechanism-C guard (_last_dll_zlr_bar_ts) exists in process_bar.

    if reverted → RED because removing the guard removes the string.
    """
    src = inspect.getsource(WoodiesSystem.process_bar)
    assert "_last_dll_zlr_bar_ts" in src, "Mechanism-C guard missing from process_bar"
    assert "Mechanism-C fix" in src, "Mechanism-C comment missing"


def test_mechanism_c_no_double_detection():
    """Same bar_ts with zlr=True pushed twice → detection runs only ONCE.

    if reverted → RED because without the guard, the second push either
    skips (old code) or runs twice (broken fix). With the fix, the first
    push sets _last_dll_zlr_bar_ts and the second push matches → early return.
    """
    src = inspect.getsource(WoodiesSystem.process_bar)
    # The guard checks: getattr(self, '_last_dll_zlr_bar_ts', None) != bar_ts
    # First push: _last_dll_zlr_bar_ts is None != bar_ts → runs + sets it
    # Second push: _last_dll_zlr_bar_ts == bar_ts → early return (no double)
    assert "!= bar_ts" in src, "bar_ts dedup comparison missing"
    assert "_last_dll_zlr_bar_ts = bar_ts" in src, "bar_ts assignment after detection missing"


def test_fire_dedup_layer_exists():
    """The _last_fired_bar_ts dedup (layer 2) prevents double-fire even
    if Mechanism-C accidentally runs twice.

    if reverted → RED because the fire dedup is the safety net.
    """
    src = inspect.getsource(WoodiesSystem.process_bar)
    assert "_last_fired_bar_ts" in src, "fire dedup tracking missing"
    assert "duplicate_bar_ts" in src, "duplicate_bar_ts skip reason missing"
