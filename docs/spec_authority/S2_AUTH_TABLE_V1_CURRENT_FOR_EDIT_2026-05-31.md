# S2 Auth Table — מצב נוכחי (LOCKED V1) · עותק עבודה לעדכון min3/max5

**תאריך:** 2026-05-31 · **מקור אמת:** `backend/v9/systems/five_min/auth_table_v1.py` (70 תאים, LOCKED 2026-05-25)
**מטרה:** Michael מעדכן ידנית לפי החלטת GAP-4 (per-trade, **min 3 / max 5**). זה **עותק עבודה** — לא דורס את V1 הנעול עד אישור.

**איך לקרוא כל תא:** `verdict · HIGH/MED/LOW`
- `verdict` ∈ FULL / REDUCED / SKIP (SKIP = לא יורה כלל).
- שלושת המספרים = כמה חוזים לפי ה-quality tier (קרבת מחיר ל-POC/VAH/VAL): HIGH / MEDIUM / LOW.
- היום הטווח 0–3. בעדכון שלך הטווח יהיה **3–5** (ו-SKIP נשאר 0).

---

## הטבלה הנוכחית (10 תבניות × 7 סוגי-יום)

| Pattern \ DayType | Trend_Normal | Trend_DD | Neutral_Extreme | Variation | Neutral_Center | Normal | Nontrend |
|---|---|---|---|---|---|---|---|
| **REACTIVE_LONG** | REDUCED · 2/1/0 | REDUCED · 2/1/0 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | SKIP · 0/0/0 |
| **REACTIVE_SHORT** | REDUCED · 2/2/0 | REDUCED · 2/2/0 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | SKIP · 0/0/0 |
| **INITIATIVE_LONG** | FULL · 3/2/1 | FULL · 3/2/1 | SKIP · 0/0/0 | FULL · 3/2/1 | SKIP · 0/0/0 | SKIP · 0/0/0 | SKIP · 0/0/0 |
| **INITIATIVE_SHORT** | FULL · 3/2/1 | FULL · 3/2/1 | SKIP · 0/0/0 | FULL · 3/2/1 | SKIP · 0/0/0 | SKIP · 0/0/0 | SKIP · 0/0/0 |
| **INVERSE_HNS_LONG** | SKIP · 0/0/0 | SKIP · 0/0/0 | FULL · 3/2/1 | REDUCED · 2/1/0 | FULL · 3/2/1 | FULL · 3/2/1 | SKIP · 0/0/0 |
| **HNS_TOP_SHORT** | SKIP · 0/0/0 | SKIP · 0/0/0 | FULL · 3/2/1 | REDUCED · 2/1/0 | FULL · 3/2/1 | FULL · 3/2/1 | SKIP · 0/0/0 |
| **DOUBLE_BOTTOM_EE_LONG** | SKIP · 0/0/0 | SKIP · 0/0/0 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | SKIP · 0/0/0 |
| **DOUBLE_TOP_AA_SHORT** | SKIP · 0/0/0 | SKIP · 0/0/0 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | FULL · 3/2/2 | SKIP · 0/0/0 |
| **BULL_FLAG_LONG** | FULL · 3/2/2 | FULL · 3/2/2 | REDUCED · 2/2/0 | FULL · 3/2/2 | SKIP · 0/0/0 | REDUCED · 2/2/0 | SKIP · 0/0/0 |
| **BEAR_FLAG_SHORT** | FULL · 3/2/2 | FULL · 3/2/2 | REDUCED · 2/2/0 | FULL · 3/2/1 | SKIP · 0/0/0 | REDUCED · 2/1/0 | SKIP · 0/0/0 |

---

## נקודות החלטה לעדכון (min 3 / max 5, per-trade)

1. **המרת tier:** הצעה ל-mapping ישיר — HIGH→5, MED→4, LOW→3 (SKIP נשאר 0). זה מעלה הכל ב-+2. אשר/שנה.
2. **תאים עם LOW=0 (לא-SKIP):** היום יש תאים כמו REACTIVE_LONG/Trend_Normal = `REDUCED 2/1/0` — ב-LOW tier הם **לא יורים** (0) למרות verdict≠SKIP. עם רצפת min-3, LOW=0 הופך ל-3 או נשאר 0 (אל-תירה ב-LOW)? צריך הכרעה פר-שורה כזו.
3. **verdict REDUCED מול FULL:** האם בעולם 3-5 עדיין צריך REDUCED (סייז קטן יותר), או שכל מה שלא SKIP = טווח 3-5 מלא?
4. **תקרת המערכת:** `MAX_CONTRACTS` יעודכן ל-**5** וייאכף (כרגע 2, dead). מינימום 3 ייאכף לכל ירי שאינו SKIP.

**ערוך את הטבלה למעלה ישירות** (החלף את ה-H/M/L לערכי 3-5 שתרצה), וכשתסיים אבנה ממנה את `auth_table_v1.py` המעודכן + עדכון האסרטים (max=5), עם golden regression. *(שינוי sizing = trading logic → ייכנס מאחורי אישורך כ-D-decision.)*
