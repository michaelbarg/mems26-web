# CC — הסבר + סגירת פערים על חבילת 4-הבאגים (2026-06-09)

**קרא קודם:** `CLAUDE.md` (§Pre-LIVE Discipline · §Standing Decisions · §Source-of-Truth Rule 5),
`docs/handoff/CC_HANDOFF_CONTRACT.md`, ו-`docs/handoff/HANDOFF_NEXT_CHAT_2026-06-08_NIGHT.md` §3.
זה פרומפט-ביקורת מ-Cowork (verifier בלתי-תלוי). אימתתי את הקומיטים
`638e664` (S2⟂S3) · `0bc1d20` (#1) · `2aef154` (#3) · `23163d9` (#2/#4).

**מטרה כפולה:** (א) לכל פער למטה — **תסביר קודם *למה* לא ביצעת** (החלטה מודעת? פספוס?
חוסם? נדחה?). אל תתקן לפני שהסברת. (ב) אחרי ההסבר — תסגור, עם ראיה גולמית (Rule 5:
פקודה+פלט, לא "confirmed").

**איסור מוחלט (§Standing Decisions):** אל תדליק/תשחזר אף דגל default-OFF
(`S2_CHOPPINESS_GATE` · `LAYER0_CHOP_GATE` · `S2_REQUIRE_COT_AMT`). אם תיקון דורש זאת —
STRATEGIC-STOP + שאל את Michael.

---

## פער 1 🔴 — Inspector לא יושר ל-engine (§3.3 + בעיה 5 בדוח, P0)
התיקון של באג #3 העביר את ה-engine ל-`_det_buf = buffer[:-1]`, אבל
`backend/v9/systems/build_status/s2_inspector.py:346` עדיין `_b4 = bar_buffer[-1]`
(הבר החלקי). כלומר אי-ההתאמה engine≠inspector שבאג #3 בא לתקן **עדיין קיימת בצד
התצוגה** — בדיוק האזהרה ב-§0 ("inspector ≠ engine") ובדרישת §3.3. זה גם **בעיה 5
(P0)** ב-`docs/reports/ISSUES_AND_RECOMMENDATIONS_2026-06-09.txt`: "ה-dashboard משקר
(בלי כוונה)" — Michael רואה "הכל ירוק" ואין fire.

- **הבהרה שדורשת אימות:** הדוח טוען שה-inspector "קורא ברים מה-DB"; אני מצאתי שהוא
  קורא `getattr(five_min_system,"_bar_buffer")` (in-memory) ב-`:125` ומשתמש ב-`[-1]`
  כ-b4 ב-`:346`. **אמת איזו טענה נכונה** לפני התיקון (Rule 2 — verify before you trust).
- **הסבר:** למה ה-inspector לא יושר באותו commit של באג #3?
- **סגירה (עדיף Option ב מהדוח):** במקום שה-inspector ירוץ detection עצמאי על חלון
  משלו, שה-engine ישמור את תוצאת ה-detection האחרונה (`detected`/`reason`/`b4_ts`)
  ב-state, וה-inspector יציג אותה — **single source of truth**. אם זה גדול מדי כרגע,
  כפתרון-ביניים יישר את חלון ה-b4 ל-`buffer[:-1]`. בכל מקרה: הוכח עם בר-בדיקה
  ש-inspector.b4 == engine.b4.

## פער 2 🔴 — טסט #3 טאוטולוגי (מפר CC_HANDOFF_CONTRACT)
`tests/v9/regression/test_s2_detect_on_completed_bar.py` מחשב מחדש
`buffer[:-1] if len>=8` *בתוך הטסט עצמו* ואף פעם לא מייבא את `five_min_system.py`.
לכן טענת "RED-on-revert" שגויה — החזרת התיקון לא מכשילה את הטסט.

- **הסבר:** למה הטסט לא קורא לנתיב האמיתי?
- **סגירה:** כתוב טסט שמפעיל את הקוד שבאמת תוקן (FiveMinSystem על buffer שבו הבר
  האחרון חלקי, ומאמת שה-detection/entry נגזרים מהבר המושלם). הוכח RED-on-revert:
  `git stash` את התיקון → הטסט נכשל → unstash → עובר. הדבק את שתי הריצות.

## פער 3 🔴 — #2/#4 (`23163d9`) עלה בלי שום regression test
מפר CLAUDE.md "Add a regression test for every bug fix".

- **הסבר:** למה לא צורף טסט?
- **סגירה:** הוסף regression ל-ts-parse: מחרוזת-ISO ו-epoch-int שניהם נשמרים נכון;
  הוכח RED-on-revert (הקוד הישן `fromtimestamp(string)` קורס/שגוי). ודא ש-`safe_writer`
  לא נשבר לטבלאות אחרות.

## פער 4 🟡 — טסט #1 לא מפעיל את `process_bar`
`tests/v9/regression/test_dll_fallback_stop.py` בונה `PatternResult` ידנית וקורא
ל-`compute_stop` ישירות — לא מאתחל `WoodiesSystem` ולא קורא ל-`process_bar`. ה-end-to-end
של §3.2 (בר `zlr_detected=True` → אין `process_bar error` → ZLR ב-`active_patterns` →
`stop>0` אמיתי) לא מכוסה אוטומטית.

- **הסבר:** למה לא נבדק הנתיב המחובר?
- **סגירה:** טסט שמזרים בר עם `zlr_detected=True` דרך `process_bar` ומאמת:
  אין חריגה · ZLR נוסף ל-patterns · `stop>0` (לא 0.0, לא None) · R:R שפוי.

## פער 5 🟡 — אין flag gate על #3
שאר השינויים הפיכים/מגודרים; #3 קשיח בקוד. ה-handoff §3.3 ציין "flag" כתנאי.

- **הסבר:** למה #3 לא גודר ב-flag (החלטה מודעת שהוא תמיד-נכון, או פספוס)?
- אם מודע — נמק בכתב; אם לא — הוסף flag הפיך (default = ההתנהגות החדשה).

## פער 6 🟡 — אין דוח-תיקון עם פלט גולמי (Rule 5)
"201/198 green" קיים רק בהודעות-commit. דוח `STOP_AND_BUGS_INVESTIGATION_2026-06-08.md`
נכתב 20:24, *לפני* הקומיטים, ועדיין כתוב בו "תיקון מוצע (לא בוצע)".

- **סגירה:** דוח-תיקון קצר עם פלט `pytest` גולמי מודבק לכל 4 הבאגים + סעיף **NOT-DONE**
  (כולל מה שנדחה ולמה). עדכן את שורת ה-stale בדוח החקירה.

## פער 7 🟡 — הבורדים לא עודכנו (חובה ב-CLAUDE.md §Roadmap auto-update)
`docs/plans/ROADMAP_TO_LIVE.html` modified+uncommitted ועדיין ממסגר את הבאגים כ-"CC
מתקן"/Phase-0 כ-"uncommitted". ב-`docs/plans/STATUS_BOARD.md` רשומת-הלוג האחרונה היא
מ-**2026-06-01** — אין שורת 06-08/09 ל-4 הבאגים בפורמט finding+fix+verification.

- **סגירה:** עדכן ROADMAP (סמן done, רענן "אתה כאן"+"עודכן") ו-STATUS_BOARD (שורת-לוג
  לכל באג: שורש → תיקון → אימות). commit את הבורדים.

## פער 8 🔵 — אינדקס לא חודש
קבצי-הטסט החדשים לא מופיעים ב-`tests/v9/regression/_INDEX.md`.

- **סגירה:** `python3 scripts/gen_index.py` → commit האינדקס המרענן.

---

## פורמט תשובה נדרש
1. **למה-לא** לכל פער (1–8) — שורה-שתיים, כן/לא-מודע + נימוק.
2. **תיקונים** — diff/קומיט לכל פער שנסגר.
3. **ראיה גולמית (Rule 5)** — פקודות + פלט מלא של `pytest`, לא סטטוס.
4. **NOT-DONE** — מה לא נסגר ולמה (כולל frontend חלק-C ואימות-ירי-חי RTH אם נדחים).
5. **אישור Standing-Decisions** — אף דגל default-off לא הודלק.

אל תתקדם ל-§6.2 (ריצת-RTH / אימות-ירי-חי) עד שפערים 1–4 חיים+מאומתים.

---

## חלק ב' — בעיות מערכתיות מ-`ISSUES_AND_RECOMMENDATIONS_2026-06-09.txt`
הדוח (replay של 06-08: 80 fires פוטנציאליים, 0 בפועל) מעלה 7 בעיות. בעיות 1/2/4/5
חופפות לפערים למעלה. הנותרות הן עבודה **חדשה** — לא "למה לא ביצעת" אלא triage:
תאשר/תתמחר/תסמן כהחלטת-Michael. **אל תיגע ב-trading-logic בלי STRATEGIC-STOP.**

### בעיה 3 🟡 [P1] — Double Top AA יורה 43× על אותו setup
דטקטורים של chart-patterns (Double/H&S/Flag) הם stateless → fire חוזר כל בר אחרי
פריצה (ה-cooldown חוסם אבל מבזבז CPU+מטשטש לוג).
- **פעולה:** הצע diff ל-dedup ברמת ה-engine: `last_fire_pattern_id + ts` ב-FiveMinSystem,
  skip אם אותו pattern+direction תוך N ברים (N = lookback הדטקטור). אל תשנה את הדטקטורים.
  זה משנה התנהגות-ירי → **STRATEGIC-STOP + אישור-Michael לפני מימוש.**

### בעיה 6 🔴 [P0] — CCI של Python ≠ DLL (פער 1.8 נק' → מפספס ZLR)
Python CCI=-98.2 מול DLL שסימן ZLR (≤-100). זה גם פתוח ב-handoff §5 ("פער-CCI").
חשוד: seed period (Python 50 ברים מול אלפי ב-DLL) או OHLC source.
- **פעולה (אבחן-קודם):** הצג מאיפה הפער — הרץ את שני החישובים על אותו חלון והדבק
  פלט. לפי CLAUDE.md §Sierra (DLL=source-of-truth) ההמלצה היא **להשתמש ב-CCI שכבר
  מגיע ב-export JSON במקום לחשב מחדש** — אך זה משנה זיהוי → STRATEGIC-STOP + אישור.
  קשור ל-המלצת-טווח-ארוך של בעיה 1 (לכייל Python detectors מול DLL ואז לבטל את
  ה-DLL-fallback לחלוטין).

### בעיה 7 🔵 — Initiative expansion gate מחמיר ביום תנודתי (החלטת-Michael)
1.3×avg_range; ביום עם avg גבוה הסף עולה → 0 Initiative fires. **הדוח עצמו מסמן: זו
החלטת-כיול, לא באג.** אל תשנה. הצג ל-Michael את האפשרויות (1.15× · cap על avg ·
להשאיר) והמתן להחלטה.

### העמקות על הבאגים שכבר תוקנו (תעד, אל תבצע בלי אישור)
- **בעיה 1 (#1):** ה-DLL-fallback הוא פלסתר — קיים כי Python מפספס מה ש-DLL מזהה.
  טווח-ארוך: לכייל את ה-Python ZLR/HFE מול DLL ואז לבטל fallback (תלוי בבעיה 6).
- **בעיה 2 (#2 partial-bar):** `buffer[:-1]` הוא convention ולא contract. המלצת-הדוח:
  מודל מפורש `on_bar_close` (trigger detection כשה-ts משתנה, entry=close של הבר שנסגר).
- **בעיה 4 (#2/#4 ts):** רוחבי — `safe_writer` משמש 11+ טבלאות. המלצה: `ensure_iso_ts(raw_ts)`
  מרכזית + audit חד-פעמי של כל קריאות `safe_execute` שמעבירות ts. (משלים פער 3 למעלה.)

### תוספת לפורמט התשובה
6. **טבלת-triage לבעיות 3/6/7** — לכל אחת: אבחון/ראיה · הצעת-פתרון · "דורש STRATEGIC-STOP?"
   · הערכת-זמן. בעיות שמשנות trading-logic נשארות OPEN עד אישור-Michael (אל תממש).
7. עדכן את `ISSUES_AND_RECOMMENDATIONS_2026-06-09.txt` עם סטטוס מעודכן (תוקן/triaged/parked).
