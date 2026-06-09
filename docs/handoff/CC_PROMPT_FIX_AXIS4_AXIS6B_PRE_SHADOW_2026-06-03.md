# CC PROMPT — תיקון 2 חוסמי-איכות לפני SHADOW (ציר 4 + ציר 6b) · 2026-06-03

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** P0 איכות-נתונים, שער אחרון לפני SHADOW. **אישור Michael 2026-06-03.**
שני הממצאים אומתו בלתי-תלוי ע"י Cowork בקוד. שניהם **חוסמי-SHADOW** (לא "non-blocking") — soak על דאטה מזוהם/חסר = בזבוז.

## ציר 4 — history_loader עוקף את גייט-RTH → ברים מנופחים עם is_synthetic=0
**אומת (Cowork):** `history_loader.py:336` עושה `INSERT OR IGNORE INTO v9_bars_5min` (וכן cumulative_delta:344, volume_profile:352)
**בלי** גייט-RTH — בעוד תיקון B4 הגן רק על ה-POST. תוצאה: ברים pre-RTH מצטברים (vol עד 840K) נכנסים עם `is_synthetic=0`
→ מזהמים את ה-VSA/rolling_avg/כיול שזו מטרת SHADOW (אותה מחלקת באג כמו B4).
**תיקון:**
- החל את אותו גייט-RTH של ה-POST (`_is_within_rth`, 09:30–16:00 `America/New_York`, DST-safe ZoneInfo — כבר קיים ב-`bars.py`) גם ב-`history_loader` לפני ה-`INSERT`, **או** סמן ברי-עומס מחוץ ל-RTH כ-`is_synthetic=1`.
- אל תשבור backfill לגיטימי של ברי-RTH (gap-fill תקין נשאר).
- **אימות (raw):** אחרי תיקון + reload — `MAX(volume) WHERE is_synthetic=0` שפוי (≈ עשרות-אלפים, לא 100K+); 0 ברי is_synthetic=0 עם vol≥100K.

## ציר 6b — ברי woodies_5min לא נשמרים ל-PG (ts unix-int מול עמודת DateTime)
**אומת (Cowork):** `V9Bar5MinWoodies.ts = Column(DateTime(timezone=True))`, אבל `woodies_system.py:548` שולח `bar_ts` כ-unix-int
→ PG דוחה (`column "ts" is of type timestamp ... expression is of type integer`). SQLite היה סלחני; PG קפדן. **ברי S4 לא נכנסים.**
(זה גם מסביר ש-"woodies writes work, 6 rows" מ-`2742e4c` נבדק עם ts לא-מייצג.)
**תיקון:**
- המר `bar_ts` ל-timestamp תקין לפני הכתיבה (ISO string / datetime aware UTC) — באותה צורה ש-writers אחרים עושים (`_ts_from_unix` ב-`bars.py`). זהה גם ל-`v9_bars_30min_woodies` אם רלוונטי.
- שמור TZ מפורש (Rule 4 — לא "assumed local").
- **אימות (raw):** הזרם בר woodies_5min RTH-valid → `COUNT(*) v9_bars_5min_woodies` **עולה**; `SELECT ts ...` מחזיר timestamp תקין.

## Acceptance (✓/✗ + raw)
- [ ] ציר 4: `MAX(volume) WHERE is_synthetic=0` שפוי + 0 ברי-עומס is_synthetic=0 (raw query).
- [ ] ציר 6b: woodies_5min count עולה אחרי בר RTH-valid (raw); ts נשמר כ-timestamp.
- [ ] regression ירוק · commit פר-תיקון · `git log`. סעיף NOT-DONE.

## Invariants
localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · No silent failures · אל תיגע ב-risk-logic/sc_study/polling · Cowork מאמת בלתי-תלוי. אחרי 2 התיקונים + הצלבה → SHADOW נפתח.
