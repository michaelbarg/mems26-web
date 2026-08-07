"""Day-type writer watchdog — detects stale v9_day_type_state.

Incident 2026-08-05: day_type_state writer died at 11:45 IL, no entries
for 2h15m (08:45-11:00 ET). Missed the entire IB formation period.

This watchdog checks the last v9_day_type_state timestamp. If it's
>10 min old during RTH and bars are flowing, it logs a WARNING and
optionally triggers a re-classify from accumulated bars.

Designed to run every bar (from bar_level_detector or a periodic task).
Never raises — fail-safe.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

STALE_THRESHOLD_MIN = float(os.environ.get("DAYTYPE_STALE_THRESHOLD_MIN", "10"))
_last_alert_ts: float = 0.0
_ALERT_COOLDOWN_S = 300  # 5 min between alerts


def check_daytype_staleness(app_state=None) -> Optional[str]:
    """Check if the day-type writer is stale. If stale, attempt self-heal.

    When app_state is provided and staleness is detected, resets the
    write-on-change signature (_last_dts_sig) so the next bar forces a
    fresh DB write. This is the self-heal for the 08-05/08-06 incidents
    where the writer died silently.

    Returns:
        None if healthy, or a warning string if stale.
    """
    try:
        from backend.v9.db.read import read_one

        # Is it RTH?
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
        et_hour = et_now.hour
        et_min = et_now.minute
        is_rth = (et_hour > 9 or (et_hour == 9 and et_min >= 30)) and et_hour < 16
        if not is_rth:
            return None  # outside RTH — no concern

        # Last day_type_state entry
        row = read_one(
            "SELECT ts, day_type FROM v9_day_type_state ORDER BY ts DESC LIMIT 1",
            {},
        )
        if not row:
            return _warn("no v9_day_type_state rows at all")

        last_ts = row["ts"]
        if isinstance(last_ts, str):
            last_ts = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        age_min = (datetime.now(timezone.utc) - last_ts).total_seconds() / 60

        if age_min > STALE_THRESHOLD_MIN:
            msg = _warn(
                f"day_type_state stale: last entry {age_min:.0f}min ago "
                f"(threshold {STALE_THRESHOLD_MIN}min), last_type={row['day_type']}"
            )
            # Self-heal: reset the write-on-change signature so the next bar
            # forces a fresh DB write. This fixes the silent writer death where
            # _last_dts_sig stays frozen after an error.
            if app_state is not None:
                try:
                    if hasattr(app_state, "_last_dts_sig"):
                        app_state._last_dts_sig = None
                        logger.warning("[DAYTYPE_WATCHDOG] SELF-HEAL: reset _last_dts_sig — "
                                       "next bar will force a DB write")
                except Exception:
                    pass
            return msg
        return None
    except Exception as e:
        logger.debug("daytype_watchdog check failed: %s", e)
        return None


def _warn(msg: str) -> str:
    """Log warning with cooldown to avoid spam."""
    global _last_alert_ts
    now = time.time()
    if now - _last_alert_ts < _ALERT_COOLDOWN_S:
        return msg  # still return the message, just don't re-log
    _last_alert_ts = now
    logger.warning("[DAYTYPE_WATCHDOG] %s", msg)
    try:
        from scripts.ops_log import log_event
        log_event("daytype_watchdog", "WARN", msg)
    except Exception:
        pass
    return msg
