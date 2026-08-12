"""step_scaled_ladder — F3 STEP_SCALED_LADDER_V1 (2026-08-12).

Three independent analyses converged:
  LEG_EXEMPTION_REPLAY §R2, TREND_STEP_ENTRY §9, SYSTEM4_AUDIT D4.

Problem: the detector's stop goes to the StopResolver which returns stops
sized by ATR (e.g. 0.8×ATR = 11pt on a 14pt ATR session). This produces
R=15 on a trend-day step of 11pt — no trade would ever bank.

Solution: scale stop and targets to the session's median step size.
  Stop = max(STEP_STOP_FLOOR, STEP_STOP_FRAC × median_step)
  T1 = 0.5 × median_step
  T2 = 1.0 × median_step
  T3 = 1.5 × median_step

Flag: STEP_SCALED_LADDER_V1 (default OFF).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Tunable defaults (env-overridable in the gateway)
STEP_STOP_FLOOR = 4.0       # minimum stop in points
STEP_STOP_FRAC = 0.6        # stop = 60% of median step
STEP_T1_FRAC = 0.5          # T1 = 50% of step
STEP_T2_FRAC = 1.0          # T2 = 100% of step
STEP_T3_FRAC = 1.5          # T3 = 150% of step
TICK_SIZE = 0.25


def compute_median_session_step(
    bars: List[Dict],
    direction: str = "LONG",
) -> Optional[float]:
    """Compute the median price step (extreme-advance increment) for today's session.

    For LONG: each time the session high advances, record the step size.
    For SHORT: each time the session low descends, record the step size.
    Returns the median of these steps, or None if < 3 steps found.
    """
    if not bars or len(bars) < 5:
        return None

    steps = []
    if direction == "LONG":
        running = float(bars[0].get("h", bars[0].get("high", 0)))
        for b in bars[1:]:
            h = float(b.get("h", b.get("high", 0)))
            if h > running:
                steps.append(h - running)
                running = h
    else:  # SHORT
        running = float(bars[0].get("l", bars[0].get("low", 0)))
        for b in bars[1:]:
            l = float(b.get("l", b.get("low", 0)))
            if l < running:
                steps.append(running - l)
                running = l

    if len(steps) < 3:
        return None

    steps.sort()
    mid = len(steps) // 2
    if len(steps) % 2 == 0:
        median = (steps[mid - 1] + steps[mid]) / 2.0
    else:
        median = steps[mid]

    return round(median, 2)


def _snap(price: float) -> float:
    """Snap to MES tick grid (0.25)."""
    return round(round(price / TICK_SIZE) * TICK_SIZE, 2)


def build_step_ladder(
    entry_price: float,
    direction: str,
    bars: List[Dict],
    *,
    stop_floor: float = STEP_STOP_FLOOR,
    stop_frac: float = STEP_STOP_FRAC,
    t1_frac: float = STEP_T1_FRAC,
    t2_frac: float = STEP_T2_FRAC,
    t3_frac: float = STEP_T3_FRAC,
) -> Optional[Dict]:
    """Build a step-scaled stop/target ladder from session bars.

    Returns dict with stop, t1, t2, t3, median_step, or None if
    median_step unavailable.
    """
    median = compute_median_session_step(bars, direction)
    if median is None or median <= 0:
        return None

    sign = 1.0 if direction == "LONG" else -1.0
    stop_dist = max(stop_floor, stop_frac * median)

    result = {
        "stop": _snap(entry_price - sign * stop_dist),
        "t1": _snap(entry_price + sign * t1_frac * median),
        "t2": _snap(entry_price + sign * t2_frac * median),
        "t3": _snap(entry_price + sign * t3_frac * median),
        "median_step": median,
        "stop_dist": round(stop_dist, 2),
    }

    logger.info(
        "[StepLadder] %s entry=%.2f median_step=%.2f → stop=%.2f (%.1fpt) "
        "t1=%.2f t2=%.2f t3=%.2f",
        direction, entry_price, median,
        result["stop"], stop_dist,
        result["t1"], result["t2"], result["t3"])

    return result
