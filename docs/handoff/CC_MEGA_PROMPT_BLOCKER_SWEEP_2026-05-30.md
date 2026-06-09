# CC MEGA-PROMPT · Blocker Sweep (ROADMAP §1.5–§1.14) · 2026-05-30

**כותב:** Cowork (גישת DB + קוד read-only · אין API/לוגים/Sierra)
**מבצע:** Claude Code (Mac · API/לוגים/Sierra)
**מאמת G3:** Cursor
**מקור:** `docs/plans/ROADMAP_TO_LIVE.html` §1 · `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` · דוח EOD 29/5

---

## עיקרון-על (חובה — CLAUDE.md)

**הקוד זז מאז שהפריטים נכתבו.** Cowork אימת 2026-05-30 שכמה "באגים" כבר תוקנו
חלקית/מלאה. לכן **כל משימה כאן היא diagnose-first**: הרץ את פקודת ה‑Verify, ורק אם
הבאג עדיין קיים בקוד/DB הנוכחי — תקן. **אל תתקן באג שכבר תוקן** (טעות P27.5d).

- Smallest correct change + regression test לכל תיקון.
- "תוקן" = פקודה + פלט גולמי, לא הצהרה (Rule 5).
- **שינוי לוגיקת-מסחר (gate/סף/טקטיקה) → STOP + אישור Michael.** מסומן במשימות.
- עדכן `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md` אחרי כל משימה (CLAUDE.md §Roadmap auto-update).

מה שכבר אומת ע"י Cowork 30/5 (אל תיגע אלא לאמת):
- `bars_5min` future-ts = **0** (commits `c581f4d`,`b76d5e2`). §1.9 — done.
- frozen-tail: cci_14 משתנה על ברי 5-דק' שונים → לא נראה בנתונים; נותר אימות RTH חי. §1.1.

---

## משימות (no-decision — בצע לפי הסדר)

### T1 · §1.5 — TIME_STOP Woodies יורה מוקדם
**Goal:** TIME_STOP יורה לפי זמן-קיר (spec 90 דק' / Layer 4 day-type limits), לא לפי ספירת pushes.
**Verify-first:**
```bash
# מי האוטוריטה? W-10 (Woodies) או Layer 4?
grep -n "time_stop_minutes" backend/v9/config/dispatcher_config.yaml
# האם _bar_count עדיין עולה לכל push? בדוק את מפתח ה-dedup:
sed -n '202,212p' backend/v9/systems/woodies/woodies_system.py
# מה ts של ברי woodies — ייחודי לכל push (ms)?
python3 -c "import sqlite3;d=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);print(d.execute(\"SELECT ts FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT 5\").fetchall())"
```
**אבחנה ידועה (Cowork):** `woodies_system.py:206` מבצע dedup על `bar.get("ts")` *המדויק*.
אם ה‑ts כולל milliseconds (ייחודי לכל push) — `_bar_count` עדיין מתנפח.
**If confirmed — fix:** רצף את מפתח הספירה ל‑**5-min boundary** (floor), לא ts גולמי:
`_bar_ts_key = floor_to_5min(bar["ts"])`. אם W-10 מושבת ב-YAML (Option B, Michael 28/5) ו-Layer 4
הוא האוטוריטה — ודא ש-Layer 4 (`bar_level_detector._check_time_stop`) סופר ברים סגורים, לא pushes,
ושם תקן את הספירה.
**Tests:** רגרסיה — 40 pushes באותו 5-min bucket → `_bar_count` עולה ב-1; trade עם 18 ברים סגורים → TIME_STOP יורה ב-90 דק', לא ב-32.
**Forbidden:** אל תשנה את ערך ה-90 דק' / day-type limits (אלה spec). תקן רק את הספירה.
**Stop:** אם מסתבר שצריך לשנות limit/gate — עצור ושאל.
**Deliverable:** commit + raw test output ב-`STATUS_BOARD`.

### T2 · §1.6 — T1 hit לא נתפס לעסקאות Woodies
**Goal:** BarLevelDetector רואה ברי Woodies → T1/T2 נרשמים → Smart BE מופעל.
**Verify-first:**
```bash
sed -n '27,60p' backend/v9/services/trade_manager/bar_level_detector.py   # subscribe channel + _parse_ts
# trades וודי עם exit מעל T1 אך t1_hit_ts ריק:
python3 -c "import sqlite3;d=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);print(d.execute(\"SELECT id,firing_system,t1,t1_hit_ts,exit_price FROM v9_trades WHERE firing_system='4' AND t1_hit_ts IS NULL ORDER BY id DESC LIMIT 10\").fetchall())"
```
**אבחנה ידועה (Cowork):** `bar_level_detector.py:38` מנוי **רק** ל-`"5min"`. ברי S4 מגיעים ב-`woodies_5min`.
**If confirmed — fix:** הוסף מנוי גם ל-`"woodies_5min"` (או נתב ברי woodies ל-detector), עם
`_parse_ts` DST-aware (mirror `_chicago_to_utc`). שמור על dedup כדי לא לספור בר פעמיים.
**Tests:** trade S4 עם בר שחוצה T1 ב-`woodies_5min` → `t1_hit_ts` נכתב + Smart BE מופעל.
**Forbidden:** אל תשנה את לוגיקת ה-T1/BE עצמה — רק את מקור הברים.
**Deliverable:** commit + raw output.

### T3 · §1.13 — Status enum sync (`/api/v9/status.day_type`)
**Goal:** ה-status שמדווח ל-UI תואם לשורת ה-DB המסווגת.
**Verify-first:**
```bash
sed -n '90,130p' backend/v9/systems/day_type/consumer.py   # legacy_status mapping
grep -rn "status" backend/v9/api/v9/status*.py | grep -i day_type
# האם /status עדיין מחזיר PENDING בעוד DB מסווג?
python3 -c "import sqlite3;d=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);print(d.execute(\"SELECT date,day_type,lock_state,status,confidence FROM v9_day_type_history ORDER BY date DESC LIMIT 3\").fetchall())"
```
**הערה:** consumer.py כבר ממפה `lock_state→status` (`_map_legacy_status`, ~:196). ייתכן שכבר תוקן —
**אם ה-DB וה-endpoint תואמים, סמן done ואל תיגע.** אם לא — מצא היכן ה-endpoint קורא שדה ישן ותקן.
**Tests:** מצב מסווג ב-DB → `/status.day_type` ≠ PENDING.
**Deliverable:** raw output של ה-endpoint מול ה-DB.

### T4 · §1.11 — פצצות TZ/DST (אימות + סגירה)
**Goal:** לאשר ששתי הפצצות סגורות, ולהוסיף רגרסיית CST.
**Verify-first (Cowork מצא שכבר תוקן — אַמת):**
```bash
sed -n '40,46p' backend/v9/api/v9/woodies_chart_routes.py   # ציפייה: _chicago_to_utc (לא +5*3600)
grep -n "et_today\|date('now')" backend/v9/api/v9/key_levels_routes.py  # ציפייה: et_today(), לא date('now')
```
**If already fixed:** הוסף רגרסיה ב-CST (mock `datetime.now(ZoneInfo('America/Chicago'))` לתאריך דצמבר)
שמוודאת אין double-correction, וסמן §1.11 done. **If a residual hardcode נשאר** — החלף ל-ZoneInfo DST-aware.
**Deliverable:** raw grep + test PASS.

### T5 · §1.12 — triage לכשלי pytest
**Goal:** רשימה מסווגת של כל כשל — regression אמיתי מול fixture-drift.
**Run:**
```bash
cd /Users/michael/Downloads/mems26_web_git
python3 -m pytest tests/v9/ -q 2>&1 | tail -60
```
לכל כשל: file:line · regression אמיתי / drift / legacy-non-trading · האם חוסם trading path.
**Forbidden:** אל "תתקן" טסט ע"י החלשת assertion בלי להבין את השורש.
**Deliverable:** טבלה ב-`docs/reports/PYTEST_TRIAGE_2026-05-30.md`.

### T6 · §1.7 — Footprint dedup (commit + tests · ה-RTH gate = החלטה)
**Goal:** ה-dedup שכבר נכתב יהיה committed + מכוסה בטסטים. **בלי** ה-RTH gate (ראה החלטות).
**Verify-first:**
```bash
git diff --stat backend/v9/systems/footprint/footprint_system.py   # uncommitted?
sed -n '430,500p' backend/v9/systems/footprint/footprint_system.py  # dedup_key + _fired_level_bar
# כמה bursts בחלון האחרון (אותו price+דקה)?
python3 -c "import sqlite3;d=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);print(d.execute(\"SELECT entry_price,substr(entry_ts,1,16) m,COUNT(*) n FROM v9_trades WHERE firing_system='3' AND entry_ts>datetime('now','-2 day') GROUP BY entry_price,m HAVING n>1 ORDER BY n DESC LIMIT 8\").fetchall())"
```
**If confirmed:** הוסף רגרסיה — אותה (price-level + bar_ts + direction) → fire אחד בלבד; commit.
**STOP / החלטת Michael:** הוספת **RTH gate** ל-S3 (חסימת overnight) היא שינוי gate = לוגיקת-מסחר.
**אל תוסיף RTH gate בלי אישור** — תעד כפריט החלטה.
**Deliverable:** commit (dedup+tests) + raw burst-count אחרי.

### T7 · §1.8 — מקור 12 עסקאות @5900 (חקר בלבד — בלי מחיקה)
**Goal:** לזהות מי יוצר entry=5900/stop=5900.25/t1=5910.
**Run:**
```bash
grep -rn "5900\|5910\|5920" backend/v9 --include=*.py | grep -v __pycache__
ls backend/v9/**/fixtures* backend/v9/**/*seed* 2>/dev/null
python3 -c "import sqlite3;d=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);print(d.execute(\"SELECT id,mode,state,is_synthetic,created_at FROM v9_trades WHERE entry_price=5900.0 ORDER BY id\").fetchall())"
```
**STOP / החלטת Michael:** מחיקת השורות דורשת גיבוי + אישור (CLAUDE.md). **אל תמחק.**
דווח את המקור + הצעת תיקון (seed guard / mode tag) להחלטה.
**Deliverable:** `docs/reports/FAKE_5900_SOURCE_2026-05-30.md` + שורת החלטה ב-ROADMAP §1.8.

### T8 · §1.14 — 5min restart gaps + S1 restart resets state (diagnose + propose)
**Goal:** אבחון + הצעת תיקון (לא מימוש מלא לפני אישור heuristics).
**Run:**
```bash
sed -n '1,60p' bridge/v9_streams/bars_5min_stream.py   # האם נשלח רק latest bar?
grep -rn "def reset\|seed\|hydrate" backend/v9/systems/day_type/state_machine.py backend/v9/systems/day_type/day_type_seed.py | grep -v __pycache__
```
הצע: backfill מ-Sierra export ל-5min אחרי restart; replay של 6 ברי פתיחה ל-S1 (day_type_seed)
כדי לשחזר opening_type במקום INDETERMINATE.
**Deliverable:** הצעה ב-`docs/reports/RESTART_RECOVERY_PLAN_2026-05-30.md`. מימוש = אחרי אישור.

---

## דורש החלטת Michael (לא בוצע כאן — נדרש לפני ביצוע)

| # | נושא | ההחלטה הדרושה |
|---|------|----------------|
| §1.2 | Gateway canonical | D-093.Q1 — Legacy / New(`services/trading_gateway/` W11+W14) / Merge. המלצת מחקר: New. |
| §1.4 | Sierra order routing (P5-1) | D-093.Q1 + Q2 (DEMO account) + re-lock (`BuyEntry`+Attached מול `SubmitOCOOrder`). **P5-0 audit / P5-7 / P5-6 כן יכולים לרוץ עכשיו** (ראה `META_PROMPT_PIPELINE5_DLL_SIERRA_DEMO_2026-05-26.md`). |
| §1.7 | RTH gate על S3 | הוספת gate שחוסם footprint overnight = שינוי לוגיקת-מסחר. |
| §1.8 | מחיקת 12 עסקאות @5900 | מחיקת trades דורשת גיבוי + אישור. |
| §1.3 | חיווט pre_fire_validator לנתיב הירי | אם הוא לא נקרא בנתיב מסוים — חיווטו משנה מה נחסם. אַבחֵן קודם (footprint *כן* קורא לו), ואשר לפני הפעלה רוחבית. |

---

## סדר ביצוע מומלץ
T4 (אימות זול) → T3 (אימות זול) → T5 (triage) → T2 (T1 detection) → T1 (TIME_STOP) →
T6 (footprint commit) → T7 (חקר @5900) → T8 (restart). אחרי כל אחת: עדכן ROADMAP+STATUS_BOARD.
