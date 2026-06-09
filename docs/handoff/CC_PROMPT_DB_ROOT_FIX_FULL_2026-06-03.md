# CC PROMPT — DB Root Fix (FULL, מהשורש) · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אוטונומי **עם שער-דיווח אחרי כל phase** (commit + פלט גולמי; אם phase נכשל — עצור, השאר מצב בטוח, דווח). **אל תעשה `git add -A`.**
**אישור Michael 2026-06-03:** תיקון שורש מלא — **לא אוספים SHADOW היום.** קח את הזמן, עשה נכון.

## רקע — למה זה חזר (audit Cowork 2026-06-03)
תיקון 2/6 טען "ALL writes through safe_writer" — **שגוי בפועל.** עדיין קיימים:
- **~15 אתרי כתיבת-ORM** (`db.add`+`db.commit`) ב-`api/v9/bars.py` (כל ה-ingestion endpoints) + עוד.
- **עשרות `sqlite3.connect` גולמיים** בלי `mode=ro` (חלקם כותבים: `woodies_system.py:141`, `footprint_system.py:84`, `tpo_system.py:88`, `session_boundary/manager.py:66`, ...).
- `get_db()` ORM commits לא מסורלים (המנעול עליהם בוטל — deadlock).
→ ORM ו-raw מתחרים על אותו קובץ. `Rowid out of order` נמשך גם אחרי השבתת tick_reversal (אומת: אותו עמוד 96566/rowid 325707 ב-2 בדיקות 10 דק' זו מזו = השחתה אמיתית על דיסק).
**קרא קודם:** `CC_PROMPT_DB_WRITE_SAFETY_ROOT_FIX_2026-06-02.md` + `CC_PROMPT_DB_TRUE_ROOT_FIX_2026-06-02.md` (ניסיונות קודמים — מה נוסה ולמה לא הספיק).

## 🚫 INVARIANTS
- **אל תחזיר lock ל-`get_db()`/commit** — זה ה-deadlock ב-uvicorn. הפתרון הוא `safe_writer` (חיבור קצר משלו תחת `_write_lock`, לא חוסם event-loop).
- `safe_writer.py` `_write_lock` + `_open_conn` (WAL+busy_timeout) — **אל תשנה את הליבה**, רק השתמש בה.
- אל תיגע: `sc_study/` · B2/B3 · polling · LaunchAgent · bridge routes.
- כל write חייב לעבור `safe_execute`/`safe_executemany`. כל read = `file:...?mode=ro`. **אפס** raw `sqlite3.connect` שכותב.

---

## PHASE 1 — המרת כל כותבי ה-ingestion החמים ל-safe_writer (הליבה)
**יעד:** `api/v9/bars.py` POST endpoints. המר כל `db.add(row)`/`db.commit()` ל-`safe_executemany("INSERT OR REPLACE INTO <t> (...) VALUES (...)", params_list)` — **שמור את כל לוגיקת ה-enrichment/dedup/UPSERT הקיימת.** אתרי-מטרה (אמת שורות בקוד הנוכחי):
- `/5min` (338) · `/volume_profile` (511) · `/imbalance` (587) · `/stacked_imbalance` (653) · **`/cumulative_delta` (732)** · `/woodies` (801) · `/woodies_5min` · `/tpo` (1019) · `/5min_continuous` · `/cvd_continuous` · raw `conn.commit()` (889).
- `/tick_reversal`,`/footprint` כבר מושבתים — השאר.
- שים לב ל-`/cumulative_delta`: יש enrichment שמעדכן `v9_bars_5min.cumulative_delta` (docstring 177-178) — שמור את שני הצעדים, שניהם דרך safe_writer.
- **לכל endpoint: טסט אנטי-טאוטולוגי** שמייבא וקורא ל-route האמיתי, מאמת שהשורה נכתבה + dedup עובד; *"if reverted → RED because ___"*.
- **שער Phase 1:** grep ב-`bars.py` → **0** `db.add`/`db.commit` (פרט ל-disabled) · regression ≥87 green · commit אטומי · `git log` + פלט.

## PHASE 2 — חיסול raw-write connects שנותרו + אכיפת mode=ro לקריאות
1. עבור על כל `sqlite3.connect` ב-`backend/v9/` (ראה audit). לכל אחד: **כותב?** → `safe_execute`. **קורא?** → `file:...?mode=ro`. (כולל `woodies_system.py:141`, `footprint_system.py:84`, `tpo_system.py:88`, `session_boundary/manager.py:66`, routes).
2. **שער Phase 2:** `grep -rn "sqlite3.connect" backend/v9/ | grep -v "mode=ro\|safe_writer\|migrations"` → **0** (או רק קריאות מתועדות מפורש). regression green · commit · פלט.

## PHASE 3 — בידוד ה-journals בתדר-גבוה ל-DB נפרד (defense-in-depth)
**עיקרון:** journals append-only בתדר-גבוה (`cumulative_delta`, `imbalance`, `stacked_imbalance`, `tpo`, + tick/footprint כשייפתחו) → DB נפרד `data/mems26_journals.db` (FIFO-capped), דרך `safe_execute(..., db_path=JOURNAL_DB)`. הטבלאות הקריטיות (`v9_trades`, `v9_day_type_history`, `v9_bars_5min`) נשארות ב-DB הראשי — כך השחתת journal לא נוגעת במסחר.
1. **audit-first:** מפה את כל נתיבי ה-**קריאה** של טבלאות ה-journal (routes/aggregators) לפני העברה. דווח.
2. צור `mems26_journals.db` + הגדר `JOURNAL_DB_PATH`; העבר כתיבה+קריאה של ה-journals לשם. שמור enrichment columns בטבלאות הראשיות (`v9_bars_5min.cumulative_delta`) ב-DB הראשי.
3. FIFO cap (מחק ישן מעבר ל-N) דרך safe_writer.
- **שער Phase 3:** journals כותבים ל-DB הנפרד · קריאות עובדות · `v9_trades`/bars לא הושפעו · regression green · commit · פלט. אם מורכב מדי לפני שנגמר הזמן — **עצור אחרי Phase 2 (הליבה כבר מתקנת את ה-race) ודווח Phase 3 כ-NOT-DONE עם תוכנית.**

## PHASE 4 — rebuild נקי + אימות תחת עומס (השער האמיתי)
1. **עצור backend.** `PRAGMA integrity_check` (זהה את הטבלאות המושחתות). recover/rebuild נקי + `VACUUM`. **לא** מ-`.corrupt.bak`.
2. **load-soak:** הרץ סקריפט שמדמה דחיפות בתדר-גבוה לכל ה-endpoints החמים (cumulative_delta/imbalance/woodies/tpo) במקביל למשך ≥10 דק'.
3. **עצור backend → `integrity_check` שוב = `ok`.** הדבק פלט. זה השער שמוכיח שה-root נסגר (לא band-aid).
- **שער Phase 4:** integrity backend-כבוי `ok` **אחרי** soak תחת עומס. אם לא → ה-root לא נסגר, דווח איזו טבלה עדיין נשברת.

---

## דוח (חלק C) פר phase
טבלת phase · Status · Evidence(command+output) · *"if reverted → RED"* לכל טסט · NOT-DONE · Open.
**מדדי הצלחה כוללים:** (1) `bars.py` 0 ORM-write · (2) 0 raw-write connect · (3) journals מבודדים · (4) integrity=ok אחרי soak. החלטות פתוחות ל-Michael: sc_study v9.4.5 · CLAUDE.md §DB Write-Safety (לעדכן לתאר את הארכיטקטורה החדשה: safe_writer-only + journal isolation, **לא** get_db lock).

**אחרי הדוח — Cowork מאמת בלתי-תלוי (חלק D) לפני סימון DONE. CC אל תעדכן STATUS_BOARD/ROADMAP.**
