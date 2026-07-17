#!/usr/bin/env python3
"""gen_daily_report — דוח-יומי אוטומטי (Michael 2026-07-16, "דוח יומי שגם יופיע בכיס").

רץ על מכונת-המסחר (Postgres מקומי) בסגירת-RTH (~23:05 IL). מייצר:
  - docs/handoff/DAILY_REPORT.md   (רשומה בגיט — היסטוריה)
  - ~/SierraChart_Data/v9_export/daily_report.json  (הכיס קורא → כרטיס)

קריאה-בלבד מה-DB. אין תופעות-לוואי. הרצה: `python3 scripts/gen_daily_report.py [YYYY-MM-DD]`.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")

# ── central ops log (N12) — GUARDED: logging must never break the report
try:
    from scripts.ops_log import log_event
except Exception:  # pragma: no cover
    def log_event(*_a, **_k):
        return False


def _rows(sql, params=None):
    from backend.v9.db.read import read_all
    return [dict(r) for r in read_all(sql, params or {})]


def build(day: str) -> dict:
    trades = _rows(
        """SELECT id, mode, state, direction, entry_price, pnl_usd,
                  quality->>'pattern' AS pattern,
                  COALESCE((quality->>'contracts')::int,0) AS contracts,
                  to_char(entry_ts AT TIME ZONE 'Asia/Jerusalem','HH24:MI') AS t_in
           FROM v9_trades
           WHERE (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date = :d
             AND mode <> 'shadow'
           ORDER BY entry_ts""", {"d": day})
    closed = [t for t in trades if t["state"] == "CLOSED"]
    pnl = round(sum((t.get("pnl_usd") or 0) for t in closed), 2)
    wins = sum(1 for t in closed if (t.get("pnl_usd") or 0) > 0)
    day_type = None
    try:
        dt = _rows("""SELECT day_type, confidence
                      FROM v9_day_type_state
                      WHERE (updated_at AT TIME ZONE 'Asia/Jerusalem')::date = :d
                      ORDER BY updated_at DESC LIMIT 1""", {"d": day})
        if dt:
            day_type = dt[0]
    except Exception:
        pass
    return {
        "date": day,
        "generated": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "pnl_usd": pnl,
        "n_trades": len(closed),
        "wins": wins,
        "losses": len(closed) - wins,
        "day_type": day_type,
        "trades": trades,
    }


def to_md(r: dict) -> str:
    lines = [f"# דוח-יומי — {r['date']}", "",
             f"**P&L: {'+' if r['pnl_usd']>=0 else ''}{r['pnl_usd']}$** · "
             f"{r['n_trades']} עסקאות ({r['wins']}W/{r['losses']}L) · "
             f"סוג-יום: {(r.get('day_type') or {}).get('day_type','—')}",
             f"_נוצר {r['generated']}_", ""]
    if r["trades"]:
        lines += ["| # | שעה | תבנית | כיוון | ח' | כניסה | מצב | P&L |",
                  "|---|---|---|---|---|---|---|---|"]
        for t in r["trades"]:
            lines.append(f"| {t['id']} | {t.get('t_in','')} | {t.get('pattern') or '—'} | "
                         f"{t.get('direction','')} | {t.get('contracts',0)} | {t.get('entry_price','')} | "
                         f"{t['state']} | {t.get('pnl_usd','')} |")
    else:
        lines.append("_אין עסקאות היום._")
    return "\n".join(lines) + "\n"


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else \
        datetime.now().astimezone().strftime("%Y-%m-%d")
    r = build(day)
    (REPO / "docs/handoff/DAILY_REPORT.md").write_text(to_md(r), encoding="utf-8")
    try:
        os.makedirs(EXPORT, exist_ok=True)
        Path(f"{EXPORT}/daily_report.json").write_text(
            json.dumps(r, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[daily] export json failed (non-fatal): {e}")
        log_event("gen_daily_report", "WARN", f"{day}: export daily_report.json failed: {e}")
    print(f"[daily] {day}: P&L {r['pnl_usd']}$ · {r['n_trades']} trades "
          f"({r['wins']}W/{r['losses']}L) → DAILY_REPORT.md + daily_report.json")
    log_event("gen_daily_report", "INFO",
              f"{day}: P&L {r['pnl_usd']}$ · {r['n_trades']} trades "
              f"({r['wins']}W/{r['losses']}L) → DAILY_REPORT.md + daily_report.json")


if __name__ == "__main__":
    main()
