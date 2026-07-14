# iMac — בדיקת פרה-לייב להרצה + דיווח · 2026-07-14

**למכונת-המסחר (iMac).** מריץ: Cowork/CC על ה-iMac. **הכל על SIM** (שער `is_sim=1`
לפני כל פקודה — אל תריץ פקודות אם `is_sim=0`!). מטרה: להוכיח שהמערכת מזהה נכון את
סיירה מקצה-לקצה, לפני שמייקל מעביר ללייב. **החזר דוח עם ראיות (Rule 5); מייקל ממתין
לאישור-Cowork-dev לפני מעבר-לייב.**

## 0 · קדם (משיכה + בריאות)
- [ ] כפתור-עדכון → HEAD אחרון · `flag_guard PASS` · `fire_drill 🟢`.
- [ ] `sierra_state.json` טרי (<3ש') · `is_sim=1` · `order_placement_armed` מוצג.

## 1 · זיהוי-סיירה (המוניטור החדש)
- [ ] `curl -s localhost:8000/api/v9/agent/sierra_live_check` → **verdict 🟢**.
      צרף את ה-JSON המלא (‏is_sim · armed · qty · closures_today · records==reality).

## 2 · סבב-סים מלא (הוכחת זיהוי-עסקה + זיהוי-סגירה-על-מימוש)
שער-בטיחות: ודא `is_sim=1` לפני כל צעד.
- [ ] **BUY 3** (stop+t1+t2+t3) → `sierra_state`: `qty=3, working=6`. המוניטור:
      `open_trade_detect` מזהה עסקה-פתוחה · `records==reality` MATCH.
- [ ] המתן למימוש **T1** (או הזז-מחיר-סים אם צריך) → `qty` יורד ל-2 · `closures_on_fills`
      רושם את הסגירה-החלקית עם `exit_reason` (T1). **זו ההוכחה שהמערכת "יודעת" שנסגר על מימוש.**
- [ ] **FLATTEN_ACCOUNT** → `qty=0, working=0` · המוניטור חוזר ל-flat · reconcile MATCH.

## 3 · לוגר-Google-Sheets (T2) — אימות על עסקת-סים
> הלוגר הוא **LIVE-only** (מדלג demo/sim). כדי לבדוק בלי כסף-אמיתי:
- [ ] אפשרות א' (מומלץ): הרץ ידנית `python3 -c "from backend.v9.services.gsheets_trade_logger import log_live_fill; ..."`
      עם `entry_order_id` של עסקת-הסים מצעד-2, ואמת שהשורה הגיעה ל-Sheet (עם P&L מ-fills).
- [ ] אפשרות ב': אם קשה — דווח שהלוגר מוגדר (URL+flag) ושהנתיב `log_live_fill →
      LedgerTrade → webhook` תקין בקוד, ונאמת על העסקה-הלייב-הראשונה.

## 4 · דיווח (Rule 5)
החזר: פלט-JSON של §1 · לוג-qty של §2 (3→2→0) עם exit_reasons · תוצאת §3 ·
`flag_guard`/`fire_drill` · **וכל DIVERGENCE/NAKED/ALERT שצץ**. אם כל 3 הירוקים —
ציין "‏PRE-LIVE GREEN". אם משהו לא-ירוק — עצור, אל תעבור-לייב, דווח את השורש.

## שער-לייב (מייקל)
מייקל מעביר ללייב **רק אחרי**: (1) הדוח מ-iMac ‏PRE-LIVE GREEN, (2) אישור-Cowork-dev
של הדוח. אז: כיבוי Trade-Simulation-Mode בסיירה (`is_sim→0`) + חשבון-אמת ממומן.
`In:22=1` = חימוש (כבר); הוא **אינו** סים/לייב — סים/לייב = מתג-הסים של סיירה.
