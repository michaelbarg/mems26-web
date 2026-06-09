# CC PROMPT — רציפות נרות (diagnose-first → תיקון שורש)

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael: "הנרות לא רציפים, צריך לסדר") · **מצב:** SHADOW
**משמעת:** diagnose-first — **קודם למפות את הפערים המדויקים עם ראיות, ואז לתקן שורש (לא פלסטר)** · Rule 5 · source-of-truth (אפס סינתוז) · אפס שינוי order/risk/sizing · גיבוי DB לפני שינוי נתונים.

## רקע
אחרי תיקון ה-OOH (`0bc2d0f`) ה-backend חי וה-fallback מציג "LAST SESSION", אבל **סדרת הנרות עדיין לא רציפה** (פערים). ידוע מהאבחון: ה-export של Sierra הוא RTH-only, יש פערי גבול-session, ו-lag של ~332s (stale 6m) overnight. הטבלה הרציפה (`v9_bars_5min_woodies`) רצה 24/6.

## שלב 0 · ⚠️ מחיר זמן-אמת תקוע (עדיפות עליונה)
**סימפטום (Michael + צילום Cowork):** ה"מחיר זמן-אמת" בדאשבורד **תקוע על 7590.50**, בעוד המחיר האמיתי ~**7612-7614.90** והנרות עצמם כבר עלו לשם. כלומר סדרת הנרות זזה אבל מחיר ה-live קפא. Michael ביקש שמחיר ה-live יילקח מ-**Woodies** (ה-stream שזז), אך כרגע יש טעות.
**אבחן (diagnose-first, ראיה גולמית):**
1. **מאיפה הדאשבורד לוקח את ה-live price?** (איזה endpoint/WS channel/קובץ — `live_price.json`? `mes_ai_data.json` `current_price`? `/api/v9/live`? WS?). הדבק את הנתיב בקוד (frontend → backend → מקור).
2. **למה הוא תקוע על 7590.50?** בדוק טריות המקור: האם `~/SierraChart_Data/v9_export/live_price.json` מתעדכן על הדיסק (mtime + ערך) או קפוא? (באבחון הקודם הוא הראה 7590.50 ב-04:30). האם ה-backend מקבל ומפיץ אותו, או cache/WS מת (Redis למטה → polling)?
3. **למה ה-Woodies stream כן זז אבל המחיר לא?** השווה: `woodies_5min` current bar close (מתעדכן ל-7614) מול מקור ה-live price (תקוע 7590.50) — הם מנותקים.
**תיקון שורש (אחרי אבחון):** חבר את מחיר ה-live למקור הרציף/הטרי (לפי כוונת Michael — Woodies current value, או תיקון הקובץ/הזרמה שקפא). אפס סינתוז. אמת שהמחיר זז בזמן אמת בצילום/JSON אחרי התיקון.

## שלב 1 · אבחון הפערים (READ-ONLY, ראיות גולמיות)
1. **מפה את הפערים בפועל** ב-`v9_bars_5min` וב-`v9_bars_5min_woodies`: שאילתה שמוצאת חורים ברצף ה-5-דק' (slots חסרים) לאורך 48h אחרונות. הדבק: רשימת הפערים (from_ts → to_ts, מס' slots חסרים), והאם הם ב-RTH / overnight / גבול-session / maintenance (17-18 ET).
2. **שורש לכל סוג פער:** export RTH-only? lag/stale? קליטה מפספסת? dedup מחק יותר מדי? session reset? הבחן בין "אין נתון אמיתי" (maintenance) ל"נתון קיים אך לא נקלט".
3. **השווה מקורות:** האם `v9_bars_5min_woodies` מכסה את הפערים של `v9_bars_5min` (כלומר האם המקור הרציף מכיל את מה שחסר). הדבק ספירות חופפות.

## שלב 2 · תיקון רציפות (אחרי שהאבחון ברור)
- **בנה סדרת 5-דק' רציפה** למקור התצוגה מהטבלה הרציפה (`v9_bars_5min_woodies`, 24/6) עם **gap-fill** ל-slots חסרים שיש להם נתון במקור.
- **תיוג session-phase** (RTH/OVERNIGHT/POST/MAINTENANCE) לכל בר.
- ⚠️ **אפס סינתוז:** ל-slot שבאמת אין בו נתון (maintenance 17-18 ET, שוק סגור) — **אל תמציא בר**. סמן פער אמיתי כ-gap (או דלג), אל תזייף OHLC. (CLAUDE.md §honest failure.)
- ⚠️ **בטיחות:** הרציפות היא לתצוגה/הקשר. נרות overnight/gap-filled **לא** מזינים ירי — שערי ה-RTH נשארים (אומתו: five_min OVERNIGHT_MODE, woodies `_is_rth_bar`, state_machine `is_rth`).
- טפל ב-lag/stale: אם ה-5-דק' מגיע באיחור, אבחן אם זה cadence של overnight (תקין) או באג קליטה (לתקן).

## פלט
`docs/reports/BAR_CONTINUITY_2026-06-01.md`: מפת הפערים (ראיה גולמית) → שורש לכל סוג → diff התיקון → אימות שהסדרה רציפה (שאילתה: 0 פערים בתוך חלונות שיש בהם נתון) + שפערי-maintenance מסומנים ולא מזויפים + שהיסטורי לא מזין ירי. golden/regression. עדכון STATUS_BOARD.

**שערים:** diagnose-first — דווח את מפת הפערים והשורש **לפני** תיקון. אפס סינתוז (פער אמיתי נשאר פער). היסטורי = תצוגה בלבד. גיבוי DB לפני כל מחיקה/שינוי. אל תיגע ב-order/risk/sizing. תאם עם Michael אם הפתרון נוגע בקליטה (bar_ingestion) שכבר תוקנה.
