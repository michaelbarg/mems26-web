# פרומפט CC — אבחון בלבד: באג TZ ב-BarLevelDetector (T1 לא נתפס)

> להדבקה ב-Claude Code. **קרא קודם `CLAUDE.md` (§Source-of-Truth, Rule 4 TZ).**
> ⚠️ **DIAGNOSE ONLY — אפס שינוי קוד.** diagnose-first לפני תיקון לוגיקת מסחר.
> התוצר הוא אבחון + הצעת תיקון, **לא** התיקון עצמו.

---

## הרקע
מתוך `PYTEST_GREEN_FINAL_2026-05-31.md`: הכשל היחיד שנשאר —
`tests/atomic/test_cross_system_integration.py::test_bar_level_detector_closes_trades`
— **T1 לא נתפס**. תצפית: trade LONG entry=7450 T1=7455 FILLED; bar high=7456 (חוצה
T1); ts עתידי; DB מבודד. חשד: `bar_level_detector._parse_ts` / השוואת datetime
naive מול aware (~שורה 91) גורמת ל-entry guard לדלג על הבר.

## מה לאבחן (עם ראיות גולמיות לכל צעד)

1. **שחזר:** רוץ את הטסט, הדבק traceback מלא + השורה המדויקת שנכשלת.
2. **קרא** `bar_level_detector.py` — `on_bar`, `_parse_ts`, ה-entry guard (~91).
   הצג: איזו השוואה בדיוק, ומה ה-**types** של שני הצדדים (naive/aware) ברגע הכשל
   (הוסף הדפסות זמניות **בטסט/בסקריפט אבחון נפרד**, לא בקוד production).
3. **מקור אי-ההתאמה:** מאיפה מגיע כל ts —
   - ה-bar ts (מה הפורמט ב-`v9_bars_5min`/הזרם — naive או aware? איזה TZ?)
   - ה-trade `entry_ts` (איך נשמר/נטען — naive או aware?)
   מי משניהם naive ומי aware, ולמה.
4. **היקף (קריטי):** האם זה משפיע **רק על הטסט**, או גם על **SHADOW חי**? כלומר —
   בקליטה אמיתית, האם bar ts ו-entry_ts עקביים (שניהם aware/UTC) או מעורבים? אם
   מעורבים גם בחי → T1/T2 עלולים לא להיתפס בפועל. אמת מול נתונים אמיתיים (שאילתה).
5. **קשר ל-1.6:** מה תיקון ה-T1 מ-30/5 שינה (`9410279` / subscription ל-woodies_5min
   + dedup), ולמה הוא לא כיסה את ה-tz-mismatch הזה?
6. **blast radius:** מי עוד משתמש ב-`_parse_ts` / באותה השוואה (rg), שעלול להיות
   מושפע מאותו תיקון.

## תוצר
`docs/reports/DIAGNOSE_T1_TZ_2026-05-31.md`:
- שורש מאומת (types + מקור naive/aware + פלט גולמי).
- היקף: טסט-בלבד מול SHADOW-חי (עם ראיה).
- קשר ל-1.6.
- **הצעת תיקון** (נרמול UTC tz-aware עקבי — איפה בדיוק) + blast radius — **כהצעה, לא מיושם**.
- מה רגרסיה צריכה לכסות.

## אסור
שינוי קוד production · תיקון הבאג · "1-line quick fix". אבחון בלבד → עצור → דווח →
המתן להחלטת Michael על התיקון.
