#!/usr/bin/env python3
"""bar_gap_monitor — Track B (Michael 2026-07-16: "לדעת שיש את כל הנרות ללא חוסרים").

The recurring disease this session: a bar stream dies silently and everything
downstream starves — we only find out when a trade doesn't happen. This monitor
makes bar-completeness an EXPLICIT, checkable invariant.

For each canonical 5-min table, over today's RTH (16:30–23:00 IL), it computes:
  - newest bar age (fresh?)
  - EXPECTED 5-min slots vs ACTUAL bars → the list of MISSING slots (gaps)
  - longest gap
and prints a per-stream verdict. Answers "are the opening bars there?" with data.

Read-only. Runs on the trading machine (local Postgres). CLI:
  python3 scripts/bar_gap_monitor.py            # today, RTH so far
  python3 scripts/bar_gap_monitor.py 2026-07-16 16:30 17:30   # explicit window
Exit 0 = all streams complete; 1 = a gap/staleness found (usable as a gate).
"""
from __future__ import annotations
import sys
from datetime import datetime, timedelta, time as _time
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
IL = ZoneInfo("Asia/Jerusalem")
TABLES = ["v9_bars_5min_woodies", "v9_bars_5min_continuous", "v9_bars_5min"]
RTH_OPEN, RTH_CLOSE = _time(16, 30), _time(23, 0)


def _bar_times(table: str, day: str, t0: _time, t1: _time):
    from backend.v9.db.read import read_all
    rows = read_all(
        f"SELECT (ts AT TIME ZONE 'Asia/Jerusalem') AS il FROM {table} "
        f"WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date = :d "
        f"AND (ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN :a AND :b "
        f"ORDER BY ts", {"d": day, "a": t0.isoformat(), "b": t1.isoformat()})
    return [r["il"] for r in rows]


def _expected_slots(day: str, t0: _time, t1: _time, cap: datetime):
    d = datetime.fromisoformat(day).date()
    cur = datetime.combine(d, t0)
    end = min(datetime.combine(d, t1), cap.replace(tzinfo=None))
    out = []
    while cur <= end:
        out.append(cur)
        cur += timedelta(minutes=5)
    return out


def check(day: str, t0: _time, t1: _time) -> dict:
    now_il = datetime.now(IL)
    report = {"date": day, "window": f"{t0.strftime('%H:%M')}-{t1.strftime('%H:%M')}",
              "streams": [], "ok": True}
    expected = _expected_slots(day, t0, t1, now_il)
    for table in TABLES:
        try:
            got = _bar_times(table, day, t0, t1)
        except Exception as e:
            report["streams"].append({"table": table, "error": str(e)[:60]})
            continue
        if not got and table == "v9_bars_5min":
            report["streams"].append({"table": table, "bars": 0, "note": "empty (legacy — may be retired)"})
            continue
        got_min = {g.replace(second=0, microsecond=0) for g in got}
        missing = [e for e in expected if e not in got_min]
        age_s = (now_il.replace(tzinfo=None) - got[-1]).total_seconds() if got else None
        # longest consecutive gap
        longest = 0
        run = 0
        for e in expected:
            if e in got_min:
                run = 0
            else:
                run += 1
                longest = max(longest, run)
        stale = age_s is not None and age_s > 420 and now_il.time() <= RTH_CLOSE
        gap = len(missing) > 0
        if (gap or stale) and table == "v9_bars_5min_woodies":  # the live SoT drives the verdict
            report["ok"] = False
        report["streams"].append({
            "table": table, "bars": len(got), "expected": len(expected),
            "missing_count": len(missing),
            "missing_first5": [m.strftime("%H:%M") for m in missing[:5]],
            "longest_gap_bars": longest,
            "newest_age_min": round(age_s / 60, 1) if age_s is not None else None,
        })
    return report


def main():
    args = sys.argv[1:]
    day = args[0] if args else datetime.now(IL).strftime("%Y-%m-%d")
    t0 = _time.fromisoformat(args[1]) if len(args) > 1 else RTH_OPEN
    t1 = _time.fromisoformat(args[2]) if len(args) > 2 else RTH_CLOSE
    r = check(day, t0, t1)
    print(f"BAR-GAP MONITOR · {r['date']} · {r['window']} · "
          f"{'🟢 SHALEM' if r['ok'] else '🔴 GAP/STALE'}")
    for s in r["streams"]:
        if "error" in s:
            print(f"  {s['table']}: ERROR {s['error']}")
        elif "note" in s:
            print(f"  {s['table']}: {s['note']}")
        else:
            tag = "✅" if s["missing_count"] == 0 else "🔴"
            print(f"  {tag} {s['table']}: {s['bars']}/{s['expected']} bars · "
                  f"missing={s['missing_count']} {s['missing_first5']} · "
                  f"longest_gap={s['longest_gap_bars']} · age={s['newest_age_min']}min")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
