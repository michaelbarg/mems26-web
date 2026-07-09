"""SYS-3: Sierra position reconciler — "records ≠ reality" killer.

FIX-6 (incident 333, Michael's explicit demand): the system must always know
what Sierra actually holds. Runs every ≤30s (fill_poller cycle or standalone),
compares TM open trades vs TradeActivityLog position state.

Divergence → WARNING (noisy) + freeze auto-actions on the trade.
Auto-adopt = next phase (Michael's ruling), not this version.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

EVENTS_FILE = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/trade_activity_events.jsonl"))


def _sierra_position_qty() -> Optional[int]:
    """Read the latest position quantity from trade_activity_events.jsonl.

    Returns the most recent POSITION_CHANGE new_qty, or None if no data.
    """
    if not EVENTS_FILE.exists():
        return None
    try:
        last_pos = None
        with open(EVENTS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if ev.get("type") == "POSITION_CHANGE":
                        last_pos = ev.get("new_qty")
                except json.JSONDecodeError:
                    continue
        return int(last_pos) if last_pos is not None else None
    except OSError:
        return None


def reconcile_position(tm) -> Tuple[bool, str]:
    """Compare TM open trades vs Sierra's actual position.

    Returns (ok, message). ok=False means divergence detected.
    """
    sierra_qty = _sierra_position_qty()
    if sierra_qty is None:
        return True, "no Sierra position data (events file empty)"

    # Count TM open contracts (demo + live, not shadow)
    tm_qty = 0
    tm_trades = []
    try:
        active = tm.get_active_trades() if hasattr(tm, "get_active_trades") else []
        for t in (active or []):
            mode = getattr(t, "mode", "shadow")
            if mode not in ("demo", "live"):
                continue
            state = getattr(t, "state", "")
            if state in ("CLOSED", "CANCELLED"):
                continue
            direction = str(getattr(t, "direction", "")).upper()
            from backend.v9.services.trade_manager.manager import trade_contract_count
            n = trade_contract_count(t)
            # Subtract hit targets
            for tgt in ("t1_hit_ts", "t2_hit_ts", "t3_hit_ts"):
                if getattr(t, tgt, None) is not None:
                    n -= 1
            n = max(0, n)
            if direction == "LONG":
                tm_qty += n
            elif direction == "SHORT":
                tm_qty -= n
            if n > 0:
                tm_trades.append(f"#{t.id}({mode},{direction},{n}c)")
    except Exception as e:
        logger.warning("[Reconciler] TM query error: %s", e)
        return True, f"TM query error: {e}"

    if tm_qty == sierra_qty:
        return True, f"MATCH: TM={tm_qty} Sierra={sierra_qty}"

    msg = (f"DIVERGENCE: TM says {tm_qty} contracts {tm_trades}, "
           f"Sierra says {sierra_qty}. Records ≠ reality!")
    logger.warning("[Reconciler] SYS-3 %s", msg)
    return False, msg
