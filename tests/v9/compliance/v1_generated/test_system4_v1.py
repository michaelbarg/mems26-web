"""V1 gap tests for System 4 (woodies).

Each test asserts a specific spec requirement that is NOT met in code.
Failures are EXPECTED — they prove drift.
"""
import pytest
from backend.v9.systems.woodies.cci_calc import compute_all_studies
from backend.v9.systems.woodies.schemas import WoodiesBar


# ── GAP: lsma_above_price missing from compute_all_studies ────

class TestLSMAAbovePriceInOutput:
    """Spec Section 4 Study #5: lsma_above_price (bool).
    compute_all_studies does not return this field.
    """

    def test_lsma_above_price_in_studies(self):
        """Spec: compute_all_studies must return lsma_above_price."""
        highs = [5250 + i * 0.5 for i in range(20)]
        lows = [5245 + i * 0.5 for i in range(20)]
        closes = [5248 + i * 0.5 for i in range(20)]

        studies = compute_all_studies(highs, lows, closes)
        assert "lsma_above_price" in studies, (
            f"Spec Study #5: compute_all_studies must return 'lsma_above_price'. "
            f"Keys returned: {list(studies.keys())}"
        )


# ── GAP: zlr_detected missing from compute_all_studies ────────

class TestZLRDetectedInOutput:
    """Spec Section 4 Study #10: zlr_detected (bool).
    compute_all_studies does not compute ZLR detection.
    """

    def test_zlr_detected_in_studies(self):
        """Spec: compute_all_studies must return zlr_detected."""
        highs = [5250 + i * 0.5 for i in range(20)]
        lows = [5245 + i * 0.5 for i in range(20)]
        closes = [5248 + i * 0.5 for i in range(20)]

        studies = compute_all_studies(highs, lows, closes)
        assert "zlr_detected" in studies, (
            f"Spec Study #10: compute_all_studies must return 'zlr_detected'. "
            f"Keys returned: {list(studies.keys())}"
        )


# ── GAP: zlr_direction missing from compute_all_studies ───────

class TestZLRDirectionInOutput:
    """Spec Section 4 Study #11: zlr_direction ("UP"/"DOWN"/"NONE").
    compute_all_studies does not compute ZLR direction.
    """

    def test_zlr_direction_in_studies(self):
        """Spec: compute_all_studies must return zlr_direction."""
        highs = [5250 + i * 0.5 for i in range(20)]
        lows = [5245 + i * 0.5 for i in range(20)]
        closes = [5248 + i * 0.5 for i in range(20)]

        studies = compute_all_studies(highs, lows, closes)
        assert "zlr_direction" in studies, (
            f"Spec Study #11: compute_all_studies must return 'zlr_direction'. "
            f"Keys returned: {list(studies.keys())}"
        )


# ── GAP: WoodiesBar schema must match all 11 DLL fields ──────

class TestWoodiesBarSchemaComplete:
    """Spec Section 6: JSON export has all 11 studies.
    WoodiesBar Pydantic schema must include every field.
    """

    def test_woodies_bar_has_all_11_fields(self):
        """Spec: WoodiesBar must have all 11 study fields from DLL."""
        required_fields = [
            "cci_14", "cci_6_tcci", "ema_34", "lsma_value",
            "lsma_above_price", "swi_value", "czi_value",
            "trend_state", "predictor_next_cci",
            "zlr_detected", "zlr_direction",
        ]
        bar_fields = set(WoodiesBar.model_fields.keys())
        for field in required_fields:
            assert field in bar_fields, (
                f"WoodiesBar missing spec field: {field}. "
                f"Available: {sorted(bar_fields)}"
            )


# ── GAP: Trend state thresholds match DLL ─────────────────────

class TestTrendStateThresholds:
    """Spec Section 4 Study #8 — Trend State:
    BLUE: CCI > 50 AND prev > 0 AND SWI > 20
    RED: CCI < -50 AND prev < 0 AND SWI < -20
    YELLOW: CCI crossed zero recently
    GRAY: choppy / no clear trend
    """

    def test_blue_trend_state(self):
        """Spec: BLUE requires CCI>50 AND prev>0 AND SWI>20."""
        from backend.v9.systems.woodies.cci_calc import calc_trend_state
        result = calc_trend_state(cci14=60, cci14_prev=10, swi=25)
        assert result == "BLUE", f"Expected BLUE, got {result}"

    def test_red_trend_state(self):
        """Spec: RED requires CCI<-50 AND prev<0 AND SWI<-20."""
        from backend.v9.systems.woodies.cci_calc import calc_trend_state
        result = calc_trend_state(cci14=-60, cci14_prev=-10, swi=-25)
        assert result == "RED", f"Expected RED, got {result}"

    def test_yellow_trend_state_zero_cross(self):
        """Spec: YELLOW when CCI crossed zero recently."""
        from backend.v9.systems.woodies.cci_calc import calc_trend_state
        result = calc_trend_state(cci14=5, cci14_prev=-10, swi=2)
        assert result == "YELLOW", f"Expected YELLOW, got {result}"


# ── GAP: VEGAS double divergence ──────────────────────────────

class TestVegasDoubleDivergence:
    """Spec Pattern B1: VEGAS requires DOUBLE divergence
    (CCI-14 double divergence vs price).
    """

    def test_vegas_requires_double_divergence(self):
        """Spec: VEGAS detector must check for DOUBLE divergence, not single."""
        from backend.v9.systems.woodies.patterns.vegas import detect_vegas
        import inspect
        source = inspect.getsource(detect_vegas)
        # The function should check for two consecutive divergence points
        assert "double" in source.lower() or "second" in source.lower() or \
               source.count("diverge") >= 2, (
            "VEGAS spec requires DOUBLE divergence detection. "
            "Implementation may only detect single divergence."
        )
