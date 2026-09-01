#!/usr/bin/env python3
"""אמת-המילויים — P&L ממחיר-מילוי בפועל, לא ממחיר-הפקודה.

פסיקת-מייקל 01.09: *"תתקן את הדיוקים באיך אתה מקבל הפסד/רווח של עסקה פעילה
ומחיר ממוצע אמיתי בפועל של החוזים — ולא מה שירית."*

הבעיה: `v9_trades.entry_price` הוא מה שהמערכת **שלחה**. מה שסיירה **מילאה** נמצא
ב-`trade_fills_journal.jsonl` (‏`kind=ENTRY|T1|T2|T3|STOP`, ‏`price`, `contracts`,
`order_id`). כשהם נבדלים — כל P&L שנגזר מ-`entry_price` שגוי.

שיטת-הקישור: רשומת-ENTRY נושאת את מזהי-הברקט שלה (`c1_stop_id`, `c1_target_id`,
`c2_*` …). כל מילוי-יציאה נושא `order_id`. ⇒ הקישור הוא **דרך מזהי-ההזמנה**
ולא לפי קרבת-זמן — כלומר ודאי ולא משוער.

‏🔴 מה שהכלי הזה **לא** עושה: אינו כותב ל-DB ואינו נוגע במסחר. קריאה בלבד.
"""
import json, os, sys, collections
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text

JOURNAL = os.getenv("TRADE_FILLS_JOURNAL_PATH",
                    "/Users/michael/SierraChart_Data/v9_export/trade_fills_journal.jsonl")
DB = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")
DPP = 5.0   # $ לנקודה לחוזה — MES


def load():
    out = []
    with open(JOURNAL, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else "2026-08-31"
    rows = load()
    for r in rows:
        try:
            r["dt"] = datetime.fromtimestamp(int(r["ts"]), tz=timezone.utc)
        except Exception:
            r["dt"] = None

    todays = [r for r in rows if r["dt"] and r["dt"].strftime("%Y-%m-%d") == day]
    print(f"יומן-המילויים · {day} · {len(todays)} מילויים "
          f"(מתוך {len(rows)} בסך-הכל)\n")
    if not todays:
        print("אין מילויים ביום הזה."); return

    # ── בניית ברקטים: ENTRY → כל מזהי-היציאה שלו ──────────────────────────
    exit_owner = {}          # order_id של יציאה → ENTRY
    entries = [r for r in todays if r.get("kind") == "ENTRY"]
    for e in entries:
        for k, v in e.items():
            if k.endswith(("_stop_id", "_target_id")) and v:
                exit_owner[int(v)] = e
    for e in entries:
        e["_exits"] = []
    orphan = []
    for r in todays:
        if r.get("kind") == "ENTRY":
            continue
        own = exit_owner.get(int(r.get("order_id") or 0))
        (own["_exits"] if own else orphan).append(r)

    eng = create_engine(DB)
    with eng.connect() as c:
        db = {r["id"]: dict(r) for r in c.execute(text("""
            SELECT id, entry_price, exit_price, pnl_usd, direction, mode, exit_reason,
                   (quality->>'contracts')::int AS contracts,
                   to_char(entry_ts,'HH24:MI:SS') t
            FROM v9_trades WHERE entry_ts::date = :d ORDER BY id"""), {"d": day}).mappings()}

    print(f"{'ENTRY':>8} {'שעה':>9} {'כיוון':>6} {'ח':>3} {'מולא@':>9} "
          f"{'ספרים@':>9} {'פער':>7} {'P&L-מילוי':>11} {'P&L-ספרים':>11}")
    print("-" * 92)

    tot_fill = 0.0
    tot_book = 0.0
    for e in sorted(entries, key=lambda x: x["ts"]):
        ep = float(e["price"]); qty = int(e.get("contracts") or 1)
        d = (e.get("direction") or "").upper()
        sign = 1.0 if d == "LONG" else -1.0
        pnl_fill = sum(sign * (float(x["price"]) - ep) * int(x.get("contracts") or 1) * DPP
                       for x in e["_exits"])
        closed = sum(int(x.get("contracts") or 1) for x in e["_exits"])
        hhmm = e["dt"].astimezone().strftime("%H:%M:%S")

        # התאמה לספרים: אותו כיוון + מחיר-כניסה קרוב (הספרים מחזיקים מחיר-פקודה)
        cand = [t for t in db.values()
                if (t["direction"] or "").upper() == d
                and abs(float(t["entry_price"] or 0) - ep) <= 3.0]
        bk = cand[0] if len(cand) == 1 else (
            min(cand, key=lambda t: abs(float(t["entry_price"]) - ep)) if cand else None)

        bp = float(bk["entry_price"]) if bk else None
        gap = (ep - bp) if bp is not None else None
        bpnl = (float(bk["pnl_usd"]) if bk and bk["pnl_usd"] is not None else None)
        tot_fill += pnl_fill
        if bpnl is not None:
            tot_book += bpnl

        print(f"{e['order_id']:>8} {hhmm:>9} {d[:5]:>6} {qty:>3} {ep:>9.2f} "
              f"{(f'{bp:.2f}' if bp else '—'):>9} "
              f"{(f'{gap:+.2f}' if gap is not None else '—'):>7} "
              f"{pnl_fill:>+11.2f} "
              f"{(f'{bpnl:+.2f}' if bpnl is not None else 'NULL'):>11}"
              + ("" if closed == qty else f"   ⚠ נסגרו {closed}/{qty}"))

    print("-" * 92)
    _tot = "סה" + chr(34) + "כ"
    print(f"{_tot:>38} {tot_fill:>+35.2f} {tot_book:>+11.2f}")
    if orphan:
        print(f"\n⚠ {len(orphan)} מילויי-יציאה בלי ENTRY מזוהה "
              f"(ברקט מיום קודם, או ENTRY שלא נרשם ביומן)")
    print("\nהערה: 'P&L-מילוי' נגזר אך-ורק ממחירי-סיירה. 'P&L-ספרים' הוא מה ש-v9_trades")
    print("מחזיק. NULL = T-160 סירב להמציא מחיר-יציאה. פער בעמודת-'פער' פירושו")
    print("שהמערכת רשמה מחיר-פקודה במקום מחיר-מילוי.")


if __name__ == "__main__":
    main()
