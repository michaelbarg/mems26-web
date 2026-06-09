# HANDOFF — צ'אט הבא (Cowork) · backtester + מצב מלא · 2026-06-09

אתה (Cowork הבא) = **orchestrator + verifier בלתי-תלוי** של MEMS26. CC מבצע על ה-Mac;
אתה כותב פרומפטים, מצליב (**Rule 5: פקודה+פלט גולמי**), מעדכן בורדים, מאשר לפני fire-path.
**עבוד דרך ה-index** (`SYSTEM_INDEX.md` + `_INDEX.md`) — אל תגרֵף עיוור.

## קרא קודם
1. `CLAUDE.md` — §Pre-LIVE Discipline · §Standing Decisions · §S2⟂S3 · §Codebase Index Protocol · §Frontend Polling Floors.
2. `SYSTEM_INDEX.md` (`backend/main.py` הוא ה-entrypoint, **לא** `backend/v9/main.py`).
3. הזיכרון של Cowork + הדוחות `docs/reports/ALL_FIXES_SUMMARY_2026-06-09.txt` · `ISSUES_AND_RECOMMENDATIONS_2026-06-09.txt`.

## ⚠️ מסמכים שנכתבו בסשן הזה אבל **טרם נשלחו ל-CC**
Michael עוד לא מסר אותם ל-CC. הם מוכנים, מאומתים-Cowork:
| קובץ | מה | סטטוס |
|------|-----|-------|
| `docs/handoff/CC_CONTINUATION_MASTER_2026-06-09.md` | פרומפט-ההמשך המאוחד ל-CC (A→E) | **מוכן, לא נשלח** |
| `docs/handoff/CC_FIX_FAKE_TESTS_AND_REPLAY_2026-06-09.md` | ביקורת-עומק על טסטים-מזויפים + flag #3 + replay-artifact | מוכן, לא נשלח |
| `docs/handoff/CC_EXPLAIN_AND_CLOSE_GAPS_2026-06-09.md` | 8 פערים + 7 בעיות-מערכת | מוכן, לא נשלח |
| `docs/handoff/HANDOFF_MACHINE_MIGRATION_AND_DEV_STATE_2026-06-09.md` | מעבר-מחשב + worklist | מוכן |
→ **הצעד הראשון:** ודא עם Michael אילו מהם נשלחו, ואל תכפיל פרומפט קיים.

## מצב מאומת (Cowork)
**5 תיקונים — קוד תקין + committed:** #1 S4 stop (`0bc1d20`) · #3 partial-bar (`2aef154`) ·
#2/#4 ts (`23163d9`) · #5 inspector=engine (`0efe9e0`) · S2⟂S3 (`638e664`).
**🔴 לא DONE:** 3 טסטים **טאוטולוגיים** (משכפלים לוגיקה בטסט, לא מייבאים מודול) + #2/#4 בלי טסט +
#3 בלי flag + replay "80 fires" בלי artifact (ו-43/51 הם Double-Top כפול = ניפוח). פירוט: `CC_FIX_FAKE_TESTS...`.
**⚠️ git:** הענף **26 commits לפני origin** — push לפני כל clone/מעבר (Cowork חסום מ-push, רק מה-Mac).

## worklist פתוח (A→E) — מקור: `CC_CONTINUATION_MASTER_2026-06-09.md`
- **A** סגירת טסטים-מזויפים + flag #3 + replay-artifact (דחוף).
- **B** בורדים (ROADMAP+STATUS_BOARD) + `gen_index` לקוד.
- **C** 🆕 אינדקס+ביקורת לדוחות: אין `_INDEX.md` ל-`docs/reports`(~150)/`docs/handoff`(~248); + טבלת-ביקורת המלצות (אושר/בוצע/רלוונטי/נכון-מסחרית).
- **D** 🆕 backtester + סוכן יומי (ראה משימה-ראשית למטה).
- **E** אימות-ירי-חי RTH — כולל אימות שעסקאות **באמת** נכתבות ל-`v9_trades` (הבאג מאתמול).

---

## 🎯 המשימה הראשית של הצ'אט הבא — backtester "כתוב-פעם, שפר-בלבד"
**דרישת-Michael:** סקריפט מסודר שמריץ את הבדיקה (האם המערכת יורה · entry · מיקום-סטופ ·
יציאה · רווח/הפסד · #עסקאות · זמן · תזוזת-סטופ · כל מטריקה) — **שלא נכתב מחדש כל פעם**, אלא
משתפר בהתאם לשינויים. אם מורכב מדי — **המלץ דרך חכמה יותר**.

### המלצת-Cowork (כבר גובשה — אמת מול ה-index ואז ספֵּק אפיון)
**אל תבנה backtester עצמאי שמשכפל זיהוי/יציאות — הוא יזדקן וידרוש כתיבה-מחדש (בדיוק החשש).**
במקום זה: **driver דק יחיד מעל הרכיבים האמיתיים:**
- מזרים ברים היסטוריים דרך **הגלאים האמיתיים** (`five_min`/`woodies`) ואת היציאות דרך
  **`backend/v9/services/trade_manager/manager.py`** במצב `REPLAY/OFFLINE` (flag), לא DB חי.
- **סטופ/targets = הטבלה המוגדרת** per-pattern × per-day-type (`config/*.yaml` + xlsx/Drive). **אל תמציא** — צרוך.
- כותב תוצאות לטבלה ייעודית `v9_backtest_runs` (+ דוח). פרמטרים: טווח-תאריכים, מערכות.
- **למה זה "כתוב-פעם":** הוא **מייבא** את מנוע-הייצור (לא מעתיק) → כשהזיהוי/סטופ משתנים,
  ה-backtest משתמש בלוגיקה החדשה **חינם**. תחזוקה = רק להתאים את ה-driver, לא לשכתב את הליבה.
- **סוכן יומי:** scheduled-task שמריץ את ה-driver על היום הקודם ושולח דוח (Cowork מקים אחרי שעובד).
- **תנאי-קדם:** בעיה 3 (Double-Top dedup) חייבת להיסגר קודם — אחרת ירי-רפאים מנפחים P&L.
- **אזהרת-יושר:** P&L מ-backtest היפותטי (slippage/fills/נתיב-תוך-בר); הנחת תוך-בר = stop-first שמרני.

### אם גם ה-driver הדק מורכב מדי — חלופות (לשקול, לפי עלות/תועלת)
1. **Replay דרך ה-API החי במצב-shadow** על ברים מוזרקים — פחות קוד, אבל תלוי-backend-רץ.
2. **דוח-תצפית בלבד** (להרחיב את `missed_trade_detector` שכבר מחשב `hypothetical_r`) — בלי P&L-מלא, מהיר, פחות-מדויק.
3. **ספריית-backtest חיצונית** (vectorbt/backtrader) — רק אם נקבל את אותם entry/stop מהמערכת; אחרת drift.
→ ההמלצה נשארת #driver-דק (1 הכי קרוב). ספֵּק אפיון מלא ל-Michael עם trade-offs לפני בנייה.

---

## החלטות שממתינות ל-Michael (אל תבצע trading-logic בלי אישור)
1. מקור-נתונים → **Sierra historical export + study fields** (source-of-truth).
2. בסיס-P&L → **Gross + Net** (slippage+עמלות).
3. היקף → **S2+S4** (S3 מושתק).
4. הנחת תוך-בר → **stop-first** שמרני.
5. בעיה 3 Double-Top dedup → לאשר (תנאי-קדם).
6. בעיה 6 CCI≠DLL → CCI מה-export.
7. בעיה 7 Initiative calib → החלטת-Michael.
**מוגדר כבר (constraint, לא החלטה):** סטופ+targets per-pattern×day-type — ה-backtester צורך את הטבלה.

## הצעד הראשון בצ'אט הבא
1. ודא עם Michael אילו פרומפטים כבר נשלחו ל-CC (למעלה).
2. אם A עוד פתוח — הצלב את חבילת-CC (Rule 5) לפני שמתקדמים.
3. ספֵּק את אפיון ה-backtester (driver-דק) עם trade-offs → אישור-Michael → פרומפט-בנייה ל-CC → סוכן-יומי.
