"""Item-18 halt-proof — when a directional day has demonstrably stalled.

CC's DAY_DIRECTION_DOCTRINE_V1 v1 blocks ALL counter-expansion entries on a
directional day (Variation/Trend). Michael's doctrine (ledger #24): the counter
side opens ONLY after a *proven stop* — "2 consecutive closes back through the
expansion level" (or a double-print). This module supplies that proof so a
counter entry is released once the trend has actually halted, instead of being
blocked for the whole session.

Pure + fail-safe. Consumed by the gateway's day-direction block.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


def halt_proof_met(
    *,
    expansion_dir: str,
    expansion_level: Optional[float],
    recent_closes: List[float],
    min_closes: int = 2,
) -> bool:
    """True if the expansion has been proven to stall.

    UP expansion (broke above IB high): proof = the last `min_closes` bar
    closes are ALL back BELOW the expansion level (price re-entered the range).
    DOWN expansion: proof = last `min_closes` closes ALL back ABOVE the level.

    Fail-safe: missing level or too few closes → False (no proof → stay blocked).
    """
    if expansion_level is None:
        return False
    closes = [c for c in recent_closes if c is not None]
    if len(closes) < min_closes:
        return False
    last = closes[-min_closes:]
    if expansion_dir == "UP":
        return all(c < expansion_level for c in last)
    if expansion_dir == "DOWN":
        return all(c > expansion_level for c in last)
    return False


def gather_recent_closes(n: int = 3) -> List[float]:
    """Last `n` RTH closes from the canonical bar table (fail-safe → [])."""
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT close FROM v9_bars_5min_woodies "
            "WHERE (ts::timestamptz AT TIME ZONE 'America/Chicago')::date = "
            "      (now() AT TIME ZONE 'America/Chicago')::date "
            "  AND (ts::timestamptz AT TIME ZONE 'America/Chicago')::time >= '08:30' "
            "ORDER BY ts::timestamptz DESC LIMIT :n",
            {"n": n},
        )
        return [float(r["close"]) for r in rows][::-1]  # oldest→newest
    except Exception as e:
        logger.warning("[DayDirection] recent-closes read failed (no halt-proof): %s", e)
        return []


def min_closes_required() -> int:
    """Confirm-bar count for the halt-proof (default 2; tunable, unapproved>2)."""
    try:
        return max(1, int(os.getenv("DAY_DIRECTION_HALT_CLOSES", "2")))
    except (TypeError, ValueError):
        return 2
