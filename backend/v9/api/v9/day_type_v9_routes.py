"""API: /api/v9/day_type/v9/* — V9 Day Type endpoints (3a-S4 REVISED C3).

Alongside existing backend/v9/systems/day_type/api.py (NOT replacing it).
Reads from v9_day_type_history table using V9 columns.

Endpoints:
    GET /api/v9/day_type/v9/current  — today's classification or null
    GET /api/v9/day_type/v9/history   — last N days DESC (default 30, max 365)
    GET /api/v9/day_type/v9/stats     — distribution + percentages
"""

import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

router = APIRouter(prefix="/api/v9/day_type/v9", tags=["v9-day-type-v9"])


@router.get("/current")
def get_current():
    """Today's day type classification from v9_day_type_history.

    Returns the V9 row for today's session_date, or null if not yet classified.
    Uses V9 columns (probability, directional_certainty, trading_confidence).
    """
    today = date.today().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM v9_day_type_history WHERE date = ? LIMIT 1",
            (today,),
        ).fetchone()
        conn.close()

        if row is None:
            return {"classified": False, "session_date": today, "data": None}

        r = dict(row)
        return {
            "classified": True,
            "session_date": today,
            "data": _row_to_v9_dict(r),
        }
    except Exception as e:
        return {"classified": False, "session_date": today, "data": None, "error": str(e)}


@router.get("/history")
def get_history(days: int = Query(30, ge=1, le=365)):
    """Last N days of day type classifications, DESC order.

    Returns V9 fields (probability, directional_certainty, trading_confidence,
    active_zohar_rules) when available, falls back to V1 fields otherwise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM v9_day_type_history ORDER BY date DESC LIMIT ?",
            (days,),
        ).fetchall()
        conn.close()

        items = [_row_to_v9_dict(dict(r)) for r in rows]
        return {"items": items, "count": len(items), "days_requested": days}
    except Exception as e:
        return {"items": [], "count": 0, "error": str(e)}


@router.get("/stats")
def get_stats(days: int = Query(30, ge=1, le=365)):
    """Day type distribution over last N days.

    Returns count and percentage per day type.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT day_type, COUNT(*) as cnt
               FROM v9_day_type_history
               WHERE date >= date('now', ?)
               GROUP BY day_type
               ORDER BY cnt DESC""",
            (f"-{days} days",),
        ).fetchall()
        conn.close()

        total = sum(r["cnt"] for r in rows)
        distribution = {}
        for r in rows:
            dt = r["day_type"]
            cnt = r["cnt"]
            distribution[dt] = {
                "count": cnt,
                "percentage": round(cnt / total * 100, 1) if total > 0 else 0,
            }

        return {
            "distribution": distribution,
            "total_days": total,
            "period_days": days,
        }
    except Exception as e:
        return {"distribution": {}, "total_days": 0, "error": str(e)}


def _row_to_v9_dict(r: dict) -> dict:
    """Convert a DB row dict to V9 API response format.

    Uses V9 columns when present, falls back to V1 columns.
    """
    # V9 fields (from 3a-S4 columns)
    probability = r.get("probability")
    directional = r.get("directional_certainty")
    trading = r.get("trading_confidence")
    zohar_rules = r.get("active_zohar_rules")

    # Parse JSON if it's a string (sqlite3 returns raw string for JSON columns)
    if isinstance(zohar_rules, str):
        import json
        try:
            zohar_rules = json.loads(zohar_rules)
        except (json.JSONDecodeError, TypeError):
            zohar_rules = []

    # Fallback: if V9 probability not set, use V1 confidence
    if probability is None and r.get("confidence") is not None:
        probability = r["confidence"] / 100.0 if r["confidence"] > 1 else r["confidence"]

    return {
        "session_date": r.get("date"),
        "day_type": r.get("day_type"),
        "probability": probability,
        "directional_certainty": directional,
        "trading_confidence": trading,
        "ib_h": r.get("ib_high"),
        "ib_l": r.get("ib_low"),
        "ib_width": r.get("ib_width"),
        "ib_width_class": r.get("ib_width_class"),
        "opening_type": r.get("opening_type"),
        "last_updated_at": r.get("last_updated_at"),
        "reasoning_notes": r.get("reasoning_notes"),
        "active_zohar_rules": zohar_rules or [],
    }
