"""ZLR (Zero Line Reject) -- Continuation pattern.

ZLR UP:  CCI was above +100 -> pulls back toward zero (stays > -100) -> bounces up.
ZLR DOWN: CCI was below -100 -> pulls back toward zero (stays < +100) -> drops.
Lookback: 12 bars (matching DLL).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A1).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

LOOKBACK = 12
PATTERN_ID = "ZLR"
GROUP = "CONTINUATION"
# MES tick size for stop/target computation
TICK_SIZE = 0.25
STOP_TICKS = 8
TARGET1_TICKS = 12
TARGET2_TICKS = 24


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect ZLR pattern from WoodiesBar list.

    Returns PatternResult with detected=True if a ZLR is found.
    """
    n = len(bars)
    if n < LOOKBACK + 1:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    cci_history = [b.cci_14 for b in bars]
    current = cci_history[-1]
    prev = cci_history[-2]
    bar = bars[-1]

    # ZLR UP: find most recent bar where CCI > +100 within lookback
    for i in range(n - 2, max(n - LOOKBACK - 2, -1), -1):
        if cci_history[i] > 100:
            pulled = any(
                -50 <= cci_history[j] <= 100
                for j in range(i + 1, n - 1)
            )
            if pulled and current > prev and 0 < current < 200:
                bars_since = n - 1 - i
                entry = bar.close
                stop = entry - STOP_TICKS * TICK_SIZE
                return PatternResult(
                    detected=True,
                    pattern_id=PATTERN_ID,
                    direction="LONG",
                    confidence=min(0.9, 0.5 + current / 400),
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
                    details={"bars_since_extreme": bars_since},
                )
            break

    # ZLR DOWN: find most recent bar where CCI < -100 within lookback
    for i in range(n - 2, max(n - LOOKBACK - 2, -1), -1):
        if cci_history[i] < -100:
            pulled = any(
                -100 <= cci_history[j] <= 50
                for j in range(i + 1, n - 1)
            )
            if pulled and current < prev and -200 < current < 0:
                bars_since = n - 1 - i
                entry = bar.close
                stop = entry + STOP_TICKS * TICK_SIZE
                return PatternResult(
                    detected=True,
                    pattern_id=PATTERN_ID,
                    direction="SHORT",
                    confidence=min(0.9, 0.5 + abs(current) / 400),
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
                    details={"bars_since_extreme": bars_since},
                )
            break

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_zlr(cci_history: list, bar_index: int, ts: float,
               **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK + 1:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]

    # ZLR UP
    for i in range(n - 2, max(n - LOOKBACK - 1, -1), -1):
        if cci_history[i] > 100:
            bars_since = n - 1 - i
            pulled = any(
                -50 <= cci_history[j] <= 100
                for j in range(i + 1, n - 1)
            )
            if pulled and current > prev and 0 < current < 200:
                return PatternSignal(
                    pattern="ZLR", group="CONTINUATION", direction="LONG",
                    confidence=min(0.9, 0.5 + current / 400),
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"bars_since_extreme": bars_since},
                )
            break

    # ZLR DOWN
    for i in range(n - 2, max(n - LOOKBACK - 1, -1), -1):
        if cci_history[i] < -100:
            bars_since = n - 1 - i
            pulled = any(
                -100 <= cci_history[j] <= 50
                for j in range(i + 1, n - 1)
            )
            if pulled and current < prev and -200 < current < 0:
                return PatternSignal(
                    pattern="ZLR", group="CONTINUATION", direction="SHORT",
                    confidence=min(0.9, 0.5 + abs(current) / 400),
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"bars_since_extreme": bars_since},
                )
            break

    return None
