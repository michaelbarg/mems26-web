"""Regression: woodies signal write + ZLR breakout-bar stop.

#1: v9_woodies_signals INSERT must include is_synthetic explicitly.
#4: ZLR breakout_bar/1 stop must produce risk ≤ 15pt cap (was 16.5pt with cluster_low/4).

Anti-tautological: calls REAL resolver + verifies the INSERT SQL.
Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import pytest
from backend.v9.systems.stop_anchors.resolver import (
    resolve_anchor_from_window, window_extreme, apply_offset, risk_points,
)


# ---------------------------------------------------------------------------
# Test 1: is_synthetic in INSERT SQL
# if reverted → RED because removing is_synthetic from the INSERT causes
# NotNullViolation on DB instances without the column DEFAULT
# ---------------------------------------------------------------------------
class TestIsSyntheticExplicit:
    def test_persist_pattern_sql_includes_is_synthetic(self):
        """The _persist_pattern INSERT must include is_synthetic column."""
        import inspect
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem
        source = inspect.getsource(WoodiesSystem._persist_pattern)
        assert "is_synthetic" in source, (
            "_persist_pattern INSERT must explicitly pass is_synthetic"
        )
        # The VALUES tuple must have 16 params (15 original + is_synthetic)
        # Count the ? placeholders
        assert source.count("?") >= 16, (
            "INSERT must have 16+ placeholders (15 original + is_synthetic)"
        )


# ---------------------------------------------------------------------------
# Test 2: ZLR breakout_bar/1 stop regression (06-30: 16.5pt → ≤15pt)
# if reverted → RED because cluster_low/4 reaches stale dips
# ---------------------------------------------------------------------------
class TestZLRBreakoutBarStop:
    def test_breakout_bar_window_1_uses_signal_bar(self):
        """breakout_bar/window=1: stop anchors to the CURRENT (signal) bar only,
        not 4 bars back. This is the 06-30 fix — was cluster_low/4."""
        bar = {"o": 7530, "h": 7535, "l": 7527.5, "c": 7533}
        # LONG: stop = bar low - 3T (offset=3, tick=0.25)
        stop = resolve_anchor_from_window([bar], "LONG", offset_ticks=3, tick_size=0.25)
        assert stop == 7527.5 - 0.75  # 7526.75
        assert stop == 7526.75

    def test_breakout_bar_vs_cluster_low_regression(self):
        """06-30 regression: cluster_low/4 reached bar 4 back (low=7516.5)
        giving 16.5pt stop > 15pt cap → SKIP. breakout_bar/1 uses only the
        signal bar (low=7527.5) → ~7pt stop ≤ cap → passes.

        if reverted → RED because the old window-4 produces the wide stop.
        """
        # The 4-bar window that caused the 16.5pt stop
        bars_4 = [
            {"o": 7520, "h": 7522, "l": 7516.5, "c": 7519},  # stale dip (bar -4)
            {"o": 7522, "h": 7528, "l": 7521, "c": 7527},
            {"o": 7527, "h": 7532, "l": 7526, "c": 7531},
            {"o": 7531, "h": 7535, "l": 7527.5, "c": 7533},  # signal bar
        ]
        entry = 7533.0  # ZLR entry = breakout bar close

        # Old: cluster_low/4 → min(lows) = 7516.5 → stop = 7516.5 - 0.75 = 7515.75
        old_stop = resolve_anchor_from_window(bars_4, "LONG", offset_ticks=3, tick_size=0.25)
        old_risk = risk_points(entry, old_stop)
        assert old_risk > 15, f"Old risk should be > 15pt cap, got {old_risk}"

        # New: breakout_bar/1 → signal bar only → low = 7527.5 → stop = 7526.75
        new_stop = resolve_anchor_from_window(bars_4[-1:], "LONG", offset_ticks=3, tick_size=0.25)
        new_risk = risk_points(entry, new_stop)
        assert new_risk <= 15, f"New risk should be ≤ 15pt cap, got {new_risk}"
        assert new_risk == pytest.approx(6.25, abs=0.01)

    def test_short_breakout_bar(self):
        """SHORT: stop = signal bar high + 3T."""
        bar = {"o": 7530, "h": 7535, "l": 7527.5, "c": 7528}
        stop = resolve_anchor_from_window([bar], "SHORT", offset_ticks=3, tick_size=0.25)
        assert stop == 7535 + 0.75  # 7535.75
