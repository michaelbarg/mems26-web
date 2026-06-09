# CC PROMPT — באג צ'ארט (setData null) + זיהוי סוג-יום לא לפי האפיון

**תאריך:** 2026-06-01 (RTH חי) · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing.

## חלק A · באג צ'ארט — `candleRef.current.setData` null (תיקון)
**שגיאה:** `Cannot read properties of null (reading 'setData')` ב-`frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx:552` (`ChartV5b.useCallback[loadBars]`).
**שורש (אומת Cowork):** שורה 552 קוראת `candleRef.current.setData(...)` **בלי null-guard**. כש-`loadBars` רץ לפני שה-series נוצר (או אחרי unmount/dispose), `candleRef.current=null` → קריסה.
**תיקון (smallest):** הוסף guard לפני בלוק ה-setData (אחרי שורה 551):
```ts
if (!candleRef.current) return;
```
ובדוק שגם שאר ה-series refs שנעשה בהם שימוש ב-`loadBars` (volume/CVD/overlay) מוגנים (guard / optional-chaining). אמת: טעינה/רענון של הצ'ארט לא קורס, הנרות נטענים.

## חלק B · סוג-יום לא מזוהה לפי האפיון (diagnose-first)
**תלונה (Michael):** המערכת לא מזהה סוג-יום לפי ההנחיות (Day Type spec). ב-RTH ה-day_type נשאר UNKNOWN/לא מסווג כצפוי.
**אבחן (READ-ONLY) — צלם את ה-state החי של S1 ב-RTH והדבק:**
- `opening_type` + confidence (מה זוהה? OPEN_DRIVE/TEST/REJECTION/AUCTION/INDETERMINATE) + מקור (price/CVD).
- IB: high/low/width + class + locked?
- decision-matrix: מה החזיר על (opening × ib_width)?
- `day_type` vote · `lock_state` · confidence · stage נוכחי (A2→C) · staging checkpoint · zohar verdicts.
**זהה איזה תנאי/gate מונע סיווג לפי האפיון:**
- opening_type=INDETERMINATE/UNKNOWN → מדוע? (input חסר? <3 ברים? CVD/price לא מספיק?)
- confidence < סף נעילה (0.85) → תקוע?
- staging cap מחזיק confidence נמוך (flag ON)?
- matrix מחזיר Normal/INDETERMINATE?
**סווג:** באג (סוטה מהאפיון) · מוקדם-RTH (מתפתח, לא באג) · data (קלט חסר לזיהוי). **דווח שורש + תיקון מומלץ — strategic-stop לפני שינוי לוגיקת-זיהוי** (trading logic, אישור Michael).
מקור אפיון: Day Type spec · `MEMS26_PIPELINE_FLOW.html` Phase 1 · RESEARCH_01/03.

## פלט
`docs/reports/CHART_BUG_AND_DAYTYPE_DETECT_2026-06-01.md`: חלק A diff + אימות אין קריסה · חלק B state חי + שורש + סיווג + המלצה. עדכון STATUS_BOARD.

**שערים:** חלק A = תיקון frontend בטוח (null-guard). חלק B = diagnose-first בלבד, strategic-stop לפני שינוי לוגיקת day-type. אפס שינוי order/risk/sizing.
