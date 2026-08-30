#!/usr/bin/env python3
"""T-153: Shadow promotion board — reads the unified ledger and reports.

Usage:
  python3 scripts/shadow_promotion_board.py              # print report
  python3 scripts/shadow_promotion_board.py --write      # write docs/reports/SHADOW_BOARD.md
  python3 scripts/shadow_promotion_board.py --alert      # alert if zero events today

T-152: unique event counting — counts per (pattern, direction, 30min window),
not raw rows, because shadow has no slot limit and inflates everything.
"""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# T-161 (2026-08-30): הלוח קורא מה-DB, אבל לא טען את .env — ובלי DATABASE_URL
# ‏backend/v9/db/read.py נופל ל-SQLite, שלא יודע לפרסר את ה-SQL של Postgres שכאן
# (‏"near '7 days': syntax error") ⇒ read_all מחזיר [] בשקט והלוח מדווח
# **אפס-כוזב** (0 במקום 146). חמור יותר: ‏--alert על המסלול השבור יורה
# התרעת-טלפון שקרית "צל ריק" בכל לילה. זו מחלקת-הכשל של sot_health (SQLite-stale
# ⇒ 🔴 כוזב) שמתועדת ב-CLAUDE.md.
# הקונבנציה זהה ל-scripts/fire_drill.py; ממוגן כך שייבוא המודול (טסטים/כלים)
# לעולם לא ירעיל את סביבת-התהליך.
if __name__ == "__main__" or os.getenv("SHADOW_BOARD_LOAD_ENV", "0") == "1":
    from scripts.flag_guard import parse_env  # noqa: E402
    for _k, _v in parse_env(os.path.join(ROOT, ".env")).items():
        os.environ.setdefault(_k, _v)


def _read():
    from backend.v9.db.read import read_all
    return read_all


def generate_report():
    read_all = _read()

    # All shadow events from the unified view
    rows = read_all(
        "SELECT ts, source, flag, trade_id, pattern, direction, price, "
        "decision, pnl_sim, outcome FROM v9_shadow_ledger "
        "WHERE ts >= now() - interval '7 days' ORDER BY ts DESC", {})

    # Today's events
    today = read_all(
        "SELECT ts, source, flag, pattern, direction, decision, pnl_sim "
        "FROM v9_shadow_ledger "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
        "(now() AT TIME ZONE 'America/New_York')::date "
        "ORDER BY ts DESC", {})

    # T-152: unique events (pattern+direction per 30min window)
    def _unique_count(events):
        seen = set()
        for e in events:
            ts = e.get("ts")
            pat = e.get("pattern") or ""
            d = e.get("direction") or ""
            # 30-min window: round to nearest 30 min
            if hasattr(ts, "hour"):
                window = f"{ts.date()}_{ts.hour}_{ts.minute // 30}"
            else:
                window = str(ts)[:16]
            key = (pat, d, window)
            seen.add(key)
        return len(seen)

    lines = []
    lines.append("# Shadow Promotion Board")
    lines.append(f"\nGenerated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"\n## Last 7 days: {len(rows)} raw events, "
                 f"{_unique_count(rows)} unique")
    lines.append(f"## Today: {len(today)} raw events, "
                 f"{_unique_count(today)} unique")

    # Per-flag summary
    lines.append("\n## Per-flag summary (last 7 days)")
    lines.append("| Flag | Events | Unique | Avg pnl_sim |")
    lines.append("|---|---|---|---|")
    flags = {}
    for r in rows:
        f = r.get("flag") or "?"
        if f not in flags:
            flags[f] = {"n": 0, "pnl": []}
        flags[f]["n"] += 1
        p = r.get("pnl_sim")
        if p is not None:
            try:
                flags[f]["pnl"].append(float(p))
            except (TypeError, ValueError):
                pass
    for f, data in sorted(flags.items()):
        avg = sum(data["pnl"]) / len(data["pnl"]) if data["pnl"] else 0
        lines.append(f"| {f} | {data['n']} | — | {avg:+.2f} |")

    report = "\n".join(lines)
    return report, len(today)


def main():
    report, today_count = generate_report()
    print(report)

    if "--write" in sys.argv:
        out = "docs/reports/SHADOW_BOARD.md"
        with open(out, "w") as f:
            f.write(report)
        print(f"\nWritten to {out}")

    if "--alert" in sys.argv and today_count == 0:
        try:
            from backend.v9.services.phone_alert import push
            push("shadow_empty",
                 "\u26a0\ufe0f MEMS26: צל ריק",
                 "אפס אירועי-צל היום — תקלת-גלאי או דגלים כבויים",
                 priority=0)
            print("Alert sent: zero shadow events today")
        except Exception as e:
            print(f"Alert failed: {e}")


if __name__ == "__main__":
    main()
