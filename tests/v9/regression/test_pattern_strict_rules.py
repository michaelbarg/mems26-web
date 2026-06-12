"""Regression — strict rules for losing patterns (Michael 2026-06-12 evening).

1. giant_bar_stop: tiny bars must NOT be re-anchored (VEGAS 18:35 bug — 6pt stop
   on a 1.0pt bar via the floor).
2. GIANT_BAR_EXCLUDE wiring: ZLR/HFE over-cap → strict SKIP, no re-anchor.
3. PATTERN_LOSS_BREAKER wiring present in the fire path.
"""
import inspect

import pytest

from backend.v9.systems.woodies.woodies_system import giant_bar_stop
from backend.v9.systems.woodies import woodies_system


class TestGiantBarPrecondition:
    def test_tiny_bar_not_reanchored(self):
        """The 18:35 VEGAS bug: bar_range=1.0 must return None (floor must not apply)."""
        assert giant_bar_stop(7444.75, 1.0, risk=57.2, cap=20,
                              bar_high=7445.0, bar_low=7444.0, frac=0.38, floor=6.0) is None

    def test_genuine_giant_bar_still_works(self):
        res = giant_bar_stop(7397.25, -1.0, risk=32.5, cap=15,
                             bar_high=7400.0, bar_low=7370.0, frac=0.38, floor=6.0)
        assert res is not None and res[1] == pytest.approx(11.4)

    def test_min_range_env(self, monkeypatch):
        monkeypatch.setenv("GIANT_BAR_MIN_RANGE_PT", "40")
        assert giant_bar_stop(7397.25, -1.0, risk=32.5, cap=15,
                              bar_high=7400.0, bar_low=7370.0, frac=0.38, floor=6.0) is None
        monkeypatch.setenv("GIANT_BAR_MIN_RANGE_PT", "12")
        assert giant_bar_stop(7397.25, -1.0, risk=32.5, cap=15,
                              bar_high=7400.0, bar_low=7370.0, frac=0.38, floor=6.0) is not None


class TestWiring:
    def test_loss_breaker_wired(self):
        src = inspect.getsource(woodies_system.WoodiesSystem.process_bar)
        assert "PATTERN_LOSS_BREAKER" in src and "pattern_id_at_entry = :pid" in src, (
            "loss breaker no longer wired into the fire path"
        )

    def test_exclude_list_wired(self):
        src = inspect.getsource(woodies_system.WoodiesSystem.process_bar)
        assert "GIANT_BAR_EXCLUDE" in src and "RISK_CAP_STRICT_SKIP" in src, (
            "ZLR/HFE strict-skip exclusion no longer wired"
        )
        assert '"ZLR,HFE"' in src  # default exclusion per Michael 2026-06-12
