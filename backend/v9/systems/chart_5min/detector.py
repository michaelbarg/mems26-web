"""Tiered Pattern Detector — runs patterns per V3.1/V3.3 spec.

Flow:
1. Receive new bar
2. Check time → first hour or day type mode
3. Run eligible patterns per tier
4. Compute chop score
5. Validate pattern structure (single check)
6. Matrix lookup → trade management
7. Confluence count → classification
8. Emit setup package
"""

from __future__ import annotations
import logging
from typing import List, Optional

from backend.v9.systems.chart_5min.models import (
    Bar, PatternResult, ALL_TIERS, FIRST_HOUR_ELIGIBILITY,
)
from backend.v9.systems.chart_5min.patterns import PATTERN_REGISTRY
from backend.v9.systems.chart_5min.matrix import (
    lookup_matrix, classify_opportunity, sizing_for_classification, TradeManagement,
)
from backend.v9.systems.chart_5min.schemas import (
    PatternDetection, ChopScore, ConfluenceBreakdown, SetupPackage, SystemState,
)

logger = logging.getLogger("v9.chart_5min")


class Chart5MinDetector:
    """Main detector engine for System 2."""

    def __init__(self):
        self._bars: List[Bar] = []
        self._bar_count: int = 0
        self._day_type: Optional[str] = None
        self._day_type_locked: bool = False
        self._opening_type: Optional[str] = None
        self._killzone_blocked: bool = False
        self._killzone_quality: Optional[str] = None
        self._woodies_trend: Optional[str] = None
        self._reference_lines: List[float] = []
        self._last_setup: Optional[SetupPackage] = None
        self._active_patterns: List[PatternDetection] = []

    @property
    def is_first_hour(self) -> bool:
        return not self._day_type_locked and self._bar_count <= 12

    def get_state(self) -> SystemState:
        return SystemState(
            bar_count=self._bar_count,
            is_first_hour=self.is_first_hour,
            day_type=self._day_type,
            day_type_locked=self._day_type_locked,
            opening_type=self._opening_type,
            active_patterns=self._active_patterns,
            chop=self._compute_chop(),
            last_setup=self._last_setup,
            killzone_blocked=self._killzone_blocked,
        )

    # ─── External inputs ────────────────────────────────────

    def set_day_type(self, day_type: str, locked: bool = False):
        self._day_type = day_type
        self._day_type_locked = locked

    def set_opening_type(self, opening_type: str):
        self._opening_type = opening_type

    def set_killzone(self, blocked: bool, quality: Optional[str] = None):
        self._killzone_blocked = blocked
        self._killzone_quality = quality

    def set_woodies_trend(self, trend: str):
        self._woodies_trend = trend

    def set_reference_lines(self, lines: List[float]):
        self._reference_lines = lines

    def _validate_test_phase(self, pattern: PatternDetection) -> bool:
        """V3.0 Step 8 placeholder: validate pullback/test phase."""
        return True

    # ─── Main processing ────────────────────────────────────

    def process_bar(self, bar: Bar) -> Optional[SetupPackage]:
        """Process a new 5-min bar. Returns SetupPackage if a setup is found."""
        self._bars.append(bar)
        self._bar_count += 1

        # Keep buffer bounded
        if len(self._bars) > 600:
            self._bars = self._bars[-500:]

        # Q2: Killzone blocked?
        if self._killzone_blocked:
            return None

        # Nontrend/Neutral early exit (limited scalps only — still detect)
        # Run detection regardless, matrix handles the filtering

        # Determine eligible patterns
        detections = self._run_detection()

        if not detections:
            self._active_patterns = []
            return None

        # Pick best detection
        best = max(detections, key=lambda d: d.completion * d.confidence)

        # Q5: Pattern structure intact?
        if not self._validate_structure(best):
            return None

        # Matrix lookup
        mgmt = lookup_matrix(
            day_type=self._day_type or "NORMAL",
            pattern_id=best.pattern_id,
            direction=best.direction,
            is_first_hour=self.is_first_hour,
            opening_type=self._opening_type,
        )

        if mgmt.blocked:
            return None

        # Q6: Confluence count
        chop = self._compute_chop()
        confluence = self._compute_confluence(best, chop)

        # Classification
        classification = classify_opportunity(confluence.total, self.is_first_hour)
        sizing = sizing_for_classification(classification)

        # Override sizing from matrix if more restrictive
        sizing_rank = {"MIN": 0, "HALF": 1, "FULL": 2}
        if sizing_rank.get(mgmt.sizing, 0) < sizing_rank.get(sizing, 0):
            sizing = mgmt.sizing

        setup = SetupPackage(
            ts=str(bar.ts),
            pattern=PatternDetection(
                pattern_id=best.pattern_id,
                group=best.group,
                tier=self._tier_for_pattern(best.pattern_id),
                direction=best.direction,
                completion=best.completion,
                bar_count=best.bar_count,
                method=best.method,
                potential_r=best.potential_r,
                key_levels=best.key_levels,
            ),
            day_type=self._day_type or "UNKNOWN",
            opening_type=self._opening_type,
            matrix_cell=f"{self._day_type or 'UNKNOWN'} x {best.pattern_id} x {best.direction}",
            direction=best.direction,
            entry_zone=best.key_levels.get("entry_zone"),
            stop_zone=best.key_levels.get("stop"),
            t1={"reason": mgmt.t1_reason, "contracts": mgmt.t1_contracts} if mgmt.t1_reason else None,
            t2={"reason": mgmt.t2_reason, "contracts": mgmt.t2_contracts} if mgmt.t2_reason else None,
            t3={"reason": mgmt.t3_reason, "contracts": mgmt.t3_contracts} if mgmt.t3_reason else None,
            time_stop_min=mgmt.time_stop_min,
            sizing=sizing,
            classification=classification,
            confluence=confluence,
            chop=chop,
            is_first_hour=self.is_first_hour,
        )

        self._last_setup = setup
        self._active_patterns = [setup.pattern]
        return setup

    # ─── Detection ──────────────────────────────────────────

    def _run_detection(self) -> List[PatternResult]:
        """Run pattern detectors according to tier and eligibility rules."""
        results = []

        if self.is_first_hour:
            eligible = self._first_hour_eligible()
        else:
            eligible = self._tier_eligible()

        for pattern_id in eligible:
            detector = PATTERN_REGISTRY.get(pattern_id)
            if not detector:
                continue

            tier = self._tier_for_pattern(pattern_id)
            tier_config = ALL_TIERS[tier - 1] if 1 <= tier <= 4 else ALL_TIERS[0]

            # Tier 3/4 run every N bars
            if tier_config.run_every_n_bars > 1:
                if self._bar_count % tier_config.run_every_n_bars != 0:
                    continue

            # Slice buffer to tier window
            buf = self._bars[-tier_config.buffer_size:]

            result = detector(buf)
            if result.detected:
                results.append(result)

        return results

    def _first_hour_eligible(self) -> List[str]:
        """Get eligible patterns for first hour based on bar count (V3.3)."""
        bc = self._bar_count
        if bc < 4:
            return []
        if bc < 6:
            return FIRST_HOUR_ELIGIBILITY[4]
        if bc < 10:
            return FIRST_HOUR_ELIGIBILITY[6]
        return FIRST_HOUR_ELIGIBILITY[10]

    def _tier_eligible(self) -> List[str]:
        """Get all eligible patterns across all tiers."""
        eligible = []
        for tier in ALL_TIERS:
            if len(self._bars) >= tier.buffer_size // 2:
                eligible.extend(tier.patterns)
        return list(set(eligible))

    @staticmethod
    def _tier_for_pattern(pattern_id: str) -> int:
        for tier in ALL_TIERS:
            if pattern_id in tier.patterns:
                return tier.tier
        return 1

    # ─── Validation (V3.1: single check) ────────────────────

    def _validate_structure(self, pattern: PatternResult) -> bool:
        """Q5: Pattern Structure Intact? Single check per V3.1."""
        if not self._bars:
            return False

        last = self._bars[-1]

        if pattern.pattern_id in ("reactive_buyer",):
            # POC not broken below belly
            stop = pattern.key_levels.get("support", 0)
            return last.c > stop

        if pattern.pattern_id in ("reactive_seller",):
            stop = pattern.key_levels.get("resistance", float("inf"))
            return last.c < stop

        if pattern.pattern_id in ("initiative_buyer",):
            return last.c > last.poc_price or last.poc_price == 0

        if pattern.pattern_id in ("initiative_seller",):
            return last.c < last.poc_price or last.poc_price == 0

        # Chart patterns: boundary not broken
        stop = pattern.key_levels.get("stop")
        if stop is None:
            return True
        if pattern.direction == "LONG":
            return last.c > stop
        return last.c < stop

    # ─── Chop Detection (V3.1) ──────────────────────────────

    def _compute_chop(self) -> ChopScore:
        """Compute chop score from 5 metrics (V3.1)."""
        if len(self._bars) < 6:
            return ChopScore()

        micro = self._chop_window(self._bars[-15:]) if len(self._bars) >= 15 else 0.0
        session = self._chop_window(self._bars[-50:]) if len(self._bars) >= 50 else 0.0
        macro = self._chop_window(self._bars[-120:]) if len(self._bars) >= 120 else 0.0
        composite = micro * 0.5 + session * 0.3 + macro * 0.2

        return ChopScore(micro=micro, session=session, macro=macro, composite=composite)

    @staticmethod
    def _chop_window(bars: List[Bar]) -> float:
        """Compute chop score for a window of bars. Returns 0-100."""
        if len(bars) < 3:
            return 0.0

        # 1. Range compression: current range / average
        ranges = [b.range for b in bars]
        avg_r = sum(ranges) / len(ranges)
        current_r = ranges[-1]
        range_comp = min(100, (1 - current_r / avg_r) * 100) if avg_r > 0 else 50

        # 2. Direction reversals
        reversals = 0
        for i in range(1, len(bars)):
            if (bars[i].is_bullish and bars[i - 1].is_bearish) or \
               (bars[i].is_bearish and bars[i - 1].is_bullish):
                reversals += 1
        reversal_pct = reversals / (len(bars) - 1) * 100

        # 3. Body size variance
        bodies = [b.body for b in bars]
        avg_body = sum(bodies) / len(bodies) if bodies else 1
        variance = sum((b - avg_body) ** 2 for b in bodies) / len(bodies) if bodies else 0
        body_var_score = min(100, variance / (avg_body ** 2) * 100) if avg_body > 0 else 50

        # Composite: weighted average
        score = range_comp * 0.3 + reversal_pct * 0.4 + body_var_score * 0.3
        return min(100, max(0, score))

    # ─── Confluence (V3.1) ──────────────────────────────────

    def _compute_confluence(self, pattern: PatternResult, chop: ChopScore) -> ConfluenceBreakdown:
        """Q6: Confluence Count per V3.1."""
        c = ConfluenceBreakdown(base=1)

        # +1 Day Type aligned
        if self._day_type:
            if self._is_day_type_aligned(pattern):
                c.day_type_aligned = 1

        # +1 Killzone HIGH
        if self._killzone_quality in ("NY_PRIME", "OPEN_IB", "PM_PRIME"):
            c.killzone_high = 1

        # +1 Reference Lines (price near a reference level)
        if self._reference_lines and self._bars:
            last_c = self._bars[-1].c
            for level in self._reference_lines:
                if abs(last_c - level) / level < 0.002:  # within 0.2%
                    c.reference_lines = 1
                    break

        # +1 Woodies CCI aligned
        if self._woodies_trend:
            if (pattern.direction == "LONG" and self._woodies_trend == "BLUE") or \
               (pattern.direction == "SHORT" and self._woodies_trend == "RED"):
                c.woodies_cci = 1

        # +2 Tier 3/4 confirmation
        tier = self._tier_for_pattern(pattern.pattern_id)
        if tier >= 3:
            c.tier_34_confirms = 2

        # -1 Chop penalty
        if chop.composite > 60:
            c.chop_penalty = -1

        c.total = (
            c.base + c.day_type_aligned + c.killzone_high +
            c.reference_lines + c.woodies_cci + c.tier_34_confirms +
            c.chop_penalty
        )
        c.total = max(0, c.total)
        return c

    def _is_day_type_aligned(self, pattern: PatternResult) -> bool:
        """Check if Day Type supports this pattern direction."""
        dt = self._day_type
        pid = pattern.pattern_id
        d = pattern.direction

        # Trend Normal/DD + Initiative continuation = aligned
        if dt in ("TREND_NORMAL", "TREND_DD"):
            if "initiative" in pid and d in ("LONG", "SHORT"):
                return True
            if pid in ("bull_flag", "bull_pennant") and d == "LONG":
                return True
            if pid in ("bear_flag", "bear_pennant") and d == "SHORT":
                return True

        # Variation + Reactive = aligned
        if dt == "VARIATION":
            if "reactive" in pid:
                return True
            if pid in ("double_bottom", "double_top"):
                return True

        return False
