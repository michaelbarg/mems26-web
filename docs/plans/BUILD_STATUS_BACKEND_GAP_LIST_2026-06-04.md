# Build Status — gap-list ל-backend (קלט לפרומפט-מימוש) · 2026-06-04

> מה ה-inspectors/endpoint צריכים לחשוף בנוסף כדי שה-`⧗ ממתין ל-backend` בעמוד `/build`
> יהפכו ל-`● חי`. מסודר P0→P2. כל פריט: **מה לחשוף · מאיפה · לאן בסכמה · קובץ-יעד.**
> מקור: `BUILD_STATUS_COMPONENT_AUDIT.md`. כל שינוי כאן = פרומפט backend נפרד לאישור מייקל.
> תזכורת Rule 1: כשהמקור הקנוני שותק — `present=false`/`None`, לא סינתזה.

## P0 — חוסם הבנה / קריטי ל-LIVE

### P0-1 · שערי-אש גלובליים (`pre_fire_validator` + `risk_checks`)
- **לחשוף:** שורת gate גלובלית אחת עם תוצאת 7 הבדיקות של `pre_fire_validator`
  (side, ordering, R:R≥1.0, confidence, time_stop, entry/stop≠provisional, dedup) +
  תקרות `risk_checks` LIVE (loss $250, 5 trades, 2 contracts, 14:30 cutoff, 2-consec-loss STOP).
- **מאיפה:** `backend/v9/shared/pre_fire_validator.py` · `backend/v9/gateway/risk_checks.py`
  (news placeholder `risk_checks.py:70-74` → לסמן `not_implemented`).
- **לאן בסכמה:** מבנה חדש `global_firewall` ב-`BuildStatusResponse` (או `global_gates` ברמת-תגובה,
  לא פר-מערכת), עם `{key, passed, detail, severity}` לכל בדיקה.
- **קובץ-יעד:** inspector חדש → wire ב-`backend/v9/systems/build_status/aggregator.py:106`.

### P0-2 · שלב TARGETS/STOP (S2 · S4 · S3) — ★ הפריט החוסם את התצוגה האמיתית
> **פרומפט מימוש קיים ומאושר:** `docs/handoff/CC_PROMPT_P0_2_EXPOSE_TARGETS_STOP_2026-06-04.md`.
> השדות כאן **מסונכרנים** איתו verbatim. **exposure-only** — מציגים מה שהמנוע כבר מחשב, באותו
> `compute_stop`/targets; **0 שינוי בערכי stop/target** (שינוי-ערך = strategic-stop נפרד).
- **לחשוף — S2** (`five_min/adaptive_stop.compute_stop` + `targets_table.get_targets`):
  `stop_price` · `risk_1R` · `t1_price`/`t2_price`/`t3_price` · `r_t1` · `time_stop` ·
  `sizing` (full/half/reject) · VSA `variant_tag`.
- **לחשוף — S4** (woodies stop שכבתי: primary 3 ticks / ATR-cap×group / floor):
  `stop_price` · `atr_14_ticks` · `r_t1` · `t1_price`/`t2_price` (ticks לפי תבנית) · `entry_price` ·
  **Day-Type Matrix verdict** (✅/⚠️/❌ לתבנית×יום) — ראה P0-3 (נכלל באותו פרומפט).
- **לחשוף — S3:** `stop=min(low,entry−tick)` · `t1`/`t2` · `time_stop=15` (כשיופעל).
- **שאלת אודיט מרכזית (מה-CC prompt):** האם המנוע מחשב stop/r_t1 **prospective** לתבנית
  armed-שלא-ירתה, או רק ב-fire-time? אם רק ב-fire-time → להוסיף **preview read-only** שקורא לאותו
  `compute_stop`/targets (לא reimplement, לא synth).
- **לאן בסכמה:** בלוק `targets_stop` חדש ב-`SystemBlock` (או stage חדש ב-`components[]`).
- **קובץ-יעד:** `s2_inspector.py` · `woodies_inspector.py` · `footprint_inspector.py`.
- **הערה:** מודל ה-stop של Woodies שונה מ-five_min — לא לאחד.
- **★ זהו ה-unblocker היחיד (מאושר מייקל 2026-06-04):** חשיפת `r_t1`/`risk_1R` מהמנוע ל-inspector
  סוגרת 3 דברים יחד: (א) שלב TARGETS/STOP בתצוגה · (ב) **גייט אמיתי** (`r_t1≥min_r_t1_threshold`
  במקום `confidence≥0.5`) · (ג) stop/r_t1 אמיתי לכל הצרכנים. ברגע שייחשף — מחליפים כל `⧗ ממתין`
  בבדיקת `r_t1≥threshold`, ואותו נתון מזין stop/r_t1 ל-S2/S4/S3 יחד. P1-5 תלוי בו.
- **★ זהו ה-unblocker היחיד (מאושר מייקל 2026-06-04):** חשיפת `r_t1`/1R מהמנוע ל-inspector היא
  מה שחוסם גם את **שלב TARGETS/STOP בתצוגה** וגם את **כל השערים האמיתיים** (S4 `confidence_score`,
  וכל שער עתידי תלוי-r_t1). ברגע שזה ייחשף:
  1. מחליפים את כל ה-`⧗ ממתין` של אותם שערים בבדיקת `r_t1 ≥ min_r_t1_threshold` האמיתית
     (S4: להחליף `woodies_inspector.py:344` `confidence>=0.5` → `r_t1>=threshold`).
  2. אותו נתון בדיוק מזין את ה-stop/r_t1 ל**כל** המערכות (S2/S4/S3) — תצוגת TARGETS/STOP + שערים
     אמיתיים נפתחים יחד מאותה חשיפה.
  לכן P0-2 קודם ל-P1-5; P1-5 תלוי בו.

### P0-3 · Day-Type Matrix verdict (S4) — נכלל באותו פרומפט CC של P0-2
> מסופק ע"י `CC_PROMPT_P0_2_EXPOSE_TARGETS_STOP_2026-06-04.md` (חלק מחשיפת S4). לא פרומפט נפרד.
- **לחשוף:** `matrix_verdict` (✅/⚠️/❌ לכל תבנית×יום) + `entry_hint` + `t1_ref`.
- **מאיפה:** מטריצת ההחלטה של Woodies.
- **לאן בסכמה:** `global_gates`/חדש פר-תבנית ב-S4 (לצד בלוק `targets_stop`).
- **קובץ-יעד:** `woodies_inspector.py`.
- **למה P0:** בלי זה תבנית ❌ ליום (ZLR ב-Neutral) נראית ירוקה כמו ✅ — סיכון פרשנות.

## P1 — שערים אמיתיים וטריות

### P1-1 · חיווט S6 Killzone כשער אמיתי
- **לחשוף:** `is_gate_open` (OPEN/CLOSED), `current_killzone`, `quality`, `volatility`,
  `sizing_modifier`, `block_reason`, `time_in_zone_min`, `time_to_next_zone_min`.
- **מאיפה:** `get_killzone_status()` + `is_gate_open()` (canonical `zones.py` — 11 אזורים).
- **קובץ-יעד:** `killzone_inspector.py` (חדש) → `aggregator.py:106`.
- **הכרעת מייקל (2026-06-04):** קנוני = **`zones.py` (11 אזורים)**; להחליף את ה-RTH הגנרי
  (`_compute_rtb_session`) בשער ה-killzone האמיתי. הגדרת ה-11 "קנוני-לעת-עתה, נתון לעדכון".

### P1-2 · S/R proximity + COT/AMT directional כשערים אמיתיים (S2)
- **לחשוף:** `sr_proximity.check_proximity` כשער עם ערך חי · COT>AMT directional עם הערכים החיים.
- **מאיפה:** כרגע placeholder always-pass.
- **קובץ-יעד:** `s2_inspector.py`.

### P1-3 · anti-patterns + A7 universal (S4)
- **לחשוף:** AP1/4/5/7/8/9 + `reject_reason` · A7 (news ±5m, cool-down 30m, daily loss −$200,
  stop 3–8pt, bridge, EOD>60m).
- **קובץ-יעד:** `woodies_inspector.py`.
- **למה:** תבנית חסומה ב-AP נראית כמו "לא זוהתה".

### P1-4 · freshness ל-3 קובצי Sierra של S2
- **לחשוף:** freshness ל-`cumulative_delta.json` (COT/AMT) · `tpo.json` (POC) · `volume_profile.json` (S/R).
- **קובץ-יעד:** `s2_inspector.py` (3 בדיקות freshness בשלב מקור).

### P1-5 · dispatch (S4) — winning_pattern לפי r_t1 + החלפת פרוקסי ה-confidence
- **לחשוף:** `winning_pattern` + `r_t1` מול `min_r_t1_threshold` + GRAY/YELLOW.
- **קובץ-יעד:** `woodies_inspector.py`.
- **הכרעת מייקל (2026-06-04):** השער הנוכחי `pattern.confidence >= 0.5` (`woodies_inspector.py:344-352`,
  stage `sizing`/`confidence_score`) הוא **פרוקסי** — לא השער האמיתי. הסיבה שלא משתמש באמיתי:
  ה-inspector קורא רק את `confidence` מאובייקט-התבנית; ה-`r_t1` דורש את מרחק-הסטופ החי שמחושב
  בנתיב ה-dispatch ולא נחשף ל-read-path. **פעולה:** עד שה-`r_t1` זמין (תלוי P0-2) — לפלוט את
  שער זה כ-`present=false` (⧗ ממתין), לא כפרוקסי ירוק. כש-`r_t1` זמין → להחליף שורה 344 ב-
  `r_t1 >= min_r_t1_threshold`. (ב-`s2_inspector` אין פרוקסי כזה — האודיט מיתג בטעות "S2".)

## P2 — חיווט צופים והקשר

### P2-1 · חיווט S5 TPO
- **לחשוף:** POC/VAH/VAL, IB (high/low/width/class/locked), `profile_shape`+confidence,
  single_prints, tails, hvn/lvn, naked_pocs, `intent`/`otf_clarity`/migration, `data_quality`.
- **מאיפה:** `v9_tpo_sessions` (CASH row) + `TPOProfile` חי.
- **קובץ-יעד:** `tpo_inspector.py` (חדש) → `aggregator.py:106`.

### P2-2 · pre-open context (S1)
- **לחשוף:** pd_poc/vah/val, on_high/low, gap_size/direction, location_vs_pd, overnight_bias +
  decision matrix (`matrix_cell`/vote_history) + `get_targets()` (T1/T2/T3, time_stop, sizing).
- **מאיפה:** `prev_day.load_previous_day_context` (קיים, לא נקרא ע"י ה-inspector).
- **קובץ-יעד:** `day_type_inspector.py`.

### P2-3 · באנר "מושבת" (S3)
- **לחשוף:** מודעות לדגל `FOOTPRINT_DISABLED`/`S3_MUTE`; לתקן את קריאת `get_state()`→`get_current()`.
- **מאיפה:** `backend/v9/shared/atr.py:101` · skip ב-`footprint_system.py:143-146`.
- **קובץ-יעד:** `footprint_inspector.py`.
- **הכרעת מייקל (2026-06-04):** S3 = **מערכת יורה** (`firing`, לא observer). מושבת כרגע →
  להציג באנר "מושבת" עד פתיחה; כשנפתח, יורה כרגיל. הדגל `FOOTPRINT_DISABLED` חייב להיחשף ל-endpoint.

### P2-4 · טבלאות אפיון מ-endpoint (להסרת drift ב-frontend)
- **לחשוף:** `targets_table.py._TARGETS` + `atr_caps.py` (ATR_MULTIPLIERS, PATTERN_TIME_STOPS)
  כאובייקט בתגובה (או endpoint `/api/v9/build/day-type-tables`).
- **למה:** כרגע ממורקרים ב-`BuildTreeView.tsx` (verbatim) — duplication. חשיפה מה-backend
  מבטלת את סיכון ה-drift ומאפשרת להסיר את הקבועים מה-frontend.
- **קובץ-יעד:** `aggregator.py` / route חדש.

## סדר מומלץ למימוש
P0-1 → P0-2 → P0-3 → P1-1 → P1-2/3/4/5 → P2. כל פריט עם **regression test** (Pre-LIVE discipline),
ואימות 4 צירי UAT (Quality/Recency/Cardinality/Latency) לכל שדה חדש בתגובה.
