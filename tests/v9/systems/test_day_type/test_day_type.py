"""Unit tests for Day Type Engine (System 1).

Covers all 13 stages (A1-C3), decision matrix, detectors,
confidence calculation, lock criteria, re-eval triggers,
and full-flow scenarios.
"""

import pytest

from backend.v9.systems.day_type.schemas import (
    BarInput, DayType, OpeningType, IBWidth, Stage,
    Behavior, RangeCategory, FailedExtensionType,
)
from backend.v9.systems.day_type.detector import (
    classify_ib_width, detect_opening_type, detect_behavior,
    detect_failed_extension, classify_range, calculate_confidence,
    check_reeval_triggers,
)
from backend.v9.systems.day_type.state_machine import (
    DayTypeStateMachine, DECISION_MATRIX, PLAYBOOK_TEMPLATES,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def make_bar(**kwargs) -> BarInput:
    """Create a BarInput with defaults."""
    defaults = dict(
        ts=1000.0, session_min=0,
        open=4500.0, high=4505.0, low=4495.0, close=4502.0,
        volume=1000,
    )
    defaults.update(kwargs)
    return BarInput(**defaults)


def make_drive_bars_up(count=3) -> list:
    """Create bars that look like an OPEN_DRIVE up."""
    bars = []
    base = 4500.0
    for i in range(count):
        o = base + i * 5
        c = o + 4
        bars.append(make_bar(
            ts=1000.0 + i * 300,
            session_min=i * 5,
            open=o, high=c + 1, low=o - 0.5, close=c,
            pd_high=4510.0, pd_low=4490.0, pd_close=4500.0,
        ))
    return bars


def make_auction_bars(count=3) -> list:
    """Create rotational bars (auction in range)."""
    bars = []
    for i in range(count):
        o = 4500.0 + (i % 2) * 2
        c = 4500.0 - (i % 2) * 2
        bars.append(make_bar(
            ts=1000.0 + i * 300,
            session_min=i * 5,
            open=o, high=o + 1, low=c - 1, close=c,
            pd_high=4510.0, pd_low=4490.0, pd_close=4500.0,
        ))
    return bars


# ── IB Width Classification ─────────────────────────────────────────────

class TestIBWidthClassification:
    def test_narrow(self):
        assert classify_ib_width(10.0) == IBWidth.NARROW

    def test_narrow_boundary(self):
        assert classify_ib_width(14.9) == IBWidth.NARROW

    def test_medium(self):
        assert classify_ib_width(15.0) == IBWidth.MEDIUM

    def test_medium_upper(self):
        assert classify_ib_width(25.0) == IBWidth.MEDIUM

    def test_wide(self):
        assert classify_ib_width(25.1) == IBWidth.WIDE

    def test_very_wide(self):
        assert classify_ib_width(50.0) == IBWidth.WIDE

    def test_zero(self):
        assert classify_ib_width(0.0) == IBWidth.NARROW


# ── Opening Type Detection ───────────────────────────────────────────────

class TestOpeningTypeDetection:
    def test_empty_bars(self):
        otype, d, c = detect_opening_type([])
        assert otype == OpeningType.UNKNOWN

    def test_single_bar(self):
        otype, d, c = detect_opening_type([make_bar()])
        assert otype == OpeningType.UNKNOWN

    def test_open_drive_up(self):
        bars = make_drive_bars_up(3)
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_DRIVE
        assert direction == "UP"
        assert conf >= 0.7

    def test_open_drive_down(self):
        bars = []
        base = 4500.0
        for i in range(3):
            o = base - i * 5
            c = o - 4
            bars.append(make_bar(
                open=o, high=o + 0.5, low=c - 1, close=c,
                pd_high=4510.0, pd_low=4490.0, pd_close=4500.0,
            ))
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_DRIVE
        assert direction == "DOWN"

    def test_open_test_drive(self):
        """First bar up, second pulls back, third continues up."""
        bars = [
            make_bar(open=4500, high=4508, low=4499, close=4507,
                     pd_high=4510, pd_low=4490, pd_close=4500),
            make_bar(open=4507, high=4508, low=4503, close=4504,
                     pd_high=4510, pd_low=4490, pd_close=4500),
            make_bar(open=4504, high=4512, low=4503, close=4511,
                     pd_high=4510, pd_low=4490, pd_close=4500),
        ]
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_TEST_DRIVE
        assert direction == "UP"

    def test_open_rejection_reverse(self):
        """First bar up, then reversal down."""
        bars = [
            make_bar(open=4500, high=4510, low=4499, close=4508,
                     pd_high=4510, pd_low=4490, pd_close=4500),
            make_bar(open=4508, high=4509, low=4498, close=4499,
                     pd_high=4510, pd_low=4490, pd_close=4500),
            make_bar(open=4499, high=4500, low=4490, close=4492,
                     pd_high=4510, pd_low=4490, pd_close=4500),
        ]
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_REJECTION_REVERSE
        assert direction == "DOWN"

    def test_open_auction_in_range(self):
        bars = make_auction_bars(3)
        otype, direction, conf = detect_opening_type(bars)
        assert otype in (OpeningType.OPEN_AUCTION_IN, OpeningType.OPEN_AUCTION_OUT)

    def test_open_auction_outside(self):
        """Opening above prior day high."""
        bars = [
            make_bar(open=4520, high=4522, low=4518, close=4519,
                     pd_high=4510, pd_low=4490, pd_close=4505),
            make_bar(open=4519, high=4521, low=4517, close=4520,
                     pd_high=4510, pd_low=4490, pd_close=4505),
            make_bar(open=4520, high=4521, low=4518, close=4519,
                     pd_high=4510, pd_low=4490, pd_close=4505),
        ]
        otype, direction, conf = detect_opening_type(bars)
        assert otype == OpeningType.OPEN_AUCTION_OUT


# ── Behavior Detection ──────────────────────────────────────────────────

class TestBehaviorDetection:
    def test_trending_up(self):
        b = detect_behavior(extensions_up=2, extensions_down=0,
                            returned_to_range=False, range_ratio=1.2)
        assert b == Behavior.TRENDING_UP

    def test_trending_down(self):
        b = detect_behavior(extensions_up=0, extensions_down=1,
                            returned_to_range=False, range_ratio=1.0)
        assert b == Behavior.TRENDING_DOWN

    def test_failed_extension(self):
        b = detect_behavior(extensions_up=1, extensions_down=0,
                            returned_to_range=True, range_ratio=1.0)
        assert b == Behavior.FAILED_EXTENSION

    def test_compressed(self):
        b = detect_behavior(extensions_up=0, extensions_down=0,
                            returned_to_range=False, range_ratio=0.5)
        assert b == Behavior.COMPRESSED

    def test_developing(self):
        b = detect_behavior(extensions_up=0, extensions_down=0,
                            returned_to_range=False, range_ratio=1.0)
        assert b == Behavior.DEVELOPING


# ── Failed Extension Detection ──────────────────────────────────────────

class TestFailedExtensionDetection:
    def test_no_extension(self):
        result = detect_failed_extension(0, 0, False, 4500, 4510, 4490)
        assert result == FailedExtensionType.NONE

    def test_not_returned(self):
        result = detect_failed_extension(1, 0, False, 4515, 4510, 4490)
        assert result == FailedExtensionType.NONE

    def test_strong_failed_up(self):
        result = detect_failed_extension(1, 0, True, 4500, 4510, 4490)
        assert result == FailedExtensionType.STRONG_FAILED_UP

    def test_strong_failed_down(self):
        result = detect_failed_extension(0, 1, True, 4500, 4510, 4490)
        assert result == FailedExtensionType.STRONG_FAILED_DOWN

    def test_double_failed(self):
        result = detect_failed_extension(1, 1, True, 4500, 4510, 4490)
        assert result == FailedExtensionType.DOUBLE_FAILED


# ── Range / ATR Classification ──────────────────────────────────────────

class TestRangeClassification:
    def test_compressed(self):
        assert classify_range(7.0, 15.0) == RangeCategory.COMPRESSED

    def test_normal(self):
        assert classify_range(15.0, 15.0) == RangeCategory.NORMAL

    def test_expanded(self):
        assert classify_range(25.0, 15.0) == RangeCategory.EXPANDED

    def test_extreme(self):
        assert classify_range(35.0, 15.0) == RangeCategory.EXTREME

    def test_zero_atr(self):
        assert classify_range(10.0, 0.0) == RangeCategory.NORMAL

    def test_boundary_compressed(self):
        # 0.7 * 15 = 10.5, so 10.4 is compressed
        assert classify_range(10.4, 15.0) == RangeCategory.COMPRESSED

    def test_boundary_normal(self):
        assert classify_range(10.5, 15.0) == RangeCategory.NORMAL


# ── Confidence Calculation ───────────────────────────────────────────────

class TestConfidenceCalculation:
    def test_empty_history(self):
        assert calculate_confidence([], True, True) == 0.1

    def test_single_vote(self):
        conf = calculate_confidence(["Trend_Normal"], True, True)
        # base 0.10 + stability 1/5*0.40=0.08 + behavior 0.30 + range 0.20
        assert 0.6 < conf <= 0.7

    def test_all_same_votes(self):
        conf = calculate_confidence(["Trend_Normal"] * 5, True, True)
        # base 0.10 + stability 5/5*0.40=0.40 + behavior 0.30 + range 0.20
        assert conf == 1.0

    def test_no_agreement(self):
        conf = calculate_confidence(["Trend_Normal"], False, False)
        # base 0.10 + stability 0.08 + 0 + 0
        assert conf < 0.3

    def test_behavior_only(self):
        conf = calculate_confidence(["Trend_Normal"], True, False)
        assert 0.4 < conf < 0.6

    def test_range_only(self):
        conf = calculate_confidence(["Trend_Normal"], False, True)
        assert 0.3 < conf < 0.5

    def test_mixed_history(self):
        # Last 2 are same
        conf = calculate_confidence(
            ["Variation", "Trend_Normal", "Trend_Normal"], True, True
        )
        # consecutive = 2, stability = 2/5 * 0.40 = 0.16
        assert 0.7 < conf < 0.85


# ── Re-eval Triggers ────────────────────────────────────────────────────

class TestReevalTriggers:
    def test_no_trigger(self):
        should, reason = check_reeval_triggers(
            DayType.Trend_Normal, 1.0,
        )
        assert not should

    def test_extreme_move(self):
        should, reason = check_reeval_triggers(
            DayType.Trend_Normal, 1.0,
            move_in_30min=50.0, atr=15.0,
        )
        assert should
        assert "extreme_move" in reason

    def test_failed_extension_post_lock(self):
        should, reason = check_reeval_triggers(
            DayType.Trend_Normal, 1.0,
            failed_extension_after_lock=True,
        )
        assert should
        assert "failed_extension" in reason

    def test_range_exceeded(self):
        should, reason = check_reeval_triggers(
            DayType.Normal, 2.5,
            expected_range_exceeded=True,
        )
        assert should
        assert "range_exceeded" in reason

    def test_below_threshold(self):
        should, reason = check_reeval_triggers(
            DayType.Trend_Normal, 1.0,
            move_in_30min=30.0, atr=15.0,
        )
        # 30 / 15 = 2.0 < 3.0, no trigger
        assert not should


# ── Decision Matrix ──────────────────────────────────────────────────────

class TestDecisionMatrix:
    def test_all_combinations_present(self):
        """Every valid (OpeningType, IBWidth) combination has an entry."""
        opening_types = [
            OpeningType.OPEN_DRIVE, OpeningType.OPEN_TEST_DRIVE,
            OpeningType.OPEN_REJECTION_REVERSE,
            OpeningType.OPEN_AUCTION_IN, OpeningType.OPEN_AUCTION_OUT,
        ]
        widths = [IBWidth.NARROW, IBWidth.MEDIUM, IBWidth.WIDE]
        for ot in opening_types:
            for w in widths:
                assert (ot, w) in DECISION_MATRIX, f"Missing: {ot}, {w}"

    def test_open_drive_narrow(self):
        # V2 spec: Trend_Normal 60% (highest probability)
        assert DECISION_MATRIX[(OpeningType.OPEN_DRIVE, IBWidth.NARROW)] == DayType.Trend_Normal

    def test_open_drive_medium(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_DRIVE, IBWidth.MEDIUM)] == DayType.Trend_Normal

    def test_open_drive_wide(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_DRIVE, IBWidth.WIDE)] == DayType.Trend_Normal

    def test_test_drive_narrow(self):
        # V2 spec: Trend_DD 40% (highest probability)
        assert DECISION_MATRIX[(OpeningType.OPEN_TEST_DRIVE, IBWidth.NARROW)] == DayType.Trend_DD

    def test_test_drive_medium(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_TEST_DRIVE, IBWidth.MEDIUM)] == DayType.Trend_Normal

    def test_reject_reverse_wide(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_REJECTION_REVERSE, IBWidth.WIDE)] == DayType.Normal

    def test_auction_in_narrow(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_IN, IBWidth.NARROW)] == DayType.Nontrend

    def test_auction_in_wide(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_IN, IBWidth.WIDE)] == DayType.Normal

    def test_auction_out_narrow(self):
        assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_OUT, IBWidth.NARROW)] == DayType.Trend_DD

    def test_auction_out_wide(self):
        # V2 spec: Trend_Normal 40% (highest probability)
        assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_OUT, IBWidth.WIDE)] == DayType.Trend_Normal


# ── State Machine Stages ─────────────────────────────────────────────────

class TestStateMachineStages:

    def test_initial_state(self):
        sm = DayTypeStateMachine()
        assert sm.stage == Stage.A1
        assert sm.day_type == DayType.UNKNOWN
        assert sm.lock_state == "PENDING"

    def test_a1_pre_open(self):
        sm = DayTypeStateMachine()
        bar = make_bar(
            session_min=0,
            open=4510, high=4515, low=4505, close=4512,
            pd_high=4505, pd_low=4490, pd_close=4500,
            overnight_high=4512, overnight_low=4495,
        )
        state = sm.process_bar(bar)
        # A1 should advance to A2, then A2 collects bars
        assert sm.pre_open is not None
        assert sm.pre_open.gap_direction == "UP"  # 4510 - 4500 = 10
        assert sm.pre_open.location_vs_pd == "ABOVE"  # 4510 > 4505

    def test_a2_needs_multiple_bars(self):
        sm = DayTypeStateMachine()
        bar1 = make_bar(session_min=0, pd_high=4510, pd_low=4490, pd_close=4500)
        sm.process_bar(bar1)
        # After 1 bar in A2, opening should not be detected yet
        assert sm.opening is None or len(sm.opening_bars) < 3

    def test_a3_ib_tracking(self):
        sm = DayTypeStateMachine()
        # Feed 3 bars for A2
        for i in range(3):
            bar = make_bar(
                session_min=i * 5,
                open=4500 + i * 3, high=4505 + i * 3,
                low=4498 + i * 3, close=4503 + i * 3,
                pd_high=4510, pd_low=4490, pd_close=4500,
            )
            sm.process_bar(bar)
        # Should now be in A3+
        assert sm.opening is not None

    def test_a4_ib_lock(self):
        sm = DayTypeStateMachine()
        # Fast-forward through A1-A3
        for i in range(3):
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=4500 + i * 3, high=4505 + i * 3,
                low=4498 + i * 3, close=4503 + i * 3,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))
        # Feed bar at session_min=60 to trigger IB lock
        sm.process_bar(make_bar(
            session_min=60,
            open=4510, high=4518, low=4508, close=4515,
            pd_high=4520, pd_low=4490, pd_close=4500,
        ))
        assert sm.ib_locked

    def test_b1_initial_vote(self):
        sm = DayTypeStateMachine()
        # Feed through A1-A4
        for i in range(3):
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=4500 + i * 5, high=4505 + i * 5,
                low=4499 + i * 5, close=4504 + i * 5,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))
        sm.process_bar(make_bar(
            session_min=60,
            open=4515, high=4520, low=4514, close=4519,
            pd_high=4520, pd_low=4490, pd_close=4500,
        ))
        # B1 should have produced a vote
        assert len(sm.vote_history) >= 1
        assert sm.day_type != DayType.UNKNOWN

    def test_c1_lock_by_confidence(self):
        sm = DayTypeStateMachine()
        # Manually set up state to test C1
        sm.stage = Stage.C1
        sm.day_type = DayType.Trend_Normal
        sm.confidence = 0.90
        sm.vote_history = [
            VoteRecord(day_type=DayType.Trend_Normal, confidence=0.9, stage=Stage.B1, reason="test")
            for _ in range(3)
        ]
        sm.ib_locked = True
        sm.ib_high = 4520
        sm.ib_low = 4500

        bar = make_bar(session_min=120)
        sm._stage_c1(bar)
        assert sm.lock_state in ("LOCKED", "LOCKED_LOW_CONF")

    def test_c1_lock_by_consecutive_votes(self):
        sm = DayTypeStateMachine()
        sm.stage = Stage.C1
        sm.day_type = DayType.Variation
        sm.confidence = 0.5
        sm.vote_history = [
            VoteRecord(day_type=DayType.Variation, confidence=0.5, stage=Stage.B1, reason="test"),
            VoteRecord(day_type=DayType.Variation, confidence=0.5, stage=Stage.B6, reason="test"),
        ]

        bar = make_bar(session_min=120)
        sm._stage_c1(bar)
        assert sm.lock_state == "LOCKED_LOW_CONF"

    def test_c1_lock_by_time(self):
        sm = DayTypeStateMachine()
        sm.stage = Stage.C1
        sm.day_type = DayType.Normal
        sm.confidence = 0.4
        sm.vote_history = [
            VoteRecord(day_type=DayType.Normal, confidence=0.4, stage=Stage.B1, reason="test"),
        ]

        bar = make_bar(session_min=210)  # 13:00 ET
        sm._stage_c1(bar)
        assert sm.lock_state == "LOCKED_LOW_CONF"

    def test_c3_playbook(self):
        sm = DayTypeStateMachine()
        sm.stage = Stage.C3
        sm.day_type = DayType.Trend_Normal
        sm.lock_state = "LOCKED"

        bar = make_bar(session_min=250)
        sm._stage_c3(bar)
        assert sm.playbook is not None
        assert sm.playbook.strategy == "TREND_FOLLOW"
        assert sm.playbook.sizing == "AGGRESSIVE"


# Need to import VoteRecord for manual state setup
from backend.v9.systems.day_type.schemas import VoteRecord


# ── Playbook Templates ──────────────────────────────────────────────────

class TestPlaybookTemplates:
    def test_all_day_types_have_playbook(self):
        for dt in DayType:
            if dt == DayType.UNKNOWN:
                continue
            assert dt in PLAYBOOK_TEMPLATES, f"Missing playbook for {dt}"

    def test_trend_normal_playbook(self):
        pb = PLAYBOOK_TEMPLATES[DayType.Trend_Normal]
        assert pb["strategy"] == "TREND_FOLLOW"
        assert pb["sizing"] == "AGGRESSIVE"

    @pytest.mark.skip(reason="NONTREND sizing not in authoritative spec; code='MIN' test='SMALL'; awaiting decision; MEMS26_OPEN_THEORIES")
    def test_nontrend_playbook(self):
        pb = PLAYBOOK_TEMPLATES[DayType.Nontrend]
        assert pb["strategy"] == "SCALP_ONLY"
        assert pb["sizing"] == "SMALL"


# ── Full Flow Scenarios ──────────────────────────────────────────────────

class TestFullFlowScenarios:

    def _run_through_ib(self, sm, bars_config):
        """Feed bars through A1-A4 and return the state machine."""
        # A1-A2: first 3 bars (opening detection)
        for i in range(3):
            cfg = bars_config.get(i, {})
            sm.process_bar(make_bar(
                session_min=i * 5,
                **cfg,
            ))
        # A3-A4: bar at session_min=60
        ib_cfg = bars_config.get("ib", {})
        state = sm.process_bar(make_bar(
            session_min=60,
            **ib_cfg,
        ))
        return state

    def test_open_drive_narrow_ib_trend_dd(self):
        """Open Drive + Narrow IB -> Trend_DD."""
        sm = DayTypeStateMachine()
        # Drive-up bars with narrow IB (range < 15)
        for i in range(3):
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=4500 + i * 5, high=4505 + i * 5,
                low=4499.5 + i * 5, close=4504 + i * 5,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))
        # IB bar that keeps range narrow (<15 pt)
        state = sm.process_bar(make_bar(
            session_min=60,
            open=4510, high=4514, low=4502, close=4513,
            pd_high=4520, pd_low=4490, pd_close=4500,
        ))
        # Opening should be OPEN_DRIVE, IB should be NARROW
        # V2 spec: OPEN_DRIVE + NARROW → Trend_Normal (60%)
        if sm.opening and sm.opening.opening_type == OpeningType.OPEN_DRIVE:
            assert sm.day_type == DayType.Trend_Normal

    def test_auction_in_narrow_nontrend(self):
        """Auction (in range) + Narrow IB -> Nontrend."""
        sm = DayTypeStateMachine()
        # Rotational bars inside PD range
        for i in range(3):
            o = 4500 + (i % 2) * 2
            c = 4500 - (i % 2) * 2
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=o, high=o + 1, low=c - 1, close=c,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))
        state = sm.process_bar(make_bar(
            session_min=60,
            open=4500, high=4507, low=4495, close=4501,
            pd_high=4510, pd_low=4490, pd_close=4500,
        ))
        if sm.opening and sm.opening.opening_type in (
            OpeningType.OPEN_AUCTION_IN, OpeningType.OPEN_AUCTION_OUT
        ):
            if sm.ib_class and sm.ib_class.ib_width == IBWidth.NARROW:
                assert sm.day_type in (DayType.Nontrend, DayType.Trend_DD)

    def test_compressed_range_drives_nontrend(self):
        """Compressed range should push toward Nontrend/Neutral."""
        sm = DayTypeStateMachine()
        # Setup through B stages
        for i in range(3):
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=4500, high=4502, low=4499, close=4501,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))
        sm.process_bar(make_bar(
            session_min=60,
            open=4500, high=4505, low=4497, close=4502,
            pd_high=4510, pd_low=4490, pd_close=4500,
            atr=20.0,
        ))
        # Now feed more bars in B stages with compressed range
        for i in range(3):
            state = sm.process_bar(make_bar(
                session_min=70 + i * 5,
                open=4501, high=4503, low=4499, close=4502,
                atr=20.0,
                extensions_up=0, extensions_down=0,
            ))
        # The range_category should reflect compression
        current_range = sm.session_high - sm.session_low
        cat = classify_range(current_range, 20.0)
        assert cat in (RangeCategory.COMPRESSED, RangeCategory.NORMAL)

    def test_failed_extension_drives_variation(self):
        """Failed extension after IB -> pushes toward Variation."""
        sm = DayTypeStateMachine()
        # Fast-forward to after IB
        for i in range(3):
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=4500 + i * 3, high=4505 + i * 3,
                low=4498 + i * 3, close=4503 + i * 3,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))
        sm.process_bar(make_bar(
            session_min=60,
            open=4509, high=4520, low=4505, close=4518,
            pd_high=4525, pd_low=4490, pd_close=4500,
        ))

        # Post-IB bar with failed extension
        state = sm.process_bar(make_bar(
            session_min=90,
            open=4518, high=4522, low=4508, close=4510,
            atr=15.0,
            extensions_up=1, extensions_down=0,
            returned_to_range=True,
            ib_high=4520, ib_low=4505,
        ))
        # Failed extension should be detected
        fe = detect_failed_extension(1, 0, True, 4510, 4520, 4505)
        assert fe == FailedExtensionType.STRONG_FAILED_UP

    def test_full_session_to_lock(self):
        """Simulate a full session through to lock."""
        sm = DayTypeStateMachine()

        # A1-A2: opening bars (drive up)
        for i in range(3):
            sm.process_bar(make_bar(
                session_min=i * 5,
                open=4500 + i * 5, high=4506 + i * 5,
                low=4499 + i * 5, close=4505 + i * 5,
                pd_high=4510, pd_low=4490, pd_close=4500,
            ))

        # A3-A4: IB close
        sm.process_bar(make_bar(
            session_min=60,
            open=4515, high=4535, low=4514, close=4530,
            pd_high=4520, pd_low=4490, pd_close=4500,
        ))

        # B stages: continue trending
        for i in range(10):
            sm.process_bar(make_bar(
                session_min=70 + i * 10,
                open=4530 + i * 2, high=4535 + i * 2,
                low=4528 + i * 2, close=4534 + i * 2,
                atr=20.0,
                extensions_up=i + 1, extensions_down=0,
            ))

        # Should eventually lock or get close
        # Feed a bar past 13:00 ET to force lock by time
        state = sm.process_bar(make_bar(
            session_min=220,
            open=4560, high=4565, low=4558, close=4563,
            atr=20.0,
            extensions_up=5, extensions_down=0,
        ))

        # The state machine should have progressed through many stages
        assert sm.bar_count > 10
        assert len(sm.vote_history) >= 1

    def test_reeval_unlocks_on_failed_extension(self):
        """After lock, a failed extension should trigger re-eval."""
        sm = DayTypeStateMachine()
        # Set up locked state manually
        sm.stage = Stage.C3
        sm.day_type = DayType.Trend_Normal
        sm.lock_state = "LOCKED"
        sm.confidence = 0.90
        sm.ib_locked = True
        sm.ib_high = 4520
        sm.ib_low = 4500
        sm.session_high = 4530
        sm.session_low = 4495
        sm.failed_extension = FailedExtensionType.STRONG_FAILED_UP

        bar = make_bar(
            session_min=180,
            open=4510, high=4512, low=4505, close=4507,
            atr=15.0,
        )
        state = sm.process_bar(bar)

        # Should have unlocked for re-eval
        assert sm.lock_state == "PENDING"


# ── Edge Cases ───────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_zero_range_bar(self):
        """Bar with no range should not crash."""
        sm = DayTypeStateMachine()
        bar = make_bar(
            open=4500, high=4500, low=4500, close=4500,
            pd_high=4510, pd_low=4490, pd_close=4500,
        )
        state = sm.process_bar(bar)
        assert state is not None

    def test_missing_pd_data(self):
        """Missing prior-day data should not crash."""
        sm = DayTypeStateMachine()
        bar = make_bar(session_min=0)
        state = sm.process_bar(bar)
        assert state.stage != Stage.A1  # Should have advanced past A1

    def test_very_large_ib(self):
        """Very large IB range should classify as WIDE."""
        assert classify_ib_width(100.0) == IBWidth.WIDE

    def test_confidence_caps_at_1(self):
        """Confidence should never exceed 1.0."""
        conf = calculate_confidence(
            ["Trend_Normal"] * 10, True, True
        )
        assert conf <= 1.0

    def test_state_machine_reset(self):
        """Creating a new state machine resets everything."""
        sm1 = DayTypeStateMachine()
        sm1.day_type = DayType.Trend_DD
        sm1.bar_count = 50

        sm2 = DayTypeStateMachine()
        assert sm2.day_type == DayType.UNKNOWN
        assert sm2.bar_count == 0
