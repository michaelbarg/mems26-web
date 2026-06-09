# AGENT PROMPT — חקר + עיצוב-מחדש של עמוד Trades (design-research, NOT implementation) · 2026-06-03

**סוג משימה:** סוכן-חקירה/עיצוב, **read-only**. לחקור את המערכת ולהציע עיצוב-מחדש לעמוד Trades.
**לא לממש קוד.** התוצר = מסמך-עיצוב + mockup. אישור Michael 2026-06-03.

## המטרה (במילים של Michael)
עמוד Trades שיהיה **נוח לעבודה חכמה ולהסקת מסקנות** — לא רק רשימת עסקאות, אלא משטח שממנו אפשר **להחליט כיול**:
מה עובד, מה לא, ולמה. זכור: מטרת SHADOW היא לאסוף דאטה לכיול — העמוד צריך לשרת את ההחלטות האלה.

## שלב 1 — חקירה (read-only, הבן לפני שמעצבים)
1. **מודל-הנתונים:** `backend/v9/db/models.py` (`V9Trade`) + `v9_trade_management_log` — אילו שדות קיימים בפועל
   (entry/exit/stop/T1–T3/firing_system/pattern/day_type_at_entry/R/MAE/MFE/mode/result/timestamps…). **רשום את הרשימה המלאה.**
2. **ה-API:** `backend/v9/api/v9/trades.py` (+ `/trades/active`) — מה נחשף, באילו צורות.
3. **ה-UI הקיים:** `frontend/v9/src/v9/components/trades/*` (TradesView/TradesTable/TradeFilters/SelectedTradePanel/TradePathVisual/…).
4. **חוב ידוע:** `docs/reports/TRADES_PAGE_CHECKLIST_2026-05-31.md` + `CC_PROMPT_TRADES_PAGE_AUDIT_EXPAND_2026-05-31.md` —
   באגים שהעיצוב-מחדש **חייב** לפתור: Scratch תמיד 0 · mode=SHADOW default · מסנן-תאריך לקסיקלי · חסר WR%+R.
5. **משטח-אחות:** איך `BuildTreeView` עוצב (`docs/plans/BUILD_STATUS_REDESIGN_MOCKUP.html`) — לעקביות שפה-עיצובית (`design/tokens`).

## שלב 2 — חשיבה: אילו מסקנות הטריידר צריך להסיק
עצב **לאחור מהשאלות**, לא מהשדות. לכל הפחות:
- ביצועים **פר-מערכת** (S2/S3/S4) ו**פר-pattern** ו**פר-day-type**: WR, expectancy, ממוצע-R, מספר-עסקאות.
- **התפלגות יעדים:** כמה הגיעו ל-T1/T2/T3, כמה stopped, כמה BE/scratch — והאם הסכמה פר-day-type מתממשת.
- **MAE/MFE** (כמה "כאב" לפני שעבד) → תובנות stop/target.
- **זמן-ביום / killzone**, ו-trend מצטבר (equity curve) — מה משתפר/מתדרדר לאורך ה-soak.
- **drill-down** מעסקה בודדת (path: entry→stop/targets→ניהול→exit) לתמונה-הגדולה ובחזרה.

## שלב 3 — תוצר (deliverables)
1. **מסמך-עיצוב** `docs/plans/TRADES_PAGE_REDESIGN_2026-06-03.md`: שאלות-המפתח → אילו פאנלים/ויזואליזציות עונות עליהן → layout (סקירה→drill-down) → אילו שדות כבר קיימים מול אילו **חסרים ב-backend** (לסמן "צריך backend", לא לסנתז).
2. **Mockup** (HTML, בסגנון `BUILD_STATUS_REDESIGN_MOCKUP.html`, `design/tokens`).
3. **gap-list:** מה ה-backend צריך לחשוף בנוסף (WR/expectancy/R/MAE/MFE aggregations) — כקלט לפרומפט-מימוש עתידי.

## Invariants
read-only, **לא לממש** · source-of-truth: לעצב רק סביב שדות אמיתיים, חסרים = "ממתין ל-backend" (לא סינתזה) · localhost · לא לגעת ב-risk-logic. Michael מאשר את העיצוב לפני מימוש.
