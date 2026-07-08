#!/usr/bin/env python3
"""TP audit v1 — האם המימושים (T1) נכונים פר-תבנית×סוג-יום מול מה שהיום נתן
(מייקל 2026-07-08; המתודולוגיה: docs/handoff/RESEARCH_PROMPT_TP_AUDIT_2026-07-08.md).

v1 עובד על ה-API המקומי (עסקאות אחרונות + ברים זמינים) — דוח ראשוני; המחקר המלא
(30 יום, ברים היסטוריים מלאים) ירוץ כשה-DB ההיסטורי נגיש לסוכן.
פלט: docs/reports/TP_AUDIT_<date>.md. דוח בלבד — אפס שינויי קוד/קונפיג.
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(path, timeout=8):
    try:
        with urllib.request.urlopen(f"http://localhost:8000{path}", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main():
    trades = api("/api/v9/trades/recent?limit=200") or []
    bars_raw = api("/api/v9/chart/bars5min?limit=500") or []
    bars = bars_raw if isinstance(bars_raw, list) else bars_raw.get("bars", [])

    # index bars by day for MFE
    by_day = defaultdict(list)
    for b in bars:
        ts = str(b.get("ts", ""))
        if len(ts) >= 10:
            by_day[ts[:10]].append(b)

    def mfe(day, entry_ts, entry, direction):
        rows = [b for b in by_day.get(day, []) if str(b["ts"])[11:16] >= entry_ts[11:16]]
        if not rows or entry is None:
            return None
        hs = [float(b.get("h", b.get("high", 0))) for b in rows]
        ls = [float(b.get("l", b.get("low", 0))) for b in rows]
        return (max(hs) - entry) if direction == "LONG" else (entry - min(ls))

    agg = defaultdict(lambda: {"n": 0, "t1_dists": [], "mfes": [], "t1_hits": 0})
    skipped = 0
    for t in trades:
        entry, t1 = t.get("entry_price"), t.get("t1")
        ets = str(t.get("entry_ts", ""))
        if not (entry and t1 and len(ets) >= 16):
            skipped += 1
            continue
        day = ets[:10]
        m = mfe(day, ets, float(entry), t.get("direction", "LONG"))
        if m is None:
            skipped += 1
            continue
        key = (str(t.get("trigger", "?"))[:16], str(t.get("day_type_at_entry") or "?"))
        a = agg[key]
        a["n"] += 1
        a["t1_dists"].append(abs(float(t1) - float(entry)))
        a["mfes"].append(m)
        if t.get("t1_hit_ts"):
            a["t1_hits"] += 1

    def med(xs):
        s = sorted(xs)
        return s[len(s) // 2] if s else 0.0

    lines = [f"# TP Audit v1 · {date.today().isoformat()}",
             "",
             f"מדגם: {sum(a['n'] for a in agg.values())} עסקאות (מ-API, ימים זמינים בברים) · דולג: {skipped}",
             "",
             "| תבנית | סוג-יום | n | T1 חציוני (נק') | MFE חציוני (נק') | T1/MFE | hit-rate | דגל |",
             "|---|---|---|---|---|---|---|---|"]
    flags = []
    for (pat, dt), a in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
        t1m, mm = med(a["t1_dists"]), med(a["mfes"])
        ratio = (t1m / mm) if mm > 0 else float("inf")
        hr = a["t1_hits"] / a["n"] if a["n"] else 0
        flag = ""
        if a["n"] >= 3:
            if ratio > 1.5:
                flag = "🔴 T1 רחוק מדי"
                flags.append(f"{pat}×{dt}: T1 חציוני {t1m:.1f} מול MFE {mm:.1f} (יחס {ratio:.1f}) — לקרב/מדף")
            elif ratio < 0.35 and hr > 0.7:
                flag = "🟡 T1 קרוב — מוותר על תנועה"
                flags.append(f"{pat}×{dt}: T1 {t1m:.1f} לוקח רק {ratio:.0%} מה-MFE {mm:.1f} — לשקול הרחקה/runner")
        lines.append(f"| {pat} | {dt} | {a['n']} | {t1m:.1f} | {mm:.1f} | "
                     f"{'∞' if ratio == float('inf') else f'{ratio:.2f}'} | {hr:.0%} | {flag} |")

    lines += ["", "## תאי-הפסד מועמדים", ""]
    lines += [f"- {f}" for f in flags] if flags else ["- אין תאים מובהקים במדגם הזמין (n קטן) — המחקר המלא ירחיב ל-30 יום."]
    lines += ["", "_v1 — מדגם מוגבל לברים הזמינים ב-API; רגישות L6 (P&L מ-bar לא fill) בתוקף._",
              "_אפס שינויים בוצעו. המלצות = פסיקת מייקל בלבד._"]

    out = os.path.join(ROOT, "docs", "reports", f"TP_AUDIT_{date.today().isoformat()}.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:14]))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
