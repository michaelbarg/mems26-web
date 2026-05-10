"""VEGAS (Virtual Extended Geometric Algo Scan) -- Reversal pattern.

Multiple indicators align for strong trend entry via divergence detection.
Price makes HH but CCI makes LH (bearish divergence), or
price makes LL but CCI makes HL (bullish divergence).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B1).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

LOOKBACK = 20
PATTERN_ID = "VEGAS"
GROUP = "REVERSAL"
TICK_SIZE = 0.25
STOP_TICKS = 12
TARGET1_TICKS = 16
TARGET2_TICKS = 32


def _find_swings(values: List[float], min_swing: int = 3) -> list:
    """Find swing highs and lows as (index, value, type='H'|'L')."""
    swings = []
    for i in range(min_swing, len(values) - 1):
        is_high = all(values[i] >= values[i - j] for j in range(1, min_swing + 1))
        if i + 1 < len(values):
            is_high = is_high and values[i] > values[i + 1]
        if is_high:
            swings.append((i, values[i], "H"))

        is_low = all(values[i] <= values[i - j] for j in range(1, min_swing + 1))
        if i + 1 < len(values):
            is_low = is_low and values[i] < values[i + 1]
        if is_low:
            swings.append((i, values[i], "L"))
    return swings


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect VEGAS pattern from WoodiesBar list."""
    if len(bars) < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    window_bars = bars[-LOOKBACK:]
    window_cci = [b.cci_14 for b in window_bars]
    window_price = [b.close for b in window_bars]
    bar = bars[-1]

    price_swings = _find_swings(window_price, 2)
    cci_swings = _find_swings(window_cci, 2)

    price_highs = [(i, v) for i, v, t in price_swings if t == "H"]
    cci_highs = [(i, v) for i, v, t in cci_swings if t == "H"]
    price_lows = [(i, v) for i, v, t in price_swings if t == "L"]
    cci_lows = [(i, v) for i, v, t in cci_swings if t == "L"]

    # Bearish VEGAS: price HH, CCI LH
    if len(price_highs) >= 2 and len(cci_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        c1, c2 = cci_highs[-2], cci_highs[-1]
        if p2[1] > p1[1] and c2[1] < c1[1]:
            entry = bar.close
            stop = entry + STOP_TICKS * TICK_SIZE
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="SHORT",
                confidence=0.75,
                entry_price=entry,
                stop=stop,
                targets=[
                    entry - TARGET1_TICKS * TICK_SIZE,
                    entry - TARGET2_TICKS * TICK_SIZE,
                ],
                group=GROUP,
                cci_at_signal=bar.cci_14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"price_hh": True, "cci_lh": True},
            )

    # Bullish VEGAS: price LL, CCI HL
    if len(price_lows) >= 2 and len(cci_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        c1, c2 = cci_lows[-2], cci_lows[-1]
        if p2[1] < p1[1] and c2[1] > c1[1]:
            entry = bar.close
            stop = entry - STOP_TICKS * TICK_SIZE
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="LONG",
                confidence=0.75,
                entry_price=entry,
                stop=stop,
                targets=[
                    entry + TARGET1_TICKS * TICK_SIZE,
                    entry + TARGET2_TICKS * TICK_SIZE,
                ],
                group=GROUP,
                cci_at_signal=bar.cci_14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"price_ll": True, "cci_hl": True},
            )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_vegas(cci_history: list, bar_index: int, ts: float,
                 price_closes: list = None, **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
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
