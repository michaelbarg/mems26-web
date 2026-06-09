# CC PROMPT — תיקון 2 באגי wiring → התבניות נדרכות (S4 bar_count + S2 opening_type)

**תאריך:** 2026-06-01 (RTH, ~שעתיים אל תוך המסחר) · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing.
**רקע:** Michael — **התבניות צריכות להיות ברובן ARMED אחרי שעתיים, והן לא.** CC זיהה 2 באגי wiring שזה השורש:

## באג 1 · S4 `_bar_count=None` → trend תקוע GRAY/YELLOW → A1 חוסם את כל 9 התבניות
- BarRouter **כן** שולח `woodies_5min` ל-S4, אבל WoodiesSystem **לא סופר ברים** (`_bar_count` לא מתעדכן) → trend persistence לא נספר → `trend_state` תקוע GRAY/YELLOW → **A1 Trend-Gate vetoes כל 9 התבניות** → S4 לעולם לא נדרך.
- **תקן:** WoodiesSystem יגדיל `_bar_count` בכל בר `woodies_5min` שמתקבל (וימלא את ה-buffer כראוי). smallest change.
- **אמת:** `bar_count` עולה · `trend_state` מתקדם ל-BLUE/RED (לא תקוע GRAY) · תבניות S4 עוברות את A1 ומגיעות ל-armed.

## באג 2 · S2 `opening_type=NA` → S1 לא מפרסם classification event → gating שבור
- אפס אירועי `day_type_classification` בלוג → DayType **לא מפרסם** את הסיווג ל-BarRouter → S2 לא מקבל `opening_type` → ה-day-type gating של S2 שבור → תבניות S2 חסומות.
- **תקן:** S1 יפרסם `day_type_classification` event (opening_type + day_type + confidence) ל-BarRouter בכל סיווג/עדכון; S2 (וכל צרכן) יקבל ויעדכן את ה-opening_type/day_type שלו.
- **אמת:** S2 מקבל opening_type חי · ה-gating של S2 עובד · תבניות S2 נדרכות.

## אימות סופי (Rule 5) — #4
אחרי שני התיקונים, ב-RTH: **רוב התבניות (S2/S3/S4) ARMED** (לא חסומות-ע"י-באג). לכל תבנית שעדיין לא armed — להראות שזה **אין-setup לגיטימי** (תקין) ולא wiring/gate שבור. הדבק per-pattern state (armed/blocked + סיבה).

## day-type continuous (דרישת Michael)
ודא שאחרי 30 דק' ה-day-type **ממשיך לסווג רציף לפי איך שהיום מתנהג** (re-diagnosis מתמשך) — לא תקוע על סיווג אחד. (אחרי שבאג 2 מתוקן והסיווג זורם, לאמת שה-vote מתעדכן עם הברים.)

## פלט
`docs/reports/FIX_WIRING_PATTERNS_ARM_2026-06-01.md`: diff שני התיקונים · אימות trend→BLUE/RED · S2 מקבל opening_type · per-pattern armed/blocked + סיבה · day-type מסווג רציף. עדכון STATUS_BOARD.

**שערים:** תיקוני wiring (ספירת ברים + פרסום event) — תשתית, לא לוגיקת-זיהוי. אם נדרש שינוי לוגיקה → strategic-stop. אפס שינוי order/risk/sizing.
