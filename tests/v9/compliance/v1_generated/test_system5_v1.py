"""V1 gap tests for System 5 (tpo).

Each test asserts a specific spec requirement that is NOT met in code.
Failures are EXPECTED — they prove drift.
"""
import pytest
from backend.v9.systems.tpo.schemas import (
    TPOProfile, TPOConfig, SessionState, ProfileShape,
    OpeningBehavior, OTFClarity, TPOLevel,
)
from backend.v9.systems.tpo.detector import (
    classify_shape, detect_intent, infer_otf_clarity,
)
from backend.v9.systems.tpo.profile_builder import (
    init_profile, lock_ib, refresh_levels,
)


# -- GAP: Stage F EOD processing ---

class TestStageF_EOD:
    """Spec Stage F: EOD processing (F1-F4).
    F1: Final lock, F2: Update naked POCs, F3: Stacked HVN, F4: Save to DB.
    Not implemented.
    """

    def test_eod_module_exists(self):
        """Spec: TPO system must have EOD processing module."""
        try:
            from backend.v9.systems.tpo import eod
            assert hasattr(eod, "process_eod"), (
                "eod module must have process_eod function"
            )
        except ImportError:
            pytest.fail(
                "Spec Stage F: TPO must have EOD processing module. "
                "Not found at backend.v9.systems.tpo.eod"
            )

    def test_profile_has_eod_fields(self):
        """Spec F2: Profile must track naked POC 'touched today' status."""
        profile = TPOProfile()
        assert hasattr(profile, "naked_poc_touched_today") or \
               hasattr(profile, "naked_poc_status"), (
            "Spec F2/D4: TPOProfile must track which naked POCs were "
            "touched today. Field missing."
        )


# -- GAP: Opening behavior 4-type classification ---

class TestOpeningBehaviorClassification:
    """Spec Stage B Q4: First 5 min behavior must be classified as:
    ONE-WAY MOVE, TEST & REVERSE, OSCILLATE, STRONG ONE-WAY THEN REVERSE.
    """

    def test_opening_behavior_has_classification(self):
        """Spec: OpeningBehavior must have a 'behavior_type' classification."""
        ob = OpeningBehavior()
        assert hasattr(ob, "behavior_type") or \
               hasattr(ob, "classification"), (
            "Spec B Q4: OpeningBehavior must classify as "
            "ONE_WAY/TEST_REVERSE/OSCILLATE/STRONG_REVERSE. "
            f"Current fields: {list(ob.model_fields.keys())}"
        )


# -- GAP: Shape lock at 14:00 ET ---

class TestShapeLockAt1400:
    """Spec Stage D Q12: Profile shape must be LOCKED at 14:00 ET
    with confidence >= 0.85.
    """

    def test_shape_lock_requires_time_check(self):
        """Spec: classify_shape or a wrapper must accept session_min for time gating."""
        import inspect
        sig = inspect.signature(classify_shape)
        params = list(sig.parameters.keys())
        has_time_param = any(p in params for p in
                            ["session_min", "time_et", "current_time"])
        assert has_time_param, (
            f"Spec D Q12: classify_shape must accept time parameter "
            f"to enforce lock at 14:00 ET. "
            f"Current params: {params}"
        )


# -- GAP: Opening behavior to Redis ---

class TestOpeningBehaviorRedisPublish:
    """Spec Stage B Q5: opening_behavior_data must be published to Redis
    at 09:45 (15 min mark).
    """

    def test_redis_publish_function_exists(self):
        """Spec: TPO system must have Redis publishing for opening behavior."""
        try:
            from backend.v9.systems.tpo import api
            assert hasattr(api, "publish_opening_behavior") or \
                   hasattr(api, "push_opening_to_redis"), (
                "TPO API must have opening behavior Redis publish function"
            )
        except (ImportError, AttributeError):
            pytest.fail(
                "Spec B Q5: TPO must publish opening_behavior_data to Redis. "
                "No publish function found."
            )


# -- GAP: Degraded mode gap detection ---

class TestDegradedModeGapDetection:
    """Spec: If Sierra DLL data gap > 60sec, mark letter INCOMPLETE
    and set data_quality = DEGRADED.
    """

    def test_profile_supports_degraded_mode(self):
        """Spec: Profile must support DEGRADED data_quality."""
        profile = TPOProfile(data_quality="DEGRADED")
        assert profile.data_quality == "DEGRADED"

    def test_profile_tracks_incomplete_letters(self):
        """Spec: Profile must track which letters are INCOMPLETE."""
        profile = TPOProfile()
        assert hasattr(profile, "incomplete_letters"), (
            "Spec: TPOProfile must track incomplete_letters "
            "for degraded mode (DLL gap > 60sec). Field missing."
        )


# -- GAP: 8 profile shapes correctly mapped ---

class TestProfileShapeDayTypeMapping:
    """Spec Stage D Q11: Each of 8 shapes maps to a day type suggestion."""

    def test_all_8_shapes_exist(self):
        """Spec: ProfileShape enum must have exactly 8 values."""
        shapes = [s for s in ProfileShape]
        assert len(shapes) == 8, (
            f"Spec defines 8 profile shapes. Got {len(shapes)}: "
            f"{[s.value for s in shapes]}"
        )

    def test_shape_classification_works(self):
        """Spec: classify_shape must set a valid shape on the profile."""
        profile = TPOProfile(
            session_high=5260.0,
            session_low=5240.0,
            poc=5250.0,
        )
        profile.ib.high = 5255.0
        profile.ib.low = 5245.0
        profile.ib.width = 10.0
        profile.ib.locked = True

        for p in range(5240, 5261):
            key = f"{float(p):.4f}"
            letters = ["A", "B", "C"] if 5248 <= p <= 5252 else ["A"]
            profile.levels[key] = TPOLevel(price=float(p), letters=letters)

        config = TPOConfig()
        result = classify_shape(profile, config)
        assert result.shape is not None, (
            "classify_shape must set a ProfileShape value"
        )
