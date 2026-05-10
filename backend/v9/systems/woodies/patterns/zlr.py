"""ZLR (Zero Line Reject) — Continuation pattern.

ZLR UP:  CCI was above +100 → pulls back toward zero (stays > -100) → bounces up.
ZLR DOWN: CCI was below -100 → pulls back toward zero (stays < +100) → drops.
Lookback: 12 bars (matching DLL).
"""

from typing import Optional
from backend.v9.systems.woodies.schemas import PatternSignal

LOOKBACK = 12


def detect_zlr(cci_history: list, bar_index: int, ts: float,
               **kwargs) -> Optional[PatternSignal]:
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
