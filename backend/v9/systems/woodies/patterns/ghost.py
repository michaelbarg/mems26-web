"""GHOST -- Reversal pattern (CCI divergence).

CCI forms a head-and-shoulders pattern (three pushes, middle highest/lowest).
Bearish GHOST: CCI makes three peaks, middle highest (head-and-shoulders).
Bullish GHOST: CCI makes three troughs, middle lowest (inverse H&S).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B2).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

LOOKBACK = 20
PATTERN_ID = "GHOST"
GROUP = "REVERSAL"
TICK_SIZE = 0.25
STOP_TICKS = 12
TARGET1_TICKS = 16
TARGET2_TICKS = 32


def _find_extremes(values: List[float], kind: str = "high") -> list:
    """Find local extremes. kind='high' or 'low'."""
    extremes = []
    for i in range(2, len(values) - 1):
        if kind == "high":
            if values[i] > values[i - 1] and values[i] > values[i - 2] and values[i] > values[i + 1]:
                extremes.append((i, values[i]))
        else:
            if values[i] < values[i - 1] and values[i] < values[i - 2] and values[i] < values[i + 1]:
                extremes.append((i, values[i]))
    return extremes


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect GHOST pattern from WoodiesBar list."""
    if len(bars) < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    window = [b.cci_14 for b in bars[-LOOKBACK:]]
    bar = bars[-1]

    # Bearish GHOST: three CCI peaks, middle is highest
    peaks = _find_extremes(window, "high")
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if p2[1] > p1[1] and p2[1] > p3[1] and p3[1] < p1[1]:
            current = window[-1]
            if current < p3[1]:
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
                    cci_at_signal=current,
                    bar_index=len(bars) - 1,
                    ts=bar.ts,
                    details={"left": round(p1[1], 2), "head": round(p2[1], 2),
                             "right": round(p3[1], 2)},
                )

    # Bullish GHOST: three CCI troughs, middle is lowest
    troughs = _find_extremes(window, "low")
    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[1] < t3[1] and t3[1] > t1[1]:
            current = window[-1]
            if current > t3[1]:
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
                    cci_at_signal=current,
                    bar_index=len(bars) - 1,
                    ts=bar.ts,
                    details={"left": round(t1[1], 2), "head": round(t2[1], 2),
                             "right": round(t3[1], 2)},
                )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_ghost(cci_history: list, bar_index: int, ts: float,
                 **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]

    peaks = _find_extremes(window, "high")
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if p2[1] > p1[1] and p2[1] > p3[1] and p3[1] < p1[1]:
            current = window[-1]
            if current < p3[1]:
                return PatternSignal(
                    pattern="GHOST", group="REVERSAL", direction="SHORT",
                    confidence=0.7,
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"left": round(p1[1], 2), "head": round(p2[1], 2),
                             "right": round(p3[1], 2)},
                )

    troughs = _find_extremes(window, "low")
    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[1] < t3[1] and t3[1] > t1[1]:
            current = window[-1]
            if current > t3[1]:
                return PatternSignal(
                    pattern="GHOST", group="REVERSAL", direction="LONG",
                    confidence=0.7,
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"left": round(t1[1], 2), "head": round(t2[1], 2),
                             "right": round(t3[1], 2)},
                )

    return None
