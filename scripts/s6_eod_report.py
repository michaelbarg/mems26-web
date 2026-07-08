#!/usr/bin/env python3
"""System-6 EOD report — ביקורת סטופ-חכם/מימוש-חכם על עסקאות היום (מייקל 2026-07-08).

שלב 1 בהפיכת מערכת 6 לסוכן מנהל-עסקאות: כל ערב היא שופטת את היום —
  · סטופ חכם? מרחק הסטופ ביחס לנר הממוצע (רצועה 0.5–1.5×ATR) + מבנה
  · מימוש חכם? מרחק T1 מול ה-MFE בפועל (כמה מהתנועה באמת נלקח/הוחמץ)
  · wick-out? סטופ שנפגע ואז המחיר חזר ≥1R לטובת העסקה (סטופ צמוד מדי)
  · יעד מחוץ ליום? T מעבר ל-IB-H ביום לא-נייטרלי (פסיקת מייקל 07-08)
פלט: docs/reports/system6/S6_EOD_<date>.md — עברית, עם המלצות תיקון.
הרצה: python3 scripts/s6_eod_report.py [--date YYYY-MM-DD]
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(path, timeout=6):
    try:
        with urllib.request.urlopen(f"http://localhost:8000{path}", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def get_bars(limit=250):
    d = api(f"/api/v9/chart/bars5min?limit={limit}") or []
    rows = d if isinstance(d, list) else d.get("bars", [])
    out = []
    for b in rows:
        ts = b.get("ts") or b.get("time")
        h, l = b.get("high", b.get("h")), b.get("low", b.get("l"))
        if ts is None or h is None or l is None:
            continue
        out.append({"ts": str(ts), "h": float(h), "l": float(l)})
    return out


def atr_pts(bars, n=14):
    rngs = [b["h"] - b["l"] for b in bars[-n:]]
    return (sum(rngs) / len(rngs)) if rngs else 0.0


def mfe_mae(bars, entry_ts, entry, direction):
    """MFE/MAE בנקודות מהכניסה עד סוף היום."""
    after = [b for b in bars if b["ts"] >= entry_ts[:16]]
    if not after:
        return None, None
    if direction == "LONG":
        return max(b["h"] for b in after) - entry, entry - min(b["l"] for b in after)
    return entry - min(b["l"] for b in after), max(b["h"] for b in after) - entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    trades = api("/api/v9/trades/recent?limit=30") or []
    todays = [t for t in trades if str(t.get("entry_ts", ""))[:10] == args.date]
    bars = get_bars()
    atr = atr_pts(bars)
    day = (api("/api/v9/day_type/state") or {}).get("state", {})
    day_type = day.get("day_type", "?")

    lines = [f"# מערכת 6 — דוח סוף-יום · {args.date}",
             "",
             f"סוג-יום (סוף): **{day_type}** (conf {day.get('confidence')}) · "
             f"ATR-14 ≈ **{atr:.1f} נק'** · עסקאות היום: **{len(todays)}**",
             "", "| # | מצב | כיוון | תבנית | סטופ (נק' · ×ATR) | שיפוט-סטופ | T1 מול MFE | שיפוט-מימוש | תוצאה |",
             "|---|-----|-------|--------|------------------|------------|------------|-------------|-------|"]
    recs = []

    for t in todays:
        tid, mode = t.get("id"), t.get("mode")
        entry, stop = t.get("entry_price"), t.get("stop")
        d = t.get("direction", "?")
        q = t.get("quality") if isinstance(t.get("quality"), dict) else {}
        istop = q.get("initial_stop") or stop
        risk = abs(entry - istop) if (entry and istop) else None
        x_atr = (risk / atr) if (risk and atr) else None
        stop_verdict = "—"
        if x_atr is not None:
            if x_atr < 0.4:
                stop_verdict = "🔴 צמוד מדי"
                recs.append(f"עסקה {tid}: סטופ {risk:.1f} נק' = {x_atr:.2f}×ATR — מתחת לרצועה; לבדוק את העוגן")
            elif x_atr > 1.6:
                stop_verdict = "🟡 רחב"
                recs.append(f"עסקה {tid}: סטופ {x_atr:.2f}×ATR — מעל התקרה; שער-הגודל אמור היה לקצץ")
            else:
                stop_verdict = "🟢 ברצועה"
        mfe = mae = None
        if entry and t.get("entry_ts"):
            mfe, mae = mfe_mae(bars, str(t["entry_ts"]), float(entry), d)
        t1 = t.get("t1")
        tp_verdict = "—"
        t1_vs = "—"
        if t1 and entry and mfe is not None:
            t1_dist = abs(float(t1) - float(entry))
            t1_vs = f"{t1_dist:.1f} / {mfe:.1f}"
            if mfe >= t1_dist and not t.get("t1_hit_ts"):
                tp_verdict = "🔴 T1 היה בהישג-יד ולא מומש"
                recs.append(f"עסקה {tid}: MFE {mfe:.1f} ≥ T1 {t1_dist:.1f} אך T1 לא נרשם — לבדוק ניהול/פילים")
            elif t1_dist > mfe * 2 and mfe > 0:
                tp_verdict = "🔴 T1 רחוק פי-2 מה-MFE"
                recs.append(f"עסקה {tid}: T1 {t1_dist:.1f} נק' מול MFE {mfe:.1f} — יעד לא-ריאלי לסוג-היום ({day_type})")
            else:
                tp_verdict = "🟢 סביר"
        wick = ""
        if t.get("exit_reason") == "STOP_HIT" and mfe is not None and risk and mfe >= risk:
            wick = " · ⚠ wick-out (אחרי הסטופ המחיר נתן ≥1R)"
            recs.append(f"עסקה {tid}: סטופ נפגע ואז המחיר נתן ≥1R — מועמד לסטופ-מבני רחב יותר")
        lines.append(
            f"| {tid} | {mode} | {d} | {str(t.get('trigger'))[:14]} | "
            f"{(f'{risk:.1f} · {x_atr:.2f}×' if x_atr is not None else '—')} | {stop_verdict} | "
            f"{t1_vs} | {tp_verdict}{wick} | {t.get('exit_reason') or t.get('state')} ({t.get('pnl_usd')}$) |")

    lines += ["", "## המלצות תיקון (מערכת 6 → מייקל/Cowork)", ""]
    lines += [f"- {r}" for r in recs] if recs else ["- אין ממצאים חריגים היום."]
    lines += ["", "_דוח אוטומטי — שלב 1 של מערכת-6-כסוכן. פסיקות: מייקל בלבד._"]

    outdir = os.path.join(ROOT, "docs", "reports", "system6")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"S6_EOD_{args.date}.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"written: {out} · trades={len(todays)} · recs={len(recs)}")
    print("\n".join(lines[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
