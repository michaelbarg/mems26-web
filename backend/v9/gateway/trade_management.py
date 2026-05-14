"""ζ.C2 + ζ.C4-C7 — Trade Management "Don't Give Back" Rules.

7 rules total (C.1 Smart BE + C.3 Time Stops already present):
  C.2  Trailing stop on T3 fill
  C.4  Lock-in at 2R: move stop to lock 1R profit
  C.5  Scale-out at T2: exit 1 contract at T2, trail remainder
  C.6  Time decay: if no progress in 10 bars, tighten stop to midpoint
  C.7  Reversal signal exit: if opposing system fires, close immediately
"""
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def apply_trailing_stop(trade: dict, current_bar: dict) -> Optional[dict]:
    """C.2: After T2 fill with C3 still live, enable trailing stop.

    Trail by high watermark minus trail_offset (🟡 2pt default for MES).
    """
    t2_hit = trade.get("t2_hit_ts")
    t3_hit = trade.get("t3_hit_ts")
    if not t2_hit or t3_hit:
        return None  # T2 not hit yet, or T3 already filled

    direction = trade.get("direction")
    current_stop = trade.get("stop", trade.get("stop_price", 0))
    trail_offset = 2.0  # 🟡 MES default — calibrate post-SHADOW

    if direction == "LONG":
        high = current_bar.get("high", current_bar.get("h", 0))
        new_stop = high - trail_offset
        if new_stop > current_stop:
            return {
                "new_stop": round(new_stop, 2),
                "rule": "C2_TRAILING_T3",
                "reasoning_notes": f"Trailing stop: high={high:.2f} - {trail_offset}pt = {new_stop:.2f} (was {current_stop:.2f})",
            }
    elif direction == "SHORT":
        low = current_bar.get("low", current_bar.get("l", 0))
        new_stop = low + trail_offset
        if new_stop < current_stop:
            return {
                "new_stop": round(new_stop, 2),
                "rule": "C2_TRAILING_T3",
                "reasoning_notes": f"Trailing stop: low={low:.2f} + {trail_offset}pt = {new_stop:.2f} (was {current_stop:.2f})",
            }
    return None


def apply_lockin_2r(trade: dict, current_price: float) -> Optional[dict]:
    """C.4: At 2R profit, lock in 1R by moving stop."""
    entry = trade.get("entry_price", 0)
    stop = trade.get("stop", trade.get("stop_price", 0))
    direction = trade.get("direction")
    if not entry or not stop:
        return None

    risk = abs(entry - stop)
    if risk <= 0:
        return None

    if direction == "LONG":
        r_multiple = (current_price - entry) / risk
        if r_multiple >= 2.0 and stop < entry + risk:
            new_stop = entry + risk  # lock 1R
            return {
                "new_stop": round(new_stop, 2),
                "rule": "C4_LOCKIN_2R",
                "reasoning_notes": f"Lock-in at 2R: price={current_price:.2f}, R={r_multiple:.1f}, locking 1R at {new_stop:.2f}",
            }
    elif direction == "SHORT":
        r_multiple = (entry - current_price) / risk
        if r_multiple >= 2.0 and stop > entry - risk:
            new_stop = entry - risk
            return {
                "new_stop": round(new_stop, 2),
                "rule": "C4_LOCKIN_2R",
                "reasoning_notes": f"Lock-in at 2R: price={current_price:.2f}, R={r_multiple:.1f}, locking 1R at {new_stop:.2f}",
            }
    return None


def check_time_decay(trade: dict, bars_since_entry: int) -> Optional[dict]:
    """C.6: If no progress in 10 bars, tighten stop to entry-stop midpoint."""
    if bars_since_entry < 10:
        return None

    entry = trade.get("entry_price", 0)
    stop = trade.get("stop", trade.get("stop_price", 0))
    current_price = trade.get("last_price", entry)
    direction = trade.get("direction")

    # Check if trade has made progress
    if direction == "LONG" and current_price > entry + 1.0:
        return None  # Has progress, no decay
    if direction == "SHORT" and current_price < entry - 1.0:
        return None

    # Tighten to midpoint
    midpoint = round((entry + stop) / 2, 2)
    return {
        "new_stop": midpoint,
        "rule": "C6_TIME_DECAY",
        "reasoning_notes": f"Time decay: {bars_since_entry} bars, no progress, tightening to midpoint {midpoint}",
    }


def check_reversal_exit(trade: dict, opposing_fire: Optional[dict]) -> Optional[dict]:
    """C.7: If opposing system fires in reverse direction, close immediately."""
    if not opposing_fire:
        return None

    trade_dir = trade.get("direction")
    fire_dir = opposing_fire.get("direction")

    if trade_dir and fire_dir and trade_dir != fire_dir:
        return {
            "action": "CLOSE",
            "rule": "C7_REVERSAL_EXIT",
            "reasoning_notes": f"Opposing fire {opposing_fire.get('signal', '?')} {fire_dir} vs trade {trade_dir} → close",
        }
    return None
