# CC PROMPT — PG upsert ON CONFLICT ללא constraint תואם → silent dropped writes (P0, חוסם-SHADOW) · 2026-06-03

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** המשך ישיר ל-`POSTGRES_MIGRATION_REPORT_2026-06-03.md`. אימות בלתי-תלוי (Cowork) מצא באג latent שה-soak פספס.

## הממצא (Cowork, raw — code-level)
ה-shim `_sqlite_to_pg_upsert()` (`safe_writer.py:62-114`) **מנחש** את עמודת ה-conflict מרשימת-העמודות,
עם **fallthrough ל-`ON CONFLICT (ts)`**. אם לטבלה אין UNIQUE תואם → Postgres זורק
`there is no unique or exclusion constraint matching the ON CONFLICT specification` → `safe_writer` בולע
ל-warning ומחזיר 0 → **כתיבה שנפלה בשקט** (מפר CLAUDE.md §Rule 1 "honest failure" + "No silent failures").

**אומת (raw):**
- `v9_bars_5min_woodies` (טבלת S4!): INSERT הכותב `(ts, symbol, ...)` (`woodies_system.py:543`) → shim פולט `ON CONFLICT (ts, symbol)`.
  המודל `V9Bar5MinWoodies` (`db/models/bars_woodies.py`) מכיל **רק** `__tablename__` — `ts` index-only, `symbol` לא-unique,
  **אין `__table_args__`/`UniqueConstraint`** → אין constraint תואם → **כל כתיבת בר-woodies 5-דק' נופלת בשקט ב-PG.**
- `v9_reversal_enrichment`: shim פולט `ON CONFLICT (bar_ts)` (`reversal_handler.py`); אין unique על `bar_ts` במודל → אותו כשל (tick_reversal מושבת → דחיפות נמוכה, אבל אותה מחלקה).
- **ה-soak (Phase 5) פספס:** הריץ רק 5 endpoints של ingestion (5min/cvd/imbalance/woodies_5min/tpo); ברי woodies_5min נדחו ע"י גייט-RTH → 0 שורות → נתיב-הכתיבה הזה **לא הורץ**. רק הנתיבים-החמים אומתו.

## פעולות
1. **תקן constraints כך שכל יעד-ON-CONFLICT יתקיים בפועל:**
   - `V9Bar5MinWoodies`: הוסף `__table_args__ = (UniqueConstraint("ts","symbol", name="uq_woodies5_ts_symbol"),)` (או מפתח-בר ייחודי עקבי). זהה גם ל-`v9_bars_30min_woodies` אם כותב OR REPLACE.
   - `v9_reversal_enrichment`: הוסף unique על `bar_ts` (או שנה את יעד ה-conflict ב-shim/ב-SQL).
2. **אודיט מלא:** לכל אחד מ-~32 אתרי `INSERT OR REPLACE`/`OR IGNORE` שעוברים דרך ה-shim — אמת שעמודת/ות ה-ON CONFLICT
   שה-shim מנחש **קיימת כ-UNIQUE/PK בסכמת-PG**. הדבק טבלה: site → table → conflict-col → האם UNIQUE קיים (✓/✗).
3. **העדף לפרוש את ה-shim:** המר את ה-INSERT OR REPLACE לתחביר `ON CONFLICT` מפורש פר-טבלה (לא ניחוש-runtime).
   הניחוש-בזמן-ריצה הוא silent-failure surface שאסור ל-LIVE.
4. **soak מתוקן:** הזרם ברי **woodies_5min תקפים-RTH** + reversal במקביל ל-ingestion → אמת ששורות **נכתבות בפועל**
   (`COUNT(*) v9_bars_5min_woodies` עולה), לא רק "0 errors".
5. **green את 9 הטסטים** (3 `test_historical_replay` + 6 `test_day_type_api_v9`) — עדכן fixtures ל-engine-based, או הדבק raw שמוכיח fixture-only ולא רגרסיה.
6. **ניקויים מינוריים:** `import sqlite3` מת ב-`bridge/v9_startup.py`; נתיב-fallback ל-SQLite ב-`main.py` hydration (מזהיר "malformed"); `session_boundary/manager.py` db_path-fallback.

## Acceptance (✓/✗ + raw)
- [ ] `v9_bars_5min_woodies` + `v9_reversal_enrichment` בעלי UNIQUE תואם ל-conflict-col. 
- [ ] טבלת-אודיט של כל ~32 האתרים: conflict-col קיים כ-UNIQUE (0 ✗).
- [ ] soak כולל woodies_5min RTH-valid + reversal → `COUNT(*)` של שתי הטבלאות **עולה** (raw).
- [ ] 9 הטסטים ירוקים (או raw שמוכיח fixture-only). [ ] commit פר-תיקון · `git log`.

## Invariants
localhost בלבד · ❌ לא Render/Upstash/prod-PG · get_db בלי lock · **❌ לא לאסוף SHADOW עד ש-(1)+(3) עוברים** (כתיבות-woodies לא-נופלות-בשקט). Cowork מאמת בלתי-תלוי.
