"""GB100 (Ghost Break 100) — Continuation pattern.

CCI crosses +100 or -100 with momentum, confirming trend continuation.
Must already be in a trend (BLUE/RED).
"""

from typing import Optional
from backend.v9.systems.woodies.schemas import PatternSignal


def detect_gb100(cci_history: list, bar_index: int, ts: float,
                 trend_state: str = "GRAY", **kwargs) -> Optional[PatternSignal]:
    n = len(cci_history)
    if n < 3:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]
    prev2 = cci_history[-3]

    # GB100 LONG: CCI crosses above +100 in a BLUE trend
    if trend_state == "BLUE" and current > 100 and prev <= 100 and prev2 < 100:
        return PatternSignal(
            pattern="GB100", group="CONTINUATION", direction="LONG",
            confidence=min(0.85, 0.5 + (current - 100) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"cross_level": 100, "momentum": round(current - prev, 2)},
        )

    # GB100 SHORT: CCI crosses below -100 in a RED trend
    if trend_state == "RED" and current < -100 and prev >= -100 and prev2 > -100:
        return PatternSignal(
            pattern="GB100", group="CONTINUATION", direction="SHORT",
            confidence=min(0.85, 0.5 + (abs(current) - 100) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"cross_level": -100, "momentum": round(current - prev, 2)},
        )

    return None
