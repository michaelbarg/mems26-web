"""Previous trading day context for S1 Day Type (P30 Wave 1a).

Shared loader for A1 pd_high/pd_low/pd_close and TPO previous-day API.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional, Union

from backend.v9.db.read import read_all, read_one
from backend.v9.services.market_clock import get_previous_trading_day

DEFAULT_DB_PATH = Path("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")


def missing_pd_context(missing_fields: list[str]) -> dict[str, Any]:
    return {
        "pd_high": None,
        "pd_low": None,
        "pd_close": None,
        "pd_context_status": "DEGRADED",
        "degraded_reason": "missing_previous_day_context",
        "missing_pd_fields": list(missing_fields),
    }


def _resolve_prev_date(previous_trading_day: Optional[Union[date, str]] = None) -> str:
    if previous_trading_day is None:
        return get_previous_trading_day().isoformat()
    if hasattr(previous_trading_day, "isoformat"):
        return previous_trading_day.isoformat()
    return str(previous_trading_day)


def load_previous_day_context(
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
    previous_trading_day: Optional[Union[date, str]] = None,
) -> dict[str, Any]:
    """Load previous-day context for DayType A1 without inventing defaults.

    pd_close: last 5-min bar close on previous session date.
    pd_high/pd_low: TPO range preferred, 5-min hi/lo fallback.
    """
    prev_date = _resolve_prev_date(previous_trading_day)
    bars_row = read_one(
        """SELECT max(high) as hi, min(low) as lo,
                  (SELECT close FROM v9_bars_5min
                   WHERE date(ts)=:prev_date
                   ORDER BY ts DESC LIMIT 1) as last_c
           FROM v9_bars_5min WHERE date(ts)=:prev_date""",
        {"prev_date": prev_date},
    )

    pd_close = bars_row["last_c"] if bars_row else None
    bars_high = bars_row["hi"] if bars_row else None
    bars_low = bars_row["lo"] if bars_row else None

    tpo_row = read_one(
        """SELECT range_high, range_low
           FROM v9_tpo_sessions
           WHERE trading_date=:prev_date AND session_type='CASH'
           ORDER BY id DESC LIMIT 1""",
        {"prev_date": prev_date},
    )

    pd_high = (tpo_row["range_high"] if tpo_row else None) or bars_high
    pd_low = (tpo_row["range_low"] if tpo_row else None) or bars_low

    context = {"pd_high": pd_high, "pd_low": pd_low, "pd_close": pd_close}
    missing_fields = [field for field, value in context.items() if value is None]
    if missing_fields:
        degraded = missing_pd_context(missing_fields)
        degraded.update(context)
        return degraded

    return {
        **context,
        "pd_context_status": "OK",
        "degraded_reason": None,
        "missing_pd_fields": [],
    }


def load_tpo_previous_day_summary(
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
    previous_trading_day: Optional[Union[date, str]] = None,
) -> dict[str, Any]:
    """TPO session row for previous trading day (API-shaped, no HTTP)."""
    prev_date = _resolve_prev_date(previous_trading_day)
    try:
        row = read_one(
            "SELECT * FROM v9_tpo_sessions WHERE trading_date=:prev_date AND session_type='CASH' ORDER BY id DESC LIMIT 1",
            {"prev_date": prev_date},
        )
    except Exception as e:
        return {"session_date": prev_date, "found": False, "error": str(e)}

    if not row:
        return {
            "session_date": prev_date,
            "found": False,
            "poc": None,
            "vah": None,
            "val": None,
            "ib_high": None,
            "ib_low": None,
            "ib_width": None,
            "profile_shape": None,
            "opening_type": None,
        }

    r = dict(row)
    return {
        "session_date": prev_date,
        "found": True,
        "poc": r.get("poc_price"),
        "vah": r.get("vah_price"),
        "val": r.get("val_price"),
        "ib_high": r.get("ib_high"),
        "ib_low": r.get("ib_low"),
        "ib_width": r.get("ib_width"),
        "profile_shape": r.get("profile_shape"),
        "opening_type": r.get("opening_type"),
        "range_high": r.get("range_high"),
        "range_low": r.get("range_low"),
    }
