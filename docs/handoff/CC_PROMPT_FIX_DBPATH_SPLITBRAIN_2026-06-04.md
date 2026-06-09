# CC PROMPT — 🔴 P0 split-brain: כתיבות עם db_path הולכות ל-SQLite, לא ל-PG (מבטל SHADOW GO) · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** P0 שלמות-נתונים. **אומת בלתי-תלוי ע"י Cowork בקוד.** זה מבטל את "migration complete / SHADOW GO".

## הממצא (Cowork, raw — code-level)
`safe_writer._get_engine(db_path)`:
```python
if db_path is None: return app engine   # PG
return create_engine(f"sqlite:///{db_path}")   # ← כל db_path = SQLite engine
```
כלומר **כל קריאה ל-`safe_execute(..., db_path=X)` כותבת ל-SQLite, לא ל-Postgres.** והמחלקות הבאות מאתחלות
`self.db_path` ל**נתיב-SQLite** (ברירת-מחדל) ומעבירות אותו — אז כתיבותיהן נופלות ל-SQLite הישן, **לא ל-PG**:
- `gateway/trading_gateway.py:426,442` (`DB_PATH=./data/mems26_local.db`) — כתיבות הקשורות לעסקאות.
- `systems/tpo/tpo_system.py:449,479,556,564` + `services/tpo_history_snapshotter.py:286` — TPO.
- `systems/reversal/reversal_handler.py:91` — `v9_reversal_enrichment`.
- `systems/footprint/footprint_system.py:326,340,523` — footprint (גם אם מושבת).
- `services/session_boundary/manager.py:60,83,175,180,193,199,206` — **`v9_day_type_state`** (S1).

**תוצאה:** split-brain — קריאות מ-PG (`db/read.py`), אבל כתיבות S1/S3/S4/TPO/gateway ל-SQLite → נתונים נעלמים מ-PG **בשקט**
(מפר Rule 1 + "No silent failures"). ה-soak לא תפס (SQLite קיבל → "0 errors"); ה-audit קרא מ-PG (DB אחר). תיקון woodies (`20f9df7`)
פתר רק אתר אחד; הטענה הקודמת ש-`session_boundary` "works via engine fallback" **שגויה** — הוא נתב ל-SQLite.

## פעולות
1. **הסר `db_path=self.db_path` מכל הכותבים בפרודקשן** (הרשימה למעלה) → ייפלו ל-app engine (PG). ודא ש-`bar_ts`/ts הם timestamp תקין (כמו תיקון 6b), לא unix-int, לכל אחד.
2. **הקשח את `_get_engine` (defense-in-depth):** כש-`DATABASE_URL` הוא Postgres — אם `db_path` שווה ל-DB המקומי המוגדר (או בכלל), **התעלם ממנו והשתמש ב-app engine**, עם `logger.warning` (לא ליצור SQLite engine שקט בפרודקשן). השאר תמיכת-SQLite אמיתית רק לטסטים/מיגרציות מפורשות.
3. **lint-guard:** אסור `safe_execute(..., db_path=...)` עם נתיב-קובץ בפרודקשן (`backend/v9` למעט tests/migrations) → כותב חדש לא יוכל להישחל חזרה ל-SQLite.
4. **אימות פר-מערכת (raw, ל-PG):** הזרם/הפעל כל נתיב (tpo, reversal, day_type_state, gateway-write) ואשר ש-`COUNT(*)` של הטבלה **עולה ב-Postgres** (`psql`/read_scalar על PG), ושאין כתיבה ל-`data/mems26_local.db` (בדוק mtime לא מתעדכן).

## Acceptance (✓/✗ + raw)
- [ ] 0 קריאות `safe_execute(db_path=...)` עם נתיב-קובץ ב-`backend/v9` (למעט tests/migrations) — grep raw.
- [ ] `_get_engine` לא יוצר SQLite engine כש-DATABASE_URL=PG (טסט + warning).
- [ ] פר-מערכת (tpo/reversal/day_type_state/gateway): `COUNT(*)` עולה **ב-PG** אחרי כתיבה (raw); `data/mems26_local.db` mtime לא זז.
- [ ] regression ירוק · commit · `git log` · סעיף NOT-DONE.

## Invariants
localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · No silent failures · get_db בלי lock · אל תיגע risk-logic/sc_study · Cowork מאמת בלתי-תלוי.
**❌ SHADOW נשאר חסום** עד שכל הכתיבות מאומתות ל-PG (לא רק 4+6b).
