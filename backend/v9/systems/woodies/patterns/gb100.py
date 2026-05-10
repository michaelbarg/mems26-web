"""GB100 (Ghost Bar 100) -- Continuation pattern.

CCI-14 bar touches +/-100 line and reverses back into the trend direction.
Specifically: CCI crosses the +100 or -100 level with momentum, confirming
trend continuation. Must already be in a trend (BLUE/RED).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A4).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

PATTERN_ID = "GB100"
GROUP = "CONTINUATION"
TICK_SIZE = 0.25
STOP_TICKS = 8
TARGET1_TICKS = 12
TARGET2_TICKS = 24


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect GB100 pattern from WoodiesBar list."""
    if len(bars) < 3:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    bar = bars[-1]
    current = bar.cci_14
    prev = bars[-2].cci_14
    prev2 = bars[-3].cci_14
    trend = bar.trend_state

    # GB100 LONG: CCI crosses above +100 in a BLUE trend
    if trend == "BLUE" and current > 100 and prev <= 100 and prev2 < 100:
        entry = bar.close
        stop = entry - STOP_TICKS * TICK_SIZE
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="LONG",
            confidence=min(0.85, 0.5 + (current - 100) / 200),
            entry_price=entry,
            stop=stop,
            targets=[
                entry + TARGET1_TICKS * TICK_SIZE,
                entry + TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=len(bars) - 1,
            ts=bar.ts,
            details={"cross_level": 100, "momentum": round(current - prev, 2)},
        )

    # GB100 SHORT: CCI crosses below -100 in a RED trend
    if trend == "RED" and current < -100 and prev >= -100 and prev2 > -100:
        entry = bar.close
        stop = entry + STOP_TICKS * TICK_SIZE
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="SHORT",
            confidence=min(0.85, 0.5 + (abs(current) - 100) / 200),
            entry_price=entry,
            stop=stop,
            targets=[
                entry - TARGET1_TICKS * TICK_SIZE,
                entry - TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=len(bars) - 1,
            ts=bar.ts,
            details={"cross_level": -100, "momentum": round(current - prev, 2)},
        )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_gb100(cci_history: list, bar_index: int, ts: float,
                 trend_state: str = "GRAY", **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < 3:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]
    prev2 = cci_history[-3]

    if trend_state == "BLUE" and current > 100 and prev <= 100 and prev2 < 100:
        return PatternSignal(
            pattern="GB100", group="CONTINUATION", direction="LONG",
            confidence=min(0.85, 0.5 + (current - 100) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"cross_level": 100, "momentum": round(current - prev, 2)},
        )

    if trend_state == "RED" and current < -100 and prev >= -100 and prev2 > -100:
        return PatternSignal(
            pattern="GB100", group="CONTINUATION", direction="SHORT",
            confidence=min(0.85, 0.5 + (abs(current) - 100) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"cross_level": -100, "momentum": round(current - prev, 2)},
        )

    return None
