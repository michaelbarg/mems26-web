"""TT (Turbo Trend) -- Continuation pattern.

TCCI (CCI-6) hooks in the trend direction while CCI-14 is trending.
Specifically: TCCI touches or crosses CCI-14 during a trend, then
bounces back in the trend direction. Confirms trend strength.

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A3).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

PATTERN_ID = "TT"
GROUP = "CONTINUATION"
TICK_SIZE = 0.25
STOP_TICKS = 8
TARGET1_TICKS = 12
TARGET2_TICKS = 20


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect TT pattern from WoodiesBar list."""
    if len(bars) < 3:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    bar = bars[-1]
    bar_prev = bars[-2]
    bar_prev2 = bars[-3]

    cci14 = bar.cci_14
    cci14_prev = bar_prev.cci_14
    cci6 = bar.cci_6_tcci
    cci6_prev = bar_prev.cci_6_tcci
    cci6_prev2 = bar_prev2.cci_6_tcci
    trend = bar.trend_state

    # TT LONG: trend BLUE, TCCI touched CCI-14 from above then bounced
    if trend == "BLUE" and cci14 > 0:
        touched = (cci6_prev <= cci14_prev + 5)
        bounced = (cci6 > cci14 + 5) and (cci6 > cci6_prev)
        was_above = (cci6_prev2 > bar_prev2.cci_14 + 10)
        if touched and bounced and was_above:
            entry = bar.close
            stop = entry - STOP_TICKS * TICK_SIZE
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="LONG",
                confidence=0.7,
                entry_price=entry,
                stop=stop,
                targets=[
                    entry + TARGET1_TICKS * TICK_SIZE,
                    entry + TARGET2_TICKS * TICK_SIZE,
                ],
                group=GROUP,
                cci_at_signal=cci14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

    # TT SHORT: trend RED, TCCI touched CCI-14 from below then dropped
    if trend == "RED" and cci14 < 0:
        touched = (cci6_prev >= cci14_prev - 5)
        bounced = (cci6 < cci14 - 5) and (cci6 < cci6_prev)
        was_below = (cci6_prev2 < bar_prev2.cci_14 - 10)
        if touched and bounced and was_below:
            entry = bar.close
            stop = entry + STOP_TICKS * TICK_SIZE
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="SHORT",
                confidence=0.7,
                entry_price=entry,
                stop=stop,
                targets=[
                    entry - TARGET1_TICKS * TICK_SIZE,
                    entry - TARGET2_TICKS * TICK_SIZE,
                ],
                group=GROUP,
                cci_at_signal=cci14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_tt(cci_history: list, bar_index: int, ts: float,
              cci6_history: list = None, trend_state: str = "GRAY",
              **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    if cci6_history is None or len(cci6_history) < 3 or len(cci_history) < 3:
        return None

    cci14 = cci_history[-1]
    cci14_prev = cci_history[-2]
    cci6 = cci6_history[-1]
    cci6_prev = cci6_history[-2]
    cci6_prev2 = cci6_history[-3]

    if trend_state == "BLUE" and cci14 > 0:
        touched = (cci6_prev <= cci14_prev + 5)
        bounced = (cci6 > cci14 + 5) and (cci6 > cci6_prev)
        was_above = (cci6_prev2 > cci14_prev + 10)
        if touched and bounced and was_above:
            return PatternSignal(
                pattern="TT", group="CONTINUATION", direction="LONG",
                confidence=0.7,
                cci_at_signal=cci14, bar_index=bar_index, ts=ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

    if trend_state == "RED" and cci14 < 0:
        touched = (cci6_prev >= cci14_prev - 5)
        bounced = (cci6 < cci14 - 5) and (cci6 < cci6_prev)
        was_below = (cci6_prev2 < cci14_prev - 10)
        if touched and bounced and was_below:
            return PatternSignal(
                pattern="TT", group="CONTINUATION", direction="SHORT",
                confidence=0.7,
                cci_at_signal=cci14, bar_index=bar_index, ts=ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

    return None
