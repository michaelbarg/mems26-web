# CC PROMPT — Build Status: להציג סוג-יום + סיווג פתיחה מסודר (שאדע שהמערכת מזהה ומטפלת)

**תאריך:** 2026-06-01 (RTH חי) · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing.
**בקשה (Michael):** ב-Build Status **לא רואים את כל הקטגוריה של סוג-היום והפתיחה מסודרת** — צריך שאראה שהמערכת **יודעת לזהות** ו**מטפלת** בזה.

## Phase A · אבחון (READ-ONLY)
1. מה Build Status מציג כיום ל-**S1 (Day Type)**? (האם יש section ל-S1 כמו ל-S2/S3/S4, או רק למערכות היורות?) הדבק.
2. אילו שדות S1 זמינים ב-endpoint (`/api/v9/day_type/...` / build_status) שאינם מוצגים: `opening_type`+confidence · `ib_width` class (NARROW/MEDIUM/WIDE/EXTREME) · `day_type` vote · `lock_state` · `confidence` · stage (A2/A3/B/C) · decision-matrix result · staging checkpoint (30/60/90).
3. קבע מה חסר בתצוגה.

## Phase B · להציג מסודר ב-Build Status
הוסף/הרחב section **S1 · Day Type + Opening** שמראה במבט:
- **סיווג פתיחה:** OPEN_DRIVE / TEST_DRIVE / REJECTION_REVERSE / AUCTION_IN/OUT + confidence + מקור (price / CVD כשהדגל ON).
- **IB:** high/low/width + class (NARROW/MEDIUM/WIDE/EXTREME) + locked?
- **סוג-יום:** ה-vote הנוכחי + lock_state + confidence + באיזה stage (A2→C) + מה ה-decision-matrix החזיר.
- **staging:** checkpoint נוכחי (30/60/90) אם הדגל ON.
- כל שדה עם Live/Required/Present כמו שאר ה-stages, כך ש-Michael רואה ש-S1 **מזהה ומטפל** (לא "—").
- pre-RTH: להציג "ממתין ל-RTH" במקום ריק.

## אימות (Rule 5)
- ב-RTH: ה-section מציג את הסיווג החי (opening_type, ib_width, day_type, lock_state, confidence) ומתעדכן ככל שמתפתח.
- screenshot של ה-section המלא.

## פלט
`docs/reports/BUILD_STATUS_DAYTYPE_VISIBILITY_2026-06-01.md`: מה היה חסר · diff (frontend + endpoint אם צריך) · screenshot. עדכון STATUS_BOARD.

**שערים:** תצוגה בלבד (observability) · אפס שינוי order/risk/sizing/לוגיקת-זיהוי · אם נדרש שדה שלא קיים ב-endpoint — להוסיף לפלט ה-API (לא לשנות את הזיהוי עצמו).
