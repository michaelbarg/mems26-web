# CC — פרומפט-המשך מאוחד (ממשיך את Cowork מאותה נקודה) · 2026-06-09

אתה ממשיך עבודה משותפת עם **Cowork (verifier בלתי-תלוי)**. עבוד **יעיל דרך ה-index**,
הדבק ראיות גולמיות (Rule 5), אל תיגע ב-fire-path/trading-logic בלי STRATEGIC-STOP + אישור-Michael.

## קרא קודם (לפי הסדר)
1. `CLAUDE.md` — §Pre-LIVE Discipline · §Standing Decisions · §S2⟂S3 · §Codebase Index Protocol · **§Frontend Polling Floors**.
2. `SYSTEM_INDEX.md` + ה-`_INDEX.md` הרלוונטי — **תמיד אתר קובץ/פונקציה דרך ה-index לפני grep עיוור.** (תזכורת: `backend/main.py` הוא ה-entrypoint, **לא** `backend/v9/main.py`.)
3. הזיכרון של Cowork + הדוחות: `docs/reports/ALL_FIXES_SUMMARY_2026-06-09.txt`, `ISSUES_AND_RECOMMENDATIONS_2026-06-09.txt`.
4. הפרומפטים הפתוחים שכתב Cowork: `CC_EXPLAIN_AND_CLOSE_GAPS_2026-06-09.md`, `CC_FIX_FAKE_TESTS_AND_REPLAY_2026-06-09.md`, `HANDOFF_MACHINE_MIGRATION_AND_DEV_STATE_2026-06-09.md`.

## איפה אנחנו (מצב מאומת ע"י Cowork)
**קוד תקין + committed:** #1 S4 stop (`0bc1d20`) · #3 S2 partial-bar (`2aef154`) · #2/#4 ts (`23163d9`) ·
#5 inspector=engine (`0efe9e0`) · S2⟂S3 (`638e664`). **כל 5 התיקונים נכונים ברמת-הקוד.**
**אבל לא לסמן "DONE":** ראה §A.

---

## A · 🔴 לסגור טסטים-מזויפים + flag + replay-artifact  [המשימה הדחופה]
**מקור מלא:** `docs/handoff/CC_FIX_FAKE_TESTS_AND_REPLAY_2026-06-09.md`. תקציר:
- 3 טסטים **טאוטולוגיים** (משכפלים את לוגיקת-הייצור בתוך הטסט, לא מייבאים את המודול):
  `test_inspector_engine_alignment.py:36-37` · `test_s2_detect_on_completed_bar.py:19,28,37` · `test_dll_fallback_stop.py`.
  כתוב מחדש כך שכל טסט **מייבא+קורא לקוד האמיתי** ומוכיח RED-on-revert ע"י `git stash` (הדבק 2 ריצות).
- **#2/#4 בלי שום טסט** — הוסף.
- **#3 בלי flag** (`five_min_system.py:922` קשיח) — הוסף flag הפיך או נמק בכתב.
- **Replay "80 fires" בלי artifact** — commit script + `docs/reports/REPLAY_2026-06-08_RAW.txt`. **תקן ניפוח:** 43/51 הם Double-Top על *אותו* setup (בעיה 3) → דווח **distinct** בנפרד (~9-10), לא 80.

## B · 🟡 בורדים + index-קוד  [Cowork מתחיל; CC משלים]
- `gen_index.py` אחרי קבצי-הטסט החדשים → commit `_INDEX` מרענן.
- ROADMAP_TO_LIVE.html + STATUS_BOARD.md: שורת-לוג finding→fix→verification ל-5 התיקונים (Cowork עושה; אל תכפיל).

## C · 🆕 אינדקס + ביקורת לדוחות-הסוכנים  [חדש — בקשת Michael]
אין `_INDEX.md` ל-`docs/reports/` (~150) ול-`docs/handoff/` (~248). בנה:
1. **`docs/reports/_INDEX.md` + `docs/handoff/_INDEX.md`** — שורה לכל קובץ: תאריך · נושא · תוצר/ממצא עיקרי (משפט).
   הרחב את `gen_index.py` שיכסה גם תיקיות-docs (לא רק קוד), כדי שיתעדכן אוטומטית.
2. **`docs/reports/AGENT_AUDIT_REGISTER_2026-06-09.md`** — טבלת-ביקורת על דוחות-המערכת מהימים האחרונים:
   `דוח · המלצה · אושרה? (Michael) · בוצעה? (commit) · רלוונטית עדיין? · נכונה מבחינת-מסחר?`.
   סווג כל פריט KEEP/DONE/STALE/REJECTED. **הצלב מול git log** (בוצע=commit קיים) ומול §Standing Decisions (לא להחיות דגל-כבוי).
3. **בקרת-תקינות-מסחר:** לכל המלצה שנגעה ב-fire/stop/target — סמן אם היא תואמת את טבלת-הסטופים המוגדרת ואת §Standing Decisions; כל סתירה = שורת-OPEN לאישור-Michael.

## D · 🆕 Backtester יומי + סוכן  [חדש — בקשת Michael · אפיון לפני בנייה]
Cowork יכתוב אפיון מלא; הנה העקרונות שיש לאמת מול ה-index לפני בנייה:
- **בנה על הקיים, אל תשכפל:** הזרם ברים דרך **הגלאים האמיתיים** (`five_min`/`woodies`) ואת היציאות דרך
  **`backend/v9/services/trade_manager/manager.py`** (לוגיקת stop/T1-T5/contracts/trailing האמיתית). אתר ב-index.
- **סטופ/targets = הטבלה המוגדרת** per-pattern × per-day-type (xlsx/Drive + `config/*.yaml`). **אל תמציא סטופים** — צרוך את הטבלה.
- **מקור-נתונים:** Sierra export היסטורי עם שדות-study (CCI/SWI/TCCI/volume) — source-of-truth, לא חישוב-פייתון. (תלוי החלטת-Michael §החלטות.)
- **מטריקות:** ירה/לא · entry/exit price+זמן · stop+תזוזות · R · P&L (Gross+Net) · #עסקאות distinct · win-rate · MAE/MFE · משך · פילוח pattern/day-type/שעה.
- **הנחת תוך-בר:** stop-first (שמרני) כברירת-מחדל.
- **סוכן יומי:** scheduled-task שמריץ על היום הקודם ושולח דוח. Cowork מקים את התזמון אחרי שה-harness עובד.
- **תנאי-קדם:** בעיה 3 (Double-Top dedup) חייבת להיסגר קודם — אחרת ירי-רפאים מנפחים P&L.

## E · אחרי A+D-prereq: אימות-ירי-חי RTH (§6.2)
ריצת-RTH: ZLR/Reactive **באמת יורים** → `active_patterns` + שורות ב-`v9_trades`. (הערה: "אתמול 0 עסקאות
ב-trades" = באג #2/#4, תוקן `23163d9` — **אמת שזה באמת נכתב עכשיו**, אל תניח.)

---

## החלטות שממתינות ל-Michael (אל תבצע trading-logic בלי אישור)
| # | החלטה | המלצת-Cowork |
|---|-------|--------------|
| 1 | מקור-נתונים backtest | Sierra historical export + study fields |
| 2 | בסיס-P&L | Gross + Net (slippage+עמלות) |
| 3 | היקף-מערכות | S2+S4 (S3 מושתק) |
| 4 | הנחת תוך-בר | stop-first שמרני |
| 5 | בעיה 3 Double-Top dedup | לאשר — תנאי-קדם ל-backtest |
| 6 | בעיה 6 CCI≠DLL | להשתמש ב-CCI מה-export |
| 7 | בעיה 7 Initiative calib | החלטת-Michael |
**מוגדר כבר (constraint):** סטופ+targets per-pattern×day-type — ה-backtester צורך את הטבלה, לא ממציא.

## פורמט תשובה (Rule 5)
לכל משימה: diff/commit · פלט גולמי (pytest stash=אדום/pop=ירוק) · NOT-DONE · אישור שאף דגל default-off לא הודלק.
**סדר:** A (דחוף) → C (index+audit) → B (בורדים) → D-אפיון → E. עצור-אסטרטגית לפני כל trading-logic.
