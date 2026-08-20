"""Daily P&L table from Sierra's OWN per-day Trade Activity Logs.

Michael 2026-07-28: "אני רוצה שתחקור עסקאות מפסידות של המערכת בלייב ואני רוצה
שתאמת שהן באמת הפסידו כי לדעתי אתה לא לוקח נתונים או מציב נכונים" — he was right.

REJECTED SOURCE — `trade_activity_events.jsonl` (the feeder's journal).
Verified broken 2026-07-28 in BOTH directions:
  • duplicates — 2363 events held only 309 unique ones; a single −125.00 close was
    emitted 117 times (the feeder writes offset 0 whenever `strings` fails, so the
    next poll re-emits the entire file). Summing it gave −27,305 instead of −1,419.
  • gaps — the offset file is keyed per ACCOUNT but the log is per DAY, so a new
    day starts with yesterday's large offset and whole sessions are skipped.
  • its `ts` is the SCAN time, not the trade time (237 distinct stamps for 2363
    events, 24 sharing one microsecond) — so it cannot place a close on a day or
    correlate it to a trade at all.

ACCEPTED SOURCE — `~/SierraChart/TradeActivityLogs/TradeActivityLog_<day>_UTC.<acct>.data`.
One file per day per account, written by Sierra itself. The day comes from the
FILENAME (no timestamp inference), and each "Closed Trade Profit/Loss" line is a
real close. This is Sierra's own record — nothing here is computed by us.

Two hard limits, stated rather than papered over (Rule 1):
  • the log has no owner tag → a day's total mixes Michael's manual trades with
    the system's. The per-day `entries` ladder (0 → N) is exposed so the split is
    at least visible: system size is 1-5 contracts, Michael's blocks are larger.
  • SIMULATED account logs contain NO "Closed Trade Profit/Loss" lines at all
    (only "Trade simulation fill") → sim P&L is genuinely unavailable here and is
    reported as None, never as 0.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LOG_DIR = Path(os.path.expanduser("~/SierraChart/TradeActivityLogs"))
LIVE_ACCOUNT = os.getenv("SIERRA_LIVE_ACCOUNT", "37138283")

_CLOSE_RE = re.compile(r"Closed Trade Profit/Loss: (-?[\d.]+)\.")
_POS_RE = re.compile(r"Updated Internal Position Quantity to (-?\d+)\. Previous: (-?\d+)")
_DAY_RE = re.compile(r"TradeActivityLog_(\d{4}-\d{2}-\d{2})_UTC\.")


def _strings(path: Path) -> Optional[str]:
    """Extract text from Sierra's binary log. None on failure — NEVER '' (an
    empty string would be silently read as 'no trades that day')."""
    try:
        r = subprocess.run(["strings", str(path)], capture_output=True,
                           text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except Exception as e:
        logger.warning("[DailyPnl] strings failed on %s: %s", path.name, e)
        return None


def parse_day_log(text: str) -> Dict[str, Any]:
    """Pure: log text → {closes, pnl, wins, losses, biggest_*, entries}."""
    closes = [float(x) for x in _CLOSE_RE.findall(text)]
    ladder = [(int(new), int(prev)) for new, prev in _POS_RE.findall(text)]
    entries = [abs(new) for new, prev in ladder if prev == 0 and new != 0]
    return {
        "pnl": round(sum(closes), 2),
        "closes": len(closes),
        "wins": sum(1 for x in closes if x > 0),
        "losses": sum(1 for x in closes if x < 0),
        "biggest_win": max(closes) if closes else 0.0,
        "biggest_loss": min(closes) if closes else 0.0,
        "entries": entries,
        "max_entry_size": max(entries) if entries else 0,
        "values": closes,
    }


def _system_pnl_by_day() -> Dict[str, Dict[str, Any]]:
    """Our own books, per day, next to Sierra's per-fill truth.

    `pnl_usd` is COMPUTED by us — it is the claim. `pnl_sierra` is reconstructed
    from the fills journal by `sierra_pnl_reconcile` (T-10), so `books_vs_sierra`
    below is the first per-day statement of how far our arithmetic drifted from
    what the broker actually filled. NULL `pnl_sierra` = that day's trades could
    not be reconciled (no correlatable fills), never "no difference".
    """
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT to_char(COALESCE(exit_ts, updated_at) AT TIME ZONE 'UTC', "
            "'YYYY-MM-DD') AS day, COALESCE(SUM(pnl_usd), 0) AS pnl, COUNT(*) AS n, "
            "SUM(pnl_sierra) AS pnl_sierra, "
            "COUNT(pnl_sierra) AS n_reconciled "
            "FROM v9_trades WHERE state = 'CLOSED' AND mode = 'live' GROUP BY 1", {})
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            ps = r.get("pnl_sierra")
            out[r["day"]] = {
                "pnl": round(float(r["pnl"] or 0), 2),
                "trades": int(r["n"]),
                "pnl_sierra": None if ps is None else round(float(ps), 2),
                "reconciled": int(r.get("n_reconciled") or 0),
            }
        return out
    except Exception as e:
        logger.warning("[DailyPnl] system-pnl query failed: %s", e)
        return {}


def books_vs_sierra(mode: str = "live", tol: float = 0.01) -> Dict[str, Any]:
    """The one call an EOD / daily report makes to hear the books-vs-broker alarm.

    Startup-safe and read-only: a missing journal, a missing DB or an unreachable
    import degrades to `{"ok": None, ...}` — "not checked" — and NEVER to
    `{"ok": True}`, which would be a green light nobody earned (Rule 1).
    """
    try:
        from backend.v9.db.read import read_all
        from backend.v9.services.sierra_pnl_reconcile import (
            divergence_summary, load_journal,
        )
        fills = load_journal()
        if not fills:
            return {"ok": None, "reason": "fills journal empty or missing"}
        rows = read_all(
            "SELECT id, mode, exit_reason, pnl_usd, pnl_sierra, quality "
            "FROM v9_trades WHERE state = 'CLOSED'"
            + (" AND mode = :mode" if mode else ""),
            {"mode": mode} if mode else {})
        if not rows:
            # read.py falls back to a stale SQLite file when DATABASE_URL is
            # unset/unreachable — and that file has no pnl_sierra column, so the
            # query returns nothing. Saying "ok" here would be the exact lie
            # this check exists to catch.
            return {"ok": None, "reason": "no CLOSED rows readable — wrong or "
                                          "unreachable DATABASE_URL?"}
        out = divergence_summary(rows, fills=fills, tol=tol)
        out["rows_read"] = len(rows)
        return out
    except Exception as e:
        logger.warning("[DailyPnl] books-vs-sierra check failed: %s", e)
        return {"ok": None, "reason": f"check failed: {e}"}


def daily_pnl_table(days_limit: int = 30, account: str = "") -> Dict[str, Any]:
    acct = account or LIVE_ACCOUNT
    if not LOG_DIR.exists():
        return {"ok": False, "error": f"{LOG_DIR} not found", "rows": []}

    per_day: Dict[str, Dict[str, Any]] = {}
    unreadable: List[str] = []
    for p in sorted(LOG_DIR.glob(f"TradeActivityLog_*_UTC.{acct}.data")):
        m = _DAY_RE.search(p.name)
        if not m:
            continue
        day = m.group(1)
        if not day.startswith("20") or day > "2099":
            continue
        text = _strings(p)
        if text is None:
            unreadable.append(day)
            continue
        d = parse_day_log(text)
        if d["closes"] == 0 and not d["entries"]:
            continue
        per_day[day] = d

    sys_by_day = _system_pnl_by_day()
    days = sorted(per_day)[-days_limit:]
    rows: List[Dict[str, Any]] = []
    cum = 0.0
    for day in days:
        d = per_day[day]
        s = sys_by_day.get(day)
        cum = round(cum + d["pnl"], 2)
        rows.append({
            "day": day, "pnl": d["pnl"], "closes": d["closes"],
            "wins": d["wins"], "losses": d["losses"],
            "biggest_win": d["biggest_win"], "biggest_loss": d["biggest_loss"],
            "entries": d["entries"], "max_entry_size": d["max_entry_size"],
            "cumulative": cum,
            "books_claim": s["pnl"] if s else None,
            "books_trades": s["trades"] if s else None,
            # T-10: what Sierra's own fills say the same trades made, and how
            # many of them could be reconciled at all.
            "books_sierra": s.get("pnl_sierra") if s else None,
            "books_reconciled": s.get("reconciled") if s else None,
            # books claim system trades on a day Sierra's live account never
            # opened a position → those rows are not live trades.
            "books_unbacked": bool(s and not d["entries"]),
        })
    rows.reverse()
    out = {
        "ok": True, "rows": rows, "account": acct,
        "source": "Sierra per-day TradeActivityLog files",
        "books_vs_sierra": books_vs_sierra(),
        "note": ("סכום היום מסיירה — כולל עסקאות ידניות וגם של המערכת (אין תיוג-בעלים "
                 "בלוג). 'הספרים' = החישוב שלנו; `books_sierra` הוא אותן עסקאות לפי "
                 "המילויים בפועל (T-10). פער בין השניים = הספרים משקרים, לא השוק."),
    }
    if unreadable:
        out["unreadable_days"] = unreadable
    return out
