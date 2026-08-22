"""C1: S2_DELTA_DBL_V1 — Delta-triggered double bottom/top detector.

Michael's primitive from cvd_effort_result.py §P2 ("volume comes in" = delta
arrives). Conditioned on day_type in {Normal, Trend_Normal, Trend_DD} — without
the conditioning the same detector is -$2,038.

Measured: +$2,254/34 sessions @6c (IS +$1,218 / OOS +$1,036); positive at all
three slippage levels.  Shadow for ≥10 sessions before live.

This is a SEPARATE stream from the slot competition — it does NOT take an S2
slot.  Routes through the gateway with its own classification.

Flag: S2_DELTA_DBL_V1 (default OFF).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Detection parameters (from cvd_effort_result.py §P2)
DBT_MIN = 4     # min bars between T1 and T2
DBT_MAX = 20    # max bars between T1 and T2
DELTA_MULT = 1.0  # delta must be >= this × avg_abs_delta
NECK_MIN_FRAC = 0.8  # neck height must be >= this × ATR
T2_TOL_FRAC = 0.75   # T2 level within this × ATR of T1

# Day types where the detector is active (the conditioning is everything)
ACTIVE_DAY_TYPES = frozenset({"Normal", "Trend_Normal", "Trend_DD"})


def enabled() -> bool:
    return os.getenv("S2_DELTA_DBL_V1", "0").lower() in (
        "1", "true", "yes", "shadow")


def shadow_only() -> bool:
    return os.getenv("S2_DELTA_DBL_V1", "0").lower() == "shadow"


def _swing_low(bars: List[Dict], idx: int) -> bool:
    """True if bars[idx] is a local low (lower than neighbors)."""
    if idx < 2 or idx >= len(bars):
        return False
    lo = bars[idx].get("l", bars[idx].get("low", 0)) or 0
    return all(
        lo <= (bars[k].get("l", bars[k].get("low", 0)) or 0)
        for k in range(max(0, idx - 2), min(len(bars), idx + 3))
        if k != idx
    )


def _swing_high(bars: List[Dict], idx: int) -> bool:
    """True if bars[idx] is a local high."""
    if idx < 2 or idx >= len(bars):
        return False
    hi = bars[idx].get("h", bars[idx].get("high", 0)) or 0
    return all(
        hi >= (bars[k].get("h", bars[k].get("high", 0)) or 0)
        for k in range(max(0, idx - 2), min(len(bars), idx + 3))
        if k != idx
    )


def detect_delta_dbl(
    bars: List[Dict],
    day_type: Optional[str],
    atr: Optional[float],
    deltas: Optional[List[float]],
) -> Optional[Dict[str, Any]]:
    """Detect a delta-triggered double bottom or top on the last bar.

    Args:
        bars: 5-min OHLCV bars (newest last).
        day_type: current day type string.
        atr: ATR14 in points (for size thresholds).
        deltas: per-bar cumulative delta diffs aligned to bars
                (same length, or None if unavailable).

    Returns:
        Setup dict or None.
    """
    if not enabled():
        return None
    if day_type not in ACTIVE_DAY_TYPES:
        return None
    if not bars or len(bars) < DBT_MIN + 2:
        return None
    if atr is None or atr <= 0:
        return None
    if not deltas or len(deltas) < len(bars):
        return None

    i = len(bars) - 1
    bar = bars[i]
    c = bar.get("c", bar.get("close", 0)) or 0
    o = bar.get("o", bar.get("open", 0)) or 0
    d = deltas[i]
    ad = sum(abs(deltas[k]) for k in range(max(0, i - 14), i)) / max(1, min(14, i))

    # --- Double bottom (LONG) ---
    for j in range(max(0, i - DBT_MAX), i - DBT_MIN + 1):
        if not _swing_low(bars, j):
            continue
        t2_idx = min(range(j + DBT_MIN, i + 1),
                     key=lambda k: (bars[k].get("l", bars[k].get("low", 0)) or 0))
        t1_low = bars[j].get("l", bars[j].get("low", 0)) or 0
        t2_low = bars[t2_idx].get("l", bars[t2_idx].get("low", 0)) or 0
        if abs(t2_low - t1_low) > T2_TOL_FRAC * atr or t2_idx == j:
            continue
        neck = max(
            (bars[k].get("h", bars[k].get("high", 0)) or 0)
            for k in range(j, t2_idx + 1))
        if neck - t1_low < NECK_MIN_FRAC * atr:
            continue
        if i - t2_idx > 5:
            continue
        if d >= DELTA_MULT * ad and c > (bars[i - 1].get("h", bars[i - 1].get("high", 0)) or 0) and c > o:
            stop = min(t1_low, t2_low) - 0.25  # 1 tick below the double bottom
            t1 = c + 0.45 * (neck - stop)
            t2 = c + 0.80 * (neck - stop)
            t3 = c + 1.30 * (neck - stop)
            return {
                "pattern": "S2_DELTA_DBL_LONG",
                "classification": "S2_DELTA_DBL_LONG",
                "direction": "LONG",
                "entry_price": c,
                "stop": round(stop, 2),
                "t1": round(t1, 2),
                "t2": round(t2, 2),
                "t3": round(t3, 2),
                "metadata": {
                    "pattern": "S2_DELTA_DBL_LONG",
                    "shadow_only": shadow_only(),
                    "day_type": day_type,
                    "t1_bar": j,
                    "t2_bar": t2_idx,
                    "delta": round(d, 1),
                    "delta_ratio": round(d / max(ad, 0.1), 2),
                    "neck": round(neck, 2),
                },
            }
        break  # first match only

    # --- Double top (SHORT) ---
    for j in range(max(0, i - DBT_MAX), i - DBT_MIN + 1):
        if not _swing_high(bars, j):
            continue
        t2_idx = max(range(j + DBT_MIN, i + 1),
                     key=lambda k: (bars[k].get("h", bars[k].get("high", 0)) or 0))
        t1_high = bars[j].get("h", bars[j].get("high", 0)) or 0
        t2_high = bars[t2_idx].get("h", bars[t2_idx].get("high", 0)) or 0
        if abs(t2_high - t1_high) > T2_TOL_FRAC * atr or t2_idx == j:
            continue
        neck = min(
            (bars[k].get("l", bars[k].get("low", 0)) or 0)
            for k in range(j, t2_idx + 1))
        if t1_high - neck < NECK_MIN_FRAC * atr:
            continue
        if i - t2_idx > 5:
            continue
        if d <= -DELTA_MULT * ad and c < (bars[i - 1].get("l", bars[i - 1].get("low", 0)) or 0) and c < o:
            stop = max(t1_high, t2_high) + 0.25
            risk = stop - c
            t1 = c - 0.45 * risk
            t2 = c - 0.80 * risk
            t3 = c - 1.30 * risk
            return {
                "pattern": "S2_DELTA_DBL_SHORT",
                "classification": "S2_DELTA_DBL_SHORT",
                "direction": "SHORT",
                "entry_price": c,
                "stop": round(stop, 2),
                "t1": round(t1, 2),
                "t2": round(t2, 2),
                "t3": round(t3, 2),
                "metadata": {
                    "pattern": "S2_DELTA_DBL_SHORT",
                    "shadow_only": shadow_only(),
                    "day_type": day_type,
                    "t1_bar": j,
                    "t2_bar": t2_idx,
                    "delta": round(d, 1),
                    "delta_ratio": round(abs(d) / max(ad, 0.1), 2),
                    "neck": round(neck, 2),
                },
            }
        break

    return None
