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


def _persist(*, trade_id, mode, direction, pattern, entry_price,
             score, sizing, blocked, components, outcome):
    """Write to v9_s7_shadow_log (DB) — create table if needed."""
    try:
        from backend.v9.db.read import read_all
        import json

        # Auto-create table if missing
        from backend.v9.db.session import engine
        with engine.connect() as conn:
            conn.execute("""
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
            """)

        from backend.v9.db.session import engine as _eng
        with _eng.connect() as conn:
            conn.execute(
                "INSERT INTO v9_s7_shadow_log "
                "(trade_id, mode, direction, pattern, entry_price, score, sizing, blocked, components, outcome) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (trade_id, mode, direction, pattern, entry_price,
                 score, sizing, blocked, json.dumps(components), outcome),
            )
        logger.info("S7_SHADOW: trade=%s score=%s sizing=%s blocked=%s",
                     trade_id, score, sizing, blocked)
    except Exception:
        logger.debug("S7 shadow persist error: %s", traceback.format_exc())
