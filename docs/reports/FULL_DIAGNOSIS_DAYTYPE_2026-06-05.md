# אבחון מלא · day_type=UNKNOWN (שורש) + choppiness · 2026-06-05

מקור-אמת: קוד ב-repo + state חי (`/api/v9/day_type/state`). שורש מאומת, לא השערה.

## השורש (חד-משמעי)
**S1 day_type לא מקבל ברי-5min → `process_bar` רץ 0 פעמים → תקוע ב-stage A1 → day_type=UNKNOWN לנצח.**

ראיות:
- מצב חי 09:31 CT (61 דק' לתוך RTH, אחרי סגירת-IB): `stage=A1`, `bar_count=0`,
  `ib_locked=false`, `session_min=0`, `day_type=UNKNOWN`, `vote_history=[]`.
- `state_machine.py:315` — `bar_count` עולה **בשורה הראשונה** של `process_bar`. bar_count=0 ⇒
  process_bar **מעולם לא רץ**.
- `wrappers.py:44` — `subscribed_streams = ["cumulative_delta", "volume_profile"]`.
  **S1 מנוי לזרמים האלה בלבד — לא ל-`"5min"`.** ה-state machine צריך ברי-5min RTH
  (OHLC + IB + opening) כדי להתקדם A1→A4→B1(vote). הוא לא מקבל אותם.
- השוואה: `five_min` מנוי ל-`"5min"` (עובד, buffer=166) · `woodies` ל-`"woodies_5min"`
  (עובד, hydrated) · `day_type` ל-cumulative_delta/volume_profile (bar_count=0).
- **לא** atr (מחושב מ-bar_ranges, `state_machine.py:324`), **לא** IB-timing (vote ב-B1
  אחרי 60-דק'-IB — `:505,549-554`), **לא** ה-confidence ש-CC שינה. הכל downstream של
  "אין ברים בכלל".

## מה לא קשור (להסיר רעש)
- CC שינה `compliance_manifest.yaml` confidence 0.70→0.85 — לא נגע בשורש, ו-סף-נעילה
  גבוה יותר רק **מחמיר**. **לבטל (revert).**
- A5 (CC תיקן ל-advisory) — תקין ובטוח, אבל לא קשור ל-day_type.
- S3 0-ברים — מושתק (S3_MUTE) פר-החלטת Michael, parked.

## choppiness (נפרד)
`chop=79 stale 1m` נכשל ב-gate `<70`. `chop_score.py`: ≥75 = chop-tier עליון. **79 = choppy
אמיתי → חסימה מוצדקת** *אם* הערך טרי. ה-"stale 1m" חשוד — ה-refresher (`chop_score.py:248`,
interval) מפגר → הגייט חוסם על ערך ישן. צריך לאמת מול Sierra אם 79 חי או תקוע.

## אפיון נכון (הגדרת Michael 2026-06-05) — מתקן את הלוגיקה
day_type = **מסווג רציף ודינמי**, לא נעילה-חד-פעמית:
1. **הצבעה מרגע פתיחת RTH** (08:30 CT), לא ממתינה לסגירת-IB.
2. השעה-הראשונה מסייעת לקבוע את ה**פתיחה**; **תוך 30 דק' כבר יש סוג-יום** (ראשוני, בביטחון עולה).
3. **דינמי — סוג-היום משתנה לאורך הסשן** לפי מה שקורה בשוק (לא ננעל ב-IB).
4. הוא ה**קובע**, מתעדכן רציף, ו**מופץ בזמן-אמת לכל המערכות** (S2 day-patterns · Woodies A2 ·
   build_status · gateway).

**הפער מול היום:** הקוד מצביע **רק** ב-B1 אחרי 60-דק'-IB (`:505,549-554`) ואז נועל —
מנוגד לאפיון. צריך הצבעה-מדורגת מהפתיחה + re-eval רציף שמשנה את סוג-היום.

═══════════════════════════════════════
## בדיוק מה נדרש כדי שהמערכת תעבוד חלק
═══════════════════════════════════════
**0 · קודם-כל (חוסם הכל):** בלי זה כל השאר חסר-משמעות —
1. **🔴 חוּט S1 day_type לזרם ה-5min** — `wrappers.py:44`: להוסיף/להחליף `subscribed_streams`
   כך ש-S1 יקבל ברי-5min RTH (OHLC + session_min + is_rth + IB), כמו `five_min`. בלי זה
   day_type=UNKNOWN לנצח. **אימות:** `bar_count` עולה מ-0.
2. **🔴 הצבעה רציפה-מדורגת (אפיון Michael)** — לשנות מ-"vote-once-at-IB-lock" ל:
   הצבעה **מהפתיחה**, סוג-יום **ראשוני תוך 30 דק'** (ביטחון עולה לאורך השעה), **re-eval
   רציף ששמשנה** את סוג-היום לפי השוק (לא נעילה). המכונה כבר מדורגת (A1→C3) + יש
   `_check_reeval` — להפעיל הצבעה מוקדמת + לבטל את הנעילה-הקשיחה.
3. **🔴 הפצה בזמן-אמת לכל המערכות** — סוג-היום העדכני (S1) → S2 day-patterns gate · Woodies A2 ·
   build_status · gateway. מקור-יחיד, מתעדכן בכל בר. *(2-3 = trading-logic → אישור Michael; זה האפיון שלו.)*
2. **🟡 revert** ל-`compliance_manifest.yaml` 0.85→0.70 (השינוי של CC, לא קשור, מחמיר).
3. **🔴 B-11** — `bridge_inspector` rowid→ts_col → ה-Build Status יפסיק להציג BLOCKED/dead שקרי.
4. **🟡 choppiness** — לאמת שה-chop-score טרי (לא stale 1m); אם ה-refresher מפגר → לתקן את
   תדירות-הרענון / מקור. אם 79 אמיתי — החסימה מוצדקת.
5. **parked:** S3 (מושתק) · B-14 · B-13 write-guard · ZLR-counterfactual (לכשתידרך).
