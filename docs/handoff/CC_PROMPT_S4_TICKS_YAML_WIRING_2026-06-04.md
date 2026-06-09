# CC PROMPT — חיווט S4 pattern ticks ל-YAML (להפוך mirror→authoritative) + חיזוק טסט · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** המשך ישיר ל-commit `182862b` (config→YAML, Option A).
**אישור Michael 2026-06-04.** מבוסס על ממצא הצלבת-Cowork: `STATUS_BOARD.md` § "config→YAML round-trip" (2026-06-04 eve).

## רקע (ממצא Cowork — אומת)
ב-`182862b` נוצר `config/stop_params.yaml` עם בלוק `s4_patterns` (9 תבניות), אבל **9 ה-detectors של Woodies לא קוראים ממנו** —
כל אחד עדיין משתמש בקבועי-מודול קשיחים `STOP_TICKS`/`TARGET1_TICKS`/`TARGET2_TICKS`. כלומר בלוק ה-`s4_patterns` הוא
**mirror-בלבד / אינרטי** — עריכת ה-YAML לא משנה התנהגות S4. (S2 `adaptive_stop` + auth + targets + `min_r_t1_threshold` **כן** מחווטים.)
Cowork אימת **0 drift** היום בין ה-YAML לקבועים, ולכן זו **חיווט-בלבד, 0 שינוי-ערך** — לא strategic-stop.

> **מטרה אחת:** להפוך את 9 ה-detectors לקרוא את `stop_ticks/t1_ticks/t2_ticks` מ-`load_stop_params()['s4_patterns'][PID]`,
> עם **fallback לקבוע הקשיח** הקיים (Rule 1: YAML שותק/לא-תקין → קבוע + warning, לא סינתזה). + לחזק את הטסט שיתפוס drift אמיתי.

## ⛔ risk surface — מה אסור
- **אסור לשנות ערך** stop/t1/t2 כלשהו (ה-YAML כבר == המקור, אומת). זו חיווט בלבד.
- **אל תיגע** ב-`_T1_TICKS` (=4) — הוא **שונה** מ-`TARGET1_TICKS`. `_T1_TICKS` = ברירת-מחדל לחישוב R_t1; ה-YAML `t1_ticks` ממפה ל-**`TARGET1_TICKS`** (יעד), לא ל-`_T1_TICKS`. אל תאחד/תבלבל ביניהם.
- אל תיגע ב-S2/adaptive_stop (כבר מחווט), sc_study, risk_checks, polling-floors.

## Phase 1 — אודיט (diagnose-first, הדבק ממצא)
1. לכל 9 הקבצים `backend/v9/systems/woodies/patterns/{zlr,tlb,tt,gb100,vegas,ghost,famir,htlb,hfe}.py` —
   הדבק את שורות ההגדרה (`STOP_TICKS=/TARGET1_TICKS=/TARGET2_TICKS=`) **ואת אתרי-הצריכה** (היכן בגוף ה-detect הם נקראים, כמו `zlr.py:105,119,120`).
2. ודא שאין צרכן חוצה-מודול לקבועים האלה (Cowork מצא 0 — אמת מחדש: `grep -rn "\.STOP_TICKS\|import STOP_TICKS" backend/v9`).
3. **הכרעת-עיצוב (single-source):** בחר את החיווט הנקי — מומלץ helper מרכזי אחד (למשל `woodies/_pattern_ticks.py::get_ticks(PID) -> (stop,t1,t2)` שקורא `load_stop_params()` עם fallback), ולא 9 העתקים של `_try_load`. הדבק את ההכרעה ונמק.

## Phase 2 — חיווט
- כל detector שואב את שלושת ה-ticks מ-`load_stop_params()['s4_patterns'][PID]` (PID = מזהה התבנית), **fallback** לקבוע הקשיח הקיים אם חסר/לא-תקין.
- שמור על אתרי-הצריכה הקיימים (`STOP_TICKS * TICK_SIZE` וכו') — רק המקור משתנה מקבוע-מודול ל-ערך-נטען.
- guardrails כבר ב-`load_stop_params` (`max_stop_ticks=20`, `max_t2_ticks=50`) — אם הם דוחים, נופלים ל-fallback + `logger.warning` (B4, אין כשל שקט).

## Phase 3 — חיזוק הטסט (anti-tautological, B1)
`test_stop_params_roundtrip` הנוכחי משווה S4 מול **ליטרלים בטסט** (3/9 בלבד) — פסול לכיסוי-drift. החלף/הוסף:
- **`test_s4_ticks_yaml_matches_detector_constants`** — לולאה על **כל 9** התבניות, `assert load_stop_params()['s4_patterns'][PID] == {stop_ticks: <DETECTOR>.STOP_TICKS, t1_ticks: <DETECTOR>.TARGET1_TICKS, t2_ticks: <DETECTOR>.TARGET2_TICKS}` — **מייבא את קבועי ה-detector האמיתיים**, לא ליטרל.
- **`test_s4_detector_reads_from_yaml`** (litmus אמיתי) — monkeypatch/override של ערך YAML ל-PID אחד (למשל ZLR stop_ticks 8→9) → טען מחדש → קרא ל**נתיב הייצור** של ה-detector (או ל-helper) → `assert` שה-stop האפקטיבי השתנה ל-9. **if reverted (חיווט מוסר) → RED because** ה-detector יחזור לקרוא את הקבוע הקשיח וה-override יתעלם.

## Acceptance (✓/✗ + raw לכל אחד)
- [ ] Phase 1 audit מודבק (9 קבצים: הגדרה + אתרי-צריכה) + הכרעת single-source מנומקת.
- [ ] 9 ה-detectors קוראים ticks מ-YAML עם fallback (הדבק diff מייצג של 1 detector + ה-helper).
- [ ] `test_s4_ticks_yaml_matches_detector_constants` עובר על **9/9** (raw) + שורת *"if reverted → RED because ___"*.
- [ ] `test_s4_detector_reads_from_yaml` מוכיח override חי דרך נתיב-הייצור (raw) + litmus.
- [ ] **0 שינוי-ערך:** ה-ticks האפקטיביים בברירת-מחדל == הקבועים הקשיחים (raw: pytest ירוק + grep שהקבועים לא נמחקו, נשמרו כ-fallback).
- [ ] regression מלא ירוק (raw) · `git log -1` · סעיף **NOT-DONE/DEVIATIONS** (גם אם "none").

## Invariants
חיווט-בלבד — 0 שינוי-ערך · `_T1_TICKS` ≠ `TARGET1_TICKS` (אל תאחד) · single-source · fallback ב-Rule 1 (חסר→קבוע+warning) ·
localhost-PG · No silent failures · Cowork מאמת בלתי-תלוי (litmus revert→RED + הצלבת 9 התבניות מול source).
