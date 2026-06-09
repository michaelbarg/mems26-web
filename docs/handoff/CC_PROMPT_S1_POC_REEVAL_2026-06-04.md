# CC PROMPT — S1 day-type re-classification דינמי לפי POC/value-area (מ-Sierra) · flag-gated, default OFF · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אישור-כיוון Michael 2026-06-04. ספק מלא: `docs/plans/S1_POC_VALUE_AREA_REEVAL_DESIGN_2026-06-04.md`.
**זה שינוי trading-logic → strategic-stop.** ברירת-מחדל **OFF = ההתנהגות הקיימת בדיוק**; הדלקה ל-live = אישור Michael נפרד + SHADOW soak. החשיפה כאן = לבנות את היכולת מאחורי flag, לא להפעיל אותה.

## רקע (אומת ע"י Cowork, code-level)
S1 הוא OBSERVER (D-096) אבל ה-`day_type` שלו **מגדר את הירי של S2 (Auth Table) ו-S4 (Woodies Matrix)** — לכן הסיווג חייב להישאר נכון לאורך היום. היום ה-re-eval (`detector.check_reeval_triggers` ב-`:503`, נקרא מ-`state_machine._check_reeval:803`) מבוסס **גודל-טווח בלבד**: trigger#2 `extreme_move_3atr` **מת** (`move_30=None` ב-`state_machine.py:783`), trigger `news_event` **מת** (לא מועבר), trigger#3 `failed_extension` ו-#4 `range_exceeded` חיים. **אין שום trigger מבוסס POC**. בנוסף stub מת: `_max_tpo_row_width=0` (`:258`) + `update_max_tpo_row_width()` (`:887`) לא נקרא → "Zohar Width Rule" (`:941`) תמיד עובר.
**מקור הנתונים (הכרעת Michael):** POC/VAH/VAL/IB/migration החיים מגיעים **ישירות מ-Sierra** (Study ID:6 → `tpo.json`), שכבר נחשפים ב-`GET /api/v9/tpo/current` (`tpo_routes.py:421`, `_load_sierra_tpo`, `found=false` כש-stale). S4 כבר צורך משם (`decision_tree.py:114`, `B4PocMigrationQuery`). **S1 יקרא מאותו מקור — אפס חישוב/סינתזה ב-S1.**

## ⛔ risk surface — מה אסור
- אל תיגע ב-`sc_study`/Sierra/DLL · אל תשנה ערכי-risk/stop/target · אל תיגע ב-S2/S4 firing.
- **POC רק מ-Sierra** (`/api/v9/tpo/current`); `found=false`/stale → **לא לסווג-מחדש, לא לסנתז** (Rule 1). אסור לגזור POC מברים ב-S1.
- **flag default OFF** → כשכבוי, `_check_reeval`/`_stage_b6` חייבים להחזיר תוצאה **זהה-bit** למצב טרום-השינוי.
- **לא לכפול** את `B4PocMigrationQuery` — אם הלוגיקה זהה, לחלץ helper משותף או לצרוך אותו (single-source).

## Phase 1 — אודיט (diagnose-first, הדבק)
1. הדבק `_check_reeval` (`:782`) + `check_reeval_triggers` (`detector.py:503-538`) + מצב 4 ה-triggers.
2. הדבק `curl -s localhost:8000/api/v9/tpo/current | jq '{found, poc, vah, val, profile_shape, poc_migration, ib_high, ib_low, ib_class, ib_locked}'` — הוכח אילו שדות זמינים חיים ומה ה-shape של `poc_migration` (direction/magnitude/stuck). אם השרת כבוי — fixture שמדגים.
3. הדבק `_stage_b6` (`:622`) + `_rescore_from_behavior` (`:662`) — נקודות-החיבור לסיווג-מחדש. ואת `_max_tpo_row_width`/`update_max_tpo_row_width`/Zohar Width Rule (`:258,887,941`).
4. בדוק את `B4PocMigrationQuery` — האם הלוגיקה ניתנת-לשיתוף.

## Phase 2 — צריכת Sierra-TPO (read-only, Rule 1)
- מתודה ב-state machine שמושכת `/api/v9/tpo/current` (כמו S4) ומחזירה `{found, poc, vah, val, profile_shape, poc_migration, ib_*}`.
- `found=false`/stale → ה-triggers החדשים **לא מופעלים** (סימון `pd_context_status=degraded`), נשארים על הסיווג.

## Phase 3 — triggers חדשים (מאחורי flag) + החייאת המתים
ב-`check_reeval_triggers`/`_check_reeval` הוסף קלטי-POC + ענפים (פעילים רק כשה-flag ON):
- **`poc_migration` כיווני+סדרתי מחוץ ל-IB** → re-eval לכיוון `Trend_Normal` (`Trend_DD` אם עוצמה/מרחק גדולים).
- **POC תקוע/רוטציה בתוך VA** (`stuck_minutes` גבוה, migration≈0) → `Neutral_Center`/`Nontrend`.
- **דחיית value-area** (פריצת VAH/VAL + חזרה) → מתחבר ל-`failed_extension` הקיים → `Variation`/`Neutral`.
- **stopgap (זול, מתחבר):** החייה `move_30` עם `deque(maxlen=6)` (`move_30=abs(close-closes[-6])`) + חווט `news_event`.
- **החייה `_max_tpo_row_width`:** חווט `update_max_tpo_row_width()` מ-`profile_shape`/TPO החי → Zohar Width Rule פעיל.
ספי-הנדידה (magnitude/stuck) — **YAML-tunable** (`config/s1_reeval.yaml`), עם default שמשמר התנהגות נוכחית כש-flag OFF.

## Phase 4 — rescore מבוסס-POC
ב-`_rescore_from_behavior`/`_stage_b6`: מועמד-סיווג מ-`profile_shape`+`poc_migration` (רק כש-flag ON), בתוך מנגנון ה-vote הקיים (סף `0.15` נשמר).

## Phase 5 — flag + config
- `S1_POC_REEVAL` flag (env/`s1_reeval.yaml`), **default OFF**. כבוי → 0 שינוי. דלוק → ה-triggers/rescore/Width פעילים.
- ספים ב-`s1_reeval.yaml` (migration_min, stuck_min_minutes, width_max_letters), נטענים דרך `config_loader` (fallback בטוח, No silent failure).

## Acceptance (✓/✗ + raw)
- [ ] Phase-1 audit מודבק (triggers + `tpo/current` payload + rescore + Width stub).
- [ ] S1 קורא Sierra-TPO; `found=false`→0 re-eval (raw).
- [ ] **טסט default-OFF = 0 שינוי:** עם flag OFF, `_check_reeval`/`_stage_b6` זהים למצב טרום-השינוי על אותו קלט (raw). *if reverted→baseline.*
- [ ] **טסט אנטי-טאוטולוגי (B1) flag ON:** מזין נתיב-ייצור (state machine האמיתי) עם `poc_migration` כיווני שמעבר לסף → `day_type` משתנה ל-Trend; *"if reverted (trigger מוסר) → RED because הסיווג נשאר נעול."* assert על `state.day_type` האמיתי, לא על משתנה-ביניים.
- [ ] טסט: POC תקוע → Neutral; value-area rejection → Variation (raw).
- [ ] `_max_tpo_row_width` מחווט (Zohar Width Rule יורד על profile רחב) — טסט (raw).
- [ ] regression מלא ירוק · `git log -1` · **NOT-DONE/DEVIATIONS** (גם "none").

## Invariants
trading-logic — **flag default OFF = 0 שינוי**, הדלקה=strategic-stop+אישור Michael+SHADOW soak · S1 נשאר OBSERVER (D-096) · POC רק מ-Sierra, חסר→no-reeval (Rule 1, לא סינתזה) · single-source (לא לכפול B4PocMigration) · אל תיגע sc_study/risk-values/S2-S4-firing · localhost-PG · No silent failures · Cowork מאמת בלתי-תלוי (litmus revert→RED + flag-OFF זהה + found=false no-op).
