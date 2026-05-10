"""VEGAS (VEGAs Double Divergence) — Reversal pattern.

Price makes HH but CCI makes LH (bearish), or
Price makes LL but CCI makes HL (bullish).
Requires double divergence (two consecutive swing comparisons).
"""

from typing import Optional, List
from backend.v9.systems.woodies.schemas import PatternSignal

LOOKBACK = 20


def _find_swings(values: List[float], min_swing: int = 3) -> list:
    """Find swing highs and lows as (index, value, type='H'|'L')."""
    swings = []
    for i in range(min_swing, len(values) - 1):
        is_high = all(values[i] >= values[i - j] for j in range(1, min_swing + 1))
        is_high = is_high and values[i] > values[i + 1] if i + 1 < len(values) else is_high
        if is_high:
            swings.append((i, values[i], "H"))

        is_low = all(values[i] <= values[i - j] for j in range(1, min_swing + 1))
        is_low = is_low and values[i] < values[i + 1] if i + 1 < len(values) else is_low
        if is_low:
            swings.append((i, values[i], "L"))
    return swings


def detect_vegas(cci_history: list, bar_index: int, ts: float,
                 price_closes: list = None, **kwargs) -> Optional[PatternSignal]:
    if price_closes is None or len(price_closes) < LOOKBACK or len(cci_history) < LOOKBACK:
        return None

    window_cci = cci_history[-LOOKBACK:]
    window_price = price_closes[-LOOKBACK:]

    price_swings = _find_swings(window_price, 2)
    cci_swings = _find_swings(window_cci, 2)

    price_highs = [(i, v) for i, v, t in price_swings if t == "H"]
    cci_highs = [(i, v) for i, v, t in cci_swings if t == "H"]
    price_lows = [(i, v) for i, v, t in price_swings if t == "L"]
    cci_lows = [(i, v) for i, v, t in cci_swings if t == "L"]

    # Bearish: price HH, CCI LH
    if len(price_highs) >= 2 and len(cci_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        c1, c2 = cci_highs[-2], cci_highs[-1]
        if p2[1] > p1[1] and c2[1] < c1[1]:
            return PatternSignal(
                pattern="VEGAS", group="REVERSAL", direction="SHORT",
                confidence=0.75,
                cci_at_signal=cci_history[-1], bar_index=bar_index, ts=ts,
                details={"price_hh": True, "cci_lh": True},
            )

    # Bullish: price LL, CCI HL
    if len(price_lows) >= 2 and len(cci_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        c1, c2 = cci_lows[-2], cci_lows[-1]
        if p2[1] < p1[1] and c2[1] > c1[1]:
            return PatternSignal(
                pattern="VEGAS", group="REVERSAL", direction="LONG",
                confidence=0.75,
                cci_at_signal=cci_history[-1], bar_index=bar_index, ts=ts,
                details={"price_ll": True, "cci_hl": True},
            )

    return None
