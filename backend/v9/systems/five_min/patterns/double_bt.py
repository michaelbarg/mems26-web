"""double_bt — Double Bottom Eve&Eve (LONG) + Double Top Adam&Adam (SHORT) per D-091 §7+§8.

Geometric Bulkowski-style detection · 2 swing points · neckline · breakout trigger.
Variant constraint:
  - Eve&Eve (Double Bottom): both troughs rounded/wide (>= TROUGH_MIN_WIDTH_BARS)
  - Adam&Adam (Double Top): both peaks sharp/V-shaped (<= PEAK_MAX_WIDTH_BARS)

Stage 3 only · gated upstream in five_min_system.process_bar.

Detection geometry defaults (Cursor-seeded · SHADOW-calibratable):
  MIN_BARS_REQUIRED     = 10       # 2 troughs + intermediate · Bulkowski "10-30 bar pattern"
  SEARCH_WINDOW         = 30       # last N bars searched for pivots
  PIVOT_LOOKBACK        = 2        # Bulkowski standard
  TROUGH_SYM_PCT        = 0.03     # 3% · stricter than H&S (only 2 points)
  TROUGH_MIN_WIDTH_BARS = 3        # Eve variant: rounded · >= 3 bars wide at trough
  PEAK_MAX_WIDTH_BARS   = 2        # Adam variant: V-shaped · <= 2 bars wide at peak
  NECKLINE_MIN_RISE_PCT = 0.10     # neckline must be >= 10% of pattern height above troughs
  TICK_SIZE             = 0.25     # MES

These 7 constants are SHADOW-calibratable. Do NOT hardcode at call sites.
"""
from __future__ import annotations
import logging
import time
from typing import List, Dict, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

# ── Module constants · SHADOW-calibratable ──
MIN_BARS_REQUIRED = 10
SEARCH_WINDOW = 30
PIVOT_LOOKBACK = 2
TROUGH_SYM_PCT = 0.03
TROUGH_MIN_WIDTH_BARS = 3
PEAK_MAX_WIDTH_BARS = 2
NECKLINE_MIN_RISE_PCT = 0.10
TICK_SIZE = 0.25

Direction = Literal["LONG", "SHORT"]

_last_warn_ts: Dict[str, float] = {}


def _rate_limited_warn(category: str, msg: str, *args) -> None:
    now = time.monotonic()
    last = _last_warn_ts.get(category, 0.0)
    if now - last >= 60.0:
        logger.warning(msg, *args)
        _last_warn_ts[category] = now


# ── Pivot helpers ──


def _swing_lows(bars: List[Dict], lookback: int = PIVOT_LOOKBACK) -> List[Tuple[int, float]]:
    """Find swing low pivots."""
    pivots = []
    for i in range(lookback, len(bars) - lookback):
        low_i = bars[i]["l"]
        is_pivot = True
        for j in range(1, lookback + 1):
            if bars[i - j]["l"] <= low_i or bars[i + j]["l"] <= low_i:
                is_pivot = False
                break
        if is_pivot:
            pivots.append((i, low_i))
    return pivots


def _swing_highs(bars: List[Dict], lookback: int = PIVOT_LOOKBACK) -> List[Tuple[int, float]]:
    """Find swing high pivots."""
    pivots = []
    for i in range(lookback, len(bars) - lookback):
        high_i = bars[i]["h"]
        is_pivot = True
        for j in range(1, lookback + 1):
            if bars[i - j]["h"] >= high_i or bars[i + j]["h"] >= high_i:
                is_pivot = False
                break
        if is_pivot:
            pivots.append((i, high_i))
    return pivots


def _trough_width_bars(bars: List[Dict], pivot_idx: int, pivot_low: float) -> int:
    """Count consecutive bars at similar low around pivot (Eve = wider)."""
    tolerance = TICK_SIZE * 2  # 2 ticks (0.50pt) tolerance for "similar low"
    width = 1  # pivot bar itself
    for j in range(pivot_idx - 1, -1, -1):
        if abs(bars[j]["l"] - pivot_low) <= tolerance:
            width += 1
        else:
            break
    for j in range(pivot_idx + 1, len(bars)):
        if abs(bars[j]["l"] - pivot_low) <= tolerance:
            width += 1
        else:
            break
    return width


def _peak_width_bars(bars: List[Dict], pivot_idx: int, pivot_high: float) -> int:
    """Count consecutive bars at similar high around pivot (Adam = narrower)."""
    tolerance = TICK_SIZE * 2  # 2 ticks
    width = 1
    for j in range(pivot_idx - 1, -1, -1):
        if abs(bars[j]["h"] - pivot_high) <= tolerance:
            width += 1
        else:
            break
    for j in range(pivot_idx + 1, len(bars)):
        if abs(bars[j]["h"] - pivot_high) <= tolerance:
            width += 1
        else:
            break
    return width


def _troughs_symmetric(t1: float, t2: float) -> bool:
    """Check trough symmetry within TROUGH_SYM_PCT."""
    lower = min(t1, t2)
    if lower <= 0:
        return False
    return abs(t1 - t2) / lower <= TROUGH_SYM_PCT


def _confidence_double_bottom(t1: float, t2: float, w1: int, w2: int) -> float:
    """Confidence for Double Bottom Eve&Eve."""
    lower = min(t1, t2)
    if lower <= 0:
        return 0.6
    asym = abs(t1 - t2) / lower
    sym_score = max(0.0, 1.0 - asym / TROUGH_SYM_PCT)
    min_width = min(w1, w2)
    variant_score = min(1.0, max(0.0, (min_width / TROUGH_MIN_WIDTH_BARS - 1) / 2))
    return max(0.0, min(1.0, 0.60 + 0.20 * sym_score + 0.20 * variant_score))


def _confidence_double_top(p1: float, p2: float, w1: int, w2: int) -> float:
    """Confidence for Double Top Adam&Adam."""
    lower = min(p1, p2)
    if lower <= 0:
        return 0.6
    asym = abs(p1 - p2) / lower
    sym_score = max(0.0, 1.0 - asym / TROUGH_SYM_PCT)
    max_width = max(w1, w2)
    variant_score = min(1.0, max(0.0, (PEAK_MAX_WIDTH_BARS - max_width + 1) / 2))
    return max(0.0, min(1.0, 0.60 + 0.20 * sym_score + 0.20 * variant_score))


# ── Public detectors ──


def detect_double_bottom_ee(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Double Bottom (Eve&Eve · bullish reversal).

    2 troughs at similar low, both rounded (>= TROUGH_MIN_WIDTH_BARS).
    Neckline = max(intermediate highs). Fire: close > neckline + 1T.
    """
    if len(bars) < MIN_BARS_REQUIRED:
        return (None, 0.0, {})

    window = bars[-min(len(bars), SEARCH_WINDOW):]
    lows = _swing_lows(window)

    if len(lows) < 2:
        return (None, 0.0, {})

    for i in range(len(lows) - 1):
        t1_idx, t1_price = lows[i]
        t2_idx, t2_price = lows[i + 1]

        if not _troughs_symmetric(t1_price, t2_price):
            continue

        # Eve variant: both troughs must be wide
        w1 = _trough_width_bars(window, t1_idx, t1_price)
        w2 = _trough_width_bars(window, t2_idx, t2_price)
        if w1 < TROUGH_MIN_WIDTH_BARS or w2 < TROUGH_MIN_WIDTH_BARS:
            continue

        # Neckline: max high between the two troughs
        nl_highs = [window[j]["h"] for j in range(t1_idx + 1, t2_idx) if j < len(window)]
        if not nl_highs:
            continue
        neckline = max(nl_highs)

        lower_trough = min(t1_price, t2_price)
        pattern_height = neckline - lower_trough
        if pattern_height <= 0:
            continue

        # Neckline must rise sufficiently above troughs (reject degenerate patterns)
        if lower_trough > 0 and pattern_height / lower_trough < NECKLINE_MIN_RISE_PCT / 100:
            continue

        # Breakout: last bar close > neckline + 1T
        last_close = window[-1]["c"]
        if last_close <= neckline + TICK_SIZE:
            continue

        bar_count = t2_idx - t1_idx + 1
        conf = _confidence_double_bottom(t1_price, t2_price, w1, w2)

        return ("LONG", conf, {
            "kind": "DOUBLE_BOTTOM_EE",
            "pattern_name": "DOUBLE_BOTTOM_EE_LONG",
            "structural_anchor": lower_trough - TICK_SIZE,
            "pattern_measure": pattern_height,
            "neckline_price": neckline,
            "trough1_price": t1_price,
            "trough2_price": t2_price,
            "bar_count": bar_count,
            "stage": 3,
        })

    return (None, 0.0, {})


def detect_double_top_aa(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Double Top (Adam&Adam · bearish reversal).

    2 peaks at similar high, both sharp (<= PEAK_MAX_WIDTH_BARS).
    Neckline = min(intermediate lows). Fire: close < neckline - 1T.
    """
    if len(bars) < MIN_BARS_REQUIRED:
        return (None, 0.0, {})

    window = bars[-min(len(bars), SEARCH_WINDOW):]
    highs = _swing_highs(window)

    if len(highs) < 2:
        return (None, 0.0, {})

    for i in range(len(highs) - 1):
        p1_idx, p1_price = highs[i]
        p2_idx, p2_price = highs[i + 1]

        if not _troughs_symmetric(p1_price, p2_price):  # reuse symmetry check
            continue

        # Adam variant: both peaks must be sharp
        w1 = _peak_width_bars(window, p1_idx, p1_price)
        w2 = _peak_width_bars(window, p2_idx, p2_price)
        if w1 > PEAK_MAX_WIDTH_BARS or w2 > PEAK_MAX_WIDTH_BARS:
            continue

        # Neckline: min low between the two peaks
        nl_lows = [window[j]["l"] for j in range(p1_idx + 1, p2_idx) if j < len(window)]
        if not nl_lows:
            continue
        neckline = min(nl_lows)

        higher_peak = max(p1_price, p2_price)
        pattern_height = higher_peak - neckline
        if pattern_height <= 0:
            continue

        if higher_peak > 0 and pattern_height / higher_peak < NECKLINE_MIN_RISE_PCT / 100:
            continue

        # Breakout: last bar close < neckline - 1T
        last_close = window[-1]["c"]
        if last_close >= neckline - TICK_SIZE:
            continue

        bar_count = p2_idx - p1_idx + 1
        conf = _confidence_double_top(p1_price, p2_price, w1, w2)

        return ("SHORT", conf, {
            "kind": "DOUBLE_TOP_AA",
            "pattern_name": "DOUBLE_TOP_AA_SHORT",
            "structural_anchor": higher_peak + TICK_SIZE,
            "pattern_measure": pattern_height,
            "neckline_price": neckline,
            "trough1_price": p1_price,
            "trough2_price": p2_price,
            "bar_count": bar_count,
            "stage": 3,
        })

    return (None, 0.0, {})
