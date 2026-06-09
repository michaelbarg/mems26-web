# CC PROMPT — הגירת ה-stack המקומי ל-Postgres מקומי (root fix ל-DB corruption) · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** P0 בטיחות. commit אטומי פר-שלב · לא `git add -A` · פלט גולמי.
**אישור Michael 2026-06-03:** נתוני-עבר מתכלים → מתחילים נקי על Postgres מקומי. **פתרון-שורש להחלפת SQLite.**
תוכנית-אב מלאה: `docs/plans/POSTGRES_MIGRATION_PLAN_2026-06-03.md` (קרא אותה קודם).

## הקשר — למה ולא band-aid נוסף
אבחון read-only (Cowork, 2026-06-03) על `data/mems26_local.db`:
- `quick_check` → `Page 76860 btreeInitPage error 11` + `Rowid out of order` → `dbstat` ממפה ל-**`v9_bars_footprint`**.
  הקריאה ל-`v9_bars_5min` כבר נכשלת `malformed` → זו הסיבה ל"אין נרות".
- הכותב היחיד (לא-טסט) של הטבלה: `POST /api/v9/bars/footprint` (`bars.py:415`) → `db.add`+`db.commit()`,
  כתיבת-ORM **לא-מסורלת** העוקפת את `safe_writer`, על endpoint סינכרוני שרץ ב-threadpool במקביל לכתיבות safe_writer.
- ה-endpoint **לא** מגודר ב-`FOOTPRINT_DISABLED`, ו-`FOOTPRINT_DISABLED` **לא מיוצא** ב-`start_all.sh`/LaunchAgent/`.env`
  → footprint **לא באמת מושבת בזמן ריצה** (בניגוד ל-CLAUDE.md). `FootprintStream` פעיל ב-`ALL_STREAMS`.
- WAL **אחיד** (engine + safe_writer שניהם WAL+busy_timeout=5000). כלומר השורש = **מקביליות-כתיבה מ-ORM שלא עובר lock אחד**,
  ותיקון-כותב-אחד-בכל-פעם הוא whack-a-mole. **Postgres מסיר את כל המחלקה** (MVCC נייטיב).

## גבולות-גזרה (Invariants — קשיח)
- **Postgres מקומי בלבד** (`postgresql://localhost/mems26`). ❌ לעולם לא Render/Upstash/prod-Postgres.
- **Bridge Local-Only** נשאר: דחיפה רק ל-`http://localhost:8000`.
- get_db: לא להחזיר lock. Sierra=SoT. אל תיגע `sc_study/`/B2/B3/LaunchAgent-stability/polling-floors.
- **❌ לא לאסוף SHADOW** עד Phase-5 soak-מקביליות נקי עובר.
- לשמור SQLite כ-fallback; **לא** למחוק `safe_writer`/כותבים-גולמיים עד PG מוכח על כמה סשנים.

## שלבים (כל שלב = שער; עצור + דווח raw לפני המעבר)

### Phase 0 — Postgres מקומי רץ
- התקן+הפעל Postgres מקומי (Homebrew `postgresql@16` או Postgres.app). `createdb mems26`.
- `export DATABASE_URL=postgresql://localhost/mems26` (start_all.sh + הסביבה; **לא** ב-LaunchAgent של הגשר אם זה משנה את כללי-הענן — רק את ה-DB המקומי).
- אמת `session.py` נכנס לענף non-sqlite (pool_pre_ping, pool_size=5, ללא WAL pragma).
- **שער 0:** הדבק `python3 -c "from backend.v9.db.session import engine; print(engine.connect().execute(__import__('sqlalchemy').text('SELECT 1')).fetchone())"` → `(1,)`.

### Phase 1 — schema ריק על PG  ⚠️ גדול יותר מ-init_db()
- **ממצא Cowork (אימת, מפריך את הנחת "ה-ORM פשוט יעבוד"):** רק **22 מתוך 43** הטבלאות יש להן מודל-ORM ב-`db/models.py`.
  `Base.metadata.create_all` ייצור **רק את ה-22** → 21 הנותרות (raw-SQL-managed) **לא יתקיימו** ב-PG → כל INSERT אליהן ייכשל.
  ביניהן חמות: `v9_bars_cumulative_delta`, `v9_bars_imbalance`, `v9_bars_stacked_imbalance`, `v9_bars_volume_profile`,
  `v9_bars_woodies`, `v9_woodies_signals`, `v9_day_type_state`, `v9_chop_score`, `v9_footprint_journal`, `v9_tpo_journal`, `v9_tpo_sessions` ועוד.
- **ה-DDL כבר חולץ מ-`sqlite_master`** (קריא למרות ה-corruption): **`docs/handoff/POSTGRES_MIGRATION_MISSING_DDL_2026-06-03.sql`** — 19 טבלאות-חיות
  (2 ה-`*_backup_p31s9` מתכלים, דלג). המר ל-PG: `INTEGER PRIMARY KEY AUTOINCREMENT`→`BIGSERIAL PRIMARY KEY`; `TEXT`/`REAL` תקפים;
  שמר `bar_id TEXT UNIQUE` (יעד ה-`ON CONFLICT` של Phase 3). העדף **הוספת מודלי-ORM** ל-19 על-פני DDL ידני (אז create_all מכסה הכל).
- migration `019` (`sqlite3.connect`+`INSERT OR IGNORE`) SQLite-only → המר/דלג (fresh start).
- **שער 1:** הדבק `information_schema.tables` מול 41 הצפויות (43 פחות 2 backups); seed-rows נדרשים (`v9_session_meta`) קיימים.

### Phase 2 — המרת קריאות (~22 אתרים raw `mode=ro`)
- הוסף helper משותף (למשל `db/read.py: read_all(sql, params)`) שמשתמש ב-`engine.connect()`+`text()` — עובד על SQLite **וגם** PG.
- המר כל `sqlite3.connect(f"file:...?mode=ro")`: placeholders `?`→`:name`; גישת-שורה לפי-שם; הסר `mode=ro`/`immutable=1`.
- רשימת אתרים (מ-grep): woodies/routes, open_type_routes, admin_routes, bars_5min_history, tpo_routes×5, footprint/routes,
  day_type_v9_routes×3, reversal_routes, key_levels_routes×2, shadow_routes, woodies_chart_routes, woodies_system,
  footprint_system (כולל `hydrate():110` שפתח RW בטעות), s2/woodies/day_type/bridge-inspectors, tpo_system, day_type/api×2, prev_day×2, historical_replay, session_boundary/manager.
- **שער 2:** `grep -rn "sqlite3.connect" backend/ | grep -v test` = 0; קריאה לדוגמה מחזירה נתונים מ-PG.

### Phase 3 — המרת כתיבות / פרישת safe_writer (13 אתרים)
- `INSERT OR REPLACE` → `INSERT ... ON CONFLICT (<unique>) DO UPDATE` (ודא unique/PK נכון בכל מודל); או upsert דרך ORM.
- ה-13 קוראי-safe_writer + כותבי-ORM (`post_footprint`, trades, trade_manager flush×6, trading_gateway, woodies/api, day_type/api/consumer, five_min, woodies_system) → על PG `db.commit` בטוח; אין צורך ב-lock.
- **שער 3:** `grep -rn "safe_execute\|INSERT OR REPLACE\|INSERT OR IGNORE" backend/ | grep -v test` = 0 (או safe_writer עוטף-engine בלבד); כתיבה לדוגמה נכתבת ל-PG.

### Phase 4 — גשר
- `bars_5min_stream.py:32` (קריאת MAX(ts) backfill) + `v9_startup.py:134` (DELETE wipe-today) → דרך ה-API או חיבור-PG.
- ריבוי-processes (backend+bridge על אותו PG) = הניצחון של PG. שמר Bridge Local-Only.
- **שער 4:** הגשר עולה, דוחף ל-localhost:8000, אין שגיאות-DB ב-`/tmp/bridge.err.log`.

### Phase 5 — דיאלקט + אימות + soak (שער-GO)
- grep+המרה: `PRAGMA`/`sqlite_master`/`AUTOINCREMENT`/`strftime`/`julianday`. הסר WAL/busy_timeout/checkpoint/`check_same_thread`.
- אימות: (a) אפליקציה עולה על PG; (b) גשר דוחף ונתונים זורמים; (c) **4 צירי UAT** על endpoint-נתונים (quality/recency/cardinality/latency<סף);
  (d) **soak-מקביליות** footprint+woodies+day_type+ingestion במקביל ≥10 דק' → 0 שגיאות, 0 deadlocks.
- **שער 5 (GO):** הדבק raw של (c)+(d). זה מחליף את `integrity backend-כבוי=ok` של SQLite.

## Acceptance (פר-שלב, ✓/✗ + raw)
- [ ] Phase 0: `SELECT 1` מ-PG. [ ] Phase 1: כל הטבלאות+seed קיימות. [ ] Phase 2: 0 raw sqlite3 reads.
- [ ] Phase 3: 0 raw-SQLite writes / 0 `INSERT OR REPLACE`. [ ] Phase 4: גשר דוחף ל-PG נקי.
- [ ] Phase 5: 4-UAT + soak-מקביליות נקי (raw). [ ] regression ירוק · commit פר-שלב · `git log`.

## הערה
זה reopener של "DB root fix verified" → הפתרון האמיתי הוא הגירה, לא עוד המרת-כותב. עדכן STATUS_BOARD/ROADMAP פר-שער (Cowork מאמת בלתי-תלוי). אל תאסוף SHADOW עד שער-5.
