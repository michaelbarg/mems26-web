# CC PROMPT — RTH עכשיו · 4 דחופים (לא לאבד יום מסחר)

**תאריך:** 2026-06-01 (RTH חי) · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing · strategic-stop על DLL/trading-logic.
סדר ביצוע לפי עדיפות. דווח אחרי כל פריט.

## P1 · POC/VAH/VAL של היום — דחוף (לא לאבד את ה-VA של היום)
מקור: `CC_PROMPT_RESTART_FIX_POC_VAH_VAL_2026-06-01.md`. **השורש (Michael): ה-POC נמצא ב-Sierra chart 3, לא chart 12.**
- **נתיב מהיר קודם:** בדוק אם ל-DLL יש **Input** ל-chart-number של ה-TPO/VA (כמו Input 19=12 ל-Woodies). אם כן → **הגדר ל-3 ב-Sierra UI — מיידי, ללא rebuild**, וה-POC יתוקן עכשיו.
- אם hardcoded → DLL cross-chart read מ-chart 3 (strategic-stop: diff לפני deploy, runbook §7a, לא לשבור chart 12/#5).
- אמת מול Sierra: POC **7594.75** / VAH **7593.50** / VAL **7582.75** (IB כבר תואם).

## P2 · Build Status — סוג-יום + סיווג פתיחה: להציג ולדאוג שעובד
מקור: `CC_PROMPT_BUILD_STATUS_DAYTYPE_OPENING_VISIBILITY_2026-06-01.md`.
- אבחן **למה** S1 (day-type+opening) לא מופיע מסודר ב-Build Status (אין section? endpoint לא מחזיר?).
- הצג section S1: opening_type+conf · IB width+class · day_type vote · lock_state · confidence · stage · staging — עם Live/Required/Present, כך ש-Michael רואה שהמערכת **מזהה ומטפלת**.

## P3 · שכל המערכות יכולות לירות
- אמת ב-RTH ש-**S2 · S3 · S4** כולן **יכולות** לירות (כרגע נראה רק S4 HTLB ירה).
- לכל מערכת: האם היא **חסומה ע"י באג** (wiring/gate שגוי) או פשוט **אין setup כרגע** (תקין)? הבחן ביניהם עם ראיה (לוג/state per-system).
- תקן רק מה שחסום-ע"י-באג (לא לכפות ירי). strategic-stop אם נדרש שינוי trading-logic.

## P4 · זיהוי סוג-יום עובד לפי האפיון
מקור: `CC_PROMPT_CHART_BUG_AND_DAYTYPE_DETECT_2026-06-01.md` חלק B (מתחבר ל-P2).
- אבחן למה day-type/opening לא מסווג לפי האפיון; זהה ה-gate. **strategic-stop לפני שינוי לוגיקה.** ייתכן קשור ל-P1 (אם opening/VA ממקור שגוי).

## פלט
דוח מרוכז `docs/reports/RTH_NOW_PRIORITIES_2026-06-01.md` (או per-פריט) + עדכון STATUS_BOARD אחרי כל פריט. Rule 5 (ראיות גולמיות: Sierra-vs-dashboard, per-system state, screenshots).

**שערים:** P1 נתיב-מהיר (Input) עדיף על rebuild. DLL/trading-logic = strategic-stop + אישור Michael + diff. אפס שינוי order/risk/sizing. firing RTH-gated ללא שינוי.
