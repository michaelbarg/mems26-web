# CC MEGA-PROMPT · Blocker Sweep ROUND 2 (commit + tests + fixture drift) · 2026-05-30

**כותב:** Cowork · **מבצע:** Claude Code (Mac · venv · git) · **מאמת:** Cursor G3
**הקשר:** סבב 1 (`CC_MEGA_PROMPT_BLOCKER_SWEEP_2026-05-30.md`) הוטמע אך **לא קומיט** (נעילת git).
Cowork אימת diffs + אבחן את "רגרסיית" ה-IB-lock כ-**fixture drift**.

## עיקרון-על
Diagnose-first · smallest correct change · regression test · "תוקן" = פקודה+פלט.
**אסור:** לשנות לוגיקת state-machine של נעילת IB · RTH gate על S3 · מחיקת/סימון @5900 ·
Pipeline 5. אלה החלטות Michael / מסכנים source-of-truth — דלג עליהם.

---

### R2-1 · COMMIT working-tree (קריטי — שום דבר לא committed)
פתור את נעילת ה-git (`rm -f .git/index.lock` אם אין תהליך git חי) וקמיט בקבוצות הגיוניות:
- `woodies_system.py` (TIME_STOP 5-min floor)
- `bar_level_detector.py` (subscribe woodies_5min + dedup)
- `footprint_system.py` (dedup level+dir+bar_ts)
- `db/models/trades.py` + `trades.py` (is_synthetic ORM + API filter)
- `tests/v9/systems/test_day_type_ib_live.py` (**Cowork fixture fix — אומת**)
לכל קומיט: הודעת commit עם finding+fix. **אל תקמיט** `STATUS_BOARD.md`/`ROADMAP_TO_LIVE.html` עם הקוד (docs נפרד).

### R2-2 · Regression tests לתיקוני סבב 1
- TIME_STOP: 40 pushes באותו 5-min bucket → `_bar_count` עולה ב-1; 18 ברים סגורים → fire ב-90 דק'.
- T1 detection: trade S4 + בר ב-`woodies_5min` שחוצה T1 → `t1_hit_ts` נכתב + Smart BE.
- Footprint dedup: אותו (level+dir+bar_ts) → fire אחד.
הרץ והדבק פלט גולמי.

### R2-3 · ISO-ts robustness ב-TIME_STOP (השלמת R1-T1)
ב-`woodies_system.py:206` ה-fallback ל-ts בפורמט ISO מרצף ל**דקה** ולא ל-5-דק'.
תקן: פרסר ISO→epoch ואז floor `%300` (או floor ל-bucket 5-דק' מתוך המחרוזת). regression עם ts ISO.

### R2-4 · Fixture drift — `test_day_type.py` (group 9) · **אבחון Cowork מצורף**
**אל תיגע ב-state_machine.** A4 (`state_machine.py:495-502`) בכוונה מסרב לנעול בלי Sierra IB
(source-of-truth, 28/5). הטסט `make_bar` (`tests/v9/systems/test_day_type/test_day_type.py:26`)
מזין high/low בלי `ib_high/ib_low`. **תיקון:** הוסף ל-`make_bar`:
```python
defaults.setdefault("ib_high", defaults["high"])
defaults.setdefault("ib_low",  defaults["low"])
```
(Cowork אימת אמפירית: בלי Sierra IB→A3 לא נעל · עם→B2 נעל.) הרץ `pytest tests/v9/systems/test_day_type/ -q`
והדבק פלט. אם טסט אחר ציפה ל"לא-נעל" — דווח, אל תכפה.

### R2-5 · api/ conftest blocker
`tests/v9/api/conftest.py:3` מגדיר `pytest_plugins` ב-conftest לא-top-level → חוסם את כל `tests/v9/api/`.
העבר את ההצהרה ל-conftest ברמה העליונה (`tests/conftest.py`). הרץ `pytest tests/v9/api/ -q`.

### R2-6 · TPO snapshotter TZ (group 5 · 7 fails)
`test_tpo_history_snapshotter.py`: `slot_start_ts_str()` מחזיר UTC במקום ET. אבחן את הפונקציה,
תקן להמרת ET DST-aware (ZoneInfo America/New_York), regression. הדבק פלט.

### R2-7 · CST regression ל-TZ/DST (סגירת §1.11)
§1.11 אומת סגור (`_chicago_to_utc`, `et_today()`). הוסף טסט שרץ עם תאריך דצמבר (CST) ומוודא
אין double-correction ב-`woodies_chart_routes` + `key_levels` מחזיר את היום ה-ET הנכון.

### R2-8 · Gateway DB path + test isolation (שורש @5900 — אבחון Cowork)
**שורש (אומת Cowork 30/5, `FAKE_5900_SOURCE_2026-05-30.md`):** `gateway/trading_gateway.py:25`
מקודד `DB_PATH = ".../mems26_local.db"` ועוקף `DATABASE_URL` → טסטי gateway (entry=5900)
רושמים SHADOW ל-DB החי (12 שורות 29/5 + 3 חדשות 844-846 מ-30/5 14:19).
**תיקון (אין שינוי לוגיקת-מסחר):**
1. החלף את `DB_PATH` הקשיח בקריאה מ-`db/session.py` (DATABASE_URL/db_path).
2. conftest fixture שמכוון `DATABASE_URL`/DB_PATH של ה-Gateway ל-temp DB בטסטים.
3. regression: הרצת טסטי gateway → `COUNT(*) WHERE entry_price=5900 AND is_synthetic=0` לא גדל.
**⚠️ סטטוס 30/5 (Cowork):** חלק 1 בוצע (`65f00e5` DB_PATH→DATABASE_URL) אבל **הזיהום חזר —
15 שורות חדשות 847-861 is_synthetic=0**. הסיבה: `DATABASE_URL` ברירת-מחדל = ה-DB החי
(`db/session.py:14`), אז הטסטים עדיין כותבים אליו. **חלק 1 לא מספיק — חובה חלק 2:**
1. **בידוד DB לטסטים (החסר):** ב-`tests/conftest.py` (top-level) fixture שמכוון `DATABASE_URL`
   ל-temp file / `:memory:` לפני שה-gateway/TradeManager נטענים, כך שטסטים לעולם לא נוגעים
   ב-`mems26_local.db`. ודא שגם `gateway` קורא את אותו session (לא נתיב נפרד).
2. **סימון (Michael אישר):** גבה (`cp data/mems26_local.db data/mems26_local.db.bak-$(date +%F)`)
   ואז `UPDATE v9_trades SET is_synthetic=1 WHERE id IN (844,845,846,847,848,849,850,851,852,853,854,855,856,857,858,859,860,861);`
3. **אמת:** הרץ את טסטי ה-gateway פעמיים → `SELECT COUNT(*) FROM v9_trades WHERE entry_price=5900 AND is_synthetic=0;`
   נשאר **0** (לא גדל). זו ההוכחה שהבידוד עובד.

### R2-9 · Restart recovery (✅ Michael-approved 30/5 · §1.15)
מקור: `RESTART_RECOVERY_PLAN_2026-05-30.md` (v2). עיקרון: load-from-source, לא ניחוש.
1. **Backfill 5min (חובה):** ב-startup `MAX(ts)` מ-`v9_bars_5min`; דחיפה ראשונה שולחת
   את כל הברים שאחרי ה-ts (`_first_push` flag ב-`bars_5min_stream.py`), ואז latest-only.
2. **S1 load-from-DB:** ב-`day_type_seed.py` — במקום לכפות `opening_type=INDETERMINATE`
   (שורה ~111), טען `opening_type`/`day_type`/`lock_state`/`confidence` מהשורה של היום
   ב-`v9_day_type_history` אם `date==et_today()` ו-`status!='ROLLED_OVER'`. IB/טווח נשארים
   מ-Sierra (`maybe_seed_ib_from_tpo`). רק אם אין שורה → INDETERMINATE אמיתי.
**אסור (Michael):** אין replay של ברי פתיחה ואין כלל-13:00 (בוטלו — over-engineering).
**אסור:** לשנות את לוגיקת A4 (source-of-truth). **Tests:** seed אחרי שמירת OPEN_DRIVE →
`opening_type=='OPEN_DRIVE'`; restart מול backfill → אין פערי 5min; אין שורה → INDETERMINATE.

---

## נשאר להחלטת Michael (לא בסבב הזה)
@5900 (סמן/מחק) · RTH gate על S3 · Gateway canonical (D-093.Q1) · pre_fire wiring · Pipeline 5 (מוקפא).

## אחרי כל משימה
עדכן `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md` (finding+fix+פלט אימות). החזר טבלה:
משימה | אומת? | מה תוקן/קומיט | pytest output.
