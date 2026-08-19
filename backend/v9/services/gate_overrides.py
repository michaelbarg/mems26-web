"""Phone-triggered gate overrides — Michael 2026-08-19:
"אני רוצה שתייצר מנגנון שיאפשר לי דרך האפליקציה לבטל חוסם".

Design:
- An override flips the gate's env flag IN-PROCESS ONLY (os.environ of the
  running backend). Every whitelisted gate reads its flag with os.getenv at
  call time (verified per-flag with grep on 2026-08-19), so the change takes
  effect on the next candidate — no restart, no .env edit, no flag_guard
  drift (flag_guard reads the FILE, which stays canonical).
- SESSION-SCOPED BY CONSTRUCTION: a backend restart re-applies .env, so every
  override dies with the process. That is the intended semantic — a phone
  override is "for now", never a standing ruling. Standing changes still go
  through Michael's written ruling + RULED_FLAGS.
- ONLY opinion gates are overridable. The safety set (kill switch, session
  clock, cold-start, feed watchdog, dedup, daily-loss halt, margin/entry
  guards, cluster guard) is deliberately NOT here and must never be added
  without a written ruling.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

#: blocked_by name → (env flag, value that disables the gate, Hebrew label)
#: Every flag here was verified to be read via os.getenv AT CALL TIME inside
#: trading_gateway (2026-08-19). Do not add a flag without that verification —
#: an import-time-cached flag would make the button a lie.
OVERRIDABLE: Dict[str, tuple] = {
    "lsma_flat":             ("LSMA_FLAT_GATE_V1", "0", "LSMA שטוח"),
    "extreme_chase_guard":   ("EXTREME_CHASE_GUARD_V1", "0", "רדיפת-קיצון"),
    "daytype_playbook":      ("DAYTYPE_PLAYBOOK", "0", "פלייבוק סוג-יום"),
    "cont_trend_filter":     ("CONT_TREND_FILTER", "0", "המשך-עם-מגמה"),
    "direction_context":     ("DIRECTION_CONTEXT", "0", "הקשר-כיוון"),
    "rr_entry_gate":         ("RR_ENTRY_GATE_V1", "0", "שער R:R"),
    "pattern_stop_cooldown": ("PATTERN_STOP_COOLDOWN_V1", "0", "צינון אחרי-סטופ"),
    "location_gate":         ("DAYTYPE_LOCATION_GATE", "0", "שער-מיקום (דלתון)"),
    "entry_not_confirmed":   ("S4_ENTRY_CONFIRM_V1", "0", "אישור-כניסה"),
}

# gate → {"flag":..., "was":..., "ts":...} — active overrides this process.
_active: Dict[str, dict] = {}


def set_override(gate: str) -> Optional[dict]:
    """Disable `gate` for the rest of this backend session. None = refused."""
    spec = OVERRIDABLE.get(gate)
    if spec is None:
        logger.warning("[GateOverride] REFUSED — '%s' is not an overridable "
                       "gate (safety set or unknown)", gate)
        return None
    flag, off_val, label = spec
    if gate not in _active:
        _active[gate] = {"flag": flag, "was": os.environ.get(flag),
                         "label": label,
                         "ts": time.strftime("%H:%M:%S")}
    os.environ[flag] = off_val
    logger.warning("[GateOverride] 🔓 Michael (phone): gate '%s' DISABLED "
                   "(%s=%s) — session-scoped, reverts on restart",
                   gate, flag, off_val)
    try:
        from scripts.ops_log import log_event
        log_event("gateway", "WARNING",
                  f"GATE OVERRIDE (phone): {gate} disabled ({flag}={off_val})")
    except Exception:
        pass
    return {"gate": gate, "flag": flag, "label": label}


def clear_override(gate: str) -> bool:
    """Restore the gate to its pre-override value."""
    rec = _active.pop(gate, None)
    if rec is None:
        return False
    if rec["was"] is None:
        os.environ.pop(rec["flag"], None)
    else:
        os.environ[rec["flag"]] = rec["was"]
    logger.warning("[GateOverride] 🔒 Michael (phone): gate '%s' RESTORED "
                   "(%s=%s)", gate, rec["flag"], rec["was"])
    return True


def active_overrides() -> list:
    return [{"gate": g, "label": r["label"], "flag": r["flag"], "ts": r["ts"]}
            for g, r in _active.items()]


def overridable_gates() -> list:
    return list(OVERRIDABLE.keys())
