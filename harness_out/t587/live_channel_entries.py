# -*- coding: utf-8 -*-
"""fix-agent 18.10 — prepend the (late) night's two entries to LIVE_CHANNEL.md (idempotent)."""
import io, sys
P = "/Users/michael/Downloads/mems26_web_git/docs/handoff/LIVE_CHANNEL.md"
s = io.open(P, encoding="utf-8").read()
if "[fix-agent · T-589" in s:
    print("already applied"); sys.exit(0)

E1 = ("🔵 **[fix-agent · T-589 · 18.10 11:15 IL · BRIEF §2.2 #3 — היתר ZLR SHORT · Normal · 18–19h לבדו: Δ 0.00$ על 70 (אינרטי — ZLR פסוק לצל); שלב 2: הצל של ZLR מחזיק בשתי החזקות]**\n"
    "ריצת ליל 17→18.10 נורתה באיחור (09:55 — המק לא היה מחובר כל השבוע). וריאנט `config/decision_tree_v3.t587_allow.yaml` (`harness_out/t587/make_variant_zlr.py`, מתכון T-564b/T-579b: רק SKIP(location) של "
    "`responsive_normal→SHORT→zone near_val|mid_value` ⇒ TAKE ל-ZLR בשעה 18|19; 27/4,732 וקטורים משתנים, 0 מחוץ להקשר, 0 סחיפת-מדיניות). יום-שלם 10:03–10:23 על `harness_out/t586/sessions70.txt` מול ייחוס-אותו-לילה t567ref (3.4.0; "
    "השינוי היחיד בבאקנד מאז 08.10 — `bars.py` — אינו בנתיב ההרנס): **Δ 0.00$ · 0/0/70 · 0 עסקאות נוספו.** 27 TAKE ⇒ 0 עסקאות כי `ZLR_SHADOW_V1=1` (פסיקת 07.09 \"צל לשבוע\") מנתב כל ZLR לצל לפני השערים (`trading_gateway.py:803`); "
    "10/27 עברו את כל השערים ונותבו לצל, 17/27 נחסמו אחרי העץ (entry_not_confirmed 6 · extreme_chase_guard 6 · rr_entry_gate 3 · structural_targets_wrong_side 2). "
    "**שלב 2 (הזוג שמבודד את ההיתר, `run2.sh`):** t587s = לייב + `ZLR_SHADOW_V1=0` מול t567ref: **Δ −330.60$ ברוטו / −406.00$ נטו (+29 סיבובים) · 15/17/38 · החזקה-A (28.09–09.10) −26.25 · החזקה-B (10.09–25.09) −67.50 · 06 −11 · 07 +225 · 08 −201 · 09 −317 · 10 −26 · נוספו 58 (32 זכיות, +178.75) / הוסרו 29 (+509.35)** ⇒ הצל של ZLR **מחזיק בשתי החזקות עוקבות (§2.6)** — 50 עסקאות-ZLR חיות Σ +111 גולמי, אבל הן תופסות סלוט מעסקאות טובות יותר. "
    "t587sz = אותו דבר + ההיתר, מול t587s (ההיתר לבדו, מבודד): Δ +120.00$ / +117.40$ נטו · 2/1/67 · החזקות A/B 0 (N=0) · 07 +108 · 08 +12 — מזה +48.75 של 24.08 הוא דריפט-ייחוס מוכר (אין וקטור-היתר באותו יום) ⇒ ההיתר-נטו ≈ +71$ על N=2 (07.13 +107.50: ZLR SHORT 18:09 +50 דחק REACTIVE_LONG −57.50 · 08.31 −36.25) — עובר פורמלית רק על-גבי שחרור-הצל שנכשל; בלייב ZLR לא יורה. "
    "כלל-הקבלה: #3 אינרטי ⇒ לא עובר; שחרור-הצל לא עובר. **§2.2 נסגר** (#1 +121$ N=3 ממתין לכן/לא · #2 −105$ · #3 אינרטי) ⇒ הבא §2.3. דוח: `docs/reports/T589_ALLOW_ZLR_SHORT_NORMAL_1819_2026-10-18.md` · `harness_out/t587/run.out`, `run2.out`, `two_holdouts_t587s.out`. אפס נגיעה בלייב; pid 2030; ≤2 וריאנטים במקביל לצד התור של cowork (t586).\n\n")

E2 = ("🟠 **[fix-agent · T-527 · 18.10 11:15 IL · BRIEF §3.4 — `SIERRA_FLAT` בלי מחיר: 4/13 הן פקודות שמעולם לא בוצעו; `broker_truth` השמיט אותן — תוקן + 12 מבחנים; דגל-כבוי `POSITION_TRUTH_UNFILLED_CANCEL_V1`]**\n"
    "**הממצא (SELECT):** `SIERRA_FLAT 13/1/5`. ארבע (`571·955·979·1220`) עם `entry_ts NULL` ובלי `sierra_order_id`, אין ENTRY ביומן-ה-DLL ב-±3 דק׳, אין round-trip אצל הברוקר ⇒ POSITION_TRUTH סגר פקודה PENDING שסיירה מעולם לא החזיקה, והספרים קוראים לה עסקה לא-מתומחרת. "
    "**השורש של \"955/979/1220 נושרות\" (ריצה 174):** `scripts/broker_truth.py` סינן `entry_ts >= since` — NULL נשמט בשקט. **תוקן:** עוגן `coalesce(entry_ts, created_at)`, שורה כזו נרשמת `NEVER-FILLED` עם broker=None (לא מתומחרת); `main()`+פונקציות; וגם `KeyError` על יום-ידני-בלבד (הפיל את הריצה לפני `broker.json`). "
    "dry-run `--since 2026-09-01` (JSON ל-/tmp): 69 שורות זהות בייט-בייט, +6 נרשמות — ביניהן **`#3046` 05.10 GB100: ספרים −27.50 מול ברוקר +53.75 (Δ +81.25)**, שעד היום נספר כ-round-trip \"ידני\". "
    "**נבנה-כבוי** (`fill_poller.py`): PENDING-בלי-ack + סיירה שטוחה אחרי חסד ⇒ אותה סגירה `SIERRA_FLAT` עם `outcome CANCELLED` (תקדים P8) + `quality.never_filled`; pnl NULL (T-160); OFF זהה-בייט. 6+6 מבחנים חדשים + 12 קיימים ירוקים; flag_guard PASS 274; FLAG_REGISTRY. משלים את T-583 (ack/מילוי-פנטום ואז דחייה — לא נגע). "
    "`939/3140`: בוצעו ונסגרו ב-EOD אבל בזרם-הפעילות אין אירועים בחלונות שלהן (פער-סורק) ⇒ אין ממה לתמחר בכותב-היציאה. **פסיקות באינבוקס:** הדלקת הדגל; UPDATE ל-5 האפסים המסונתזים (SQL בדוח) — DB-write ע״י cowork/מייקל. "
    "§3.1 (T-259) דולג הלילה: דורש `launchctl` (חלון-שבת בלבד). דוח: `docs/reports/T527_SIERRA_FLAT_NEVER_FILLED_2026-10-18.md`.\n\n")

assert "{{" not in E1 + E2, "placeholders not filled"
io.open(P, "w", encoding="utf-8").write(E1 + E2 + s)
print("prepended 2 entries")
