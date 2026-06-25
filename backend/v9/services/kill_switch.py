"""Kill-switch — instantly halt ALL firing (S2+S4) and resume.

One control to stop all trading activity. When engaged:
- Every gateway route_setup returns blocked_by="kill_switch"
- Logged + alerted

Thread-safe, in-memory state. Default: DISENGAGED.

API: POST /api/v9/admin/kill   → engage
     POST /api/v9/admin/resume → disengage
     GET  /api/v9/admin/kill   → status
CLI: python3 scripts/kill_switch.py engage|disengage|status
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger("kill_switch")

_lock = threading.Lock()
_state = {
    "engaged": False,
    "engaged_at": None,
    "engaged_by": None,
    "reason": None,
}


def engage(reason: str = "manual", by: str = "unknown") -> None:
    """Engage the kill-switch — halt ALL firing immediately."""
    with _lock:
        _state["engaged"] = True
        _state["engaged_at"] = time.time()
        _state["engaged_by"] = by
        _state["reason"] = reason
    logger.warning("[KillSwitch] ENGAGED by %s: %s", by, reason)
    try:
        from backend.v9.services.alerter import alert
        alert("KILL_SWITCH", "ENGAGED by %s: %s" % (by, reason), severity="critical")
    except Exception:
        pass


def disengage(by: str = "unknown") -> None:
    """Disengage the kill-switch — resume firing."""
    with _lock:
        _state["engaged"] = False
        _state["reason"] = None
    logger.warning("[KillSwitch] DISENGAGED by %s", by)


def is_engaged() -> Tuple[bool, Optional[str]]:
    """Check if the kill-switch is engaged. Returns (engaged, reason)."""
    with _lock:
        if _state["engaged"]:
            return (True, "KILL_SWITCH engaged: %s (by %s)" % (
                _state.get("reason", ""), _state.get("engaged_by", "")))
        return (False, None)


def status() -> dict:
    """Return current kill-switch state."""
    with _lock:
        return dict(_state)
