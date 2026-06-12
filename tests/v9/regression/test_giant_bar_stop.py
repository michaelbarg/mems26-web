"""Regression — GIANT_BAR_STOP_V1 intra-bar stop re-anchor (2026-06-12).

RED-on-revert: weakening giant_bar_stop() or unwiring it from the caps block
fails these. The #69 scenario is encoded exactly.
"""
import pytest

from backend.v9.systems.woodies.woodies_system import giant_bar_stop


class TestGiantBarStop:
    def test_trade_69_scenario_short(self):
        """#69: ZLR SHORT entry 7397.25, anchor 7429.75 (32.5pt), cap 15.
        Entry bar ~30pt → re-anchor to 0.38×30=11.4pt inside the bar."""
        res = giant_bar_stop(entry=7397.25, sign=-1.0, risk=32.5, cap=15,
                             bar_high=7400.0, bar_low=7370.0, frac=0.38, floor=6.0)
        assert res is not None
        new_stop, new_risk = res
        assert new_risk == pytest.approx(11.4)
        assert new_stop == pytest.approx(7397.25 + 11.4)  # SHORT: stop above entry
        assert new_risk < 15  # within cap

    def test_long_direction(self):
        res = giant_bar_stop(entry=7400.0, sign=1.0, risk=40.0, cap=15,
                             bar_high=7405.0, bar_low=7380.0, frac=0.38, floor=6.0)
        new_stop, new_risk = res
        assert new_risk == pytest.approx(9.5)   # 0.38×25
        assert new_stop == pytest.approx(7390.5)  # LONG: stop below entry

    def test_floor_applies_on_small_bar(self):
        res = giant_bar_stop(entry=7400.0, sign=1.0, risk=30.0, cap=15,
                             bar_high=7404.0, bar_low=7396.0, frac=0.38, floor=6.0)
        assert res[1] == pytest.approx(6.0)  # 0.38×8=3.04 → floor 6

    def test_cap_clamps(self):
        res = giant_bar_stop(entry=7400.0, sign=1.0, risk=60.0, cap=15,
                             bar_high=7450.0, bar_low=7390.0, frac=0.38, floor=6.0)
        assert res[1] == pytest.approx(15.0)  # 0.38×60=22.8 → cap 15

    def test_not_applicable_when_risk_already_small(self):
        assert giant_bar_stop(7400.0, 1.0, risk=5.0, cap=15,
                              bar_high=7410.0, bar_low=7390.0, frac=0.38, floor=6.0) is None

    def test_degenerate_bar_returns_none(self):
        assert giant_bar_stop(7400.0, 1.0, 30.0, 15, 7400.0, 7400.0) is None


class TestWiring:
    """The caps block must call giant_bar_stop when the flag is ON."""

    def test_flag_gated_call_present(self):
        import inspect
        from backend.v9.systems.woodies import woodies_system
        src = inspect.getsource(woodies_system.WoodiesSystem.process_bar)
        assert "GIANT_BAR_STOP_V1" in src and "giant_bar_stop(" in src, (
            "giant_bar_stop is no longer wired into the PATTERN_RISK_CAPS block"
        )
