# CC PROMPT — S4 Woodies Can-Fire & Trend Consistency (2026-06-02)

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

מטרה אחת: לתקן את אי-העקביות ב-`trend_state` בתוך `WoodiesSystem.process_bar`
(stale current_state נקרא ל-YELLOW pre-drop + dispatcher במקום ה-`studies` של
הבר הנוכחי), ולהפוך את S4 ל-observable ב-Build-Status. **לא** לשנות risk surface,
לא להדליק flags ל-live, לא לגעת ב-`sc_study/`/bridge/market-data routes.

Risk surface אסור לגעת: `cci_calc.py`, `pattern_engine.py`, `trend_relabel.py`
(הלוגיקה תקינה), bridge, sc_study, DLL export paths.

---

## רקע — מצב מאומת (ראיה, לא טענה)

הפייפליין **עובד** ו-S4 **יורה**. אל תניח שהוא חסום. ראיות גולמיות:

- בארים מגיעים + studies + trend מתקדם:
  `v9_bars_5min_woodies` = 109 שורות; trend distribution = BLUE 67, GRAY 34,
  RED 3, YELLOW 5. הבר האחרון `ts=1780384800 cci_14=61.22 trend=BLUE`.
  → A1 **לא** תקוע GRAY/YELLOW. הטענה "A1 חוסם הכל" **הופרכה**.
- patterns מזוהים ומתמידים: `v9_woodies_signals` = 455 שורות, כל 9 הסוגים —
  HTLB 243, TLB 148, ZLR 23, GB100 16, FAMIR 8, VEGAS 7, HFE 6, TT 4.
- S4 ירה trades: `v9_trades WHERE firing_system=4` = 10 שורות, האחרון
  `id=384 SHORT FILLED 2026-06-02 07:46:52` (היום). טווח 2026-06-01→06-02.

המסקנה: אין gap של "can't fire". ה-gaps הם **עקביות trend** + **observability**.

---

## Phase 1 — תיקון stale `trend_state` ב-YELLOW pre-drop ו-dispatcher

### הבאג (ראיה: file:line)
`backend/v9/systems/woodies/woodies_system.py:359`:
```python
trend_state_str = (self.current_state.get("trend_state") or "GRAY").upper()
```
`self.current_state["trend_state"]` מתעדכן **רק** ב-hydrate (שורה 186) וב-
`current_state.update(...)` בשורה 425 — שרץ **אחרי** `evaluate_bar` (שורה 422).
grep מאשר רק שני update-ים (186, 425), אין עדכון מוקדם ב-process_bar.

לכן בשורה 359 הערך הוא של **הבר הקודם**. שתי תוצאות שגויות:
1. YELLOW pre-drop (שורה 368) `if patterns and _ts == TrendState.YELLOW` — בודק
   trend ישן. בר שהפך YELLOW עכשיו לא ייחסם; בר שיצא מ-YELLOW ייחסם בטעות.
2. ה-dispatcher (שורה 374) `_pattern_dispatcher.select_winner(patterns, _ts)`
   מקבל trend ישן → העדפת CONT/REV family שגויה בבר מעבר.

בנוסף, `apply_extreme_trend_relabel(studies)` (שורה 279) משנה את
`studies["trend_state"]`, אבל ה-`_ts` בשורה 359-363 נקרא מ-`current_state`, לא
מ-`studies` — לכן ה-relabel **לעולם לא מגיע** ל-YELLOW pre-drop ול-dispatcher
(הוא כן מגיע ל-A1 כי `_a1_trend_gate` קורא `ctx.studies` — decision_tree.py:176).
זו אי-עקביות single-source: A1 רואה studies, הדיספצ'ר רואה current_state ישן.

### התיקון (smallest correct change)
בשורה 359, החלף את מקור ה-trend ל-`studies` של הבר הנוכחי (אותו מקור ש-A1 רואה):
```python
trend_state_str = (studies.get("trend_state") or "GRAY").upper()
```
(`studies` כבר כולל את ה-relabel מהשורה 279, ותואם ל-`ctx.studies` שמועבר
ל-decision_tree.evaluate_bar.) אל תשנה שום דבר אחר בבלוק.

### Acceptance Criteria (בינארי)
- ✓/✗ בבר עם `studies["trend_state"]=="YELLOW"` ו-patterns לא-ריק →
  `process_bar` משאיר `current_state["active_patterns"]==[]` (נחסם),
  **גם אם** `current_state["trend_state"]` היה "BLUE" לפני הבר.
- ✓/✗ ה-dispatcher מקבל את ה-`TrendState` שנגזר מ-`studies["trend_state"]`
  (לא מ-current_state הישן).

### Anti-tautological test (חובה — קורא לקוד הייצור)
קובץ: `tests/woodies/test_trend_state_source_consistency.py`.
- ייבא `WoodiesSystem`, הזרק bar עם `current_state["trend_state"]="BLUE"`
  ידני, ואז קרא ל-`await sys.process_bar(event)` עם payload שבו
  `trend_state="YELLOW"` ו-CCI שמייצר לפחות 2 patterns.
- assert על הצרכן האמיתי: `sys.current_state["active_patterns"] == []`
  ו-`sys.current_state["decision_tree"]["ready_to_route"] is False`.
- *"if reverted → RED because"*: עם השורה הישנה (`current_state.get`), הקוד
  קורא "BLUE" הישן, ה-YELLOW pre-drop לא מפעיל, patterns נשארים → active_patterns
  לא ריק → assert נכשל (אדום).
- אסור לשכפל את לוגיקת ה-pre-drop לתוך הטסט; ה-assert על הפלט של process_bar.

---

## Phase 2 — Build-Status observability ל-S4 (לא risk surface)

כיום אין שדה observability שמסביר *למה* S4 לא ירה בבר נתון. צריך לחשוף את
המצב הקיים (ה-decision_tree כבר מחזיק אותו — לא להמציא ערכים חדשים).

### מה לחשוף (קרא מ-`current_state` / `dt_summary` הקיימים — Rule 1)
ב-`get_current()` (woodies_system.py:733) ודא שהשדות הבאים זמינים לצרכן
ה-Build-Status (אם כבר ב-current_state — לא לשכפל, רק לוודא שהם נכללים):
- `trend_state` (כבר קיים, שורה 432) — אחרי relabel.
- `bar_count` — חשוף את `self._bar_count` (כרגע **לא** ב-current_state; הוסף
  `"bar_count": self._bar_count` ל-update בשורה 425).
- per-pattern armed/blocked: לכל pattern ב-`active_patterns`, הוסף שדה
  `blocked_reason` הנגזר מ-`dt_summary["failed_stages"]` / `pending_stages`
  (כבר ב-current_state שורות 454-455). אם `ready_to_route is False`, ה-reason
  הוא `failed_stages` הראשון (A1/A5/A7 וכו'). אל תמציא reason — מפה מ-StageResult.

### Acceptance Criteria
- ✓/✗ `get_current()["bar_count"]` מחזיר int לא-None אחרי `process_bar`.
- ✓/✗ `get_current()` כולל `failed_stages` ו-`trend_state` (post-relabel).
- ✓/✗ כשבר נחסם, ה-reason המוצג תואם ל-`StageResult.message` של ה-stage שנכשל.

### Anti-tautological test
`tests/woodies/test_build_status_fields.py` — קרא `process_bar` על bar אמיתי,
ואז assert ש-`sys.get_current()["bar_count"] == sys._bar_count` ו-
`"trend_state" in sys.get_current()`. *"if reverted → RED because"*: אם
מורידים את `"bar_count"` מה-update בשורה 425, המפתח נעדר → KeyError/assert אדום.

---

## NOTE — לא לתקן כאן
- `trend_original` (A/B comparison) — מטופל ע"י ה-orchestrator בנפרד. רק לציין
  בדוח שהשדה נעדר מ-`v9_bars_5min_woodies` ומ-current_state. **אל תכתוב** את
  התיקון.
- `S4_EXTREME_TREND_RELABEL` flag — מאומת **OFF** ב-production (grep ב-
  scripts/*.sh, *.plist, *.env, *.cfg = 0 hits; default OFF ב-atr.py:89).
  הקוד wired (woodies_system.py:279 → trend_relabel.py) אבל אינרטי. **אל תדליק**
  ל-live בלי אישור Michael (Rule B5). רק תעד שהוא OFF + שיש 5 בארים אחרונים עם
  |CCI|>=200 ו-trend GRAY/YELLOW שהיו מושפעים אילו היה ON.
- `a1_strategic_gate.py` (class `A1StrategicGate`) — **לא** רץ בנתיב החי;
  decision_tree משתמש ב-`_a1_trend_gate` שקורא `studies["trend_state"]` מה-DLL.
  אל תנסה לחבר את ה-class הזה — מחוץ להיקף.

---

## תבנית דוח (חובה — חלק C של החוזה)
1. טבלת phases: `Phase · Status (DONE/PARTIAL/NOT-DONE) · Evidence (command+output) · Deviation`.
2. לכל טסט שורת *"if reverted → RED because ___"*.
3. סעיף **NOT DONE / DEVIATIONS** (גם אם "none").
4. **Open / מה נשאר** — כולל trend_original ו-relabel-flag כ-OPEN deferred.

כל "בוצע/עובר" = command + raw output (Rule 5). בלי פלט = לא נחשב.
