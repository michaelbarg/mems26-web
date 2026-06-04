"""Day Type Engine — 13-stage state machine (A1 -> C3).

V9 Hybrid Enhancement (LOCKED 15/5 option D):
- Backward-compatible process_bar() preserved for 3 production callers
- New V9 methods: on_trigger(), to_classification(), update_cvd_state(),
  update_max_tpo_row_width()
- New output: DayTypeClassification dataclass (13 fields, no status enum)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Dict

from .schemas import (
    BarInput, DayType, OpeningType, IBWidth, Stage,
    Behavior, RangeCategory, FailedExtensionType,
    PreOpenContext, OpeningDetection, IBClassification,
    VoteRecord, PlaybookOutput, DayTypeState, DayTypeConfig,
)

# Internal lock state constants (LockState enum removed per LOCKED 15/5)
_LOCK_PENDING = "PENDING"
_LOCK_LOCKED = "LOCKED"
_LOCK_LOW_CONF = "LOCKED_LOW_CONF"
from .detector import (
    classify_ib_width, detect_opening_type, detect_opening_type_cvd,
    classify_ib_width_atr, cap_confidence_staged,
    detect_behavior,
    detect_failed_extension, classify_range, calculate_confidence,
    check_reeval_triggers,
)
from .triggers import TriggerEvent, TriggerType
from .zohar_rules import ZoharRulesEngine, RuleVerdict
from .extensions import ExtensionTracker
from .decision_matrix import DECISION_MATRIX  # Single source (extracted in 3a-S5 C3)

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
    DayType.Neutral_Extreme: {
        "strategy": "FADE_EXTREMES",
        "sizing": "HALF",
        "time_stop_min": 45,
        "key_rules": [
            "Open at VA edge — wider expected range",
            "Fade extreme ticks back toward POC",
            "45min window before Type C exit (DD path)",
            "Half size · 1 contract",
        ],
    },
    DayType.Neutral_Center: {
        "strategy": "FADE_EXTREMES",
        "sizing": "HALF",
        "time_stop_min": 30,
        "key_rules": [
            "Open inside VA — narrower expected range",
            "Fade extremes · expect rotation around POC",
            "30min window before Type C exit",
            "Half size · 1 contract",
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


# ── V9 Enhancement: DayTypeClassification + Lookup (LOCKED 15/5 option D) ──

@dataclass(frozen=True)
class DayTypeClassification:
    """V9 output type (per LOCKED 15/5 spec).

    No status enum, no locked_at. Uses last_updated_at.
    This is the NEW output for V9 consumers (3a-S4 DB, 3a-S5 API).
    Existing DayTypeState retained for backward compat with 3 callers.
    """
    timestamp: datetime
    day_type: DayType
    probability: float
    directional_certainty: str
    trading_confidence: str
    ib_h: Optional[float]
    ib_l: Optional[float]
    ib_width: Optional[float]
    ib_width_class: Optional[str]
    opening_type: Optional[str]
    last_updated_at: datetime
    reasoning_notes: str
    active_zohar_rules: List[str] = field(default_factory=list)


# LOCKED: Zohar slide deck (per-type tables, pp.2-7)
DAY_TYPE_LOOKUP: Dict[DayType, Dict[str, str]] = {
    DayType.Trend_Normal: {"directional": "HIGH",   "trading": "LOW"},
    DayType.Trend_DD:     {"directional": "MEDIUM", "trading": "MEDIUM"},
    DayType.Variation:    {"directional": "MEDIUM", "trading": "HIGH"},
    DayType.Normal:       {"directional": "LOW",    "trading": "HIGH"},
    DayType.Neutral_Extreme: {"directional": "LOW", "trading": "HIGH"},
    DayType.Neutral_Center:  {"directional": "LOW", "trading": "HIGH"},
    DayType.Nontrend:     {"directional": "LOW",    "trading": "MEDIUM"},
}

# Reverse lookup: lowercase day_type string -> DayType enum
_DT_FROM_LOWER: Dict[str, DayType] = {
    dt.value.lower(): dt for dt in DayType if dt != DayType.UNKNOWN
}


class DayTypeStateMachine:
    """13-stage state machine for day type classification.

    V9 Hybrid Enhancement (LOCKED 15/5 option D):
    - Backward compatible process_bar() preserved for 3 callers
    - New V9 methods: on_trigger(), to_classification(), update_cvd_state(),
      update_max_tpo_row_width()

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

    Rule adjustment factors (LOCKED, 3a-S3 Section C5):
        DELTA_BOOST_NEUTRAL = 0.2
        TIMING_BIAS_BOOST = 0.05
        WIDTH_INVALIDATE = 0.0
    """

    # LOCKED constants (3a-S3 Section C5)
    DELTA_BOOST_NEUTRAL: float = 0.2   # Boost to NEUTRAL prob on both-side extension
    TIMING_BIAS_BOOST: float = 0.05    # Boost from timing bias rule
    WIDTH_INVALIDATE: float = 0.0      # Set TREND_NORMAL prob to 0 on wide TPO

    def __init__(
        self,
        config: Optional[DayTypeConfig] = None,
        zohar_engine: Optional[ZoharRulesEngine] = None,
        extension_tracker: Optional[ExtensionTracker] = None,
        decision_matrix: Optional[object] = None,
        prev_day_summary: Optional[Dict[str, Any]] = None,
    ):
        self.config = config or DayTypeConfig()
        self.stage: Stage = Stage.A1
        self.day_type: DayType = DayType.UNKNOWN
        self.confidence: float = 0.0
        self.lock_state: str = _LOCK_PENDING

        # A1
        self.pre_open: Optional[PreOpenContext] = None
        self.pd_context_status: str = "PENDING"
        self.pd_degraded_reason: Optional[str] = None
        self.missing_pd_fields: List[str] = []
        # Stream 1.5 · prev_day context for NeuE/NeuC classification (D-091.Q1)
        _pds = prev_day_summary or {}
        self.prev_vah: Optional[float] = _pds.get("vah")
        self.prev_val: Optional[float] = _pds.get("val")
        self.session_date: Optional[str] = _pds.get("session_date")
        self.session_open_price: Optional[float] = None  # captured in _stage_a1
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
        # Tracking — overall session (all bars)
        self.session_high: float = 0.0
        self.session_low: float = float("inf")
        # Tracking — Globex range (pre-RTH bars, is_rth=False)
        self.globex_h: float = 0.0
        self.globex_l: float = float("inf")
        # Tracking — RTH session range (RTH bars only, is_rth=True)
        self.rth_session_h: float = 0.0
        self.rth_session_l: float = float("inf")
        self.bar_count: int = 0
        self.consecutive_same_vote: int = 0
        self._last_bar_ts: Optional[float] = None  # dedup: skip duplicate pushes

        # V9 optional collaborators (Hybrid, LOCKED 15/5 option D)
        self._zohar_engine: Optional[ZoharRulesEngine] = zohar_engine
        self._extension_tracker: Optional[ExtensionTracker] = extension_tracker
        self._decision_matrix: Optional[object] = decision_matrix
        self._latest_cvd_state: Optional[str] = None
        self.meta: Dict[str, Any] = {}  # shadow/calibration metadata (CVD opening, etc.)
        # S1_IB_WIDTH_ATR: rolling ATR-14 from 5-min bar ranges
        self._bar_ranges: List[float] = []  # last 14 bar ranges (high-low)
        self._last_atr_daily: Optional[float] = None
        self._max_tpo_row_width: int = 0
        self._active_zohar_rules: List[str] = []
        self._last_state: Optional[DayTypeState] = None

    def reset(self) -> None:
        """Reset all mutable state to __init__ defaults.

        Called by SessionBoundaryManager at 18:00 ET rollover.
        After reset(), to_classification() returns None until new RTH data arrives.
        """
        self.stage = Stage.A1
        self.day_type = DayType.UNKNOWN
        self.confidence = 0.0
        self.lock_state = _LOCK_PENDING
        # A1
        self.pre_open = None
        self.pd_context_status = "PENDING"
        self.pd_degraded_reason = None
        self.missing_pd_fields = []
        self.session_open_price = None
        # A2
        self.opening = None
        self.opening_bars = []
        # A3-A4
        self.ib_high = 0.0
        self.ib_low = float("inf")
        self.ib_class = None
        self.ib_locked = False
        # B1+
        self.vote_history = []
        self.behavior = Behavior.DEVELOPING
        self.range_category = RangeCategory.NORMAL
        self.failed_extension = FailedExtensionType.NONE
        self.playbook = None
        # Tracking
        self.session_high = 0.0
        self.session_low = float("inf")
        self.globex_h = 0.0
        self.globex_l = float("inf")
        self.rth_session_h = 0.0
        self.rth_session_l = float("inf")
        self.bar_count = 0
        self.consecutive_same_vote = 0
        # V9 collaborator state
        self._latest_cvd_state = None
        self._max_tpo_row_width = 0
        self._active_zohar_rules = []
        self._last_state = None
        self._last_bar_ts = None

    # ── Main Entry ───────────────────────────────────────────────────────

    def process_bar(self, bar: BarInput) -> DayTypeState:
        """Process a single bar and advance the state machine.

        Returns updated DayTypeState.
        """
        self.bar_count += 1

        # S1_IB_WIDTH_ATR: update rolling ATR-14 from bar ranges
        bar_range = bar.high - bar.low
        if bar_range > 0:
            self._bar_ranges.append(bar_range)
            if len(self._bar_ranges) > 14:
                self._bar_ranges = self._bar_ranges[-14:]
            if len(self._bar_ranges) >= 5:
                self._last_atr_daily = sum(self._bar_ranges) / len(self._bar_ranges)

        # Track session range (all bars) + split Globex vs RTH
        self.session_high = max(self.session_high, bar.high)
        self.session_low = min(self.session_low, bar.low)
        if bar.is_rth:
            self.rth_session_h = max(self.rth_session_h, bar.high)
            self.rth_session_l = min(self.rth_session_l, bar.low)
        else:
            self.globex_h = max(self.globex_h, bar.high)
            self.globex_l = min(self.globex_l, bar.low)

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
        if self.lock_state in (_LOCK_LOCKED, _LOCK_LOW_CONF):
            self._check_reeval(bar)

        state = self._build_state(bar)
        self._last_state = state  # V9: cache for on_trigger/to_classification
        return state

    # ── Part A: Pre-Open & Opening ───────────────────────────────────────

    def _stage_a1(self, bar: BarInput):
        """A1: Pre-Open Context — gap, location vs PD, overnight bias."""
        if self.session_open_price is None:
            self.session_open_price = bar.open
        missing_pd = [
            field_name
            for field_name in ("pd_high", "pd_low", "pd_close")
            if getattr(bar, field_name) is None
        ]

        if missing_pd:
            overnight_bias = "UNKNOWN"
            if bar.overnight_high is not None and bar.overnight_low is not None:
                on_mid = (bar.overnight_high + bar.overnight_low) / 2.0
                if bar.open > on_mid:
                    overnight_bias = "BULLISH"
                elif bar.open < on_mid:
                    overnight_bias = "BEARISH"
                else:
                    overnight_bias = "NEUTRAL"

            self.pd_context_status = "DEGRADED"
            self.pd_degraded_reason = "missing_previous_day_context"
            self.missing_pd_fields = missing_pd
            self.pre_open = PreOpenContext(
                gap_size=None,
                gap_direction="UNKNOWN",
                gap_magnitude="UNKNOWN",
                location_vs_pd="UNKNOWN",
                overnight_bias=overnight_bias,
                pd_context_status=self.pd_context_status,
                degraded_reason=self.pd_degraded_reason,
                missing_pd_fields=list(missing_pd),
            )
            self.stage = Stage.A1
            self.day_type = DayType.UNKNOWN
            self.confidence = 0.0
            self.lock_state = _LOCK_PENDING
            return

        gap_size = 0.0
        gap_direction = "FLAT"
        gap_magnitude = "SMALL_GAP"
        location_vs_pd = "INSIDE"
        overnight_bias = "NEUTRAL"
        self.pd_context_status = "OK"
        self.pd_degraded_reason = None
        self.missing_pd_fields = []

        if bar.pd_close is not None:
            gap_size = bar.open - bar.pd_close
            if gap_size > 2.0:
                gap_direction = "UP"
            elif gap_size < -2.0:
                gap_direction = "DOWN"
            _atr_gap = bar.atr if bar.atr and bar.atr > 0 else self._last_atr_daily
            if _atr_gap and _atr_gap > 0:
                ratio = abs(gap_size) / _atr_gap
                if ratio >= 1.0:
                    gap_magnitude = "LARGE_GAP"
                elif ratio >= 0.3:
                    gap_magnitude = "MEDIUM_GAP"

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
            gap_magnitude=gap_magnitude,
            location_vs_pd=location_vs_pd,
            overnight_bias=overnight_bias,
            pd_context_status=self.pd_context_status,
            degraded_reason=self.pd_degraded_reason,
            missing_pd_fields=list(self.missing_pd_fields),
        )
        self.stage = Stage.A2

    def _stage_a2(self, bar: BarInput):
        """A2: Opening Type Detection — accumulate first few RTH bars only."""
        if not bar.is_rth:
            return  # Globex bars must not count toward opening type detection
        self.opening_bars.append(bar)

        # Need at least 3 bars (15 min on 5-min chart) for detection
        if len(self.opening_bars) >= 3:
            # D-094: CVD-enhanced detection (flag S1_CVD_OPENING)
            # footprint_deltas from bar delta field (source-of-truth when available)
            # S1_CVD_OPENING: compute per-bar delta proxy from OHLCV.
            # sign(close-open) × volume approximates buy/sell imbalance.
            # Full footprint deltas are preferred when available from DLL.
            _fp_deltas = []
            for _b in self.opening_bars:
                _dir = 1 if _b.close >= _b.open else -1
                _fp_deltas.append(_dir * _b.volume)
            otype, direction, conf, _shadow = detect_opening_type_cvd(
                self.opening_bars, footprint_deltas=_fp_deltas,
            )
            self.opening = OpeningDetection(
                opening_type=otype,
                drive_direction=direction,
                confidence=conf,
            )
            if _shadow:
                self.meta["cvd_opening_shadow"] = _shadow
            self.stage = Stage.A3

    def _stage_a3(self, bar: BarInput):
        """A3: IB Tracking — accept Sierra Study ID:6 IB only.

        Pre-LIVE cleanup (2026-05-28): removed bars-derived IB fallback
        (`max(self.ib_high, bar.high)`). When `bar.ib_high/ib_low` are None
        (Sierra reports `ib.found=false`, e.g. pre-RTH or Study not loaded),
        we keep the running values untouched and stay in stage A3 until
        Sierra supplies IB. This guarantees DB IB == Sierra Study IB.
        """
        if not bar.is_rth:
            return  # Pre-RTH (Globex) bars must not contaminate the RTH IB
        if bar.ib_high is not None:
            self.ib_high = max(self.ib_high, bar.ib_high)
        if bar.ib_low is not None:
            self.ib_low = min(self.ib_low, bar.ib_low)

        # IB closes at configured duration (default 60 min = 09:30-10:30)
        if bar.session_min >= self.config.ib_period_min:
            self.stage = Stage.A4

    def _stage_a4(self, bar: BarInput):
        """A4: IB Lock & Width Classification.

        Pre-LIVE source-of-truth cleanup (2026-05-28):
        - Removed `if self.ib_low == inf: self.ib_low = bar.low` fallback,
          which polluted v9_day_type_history with `ib_high=0.0
          ib_low=<bar.low>` whenever Sierra Study 6 went silent before A3
          had captured both sides. The bar.low fallback IS bar synthesis
          and violates the source-of-truth rule.
        - When Sierra IB is incomplete (self.ib_high==0 OR
          self.ib_low==inf) we STAY in A4 and re-poll Sierra on the next
          bar via `_stage_a3` — which is invoked again because we don't
          advance the stage. This is a loud failure (classification halts)
          instead of silent garbage (wrong IB written to DB).
        """
        ib_high_set = self.ib_high not in (0.0, None) and self.ib_high > 0
        ib_low_set = self.ib_low != float("inf") and self.ib_low is not None
        if not (ib_high_set and ib_low_set):
            # Sierra IB never arrived. Drop back to A3 so the next bar can
            # re-attempt picking up Sierra's locked IB. Classification
            # cannot proceed without authoritative IB.
            self.stage = Stage.A3
            return

        ib_range = self.ib_high - self.ib_low
        # D-094: ATR-relative IB width when flag ON (uses daily ATR from bar.atr)
        _atr_daily = getattr(self, '_last_atr_daily', None)
        ib_width = classify_ib_width_atr(
            ib_range,
            atr_daily=_atr_daily,
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
        matrix_cell = DECISION_MATRIX.get(key, DayType.Normal)
        voted_type = matrix_cell.get("top1", DayType.Normal) if isinstance(matrix_cell, dict) else matrix_cell

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
        _atr_b3 = bar.atr if bar.atr and bar.atr > 0 else self._last_atr_daily
        if _atr_b3 and _atr_b3 > 0:
            current_range = self.session_high - self.session_low
            range_ratio = current_range / _atr_b3

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
        atr = bar.atr if bar.atr and bar.atr > 0 else (self._last_atr_daily if self._last_atr_daily and self._last_atr_daily > 0 else current_range)
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
            from backend.v9.systems.day_type.neutral_classifier import classify_neutral_subtype
            return classify_neutral_subtype(
                session_open_price=self.session_open_price,
                prev_vah=self.prev_vah,
                prev_val=self.prev_val,
                session_date=self.session_date,
            )

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
        if dt in (DayType.Normal, DayType.Neutral_Extreme, DayType.Neutral_Center, DayType.Neutral):
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
        if dt in (DayType.Neutral_Extreme, DayType.Neutral_Center, DayType.Neutral, DayType.Nontrend):
            return self.range_category in (RangeCategory.COMPRESSED, RangeCategory.NORMAL)
        return True

    # ── Part C: Final Lock & Output ──────────────────────────────────────

    def _stage_c1(self, bar: BarInput):
        """C1: Lock criteria check.

        Lock when:
        - confidence >= 0.85 (config.confidence_threshold · ConfidenceThreshold default), OR
        - same vote 2x consecutive, OR
        - session_min >= 210 (13:00 ET)
        """
        if self.lock_state != _LOCK_PENDING:
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
                self.lock_state = _LOCK_LOCKED
            else:
                self.lock_state = _LOCK_LOW_CONF
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
        # S1_DAYTYPE_STAGING: cap confidence by session stage (flag-gated)
        self.confidence = cap_confidence_staged(self.confidence, bar.session_min)
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
        atr = bar.atr if bar.atr and bar.atr > 0 else self._last_atr_daily

        failed_ext_post_lock = (
            self.failed_extension != FailedExtensionType.NONE
            and self.lock_state in (_LOCK_LOCKED, _LOCK_LOW_CONF)
        )

        # Check if range exceeds expectations
        expected_exceeded = False
        current_range = self.session_high - self.session_low
        if atr and atr > 0:
            ratio = current_range / atr
            if self.day_type in (DayType.Nontrend, DayType.Neutral_Extreme, DayType.Neutral_Center, DayType.Neutral) and ratio > 1.5:
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
            self.lock_state = _LOCK_PENDING
            self.stage = Stage.B2
            self.playbook = None

    # ── Build Output ─────────────────────────────────────────────────────

    def _build_state(self, bar: BarInput) -> DayTypeState:
        """Build the DayTypeState output."""
        ib_h_live = self.ib_high if self.ib_high > 0 else None
        ib_l_live = self.ib_low if self.ib_low < float("inf") else None
        ib_range_live = round(ib_h_live - ib_l_live, 2) if (ib_h_live is not None and ib_l_live is not None) else None
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
            profile_shape="UNKNOWN",
            meta={
                "bar_count": self.bar_count,
                "session_high": self.session_high,
                "session_low": self.session_low if self.session_low < float("inf") else None,
                "consecutive_same_vote": self.consecutive_same_vote,
                "profile_shape": "UNKNOWN",
                "pd_context_status": self.pd_context_status,
                "pd_degraded_reason": self.pd_degraded_reason,
                "missing_pd_fields": list(self.missing_pd_fields),
                # IB live tracking (available from first A3 bar, before A4 lock)
                "ib_high_live": ib_h_live,
                "ib_low_live": ib_l_live,
                "ib_range_live": ib_range_live,
                "ib_locked": self.ib_locked,
                # Separate Globex and RTH session ranges
                "globex_h": self.globex_h if self.globex_h > 0 else None,
                "globex_l": self.globex_l if self.globex_l < float("inf") else None,
                "rth_session_h": self.rth_session_h if self.rth_session_h > 0 else None,
                "rth_session_l": self.rth_session_l if self.rth_session_l < float("inf") else None,
            },
        )

    # ── V9 Enhancement Methods (Hybrid, LOCKED 15/5 option D) ───────────

    def get_current(self) -> dict:
        """Snapshot for cross-context capture at trade fire time (RCA-2)."""
        if self._last_state is None:
            return {"running": False}
        s = self._last_state
        return {
            "running": True,
            "day_type": s.day_type.value,
            "confidence": round(s.confidence, 3),
            "lock_state": s.lock_state,
            "stage": s.stage.value if s.stage else None,
            "opening_type": s.opening_type.value if s.opening_type else None,
            "ib_width": s.ib_width.value if s.ib_width else None,
            "ib_high_live": s.meta.get("ib_high_live"),
            "ib_low_live": s.meta.get("ib_low_live"),
            "ib_locked": s.meta.get("ib_locked", False),
        }

    def update_cvd_state(self, cvd_state_value: str) -> None:
        """V9: called when CVDContextClassifier publishes new state."""
        self._latest_cvd_state = cvd_state_value

    def update_max_tpo_row_width(self, max_width: int) -> None:
        """V9: called from TPO computation for Zohar Width Rule."""
        self._max_tpo_row_width = max_width

    def on_trigger(self, trigger: TriggerEvent) -> Optional[DayTypeClassification]:
        """V9 entry point for trigger-based consumers.

        Internally reads cached state from last process_bar() call,
        applies Zohar rules if collaborators are present, and returns
        DayTypeClassification (13 fields, no status enum).

        Returns None if process_bar() hasn't been called yet or
        if opening_type/ib_width are still UNKNOWN.
        """
        if self._last_state is None:
            return None
        if self._last_state.opening_type == OpeningType.UNKNOWN:
            return None
        if self._last_state.ib_width == IBWidth.UNKNOWN:
            return None

        now = datetime.fromtimestamp(trigger.ts, tz=timezone.utc)
        active_rules: List[str] = []
        reasoning_parts: List[str] = []

        # Get base probabilities from decision matrix or fallback
        if self._decision_matrix is not None and hasattr(self._decision_matrix, 'get_probabilities'):
            probabilities: Dict[str, float] = dict(
                self._decision_matrix.get_probabilities(
                    opening_type=self._last_state.opening_type.value,
                    width_class=self._last_state.ib_width.value,
                )
            )
        else:
            # Fallback: single winner from last process_bar
            winner_key = self._last_state.day_type.value.lower()
            probabilities = {dt.value.lower(): 0.0 for dt in DayType if dt != DayType.UNKNOWN}
            probabilities[winner_key] = 1.0

        # Apply Zohar rules if engine + extension tracker present
        if self._zohar_engine is not None:
            # Delta rule: both-side extension -> boost NEUTRAL
            if self._extension_tracker is not None:
                delta_verdict = self._zohar_engine.evaluate_delta(
                    extensions_up=self._extension_tracker.extensions_up,
                    extensions_down=self._extension_tracker.extensions_down,
                )
                if delta_verdict == RuleVerdict.DOWNGRADE:
                    active_rules.append("delta")
                    reasoning_parts.append("delta: both-side extension")
                    current_neutral = probabilities.get("neutral", 0.0)
                    probabilities["neutral"] = min(1.0, current_neutral + self.DELTA_BOOST_NEUTRAL)

            # Width rule: wide TPO row -> invalidate TREND_NORMAL
            width_verdict = self._zohar_engine.evaluate_width(
                max_tpo_count=self._max_tpo_row_width,
            )
            if width_verdict == RuleVerdict.DOWNGRADE:
                active_rules.append("width")
                reasoning_parts.append(
                    f"width: max_tpo_row={self._max_tpo_row_width}"
                    f" > {self._zohar_engine.WIDTH_MAX_LETTERS}"
                )
                probabilities["trend_normal"] = self.WIDTH_INVALIDATE

            # Timing bias rule
            has_reversal = self.behavior == Behavior.FAILED_EXTENSION
            has_trend_cont = self.behavior in (Behavior.TRENDING_UP, Behavior.TRENDING_DOWN)
            timing_suggestion = self._zohar_engine.evaluate_timing_bias(
                current_time=now.time(),
                has_reversal=has_reversal,
                has_trend_continuation=has_trend_cont,
            )
            if timing_suggestion is not None:
                active_rules.append("timing_bias")
                suggested_key = timing_suggestion.value.lower()
                current = probabilities.get(suggested_key, 0.0)
                probabilities[suggested_key] = min(1.0, current + self.TIMING_BIAS_BOOST)
                reasoning_parts.append(f"timing: bias toward {suggested_key}")

        # Pick winner: probability = max()
        winning_type_str = max(probabilities, key=lambda k: probabilities[k])
        winning_type = _DT_FROM_LOWER.get(winning_type_str, DayType.UNKNOWN)
        max_prob = probabilities[winning_type_str]
        lookup = DAY_TYPE_LOOKUP.get(winning_type, {"directional": "LOW", "trading": "LOW"})

        self._active_zohar_rules = active_rules

        # Build reasoning
        reasoning = (
            f"Opening={self._last_state.opening_type.value}"
            f" Width={self._last_state.ib_width.value}"
            f" winner={winning_type_str} ({max_prob:.2f})"
        )
        if reasoning_parts:
            reasoning += " " + " ".join(reasoning_parts)
        if self._latest_cvd_state is not None:
            reasoning += f" CVD={self._latest_cvd_state}"

        # IB values from ib_class (IBClassification)
        ib_h = self._last_state.ib_class.ib_high if self._last_state.ib_class else None
        ib_l = self._last_state.ib_class.ib_low if self._last_state.ib_class else None
        ib_w = self._last_state.ib_class.ib_range if self._last_state.ib_class else None

        return DayTypeClassification(
            timestamp=now,
            day_type=winning_type,
            probability=max_prob,
            directional_certainty=lookup["directional"],
            trading_confidence=lookup["trading"],
            ib_h=ib_h,
            ib_l=ib_l,
            ib_width=ib_w,
            ib_width_class=self._last_state.ib_width.value,
            opening_type=self._last_state.opening_type.value,
            last_updated_at=now,
            reasoning_notes=reasoning,
            active_zohar_rules=active_rules,
        )

    def to_classification(self) -> Optional[DayTypeClassification]:
        """V9: convert current internal state to DayTypeClassification.

        Used by 3a-S4 (DB consumer) and 3a-S5 (API).
        Returns None if process_bar() hasn't been called yet or
        if state is still UNKNOWN.
        """
        if self._last_state is None:
            return None
        if self._last_state.opening_type == OpeningType.UNKNOWN:
            return None
        if self._last_state.ib_width == IBWidth.UNKNOWN:
            # During A3: IB is still developing — return partial classification
            # with live values so the cockpit can display IB size in real time.
            ib_h_live = self._last_state.meta.get("ib_high_live")
            ib_l_live = self._last_state.meta.get("ib_low_live")
            ib_r_live = self._last_state.meta.get("ib_range_live")
            if ib_h_live is None or ib_l_live is None:
                return None  # IB tracking not started yet (pre-A3)
            now = datetime.now(tz=timezone.utc)
            opening = self._last_state.opening_type
            return DayTypeClassification(
                timestamp=now,
                day_type=DayType.UNKNOWN,
                probability=0.0,
                directional_certainty="LOW",
                trading_confidence="LOW",
                ib_h=ib_h_live,
                ib_l=ib_l_live,
                ib_width=ib_r_live,
                ib_width_class="DEVELOPING",
                opening_type=opening.value if opening != OpeningType.UNKNOWN else None,
                last_updated_at=now,
                reasoning_notes=(
                    f"IB developing: h={ib_h_live} l={ib_l_live}"
                    f" range={ib_r_live} session_min={self._last_state.session_min}"
                ),
                active_zohar_rules=[],
            )

        winning_type = self._last_state.day_type
        if winning_type == DayType.UNKNOWN:
            return None

        lookup = DAY_TYPE_LOOKUP.get(winning_type, {"directional": "LOW", "trading": "LOW"})
        now = datetime.now(tz=timezone.utc)

        ib_h = self._last_state.ib_class.ib_high if self._last_state.ib_class else None
        ib_l = self._last_state.ib_class.ib_low if self._last_state.ib_class else None
        ib_w = self._last_state.ib_class.ib_range if self._last_state.ib_class else None

        return DayTypeClassification(
            timestamp=now,
            day_type=winning_type,
            probability=self._last_state.confidence,
            directional_certainty=lookup["directional"],
            trading_confidence=lookup["trading"],
            ib_h=ib_h,
            ib_l=ib_l,
            ib_width=ib_w,
            ib_width_class=self._last_state.ib_width.value,
            opening_type=self._last_state.opening_type.value,
            last_updated_at=now,
            reasoning_notes=(
                f"Converted from DayTypeState"
                f" stage={self._last_state.stage.value}"
            ),
            active_zohar_rules=self._active_zohar_rules,
        )
