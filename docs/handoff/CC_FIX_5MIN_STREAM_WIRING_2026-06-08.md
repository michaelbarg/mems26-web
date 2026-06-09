# CC — שורש-2: פיצול 5min vs 5min_continuous (market-data route, §7a!)

**רקע (Cowork אבחן בקוד + Michael אישר: יש ברים על מסך Sierra, זו בעיית-חיווט אצלנו):**
- מנוע ה-day_type ניזון מ-`bar_router.subscribe("5min", _day_type_on_bar)` (main.py:413).
- ה-stream **"5min"** כותב ל-`v9_bars_5min` — **תקוע בשישי 23:55**.
- הברים הטריים של היום ב-**`v9_bars_5min_continuous`** (stream "5min_continuous", טרי).
- `/bars/5min` (bars.py:341) מדווח `rth_skipped` — חשד שה-RTH-gate (bars.py:_is_rth)
  **דוחה את ברי-RTH של היום בגלל TZ** (משפחת I-20/C-6), או שה-export 5min.json תקוע ב-Globex.

**⚠️ §7a — market/time data path.** אסור לשנות בלי: (1) לקרוא
`docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md §7a`, (2) לאמת מול ה-export החי ב-
`~/SierraChart_Data/v9_export/`, (3) **אפס סינתוז** OHLC. diagnose-first, read-only עד
שהשורש ברור. פלט גולמי → `docs/reports/FIX_5MIN_WIRING_2026-06-08.txt`.

## 1 — איזה export טרי? (mtimes + last bar ts)
```bash
for f in 5min 5min_continuous; do
  echo "== $f.json =="; stat -f '%Sm' ~/SierraChart_Data/v9_export/$f.json 2>/dev/null
  tail -c 250 ~/SierraChart_Data/v9_export/$f.json; echo; done
```
**שאלה:** האם `5min.json` באמת תקוע ב-Globex (04:50 ET) או שיש בו ברי-RTH של היום?

## 2 — האם ה-RTH-gate דוחה ברי-RTH טריים? (TZ)
```bash
grep -n "_is_rth\|et_minutes\|RTH_START\|RTH_END\|ZoneInfo\|America/New_York" backend/v9/api/v9/bars.py | head
tail -60 /tmp/backend.log | grep -iE "rth_skip|RTH time-gate|inserted=0"
```
קח בר-RTH אמיתי של היום (ts ידוע) והעבר ב-`_is_rth(ts)` ידנית — מחזיר True או False?
אם False על בר-RTH אמיתי → ה-gate מפרש שגוי את ה-TZ → **זה השורש** (דוחה ברים נכונים).

## 3 — DB: מה באמת טרי
```bash
for t in v9_bars_5min v9_bars_5min_continuous; do
  psql "$DATABASE_URL" -c "SELECT '$t', MAX(ts) FROM $t;"; done
```

## 4 — מצב המנוע החי (אחרי restart עם תיקון-Cowork bebea27)
Cowork תיקן את ה-endpoint המת (status קורא עכשיו את `app.state.day_type_machine`).
אחרי restart:
```bash
curl -s localhost:8000/api/v9/status | python3 -c "import sys,json;print(json.load(sys.stdin).get('day_type'))"
```
זה יראה את הסיווג **האמיתי** של המנוע החי (לא ה-wrapper המת).

## הכרעה (אחרי 1-4, דווח ל-Cowork+Michael לפני תיקון)
- אם השורש = **RTH-gate TZ** → תקן את המרת-ה-TZ ב-`_is_rth` (משפחת I-20/C-6) → ברי-RTH
  ייכנסו ל-`v9_bars_5min` והמנוע יקבל אותם. (smallest fix, §7a: לאמת מול Sierra.)
- אם השורש = **export 5min.json תקוע** → בעיית-Sierra (chart-source), לא קוד — דווח ל-Michael.
- אם צריך **לחבר את המנוע ל-continuous** → שינוי-subscribe; החלטת-Michael (משנה מקור-בר).

## NOT-DONE
- אל תשנה את נתיב-הברים לפני קריאת §7a + אימות-Sierra חי + אישור-Michael.
- אפס סינתוז. עצור-ושאל אם השורש לא חד-משמעי.
