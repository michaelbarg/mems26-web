"""TSF (Trend Stop Floor) Shadow Log — records what the floor WOULD do.

Observability only: logs whether the floor would widen the stop, and by
how much, for each fire on a trend day. Does NOT change stops.
Flag: TSF_SHADOW_LOG_V1 (default OFF).

After 3 trading days → report → Michael rules on ignition.
"""

from __future__ import annotations

import logging
import os
import traceback
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_table_created = False


def log_tsf_shadow(
    *,
    trade_id: Optional[int],
    mode: str,
    direction: str,
    entry_price: float,
    stop: float,
    day_type: Optional[str] = None,
    day_direction: Optional[str] = None,
    ib_width: Optional[float] = None,
    t1_hit: bool = False,
) -> Optional[Dict]:
    """Log what trend stop floor would compute. Never raises."""
    if os.getenv("TSF_SHADOW_LOG_V1", "0").lower() not in ("1", "true", "yes"):
        return None
    try:
        result = _compute_tsf(
            direction=direction,
            entry_price=entry_price,
            stop=stop,
            day_type=day_type,
            day_direction=day_direction,
            ib_width=ib_width,
            t1_hit=t1_hit,
        )

        _persist(trade_id=trade_id, mode=mode, **result)
        return result
    except Exception:
        logger.debug("TSF shadow log error: %s", traceback.format_exc())
        return None


def _compute_tsf(*, direction, entry_price, stop, day_type,
                  day_direction, ib_width, t1_hit) -> Dict:
    """Compute trend stop floor without applying it."""
    is_trend = (day_type or "").startswith("Trend") or (
        (day_type or "").startswith("Variation") and day_direction and
        "with" in (day_direction or "").lower()
    )

    dir_up = direction == "LONG"
    trend_up = day_direction and "UP" in (day_direction or "").upper()
    with_trend = is_trend and (dir_up == trend_up)

    floor_pts = max(6.0, 0.15 * (ib_width or 40.0))
    current_risk = abs(entry_price - stop)

    would_apply = with_trend and not t1_hit and current_risk < floor_pts
    widened_stop = None
    delta_pts = 0.0

    if would_apply:
        sgn = 1.0 if direction == "LONG" else -1.0
        widened_stop = entry_price - sgn * floor_pts
        delta_pts = floor_pts - current_risk

    return {
        "direction": direction,
        "entry_price": entry_price,
        "stop": stop,
        "day_type": day_type,
        "is_trend": is_trend,
        "with_trend": with_trend,
        "ib_width": ib_width,
        "floor_pts": round(floor_pts, 2),
        "current_risk": round(current_risk, 2),
        "would_apply": would_apply,
        "widened_stop": round(widened_stop, 2) if widened_stop else None,
        "delta_pts": round(delta_pts, 2),
        "t1_hit": t1_hit,
    }


def _ensure_table():
    """Create v9_tsf_shadow_log if it doesn't exist (SA-2.0 safe)."""
    global _table_created
    if _table_created:
        return
    try:
        from sqlalchemy import text
        from backend.v9.db.session import engine
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS v9_tsf_shadow_log (
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMP DEFAULT NOW(),
                    trade_id INTEGER,
                    mode VARCHAR(10),
                    direction VARCHAR(10),
                    day_type VARCHAR(30),
                    is_trend BOOLEAN,
                    with_trend BOOLEAN,
                    ib_width FLOAT,
                    floor_pts FLOAT,
                    current_risk FLOAT,
                    would_apply BOOLEAN,
                    widened_stop FLOAT,
                    delta_pts FLOAT
                )
            """))
            conn.commit()
        _table_created = True
    except Exception:
        logger.debug("TSF shadow table creation failed: %s", traceback.format_exc())


def _persist(*, trade_id, mode, **data):
    """Write to v9_tsf_shadow_log (SA-2.0 compatible)."""
    try:
        from sqlalchemy import text
        from backend.v9.db.session import engine
        _ensure_table()
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO v9_tsf_shadow_log "
                    "(trade_id, mode, direction, day_type, is_trend, with_trend, "
                    "ib_width, floor_pts, current_risk, would_apply, widened_stop, delta_pts) "
                    "VALUES (:tid, :mode, :dir, :dt, :ist, :wt, :iw, :fp, :cr, :wa, :ws, :dp)"
                ),
                {
                    "tid": trade_id, "mode": mode, "dir": data.get("direction"),
                    "dt": data.get("day_type"), "ist": data.get("is_trend"),
                    "wt": data.get("with_trend"), "iw": data.get("ib_width"),
                    "fp": data.get("floor_pts"), "cr": data.get("current_risk"),
                    "wa": data.get("would_apply"), "ws": data.get("widened_stop"),
                    "dp": data.get("delta_pts"),
                },
            )
            conn.commit()
        logger.info("TSF_SHADOW: trade=%s would_apply=%s floor=%.1f risk=%.1f delta=%.1f",
                     trade_id, data.get("would_apply"), data.get("floor_pts", 0),
                     data.get("current_risk", 0), data.get("delta_pts", 0))
    except Exception:
        logger.debug("TSF shadow persist error: %s", traceback.format_exc())
