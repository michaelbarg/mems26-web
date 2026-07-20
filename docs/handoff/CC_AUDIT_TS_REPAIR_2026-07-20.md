# CC AUDIT — ביקורת על פעולות cursor הערב (2026-07-20 22:30–23:20 IL)

**אל: cc-macbook / cowork-dev · מאת: cursor-agent · מייקל ביקש ביקורת-נזק מלאה.**
בדקו כל סעיף עם הפקודות המצורפות (חוק-5: פלט-גולמי, לא "אושר"). כל סטייה מה-EXPECTED = דווחו מיד.

---

## מה קרה (רקע ב-3 שורות)
ה-backend של הבוקר (לפני restart 14:30 ET) כתב את כל ברי-ה-RTH של היום **שעה מוקדם** ל-PG
(`v9_bars_5min` אף החזיק 3 קונבנציות במקביל: ‎−3h/−1h/נכון — תוכן משוכפל). ה"12 ברים ראשונים"
שהמסווג ראה היו בעצם השעה השנייה → `S1_IB_SANITY_V1` פסל את ה-IB **הנכון** של Sierra (7552.25/7506.0)
והחליף ב-7523.75/7501.0 → תווית Neutral_Extreme כוזבת מ-13:40 ET. מייקל זיהה (Variation→Trend-down),
אימות-בר-מתמטיקה אישר, מייקל אישר תיקון ב-22:44.

## שינויים שבוצעו (קומיטים `4d1f45f3`, `81fe0e2e`)

### 1. תיקון-דאטה ב-PG (חד-פעמי, עם גיבוי) — `scripts/repair_bars_ts_shift_2026_07_20.py --apply`
שיטה: התאמת-OHLC אמפירית של כל שורת-DB של היום מול `~/SierraChart_Data/v9_export/5min.json`
(עוגן-אמת: epoch-הקובץ+5h = הרגע-האמיתי; אומת מול live_price). **אפס הנחות-TZ.**

| טבלה | לפני | פעולה | גיבוי |
|---|---|---|---|
| `v9_bars_5min` | דלתא {‎−3h:30, ‎−1h:65, 0:11} | DELETE 95 שגויות → INSERT 65 קנוניות מהייצוא (OHLCV+vah/val/poc_vol/cum_delta, symbol='MES') | `v9_bars_5min_bak_0720` (113) |
| `v9_bars_5min_woodies` | דלתא {‎−1h:77, 0:11} | UPDATE ts+1h ל-65 (שדות-CCI/LSMA **נשמרו**) + DELETE 12 כפולות-תוכן | `v9_bars_5min_woodies_bak_0720` (275) |

**בדקו (EXPECTED מימין):**
```sql
-- IB האמיתי חזר לטבלה:
SELECT max(high), min(low), count(*) FROM v9_bars_5min
WHERE ts>='2026-07-20 16:30+03' AND ts<'2026-07-20 17:30+03';   -- 7552.25 | 7506.0 | 12
-- רציפות RTH בלי פערים/כפילויות:
WITH t AS (SELECT ts, lag(ts) OVER (ORDER BY ts) p FROM v9_bars_5min_woodies
  WHERE ts>='2026-07-20 16:30+03' AND ts<'2026-07-20 23:00+03')
SELECT count(*) FROM t WHERE ts-p > interval '5 minutes';        -- 0
SELECT ts, count(*) FROM v9_bars_5min WHERE ts>='2026-07-20 00:00+03'
GROUP BY ts HAVING count(*)>1;                                    -- 0 rows
-- הגיבויים קיימים:
SELECT count(*) FROM v9_bars_5min_bak_0720;                       -- 113
SELECT count(*) FROM v9_bars_5min_woodies_bak_0720;               -- 275
```

**נקודות-נזק אפשריות לבדוק (הודאה-מראש, לא להסתיר):**
1. **7 שורות לא-מותאמות** ב-`v9_bars_5min` (מתוך 113) לא זוהו חד-משמעית ב-OHLC-match ולא נגעתי בהן.
   בדקו: `SELECT * FROM v9_bars_5min WHERE ts>='2026-07-20 00:00+03' AND ts<'2026-07-20 16:30+03'` —
   אם נשארו שורות עם תוכן-RTH בתיוג-בוקר, למחוק ידנית (יש גיבוי).
2. **שורות ה-INSERT** קיבלו `symbol='MES'` ו-vp-fields מהייצוא. ודאו שאין צרכן שמצפה ל-symbol אחר
   ושה-`cumulative_delta` מהייצוא עקבי עם שכנותיו (הוא cumulative — בדקו מונוטוניות סבירה בתוך הסשן).
3. **ברי-woodies מחוץ ל-RTH** (לילה 00:00–15:30) לא נבדקו מול מקור-אמת (אין להם ייצוא-התאמה) — לא נגעתי.
4. **טבלאות אחרות** שנכתבו מברי-הבוקר המוזזים (למשל `v9_bars_cumulative_delta`, `v9_five_min_setups`
   של היום, aggregates) — **לא תוקנו**. השפעה על מסחר-מחר: אפסית (יום חדש), אבל דוחות-היום עלולים להציג
   זמנים שגויים. החליטו אם שווה תיקון או הערת-שוליים.

### 2. תיקון-תווית — `v9_day_type_history` 2026-07-20
`UPDATE ... SET day_type='Normal_Variation' WHERE date='2026-07-20' AND day_type IN ('Neutral_Extreme','Neutral_Center')`
בוצע ב-23:00 — **אבל המנוע-החי דרס חזרה ל-Neutral_Extreme תוך 2 דק'** (state בזיכרון עדיין מורעל,
כותב כל ~2 דק' גם אחרי close). **פעולת-בוקר חובה אחרי ה-restart:** להריץ שוב את ה-UPDATE ולאמת שהוא
מחזיק. `classify_replay?date=2026-07-20` הקנוני כבר מחזיר `Normal_Variation / DOWN / ib_source=sierra_tpo`.

### 3. קוד חדש — `TS_OFFSET_INGEST_GATE_V1` (ברירת-מחדל **OFF** — אפס שינוי-ריצה עד פסיקה)
`backend/v9/api/v9/bars.py`: פונקציה `_ts_offset_ingest_gate` + חיבור ב-`post_bars_5min` ו-`post_woodies_5min`.
לוגיקה: ts-חדש מתקדם push-אחרי-push (פיד חי) אבל >900s מאחורי now → דחיית-batch כנה (בלי ניחוש-shift).
זה סוגר את החור של היום (‎−1h מתחת לחלון `_hour_shift_fix` 3600±120s → לא תוקן ולא נדחה).
בדקו: (א) קריאת-קוד — הדחייה רק כשהדגל ON; (ב) `BRIDGE_TOKEN=test pytest
tests/v9/regression/test_ts_offset_ingest_gate.py -q` → **6 passed**; (ג) שיקול-הדלקה לבוקר (פסיקת-מייקל).

### 4. טסטים (מהבוקר, קומיט `d6478752`) — בידוד דגלי-ייצור ב-2 קבצי-טסט של ה-gateway
`_isolate_gates()` ב-`test_gateway_block_reason_precise.py` + `test_gateway_decisions_feed.py`.
טסט-בלבד. בדקו: עם `.env` מלא → `10 passed` (זה היה פער-§0).

## מה **לא** שונה (לוודא אפס-רגרסיה)
- אפס שינוי בשערי-מסחר/סיכון/sizing/ניתוב. אפס שינוי-דגלים ב-`.env`.
- `_hour_shift_fix` לא שונה. `S1_IB_SANITY_V1` לא שונה (עדיין ON — והוא פעל "נכון" על דאטה רעה;
  ההגנה האמיתית היא שער-ה-TS).
- `flag_guard` צריך להישאר PASS: `python3 scripts/flag_guard.py` (אין דגל חדש ב-.env).

## Rollback מלא (אם מוצאים נזק)
```sql
BEGIN;
DELETE FROM v9_bars_5min          WHERE ts>='2026-07-20 00:00+03' AND ts<'2026-07-20 23:59+03';
INSERT INTO v9_bars_5min          SELECT * FROM v9_bars_5min_bak_0720;
DELETE FROM v9_bars_5min_woodies  WHERE ts>='2026-07-20 00:00+03' AND ts<'2026-07-20 23:59+03';
INSERT INTO v9_bars_5min_woodies  SELECT * FROM v9_bars_5min_woodies_bak_0720;
COMMIT;
```
(+ `git revert 81fe0e2e` לקוד. התווית: `UPDATE v9_day_type_history SET day_type='Neutral_Extreme' WHERE date='2026-07-20'`.)

## שאלות פתוחות למייקל (מהביקורת הזו)
1. הדלקת `TS_OFFSET_INGEST_GATE_V1` ב-restart-הבוקר (המלצת-cursor: כן).
2. סעיף-נזק-4 למעלה: לתקן גם טבלאות-משנה של היום או להסתפק בהערה?
3. `IB_BREAK_ANY_EXPANSION_V1` למחר (ההכרעה הפתוחה מקבוצה-6).
