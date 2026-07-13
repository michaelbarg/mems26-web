#!/usr/bin/env python3
"""update_news_calendar — weekly auto-seed of config/news_calendar.yaml (Michael 07-13).

Source: ForexFactory's public weekly JSON (nfs.faireconomy.media/ff_calendar_thisweek.json)
— the standard free calendar that carries an IMPORTANCE rating. Filter:
country == USD AND impact == High  ≈  TradingView's red-USA events.

Safety/honesty:
  - The MANUAL events already in the yaml for dates NOT covered by the fetch
    window are preserved; fetched days are REPLACED (source of truth per day).
  - Every run prints the resulting week so Michael/the Monday audit can eyeball
    it against TradingView (the 07-13 lesson: one web source got CPI's DAY
    wrong — cross-check before trusting; Rule 2).
  - Fetch failure → yaml untouched + nonzero exit (the gate keeps yesterday's
    calendar and fails open per-event; it never invents).

Usage: python3 scripts/update_news_calendar.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
CAL = REPO / "config" / "news_calendar.yaml"
URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
ET = ZoneInfo("America/New_York")

HEADER = """# לוח-אירועים כלכלי — חלון-חדשות NO_TRADE (מתעדכן אוטומטית).
# TZ מפורש (Rule 4): time_et = America/New_York.
# נוצר ע"י scripts/update_news_calendar.py ממקור ForexFactory (impact=High, USD)
# ≈ "אדום-ארה"ב" של TradingView. אימות-עין שבועי מול TradingView בביקורת-שני.
# עריכה ידנית מותרת — ריצת-עדכון מחליפה רק ימים שהמקור מכסה.

events:
"""


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "MEMS26-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        raw = fetch()
    except Exception as e:
        print(f"[news_cal] FETCH FAILED — calendar untouched (fail-open per-event): {e}")
        return 1

    evs = []
    for e in raw:
        try:
            if str(e.get("country", "")).upper() != "USD":
                continue
            if str(e.get("impact", "")).lower() != "high":
                continue
            # ff dates are ISO with offset, e.g. "2026-07-13T08:30:00-04:00"
            dt = datetime.fromisoformat(e["date"]).astimezone(ET)
            evs.append({"date": dt.strftime("%Y-%m-%d"), "time_et": dt.strftime("%H:%M"),
                        "name": str(e.get("title", "?")).strip()})
        except Exception:
            continue
    if not evs:
        print("[news_cal] source returned 0 High/USD events — refusing to overwrite (suspicious)")
        return 1

    fetched_dates = {e["date"] for e in evs}

    # preserve manual events on dates the fetch window doesn't cover
    kept = []
    try:
        import yaml
        old = yaml.safe_load(CAL.read_text(encoding="utf-8")) or {}
        for e in old.get("events") or []:
            if str(e.get("date")) not in fetched_dates:
                kept.append({"date": str(e["date"]), "time_et": str(e["time_et"]),
                             "name": str(e.get("name", "?"))})
    except Exception:
        pass

    allev = sorted(kept + evs, key=lambda x: (x["date"], x["time_et"]))
    lines = ""
    for e in allev:
        nm = e["name"].replace('"', "'")
        lines += (f'  - date: {e["date"]}\n    time_et: "{e["time_et"]}"\n'
                  f'    name: "{nm}"\n    severity: red\n')

    print(f"[news_cal] {len(evs)} fetched High/USD + {len(kept)} kept manual:")
    for e in allev:
        print(f"   {e['date']} {e['time_et']} ET — {e['name']}")

    if args.dry_run:
        print("[news_cal] dry-run — not written")
        return 0
    CAL.write_text(HEADER + lines, encoding="utf-8")
    print(f"[news_cal] wrote {CAL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
