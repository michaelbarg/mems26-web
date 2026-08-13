"""v9_day_type_state persist — extracted from backend/main.py (K2, 2026-08-08).

Write-on-change persist for the day-type writer (single writer, 07-15 decision
4/6). Extracted so the ARM-AFTER-SUCCESS rule is regression-testable:

K2 root defect: main.py armed the write-on-change signature
(`app_state._last_dts_sig = sig`) BEFORE the INSERT. When the INSERT failed
(safe_execute returns None on failure — it never raises), the signature was
already armed, so every following bar with the same state hit the skip branch
and the row was NEVER written — the writer looked dead until the state next
changed (Friday 08-07: 54-60 min gaps during RTH). The fix: the signature is
armed ONLY after a successful INSERT; a failed write leaves it unchanged so
the very next bar retries.

Never raises: returns a status string; all failures are logged WARNINGs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("mems26")

# Status values returned by persist_state_row
SKIPPED = "skipped"            # write-on-change: state unchanged since last row
WRITTEN = "written"            # extended (migration 022) column set written
WRITTEN_LEGACY = "written_legacy"  # legacy column set written (022 missing)
FAILED = "failed"              # both INSERTs failed — sig NOT armed, retry next bar


def compute_sig(state: Any) -> tuple:
    """The write-on-change signature: a row means something moved."""
    return (
        state.day_type.value if hasattr(state.day_type, "value") else str(state.day_type),
        state.stage.value if hasattr(state.stage, "value") else str(state.stage),
        round(float(state.confidence or 0.0), 2),
        str(state.lock_state),
    )


def persist_state_row(
    app_state: Any,
    state: Any,
    opening_type: str,
    last_cls_result: Optional[dict],
    session_date_iso: str,
) -> str:
    """Persist one v9_day_type_state row (write-on-change).

    Returns SKIPPED / WRITTEN / WRITTEN_LEGACY / FAILED. Never raises.
    """
    try:
        from backend.v9.db.safe_writer import safe_execute

        # H2 heartbeat (2026-08-13): update a timestamp on EVERY call (even
        # when write-on-change skips). The watchdog reads this to distinguish
        # "writer alive but idle (state unchanged)" from "writer dead (no bars)".
        import time as _hb_time
        app_state._daytype_writer_heartbeat = _hb_time.time()

        cur_sig = compute_sig(state)
        if getattr(app_state, "_last_dts_sig", None) == cur_sig:
            return SKIPPED

        dts_row = (
            datetime.now(timezone.utc).isoformat(),
            state.stage.value if hasattr(state.stage, "value") else str(state.stage),
            state.day_type.value if hasattr(state.day_type, "value") else str(state.day_type),
            state.day_type.value if state.lock_state == "LOCKED" else None,
            state.confidence,
            state.ib_width.value if hasattr(state.ib_width, "value") else None,
            opening_type,
            state.behavior.value if hasattr(state.behavior, "value") else None,
            str(state.lock_state),
            datetime.now(timezone.utc).isoformat(),
        )
        # N1 RC#4 (migration 022): additive observability columns from TODAY's
        # canonical classify_session result (honest NULLs when absent/stale —
        # state_row_extras enforces the session_date freshness stamp, Rule 1).
        from backend.v9.systems.day_type.classifier_core import state_row_extras
        xtr = state_row_extras(last_cls_result, session_date_iso)

        ins = safe_execute(
            """INSERT INTO v9_day_type_state (ts, stage, day_type, classification, confidence,
               ib_width_class, opening_type, behavior, lock_state, created_at,
               direction, reason, sides, rib)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            dts_row + (xtr["direction"], xtr["reason"], xtr["sides"], xtr["rib"]),
        )
        if ins is not None:
            app_state._last_dts_sig = cur_sig  # K2: arm ONLY after success
            return WRITTEN

        # Extended INSERT failed (e.g. migration 022 not applied on this DB
        # yet) — never let observability columns stop state persistence:
        # fall back to the legacy column set + loud warning (no silent drift).
        ins2 = safe_execute(
            """INSERT INTO v9_day_type_state (ts, stage, day_type, classification, confidence,
               ib_width_class, opening_type, behavior, lock_state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            dts_row,
        )
        if ins2 is not None:
            app_state._last_dts_sig = cur_sig  # K2: arm ONLY after success
            logger.warning(
                "[DayType] extended persist failed — wrote legacy columns; run "
                "backend/v9/db/migrations/versions/022_day_type_state_n1_columns.py")
            return WRITTEN_LEGACY

        # K2: BOTH inserts failed → sig stays un-armed so the next bar RETRIES
        # (pre-fix, the armed sig turned one transient DB error into a silent
        # write blackout until the state changed — the Friday 54-min gap class).
        logger.warning(
            "[DayType] persist FAILED (extended + legacy) — signature NOT armed, "
            "will retry on next bar")
        return FAILED
    except Exception as db_err:
        logger.warning("[DayType] DB persist skipped: %s", db_err, exc_info=True)
        return FAILED
