# תיקון-DB היסטורי · שכבה-A — בוצע (cowork-night 2026-08-27 23:29–23:45 IL)

**פקודת-עבודה:** `docs/handoff/CC_WORKORDER_DB_REPAIR_2026-08-25.md` (פסיקת-מייקל 25.08).
**מבצע:** cowork-night (חובה-4; claim ‏ce48eeea — cc לא התחיל עד 23:20).
**כלי-האמת היחיד:** `backend/v9/replay/scid_validator.py` (per workorder; ‏rebuild_bar_truth אסור).
**סקריפט:** `scripts/db_repair_layer_a.py` (dry-run כברירת-מחדל; ‏`--execute` עם `lock_timeout='3s'`).

## מה בוצע (בסדר)

1. **snapshot** — `scripts/mems26_snapshot.sh "pre-db-repair"` →
   `~/mems26_snapshots/20260827T203134Z_pre-db-repair/` **+ pg_dump שתי הטבלאות**
   (`db_repair_tables.sql`, ‏3,018,731B, ‏19,727 שורות — כולל כל שורה שנמחקה/עודכנה).
2. **dry-run** (`/tmp/db_repair_dryrun.log`): ‏9 סשני שכבה-A →
   `TOTAL updates=245 deletes=282 inserts=259`; ‏rows_before=5219.
3. **כתיבה** (`/tmp/db_repair_exec.log`): אצווה-פר-סשן, ‏`SET LOCAL lock_timeout='3s'`,
   ‏`pg_isready`+‏health-probe אחרי כל אצווה — **9/9 probes ירוקים**, כל אצווה ‏0.01s.
4. **סכימה (שלב-3 של הפקודה):** ‏`ADD COLUMN symbol DEFAULT 'MES'` + ‏`source_version
   DEFAULT 'live'` (בפועל אין עמודות כאלה בסכימה המקורית — הותאם) → תיוג ‏632 שורות-כפל
   טבלה-רחבה כ-`legacy_dup_<rn>` (נייטרלי-ערכית; ‏CVD של סשני-D1 לא תוקן — ממתין
   לפסיקה) → **`UNIQUE (ts, symbol, source_version)` נוצר**.
5. **שאריות אחרי-RTH:** ‏24 שורות-כפל ‏16:00–16:55 ET על 07-10/07-13 (delta זהה,
   ‏cumulative בעוגן-סותר) — נמחקו rank-2 בלבד, ‏9 התאריכים המתוקנים בלבד; שמורות ב-dump.

## ארבעת-הצירים (Rule 5 — פלט גולמי)

**Quality** — כל 9 הסשנים:
```
2026-07-07..2026-08-13 (9/9): judge=True cov=1.0 conf=0 delta_mm=0 cum_mm=0
```
**Recency** — `max_ts` לא זז ע"י התיקון: ‏exec סיים עם `max_ts_after=2026-08-27 23:30+03
(unchanged=True)`; אחרי push-חי של 23:35 שתי הטבלאות על ‏23:35+03 — הכותב החי ממשיך
לכתוב גם עם האילוץ החדש.
**Cardinality** — ‏78/78 משבצות-RTH פר-סשן (cov=1.0); טבלה: ‏5219→5196 (‏-23 =
‏282del/259ins) →‏5172 אחרי מחיקת 24 השאריות.
**Latency** — ‏health ‏200 ‏1.9ms · ‏decisions ‏200 ‏8.8ms (אחרי הכל).

## 🔴 ממצא-אגב קריטי: מכונת-הכפל החיה **מוחקת היסטוריה בפועל** (לא רק מזהמת)

בין ה-baseline של 25.08 ללילה: ‏**08-14 ו-08-21 איבדו את כל ה-CVD** (‏89+89 שורות → ‏0).
הוכחה שזה לא התיקון: ‏**ה-pg_dump שצולם לפני כל כתיבה שלי כבר מכיל 0 שורות** בשני
התאריכים, ‏08-25 מנופח ל-178 ו-08-18 ל-146. המנגנון: ‏`bar_id="cvd_<chart_idx>"` +
‏`ON CONFLICT(bar_id) DO UPDATE SET ts=…` — רילוד-צ'ארט ממספר-מחדש ומזיז שורות
היסטוריות לתאריכים אחרים (D3a בפעולה). תוצאה חיה: ‏08-14 היה PASS ב-25.08 — היום FAIL
(‏cov 0.0), ‏וה-S2-CVD מורעב הערב (`insufficient coverage: 1/20 rows` בלוג). **האילוץ
החדש בולם חלק מהתנועה** (מעבר ל-ts תפוס = ‏unique-violation), אך תיקון-הכותב עצמו =
‏R0 של ה-RCA — **פסיקת-מייקל נדרשת**, לא בוצע הלילה.

## מאזן 34 הסשנים

baseline ‏25.08: ‏9 PASS · אחרי-התיקון: **17 PASS** = ‏9 שכבה-A מתוקנים + ‏8 שורדים
(‏07-30·07-31·08-05·08-06·08-17·08-18·08-19·08-20). ‏08-14 נפל בין-לבין למכונת-הכפל
(לא היה חלק מהמנדט; ישוב עם R0+תיקון-עוקב). מלא: ‏`/tmp/scid_diff_post_repair.log`
מול ‏`/tmp/scid_diff_run_BASELINE_0825.log`.

**לא-בוצע (מחוץ למנדט):** ‏D1 (12 סשני-היסט; ממתין לפסיקת-ווּדיס) · ‏D4/D2 · ‏R0
(עצירת-הדימום בכותב) · תיקון ‏08-14/08-21 שנשחקו אחרי ה-baseline.
