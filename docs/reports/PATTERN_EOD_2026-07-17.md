# MEMS26 · דוח EOD מאוחד — 2026-07-17 (יום שישי · **יום-LIVE-אמת על ה-MacBook** · Normal · רוטציה-סוערת)

**שער-זמן (I-9):** ✅ הופק אחרי-הסגירה — בעת-הריצה **15:12 CT** (≥15:00 CT; אומת `TZ=America/Chicago date` → `2026-07-17 15:12:49 CDT`; IL 23:12 IDT; `/api/v9/health` → `status=ok`). RTH מלא (08:30–14:55 CT, **78 ברי-5דק'**, `bars_last_ts=2026-07-17 22:55 IL` = 14:55 CT). ה-feed **בריא וטרי** (בריפינג-בוקר: `sierra.writing=true`, age 0.1–0.9s).

**מקורות:** (1) API חי דרך Chrome (`http://localhost:8000`): `/trades/recent?limit=100` → **10 עסקאות-היום (ids 388,395–404)** · `/chart/bars5min?limit=500` → 362 ברים (78 RTH-היום) · `/gateway/decisions` · `/gateway/status` · `/day_type/current` · `/woodies/signals`+`/patterns` · `/footprint/journal` · `/missed-trades` · `/veto/state` · `/layer0/state`. (2) **`docs/reports/OPS_LOG_2026-07-17.md`** — לוג-התפעול-החי של היום (271 שורות; מקור-האמת ל-block-reasons + תקריות). (3) שני האודיטים של-היום: **`PATTERN_MGMT_AUDIT_2026-07-17.md`** (A1–A7) + **`PATTERN_MISS_AUDIT_2026-07-17.md`** (F1–F5). (4) בריפינג-בוקר `briefings/BRIEF_2026-07-17.md`.

> ⚠️ **אין `PATTERN_DIAG_2026-07-17.md`** (סוכן-snapshots-30דק' מושבת מאז 06-10) ⇒ ספירת-`נדרכה#`-מלאה לא-זמינה. הטבלה נבנתה מ-**10-העסקאות-שנורו + 44 חסימות-gateway מתועדות ב-OPS_LOG + counterfactual-חי של `missed_watch`**. זמנים ב-CT (=IL−8=ET−1). **שום קוד/flag/.env/DB לא-שונה בריצה זו — read-only EOD.**

---

## כותרות-על

> **🔴🔴 כותרת-על #1 — תקרית-בטיחות-חיה, לא-נפתרה: פוזיציית-שורט −5 עירומה (ללא-סטופ) על החשבון-האמת 37138283 דרך סגירת-שישי.** מקור = **S-13 (כניסה-עירומה-לסירוגין)**. `session-watch` תיעד 7 ריצות-הסלמה (13→14→15→16→17 + flatten-2215-check): `sierra_qty=−5 · working_orders=0 (אין סטופ) · tm_open=0/tm_net_qty=0 · is_sim=0/armed=1`. הרשומות-הפנימיות מראות **שטוח**, בעוד הברוקר מחזיק −5 → **סגירות-פיקטיביות מדליפות חוזים** (#400 נרשם `CLOSED WIN +$20` בעוד סיירה −5). מייקל התבקש **7 פעמים** לפתוח Sierra → לאמת −5 → `FLATTEN_ACCOUNT` או סטופ-ידני. **תוצר-לוואי מאומת:** #398 (live ZLR LONG 11:45) נכשל `ORDER_FAILED:−1` כי היתום תפס-את-החשבון — הצל-shadow #397 ניצח +$106.25 שה-live לא-קיבל. **זו הבעיה #1 (כסף-אמת, סיכון-סוף-שבוע).** → I-68.

> **🔴 כותרת-על #2 — I-22 (ניפוח-R) חזר עם ראיה-מתמטית-ניצחת + חשוד-אחות I-65 (אופטימיות-shadow תוך-בר).** טווח-היום כולו **54.5pt** (H 7539 / L 7484.5) ⇒ ה-R-המקסימלי-האפשרי על שורט מ-~7519 הוא **~6.4R**. ובכל-זאת: #395 רשם **R=42**, #399 **R=22.5**, #400 **R=16** — **בלתי-אפשריים פיזיקלית**. הצלבה שנייה: #400 (live) `pnl_r=16` אך `pnl_usd=+$20` (~4pt ≈ +1R) ו-`gateway.daily_pnl=−58.75` על 2 עסקאות-live → **`pnl_usd` אמין, `pnl_r` מנופח**. השורש (כמו 07-13): R מחולק ב-stop-הנגרר במקום ב-stop_initial. **בנוסף (I-65, חדש-נקי):** #395(shadow) ניצח +$52.5 על אותו-סיגנל בדיוק ש-#396(live) הפסיד עליו −$78.75 — כי ה-shadow-sim **התעלם מסדר-התוך-בר**: הסטופ 7525 נגע ב-10:55 (בר-כניסה H=7536.5, live נעצר תוך-43-שניות), וה-T1 (7513.75) הגיע רק ב-11:05 — ה-shadow זיכה את-ה-T1-המאוחר והתעלם מהסטופ-שקדם-לו. **זה מסביר את-כל-הפער shadow(+$277.5) מול live(−$58.75).** → I-22 + I-65.

> **🟠 כותרת-על #3 — פספוס-הבוקר (F1–F5) + over-fire של INITIATIVE על Normal (A5) — שני-צדדים של אותו-מטבע-כיול.** ה-detectors פספסו את-ראלי-הפתיחה (+~54pt ORR long אל IB_H 7539) — **`missed +54pt ORR long` תועד ב-OPS_LOG 09:11 CT**; מייקל לקח +27pt ידנית על אותו-גרף. השורש (PATTERN_MISS_AUDIT): הקריטריונים מכוילים לטרנד-מבוסס-צבוע (BLUE-lag ~6 ברים, ZLR 6-blue, GB100 fresh-cross, S2 B2 מול ממוצע-לילה-מורעל) — ביום-גאפ הראלי נגמר לפני-שהם-מבשילים. **בצד-השני:** ה-*יחיד* ש-כן-ירה-חי בבוקר, #396 INITIATIVE_SHORT, ירה **על-Normal-בגודל-מלא בניגוד ל-verdict LOCKED `INITIATIVE×Normal=SKIP`** (A5: `OFA_Initiative` לא-מתמפה ל-`INITIATIVE` באות-table → "using max" → FULL) — ונעצר תוך-43-שניות (−$78.75). **A5 עלה כסף-אמת היום.** → I-69 + A1/A3/F-cluster (audit docs).

> **🟢 כותרת-על #4 — הכיוון-של-אחה"צ היה נכון: 4 שורטי-אחה"צ (S4 ZLR + S2 BEAR_FLAG) תפסו את-הירידה 7539→7484.5.** #399/#400 (BEAR_FLAG 13:10), #401/#402 (ZLR 13:35/13:40), #404 (ZLR 14:10) — כולם שורטים-מנצחים-אמיתיים ברגל-היורדת אל שפל-היום 7484.5. shadow-נטו +$277.5 (6W/1L) · **live-נטו −$58.75** (הפער = הבוקר-שפספס/A5 + היתום). המפסיד-היחיד-בשורט: אין; המפסיד = #403 (REACTIVE_LONG 13:55, לונג-נגד-מגמה, −$86.25, מוצדק).

---

## מצב-היום

**צורת-יום (78 ברים, feed בריא):** פתיחה **7529.5** (08:30 CT) → **ראלי-פתיחה** אל **IB_H / שיא-יום 7539** (~+54pt מעל שפל-הפרה-RTH ~7485; = ה"ORR long" שפוספס) → **היפוך + רוטציה-יורדת-סוערת** כל-אחה"צ דרך 7525→7508→7500 → **שפל-יום 7484.5** (~14:35 CT) → נעילה **7496.75** (14:55 CT). **טווח 54.5pt · נטו −32.75pt** (open→close). **Day-type = Normal** (conf 100, override `DAY_TYPE_MANUAL_OVERRIDE=2026-07-17:Normal`), **IB 7473–7539 (רוחב 66 = EXTREME)**, stage C3, `opening_type=OPEN_TEST_DRIVE`. `layer0.chop=22/FOUND` (לא-צ'ופ; שערי-chop מושבתים ממילא). 10 העסקאות: 2 בוקר (INITIATIVE_SHORT over-fire + ZLR-LONG שנכשל-place) · 8 אחה"צ (7 שורט + 1 לונג-נגד-מגמה).

| CT | O | H | L | C | הערה |
|----|---|---|---|---|------|
| 08:30 | 7529.5 | 7539 | 7522 | 7534 | פתיחה · IB מתחיל |
| ~08:45–09:20 | | **7539** | | | **ראלי-ORR (+~54pt) → IB_H — פוספס (F1–F5)** |
| 09:55 | 7526.5 | **7536.5** | 7525.25 | 7534 | **#395/#396 entry INITIATIVE_SHORT 7519.5 (A5 over-fire) → live stop 43s @7524.75** |
| 10:05 | 7534.5 | 7537 | 7517.25 | 7521 | #395(shadow) T1 מאוחר @7513.75 (11:05) |
| 11:45 | | | | | **#397/#398 entry ZLR LONG 7529.75 · #398(live) ORDER_FAILED (יתום) · #397(shadow) +$106.25** |
| 13:10 | | | | | **#399/#400 entry BEAR_FLAG_SHORT 7508.25 → WIN (שניהם)** |
| 13:35–14:10 | | | | | **#401/#402/#404 ZLR_SHORT — 3 שורטים-מנצחים ברגל-היורדת** |
| 13:55 | | | | | **#403 REACTIVE_LONG 7511 → STOP −$86.25 (לונג-נגד-מגמה, מוצדק)** |
| ~14:35 | — | — | **7484.5** | — | **שפל-יום** (כיוון-שורט אומת) |
| 14:55 | — | — | — | **7496.75** | **נעילה** (נטו −32.75pt) |

**Snapshots post-close (15:1x CT):**
- `/gateway/status`: `trades_today=2 · daily_pnl=−$58.75` (**מונים-חיים** — תואם בדיוק #396 −78.75 + #400 +20; **I-23 ממשיך-תקין**) · `shadow_active_count=5` · `live_enabled_systems=[2,4]` · `demo_enabled=[]` (**I-62 נמשך**) · `cooldown.consecutive_stops=6` (לא-פעיל) · `cluster_guard.recent_attempts=1` (לא-פעיל) · `chop_state=FOUND`.
- `/day_type/current`: `Normal · conf 100 · B2/C3 · IB 7473–7539 (EXTREME) · opening OPEN_TEST_DRIVE · source=v9`. תוויות **סבירות** (ראלי-פתיחה + רוטציה).
- `/woodies`: `trend=RED · cci_14=−92.08 · classification=NO_SETUP` · **20 signals היום** (ZLR/SHORT×14, GB100/SHORT×3, FAMIR/LONG×2, ZLR/LONG×1).
- `/footprint/journal`: **20 רשומות, כולן `NO_SETUP`** (S3 מושתק — **I-11**, צפוי).
- `/missed-trades`: **count=0, candidates=[]** — ⚠️ ה-endpoint-הזה **ריק** למרות ש-`missed_watch` ב-OPS_LOG תיעד 20 missed-winners. **פער-endpoint** (ה-buffer של `/gateway/decisions` הוא in-memory-since-restart, 22 רשומות בלבד) → הצד-האמין לחסימות-היום הוא **OPS_LOG**, לא ה-endpoint.

---

## 1. עסקאות שנורו היום — 10 (7 shadow · 2 live · 1 demo-poison)

⚠️ **#388 (demo, ZLR LONG, פרה-RTH ~01:01 CT, exit 7610.5 = מחיר-אתמול, `ex_reason=manual`, R=0/BE)** = **דמו-הרעל-הפרה-פתיחה** ש-HOTFIX-2 (10:04 CT) תיקן ("pre-open demo poisoned replay → classifier blind all session"; `_entry_gap` עכשיו RTH-trades-only). **לא-נספר כסיגנל.**

| id | mode | מ' | תבנית | כיוון | CT-in | entry | stopI (1R) | exit | exit_reason | תוצאה | USD | R-**רשום** | R-**אמת** (הערכה) |
|----|------|-----|-------|-------|-------|-------|-----------|------|-------------|--------|-----|-----------|--------------------|
| 396 | **live** | S2 | INITIATIVE_SHORT | SHORT | 09:55 | 7519.5 | 7525 (5.5) | 7524.75 | `STOP_HIT` (43s) | **LOSS** | **−78.75** | −0.72 | **−1** |
| 395 | shadow | S2 | INITIATIVE_SHORT | SHORT | 09:55 | 7519.5 | 7525 (5.5) | 7519.25 | `STOP_HIT` | WIN⚠ | +52.5 | **42** ⚠ | **−1** (סטופ-נגע-ראשון תוך-בר) |
| 398 | **live** | S4 | ZLR | LONG | 11:45 | 7529.75 | 7524.5 (5.25) | — | `ORDER_FAILED:−1` (יתום) | BE | 0 | 0 | **0** (נכשל-place) |
| 397 | shadow | S4 | ZLR | LONG | 11:45 | 7529.75 | 7524.5 (5.25) | 7529.75 | `STOP_HIT` (post-T3) | **WIN** | +106.25 | 1.01 | **~+1.7** (H 7539) |
| 400 | **live** | S2 | BEAR_FLAG_SHORT | SHORT | 13:10 | 7508.25 | 7512 (3.75) | 7508 | `STOP_HIT` (post-T1) | **WIN** | +20 | **16** ⚠ | **~+1** |
| 399 | shadow | S2 | BEAR_FLAG_SHORT | SHORT | 13:10 | 7508.25 | 7512 (3.75) | 7508 | `STOP_HIT` (post-T2) | **WIN** | +56.25 | **22.5** ⚠ | **~+1.5** |
| 401 | shadow | S4 | ZLR | SHORT | 13:35 | 7501.75 | 7507.5 (5.75) | 7501.75 | `STOP_HIT` (post-T1) | WIN | +28.75 | 0.25 | **~+0.5** |
| 402 | shadow | S4 | ZLR | SHORT | 13:40 | 7500.25 | 7505.5 (5.25) | 7500.25 | `STOP_HIT` (post-T1) | WIN | +26.25 | 0.25 | **~+0.5** |
| 403 | shadow | S2 | REACTIVE_LONG | LONG | 13:55 | 7511 | 7505.25 (5.75) | 7505.25 | `STOP_HIT` | **LOSS** | −86.25 | −0.75 | **−1** (לונג-נגד-מגמה, מוצדק) |
| 404 | shadow | S4 | ZLR | SHORT | 14:10 | 7499.25 | 7505.5 (6.25) | 7499.25 | `STOP_HIT` (post-T2) | WIN | +93.75 | 0.75 | **~+1.5** |

**כלכלה (מ-`pnl_usd`, המדד-האמין):** **live נטו −$58.75** (#396 −78.75 · #398 0 · #400 +20 = מאשר `gateway.daily_pnl`) · **shadow נטו +$277.5** (6W/1L). ⚠️ **`ΣR-רשום`=חסר-משמעות** (I-22: 42+22.5+16 בלתי-אפשריים). **`ΣR-אמת` (הערכה, honest intrabar):** live ≈ **−1R** (#396 −1 · #398 0 · #400 +1) · shadow ≈ **+3R** (אילו #395 מתוקן ל-−1R לפי סדר-תוך-בר). **הפרש live↔shadow = I-65 (אופטימיות-sim).**

**הערות פר-עסקה:**
- **#396/#395 (INITIATIVE_SHORT, 09:55) — A5 over-fire + I-65:** INITIATIVE ירה על-Normal-בגודל-מלא (A5: `INITIATIVE×Normal=SKIP` עוקף). #396(live) נעצר **תוך-43-שניות** @7524.75 (בר-כניסה H=7536.5 — המחיר זינק-מעלה-מיד). #395(shadow) "ניצח" +$52.5 ע"י זיכוי-T1-מאוחר (7513.75 @11:05) תוך התעלמות-מהסטופ-שקדם. **אותו-סיגנל, +$52.5 מול −$78.75.** → I-69 (A5) + I-65 (sim).
- **#398/#397 (ZLR LONG, 11:45) — יתום חוסם-live:** #398(live) `ORDER_FAILED:−1` — היתום −3 תפס-את-החשבון. הצל #397(shadow) T1/T2/T3-fill (12:50–52) → +$106.25. **ה-live פספס winner-אמת בגלל היתום (I-68).**
- **#399/#400 (BEAR_FLAG_SHORT, 13:10):** שניהם WIN-אמת ברגל-היורדת (מחיר נפל 7508→7484.5). shadow/live **הסכימו-כיוונית** (ניגוד-מרענן ל-#395/#396). ⚠️ R-רשום מנופח (22.5/16).
- **#401/#402/#404 (ZLR_SHORT, אחה"צ):** 3 שורטי-המשך-מנצחים ברגל-היורדת אל 7484.5. small-real wins (+$28.75/+26.25/+93.75).
- **#403 (REACTIVE_LONG, 13:55):** לונג-נגד-המגמה-היורדת; נעצר −$86.25. **הפסד-מוצדק** (כיוון-שגוי). שער-המשפחה לא-סינן לונג-נגד-מגמה (I-41/I-50-inv, נמשך).
- **כל 10 היציאות = `STOP_HIT`** (סטופ-נגרר) — אף עסקה לא-נסגרה ב-target-exit או timeout. דפוס-ניהול (attached-OCO trailing).

---

## 2. טבלת תבניות — נדרכה / נורתה / לא-נורתה / תחזית-נגד

*(אין DIAG intraday ⇒ `נדרכה#` = signals-log של `/woodies/signals` + חסימות-OPS_LOG. `נורתה#` = 10-העסקאות. `לא-נורתה#` = 44 חסימות-gateway-מתועדות + counterfactual-חי של `missed_watch`.)*

| מערכת | תבנית | נדרכה # | נורתה # | לא-נדרכה # (סיבות) | לא-נורתה # (פירוק סיבות-דחייה) | תחזית-נגד: W/L, ΣR |
|-------|-------|---------|---------|-------------------|------------------------------|--------------------|
| **S2** | INITIATIVE_SHORT | ≥1 | **2** (395/396) | — | 1× `cont_trend_filter` (09:35, "היה מפסיד −6.75") | **1W/1L** (shadow/live סתרו) · **live −1R** (A5 over-fire) |
| **S2** | REACTIVE_SHORT | ≥5 | 0 | — | 5× (`daytype_playbook`×1, `location_gate`×2, `rr_entry_gate`×2) | מעורב: 1 missed-winner (+4.75pt @11:35) · 4 מוצדקים |
| **S2** | REACTIVE_LONG | ≥6 | **1** (403) | — | ≥6× `location_gate` | 403 **−1** (מוצדק) · CF: 3 missed-winner (+4–5pt) / 3 מוצדק |
| **S2** | BEAR_FLAG_SHORT | 1 | **2** (399/400) | — | — | **2W** · ~+1 to +1.5R (רגל-יורדת) |
| **S2** | FLAGS(BULL)/HNS/DBDT | 0 | 0 | לא-נדרכו | — | ⚪ לא-נצפו |
| **S4** | ZLR (SHORT) | **14** (signals) | **4** (401/402/404 + #388-poison) | — | רוב-ה-14: `cont_trend_filter`/`daytype_playbook`/`rr_entry_gate`/`eod_cutoff`/`session_closed` | **3W-אמת** אחה"צ · CF: `cont_trend` 4miss/4right |
| **S4** | ZLR (LONG) | 1 (signal) + פירי-בוקר | **1** (397/398) | — | ≥8× `rr_entry_gate` (בוקר, ראלי) | 397 **~+1.7R**; #398 נכשל. CF: `rr_gate` 6miss/8right |
| **S4** | GB100 (SHORT) | **3** (signals) | 0 | — | לא-נותב (fresh-cross-only, F4) | ⚪ פוספס-מבנית (F1/F4) |
| **S4** | FAMIR (LONG) | **2** (signals) | 0 | — | 1× `eod_entry_cutoff` (15:30) | ⚪ מאוחר/נגד-מגמה |
| **S4** | GHOST (L/S) | ≥8 (blocks) | 0 | — | `location_gate`×רבים + `entry_not_confirmed`×2 | **I-67 נמשך** · CF: 2 missed-winner (+4–6.75pt) · רוב מוצדק |
| **S4** | TLB/TT/HTLB/HFE | 0 | 0 | לא-נורו | — | ⚪ תואם-יום |
| **S3** | ABS/STACK/SWEEP/EXH | 0 | 0 | **muted (I-11)** — 20/20 NO_SETUP | — | ⚪ מחוץ-לסקופ |
| **S1** | Day Type | — | Normal(override) | — | — | 🟡 machine≠override (A6) |

**סיכום-ספירה:** **10 עסקאות נורו** (7 shadow + 2 live + 1 demo-poison); **6 WIN-shadow / 1 LOSS-shadow · 1 WIN-live / 1 LOSS-live / 1 FAILED-live.** **44 חסימות-gateway מתועדות** (ראה §3). **20 signals-Woodies** (רק 4 ZLR נותבו). **ΣR-רשום מנופח (I-22) — לא-בשימוש; live-נטו −$58.75, shadow-נטו +$277.5 (מנופח ע"י I-65).**

---

## 3. תחזית-נגד (counterfactual) — פירוק-שערים + החזרת-ברים

**מקור-על:** ה-supervisor `missed_watch` **כבר חישב counterfactual-חי** לכל-חסימה (סף: `T1eq +4.0pt` = "missed-winner" · `STOPeq −6.0pt` = "gate-right/מוצדק", חלון 45דק'). סיכום-EOD שלו (OPS_LOG 16:21 ET):

| gate | חסימות (tracked) | 🔴 missed-winner (+4pt) | ✅ מוצדק (−6pt) | הערכה |
|------|-----------------|------------------------|----------------|--------|
| **rr_entry_gate** | 14 | **6** | 8 | ~break-even; חסם לונגי-בוקר בראלי + שורטי-אחה"צ |
| **location_gate** | 12 | **6** | 6 | 50/50; חסם REACTIVE_LONG-בוקר (קשור A1) + GHOST |
| **cont_trend_filter** | 8 | **4** | 4 | 50/50; חסם INITIATIVE_SHORT-בוקר + ZLR-אחה"צ |
| **daytype_playbook** | 7 | **2** | 5 | רוב-מוצדק |
| **entry_not_confirmed** | 3 | **2** | 1 | 2/3 missed (GHOST +4/+6.75pt) |
| **Σ tracked** | **44** | **20** | **24** | ~**איזון** (חסך-הפסדים כמעט-כמו שפספס-מנצחים) |
| eod_entry_cutoff | ~7 | 0 | (כולם נכונים — אחרי-cutoff) | ✅ מוצדק |
| session_gate_closed | ~5 | 0 | (RTH נסגר) | ✅ מוצדק |

**קריאה קריטית (Rule 2 — לא-לקבל את-הסף כפשוטו):** סף ה-`+4pt=winner` הוא **נדיב** — כמעט-כל-ה-missed-winners הגיעו ל-**+4 עד +6pt בלבד** (≈T1/~1R) ואז התהפכו ברוטציה-הסוערת (טווח-יום 54.5pt, שני-כיווני). ⇒ הפספוסים הם **T1-scalp-misses**, לא runners-גדולים. הצירוף **20-פספסו / 24-חסך-הפסד** אומר ש-`rr_entry_gate`/`location_gate`/`cont_trend_filter` היו **~break-even ולא מרשיעים באופן-חד** — הם חסכו כמעט-כמה-הפסדים שהחמיצו-מנצחים. **החריג המשמעותי היחיד = הבוקר:** הראלי +54pt (F1–F5) לא-הגיע-כלל-לשער (פספוס-detector, לא פספוס-gate), ובמקביל ה-longs-שכן-הגיעו נחסמו ב-`location_gate`/`rr_entry_gate` (קשור A1 — Normal לא-בפטור-ה-fade).

**החזרת-ברים על 3 העסקאות-הקריטיות (honest intrabar, 1R=|entry−stopI|):**

| id | כיוון | entry | stopI | 1R | סדר-תוך-בר בפועל | תוצאה-אמת | R-רשום | Δ (I-22/I-65) |
|----|-------|-------|-------|-----|-------------------|-----------|--------|----------------|
| 396 | SHORT | 7519.5 | 7525 | 5.5 | ↑7536.5 (סטופ נגע 10:55:43) ثم↓7513.75 (11:05) | **STOP −1** ✓ | −0.72 | — (live=נכון) |
| 395 | SHORT | 7519.5 | 7525 | 5.5 | זהה (סטופ קדם ל-T1) | **STOP −1** (אך נרשם WIN) | **42** | **−43** (I-65 sim + I-22 R) |
| 400 | SHORT | 7508.25 | 7512 | 3.75 | ↓ל-7484.5 (רגל-יורדת) | **~+1R** (usd +$20) | **16** | **−15** (I-22 R) |

**קביעה:** **live ΣR-אמת ≈ −1R** (−$58.75) · **shadow ΣR-אמת ≈ +3R** (אחרי-תיקון #395), **לא +$277.5/ΣR-מנופח.** הכיוון-של-אחה"צ (שורט) היה **נכון** — 4 שורטי-אחה"צ תפסו את-7539→7484.5. הבעיה: (א) **הבוקר-פוספס** (F1–F5 + A1) · (ב) **A5 over-fire** נתן את-ההפסד-החי-היחיד · (ג) **היתום** מנע את-ה-live-long-המנצח (#398). **החסימות עצמן ~מאוזנות** — אין "דחייה-שמרנית-מדי" חד-משמעית; יש **פספוס-detector-בבוקר** (upstream של השערים).

---

## 4. לקחים

- **הבטיחות-החיה קודמת-לכל: פוזיציה −5 עירומה על-כסף-אמת דרך-שישי היא הבעיה #1** (I-68 / S-13). היא לא-תבנית ולא-כיול — היא **דליפת-חוזים-לברוקר עם ledger-שקרי** (#400 "סגור +20" מול Sierra −5). דורש reconciler-שמשטח-אוטומטית (C3) + חסימת-entry-כשיש-חוסר-התאמה. **עד-שזה-נסגר, כל מדד-P&L-פנימי לא-אמין** (ה−$58.75 לא-כולל את-~$270-האמת של-השורט-הידני/היתום).
- **I-22 (R-חשבונאות) עדיין חוסם כל מדידת-ביצועים.** טווח-יום 54.5pt ⇒ max ~6.4R, אך נרשמו 42/22.5/16. `pnl_usd` אמין (`daily_pnl=−58.75` תואם), `pnl_r` לא. **ב-LIVE זה מעוות sizing/risk מבוסס-R** — תנאי-קדם למדידה. תיקון: חלק ב-`stop_initial`, אכוף `sign(pnl_r)==sign(pnl_usd)`.
- **I-65 (אופטימיות-shadow תוך-בר) — הוכחה-נקייה היום.** #395(shadow +$52.5) מול #396(live −$78.75) על-אותו-סיגנל: ה-sim זיכה T1-מאוחר והתעלם-מהסטופ-שקדם-לו תוך-בר. **ה-shadow-book (+$277.5) מנופח שיטתית** — לא-להסיק ממנו win-rate. תיקון: ב-sim, כשגם-סטופ-וגם-target בחלון — לכבד את-סדר-הברים (stop-before-target).
- **פספוס-הבוקר (F1–F5) הוא upstream-של-השערים.** הראלי +54pt לא-הגיע-לשער-כלל — ה-detectors מכוילים לטרנד-מבוסס-צבוע. מייקל לקח +27pt ידנית. 8 הצעות-דירוג בפרומפט (GB100-GRAY-opening, S2-RVOL-session, ZLR-S1.1-6→3, ...) — **כולן דגל-OFF, דורשות ריצת-`audit_pattern_miss.py` על-ה-Mac + פסיקת-Michael.**
- **A5 (INITIATIVE over-fire על Normal) עלה כסף-אמת.** ה-verdict LOCKED `INITIATIVE×Normal=SKIP` נעקף (auth-key `OFA_Initiative`≠`INITIATIVE`) → #396 ירה-מלא-ונעצר −$78.75. **תיקון = הקטנת-ירי** (risk-surface, דורש-Michael).
- **הכיוון-של-אחה"צ צדק — והשורטים-האמיתיים ניצחו.** ברגע-שהמגמה-נצבעה (RED), S4-ZLR + S2-BEAR_FLAG תפסו את-7539→7484.5. הצד-הטכני-של-האחה"צ בריא.
- **החסימות ~מאוזנות (20-פספסו/24-חסך) — אל-תרדוף-אחרי-כל-פספוס.** הסף +4pt נדיב; רוב-הפספוסים היו T1-scalps שהתהפכו. אין ראיה חד-משמעית ש-`rr_entry_gate`/`location_gate` שמרניים-מדי — הם ~break-even ביום-רוטציה-סוער.
- **אל-תסיק מ-n-קטן.** 10 עסקאות, יום-אחד, יום-LIVE-ראשון-על-MacBook עם 4 hotfixes-חיים במהלכו. I-68/I-22/I-65/A5 הם **ודאיים** (בטיחות/שחיתות-נתונים/קוד); ה-gate-calibration הוא n≤14 פר-שער.

---

## 5. מקור-אמת — דורש הצלבת CC מול Sierra v9_export / DB / לוג (Rule 2/5)

1. **🔴🔴 I-68 (יתום-עירום S-13):** לפתוח Sierra → לאמת `position_qty=−5 / working_orders=0 / avg~7502.7` על 37138283 → `FLATTEN_ACCOUNT` או סטופ-ידני; לתקן ledger #400 (CLOSED→פתוח). לחלץ שורש `reconcile.py` (C1/C3: למה ORDER_SUBMITTED=stop-ok; למה streak-pinned-0/3-לא-משטח). **חוסם-LIVE.**
2. **🔴 I-22 (R-חשבונאות):** לחלץ נוסחת-`pnl_r` (write-path `v9_trades`/gateway) — לאשר חלוקה ב-stop-נגרר; לתקן ל-`stop_initial` + לאכוף `sign`. לצלב 395/399/400 raw.
3. **🔴 I-65 (shadow-sim intrabar):** לחלץ את-נתיב-ה-hit-detection של-ה-shadow-sim — למה #395 ספר T1(7513.75@11:05) בעוד הסטופ(7525) נגע ב-10:55. לצלב לוג 09:55–11:05 CT.
4. **🟠 I-69 / A5 (INITIATIVE auth-key):** לאשר ש-`_auth_cell` מפספס `OFA_Initiative→INITIATIVE` (sizing.py:42-46 / five_min_system.py:1348-1373) → FULL במקום SKIP. לצלב fire #396 raw (day_type=Normal, size).
5. **🟠 F1–F5 (pattern-miss):** להריץ על-ה-Mac `python3 scripts/audit_pattern_miss.py --date 2026-07-17 --relax all --out docs/reports/PATTERN_MISS_RUN_2026-07-17.md` (+ 07-16/07-15) → per-swing near-miss + false-fire-count פר-relaxation. + לצלב `[Woodies] HTLB dir-gate` לוג (האם bias-DOWN-latched חסם longs-בוקר).
6. **🟠 A1/A3 (Normal-day fade):** אושר-חי `NORMAL_ROTATION_FIX_V1` נפרס 12:27 CT — לצלב שהוא-אכן-הוסיף `Normal` ל-exemption(gateway:811)+stop-floor(stop_resolver:75) בלי-רגרסיה.
7. **🟠 I-67 (GHOST):** למה GHOST נדרך ≥8× היום ונחסם `location_gate`/`entry_not_confirmed` — לזהות מקור-התבנית ב-קוד (S4-detector/fallback/באג-שיוך).
8. **🟡 endpoint-פערים:** `/missed-trades count=0` מול 20-missed-winners ב-OPS_LOG · `/gateway/decisions buffer=22 in-memory-since-restart` — לחווט persistence כדי ש-EOD-endpoint לא-יהיה-עיוור.

**NOT-DONE / מגבלות:**
- כל-הקריאות דרך Chrome מול `localhost:8000` (אין PG-ישיר מ-sandbox); **ערכי-Sierra-גולמיים (CCI/TCCI/study) לא-הוצלבו** — read-only, CC.
- אין intraday-DIAG ⇒ `נדרכה#`-מלא מ-signals-log + OPS_LOG (לא מ-snapshot-30דק').
- `git pull` נכשל בריצה זו (remote חסום ב-sandbox) — עבדתי מול ה-checkout המקומי (HEAD `bbce19da`, 2026-07-17 20:27 IL). ⇒ ייתכן ש-CC/iMac הוסיפו entries אחרי-כן.
- ה-counterfactual מבוסס על-סף-`missed_watch` (+4/−6) + 78-ברי-5דק' + `stop_initial`. **ΣR-אמת = הערכה** (pnl_r שבור; חישוב-single-contract-equivalent).
- **שום קוד/flag/.env/DB לא-שונה בריצה זו.**

— הרצה-מתוזמנת `mems26-eod-issues-designs`, 2026-07-17 15:12 CT (מקור: Chrome-MCP חי + OPS_LOG + audits; read-only; לא-קומיט)
