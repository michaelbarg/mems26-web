# ניתוח עסקאות-שלא-בוצעו · 2026-07-17 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:23 CT** (`TZ=America/Chicago date` → `2026-07-17 15:23:14 CDT`, יום ו'; IL 23:23) ✓ — אחרי סגירת RTH 15:00. ריצה אוטונומית — Michael לא נוכח. **לא שונה קוד / flag / .env / DB (read-only).** API-חי דרך Chrome→localhost:8000 (המסחר עבר היום ל-MacBook הזה, S-15 → localhost נגיש, בניגוד ל-07-16 העיוור). **מקור-אמת ל-CCI+מחיר = Sierra woodies export** (הצלבה ל-CC למטה — קריטי היום).

> ⚠️ הערה תפעולית: `git pull` חסום מה-sandbox של cowork (SSH:22 forbidden, S-11) → עבדתי על מצב-הריפו המקומי. הדוח לא נדחף אוטומטית; להריץ `git add/commit/push` ידנית.

---

> 🔴🔴 **ממצא-העל #1 — DATA-QUALITY: פיד `bars5min` מושחת היום (I-40 חוזר בחומרה).** 8 ברים כפולים-בייט-לבייט (`12:05`=`11:05` · `12:35`=`11:35` · **כל הבלוק `14:20–14:50`=`13:20–13:50`**, כולל volume זהה) + **דה-סנכרון מתגלגל מול woodies** (ממוצע +8pt, עד **+32pt**, רק **10/44 close-match** מול 45/45 ב-07-13). **הפילים-האמת של סיירה מאמתים ש-woodies = האמת ו-`bars5min` שגוי** (עסקה 397 LONG e7529.75→T3 7539 ✅ תואם woodies c7534, סותר bars5min c7521-יורד). ⇒ **אין להשתמש ב-`bars5min` למחיר היום; כל הריפליי מעוגן ל-woodies+פילים.** → **הצלבה דחופה ל-CC** (משפחת I-40/I-47, roll-חוזה/dedup-buffer).

> 🟢 **ממצא-העל #2 — אפס פספוס-מגייט (קטגוריה ריקה, כמו 07-13).** `blocked_by=null` על כל 10 הירי · `/missed-trades count=0`. גייטי-chop OFF (standing 06-08). day_type=**Normal** (p=1.00, errors=[]). **אף setup תקף לא נחסם ע"י גייט** — התוצאה נקייה, לא כשל.

> 🔴 **ממצא-העל #3 — הכאב-האמת = ביצוע-לייב, לא פספוס. live net ≈ −$58.75 (2 ירי).** (א) **396 INITIATIVE_SHORT @09:55 live −$78.75** — שורט מוקדם-מדי, נעצר על גרינד-הבוקר-למעלה (7539@11:50) לפני שהיום ירד. (ב) **400 BEAR_FLAG_SHORT @13:10 live +$20 בלבד** — צדק בכיוון אבל נחתך ל-BE (I-22) בעוד **MFE=22pt** (רכב עד ~7486) → ~5R הושארו על השולחן. הכיוון-השורט של המערכת היה **נכון** — הניהול (BE-מוקדם) והתזמון (מוקדם-מדי בבוקר) אכלו את ה-R.

> 🔴 **ממצא-העל #4 — לונג-נגד-מגמה שוב הפסיד (I-41/I-50/I-67).** **403 REACTIVE_LONG @13:55 shadow −$86.25** (mae 24pt!) על `woodies_trend=RED`. תואם-בול את פער-פילטר-המגמה מ-07-13 (367/368) ומ-EOD-07-17 (`NORMAL_ROTATION_FIX_V1`). היום היחיד-שהפסיד-גדול בצד-הלונג ביום-יורד. → CC.

> 🟡 **ממצא-העל #5 — פספוס-אמת יחיד+קטן: רגל-הפריצה הראשונית 12:20→13:05.** woodies התהפך GRAY@12:20→RED@13:00, אך פלט **HFE-UP (נגד-מגמה) 13:00–13:45** ולא ZLR-DOWN-המשך עד **13:40**. הרגל 7534→7511 (12:05→13:00) לא-נותבה ב-S4. **אבל S2 BEAR_FLAG תפס אותה 10דק'-אחרי (13:10, 399/400)** ⇒ הפספוס-הנקי = ~23pt מקוצרים ב-~+2R, לא רגל-שלמה. שאר רגל-הירידה (13:10→14:25 שפל 7486) **נתפסה היטב** (399/400/401/402/404 כולם ניצחו ב-shadow).

> 🔴 **ממצא-העל #6 — R-artifacts + shadow↔live divergence נמשכים.** `pnl_r=42` על 395 ($52.5) · `pnl_r=22.5` על 399 · `pnl_r=16` על 400 ($20) — ניפוח-R מסטופ-מיקרו/נגרר (**I-22**). **395 shadow WIN +$52.5 מול 396 live LOSS −$78.75 על setup-זהה** (e7519.5/stop7525) + 395 `mfe=5.75` אך `t1_hit=true` (T1 10pt-רחוק) = **phantom-T1** (**I-58/I-64**). → CC.

## מקורות-אמת + כיסוי (הצלבה ל-CC) — **מקור-אמת = Sierra woodies + פילים**

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart` (limit=80) | **11:20→15:25 (50 ברים)** ✅ **SoT** | `source=sierra_woodies_5min_json` · `age_s=3` fresh · `stale=false`. trend BLUE(בוקר-bounce)→GRAY(12:20-12:55)→**RED**(13:00+). **מאומת מול פילים-אמת** (397/400/401/402/404 מחירי-כניסה תואמים woodies close ±). **מכסה 08:30–11:15? לא** — עיוורון-בוקר (I-60-adj). |
| `/api/v9/chart/bars5min` (limit=80) | 08:30→14:55 (78 ברים) **⚠️ מושחת** | TZ=+03:00(IL). **8 ברים כפולים + דה-סנכרון עד +32pt מול woodies+פילים** (ראה #1). `high 7539@10:50 · low 7484.5@14:10` **בלתי-אמינים** (זמנים-מוזזים). **לא-בשימוש למחיר.** → I-40 ל-CC. |
| `/api/v9/trades/recent` (limit=200→100) | **היום: 10 שורות** (388,395–404; חסר 398) | `limit=200` החזיר 100 (cap, I-25). **1 demo `ZLR LONG` @01:01 e7610.5 (overnight) — לא-רלוונטי.** **9 fires-RTH: 395–404. כולן `blocked_by=null`.** |
| `/api/v9/build/pattern-status` | live post-close | day_type=**Normal** p=1.00 · opening=**OPEN_TEST_DRIVE** · S4 trend=**RED** · `errors=[]` · woodies_5min **FRESH 0s** · S2 mode=OVERNIGHT_MODE (post-close). `readiness=READY`. |
| `/api/v9/missed-trades` | **count=0, candidates=[]** | 🟢 ריק — פער-persistence נמשך (I-60, כמו 07-08/09/13). blocked/shadow לא-נשמרים. |

**הצלבת-מקורות (Rule 2 ✓):** overlap woodies↔bars5min = **10/44 close-match בלבד** (מול 45/45 ב-07-13) ⇒ **פיד-שבור, לא feed-נקי.** ההכרעה עם-פילים: עסקה **397 LONG @11:45 e7529.75, T1/T2/T3=7535/7536.5/7539 כולם ✅** — תואם woodies (11:45 c7534.25, 11:50 c7534.5) וסותר bars5min (11:45 c7521 יורד ל-7514). **⇒ woodies=SoT, bars5min=מושחת.** **⚠️ ל-CC: לאמת ב-Sierra v9_export אם bars5min ו-woodies על אותו חוזה/chart; משפחת I-40 (roll/dedup).**

## מבנה-היום (RTH, מעוגן woodies+פילים · bars5min מושחת ⇒ בוקר בלתי-ניתן-לאימות)

open ~**7529.5@08:30** → chop/bounce-בוקר (שורט-לייב 396 @09:55 e7519.5 נעצר) → **שיא 7539@~10:50–11:50** (woodies-verified 11:50) → **פריצה-למטה 12:20** (BLUE→GRAY cci−15→−200 @12:20–12:50 → RED@13:00) → גרינד-יורד 13:00→**שפל-יום 7486.25@14:25** (woodies-RTH) → bounce-נעילה ל-~7490 (15:00 woodies c7490). **יום-Normal/יורד** (נטו ~−40 open→close, נעילה מעל השפל). day_type=**Normal** (p=1.00). ⚠️ `day_type` דיווח `ib_low=session_low=7473` — **לא-מאומת** (woodies-RTH low=7486.25; bars5min-low מושחת) — ל-CC (חשד ערך-IB stale/Globex).

## עסקאות-שירתו היום (הקשר — ירו, לא-פוספסו · ground-truth trades/recent · כולן `blocked_by=null`)

| id | זמן(CT) | תבנית | מער' | כיוון | entry | stop(risk) | תוצאה | mfe(pt) | mode | trend | הערה |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 395 | 09:55 | INITIATIVE_SHORT | S2 | SHORT | 7519.5 | 7525 (5.5) | **WIN** T1 | 5.75 | shadow | GRAY | ⚠️ `pnl_r=42`/$52.5 · **mfe 5.75 < T1(10pt) אך t1_hit=true** = phantom-T1 (I-58). |
| **396** | 09:55 | INITIATIVE_SHORT | S2 | SHORT | 7519.5 | 7525 (5.5) | **LOSS −$78.75** STOP@7524.75 | — | **live** | GRAY | 🔴 **live-מפסיד** — שורט מוקדם-מדי, נעצר על גרינד-בוקר-למעלה 7539. **היפוך-תוצאה מול 395** (I-64/I-65). |
| 397 | 11:45 | ZLR | S4 | LONG | 7529.75 | 7524.5 (5.25) | **WIN** T1/T2/T3 ✅ | — | shadow | BLUE | 🟢 לונג-bounce מנצח +$106.25. **עוגן-האימות ל-woodies=SoT.** |
| 399 | 13:10 | BEAR_FLAG_SHORT | S2 | SHORT | 7508.25 | 7512 (3.75) | **WIN** T1+T2 | 22 | shadow | RED | 🟢 עם-המגמה. `pnl_r=22.5`. |
| **400** | 13:10 | BEAR_FLAG_SHORT | S2 | SHORT | 7508.25 | 7512 (3.75) | **WIN +$20** (BE@7508) | **22** | **live** | RED | 🟢 **live-מנצח-זעיר** — נחתך ל-BE (I-22) בעוד MFE 22pt → ~5R הושארו. `pnl_r=16`. |
| 401 | 13:35 | ZLR | S4 | SHORT | 7501.75 | 7507.5 (5.75) | **WIN** T1 | 10.5 | shadow | RED | 🟢 עם-המגמה. |
| 402 | 13:40 | ZLR | S4 | SHORT | 7500.25 | 7505.5 (5.25) | **WIN** T1 | 1.75 | shadow | RED | 🟢 עם-המגמה (ZLR-DOWN woodies 13:40). |
| **403** | 13:55 | REACTIVE_LONG | S2 | 🔴LONG | 7511 | 7505.25 (5.75) | **LOSS −$86.25** STOP | 0 | shadow | **RED** | 🔴 **לונג-נגד-מגמה** (mae 24pt). I-41/I-50/I-67. |
| 404 | 14:10 | ZLR | S4 | SHORT | 7499.25 | 7505.5 (6.25) | **WIN** T1+T2 (BE) | 13 | shadow | RED | 🟢 עם-המגמה, ZLR-DOWN cci−188. רכב לשפל אך נחתך ל-BE. |
| 388 | 01:01 | ZLR | S4 | LONG | 7610.5 | 7602.5 | BE (manual) | — | demo | — | overnight demo — לא-נספר. |

**Σ fires-אמת:** **live n=2 → net ≈ −$58.75** (396 −$78.75 · 400 +$20). **shadow: 6 shorts (5 ניצחו, עם-המגמה) + 1 long-bounce (397 +$106) + 1 long-נגד-מגמה (403 −$86 הפסיד).** **הכיוון-השורט נתפס ונכון; ההפסד-הלייב = תזמון(396)+ניהול-BE(400)+לונג-נגד-מגמה(403).**

## טבלת setups-שלא-בוצעו — lookback מתגלגל 6-ברים (08:30→15:00 CT)

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay) | gate-שחסם (reject_reason/blocked_by) | I-# |
|---|---|---|---|---|---|---|---|---|---|
| 08:30–11:15 | (בוקר) | S2/S4 | ⚠️ **בלתי-ניתן-לאימות** | — | — | — | **woodies-blind + bars5min-מושחת** (Rule 1: propagate "missing") | עיוורון-בוקר + פיד-שבור | I-60-adj / **I-40** |
| **12:25–13:05** | **breakdown-cont SHORT** (7534→7511, BLUE→RED) | **S4** | ⚠️ woodies פלט **HFE-UP** (נגד-מגמה) 13:00–13:45, **לא** ZLR-DOWN עד 13:40 | ~7511 | 7521 (10) | T1✓ · T2✓ | **🟡 +2R** (7534→שפל 7486) — **אך S2 BEAR_FLAG תפס 13:10 (399/400)** ⇒ פספוס-נקי ~23pt/~+2R בלבד | **detection-lag S4** (HFE-UP במקום ZLR-DOWN); S2 REACTIVE_SHORT `Missing: data.mode_context`* | I-3(חשד)/**mode_context** |
| 13:40 | ZLR-DOWN cont-SHORT | S4 | ✅ `zlr=DOWN` cci−101 c7497 | 7500.25 | 7505.5 | T1✓ | **נותב (402), WIN** | `blocked_by=null` (ירה) | — |
| 14:00/14:05 | ZLR-DOWN cont-SHORT | S4 | ✅ `zlr=DOWN` cci−3/−75 | ~7499 | 7505 | — | **מכוסה ע"י 404 (14:10)** — אותה רגל, לא-מצטבר | לא-נותב-בנפרד (dedup תקין) | — (נכון) |
| 14:10 | ZLR-DOWN cont-SHORT | S4 | ✅ `zlr=DOWN` cci−188 c7492.5 | 7499.25 | 7505.5 | T1✓T2✓ | **נותב (404), WIN** (רכב לשפל 7486, נחתך ל-BE) | `blocked_by=null` (ירה) | I-22(ניהול) |
| 14:35 | ZLR-DOWN cont-SHORT | S4 | ✅ `zlr=DOWN` cci−56 c7493.5 | 7493.5 | 7499 | — | **~0R** — המחיר כבר בשפל (7486); bounce-נעילה ל-7505 מיד | לא-נותב (סוף-רגל, מוצדק) | — (נכון) |
| 15:00/15:05 | ZLR-DOWN | S4 | ✅ post-close | — | — | — | **overnight — לא-routable ב-RTH** | מחוץ-לחלון | — |

**ΣR-נגד (replay מבני, deduped, מעוגן-woodies):**
- **🟡 פספוס-גייט-אמת יחיד = 12:25–13:05** (~+2R): S4 detection-lag (HFE-UP במקום ZLR-DOWN) על רגל-הפריצה הראשונית, **אך S2 BEAR_FLAG תפס 10דק'-אחרי (13:10)** ⇒ הפספוס-הנקי קטן (~23pt מקוצרים). חשד-משני: S2 REACTIVE_SHORT `Missing: data.mode_context`*.
- **🟢 שאר רגל-הירידה (13:10→שפל 7486) נתפסה היטב** — 399/400/401/402/404 כולם WIN (shadow). 14:00/14:05/14:35 = זנב-אותה-רגל (dedup תקין, אי-נתוב מוצדק).
- **⚠️ בוקר 08:30–11:15 = בלתי-ניתן-לאימות** (blind+corrupt) — Rule 1: "missing", לא-מסונתז.
- ⇒ **ΣR-נגד (missed-גייט אמת) ≈ +2R גרוס** (רגל-אחת, פספוס-חלקי-קצר). **הכאב-האמת היום איננו ב-missed** אלא ב-(1) פיד-מושחת (I-40), (2) ביצוע-לייב (396 מוקדם −$78.75 · 400 BE-מוקדם −5R-give-back), (3) לונג-נגד-מגמה (403 −$86).

*`Missing: data.mode_context` נקרא **post-close** (S2 ב-OVERNIGHT_MODE כרגע) — **לא ניתן לייחס בוודאות ל-RTH.** → CC לאמת אם `mode_context` היה None בזמן-אמת (אם כן — REACTIVE_SHORT נחסם בפריצה = פספוס-גייט אמת).

## 🎯 BENCHMARK — 5 הסלוטים של Michael (template יום-יורד 06-05) מול היום

היום **יום-Normal/יורד** (open 7529.5→שיא 7539@11:50→שפל 7486@14:25→נעל ~7490) ⇒ **תזת-שורט תקפה**, אך **הירידה היתה אחה"צ-כבדה** (הבוקר היה bounce ל-7539), בעוד סלוטי-ה-benchmark כולם 08:30–10:00:

| # | סלוט(CT) | סוג(template) | מה קרה בפועל | תקף היום? | המערכת | הערכה |
|---|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2) | בוקר chop/bounce — ההיפוך-למטה האמת ~12:20 | 🟡 מוקדם ב-~4ש' | blind(woodies) + bars5min-מושחת | בלתי-ניתן-לאימות |
| 2 | 9:00 | LONG טקטי | מחיר ~7508–7516 (bounce מאוחר יותר) | 🟡 long-bounce תקף רק ב-11:45 (397 +$106) | blind | נתפס-מאוחר (397) |
| 3 | 9:20 | SHORT | 09:55 INITIATIVE_SHORT ירה (395/396) | ✅ כיוון-נכון, **תזמון מוקדם** | ירה 09:55 | **396 live הפסיד** (−$78.75, מוקדם) |
| 4 | 9:35 | SHORT | אותו fire 09:55 | ✅ כיוון-נכון, מוקדם | ירה 09:55 | 396 live הפסיד |
| 5 | 10:00 | SHORT | הבוקר עלה ל-7539@11:50 → ירידה רק אחה"צ | ❌ **מוקדם-מדי** (שורט 10:00 היה נעצר) | blind | הירידה-האמת 13:00+ (נתפסה 399–404) |

**שורת-benchmark: 0/5 אותרו-בזמן-המדויק** (בוקר = woodies-blind + bars5min-מושחת + הירידה אחה"צ-כבדה). **הכיוון-השורט תקף** אך **הסלוטים מוקדמים ב-~3ש'** — היום הבוקר היה bounce (7539), לא down-leg; **השורט-הלייב היחיד בבוקר (396 @09:55) הפסיד דווקא כי היה מוקדם.** ⇒ **K/5 = 0/5 בזמן-מדויק · 2/5 (9:20/9:35) כיוון-תקף-אך-מוקדם-והפסיד-לייב · 1/5 (10:00) לא-תקף (מוקדם) · 2/5 (8:35/9:00) בלתי-ניתן-לאימות.** ה-benchmark **לא חשף פער-גייט חדש** — הפער היום = פיד-מושחת + תזמון-לייב + לונג-נגד-מגמה.

## פירוק לפי gate

| gate | #setups | סטטוס |
|---|---|---|
| **🟢 choppiness (S2 `choppiness_ok` / Layer-0)** | **0** | **OFF** (standing 06-08). לא חסם דבר. |
| **🟢 sizing / A5 (aux_count)** | 0 | 0 חסימות. |
| **🟢 A1-veto / trend_state** | 0 | 0 חסימות. trend נכון RED. |
| **🟢 day_type** | 0 | **Normal** p=1.00 (endpoint חי, errors=[]). |
| **🟢 opening / FHB** | 0 | OPEN_TEST_DRIVE מסווג; 0 חסימות. |
| **🟡 S4 detection-lag (HFE-UP במקום ZLR-DOWN בפריצה)** | 1 רגל (12:25–13:05, ~+2R) | הפספוס-החלקי-היחיד. S2 BEAR_FLAG תפס 10דק'-אחרי ⇒ עלות קטנה. |
| **🔬 S2 `Missing: data.mode_context`** | (post-close read) | REACTIVE_SHORT + 5 תבניות-S2 חסומות **כרגע** (OVERNIGHT_MODE). **לא-מיוחס-ל-RTH** — → CC לאמת. |
| **🔴 I-40 — `bars5min` מושחת (dup-blocks + desync)** | פיד-כולו | **החומרה-#1 היום.** 8 ברים כפולים + עד +32pt דה-סנכרון. woodies+פילים = SoT. → CC (roll/dedup-buffer). |
| **🔴 I-41/I-50/I-67 — לונג-נגד-מגמה (403)** | 1 fire (−$86.25) | פער-פילטר-מגמה — REACTIVE_LONG על RED. תואם EOD-07-17 (`NORMAL_ROTATION_FIX_V1`). → CC. |
| **🔴 I-22 — R-artifact + BE-מוקדם** | 3 (395/399/400) + ניהול-400/404 | `pnl_r` 42/22.5/16 מסטופ-מיקרו/נגרר; **400 live נחתך ל-BE בעוד MFE 22pt.** → CC. |
| **🔴 I-58/I-64 — shadow↔live divergence** | 395↔396 | setup-זהה: shadow WIN $52.5 מול live LOSS −$78.75 + phantom-T1 (mfe 5.75<T1). → CC. |
| **🟡 I-60 — missed-store ריק** | 0 | `/missed-trades count=0`. blocked/shadow לא-persisted. נמשך. |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🟢 גייטים-נקיים (תוקן eve, נמשך):** `blocked_by=null` על כל 9 הירי-RTH; chop-gates OFF עובד-כמתוכנן; day_type=Normal חי (I-1 סגור). **קטגוריית פספוס-מגייט ריקה שוב.**
- **🟢 כיוון-שורט נתפס:** 5/6 שורטי-shadow ניצחו (עם-המגמה); רגל-הירידה 13:10→7486 נתפסה היטב.
- **🔴 חדש-חמור: I-40 חוזר** — `bars5min` מושחת (dup-blocks + desync). היה 🟡 display-נקי לאחרונה (07-08) → **🔴 שוב.** → CC.
- **🔴 נמשך: לונג-נגד-מגמה (403 −$86)** — I-41/I-50/I-67. `NORMAL_ROTATION_FIX_V1` (EOD-07-17) נועד לזה; לוודא שתפס.
- **🔴 נמשך: I-22 (R-artifact + BE-מוקדם)** · **I-58/I-64 (shadow↔live divergence 395/396)** · **I-60 (store-ריק)** · **עיוורון-בוקר (I-60-adj)**.

## נטיפיקציה ל-Michael
**🔴🔴 DATA: פיד `bars5min` מושחת היום (I-40 חוזר) — 8 ברים כפולים-בייט-לבייט + דה-סנכרון עד +32pt מול woodies. פילים-אמת מאשרים woodies=SoT, bars5min שגוי. הצלבה דחופה ל-CC.**
**🟢 אפס פספוס-מגייט: `blocked_by=null` על כל 9 הירי · `/missed-trades count=0` · day_type=Normal · chop-gates OFF. הגייטים לא חסמו כלום.**
**🔴 הכאב = ביצוע-לייב, לא פספוס: live net ≈ −$58.75 (396 INITIATIVE_SHORT @09:55 מוקדם −$78.75 · 400 BEAR_FLAG @13:10 נחתך ל-BE +$20 בעוד MFE 22pt). + 403 REACTIVE_LONG @13:55 נגד-מגמה −$86 (shadow, I-41/50/67).**
**🟡 פספוס-אמת יחיד+קטן: רגל-פריצה 12:25–13:05 (S4 פלט HFE-UP במקום ZLR-DOWN) — אך S2 BEAR_FLAG תפס 10דק'-אחרי. ΣR-נגד ≈ +2R (רגל-אחת, חלקי).**
**⚠️ R-artifacts (395/399/400 = I-22) + shadow↔live divergence (395↔396 = I-58/64). benchmark 0/5 בזמן-מדויק (בוקר blind+corrupt, הירידה אחה"צ-כבדה); כיוון-שורט תקף אך סלוטים מוקדמים ב-~3ש'. לא שונה קוד.**

---
*נוצר אוטונומית ע"י Cowork (15:23 CT, 2026-07-17). מאומת-תוכניתית (Rule 2/5): woodies=SoT אומת ע"י פילים-אמת (397 LONG e7529.75→T3 7539 תואם woodies c7534, סותר bars5min c7521) · bars5min מושחת: 8 dup-bars (12:05=11:05·12:35=11:35·14:20–14:50=13:20–13:50) + overlap 10/44 close-match בלבד (מול 45/45 ב-07-13), desync avg+8/max+32pt · woodies-RTH struct: first 11:20 / hi 7539@11:50 / lo 7486.25@14:25 / lastRTH 15:00 c7490 · trend BLUE→GRAY(12:20)→RED(13:00) · ZLR-UP @11:35/40/45,12:00/05/25 · ZLR-DOWN @13:40,14:00/05/10/35,15:00/05(overnight) · HFE-UP @13:00–13:45(נגד-מגמה) · fires-אמת 9-RTH: 395 S2-INIT-SHORT 09:55 WIN-shadow(phantom-T1) · 396 S2-INIT-SHORT 09:55 −$78.75 LIVE-LOSS · 397 S4-ZLR-LONG 11:45 +$106 shadow(bounce) · 399 S2-BEAR_FLAG 13:10 WIN shadow · 400 S2-BEAR_FLAG 13:10 +$20 LIVE(BE,mfe22) · 401 S4-ZLR-SHORT 13:35 WIN · 402 S4-ZLR-SHORT 13:40 WIN · 403 S2-REACTIVE-LONG 13:55 −$86.25 shadow(נגד-מגמה RED) · 404 S4-ZLR-SHORT 14:10 WIN(BE,mfe13) · +388 demo overnight · pattern-status day_type=Normal p=1.00 errors=[] woodies_5min FRESH 0s readiness=READY · missed-store count=0. TZ: woodies=UTC(ts_unix) · bars5min/trades=+03:00(IL,−8→CT). **לא שונה קוד/flag/.env/DB.***
