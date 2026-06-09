# Postgres Migration Plan — root fix for DB corruption | 2026-06-03

**החלטת Michael (2026-06-03):** נתוני-עבר מתכלים (אפשר למחוק) → מתחילים נקי על **Postgres מקומי**.
זהו פתרון-השורש: הוא מחסל את **כל** מחלקת ה-corruption של SQLite, לא רק את footprint.

## למה זה פותר מהשורש (כולל footprint)
כל ה-corruption כאן נובע מ-SQLite היותו **קובץ** שכמה כותבים/חיבורים ניגשים אליו במקביל
(backend threadpool + safe_writer + bridge-process). `safe_writer`, ה-`_write_lock`,
ומשחק ה-whack-a-mole של "להמיר עוד כותב" קיימים **רק** כדי לעקוף את המגבלה הזו.
Postgres הוא process-שרת עם MVCC שמטפל במקביליות נייטיב → אותו `db.commit()` של
`post_footprint` (ושל ~20 כותבי-ORM) **פשוט עובד**, בלי corruption, בלי lock, בלי gate.
אפשר בסוף **למחוק** את `safe_writer` ואת הכותבים הגולמיים.

## ⚠️ מה Postgres *לא* פותר לבד (ולמה זה לא flip-flag)
1. **לא מרפא נתונים מושחתים על-דיסק.** ה-SQLite הנוכחי `malformed` — אי אפשר להגר ממנו.
   כיוון שנתוני-עבר מתכלים: **לא מהגרים נתונים** — מקימים schema ריק ונותנים ל-data החדש לזרום. (recovery מתבטל.)
2. **קוד SQLite-ספציפי יישבר.** הטענה ב-handoff §3 "ה-ORM פשוט יעבוד" נכונה רק לנתיבי-ORM.
   audit (read-only, 2026-06-03) מצא חלקים שחייבים המרה:
   - **~22 נתיבי-קריאה גולמיים** `sqlite3.connect(f"file:...?mode=ro")` (URI של SQLite) — יישברו.
   - **13 קבצים** קוראים ל-`safe_writer` (כתיבה גולמית עם תחביר `INSERT OR REPLACE`) — SQLite-only.
   - **~34 landmines של דיאלקט**: `INSERT OR REPLACE`/`INSERT OR IGNORE` (חייב→`ON CONFLICT`), `PRAGMA`, `sqlite_master`.
   - **2 נגיעות-SQLite ישירות בגשר**: `bars_5min_stream.py:32` (קריאת MAX(ts)) + `v9_startup.py:134` (DELETE wipe-today).
   - driver: `psycopg2-binary>=2.9` **כבר ב-requirements.txt** ✓.
   המשמעות: גם עם נתונים-נקיים, **קוד-הקאטאובר הוא big-bang** — עד שכל נתיבי ה-raw-SQLite מומרים, האפליקציה לא רצה טהור על PG.

## גבולות-גזרה קשיחים (אסור לחרוג)
- **Postgres מקומי בלבד (`localhost`/`127.0.0.1`)**. לעולם לא ה-Postgres של Render, לא Upstash, לא prod.
- כלל **Bridge Local-Only** נשאר: הגשר דוחף **רק** ל-`http://localhost:8000`.
- אל תיגע ב-Render/Upstash/prod-Postgres (פריסה נפרדת/ישנה).
- get_db: לא להחזיר lock (לא רלוונטי על PG ממילא).
- **❌ לא לאסוף SHADOW** עד שה-stack רץ טהור על PG **+** soak-מקביליות נקי (ראה Phase 5).

## שלבים (כל שלב = שער; CC עוצר + מדווח raw לפי CC_HANDOFF_CONTRACT)

**Phase 0 — infra (Postgres מקומי רץ).** Homebrew `postgresql@16` (או Postgres.app), `createdb mems26`,
`DATABASE_URL=postgresql://localhost/mems26`. לוודא `session.py` מתחבר (ענף non-sqlite: pool_pre_ping, ללא WAL — נכון).
שער: `SELECT 1` עובר.

**Phase 1 — schema ריק.** `init_db()` → `Base.metadata.create_all`. **אודיט קריטי:** לוודא שלכל 40+ הטבלאות
שנכתבות יש מודל-ORM ב-`db/models.py`. טבלאות שנוצרו רק דרך migrations/raw-SQL (למשל migration 019,
שמשתמש ב-`sqlite3.connect`+`INSERT OR IGNORE` — SQLite-only) לא ייווצרו ע"י create_all → להמיר DDL ל-PG או
לזרוע ב-ORM. שער: כל הטבלאות קיימות ב-PG; seed-rows נדרשים קיימים.

**Phase 2 — המרת קריאות (~22 אתרים).** `sqlite3.connect(mode=ro)` → קריאת-engine משותפת (`engine.connect()`+`text()`),
שעובדת גם על SQLite וגם על PG. לשים לב: placeholders `?`→`:name`, גישת-שורה לפי-אינדקס מול שם, נפילת `mode=ro`/`immutable=1`.
שער: 0 `sqlite3.connect` שאינו-טסט ב-`backend/`; קריאות מחזירות נתונים מ-PG.

**Phase 3 — המרת כתיבות / פרישת safe_writer (13 אתרים).** `INSERT OR REPLACE` → `INSERT ... ON CONFLICT (pk) DO UPDATE`
(דורש unique/PK נכון בכל מודל). אפשרות נקייה: upsert דרך ORM. `post_footprint` db.commit → עובד על PG כמו-שהוא
(שאלת ה-footprint-disable הופכת ל-החלטת-מוצר בלבד, לא בטיחות-DB). שער: 0 כתיבות raw-SQLite; כתיבות עוברות ל-PG.

**Phase 4 — גשר.** `bars_5min_stream` (קריאת backfill) + `v9_startup` (wipe-today DELETE) → דרך ה-API או חיבור-PG.
ריבוי-processes הוא בדיוק הניצחון של PG (multi-client נייטיב). לשמר Bridge Local-Only. שער: גשר עולה ודוחף, אין שגיאות-DB.

**Phase 5 — דיאלקט + אימות + soak.** grep ל-SQLite-only (`PRAGMA`/`sqlite_master`/`AUTOINCREMENT`/`strftime`/`julianday`) והמרה.
להסיר WAL/busy_timeout/checkpoint/`check_same_thread` (PG-irrelevant; כבר מגודר לענף sqlite ב-session.py).
אימות: (a) האפליקציה עולה על PG; (b) הגשר דוחף ונתונים זורמים; (c) **4 צירי UAT** על endpoint-נתונים (quality/recency/cardinality/latency)
עם latency מתחת לסף (LIVE-readiness); (d) **soak-מקביליות**: footprint+woodies+day_type+ingestion במקביל ≥10 דק' → 0 שגיאות, 0 deadlocks.
ב-PG אין כשל "malformed image"; השער הוא **soak-מקביליות נקי**, מחליף את `integrity backend-כבוי=ok` של SQLite.

**Cutover.** לשמור את קובץ ה-SQLite כ-fallback עד ש-PG מוכח על-פני כמה סשנים. **לא** למחוק את `safe_writer`/הכותבים-הגולמיים
עד שה-PG מוכח. לתעד החלטה ב-STATUS_BOARD לאחר כל שער.

## פרומפט CC
`docs/handoff/CC_PROMPT_POSTGRES_MIGRATION_2026-06-03.md` (Phase 0→5, שערים פר-שלב).
