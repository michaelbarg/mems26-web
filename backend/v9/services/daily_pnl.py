"""Daily P&L table from Sierra's own trade activity journal (Michael 2026-07-28:
"נרצה לבנות לעצמנו טבלה של רווח והפסד לפי ימים ולהבין איפה נפלנו ומה טעינו").

Source of truth: trade_activity_events.jsonl — the DLL's export of Sierra's
Trade Activity Log (CLOSED_TRADE_PNL per contract-close, ISO-UTC `ts`).
This is Sierra truth for ALL closes on the chart's account — system AND
Michael's manual trades — which our v9_trades books deliberately do not hold
for manual positions (ownership ruling).

Day boundary: America/New_York calendar date of the close (ET — the trading
timezone; explicit per Rule 4). Events missing/with unparseable ts are counted
under "unknown" — never guessed onto a day (Rule 1).

Known limitation (stated, not hidden): the journal does not carry the account
per event, so SIM-era closes (e.g. the 2026-07-10 sim flood) appear alongside
live ones. The `system_pnl` column (from v9_trades, mode=live) lets Michael
see the system-vs-manual split per day.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
JOURNAL = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/trade_activity_events.jsonl"))


def _event_day(ev: Dict[str, Any]) -> str:
    ts = ev.get("ts")
    if not ts:
        return "unknown"
    try:
        return datetime.fromisoformat(str(ts)).astimezone(ET).date().isoformat()
    except Exception:
        return "unknown"


def group_daily(lines: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Pure: jsonl lines → {day: {pnl, closes, wins, losses, biggest_loss, biggest_win}}."""
    days: Dict[str, Dict[str, Any]] = {}
    for ln in lines:
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        if ev.get("type") != "CLOSED_TRADE_PNL":
            continue
        try:
            pnl = float(ev.get("pnl"))
        except (TypeError, ValueError):
            continue
        d = days.setdefault(_event_day(ev), {
            "pnl": 0.0, "closes": 0, "wins": 0, "losses": 0,
            "biggest_win": 0.0, "biggest_loss": 0.0,
        })
        d["pnl"] = round(d["pnl"] + pnl, 2)
        d["closes"] += 1
        if pnl > 0:
            d["wins"] += 1
            d["biggest_win"] = max(d["biggest_win"], pnl)
        elif pnl < 0:
            d["losses"] += 1
            d["biggest_loss"] = min(d["biggest_loss"], pnl)
    return days


def _system_pnl_by_day() -> Dict[str, float]:
    """Per-day realized P&L of SYSTEM live trades from our books (v9_trades).
    Errors → {} (the journal column still renders; no silent lie)."""
    try:
        from backend.v9.db.read import read_all
        # Real columns (verified 07-28 via information_schema): pnl_usd + exit_ts.
        # exit_ts is timestamptz → a SINGLE `AT TIME ZONE 'America/New_York'`
        # converts to ET wall time. (First cut double-converted via UTC, which
        # re-interpreted the naive result as NY wall time and pushed evening
        # closes onto the next day — Rule 4.)
        rows = read_all(
            "SELECT to_char(COALESCE(exit_ts, updated_at) "
            "AT TIME ZONE 'America/New_York', 'YYYY-MM-DD') AS day, "
            "COALESCE(SUM(pnl_usd), 0) AS pnl, COUNT(*) AS n "
            "FROM v9_trades WHERE state = 'CLOSED' AND mode = 'live' "
            "GROUP BY 1", {})
        return {r["day"]: {"pnl": round(float(r["pnl"] or 0), 2), "trades": int(r["n"])}
                for r in rows}
    except Exception as e:
        logger.warning("[DailyPnl] system-pnl query failed: %s", e)
        return {}


def daily_pnl_table(days_limit: int = 30) -> Dict[str, Any]:
    if not JOURNAL.exists():
        return {"ok": False, "error": "trade_activity_events.jsonl not found", "rows": []}
    try:
        with JOURNAL.open() as f:
            grouped = group_daily(f)
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}

    sys_by_day = _system_pnl_by_day()
    known = sorted((k for k in grouped if k != "unknown"), reverse=True)[:days_limit]
    rows: List[Dict[str, Any]] = []
    cum = 0.0
    for day in sorted(known):  # ascending for cumulative, reversed for display
        r = {"day": day, **grouped[day]}
        s = sys_by_day.get(day)
        r["system_pnl"] = s["pnl"] if s else None
        r["system_trades"] = s["trades"] if s else None
        cum = round(cum + r["pnl"], 2)
        r["cumulative"] = cum
        rows.append(r)
    rows.reverse()
    out = {"ok": True, "rows": rows, "source": "sierra trade activity journal",
           "tz": "America/New_York",
           "note": "journal has no per-event account — sim-era closes included; "
                   "system_pnl = our booked live trades only"}
    if "unknown" in grouped:
        out["unknown_ts_events"] = grouped["unknown"]["closes"]
    return out
