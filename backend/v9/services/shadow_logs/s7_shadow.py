"""S7 Shadow Log — records what S7 scoring WOULD decide on each fire.

Observability only: logs score/sizing/blocked to v9_s7_shadow_log table.
Does NOT change any trading behavior. Flag: S7_SHADOW_LOG_V1 (default OFF).

After 3 trading days of shadow data → report → Michael rules on ignition.
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_table_created = False


def log_s7_shadow(
    *,
    trade_id: Optional[int],
    mode: str,
    setup: Dict[str, Any],
    market_context: Optional[Any] = None,
    bar_ts: Optional[datetime] = None,
    outcome: Optional[str] = None,
) -> Optional[Dict]:
    """Log what S7 would score for this fire. Never raises."""
    if os.getenv("S7_SHADOW_LOG_V1", "0").lower() not in ("1", "true", "yes"):
        return None
    try:
        from backend.v9.systems.system7_score import score as s7_score
        result = s7_score(setup=setup, market_context=market_context, bar_ts=bar_ts)

        _persist(
            trade_id=trade_id,
            mode=mode,
            direction=setup.get("direction"),
            pattern=setup.get("pattern", setup.get("classification", "")),
            entry_price=setup.get("entry_price"),
            score=result.get("score"),
            sizing=result.get("sizing"),
            blocked=result.get("blocked", False),
            components=result.get("components"),
            outcome=outcome,
        )
        return result
    except Exception:
        logger.debug("S7 shadow log error: %s", traceback.format_exc())
        return None


def _ensure_table():
    """Create v9_s7_shadow_log if it doesn't exist (SA-2.0 safe)."""
    global _table_created
    if _table_created:
        return
    try:
        from sqlalchemy import text
        from backend.v9.db.session import engine
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS v9_s7_shadow_log (
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMP DEFAULT NOW(),
                    trade_id INTEGER,
                    mode VARCHAR(10),
                    direction VARCHAR(10),
                    pattern VARCHAR(40),
                    entry_price FLOAT,
                    score FLOAT,
                    sizing INTEGER,
                    blocked BOOLEAN,
                    components JSON,
                    outcome VARCHAR(10)
                )
            """))
            conn.commit()
        _table_created = True
    except Exception:
        logger.debug("S7 shadow table creation failed: %s", traceback.format_exc())


def _persist(*, trade_id, mode, direction, pattern, entry_price,
             score, sizing, blocked, components, outcome):
    """Write to v9_s7_shadow_log (SA-2.0 compatible)."""
    try:
        import json
        from sqlalchemy import text
        from backend.v9.db.session import engine

        _ensure_table()

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO v9_s7_shadow_log "
                    "(trade_id, mode, direction, pattern, entry_price, score, sizing, blocked, components, outcome) "
                    "VALUES (:tid, :mode, :dir, :pat, :ep, :sc, :sz, :bl, :comp, :oc)"
                ),
                {
                    "tid": trade_id, "mode": mode, "dir": direction,
                    "pat": pattern, "ep": entry_price, "sc": score,
                    "sz": sizing, "bl": blocked,
                    "comp": json.dumps(components) if components else None,
                    "oc": outcome,
                },
            )
            conn.commit()
        logger.info("S7_SHADOW: trade=%s score=%s sizing=%s blocked=%s",
                     trade_id, score, sizing, blocked)
    except Exception:
        logger.debug("S7 shadow persist error: %s", traceback.format_exc())
