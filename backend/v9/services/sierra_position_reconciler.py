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
STATE_FILE = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/sierra_state.json"))
STATE_MAX_AGE_S = 10.0  # fresher than this → authoritative


def _sierra_state_qty() -> Optional[int]:
    """FIX-13: read the net position from the DLL's sierra_state.json —
    second-fresh native truth, immune to the activity-log parsing family
    (wrong account file, duplicate feeders, sim files without position
    lines — all three bit on 07-10). Only trusted when the file is fresh
    (≤10s); stale/missing → None so the caller falls back to the events
    journal. Honest None on any parse gap (Rule 1)."""
    try:
        if not STATE_FILE.exists():
            return None
        import time as _t
        if (_t.time() - STATE_FILE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        data = json.loads(STATE_FILE.read_text().strip() or "{}")
        qty = data.get("position_qty")
        return int(qty) if qty is not None else None
    except (OSError, ValueError, TypeError):
        return None


def _sierra_state_working() -> Optional[int]:
    """working_orders from the fresh state file; None if stale/absent (Rule 1)."""
    try:
        if not STATE_FILE.exists():
            return None
        import time as _t
        if (_t.time() - STATE_FILE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        data = json.loads(STATE_FILE.read_text().strip() or "{}")
        w = data.get("working_orders")
        return int(w) if w is not None else None
    except (OSError, ValueError, TypeError):
        return None


# Phantom-heal: consecutive checks where TM is in-position but Sierra is
# definitively flat (qty=0, working=0). Reset on any other outcome.
_phantom_flat_streak = 0


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
    # FIX-13: prefer the DLL's native state export when fresh; fall back to
    # the parsed activity journal only when sierra_state.json is absent/stale.
    src = "state"
    sierra_qty = _sierra_state_qty()
    if sierra_qty is None:
        src = "events"
        sierra_qty = _sierra_position_qty()
    if sierra_qty is None:
        return True, "no Sierra position data (state file + events file empty)"

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
            for tgt in ("t1_hit_ts", "t2_hit_ts", "t3_hit_ts", "t4_hit_ts"):
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

    global _phantom_flat_streak
    if tm_qty == sierra_qty:
        _phantom_flat_streak = 0
        return True, f"MATCH: TM={tm_qty} Sierra={sierra_qty} (src={src})"

    # ── PHANTOM-HEAL (Michael 07-13, PHANTOM_HEAL_V1) ──────────────────────
    # A trade FILLED in the backend with NO real Sierra fill (op=PLACE that
    # recorded an ENTRY-fill but never opened a position) stays active forever:
    # target-hit detection awaits real Sierra fills (I-62-FULL), none come, the
    # slot is blocked, and no new trades can fire (the 07-13 sim-day loss).
    # When Sierra is DEFINITIVELY flat (state-file qty=0 AND working=0) for
    # >=N consecutive checks while the backend is in-position, the backend is
    # wrong → close the phantom trade(s) and free the slot. Conservative to
    # avoid the OPPOSITE (07-10 phantom-CLOSE of a REAL trade): requires the
    # FRESH state file (not the events journal), zero working orders, and a
    # sustained streak — a momentary flat never triggers it. Flag default OFF.
    _heal_on = os.getenv("PHANTOM_HEAL_V1", "0").lower() in ("1", "true", "yes")
    _need = int(os.getenv("PHANTOM_HEAL_STREAK", "3"))
    _working = _sierra_state_working()
    if _heal_on and src == "state" and sierra_qty == 0 and _working == 0 and tm_qty != 0:
        _phantom_flat_streak += 1
        if _phantom_flat_streak >= _need:
            healed = []
            try:
                for t in (tm.get_active_trades() or []):
                    if getattr(t, "mode", "shadow") not in ("demo", "live"):
                        continue
                    if getattr(t, "state", "") in ("CLOSED", "CANCELLED"):
                        continue
                    tid = getattr(t, "id", None)
                    if tid is None:
                        continue
                    if hasattr(tm, "close_trade"):
                        tm.close_trade(int(tid), reason="phantom_reconcile")
                        healed.append(int(tid))
            except Exception as _he:
                logger.warning("[Reconciler] phantom-heal close error: %s", _he)
            _phantom_flat_streak = 0
            hmsg = (f"PHANTOM-HEAL: Sierra flat {_need}x (qty=0,working=0) but backend "
                    f"held {tm_trades} → closed phantom {healed}, slot freed.")
            logger.warning("[Reconciler] SYS-3 %s", hmsg)
            try:
                from backend.v9.services.phone_alert import push as _pp
                _pp("phantom_heal", "♻️ MEMS26: phantom נוקה", hmsg, priority=0)
            except Exception:
                pass
            return True, hmsg
    elif sierra_qty != 0:
        # Sierra is definitively NOT flat — the phantom condition is genuinely
        # over.  Reset.  (Michael 07-15 fix: only reset when Sierra proves it's
        # not flat.  A stale state file / heal-flag-off / momentary working!=0
        # should NOT wipe accumulated evidence — that caused 0/3 stuck loops.)
        _phantom_flat_streak = 0

    msg = (f"DIVERGENCE: TM says {tm_qty} contracts {tm_trades}, "
           f"Sierra says {sierra_qty} (src={src}). Records ≠ reality!"
           + (f" [phantom-heal streak {_phantom_flat_streak}/{_need}]" if _heal_on else ""))
    logger.warning("[Reconciler] SYS-3 %s", msg)
    # IDEA-2 (Michael 07-13): records≠reality is exactly what he must know about
    # when away from the screen. Rate-limited inside push(); never raises.
    try:
        from backend.v9.services.phone_alert import push as _phone_push
        _phone_push("reconciler_divergence", "🔴 MEMS26: DIVERGENCE", msg, priority=1)
    except Exception:
        pass
    return False, msg
