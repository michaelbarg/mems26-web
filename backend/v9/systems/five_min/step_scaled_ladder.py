"""step_scaled_ladder — F3 STEP_SCALED_LADDER_V1 (2026-08-12, realigned 2026-08-13).

Three independent analyses converged:
  LEG_EXEMPTION_REPLAY §R2, TREND_STEP_ENTRY §9, SYSTEM4_AUDIT D4.

Problem: the detector's stop goes to the StopResolver which returns stops
sized by ATR (e.g. 0.8×ATR = 11pt on a 14pt ATR session). This produces
R=15 on a trend-day step of 11pt — no trade would ever bank.

Solution: scale stop and targets to the session's median step size.
  Stop = max(STEP_STOP_FLOOR, STEP_STOP_FRAC × median_step)
  T1 = 0.5 × median_step   (floored at min_rr × stop — see below)
  T2 = 1.0 × median_step
  T3 = 1.5 × median_step

REALIGNMENT (Michael 2026-08-13 "ליישר לפי רחב יותר", after
FIREPATH_PROOF_2026-08-12 found the mismatch):
  The original measure counted *extreme-advance increments* — every tick the
  session high/low advanced (median 2-3pt on 08-11) — while the replay-GO
  evidence (TREND_STEP_ENTRY §9) measured *zigzag swing legs* (median ~10.4pt
  on the same tape). stop=floor(4) with T1=0.5×2.5 gave RR 0.25-0.44 which
  rr_entry_gate rightly blocks — the ladder was mathematically impassable on
  Trend labels (cap 0.833 < rr_min 1.0).
  Now the step = zigzag leg amplitude (same construction as the §9 analysis,
  ZZ_REV default 5.0pt), legs in the trade direction, fallback to all legs.
  In addition T1 is structurally floored at min_rr × stop_dist so a ladder
  bracket can never fail the R:R gate it was built to pass.

Flag: STEP_SCALED_LADDER_V1 (default OFF; ruled ON 2026-08-12, realigned
2026-08-13 under the same ruling).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Tunable defaults (env-overridable in the gateway)
STEP_STOP_FLOOR = 4.0       # minimum stop in points
STEP_STOP_FRAC = 0.6        # stop = 60% of median step
STEP_T1_FRAC = 0.5          # T1 = 50% of step
STEP_T2_FRAC = 1.0          # T2 = 100% of step
STEP_T3_FRAC = 1.5          # T3 = 150% of step
STEP_ZZ_REV = 5.0           # pt — swing-reversal threshold (TREND_STEP §9 value)
TICK_SIZE = 0.25


def _hl(b: Dict) -> Tuple[float, float]:
    return (float(b.get("h", b.get("high", 0))),
            float(b.get("l", b.get("low", 0))))


def _zigzag(bars: List[Dict], rev: float) -> List[Tuple[int, float, str]]:
    """Causal zigzag pivots [(idx, price, 'H'|'L'), ...] — same construction
    as scripts/replay_trend_step_entry.py::zigzag (the §9 analysis)."""
    n = len(bars)
    if n < 2:
        return []
    hi_i, hi_p = 0, _hl(bars[0])[0]
    lo_i, lo_p = 0, _hl(bars[0])[1]
    direction = 0
    piv: List[Tuple[int, float, str]] = []
    start = n
    for i in range(1, n):
        h, l = _hl(bars[i])
        if h > hi_p:
            hi_i, hi_p = i, h
        if l < lo_p:
            lo_i, lo_p = i, l
        if hi_p - lo_p >= rev and hi_i != lo_i:
            if lo_i < hi_i:
                direction, piv = 1, [(lo_i, _hl(bars[lo_i])[1], "L")]
                hi_i, hi_p = lo_i, _hl(bars[lo_i])[0]
                for j in range(lo_i, i + 1):
                    hj = _hl(bars[j])[0]
                    if hj > hi_p:
                        hi_i, hi_p = j, hj
            else:
                direction, piv = -1, [(hi_i, _hl(bars[hi_i])[0], "H")]
                lo_i, lo_p = hi_i, _hl(bars[hi_i])[1]
                for j in range(hi_i, i + 1):
                    lj = _hl(bars[j])[1]
                    if lj < lo_p:
                        lo_i, lo_p = j, lj
            start = i + 1
            break
    if direction == 0:
        return []
    for i in range(start, n):
        h, l = _hl(bars[i])
        if direction == 1:
            if h > hi_p:
                hi_i, hi_p = i, h
            if i > hi_i and hi_p - l >= rev:
                piv.append((hi_i, hi_p, "H"))
                direction = -1
                lo_i, lo_p = i, l
                for j in range(hi_i + 1, i + 1):
                    lj = _hl(bars[j])[1]
                    if lj < lo_p:
                        lo_i, lo_p = j, lj
        else:
            if l < lo_p:
                lo_i, lo_p = i, l
            if i > lo_i and h - lo_p >= rev:
                piv.append((lo_i, lo_p, "L"))
                direction = 1
                hi_i, hi_p = i, h
                for j in range(lo_i + 1, i + 1):
                    hj = _hl(bars[j])[0]
                    if hj > hi_p:
                        hi_i, hi_p = j, hj
    piv.append((hi_i, hi_p, "H") if direction == 1 else (lo_i, lo_p, "L"))
    return piv


def compute_median_session_step(
    bars: List[Dict],
    direction: str = "LONG",
    *,
    zz_rev: float = STEP_ZZ_REV,
) -> Optional[float]:
    """Median swing-leg amplitude for today's session (the WIDE measure).

    A "step" is the amplitude of a completed zigzag leg (reversal threshold
    `zz_rev`). Legs ENDING in the trade direction are preferred (SHORT →
    down-legs ending at an L pivot; LONG → up-legs ending at an H pivot);
    if fewer than 3 such legs exist, all legs are used. Returns None if
    fewer than 3 legs total (fail-open: caller keeps its existing bracket).
    """
    if not bars or len(bars) < 5:
        return None

    piv = _zigzag(bars, float(zz_rev))
    if len(piv) < 2:
        return None

    want = "H" if str(direction).upper() == "LONG" else "L"
    directional: List[float] = []
    all_legs: List[float] = []
    for a, b in zip(piv, piv[1:]):
        amp = abs(b[1] - a[1])
        if amp <= 0:
            continue
        all_legs.append(amp)
        if b[2] == want:
            directional.append(amp)

    legs = directional if len(directional) >= 3 else all_legs
    if len(legs) < 3:
        return None

    legs.sort()
    mid = len(legs) // 2
    if len(legs) % 2 == 0:
        median = (legs[mid - 1] + legs[mid]) / 2.0
    else:
        median = legs[mid]

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
    zz_rev: float = STEP_ZZ_REV,
    min_rr: float = 0.0,
) -> Optional[Dict]:
    """Build a step-scaled stop/target ladder from session bars.

    `min_rr` (13.08): structural R:R floor — T1 distance is raised to at
    least min_rr × stop_dist (and T2/T3 keep ordering), so a ladder bracket
    can never fail rr_entry_gate by construction. 0.0 = no floor.

    Returns dict with stop, t1, t2, t3, median_step, or None if
    median_step unavailable.
    """
    median = compute_median_session_step(bars, direction, zz_rev=zz_rev)
    if median is None or median <= 0:
        return None

    sign = 1.0 if direction == "LONG" else -1.0
    stop_dist = max(stop_floor, stop_frac * median)

    # Snap the STOP first and measure the REAL (post-snap) stop distance —
    # the R:R gate downstream judges actual prices, so the T1 floor must be
    # computed against what will actually reach Sierra (13.08: nearest-tick
    # snapping on both legs let RR land at 0.997 and fail a 1.0 gate by a
    # quarter tick).
    stop_price = _snap(entry_price - sign * stop_dist)
    real_stop_dist = abs(entry_price - stop_price)

    t1_dist = t1_frac * median
    if min_rr > 0:
        t1_dist = max(t1_dist, min_rr * real_stop_dist)
        # ceil to the tick grid so post-snap RR can only round UP
        import math
        t1_dist = math.ceil(t1_dist / TICK_SIZE) * TICK_SIZE
    t2_dist = max(t2_frac * median, t1_dist)
    t3_dist = max(t3_frac * median, t2_dist)

    result = {
        "stop": stop_price,
        "t1": _snap(entry_price + sign * t1_dist),
        "t2": _snap(entry_price + sign * t2_dist),
        "t3": _snap(entry_price + sign * t3_dist),
        "median_step": median,
        "stop_dist": round(real_stop_dist, 2),
    }

    logger.info(
        "[StepLadder] %s entry=%.2f median_step=%.2f (zz_rev=%.1f, min_rr=%.2f) → "
        "stop=%.2f (%.1fpt) t1=%.2f t2=%.2f t3=%.2f",
        direction, entry_price, median, zz_rev, min_rr,
        result["stop"], stop_dist,
        result["t1"], result["t2"], result["t3"])

    return result
