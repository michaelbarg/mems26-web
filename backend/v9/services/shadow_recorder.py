"""T-153: record_shadow_event — durable shadow ledger writer.

Every shadow branch calls this to record what it WOULD have done.
Never raises (swallowed pattern, like candidate_ledger.py:248).
Never touches the live trading path.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def record_shadow_event(
    *,
    flag: str,
    pattern: Optional[str] = None,
    direction: Optional[str] = None,
    price: Optional[float] = None,
    decision: str = "SHADOW",
    pnl_sim: Optional[float] = None,
    unit: Optional[str] = None,
    outcome: Optional[str] = None,
    trade_id: Optional[int] = None,
    session_date: Optional[str] = None,
) -> None:
    """Write one shadow event to v9_shadow_events. Never raises."""
    try:
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            "INSERT INTO v9_shadow_events "
            "(ts, session_date, flag, trade_id, pattern, direction, price, "
            "decision, pnl_sim, unit, outcome) "
            "VALUES (now(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_date, flag, trade_id, pattern, direction, price,
             decision, pnl_sim, unit, outcome),
        )
    except Exception as e:
        logger.debug("[ShadowRecorder] write failed (non-fatal): %s", e)
