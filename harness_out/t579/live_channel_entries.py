# -*- coding: utf-8 -*-
"""fix-agent 09.10 — prepend the night's LIVE_CHANNEL entries (two items). Idempotent."""
import io, sys
P = "/Users/michael/Downloads/mems26_web_git/docs/handoff/LIVE_CHANNEL.md"
s = io.open(P, encoding="utf-8").read()
if "[fix-agent · T-579 ·" in s:
    print("already applied"); sys.exit(0)

E1 = ("🔵 **[fix-agent · T-579 · 09.10 00:35 IL · BRIEF §2.2 #2 — היתר REACTIVE_SHORT · Variation · 18–19h לבדו: נמדד יום-שלם, לא עולה]** "
    "וריאנט `config/decision_tree_v3.t579b_allow.yaml` (מתכון T-564b: רק `against` SKIP→TAKE; 13 וקטורים מתוך 4,520 של t567ref, 0 מחוץ להקשר, 0 סחיפה) "
    "מול ייחוס-אותו-לילה **t567ref** (3.4.0, 67 סשנים, במקביל לתור של cowork): **Δ −100.00$ ברוטו / −105.20$ נטו · 1/1/65 · החזקה-10 Δ 0 (N=0) · "
    "06 −118 · 07 +18 · 08/09/10 0 · +4 (2 זכיות, −3.75) / −2 (+96.25) ⇒ לא עובר §2ד; אין פסיקה.** "
    "06.15 −117.50: REACTIVE_SHORT 19:40 נעצר (−23.75) ותפס את הסלוט מ-CEILING_FLIP_SHORT 19:50 (+78.75 בייחוס); 07.21 +17.50. 11/13 וקטורים לא הפכו לעסקה. "
    "t567a של cowork (החבילה) נפל על אותו 06.15. ההיתר-לפי-תבנית אינו סימטרי: INITIATIVE_SHORT לבדו +121$ (אמש), REACTIVE_SHORT לבדו −105$. "
    "הבא: §2.2 #3 ZLR SHORT · Normal · 18–19h לבדו. דוח `docs/reports/T579_ALLOW_REACTIVE_SHORT_VAR_1819_2026-10-09.md` · פלט `harness_out/t579/run.out`.\n\n")

E2 = ("🟠 **[fix-agent · T-532/T-265 · 09.10 00:35 IL · BRIEF §3.3 — \"ייצוא-RTH תקוע על שישי\": תוקן בשורש, 31 מבחנים, ממתין לאימות בריסטארט הבא]** "
    "**הממצא:** S1 (`_day_type_on_bar`) ו-S2 מנויים רק לנושא `'5min'` = `POST /bars/5min` = הלגאסי `5min.json`; הקנוני מגיע אליהם רק דרך ה-failover של 14.08, "
    "ששואל \"הערוץ הגולמי דחף לאחרונה?\" — והקובץ התקוע **נדחף** כל ~4ש׳ (mtime טרי, תוכן קפוא; השער מעביר אצווה לא-מתקדמת \"pass but logged\" — ראיה: הלוג 08.10 16:29:58), "
    "`_record_push(\"5min\")` נרשם ללא תנאי ⇒ בריאות \"טרי\", failover שותק, `_route_bar` חוסם את הבר ⇒ S1/S2 בלי אף בר והמסך חי. אותו מעקב-מחיר לקח סגירת-שישי ⇒ רצועת-המחיר מול מחיר בן 65ש׳ (נעילה על פער). "
    "**התיקון (`bars.py`):** דחיפה נספרת רק עם בר טרי (≤900ש׳) או מחוץ ל-RTH (`market_clock`, חסד 15 דק׳ אחרי הפתיחה); מעקב-המחיר זז רק מבר טרי; הרצועה נבדקת רק מול מעקב טרי. "
    "**`fire_drill`:** `cme_globex_open` + `feed_price_line` — שוק סגור ⇒ שתי שורות-ה-feed מידע-בלבד (לא NO-GO בחלון-שבת; הדריל המלא ב-00:06 = הפסקה יומית: שתי ℹ, GO). "
    "זהה-בייט בכל דחיפת-RTH בריאה ובכל שעה מחוץ ל-RTH (FAILOVER בלוג 02–08.10: 489, אפס בתוך 16:30–23:00). flag_guard PASS 274. "
    "לא שוחזר חי בלוגים של השבוע — מאומת במבחן על המנגנון. פתוח לתור: S2 hydration מלגאסי-תקוע, S1 `pd_close` מלגאסי-בלבד (דגל+מדידה). "
    "`tests/v9/api/test_bars_woodies_routing.py` נכשל 2 גם ב-HEAD (קדם ל-failover) — לא שלי. דוח `docs/reports/T265_T532_RAW_5MIN_CANONICAL_FAILOVER_2026-10-09.md`.\n\n")

io.open(P, "w", encoding="utf-8").write(E1 + E2 + s)
print("prepended 2 entries")
