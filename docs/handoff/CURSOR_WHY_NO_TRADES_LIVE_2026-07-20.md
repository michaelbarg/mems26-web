# cursor — אבחון-חי: למה אין עסקאות (אחרי הדלקת-הדגלים ~13:00 ET)

**מצב:** 4 דגלי-דלתון הודלקו + ריסטארט (13:00 ET). day_type=Variation. מייקל: "למה אין עסקאות?"
**מבצע: cursor · קריאה-בלבד · חוק-5 (פקודה+פלט-גולמי).** ⛔ אין PLACE · אין שינוי-.env/דגלים · אין ריסטארט.
**מטרה: תשובה חד-משמעית — או "שוק-שקט אין setup תקף", או "setup נוצר ונחסם ע"י שער X" (עם ראיה).**

## מה לבדוק (כל שורה = פקודה + פלט + מסקנה)

### 1. הדגלים באמת חיים בתה-process?
`ps eww` של ה-backend / boot-line — אשר `STRUCTURAL_STOP_ORIGIN_V1=1 · STOP_WINDOW_COMPLETED_V1=1 ·
STOP_WIDEN_TO_STRUCTURE_V1=1 · REQUIRE_WITH_TREND_DAY_DIRECTION_V1=1` בפרוסס שרץ (לא רק ב-.env).

### 2. הצינור פעיל?
בר-woodies אחרון (טרי?) · S2 buffer≥4 · bar_router received/dispatched עולה · WS/relay חי.

### 3. גזרת-ההחלטות מאז 13:00 (הלב)
`/api/v9/gateway/decisions` — **כל** setup שהוערך מאז הריסטארט: pattern · direction · day_type · decision · **blocked_by**.
- אם `fired>0` → יש עסקאות (מייקל צודק לבדוק את הרישום).
- אם `blocked>0` → **איזה שער** חוסם עכשיו (זה מה שמייקל רוצה).
- אם `0/0/buffer_len=0` → כלום לא הוערך → עבור ל-4.

### 4. האם setups בכלל נוצרים? (detection מול gateway)
- לוג-הזיהוי (S2_DETECTION_LOG=1) / `audit_pattern_miss --date 2026-07-20 --relax all` — כמה תבניות
  זוהו היום, וכמה מהן **אחרי 13:00**. האם דטקטור מזהה אבל לא משגר ל-gateway?
- `fire_readiness_real --date 2026-07-20` — אילו setups would_fire מול blocked_by (מתחת לדגלים החיים).

### 5. המצב-הנוכחי בשוק — יש setup שאמור לירות עכשיו?
מחיר מול VAH/VAL/POC · trend_state · CVD · האם כרגע יש דפוס (REACTIVE@VAH / ZLR / וכו') שהדוקטרינה
אומרת שצריך לירות, והוא לא נורה? אם כן — עקוב אותו דרך השרשרת ומצא את נקודת-העצירה.

## התוצר
`docs/handoff/WHY_NO_TRADES_2026-07-20.md` — טבלת setups-מאז-13:00 [pattern/dir/day_type/decision/blocked_by] +
**מסקנה אחת:** (א) שוק-שקט (אין setup תקף — תקין) · (ב) setup-נחסם (שם-השער + האם לגיטימי או באג) ·
(ג) detection-לא-מגיע-ל-gateway (חוליה שבורה). אם (ב/ג) — הצע תיקון (דגל-OFF, cowork מאמת, cc מבצע).
```
git pull → בצע → commit+push → שורת-LOG ב-LIVE_CHANNEL.
```
