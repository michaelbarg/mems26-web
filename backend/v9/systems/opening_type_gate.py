"""opening_type_gate — blocks counter-drive fires during the opening window.

#68 FIX B. Governs ONLY RTH open → IB-lock (~60min). After IB-lock, inert.

Rules:
  OPEN_DRIVE / OPEN_TEST_DRIVE → ALLOW with-drive, BLOCK counter-drive.
  OPEN_AUCTION / rotation       → HOLD all fires (no edge).
  Drive fails (returned_through_open) → release.

Flag: OPENING_TYPE_GATE (default OFF). Fail-open on missing data.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# How many bars constitute a "drive detection window" (30 min = 6 bars of 5min)
_DRIVE_DETECT_BARS = 6


def _enabled() -> bool:
    return os.environ.get("OPENING_TYPE_GATE", "0").lower() in ("1", "true", "yes")


def decide(
    *,
    direction: str,
    rth_bars: List[Dict],
    ib_locked: bool,
    opening_print: Optional[float] = None,
) -> Tuple[bool, str]:
    """Decide whether to allow/block a fire based on opening-type analysis.

    Args:
        direction: "LONG" or "SHORT"
        rth_bars: RTH 5-min bars accumulated so far [{o,h,l,c,...}]
        ib_locked: True after IB lock (60 min) → gate becomes inert
        opening_print: first RTH bar's open price

    Returns:
        (allow: bool, reason: str)
    """
    if not _enabled():
        return (True, "gate OFF")

    # After IB lock → inert (position gate takes over)
    if ib_locked:
        return (True, "post-IB-lock (inert)")

    if not rth_bars:
        return (True, "no RTH bars yet (fail-open)")

    dir_upper = direction.upper()

    # Determine opening print
    if opening_print is None:
        opening_print = rth_bars[0].get("o", rth_bars[0].get("open"))
    if opening_print is None:
        return (True, "no opening print (fail-open)")

    n = len(rth_bars)

    # Detect drive direction
    if n >= _DRIVE_DETECT_BARS:
        # Use opening_detector_v2 for classification
        drive_type, drive_dir = _detect_from_bars(rth_bars[:_DRIVE_DETECT_BARS], opening_print)
    else:
        # Early bars: use running bias = sign(last_close − opening_print)
        drive_type, drive_dir = _early_bias(rth_bars, opening_print)

    # Check if drive has failed (price returned through opening print)
    if _drive_failed(rth_bars, opening_print):
        return (True, f"drive failed (returned through open) — released")

    # Apply rules based on opening type
    if drive_type in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "EARLY_BIAS"):
        if drive_dir == "UP":
            if dir_upper == "SHORT":
                return (False, f"counter-drive: SHORT against {drive_type} UP")
            return (True, f"with-drive: LONG with {drive_type} UP")
        elif drive_dir == "DOWN":
            if dir_upper == "LONG":
                return (False, f"counter-drive: LONG against {drive_type} DOWN")
            return (True, f"with-drive: SHORT with {drive_type} DOWN")
        # NEUTRAL direction on a drive → fail-open
        return (True, f"{drive_type} direction NEUTRAL (fail-open)")

    if drive_type in ("OPEN_AUCTION_IN", "OPEN_AUCTION_OUT", "OPEN_AUCTION"):
        return (False, f"HOLD: {drive_type} — no opening edge (rotation)")

    if drive_type == "OPEN_REJECTION_REVERSE":
        # ORR: the reversal direction is the drive direction
        if drive_dir == "UP" and dir_upper == "SHORT":
            return (False, f"counter-drive: SHORT against ORR UP")
        if drive_dir == "DOWN" and dir_upper == "LONG":
            return (False, f"counter-drive: LONG against ORR DOWN")
        return (True, f"with-drive: {dir_upper} with ORR {drive_dir}")

    # UNKNOWN → fail-open
    return (True, f"opening_type={drive_type} (fail-open)")


def _detect_from_bars(
    bars: List[Dict], opening_print: float
) -> Tuple[str, str]:
    """Use opening_detector_v2 on the first 6 RTH bars."""
    try:
        from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
        result = detect_opening_type(bars, opening_print)
        return result.get("opening_type", "UNKNOWN"), result.get("direction", "NEUTRAL")
    except Exception:
        return "UNKNOWN", "NEUTRAL"


def _early_bias(
    bars: List[Dict], opening_print: float
) -> Tuple[str, str]:
    """Before 6 bars: running bias from sign(last_close − opening_print)."""
    last_close = bars[-1].get("c", bars[-1].get("close"))
    if last_close is None:
        return "UNKNOWN", "NEUTRAL"

    diff = last_close - opening_print
    if abs(diff) < 1.0:  # less than 1pt → no clear bias
        return "UNKNOWN", "NEUTRAL"

    direction = "UP" if diff > 0 else "DOWN"
    return "EARLY_BIAS", direction


def _drive_failed(bars: List[Dict], opening_print: float) -> bool:
    """Check if the drive has failed: price drove away then returned through the open.

    A failed drive = at least 3 bars of directional move from the open,
    then the close returns to the other side of the opening print.
    """
    if len(bars) < 4:
        return False

    closes = [b.get("c", b.get("close")) for b in bars]
    closes = [c for c in closes if c is not None]
    if len(closes) < 4:
        return False

    # Check first 3 closes for a directional move
    first_3 = closes[:3]
    all_above = all(c > opening_print for c in first_3)
    all_below = all(c < opening_print for c in first_3)

    if not (all_above or all_below):
        return False

    # Check if later close returned through the open
    last_close = closes[-1]
    if all_above and last_close < opening_print:
        return True
    if all_below and last_close > opening_print:
        return True

    return False
