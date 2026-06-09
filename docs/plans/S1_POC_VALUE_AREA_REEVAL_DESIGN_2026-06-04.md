# עיצוב · S1 day-type re-classification דינמי לפי POC / value-area · 2026-06-04

**סוג:** design-research, **read-only — לא מומש קוד.** · לאישור Michael לפני מימוש.
**מטרה (הגדרת Michael):** סוג-היום צריך להיות **דינמי** — מסווגים אחרי החצי-שעה הראשונה (IB) ו**מעדכנים לפי התנהגות השוק מול ה-IB ומול קווי ה-POC** (נדידת POC / קבלה-דחייה של value-area), לא רק לפי גודל-טווח.
**מקורות שנקראו:** `day_type/state_machine.py`, `day_type/detector.py` (`check_reeval_triggers`), `tpo/tpo_system.py`, `woodies/decision_tree.py` + `stages/*`, `api/v9/tpo_routes.py`, `BUILD_STATUS_BACKEND_GAP_LIST` (P2-1).

> **עקרון-על (CLAUDE.md Rule 1):** POC/VAH/VAL חיים מגיעים **רק** מ-S5/TPO (source-of-truth). אם S5 שותק (`found=false`) → **לא לסווג-מחדש ולא לסנתז** day_type ממחיר. "חסר" = להישאר על הסיווג הקיים, לא לנחש.

---

## 1. אבחון — מה קיים היום (diagnose-first)

### 1.1 ה-re-eval של S1 — מצב נוכחי (`detector.py:503` + `state_machine.py:803`)
4 triggers; **2 מתים**:

| # | trigger | בודק | מצב |
|---|---|---|---|
| 1 | `news_event` (FOMC/NFP) | מועבר ל-`check_reeval_triggers` | ⛔ **מת** — לא מועבר בקריאה (default False) |
| 2 | `extreme_move_3atr` | `move_in_30min > 3×ATR` | ⛔ **מת** — `move_30=None` (`state_machine.py:783`) |
| 3 | `failed_extension_post_lock` | failed extension אחרי lock | ✅ חי |
| 4 | `range_exceeded_for_type` | `range/ATR` מעל סף-פר-יום | ✅ חי |

**מסקנה:** ה-re-eval כיום **מבוסס גודל-טווח בלבד** (range/ATR + failed-extension). **אין שום trigger מבוסס POC / value-area** — בדיוק הפער שזיהית.

### 1.2 מנגנון הסיווג-מחדש שכבר קיים ב-S1 (ADAPT — לא לבנות חדש)
- **`_stage_b6` (`state_machine.py:622`)** — vote-update: `_rescore_from_behavior` מציע day_type חלופי; מחליף אם `conf_diff > 0.15`. שומר `vote_history`.
- **`_check_reeval` (`:782`)** — אחרי lock: אם trigger יורה → `lock_state=PENDING`, חוזר ל-stage B2 לסיווג-מחדש.
- **המטריצה הראשונית** — `opening_type × ib_width → day_type` (`:567`), עם `prev_vah/prev_val` (אתמול) ל-NeuE/NeuC.
- **stub מת רלוונטי:** `_max_tpo_row_width=0` (`:258`) לעולם לא נכתב; `update_max_tpo_row_width()` (`:887`) לעולם לא נקרא → **"Zohar Width Rule"** (`:941`) שאמור להוריד TREND_NORMAL על פרופיל רחב **תמיד עובר** (0). כלומר כבר תוכנן נתיב-TPO ל-S1 — ומת.

### 1.3 S5/TPO — **כבר מחשב את כל מה שצריך, חי** (`tpo_system.py`)
| שדה | שורה | מה |
|---|---|---|
| `poc`, `vah`, `val` | 59-61 | POC + גבולות value-area |
| **`poc_migration`** | 70 (`_update_poc_migration:230-254`) | **כיוון · עוצמה · דקות-תקיעה** ← הסיגנל המרכזי שאתה רוצה |
| `ib_high/low/width/class/locked` | 64-69 | IB (מקור: Sierra Study ID:6) |
| `profile_shape` | 62 | D / b / P / neutral |
| `hvn/lvn`, `volume_cluster`, `ufl_ufh`, `otf_clarity` | 71-73,214-215 | צמתי-נפח, unfair high/low, intent |

נוחת ב-`v9_tpo_sessions` (DB) + `current_state` (זיכרון) + נחשף ב-**`GET /api/v9/tpo/current`** (`tpo_routes.py:421` — קורא Sierra `tpo.json`, fallback ל-DB, `max_age` 30ש', `found=false` כשבייש).

### 1.4 התקדים — S4 כבר צורך את זה (single-source, אל תכפיל)
S4/Woodies כבר מושך POC/VAH/VAL/migration/OTF דרך **`/api/v9/tpo/current`** (`decision_tree.py:114`), כולל **`B4PocMigrationQuery`** (לוגיקת נדידת-POC קיימת) ו-`A4PocSufferingQuery`. **המשמעות:** יש דפוס-צריכה מוכח + לוגיקת-נדידה קיימת — S1 צריך **לעשות ADAPT לאותו מקור**, לא להמציא.

---

## 2. העיצוב המוצע — POC/value-area כ-trigger לסיווג-מחדש

### 2.1 נתיב-הנתונים (החלטת ארכיטקטורה)
**מומלץ: S1 צורך את `GET /api/v9/tpo/current`** (אותו endpoint כמו S4) — single-source, עמיד (fallback מובנה), עקבי. חלופה (in-process direct call ל-`tpo_system.get_current()`) מהירה יותר אבל יוצרת נתיב-צריכה שני לאותו דאטה → סיכון-drift מול S4. **Rule 1:** `found=false`/stale → אין re-eval (נשארים על הסיווג), לא סינתזה.

### 2.2 ה-triggers החדשים (מהדאטה הקיימת של S5)
לחווט ל-`_check_reeval` (ADAPT — להוסיף קלט POC לצד range/failed-extension):

| סיגנל (מ-S5) | התנהגות-שוק | סיווג-מחדש מוצע |
|---|---|---|
| **`poc_migration` כיווני + סדרתי** (POC נודד עקבית מחוץ ל-IB) | יום מגמתי | → `Trend_Normal` (ו-`Trend_DD` אם העוצמה/המרחק גדולים) |
| **POC תקוע/רוטציה בתוך value-area** (`stuck_minutes` גבוה, migration≈0) | יום ניטרלי/דשדוש | → `Neutral_Center` / `Nontrend` |
| **קבלת value-area** (פריצת VAH/VAL + acceptance, לא חזרה) | המשך מגמתי | אישור trend / ביטול `failed_extension` |
| **דחיית value-area** (פריצה + חזרה לתוך VA) | failed extension | → `Variation` / `Neutral` (מתחבר ל-trigger#3 הקיים) |
| **שינוי `profile_shape` אמצע-סשן** (D→b/P) | מבנה השתנה | טריגר ל-rescore (`_stage_b6`) |
| **`_max_tpo_row_width` רחב** (להחיות את ה-stub) | פרופיל רחב | הורדת `Trend_Normal` (Zohar Width Rule `:941`) |

**עיגון בטקסונומיה:** ה-playbooks כבר מדברים POC ("fade extremes around POC", "rotation around POC") → רוטציה-סביב-POC = ניטרלי; נדידת-POC-מחוץ-ל-IB = מגמתי. כלומר המיפוי עקבי עם שפת-המערכת הקיימת.

### 2.3 איפה זה מתחבר (ADAPT, smallest correct change)
1. **`_check_reeval`** — להעביר את שדות ה-POC (migration/acceptance) ל-`check_reeval_triggers`, ולהוסיף שם 1-2 triggers חדשים (`poc_migration_trend`, `value_area_rejection`). (במקביל: לחווט `news_event` ולהחיות `move_30` כ-stopgap — זול, מתחבר.)
2. **`_rescore_from_behavior` / `_stage_b6`** — להוסיף מועמד-סיווג מבוסס-POC (profile_shape + migration) למנגנון ה-vote הקיים (סף 0.15 נשמר).
3. **`update_max_tpo_row_width()`** — לחווט קריאה חיה מ-S5 (להחיות את ה-Zohar Width Rule המת).

### 2.4 source-of-truth ו-degradation
- כל שדה-POC נצרך **רק** מ-S5; `found=false` → ה-trigger לא מופעל (נשארים על הסיווג, `pd_context_status=degraded`), **לא** לגזור POC ממחיר/ברים ב-S1 (אנטי-דפוס Rule 1).
- TZ מפורש על חלון-ה-IB/RTH (Rule 4).

---

## 3. gap-list למימוש (קלט לפרומפט עתידי — לא עכשיו)

**G1 — נתיב S5→S1.** לצרוך `/api/v9/tpo/current` ב-state machine (או in-process), עם schema קריאה ל-`poc/vah/val/poc_migration/profile_shape/found`. עמידה ב-Rule 1 (found=false→no-op).
**G2 — triggers ב-`check_reeval_triggers`.** להוסיף `poc_migration_trend` + `value_area_rejection`/`acceptance` כקלטים+ענפים; להחיות `news_event`+`move_30` (stopgap). regression-test לכל trigger (litmus revert→RED).
**G3 — rescore מבוסס-POC.** מועמד-סיווג מ-profile_shape+migration ל-`_rescore_from_behavior`; שמירת סף-0.15.
**G4 — להחיות `_max_tpo_row_width`.** לחווט `update_max_tpo_row_width()` מ-S5 → Zohar Width Rule פעיל.
**G5 — `tpo_inspector.py` (P2-1).** לחשוף POC/VAH/VAL/IB/migration/intent ל-`/build` (`aggregator.py:106`) — כדי שנראה את הסיווג-מחדש החי ב-Build-Status. (מתחבר ל-build-status drift.)
**G6 — אימות consistency.** ה-day_type שמוצג == מה ש-S2/S4 גידרו עליו בפועל (כי S1 מגדר את שניהם).

---

## 4. סיכון ו-invariants
- **trading-logic — strategic-stop.** משנה את לוגיקת-הסיווג שמגדרת את **כל** הירי של S2/S4. flag-gated · ברירת-מחדל = ההתנהגות הקיימת · **SHADOW soak לפני DEMO/LIVE**.
- S1 נשאר **OBSERVER** (D-096) — זה משנה רק את ה-classification, לא מחזיר Signal של S1.
- source-of-truth: POC רק מ-S5; חסר=לא-re-eval, לא סינתזה. אל תיגע sc_study/risk-VALUES.
- **לא לכפול את `B4PocMigrationQuery`** — אם הלוגיקה זהה, לחלץ ל-helper משותף או לצרוך אותו (single-source).
- **Michael מאשר את העיצוב לפני מימוש.** הפער הפתוח להכרעה: נתיב-נתונים (HTTP מול in-process) + סף-העוצמה של "נדידה מובהקת" (כיול — כנראה מ-soak).
