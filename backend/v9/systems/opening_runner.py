"""Opening Runner Ride — P2 (2026-07-29).

Michael mandate: "long until the end" — after T1 of an opening trade, the
runner doesn't close at T3-fixed. Instead it trails on the 30-min swing
(structural trail), with exits on:
  - LSMA color flip against the trade
  - 15:45 ET on trend days (C4_TREND_FLATTEN_V1 already handles this)
  - Stop-hit at the trailing level

Flag: OPENING_RUNNER_RIDE_V1 (default OFF). When OFF, the existing T2/T3
management runs unchanged (byte-identical).

This module computes the trail level from recent bars — it does NOT place
orders or modify stops directly. The caller (bar_level_detector) uses the
returned trail level to issue MODIFY_STOP.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _flag_on() -> bool:
    return os.getenv("OPENING_RUNNER_RIDE_V1", "0").lower() in ("1", "true", "yes")


def compute_structural_trail(
    *,
    direction: str,
    bars: List[Dict],
    window: int = 6,  # 6 × 5min = 30 min
    tick: float = 0.25,
    buffer_ticks: int = 4,  # 1 point buffer behind the swing
) -> Optional[float]:
    """Compute the structural trailing stop for an opening runner.

    LONG: trail on the lowest low of the last `window` bars − buffer.
    SHORT: trail on the highest high of the last `window` bars + buffer.

    Returns None if insufficient data (Rule 1: honest None, never synthesize).
    """
    if not _flag_on():
        return None

    recent = bars[-window:] if len(bars) >= window else bars
    if len(recent) < 3:
        return None

    d = direction.upper()
    buf = buffer_ticks * tick

    if d == "LONG":
        lows = []
        for b in recent:
            l = b.get("l", b.get("low"))
            if l is not None:
                lows.append(float(l))
        if not lows:
            return None
        trail = min(lows) - buf
    elif d == "SHORT":
        highs = []
        for b in recent:
            h = b.get("h", b.get("high"))
            if h is not None:
                highs.append(float(h))
        if not highs:
            return None
        trail = max(highs) + buf
    else:
        return None

    # Tick-snap
    return round(round(trail / tick) * tick, 2)


def should_exit_lsma_cross(
    *,
    direction: str,
    trend_state: Optional[str],
) -> bool:
    """Exit the runner when the LSMA trend flips against the trade direction.

    LONG + RED → exit. SHORT + BLUE → exit. Unknown/None → hold (fail-safe).
    """
    if not _flag_on():
        return False
    if trend_state is None:
        return False
    ts = trend_state.upper()
    d = direction.upper()
    return (d == "LONG" and ts == "RED") or (d == "SHORT" and ts == "BLUE")
