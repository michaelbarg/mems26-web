"""TLB (Trend Line Break) -- Continuation pattern.

CCI breaks through a trendline drawn along recent CCI swing points.
Detection: linear regression on CCI over lookback window; break when
current CCI deviates significantly from projected trendline.

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A2).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

LOOKBACK = 10
PATTERN_ID = "TLB"
GROUP = "CONTINUATION"
TICK_SIZE = 0.25
STOP_TICKS = 10
TARGET1_TICKS = 15
TARGET2_TICKS = 30


def _linreg_slope(values: List[float]) -> tuple:
    """Linear regression slope and intercept over values."""
    n = len(values)
    sum_x = sum_y = sum_xy = sum_x2 = 0.0
    for i in range(n):
        sum_x += i
        sum_y += values[i]
        sum_xy += i * values[i]
        sum_x2 += i * i
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 0.001:
        return 0.0, 0.0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect TLB pattern from WoodiesBar list."""
    n = len(bars)
    if n < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    window = [b.cci_14 for b in bars[-LOOKBACK:]]
    current = window[-1]
    prev = window[-2]
    bar = bars[-1]

    slope, intercept = _linreg_slope(window)
    predicted = intercept + slope * (LOOKBACK - 1)

    # TLB UP: downward trendline broken upward
    if slope < -2 and current > predicted + 10 and current > prev:
        entry = bar.close
        stop = entry - STOP_TICKS * TICK_SIZE
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="LONG",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            entry_price=entry,
            stop=stop,
            targets=[
                entry + TARGET1_TICKS * TICK_SIZE,
                entry + TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=n - 1,
            ts=bar.ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    # TLB DOWN: upward trendline broken downward
    if slope > 2 and current < predicted - 10 and current < prev:
        entry = bar.close
        stop = entry + STOP_TICKS * TICK_SIZE
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="SHORT",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            entry_price=entry,
            stop=stop,
            targets=[
                entry - TARGET1_TICKS * TICK_SIZE,
                entry - TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=n - 1,
            ts=bar.ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_tlb(cci_history: list, bar_index: int, ts: float,
               **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]
    current = window[-1]
    prev = window[-2]

    slope, intercept = _linreg_slope(window)
    predicted = intercept + slope * (LOOKBACK - 1)

    if slope < -2 and current > predicted + 10 and current > prev:
        return PatternSignal(
            pattern="TLB", group="CONTINUATION", direction="LONG",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    if slope > 2 and current < predicted - 10 and current < prev:
        return PatternSignal(
            pattern="TLB", group="CONTINUATION", direction="SHORT",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    return None
