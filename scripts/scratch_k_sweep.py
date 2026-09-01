#!/usr/bin/env python3
"""סריקת-k לסף ה-MAE-scratch — מה היה קורה בכל סף, על נתוני-אמת.

הרקע (AUDIT_2026-09-01): דלי-ה-scratch (<3 נק') הוא היחיד שמרוויח — 112 עסקאות,
75% פגיעה, +$24.48 לעסקה. כל השאר: 269 עסקאות, ‎−$26,131. הסף שיצא אתמול על ZLR
היה 4.0 נק' ב-ATR14=3.84 (‏1.04×ATR) — בתוך הדלי 3-5 נק' שפגיעתו 4%.

השיטה: לכל עסקה סגורה מחשבים MAE (התנועה הגרועה ביותר בין כניסה ליציאה) מברי-5-דק',
ו-ATR14 מ-14 הברים שלפני הכניסה. לכל k: אם MAE ≥ k×ATR ⇒ העסקה הייתה נחתכת ב-k×ATR;
אחרת נשארת כפי שהייתה.

🔴 שלוש מגבלות שחייבות להופיע בכל ציטוט של הפלט:
  1. MAE מחושב מ-high/low של ברי-5-דק' — **הנתיב בתוך הבר לא ידוע**. אם גם הסף וגם
     היעד נגעו באותו בר, ההנחה כאן היא שהסקראץ' קדם. זו הטיה **לטובת** הסקראץ'.
  1ב. שני תיקוני-ניוון הוחלו: עלות-החיתוך מוגבלת ל-|כניסה−יציאה| בפועל (אחרת
     המודל ממציא הפסד גדול מהסטופ האמיתי ב-k גבוה), ורצפת-עלות 0.5 נק' לעמלה+החלקה
     (אחרת k→0 = יציאה חינם והעקומה משתפרת עד לאבסורד).
  2. ‏`exit_fills` קיים ב-12 עסקאות מתוך 413 (‏T-190) ⇒ **אי-אפשר לדעת אילו עסקאות
     כבר עברו T1**. הסקראץ' האמיתי פועל רק לפני T1. כאן מוחל על כולן ⇒ הטיה נוספת.
  3. אפס החלקה (slippage). מילוי בדיוק בסף.
⇒ המספרים כאן הם **גבול-עליון** לשיפור, לא תחזית.
"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text

DB = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")
DOLLARS_PER_PT = 5.0
FLOOR_PTS = 0.5   # עמלה+החלקה: יציאה לעולם אינה חינם (רצפה של 2 טיקים)
eng = create_engine(DB)

TRADES = text("""
SELECT id, direction, entry_ts, exit_ts, entry_price, exit_price, pnl_usd, mode,
       COALESCE((quality->>'contracts')::int, 1) AS contracts,
       COALESCE(NULLIF(pattern_id_at_entry,''),'?') AS pattern
FROM v9_trades
WHERE exit_price IS NOT NULL AND pnl_usd IS NOT NULL
  AND entry_ts >= '2026-07-01' AND exit_ts IS NOT NULL
ORDER BY id
""")

MAE = text("""
SELECT max(high) hi, min(low) lo FROM v9_bars_5min_woodies
WHERE ts >= :a AND ts <= :b
""")

ATR = text("""
SELECT avg(tr) FROM (
  SELECT greatest(high-low,
                  abs(high - lag(close) OVER (ORDER BY ts)),
                  abs(low  - lag(close) OVER (ORDER BY ts))) tr
  FROM v9_bars_5min_woodies WHERE ts < :a ORDER BY ts DESC LIMIT 15
) q
""")


def main():
    rows = []
    with eng.connect() as c:
        for t in c.execute(TRADES).mappings():
            m = c.execute(MAE, {"a": t["entry_ts"], "b": t["exit_ts"]}).first()
            a = c.execute(ATR, {"a": t["entry_ts"]}).scalar()
            if not m or m.hi is None or not a or a <= 0:
                continue
            ep = float(t["entry_price"])
            mae = (ep - float(m.lo)) if t["direction"] == "LONG" else (float(m.hi) - ep)
            rows.append({
                "id": t["id"], "mode": t["mode"], "pattern": t["pattern"],
                "mae": max(0.0, mae), "atr": float(a),
                "pnl": float(t["pnl_usd"]), "c": int(t["contracts"]),
                # מרחק-היציאה בפועל בנקודות — תקרה לעלות-החיתוך
                "real_loss_pts": (abs(ep - float(t["exit_price"]))
                                  if float(t["pnl_usd"]) < 0 else 0.0),
            })

    if not rows:
        print("אין נתונים"); return

    print(f"בסיס: {len(rows)} עסקאות סגורות עם ברים · "
          f"ATR14 חציוני {sorted(r['atr'] for r in rows)[len(rows)//2]:.2f} נק'\n")
    base = sum(r["pnl"] for r in rows)
    base_w = sum(1 for r in rows if r["pnl"] > 0)
    print(f"{'k':>5} {'סף@ATR':>8} {'P&L':>11} {'דלתא':>10} {'פגיעה':>7} "
          f"{'נחתכו':>7} {'מנצחות שנהרגו':>14} {'$ שאבדו':>10}")
    print("-" * 82)
    print(f"{'היום':>5} {'—':>8} {base:>11,.0f} {'—':>10} "
          f"{100.0*base_w/len(rows):>6.1f}% {'—':>7} {'—':>14} {'—':>10}")

    for k10 in range(5, 16):
        k = k10 / 10.0
        tot = cut = killed = lost = 0.0
        wins = 0
        for r in rows:
            thr = k * r["atr"]
            if r["mae"] >= thr:
                # תיקון-ניוון 1: חיתוך מוקדם לא יכול לעלות יותר מהיציאה בפועל.
                # בלעדיו המודל "ממציא" הפסדים גדולים מהסטופ האמיתי ב-k גבוה.
                cost = min(thr, r["real_loss_pts"]) if r["real_loss_pts"] > 0 else thr
                # תיקון-ניוון 2: רצפת-עלות — עמלה + החלקה של טיק. בלעדיה k→0 = יציאה
                # חינם, והעקומה משתפרת מונוטונית עד לאבסורד.
                p = -(cost + FLOOR_PTS) * r["c"] * DOLLARS_PER_PT
                cut += 1
                if r["pnl"] > 0:                 # מנצחת שנהרגה ע"י הסף
                    killed += 1
                    lost += r["pnl"] - p
            else:
                p = r["pnl"]
            tot += p
            if p > 0:
                wins += 1
        print(f"{k:>5.1f} {k*rows[0]['atr']:>7.1f}נ {tot:>11,.0f} {tot-base:>+10,.0f} "
              f"{100.0*wins/len(rows):>6.1f}% {int(cut):>7} {int(killed):>14} {lost:>10,.0f}")

    print("\n⚠ גבול-עליון בלבד — ראה שלוש המגבלות ב-docstring.")
    print("  בפרט: הסקראץ' האמיתי פועל רק לפני T1, וכאן הוא מוחל על כל העסקאות.")


if __name__ == "__main__":
    main()
