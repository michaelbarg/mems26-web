"""Opening windows — tiered time windows per opening type (Dalton Step 2).

Each opening type has a characteristic resolution time:
  OPEN_DRIVE            :  5–15 min (1–3 bars) — resolves fast, drives away
  OPEN_TEST_DRIVE       : 10–20 min (2–4 bars) — poke + reversal + drive
  OPEN_REJECTION_REVERSE: 15–30 min (3–6 bars) — needs the full reversal
  OPEN_AUCTION_IN/OUT   : 30+  min (6+ bars)   — rotational, slow resolution

The engine evaluates per-bar: given the current opening_type and elapsed
bars since RTH open, it returns a window phase:
  DEVELOPING — opening still forming, wait for confirmation
  CONFIRMED  — window elapsed, opening type is reliable
  STALE      — opening type was reclassified (re-eval triggered)

Drive location filter (OPEN_DRIVE only):
  Far from 7-day value area → high conviction (real directional move)
  At balance edge           → exhaustion suspicion (reduce conviction)

Pure detection — no behavior change. Flag: OPENING_WINDOWS_V1 (OFF).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


# ── Time windows (in 5-min bars) ──
WINDOWS = {
    "OPEN_DRIVE":              (1, 3),   #  5–15 min
    "OPEN_TEST_DRIVE":         (2, 4),   # 10–20 min
    "OPEN_REJECTION_REVERSE":  (3, 6),   # 15–30 min
    "OPEN_AUCTION_IN":         (6, 12),  # 30–60 min
    "OPEN_AUCTION_OUT":        (6, 12),  # 30–60 min
}

DEFAULT_WINDOW = (3, 6)  # fallback for unknown types


@dataclass
class WindowState:
    """Current state of the opening window evaluation."""
    opening_type: str
    phase: str              # DEVELOPING / CONFIRMED / STALE
    bars_elapsed: int
    window_min: int         # minimum bars for confirmation
    window_max: int         # maximum bars (fully resolved)
    confidence_pct: float   # 0.0–1.0 confidence in the opening type
    drive_location: Optional[str] = None  # "VALUE_DRIVEN" / "EXHAUSTION_RISK" / None


def evaluate_window(
    *,
    opening_type: str,
    bars_since_open: int,
    opening_changed: bool = False,
) -> WindowState:
    """Evaluate the opening window phase for the current bar.

    Args:
        opening_type: current classification (OPEN_DRIVE, etc.)
        bars_since_open: number of 5-min bars since RTH open (09:30 ET)
        opening_changed: True if opening_type changed from previous bar

    Returns:
        WindowState with phase, confidence, and window bounds.
    """
    win_min, win_max = WINDOWS.get(opening_type, DEFAULT_WINDOW)

    if opening_changed:
        phase = "STALE"
        confidence = 0.3  # reclassified → low confidence until re-confirmed
    elif bars_since_open < win_min:
        phase = "DEVELOPING"
        confidence = 0.2 + 0.3 * (bars_since_open / win_min)  # ramps 0.2→0.5
    elif bars_since_open < win_max:
        phase = "DEVELOPING"
        confidence = 0.5 + 0.3 * ((bars_since_open - win_min) / max(win_max - win_min, 1))
    else:
        phase = "CONFIRMED"
        confidence = 0.8 + 0.2 * min((bars_since_open - win_max) / 6, 1.0)  # ramps to 1.0

    return WindowState(
        opening_type=opening_type,
        phase=phase,
        bars_elapsed=bars_since_open,
        window_min=win_min,
        window_max=win_max,
        confidence_pct=round(confidence, 3),
    )


def evaluate_drive_location(
    *,
    opening_type: str,
    open_price: float,
    current_price: float,
    balance7: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Classify OPEN_DRIVE location relative to 7-day value area.

    Returns:
        "VALUE_DRIVEN"    — drive moves AWAY from value (real directional move)
        "EXHAUSTION_RISK" — drive at balance edge (potential exhaustion)
        None              — not OPEN_DRIVE or insufficient data
    """
    if "DRIVE" not in (opening_type or ""):
        return None
    if balance7 is None:
        return None

    b7_range = balance7.get("range") or []
    b7_value = balance7.get("value") or []
    if len(b7_range) < 2 or len(b7_value) < 2:
        return None
    if any(v is None for v in b7_range + b7_value):
        return None

    range_low, range_high = float(b7_range[0]), float(b7_range[1])
    val, vah = float(b7_value[0]), float(b7_value[1])
    value_width = vah - val
    if value_width <= 0:
        return None

    # Is the drive moving away from value?
    drive_up = current_price > open_price
    above_vah = current_price > vah
    below_val = current_price < val

    if drive_up and above_vah:
        # Driving UP above the value area → real breakout
        dist_from_value = current_price - vah
        if dist_from_value > 0.3 * value_width:
            return "VALUE_DRIVEN"

    if not drive_up and below_val:
        # Driving DOWN below value area → real breakdown
        dist_from_value = val - current_price
        if dist_from_value > 0.3 * value_width:
            return "VALUE_DRIVEN"

    # At balance edge: price near VAH/VAL (within 30% of value width)
    near_vah = abs(current_price - vah) <= 0.3 * value_width
    near_val = abs(current_price - val) <= 0.3 * value_width
    at_range_edge = (current_price >= range_high - 0.1 * value_width or
                     current_price <= range_low + 0.1 * value_width)

    if (near_vah or near_val) and at_range_edge:
        return "EXHAUSTION_RISK"

    return None


def evaluate_opening_live(
    *,
    opening_type: str,
    bars_since_open: int,
    opening_changed: bool = False,
    open_price: Optional[float] = None,
    current_price: Optional[float] = None,
    balance7: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Combined evaluation for radar/API consumption.

    Returns dict with window phase + drive location.
    """
    ws = evaluate_window(
        opening_type=opening_type,
        bars_since_open=bars_since_open,
        opening_changed=opening_changed,
    )

    drive_loc = None
    if open_price and current_price:
        drive_loc = evaluate_drive_location(
            opening_type=opening_type,
            open_price=open_price,
            current_price=current_price,
            balance7=balance7,
        )
    ws.drive_location = drive_loc

    return {
        "opening_type": ws.opening_type,
        "phase": ws.phase,
        "bars_elapsed": ws.bars_elapsed,
        "window": f"{ws.window_min * 5}-{ws.window_max * 5}min",
        "confidence": ws.confidence_pct,
        "drive_location": ws.drive_location,
    }
