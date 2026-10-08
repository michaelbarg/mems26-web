# -*- coding: utf-8 -*-
"""fix-agent 09.10 — TASK_LOG edits for the night (T-579 row, T-532/T-265 next-step cells, header line).
Idempotent: refuses to apply twice."""
import io, sys
P = "/Users/michael/Downloads/mems26_web_git/docs/plans/TASK_LOG.md"
s = io.open(P, encoding="utf-8").read()
if "| T-579 |" in s:
    print("already applied"); sys.exit(0)

ROW_T579 = ("| T-579 | 🔵 **היתר REACTIVE_SHORT ביום Variation 18:00–19:59 נגד-ההינט — BRIEF §2.2 #2, לבדו (fix-agent ליל 08→09.10).** "
    "וריאנט `config/decision_tree_v3.t579b_allow.yaml` (`harness_out/t579/make_variant_reactive.py`, מ-3.4.0, אותו מתכון של T-564b: רק `against` SKIP→TAKE, "
    "יציאה ברירת-מחדל; 13 וקטורים מתוך 4,520 של t567ref משתנים, 0 מחוץ להקשר, 0 סחיפת-מדיניות; 12 מהם בשעה 19). "
    "**נמדד יום-שלם 23:45–00:00 על 67 מול ייחוס-אותו-לילה t567ref (3.4.0): Δ −100.00$ ברוטו / −105.20$ נטו · טוב 1 / רע 1 / זהה 65 · "
    "החזקה-10 Δ 0 (N=0) · חודשים 06 −118 · 07 +18 · 08/09/10 0 · נוספו 4 (2 זכיות, −3.75) / הוסרו 2 (+96.25) ⇒ לא עובר §2ד.** "
    "06.15 −117.50: REACTIVE_SHORT 19:40 @7640.75 (סטופ 4.75 נק׳) נעצר 20:25 ותפס את הסלוט מ-CEILING_FLIP_SHORT 19:50 (+78.75 בייחוס); 07.21 +17.50 (החליף DT +17.50 ב-+35). "
    "11 מ-13 הווקטורים לא הפכו לעסקה ביום-השלם (סלוט/שערים) — אותו פער כמו ב-T-564 (כיול +40$/מועמד ⇒ 2 ירו). "
    "t567a של cowork (החבילה REACTIVE+INITIATIVE+ZLR, כל שלב C) נפל על אותו יום 06.15 (−93.75). דוח: `docs/reports/T579_ALLOW_REACTIVE_SHORT_VAR_1819_2026-10-09.md`. "
    "| 🔵 נמדד · לא עולה | fix-agent | **אין פסיקה** (נופל על Δנטו ועל יוני; N=2 ימים). הבא בתור §2.2 #3: ZLR SHORT · Normal · 18–19h לבדו (אותו מתכון, לילה הבא). "
    "הקובץ נשאר וריאנט-מדידה בלבד (`DECISION_TREE_V3_PATH` בהרנס). |\n")

T532_ADD = (" **עדכון 09.10 00:35 IL fix-agent (BRIEF §3.3 — תיקון-שורש, ממתין לאימות):** המשפחה \"ייצוא טרי ≠ פיד חי\" נסגרה בקוד: "
    "`bars.py` — דחיפת `/5min` נספרת לבריאות-הזרם רק אם סיפקה בר טרי (≤`BAR5_RAW_STALE_SEC`=900ש׳) או מחוץ ל-RTH (`_raw_5min_push_counts`, חסד 15 דק׳ אחרי 09:30 ET), "
    "מעקב-המחיר זז רק מבר טרי, ורצועת-המחיר נבדקת רק מול מעקב טרי (`_tracker_is_fresh`) ⇒ ייצוא תקוע-על-שישי בתוך RTH מיישן את `'5min'` (המדד צועק) "
    "וה-failover של woodies (14.08) מזין את S1/S2 מהקנוני אחרי 120ש׳; `fire_drill` — `cme_globex_open` + `feed_price_line`: שוק סגור ⇒ שתי שורות-ה-feed מידע-בלבד (לא NO-GO בחלון-שבת). "
    "31 מבחנים ירוקים (`tests/v9/regression/test_t265_raw_5min_push_counts.py`, `test_t265_fire_drill_closed_market.py`), flag_guard PASS 274, דריל מלא GO בהפסקה היומית. "
    "זהה-בייט בכל דחיפת-RTH בריאה ומחוץ ל-RTH; נכנס לתוקף בריסטארט הבא. לא שוחזר חי בלוגים של 02–08.10 (05.10 התאוששה לפני הפתיחה) — מאומת במבחן על המנגנון. "
    "ממצאים פתוחים לתור: S2 hydration מלגאסי-תקוע (ריק≠תקוע, `five_min_system.py:462`), S1 `pd_close` מלגאסי-בלבד (`prev_day.py`; משרת גם את ההרנס ⇒ דגל+מדידה). "
    "דוח: `docs/reports/T265_T532_RAW_5MIN_CANONICAL_FAILOVER_2026-10-09.md`.")

T265_ADD = (" **09.10 fix-agent:** המשפחה טופלה בשורש תחת [[T-532]] (ספירת-דחיפה לפי בר-טרי + failover קנוני ל-S1/S2 + דריל מודע-שוק; "
    "07.09 היה Labor Day — השער דחה כדין) — דוח `docs/reports/T265_T532_RAW_5MIN_CANONICAL_FAILOVER_2026-10-09.md`; נשאר בארכיון.")

HEADER = ("**עודכן:** 2026-10-09 00:35 IL fix-agent — **ליל 08→09.10 (BRIEF §2.2 #2 + §3.3):** T-579 היתר REACTIVE_SHORT/Variation/18–19h לבדו נמדד יום-שלם מול t567ref: "
    "Δ −105.20$ נטו · 06 −118 · החזקה N=0 ⇒ לא עולה, אין פסיקה · T-532/T-265 תיקון-שורש (`bars.py`: דחיפת-`/5min` נספרת רק עם בר-טרי/מחוץ-ל-RTH, מעקב-מחיר ורצועה טריים-בלבד ⇒ "
    "failover קנוני ל-S1/S2; `fire_drill`: לא מכריז feed ישן על שוק סגור), 31 מבחנים, flag_guard PASS, ממתין לאימות בריסטארט הבא · "
    "אימות-צולב לתור-הלילה של cowork (`harness_out/t579/crosscheck.out`) ושורות-פסיקה ל-08:30 באינבוקס. pid 85469 לאורך הריצה; אפס נגיעה בלייב.\n\n")

lines = s.split("\n")
out = []; done_571 = done_532 = done_265 = done_hdr = False
for i, ln in enumerate(lines):
    if not done_hdr and ln.startswith("**מקרא:**"):
        out.append(ln); out.append(""); out.append(HEADER.rstrip("\n")); done_hdr = True; continue
    if ln.startswith("| T-532 |") and not done_532:
        assert ln.rstrip().endswith("|"); ln = ln.rstrip()[:-1].rstrip() + T532_ADD + " |"; done_532 = True
    if ln.startswith("| T-265 |") and not done_265:
        assert ln.rstrip().endswith("|"); ln = ln.rstrip()[:-1].rstrip() + T265_ADD + " |"; done_265 = True
    out.append(ln)
    if ln.startswith("| T-571 |") and not done_571:
        out.append(ROW_T579.rstrip("\n")); done_571 = True
assert done_571 and done_532 and done_265 and done_hdr, (done_571, done_532, done_265, done_hdr)
io.open(P, "w", encoding="utf-8").write("\n".join(out))
print("applied: header, T-579 row after T-571, T-532 + T-265 cells")
