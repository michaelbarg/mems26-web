"""flags — Bull Flag (LONG) + Bear Flag (SHORT) continuation detectors per D-091 §9+§10.

Pole/flag/breakout geometric detection · Bulkowski 1,028 trades + Brooks H2/L2.
Stage 3 only · gated upstream in five_min_system.process_bar.

Detection geometry defaults (Michael lock 3 · 24/5 16:27 IL · SHADOW-calibratable):
  MIN_BARS_REQUIRED     = 10
  SEARCH_WINDOW         = 30
  POLE_MIN_BARS         = 5
  POLE_MAX_BARS         = 15
  POLE_MIN_HEIGHT_TICKS = 16     # 4pt MES minimum pole
  POLE_DIRECTIONAL_PCT  = 0.60   # 60% bars closing in pole direction
  FLAG_MIN_BARS         = 3
  FLAG_MAX_BARS         = 8
  FLAG_MAX_RETRACE_PCT  = 0.50   # flag retraces <= 50% of pole
  TICK_SIZE             = 0.25   # MES

These 10 constants are SHADOW-calibratable. Do NOT hardcode at call sites.

NOTE: info["trail_active"] is added LATER by the integration layer
(five_min_system.process_bar) based on current_day_type. The detector itself
does NOT set trail_active — that field reflects system context, not pattern shape.
"""
from __future__ import annotations
import logging
import time
from typing import List, Dict, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

# ── Module constants · SHADOW-calibratable ──
MIN_BARS_REQUIRED = 10
SEARCH_WINDOW = 30
POLE_MIN_BARS = 5
POLE_MAX_BARS = 15
POLE_MIN_HEIGHT_TICKS = 16
POLE_DIRECTIONAL_PCT = 0.60
FLAG_MIN_BARS = 3
FLAG_MAX_BARS = 8
FLAG_MAX_RETRACE_PCT = 0.50
TICK_SIZE = 0.25

# S2 ATR-relative pole/flag (E2E 2/2 · shadow only)
from backend.v9.shared.atr import S2_ATR_RELATIVE  # noqa: E402
_POLE_MIN_ATR_K = 5.5   # pole ≥ 5.5×ATR
_FLAG_MAX_ATR_K = 2.5    # flag ≤ 2.5×ATR


def get_pole_min_height_ticks(atr_5m=None) -> int:
    """Pole minimum height in ticks — ATR-relative when flag ON."""
    if S2_ATR_RELATIVE and atr_5m is not None:
        return max(1, round(_POLE_MIN_ATR_K * atr_5m / TICK_SIZE))
    return POLE_MIN_HEIGHT_TICKS


def get_flag_max_height_ticks(atr_5m=None) -> int:
    """Flag max height in ticks (retrace ceiling) — ATR-relative when flag ON."""
    if S2_ATR_RELATIVE and atr_5m is not None:
        return max(1, round(_FLAG_MAX_ATR_K * atr_5m / TICK_SIZE))
    return None  # caller uses FLAG_MAX_RETRACE_PCT when None

Direction = Literal["LONG", "SHORT"]

_last_warn_ts: Dict[str, float] = {}


def _rate_limited_warn(category: str, msg: str, *args) -> None:
    now = time.monotonic()
    last = _last_warn_ts.get(category, 0.0)
    if now - last >= 60.0:
        logger.warning(msg, *args)
        _last_warn_ts[category] = now


def _find_pole_bull(bars: List[Dict]) -> Optional[Dict]:
    """Find newest valid bull pole (upward thrust). Returns pole info or None."""
    window = bars[-min(len(bars), SEARCH_WINDOW):]
    n = len(window)

    # Pole top must leave room for flag + breakout bar after it
    max_top = n - FLAG_MIN_BARS - 1  # -1 for breakout bar
    for start in range(max(0, max_top - POLE_MAX_BARS), -1, -1):
        # Find highest high in candidate range (up to max_top)
        best_top = start
        for j in range(start + 1, min(start + POLE_MAX_BARS + 1, max_top + 1)):
            if window[j]["h"] > window[best_top]["h"]:
                best_top = j
        pole_len = best_top - start + 1
        if pole_len < POLE_MIN_BARS or pole_len > POLE_MAX_BARS:
            continue

        pole_height = window[best_top]["h"] - window[start]["l"]
        if pole_height < POLE_MIN_HEIGHT_TICKS * TICK_SIZE:
            continue

        up_count = sum(1 for j in range(start, best_top + 1) if window[j]["c"] > window[j]["o"])
        if up_count / pole_len < POLE_DIRECTIONAL_PCT:
            continue

        return {
            "start_idx": start, "top_idx": best_top,
            "start_low": window[start]["l"], "top_high": window[best_top]["h"],
            "pole_height": pole_height, "pole_bars": pole_len,
            "window": window,
        }
    return None


def _find_pole_bear(bars: List[Dict]) -> Optional[Dict]:
    """Find newest valid bear pole (downward thrust)."""
    window = bars[-min(len(bars), SEARCH_WINDOW):]
    n = len(window)

    max_bot = n - FLAG_MIN_BARS - 1
    for start in range(max(0, max_bot - POLE_MAX_BARS), -1, -1):
        best_bot = start
        for j in range(start + 1, min(start + POLE_MAX_BARS + 1, max_bot + 1)):
            if window[j]["l"] < window[best_bot]["l"]:
                best_bot = j
        pole_len = best_bot - start + 1
        if pole_len < POLE_MIN_BARS or pole_len > POLE_MAX_BARS:
            continue

        pole_height = window[start]["h"] - window[best_bot]["l"]
        if pole_height < POLE_MIN_HEIGHT_TICKS * TICK_SIZE:
            continue

        down_count = sum(1 for j in range(start, best_bot + 1) if window[j]["c"] < window[j]["o"])
        if down_count / pole_len < POLE_DIRECTIONAL_PCT:
            continue

        return {
            "start_idx": start, "bottom_idx": best_bot,
            "start_high": window[start]["h"], "bottom_low": window[best_bot]["l"],
            "pole_height": pole_height, "pole_bars": pole_len,
            "window": window,
        }
    return None


def detect_bull_flag(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Bull Flag (LONG continuation). Pole up + flag consolidation + breakout."""
    if len(bars) < MIN_BARS_REQUIRED:
        return (None, 0.0, {})

    pole = _find_pole_bull(bars)
    if pole is None:
        return (None, 0.0, {})

    w = pole["window"]
    top_idx = pole["top_idx"]
    flag_start = top_idx + 1
    flag_end = len(w) - 2  # bar before breakout
    if flag_end < flag_start:
        return (None, 0.0, {})

    flag_len = flag_end - flag_start + 1
    if flag_len < FLAG_MIN_BARS or flag_len > FLAG_MAX_BARS:
        return (None, 0.0, {})

    flag_bars = w[flag_start:flag_end + 1]
    flag_low = min(b["l"] for b in flag_bars)
    flag_high = max(b["h"] for b in flag_bars)

    retrace = (pole["top_high"] - flag_low) / pole["pole_height"] if pole["pole_height"] > 0 else 1.0
    if retrace > FLAG_MAX_RETRACE_PCT:
        return (None, 0.0, {})

    # Defensive: no flag bar closes above pole top
    if any(b["c"] > pole["top_high"] for b in flag_bars):
        return (None, 0.0, {})

    # Breakout
    breakout = w[-1]
    if breakout["c"] <= flag_high + TICK_SIZE:
        return (None, 0.0, {})

    pm = pole["pole_height"]
    bar_count = (flag_end + 1) - pole["start_idx"] + 1

    # Confidence
    pole_ht = pm / TICK_SIZE
    pole_score = min(1.0, max(0.0, (pole_ht - POLE_MIN_HEIGHT_TICKS) / POLE_MIN_HEIGHT_TICKS))
    retrace_score = max(0.0, 1.0 - retrace / FLAG_MAX_RETRACE_PCT)
    conf = min(1.0, max(0.0, 0.60 + 0.20 * pole_score + 0.20 * retrace_score))

    return ("LONG", conf, {
        "kind": "BULL_FLAG",
        "pattern_name": "BULL_FLAG_LONG",
        "structural_anchor": flag_low - TICK_SIZE,
        "pattern_measure": pm,
        "pole_top_price": pole["top_high"],
        "pole_start_price": pole["start_low"],
        "flag_low": flag_low,
        "flag_high": flag_high,
        "pole_bars": pole["pole_bars"],
        "flag_bars": flag_len,
        "bar_count": bar_count,
        "stage": 3,
    })


def detect_bear_flag(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Bear Flag (SHORT continuation). Pole down + flag consolidation + breakdown."""
    if len(bars) < MIN_BARS_REQUIRED:
        return (None, 0.0, {})

    pole = _find_pole_bear(bars)
    if pole is None:
        return (None, 0.0, {})

    w = pole["window"]
    bot_idx = pole["bottom_idx"]
    flag_start = bot_idx + 1
    flag_end = len(w) - 2
    if flag_end < flag_start:
        return (None, 0.0, {})

    flag_len = flag_end - flag_start + 1
    if flag_len < FLAG_MIN_BARS or flag_len > FLAG_MAX_BARS:
        return (None, 0.0, {})

    flag_bars = w[flag_start:flag_end + 1]
    flag_high = max(b["h"] for b in flag_bars)
    flag_low = min(b["l"] for b in flag_bars)

    retrace = (flag_high - pole["bottom_low"]) / pole["pole_height"] if pole["pole_height"] > 0 else 1.0
    if retrace > FLAG_MAX_RETRACE_PCT:
        return (None, 0.0, {})

    if any(b["c"] < pole["bottom_low"] for b in flag_bars):
        return (None, 0.0, {})

    breakout = w[-1]
    if breakout["c"] >= flag_low - TICK_SIZE:
        return (None, 0.0, {})

    pm = pole["pole_height"]
    bar_count = (flag_end + 1) - pole["start_idx"] + 1

    pole_ht = pm / TICK_SIZE
    pole_score = min(1.0, max(0.0, (pole_ht - POLE_MIN_HEIGHT_TICKS) / POLE_MIN_HEIGHT_TICKS))
    retrace_score = max(0.0, 1.0 - retrace / FLAG_MAX_RETRACE_PCT)
    conf = min(1.0, max(0.0, 0.60 + 0.20 * pole_score + 0.20 * retrace_score))

    return ("SHORT", conf, {
        "kind": "BEAR_FLAG",
        "pattern_name": "BEAR_FLAG_SHORT",
        "structural_anchor": flag_high + TICK_SIZE,
        "pattern_measure": pm,
        "pole_top_price": pole["start_high"],
        "pole_start_price": pole["bottom_low"],
        "flag_low": flag_low,
        "flag_high": flag_high,
        "pole_bars": pole["pole_bars"],
        "flag_bars": flag_len,
        "bar_count": bar_count,
        "stage": 3,
    })
