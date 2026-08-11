"""A1 — STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1 (2026-08-11).

Case #655: DOUBLE_BOTTOM_EE_LONG bought 7795.00 on a Normal day — every
structural objective (half-extension 7781.12, VAH 7790.00, IB-high 7791.25)
was BELOW the entry. The system computed the correct Dalton read and then
R-fallback-rescued the targets, executing a −$63.75 loser.

This veto has two prongs:
  (a) all-wrong-side structural targets → blocked_by=structural_targets_wrong_side
  (b) R:R < 0.3 hard floor (un-rescuable) → blocked_by=rr_hard_floor
"""
import inspect

import pytest

from backend.v9.systems.structural_targets import _build_result


# ── _build_result: all-wrong-side detection ────────────────────────────────

class TestAllWrongSideDetection:
    """_build_result must set no_trade=True when ALL targets are wrong-side."""

    def test_all_wrong_side_long(self):
        """Case #655: c1/c2/c3 all below LONG entry → no_trade=True."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.0,
            c1=7781.0, c2=7790.0, c3=7791.25,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["no_trade"] is True
        assert result["all_wrong_side"] is True

    def test_all_wrong_side_short(self):
        """Mirror: c1/c2/c3 all above SHORT entry → no_trade=True."""
        result = _build_result(
            direction="SHORT", entry=7780.0, stop=7785.0,
            c1=7790.0, c2=7795.0, c3=7800.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["no_trade"] is True
        assert result["all_wrong_side"] is True

    def test_one_correct_side_long(self):
        """c1 wrong-side but c2 correct → NOT all-wrong-side."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.0,
            c1=7790.0, c2=7800.0, c3=7805.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["no_trade"] is False
        assert result["all_wrong_side"] is False

    def test_all_correct_side(self):
        """All targets on correct side → no_trade=False."""
        result = _build_result(
            direction="LONG", entry=7780.0, stop=7775.0,
            c1=7785.0, c2=7790.0, c3=7795.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["no_trade"] is False
        assert result["all_wrong_side"] is False

    def test_none_targets_not_wrong_side(self):
        """None targets are 'missing', not wrong-side — only non-None count."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.0,
            c1=7800.0, c2=None, c3=None,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["no_trade"] is False

    def test_all_none_targets(self):
        """All None → no non-None targets → no_trade=False (nothing wrong)."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.0,
            c1=None, c2=None, c3=None,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["all_wrong_side"] is False

    def test_case_655_exact_numbers(self):
        """Replay exact #655 numbers from the forensics report."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.75,
            c1=7781.12, c2=7790.0, c3=7791.25,
            contracts=4, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["no_trade"] is True
        assert result["all_wrong_side"] is True

    def test_short_c1_below_entry_c2c3_above(self):
        """SHORT: c1 below entry (correct), c2/c3 above → not all wrong-side."""
        result = _build_result(
            direction="SHORT", entry=7800.0, stop=7805.0,
            c1=7795.0, c2=7810.0, c3=7815.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["all_wrong_side"] is False

    def test_edge_case_target_equals_entry(self):
        """Target exactly at entry is wrong-side for c2/c3 (<=entry for LONG).
        c1 gets the c1_floor bump (0.5×ATR) so it's pushed to the correct side.
        Result: NOT all-wrong-side (c1 was bumped above entry)."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.0,
            c1=7795.0, c2=7795.0, c3=7795.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        # c1 gets floor-bumped above entry; c2/c3 at entry → wrong-side
        # But c1 is on correct side → not ALL wrong-side
        assert result["all_wrong_side"] is False


# ── Gateway code-path tests ────────────────────────────────────────────────
# (following the project's existing pattern: verify code paths exist via
# inspect.getsource, not full integration — the gateway has too many
# dependencies for isolated unit tests)

class TestGatewayVetoCodePath:
    """Verify the veto gate code exists in the gateway."""

    def test_veto_gate_exists_in_gateway(self):
        """The STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1 gate must exist."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1" in src
        assert "structural_targets_wrong_side" in src
        assert "all_wrong_side" in src

    def test_rr_hard_floor_exists_in_gateway(self):
        """The R:R hard floor gate must exist."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        assert "rr_hard_floor" in src
        assert "RR_HARD_FLOOR" in src
        assert "un-rescuable" in src

    def test_veto_before_target_application(self):
        """The veto must fire BEFORE targets are applied to the setup."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        # The veto line must appear BEFORE the target application lines
        veto_pos = src.index("structural_targets_wrong_side")
        apply_pos = src.index('setup["t1"] = _st["t1_price"]')
        assert veto_pos < apply_pos, \
            "veto must fire before targets are applied to setup"

    def test_hard_floor_after_wrong_side_check(self):
        """R:R hard floor must be checked after wrong-side (t1_dist > 0)."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        floor_pos = src.index("rr_hard_floor")
        wrong_side_pos = src.index("t1_wrong_side")
        assert floor_pos > wrong_side_pos, \
            "hard floor check must come after wrong-side check (t1_dist guaranteed > 0)"

    def test_flag_default_off(self):
        """Flag must default to OFF (0)."""
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)
        # The getenv default must be "0"
        assert 'STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1", "0"' in src


# ── Regression: valid trades must NOT be blocked ───────────────────────────

class TestRegressionValidTrades:
    """Verify that correct-side setups produce the expected results."""

    def test_normal_long_from_ibl(self):
        """Normal day LONG from IBL area: all targets above entry."""
        result = _build_result(
            direction="LONG", entry=7770.0, stop=7765.0,
            c1=7775.0, c2=7780.0, c3=7790.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["all_wrong_side"] is False
        assert result["no_trade"] is False
        # T1 should be on correct side
        assert result["t1_price"] > 7770.0

    def test_normal_short_from_ibh(self):
        """Normal day SHORT from IBH area: all targets below entry."""
        result = _build_result(
            direction="SHORT", entry=7790.0, stop=7795.0,
            c1=7785.0, c2=7780.0, c3=7770.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["all_wrong_side"] is False
        assert result["no_trade"] is False
        assert result["t1_price"] < 7790.0

    def test_variation_long_mixed(self):
        """Variation: c1 beyond IB but c2 at POC (could be below entry if entry
        is above POC). Only wrong-side if ALL wrong-side."""
        result = _build_result(
            direction="LONG", entry=7785.0, stop=7780.0,
            c1=7790.0, c2=7783.0, c3=7795.0,
            contracts=3, time_stop_minutes=60, trail_after_c2=True,
            day_type="Variation",
        )
        # c2 is below entry → wrong-side, but c1 and c3 correct → NOT all wrong
        assert result["all_wrong_side"] is False

    def test_tight_but_correct_targets(self):
        """Targets barely above entry — tight but correct side."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7790.0,
            c1=7795.50, c2=7796.0, c3=7797.0,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type="Normal",
        )
        assert result["all_wrong_side"] is False

    def test_wide_risk_correct_targets(self):
        """Wide stop (structural) with correct-side targets."""
        result = _build_result(
            direction="LONG", entry=7795.0, stop=7767.0,
            c1=7800.0, c2=7810.0, c3=7820.0,
            contracts=3, time_stop_minutes=60, trail_after_c2=True,
            day_type="Trend_Normal",
        )
        assert result["all_wrong_side"] is False
        assert result["no_trade"] is False
