פעל לפי docs/handoff/CC_HANDOFF_CONTRACT.md

# CC PROMPT — S1 Day-Type Pipeline Audit & Fix (2026-06-02)

**מטרה אחת:** לתקן את צינור S1 (Day-Type classifier) כך שהוא (a) מסווג לפי הספק, (b) הפלטים שלו מגיעים נכון ל-Build Status. כל phase אטומי. **אסור** לגעת ב-`sc_study/`, bridge, market-data routes (CLAUDE.md §7a anti-regression). **אסור** להפעיל שירותים במהלך פיתוח (CLAUDE.md § Service Bring-Up).

**Risk surface (DO NOT TOUCH without strategic-stop):** decision matrix priors, lock thresholds (`min_session_min_for_lock`, `confidence_threshold`), Auth-Table gating. שינוי trading-logic = flag-gated + אישור Michael (Contract B5).

**מצב נוכחי (מאומת ע"י Cowork, 2026-06-02, raw evidence per gap below).** הצינור Sierra→bridge→DB→backend חי וכותב, אבל מספר input-ים מתים והופכים את הסיווג לא-תקין. הסיווג היחיד שנכתב ל-`v9_day_type_history` הוא `Normal / LOCKED_LOW_CONF / p=0.68` חוזר — חשד חזק שהוא תוצר של inputs מתים, לא של סיווג אמיתי.

---

## Phase 1 — `bar.atr` הוא None לאורך כל הצינור (degraded B3/B5/re-eval)

**Evidence (file:line + raw):**
- `backend/main.py:230-244` — ה-`BarInput` שנבנה ב-`_day_type_on_bar` **לא מעביר `atr=`**. השדה `BarInput.atr` (schemas.py:128) נשאר default `None`.
- `data/mems26_local.db` — `PRAGMA table_info(v9_bars_5min)` מחזיר: `['id','ts','symbol','open','high','low','close','volume','poc_vol','vah','val','cumulative_delta','created_at','is_synthetic']` — **אין עמודת `atr`**. כלומר גם אם היו קוראים מה-bar, אין מה לקרוא.
- תוצאה: `state_machine._stage_b3:589` `if bar.atr and bar.atr>0` → תמיד False → `range_ratio=1.0` קבוע. `_stage_b5:617` `atr = ... else current_range` → degenerate (range/range). `_check_reeval:794` `if atr and atr>0` → תמיד False.

**Smallest correct fix:** ב-`_day_type_on_bar`, לפני בניית `BarInput`, לחשב ATR-14 מ-DB ולהעביר `atr=`. השתמש ב-`backend/v9/shared/atr.atr_daily(...)` (source-of-truth מ-DB bars, מחזיר None < 14 bars). העבר `atr_daily` value ל-`BarInput(atr=...)`. אם None — להשאיר None (Rule 1: honest failure, אל תסנתז). **אל תוסיף עמודת atr ל-v9_bars_5min** (זה bar synthesis); חשב on-read.

**Anti-tautological test:** `backend/v9/tests/test_s1_atr_wired.py` — לייבא ולהריץ את ה-path האמיתי שבונה `BarInput` ב-`_day_type_on_bar` (extract ל-helper טהור אם צריך, או לבדוק ש-`atr_daily` נקרא). assert: בהינתן ≥14 daily bars מ-fixture DB, ה-`BarInput.atr` שמגיע ל-`process_bar` הוא float>0, ואז `_stage_b5` מחזיר `range_category` שתלוי ב-ATR (לא ב-degenerate range/range).
*"if reverted → RED because `bar.atr` חוזר None ו-range_ratio נשאר 1.0 קבוע."*

---

## Phase 2 — `S1_IB_WIDTH_ATR` flag dead-wired + input שגוי (5-min range מתחזה ל-daily ATR)

**Evidence:**
- `backend/v9/shared/atr.py:87` — `S1_IB_WIDTH_ATR` נקרא ל-module constant.
- `grep S1_IB_WIDTH_ATR backend/**/*.py` — מופיע ב-import (detector.py:36) וב-comment בלבד. **`classify_ib_width_atr` (detector.py:56-81) לעולם לא בודק את הדגל** — הוא תמיד מחשב ATR-relative. הדגל מת (defined, never gates consumer) — בדיוק ה-anti-pattern של feedback_full_decision_pipeline_wiring.
- `state_machine.py:317-324` — `_last_atr_daily` מחושב מ-`bar.high-bar.low` של בארים של **5 דקות** (`self._bar_ranges`), אבל מועבר ל-`classify_ib_width_atr(atr_daily=_atr_daily)` (state_machine.py:534-540). כלומר "atr_daily" הוא ממוצע טווח 5-דקתי (~כמה נקודות), לא ATR יומי. `ratio = ib_range_pt / atr` (detector.py:73) יוצא ענק → כמעט תמיד `EXTREME`.

**Smallest correct fix (flag-gated, Michael approval לפני live):**
1. החלט עם Michael: האם S1_IB_WIDTH_ATR אמור לשלוט על בחירת מצב נקודות-מוחלט מול ATR-יחסי? אם כן — `classify_ib_width_atr` חייב לבדוק את הדגל ולחזור ל-thresholds מוחלטים (`narrow_max/medium_max` pt) כשהדגל OFF. אם הוחלט "תמיד ATR-relative" (כפי שה-docstring טוען, Michael 2026-06-01) — **למחוק את הדגל** מ-atr.py ומה-imports (no dead flags).
2. לתקן את ה-input: להעביר ATR **יומי** אמיתי (`atr_daily` מ-DB daily aggregates) ל-`classify_ib_width_atr`, לא ממוצע 5-דקתי. לשנות שם המשתנה `_last_atr_daily`→`_last_atr_5min_avg` או להחליף את המקור.

**Anti-tautological test:** `test_s1_ib_width_atr.py` — לקרוא ל-`classify_ib_width_atr` עם `ib_range_pt=20, atr_daily=40` (ATR יומי ריאלי) → assert `MEDIUM` (ratio 0.5), ולא `EXTREME`. בנוסף, אם הדגל נשמר: assert שכש-`S1_IB_WIDTH_ATR=OFF` הפונקציה מחזירה מצב לפי thresholds מוחלטים.
*"if reverted → RED because input של 5-min avg מחזיר ratio ענק ו-EXTREME על IB נורמלי."*

---

## Phase 3 — `S1_DAYTYPE_STAGING` C-period re-eval helper מוגדר אך אינו נקרא (dead-wired)

**Evidence:**
- `detector.py:100-119` `check_c_period_reeval(...)` מוגדר ו-flag-gated.
- `grep check_c_period_reeval backend/**/*.py` — **אפס callers** מחוץ להגדרה. ה-state machine לא קורא לו. helper מת.
- `cap_confidence_staged` (detector.py:84-97) נקרא (state_machine.py:765) אבל cap רק `session_min < 60`; אחרי IB lock לא משפיע — חצי מהפיצ'ר מחובר, חצי מת.

**Smallest correct fix (flag-gated):** או לחבר את `check_c_period_reeval` דרך ה-consumer האמיתי (לקרוא לו ב-`_stage_c1`/`_check_reeval` עם `retrace_depth` אמיתי), או — אם הוחלט שלא בשימוש — למחוק אותו ולתעד ב-DECISION_LEDGER. אל תשאיר helper מת.

**Anti-tautological test:** `test_s1_staging_wired.py` — עם `S1_DAYTYPE_STAGING=1`, להריץ `process_bar` ברצף שמייצר retrace עמוק ב-C-period, ולאמת שהמכונה החזירה verdict `RE_DIAGNOSE`/HOLD דרך הנתיב האמיתי (לא ע"י קריאה ישירה ל-helper).
*"if reverted → RED because אם ה-helper לא מחובר, retrace עמוק לא משנה דבר."*

---

## Phase 4 — C3 hard-lock: re-eval triggers מתים (סותר ההחלטה "day-type continuous, not hard lock")

**Evidence:**
- `state_machine.py:783` `move_30 = None  # Would need bar history` — קבוע. Trigger "extreme_move_3atr" (detector.py:526) לעולם לא מופעל.
- `_check_reeval:794` `if atr and atr>0` → `atr=bar.atr` תמיד None (Phase 1) → `expected_exceeded` (state_machine.py:792-799) תמיד False.
- נשאר רק `failed_ext_post_lock`, אבל הוא תלוי ב-`bar.extensions_up/down/returned_to_range` שגם הם לא מאוכלסים מ-`_day_type_on_bar` (main.py:230-244 לא מעביר אותם). → **C3 הוא hard-lock דה-פקטו**, סותר את ההחלטה הנעולה "day-type = continuous".
- DB confirm: `SELECT distinct stage,count FROM v9_day_type_state` → `C3:104, B2:81, A2:255, A3:28`; `lock_state` distinct = `LOCKED_LOW_CONF:104, PENDING:364` — אף פעם לא חזר מ-C3 ל-B2 ביום נעול.

**Smallest correct fix:** (1) לחשב `move_in_30min` מ-bar history אמיתי (חלון 6 בארים של 5-דקות מ-DB) ולהעביר ל-`check_reeval_triggers`. (2) לאכלס `extensions_up/down/returned_to_range` ב-`BarInput` מנתונים אמיתיים (Sierra/DB), או — אם לא זמין — להשאיר None ולתעד שה-trigger לא פעיל (no silent). (3) לאחר Phase 1, `atr` יהיה זמין ל-`expected_range_exceeded`.

**Anti-tautological test:** `test_s1_reeval_unlocks.py` — להריץ `process_bar` עד C3+LOCKED, ואז להזין bar עם תנועה > 3·ATR ב-30 דק' → assert `lock_state` חזר ל-`PENDING` ו-`stage==B2`.
*"if reverted → RED because move_30=None ⇒ extreme-move trigger מת ⇒ נשאר LOCKED לנצח."*

---

## Phase 5 — Build Status inspector: AttributeError שקט מפיל את כל ה-interpretations

**Evidence:**
- `backend/v9/systems/build_status/day_type_inspector.py:76` — `str(_m.ib_class.width.value)`. אבל `IBClassification` (schemas.py:159-164) חושף `ib_width`, **לא `width`**. → `AttributeError` ברגע ש-`ib_class` קיים.
- השגיאה נבלעת ב-`except Exception: pass` (inspector.py:78) — מפר CLAUDE.md "No silent failures". התוצאה: כל `system.interpretations` (day_type, opening_type, behavior, ib_width_class) **נופלות בשקט** ברגע שה-IB ננעל — בדיוק כשהן הכי שימושיות.

**Smallest correct fix:** `_m.ib_class.width.value` → `_m.ib_class.ib_width.value`. להחליף את ה-`except Exception: pass` ב-`except Exception as e: logger.warning("[BuildStatus/DayType] interpretations build failed: %s", e)`.

**Anti-tautological test:** `test_build_status_interpretations.py` — לבנות `DayTypeStateMachine`, להריץ bars עד ש-`ib_class` מאוכלס, לקרוא ל-`day_type_inspector.inspect(machine)`, ו-assert ש-`system.interpretations` מכיל `ib_width_class` עם value אמיתי (לא ריק).
*"if reverted → RED because `.width` זורק AttributeError ו-interpretations נשארת ריקה."*

---

## Phase 6 — Duplicate bar processing מנפח `bar_count` פי-2 לכל בר אמיתי

**Evidence:**
- `data/mems26_local.db` `SELECT ts FROM v9_day_type_state ORDER BY ts DESC LIMIT 6` → זוגות ~1-2 שניות זה מזה לכל אינטרוול 5-דקות (08:30:06 + 08:30:05; 08:25:04 + 08:25:03; …). שתי כתיבות לכל בר 5-דקתי.
- ה-dedup ב-main.py:191-194 ממפתח על `bar.get("ts")`; שתי דחיפות עם `ts` שונה (timestamp שונה / event כפול) עוברות → `process_bar` רץ פעמיים → `bar_count += 1` פעמיים (state_machine.py:315).
- השפעה: `bar_count` שמוצג ב-Build Status (inspector.py:65) מנופח; כל aggregator המסתמך על מונה בארים סופר כפול (CLAUDE.md Source-of-Truth Rule 3 — min/max/append amplifiers).

**Smallest correct fix:** לחזק dedup — להוסיף guard נוסף על bucket של 5-דקות (floor של ts ל-300s) או על `(ts, close)` כך שדחיפה כפולה באותו bucket תידחה. לתעד ב-DECISION_LEDGER מאיפה הדחיפה השנייה מגיעה (diagnose-first: לאשר בלוג שזה אותו bar).

**Anti-tautological test:** `test_s1_dedup_bucket.py` — לקרוא ל-handler (או helper) פעמיים עם שני bar dicts באותו 5-min bucket אך ts שונה → assert `process_bar` נקרא פעם אחת בלבד (mock/spy) ו-`bar_count==1`.
*"if reverted → RED because שני pushes באותו bucket מגדילים bar_count ל-2."*

---

## NOT DONE / DEVIATIONS (חובה למלא ע"י CC)
- *(CC ממלא — מה לא בוצע, למה, מה צריד. אם ריק: "none".)*

## דוח חובה (Contract C)
1. טבלת phases: `Phase · Status (DONE/PARTIAL/NOT-DONE) · Evidence (command+output) · Deviation`.
2. לכל טסט שורת *"if reverted → RED because ___"*.
3. סעיף NOT DONE / DEVIATIONS.
4. Open / מה נשאר.
5. עדכון `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (CLAUDE.md § Roadmap auto-update) — root-cause + fix + verification לכל phase.
