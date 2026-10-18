# -*- coding: utf-8 -*-
"""fix-agent 18.10 — TASK_LOG edits for the (late) night 17→18.10: T-589 row after T-584, T-527 next-step cell, header line.
Idempotent: refuses to apply twice."""
import io, sys
P = "/Users/michael/Downloads/mems26_web_git/docs/plans/TASK_LOG.md"
s = io.open(P, encoding="utf-8").read()
if "| T-589 |" in s:
    print("already applied"); sys.exit(0)

ROW_T587 = ("| T-589 | 🔵 **היתר ZLR SHORT ביום Normal 18:00–19:59 בתוך-הערך — BRIEF §2.2 #3, לבדו (fix-agent, ריצת ליל 17→18.10 שנורתה באיחור ב-18.10 09:55; המק לא היה מחובר כל השבוע).** "
    "וריאנט `config/decision_tree_v3.t587_allow.yaml` (`harness_out/t587/make_variant_zlr.py`, מ-3.4.0, מתכון T-564b/T-579b: רק SKIP(`location`) של `responsive_normal→SHORT→zone near_val|mid_value` הופך ל-TAKE ל-pattern=ZLR בשעה 18|19, יציאה ברירת-מחדל; "
    "27 וקטורים מתוך 4,732 של t567ref משתנים, 0 מחוץ להקשר, 0 סחיפת-מדיניות). **נמדד יום-שלם 10:03–10:23 על 70 (67 + 07/08/09.10) מול ייחוס-אותו-לילה t567ref (3.4.0): Δ 0.00$ ברוטו/נטו · 0 / 0 / 70 · 0 עסקאות נוספו ⇒ אינרטי.** "
    "הסיבה: `ZLR_SHADOW_V1=1` (פסיקת 07.09 \"צל לשבוע, מתקנים ולא מבטלים\" — 6 שבועות) מנתב כל ZLR לצל ב-`trading_gateway.py:803` לפני השערים; בייחוס אפס עסקאות-ZLR חיות; 10/27 הווקטורים עברו את כל השערים ונותבו לצל, 17/27 נחסמו גם אחרי העץ (entry_not_confirmed 6 · extreme_chase_guard 6 · rr_entry_gate 3 · structural_targets_wrong_side 2). "
    "**שלב 2 (`run2.sh`, 10:25–11:05) — הזוג שמבודד את ההיתר בלי הצל:** t587s = לייב + `ZLR_SHADOW_V1=0` מול t567ref: **Δ −330.60$ / −406.00$ נטו (+29 סיבובים) · 15/17/38 · החזקה-A (28.09–09.10) −26.25 · החזקה-B (10.09–25.09) −67.50 · 07 +225 · 08 −201 · 09 −317 · נוספו 58 (+178.75) / הוסרו 29 (+509.35) ⇒ הצל של ZLR מחזיק בשתי החזקות (§2.6)**; "
    "t587sz = + ההיתר, מול t587s (ההיתר לבדו): Δ +120.00$ / +117.40$ נטו · 2/1/67 · החזקה A/B 0 (N=0) · 07 +108 · 08 +12 — מזה +48.75 של 24.08 הוא דריפט-ייחוס (אין וקטור-היתר) ⇒ ההיתר-נטו ≈ +71$ על N=2 (07.13 +107.50 · 08.31 −36.25) — עובר פורמלית רק על-גבי שחרור-הצל שנכשל. "
    "מזהה: T-589 (תג-ההרנס t587* הוקצה 10:03; cowork-dev לקח T-587 ב-10:18). דוח: `docs/reports/T589_ALLOW_ZLR_SHORT_NORMAL_1819_2026-10-18.md`. "
    "| 🔵 נמדד · אינרטי תחת ZLR_SHADOW_V1 | fix-agent | **אין פסיקה** (#3 אינרטי; הצל מחזיק: −406$ נטו, A −26 · B −68). הקובץ נשאר וריאנט-מדידה בלבד (`DECISION_TREE_V3_PATH` בהרנס). §2.2 נסגר (#1 ממתין לכן/לא, #2 לא, #3 אינרטי) ⇒ הבא בתור §2.3 (יציאות אחרי +1R, שלושה וריאנטים לבד). |\n")

T527_ADD = (" **עדכון 18.10 10:5x IL fix-agent (BRIEF §3.4 — שורש + מבחן, ממתין לאימות/פסיקה):** (א) **השורש של \"955/979/1220 נושרות\":** `entry_ts` NULL (פקודה PENDING בלי submit-ack ש-POSITION_TRUTH סגר כ-SIERRA_FLAT — מעולם לא בוצעה: אין ENTRY ביומן-ה-DLL ב-±3 דק׳, אין round-trip אצל הברוקר) ו-`broker_truth` סינן `entry_ts >= since` ⇒ נשמטה בשקט. 4 מ-13 ה-`SIERRA_FLAT` (571·955·979·1220) הן כניסות שלא קרו. "
    "**תוקן** `scripts/broker_truth.py`: עוגן `coalesce(entry_ts, created_at)` (+ `main()`/פונקציות), שורה כזו נרשמת `NEVER-FILLED` עם broker=None; גם `KeyError` על יום-ידני-בלבד (הפיל את הריצה לפני `broker.json`, `--since 2026-08-25`) תוקן. dry-run `--since 2026-09-01`: 69 שורות זהות בייט-בייט, +6 נרשמות (955·979·1220·1337·2038·**3046** — ספרים −27.50 מול ברוקר +53.75, Δ +81.25, היה \"ידני\"). 6 מבחנים `tests/v9/regression/test_t527_broker_truth_candidates.py`. "
    "(ב) **נבנה-כבוי** `POSITION_TRUTH_UNFILLED_CANCEL_V1` (`fill_poller.py`): PENDING-בלי-ack + סיירה שטוחה ⇒ אותה סגירה SIERRA_FLAT עם `outcome CANCELLED` (תקדים P8) + `quality.never_filled`; pnl נשאר NULL; OFF זהה-בייט; 6 מבחנים `test_t527_unfilled_cancel.py` + 12 קיימים; flag_guard PASS 274; FLAG_REGISTRY. משלים את [[T-583]] (המקרה עם ack/מילוי-פנטום ואז דחייה — לא נגע). "
    "(ג) 939/3140 בוצעו ונסגרו ב-EOD אבל בזרם-הפעילות אין אירועים בחלונות שלהן (פער-סורק) ⇒ אין ממה לתמחר בכותב-היציאה; המספר היחיד = הפרש `acct_daily_pl` — מנגנון נפרד, לא נבנה. **פסיקות באינבוקס:** הדלקת הדגל; UPDATE ל-5 האפסים המסונתזים (548·571·708·744·820 ⇒ NULL/UNPRICED, SQL בדוח) — DB-write ע״י cowork/מייקל. דוח: `docs/reports/T527_SIERRA_FLAT_NEVER_FILLED_2026-10-18.md`.")

HEADER = ("**עודכן:** 2026-10-18 11:15 IL fix-agent — **ריצת ליל 17→18.10, נורתה באיחור ב-09:55 (המק לא היה מחובר כל השבוע; BRIEF §2.2 #3 + §3.4):** "
    "T-589 היתר ZLR SHORT/Normal/18–19h לבדו, יום-שלם על 70 מול t567ref: Δ 0.00$ — אינרטי, `ZLR_SHADOW_V1=1` מנתב כל ZLR לצל (27 TAKE ⇒ 0 עסקאות); שלב 2: שחרור-הצל (`ZLR_SHADOW_V1=0`) −406$ נטו, החזקה-A −26 · החזקה-B −68 ⇒ הצל של ZLR מחזיק בשתי החזקות (§2.6); ההיתר מבודד על-גביו ≈ +71$ על N=2 — אין פסיקה; §2.2 נסגר ⇒ הבא §2.3 · "
    "T-527 שורש: 4/13 `SIERRA_FLAT` הן פקודות שלא בוצעו (entry_ts NULL) ו-`broker_truth` השמיט אותן (`entry_ts >= since`) — תוקן + 12 מבחנים; דגל-כבוי `POSITION_TRUTH_UNFILLED_CANCEL_V1` (CANCELLED במקום UNPRICED, OFF זהה-בייט); `#3046` ספרים −27.50 מול ברוקר +53.75 נחשף; flag_guard PASS 274 · "
    "§3.1 (T-259) דולג: דורש `launchctl` — מחוץ לסמכות ביום-חול, חלון-שבת בלבד. pid 2030 לאורך הריצה; אפס נגיעה ב-.env/RULED_FLAGS/עץ-חי/DB/ריסטארט; ההרנס לצד התור של cowork (t586, ≤2 במקביל), מחוץ ל-RTH (יום ראשון).\n\n")

lines = s.split("\n")
out = []; done_row = done_527 = done_hdr = False
for ln in lines:
    if not done_hdr and ln.startswith("**מקרא:**"):
        out.append(ln); out.append(""); out.append(HEADER.rstrip("\n")); done_hdr = True; continue
    if ln.startswith("| T-527 |") and not done_527:
        assert ln.rstrip().endswith("|"); ln = ln.rstrip()[:-1].rstrip() + T527_ADD + " |"; done_527 = True
    out.append(ln)
    if ln.startswith("| T-584 |") and not done_row:
        out.append(ROW_T587.rstrip("\n")); done_row = True
assert done_row and done_527 and done_hdr, (done_row, done_527, done_hdr)
assert "{{" not in ROW_T587 + HEADER, "placeholders not filled"
io.open(P, "w", encoding="utf-8").write("\n".join(out))
print("applied: header, T-589 row after T-584, T-527 cell")
