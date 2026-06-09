> ⛔ **OBSOLETE (2026-06-05) — אל תשלח.** האבחון שעמד בבסיסו שגוי: ה-S1 האמיתי
> (`backend/main.py:405`) **מחווט נכון** (5min + IB מ-Sierra TPO) ו-day_type **מסווג Normal**.
> מה שנראה כ-UNKNOWN הוא endpoint שקורא instance-מת (`/day_type/state`→wrapper). הפעולות
> הנכונות: (1) `/state` יקרא את ה-machine האמיתי/DB; (2) הסר את ה-dead-wrapper; (3) propagation
> ל-Woodies A4. ראה VERIFY_DAYTYPE + I-1 ברשימת-הבעיות.

# CC — day_type · תיקון שורש + אפיון Michael · 2026-06-05

חוזה `CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. בסיום: `docs/reports/VERIFY_DAYTYPE_<תאריך>.md`
עם raw output. אל תיגע בלוגיקת-מסחר מעבר ל-day_type.

## ⚠️ קודם
Cowork תיקן השחתה ב-`state_machine.py:1` (תו "לך" תועה לפני ה-docstring → syntax error). **אל תחזיר.**
ודא `python -c "import backend.v9.systems.day_type.state_machine"` עובר.

## השורש (אומת חי 09:31 CT, אחרי סגירת-IB)
`/api/v9/day_type/state` → `bar_count=0`, `stage=A1`, `session_min=0`, `day_type=UNKNOWN`.
`state_machine.py:315` — bar_count עולה בשורה-הראשונה של `process_bar` ⇒ **process_bar מעולם לא רץ**.
הסיבה: **`wrappers.py:44`** `subscribed_streams=["cumulative_delta","volume_profile"]` — S1 **לא מנוי
ל-`"5min"`** → לא מקבל ברי-RTH. (five_min מנוי ל-"5min" ✓, woodies ל-"woodies_5min" ✓.)
**לא** atr, **לא** IB-timing, **לא** confidence.

## אפיון Michael (מחייב — מתקן את הלוגיקה)
day_type = **מסווג רציף ודינמי**: (א) הצבעה **מפתיחת RTH**; (ב) סוג-יום **ראשוני תוך 30 דק'**
(ביטחון עולה לאורך השעה); (ג) **משתנה לאורך היום** לפי השוק (לא נעילה-חד-פעמית); (ד) **מופץ
בזמן-אמת לכל המערכות**.

## ⚠️ ארכיטקטורה (אפיון Michael — מחייב)
S1 צורך **studies של Sierra ישירות** — **לא** מסנתז מ-5min. מקורות: **IB** מ-TPO/
previous_session export (`tpo_routes.py:197` "DLL emits previous_session.ib_high/ib_low") ·
**POC** מ-volume_profile · opening. **אסור לסנתז IB/POC מ-ברים** (CLAUDE.md Sierra=SoT).

## מה לעשות
1. **🔴 חוט S1 לצרוך את ה-studies הנכונים של Sierra → `process_bar`** — ה-root: `wrappers.py:44`
   S1 מנוי ל-`cumulative_delta`/`volume_profile`, אבל ה-dispatch (`on_bar_received`) של הזרמים
   האלה ל-`analyze()` **לא מחווט** (`bars.py:438` `_dispatch` הוא רק ל-S3) → `process_bar` רץ
   0 פעמים. **וגם** ה-IB מגיע מ-export אחר (TPO/previous_session), לא מ-cumulative_delta — אז
   ה-BarInput לא מקבל ib_high/ib_low. אבחן+תקן: (א) איזה study-stream נושא IB/POC/opening; (ב)
   חווט אותו ל-S1 (dispatch → analyze → process_bar) עם ה-BarInput מאוכלס מ-Sierra; **בלי 5min synthesis.**
   **אימות:** `bar_count` עולה מ-0 · `ib_high/ib_low` ב-BarInput = ערכי-Sierra (לא מחושב מ-ברים).
2. **🔴 הצבעה רציפה-מדורגת** — `state_machine.py`: הצבעת day_type **ראשונית מהפתיחה** (לא רק B1
   אחרי 60-דק'-IB; השתמש במבנה A1→C3 + `_check_reeval` הקיימים), ביטחון עולה, **re-eval רציף
   שמשנה** את הסוג, **בלי נעילה קשיחה**. **אימות:** day_type≠UNKNOWN תוך ~30 דק', ומשתנה כשהשוק משתנה.
3. **🔴 הפצה real-time** — סוג-היום העדכני (מקור-יחיד S1) → S2 day-patterns gate · Woodies A2 ·
   build_status · gateway, **בכל בר**. **אימות:** כל אלה מציגים את אותו day_type עדכני.

(הוסר: לא לגעת ב-`compliance_manifest.yaml` confidence — האפיון דורש 0.85, וזה לא-קשור לשורש.)

## VERIFY (raw output, Rule 5)
- `state_machine.py` מתקמפל (import עובר).
- `curl /api/v9/day_type/state` לאורך הסשן: bar_count עולה · day_type נקבע תוך ~30 דק' · משתנה דינמית.
- day_type זהה ב-S2/Woodies/build_status/gateway.
- **anti-tautological:** revert החיווט (סעיף 1) → day_type חוזר UNKNOWN (RED); עם החיווט → נקבע (GREEN).
- NOT-DONE: כל מה שנשאר.

**זה trading-logic לפי אפיון Michael — מאושר. עצור-אסטרטגי + VERIFY לפני שמכריזים תקין.**
