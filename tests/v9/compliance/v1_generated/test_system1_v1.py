"""V1 gap tests for System 1 (day_type).

Each test asserts a specific spec requirement that is NOT met in code.
Failures are EXPECTED — they prove drift.
"""
import pytest
from backend.v9.systems.day_type.schemas import (
    DayTypeConfig, BarInput, DayType, OpeningType, IBWidth,
)
from backend.v9.systems.day_type.state_machine import (
    DayTypeStateMachine, DECISION_MATRIX,
)
from backend.v9.systems.day_type.detector import (
    detect_opening_type, classify_ib_width,
)


# ── GAP: V2 Tree confidence threshold is 0.85 ──────────────────

class TestConfidenceThresholdSpec:
    """V2 Tree Q14/E1 says min_lock_confidence = 0.85 (default).
    Code uses 0.70 default — too low, locks day type prematurely.
    """

    def test_default_confidence_threshold_is_085(self):
        """Spec: min_lock_confidence default = 0.85."""
        config = DayTypeConfig()
        assert config.confidence_threshold == 0.85, (
            f"Spec requires default confidence_threshold=0.85, "
            f"got {config.confidence_threshold}"
        )


# ── GAP: Decision matrix must return top-2 + probabilities ─────

class TestDecisionMatrixProbabilities:
    """V2 Tree: Decision Matrix outputs top1 + top2 + confidence (0.45-0.75).
    Code returns single DayType per cell, not probability distribution.
    """

    def test_matrix_cell_returns_top2_and_probabilities(self):
        """Spec: each matrix cell must return top-2 candidates + probabilities."""
        key = (OpeningType.OPEN_DRIVE, IBWidth.NARROW)
        result = DECISION_MATRIX.get(key)
        # Spec says: Trend_Normal: 60%, Trend_DD: 25%, Variation: 15%
        assert isinstance(result, dict), (
            f"Matrix cell should return dict with probabilities, "
            f"got {type(result).__name__}: {result}"
        )
        assert "top1" in result and "top2" in result, (
            "Matrix cell must contain top1 and top2 keys"
        )


# ── GAP: INDETERMINATE opening type ────────────────────────────

class TestIndeterminateOpeningType:
    """V2 Tree Q7: When opening is ambiguous, classify as INDETERMINATE
    and wait until 10:30 IB lock. Code has no INDETERMINATE type.
    """

    def test_indeterminate_opening_exists(self):
        """Spec: OpeningType enum must include INDETERMINATE."""
        assert hasattr(OpeningType, "INDETERMINATE"), (
            "V2 Tree defines INDETERMINATE opening type — "
            "code only has UNKNOWN (different semantics)"
        )


# ── GAP: Opening confidence percentages per spec ───────────────

class TestOpeningConfidencePercentages:
    """V2 Tree assigns specific confidence per opening type:
    OD=95%, OTD=85%, ORR=50%, OA=40%.
    """

    def test_open_drive_confidence_is_095(self):
        """Spec: OPEN_DRIVE initial confidence = 0.95."""
        bars = [
            BarInput(ts=1.0, session_min=5, open=5250, high=5253,
                     low=5250, close=5253),
            BarInput(ts=2.0, session_min=10, open=5253, high=5256,
                     low=5253, close=5256),
            BarInput(ts=3.0, session_min=15, open=5256, high=5259,
                     low=5256, close=5259),
        ]
        otype, direction, conf = detect_opening_type(bars)
        if otype == OpeningType.OPEN_DRIVE:
            assert conf == 0.95, (
                f"Spec: OPEN_DRIVE confidence must be 0.95, got {conf}"
            )


# ── GAP: A1 gap magnitude classification ──────────────────────

class TestGapMagnitudeClassification:
    """V1 Tree A1: gap magnitude = SMALL_GAP (<0.3 ATR),
    MEDIUM_GAP (0.3-1.0 ATR), LARGE_GAP (>=1.0 ATR).
    Code only classifies gap as UP/DOWN/FLAT.
    """

    def test_pre_open_has_gap_magnitude(self):
        """Spec: PreOpenContext must include gap_magnitude field."""
        sm = DayTypeStateMachine()
        bar = BarInput(
            ts=1.0, session_min=0,
            open=5260, high=5262, low=5258, close=5261,
            pd_close=5250, pd_high=5255, pd_low=5240,
            atr=10.0,
        )
        state = sm.process_bar(bar)
        assert state.pre_open is not None
        assert hasattr(state.pre_open, "gap_magnitude"), (
            "PreOpenContext must have gap_magnitude field "
            "(SMALL_GAP/MEDIUM_GAP/LARGE_GAP)"
        )
        assert state.pre_open.gap_magnitude in (
            "SMALL_GAP", "MEDIUM_GAP", "LARGE_GAP"
        ), f"gap_magnitude must be SMALL/MEDIUM/LARGE, got {state.pre_open.gap_magnitude}"


# ── GAP: IB Width boundary differs between V1 and V2 trees ────

class TestIBWidthBoundary:
    """V1 Tree: MEDIUM = 15-20pt, WIDE > 20pt.
    V2 Tree: MEDIUM = 15-25pt, WIDE > 25pt.
    Code follows V2 (25pt boundary). This test documents the divergence.
    """

    def test_20pt_ib_classified_as_medium_v1_tree(self):
        """V1 Tree: 20pt IB should be at MEDIUM/WIDE boundary."""
        width = classify_ib_width(20.0, narrow_max=15.0, medium_max=20.0)
        assert width == IBWidth.MEDIUM, (
            f"V1 Tree: 20pt is MEDIUM (upper bound). Got {width}"
        )

    def test_21pt_ib_classified_as_wide_v1_tree(self):
        """V1 Tree: 21pt IB should be WIDE."""
        width = classify_ib_width(21.0, narrow_max=15.0, medium_max=20.0)
        assert width == IBWidth.WIDE, (
            f"V1 Tree: 21pt should be WIDE per V1 (max_medium=20). Got {width}"
        )


# ── GAP: Profile shape boost not integrated ───────────────────

class TestProfileShapeBoost:
    """V2 Tree Stage C2/D1: 8 profile shapes provide confidence boosts.
    State machine does not read profile shape from TPO system.
    """

    def test_state_includes_profile_shape(self):
        """Spec: DayTypeState should incorporate profile shape data."""
        sm = DayTypeStateMachine()
        # Process bars through IB lock
        for i in range(15):
            bar = BarInput(
                ts=float(i), session_min=i * 5,
                open=5250, high=5255, low=5245, close=5252,
            )
            state = sm.process_bar(bar)
        # After IB lock, profile shape should be accessible
        assert hasattr(state, "profile_shape") or (
            state.meta.get("profile_shape") is not None
        ), "DayTypeState must include profile_shape from TPO (V2 Tree Stage C2)"


# ── GAP: Re-eval Trigger 1 (News Events) ──────────────────────

class TestReEvalNewsEventTrigger:
    """V2 Tree Q16 Trigger 1: News Event (FOMC, NFP) should force re-eval.
    Code only implements triggers 2 (extreme move), 3 (failed ext), 4 (range).
    """

    def test_reeval_has_news_trigger(self):
        """Spec: check_reeval_triggers must accept news_event parameter."""
        from backend.v9.systems.day_type.detector import check_reeval_triggers
        import inspect
        sig = inspect.signature(check_reeval_triggers)
        params = list(sig.parameters.keys())
        assert "news_event" in params, (
            f"check_reeval_triggers must accept news_event parameter. "
            f"Current params: {params}"
        )
