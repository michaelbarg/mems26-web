# CC — S1 Day-Type לא מתעדכן כשאופי-היום משתנה (דיאגנוסטיקה)

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**

**מטרה אחת:** לאבחן *למה ה-day_type של S1 לא משתנה* כשאופי-היום בפועל השתנה
(הערת Michael, 2026-06-08). **דיאגנוסטיקה ראשית — קריאה/אבחון; שום תיקון ל-live
בלי strategic-stop + אישור Michael (B5).** מותר להציע fix flag-gated + טסט, אבל
לא להדליק ל-live.

> **אזהרת אנטי-רגרסיה (P27.5d):** אל תציע fix שכבר קיים בקוד. הקוד **כבר** תומך
> ב-re-eval מתמשך — `state_machine.py:718–722, 768–770`: *"lock_state ... does NOT
> prevent re-evaluation"* + *"ALWAYS loop back to B2"*. כלומר **ה-lock אינו השורש.**
> אבחן מה באמת חוסם את ה-vote/קצב-הסשן לפני שאתה נוגע בקוד.

---

## ראיות חיות (snapshot 2026-06-08 ~11:43–11:50 CT, דרך API)

| מקור | day_type | opening_type | lock_state | session_min | vote_history |
|------|----------|--------------|------------|-------------|--------------|
| `/api/v9/day_type/state` | Trend_Normal (conf 0.38) | **UNKNOWN** | **LOCKED_LOW_CONF** | **0** | **[]** (ריק) |
| `/api/v9/key_levels` (pill, מ-`v9_day_type_history`) | Trend_Normal | **OPEN_DRIVE** | — | — | — |
| `/api/v9/five_min/current` | — | **OPEN_DRIVE** | — | — | buffer 42, DAY_TYPE_MODE |

**אנומליות:**
1. **`session_min=0` ב-~193 דק' לתוך RTH** — לא-הגיוני. כל שערי-הזמן ב-state machine
   תלויים בו: IB-period (`state_machine.py:505` `session_min >= ib_period_min`),
   C-period detector (`detector.py:47–48,95,114`, 60–90 דק'), forced-lock
   (`:740` `session_min >= min_session_min_for_lock`, ברירת-מחדל 210 ב-`schemas.py:101`),
   ו-confidence staging (`:754` `cap_confidence_staged(.., session_min)`). אם
   session_min תקוע 0 → המכונה "חושבת" שעדיין טרם-IB ולא מתקדמת.
2. **`vote_history=[]`** — אף vote לא נצבר (`:568,:651`), אז אין על מה להריץ
   reclassification/consecutive-vote.
3. **`opening_type=UNKNOWN` ב-state** בעוד five_min+pill = **OPEN_DRIVE** — פער-instance.
4. **חשד-על (CLAUDE.md §Codebase Index):** `/api/v9/day_type/state` קורא
   **instance-wrapper מת**; הסיווג האמיתי ב-`app.state.day_type_machine` +
   `v9_day_type_state`. ⇒ ייתכן ש-session_min=0/vote=[]/UNKNOWN הם של ה-wrapper המת,
   לא של המכונה החיה. **חובה להצליב את שלושת המשטחים לפני מסקנה.**

---

## Phases (אטומיים)

### Phase 0 — Reproduce + לזהות את ה-instance האמיתי
- הצמד raw של שלושת המשטחים: (a) `/api/v9/day_type/state`, (b) הערך החי ב-
  `app.state.day_type_machine` (מתוך הקוד/לוג שמזין אותו — לא ה-endpoint),
  (c) DB: `SELECT * FROM v9_day_type_state` + `SELECT date, day_type, opening_type,
  lock_state, session_min FROM v9_day_type_history WHERE date=<today ET>`.
- **AC (בינארי):** טבלה עם 3 השורות + הכרעה מפורשת — האם ה-endpoint קורא את
  אותו instance שמזין את ה-DB/dashboard, או wrapper נפרד? פקודת-אימות: ה-SQL לעיל
  + grep לנתיב ה-endpoint (`day_type/api.py`/wrapper) מול `app.state.day_type_machine`.
  *if instance-split מאומת → זה ממצא #1 (מסביר UNKNOWN/0/[] של ה-endpoint).*

### Phase 1 — מאיפה מגיע `session_min` למכונה החיה (השורש המשוער)
- עקוב אחר הנתיב האמיתי: `backend/main.py` (5min → `_day_type_on_bar` →
  `day_type_machine`) — מי בונה את ה-`BarInput.session_min` שמוזן? מה הערך בפועל
  ב-runtime (לוג/print-probe על המכונה החיה, לא ה-endpoint)?
- **AC:** ציון השורה המדויקת שמחשבת `session_min` לנתיב-ההזנה החי + הערך בפועל
  ב-~13:00 IL. אם session_min מגיע 0 למכונה החיה → ממצא-שורש; אם מגיע נכון למכונה
  אבל 0 רק ב-endpoint → ממצא = endpoint/wrapper. *if reverted/הצלבה → איזה משטח משקר.*

### Phase 2 — האם ה-vote/reclass בכלל רץ על המכונה החיה
- האם `vote_history` של **המכונה החיה** מצטבר (לא ה-endpoint)? אם ריק — למה?
  (לא עוברים IB-stage בגלל session_min? bars לא מגיעים? exception נבלע — בדוק B4).
- **AC:** ספירת votes חיה + הנתיב שבו vote נוסף (`:568`/`:651`) רץ או מדולג, עם
  הסיבה המדויקת. פקודה: לוג/probe על `len(machine.vote_history)` לאורך 2–3 ברים.

### Phase 3 — DYNAMIC (shadow) מול LIVE reclass — מה מחווט לאן
- `shadow_reclass.py` מסומן **"SHADOW LOG ONLY"** (D-S1DYN) ⇒ `S1_DYNAMIC_RECLASS`
  רק *מתעד*, לא משנה day_type חי. ב-`.env`: `S1_DYNAMIC_RECLASS=true` +
  `S1_LIVE_RECLASS=true`. **שאלה:** האם `S1_LIVE_RECLASS` באמת **מיישם** reclass על
  ה-instance החי, ואיפה בקוד? או שאין נתיב-יישום והכל נשאר shadow?
- **AC:** ציון הקוד שבו `S1_LIVE_RECLASS` משנה את ה-day_type החי (קובץ:שורה) —
  או הצהרה מפורשת "אין נתיב כזה" (=ממצא: ה-LIVE flag דקורטיבי). *if reverted → RED because…*

### Phase 4 — `opening_type=UNKNOWN` ב-state מול OPEN_DRIVE בכל השאר
- למה ה-state-instance לא מקבל את ה-opening_type שה-five_min/pill כבר מחזיקים?
  אותו שורש כמו session_min (instance-feed) או נתיב-נפרד?
- **AC:** הנתיב/השורה שמזין opening_type ל-day_type state + למה הוא UNKNOWN שם.

### Phase 5 — דוח לפי חלק C של החוזה
טבלת phases (DONE/PARTIAL/NOT-DONE + Evidence command+output) · לכל טסט שורת
*"if reverted → RED because ___"* · סעיף **NOT DONE / DEVIATIONS** (גם אם "none")
· **Open / מה נשאר**. עדכן `MEMS26_ISSUES_REGISTER.md` I-1 + `STATUS_BOARD.md`.

---

## אסור לגעת (risk surface)
- אל תשנה fire-path / gateway / risk. אל תדליק reclass ל-live בלי strategic-stop+Michael.
- אל תיגע ב-chop gates / `FOOTPRINT_DISABLED` / Bridge local-only / LaunchAgent.
- **מקור-אמת:** ערכי IB/atr_daily/opening — להצליב מול `~/SierraChart_Data/v9_export/`
  (ה-dashboard מראה `Y IB dll_missing` ⇒ ייתכן שקלט-יום חסר מ-Sierra תורם ל-UNKNOWN/0).
  כל פער backend↔Sierra = ממצא נפרד.

## קבצים רלוונטיים (לקריאה לפני שינוי)
- `backend/v9/systems/day_type/state_machine.py` (:505,:568,:651,:718–722,:740,:754,:768–770)
- `backend/v9/systems/day_type/detector.py` (:47–48,:95,:114) · `schemas.py` (:101,:109,:207)
- `backend/v9/systems/day_type/shadow_reclass.py` (SHADOW LOG ONLY) · `consumer.py` (:200–207)
- `backend/main.py` (`_day_type_on_bar` → `day_type_machine`) · `backend/v9/api/v9/day_type/api.py`
- DB: `v9_day_type_state`, `v9_day_type_history`
