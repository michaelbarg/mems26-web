#!/usr/bin/env python3
"""T-357 / פריט 5 — טבלת-ריפליי לכל setup שהגיע ל-ADMIT בהרנס.

מה זה עונה: אילו מפיקים שיושבים ב-shadow היו מרוויחים אילו היו חיים.

כללי-המודל (מפורשים, כי כל אחד מהם הוא הנחה):
  1. **סלוט אחד**. עסקה נפתחת רק אם אין פוזיציה פתוחה — בדיוק כמו בלייב.
     בלי זה אותה תבנית נספרת 5 פעמים ברצף והטבלה שקר.
  2. גודל n = min(5, floor(225 / (5 × risk_pts))); n < 3 ⇒ אין כניסה (פסיקת 09.09).
  3. $5 לנקודה לחוזה (MES).
  4. יציאה: הולכים קדימה על ברי-5-דק' RTH. נגע בסטופ ⇒ הפסד. נגע ב-T1 ⇒ רווח.
     **נגעו בשניהם באותו בר ⇒ AMBIGUOUS** — סדר תוך-ברי אינו נצפה, ולא מייחסים
     תוצאה ([[feedback_shadow_stop_first_assigns_outcome]]). מדווח בנפרד, לא מוכרע.
  5. לא נסגר עד סוף ה-RTH ⇒ סגירה בסגירה האחרונה (EOD).
  6. T0 (entry ∓ 3.0) מדווח בעמודה נפרדת — לא מעורבב ב-P&L, כי BE-אחרי-T0
     תלוי בסדר תוך-ברי שאינו נצפה.
"""
import json, sys, glob, os, collections
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.env_loader import load_dotenv_file
load_dotenv_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), override=False)
from backend.v9.db.read import read_all

TICK_USD = 5.0
RISK_BUDGET = 225.0


def bars(session):
    rows = read_all(
        "SELECT (ts AT TIME ZONE 'Asia/Jerusalem') AS il, high, low, close "
        "FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date = (:d)::date "
        "AND (ts AT TIME ZONE 'Asia/Jerusalem')::time >= '16:30' "
        "AND (ts AT TIME ZONE 'Asia/Jerusalem')::time <= '23:00' "
        "ORDER BY ts", {"d": session})
    return [(str(r["il"])[11:16], float(r["high"]), float(r["low"]), float(r["close"]))
            for r in rows]


def size_for(risk):
    if risk <= 0:
        return 0
    return min(5, int(RISK_BUDGET // (TICK_USD * risk)))


def walk(bs, start_il, direction, entry, stop, t1):
    """→ (event, il, pts) ; event ∈ STOP / T1 / AMBIG / EOD / NOBAR"""
    seen = False
    for il, h, l, c in bs:
        if il < start_il:
            continue
        if not seen:            # skip the entry bar itself (entry is its close)
            seen = True
            continue
        if direction == "SHORT":
            hit_s, hit_t = h >= stop, l <= t1
        else:
            hit_s, hit_t = l <= stop, h >= t1
        if hit_s and hit_t:
            return "AMBIG", il, 0.0
        if hit_s:
            return "STOP", il, -(abs(entry - stop))
        if hit_t:
            return "T1", il, abs(t1 - entry)
    if bs:
        last = bs[-1]
        pts = (entry - last[3]) if direction == "SHORT" else (last[3] - entry)
        return "EOD", last[0], pts
    return "NOBAR", "-", 0.0


def main(pattern_filter=None):
    out = []
    for f in sorted(glob.glob('/tmp/h1409d/2026-*.json')):
        s = f.split('/')[-1][:-5]
        d = json.load(open(f))
        bs = bars(s)
        busy_until = "00:00"
        rs = sorted([r for r in d['routes'] if r.get('blocked_by') is None],
                    key=lambda r: r.get('il') or '')
        for r in rs:
            cls = str(r.get('classification'))
            if pattern_filter and pattern_filter not in cls:
                continue
            il = r.get('il') or ''
            if il <= busy_until:
                continue                      # slot busy — exactly as live
            entry, stop, t1 = r.get('entry'), r.get('stop'), r.get('t1')
            if not (entry and stop and t1):
                continue
            risk = abs(float(entry) - float(stop))
            n = size_for(risk)
            if n < 3:
                out.append((s, il, cls, r.get('direction'), entry, stop, t1,
                            round(risk, 2), n, "NO-SIZE", "-", 0.0, 0.0,
                            bool(r.get('shadow_only'))))
                continue
            ev, xil, pts = walk(bs, il[:5], str(r.get('direction')).upper(),
                                float(entry), float(stop), float(t1))
            usd = round(pts * TICK_USD * n, 2)
            out.append((s, il, cls, r.get('direction'), entry, stop, t1,
                        round(risk, 2), n, ev, xil, round(pts, 2), usd,
                        bool(r.get('shadow_only'))))
            if ev != "NOBAR":
                busy_until = xil
    return out


if __name__ == "__main__":
    pf = sys.argv[1] if len(sys.argv) > 1 else None
    rows = main(pf)
    hdr = f"{'session':11} {'il':9} {'pattern':22} {'dir':6} {'entry':9} {'stop':9} {'t1':9} {'risk':6} {'n':2} {'event':8} {'exit':6} {'pts':7} {'usd':9} shadow"
    print(hdr); print("-" * len(hdr))
    agg = collections.Counter(); usd_tot = 0.0; amb = 0
    for r in rows:
        print(f"{r[0]:11} {r[1]:9} {r[2]:22} {str(r[3]):6} {r[4]:<9} {r[5]:<9} {r[6]:<9} {r[7]:<6} {r[8]:<2} {r[9]:8} {r[10]:6} {r[11]:<7} {r[12]:<9} {r[13]}")
        agg[r[9]] += 1
        if r[9] == "AMBIG":
            amb += 1
        else:
            usd_tot += r[12]
    print("-" * len(hdr))
    print("תוצאות:", dict(agg))
    print(f"סה\"כ עסקאות שנפתחו: {sum(v for k,v in agg.items() if k not in ('NO-SIZE','NOBAR'))}")
    print(f"P&L מודלי (בלי ה-AMBIG): ${usd_tot:,.2f}   ·   AMBIG שלא הוכרעו: {amb}")
