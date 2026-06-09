# PATTERN_DIAG — 2026-06-08

## 08:07 CT — מחוץ ל-RTH, מדלג

RTH = 08:30–15:00 שיקגו (CT). השעה הנוכחית 08:07 CT (לפני פתיחה, 13:07 UTC). מחוץ לחלון המסחר — מדלג על בדיקת התבניות. הריצה הבאה שתיפול בתוך 08:30–15:00 CT תבצע את הבדיקה העמוקה המלאה.

---

## 08:42 CT — בדיקה עמוקה (snapshot #1, ~12 דק' לתוך RTH)

**זמן:** 2026-06-08 08:42 CT (13:42 UTC). `build/pattern-status.ts`=`2026-06-08T13:42:24Z`, `session_date=2026-06-08`, `in_session=true`, `minutes_to_close=380`.
**מקור-נתונים:** API דרך Chrome (`javascript_tool fetch` → `http://localhost:8000`). frontend (`localhost:3000`) **כבוי** ⇒ אין לוח-React לצלם; הטבלה רונדרה מ-ה-API לצילום (ID `ss_88271eqn4`, **inline-only — save_to_disk לא נשמר לדיסק ב-session הזה**, ראה NOT-DONE).

### 🔴 ממצא-על (headline): ערוץ-היצוא 5-דק'/study **לא עלה בכלל הסשן** — S1/S2/S4 רצים על ברי-יום-שישי קפואים

`build/pattern-status.readiness.verdict = **BLOCKED**` · reason `dead: tick_reversal,5min_bars`.

Bridge global-gates (mtime של קבצי-היצוא של Sierra) — **פיצול חד בין שני ערוצי-יצוא:**

| stream | present | mtime / age | req | מסקנה |
|--------|---------|-------------|-----|-------|
| `woodies_5min` | ❌ DEAD | 2026-06-05 22:20:00 · 3802 דק' | <90s | ערוץ 5דק'/study **מת מיום שישי** |
| `5min_bars` | ❌ DEAD | 2026-06-05 23:55:00 · 3707 דק' | <360s | "" |
| `tick_reversal` | ❌ DEAD | 2026-06-05 15:51:19 · 4191 דק' | <90s | "" (חוסם לוח) |
| `footprint` | ✅ FRESH | 2026-06-08 16:42:24 (IL) · 0s | <90s | ערוץ tick/CVD/footprint **חי עכשיו** |
| `cumulative_delta` | ✅ FRESH | 2026-06-08T13:39:59Z · 0s | <360s | "" |
| `volume_profile` | ✅ FRESH | 2026-06-08T13:42:20Z · 0s | <360s | "" |
| `imbalance` | ✅ FRESH | 2026-06-08T13:28:12Z · 0s | <90s | "" |
| `tpo_bars` | ❌ DEAD | 2023-11-25 · (S5/TPO לא-מחווט, ידוע) | <360s | — |

**מסקנה:** ערוץ ה-tick/price+CVD+footprint **כותב בזמן-אמת** (FRESH 0s), אבל ערוץ ה-**5דק'/study/bars** (woodies_5min + 5min_bars + tick_reversal) **לא כתב מאז יום שישי** — אף בר חדש לא נכתב מאז הפתיחה היום. זו **הישנות של I-21** אבל כ-**session-non-start** (לא stall אמצע-יום): הערוץ פשוט לא עלה הבוקר. כל S1/S2/S4 רצים על ברי-שישי **קפואים** (woodies `cci_14=-139.56` = ערך-שישי קפוא).

**מקור-אמת לבדיקת CC (לא כאן):** למה ערוץ ה-5דק'/study ב-Sierra (`MES_AI_DataExport`/study export ל-`~/SierraChart_Data/v9_export/woodies_5min*`, `5min_bars*`, `tick_reversal*`) **לא התחיל לכתוב** בפתיחת הסשן 08:30 CT, בעוד `footprint*`/`cumulative_delta*`/`volume_profile*`/`imbalance*` כן? להצליב mtime של הקבצים מול לוג הגשר/Sierra.

### טבלת 5-השאלות — S2 (five_min)

`five_min`: `running=true, hydrated=true, mode=FIRST_HOUR_TACTICAL, buffer_size=46, opening_type=UNKNOWN, last_pattern=null`. `stats`: `patterns_detected=0, setups_published=0`. כל 10 התבניות **blocked**, סיבה זהה: `Missing: day_type_gate.day_type_known, day_type_gate.auth_table_cell, data.fhb_eligible`.

| # | תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|-------|-----------|-----------|-----------|---------------|-----------|
| S2-all (REACTIVE_L/S, INITIATIVE_L/S, INV_HNS, HNS_TOP, DOUBLE_BOTTOM_EE, DOUBLE_TOP_AA, BULL_FLAG, BEAR_FLAG) | buffer=46 אבל **ברי-שישי קפואים** (last_bar `2026-06-05 23:55`) | ❌ לא — הברים לא של היום | `day_type_gate.day_type_known` חסר + `data.fhb_eligible` חסר (לא choppiness_ok כמו בימים קודמים) | **כן, מוצדק** — בלי day_type מסווג וברים-טריים אסור לדרוך | **day_type** (תלוי בערוץ 5דק' המת) + **fhb_eligible** (תלוי בברי-RTH טריים) |

ההבדל מימים קודמים: **החוסם היום הוא `day_type_known`+`fhb_eligible`, לא `choppiness_ok`** (I-16). שניהם downstream של ערוץ ה-5דק' המת.

### טבלת 5-השאלות — S4 (woodies)

`woodies`: `running=true, hydrated=true, cci_14=-139.56, cci_6_tcci=-84.59, ema_34=null, lsma_value=null, swi_value=null, czi_value=null, trend_state=RED, buffer_size=38, active_patterns=[], classification=NO_SETUP, decision_tree={} (ריק), ready_to_route=false`. כל 9 התבניות בלוח: "Data ready, trend RED · X not yet detected".

| # | תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|-------|-----------|-----------|-----------|---------------|-----------|
| S4-all (ZLR, TLB, TT, GB100, HFE, HTLB, FAMIR, Vegas, Ghost) | `cci_14=-139.56` קיים אבל **קפוא** (ערך-שישי; woodies_5min DEAD) | ❌ לא — הברים לא של היום | הלוח אומר "Data ready" אך זה **שקר** (predicate freshness מסמן בר-שישי כ-fresh, I-20); המנוע `active_patterns=[]` כי מעריך בר קפוא | החסימה **בפועל מוצדקת** (אסור לירות על בר-שישי), אבל ה**הצגה** "Data ready" שגויה | ברים-טריים מערוץ 5דק' (מת); `ema/lsma/swi/czi=null` ⇒ קלטי-Woodies המשניים גם חסרים |

`decision_tree={}` **ריק** — אין A1–A7 בסנאפ-שוט הזה (בימים קודמים היה מלא). תואם NO_SETUP על בר-קפוא. **CC: להצליב `cci_14=-139.56` מול `~/SierraChart_Data/v9_export/` — לאשר שזה ערך-שישי הקפוא.**

### טבלת 5-השאלות — S3 (footprint)

`footprint`: `running=true, hydrated=true, bars_processed_today=0, buffer_size=0, aggressive_flow=null, delta=null, cumulative_delta=0, dominance=null, last_fire=null`. כל 4 התבניות: "Insufficient buffer (0 bars, need ≥5)".

| # | תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|-------|-----------|-----------|-----------|---------------|-----------|
| S3-all (ABSORPTION, STACKED_IMBALANCE, SWEEP_RETURN, EXHAUSTION) | ❌ אין — 0 ברים, buffer 0 | — | "Insufficient buffer (0, need ≥5)" | n/a — אין מה לדרוך | **ingest שבור:** קובץ `footprint` **FRESH 0s** (נכתב עכשיו) אבל 0 ברים ל-buffer ⇒ **I-11**, file→bridge→buffer שבור |

**הוכחת-עצמאות I-11↔I-21:** היום ערוץ footprint **חי** (FRESH 0s) בעוד woodies_5min **מת** — ולמרות זאת footprint 0 ברים. ⇒ I-11 (ingest-break של footprint) **עצמאי** מ-I-21 (export-stall של 5דק'). אישור חוזר.

### Gates (S6/gateway)

`gateway`: `shadow_active_count=0, daily_pnl=0, trades_today=0, consecutive_losses=0, demo_enabled=[2,4], live_enabled=[], chop_state=EXPANDING`. cooldown/cluster_guard/SSV — כולם לא-פעילים. אין חסימת-gateway פעילה (החסם הוא feed, לא gate).

### עסקאות (trades/recent)

3 עסקאות סה"כ, **כולן מיום שישי 2026-06-05** (אין עסקה היום — צפוי, 12 דק' לתוך RTH): id=10 SHORT sys2 `pnl_r=92`, id=12 SHORT sys4 `pnl_r=16`, id=13 SHORT sys2 `pnl_r=26.75`. **I-22 (אינפלציית pnl_r ~50×) עדיין גלוי** בערכי-שישי. אין עסקה-טרייה לבדוק היום.

### עדכון-חשודים (ISSUES_REGISTER) — snapshot 08:42 CT

| # | סטטוס לפני | ממצא 08:42 | סטטוס אחרי |
|---|-----------|-----------|-----------|
| I-1 (day_type=UNKNOWN) | 🔴 | state=`A2/UNKNOWN/conf 0/opening UNKNOWN/session_min=0`. ~12דק' לתוך RTH ⇒ UNKNOWN **חלקית צפוי** בשלב IB, אבל השורש היום = **ערוץ 5דק' מת** (אין ברים לסווג). שונה מימים קודמים (פיצול-instance) — היום אי-סיווג **אמיתי** עקב feed | 🔴 |
| I-3 (ZLR) | 🔬 | armed "Data ready, trend RED · ZLR not yet detected", `active_patterns=[]` — אך על בר-שישי קפוא. אין counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | 🔴 | אישור 13: קובץ FRESH 0s, 0 ברים/buffer 0/flow null, 4 תבניות "Insufficient buffer". עצמאי מ-I-21 (היום 5דק' מת, footprint חי) | 🔴 |
| I-15 (trend_state) | 🔬 | מנוע RED + לוח RED (s4_trend_not_stuck_gray PASS) — מסכימים, אין GRAY veto. אבל `cci_14=-139.56` על בר-שישי קפוא. frontend כבוי ⇒ אין הצלבת-UI היום. ממתין הצלבת Sierra | 🔬 |
| I-16 (choppiness_ok) | 🔴 | **לא משחזר** — החוסם היום `day_type_known`+`fhb_eligible`, לא `choppiness_ok` | 🔴 (לא רלוונטי היום) |
| I-19 (pattern-status hang) | 🔴 | **לא משחזר** — 137ms ואז 79ms (200, len 77593). שאר endpoints <45ms | 🔴 (לסירוגין) |
| I-20 (freshness predicate) | 🟡 | **אומת בוטה:** `five_min.fresh=true` עם `lag=233140s` (~2.7 ימים, threshold 660); `woodies.fresh=true` lag 238840s. הלוח-readiness משתמש ב-gates (DEAD נכון) ⇒ BLOCKED נכון, אבל `data_freshness.fresh` ברמת-מערכת **משקר** | 🟡 |
| I-21 (5דק' stall) | 🔴 | **הישנות כ-session-non-start:** woodies_5min/5min_bars/tick_reversal מתים מ-שישי; הערוץ לא עלה הבוקר. השורש מאחורי I-1/I-15/S2-S4-frozen היום | 🔴 |
| I-22 (pnl_r ~50×) | 🔴 | עדיין גלוי בערכי-שישי (92R/16R/26.75R). אין עסקה-טרייה לבדוק | 🔴 |
| I-23 (gateway counters) | 🟡 | היום `trades_today=0/daily_pnl=0/shadow_active_count=0` — **נכון** (אין עסקה היום; עסקאות-שישי לא נספרות היום). לא ניתן לשחזר את אי-העקביות בלי עסקה-טרייה | 🟡 (לא נצפה היום) |

### NOT-DONE / פערים
- **צילום לא נשמר לדיסק:** `save_to_disk` ללא-אפקט ב-session הזה; ה-frontend (`localhost:3000`) כבוי ⇒ אין לוח Build-Status מרונדר לצלם. הטבלה רונדרה מה-API (inline ID `ss_88271eqn4`) אבל **אין נתיב-קובץ**. אם נדרש קובץ-צילום קבוע — להריץ כשה-frontend חי.
- **הצלבת Sierra v9_export** (CCI/study/atr/בר-קפוא) — **ל-CC**, לא בוצעה כאן (read-only API בלבד). כל ערך `cci_14`/`day_type`/freshness מסומן לבדיקה מול `~/SierraChart_Data/v9_export/`.
- **decision_tree של woodies ריק (`{}`)** — לא ניתן למפות reject_reason ברמת A1–A7 בסנאפ-שוט הזה (NO_SETUP על בר-קפוא).
- **counterfactual:** אין signal שזוהה-ונחסם היום (הכל חסום ב-feed/day_type) ⇒ אין מה לחשב. ה-EOD-counterfactual חסום גם ב-I-22 (pnl_r מנופח).

---

## 09:10 CT — בדיקה עמוקה (snapshot #2, ~40 דק' לתוך RTH)

**זמן:** 2026-06-08 09:10 CT (14:10 UTC). `build/pattern-status.ts`=`2026-06-08T14:10:19Z`, `session_date=2026-06-08`. כל ה-endpoints ענו <60ms (woodies 13 · footprint 6 · five_min 5 · stats 7 · trades 21 · gateway 5 · day_type 6 · pattern-status 56). **מקור-נתונים:** API דרך Chrome (`javascript_tool fetch` → `localhost:8000`). frontend (`localhost:3000`) **עדיין כבוי** ⇒ הטבלה רונדרה מ-API לצילום (ID `ss_5183rl3f4`, **inline-only — save_to_disk ללא-אפקט**, ראה NOT-DONE).

### 🟢 שינוי-על מאז 08:42: ערוץ ה-5דק'/study **עלה** (~09:00 CT) — I-21 התאושש חלקית

ב-08:42 ערוץ ה-5דק'/study היה DEAD-מ-שישי (session-non-start). בסנאפ-שוט זה הוא **חי**:

| stream | 08:42 | 09:10 | מסקנה |
|--------|-------|-------|-------|
| `woodies_5min` | ❌ DEAD (שישי 22:20) | ✅ **FRESH** `2026-06-08 17:00:00` IL (=09:00 CT) | ערוץ 5דק'/study **עלה** ~09:00 CT (30דק' אחרי פתיחה) |
| `5min_bars` | ❌ DEAD (שישי 23:55) | ✅ **FRESH** `17:10:00` IL (=09:10 CT) | "" |
| `footprint` | ✅ FRESH | ✅ FRESH `17:10:16` IL | חי — אבל ingest 0 ברים (I-11) |
| `cumulative_delta` | ✅ FRESH | ✅ FRESH (lag 19s) | חי |
| `volume_profile` | ✅ FRESH | ✅ FRESH (lag 3s) | חי |
| `imbalance` | ✅ FRESH | ⚠️ Present אך **lag 317s > 90s req** | stale-but-Present (I-18) |
| `tick_reversal` | ❌ DEAD (שישי 15:51) | ❌ **DEAD 4219min** (עדיין שישי 15:51:19) | **לא עלה** — חוסם לוח |
| `tpo_bars` | ❌ DEAD (2023) | ❌ DEAD (S5/TPO לא-מחווט, ידוע) | — |

**ראיות-תנועה שמאשרות שהערוץ חי:** woodies `cci_14` נע **-139.56 (קפוא-שישי) → -154.05**; five_min `buffer_size` גדל **46 → 65**; `opening_type` ב-five_min השתנה **UNKNOWN → OPEN_DRIVE**. ⇒ ברים-טריים זורמים סוף-סוף לערוץ ה-5דק'.

**מקור-אמת ל-CC (לא כאן):** למה ערוץ ה-5דק'/study התעכב ~30דק' (פתיחה 08:30, עלה ~09:00) ולמה `tick_reversal` **בכלל לא עלה** היום בעוד שאר ערוץ ה-tick/CVD/footprint כן. להצליב mtime מול לוג Sierra/גשר.

### טבלת 5-השאלות — לפי מערכת

**readiness verdict = `BLOCKED`** · reason `dead: tick_reversal` (ב-08:42 היה `tick_reversal,5min_bars` — כעת 5min_bars ירד מהרשימה כי עלה). checks: `bridge_streams_fresh=false/block (dead tick_reversal)` · `s1_day_type_classified=false/degrade (UNKNOWN)` · `s4_trend_not_stuck_gray=true (RED)` · `in_rth=true`.

| מערכת/תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|---|---|---|---|---|
| **S1 day_type** | ✅ state חוזר | ⚠️ `UNKNOWN/conf 0/opening UNKNOWN/session_min=0` ב-40דק' לתוך RTH | stage A3 (טרם-IB-classify); הערוץ עלה רק לפני ~10דק' ⇒ אין עדיין מספיק ברי-פתיחה | חלקית-מוצדק בשלב-IB; אך session_min=0 לא-הגיוני ב-40דק' (instance לא עוקב סשן) | atr_daily/yesterday-IB + ברי-פתיחה מצטברים; opening_type עדיין UNKNOWN ב-state בעוד five_min=OPEN_DRIVE (פער-instance I-1) |
| **S2 five_min** (כל 10) | ✅ buffer 65, mode FIRST_HOUR_TACTICAL | ⚠️ `patterns_detected=0`, כולן blocked | `Missing: day_type_gate.day_type_known, day_type_gate.auth_table_cell, data.choppiness_ok` | day_type_gate מוצדק (day_type=UNKNOWN); choppiness_ok = פער-חיווט אפשרי (I-16) | day_type מ-S1 (UNKNOWN) → חוסם את כל ה-10; choppiness_ok-flag |
| **S3 footprint** (כל 4) | ❌ `bars_processed_today=0`, buffer 0, flow null | ❌ קובץ FRESH אך 0 ברים = לא-הגיוני | "Insufficient buffer (0 bars, need ≥5)" | לא — החסימה היא **סימפטום** של ingest שבור, לא gate-לגיטימי | **I-11:** קובץ-footprint FRESH `17:10:16` נכתב עכשיו, אך file→bridge→buffer שבור. עצמאי מ-I-21 (אישור 14) |
| **S4 woodies** (כל 9) | ✅ cci/studies present (A2 "11 studies present") | ✅ `cci_14=-154.05 tcci=-117.43 trend=RED` (סביר; CCI נע) | `active_patterns=[]` — "Data ready, trend RED · <P> not yet detected" (A1/A3 SKIP "no patterns this bar") | מוצדק — אין detection בבר זה (לא חסם, פשוט אין setup) | אין — הערוץ עלה, מחכה ל-pattern טרי. A5 advisory `calculate_size=reject` בלי setup לחסום (I-13) |
| **gates** (S5/S6) | tpo_bars DEAD (S5 לא-מחווט, ידוע); tick_reversal DEAD חוסם | — | tick_reversal לא עלה היום | tick_reversal צריך לעלות — חוסם את כל הלוח | חיווט/עליית ערוץ tick_reversal |

### עסקאות + gateway

`trades/recent`: 3 עסקאות, **כולן מיום שישי 2026-06-05** (אין עסקה היום — צפוי): id=10 SHORT sys2 `pnl_r=92`, id=12 SHORT sys4 `pnl_r=16`, id=13 SHORT sys2 `pnl_r=26.75`. **I-22 (אינפלציית pnl_r ~50×) עדיין גלוי** בערכי-שישי. `gateway`: `trades_today=0/daily_pnl=0/shadow_active=0` (נכון היום) · `chop=FOUND`.

### עדכון-חשודים — snapshot 09:10 CT

| # | ממצא 09:10 | סטטוס |
|---|-----------|-------|
| I-1 (day_type=UNKNOWN) | עדיין `A3/UNKNOWN/conf 0/opening UNKNOWN/session_min=0`, אך **הסיבה השתנתה:** ב-08:42 = ערוץ-5דק'-מת; כעת הערוץ **עלה** (~09:00) — אז ה-UNKNOWN הוא טרם-IB-classify אמיתי (40דק', צריך עוד ברי-פתיחה). `session_min=0` ב-40דק' = instance לא-עוקב-סשן (פער קיים) | 🔴 |
| I-3 (ZLR) | armed "Data ready, trend RED · ZLR not yet detected", `active_patterns=[]` — כעת על **בר חי** (לא קפוא). עדיין לא נדרך setup; אין counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | **אישור 14 + עצמאות מוכחת שוב:** footprint gate FRESH `17:10:16` (נכתב עכשיו) בעוד 5דק'/study **עלה** היום — ועדיין `bars_processed_today=0`/buffer 0/flow null, 4 תבניות "Insufficient buffer". ⇒ file→bridge→buffer שבור, עצמאי מ-I-21 | 🔴 |
| I-15 (trend_state) | מנוע RED + לוח `s4_trend_not_stuck_gray=true RED` — מסכימים, אין GRAY veto. `cci_14=-154.05` כעת **נע** (לא קפוא — הערוץ עלה). frontend כבוי ⇒ אין הצלבת-UI. ממתין הצלבת Sierra | 🔬 |
| I-16 (choppiness_ok) | **חזר היום** — כל 10 תבניות-S2 blocked כולל `data.choppiness_ok` (בנוסף ל-day_type_gate). chop score=FOUND ב-gateway אך הדגל הבוליאני מסומן Missing ⇒ פער-חיווט (score≠gate-flag) | 🔴 |
| I-18 (freshness TZ-mix) | `imbalance` Present אך lag 317s>90s req (stale-but-Present); woodies_5min/5min_bars/footprint נושאים IL-local (17:xx) מול cumulative_delta/volume_profile ב-UTC (14:xx) — TZ-mix נמשך | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 56ms (200). שאר endpoints <25ms | 🔴 (לסירוגין) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10180/fresh=true/threshold=90` (lag שלילי ~-2.8h). ה-predicate לא אוכף סף. (readiness משתמש ב-gates → BLOCKED נכון) | 🟡 |
| I-21 (5דק' stall) | **התאושש חלקית:** ערוץ woodies_5min+5min_bars **עלה** ~09:00 CT (cci נע, buffer 46→65, opening UNKNOWN→OPEN_DRIVE). נותר: `tick_reversal` **לא עלה כלל** היום (DEAD מ-שישי) → חוסם לוח. השורש (עיכוב 30דק' + tick_reversal לא-עולה) ל-CC | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי (92/16/26.75R). אין עסקה-טרייה היום | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |

### NOT-DONE / פערים
- **צילום לא נשמר לדיסק:** `save_to_disk` ללא-אפקט ב-session (אומת שוב); frontend כבוי ⇒ אין לוח React לצלם. הטבלה רונדרה מ-API (inline ID `ss_5183rl3f4`), **אין נתיב-קובץ**.
- **הצלבת Sierra v9_export ל-CC:** כל ערך `cci_14=-154.05`/`day_type`/freshness/IL-vs-UTC ts מסומן לבדיקה מול `~/SierraChart_Data/v9_export/`. במיוחד: למה tick_reversal לא עלה היום ולמה ערוץ 5דק' התעכב 30דק'.
- **decision_tree woodies ריק** (NO_SETUP) — אין reject_reason ברמת A1–A7 בסנאפ-שוט (אין setup על בר).
- **counterfactual:** אין signal שזוהה-ונחסם היום (הכל חסום ב-feed/day_type) ⇒ אין מה לחשב. EOD-counterfactual חסום גם ב-I-22.

---

## 09:40 CT — בדיקה עמוקה (snapshot #3, ~70 דק' לתוך RTH)

**זמן:** 2026-06-08 09:40 CT (14:40 UTC). `build/pattern-status.ts`=`2026-06-08T14:40:04Z`, `session_date=2026-06-08`, `build_version=v1`.
**מקור-נתונים:** API דרך Chrome (`javascript_tool fetch` → `http://localhost:8000`). frontend (`localhost:3000`) **כבוי** (root מחזיר `{"detail":"Not Found"}`) ⇒ אין לוח-React לצלם; הטבלה רונדרה מ-ה-API לצילום (inline ID `ss_1064nuc2a`, **save_to_disk ללא-אפקט ב-session — אין נתיב-קובץ**; snapshot HTML דורבל נשמר ב-`docs/reports/snapshots/build_status_2026-06-08_0940CT.html`).
**latency:** כל 8 ה-endpoints ענו <200ms (`pattern-status`=176ms, woodies 37–89ms, day_type 56ms) ⇒ **I-19 (hang) לא משחזר**.

### 🟢🔴 שתי תזוזות-על מאז 09:10

**(1) 🟢 day_type **סוּוַּג** — Trend_Normal, עקבי על פני 3 משטחים.** ב-09:10 היה `UNKNOWN`. כעת `day_type/state` = `B2 / Trend_Normal / conf 0.38 / lock PENDING`, ה-readiness = `s1_day_type_classified ✓ day_type=Trend_Normal`, וה-S2 auth-gate = `× Trend_Normal`. ⇒ **הפיצול 3-הכיווני של I-1 לא משחזר על תווית-היום** — כל המשטחים מסכימים Trend_Normal. ⬅️ day_type **כבר לא חוסם את S2** (gate satisfied).

**(2) 🔴 השוק התהפך — CCI חצה מעל אפס, trend נכנס ל-GRAY.** woodies `cci_14` **−154.05 (09:10) → +121.58 (09:40)** — חציית-אפס מטה-מעלה. `trend_state` = **GRAY** (לא עוד RED), `tcci=+93`, `lsma 7442 / ema34 7449`. **המנוע והלוח מסכימים על GRAY** (`s4_trend_not_stuck_gray ✗ trend_state=GRAY`) ⇒ **C-1/I-15 (קונפליקט מנוע↔לוח) לא משחזר** — היום ה-GRAY אמיתי בשני המשטחים, לא תקלת-תצוגה.

### Bridge global-gates (mtime קבצי-יצוא Sierra)

| stream | present | value | req | מסקנה |
|--------|---------|-------|-----|-------|
| `woodies_5min` | ✅ FRESH | `2026-06-08 17:40:00` (IL=09:40 CT) · 0s | <90s | ערוץ 5דק'/study **חי** (התאושש מ-09:00) |
| `5min_bars` | ✅ FRESH | `17:40:00` (IL) · 0s | <360s | "" |
| `footprint` | ✅ FRESH | `17:40:03` (IL) · 0s | <90s | קובץ נכתב **עכשיו** — אך 0 ברים (I-11) |
| `cumulative_delta` | ✅ FRESH | `14:40:00Z` · lag 4.6s | <360s | חי (UTC תקין) |
| `volume_profile` | ✅ FRESH | `14:40:02Z` · 0s | <360s | חי |
| `imbalance` | ✅ FRESH | `14:40:03Z` · 0s | <90s | חי |
| `tick_reversal` | ❌ **DEAD 4248min** | `2026-06-05 15:51:19` | <90s | **לא עלה כלל היום** — חוסם לוח |
| `tpo_bars` | ❌ DEAD | `2023-11-25` (S5/TPO לא-מחווט, ידוע) | <360s | — |

⚠️ **TZ-mix (I-18):** `woodies_5min`/`footprint`/`5min_bars` נושאים זמן-ישראל (`17:40`) אך ה-`freshness.ts` מסומן `+00:00` (lag_s=**null** — לא ניתן לחשב); בעוד `cumulative_delta`/`volume_profile`/`imbalance` ב-UTC תקין (`14:40`, lag_s=4.6). מפר CLAUDE.md Rule 4.

### readiness verdict = `BLOCKED` · reason `dead: tick_reversal`

| check | passed | severity | detail |
|---|---|---|---|
| `bridge_streams_fresh` | ❌ | block | dead: tick_reversal |
| `s1_day_type_classified` | ✅ | degrade | day_type=Trend_Normal |
| `s4_trend_not_stuck_gray` | ❌ | degrade | trend_state=GRAY |
| `in_rth` | ✅ | info | RTH 09:30–16:00 ET |

### טבלת 5-השאלות — לפי מערכת

| מערכת/תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|---|---|---|---|---|
| **S1 day_type** | ✅ `Trend_Normal/conf 0.38/B2` | ⚠️ סיווג שפוי; אך `opening_type=UNKNOWN` (בעוד five_min=OPEN_DRIVE) + `session_min=0` ב-70דק' | — (מסווג; degrade-only ב-readiness) | סיווג מוצדק | **I-1 residual:** opening_type=UNKNOWN ב-state מול OPEN_DRIVE ב-five_min (פער-instance); session_min=0 לא-עוקב-סשן |
| **S2 five_min** — 4 מומנטום (Reactive L/S, Initiative L/S) + 2 flags (Bull/Bear) | ✅ buffer 8, FRESH lag 4.6s, mode DAY_TYPE_MODE | ⚠️ `patterns_detected=0`, 6 blocked | `Missing: data.choppiness_ok` | **לא-מוצדק כנראה** — gateway `chop_state=EXPANDING` (score קיים) אך הדגל הבוליאני מסומן Missing | **I-16 חזר:** פער-חיווט score≠gate-flag. CC: לחווט את הדגל מ-chop_state |
| **S2 five_min** — 4 day-patterns (INV_HNS, HNS_TOP, DOUBLE_BOTTOM_EE, DOUBLE_TOP_AA) | ✅ | ✅ | `Auth Table SKIP × Trend_Normal` | **מוצדק** — תבניות-יום אלו לא מורשות ל-Trend_Normal (auth-table by design) | — (חסימה לגיטימית לפי האפיון) |
| **S3 footprint** (כל 4: ABSORPTION/STACKED_IMBALANCE/SWEEP_RETURN/EXHAUSTION) | ❌ `bars_processed_today=0`, buffer 0, flow null, last_bar_ts=null | ❌ קובץ FRESH (נכתב עכשיו 17:40:03) אך 0 ברים = לא-הגיוני | "Insufficient buffer (0 bars, need ≥5)" | **לא** — סימפטום של ingest שבור, לא gate לגיטימי | **I-11 (אישור 15):** file→bridge→buffer שבור. עצמאי מ-I-21 (5דק' חי, footprint-file חי, אך 0 ברים מגיעים ל-buffer) |
| **S4 woodies** (כל 7: ZLR/TLB/TT/GB100/HFE/HTLB + CCI-HnS) | ✅ A2 "11 studies present", cci_14=+121.6 | ✅ CCI נע (118→121 תוך 3s), GRAY שפוי (חצה אפס) | `Stage A1 veto: trend_state=GRAY (GREY/YELLOW/INDETERMINATE — Woodies WSI rule)` | **מוצדק** — Woodies סוחר רק ב-trend נקי (RED/GREEN); GRAY=indeterminate חוסם by-design | — (אין detection ב-trend אפור; ZLR=I-3 לא נדרך, חסום A1 לפני A3) |
| **gates** (S5/S6) | tpo_bars DEAD (S5 לא-מחווט, ידוע); tick_reversal DEAD חוסם | — | tick_reversal לא עלה היום | tick_reversal צריך לעלות — חוסם את כל הלוח | חיווט/עליית ערוץ tick_reversal |

### עסקאות + gateway

`trades/recent`: 3 עסקאות, **כולן מיום שישי 2026-06-05** (אין עסקה היום — צפוי, trend GRAY + feed חסום): id=10 SHORT sys2 `pnl_r=92`, id=12 SHORT sys4 `pnl_r=16`, id=13 SHORT sys2 REACTIVE_SHORT `pnl_r=26.75` ($66.88, entry 7414.25→stop_init 7418, T1 7410.5✓ T2 7404.875✓, exit STOP_HIT@BE 7414). **I-22 אינפלציה ~50× עדיין גלוי** (id=13: $66.88 אמיתי≈+1.17R מדווח 26.75R). `gateway`: `trades_today=0/daily_pnl=0/shadow_active=0` (נכון היום) · `chop_state=EXPANDING`.

### עדכון-חשודים — snapshot 09:40 CT

| # | ממצא 09:40 | סטטוס |
|---|-----------|-------|
| I-1 (day_type=UNKNOWN) | **שיפור מהותי:** day_type=**Trend_Normal** עקבי על 3 משטחים (state+readiness+S2-gate) — הפיצול-3-כיווני **לא משחזר**, ו-day_type **כבר לא חוסם S2**. נותר residual: `opening_type=UNKNOWN` ב-state מול `OPEN_DRIVE` ב-five_min, ו-`session_min=0` ב-70דק' (instance לא-עוקב-סשן) | 🟡 (שופר מ-🔴) |
| I-3 (ZLR) | חסום ב-`Stage A1 veto trend_state=GRAY` — לא מגיע ל-A3 detection. על בר חי. אין setup, אין counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | **אישור 15 + עצמאות מוכחת:** gate `footprint` FRESH `17:40:03` (נכתב עכשיו) בעוד ערוץ 5דק' **חי** — ועדיין `bars_processed_today=0`/buffer 0/flow null, 4 תבניות "Insufficient buffer". file→bridge→buffer שבור, עצמאי מ-I-21 | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר:** מנוע=GRAY + לוח `s4_trend_not_stuck_gray ✗ GRAY` — **מסכימים**. היום ה-GRAY אמיתי (CCI חצה אפס ל-+121.6), לא תקלת-תצוגה. frontend כבוי ⇒ אין הצלבת-UI. ממתין הצלבת Sierra | 🔬 |
| I-16 (choppiness_ok) | **חזר:** 6 תבניות-S2 (4 מומנטום + 2 flags) blocked `Missing: data.choppiness_ok` בעוד gateway `chop_state=EXPANDING` (score קיים). פער-חיווט score≠gate-flag. CC: לחווט הדגל מ-chop_state | 🔴 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min/footprint/5min_bars נושאים IL-local (17:40) עם `freshness.ts` מסומן `+00:00`/`lag_s=null`; cumulative_delta/volume_profile/imbalance ב-UTC תקין (14:40, lag 4.6s). מפר Rule 4 | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 176ms (200). כל 8 endpoints <200ms | 🔴 (לסירוגין, נקי) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10795/fresh=true/threshold=90` (lag שלילי ~-3h). ה-predicate לא אוכף סף. (readiness משתמש ב-gates → BLOCKED נכון) | 🟡 |
| I-21 (5דק'/tick stall) | **5דק'/study חי** (woodies_5min/5min_bars/footprint-file FRESH 09:40, CCI נע). אך `tick_reversal` עדיין **DEAD מ-שישי 15:51** (session-non-start) → חוסם לוח. פיצול-ערוצים נמשך: tick_reversal לבדו מת | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי (92/16/26.75R; id=13 $66.88=26.75R, אמיתי≈1.17R). אין עסקה-טרייה היום | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)

- **`cci_14=+121.6` / `trend_state=GRAY`** — להצליב WSI/CCI-14/TCCI גולמי מול ה-export; לאמת שה-GRAY תואם את ה-study (ולא חישוב-בקנד).
- **footprint file FRESH אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer; הקובץ `17:40:03` נכתב, ה-ingest שותק.
- **tick_reversal session-non-start** (I-21) — CC: למה לא עלה ב-08:30 CT בעוד woodies_5min/footprint/CVD כן.
- **TZ-mislabel בגייטים** (I-18/I-20) — IL-local מסומן `+00:00`; CC לנרמל ל-UTC בגבול.

### NOT-DONE / פערים
- **צילום לא נשמר לדיסק:** `save_to_disk` ללא-אפקט ב-session (אומת שוב); frontend כבוי ⇒ אין לוח React לצלם. הטבלה רונדרה מ-API (inline ID `ss_1064nuc2a`); snapshot HTML דורבל ב-`docs/reports/snapshots/build_status_2026-06-08_0940CT.html`.
- **counterfactual:** אין signal שזוהה-ונחסם היום — S4 חסום A1-GRAY (אין detection), S2-מומנטום חסום choppiness_ok, S3 feed-dead, S2-day-patterns auth-skip לגיטימי. אין signal שעבר detection-ונחסם ⇒ אין מה לחשב. EOD-counterfactual חסום גם ב-I-22.

---

## 10:11 CT — בדיקה עמוקה (snapshot #4, ~101 דק' לתוך RTH)

**זמן:** 2026-06-08 10:11 CT (15:11 UTC). `build/pattern-status.ts`=`2026-06-08T15:11:39Z`, `session_date=2026-06-08`, `build_version` קיים, `271m לסגירה`.
**מקור-נתונים:** API דרך Chrome (`javascript_tool fetch` → `http://localhost:8000`). **🟢 שינוי-תשתית: frontend (`localhost:3000`) עלה** — לראשונה היום ה-לוח-React נגיש; **צולמו שני צילומי-React אמיתיים:** Dashboard (inline ID `ss_0324e57md`) + Build-Status decision-tree (inline ID `ss_6148nu00q`). `save_to_disk` עדיין **ללא-אפקט ב-session — אין נתיב-קובץ** (ראה NOT-DONE). (backend root `localhost:8000/` מחזיר `{"detail":"Not Found"}` — אין דף-HTML שם, זה נורמלי.)
**latency:** כל 8 ה-endpoints ענו <105ms (`pattern-status`=102ms, woodies 20ms, day_type 39ms, trades 42ms) ⇒ **I-19 (hang) לא משחזר**.

### 🟢 תזוזת-על מאז 09:40: השוק התהפך לכיוון מעלה — trend **BLUE**, S4 חזר ARMED

ב-09:40 ה-trend היה **GRAY** (CCI חצה אפס, A1 veto לכל S4). כעת `woodies.cci_14`=**+116.34** (יציב מעל-אפס; tcci=+78.65, czi=80, ema34 7454.25, lsma 7460.84), `trend_state`=**BLUE**, `interpretations.trend_direction`="uptrend (continuation LONG)". ⇒ **A1-GRAY veto נעלם** — כל 9 תבניות-S4 כעת `armed` ("Data ready, trend BLUE · X not yet detected"), `active_patterns=[]` (אין detection בבר זה). **המנוע והלוח מסכימים על BLUE** (`s4_trend_not_stuck_gray ✓ trend_state=BLUE`) ⇒ **C-1/I-15 לא משחזר**.

### 🔴 הישנות הפיצול 3-כיווני של day_type (I-1) — Variation מול Trend_Normal

ב-09:40 כל 3 המשטחים הסכימו `Trend_Normal`. **כעת חזר הפיצול:**

| משטח | תווית-day_type |
|------|----------------|
| `day_type/state` endpoint | **Variation** (0.38/B2/lock PENDING) |
| S2 component `day_type_known` | **Variation** |
| Dashboard right-panel (React) | **Variation 38% M** |
| readiness `s1_day_type_classified` | **Trend_Normal** |
| Build-Status header (React) | **Trend_Normal** |

⇒ פיצול 2-קבוצתי: **Variation** (state+S2-gate+Dashboard) מול **Trend_Normal** (readiness+Build-header). **אך day_type לא חוסם S2** (component `day_type_known`=present/Variation, `auth_table_cell`=present/`FULL 3/2/2`) — הפיצול הוא אי-עקביות תצוגה/instance, לא חסם. בנוסף `opening_type=UNKNOWN` ב-state בעוד five_min=`OPEN_DRIVE` ו-`session_min=0` ב-~101דק' לתוך RTH (instance לא-עוקב-סשן).

### 🔎 ממצא-Dashboard חדש (frontend חי): `Y IB dll_missing` — חשוד-השורש ל-opening_type/session_min

ה-Dashboard מציג במפורש **`Y IB dll_missing`** (יום-אמש IB / atr_daily חסר מה-DLL). זה ככל-הנראה **שורש ה-residual של I-1**: בלי atr_daily/yesterday-IB, ה-state-instance לא יכול להשלים `opening_type` ו-`session_min` ⇒ נשארים UNKNOWN/0. **CC: לוודא אם `Y IB`/`atr_daily` אמורים להגיע מה-Sierra-export ולמה ה-DLL מחזיר missing.** (כן: today-IB מחושב — `IBH 7469.50 / IBL 7429.00 40.5pt WIDE` מוצג; חסר רק yesterday-IB.)

### Bridge global-gates (mtime קבצי-יצוא Sierra)

| stream | present | value | req | מסקנה |
|--------|---------|-------|-----|-------|
| `woodies_5min` | ✅ FRESH | `2026-06-08 18:10:00` (IL=10:10 CT) · lag null | <90s | ערוץ 5דק'/study **חי** |
| `5min_bars` | ✅ FRESH | `18:10:00` (IL) · lag null | <360s | "" (five_min lag אמיתי 99s) |
| `footprint` | ✅ FRESH | `18:11:35` (IL) · lag null | <90s | קובץ נכתב **עכשיו** — אך 0 ברים (I-11) |
| `cumulative_delta` | ✅ FRESH | `15:09:59Z` · lag 100s | <360s | חי (UTC תקין) |
| `volume_profile` | ✅ FRESH | `15:11:37Z` · lag 2.3s | <360s | חי |
| `imbalance` | ⚠️ Present | `14:55:09Z` · lag **990s (~16דק')** | <90s | **stale-but-Present (I-18)** |
| `tick_reversal_15` | ❌ **DEAD** | `2026-06-05 15:51:19Z` · lag 256820s (~71h) | <90s | **לא עלה כלל היום** — חוסם לוח |
| `tpo` | ❌ DEAD | `2023-11-25` (S5/TPO לא-מחווט, ידוע) | — | — |

⚠️ **TZ-mix (I-18):** `woodies_5min`/`footprint`/`bars_5min` נושאים זמן-ישראל (`18:1x`) אך ה-`freshness.ts` מסומן `+00:00` (lag=**null**); בעוד `cumulative_delta`/`volume_profile`/`imbalance` ב-UTC תקין. מפר CLAUDE.md Rule 4.

### readiness verdict = `BLOCKED` · reason `dead: tick_reversal_15,tpo`

| check | passed | severity | detail |
|---|---|---|---|
| `bridge_streams_fresh` | ❌ | block | dead: tick_reversal_15,tpo |
| `s1_day_type_classified` | ✅ | degrade | day_type=Trend_Normal |
| `s4_trend_not_stuck_gray` | ✅ | degrade | trend_state=BLUE |
| `in_rth` | ✅ | info | RTH 09:30–16:00 ET |

(Build-Status banner React אישר חזותית: **"למה לא נכנסנו עכשיו — מידע לא עדכני — dead: tick_reversal_15,tpo"**; שרשרת-ההחלטה: verdict BLOCKED → Day Type ×stale → S3 BLOCKED → Footprint ×stale → ✓ Woodies CCI · S2 BLOCKED · ✓ Min Patterns-5 · ✓ Bridge·Streams.)

### טבלת 5-השאלות — לפי מערכת

| מערכת/תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|---|---|---|---|---|
| **S1 day_type** | ✅ state חוזר Variation | ⚠️ סיווג קיים אך פיצול Variation↔Trend_Normal; `opening_type=UNKNOWN`, `session_min=0` ב-101דק' | — (לא חוסם; degrade-only) | סיווג מוצדק | **I-1 residual:** פיצול-instance (Variation מול Trend_Normal) + opening_type=UNKNOWN + session_min=0; חשוד-שורש `Y IB dll_missing` |
| **S2 five_min** — כל 10 (REACTIVE_L/S, INITIATIVE_L/S, INV_HNS, HNS_TOP, DOUBLE_BOTTOM_EE, DOUBLE_TOP_AA, BULL_FLAG, BEAR_FLAG) | ✅ buffer 12, FRESH lag 99s, FHB=COMPLETE bar=13 | ⚠️ `patterns_detected=0`, כל 10 blocked | `Missing: data.choppiness_ok` (day_type_gate **כן present** הפעם) | **לא-מוצדק / mislabel** — component `choppiness_ok` נושא `chop=93` (ציון **קיים**) אך present=false; הדגל הבוליאני לא-מחווט | **I-16 משחזר** + כעת **החוסם-היחיד** של כל 10. פער score≠gate-flag. אם chop=93 אמור לחסום לגיטימית — לתייג "chop גבוה" לא "Missing" |
| **S3 footprint** (כל 4: ABSORPTION/STACKED_IMBALANCE/SWEEP_RETURN/EXHAUSTION) | ❌ `bars_processed_today=0`, buffer 0, last_bar_ts=null, fresh=false | ❌ קובץ FRESH (נכתב עכשיו 18:11:35) אך 0 ברים = לא-הגיוני | "Insufficient buffer (0 bars, need ≥5)" | **לא** — סימפטום של ingest שבור, לא gate לגיטימי | **I-11 (אישור 16):** file→bridge→buffer שבור. עצמאי מ-I-21 (5דק' חי, footprint-file חי, אך 0 ברים) |
| **S4 woodies** (כל 9: ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR + Vegas/Ghost) | ✅ A2 "11 studies present", cci_14=+116.34 | ✅ CCI יציב מעל-אפס, BLUE שפוי, נע | `active_patterns=[]` — "Data ready, trend BLUE · X not yet detected" (A1/A3 SKIP "no patterns this bar") | **מוצדק** — אין detection בבר זה (לא חסם, פשוט אין setup) | אין — הערוץ חי, trend נקי BLUE, מחכה ל-pattern טרי. A5 advisory `calculate_size=reject` בלי setup לחסום (I-13) |
| **gates** (S5/S6) | tpo DEAD (S5 לא-מחווט, ידוע); tick_reversal_15 DEAD חוסם; gateway `chop_state=FOUND` | — | tick_reversal_15 לא עלה היום | tick_reversal_15 צריך לעלות — חוסם את כל הלוח | חיווט/עליית ערוץ tick_reversal_15 |

**הערת-skew (I-16-adjacent):** ערך-ה-chop מתפצל על-פני 3 משטחים — gateway `chop_state=FOUND`, S2 component `chop=93`, Dashboard strip `0 FOUND`. ⇒ אי-עקביות-ערך של ה-chop בין משטחים (כבר-נרשם כ-skew חומרה-נמוכה ב-I-16).

### עסקאות + gateway

`trades/recent`: 3 עסקאות, **כולן מיום שישי 2026-06-05** (אין עסקה היום — צפוי: feed BLOCKED + אין detection): id=10 SHORT sys2 `pnl_r=92`, id=12 SHORT sys4 `pnl_r=16`, id=13 SHORT sys2 `pnl_usd=66.88/pnl_r=26.75`. **I-22 אינפלציה ~50× עדיין גלוי** (id=13: $66.88 אמיתי≈+1.17R מדווח 26.75R). `gateway`: `trades_today=0/daily_pnl=0/shadow_active_count=0` (נכון היום) · `chop_state=FOUND` · cooldown/cluster/SSV לא-פעילים.

### עדכון-חשודים — snapshot 10:11 CT

| # | ממצא 10:11 | סטטוס |
|---|-----------|-------|
| I-1 (day_type) | **הישנות הפיצול:** Variation (state+S2-gate+Dashboard) מול Trend_Normal (readiness+Build-header) — אחרי ש-09:40 כולם הסכימו Trend_Normal. **אך לא חוסם S2** (gate satisfied). residual: opening_type=UNKNOWN, session_min=0 ב-101דק'. **חדש:** Dashboard מראה `Y IB dll_missing` = חשוד-שורש | 🟡 |
| I-3 (ZLR) | armed "Data ready, trend BLUE · ZLR not yet detected", `active_patterns=[]` — כעת ב-trend BLUE (uptrend), על בר חי. עדיין לא נדרך setup-ZLR; אין counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | **אישור 16 + עצמאות מוכחת:** gate `footprint` FRESH `18:11:35` (נכתב עכשיו) בעוד ערוץ 5דק' **חי** — ועדיין `bars_processed_today=0`/buffer 0/last_bar_ts=null, 4 תבניות "Insufficient buffer". file→bridge→buffer שבור, עצמאי מ-I-21 | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר:** מנוע=BLUE + לוח `s4_trend_not_stuck_gray ✓ BLUE` — מסכימים. frontend חי היום אך פאנל Woodies-CCI מציג CCIDiff≈-38.77 (מדד-נגזר שונה) מול endpoint cci_14=+116 — ייתכן skew-תצוגה משני, לתעד. הצלבת Sierra חובה | 🔬 |
| I-16 (choppiness_ok) | **משחזר + כעת חוסם-יחיד:** כל 10 תבניות-S2 blocked `Missing: data.choppiness_ok`; component present=false אך value `chop=93`. day_type_gate **כן present** הפעם ⇒ choppiness_ok הוא ה-bottleneck היחיד של S2. פער score≠gate-flag מבודד וברור | 🔴 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min/footprint/bars_5min IL-local (18:1x) `+00:00`/lag=null; cumulative_delta/volume_profile/imbalance UTC; `imbalance` Present אך lag 990s>90s (stale-but-Present). מפר Rule 4 | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 102ms (200). כל 8 endpoints <105ms | 🔴 (לסירוגין, נקי) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10700/fresh=true/threshold=90` (lag שלילי ~-3h). ה-predicate לא אוכף סף. (readiness משתמש ב-gates → BLOCKED נכון) | 🟡 |
| I-21 (5דק'/tick stall) | **5דק'/study חי** (woodies_5min/5min_bars/footprint-file FRESH, CCI נע 115→116, five_min lag 99s). `tick_reversal_15` עדיין **DEAD מ-שישי 15:51** (session-non-start) → חוסם לוח. פיצול-ערוצים נמשך: tick_reversal_15 לבדו מת | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי (92/16/26.75R). אין עסקה-טרייה היום | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active_count=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)

- **`cci_14=+116.34` / `trend_state=BLUE`** — להצליב WSI/CCI-14/TCCI גולמי מול ה-export; לאמת ש-BLUE תואם את ה-study.
- **`Y IB dll_missing`** — CC: למה ה-DLL לא מחזיר yesterday-IB/atr_daily; חשוד-שורש ל-opening_type=UNKNOWN + session_min=0 (I-1 residual).
- **footprint file FRESH אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer.
- **tick_reversal_15 session-non-start** (I-21) — CC: למה לא עלה ב-08:30 CT בעוד woodies_5min/footprint/CVD כן.
- **choppiness_ok score≠gate-flag** (I-16) — `chop=93` קיים אך הדגל present=false; CC לחווט את הדגל הבוליאני מ-chop_state ולהחליט אם chop=93 אמור לחסום (אז "chop גבוה" לא "Missing").
- **TZ-mislabel בגייטים** (I-18/I-20) — IL-local מסומן `+00:00`; CC לנרמל ל-UTC בגבול ולאכוף `|lag|≤threshold`.

### NOT-DONE / פערים
- **צילום לא נשמר לדיסק:** ה-frontend עלה היום ⇒ צולמו צילומי-React אמיתיים (Dashboard `ss_0324e57md` + Build-Status `ss_6148nu00q`), אבל `save_to_disk` עדיין ללא-אפקט ב-session הזה — **אין נתיב-קובץ קבוע**. אם נדרש קובץ — להריץ בסביבה שתומכת ב-persist.
- **counterfactual:** אין signal שזוהה-ונחסם היום — S4 ARMED-BLUE אך אין detection (active_patterns=[]), S2 חסום choppiness_ok (אין detection שעבר), S3 feed-dead. אין signal שעבר detection-ונחסם ⇒ אין מה לחשב. EOD-counterfactual חסום גם ב-I-22.
- **decision_tree woodies** — `NO_SETUP`, A1/A3 SKIP "no patterns this bar" / A5 advisory `calculate_size=reject` בלי setup; אין reject ברמת-תבנית בבר זה.
- **decision_tree woodies** — `NO_SETUP`, A1 SKIP "no patterns" / A5 advisory `calculate_size=reject` בלי setup; אין reject ברמת-תבנית בבר זה.

---

## 🕙 snapshot 10:47 CT (2026-06-08 · 15:47 UTC · ~137 דק' לתוך RTH)

**מצב-על:** ה-frontend **חי** (Dashboard + Build-Status נטענים). ערוץ ה-5דק'/study **חי** היום (woodies_5min/5min_bars/footprint-file FRESH, five_min lag 153.5s). board verdict=**BLOCKED** דרך `bridge_streams_fresh ✗ → dead: tick_reversal_15,tpo`. day_type מסווג **Trend_Normal** ועקבי (state + readiness + S2-gate). trend_state התהפך מ-BLUE(10:11)→**GRAY** (cci_14≈-36.6, חצה חזרה לאזור-האפס; engine+board מסכימים GRAY). 0 fires היום; 3 העסקאות ב-`trades/recent` כולן משישי.

**Latency:** `build/pattern-status` = **90ms** (200, len 86702); 7 שאר ה-endpoints 16–32ms. נקי.

**ערכים גולמיים (raw):**
- **woodies/current:** `cci_14=-36.58 · tcci=-18.45 · ema_34=7455.62 · lsma=7466.65 · swi=-34.15 · czi=8 · trend_state=GRAY · signal=NEUTRAL · active_patterns=[] · NO_SETUP · buffer=50 · running/hydrated=true`. decision_tree: A1 SKIP "no patterns" · A2 PASS "11 studies present" · A3 SKIP "no patterns this bar" · A4 SKIP · A5 PASS "advisory:calculate_size=reject" · A6 SKIP NO_SETUP · A7 SKIP.
- **day_type/state:** `stage=B2 · day_type=Trend_Normal · confidence=0.38 · lock=PENDING · opening_type=UNKNOWN · ib_width=WIDE · behavior=DEVELOPING · range=NORMAL · session_min=0`.
- **five_min/current:** `running · DAY_TYPE_MODE · buffer_size=3 · opening_type=OPEN_DRIVE · patterns_detected=0 · setups_published=0`. data_freshness `last_bar=2026-06-08 18:45:00+03:00 (=10:45 CT) · lag=153.5s · fresh=true · thr=660`. gate `nt_day_type` present=true value=Trend_Normal satisfied.
- **footprint/current:** `bars_processed_today=0 · buffer_size=0 · aggressive_flow=null · delta=null · cumulative_delta=0 · NO_SETUP`. data_freshness `last_bar=null · fresh=false · thr=360`.
- **gateway/status:** `shadow_active_count=0 · trades_today=0 · daily_pnl=0 · demo_enabled=[2,4] · live_enabled=[] · chop_state=FOUND · cooldown/cluster/ssv inactive`.
- **trades/recent (3, כולן שישי):** id=13 SHORT $66.88/**26.75R** (e7414.25) · id=12 SHORT $20/**16R** (e7443.75) · id=10 SHORT $230/**92R** (e7444).
- **bridge global_gates (streams):** woodies_5min Present✓ (ts 18:45 IL-local) · footprint Present✓ (ts 18:47 IL-local, נכתב עכשיו) · cumulative_delta Present✓ lag154s (UTC) · volume_profile Present✓ lag2.5s · **tick_reversal_15 Present✗ lag258974s (~72h, ts 2026-06-05 10:51 CT)** · imbalance Present✓ lag133s · **tpo Present✗ (ts 2023-11-25, S5 לא-מחווט)** · bars_5min Present✓. bridge `data_freshness: last_bar=null · lag=-10646s (~-3h) · fresh=true · thr=90`.
- **readiness:** verdict=**BLOCKED** "dead: tick_reversal_15,tpo" · `bridge_streams_fresh ✗(block)` · `s1_day_type_classified ✓ Trend_Normal` · `s4_trend_not_stuck_gray ✗ GRAY` · `in_rth ✓`.

**צילומי-מסך (frontend חי):** Dashboard = **`ss_5329t09mn`** · Build-Status / עץ-החלטות = **`ss_9896u7cr0`** (chain: verdict BLOCKED → Day Type × stale → S3 BLOCKED → Footprint × stale → ✓ Woodies CCI · ✓ Min Patterns-5 · ✓ Bridge·Streams; "dead: tick_reversal_15,tpo"; risk_checks LIVE-caps כולם ✗; pre_fire_validator 7×✗). **הערה:** `save_to_disk` ללא-אפקט ב-session ⇒ אין נתיב-קובץ קבוע, רק ID inline.

### בדיקה עמוקה — S2 (five_min) · 5 שאלות

| תבנית | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| REACTIVE_LONG | כן (b1 close 7458/open 7452 bull, vol 31) | כן | **לא נחסם — armed**, awaiting detection `b1 sellers` | N/A (אין setup) | — |
| REACTIVE_SHORT | כן (b2 vol 13185 · b1 vol 31 · ratio 425 ✗) | כן | armed, awaiting `b2 volume_drop` | N/A | — |
| INITIATIVE_LONG | כן (b1 range 6.75) | כן | armed, awaiting `b1 expansion` — range 6.75 **מחוץ** [4.5,6.0] (רחב מדי) | כן (detection לגיטימי) | — |
| INITIATIVE_SHORT | כן (range 6.75) | כן | armed, awaiting `b1 expansion` (range רחב מדי) | כן | — |
| BULL_FLAG_LONG | כן (flag 10 ברים) | כן | armed, awaiting `flag length` — 10 ברים מחוץ [3,8] (ארוך מדי) | כן | — |
| BEAR_FLAG_SHORT | כן | כן | armed, awaiting `pole found` (need ≥5 bearish, ≥4pt) | כן | — |
| INV_HNS_LONG | כן | כן | **BLOCKED** — `Auth Table SKIP × Trend_Normal` | כן — day-pattern reversal לא-מורשה ב-Trend_Normal (auth-table) | — |
| HNS_TOP_SHORT | כן | כן | **BLOCKED** — `Auth Table SKIP × Trend_Normal` | כן | — |
| DOUBLE_BOTTOM_EE_LONG | כן | כן | **BLOCKED** — `Auth Table SKIP × Trend_Normal` | כן | — |
| DOUBLE_TOP_AA_SHORT | כן | כן | **BLOCKED** — `Auth Table SKIP × Trend_Normal` | כן | — |

**מסקנת-S2:** 6 תבניות מומנטום/flag **armed** וממתינות ל-detection אמיתי (ערכי-בר הגיוניים); 4 תבניות-יום חסומות **לגיטימית** ב-Auth-Table×Trend_Normal. **`choppiness_ok` אינו חוסם בסנאפ-שוט זה** (I-16 לא משחזר) — היפוך מ-10:11 שבו חסם את כל 10. day_type_gate satisfied (Trend_Normal) ⇒ הטענה ש-I-1 "משתק S2" מופרכת שוב. אין detection שעבר-ונחסם ⇒ אין counterfactual.

### בדיקה עמוקה — S3 (footprint) · 5 שאלות

| תבנית | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| ABSORPTION | **לא** (0 ברים) | N/A | `Insufficient buffer (0, need ≥5)` | כן (אין נתון) | ingest file→buffer (I-11) |
| STACKED_IMBALANCE | לא | N/A | `Insufficient buffer (0, need ≥5)` | כן | I-11 |
| SWEEP_RETURN | לא | N/A | `Insufficient buffer (0, need ≥5)` | כן | I-11 |
| EXHAUSTION | לא | N/A | `Insufficient buffer (0, need ≥5)` | כן | I-11 |

**מסקנת-S3:** כל 4 התבניות un-armable — feed מת (0 ברים) למרות שקובץ-היצוא **נכתב עכשיו** (gate footprint ts 18:47, נכתב ברגע הסנאפ-שוט). שבר ingest file→bridge→buffer, **עצמאי מ-I-21** (ערוץ 5דק' חי היום). = I-11, אישור 17.

### בדיקה עמוקה — S4 (woodies) · 5 שאלות

| תבנית | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| ZLR · TLB · TT · GB100 · Vegas/Cup · CCI-H&S · FAMIR(±200) · HTLB · HFE (כל 9) | כן (cci_14=-36.58, 11 studies present, buffer 50, ערוץ חי) | כן (CCI סביב-אפס ⇒ GRAY שפוי) | **Stage A1 veto: `trend_state=GRAY`** (GREY/YELLOW/INDETERMINATE — Woodies WSI rule), **לפני** A3-detection | כן — A1-GRAY veto לגיטימי לפי כלל-WSI (אין מסחר Woodies ב-trend לא-מוכרע). מנוע+לוח מסכימים GRAY (לא תקלת-C-1) | — |

**מסקנת-S4:** כל 9 התבניות חסומות ב-A1-GRAY veto אמיתי. engine `trend_state=GRAY` ו-board `s4_trend_not_stuck_gray ✗ GRAY` **מסכימים** ⇒ C-1 (קונפליקט מנוע↔לוח) **לא משחזר**. A5 advisory `calculate_size=reject` קיים אך A1 הוא החסם. אין setup ⇒ אין counterfactual.

### עדכון-חשודים — snapshot 10:47 CT

| # | ממצא 10:47 | סטטוס |
|---|-----------|-------|
| I-1 (day_type) | **לא חוסם S2.** state+readiness+S2-gate מסכימים **Trend_Normal** (אין פיצול-3-כיווני בסנאפ-שוט זה). residual נמשך: `opening_type=UNKNOWN` ב-state בעוד five_min+UI=**OPEN_DRIVE**, ו-`session_min=0` ב-~137דק' לתוך RTH (instance לא-עוקב-סשן). Dashboard מציג `Y IB dll_missing` = חשוד-שורש | 🟡 |
| I-2 (A5 "חוסם") | A5 = `advisory:calculate_size=reject` (PASS) — לא חוסם. אישור-תצוגה תקין | 🟡 (יציב) |
| I-3 (ZLR) | trend התהפך ל-**GRAY** ⇒ ZLR חסום ב-`Stage A1 veto: GRAY` **לפני** A3-detection (לא armed הפעם, שלא כמו 10:11 ב-BLUE). אין setup, אין counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | **אישור 17 + עצמאות מאוששת:** gate footprint Present✓ ts 18:47 (נכתב עכשיו) בעוד ערוץ 5דק' **חי** — ועדיין 0 ברים/buffer 0/flow null, 4 תבניות "Insufficient buffer". file→bridge→buffer שבור, עצמאי מ-I-21 | 🔴 |
| I-12 (A5 details ריק) | decision_tree A5 PASS advisory בלי setup; `details{}` ריק — לא ניתן לבדוק reject-context בלי setup חי | 🟡 |
| I-13 (sizing מפספס) | NO_SETUP, A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing לכייל | 🔴 (לא נצפה) |
| I-14 (הרצת-פתיחה) | opening_type=OPEN_DRIVE (לא REJECTION היום); INITIATIVE_L/S **armed** (auth FULL), חוסמות רק על `b1_expansion` range 6.75 רחב-מדי. חסם-auth נוקה. שרשרת opening→entry עדיין ל-CC | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר:** מנוע `trend_state=GRAY` (cci_14=-36.58, חצה לאזור-אפס) + לוח `s4_trend_not_stuck_gray ✗ GRAY` — **מסכימים**. אין קונפליקט. **פער-UI:** פאנל Woodies-CCI מציג `CCI -23.79 / TrendDown 1.00 / CCIDiff 4.78` מול endpoint cci_14=-36.58 — skew-תצוגה (~13pt + TrendDown≠GRAY). הצלבת Sierra חובה | 🔬 |
| I-16 (choppiness_ok) | **לא משחזר:** 6 תבניות-S2 armed וממתינות detection, 4 חסומות Auth-Table×Trend_Normal. **אין "Missing: choppiness_ok".** היפוך מ-10:11 (שם חסם כל 10) ⇒ מחזק I-17 (תנודתיות-גבול-בר). gateway chop_state=FOUND, UI strip "28 EXPANDING" | 🔴 |
| I-17 (restart/buffer-volatility) | five_min buffer=3 (נמוך — מרמז reset/early-bar), אך ערוץ חי (lag 153s). היפוך choppiness_ok 10↔present תומך בהשערת תנודתיות-גבול-בר | 🔬 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min/footprint/bars_5min נושאים IL-local (18:4x) מסומן `+00:00`/lag=undefined; cumulative_delta/volume_profile/imbalance ב-UTC תקין (15:4x). מפר Rule 4 | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 90ms (200). 7 שאר endpoints 16–32ms | 🔴 (לסירוגין, נקי) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10646/fresh=true/threshold=90` (lag שלילי ~-3h). ה-predicate לא אוכף סף. readiness משתמש ב-gates → BLOCKED נכון | 🟡 |
| I-21 (5דק'/tick stall) | **5דק'/study חי** (woodies_5min/5min_bars/footprint-file FRESH, five_min lag 153.5s, CCI נע -37.85→-36.58). `tick_reversal_15` עדיין **DEAD מ-שישי 10:51 CT** (lag ~72h, session-non-start) + tpo DEAD → board BLOCKED `dead: tick_reversal_15,tpo`. הפיצול נשאר tick_reversal_15-בלבד. CC: למה tick_reversal_15 לבדו לא עולה | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי: id=10 92R ($230), id=13 26.75R ($66.88), id=12 16R ($20). אין עסקה-טרייה היום. חוסם EOD-counterfactual | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active_count=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)

- **`cci_14=-36.58` / `trend_state=GRAY`** — להצליב WSI/CCI-14/TCCI גולמי מול ה-export; לאמת ש-GRAY תואם את ה-study (CCI סביב-אפס).
- **פער-UI Woodies-CCI** (I-15) — פאנל מציג `CCI -23.79 / TrendDown 1.00 / CCIDiff 4.78` מול endpoint `cci_14=-36.58 / GRAY`; CC לברר מקור-ה-skew (מדד-נגזר שונה? בר אחר?) ולקבוע מקור-אמת אחד.
- **`Y IB dll_missing`** (Dashboard) — CC: למה ה-DLL לא מחזיר yesterday-IB/atr_daily; חשוד-שורש ל-`opening_type=UNKNOWN`+`session_min=0` (I-1 residual).
- **footprint file FRESH אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer; עצמאי מ-I-21.
- **tick_reversal_15 session-non-start** (I-21) — CC: למה לא עלה ב-פתיחת 08:30 CT בעוד woodies_5min/footprint/CVD/volume_profile/imbalance כן עלו.
- **choppiness_ok score≠gate-flag** (I-16) — הדגל present לסירוגין; CC לחווט דגל-בוליאני יציב מ-chop_state ולהחליט אם chop גבוה אמור לחסום (תיוג "chop גבוה" לא "Missing").
- **TZ-mislabel בגייטים** (I-18/I-20) — IL-local מסומן `+00:00`; CC לנרמל ל-UTC בגבול ולאכוף `|lag|≤threshold`.

### NOT-DONE / פערים
- **צילום לא נשמר לדיסק:** ה-frontend עלה היום ⇒ צולמו צילומי-React אמיתיים (Dashboard `ss_5329t09mn` + Build-Status `ss_9896u7cr0`), אבל `save_to_disk` ללא-אפקט ב-session הזה — **אין נתיב-קובץ קבוע**, רק ID inline.
- **counterfactual:** אין signal שזוהה-ונחסם היום — S4 חסום A1-GRAY (active_patterns=[]), S2 כל ה-armed ממתינות detection שטרם-עבר, S3 feed-dead. אין detection שעבר-ונחסם ⇒ אין מה לחשב. EOD-counterfactual חסום גם ב-I-22 (pnl_r מנופח).
- **decision_tree woodies** — `NO_SETUP`, A1/A3 SKIP "no patterns this bar" / A5 advisory `calculate_size=reject` בלי setup; אין reject ברמת-תבנית בבר זה.

---

## Snapshot 11:05 CT (2026-06-08) — ~155 דק' לתוך RTH · scheduled pattern-diag-30min

**מקור:** API דרך Chrome (`localhost:8000`) · Dashboard+Build-Status frontend (`localhost:3000` — **עלה היום**). שעה: pattern-status ts `2026-06-08T16:04:36Z` = **11:04 CT**.

### בריאות-endpoints (latency)
כל 7 ה-endpoints ענו **<100ms**: woodies 17ms · footprint 30ms · five_min 39ms · five_min/stats 41ms · trades 74ms · gateway 36ms · day_type 73ms. **`build/pattern-status` = 80ms (200, len 85374)** ⇒ **I-19 לא משחזר** (snapshot נקי, ה-hang לסירוגין).

### ערכים גולמיים (raw)
- **woodies/current:** `cci_14=-102.3` (נע: -105.78→-102.3 בין 2 fetches ⇒ **ערוץ חי, לא קפוא**), `tcci=-95.61`, `ema_34=7455.45`, `lsma=7463.83`, `swi=-73.74`, `czi=-12`, `trend_state=RED`, `signal=NEUTRAL`, `active_patterns=[]`, `NO_SETUP`, buffer 50. decision_tree: A1 SKIP "no patterns" · A2 **PASS "11 studies present"** · A3 SKIP "no patterns this bar" · A5 PASS `advisory:calculate_size=reject` · A6/A7 SKIP.
- **five_min/current:** `mode=DAY_TYPE_MODE`, buffer 12, `opening_type=OPEN_DRIVE`, no pattern. stats: `patterns_detected=0`, `setups_published=0`.
- **footprint/current:** `bars_processed_today=0`, buffer 0, `aggressive_flow=null`, `cumulative_delta=0`, all flow null, `last_fire=null`.
- **day_type/state:** `stage=B2`, `day_type=Trend_Normal`, `confidence=0.38`, `lock=PENDING`, `opening_type=UNKNOWN`, `ib_width=WIDE`, `behavior=DEVELOPING`, **`session_min=0`**.
- **gateway/status:** `trades_today=0`, `daily_pnl=0`, `shadow_active_count=0`, `demo_enabled=[2,4]`, `live_enabled=[]`, cooldown inactive (0 stops).
- **trades/recent:** 3 עסקאות — **כולן משישי 06-05**: id=13 SHORT $66.88=**26.75R**, id=12 SHORT $20=**16R**, id=10 SHORT $230=**92R**. אין עסקה-טרייה היום.
- **readiness:** verdict **BLOCKED** reason `dead: tick_reversal_15,tpo`. `bridge_streams_fresh ✗ block` · `s1_day_type_classified ✓ Trend_Normal` · `s4_trend_not_stuck_gray ✓ RED` · `in_rth ✓`.
- **bridge global_gates:** woodies_5min `[FRESH] ts 19:00:00+00:00 lag_s=null` · footprint `[FRESH] ts 19:04:34 lag_s=null` · cumulative_delta `UTC 16:00:00 lag 276s` · volume_profile `UTC 16:04:35 lag 1.4s` · **tick_reversal_15 `[DEAD] 4333min · 06-05 15:51:19 lag 259997s`** · imbalance `Present lag 1156s (~19min)` · tpo `[DEAD]`. bridge aggregate `data_freshness: lag_seconds=-10523.6, fresh=true, threshold=90`.

### 5-השאלות — תבניות S2 (five_min)

| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| REACTIVE_LONG/SHORT | כן (mode DAY_TYPE, buffer 12, opening OPEN_DRIVE) | כן | **`data.choppiness_ok`** + detection (b2_volume_drop / b1_buyers) | choppiness_ok — **לא** (פער חיווט, ראה I-16) | דגל choppiness_ok בוליאני |
| INITIATIVE_LONG/SHORT | כן | כן | `data.choppiness_ok` + `detection.b1_expansion` | detection לגיטימי; choppiness_ok לא | choppiness_ok |
| INV_HNS · HNS_TOP · DOUBLE_BOTTOM_EE · DOUBLE_TOP_AA · BULL/BEAR_FLAG | כן | כן | `day_type_gate.auth_table_cell` + `data.choppiness_ok` + detection (swing/eve/neckline/pole) | auth×Trend_Normal לגיטימי לתבניות-יום; choppiness_ok לא | choppiness_ok |

**מסקנת-S2:** **כל 10 התבניות חסומות**. choppiness_ok חוזר כ-Missing וחוסם את כולן (כולל reactive/initiative) ⇒ **I-16 משחזר** (היפוך מ-10:47 שם 6 היו armed) — מחזק I-17 (תנודתיות-גבול-בר). day_type_gate **כן present** (Trend_Normal) — חוסם רק 6 תבניות-יום ב-auth, לגיטימי.

### 5-השאלות — תבניות S4 (woodies)

| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| ZLR·TLB·TT·GB100·Vegas/Cup·CCI-H&S·FAMIR·HTLB·HFE (כל 9) | כן (cci_14=-102.3 נע, 11 studies, buffer 50) | כן (CCI≈-102 ⇒ RED שפוי) | **armed** — `detection.pattern_specific` (A3 "no patterns this bar") | לא חוסם — פשוט אין setup בבר זה | — |

**מסקנת-S4:** כל 9 **armed** (trend RED, לא GRAY כמו 10:47 ⇒ אין A1-veto הפעם), חוסמות רק על היעדר-detection בבר. ZLR armed "not yet detected", active_patterns=[] ⇒ **I-3 אין counterfactual**. A5 advisory reject בלי setup.

### 5-השאלות — תבניות S3 (footprint)

| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך? | 5.מה חסר? |
|-------|-----------|-----------|-----------|---------|-----------|
| ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION | **לא** (0 ברים, buffer 0, flow null) | לא-רלוונטי | "Insufficient buffer (0, need ≥5)" — אין ingest | — | **ingest footprint שבור** (I-11) |

### עדכון-חשודים — snapshot 11:05 CT

| # | ממצא 11:05 | סטטוס |
|---|-----------|-------|
| I-1 (day_type) | **לא חוסם S2.** state+readiness+board+Dashboard+S2-gate מסכימים **Trend_Normal** (אין פיצול-3-כיווני). residual: `opening_type=UNKNOWN` ב-state בעוד five_min+UI=**OPEN_DRIVE**, ו-`session_min=0` ב-~155דק'. Dashboard `Y IB dll_missing` = חשוד-שורש | 🟡 |
| I-2 (A5 "חוסם") | A5 `advisory:calculate_size=reject` (PASS) — לא חוסם. תצוגה תקינה | 🟡 (יציב) |
| I-3 (ZLR) | trend **RED** (≠GRAY של 10:47) ⇒ ZLR **armed** "not yet detected", active_patterns=[] (A3 no pattern this bar). אין setup, אין counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | **אישור 18 + עצמאות מאוששת:** gate footprint `[FRESH] ts 19:04:34` (נכתב עכשיו) בעוד ערוץ 5דק'/woodies **חי** (cci נע) — ועדיין 0 ברים/buffer 0/flow null, 4 תבניות "Insufficient buffer". file→bridge→buffer שבור, עצמאי מ-I-21 | 🔴 |
| I-12 (A5 details ריק) | A5 PASS advisory בלי setup; `details{}` ריק — לא ניתן לבדוק reject-context | 🟡 |
| I-13 (sizing מפספס) | NO_SETUP, A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing לכייל | 🔴 (לא נצפה) |
| I-14 (הרצת-פתיחה) | opening_type=OPEN_DRIVE; INITIATIVE_L/S חסומות על `choppiness_ok`+`b1_expansion` (לא auth — auth FULL). שרשרת opening→entry ל-CC | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר (קונפליקט):** מנוע `trend_state=RED` (cci_14=-102.3) + board `s4_trend_not_stuck_gray ✓ RED` — **מסכימים**. **פער-UI נמשך + גדל:** פאנל Woodies-CCI מציג `CCI -52.4/-60.6 · CCIDiff 23.61 · TrendDown 1.00` מול endpoint `cci_14=-102.3` (~42–50pt skew). הצלבת Sierra חובה | 🔬 |
| I-16 (choppiness_ok) | **משחזר — חוסם כל 10:** כל תבניות-S2 חסומות `data.choppiness_ok` (כולל reactive/initiative). היפוך מ-10:47 (6 armed) ⇒ פער score≠gate-flag חוזר. gateway/UI chop=27 EXPANDING (score קיים). CC: לחווט דגל-בוליאני יציב | 🔴 |
| I-17 (buffer-volatility) | five_min buffer=12 (≠3 ב-10:47); היפוך choppiness_ok present↔Missing בין סנאפ-שוטים על ערוץ חי ⇒ תומך בתנודתיות-גבול-בר | 🔬 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min/footprint נושאים IL-local (`19:0x`) מסומן `+00:00`/`lag_s=null`; cumulative_delta/volume_profile ב-UTC תקין (`16:0x`). `imbalance` Present אך lag **1156s (~19min) > 90s req** = stale-but-Present. מפר Rule 4 | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 80ms (200, len 85374). שאר endpoints <75ms. נקי | 🔴 (לסירוגין) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10523.6/fresh=true/threshold=90` (lag שלילי ~-2.9h). predicate לא אוכף סף. readiness משתמש ב-gates → BLOCKED נכון | 🟡 |
| I-21 (5דק'/tick stall) | **5דק'/study/footprint-file חי** (woodies_5min/footprint FRESH, cci נע -105.78→-102.3, five_min buffer 12). `tick_reversal_15` עדיין **DEAD מ-שישי 06-05 15:51** (lag 4333min ~72h, session-non-start) + tpo DEAD → board BLOCKED `dead: tick_reversal_15,tpo`. הפיצול נשאר tick_reversal_15-בלבד. CC: למה tick_reversal_15 לבדו לא עולה | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי: id=10 92R ($230), id=13 26.75R ($66.88), id=12 16R ($20). אין עסקה-טרייה היום. חוסם EOD-counterfactual | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active_count=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |

### צילומי-מסך (Build Status / decision-tree)
ה-frontend עלה ⇒ צולמו צילומי-React חיים:
- **Dashboard** `ss_44033m1wi` — price 7453.25 live (1s ago), SHADOW, OPEN_DRIVE/Trend_Normal 38%, IB 7469.50/7429.00 **40.5pt WIDE**, **`Y IB dll_missing`**, chop **27 EXPANDING**, Woodies-CCI panel `CCI -52.4/-60.6 CCIDiff 23.61 TrendDown 1.00`, FIRING: S2 IDLE / S3 — / S4 NEUT, No Active Trade.
- **Build Status (עץ-החלטות)** `ss_45849pkir` — verdict **BLOCKED** · banner `dead: tick_reversal_15,tpo` · chain: `verdict BLOCKED → ? Day Type × stale → S3 BLOCKED → ? Footprint × stale → ✓ Woodies CCI → ✓ Min Patterns-5 → ✓ Bridge·Streams` · heartbeat <1s · RTH פתוח 233m-לסגירה · Day Type Trend_Normal · Killzone לא-מחזור.
- **הערה:** `save_to_disk` ללא-אפקט ב-session זה ⇒ אין נתיב-קובץ קבוע, רק ID inline.

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)
- **`cci_14=-102.3 / trend_state=RED`** — להצליב CCI-14/TCCI/WSI גולמי; לאמת RED.
- **פער-UI Woodies-CCI** (I-15) — פאנל `-52.4/-60.6` מול endpoint `-102.3` (~50pt); CC לקבוע מקור-אמת אחד.
- **`Y IB dll_missing`** — CC: למה DLL לא מחזיר yesterday-IB/atr_daily; חשוד-שורש ל-`opening_type=UNKNOWN`+`session_min=0` (I-1).
- **footprint file FRESH אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer; עצמאי מ-I-21.
- **tick_reversal_15 session-non-start** (I-21) — DEAD מ-שישי; CC למה לבדו לא עלה ב-08:30 CT.
- **choppiness_ok score≠gate-flag** (I-16) — חוסם כל 10 בסנאפ-שוט זה; CC לחווט דגל-בוליאני יציב.
- **TZ-mislabel** (I-18/I-20) — IL-local מסומן `+00:00`; CC לנרמל ל-UTC + לאכוף `|lag|≤threshold`.

### NOT-DONE / פערים
- **counterfactual:** אין signal שזוהה-ונחסם — S4 armed בלי detection, S2 כל 10 חסומות לפני detection (choppiness_ok), S3 feed-dead. אין detection שעבר-ונחסם ⇒ אין מה לחשב. EOD-counterfactual חסום גם ב-I-22.
- **צילום לדיסק** — לא נתמך ב-session (ID inline בלבד).

---

## Snapshot 11:43 CT (2026-06-08) — ~193 דק' לתוך RTH · scheduled pattern-diag-30min

**מקור:** API דרך Chrome (`localhost:8000`) · Dashboard frontend (`localhost:3000` — **חי**). שעה: pattern-status ts `2026-06-08T16:42:49Z` = **11:42 CT**.

### בריאות-endpoints (latency)
כל 7 ה-endpoints ענו **<100ms**: woodies 33ms · footprint/five_min/stats/gateway/day_type כולם <75ms. **`build/pattern-status` = 94ms (200, len 86477)** ⇒ **I-19 לא משחזר** (snapshot נקי, ה-hang לסירוגין; 6 סנאפ-שוטים רצופים היום נקיים).

### ערכים גולמיים (raw)
- **woodies/current:** `cci_14=-156.27→-161.2` (**נע בין 2 fetches ⇒ ערוץ חי, CCI un-frozen**, בניגוד ל-stall ההיסטורי), `tcci=-106→-109`, `ema_34=7453.3`, `lsma=7447`, `swi=-138→-143`, `czi=-49→-54`, `trend_state=RED`, `predictor=-172→-182`, `signal=NEUTRAL`, `active_patterns=[]`, `NO_SETUP`, buffer 50. decision_tree: A1 SKIP "no patterns" · **A2 PASS "11 studies present"** · A3 SKIP "no patterns this bar" · A4 SKIP · A5 PASS `advisory:calculate_size=reject` · A6/A7 SKIP.
- **five_min/current:** `mode=DAY_TYPE_MODE`, buffer **31** (עלה מ-12@11:05), `opening_type=OPEN_DRIVE`, no pattern. stats: `patterns_detected=0`, `setups_published=0`. (FHB-state לא נחשף ב-`/current` ולא ב-`/stats` — ראה NOT-DONE.)
- **footprint/current:** `bars_processed_today=0`, buffer 0, `aggressive_flow=null`, `cumulative_delta=0`, all flow null, `last_fire=null`.
- **day_type/state:** `stage=B2`, `day_type=Trend_Normal`, `confidence=0.38`, `lock=PENDING`, `opening_type=UNKNOWN`, `ib_width=WIDE`, `behavior=DEVELOPING`, **`session_min=0`** (ב-~193דק' לתוך RTH).
- **gateway/status:** `trades_today=0`, `daily_pnl=0`, `shadow_active_count=0`, `demo_enabled=[2,4]`, `live_enabled=[]`, cooldown inactive (0 stops), cluster-guard/SSV לא-פעילים.
- **trades/recent:** 3 עסקאות — **כולן משישי 06-05**: id=13 SHORT $66.88=**26.75R**, id=12 SHORT $20=**16R**, id=10 SHORT $230=**92R**. אין עסקה-טרייה היום.
- **readiness:** verdict **BLOCKED** reason `dead: tick_reversal_15,tpo`. `bridge_streams_fresh ✗` · `s1_day_type_classified ✓ Trend_Normal` · `s4_trend_not_stuck_gray ✓ RED` · `in_rth ✓`.
- **bridge global_gates (8 זרמים):** woodies_5min `[FRESH] 0s · 2026-06-08 19:40:00` ts מסומן `+00:00` (IL-local!) `lag_s=null` · footprint `[FRESH] 0s · 19:41:41` IL-local `lag_s=null` (**קובץ נכתב עכשיו**) · cumulative_delta `UTC 16:39:59 lag 108s` · volume_profile `UTC 16:41:46 lag 1.1s` · **tick_reversal_15 `[DEAD] 4370min · 06-05 15:51:19 lag 262228s (~72h)`** · imbalance `Present UTC 16:40:05 lag 102s` · tpo `[DEAD] 2023-11-25` · bars_5min `[FRESH] 19:40:00` IL-local. system-level df: five_min/woodies `last_bar_ts=2026-06-08 19:40:00+03:00, lag 61.1s, fresh=true`; bridge aggregate `last_bar_ts=null, lag_seconds=-10738.9, fresh=true, threshold=90`.

### 5-השאלות — תבניות S2 (five_min)

| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| REACTIVE_LONG/SHORT | כן (mode DAY_TYPE, buffer 31, opening OPEN_DRIVE) | כן | **armed** — detection בלבד (b2_volume_drop / b1_buyers) | לא חוסם — אין setup בבר | — |
| INITIATIVE_LONG/SHORT | כן | כן | **armed** — `detection.b1_expansion` בלבד | detection לגיטימי | — |
| BULL_FLAG / BEAR_FLAG | כן | כן | **armed** — detection (flag_length / pole_found) | לא חוסם | — |
| INV_HNS · HNS_TOP · DOUBLE_BOTTOM_EE · DOUBLE_TOP_AA | כן | כן | `day_type_gate.auth_table_cell` + detection (hns_structure/swing_highs/eve_variant) | **כן** — auth×Trend_Normal לגיטימי לתבניות-יום | — |

**מסקנת-S2:** **6/10 armed** (REACTIVE×2, INITIATIVE×2, FLAGS×2), 4 תבניות-יום חסומות לגיטימית ב-`auth_table_cell`×Trend_Normal. **אין `data.choppiness_ok` באף blocker** ⇒ **I-16 לא משחזר** (היפוך חד מ-11:05 שם כל 10 נחסמו על choppiness_ok) — מחזק חזק את **I-17 (תנודתיות-גבול-בר)**: 0-armed↔6-armed↔10-blocked בין סנאפ-שוטים על ערוץ חי. day_type_gate present (Trend_Normal), עקבי עם state+readiness ⇒ אין פיצול-3-כיווני.

### 5-השאלות — תבניות S4 (woodies)

| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|-------|-----------|-----------|-----------|----------------|-----------|
| ZLR·TLB·TT·GB100·HFE·HTLB·FAMIR (כל 7) | כן (cci_14=-161 נע, 11 studies, buffer 50) | כן (CCI≈-161 ⇒ RED שפוי) | **armed** — `detection.pattern_specific` (A3 "no patterns this bar") + targets_stop/exit_rules downstream | לא חוסם — אין setup בבר | — |

**מסקנת-S4:** כולן **armed** (trend RED יציב, **לא** GRAY ⇒ אין A1-veto), חוסמות רק על היעדר-detection בבר. **I-3 (ZLR):** armed "Data ready, trend RED · not yet detected", active_patterns=[] ⇒ **אין counterfactual** (לא נדרך setup-ZLR טרי). A5 advisory `calculate_size=reject` בלי setup לחסום ⇒ **I-12/I-13 אין ממצא-sizing לכייל**.

### 5-השאלות — תבניות S3 (footprint)

| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך? | 5.מה חסר? |
|-------|-----------|-----------|-----------|---------|-----------|
| ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION | **לא** (0 ברים, buffer 0, flow null, ts=null/fresh=false) | לא-רלוונטי | `data.buffer_size` + `data.bars_today` (0, need ≥5) | — | **ingest footprint שבור** (I-11) |

**מסקנת-S3:** כל 4 un-armable. gate `footprint`=**[FRESH] 0s · 19:41:41** (קובץ נכתב **ברגע זה**) בעוד `bars_processed_today=0` ⇒ **הוכחת-עצמאות חוזרת ל-I-11**: file→bridge→buffer שבור, **עצמאי מ-I-21** (ערוץ 5דק' חי הפעם). אישור #19 רצוף.

### עדכון-חשודים — snapshot 11:43 CT

| חשוד | ממצא 11:43 | סטטוס |
|------|-----------|-------|
| I-1 (day_type) | state=`Trend_Normal/B2/conf 0.38/lock PENDING`, **עקבי עם readiness+S2-gate** (אין פיצול) — **לא חוסם S2**. residual: `opening_type=UNKNOWN` (מול five_min/UI `OPEN_DRIVE`) + **`session_min=0`** ב-~193דק'. Dashboard `Y IB dll_missing` = חשוד-שורש | 🟡 |
| I-2 (A5 חוסם) | A5 PASS advisory (calculate_size=reject) — לא חוסם. תקין | 🟡 |
| I-3 (ZLR) | armed "trend RED · not yet detected", active_patterns=[] (A3 no pattern this bar). אין setup/counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | אישור #19 — gate FRESH `19:41:41` (נכתב עכשיו) בעוד ערוץ 5דק' חי — עדיין 0 ברים/buffer 0/flow null. **עצמאי מ-I-21, ingest-break מוכח** | 🔴 |
| I-12 (A5 details ריק) | NO_SETUP — אין reject-context לבדוק בלי setup | 🟡 |
| I-13 (sizing מפספס) | NO_SETUP, A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing | 🔴 (לא נצפה) |
| I-14 (הרצת-פתיחה) | opening_type=OPEN_DRIVE; INITIATIVE_L/S **armed** (auth FULL, חוסמות רק על b1_expansion). חסם-auth נוקה. שרשרת opening→entry ל-CC | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר (קונפליקט):** מנוע `trend_state=RED` (cci_14=-161, נע) + board `s4_trend_not_stuck_gray ✓ RED` — **מסכימים**. **פער-UI נמשך:** פאנל Woodies-CCI `CCI≈-145.08 · CCIDiff 13.56 · -107.4/-125.9 · TrendDown 1.00` מול endpoint `cci_14=-156→-161` (~15–35pt skew). הצלבת Sierra חובה | 🔬 |
| I-16 (choppiness_ok) | **לא משחזר:** 6/10 תבניות-S2 armed, 4 חסומות auth×Trend_Normal. **אין 'Missing: choppiness_ok'.** היפוך מ-11:05 (כל 10 נחסמו) ⇒ מחזק I-17 | 🔴 (לא נצפה) |
| I-17 (buffer-volatility) | five_min buffer=31 (≠12@11:05); choppiness_ok התהפך Missing→present בין סנאפ-שוטים על ערוץ חי ⇒ תומך חזק בתנודתיות-גבול-בר | 🔬 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min/footprint/bars_5min נושאים IL-local (`19:4x`) מסומן `+00:00`/`lag_s=null`; cumulative_delta/volume_profile/imbalance ב-UTC תקין (`16:4x`, lag 1–108s). מפר Rule 4 | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 94ms (200, len 86477). שאר endpoints <75ms. נקי | 🔴 (לסירוגין) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10738.9/fresh=true/threshold=90` (lag שלילי ~-3h). predicate לא אוכף סף. readiness משתמש ב-gates → BLOCKED נכון | 🟡 |
| I-21 (5דק'/tick stall) | **ערוץ 5דק'/study/footprint-file חי** (woodies_5min/footprint/bars_5min FRESH, system df lag **61.1s אמיתי**, CCI un-frozen נע -156→-161, buffer 31). `tick_reversal_15` עדיין **DEAD מ-שישי 06-05 15:51 (4370min ~72h, session-non-start)** + tpo DEAD → board BLOCKED. הפיצול נשאר tick_reversal_15-בלבד | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי: id=10 92R ($230), id=13 26.75R ($66.88), id=12 16R ($20). אין עסקה-טרייה היום. חוסם EOD-counterfactual | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active_count=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |

### צילום-מסך (Build Status / decision-tree)
ה-frontend **חי** — צולם screenshot של ה-Dashboard החי (computer-use, Chrome tier=read):
- **Dashboard** (inline) — price **7,439.50** live (0.9s ago), SHADOW, `MIDDAY 1:29`, **OPEN_DRIVE / Trend Normal 38%**, IB TODAY H 7469.50 / L 7429.00 **40.5pt WIDE**, **`Y IB dll_missing`**, today POC 7448.75/VAH 7464.25/VAL 7440.75, YEST 7552.75/7359.00 (193.75pt), **20 FOUND · SS NONE**, FIRING: S2(5-Min) **IDLE** / S3 Footprint / S4 **NEUT** Woodies, Day Type/TPO/Killzone observing, S3-panel **NO_SETUP**, Day 26/30 · 8 trades · WR 0%.
- Woodies-CCI panel: `CCI≈-145.08 · CCIDiff 13.56 · TrendDown 1.00 · ProjHigh 7738.25 / ProjLow 7145.50 · -107.4/-125.9` (פער-UI↔endpoint, I-15).
- **הערה:** `save_to_disk` ללא-אפקט ב-session זה ⇒ אין נתיב-קובץ קבוע (התמונה inline בלבד).

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)
- **`cci_14=-156→-161 / trend_state=RED`** — להצליב CCI-14/TCCI/WSI גולמי; לאמת RED.
- **פער-UI Woodies-CCI** (I-15) — פאנל `-145.08/-107.4/-125.9` מול endpoint `-156→-161` (~15–35pt); CC לקבוע מקור-אמת אחד.
- **`Y IB dll_missing`** — CC: למה DLL לא מחזיר yesterday-IB/atr_daily; חשוד-שורש ל-`opening_type=UNKNOWN`+`session_min=0` (I-1).
- **footprint file FRESH (19:41:41) אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer; **עצמאי מ-I-21** (ערוץ 5דק' חי הפעם).
- **tick_reversal_15 session-non-start** (I-21) — DEAD מ-שישי 15:51 (~72h); CC למה לבדו לא עלה ב-08:30 CT בעוד 5דק'/footprint/CVD כן.
- **choppiness_ok score≠gate-flag** (I-16/I-17) — תנודתי בין סנאפ-שוטים; CC לחווט דגל-בוליאני **יציב** מ-chop_state.
- **TZ-mislabel** (I-18/I-20) — IL-local מסומן `+00:00`; CC לנרמל ל-UTC + לאכוף `|lag|≤threshold`.

### NOT-DONE / פערים
- **counterfactual:** אין signal שזוהה-ונחסם — S4 armed בלי detection, 6 S2 armed בלי detection, 4 S2 חסומות auth (לגיטימי), S3 feed-dead. **אין detection שעבר-ונחסם ⇒ אין מה לחשב**. EOD-counterfactual חסום גם ב-I-22 (pnl_r מנופח).
- **FHB-state לא נחשף** — `/five_min/current` ו-`/stats` לא מחזירים FHB-state (ACCUMULATING/EARLY/COMPLETE) ⇒ I-4 (S2 דריכה) נבדק עקיף דרך buffer+armed+patterns_detected בלבד. CC: לחשוף FHB ב-endpoint.
- **צילום לדיסק** — `save_to_disk` לא נתמך ב-session (תמונה inline בלבד).

---

## snapshot 12:27 CT (17:27:08Z · session_date 2026-06-08 · ~237 דק' לתוך RTH)

**RTH:** 08:30–15:00 CT — **בתוך החלון** (12:27 CT). gating-CT תקין (I-9).
**מצב-לוח:** verdict **BLOCKED** · reason `dead: tick_reversal_15,tpo`. readiness: `s1_day_type_classified ✓ Trend_Normal` · `s4_trend_not_stuck_gray ✓ RED` · `in_rth ✓` · `bridge_streams_fresh ✗ dead: tick_reversal_15,tpo`.
**זריזות endpoints:** כל 8 ענו <60ms (woodies 54 · trades 46 · five_min 40 · build/pattern-status **50–121ms**, len 87.8KB). אין hang (I-19 לא משחזר, 7 ריצות רצופות היום נקיות).

### ⭐ ממצא-מרכזי חדש — Woodies HFE זוהה-ונחסם ב-A7 (R:R<1.0) — counterfactual ראשון היום
`/woodies/current`: **active_patterns=[HFE LONG conf 0.70 group REVERSAL]**, entry **7432.75** / stop **7422.25** / targets **[7435.75, 7438.75]**. decision_tree:
A1 PASS (trend RED) · A2 PASS (11 studies) · A3 PASS (patterns=['HFE']) · A4 PASS (advisory degraded: tpo/veto/killzone/layer0 missing; **day_type=Trend_Normal classified conf 0.38**) · A5 PASS (**sizing=half** — לא reject הפעם) · A6 PASS (code=STRATEGIC spec=INITIATIVE) · **A7 FAIL — `R:R < 1.0 (risk=10.50 reward=3.00)`** (owner=pre_fire_validator).

**ניתוח 5-השאלות (HFE):**
1. **יש נתון?** כן — setup מלא + decision_tree מלא A1–A7.
2. **הגיוני?** כן — CCI=-101.64/RED, entry 7432.75 בטווח-שוק, group REVERSAL מתאים ל-LONG מול RED.
3. **מה חסם?** **A7 בדיוק** — `pre_fire_validator: R:R = 3.00/10.50 = 0.29 < 1.0`. risk=entry−stop=10.5pt, reward(T1)=entry→T1=3.0pt בלבד.
4. **צריך לחסום?** **כן, מתמטית מוצדק** — עסקת sub-0.3R היא שלילית-תוחלת. **אבל** זה חושף ממצא-קונפיגורציה: stop 10.5pt מול T1 של 3pt עבור HFE/REVERSAL ⇒ **HFE כמעט-אף-פעם לא יעבור A7** בלי כיול stop/target. תואם memory `project_stop_target_placement_table` (anchor/מרחק-סטופ הם הממד החסר). **CC: לכייל stop/target של HFE — או stop צר-מדי-רחב או targets צמודים-מדי.**
5. **מה חסר?** A4 advisory degraded (tpo/killzone/layer0/veto missing — חלקם ידועים-לא-מחווטים). day_type **כן** זמין (Trend_Normal) ⇒ A5 רץ עם קונטקסט-יום הפעם (sizing=half), שלא כמו 06-05.

**counterfactual (HFE LONG, אילו A7 לא חסם):** entry 7432.75, stop 7422.25 (−10.5pt = −1R), T1 7435.75 (+3pt=+0.29R), T2 7438.75 (+6pt=+0.57R). מחיר-חי בזמן-הסנאפ ≈ **7435.75** (=T1 בדיוק) וטווח-היום 7423–7476. ⇒ סביר ש-T1 (+0.29R) נפגע, T2 אפשרי. **המסקנה:** A7 חסך עסקת sub-1R (מוצדק), אבל המבנה מצביע ש-targets של HFE צמודים-מדי לסטופ — **ממצא-כיול אמיתי, לא רעש**. (⚠️ pnl_r מנופח I-22 ⇒ אסור להסתמך על R-ים מה-DB.)

### S4 · Woodies — טבלת 5-שאלות (9 תבניות)
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|-------|---------|---------|---------|------------|---------|
| **HFE** | כן (active) | כן | **A7 R:R 0.29<1.0** (ראה ⭐ לעיל) | מוצדק; אך כיול stop/target נדרש | A4 advisory degraded |
| ZLR·TLB·TT·GB100·Vegas·Ghost·FAMIR (8) | armed (trend RED) | כן | `detection.pattern_specific` (A3 no pattern this bar) + `targets_stop.r_t1_gate` + `stop_price`/`targets`/`ready_to_route` | מוצדק (אין setup הבר) | — |

**מסקנת-S4:** trend RED ⇒ A1 עבר, כל 9 armed. רק HFE זוהה בפועל (ונחסם A7). היתר ממתינים detection. ה-`r_t1_gate` (=A7 R:R) הוא חוסם רוחבי לכל S4 — מחזק את ⭐.

### S2 · Five-Min — טבלת 5-שאלות (10 תבניות) — I-16 משחזר
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|-------|---------|---------|---------|------------|---------|
| REACTIVE_L/S · INITIATIVE_L/S (4) | ערוץ חי (buffer **57**, lag **128s**, OPEN_DRIVE) | כן | **`data.choppiness_ok`** (Missing) + detection (b1_sellers/b3_sellers/b1_expansion) | **לא** — choppiness_ok הוא קלט-חסר, לא setup-מבוסס | **דגל-בוליאני choppiness_ok לא מחווט** (I-16) |
| INV_HNS·HNS_TOP·DOUBLE_BOTTOM_EE·DOUBLE_TOP_AA·BULL_FLAG·BEAR_FLAG (6) | ערוץ חי | כן | `day_type_gate.auth_table_cell` (4 day-patterns) + **`data.choppiness_ok`** + detection | auth=לגיטימי; choppiness_ok=לא | choppiness_ok + (day-patterns auth×Trend_Normal) |

**מסקנת-S2:** **כל 10 התבניות blocked** ועל **כולן** מופיע `data.choppiness_ok` כחוסם ⇒ **I-16 משחזר** (אחרי שב-11:43 לא נצפה). gateway/UI מציגים chop score קיים (`11 FOUND` ב-Dashboard) אך הדגל-הבוליאני `data.choppiness_ok` נחשב **חסר** — פער score≠gate-flag חוזר. five_min buffer 57 (≠31@11:43) ⇒ מחזק I-17 (תנודתיות-גבול-בר/buffer). `patterns_detected=0/setups_published=0`.

### S3 · Footprint — טבלת 5-שאלות (4 תבניות) — I-11 אישור #20
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|-------|---------|---------|---------|------------|---------|
| ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION | **לא** (bars_processed_today=0, buffer 0, flow null, ts=null/fresh=false) | לא-רלוונטי | `data.buffer_size` + `data.bars_today` (0, need ≥5) | — | **ingest footprint שבור** (I-11) |

**מסקנת-S3:** כל 4 un-armable. gate `footprint`=**[FRESH] 0s · 20:28:29** (קובץ נכתב **ברגע זה**) בעוד `bars_processed_today=0` ⇒ **הוכחת-עצמאות אישור #20**: file→bridge→buffer שבור, **עצמאי מ-I-21** (ערוץ 5דק' חי הפעם, lag 128s).

### עדכון-חשודים — snapshot 12:27 CT
| חשוד | ממצא 12:27 | סטטוס |
|------|-----------|-------|
| I-1 (day_type) | **לא חוסם S2/S4** — state+readiness+S2-gate+A4 **כולם** Trend_Normal (אין פיצול-3-כיווני). board-chain מציג "Day Type × stale" = artifact-freshness (TZ-mix I-18), לא כשל-סיווג. residual: `opening_type=UNKNOWN` (מול five_min/UI OPEN_DRIVE) + **`session_min=0`** ב-~237דק' + `vote_history=[]`. Dashboard `Y IB dll_missing` = חשוד-שורש | 🟡 |
| I-2 (A5 חוסם) | A5 PASS (sizing=half) — לא חוסם. תקין | 🟡 |
| I-3 (ZLR) | armed (trend RED), active_patterns ללא ZLR (A3 no pattern this bar). אין setup-ZLR/counterfactual | 🔬 |
| I-11 (footprint 0 ברים) | **אישור #20** — gate FRESH `20:28:29` (נכתב עכשיו) בעוד ערוץ 5דק' חי — עדיין 0 ברים/buffer 0/flow null/ts=null. **ingest-break מוכח, עצמאי מ-I-21** | 🔴 |
| I-12 (A5 details ריק) | **setup חי הפעם** — A5 PASS sizing=half, `details{}` עדיין ריק (ההסבר לא נחשף ב-endpoint). החסימה היתה A7, לא A5 | 🟡 |
| I-13 (sizing מפספס) | **לא נצפה ירידת-sizing** — A5 על HFE החזיר **sizing=half (PASS)**, לא reject. החסם=A7 R:R. ⇒ בסנאפ-שוט זה sizing לא פסל. אך ⭐ stop/target צריך כיול | 🔴 (לא נצפה הפעם) |
| I-14 (הרצת-פתיחה) | opening_type=OPEN_DRIVE (five_min/UI). INITIATIVE_L/S blocked על choppiness_ok+b1_expansion (לא auth). שרשרת opening→entry ל-CC | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר קונפליקט:** מנוע `cci_14=-101.64/RED` + board `s4_trend_not_stuck_gray ✓ RED` — **מסכימים**. **פער-UI נמשך:** פאנל Woodies-CCI `CCIDiff 38.86 · CCI≈104.7/81.0` מול endpoint `-101.64` (skew גדול, סימן הפוך). הצלבת Sierra חובה | 🔬 |
| I-16 (choppiness_ok) | **משחזר** — כל 10 תבניות-S2 blocked עם `data.choppiness_ok`, בעוד Dashboard `11 FOUND` (score קיים). פער score≠gate-flag. היפוך מ-11:43 (6 armed) ⇒ מחזק I-17 | 🔴 |
| I-17 (buffer-volatility) | five_min buffer=**57** (≠31@11:43, ≠12@11:05); choppiness_ok התהפך present→Missing על ערוץ חי ⇒ תומך חזק בתנודתיות-גבול-בר/buffer | 🔬 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min(`20:15`)/footprint(`20:28`) נושאים IL-local מסומן `+00:00`/`lag=null`; cumulative_delta(`17:24`)/volume_profile(`17:28`)/imbalance(`17:25`) UTC תקין (lag 1.8–211s). מפר Rule 4. גורם ל-"Day Type/Footprint × stale" בלוח | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 50→121ms (200, len 87.8KB). שאר endpoints <60ms. נקי (7 רצופים היום) | 🔴 (לסירוגין) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-9989/fresh=true/threshold=90` (lag שלילי ~-2.77h). predicate לא אוכף סף. readiness משתמש ב-gates → BLOCKED נכון | 🟡 |
| I-21 (5דק'/tick stall) | **ערוץ 5דק'/study/footprint-file חי** (woodies_5min/footprint FRESH, five_min df **lag 128s אמיתי**, CCI נע, buffer 57). `tick_reversal_15` עדיין **DEAD מ-שישי 06-05 15:51 (265031s ~73h, session-non-start)** + tpo DEAD → board BLOCKED. פיצול נשאר tick_reversal_15-בלבד | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי: id=10 **92R** ($230), id=13 **26.75R** ($66.88), id=12 **16R** ($20). אין עסקה-טרייה היום (HFE נחסם A7). חוסם EOD-counterfactual | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active_count=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |
| I-24 (POC/TPO stream) | `tpo` stream **DEAD מ-2023-11-25** (present=false), נספר ב-`bridge_streams_fresh` ⇒ תורם ל-`dead: ...,tpo` ב-verdict. S5/TPO ידוע-לא-מחווט, אינו fire-path. (גם בלעדיו tick_reversal_15 לבדו חוסם) | 🟡 |

### צילום-מסך (Build Status / decision-tree)
ה-frontend **חי** (localhost:3000, כבר רץ — לא הופעל ע"י הסוכן). צולמו 2 screenshots (Chrome computer, tier=read):
- **Dashboard** (`ss_0180lx3lw`, inline): price **7,435.75** live (0.8s ago), SHADOW, **5 Min Tick Rev**, **Trend Normal CLASSIFIED 38%** (Dir HIGH/Trade LOW), IB TODAY H 7469.50/L 7429.00 **40.5pt WIDE**, Opening **OPEN_DRIVE WIDE**, **`Y IB dll_missing`**, today POC 7446.50/VAH 7462.75/VAL 7436.50, YEST POC 7456 · 7552.75/7359.00 (193.75pt), **11 FOUND · SS NONE**, FIRING: S2(5-Min) **IDLE** · S3 Footprint · S4 **VEG** Woodies; observing Day Type/TPO/Killzone, S3-panel NO_SETUP, Day 26/30 · 0 trades · WR 0%.
- **Build Status** (`ss_9766dsulq`, inline): header **BLOCKED** · day Trend_Normal · heartbeat <1s · ~147דק' לסגירה · RTH פתוח. באנר `dead: tick_reversal_15,tpo`. chain: **verdict BLOCKED → Day Type × stale → S3 BLOCKED → Footprint × stale → S4 BLOCKED · ✓ Woodies CCI · S2 BLOCKED · ✓ Min Patterns-5 · ✓ Bridge·Streams**. פאנל `pre_fire_validator`: **R:R ≥ 1.0 ✗** + כל 7 הבדיקות ✗ (אין fire פעיל לאמת). Killzone ✗ "KZ לא מחזור". tabs: עץ-החלטות · טבלאות-מקור 247 · מה-חסר 12.
- Woodies-CCI panel: `CCIDiff 38.86 · CCI≈104.7/81.0` מול endpoint `cci_14=-101.64` (פער-UI↔endpoint **+סימן הפוך**, I-15).
- **הערה:** `save_to_disk` ללא-אפקט ב-session זה ⇒ אין נתיב-קובץ קבוע (תמונות inline בלבד). **computer-use desktop-access dialog נכשל ב-timeout (180s)** — אין משתמש נוכח בריצה-מתוזמנת לאשר; נפל-חזרה ל-Chrome screenshot (tier=read).

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)
- **⭐ HFE A7 R:R 0.29** — להצליב entry/stop/targets של HFE מול ספק-התבנית ב-Sierra; CC לכייל stop/target table כך ש-HFE יוכל לעבור A7 (memory `project_stop_target_placement_table`).
- **`cci_14=-101.64 / trend_state=RED`** — להצליב CCI-14/TCCI/WSI גולמי; לאמת RED.
- **פער-UI Woodies-CCI** (I-15) — פאנל `CCIDiff 38.86 / ~104.7` מול endpoint `-101.64` (**סימן הפוך**); CC לקבוע מקור-אמת אחד.
- **`Y IB dll_missing`** — CC: למה DLL לא מחזיר yesterday-IB/atr_daily; חשוד-שורש ל-`opening_type=UNKNOWN`+`session_min=0`+`vote_history=[]` (I-1).
- **footprint file FRESH (20:28:29) אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer; **עצמאי מ-I-21**.
- **tick_reversal_15 session-non-start** (I-21) — DEAD מ-שישי 15:51 (~73h); CC למה לבדו לא עלה ב-08:30 CT בעוד 5דק'/footprint/CVD/imbalance כן.
- **choppiness_ok score≠gate-flag** (I-16/I-17) — תנודתי; CC לחווט דגל-בוליאני **יציב** מ-chop_state.
- **TZ-mislabel** (I-18/I-20) — IL-local מסומן `+00:00`; CC לנרמל ל-UTC + לאכוף `|lag|≤threshold`.

### NOT-DONE / פערים
- **counterfactual:** **יש מועמד ראשון** — HFE LONG שזוהה-ונחסם A7 (חושב לעיל: T1 +0.29R סביר-נפגע). אך **R מה-DB מנופח ~50× (I-22)** ⇒ ה-ΣR/win-rate של EOD חסום עד תיקון pnl_r. S2: 10 armed/blocked בלי detection-שעבר; S3: feed-dead.
- **FHB-state לא נחשף** — `/five_min/current`+`/stats` לא מחזירים FHB (ACCUMULATING/EARLY/COMPLETE) ⇒ I-4 נבדק עקיף (buffer 57 + patterns_detected 0). CC: לחשוף FHB ב-endpoint.
- **צילום לדיסק** — `save_to_disk` לא נתמך ב-session; computer-use desktop access timed-out (אין משתמש). תמונות inline בלבד.

---

## snapshot 12:45 CT (17:45Z · session_date 2026-06-08 · ~255 דק' לתוך RTH)

**RTH:** 08:30–15:00 CT — **בתוך החלון** (12:45 CT). gating-CT תקין (I-9).
**מצב-לוח:** verdict **BLOCKED** · reason `dead: tick_reversal_15,tpo`. readiness: `bridge_streams_fresh ✗ block dead: tick_reversal_15,tpo` · `s1_day_type_classified ✓ degrade Trend_Normal` · `s4_trend_not_stuck_gray ✗ degrade GRAY` · `in_rth ✓`.
**זריזות endpoints:** כל 8 ענו <90ms (gateway 4 · five_min_stats 8 · day_type 10 · footprint 39 · trades 42 · five_min 50 · woodies 54 · **build/pattern-status 83ms**, len 88,176). אין hang (I-19 לא משחזר — 8 ריצות רצופות נקיות היום).

### ⚑ שינוי-מצב מ-12:27 — trend התהפך RED→GRAY ⇒ S4 כעת A1-vetoed (אין HFE/counterfactual הבר)
`/woodies/current`: **`cci_14=+3.22`** (חצה לאזור-אפס, ≠ -101.64@12:27), cci_6_tcci=65.2, ema_34=7444.65, lsma=7430.43, swi=117.43, czi=-29.0, **`trend_state=GRAY`**, signal NEUTRAL, buffer 50, **active_patterns=[] (NO_SETUP)**. decision_tree: A1 **SKIP** (no patterns) · A2 PASS (11 studies) · A3 SKIP (no patterns this bar) · A4 SKIP · A5 PASS (advisory:calculate_size=reject) · A6 SKIP · A7 SKIP. ⇒ אין setup הבר ⇒ **אין counterfactual חדש** הסנאפ-שוט (שלא כמו HFE@12:27).

### S4 · Woodies — טבלת 5-שאלות (7 תבניות) — A1 veto (GRAY)
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|-------|---------|---------|---------|------------|---------|
| ZLR·TLB·TT·GB100·Vegas·Ghost·FAMIR (7) | כן (cci_14=+3.22, GRAY) | כן (CCI סביב-אפס ⇒ trend לא-מוגדר ⇒ GRAY סביר) | **`stage_a1.strategic_gate`** (A1 veto: trend GRAY) **לפני** detection, ואז `detection.pattern_specific`+`targets_stop.r_t1_gate`/`stop_price`/`targets`+`exit_rules.ready_to_r` | **מוצדק** — A1 veto על GRAY הוא הספק (אין trend מוגדר לירות לתוכו) | — |

**מסקנת-S4:** trend **GRAY** ⇒ A1 וֵטוֹ על כל 7 התבניות **לפני** A3-detection (≠12:27 שבו RED ⇒ A1 עבר וכולן armed). **I-3 (ZLR):** ZLR חסום `stage_a1.strategic_gate` (GRAY) לפני A3 — לא armed הפעם, לא setup, אין counterfactual.

### S2 · Five-Min — טבלת 5-שאלות (10 תבניות) — I-16 משחזר שוב
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|-------|---------|---------|---------|------------|---------|
| REACTIVE_L/S · INITIATIVE_L/S (4) | ערוץ חי (buffer **64**, mode DAY_TYPE, OPEN_DRIVE) | כן | **`data.choppiness_ok`** (Missing) + detection (b3_buyers/b1_buyers/b1_expansion) | **לא** — choppiness_ok קלט-חסר, לא setup | **דגל-בוליאני choppiness_ok לא מחווט** (I-16) |
| INV_HNS·HNS_TOP·DOUBLE_BOTTOM_EE·DOUBLE_TOP_AA·BULL_FLAG·BEAR_FLAG (6) | ערוץ חי | כן | `day_type_gate.auth_table_cell` (4 day-patterns) + **`data.choppiness_ok`** + detection (hns_structure/swing_highs/eve_variant/neckline_breakout) | auth=לגיטימי; choppiness_ok=לא | choppiness_ok + (day-patterns auth×Trend_Normal) |

**מסקנת-S2:** **כל 10 התבניות blocked**, על **כולן** `data.choppiness_ok` כחוסם ⇒ **I-16 משחזר** (כמו 12:27). gateway `chop_state=FOUND` + Dashboard `6 FOUND` (score קיים) אך הדגל-הבוליאני `data.choppiness_ok` נחשב **חסר** — פער score≠gate-flag נמשך. five_min buffer **64** (≠57@12:27) ⇒ מחזק I-17. `patterns_detected=0/setups_published=0`.

### S3 · Footprint — טבלת 5-שאלות (4 תבניות) — I-11 אישור #21
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|-------|---------|---------|---------|------------|---------|
| ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION | **לא** (bars_processed_today=0, buffer 0, flow null, cumulative_delta 0) | לא-רלוונטי | `data.buffer_size` + `data.bars_today` (0, need ≥5) | — | **ingest footprint שבור** (I-11) |

**מסקנת-S3:** כל 4 un-armable. gate `footprint`=**[FRESH] 0s · 20:41:10** (קובץ נכתב **ברגע זה**) בעוד `bars_processed_today=0` ⇒ **אישור-עצמאות #21**: file→bridge→buffer שבור, **עצמאי מ-I-21** (ערוץ 5דק' חי הפעם: woodies_5min/bars_5min FRESH, CCI נע).

### עדכון-חשודים — snapshot 12:45 CT
| חשוד | ממצא 12:45 | סטטוס |
|------|-----------|-------|
| I-1 (day_type) | **לא חוסם S2/S4** — state+readiness מסכימים Trend_Normal (`s1_day_type_classified ✓`). chain "Day Type × stale" = artifact-TZ (I-18), לא כשל-סיווג. residual: `opening_type=UNKNOWN` (מול five_min OPEN_DRIVE) + **`session_min=0`** ב-~255דק' + **`vote_history=[]`**. Dashboard `Y IB dll_missing` = חשוד-שורש | 🟡 |
| I-2 (A5 חוסם) | A5 PASS advisory (calculate_size=reject) — לא חוסם. תקין | 🟡 |
| I-3 (ZLR) | trend **GRAY** ⇒ ZLR חסום `stage_a1.strategic_gate` (A1 veto) **לפני** A3-detection (לא armed, ≠12:27 RED). אין setup/counterfactual | 🔬 |
| I-4 (S2 דריכה) | five_min buffer=**64**, mode DAY_TYPE, ערוץ חי, OPEN_DRIVE. `patterns_detected=0/setups=0` (אין detection הבר). דריכה תקינה. FHB-state עדיין לא נחשף ב-endpoint | 🔬 |
| I-11 (footprint 0 ברים) | **אישור #21** — gate FRESH `20:41:10` (נכתב עכשיו) בעוד ערוץ 5דק' חי — עדיין 0 ברים/buffer 0/flow null/cumulative_delta 0. **ingest-break מוכח, עצמאי מ-I-21** | 🔴 |
| I-12 (A5 details ריק) | NO_SETUP, A5 advisory reject; `details{}` ריק — אין reject-context לבדוק בלי setup | 🟡 |
| I-13 (sizing מפספס) | NO_SETUP (active_patterns=[]), A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing לכייל | 🔴 (לא נצפה) |
| I-14 (הרצת-פתיחה) | opening_type=OPEN_DRIVE (five_min/UI; state עדיין UNKNOWN). INITIATIVE_L/S blocked על choppiness_ok+b1_expansion (לא auth). שרשרת opening→entry ל-CC | 🔴 |
| I-15 / C-1 (trend_state) | **לא משחזר קונפליקט מנוע↔לוח:** מנוע `cci_14=+3.22/GRAY` + board `s4_trend_not_stuck_gray ✗ GRAY` — **מסכימים** (ה-GRAY אמיתי, CCI סביב-אפס). **פער-UI גדול:** פאנל Woodies-CCI `CCI≈-59.40 · TrendDown 1.00 · CCIDiff -20.69` (מציג downtrend) מול endpoint `+3.22/GRAY` ⇒ פער-משטח **גם בגודל וגם ב-regime** (UI=down, engine=GRAY). הצלבת Sierra חובה | 🔬 |
| I-16 (choppiness_ok) | **משחזר** — כל 10 תבניות-S2 blocked עם `data.choppiness_ok`, בעוד gateway `chop_state=FOUND` + Dashboard `6 FOUND` (score קיים). פער score≠gate-flag | 🔴 |
| I-17 (buffer-volatility) | five_min buffer=**64** (≠57@12:27, ≠31@11:43); choppiness_ok נשאר Missing על ערוץ חי. תומך בתנודתיות-גבול-בר/buffer | 🔬 |
| I-18 (freshness TZ-mix) | **נמשך:** woodies_5min(`20:35`)/footprint(`20:41`)/bars_5min(`20:40`) נושאים IL-local מסומן `+00:00`/`lag_s=null`; cumulative_delta(`17:40`)/volume_profile(`17:41`) UTC תקין (lag 71s/1s). **`imbalance` Present אך lag 363s > 90s req** = stale-but-Present. מפר Rule 4. גורם ל-"Day Type/Footprint × stale" בלוח | 🟡 |
| I-19 (pattern-status hang) | **לא משחזר** — 83ms (200, len 88,176). שאר endpoints <60ms. נקי (8 רצופים היום) | 🔴 (לסירוגין) |
| I-20 (freshness predicate) | **נמשך:** bridge `data_freshness.lag_seconds=-10428.98/fresh=true/threshold=90` (lag שלילי ~-2.9h). predicate לא אוכף סף. readiness משתמש ב-global_gates → BLOCKED נכון | 🟡 |
| I-21 (5דק'/tick stall) | **ערוץ 5דק'/study/footprint-file חי** (woodies_5min FRESH 20:35 · bars_5min FRESH 20:40 · footprint FRESH 20:41; CCI נע +3.22, buffer 64). `tick_reversal_15` עדיין **DEAD מ-שישי 06-05 15:51:19 (4429min ~74h, session-non-start)** + tpo DEAD → board BLOCKED. הפיצול נשאר **tick_reversal_15-בלבד** | 🔴 |
| I-22 (pnl_r ~50×) | עדיין גלוי בערכי-שישי: id=10 **92R** ($230), id=13 **26.75R** ($66.88), id=12 **16R** ($20). אין עסקה-טרייה היום (S4 GRAY-vetoed, S2 choppiness-blocked). חוסם EOD-counterfactual | 🔴 |
| I-23 (gateway counters) | `trades_today=0/daily_pnl=0/shadow_active_count=0` — נכון היום (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה | 🟡 (לא נצפה) |
| I-24 (POC/TPO stream) | `tpo` stream **DEAD מ-2023-11-25** (present=false), נספר ב-`bridge_streams_fresh` ⇒ תורם ל-`dead: ...,tpo` ב-verdict. S5/TPO ידוע-לא-מחווט, אינו fire-path (גם בלעדיו tick_reversal_15 לבדו חוסם) | 🟡 |

### צילום-מסך (Build Status / decision-tree)
ה-frontend **חי** (localhost:3000, כבר רץ — לא הופעל ע"י הסוכן). צולמו 2 screenshots (Chrome computer, tier=read):
- **Dashboard** (`ss_2943khivc`, inline): price **7,430.00** live (0.6s ago), SHADOW, **5 Min Tick Rev**, **Trend Normal CLASSIFIED 38%** (Dir HIGH/Trade LOW), IB TODAY H 7469.50/L 7429.00 **40.5pt WIDE**, Opening **OPEN_DRIVE WIDE**, **`Y IB dll_missing`**, today POC 7446.50/VAH 7463.50/VAL 7435.75, YEST POC 7456 · 7552.75/7359.00 (193.75pt), **6 FOUND · SS NONE**, FIRING: S2(5-Min) **IDLE** · S3 Footprint · S4 **NEUT** Woodies; Day 26/30 · 0 trades · WR 0%. Woodies-CCI panel: `CCI≈-59.40 · TrendDown 1.00 · CCIDiff -20.69` מול endpoint `cci_14=+3.22/GRAY` (פער-UI↔endpoint **בגודל + regime**, I-15).
- **Build Status** (`ss_4001tmon6`, inline): header **BLOCKED** · day Trend_Normal · heartbeat <1s · ~136דק' לסגירה · RTH פתוח. באנר `dead: tick_reversal_15,tpo` + runbook `docs/runbooks/SIERRA_DLL_OPS.md` · `/tmp/bridge.err.log`. chain: **verdict BLOCKED → Day Type × stale → S3 BLOCKED → Footprint × stale → S4 BLOCKED · ✓ Woodies CCI · S2 BLOCKED · ✓ Min Patterns-5 · ✓ Bridge·Streams**. פאנל `risk_checks · LIVE caps`: כל 6 ✗. פאנל `pre_fire_validator`: **R:R ≥ 1.0 ✗** + כל 7 הבדיקות ✗ (אין fire פעיל לאמת). Killzone ✗ "KZ לא מחזור". tabs: עץ-החלטות · שלמות-מקור **247** · טבלאות-אפיון · מה-חסר **12**.
- **הערה:** `save_to_disk` ללא-אפקט ב-session זה ⇒ אין נתיב-קובץ קבוע (התמונות inline, מזהים `ss_2943khivc`/`ss_4001tmon6`). computer-use desktop-access לא נוסה (ריצה-מתוזמנת, אין משתמש לאשר dialog); נפל-חזרה ל-Chrome screenshot.

### מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — לא כאן)
- **`cci_14=+3.22 / trend_state=GRAY`** — להצליב CCI-14/TCCI/WSI גולמי; לאמת חציית-אפס ⇒ GRAY (S4 A1-veto מוצדק).
- **פער-UI Woodies-CCI** (I-15) — פאנל `CCI≈-59.40/TrendDown 1.00` מול endpoint `+3.22/GRAY` (**גודל + regime הפוכים**); CC לקבוע מקור-אמת אחד — מי מציג trend-down בעוד המנוע GRAY.
- **`Y IB dll_missing`** — CC: למה DLL לא מחזיר yesterday-IB/atr_daily; חשוד-שורש ל-`opening_type=UNKNOWN`+`session_min=0`+`vote_history=[]` (I-1).
- **footprint file FRESH (20:41:10) אך 0 ברים** (I-11) — CC לאבחן file→bridge-parse→buffer; **עצמאי מ-I-21**.
- **tick_reversal_15 session-non-start** (I-21) — DEAD מ-שישי 15:51 (~74h); CC למה לבדו לא עלה ב-08:30 CT בעוד 5דק'/footprint/CVD/volume_profile/imbalance כן.
- **choppiness_ok score≠gate-flag** (I-16/I-17) — Missing למרות `chop_state=FOUND`; CC לחווט דגל-בוליאני **יציב** מ-chop_state.
- **TZ-mislabel + imbalance stale-but-Present** (I-18/I-20) — IL-local מסומן `+00:00`/lag_s=null; imbalance lag 363s>90s עדיין Present; CC לנרמל ל-UTC + לאכוף `|lag|≤threshold`.

### NOT-DONE / פערים
- **counterfactual:** **אין מועמד הסנאפ-שוט הזה** — S4 GRAY-vetoed (active_patterns=[]), S2 choppiness-blocked, S3 feed-dead. אין setup שזוהה-ונחסם להריץ עליו תחזית-נגד. (HFE@12:27 נשאר המועמד-היחיד היום, אך **R מה-DB מנופח ~50× (I-22)** ⇒ ΣR/win-rate של EOD חסום עד תיקון pnl_r.)
- **FHB-state לא נחשף** — `/five_min/current`+`/stats` לא מחזירים FHB (ACCUMULATING/EARLY/COMPLETE) ⇒ I-4 נבדק עקיף (buffer 64 + patterns_detected 0). CC: לחשוף FHB ב-endpoint.
- **פער Sierra↔backend (חובה לתעד):** כל ערכי-הקלט (CCI/WSI/OHLC/footprint-flow) **לא הוצלבו** מול `~/SierraChart_Data/v9_export/` — read-only כאן, ל-CC. פערי-UI↔endpoint שזוהו (I-15) הם פנים-backend ולא תחליף להצלבת-Sierra.

---

## 13:09 CT — בדיקה עמוקה (snapshot, ~279 דק' לתוך RTH)

**זמן:** 2026-06-08 13:09 CT (18:09 UTC). `build/pattern-status.ts`=`2026-06-08T18:09:29Z`, `session_date=2026-06-08`, `in_session=true`, `minutes_to_close=111`.
**מקור-נתונים:** API דרך Chrome (`javascript_tool fetch` → `http://localhost:8000`). frontend (`localhost:3000`) **חי** — צולמו Dashboard (`ss_6157mf3wx`) + Build-Status (`ss_14545tnnw`). **save_to_disk לא נתמך ב-session הזה** (inline-only, ראה NOT-DONE). API root `:8000/` מחזיר `{"detail":"Not Found"}` (אין UI שם; הלוח הוא ה-React ב-:3000).

### ⭐ ממצא-על (headline): verdict ירד מ-BLOCKED ל-**DEGRADED** — `bridge_streams_fresh` עובר למרות `tick_reversal_15`+`tpo` עדיין DEAD

בכל סנאפ-שוט קודם היום (08:42→12:45) ה-verdict היה **BLOCKED** דרך `bridge_streams_fresh=false` ("dead: tick_reversal_15,tpo"). כעת:

- `readiness.verdict = **DEGRADED**`, `reason = "trend_state=GRAY"`.
- `readiness.checks`: `bridge_streams_fresh` **passed:true** (severity:block) · `s1_day_type_classified` ✓ Trend_Normal · `s4_trend_not_stuck_gray` **✗ GRAY** (severity:degrade) · `in_rth` ✓.
- אבל `global_gates`: `tick_reversal_15` **present:false** ו-`tpo` **present:false** — **עדיין מתים**. ⇒ ה-readiness כבר **לא** מתייחס אליהם כחוסמים.

⇒ זהו **שינוי-התנהגות** ביחס לכל היום: או ש-`tick_reversal_15`/`tpo` הוצאו מקבוצת-הזרמים-הנדרשת ל-readiness (תואם המלצת I-24), או שינוי-לוגיקה אחר. **CC: לאשר שזו כוונה ולא דריפט — ולתעד בקוד `bridge_streams_fresh`.** עד אישור, מסומן ממצא.

### טבלת 5-השאלות — תבניות

| מערכת · תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|---|---|---|---|---|
| **S2 REACTIVE_L/S** | ✅ armed | ✅ | detection `b1_sellers`/`b3_sellers` (אין setup בבר) | ✅ מוצדק (אין תבנית) | — |
| **S2 INITIATIVE_L/S** | ✅ armed | ✅ | detection `b1_expansion` | ✅ מוצדק | — |
| **S2 BULL/BEAR_FLAG** | ✅ armed | ✅ | detection `pole_found` | ✅ מוצדק | — |
| **S2 INV_HNS / HNS_TOP / DOUBLE_BOTTOM / DOUBLE_TOP** | ⚠️ blocked | ✅ | `day_type_gate.auth_table_cell` (×Trend_Normal) + detection swing/neckline | ✅ מוצדק (Auth-Table חוסם day-patterns ב-Trend_Normal) | — |
| **S3 ABSORPTION/STACKED/SWEEP/EXHAUSTION** | ❌ un-armable | ❌ | `data.buffer_size`/`data.bars_today`=0 (I-11) | ❌ **לא** — חסם הוא feed-break, לא לוגיקה | **ingest footprint שבור** (I-11) |
| **S4 ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR** | ⚠️ blocked | ⚠️ | **`stage_a1.strategic_gate`** (A1 veto · trend_state=GRAY) **לפני** A3-detection | ❓ תלוי ב-GRAY (ראה I-15) | הצלבת WSI/CCI מול Sierra |

**S2:** `mode=DAY_TYPE_MODE`, `buffer=4`, `opening_type=OPEN_DRIVE`, `patterns_detected=0`/`setups_published=0`. **6/10 armed** על ערוץ-חי. **אין "Missing: data.choppiness_ok"** בסנאפ-שוט זה ⇒ I-16 לא משחזר (Dashboard chop `39 EXPANDING`). מחזק I-17 (תנודתיות-גבול-בר).
**S3:** `bars_processed_today=0`, `buffer=0`, כל flow=null — I-11 (אישור #22).
**S4:** `trend_state=GRAY`, `cci_14=+159.01` (נע: 155→159, **לא קפוא** ⇒ I-21 לא משחזר), `active_patterns=[]`, classification=NO_SETUP. כל תבניות S4 חסומות ב-A1-veto GRAY.

### טבלת 5-השאלות — חשודים מהרשימה (open בלבד)

| # | יש נתון? | הגיוני? | מה חסם / נצפה | צריך לחסום? | מה חסר | סטטוס-עדכון |
|---|---|---|---|---|---|---|
| **I-1** day_type | ✅ B2/Trend_Normal/0.38/LOCKED_LOW_CONF | ⚠️ | **לא חוסם** — state+readiness+S2-auth+UI("Trend Normal 38%") מסכימים. אין פיצול-3-כיווני | — | residual: `opening_type=UNKNOWN` (מול five_min/UI OPEN_DRIVE) · `session_min=0` · `vote_history=[]` ב-279דק'. Dashboard `Y IB dll_missing` | 🟡 נמשך |
| **I-2** A5 | ✅ A5 PASS `advisory:calculate_size=reject` | ✅ | **לא חוסם** (advisory) — תקין | — | — | ✅ תקין |
| **I-3** ZLR | ✅ | ✅ | `stage_a1.strategic_gate` (A1 veto GRAY) **לפני** A3. לא armed הפעם (≠RED) | ❓ תלוי GRAY | counterfactual: אין | 🔬 נמשך |
| **I-11** footprint | ❌ 0 ברים | ❌ | ingest file→bridge→buffer שבור; gate `footprint` present:true אך buffer 0 | ❌ | אבחון ingest (CC) | 🔴 נמשך (#22) |
| **I-15** CCI UI↔engine | ✅ | ❌ | engine `cci_14=+159/GRAY` ↔ board מסכים GRAY (אין קונפליקט-trend). **אבל UI Woodies-CCI panel `CCI≈103.08/CCIDiff −48.83` (מציג down)** מול endpoint +159 (~56pt + סימן הפוך) | — | **הצלבת Sierra חובה** | 🔬 נמשך |
| **I-16** choppiness_ok | ✅ present | ✅ | **לא משחזר** — 6/10 armed, אין "Missing" | — | — | 🔬 לא משחזר |
| **I-18** TZ-mix | ✅ | ❌ | board chain `Day Type × stale`+`Footprint × stale`; five_min/woodies `last_bar_ts=...+03:00` (IL-local) | — | TZ-normalize ל-UTC (CC) | 🟡 נמשך |
| **I-19** pattern-status hang | ✅ 207ms | ✅ | **לא משחזר** (8 endpoints כולם <210ms) | — | — | 🔬 לא משחזר |
| **I-20** neg-lag fresh=true | ✅ | ❌ | bridge `data_freshness.lag_seconds=-10530 / fresh=true / threshold=90` (lag שלילי ~-2.9h) | — | אכיפת-סף + TZ-normalize (CC) | 🟡 נמשך |
| **I-21** 5-דק' stall | ✅ חי | ✅ | **לא משחזר** — five_min `last_bar=13:05 CT`, lag 269.7s, CCI נע | — | — | 🟡 לא משחזר כעת |
| **I-22** pnl_r inflation | ✅ | ❌ | trades(שישי): id=10 `$230=92R`, id=13 `$66.88=26.75R`, id=12 `$20=16R`. אין עסקה-טרייה היום | — | תיקון נוסחת pnl_r (CC) | 🔴 נמשך — **חוסם EOD-counterfactual** |
| **I-23** gateway counters | ✅ | ✅ | `trades_today=0/daily_pnl=0/shadow_active_count=0` — **נכון** היום (אין עסקה) | — | לא ניתן לשחזר בלי עסקה-טרייה | 🟡 לא נצפה |
| **I-24** tpo dead | ✅ DEAD | — | `tpo` present:false. **חדש:** כעת **לא חוסם** readiness (ראה ממצא-על) | ❌ לא fire-path | החלטת-SoT: להחיות tpo-study או להוציאו רשמית מ-streams-נדרשים | 🟡 התקדמות |

### ערכים גולמיים (raw)

```
readiness: verdict=DEGRADED, reason=trend_state=GRAY
  checks: bridge_streams_fresh=PASS(block) · s1_day_type_classified=PASS Trend_Normal(degrade)
          · s4_trend_not_stuck_gray=FAIL GRAY(degrade) · in_rth=PASS
woodies: cci_14=159.01, tcci=135.58, ema_34=7441.89, lsma=7430.84, swi=146.07, czi=4,
         trend_state=GRAY, signal=NEUTRAL, buffer=50, active_patterns=[], class=NO_SETUP
  dtree: A1 SKIP no patterns · A2 PASS 11 studies · A3 SKIP no patterns this bar
         · A4 SKIP · A5 PASS advisory:calculate_size=reject · A6 SKIP NO_SETUP · A7 SKIP
five_min: running, mode=DAY_TYPE_MODE, buffer=4, opening_type=OPEN_DRIVE,
          patterns_detected=0, setups_published=0
footprint: running, bars_processed_today=0, buffer=0, cumulative_delta=0, all flow=null
day_type: stage=B2, day_type=Trend_Normal, conf=0.38, lock=LOCKED_LOW_CONF,
          opening_type=UNKNOWN, ib_width=WIDE, session_min=0, vote_history=[]
gateway: shadow_active_count=0, daily_pnl=0, trades_today=0, demo_enabled=[2,4],
         live_enabled=[], cooldown_active=false
global_gates: woodies_5min=present · footprint=present · cumulative_delta=present
         · volume_profile=present · tick_reversal_15=ABSENT · imbalance=present
         · tpo=ABSENT · bars_5min=present
freshness: bridge{fresh=true,lag=-10530,last=null} · five_min{fresh=true,lag=269.7,last=2026-06-08 21:05:00+03:00}
         · footprint{fresh=false,lag=null,last=null} · woodies{fresh=true,lag=269.7,last=21:05:00+03:00}
trades(50): only 3, all 2026-06-05 (id=13 sys2 SHORT $66.88/26.75R; id=12 sys4 SHORT $20/16R; id=10 sys2 SHORT $230/92R)
endpoint timings: woodies 43ms · footprint 51ms · gateway 57ms · five_min 61ms · five_min_stats 68ms
         · day_type 106ms · trades 108ms · pattern_status 207ms (len 88462)
Dashboard UI: price 7437.75 LIVE 1s · TRD 38% · chop "39 EXPANDING" · SS NONE · OPEN_DRIVE Trend_Normal
         · IB TODAY H7469.50/L7429 40.5pt WIDE · Y IB dll_missing · UI Woodies-CCI CCI 103.08/CCIDiff -48.83
Build-Status board: verdict DEGRADED (trend_state=GRAY); chain Day Type×stale→S3 BLOCKED
         →Footprint×stale→S4 BLOCKED→✓Woodies CCI→✓Min Patterns-5→✓Bridge·Streams; heartbeat <1s
screenshots: ss_6157mf3wx (Dashboard) · ss_14545tnnw (Build Status) — inline-only, save_to_disk לא נשמר
```

### NOT-DONE / פערים
- **counterfactual:** אין מועמד הסנאפ-שוט הזה — S4 GRAY-vetoed (active_patterns=[]), S2 ללא detection-בבר, S3 feed-dead. אין setup שזוהה-ונחסם. (R מה-DB מנופח ~50× I-22 ⇒ ΣR/win-rate של EOD חסום עד תיקון pnl_r.)
- **trend_state=GRAY על `cci_14=+159` (חיובי-מאוד)** — engine+board מסכימים GRAY (לא קונפליקט-תצוגה), אך GRAY על CCI גבוה-חיובי **חוסם את כל S4**. אם ה-GRAY שגוי → כל ירי-Woodies מדוכא שלא-בצדק. **CC: הצלבת WSI/CCI גולמי מול `~/SierraChart_Data/v9_export/` — האם WSI באמת indeterminate, או trend_state תקוע/מפגר.**
- **FHB-state לא נחשף** — `/five_min/current`+`/stats` לא מחזירים FHB ⇒ I-4 נבדק עקיף. CC: לחשוף FHB.
- **פער Sierra↔backend (חובה לתעד):** כל ערכי-הקלט (CCI/WSI/OHLC/footprint-flow) **לא הוצלבו** מול `~/SierraChart_Data/v9_export/` — read-only כאן, ל-CC. פער-UI↔endpoint (I-15) פנים-backend, לא תחליף להצלבת-Sierra.
- **save_to_disk** לא נתמך ב-session ⇒ הצילומים inline-only (IDs לעיל), לא נשמרו לדיסק.

---

## 🕐 13:38 CT — snapshot עמוק (~308 דק' לתוך RTH · ~82 דק' לסגירה)

**Headline:** verdict **DEGRADED** (לא BLOCKED) — `bridge_streams_fresh` passed:true.
**ממצא-מפתח חדש:** gate `footprint` כעת מסומן **`"disabled (S3_MUTE/S5)" · critical:false`** —
שינוי-תצורה מאז הסשן הקודם; footprint כבר לא חוסם את הלוח (אך wiring ה-ingest עדיין שבור).
ערוץ 5דק' חי (woodies_5min/bars_5min FRESH 0s), 6/10 S2 armed. אין עסקה היום.
**פער trend:** engine `/woodies/current` = **BLUE** (cci_14=+6.1) מול board readiness = **GRAY**
— flicker סביב zero-cross (cci_14≈0), לא קונפליקט-תצוגה קשיח.

### S2 · Five-Minute (last_bar 21:35:00+03:00 = 13:35 CT · lag 286.6s · buffer 10)
| תבנית | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|-------|-----------|-----------|-----------|---------------|-----------|
| REACTIVE_LONG | כן (armed) | כן | `detection.b2_volume_drop` (אין setup בבר) | כן — detection אמיתי | — |
| REACTIVE_SHORT | כן (armed) | כן | אין blocker (הכי-קרוב לירי) | כן | — |
| INITIATIVE_LONG | כן (armed) | כן | `detection.b1_expansion` | כן | — |
| INITIATIVE_SHORT | כן (armed) | כן | `detection.b1_expansion` | כן | — |
| INV_HNS_LONG | כן (blocked) | כן | `day_type_gate.auth_table_cell` + `detection.swing_lows_found` | כן — Auth-Table×Trend_Normal=SKIP (לגיטימי) | — |
| HNS_TOP_SHORT | כן (blocked) | כן | `auth_table_cell` + `swing_highs_found` | כן (auth SKIP) | — |
| DOUBLE_BOTTOM_EE | כן (blocked) | כן | `auth_table_cell` + `swing_lows_found` | כן (auth SKIP) | — |
| DOUBLE_TOP_AA | כן (blocked) | כן | `auth_table_cell` | כן (auth SKIP) | — |
| BULL_FLAG_LONG | כן (armed) | כן | `detection.flag_retrace` | כן | — |
| BEAR_FLAG_SHORT | כן (armed) | כן | `detection.pole_found` | כן | — |

⇒ 6 armed (מומנטום+flags) על detection אמיתי · 4 day-patterns חסומות לגיטימית ב-Auth×Trend_Normal.
**אין `Missing: data.choppiness_ok` בסנאפ-שוט זה** ⇒ I-16 לא משחזר (מחזק I-17 תנודתיות-גבול-בר).
day_type_gate **satisfied** ל-6 המומנטום ⇒ day_type לא חוסם S2 broadly.

### S3 · Footprint (fresh=false · last=null · bars_processed_today=0 · buffer=0)
| תבנית | 1.יש? | 2.הגיוני? | 3.מה חסם? | 4.צריך? | 5.מה חסר? |
|-------|-------|-----------|-----------|---------|-----------|
| ABSORPTION/STACKED_IMB/SWEEP_RETURN/EXHAUSTION | לא (0 ברים) | — | `data.buffer_size \|\| data.bars_today` (0<5) | — | **ingest file→bridge→buffer שבור (I-11)** |

⇒ gate `footprint`=`[disabled] [FRESH] 0s · 21:40:07` — הקובץ **נכתב ברגע זה** אך 0 ברים מגיעים ל-buffer.
**כעת מסומן `disabled (S3_MUTE/S5)`** ⇒ לא חוסם לוח, אך ה-ingest-break נשאר (לא נפתר, רק הושתק).

### S4 · Woodies CCI (last_bar 13:35 CT · lag 286.6s · buffer 50 · cci_14=+6.1 · TCCI=-63.92 · trend BLUE/GRAY flicker)
| תבנית | 1.יש? | 2.הגיוני? | 3.מה חסם? | 4.צריך? | 5.מה חסר? |
|-------|-------|-----------|-----------|---------|-----------|
| ZLR · TLB · TT · GB100 · HFE · HTLB · FAMIR (+CCI_HNS,HORIZ_TLB) | active_patterns=[] | cci_14=+6.1 zero-cross | `stage_a1.strategic_gate` (A1 veto, trend GRAY) **לפני** A3-detection | **ספק** — GRAY על cci≈0 (zero-cross אמיתי) סביר, אך חוסם כל S4 | הצלבת WSI/CCI גולמי מול Sierra |

⇒ כל 9 חסומות ב-A1 strategic_gate (trend GRAY) + downstream (targets_stop/exit_rules). אין setup ⇒ אין counterfactual.

### Gates (לא תבניות-ירי)
- **day_type_gate:** Trend_Normal CLASSIFIED 0.38/B2 — satisfied (לא חוסם 6 מומנטום; חוסם 4 day-patterns לגיטימית).
- **chop:** gateway `chop_state=EXPANDING`, UI "39 EXPANDING" — לא חוסם (Chop Gates DISABLED per CLAUDE.md).
- **killzone (S6):** board `KZ ✗ ממתין · KZ לא מחזור` — gate, לא תבנית.
- **TPO (S5):** stream `tpo` ABSENT (DEAD 2023-11-25) — לא-מחווט מכוון (I-24).

### בדיקת חשודים-פתוחים (register)
| # | סטטוס-קודם | ממצא 13:38 | סטטוס-חדש |
|---|-----------|------------|-----------|
| I-1 day_type UNKNOWN | 🟡 | **לא חוסם** — state+readiness+S2-gate מסכימים Trend_Normal (אין פיצול). residual: `opening_type=UNKNOWN` (מול five_min/UI=OPEN_DRIVE) + `session_min=0` + `vote_history=[]` ב-~308דק'. Dashboard `Y IB dll_missing` (atr_daily/yest-IB חסר=שורש). | 🟡 נמשך |
| I-3 ZLR לא ירה | 🔬 | trend **GRAY** (cci_14=+6.1 zero-cross) ⇒ ZLR חסום `stage_a1.strategic_gate` לפני A3-detection — לא armed. אין setup/counterfactual. | 🔬 |
| I-11 footprint 0 ברים | 🔴 | **אישור #23** — bars_today=0/buffer 0/flow null בעוד gate footprint נכתב עכשיו (`[FRESH] 0s·21:40:07`). **חדש: gate מסומן `disabled (S3_MUTE/S5)`** ⇒ הושתק, לא נפתר. ingest-break עצמאי. | 🔴 ingest-break (מושתק) |
| I-15 C-1 trend conflict | 🔬 | engine BLUE(cci_14=+6.1) מול board GRAY — flicker zero-cross, **לא** קונפליקט קשיח. UI CCIDiff=-64.41 ≈ endpoint TCCI -63.92 (הפאנל מציג cci_6/TCCI, לא cci_14). הצלבת Sierra חובה. | 🔬 |
| I-16 choppiness_ok missing | 🔴 | **לא משחזר** — 6/10 S2 armed, אין 'Missing: choppiness_ok'. מחזק I-17. | 🔴 (לסירוגין) |
| I-17 restart/buffer volatility | 🔬 | five_min buffer=10 (≠64@12:45); choppiness_ok present→armed ⇒ תומך בתנודתיות-גבול-בר. | 🔬 |
| I-18 C-4 TZ-mix freshness | 🟡 | נמשך — woodies_5min/footprint/bars_5min נושאים IL-local (`21:40`) מסומן `+00:00`/`lag_s=null`; cumulative_delta/volume_profile UTC תקין (`18:40`, lag 2.8-8.8s). מפר Rule 4. board `Day Type×stale`/`Footprint×stale`=artifact-TZ. | 🟡 |
| I-19 C-5 pattern-status hang | 🔴 | **לא משחזר** — pattern-status 939ms (200, len 89875), שאר endpoints 73-180ms. נקי. | 🔴 (לסירוגין) |
| I-20 C-6 lag שלילי fresh=true | 🟡 | נמשך — bridge `data_freshness.lag=-10513/fresh=true/threshold=90`. predicate לא אוכף סף. readiness משתמש ב-gates → DEGRADED נכון. | 🟡 |
| I-21 stall ערוץ 5דק' | 🟡 | **לא משחזר** — woodies_5min/bars_5min FRESH 0s, S2 last_bar 13:35 CT (lag 286.6s), cci נע. ערוץ חי. | 🟡 |
| I-22 F-1 pnl_r מנופח ~50× | 🔴 | נמשך — id=10 `$230=92R`, id=13 `$66.88=26.75R`, id=12 `$20=16R` (ערכי-שישי). אין עסקה היום. **חוסם EOD-counterfactual.** | 🔴 |
| I-23 F-2 gateway counters | 🟡 | **לא נצפה** — trades_today=0/daily_pnl=0/shadow_active_count=0 נכון היום (אין עסקה). | 🟡 |
| I-24 POC split + tpo/S3 ב-readiness | 🟡 | **התקדמות מהותית** — gate `footprint` כעת `disabled (S3_MUTE/S5)`, gate `tpo`/`tick_reversal` ABSENT אך `bridge_streams_fresh` passed:true ⇒ **כבר לא חוסמים** (verdict DEGRADED מ-GRAY בלבד). תואם המלצת-SoT (הוצאת streams לא-מחווטים). **CC: לאשר שזו כוונה ולא דריפט.** | 🟡 |

### ערכים גולמיים (13:38 CT)
```
woodies: cci_14=6.1, cci_6_tcci=-63.92, ema_34=7441.07, lsma=7436.31, swi=-63.21, czi=-25.0,
         trend_state=BLUE, predictor_next_cci=-119.39, signal=NEUTRAL, buffer=50, active_patterns=[], NO_SETUP
         dtree: A1 SKIP no patterns · A2 PASS 11 studies · A3 SKIP no patterns this bar · A4 SKIP
                · A5 PASS advisory:calculate_size=reject · A6 SKIP NO_SETUP · A7 SKIP
five_min: running, mode=DAY_TYPE_MODE, buffer=10, opening_type=OPEN_DRIVE, patterns_detected=0, setups_published=0
footprint: running, bars_processed_today=0, buffer=0, cumulative_delta=0, all flow=null, NO_SETUP
day_type: stage=B2, day_type=Trend_Normal, conf=0.38, lock=LOCKED_LOW_CONF, opening_type=UNKNOWN,
          ib_width=WIDE, behavior=DEVELOPING, range=NORMAL, session_min=0, vote_history=[]
gateway: shadow_active_count=0, daily_pnl=0, trades_today=0, demo_enabled=[2,4], live_enabled=[],
         cooldown_active=false, cluster_guard=false, ssv veto=false, chop_state=EXPANDING
readiness: verdict=DEGRADED · bridge_streams_fresh ✓(block) · s1_day_type_classified ✓ Trend_Normal(degrade)
         · s4_trend_not_stuck_gray ✗ GRAY(degrade) · in_rth ✓
global_gates: woodies_5min FRESH 0s(21:40 IL) · footprint [disabled S3_MUTE] FRESH 0s(21:40:07)
         · cumulative_delta FRESH(18:40 UTC,lag 8.8s) · volume_profile FRESH(18:40 UTC,lag 2.8s)
         · tick_reversal_15 ABSENT · tpo ABSENT
freshness: bridge{fresh=true,lag=-10513,last=null} · S2/S4{fresh=true,lag=286.6,last=2026-06-08 21:35:00+03:00}
         · footprint{fresh=false,lag=null,last=null} · S1{fresh=true,last=21:35:02+03:00}
trades(50): only 3, all 2026-06-05 (id=13 sys2 REACTIVE_SHORT $66.88/26.75R; id=12 sys4 HTLB $20/16R; id=10 sys2 BEAR_FLAG_SHORT $230/92R)
endpoint timings: woodies 73ms · footprint 83ms · gateway 106ms · five_min 121ms · five_min_stats 129ms
         · day_type 136ms · trades 180ms · pattern_status 939ms (len 89875)
Dashboard UI: price 7432.75 LIVE 1s · TRD 38% H · chop "39 EXPANDING" · SS NONE · OPEN_DRIVE Trend_Normal
         · IB TODAY H7469.50/L7429 40.5pt WIDE · Y IB dll_missing · UI Woodies CCIDiff -64.41 (≈endpoint TCCI -63.92)
Build-Status board: verdict DEGRADED (trend_state=GRAY); chain Day Type×stale→S3 BLOCKED→Footprint×stale
         →S4 BLOCKED→✓Woodies CCI→✓Min Patterns-5→✓Bridge·Streams; heartbeat <1s; 79m לסגירה
screenshots: ss_24308kk38 (Dashboard) · ss_93909txvf (Build Status decision-tree) — Chrome MCP inline+save_to_disk
```

### NOT-DONE / פערים
- **counterfactual:** אין מועמד הסנאפ-שוט הזה — S4 GRAY-vetoed (active_patterns=[]), S2 ללא detection-בבר, S3 feed-dead/disabled. אין setup שזוהה-ונחסם. (R מה-DB מנופח ~50× I-22 ⇒ ΣR/win-rate של EOD חסום עד תיקון pnl_r.)
- **שינוי-תצורה לבדיקת-CC (חדש):** gate `footprint` כעת `disabled (S3_MUTE/S5)`. **מי השתיק את S3 ומתי? כוונה או דריפט?** משפיע על I-11/I-24. לאשר מול CLAUDE.md/commit.
- **trend_state GRAY/BLUE flicker על cci_14≈0** — engine BLUE(+6.1) מול board GRAY באותו cycle. GRAY חוסם כל S4. **CC: הצלבת WSI/CCI גולמי מול `~/SierraChart_Data/v9_export/` — האם zero-cross אמיתי או trend_state מפגר/תקוע.**
- **FHB-state לא נחשף** — `/five_min/current`+`/stats` לא מחזירים FHB ⇒ I-4 נבדק עקיף. CC: לחשוף FHB.
- **פער Sierra↔backend (חובה לתעד):** כל ערכי-הקלט (CCI/WSI/OHLC/footprint-flow) **לא הוצלבו** מול `~/SierraChart_Data/v9_export/` — read-only כאן, ל-CC. פער UI↔endpoint (TCCI vs cci_14) פנים-backend, לא תחליף.

---

## 14:12 CT — סנאפ-שוט (snapshot #14 היום · ~342 דק' לתוך RTH)

**כותרת:** ⭐ **ה-verdict התהפך DEGRADED→READY.** הגייטים `tick_reversal_15` + `tpo` כעת
`disabled (S3_MUTE/S5)` (ב-13:38 רק `footprint` היה disabled, ושני אלה ABSENT) ⇒
`bridge_streams_fresh` עובר, ויחד עם trend=RED (לא GRAY) ⇒ READY. **שינוי-תצורה — CC לאשר
כוונה/דריפט** (משפיע I-11/I-24). 5דק' חי (I-21 לא משחזר). footprint עדיין 0 ברים (I-11).

### S2 — Five-Min (10/10 armed; אין 'Missing: choppiness_ok'; חוסמות על detection אמיתי)
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|------|---------|---------|---------|------------|---------|
| REACTIVE_LONG | ✓ armed | ✓ | `detection.b2_volume_drop` (b2_vol 37858·b1_vol 8047·ratio 4.70 ✗) | כן — תנאי-תבנית לא מולא | — |
| REACTIVE_SHORT | ✓ armed | ✓ | `detection.b1_buyers` (b1 close 7425.25 open 7432 bear vol 8047) | כן | — |
| INITIATIVE_LONG | ✓ armed | ✓ | `detection.b1_bull` (b1 close 7425.25<open 7432 ✗) | כן | — |
| INITIATIVE_SHORT | ✓ armed | ✓ | `detection.lookback_quiet` (lookback_max 148241·threshold 4828 ✗) | כן | — |
| INV_HNS_LONG | ✓ armed | ✓ | `swing_lows_found` 0/20 ברים | כן | — |
| HNS_TOP_SHORT | ✓ armed | ✓ | `swing_highs_found` 1/20 ברים | כן | — |
| DOUBLE_BOTTOM_EE | ✓ armed | ✓ | `swing_lows_found` 0 | כן | — |
| DOUBLE_TOP_AA / BULL_FLAG / BEAR_FLAG | ✓ armed | ✓ | detection per-bar (pole/neckline/flag) | כן | — |

ארמינג תקין (buffer 27, ערוץ חי lag 172.5s, opening_type=OPEN_DRIVE). patterns_detected=0/setups=0 (אין detection בבר). **אין חסם day_type_gate ואין 'Missing: choppiness_ok'** ⇒ I-16 לא משחזר. FHB-state עדיין לא נחשף ב-endpoint.

### S4 — Woodies (9/9 armed · trend RED · אין GRAY veto · 'not yet detected')
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|------|---------|---------|---------|------------|---------|
| ZLR / TLB / TT / GB100 / HFE / HTLB / FAMIR | ✓ armed | ✓ trend RED (cci_14=-231.41) | `detection.pattern_specific` "not yet detected" → downstream `targets_stop.*`+`exit_rules.ready_to_route` | לא חסם-שגוי — פשוט אין setup בבר | — |

A1 לא veto (trend RED, לא GRAY). אין setup ⇒ אין counterfactual. ZLR=armed "Data ready, trend RED · ZLR not yet detected" (I-3).

### S3 — Footprint (4/4 blocked · feed מת)
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|------|---------|---------|---------|------------|---------|
| ABSORPTION / STACKED_IMBALANCE / SWEEP_RETURN / EXHAUSTION | ✗ | — | `data.buffer_size`+`data.bars_today` — "Insufficient buffer (0 bars, need ≥5)" | כן (אין נתון) | **כל ה-feed**: bars_today=0/buffer 0/cum_delta 0/flow null (I-11) |

### Gates (לא תבניות-ירי)
- **day_type_gate:** Trend_Normal (readiness) — satisfied, לא חוסם S2. (פיצול מול state=Variation — ראה I-1.)
- **chop:** gateway `chop_state=FOUND`, UI "15 FOUND" — לא חוסם (Chop Gates DISABLED per CLAUDE.md).
- **killzone (S6):** board `KZ ✗ לא מחזור` — gate.
- **TPO (S5) + tick_reversal_15:** כעת `disabled (S3_MUTE/S5)` — לא חוסמים (שינוי מ-13:38 שבו היו ABSENT). I-24.

### בדיקת חשודים-פתוחים (register)
| # | ממצא 14:12 | סטטוס |
|---|------------|-------|
| I-1 day_type | **פיצול חזר** — state-endpoint+Dashboard=`Variation 0.38/B2` מול readiness+Build-header=`Trend_Normal` (ב-13:38 כולם הסכימו Trend_Normal). **לא חוסם S2** (10 armed, אין day_type_gate block). residual: opening_type=UNKNOWN (מול five_min/UI OPEN_DRIVE), session_min=0, vote_history=[] ב-~342דק'. Dashboard `Y IB dll_missing`. | 🟡 |
| I-3 ZLR | trend RED, ZLR armed "Data ready · not yet detected", active_patterns=[] (A3 no pattern this bar). אין setup/counterfactual. | 🔬 |
| I-4 S2 דריכה | 10/10 armed, buffer 27, ערוץ חי (lag 172.5s). detection=0/setups=0. דריכה תקינה. FHB לא נחשף. | 🔬 |
| I-11 footprint 0 ברים | **אישור #24** — bars_today=0/buffer 0/cum_delta 0/flow null בעוד gate footprint נכתב עכשיו (`[disabled][FRESH] 0s·22:12:51`). ingest-break, עצמאי מ-I-21 (5דק' חי). gate `disabled S3_MUTE` ⇒ מושתק, לא נפתר. | 🔴 |
| I-14 opening entry | opening_type=OPEN_DRIVE; INITIATIVE_L/S armed (auth FULL, אין SKIP×daytype), חוסמות על detection אמיתי (b1_bull/lookback_quiet). חסם-auth נוקה. שרשרת opening→entry ל-CC. | 🔴 |
| I-15 C-1 trend | engine RED (cci_14=-231.41) + board `s4_trend_not_stuck_gray ✓ RED` — **מסכימים**, אין קונפליקט. פער-UI: פאנל Woodies-CCI≈`-205.63`/CCIDiff 38.23/TrendDown 1.00 מול endpoint cci_14=-231.41 (~26pt); תחתית פאנל -172.5 מול endpoint tcci -163.06. הצלבת Sierra חובה. | 🔬 |
| I-16 choppiness_ok | **לא משחזר** — 10/10 S2 armed, אין 'Missing: choppiness_ok'. מחזק I-17. | 🔴(לסירוגין) |
| I-17 buffer volatility | five_min buffer=27 (≠10@13:38); 10/10 armed. תומך בתנודתיות-גבול-בר. | 🔬 |
| I-18 C-4 TZ-mix | נמשך — woodies_5min(`22:10`)/footprint(`22:12`)/bars_5min(`22:10`) IL-local ללא TZ-marker; cumulative_delta/volume_profile/imbalance UTC (`19:10`). board `Day Type×stale`/`Footprint×stale`=artifact-TZ. מפר Rule 4. | 🟡 |
| I-19 C-5 pattern-status hang | **לא משחזר** — pattern-status 152ms (200, len 88714), כל endpoints <180ms. נקי. | 🔴(לסירוגין) |
| I-20 C-6 lag שלילי | נמשך — bridge `data_freshness.lag=-10627/fresh=true/threshold=90`. (S2/S4 lag=+172.5/fresh=true/thr 660 חיובי-תקין.) predicate לא אוכף סף על lag שלילי. readiness משתמש ב-gates → READY (נכון בהינתן disabled-streams). | 🟡 |
| I-21 stall 5דק' | **לא משחזר** — S2/S4 last_bar=`22:10:00+03:00` (lag 172.5s אמיתי), cci_14 נע (-231.41, לא קפוא). ערוץ חי. | 🟡 |
| I-22 F-1 pnl_r מנופח | נמשך — ערכי-שישי id=13 `$66.88=26.75R`, id=12 `$20=16R`, id=10 `$230=92R`. אין עסקה-טרייה היום. **חוסם EOD-counterfactual.** | 🔴 |
| I-23 F-2 gateway counters | **לא נצפה** — trades_today=0/daily_pnl=0/shadow_active_count=0 נכון היום (אין עסקה). | 🟡 |
| I-24 POC/tpo ב-readiness | **התקדמות — disable מפורש** — tick_reversal_15+tpo (וגם footprint) כעת `disabled (S3_MUTE/S5)`/present:true ⇒ **כבר לא חוסמים** → verdict DEGRADED→READY. תואם המלצת-SoT (הוצאת streams לא-מחווטים). **CC: לאשר כוונה ולא דריפט + מתי בוצע.** | 🟡 |

### ערכים גולמיים (14:12 CT)
```
woodies: cci_14=-231.41, cci_6_tcci=-163.06, ema_34=7437.2, lsma=7431.62, swi=-143.59, czi=-78,
         trend_state=RED, predictor_next_cci=-298.15, signal=NEUTRAL, buffer=50, active_patterns=[], NO_SETUP
         dtree: A1 SKIP no patterns · A2 PASS 11 studies · A3 SKIP no patterns this bar · A4 SKIP
                · A5 PASS advisory:calculate_size=reject · A6 SKIP NO_SETUP · A7 SKIP
five_min: running, mode=DAY_TYPE_MODE, buffer=27, opening_type=OPEN_DRIVE, patterns_detected=0, setups_published=0
footprint: running, hydrated, bars_processed_today=0, buffer=0, cumulative_delta=0, flow null, NO_SETUP
day_type(state): stage=B2, day_type=Variation, conf=0.38, lock=LOCKED_LOW_CONF, opening_type=UNKNOWN,
          ib_width=WIDE, behavior=DEVELOPING, range=NORMAL, session_min=0, vote_history=[]
gateway: shadow_active_count=0, daily_pnl=0, trades_today=0, chop_state=FOUND, cluster_guard=false
readiness: verdict=READY · bridge_streams_fresh ✓(block) · s1_day_type_classified ✓ Trend_Normal(degrade)
         · s4_trend_not_stuck_gray ✓ RED(degrade) · in_rth ✓
global_gates: woodies_5min FRESH 0s(22:10 IL) · footprint [disabled S3_MUTE] FRESH 0s(22:12:51 IL)
         · cumulative_delta FRESH(19:10 UTC) · volume_profile FRESH(19:12 UTC)
         · tick_reversal_15 [disabled] DEAD 4521min(06-05 15:51) · imbalance FRESH(19:10 UTC)
         · tpo [disabled] DEAD(2023-11-25) · bars_5min FRESH 0s(22:10 IL)
freshness: bridge{fresh=true,lag=-10627,last=null,thr=90} · S2/S4{fresh=true,lag=172.5,last=2026-06-08 22:10:00+03:00,thr=660}
         · S3{fresh=false,lag=null,last=null} · S1{fresh=true,last=22:10:06+03:00}
trades(50): only 3, all 2026-06-05 (id=13 sys2 SHORT $66.88/26.75R · id=12 sys4 HTLB $20/16R · id=10 sys2 $230/92R)
endpoint timings: woodies 12ms · pattern_status 152ms (len 88714) · others <180ms
Dashboard UI: price 7413.75 LIVE 3s · VAR 38% M · chop "15 FOUND" · SS NONE · OPEN_DRIVE/Variation
         · IB TODAY H7469.50/L7429 40.5pt WIDE · Y IB dll_missing · TODAY RANGE H7476.75/L7414.75 62pt
         · Woodies-CCI panel CCI≈-205.63/CCIDiff 38.23/TrendDown 1.00 (vs endpoint cci_14=-231.41, ~26pt)
Build-Status board: verdict READY; day Trend_Normal(header); S2,S4 armed (S2 armed 10); Day Type×stale+Footprint×stale(artifact-TZ I-18);
         Woodies-CCI fresh 49s · Min Patterns-5 fresh 49s; KZ ✗ לא מחזור; heartbeat <1s; 45m לסגירה
screenshots: ss_9297052vs (Dashboard) · ss_2166m14u9 (Build Status decision-tree) — Chrome MCP, save_to_disk
```

### NOT-DONE / פערים
- **⭐ שינוי-תצורה (חדש, ל-CC):** `tick_reversal_15` + `tpo` gates עברו ABSENT→`disabled (S3_MUTE/S5)` בין 13:38↔14:12, מצטרפים ל-`footprint` שכבר disabled. ⇒ verdict DEGRADED→READY. **מי השתיק ומתי? כוונה (תואם SoT של I-24) או דריפט?** לאשר מול CLAUDE.md §S3_MUTE/I-11 + commit.
- **פיצול day_type חזר (I-1):** state+Dashboard=Variation מול readiness+board-header=Trend_Normal. לא חוסם, אך פער-instance נמשך.
- **counterfactual:** אין מועמד — S4 ללא detection (active_patterns=[]), S2 ללא detection-בבר, S3 feed-dead. אין setup שזוהה-ונחסם. (pnl_r מנופח ~50× I-22 ⇒ ΣR/win-rate של EOD חסום עד תיקון.)
- **פער Sierra↔backend (חובה לתעד):** כל ערכי-הקלט (CCI/WSI/OHLC/footprint-flow) לא הוצלבו מול `~/SierraChart_Data/v9_export/` — read-only כאן, ל-CC. פער UI↔endpoint (panel -205.63 vs cci_14 -231.41) פנים-backend, לא תחליף ל-Sierra.
- **EOD (I-9):** ריצה זו 14:12 CT — בתוך RTH. ה-EOD חייב לרוץ **אחרי 15:00 CT** (סגירה ~45 דק' מעכשיו).

---

## 🕐 14:53 CT — סנאפ-שוט (snapshot) · ~6 דק' לסגירה (אחרון RTH)

**חלון:** RTH פתוח (08:30–15:00 CT), זהו הסנאפ-שוט האחרון לפני הסגירה. כל ה-endpoints ענו <100ms (pattern-status 94ms/len 87085) — I-19 נקי, אין hang.

### טבלת 5-השאלות — תבניות S2/S3/S4

| תבנית/חשוד | 1.יש נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---|---|---|---|---|---|
| **S2 · כל 10 התבניות** | כן (buffer 43, mode DAY_TYPE) | כן — ערוץ חי (lag 100.2s, last 22:40 IL=14:40 CT) | **detection אמיתי בלבד** per-bar (Reactive_L=b2_volume_drop · Reactive_S=b1_buyers · Init_L/S=b1_expansion · InvHnS=swing_lows · HnsTop=swing_highs · DblBot=eve_variant · DblTop=swing_highs · BullFlag=pole_found · BearFlag=flag_retrace) | כן — אין setup-בבר, חסימה מוצדקת | — אין 'Missing: choppiness_ok' ואין day_type_gate block ⇒ **I-16 לא משחזר**, day_type לא חוסם S2 |
| **S4 · כל 9 התבניות** | כן (buffer 50) | כן — trend RED (cci_14=-161.18), לא GRAY | `detection.pattern_specific` (no pattern this bar) + `targets_stop.r_t1_gate/stop` — **אין A1-veto** (RED≠GRAY) | כן — NO_SETUP מוצדק | — active_patterns=[] |
| **S4 · ZLR (I-3)** | armed | כן (trend RED) | A3 "no pattern this bar" (לא A1-veto הפעם, ≠GRAY) | כן | — אין setup-ZLR טרי; **אין counterfactual** |
| **S3 · כל 4 התבניות** | **לא** — buffer 0 | לא — feed מת | `data.buffer_size` + `data.bars_today` (=0) | לא רלוונטי (אין נתון) | **I-11**: footprint `bars_today=0/buffer 0/cum_delta 0/flow null`. gate `footprint`=`[disabled S3_MUTE]` ⇒ לא חוסם לוח |

### סטטוס חשודים (register)

| # | ממצא 14:53 | סטטוס |
|---|---|---|
| I-1 day_type split | **פיצול נמשך** — state+Dashboard=`Variation 0.38/B2` מול readiness=`Trend_Normal`. opening_type=UNKNOWN (מול five_min OPEN_DRIVE), session_min=0, vote_history=[] ב-~383דק' לתוך RTH. **לא חוסם S2** (10/10 armed). | 🟡 |
| I-3 ZLR | armed trend RED, active_patterns=[] (A3 no pattern this bar). אין setup/counterfactual. | 🔬 |
| I-11 footprint ingest | **אישור #25** — `bars_today=0`/buffer 0/cum_delta 0/flow null; gate footprint=`[disabled S3_MUTE][FRESH] 0s · 22:41:38` (נכתב עכשיו) בעוד ערוץ 5דק' חי ⇒ file→bridge→buffer שבור, עצמאי מ-I-21, מושתק לא-נפתר. | 🔴 |
| I-16 choppiness_ok | **לא משחזר** — 10/10 S2 armed, אין 'Missing: choppiness_ok' (gateway chop_state=FOUND). מחזק I-17. | 🔬 |
| I-17 buffer-flip | five_min buffer=43 (≠27@14:12); 10/10 armed, choppiness_ok present ⇒ תומך בתנודתיות-גבול-בר. | 🔬 |
| I-18 TZ-mix | **נמשך** — woodies_5min(`22:25`)/footprint(`22:41`)/bars_5min IL-local מסומן `+00:00`/`lag_s=null`; cumulative_delta(`19:39:59`)/volume_profile UTC + lag אמיתי (101s). board `Day Type×stale`/`Footprint×stale`=artifact-TZ. מפר Rule 4. | 🟡 |
| I-19 pattern-status hang | **לא משחזר** — 94ms (200, len 87085), כל endpoints <100ms. נקי. | 🔬 |
| I-20 lag-predicate | **נמשך + מאומת דו-כיווני** — bridge `fresh=true/lag_s=-9799.8` (שלילי ~-2.7h); **S4 `fresh=true/lag_s=1000.2` (~16.7דק', מעל סף 660)** ⇒ ה-predicate לא אוכף סף לא על lag שלילי ולא על lag חיובי-מעל-סף. readiness משתמש ב-gates → READY (נכון). | 🟡 |
| I-21 stall 5דק' | **לא משחזר (stall)** — cci_14 נע -231.41@14:12→**-161.18** (לא קפוא), S2 last_bar=`22:40 IL`(=14:40 CT) lag 100.2s. **אך residual:** ערוץ woodies_5min/S4 last_bar=`22:25`(=14:25 CT) lag **1000s (~16דק')** — מפגר ~15דק' אחרי S2; הלוח מציג `Woodies CCI · stale 25m`. פיגור-ערוץ, לא freeze מלא. | 🟡 |
| I-22 F-1 pnl_r מנופח | **נמשך** — ערכי-שישי id=10 `$230=92R`, id=13 `$66.88=26.75R`, id=12 `$20=16R`. אין עסקה-טרייה היום. **חוסם EOD-counterfactual.** | 🔴 |
| I-23 F-2 gateway counters | **לא נצפה** — trades_today=0/daily_pnl=0/shadow_active_count=0 נכון היום (אין עסקה). | 🟡 |
| I-24 POC/tpo ב-readiness | **disable מפורש נמשך** — tick_reversal_15+tpo+footprint כולם `disabled (S3_MUTE/S5)`/critical:false ⇒ לא חוסמים → verdict READY. תואם המלצת-SoT. **CC: לאשר כוונה ולא דריפט + מתי בוצע.** | 🟡 |

### ערכים גולמיים (14:53 CT)
```
woodies: cci_14=-161.18, cci_6_tcci=-108.12, ema_34=7432.79, lsma=7419.2, swi=82.68, czi=-109,
         trend_state=RED, predictor_next_cci=-144.16, signal=NEUTRAL, buffer=50, active_patterns=[], NO_SETUP
         dtree: A1 SKIP no patterns · A2 PASS 11 studies · A3 SKIP no patterns this bar
                · A4 SKIP no touch-points · A5 PASS advisory:calculate_size=reject · A6 SKIP NO_SETUP
                · A7 SKIP no fire_setup (gateway/pre_fire run at route_setup)
five_min: running, mode=DAY_TYPE_MODE, buffer=43, opening_type=OPEN_DRIVE, patterns_detected=0, setups_published=0
footprint: running, hydrated, bars_processed_today=0, buffer=0, cumulative_delta=0, flow null, NO_SETUP
day_type(state): stage=B2, day_type=Variation, conf=0.38, lock=LOCKED_LOW_CONF, opening_type=UNKNOWN,
         ib_width=WIDE, behavior=DEVELOPING, session_min=0, vote_history=[]
gateway: shadow_active_count=0, daily_pnl=0, trades_today=0, chop_state=FOUND, cluster_guard inactive(0 attempts/60s)
readiness: verdict=READY · reason="all checks passed" · bridge_streams_fresh ✓(block)
         · s1_day_type_classified ✓ Trend_Normal(degrade) · s4_trend_not_stuck_gray ✓ RED(degrade) · in_rth ✓
S2 patterns: 10/10 armed — חוסמות על detection per-bar (b2_volume_drop/b1_buyers/b1_expansion/swing_*/eve_variant/pole_found/flag_retrace)
S4 patterns: 9/9 armed — detection.pattern_specific + targets_stop.r_t1_gate/stop
S3 patterns: 4/4 blocked — data.buffer_size + data.bars_today (=0)
global_gates: woodies_5min present/crit · [FRESH] 0s · 22:25:00(+00:00 IL-local) lag_s=null
         · footprint [disabled S3_MUTE/S5] FRESH 22:41:38 lag_s=null (bars_today=0!)
         · cumulative_delta present/crit FRESH 19:39:59 UTC lag 101.2s · volume_profile crit (<360s)
         · tick_reversal_15 [disabled S3_MUTE/S5] crit:false · imbalance crit (<90s)
         · tpo [disabled] DEAD 2023-11 · bars_5min present/crit (<360s)
data_freshness(per-system): bridge{fresh=true,lag=-9799.8,thr=90} · S2{fresh=true,lag=100.2,last=22:40:00+03:00}
         · S4{fresh=true,lag=1000.2(~16.7m),last=22:25:00+03:00} · S3{fresh=false,lag=null} · S1{fresh=true,last=22:40:08+03:00}
trades(50): only 3, all 2026-06-05 (id=13 sys2 SHORT $66.88/26.75R · id=12 sys4 SHORT $20/16R · id=10 sys2 SHORT $230/92R)
endpoint timings: woodies 24ms · footprint 5ms · five_min 16ms · stats 26ms · trades 41ms · gateway 37ms · day_type 6ms · pattern-status 94ms
Dashboard UI(:3000 live): VAR 38% M · price 7418.50 LIVE 0.5s · — CLOSED · $0/$200 · WR 0% · SHADOW 0t $0 · Tick Rev
Build-Status board: verdict READY; day Trend_Normal(header); S2 armed 10 + "FIRING" badge (אך patterns_detected=0/אין עסקה); S4 armed;
         heartbeat <1s; 11m→close; KZ ✗ לא-מחזור; DATA_FRESHNESS: Day Type ●? stale · Footprint ●? stale (artifact-TZ I-18)
         · Woodies CCI ● 660s · stale 25m · Min Patterns-5 ● 660s · warming 5m; שכבה 0 SIERRA→BRIDGE→API
screenshot: ss_8234thgv3 (Build Status · עץ-החלטות, Chrome MCP) — ⚠️ save_to_disk לא נשמר לקובץ בסשן זה; ה-ID inline בלבד
```

### NOT-DONE / פערים
- **counterfactual:** אין מועמד — S4 ללא detection (active_patterns=[]), S2 ללא detection-בבר, S3 feed-dead. אין setup שזוהה-ונחסם. (I-22 pnl_r מנופח ~50× ⇒ ΣR/win-rate של EOD חסום עד תיקון נוסחת pnl_r.)
- **⭐ residual חדש למעקב (I-21):** ערוץ woodies_5min מפגר ~15דק' אחרי five_min (S4 last 14:25 vs S2 last 14:40, lag 1000s>660 thr) בעוד CCI נע — לא freeze אך פיגור-ערוץ-יחיד. לבדוק אם woodies-export מתעדכן בתדירות נמוכה יותר מ-five_min, או stall מתהווה לקראת סגירה. **ל-CC.**
- **פער Sierra↔backend (חובה, ל-CC):** כל ערכי-הקלט (CCI/WSI/OHLC/footprint-flow) **לא הוצלבו** מול `~/SierraChart_Data/v9_export/` — read-only כאן. כל פער Sierra↔backend = ממצא; להצליב cci_14=-161.18/swi=82.68/ema_34=7432.79 מול ה-export הגולמי.
- **תצורת disable (I-24, ל-CC):** `tick_reversal_15`+`tpo`+`footprint` כולם `disabled (S3_MUTE/S5)`. לאשר מול CLAUDE.md §S3_MUTE/I-11 שזו כוונה ולא דריפט, ומתי בוצע (commit).
- **EOD (I-9):** ריצה זו 14:53 CT — ~6 דק' לסגירה, עדיין בתוך RTH. ה-EOD חייב לרוץ **אחרי 15:00 CT** (23:00 IL) — לא נכלל בסנאפ-שוט זה.

---

## Snapshot 15:07 CT (2026-06-08 Mon)

מחוץ ל-RTH, מדלג — השעה 15:07 CT עברה את סגירת ה-RTH (08:30–15:00 CT). אין snapshot מסחר; הריצה הסתיימה ללא קריאות API/צילום.

---

## Snapshot 15:38 CT (2026-06-08 Mon)

מחוץ ל-RTH, מדלג — השעה 15:38 CT עברה את סגירת ה-RTH (08:30–15:00 CT). אין snapshot מסחר; הריצה הסתיימה ללא קריאות API/צילום. (RTH הבא: שלישי 2026-06-09 08:30 CT.)
