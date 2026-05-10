"""TLB (Trend Line Break) — Continuation pattern.

CCI breaks through a trendline drawn along recent CCI swing points.
Simplified: detect when CCI breaks a linear regression slope of recent swings.
"""

from typing import Optional
from backend.v9.systems.woodies.schemas import PatternSignal

LOOKBACK = 10


def detect_tlb(cci_history: list, bar_index: int, ts: float,
               **kwargs) -> Optional[PatternSignal]:
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]
    current = window[-1]
    prev = window[-2]

    # Find slope of CCI over the window (linear regression)
    sum_x = sum_y = sum_xy = sum_x2 = 0.0
    for i in range(LOOKBACK):
        sum_x += i
        sum_y += window[i]
        sum_xy += i * window[i]
        sum_x2 += i * i
    denom = LOOKBACK * sum_x2 - sum_x * sum_x
    if abs(denom) < 0.001:
        return None
    slope = (LOOKBACK * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / LOOKBACK

    # Predicted value at the last bar (on the trendline)
    predicted = intercept + slope * (LOOKBACK - 1)

    # TLB UP: downward trendline broken upward
    if slope < -2 and current > predicted + 10 and current > prev:
        return PatternSignal(
            pattern="TLB", group="CONTINUATION", direction="LONG",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    # TLB DOWN: upward trendline broken downward
    if slope > 2 and current < predicted - 10 and current < prev:
        return PatternSignal(
            pattern="TLB", group="CONTINUATION", direction="SHORT",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    return None
