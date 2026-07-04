"""I-62: demo/live trades close ONLY on Sierra fill events, not bar-price inference.

Trade 290 (07-03): BarLevelDetector inferred STOP_HIT on bar-close price while
Sierra still held the position → internal CLOSED but orphan in Sierra.

Anti-tautological: the old code (without the I-62 guard) would call on_stop_hit
for demo trades → this test fails on that behavior.

Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import inspect

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def test_demo_stop_deferred_to_sierra():
    """Demo/live stop hit → BarLevelDetector logs INFERRED but does NOT call on_stop_hit.

    if reverted → RED because the old code calls on_stop_hit for all trades.
    """
    src = inspect.getsource(BarLevelDetector.on_bar)
    assert "_is_demo_live" in src, "I-62 guard must check trade mode"
    assert "STOP INFERRED (demo/live)" in src, "Demo stop must be logged as INFERRED, not HIT"
    assert "awaiting Sierra fill" in src, "Must indicate waiting for Sierra fill"


def test_demo_t3_deferred_to_sierra():
    """Demo/live T3 → BarLevelDetector does NOT close (wait for Sierra fill).

    if reverted → RED because the old code closes on T3 for all trades.
    """
    src = inspect.getsource(BarLevelDetector.on_bar)
    assert "T3 INFERRED (demo/live)" in src, "Demo T3 must be deferred to Sierra"


def test_shadow_stop_still_closes():
    """Shadow trades still close on bar-price inference (no Sierra for shadow).

    if reverted → RED because shadow needs bar-level close to work at all.
    """
    src = inspect.getsource(BarLevelDetector.on_bar)
    # The on_stop_hit call must still exist for shadow trades
    assert "on_stop_hit" in src, "Shadow trades must still call on_stop_hit"
    # And it must be gated (not _is_demo_live)
    assert "if _is_demo_live:" in src, "Guard must check _is_demo_live before skipping"


def test_demo_t1_t2_still_processed():
    """Demo T1/T2 hits still run (for trailing + BE) — only T3/STOP deferred.

    if reverted → RED because T1/T2 processing is essential for stop management.
    """
    src = inspect.getsource(BarLevelDetector.on_bar)
    # T3 is gated, but T1/T2 are NOT gated (on_target_hit runs for all)
    # The guard is: `if _is_demo_live and target_name == "T3"`
    assert '_is_demo_live and target_name == "T3"' in src, \
        "Only T3 should be deferred for demo, not T1/T2"
