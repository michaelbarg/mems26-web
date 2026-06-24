"""Regression: #68 structural targets for location-based day types.

Tests that REACTIVE on Normal day gets IB-center/VAL/IBL (SHORT) or
IB-center/VAH/IBH (LONG) — structural levels, not R-multiples.

RED-on-revert:
  - Reverting the resolver → returns None → caller keeps R-based targets.
  - Flipping direction flips C2/C3 (not tautological).
  - Missing IB levels → fail-safe (None).
"""
import os
import pytest
from unittest.mock import patch


# Ensure flag ON for tests
@pytest.fixture(autouse=True)
def enable_flag():
    with patch.dict(os.environ, {"DAYTYPE_TARGETS_STRUCTURAL": "1"}):
        # Reset cached style so fresh load
        import backend.v9.systems.structural_targets as st
        st._daytype_style = None
        yield
        st._daytype_style = None


TPO_NORMAL = {
    "ib_high": 7580.0,
    "ib_low": 7540.0,
    "poc": 7560.0,
    "vah": 7575.0,
    "val": 7545.0,
}

IB_CENTER = (7580.0 + 7540.0) / 2.0  # 7560.0


class TestNormalShort:
    """REACTIVE SHORT on Normal day: C1=IB-center, C2=VAL, C3=IBL."""

    def test_short_structural_targets(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Normal",
            direction="SHORT",
            entry_price=7578.0,  # near IBH
            stop_price=7585.0,
            tpo_ctx=TPO_NORMAL,
        )
        assert result is not None, "Normal SHORT should produce structural targets"
        assert result["t1_price"] == IB_CENTER  # C1 = IB-center
        assert result["t2_price"] == 7545.0     # C2 = VAL
        assert result["t3_price"] == 7540.0     # C3 = IBL
        assert result["contracts"] == 3
        assert result["structural"] is True

    def test_long_mirror(self):
        """LONG from IBL area: C1=IB-center, C2=VAH, C3=IBH."""
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Normal",
            direction="LONG",
            entry_price=7542.0,  # near IBL
            stop_price=7535.0,
            tpo_ctx=TPO_NORMAL,
        )
        assert result is not None
        assert result["t1_price"] == IB_CENTER  # C1
        assert result["t2_price"] == 7575.0     # C2 = VAH
        assert result["t3_price"] == 7580.0     # C3 = IBH
        assert result["contracts"] == 3

    def test_direction_flips_targets(self):
        """Flipping direction changes C2/C3 (not tautological)."""
        from backend.v9.systems.structural_targets import resolve_structural_targets
        short = resolve_structural_targets(
            day_type="Normal", direction="SHORT",
            entry_price=7578.0, stop_price=7585.0, tpo_ctx=TPO_NORMAL,
        )
        long = resolve_structural_targets(
            day_type="Normal", direction="LONG",
            entry_price=7542.0, stop_price=7535.0, tpo_ctx=TPO_NORMAL,
        )
        assert short["t2_price"] != long["t2_price"], "C2 must differ by direction"
        assert short["t3_price"] != long["t3_price"], "C3 must differ by direction"


class TestFailSafe:
    """Fail-safe: missing data → None (fall back to R-based)."""

    def test_missing_ib_high(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        ctx = {**TPO_NORMAL, "ib_high": None}
        result = resolve_structural_targets(
            day_type="Normal", direction="SHORT",
            entry_price=7578.0, stop_price=7585.0, tpo_ctx=ctx,
        )
        assert result is None, "Missing IB_high → fail-safe"

    def test_missing_poc(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        ctx = {**TPO_NORMAL, "poc": None}
        result = resolve_structural_targets(
            day_type="Normal", direction="SHORT",
            entry_price=7578.0, stop_price=7585.0, tpo_ctx=ctx,
        )
        assert result is None

    def test_no_tpo_ctx(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Normal", direction="SHORT",
            entry_price=7578.0, stop_price=7585.0, tpo_ctx=None,
        )
        assert result is None

    def test_flag_off(self):
        """When flag OFF (default), always returns None."""
        from backend.v9.systems.structural_targets import resolve_structural_targets
        with patch.dict(os.environ, {"DAYTYPE_TARGETS_STRUCTURAL": "0"}):
            result = resolve_structural_targets(
                day_type="Normal", direction="SHORT",
                entry_price=7578.0, stop_price=7585.0, tpo_ctx=TPO_NORMAL,
            )
            assert result is None, "Flag OFF → None (no behavior change)"


class TestTrendNormal:
    """Trend_Normal: movement-based with IB structural checkpoints."""

    def test_trend_normal_long_has_targets(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Trend_Normal", direction="LONG",
            entry_price=7585.0, stop_price=7575.0, tpo_ctx=TPO_NORMAL,
        )
        assert result is not None
        ib_width = 7580.0 - 7540.0  # 40pt
        assert result["t1_price"] == pytest.approx(7580.0 + ib_width * 2.0)  # 7660
        assert result["contracts"] == 3
        assert result["time_stop_minutes"] is None  # no time stop on trend

    def test_trend_dd_short_has_targets(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Trend_DD", direction="SHORT",
            entry_price=7535.0, stop_price=7545.0, tpo_ctx=TPO_NORMAL,
        )
        assert result is not None
        ib_width = 7580.0 - 7540.0  # 40pt
        assert result["t1_price"] == pytest.approx(7540.0 - ib_width)  # 7500
        assert result["contracts"] == 3
        assert result["time_stop_minutes"] == 90


class TestNeutralContracts:
    """#68 §C1: all day types get 3 contracts."""

    def test_neutral_extreme_3_contracts(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Neutral_Extreme", direction="SHORT",
            entry_price=7578.0, stop_price=7585.0, tpo_ctx=TPO_NORMAL,
        )
        assert result is not None
        assert result["contracts"] == 3, "NeuE must have 3 contracts (was 2)"
        assert result["t3_price"] is not None, "NeuE C3 (trail) must exist"

    def test_neutral_center_3_contracts(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Neutral_Center", direction="SHORT",
            entry_price=7578.0, stop_price=7585.0, tpo_ctx=TPO_NORMAL,
        )
        assert result is not None
        assert result["contracts"] == 3, "NeuC must have 3 contracts (was 1)"
        assert result["t2_price"] is not None, "NeuC C2 must exist"


class TestVariation:
    """Variation: go WITH IB expansion."""

    def test_long_extension(self):
        from backend.v9.systems.structural_targets import resolve_structural_targets
        result = resolve_structural_targets(
            day_type="Variation", direction="LONG",
            entry_price=7585.0, stop_price=7575.0, tpo_ctx=TPO_NORMAL,
        )
        assert result is not None
        ib_width = 7580.0 - 7540.0  # 40pt
        assert result["t1_price"] == pytest.approx(7580.0 + ib_width * 0.5)  # half ext
        assert result["t2_price"] == pytest.approx(7580.0 + ib_width)        # 1×IB
        assert result["contracts"] == 3
        assert result["time_stop_minutes"] == 60


class TestSanityCheck:
    """Target on wrong side of entry → fail-safe."""

    def test_short_c1_above_entry_fails(self):
        """If SHORT and C1 (IB-center) is above entry → fail-safe."""
        from backend.v9.systems.structural_targets import resolve_structural_targets
        # Entry below IB-center → C1 would be above entry → wrong side
        result = resolve_structural_targets(
            day_type="Normal", direction="SHORT",
            entry_price=7555.0,  # below IB-center (7560)
            stop_price=7565.0,
            tpo_ctx=TPO_NORMAL,
        )
        assert result is None, "C1 above entry for SHORT → fail-safe"
