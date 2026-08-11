"""pullback_retest — RE_PULLBACK_ENTRY_V1 (C2, 2026-08-11).

The missing Dalton entry: after the IB breaks, price extends, then pulls
back to retest the broken edge. If the retest holds (rejection bar closes
back with the break direction), enter WITH the break.

Spec (docs/research/DALTON_DAY_TYPE_2026-08-10.md §6.3):
  (a) IB broken by >= IB_BREAK_MIN_FRAC × ib_width in period C or later
  (b) Price returns to within RETEST_TOL_PT of the broken IB edge
  (c) A 5-min rejection bar closes back WITH the break direction
  Stop = beyond the retest extreme + STOP_BUFFER_TICKS
  Targets: structural (edge ± 0.5×IB, ± 1×IB, ± 2×IB)

Flag: RE_PULLBACK_ENTRY_V1 (default OFF).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Literal, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Tunable constants ──
IB_BREAK_MIN_FRAC = 0.15   # min IB penetration to qualify as "broken"
RETEST_TOL_PT = 1.5         # price within this many pts of broken edge = retest
REJECTION_MIN_BODY_PCT = 0.30  # rejection bar body must be >= 30% of range
STOP_BUFFER_TICKS = 6       # ticks beyond retest extreme for stop
TICK_SIZE = 0.25
MIN_BARS_AFTER_BREAK = 2    # at least 2 bars between break and retest

Direction = Literal["LONG", "SHORT"]


def detect_pullback_retest(
    bars: List[Dict],
    *,
    ib_high: Optional[float] = None,
    ib_low: Optional[float] = None,
    ib_locked: bool = False,
    session_min: int = 0,
) -> Tuple[Optional[Direction], float, Dict]:
    """Detect a pullback-retest of a broken IB edge.

    Returns (direction, confidence, info) or (None, 0, {}) if no pattern.
    """
    if not ib_locked or ib_high is None or ib_low is None:
        return (None, 0.0, {})

    ib_width = ib_high - ib_low
    if ib_width <= 0:
        return (None, 0.0, {})

    # Need enough bars for break + extension + pullback
    if len(bars) < 5:
        return (None, 0.0, {})

    # Only fire in period C or later (session_min >= 60, i.e. after IB lock)
    if session_min < 60:
        return (None, 0.0, {})

    min_break = IB_BREAK_MIN_FRAC * ib_width

    # Check for IB break: look at recent bars for extension beyond IB
    # We need: (1) a bar that broke the IB edge, (2) subsequent bars that
    # extended, (3) then a pullback to the edge, (4) rejection bar.
    last_bar = bars[-1]
    last_h = float(last_bar.get("h", last_bar.get("high", 0)))
    last_l = float(last_bar.get("l", last_bar.get("low", 0)))
    last_c = float(last_bar.get("c", last_bar.get("close", 0)))
    last_o = float(last_bar.get("o", last_bar.get("open", 0)))
    last_range = last_h - last_l if last_h > last_l else 0.01

    # --- LONG: IB-high was broken upward, price pulled back to ib_high ---
    result = _check_long_retest(bars, ib_high, ib_low, ib_width, min_break)
    if result[0] is not None:
        return result

    # --- SHORT: IB-low was broken downward, price pulled back to ib_low ---
    result = _check_short_retest(bars, ib_high, ib_low, ib_width, min_break)
    if result[0] is not None:
        return result

    return (None, 0.0, {})


def _check_long_retest(
    bars: List[Dict],
    ib_high: float, ib_low: float, ib_width: float, min_break: float,
) -> Tuple[Optional[Direction], float, Dict]:
    """Check for LONG retest: IB-high broken upward, pullback to ib_high."""

    # Find if IB-high was broken: any bar in the window that closed above ib_high + min_break
    break_idx = None
    max_extension = 0.0
    for i in range(len(bars) - MIN_BARS_AFTER_BREAK - 1):
        h = float(bars[i].get("h", bars[i].get("high", 0)))
        c = float(bars[i].get("c", bars[i].get("close", 0)))
        if h > ib_high + min_break and c > ib_high:
            break_idx = i
            ext = h - ib_high
            if ext > max_extension:
                max_extension = ext

    if break_idx is None:
        return (None, 0.0, {})

    # After the break, price must have extended further
    for i in range(break_idx + 1, len(bars)):
        h = float(bars[i].get("h", bars[i].get("high", 0)))
        ext = h - ib_high
        if ext > max_extension:
            max_extension = ext

    if max_extension < min_break:
        return (None, 0.0, {})

    # Check last bar: pullback to within RETEST_TOL_PT of ib_high
    last = bars[-1]
    last_l = float(last.get("l", last.get("low", 0)))
    last_c = float(last.get("c", last.get("close", 0)))
    last_o = float(last.get("o", last.get("open", 0)))
    last_h = float(last.get("h", last.get("high", 0)))
    last_range = last_h - last_l if last_h > last_l else 0.01

    # (b) Low touched or came within tolerance of ib_high (the retest)
    if last_l > ib_high + RETEST_TOL_PT:
        return (None, 0.0, {})  # didn't pull back enough

    # (c) Rejection: close above ib_high AND close > open (bullish close)
    #     AND body is a meaningful fraction of the range
    body = last_c - last_o
    if last_c <= ib_high:
        return (None, 0.0, {})  # closed below the edge — failed retest
    if body < 0:
        return (None, 0.0, {})  # bearish close — not a rejection
    if body / last_range < REJECTION_MIN_BODY_PCT:
        return (None, 0.0, {})  # doji/indecision — not convincing

    # Build the entry
    entry_price = last_c
    retest_low = last_l
    stop_price = retest_low - STOP_BUFFER_TICKS * TICK_SIZE

    # Targets: structural from IB
    t1 = ib_high + 0.5 * ib_width
    t2 = ib_high + 1.0 * ib_width
    t3 = ib_high + 2.0 * ib_width

    # Confidence: higher when the pullback was clean (close near high)
    close_quality = (last_c - last_l) / last_range if last_range > 0 else 0.5
    confidence = min(0.5 + close_quality * 0.3, 0.85)

    info = {
        "kind": "RE_PULLBACK",
        "pattern_name": "RE_PULLBACK_LONG",
        "direction": "LONG",
        "entry_price": round(entry_price, 2),
        "stop": round(stop_price, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "t3": round(t3, 2),
        "ib_high": ib_high,
        "ib_low": ib_low,
        "ib_width": round(ib_width, 2),
        "retest_low": round(retest_low, 2),
        "max_extension": round(max_extension, 2),
        "break_idx": break_idx,
    }

    logger.info(
        "[RE_PULLBACK] LONG detected: entry=%.2f stop=%.2f retest_low=%.2f "
        "ib_high=%.2f ext=%.2f conf=%.2f",
        entry_price, stop_price, retest_low, ib_high, max_extension, confidence)

    return ("LONG", confidence, info)


def _check_short_retest(
    bars: List[Dict],
    ib_high: float, ib_low: float, ib_width: float, min_break: float,
) -> Tuple[Optional[Direction], float, Dict]:
    """Check for SHORT retest: IB-low broken downward, pullback to ib_low."""

    break_idx = None
    max_extension = 0.0
    for i in range(len(bars) - MIN_BARS_AFTER_BREAK - 1):
        l = float(bars[i].get("l", bars[i].get("low", 0)))
        c = float(bars[i].get("c", bars[i].get("close", 0)))
        if l < ib_low - min_break and c < ib_low:
            break_idx = i
            ext = ib_low - l
            if ext > max_extension:
                max_extension = ext

    if break_idx is None:
        return (None, 0.0, {})

    for i in range(break_idx + 1, len(bars)):
        l = float(bars[i].get("l", bars[i].get("low", 0)))
        ext = ib_low - l
        if ext > max_extension:
            max_extension = ext

    if max_extension < min_break:
        return (None, 0.0, {})

    last = bars[-1]
    last_h = float(last.get("h", last.get("high", 0)))
    last_c = float(last.get("c", last.get("close", 0)))
    last_o = float(last.get("o", last.get("open", 0)))
    last_l = float(last.get("l", last.get("low", 0)))
    last_range = last_h - last_l if last_h > last_l else 0.01

    # (b) High touched or came within tolerance of ib_low (the retest)
    if last_h < ib_low - RETEST_TOL_PT:
        return (None, 0.0, {})

    # (c) Rejection: close below ib_low AND close < open (bearish close)
    body = last_o - last_c
    if last_c >= ib_low:
        return (None, 0.0, {})
    if body < 0:
        return (None, 0.0, {})
    if body / last_range < REJECTION_MIN_BODY_PCT:
        return (None, 0.0, {})

    entry_price = last_c
    retest_high = last_h
    stop_price = retest_high + STOP_BUFFER_TICKS * TICK_SIZE

    t1 = ib_low - 0.5 * ib_width
    t2 = ib_low - 1.0 * ib_width
    t3 = ib_low - 2.0 * ib_width

    close_quality = (last_h - last_c) / last_range if last_range > 0 else 0.5
    confidence = min(0.5 + close_quality * 0.3, 0.85)

    info = {
        "kind": "RE_PULLBACK",
        "pattern_name": "RE_PULLBACK_SHORT",
        "direction": "SHORT",
        "entry_price": round(entry_price, 2),
        "stop": round(stop_price, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "t3": round(t3, 2),
        "ib_high": ib_high,
        "ib_low": ib_low,
        "ib_width": round(ib_width, 2),
        "retest_high": round(retest_high, 2),
        "max_extension": round(max_extension, 2),
        "break_idx": break_idx,
    }

    logger.info(
        "[RE_PULLBACK] SHORT detected: entry=%.2f stop=%.2f retest_high=%.2f "
        "ib_low=%.2f ext=%.2f conf=%.2f",
        entry_price, stop_price, retest_high, ib_low, max_extension, confidence)

    return ("SHORT", confidence, info)
