# CC — תיקון טסטים-מזויפים + flag #3 + artifact ל-replay (ביקורת מעמיקה) · 2026-06-09

**קרא קודם:** `CLAUDE.md` (§Pre-LIVE Discipline · §Source-of-Truth Rule 5 · §Standing Decisions),
`docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological tests). ביקורת-Cowork על
`ALL_FIXES_SUMMARY_2026-06-09.txt` + הקומיטים `0bc1d20`/`2aef154`/`23163d9`/`0efe9e0`.

**הקדמה ישרה:** תיקוני-**הקוד** שלך נכונים (אימתתי: inspector `_raw_buffer[:-1]` תואם
engine; #1 stop אמיתי; #3 `_det_buf`; #2/#4 ts-parse). הבעיה היא ב**ראיות**: "204 green"
מטעה כי כמה טסטים לא בודקים את מה שהם טוענים, ו-"80 fires" אין לו artifact.

---

## 0 · 🔴 הבעיה השורשית — טסטים טאוטולוגיים (חוזר 3 פעמים)
הדפוס: אתה **משכפל את לוגיקת-הייצור בתוך הטסט** במקום **לייבא ולקרוא** לה. אז הטסט
מוכיח `X == X` (העתק-של-הנוסחה שווה לעצמו) — **כיסוי אפס**. "RED-on-revert" נעשה
שקרי: החזרת קובץ-הייצור לא מכשילה טסט שלא נוגע בו.

**הוכחות (file:line):**
- `tests/v9/regression/test_inspector_engine_alignment.py:36-37` —
  `_raw_buffer = getattr(fake,"_bar_buffer",[])` ואז `inspector_buffer = _raw_buffer[:-1] if len>=8`.
  זה **לא** מייבא את `s2_inspector` ולא קורא ל-`inspect_s2`/`_probe_pattern`. מייבא רק `os`+`mock`.
  → revert של `s2_inspector.py` משאיר אותו ירוק.
- `tests/v9/regression/test_s2_detect_on_completed_bar.py:19,28,37` — `_det_buf = buffer[:-1] if len>=8`
  משוכפל בטסט; **לא** מייבא `five_min_system`. (לא תוקן מהסבב הקודם.)
- `tests/v9/regression/test_dll_fallback_stop.py` — מחשב ATR מחדש וקורא `compute_stop` ישירות +
  בונה `PatternResult` ידנית; **לא** מאתחל `WoodiesSystem` ולא קורא `process_bar`.

**מבחן-קבלה לכל טסט מתוקן (חובה):** (א) `import` של מודול-הייצור האמיתי. (ב) קריאה
לפונקציה/מתודה האמיתית (לא העתק שלה). (ג) RED-on-revert **מוכח**: `git stash` של תיקון-הייצור
→ הרץ → **אדום** → `git stash pop` → **ירוק**. הדבק את שתי הריצות הגולמיות.

---

## 1 · 🔴 טסט #5 (inspector) — לכתוב מחדש שיקרא ל-inspector האמיתי
קרא ל-`s2_inspector.inspect_s2(...)` (או לנקודת-הכניסה שמרכיבה `bar_buffer`) עם
`five_min_system` מזויף שבו `_bar_buffer` בגודל ≥8 והבר האחרון **חלקי** (OHLC שונה
מהבר הקודם). אַמֵּת ש-ה-`_b4`/entry/stop שה-inspector **מחזיר בפועל** מבוססים על הבר
המושלם (`_raw_buffer[-2]`), לא החלקי. RED-on-revert: `git stash` של `0efe9e0` → הטסט
נכשל (b4 = חלקי) → pop → עובר. הדבק גולמי.

## 2 · 🔴 טסט #3 — לכתוב מחדש שיקרא ל-`FiveMinSystem`
הזרם buffer דרך הנתיב האמיתי (`process_bar`/`_run_detectors`) כך שהבר האחרון חלקי
(opening tick), ואַמֵּת ש-detection+entry נגזרים מהבר המושלם. RED-on-revert מול `2aef154`.

## 3 · 🔴 טסט #1 — end-to-end דרך `process_bar`
הזרם בר עם `zlr_detected=True` דרך `WoodiesSystem.process_bar` ואַמֵּת: אין חריגה ·
ZLR נכנס ל-`active_patterns` · `stop>0` אמיתי (לא 0.0/None) · R:R שפוי. (השאר גם את
`test_dll_zlr_stop_none_crashes` — הוא תקין.) RED-on-revert מול `0bc1d20`.

## 4 · 🔴 #2/#4 — להוסיף טסט (כרגע אפס)
טסט שמפעיל את נתיב-ה-persist האמיתי עם `ts` כמחרוזת-ISO ו-epoch-int, ומאמת שהשורה
נכתבת עם timestamptz תקין. RED-on-revert מול `23163d9` (הקוד הישן `fromtimestamp(string)`
קורס). ודא ש-`safe_writer` לא נשבר לטבלאות אחרות.

## 5 · 🟡 #3 — flag-gate (חסר)
`five_min_system.py:922` `_det_buf = self._bar_buffer[:-1]...` קשיח. או הוסף flag הפיך
(default = ההתנהגות החדשה), או נמק **בכתב** למה זה תמיד-נכון ולא צריך flag (אז עדכן את
§3.3 בהאנד-אוף בהתאם). כל שאר התיקונים הפיכים — #3 חריג.

## 6 · 🔴 Replay — artifact ניתן-לשחזור + תיקון ניפוח-הספירה
"29 S4 + 51 S2 = 80 fires" קיים רק כטקסט. נדרש:
- **script committed** + פלט גולמי ל-`docs/reports/REPLAY_2026-06-08_RAW.txt`: איזה ברים
  (קובץ/טווח), דרך איזה detectors, איך נספר fire. בלי זה אי-אפשר לאמת (Rule 5).
- **תיקון ניפוח:** 43 מתוך 51 הם **Double-Top AA על אותו setup** = בדיוק באג-הכפילות
  (בעיה 3, stateless detector). דווח **fires נפרדים** בנפרד מ-fires-גולמיים: distinct ≈
  7 Reactive + 1 Bear Flag + Double-Top-מאוחד. הכותרת "80" מנפחת פי-כמה את העבודה האמיתית.

---

## הקשר — backtest חודשי (Michael ביקש)
Cowork ינסח אפיון נפרד ל-backtest-עם-P&L על חודש Sierra. **תנאי-קדם:** dedup ל-Double-Top
(בעיה 3) חייב להיסגר קודם — אחרת חודש-היסטוריה יספור עשרות עסקאות-רפאים על setup יחיד
וינפח את ה-P&L. אל תתחיל backtest לפני שבעיה 3 מאושרת ע"י Michael ומתוקנת.

## איסור (§Standing Decisions)
אל תדליק/תשחזר אף דגל default-off (`S2_CHOPPINESS_GATE`·`LAYER0_CHOP_GATE`·`S2_REQUIRE_COT_AMT`).

## פורמט תשובה (Rule 5)
1. לכל טסט (1-4): קוד-הטסט החדש + **שתי ריצות `pytest` גולמיות** (stash=אדום, pop=ירוק).
2. #3 flag: diff או נימוק-בכתב.
3. Replay: נתיב ל-script + ה-artifact הגולמי + ספירת distinct מתוקנת.
4. NOT-DONE: מה לא נסגר ולמה.
5. אישור: אף דגל default-off לא הודלק.
