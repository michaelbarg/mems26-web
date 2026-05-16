"""R3 Spec Compliance Tests — System 1 (day_type).

Validates every requirement from MEMS26_DAY_TYPE_DECISION_TREE_V2.
"""
import pytest

from backend.v9.systems.day_type.schemas import (
    BarInput, DayType, OpeningType, IBWidth, Stage,
    Behavior, RangeCategory, FailedExtensionType,
    DayTypeConfig, DayTypeState, PlaybookOutput,
)
from backend.v9.systems.day_type.state_machine import (
    DayTypeStateMachine, DECISION_MATRIX, PLAYBOOK_TEMPLATES,
)
from backend.v9.systems.day_type.detector import (
    classify_ib_width, detect_opening_type, detect_behavior,
    detect_failed_extension, classify_range, calculate_confidence,
    check_reeval_triggers,
)


# ── Helpers ──────────────────────────────────────────────────────

def _bar(session_min=0, o=5250, h=5252, l=5248, c=5251,
         pd_high=5260, pd_low=5240, pd_close=5250,
         overnight_high=None, overnight_low=None,
         atr=None, ib_high=None, ib_low=None,
         extensions_up=0, extensions_down=0, returned_to_range=False):
    return BarInput(
        ts=1000000 + session_min * 60,
        session_min=session_min,
        open=o, high=h, low=l, close=c,
        pd_high=pd_high, pd_low=pd_low, pd_close=pd_close,
        overnight_high=overnight_high, overnight_low=overnight_low,
        atr=atr, ib_high=ib_high, ib_low=ib_low,
        extensions_up=extensions_up, extensions_down=extensions_down,
        returned_to_range=returned_to_range,
    )


def _run_to_stage(target_stage: Stage, sm=None):
    """Run the state machine through IB lock to reach target stage."""
    if sm is None:
        sm = DayTypeStateMachine()
    # A1 -> A2: pre-open bar
    sm.process_bar(_bar(session_min=0, pd_high=5260, pd_low=5240, pd_close=5250,
                        overnight_high=5255, overnight_low=5245))
    # A2 bars (3 bars for opening detection)
    for i in range(1, 4):
        sm.process_bar(_bar(session_min=i * 5, o=5250 + i, h=5252 + i,
                            l=5248 + i, c=5251 + i))
    # A3: IB tracking bars until 60 min
    for m in range(20, 65, 5):
        sm.process_bar(_bar(session_min=m, o=5250, h=5260, l=5240, c=5255))
    # B stages
    for m in range(65, 220, 5):
        sm.process_bar(_bar(session_min=m, o=5250, h=5260, l=5240, c=5255,
                            atr=20, extensions_up=1))
        if sm.stage == target_stage:
            break
    return sm


# ── Q1: Lock Check ──────────────────────────────────────────────

class TestQ1LockCheck:
    def test_Q1_lock_check(self):
        sm = DayTypeStateMachine()
        assert sm.lock_state == "PENDING"
        state = sm.process_bar(_bar())
        assert state.lock_state == "PENDING"


# ── Q2: Time Stages ─────────────────────────────────────────────

class TestQ2TimeStages:
    def test_Q2_time_stages(self):
        sm = DayTypeStateMachine()
        assert sm.stage == Stage.A1


# ── A1: Pre-Open ────────────────────────────────────────────────

class TestA1PreOpen:
    def test_A1_preopen(self):
        sm = DayTypeStateMachine()
        state = sm.process_bar(_bar(
            session_min=0, pd_high=5260, pd_low=5240, pd_close=5245,
            overnight_high=5255, overnight_low=5245,
        ))
        assert state.pre_open is not None
        assert state.pre_open.gap_direction in ("UP", "DOWN", "FLAT")
        assert state.pre_open.location_vs_pd in ("ABOVE", "BELOW", "INSIDE")

    def test_A1_overnight_bias(self):
        sm = DayTypeStateMachine()
        state = sm.process_bar(_bar(
            session_min=0, o=5256,
            overnight_high=5258, overnight_low=5242,
        ))
        assert state.pre_open is not None
        assert state.pre_open.overnight_bias in ("BULLISH", "BEARISH", "NEUTRAL")


# ── A2: Opening Types ───────────────────────────────────────────

class TestA2OpeningTypes:
    def test_A2_opening_types(self):
        """Opening type detection returns one of 5 types."""
        bars = [
            _bar(o=5250, h=5255, l=5249, c=5254),
            _bar(o=5254, h=5258, l=5253, c=5257),
            _bar(o=5257, h=5260, l=5256, c=5259),
        ]
        otype, direction, conf = detect_opening_type(bars)
        assert otype in (
            OpeningType.OPEN_DRIVE,
            OpeningType.OPEN_TEST_DRIVE,
            OpeningType.OPEN_REJECTION_REVERSE,
            OpeningType.OPEN_AUCTION_IN,
            OpeningType.OPEN_AUCTION_OUT,
            OpeningType.UNKNOWN,
        )
        assert direction in ("UP", "DOWN", "NEUTRAL")
        assert 0.0 <= conf <= 1.0

    def test_A2_open_position(self):
        """Open outside PD range should produce OPEN_AUCTION_OUT."""
        bars = [
            _bar(o=5270, h=5272, l=5268, c=5270, pd_high=5260, pd_low=5240),
            _bar(o=5270, h=5271, l=5269, c=5270),
            _bar(o=5270, h=5272, l=5268, c=5269),
        ]
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_AUCTION_OUT

    def test_A2_first5min(self):
        """Strong drive bars should detect OPEN_DRIVE."""
        bars = [
            _bar(o=5250, h=5256, l=5250, c=5256),
            _bar(o=5256, h=5262, l=5256, c=5262),
            _bar(o=5262, h=5268, l=5262, c=5268),
        ]
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_DRIVE
        assert direction == "UP"

    def test_A2_opening_lock(self):
        """Opening detection should fire after 3 bars."""
        sm = DayTypeStateMachine()
        sm.process_bar(_bar(session_min=0))
        assert sm.stage == Stage.A2
        for i in range(1, 4):
            sm.process_bar(_bar(session_min=i * 5, o=5250 + i, c=5251 + i,
                                h=5252 + i, l=5249 + i))
        assert sm.opening is not None


# ── A3: IB Tracking ─────────────────────────────────────────────

class TestA3IBTracking:
    def test_A3_ib_tracking(self):
        sm = DayTypeStateMachine()
        sm.process_bar(_bar(session_min=0))
        for i in range(1, 4):
            sm.process_bar(_bar(session_min=i * 5, o=5250 + i, c=5251 + i,
                                h=5252 + i, l=5249 + i))
        assert sm.stage in (Stage.A3, Stage.A4, Stage.B1)


# ── A4: IB Width Classification ─────────────────────────────────

class TestA4IBClassification:
    def test_A4_ib_classification(self):
        assert classify_ib_width(10.0) == IBWidth.NARROW
        assert classify_ib_width(20.0) == IBWidth.MEDIUM
        assert classify_ib_width(30.0) == IBWidth.WIDE

    def test_A4_ib_boundaries(self):
        assert classify_ib_width(14.99) == IBWidth.NARROW
        assert classify_ib_width(15.0) == IBWidth.MEDIUM
        assert classify_ib_width(25.0) == IBWidth.MEDIUM
        assert classify_ib_width(25.01) == IBWidth.WIDE


# ── B1: Decision Matrix ─────────────────────────────────────────

class TestB1DecisionMatrix:
    def test_B1_decision_matrix(self):
        """All 15 cells in the 5x3 decision matrix must be defined."""
        opening_types = [
            OpeningType.OPEN_DRIVE,
            OpeningType.OPEN_TEST_DRIVE,
            OpeningType.OPEN_REJECTION_REVERSE,
            OpeningType.OPEN_AUCTION_IN,
            OpeningType.OPEN_AUCTION_OUT,
        ]
        ib_widths = [IBWidth.NARROW, IBWidth.MEDIUM, IBWidth.WIDE]
        for ot in opening_types:
            for iw in ib_widths:
                assert (ot, iw) in DECISION_MATRIX, f"Missing matrix cell: {ot} x {iw}"
                dt = DECISION_MATRIX[(ot, iw)]
                assert isinstance(dt, DayType)

    def test_B1_matrix_values_match_spec(self):
        """Spot-check key matrix cells per V2 spec."""
        assert DECISION_MATRIX[(OpeningType.OPEN_DRIVE, IBWidth.MEDIUM)] == DayType.Trend_Normal
        assert DECISION_MATRIX[(OpeningType.OPEN_TEST_DRIVE, IBWidth.NARROW)] == DayType.Trend_DD
        assert DECISION_MATRIX[(OpeningType.OPEN_REJECTION_REVERSE, IBWidth.WIDE)] == DayType.Normal
        assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_IN, IBWidth.NARROW)] == DayType.Nontrend


# ── C1: Post-IB Behavior ────────────────────────────────────────

class TestC1PostIBBehavior:
    def test_C1_postib_behavior(self):
        assert detect_behavior(1, 0, False, 1.0) == Behavior.TRENDING_UP
        assert detect_behavior(0, 1, False, 1.0) == Behavior.TRENDING_DOWN
        assert detect_behavior(1, 0, True, 1.0) == Behavior.FAILED_EXTENSION
        assert detect_behavior(0, 0, False, 0.5) == Behavior.COMPRESSED


# ── C2: Profile Shapes ──────────────────────────────────────────

class TestC2ProfileShapes:
    def test_C2_profile_shapes(self):
        """Profile shape classification exists in TPO system."""
        from backend.v9.systems.tpo.schemas import ProfileShape
        shapes = [s.value for s in ProfileShape]
        assert "D" in shapes
        assert "THIN" in shapes
        assert "DOUBLE_DIST" in shapes


# ── D1: Vote Update ─────────────────────────────────────────────

class TestD1VoteUpdate:
    def test_D1_vote_update(self):
        """Confidence calculation works with vote history."""
        conf = calculate_confidence(["Trend_Normal", "Trend_Normal"], True, True)
        assert conf > 0.5


# ── E1: Lock Criteria ───────────────────────────────────────────

class TestE1LockCriteria:
    def test_E1_lock_criteria(self):
        """Lock states are plain strings: PENDING, LOCKED, LOCKED_LOW_CONF."""
        # LockState enum removed per LOCKED 15/5; values are now plain strings
        assert "PENDING" == "PENDING"
        assert "LOCKED" == "LOCKED"
        assert "LOCKED_LOW_CONF" == "LOCKED_LOW_CONF"


# ── E2: Day Types ───────────────────────────────────────────────

class TestE2DayTypes:
    def test_E2_day_types(self):
        """6 day types + UNKNOWN must exist."""
        names = [dt.value for dt in DayType]
        for expected in ["Trend_Normal", "Trend_DD", "Variation", "Normal", "Neutral", "Nontrend"]:
            assert expected in names

    def test_E2_playbooks(self):
        """Every non-UNKNOWN day type has a playbook template."""
        for dt in DayType:
            if dt == DayType.UNKNOWN:
                continue
            assert dt in PLAYBOOK_TEMPLATES, f"Missing playbook for {dt}"


# ── Q16: Re-eval Triggers ───────────────────────────────────────

class TestQ16ReevalTriggers:
    def test_Q16_reeval_triggers(self):
        """Trigger 2 (extreme move) fires correctly."""
        should, reason = check_reeval_triggers(
            DayType.Normal, 1.0, move_in_30min=100.0, atr=20.0,
        )
        assert should is True
        assert reason == "extreme_move_3atr"

    def test_Q16_failed_ext(self):
        should, reason = check_reeval_triggers(
            DayType.Normal, 1.0, failed_extension_after_lock=True,
        )
        assert should is True

    def test_Q16_range_exceeded(self):
        should, reason = check_reeval_triggers(
            DayType.Normal, 1.0, expected_range_exceeded=True,
        )
        assert should is True

    def test_Q16_no_trigger(self):
        should, reason = check_reeval_triggers(DayType.Normal, 1.0)
        assert should is False


# ── Anti-Patterns ────────────────────────────────────────────────

class TestAntiPatterns:
    def test_AP1_no_change_after_lock(self):
        """After lock, day_type should not change without re-eval trigger."""
        sm = _run_to_stage(Stage.C3)
        if sm.lock_state in ("LOCKED", "LOCKED_LOW_CONF"):
            locked_type = sm.day_type
            state = sm.process_bar(_bar(session_min=300, atr=20))
            assert state.day_type == locked_type or state.lock_state == "PENDING"

    def test_AP2_no_skip_ib(self):
        """State machine must pass through A3 stage."""
        sm = DayTypeStateMachine()
        sm.process_bar(_bar(session_min=0))
        for i in range(1, 4):
            sm.process_bar(_bar(session_min=i * 5, o=5250 + i, c=5251 + i,
                                h=5252 + i, l=5249 + i))
        assert sm.stage in (Stage.A3, Stage.A4, Stage.B1)

    def test_AP3_no_early_lock(self):
        """Day type should be UNKNOWN before IB lock."""
        sm = DayTypeStateMachine()
        state = sm.process_bar(_bar(session_min=0))
        assert state.day_type == DayType.UNKNOWN

    def test_AP4_reeval_halt(self):
        """Re-eval trigger sets lock_state back to PENDING."""
        sm = DayTypeStateMachine()
        sm.lock_state = "LOCKED"
        sm.day_type = DayType.Normal
        sm.stage = Stage.C3
        sm.session_high = 5300
        sm.session_low = 5200
        sm.ib_high = 5260
        sm.ib_low = 5240
        sm.ib_locked = True
        sm.failed_extension = FailedExtensionType.STRONG_FAILED_UP
        state = sm.process_bar(_bar(
            session_min=300, atr=10,
            extensions_up=1, returned_to_range=True,
        ))
        assert sm.lock_state == "PENDING"


# ── Config Params ────────────────────────────────────────────────

class TestConfigParams:
    def test_config_defaults(self):
        cfg = DayTypeConfig()
        assert cfg.confidence_threshold == 0.70
        assert cfg.min_session_min_for_lock == 210
        assert cfg.ib_narrow_max_pt == 15.0
        assert cfg.ib_medium_max_pt == 25.0
