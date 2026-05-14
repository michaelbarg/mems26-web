"""Day Type Engine — 13-stage state machine (A1 → C3)."""

from __future__ import annotations
from typing import List, Optional, Dict

from .schemas import (
    BarInput, DayType, OpeningType, IBWidth, Stage, LockState,
    Behavior, RangeCategory, FailedExtensionType,
    PreOpenContext, OpeningDetection, IBClassification,
    VoteRecord, PlaybookOutput, DayTypeState, DayTypeConfig,
)
from .detector import (
    classify_ib_width, detect_opening_type, detect_behavior,
    detect_failed_extension, classify_range, calculate_confidence,
    check_reeval_triggers,
)

# ── Decision Matrix (B1) ────────────────────────────────────────────────
# Key: (OpeningType, IBWidth) → DayType
DECISION_MATRIX: Dict[tuple, DayType] = {
    # V2 spec: highest-probability day type per Opening Type × IB Width
    (OpeningType.OPEN_DRIVE, IBWidth.NARROW):   DayType.Trend_Normal,   # 60% per spec
    (OpeningType.OPEN_DRIVE, IBWidth.MEDIUM):   DayType.Trend_Normal,   # 70%
    (OpeningType.OPEN_DRIVE, IBWidth.WIDE):     DayType.Trend_Normal,   # 50%

    (OpeningType.OPEN_TEST_DRIVE, IBWidth.NARROW):  DayType.Trend_DD,   # 40% per spec
    (OpeningType.OPEN_TEST_DRIVE, IBWidth.MEDIUM):  DayType.Trend_Normal,  # 50%
    (OpeningType.OPEN_TEST_DRIVE, IBWidth.WIDE):    DayType.Variation,  # 50%

    (OpeningType.OPEN_REJECTION_REVERSE, IBWidth.NARROW):  DayType.Variation,  # 40%
    (OpeningType.OPEN_REJECTION_REVERSE, IBWidth.MEDIUM):  DayType.Variation,  # 50%
    (OpeningType.OPEN_REJECTION_REVERSE, IBWidth.WIDE):    DayType.Normal,     # 50%

    (OpeningType.OPEN_AUCTION_IN, IBWidth.NARROW):  DayType.Nontrend,   # 50%
    (OpeningType.OPEN_AUCTION_IN, IBWidth.MEDIUM):  DayType.Normal,     # 40% per spec
    (OpeningType.OPEN_AUCTION_IN, IBWidth.WIDE):    DayType.Normal,     # 50%

    (OpeningType.OPEN_AUCTION_OUT, IBWidth.NARROW):  DayType.Trend_DD,     # 50%
    (OpeningType.OPEN_AUCTION_OUT, IBWidth.MEDIUM):  DayType.Trend_DD,     # 40%
    (OpeningType.OPEN_AUCTION_OUT, IBWidth.WIDE):    DayType.Trend_Normal, # 40% per spec
}

# ── Playbook Templates (C3) ─────────────────────────────────────────────
PLAYBOOK_TEMPLATES: Dict[DayType, dict] = {
    DayType.Trend_Normal: {
        "strategy": "TREND_FOLLOW",
        "sizing": "AGGRESSIVE",
        "time_stop_min": 0,  # V3: no time stop for Trend Normal
        "key_rules": [
            "Trade with the trend direction",
            "Add on pullbacks to VWAP/EMA",
            "Hold until close or reversal signal",
            "Avoid counter-trend trades",
        ],
    },
    DayType.Trend_DD: {
        "strategy": "TREND_FOLLOW_EXTENDED",
        "sizing": "AGGRESSIVE",
        "time_stop_min": 90,  # V3: 90min for Trend DD
        "key_rules": [
            "Double-distribution day — expect two value areas",
            "Enter on initial drive, hold through IB",
            "Watch for extension beyond IB as confirmation",
            "Tighten stops only after second distribution forms",
        ],
    },
    DayType.Variation: {
        "strategy": "BREAKOUT_FADE",
        "sizing": "FULL",
        "time_stop_min": 60,  # V3: 60min for Variation
        "key_rules": [
            "Initial move may reverse — wait for confirmation",
            "Trade the reversal after failed extension",
            "Use IB extremes as key reference levels",
            "Reduce size on first entry, add on confirmation",
        ],
    },
    DayType.Normal: {
        "strategy": "RANGE_TRADE",
        "sizing": "STANDARD",
        "time_stop_min": 30,
        "key_rules": [
            "Fade moves to IB extremes",
            "Trade both sides of the range",
            "Use tight stops — limited range expected",
            "Take profits at mid-range / VWAP",
        ],
    },
    DayType.Neutral: {
        "strategy": "FADE_EXTREMES",
        "sizing": "HALF",
        "time_stop_min": 45,  # V3: 45min for Neutral
        "key_rules": [
            "Very narrow range — reduce expectations",
            "Fade extreme ticks only",
            "Keep position size small",
            "Consider sitting out if range <10 pts",
        ],
    },
    DayType.Nontrend: {
        "strategy": "SCALP_ONLY",
        "sizing": "MIN",
        "time_stop_min": 20,  # V3: 20min for Nontrend
        "key_rules": [
            "No directional bias — scalp only",
            "Quick in/out, tight stops",
            "Use limit orders, avoid market orders",
            "Accept small wins, protect capital",
        ],
    },
}


class DayTypeStateMachine:
    """13-stage state machine for day type classification.

    Stages:
        A1: Pre-Open Context
        A2: Opening Type Detection
        A3: IB Tracking (09:30-10:30 ET)
        A4: IB Lock & Width Classification
        B1: Initial Vote (decision matrix)
        B2: Post-IB Extension Tracking
        B3: Mid-day Behavior Analysis
        B4: Failed Extension Detection
        B5: Range/ATR Comparison
        B6: Vote Update (re-score)
        C1: Lock Criteria Check
        C2: Confidence Scoring
        C3: Playbook Selection
    """

    def __init__(self, config: Optional[DayTypeConfig] = None):
        self.config = config or DayTypeConfig()
        self.stage: Stage = Stage.A1
        self.day_type: DayType = DayType.UNKNOWN
        self.confidence: float = 0.0
        self.lock_state: LockState = LockState.PENDING

        # A1
        self.pre_open: Optional[PreOpenContext] = None
        # A2
        self.opening: Optional[OpeningDetection] = None
        self.opening_bars: List[BarInput] = []
        # A3-A4
        self.ib_high: float = 0.0
        self.ib_low: float = float("inf")
        self.ib_class: Optional[IBClassification] = None
        self.ib_locked: bool = False
        # B1+
        self.vote_history: List[VoteRecord] = []
        self.behavior: Behavior = Behavior.DEVELOPING
        self.range_category: RangeCategory = RangeCategory.NORMAL
        self.failed_extension: FailedExtensionType = FailedExtensionType.NONE
        self.playbook: Optional[PlaybookOutput] = None
        # Tracking
        self.session_high: float = 0.0
        self.session_low: float = float("inf")
        self.bar_count: int = 0
        self.consecutive_same_vote: int = 0

    # ── Main Entry ───────────────────────────────────────────────────────

    def process_bar(self, bar: BarInput) -> DayTypeState:
        """Process a single bar and advance the state machine.

        Returns updated DayTypeState.
        """
        self.bar_count += 1

        # Track session range
        self.session_high = max(self.session_high, bar.high)
        self.session_low = min(self.session_low, bar.low)

        prev_stage = self.stage

        # Run stages in sequence — each stage checks if it should advance
        if self.stage == Stage.A1:
            self._stage_a1(bar)
        if self.stage == Stage.A2:
            self._stage_a2(bar)
        if self.stage == Stage.A3:
            self._stage_a3(bar)
        if self.stage == Stage.A4:
            self._stage_a4(bar)
        if self.stage == Stage.B1:
            self._stage_b1(bar)
        if self.stage in (Stage.B2, Stage.B3, Stage.B4, Stage.B5, Stage.B6):
            self._stage_b2(bar)
            self._stage_b3(bar)
            self._stage_b4(bar)
            self._stage_b5(bar)
            self._stage_b6(bar)
        if self.stage == Stage.C1:
            self._stage_c1(bar)
        if self.stage == Stage.C2:
            self._stage_c2(bar)
        if self.stage == Stage.C3:
            self._stage_c3(bar)

        # If already locked, check re-eval triggers
        if self.lock_state in (LockState.LOCKED, LockState.LOCKED_LOW_CONF):
            self._check_reeval(bar)

        return self._build_state(bar)

    # ── Part A: Pre-Open & Opening ───────────────────────────────────────

    def _stage_a1(self, bar: BarInput):
        """A1: Pre-Open Context — gap, location vs PD, overnight bias."""
        gap_size = 0.0
        gap_direction = "FLAT"
        location_vs_pd = "INSIDE"
        overnight_bias = "NEUTRAL"

        if bar.pd_close is not None:
            gap_size = bar.open - bar.pd_close
            if gap_size > 2.0:
                gap_direction = "UP"
            elif gap_size < -2.0:
                gap_direction = "DOWN"

        if bar.pd_high is not None and bar.pd_low is not None:
            if bar.open > bar.pd_high:
                location_vs_pd = "ABOVE"
            elif bar.open < bar.pd_low:
                location_vs_pd = "BELOW"

        if bar.overnight_high is not None and bar.overnight_low is not None:
            on_mid = (bar.overnight_high + bar.overnight_low) / 2.0
            if bar.open > on_mid:
                overnight_bias = "BULLISH"
            elif bar.open < on_mid:
                overnight_bias = "BEARISH"

        self.pre_open = PreOpenContext(
            gap_size=gap_size,
            gap_direction=gap_direction,
            location_vs_pd=location_vs_pd,
            overnight_bias=overnight_bias,
        )
        self.stage = Stage.A2

    def _stage_a2(self, bar: BarInput):
        """A2: Opening Type Detection — accumulate first few bars."""
        self.opening_bars.append(bar)

        # Need at least 3 bars (15 min on 5-min chart) for detection
        if len(self.opening_bars) >= 3:
            otype, direction, conf = detect_opening_type(self.opening_bars)
            self.opening = OpeningDetection(
                opening_type=otype,
                drive_direction=direction,
                confidence=conf,
            )
            self.stage = Stage.A3

    def _stage_a3(self, bar: BarInput):
        """A3: IB Tracking — track IB high/low during 09:30-10:30."""
        # Use provided IB data if available, otherwise track from bars
        if bar.ib_high is not None:
            self.ib_high = max(self.ib_high, bar.ib_high)
        else:
            self.ib_high = max(self.ib_high, bar.high)

        if bar.ib_low is not None:
            self.ib_low = min(self.ib_low, bar.ib_low)
        else:
            self.ib_low = min(self.ib_low, bar.low)

        # IB closes at configured duration (default 60 min = 09:30-10:30)
        if bar.session_min >= self.config.ib_period_min:
            self.stage = Stage.A4

    def _stage_a4(self, bar: BarInput):
        """A4: IB Lock & Width Classification."""
        if self.ib_low == float("inf"):
            self.ib_low = bar.low

        ib_range = self.ib_high - self.ib_low
        ib_width = classify_ib_width(
            ib_range,
            narrow_max=self.config.ib_narrow_max_pt,
            medium_max=self.config.ib_medium_max_pt,
        )

        self.ib_class = IBClassification(
            ib_high=self.ib_high,
            ib_low=self.ib_low,
            ib_range=ib_range,
            ib_width=ib_width,
        )
        self.ib_locked = True
        self.stage = Stage.B1

    # ── Part B: Day Development ──────────────────────────────────────────

    def _stage_b1(self, bar: BarInput):
        """B1: Initial Vote — decision matrix lookup."""
        if self.opening is None or self.ib_class is None:
            return

        key = (self.opening.opening_type, self.ib_class.ib_width)
        voted_type = DECISION_MATRIX.get(key, DayType.Normal)

        vote = VoteRecord(
            day_type=voted_type,
            confidence=0.5,
            stage=Stage.B1,
            reason=f"matrix: {self.opening.opening_type.value} x {self.ib_class.ib_width.value}",
        )
        self.vote_history.append(vote)
        self.day_type = voted_type
        self.confidence = 0.5
        self.stage = Stage.B2

    def _stage_b2(self, bar: BarInput):
        """B2: Post-IB Extension Tracking."""
        if not self.ib_locked:
            return

        # Update extension counts from bar data
        if bar.high > self.ib_high:
            # Extension up detected
            pass  # counted in bar.extensions_up
        if bar.low < self.ib_low:
            # Extension down detected
            pass  # counted in bar.extensions_down

    def _stage_b3(self, bar: BarInput):
        """B3: Mid-day Behavior Analysis."""
        range_ratio = 1.0
        if bar.atr and bar.atr > 0:
            current_range = self.session_high - self.session_low
            range_ratio = current_range / bar.atr

        self.behavior = detect_behavior(
            extensions_up=bar.extensions_up,
            extensions_down=bar.extensions_down,
            returned_to_range=bar.returned_to_range,
            range_ratio=range_ratio,
        )

    def _stage_b4(self, bar: BarInput):
        """B4: Failed Extension Detection."""
        if not self.ib_locked:
            return

        self.failed_extension = detect_failed_extension(
            extensions_up=bar.extensions_up,
            extensions_down=bar.extensions_down,
            returned_to_range=bar.returned_to_range,
            current_price=bar.close,
            ib_high=self.ib_high,
            ib_low=self.ib_low,
        )

    def _stage_b5(self, bar: BarInput):
        """B5: Range/ATR Comparison."""
        current_range = self.session_high - self.session_low
        atr = bar.atr if bar.atr and bar.atr > 0 else current_range
        self.range_category = classify_range(current_range, atr)

    def _stage_b6(self, bar: BarInput):
        """B6: Vote Update — re-score candidates, update if conf_diff > 0.15."""
        if not self.vote_history:
            return

        # Determine behavior agreement
        behavior_agrees = self._behavior_agrees_with_type(self.day_type)
        range_aligned = self._range_aligns_with_type(self.day_type)

        # Get day-type types list for confidence calc
        type_history = [v.day_type.value for v in self.vote_history]
        new_conf = calculate_confidence(type_history, behavior_agrees, range_aligned)

        # Check if behavior suggests a different day type
        new_type = self._rescore_from_behavior(bar)
        if new_type != self.day_type:
            old_conf = self.confidence
            new_type_conf = calculate_confidence(
                type_history + [new_type.value],
                self._behavior_agrees_with_type(new_type),
                self._range_aligns_with_type(new_type),
            )
            # Only switch if significant improvement
            if new_type_conf - old_conf > 0.15:
                vote = VoteRecord(
                    day_type=new_type,
                    confidence=new_type_conf,
                    stage=Stage.B6,
                    reason=f"rescore: behavior={self.behavior.value}, range={self.range_category.value}",
                )
                self.vote_history.append(vote)
                self.day_type = new_type
                self.confidence = new_type_conf
            else:
                self.confidence = new_conf
        else:
            self.confidence = new_conf

        self.stage = Stage.C1

    def _rescore_from_behavior(self, bar: BarInput) -> DayType:
        """Re-derive day type from current behavior signals."""
        if self.failed_extension != FailedExtensionType.NONE:
            if self.failed_extension == FailedExtensionType.DOUBLE_FAILED:
                return DayType.Nontrend
            return DayType.Variation

        if self.behavior == Behavior.COMPRESSED:
            if self.range_category == RangeCategory.COMPRESSED:
                return DayType.Nontrend
            return DayType.Neutral

        if self.behavior in (Behavior.TRENDING_UP, Behavior.TRENDING_DOWN):
            if self.range_category in (RangeCategory.EXPANDED, RangeCategory.EXTREME):
                return DayType.Trend_DD
            return DayType.Trend_Normal

        return self.day_type

    def _behavior_agrees_with_type(self, dt: DayType) -> bool:
        """Check if current behavior is consistent with the day type."""
        if dt in (DayType.Trend_Normal, DayType.Trend_DD):
            return self.behavior in (Behavior.TRENDING_UP, Behavior.TRENDING_DOWN)
        if dt == DayType.Variation:
            return self.behavior == Behavior.FAILED_EXTENSION
        if dt in (DayType.Normal, DayType.Neutral):
            return self.behavior in (Behavior.DEVELOPING, Behavior.COMPRESSED)
        if dt == DayType.Nontrend:
            return self.behavior == Behavior.COMPRESSED
        return False

    def _range_aligns_with_type(self, dt: DayType) -> bool:
        """Check if range category is consistent with the day type."""
        if dt in (DayType.Trend_Normal, DayType.Trend_DD):
            return self.range_category in (RangeCategory.NORMAL, RangeCategory.EXPANDED, RangeCategory.EXTREME)
        if dt == DayType.Variation:
            return self.range_category in (RangeCategory.NORMAL, RangeCategory.EXPANDED)
        if dt == DayType.Normal:
            return self.range_category == RangeCategory.NORMAL
        if dt in (DayType.Neutral, DayType.Nontrend):
            return self.range_category in (RangeCategory.COMPRESSED, RangeCategory.NORMAL)
        return True

    # ── Part C: Final Lock & Output ──────────────────────────────────────

    def _stage_c1(self, bar: BarInput):
        """C1: Lock criteria check.

        Lock when:
        - confidence >= 0.70 (per spec §S2 confidence_threshold), OR
        - same vote 2x consecutive, OR
        - session_min >= 210 (13:00 ET)
        """
        if self.lock_state != LockState.PENDING:
            self.stage = Stage.C2
            return

        # Count consecutive same votes
        consec = 0
        if self.vote_history:
            last = self.vote_history[-1].day_type
            for v in reversed(self.vote_history):
                if v.day_type == last:
                    consec += 1
                else:
                    break
        self.consecutive_same_vote = consec

        conf_threshold = self.config.confidence_threshold

        should_lock = False

        if self.confidence >= conf_threshold:
            should_lock = True
        elif consec >= 2:
            should_lock = True
        elif bar.session_min >= self.config.min_session_min_for_lock:
            should_lock = True

        if should_lock:
            if self.confidence >= conf_threshold:
                self.lock_state = LockState.LOCKED
            else:
                self.lock_state = LockState.LOCKED_LOW_CONF
        else:
            # Go back to B2 for more development
            self.stage = Stage.B2
            return

        self.stage = Stage.C2

    def _stage_c2(self, bar: BarInput):
        """C2: Confidence Scoring — final confidence calc."""
        type_history = [v.day_type.value for v in self.vote_history]
        behavior_agrees = self._behavior_agrees_with_type(self.day_type)
        range_aligned = self._range_aligns_with_type(self.day_type)

        self.confidence = calculate_confidence(type_history, behavior_agrees, range_aligned)
        self.stage = Stage.C3

    def _stage_c3(self, bar: BarInput):
        """C3: Playbook Selection — map day type to tactical rules."""
        template = PLAYBOOK_TEMPLATES.get(self.day_type, PLAYBOOK_TEMPLATES[DayType.Normal])

        self.playbook = PlaybookOutput(
            day_type=self.day_type,
            strategy=template["strategy"],
            sizing=template["sizing"],
            time_stop_min=template["time_stop_min"],
            key_rules=template["key_rules"],
        )
        # Stay at C3 — locked state

    def _check_reeval(self, bar: BarInput):
        """Check re-eval triggers after lock."""
        move_30 = None  # Would need bar history for this
        atr = bar.atr

        failed_ext_post_lock = (
            self.failed_extension != FailedExtensionType.NONE
            and self.lock_state in (LockState.LOCKED, LockState.LOCKED_LOW_CONF)
        )

        # Check if range exceeds expectations
        expected_exceeded = False
        current_range = self.session_high - self.session_low
        if atr and atr > 0:
            ratio = current_range / atr
            if self.day_type in (DayType.Nontrend, DayType.Neutral) and ratio > 1.5:
                expected_exceeded = True
            if self.day_type == DayType.Normal and ratio > 2.0:
                expected_exceeded = True

        should_reeval, reason = check_reeval_triggers(
            locked_day_type=self.day_type,
            range_ratio=current_range / atr if atr and atr > 0 else 1.0,
            move_in_30min=move_30,
            atr=atr,
            failed_extension_after_lock=failed_ext_post_lock,
            expected_range_exceeded=expected_exceeded,
        )

        if should_reeval:
            self.lock_state = LockState.PENDING
            self.stage = Stage.B2
            self.playbook = None

    # ── Build Output ─────────────────────────────────────────────────────

    def _build_state(self, bar: BarInput) -> DayTypeState:
        """Build the DayTypeState output."""
        return DayTypeState(
            stage=self.stage,
            day_type=self.day_type,
            confidence=self.confidence,
            lock_state=self.lock_state,
            opening_type=self.opening.opening_type if self.opening else OpeningType.UNKNOWN,
            ib_width=self.ib_class.ib_width if self.ib_class else IBWidth.UNKNOWN,
            behavior=self.behavior,
            range_category=self.range_category,
            failed_extension=self.failed_extension,
            vote_history=list(self.vote_history),
            pre_open=self.pre_open,
            opening=self.opening,
            ib_class=self.ib_class,
            playbook=self.playbook,
            session_min=bar.session_min,
            meta={
                "bar_count": self.bar_count,
                "session_high": self.session_high,
                "session_low": self.session_low,
                "consecutive_same_vote": self.consecutive_same_vote,
            },
        )
