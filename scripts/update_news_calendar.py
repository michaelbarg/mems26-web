#!/usr/bin/env python3
"""update_news_calendar — weekly auto-seed of config/news_calendar.yaml (Michael 07-13).

Sources, in order (Michael's ruling: "מחוברת עם TradingView"):
  1. PRIMARY — TradingView's own calendar endpoint (economic-calendar.tradingview.com):
     the EXACT data Michael's TV app shows, filter importance==1 (red) + US.
     Unofficial-but-public endpoint — no account/auth; can break someday, hence:
  2. FALLBACK — ForexFactory weekly JSON (impact==High, USD).
Cross-anchor: BLS/Fed official schedules in the Monday audit (Rule 2 — the
07-13 lesson: one aggregator got CPI's day wrong; the official source rules).

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
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
TV_URL = ("https://economic-calendar.tradingview.com/events"
          "?from={frm}&to={to}&countries=US")
ET = ZoneInfo("America/New_York")

HEADER = """# לוח-אירועים כלכלי — חלון-חדשות NO_TRADE (מתעדכן אוטומטית).
# TZ מפורש (Rule 4): time_et = America/New_York.
# נוצר ע"י scripts/update_news_calendar.py — מקור-ראשי: יומן-TradingView עצמו
# (importance=1 = אדום, US) = בדיוק מה שמייקל רואה באפליקציה; גיבוי: ForexFactory
# (impact=High/USD). עוגן-אימות: לוחות-BLS/Fed הרשמיים בביקורת-שני (Rule 2).
# עריכה ידנית מותרת — ריצת-עדכון מחליפה רק ימים שהמקור מכסה.
{source_line}
events:
"""


def _get(url: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Origin": "https://www.tradingview.com"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


_TV_SEV = {1: "red", 0: "orange", -1: "yellow"}      # TV importance → דירוג
_FF_SEV = {"high": "red", "medium": "orange", "low": "yellow"}


def fetch_tradingview():
    """ALL rated US events (red/orange/yellow) for the next 7 days — Michael's
    07-13 ruling: 'שימוש בדירוג-חשיבות של כל חלון-חדשות'."""
    from datetime import timedelta, timezone
    now = datetime.now(timezone.utc)
    url = TV_URL.format(frm=now.strftime("%Y-%m-%dT00:00:00.000Z"),
                        to=(now + timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000Z"))
    d = _get(url)
    rows = d.get("result") if isinstance(d, dict) else d
    evs = []
    for e in rows or []:
        try:
            sev = _TV_SEV.get(e.get("importance"))
            if sev is None:
                continue
            dt = datetime.fromisoformat(str(e["date"]).replace("Z", "+00:00")).astimezone(ET)
            evs.append({"date": dt.strftime("%Y-%m-%d"), "time_et": dt.strftime("%H:%M"),
                        "name": str(e.get("title", "?")).strip(), "severity": sev})
        except Exception:
            continue
    return evs


def fetch_forexfactory():
    raw = _get(FF_URL)
    evs = []
    for e in raw:
        try:
            if str(e.get("country", "")).upper() != "USD":
                continue
            sev = _FF_SEV.get(str(e.get("impact", "")).lower())
            if sev is None:
                continue
            dt = datetime.fromisoformat(e["date"]).astimezone(ET)
            evs.append({"date": dt.strftime("%Y-%m-%d"), "time_et": dt.strftime("%H:%M"),
                        "name": str(e.get("title", "?")).strip(), "severity": sev})
        except Exception:
            continue
    return evs


def _body_unchanged(lines: str) -> bool:
    """True when the on-disk yaml already carries exactly this event body.

    [T-245] Compares only what is downstream of the `events:` marker, so the
    run-timestamp comment in the header is deliberately ignored — it is the one
    field that changes on every run regardless of whether anything was learned.
    Any read/parse problem returns False (write, i.e. today's behaviour): the
    suppressor must never be the reason a real calendar update is lost.
    """
    try:
        old = CAL.read_text(encoding="utf-8")
    except OSError:
        return False
    marker = "\nevents:\n"
    _, sep, old_body = old.partition(marker)
    return bool(sep) and old_body == lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    evs, source = [], None
    try:
        evs = fetch_tradingview()
        source = "tradingview (importance=1, US)"
    except Exception as e:
        print(f"[news_cal] TradingView fetch failed ({e}) → falling back to ForexFactory")
    if not evs:
        try:
            evs = fetch_forexfactory()
            source = "forexfactory (impact=High, USD) — TV unavailable"
        except Exception as e:
            print(f"[news_cal] FETCH FAILED (both sources) — calendar untouched: {e}")
            return 1
    if not evs:
        print("[news_cal] 0 red events from both sources — refusing to overwrite (suspicious)")
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
                             "name": str(e.get("name", "?")),
                             "severity": str(e.get("severity", "red"))})
    except Exception:
        pass

    # [T-245 part 2, 2026-09-04] `name` is a TIEBREAKER, not decoration. Without
    # it this sort is stable-but-input-ordered, so two events at the same
    # date+time keep whatever order the fetch happened to return — and the
    # T-245 no-op suppressor below is defeated because the body genuinely
    # differs. Measured today: the 08:14 ET and 14:14 ET runs produced the same
    # events and still left the tree dirty, because "Average Weekly Hours" and
    # "Government Payrolls" (both 2026-09-04) swapped places. Deterministic
    # output is what makes "unchanged" mean unchanged.
    allev = sorted(kept + evs, key=lambda x: (x["date"], x["time_et"], x["name"]))
    lines = ""
    for e in allev:
        nm = e["name"].replace('"', "'")
        lines += (f'  - date: {e["date"]}\n    time_et: "{e["time_et"]}"\n'
                  f'    name: "{nm}"\n    severity: {e.get("severity", "red")}\n')

    print(f"[news_cal] source={source} · {len(evs)} fetched + {len(kept)} kept manual:")
    for e in allev:
        print(f"   {e['date']} {e['time_et']} ET — {e['name']}")

    if args.dry_run:
        print("[news_cal] dry-run — not written")
        return 0
    # [T-245] No-op write suppressor. Until now every run rewrote the file with a
    # fresh run-timestamp comment even when the event body was byte-identical, so a
    # generated artifact sat dirty in the tree after each auto-run and blocked
    # `git pull`/`commit` at the 15:30 pre-open gate's FIRST step (measured 04.09:
    # 6 of the last 15 commits to the yaml were pure 1+/1- timestamp churn).
    # Same class as T-231 (generated artifact dirties the tree), different artifact
    # and a cheaper fix: the repo contract is unchanged — the file stays tracked and
    # still rewrites whenever the events actually differ.
    if _body_unchanged(lines):
        print(f"[news_cal] unchanged — {CAL} left untouched "
              f"(event body identical; run-timestamp not bumped, T-245)")
        return 0

    src_line = f"# מקור-הריצה האחרונה: {source} · {datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')}"
    CAL.write_text(HEADER.format(source_line=src_line) + lines, encoding="utf-8")
    print(f"[news_cal] wrote {CAL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
