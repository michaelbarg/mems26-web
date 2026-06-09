# MEMS26 Pattern Diagnostics — 2026-06-09

## 08:07 CT — מחוץ ל-RTH, מדלג

RTH = 08:30–15:00 שיקגו (CT). השעה הנוכחית 08:07:54 CDT — לפני פתיחת ה-RTH (08:30). מחוץ לחלון, מדלג על בדיקת התבניות העמוקה. הריצה הבאה (כל 30 דק') תיפול בתוך ה-RTH ותבצע את ה-snapshot המלא.

---

## 08:42 CT — Snapshot עמוק #1 (בתוך RTH)

**הקשר-שלב:** ~12 דק' לתוך RTH, **First-Hour-Tactical** (IB טרם הושלמה). חלק מה"חסימות" כאן **צפויות-שלב** (day_type טרם סווג עד תום ה-IB, FHB טרם eligible) ולא באג — מסומן במפורש לכל פריט.
**Latency:** כל 8 ה-endpoints ענו <75ms; `build/pattern-status` **71ms** (I-19 לא משחזר).
**צילומי-מסך (Chrome MCP):** Dashboard=`ss_9174b893x` · Build-Status decision-tree=`ss_8552f6f4c` (verdict **DEGRADED**, chain: Day Type×stale → S3 BLOCKED → Footprint×stale → Woodies CCI✓ → S2 BLOCKED → Min-Patterns✓ → Bridge✓).

### ערכים גולמיים
- **woodies/current:** running✓ hydrated✓ · `cci_14=+218→+220` (נע, לא קפוא) · `cci_6_tcci=+142` · `ema_34=7450.7` · `lsma=7457.6` · `swi=181` · `czi=62` · **trend_state=BLUE** · signal=NEUTRAL · `classification=NO_SETUP` · buffer=50 · `active_patterns=[]` · last_reasoning="TLB SHORT size=half: CCI=141.2, trend=BLUE, conf=0.53, group=CONTINUATION".
- **footprint/current:** running✓ hydrated✓ · **bars_today=0 · buffer=0 · cumulative_delta=0 · cot=0 · amt=null** · flow null.
- **five_min/current + /stats:** running✓ · `mode=FIRST_HOUR_TACTICAL` · buffer=9 · `opening_type=OPEN_DRIVE` · patterns_detected=0 · setups_published=0.
- **day_type/state:** `stage=A3 · day_type=UNKNOWN · confidence=0 · lock=PENDING · opening_type=UNKNOWN · ib_width=UNKNOWN · behavior=DEVELOPING · vote_history=[]`.
- **gateway/status:** trades_today=0 · shadow_active=0 · daily_pnl=0 · **chop_state=FOUND** · cooldown/cluster_guard/ssv כולם inactive · demo_enabled=[2,4] · live_enabled=[].
- **readiness:** verdict=**DEGRADED**, reason=`day_type=UNKNOWN`. checks: `bridge_streams_fresh ✓(block)` · `s1_day_type_classified ✗(degrade) day_type=UNKNOWN` · `s4_trend_not_stuck_gray ✓ BLUE` · `in_rth ✓`.
- **trades/recent:** 3 עסקאות, **כולן 2026-06-05** (אין עסקה-טרייה היום): id=13 `$66.88=26.75R`, id=12 `$20=16R`, id=10 `$230=92R` (אינפלציית-R נמשכת, I-22).
- **global_gates (bridge):** woodies_5min crit `[FRESH] ts 2026-06-10 22:40` ⚠️ · footprint `[disabled S3_MUTE][FRESH] 06-09 16:39 IL` · cumulative_delta `[FRESH] 13:35 UTC` · volume_profile `[FRESH] 13:39 UTC` · tick_reversal_15 `[disabled][DEAD] מ-06-05 15:51` · imbalance `[FRESH] 13:20 UTC (~22דק' > 90s req)` · tpo `[disabled][DEAD] 2023-11-25` · bars_5min `[FRESH] 16:35 IL`.
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-118804 (~-33h) · fresh=true · threshold=90` (I-20).

### תבניות-ירי — 5 שאלות

**S4 · Woodies (ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR):**
1. **יש נתון?** כן — 11 studies present (A2 PASS), cci_14 נע +218, buffer 50.
2. **הגיוני?** כן — CCI חיובי-גבוה ⇒ trend_state=BLUE עקבי (uptrend חזק בפתיחה). engine↔board מסכימים BLUE (אין C-1).
3. **מה חסם?** כל 7 התבניות **armed** אך חסומות ב-`stage_a1.day_type_gate` (day_type=UNKNOWN) + `detection.pattern_specific` (אין תבנית-ירה על הבר) + `targets_stop.r_t1_gate`/`stop_price`. **אין A1 trend-veto** (trend=BLUE, לא GRAY).
4. **צריך לחסום?** day_type_gate — **צפוי-שלב** (IB טרם הושלמה, 12 דק' לתוך RTH). detection — לגיטימי (אין setup). ⇒ חסימה מוצדקת בשלב זה.
5. **מה חסר?** day_type (תלוי השלמת IB). ZLR: trend BLUE ⇒ A1 לא חוסם — ממתין לתבנית ארמד. אין counterfactual (I-3 ללא שינוי).

**S2 · Five-Min (10 תבניות):**
1. **יש נתון?** כן — buffer 9, mode=FIRST_HOUR_TACTICAL, ערוץ 5דק' חי.
2. **הגיוני?** כן — opening_type=OPEN_DRIVE, buffer גדל.
3. **מה חסם?** כל 10 חסומות ב-`day_type_gate.day_type_known` + `day_type_gate.auth_table_cell` + **`data.fhb_eligible`** + detection. **הפעם לא `choppiness_ok`** (chop_state=FOUND, מחווט — I-16 לא משחזר).
4. **צריך לחסום?** **צפוי-שלב** — fhb_eligible=false ב-12 דק' לתוך RTH הוא תקין (FHB צובר עד בר 4); day_type_gate ימתין להשלמת IB. חסימה מוצדקת בשלב.
5. **מה חסר?** day_type (IB), FHB-progression (זמן). FHB-state עדיין לא נחשף ב-endpoint (I-4 residual).

**S3 · Footprint (Absorption/Stacked-Imbalance/Sweep-Return/Exhaustion):**
1. **יש נתון?** **לא** — bars_today=0, buffer=0, flow null.
2. **הגיוני?** לא — קובץ-היצוא `[FRESH] 0s` (נכתב עכשיו) אך 0 ברים מגיעים ל-buffer.
3. **מה חסם?** כל 4 ב-`data.buffer_size` + `data.bars_today` ("Insufficient buffer").
4. **צריך לחסום?** כן טכנית (אין נתון), אבל ה**שורש** הוא **I-11 ingest-break** — מושתק `disabled(S3_MUTE)`, לא חוסם לוח.
5. **מה חסר?** נתיב file→bridge→buffer של footprint (I-11, אישור #26 — ראה למטה).

### חשודים פתוחים — בדיקה עמוקה

| # | ממצא @08:42 | סטטוס |
|---|-------------|-------|
| **I-1** day_type=UNKNOWN | state=`A3/UNKNOWN/conf0/opening UNKNOWN/vote_history=[]` ב-~12דק' לתוך RTH. **UNKNOWN צפוי-שלב** (IB טרם הושלמה, stage A3). readiness `s1_day_type_classified ✗ degrade` ⇒ verdict DEGRADED. מוקדם להכריע פיצול-instance — נטר ב-snapshot הבא (post-IB ~09:30). | 🟡 (early-IB) |
| **I-3** ZLR לא ירה | trend=**BLUE** (cci_14=+218) ⇒ אין A1-veto; ZLR armed אך `active_patterns=[]` (A3 no pattern this bar). אין setup/counterfactual. | 🔬 ללא שינוי |
| **I-4** S2 דריכה | ערוץ חי buffer 9, mode FHT, detection רץ; חסימה ב-fhb_eligible (צפוי-שלב). דריכה תקינה. FHB-state לא נחשף. | 🔬 |
| **I-11** S3 footprint 0 ברים | **אישור #26 — עצמאות מוכחת שוב:** gate footprint `[FRESH] 0s · 16:39 IL` (נכתב עכשיו) בעוד ערוץ 5דק'/woodies **חי** (cci נע) — ועדיין bars_today=0/buffer 0/flow null. file→bridge→buffer שבור, עצמאי מ-I-21. מושתק `disabled(S3_MUTE)`. | 🔴 (מושתק) |
| **I-15** C-1 trend conflict | engine `cci_14=+218/BLUE` + board `s4_trend_not_stuck_gray ✓ BLUE` — **מסכימים**, אין קונפליקט. פער-UI: פאנל Woodies-CCI `CCIDiff -35.07` (מציג cci_6/נגזר) מול endpoint +218 — skew-תצוגה רגיל. הצלבת Sierra חובה. | 🔬 לא משחזר |
| **I-16** choppiness_ok חסר | **לא רלוונטי היום** — chop_state=FOUND (מחווט); החוסם של S2 הוא day_type_gate+fhb_eligible, **לא** choppiness_ok. | 🔬 לא משחזר |
| **I-18** TZ-mix freshness | woodies_5min/footprint/bars_5min נושאים זמן IL ללא TZ-marker אמין (lag_s=null); cumulative_delta/volume_profile/imbalance ב-UTC תקין. **חידוד חדש:** ts של `woodies_5min` = **`2026-06-10 22:40` — תאריך-עתיד (מחר)**, לא רק offset IL +3h. ⇒ פער חמור מהרגיל — ראה ממצא-חדש. מפר Rule 4. | 🟡 + חידוד |
| **I-19** pattern-status hang | חזר ב-71ms (200). נקי. | 🔬 לא משחזר |
| **I-20** lag שלילי fresh=true | bridge `lag_seconds=-118804 (~-33h)/fresh=true/threshold=90` — ה-predicate לא אוכף סף על lag שלילי. readiness משתמש ב-gates → DEGRADED נכון. | 🟡 נמשך |
| **I-22** pnl_r מנופח ~50× | נמשך, גלוי בערכי-06-05: id=10 92R($230), id=13 26.75R($66.88), id=12 16R($20). אין עסקה-טרייה. חוסם EOD-counterfactual. | 🔴 נמשך |
| **I-23** gateway counters | `trades_today=0/daily_pnl=0/shadow_active=0` — **נכון היום** (אין עסקה). לא ניתן לשחזר בלי עסקה-טרייה. | 🟡 לא נצפה |
| **I-24** S5/TPO + dead-streams | tick_reversal_15+tpo+footprint כולם `disabled (S3_MUTE/S5)`/critical:false ⇒ **לא חוסמים** את הלוח (bridge_streams_fresh ✓). verdict DEGRADED נובע מ-day_type בלבד, לא מ-streams מתים. תואם המלצת-SoT. | 🟡 |
| **I-21** stall 5דק' | **לא משחזר** — ערוץ 5דק'/woodies חי (cci נע +218→+220, buffer 50). אין freeze. | 🟡 |

### ⚠️ ממצא-חדש (לדגל ל-CC) — `woodies_5min` עם ts תאריך-עתיד
gate `woodies_5min` (critical) מדווח `last_bar_ts = 2026-06-10 22:40:00` — **יום קדימה** מהזמן הנוכחי (06-09 13:42 UTC), `lag_s=null`. בעוד `bars_5min` (אותה משפחת IL-local) מראה `06-09 16:35`. ⇒ זה **לא** ה-offset הרגיל של I-18 (IL +3h); זהו ts **עתידי בכ-30h**. הערוץ עצמו חי (cci נע, buffer 50) — ה**נתון** תקין אך ה**חותמת** שגויה. מפר Rule 4 + Rule 1 (TZ ambiguity / ts לא-שפוי). **מקור-אמת: להצליב מול `~/SierraChart_Data/v9_export/` (woodies_5min) — האם Sierra מייצא ts עתידי, או שה-bridge ממיר שגוי?** ⇒ **ל-CC**, לא כאן.

### מקור-אמת — דורש הצלבת Sierra (ל-CC, לא כאן)
- `cci_14=+218`/trend BLUE — להצליב מול Sierra CCI-14/TCCI גולמי ב-`v9_export/` (פער UI↔engine נמשך, I-15).
- woodies_5min ts עתידי (06-10 22:40) — להצליב מול mtime+last-bar בקובץ Sierra.
- footprint file `[FRESH]` אך 0 ברים — נתיב ingest file→bridge→buffer (I-11).

**NOT-DONE:** day_type-instance (פיצול/session_min) לא נבדק לעומק — מוקדם מדי (pre-IB, stage A3); נטר post-IB. atr_daily/Y-IB `dll_missing` (Dashboard) — חשוד-שורש ל-opening_type/IB — ל-CC.

---

## [2026-06-09 09:13 CT] Snapshot עמוק #2 (~43דק' לתוך RTH, FIRST_HOUR_TACTICAL, IB טרם הושלמה)

**מקרא:** RTH 08:30–15:00 CT · all 8 endpoints ענו <200ms · build/pattern-status=136ms (I-19 נקי) · ערוץ 5דק' חי (S2/S4 lag 63.3s, fresh).
**צילומים (inline session, לא נשמרו לדיסק):** Dashboard=`ss_8950w73tx` · Build-Status decision-tree=`ss_6970q1jji`.

### 🆕 ממצא מוביל — **עסקת-S4 טרייה ירתה היום** (סותר את "אין עסקה היום" מ-08:42)
`v9_trades` id=**20** HTLB SHORT, `entry_ts=2026-06-09T16:50:05+03:00` = **08:50 CT** (firing_system=4). board pattern-status: "HTLB fired earlier today at 2026-06-09T13:50:05Z · count=1". C3 עדיין OPEN (shadow פעיל). זוהי **הירייה הראשונה של סשן 06-09** — מאפשרת לראשונה לבדוק I-22/I-23 על עסקה **בת-יום**.

### תבניות ירי — 5 השאלות

| מערכת/תבנית | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|---|---|---|---|---|---|
| **S2 · כל 10 התבניות** (REACTIVE/INITIATIVE L+S, INV_HNS, HNS_TOP, DBL_BOTTOM_EE, DBL_TOP_AA, BULL/BEAR_FLAG) | ✅ ערוץ חי buffer=77, mode=FIRST_HOUR_TACTICAL, opening_type=OPEN_DRIVE, last=REACTIVE_SHORT conf 80 | ✅ ערכים שפויים; cci_14 history buffer=19 (≥14), lag 63s | כל 10 חסומות `Missing: day_type_gate.day_type_known, day_type_gate.auth_table_cell` | **מוצדק-שלב** — day_type=UNKNOWN כי IB טרם הושלמה (~43דק'); לא over-conservative | day_type מסווג (תלוי I-1, post-IB ~09:30). **לא** choppiness_ok (chop_state=FOUND, מחווט) |
| **S3 · ABSORPTION/STACKED_IMB/SWEEP_RETURN/EXHAUSTION** | ❌ `bars_processed_today=0`, buffer=0, flow/delta/cot כולם null/0 | ❌ 0 ברים ב-~43דק' RTH = לא-הגיוני | כל 4 "Insufficient buffer (0 bars, need ≥5)" | טכנית כן (אין נתון); השורש=**I-11 ingest-break** | נתיב file→bridge→buffer של footprint (I-11 אישור #27) |
| **S4 · HTLB** (Horizontal Trend Line Break) | ✅ **ירה ב-08:50 CT** (id=20) | ✅ entry 7489.25/stop 7491.75 שפוי | — (נורתה) | — | — |
| **S4 · HFE** (Hook From Extreme) | ✅ active_patterns=[HFE] SHORT conf 0.6, group REVERSAL, entry 7465/stop 7470.25 | ✅ שפוי | **A7 FAIL** "missing fire_setup for routable pattern" (A1–A6 PASS: trend=BLUE, 11 studies, A5 sizing=half, A6 STRATEGIC) | תקין — A7 דורש fire_setup; אין setup-בר זה | — (A4 advisory degraded: day_type/tpo/killzone/layer0 missing — לא חוסם) |
| **S4 · ZLR/TLB/TT/GB100/CCI-HNS/Failed-ZLR/Hook** (יתר) | ⚠️ נתון קיים | ⚠️ | **A1 veto: trend_state=GRAY** (board) — **לפני** A3-detection | ⚠️ **ראה I-15** — engine מחזיק BLUE, board GRAY (cci_14=+18.62 near-zero) → קונפליקט | מקור-אמת אחד ל-trend_state (Sierra) |

### חשודים פתוחים — בדיקה עמוקה

| # | ממצא @09:13 CT | סטטוס |
|---|----------------|-------|
| **I-1** day_type=UNKNOWN | state=`A3/UNKNOWN/conf0/opening_type=UNKNOWN/session_min=0/vote_history=[]` ב-~43דק' לתוך RTH. **UNKNOWN עדיין צפוי-שלב** (IB מסתיימת ~09:30, stage A3). readiness `s1_day_type_classified ✗ degrade reason=day_type=UNKNOWN`. residual: five_min `opening_type=OPEN_DRIVE` מול state `UNKNOWN` (פער-instance) + `session_min=0` (instance לא-עוקב-סשן). נטר post-IB בסנאפ הבא. | 🟡 (early-IB) |
| **I-3** ZLR לא ירה | trend=BLUE (engine cci_14=+18.62) אך board A1-veto=GRAY. בכל מקרה active_patterns=[HFE] בלבד, **אין ZLR** בבר זה (A3 no ZLR). אין setup/counterfactual. | 🔬 ללא שינוי |
| **I-4** S2 דריכה | ערוץ חי buffer=77, mode=FHT, detection רץ (patterns_detected=0/setups=0 — אין detection בבר). חסימה ב-day_type_gate (צפוי-שלב). דריכה תקינה. FHB-state לא נחשף ב-endpoint. | 🔬 |
| **I-11** S3 footprint 0 ברים | **אישור #27 — עצמאות מוכחת שוב:** gate `footprint` present=true (נכתב), בעוד `bars_processed_today=0`/buffer 0/cumulative_delta 0/flow null/last_bar_ts=null, 4 תבניות "Insufficient buffer". ערוץ 5דק'/woodies **חי** (I-21 פתור) ⇒ file→bridge→buffer שבור, עצמאי מ-I-21. מושתק `critical:false (S3_MUTE)`. | 🔴 (מושתק) |
| **I-15** C-1 trend conflict | **משחזר!** engine `woodies/current` trend_state=**BLUE** (cci_14=+18.62, A1 PASS, HFE armed→A7) מול board readiness `s4_trend_not_stuck_gray ✗ GRAY` + pattern-status: כל 9 woodies "A1 veto trend_state=GRAY". cci_14=+18.62 **near-zero** ⇒ flicker/regime-disagreement סביב אפס. שונה מ-08:42 (שם שניהם הסכימו BLUE@+218). הצלבת Sierra CCI-14/TCCI חובה. | 🔬 משחזר |
| **I-16** choppiness_ok | **לא רלוונטי היום** — gateway chop_state=FOUND (מחווט); החוסם של כל 10 S2 = day_type_gate, **לא** choppiness_ok. | 🔬 לא משחזר |
| **I-18** TZ-mix freshness | נמשך: woodies_5min/footprint/bars_5min נושאים IL (`2026-06-09 17:10:00+03:00`) ללא TZ-marker אמין (lag_s=null במקצת השדות); cumulative_delta/volume_profile/imbalance ב-UTC תקין. **הערה:** ה-future-date ts (06-10) שנצפה ב-08:42 **לא משחזר** ברמת ה-gate — כעת offset IL +3h רגיל. מפר Rule 4. | 🟡 נמשך |
| **I-19** pattern-status hang | חזר ב-**136ms** (200, len 84575). נקי. | 🔬 לא משחזר |
| **I-20** lag שלילי fresh=true | bridge `data_freshness.lag_seconds=-116936 (~-32.5h)/fresh=true/threshold=90` — predicate לא אוכף סף על lag שלילי. readiness משתמש ב-gates → DEGRADED נכון. | 🟡 נמשך |
| **I-21** stall 5דק' | **לא משחזר** — S2/S4 `last_bar_ts=2026-06-09 17:10:00+03:00`, lag 63.3s, fresh=true; buffer S2=77/S4=50; cci_14 נע. אין freeze. | 🟡 |
| **I-22** pnl_r מנופח | **🆕 שוחזר על עסקה בת-יום (id=20):** HTLB SHORT entry 7489.25/stop_init 7491.75 ⇒ risk=2.5pt×$5=**$12.50/חוזה**. C1 HIT $17.5→מדווח **14R** (אמיתי 17.5/12.5=**+1.4R**); C2 HIT $35→מדווח **28R** (אמיתי +2.8R); total מדווח 21R; UI right-panel "$53 (42.0R)". ⇒ R=`pnl_usd ÷ $1.25` (ערך-טיק) ולא `÷ risk_$` — אינפלציה **×10** מאומתת על fire-בן-יום (לראשונה, לא רק ערכי-06-05). חוסם EOD-counterfactual. | 🔴 נמשך |
| **I-23** gateway counters | **🆕 שוחזר עם עסקה בת-יום:** id=20 ירה היום + C3 OPEN, אך gateway `trades_today=0`/`daily_pnl=0` (שגוי, אמור ≥1). `shadow_active_count=1` (נכון — סופר את הפתוח). top-bar UI "SHADOW 0t $0" (גם הוא 0). ⇒ מוני-היום לא נספרים גם עם עסקה-חיה. | 🟡 שוחזר |
| **I-24** S5/TPO + dead-streams | tick_reversal_15+tpo+footprint כולם present=true/**critical:false** (`S3_MUTE`/S5) ⇒ **לא חוסמים**; `bridge_streams_fresh ✓`. verdict DEGRADED נובע מ-day_type(UNKNOWN)+trend(GRAY), לא מ-streams. תואם המלצת-SoT. | 🟡 |

### מקור-אמת — דורש הצלבת Sierra (ל-CC, לא כאן)
- **I-15/C-1:** engine cci_14=+18.62/BLUE מול board GRAY — להצליב מול Sierra CCI-14/TCCI גולמי ב-`~/SierraChart_Data/v9_export/`. ב-near-zero (±18) להכריע מי מסווג נכון.
- **I-22:** נוסחת `pnl_r` — להצליב entry/stop_initial/exit מול חישוב risk_$ (CC, `DESIGNS_2026-06-08.md`).
- **I-11:** footprint file present אך 0 ברים — נתיב ingest file→bridge→buffer.

**NOT-DONE:** day_type-instance (פיצול/session_min/opening_type) לא נבדק לעומק — pre-IB (stage A3), מוקדם; נטר post-IB ~09:30. atr_daily/Y-IB `dll_missing` (Dashboard) — חשוד-שורש ל-opening_type/IB — ל-CC. FHB-state עדיין לא נחשף ב-endpoint (לא ניתן לאמת "EARLY בבר 4" של I-4).

---

## [2026-06-09 09:44 CT] Snapshot עמוק #3 (~74דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**מקרא:** RTH 08:30–15:00 CT · all 8 endpoints ענו <90ms (woodies 19 · footprint 39 · five_min 4 · stats 46 · trades 16 · gateway 23 · day_type 26 · **pattern-status 87ms** I-19 נקי) · ערוץ 5דק'/study **חי** (woodies_5min+bars_5min FRESH, cci_14 נע -89.84→-89.32, S2 buffer 94 / S4 buffer 50).
**צילומים (inline session, לא נשמרו לדיסק — disk-persist לא נתמך):** Dashboard (עם עסקת id=20 חיה)=`ss_8638wtd67` · Build-Status decision-tree=`ss_87449qch3`.
**שינוי-מצב מ-#2 (09:13):** IB הושלמה ⇒ day_type **סוּוַּג Trend_Normal** (היה UNKNOWN/A3), trend **RED יציב** (היה BLUE/GRAY flicker near-zero), 6/10 S2 **armed** (היו כל 10 חסומות day_type_gate). verdict **READY**. **I-15/C-1 לא משחזר** ברמת engine↔board (שניהם RED) — נותר רק skew UI↔engine.

### תבניות ירי — 5 השאלות

| מערכת/תבנית | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|---|---|---|---|---|---|
| **S2 · 6 מומנטום+flags** (REACTIVE L/S, INITIATIVE L/S, BULL_FLAG, BEAR_FLAG) | ✅ ערוץ חי buffer=94, mode=DAY_TYPE_MODE, opening_type=OPEN_DRIVE | ✅ ערכים שפויים, lag~real, cci-history מספקת | כולן **armed**, חוסמות רק על detection אמיתי (b3_buyers/b1_buyers/b1_expansion/pole_found/flag_length) | תקין — אין setup בבר זה (patterns_detected=0/setups=0) | — (FHB-state עדיין לא נחשף ב-endpoint) |
| **S2 · 4 day-patterns** (INV_HNS, HNS_TOP, DBL_BOTTOM_EE, DBL_TOP_AA) | ✅ | ✅ | `day_type_gate.auth_table_cell` + detection (swing_lows/highs, neckline) | **מוצדק** — auth-table×Trend_Normal חוסם day-patterns לגיטימית | — |
| **S3 · ABSORPTION/STACKED_IMB/SWEEP_RETURN/EXHAUSTION** | ❌ `bars_processed_today=0`/buffer=0/cumulative_delta=0/flow null | ❌ 0 ברים ב-74דק' RTH = לא-הגיוני | כל 4 "data.buffer_size + data.bars_today" (0, need ≥5) | טכנית כן (אין נתון); השורש=**I-11 ingest-break** | נתיב file→bridge→buffer של footprint |
| **S4 · HTLB** | ✅ **ירה ב-08:50 CT** (id=20), status=`fired` ב-board | ✅ entry 7489.25/stop 7491.75 שפוי | — (נורתה) | — | — |
| **S4 · HFE** (active_patterns) | ✅ HFE **LONG** conf 0.6, group REVERSAL, entry 7428.5/stop 7425.25/target 7429.5 | ⚠️ entry/stop שפוי אך R:R~0.31 (3.25pt stop / 1pt T1) | **A7 FAIL** "missing fire_setup for routable pattern" (A1–A6 PASS: A1 trend=RED, A2 11 studies, A3 patterns=[HFE], A4 advisory-degraded, A5 **sizing=half**, A6 STRATEGIC) | תקין — A7 דורש fire_setup; אין setup-בר זה. **A5 לא reject** (≠I-13) | — (A4 degraded: tpo/veto/killzone/layer0 missing — advisory, לא חוסם) |
| **S4 · ZLR/TLB/TT/GB100/Vegas/Ghost/FaMir** (יתר 7) | ✅ כולן **armed** (trend RED, A1 PASS — אין GRAY veto) | ✅ | `detection.pattern_specific` + `targets_stop.r_t1_gate` + `targets_stop.stop_price` (לא נדרך setup בבר) | תקין-detection; **שער ה-r_t1_gate/stop_price** = אזור I-13 (כיול stop/target table) | אין ZLR/setup טרי ⇒ אין counterfactual |

### חשודים פתוחים — בדיקה עמוקה @09:44 CT

| # | ממצא | סטטוס |
|---|------|-------|
| **I-1** day_type | **שיפור:** IB הושלמה ⇒ state=`B2/Trend_Normal/conf 0.38/lock PENDING`, **עקבי על 3 משטחים** (state-endpoint + readiness `s1_day_type_classified ✓ Trend_Normal` + S2 day_type_gate). **אין פיצול-3-כיווני.** day_type **לא חוסם** את 6 תבניות-המומנטום (armed). residual נמשך: `opening_type=UNKNOWN` (מול five_min `OPEN_DRIVE`) + `session_min=0` + `vote_history=[]` ב-74דק' לתוך RTH (instance לא-עוקב-סשן). Dashboard `Y IB dll_missing` = חשוד-שורש ל-opening_type/IB. | 🟡 |
| **I-3** ZLR | trend RED, ZLR armed אך active_patterns=[HFE] בלבד (A3 no ZLR this bar). אין setup/counterfactual. | 🔬 ללא שינוי |
| **I-4** S2 דריכה | ערוץ חי buffer=94, 6/10 armed, detection רץ (patterns_detected=0). דריכה תקינה. FHB לא נחשף. | 🔬 |
| **I-11** S3 footprint 0 ברים | **אישור #28 — עצמאות מאוששת שוב:** gate `footprint`=`[disabled][FRESH] 0s ago · 2026-06-09 17:39:23` (נכתב עכשיו) בעוד `bars_processed_today=0`/buffer 0/cumulative_delta 0/flow null. ערוץ 5דק'/woodies **חי** (I-21 פתור) ⇒ file→bridge→buffer שבור, **עצמאי מ-I-21**. מושתק `critical:false (S3_MUTE)` ⇒ לא חוסם לוח. | 🔴 (מושתק) |
| **I-15** C-1 trend conflict | **לא משחזר ברמת engine↔board:** engine trend_state=**RED** (cci_14=-89.84, A1 PASS, HFE armed) + readiness `s4_trend_not_stuck_gray ✓ RED` + pattern-status כל 9 woodies armed "trend RED" — **מסכימים, אין GRAY veto.** cci_14 **נע** (-89.84→-89.32, לא קפוא). נותר **skew UI↔engine:** פאנל Woodies-CCI מציג ≈`-71.2/-79.7` מול endpoint `-89.84` (~10–18pt). הצלבת Sierra CCI-14/TCCI חובה. | 🔬 |
| **I-16** choppiness_ok | **לא משחזר** — 6/10 S2 armed, **אין** "Missing: data.choppiness_ok"; gateway chop_state=FOUND (מחווט). מחזק I-17 (תנודתיות-גבול-בר). | 🔬 לא משחזר |
| **I-17** restart/buffer volatility | five_min buffer=94 (≠77@09:13), 6/10 armed, choppiness_ok present ⇒ תומך בתנודתיות-גבול-בר. | 🔬 |
| **I-18** TZ-mix freshness | **נמשך + future-date חזר:** gate `woodies_5min` value=`[FRESH] 0s ago · 2026-06-10 22:40:00` (**עתיד**, IL-local מסומן `+00:00`, lag_s=null); `bars_5min`=`2026-06-09 17:35:00` IL; `footprint`=`2026-06-09 17:39:23` IL. לעומתם cumulative_delta/volume_profile/imbalance ב-**UTC תקין** (`14:35`/`14:39`, lag 3-266s אמיתי). הלוח מציג `Day Type ? stale` + `Footprint ? stale` = artifact-TZ. מפר Rule 4. ⚠️ ה-future-date 06-10 ב-woodies_5min ts = אנומליה-נוספת לבדיקה (יכול להזין את skew ה-CCI ב-I-15). | 🟡 נמשך |
| **I-19** pattern-status hang | חזר ב-**87ms** (200). נקי. | 🔬 לא משחזר |
| **I-20** lag שלילי fresh=true | bridge `data_freshness.lag_seconds=-115233 (~-32h)/fresh=true/threshold=90` — predicate לא אוכף סף על lag שלילי. readiness משתמש ב-global_gates (חיוביים-אמיתיים) → READY נכון. | 🟡 נמשך |
| **I-21** stall 5דק' | **לא משחזר** — woodies_5min/bars_5min FRESH 0s, cci_14 נע, buffer S2=94/S4=50, S2 lag אמיתי. אין freeze. | 🟡 |
| **I-22** pnl_r מנופח | **🆕🔴 שוחזר חזותית על fire בן-יום (id=20):** HTLB SHORT entry 7489.25 / stop_init 7491.75 ⇒ risk=2.5pt×$5/חוזה=**$12.50**. UI right-panel: C1 `7485.75 HIT TARGET $18 = 14.0R` (אמיתי 18/12.5≈**+1.4R**, ×10); C2 `7482.25 HIT TARGET $35 = 28.0R` (אמיתי +2.8R, ×10); `Stop 7489.00 | 2/3 hit | $53 (42.0R)` (אמיתי ≈+4.2R, ×10). endpoint id=20 `pnl_usd=52.5 / pnl_r=21`. ⇒ R=`pnl_usd ÷ ~$1.25 (ערך-טיק)` ולא `÷ risk_$` — אינפלציה ~×10 **מאומתת חזותית על עסקה חיה** (שנייה לאישור ה-EOD מ-06-08). חוסם EOD-counterfactual עד תיקון. | 🔴 נמשך |
| **I-23** gateway counters | **🆕 שוחזר עם עסקה בת-יום:** id=20 ירה היום (08:50 CT) ו-C3 OPEN, אך gateway `trades_today=0`/`daily_pnl=0` (שגוי, אמור ≥1) ו-bridge `fired_today_count=0`/`last_fire_ts=null`. `shadow_active_count=1` (נכון — סופר את הפתוח). top-bar UI "SHADOW: 0t $0". ⇒ מוני-היום ו-fired_today_count לא נספרים גם עם עסקה-חיה; רק shadow_active_count נכון. | 🟡 שוחזר |
| **I-24** S5/TPO + dead-streams | `tick_reversal_15` (DEAD מ-2026-06-05 15:51) + `tpo` (DEAD 2023-11-25) + `footprint` כולם `critical:false` (`disabled S3_MUTE/S5`) ⇒ **לא חוסמים**; `bridge_streams_fresh ✓`. verdict READY. תואם המלצת-SoT. CC: לאשר כוונה + מתי בוצע. | 🟡 |

### מקור-אמת — דורש הצלבת Sierra (ל-CC, לא כאן)
- **I-15/I-18:** engine cci_14=-89.84 מול UI-panel ≈-71/-79 (~10-18pt skew) **וגם** gate `woodies_5min` ts עתיד-מתוארך (2026-06-10 22:40, TZ-mix) — להצליב CCI-14/TCCI גולמי + bar-ts מול `~/SierraChart_Data/v9_export/woodies_5min`. ה-future-ts יכול להיות מקור ה-skew.
- **I-22:** נוסחת `pnl_r` — להצליב entry/stop_initial/exit-fills של id=20 מול חישוב risk_$ פר-חוזה (CC, `DESIGNS_2026-06-08.md`).
- **I-11:** footprint file present (mtime נוכחי) אך 0 ברים — נתיב ingest file→bridge→buffer.
- **I-1:** `Y IB dll_missing` (Dashboard) — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-`opening_type=UNKNOWN`/`session_min=0`.

**NOT-DONE:** (1) day_type-instance residual (opening_type=UNKNOWN, session_min=0, vote_history=[] למרות day_type מסווג) — נדרש אבחון feed-instance/wrapper, ל-CC (פרומפט `CC_PROMPT_S1_DAYTYPE_RECLASS_2026-06-08.md`). (2) FHB-state לא נחשף ב-`five_min` endpoint — לא ניתן לאמת "EARLY בבר 4" (I-4). (3) ZLR setup טרי לא נצפה ⇒ אין counterfactual ל-I-3. (4) future-date ts ב-woodies_5min gate — אנומליה חדשה שלא אופיינה.

---

## [2026-06-09 10:08 CT] Snapshot עמוק #4 — סטטוס חשודים (Cowork, ~98דק' לתוך RTH, IB הושלמה)

ריצה רביעית בתוך RTH (10:08 CT, ~98דק'). כל 8 endpoints נענו: woodies 44ms · footprint 7ms · five_min 43ms · five_min/stats 7ms · trades 44ms · gateway 6ms · day_type 40ms · **pattern-status 80ms** (I-19 נקי). verdict **READY**, day_type **Trend_Normal** (B2/0.38), trend **RED**, price 7401.25. **צילומים (inline session, disk-persist לא נתמך):** Dashboard (עם עסקת id=20 חיה + פאנל Woodies-CCI)=`ss_07409ysbk` · Build-Status decision-tree (verdict READY, S2 armed, S4 ×1)=`ss_3877482l8`.

**שינוי מ-#3 (09:44):** trend נשאר RED (engine↔board מסכימים — I-15 לא משחזר ברמת engine↔board), אך **skew ה-UI↔engine החריף**: פאנל-CCI כעת מציג **חיובי** (+43.77) מול engine cci_14=**-84.7** (פער-סימן, לא רק גודל). buffer 94→109. S2 6/10 armed (ללא שינוי). I-22 שוחזר שוב חזותית.

### תבניות ירי — 5 השאלות

| מערכת/תבנית | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|---|---|---|---|---|---|
| **S2 · 6 מומנטום+flags** (REACTIVE L/S, INITIATIVE L/S, BULL_FLAG, BEAR_FLAG) | ✅ ערוץ חי buffer=109, mode=DAY_TYPE_MODE, opening_type=OPEN_DRIVE, last=REACTIVE_LONG conf 75 | ✅ ערכים שפויים (notes: "4-bar pattern, COT=-27227 vs AMT=-6264, location=far"), lag~229s real | כולן **armed**, חוסמות רק על detection אמיתי (b1_sellers / b4_confirm / b1_expansion / pole_found) | תקין — אין setup בבר זה (patterns_detected=0/setups=0) | — (FHB-state עדיין לא נחשף ב-endpoint) |
| **S2 · 4 day-patterns** (INV_HNS, HNS_TOP, DBL_BOTTOM_EE, DBL_TOP_AA) | ✅ | ✅ | `day_type_gate.auth_table_cell` + detection (swing_lows/highs, eve_variant) | **מוצדק** — auth-table×Trend_Normal חוסם day-patterns לגיטימית | — |
| **S3 · ABSORPTION/STACKED_IMB/SWEEP_RETURN/EXHAUSTION** | ❌ `bars_processed_today=0`/buffer=0/cumulative_delta=0/flow null | ❌ 0 ברים ב-98דק' RTH = לא-הגיוני | כל 4 "data.buffer_size + data.bars_today" (0, need ≥5) | טכנית כן (אין נתון); השורש=**I-11 ingest-break** | נתיב file→bridge→buffer של footprint |
| **S4 · HTLB** | ✅ **ירה ב-08:50 CT** (id=20), status `fired` ב-board (C1+C2 HIT, C3 OPEN) | ✅ entry 7489.25/stop 7491.75 שפוי | — (נורתה) | — | — (pnl_r מנופח — I-22) |
| **S4 · HFE** (active_patterns) | ✅ HFE **LONG** conf 0.6, group REVERSAL, entry 7392.75/stop 7383.5/target [7393.75] | ⚠️ entry/stop שפוי אך R:R~**0.11** (9.25pt stop / 1pt T1) — גרוע מ-#3 | **A7 FAIL** "missing fire_setup for routable pattern" (A1–A6 PASS: A1 trend=RED, A2 11 studies, A3 patterns=[HFE], A4 advisory-degraded, A5 **sizing=half**, A6 STRATEGIC/INITIATIVE) | תקין — A7/R:R≥1.0 חוסם setup עם T1 1pt. **A5 לא reject** (≠I-13) | — (A4 degraded: tpo/veto/killzone/layer0 missing — advisory בלבד) |
| **S4 · ZLR/TLB/TT/GB100/Vegas/Ghost/FaMir** (יתר 7) | ✅ כולן **armed** (trend RED, A1 PASS — אין GRAY veto) | ✅ | `detection.pattern_specific` + `targets_stop.r_t1_gate` + `targets_stop.stop_price` + `exit_rules.ready_to_route` | תקין-detection; שער ה-`r_t1_gate`/`stop_price` = אזור I-13 (כיול stop/target table) | אין ZLR/setup טרי ⇒ אין counterfactual |

### חשודים פתוחים — בדיקה עמוקה @10:08 CT

| # | ממצא | סטטוס |
|---|------|-------|
| **I-1** day_type | state=`B2/Trend_Normal/conf 0.38/lock PENDING/ib_width=EXTREME`, **עקבי על 3 משטחים** (state-endpoint + readiness `day_type=Trend_Normal` ✓ + S2 day_type_gate satisfied). **אין פיצול-3-כיווני**, **לא חוסם** את 6 תבניות-המומנטום. residual נמשך: `opening_type=UNKNOWN` (מול five_min `OPEN_DRIVE`) + `session_min=0` + `vote_history=[]` ב-98דק'. Dashboard `Y IB dll_missing` = חשוד-שורש. | 🟡 |
| **I-3** ZLR | trend RED, ZLR armed (A1 PASS) אך active_patterns=[HFE] בלבד (A3 no ZLR this bar). אין setup/counterfactual. | 🔬 ללא שינוי |
| **I-4** S2 דריכה | ערוץ חי buffer=109, 6/10 armed, detection רץ (patterns_detected=0/setups=0). דריכה תקינה. FHB לא נחשף. | 🔬 |
| **I-11** S3 footprint 0 ברים | **אישור #29 — עצמאות מאוששת:** gate `footprint`=`[disabled][FRESH] 0s ago · 2026-06-09 18:08:46` (נכתב עכשיו) בעוד `bars_processed_today=0`/buffer 0/cumulative_delta 0/flow null. ערוץ 5דק'/woodies **חי** (I-21 פתור) ⇒ file→bridge→buffer שבור, **עצמאי מ-I-21**. מושתק `critical:false (S3_MUTE)` ⇒ לא חוסם לוח. | 🔴 (מושתק) |
| **I-15** C-1 trend conflict | **לא משחזר ברמת engine↔board:** engine trend_state=**RED** (cci_14=-84.7, A1 PASS) + readiness `trend_state=RED` ✓ + pattern-status 9 woodies armed "trend RED" — **מסכימים, אין GRAY veto.** cci_14 נע (לא קפוא). אך **skew UI↔engine החריף לפער-סימן:** פאנל Woodies-CCI מציג **+43.77 / CCIDiff +30.24 / תחתית -7.4** מול endpoint cci_14=**-84.7** (~128pt + סימן הפוך). הצלבת Sierra CCI-14/TCCI חובה — ה-skew גדל מ-~10-18pt(#3) ל-pער-סימן. | 🔬 |
| **I-16** choppiness_ok | **לא משחזר** — 6/10 S2 armed, **אין** "Missing: data.choppiness_ok"; gateway chop_state=FOUND (UI "11 FOUND"). מחזק I-17. | 🔬 לא משחזר |
| **I-17** restart/buffer volatility | five_min buffer=109 (≠94@09:44), 6/10 armed, choppiness_ok present ⇒ תומך בתנודתיות-גבול-בר. | 🔬 |
| **I-18** TZ-mix freshness | **נמשך + future-date חזר (כמו 08:42):** gate `woodies_5min` value=`[FRESH] 0s ago · 2026-06-10 22:40:00` (**עתיד ~+30h**, marked `+00:00`, lag_s=null); `bars_5min`/`footprint`=IL-local (`17:35`/`18:08:46`). לעומתם cumulative_delta(`15:05`)/volume_profile(`15:08:45`)/imbalance(`14:50`) ב-**UTC תקין** (lag 3.9-1127s אמיתי). הלוח: `Day Type ? stale` + `Footprint ? stale` = artifact-TZ. **imbalance Present אך lag 1126.9s (~18.8דק') > סף = stale-but-Present.** מפר Rule 4. ⚠️ future-ts 06-10 ב-woodies_5min = חשוד-שורש ל-skew ה-CCI ב-I-15. | 🟡 נמשך |
| **I-19** pattern-status hang | חזר ב-**80ms** (200, len 87909). נקי. | 🔬 לא משחזר |
| **I-20** lag שלילי fresh=true | bridge `data_freshness.lag_seconds=-113471 (~-31.5h)/fresh=true/threshold=90` — predicate לא אוכף סף על lag שלילי. **בנוסף imbalance**: critical/fresh=true אך lag 1126.9s>סף (חיובי-מעל-סף לא נאכף). readiness משתמש ב-global_gates → READY נכון. | 🟡 נמשך |
| **I-21** stall 5דק' | **לא משחזר** — five_min/woodies `last_bar_ts=2026-06-09 18:05:00+03:00`, lag 228.9s, fresh=true; buffer S2=109/S4=50; cci_14 נע. אין freeze. | 🟡 |
| **I-22** pnl_r מנופח | **🔴 שוחזר חזותית שוב על fire בן-יום (id=20):** HTLB SHORT entry 7489.25/stop_init 7491.75 ⇒ risk=2.5pt×$5/חוזה=**$12.50**. UI right-panel: C1 `7485.75 HIT TARGET $18 = 14.0R` (אמיתי 18/12.5≈**+1.44R**, ×~10); C2 `7482.25 HIT TARGET $35 = 28.0R` (אמיתי +2.8R, ×10); `Stop 7489.00 | 2/3 hit | $53 (42.0R)` (אמיתי ≈+4.2R, ×10). endpoint id=20 `pnl_usd=52.5 / pnl_r=21`. ⇒ R=`pnl_usd ÷ ~$1.25 (ערך-טיק)` ולא `÷ risk_$`. אינפלציה ~×10 **מאומתת חזותית על עסקה חיה**. חוסם EOD-counterfactual עד תיקון (`DESIGNS_2026-06-08.md`). | 🔴 נמשך |
| **I-23** gateway counters | **שוחזר עם עסקה בת-יום:** id=20 ירה (08:50 CT) + C3 OPEN, אך gateway `trades_today=0`/`daily_pnl=0` ו-bridge `fired_today_count=0`/`last_fire_ts=null` (שגוי, אמור ≥1). `shadow_active_count=1` (נכון). top-bar UI "SHADOW: 0t $0". ⇒ מוני-היום+fired_today_count לא נספרים גם עם עסקה-חיה; רק shadow_active_count נכון. | 🟡 שוחזר |
| **I-24** S5/TPO + dead-streams | `tick_reversal_15` (DEAD 5717min מ-2026-06-05 15:51) + `tpo` (DEAD 2023-11-25) + `footprint` כולם `critical:false` (`disabled S3_MUTE/S5`) ⇒ **לא חוסמים**; `bridge_streams_fresh ✓`. verdict READY. תואם המלצת-SoT. CC: לאשר כוונה + מתי בוצע. | 🟡 |

### מקור-אמת — דורש הצלבת Sierra (ל-CC, לא כאן)
- **I-15/I-18 (מאוחד, מחמיר):** engine cci_14=**-84.7** (RED) מול UI-panel **+43.77** (פער-סימן ~128pt) **וגם** gate `woodies_5min` ts **עתיד-מתוארך** (2026-06-10 22:40, marked +00:00). שתי האנומליות יחד מצביעות על אותו ערוץ — להצליב CCI-14/TCCI גולמי + bar-ts מול `~/SierraChart_Data/v9_export/woodies_5min`. ה-future-ts הוא חשוד-שורש לפער-הסימן ב-CCI.
- **I-22:** נוסחת `pnl_r` של id=20 — להצליב entry/stop_initial/exit-fills מול risk_$ פר-חוזה.
- **I-11:** footprint file present (mtime נוכחי) אך 0 ברים — נתיב ingest file→bridge→buffer.
- **I-1:** `Y IB dll_missing` — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-`opening_type=UNKNOWN`/`session_min=0`.

**NOT-DONE:** (1) day_type-instance residual (opening_type=UNKNOWN, session_min=0, vote_history=[] למרות day_type מסווג) — אבחון feed-instance/wrapper, ל-CC. (2) FHB-state לא נחשף ב-`five_min` endpoint (I-4). (3) ZLR setup טרי לא נצפה ⇒ אין counterfactual ל-I-3. (4) future-date ts ב-woodies_5min gate **שוחזר** (כמו 08:42) — חשוד כעת למקור skew ה-CCI ב-I-15; טרם אופיין שורשית.

## [2026-06-09 10:43 CT] Snapshot עמוק #5 — Cowork (~133דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**מקור:** API חי דרך Chrome (`http://localhost:8000`). כל ה-endpoints חזרו `200`
(כולל `/build/pattern-status` — **I-19 לא משחזר**). צילומים (Chrome, inline; `save_to_disk`
לא נתמך בסשן זה): Dashboard=`ss_42011my9p` · **Build Status table=`ss_2433xxi3w`** (verdict
READY, day=Trend_Normal, S2 armed 10, S4 ×1, heartbeat <1s, Day Type/Footprint "? stale" אדום).

### ערכים גולמיים (raw)
- **day_type/state:** `stage=B2 · day_type=Variation · conf=0.38 · lock=PENDING · opening_type=OPEN_DRIVE · ib_width=WIDE · session_min=0 · vote_history=[]`
- **five_min/current:** `running · DAY_TYPE_MODE · buffer=5 · opening_type=OPEN_DRIVE · last_pattern=null`
- **five_min/stats:** `patterns_detected=0 · setups_published=0`
- **woodies/current:** `trend_state=RED · cci_14=-113.38 (snap a: -143.07) · tcci=-51.99 · ema_34=7406.72 · lsma=7335.68 · czi=-281 · signal=NEUTRAL · active_patterns=[] · NO_SETUP` · dtree: `A1 SKIP(no patterns) · A2 PASS(11 studies) · A3 SKIP(no patterns this bar) · A4 SKIP · A5 PASS(advisory:calculate_size=reject) · A6 SKIP · A7 SKIP`
- **footprint/current:** `bars_processed_today=0 · buffer=0 · cumulative_delta=0 · aggressive_flow/delta/dominance/amt=null`
- **gateway/status:** `trades_today=0 · shadow_active_count=0 · daily_pnl=0 · demo_enabled=[2,4] · live_enabled=[] · chop_state=FOUND · cooldown/cluster/ssv=inactive`
- **trades/recent (4):** רק `id=20` מהיום (06-09): `sys4 HTLB SHORT · entry 7489.25 · stop_init 7491.75 · exit 7383.25 · TIME_STOP · pnl_usd 582.5 · pnl_r 233 · WIN`. השאר (id=13/12/10) מ-06-05/06-08.
- **pattern-status readiness:** `verdict=READY · bridge_streams_fresh=PASS(block) · s1_day_type_classified=PASS detail="Trend_Normal"(degrade) · s4_trend_not_stuck_gray=PASS(RED) · in_rth=PASS`
- **global_gates:** `woodies_5min [FRESH 0s] ts=2026-06-10 22:40:00` (**ts עתידי!**) · `footprint [disabled S3_MUTE][FRESH] 18:40:10 crit=false` · `cumulative_delta [FRESH] 15:40:00Z` · `volume_profile [FRESH] 15:40:10Z` · `tick_reversal_15 [disabled][DEAD 5748min] 2026-06-05 crit=false` · `imbalance [FRESH] ts=15:25:02Z (~15דק')` · `tpo [disabled][DEAD] 2023-11-25 crit=false`
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-111587 (~-31h) · fresh=true`

### טבלת 5-השאלות

| סעיף | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|------|-------------|------------|------------|----------------|------------|
| **S2 כל 10 התבניות** | כן — 10/10 **armed**, ערוץ חי (lag 12.6s, buffer 5) | כן — blockers=`detection.*` בלבד (אין setup בבר), אין "Missing: choppiness_ok" | לא נחסם ע"י gate — פשוט אין תבנית-ירה בבר | לא — דריכה תקינה | FHB-state לא נחשף ב-endpoint (I-4) |
| **S4 (Woodies) 7 תבניות** | כן — 7/7 armed, fired_today=**2** (last 13:50Z=08:50 CT) | כן — trend RED, CCI סביר, A1–A7 עקבי | `detection.pattern_specific` + `targets_stop.*` (אין setup בבר) | לא | — (S4 בריא; ירה היום) |
| **S3 (Footprint) 4 תבניות** | **לא** — 4/4 `blocked`, buffer=0/bars_today=0/flow=null | לא-הגיוני — קובץ נכתב עכשיו (gate FRESH 18:40:10) אך 0 ברים | `data.buffer_size`+`data.bars_today` (ingest שבור) | מוצדק כל עוד אין ברים, אבל השורש=שבר-ingest | I-11: נתיב file→bridge→buffer (כעת מושתק S3_MUTE) |
| **day_type/S1** | כן — Variation 0.38/B2, opening_type=**OPEN_DRIVE** (לא UNKNOWN!) | חלקית — `session_min=0`+`vote_history=[]` ב-133דק' לא-הגיוני | לא חוסם S2 (S2 10/10 armed) | — | I-1: session_min/vote feed-instance מת; **פיצול Variation(state/Dashboard) ↔ Trend_Normal(readiness/Build-header)** |
| **Killzone (gate)** | כן — `✗ לא מחובר` ב-Build | סביר (advisory) | KZ לא מאשר | לא חוסם ירי (S4 ירה) | — |

### עדכון חשודים (🔬→ממצא / נמשך)
- **I-1 🔴→נמשך:** opening_type **השתפר** ל-OPEN_DRIVE (עקבי state↔five_min — הפער-instance הזה **נסגר** הסנאפ-שוט). נותר: (a) **פיצול 2-כיווני** day_type — `Variation 0.38`(state+Dashboard+S2 gate) מול `Trend_Normal`(readiness+Build-header); (b) `session_min=0`+`vote_history=[]` ב-133דק'. **לא חוסם S2** (10/10 armed). דורש אבחון feed-instance — CC.
- **I-11 🔴→נמשך (אישור #26):** קובץ footprint נכתב **עכשיו** (gate `[FRESH] 18:40:10`) אך `bars_processed_today=0`/buffer=0/flow=null. עצמאי מ-I-21 (5דק' חי, lag 12.6s). מושתק (`S3_MUTE`, crit=false) — לא-נפתר. file→bridge→buffer — CC.
- **I-3 🔬→נמשך:** ZLR **armed** (trend RED), `active_patterns=[]` (A3 no pattern this bar). אין setup-ZLR טרי ⇒ אין counterfactual.
- **I-4 🔬→תקין:** S2 דורך 10/10 על ערוץ חי. דריכה תקינה. FHB-state עדיין לא נחשף ב-endpoint.
- **I-5 (B-11) 🔴→לא משחזר:** `bridge_streams_fresh=PASS`, board READY. אין באנר OFFLINE שקרי. bridge_inspector לא מקריס.
- **I-16 🔴→לא משחזר:** אין `Missing: data.choppiness_ok` באף תבנית-S2. (chop gate OFF per CLAUDE.md; `chop_state=FOUND` בכל מקרה ≠SEARCHING.)
- **I-18 🟡→ממצא חד (החמרה):** **`woodies_5min` gate נושא ts עתידי `2026-06-10 22:40:00`** בעוד `cumulative_delta/volume_profile` נכונים ב-UTC (15:40Z). בנוסף `imbalance` מתויג `[FRESH]` אך ts=15:25:02Z (~15דק' ישן). ⇒ אי-עקביות TZ/תאריך פעילה בין הזרמים. **פער backend↔Sierra ts = ממצא** — להצליב מול `v9_export` (woodies_5min) — CC.
- **I-19 🔴→לא משחזר:** `/build/pattern-status` החזיר 200 מיידית (לא נתקע).
- **I-20 🟡→נמשך:** bridge aggregate `lag_seconds=-111587` (~−31h) עם `fresh=true` ו-`last_bar_ts=null`. lag שלילי על aggregate נמשך (קשור ל-ts-העתידי של woodies_5min, I-18).
- **I-21 🔴→לא משחזר:** ערוץ 5דק' **חי** (woodies+five_min lag 12.6s, S4 ירה היום). gate woodies_5min crit ו-present.
- **I-22 🔴→ממצא חוזר:** `pnl_r` שבור — id=20 SHORT entry 7489.25/stop_init 7491.75 (risk 2.5pt) exit 7383.25 = ~+106pt ⇒ R-אמיתי≈**42R**, אך `pnl_r=233` (~5.5× ניפוח). השאר אבסורדי יותר: id=13 תזוזה +0.25pt → `pnl_r=26.75`; id=12 +0.25pt → `pnl_r=16`; id=10 +0.25pt → `pnl_r=92`. הנוסחה לא יחסית-ל-risk. **מקלקל ΣR/win-rate** — CC.
- **I-23 🟡→ממצא חוזר:** `gateway.trades_today=0/shadow_active_count=0/daily_pnl=0` בעוד `trades/recent` מראה **id=20 מהיום** (ועוד 3 shadow) ⇒ counters לא סופרים shadow fires. WR-100% בכותרת מ-trades, לא מ-gateway.
- **I-24 🟡→נמשך (מושתק):** `tpo` gate **DEAD מ-2023-11-25** אך `disabled (S3_MUTE/S5)` crit=false ⇒ **לא נספר ב-readiness** (board READY). S5/TPO מת אך מנוטרל מה-gate הקריטי.

### מקור-אמת — להצלבת CC מול Sierra v9_export (לא כאן)
1. **woodies_5min ts עתידי** (`2026-06-10 22:40`) — להצליב מול `~/SierraChart_Data/v9_export/` (mtime+bar ts). פער backend↔Sierra. (I-18)
2. **CCI-14/TCCI** של S4 (cci_14=-113/-143) — להצליב מול study fields גולמיים. (I-3/I-15)
3. **footprint export** — הקובץ נכתב (mtime עכשיו) אך 0 ברים ב-buffer — file→bridge-parse. (I-11)
4. **pnl_r** id=20 — להצליב entry/stop/exit-fills מול risk_$ פר-חוזה. (I-22)
5. **`Y IB dll_missing`** (header) — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-`session_min=0`/פיצול day_type. (I-1)

**NOT-DONE:** (1) פיצול day_type Variation↔Trend_Normal + session_min=0/vote_history=[] — אבחון feed-instance, CC. (2) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (3) FHB-state לא נחשף (I-4). (4) אין counterfactual ל-ZLR (I-3) — לא נצפה setup טרי. (5) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [2026-06-09 11:13 CT] Snapshot עמוק #6 — Cowork (~163דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**מקור:** API חי דרך Chrome (`http://localhost:8000`). כל ה-endpoints חזרו `200`
(`/build/pattern-status` ב-206ms — **I-19 לא משחזר**). צילומים (Chrome, inline; `save_to_disk`
לא נתמך בסשן זה): Dashboard=`ss_1944tmv0n` · **Build Status table=`ss_8495tn5t4`** (verdict
READY, day=Trend_Normal, ירו היום `S2 ×1 + S4 ×1`, heartbeat <1s, Day Type/Footprint "? stale" אדום,
Killzone `✗ לא מחווט`, Woodies CCI/Min-Patterns "warming 3m").

### 🆕 ממצא מוביל — **ZLR הגיע ל-A7 לראשונה + עסקת-S2 טרייה פתוחה**
1. **ZLR נדרך ועבר A1–A6, נחסם ב-A7.** `woodies/current` מחזיר `signal=ZLR · active_patterns=[ZLR
   SHORT conf 0.65 group=CONTINUATION]`, dtree: `A1 PASS · A2 PASS · A3 PASS(patterns=['ZLR']) ·
   A4 PASS(advisory, day_type=Variation 0.38) · A5 PASS(sizing=half) · A6 PASS · A7 **FAIL** "missing
   fire_setup for routable pattern"`. זו **הפעם הראשונה** ש-ZLR מגיע ל-A7 (בסנאפ-שוטים #1–#5 הוא היה
   armed עם `active_patterns=[]`). חוסם-ה-A7 ב-`build/pattern-status`: `targets_stop.r_t1_gate,
   targets_stop.stop_price, targets_stop.targets, exit_rules.ready_to_route`.
2. **עסקת-S2 טרייה פתוחה (id=22).** `BEAR_FLAG_SHORT` SHORT entry 7313.5 / stop_init 7349.75 (risk
   **36.25pt** — סטופ רחב) / exit=null / 0/3 hit / `pnl_usd=0`. נורתה ~11:00 CT. ב-Dashboard:
   `S2 BEAR_FLA @7313.50 · C1 7259.38 / C2 7205.25 / C3 OPEN · Stop 7349.75 0/3 hit $0 (0.0R)`.

### ערכים גולמיים (raw)
- **day_type/state:** `stage=B2 · day_type=Variation · conf=0.38 · lock=PENDING · opening_type=OPEN_DRIVE · ib_width=WIDE · behavior=DEVELOPING · session_min=0 · vote_history=[]`
- **five_min/current:** `running · DAY_TYPE_MODE · buffer=6 · opening_type=OPEN_DRIVE · last_pattern=null`
- **five_min/stats:** `patterns_detected=0 · setups_published=0`
- **woodies/current:** `trend_state=RED · cci_14=-107.88 (נע: -106.84→-107.88) · cci_6/tcci=-108.93 · ema_34=7385.77 · lsma=7307.5 · swi=-30.29 · czi=-328 · predictor_next_cci=-122.82 · signal=ZLR · direction=SHORT · strength=2 · buffer=50 · classification=TACTICAL` · `active_patterns=[ZLR SHORT conf 0.65 entry=7302 stop=7319.75 targets=[7301]]` · dtree: `A1 PASS · A2 PASS(11 studies) · A3 PASS(['ZLR']) · A4 PASS(advisory:day_type=Variation 0.38) · A5 PASS(sizing=half) · A6 PASS(code=TACTICAL spec=REACTIVE) · A7 FAIL(missing fire_setup)` · notes: `"ZLR SHORT size=half: CCI=-110.6, trend=RED, conf=0.65, group=CONTINUATION"`
- **footprint/current:** `bars_processed_today=0 · buffer=0 · cumulative_delta=0 · aggressive_flow/delta/dominance/amt=null`
- **gateway/status:** `trades_today=0 · shadow_active_count=0 · daily_pnl=0 · demo_enabled=[2,4] · live_enabled=[] · cooldown/cluster=inactive`
- **trades/recent (5):** **2 מהיום (06-09):** `id=22 sys2 BEAR_FLAG_SHORT SHORT · entry 7313.5 · stop_init 7349.75 · OPEN · 11:00 CT` · `id=20 sys4 SHORT · entry 7489.25 · stop_init 7491.75 · exit 7383.25 · TIME_STOP · pnl_usd 582.5 · pnl_r 233 · WIN · 08:50 CT`. השאר (id=13/12/10) מ-06-05.
- **pattern-status readiness:** `verdict=READY · bridge_streams_fresh=PASS · s1_day_type_classified=PASS detail="Trend_Normal" · s4_trend_not_stuck_gray=PASS(RED) · in_rth=PASS`. **S2 10/10 armed** (`BEAR_FLAG_SHORT=fired`, `DOUBLE_TOP_AA_SHORT=armed []` ללא blocker; השאר `detection.*`). **S3 4/4 blocked** (`data.buffer_size`+`data.bars_today`). **S4 7/7 armed** (`detection.pattern_specific`+`targets_stop.*`+`exit_rules.ready_to_route`).
- **global_gates:** `woodies_5min [FRESH 0s] ts=2026-06-10 22:40:00` (**ts עתידי!** lag_s=null) · `footprint [disabled S3_MUTE][FRESH] 2026-06-09 19:12:01 crit=false` · `cumulative_delta [FRESH] 16:10:00Z lag 122s crit` · `volume_profile [FRESH] 16:11:59Z lag 3.5s crit` · `tick_reversal_15 [disabled][DEAD 5780min] 2026-06-05 crit=false` · `imbalance [FRESH] 15:45:02Z lag 1620s (~27דק') > 90s req` · `tpo [disabled][DEAD] 2023-11-25 crit=false`
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-109699 (~-30h) · fresh=true · threshold=90`
- **Dashboard header:** `VAR 38% M · 7311.75 · 11 FOUND · POC 7435 / VAH 7457.25 / VAL 7390.25 · IB H7417/L7390.25 26.25pt WIDE · Y IB dll_missing · Today H7491/L7299.25 191.75pt · OPEN DRIVE / Variation · WR 100% · SHADOW 0t $0`

### טבלת 5-השאלות

| סעיף | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|------|-------------|------------|------------|----------------|------------|
| **S2 כל 10 התבניות** | כן — 10/10 **armed**, ערוץ חי (lag 45s, buffer 6) | כן — `BEAR_FLAG_SHORT=fired` (id=22 פתוח); `DOUBLE_TOP_AA_SHORT` armed ללא blocker; השאר `detection.*` | רובן ממתינות detection אמיתי בבר; אין "Missing: choppiness_ok" | לא — דריכה תקינה, **אחת אף נורתה היום** | FHB-state לא נחשף ב-endpoint (I-4) |
| **S4 · ZLR (headline)** | כן — `active_patterns=[ZLR conf 0.65]`, buffer 50, CCI נע | כן — trend RED, cci_14=-107.88, ZLR זוהה; **אבל target מנוון** (entry 7302 / stop 7319.75 = risk 17.75pt / target [7301] = 1pt ⇒ R:R≈0.06) | **A7 FAIL "missing fire_setup"** → `targets_stop.r_t1_gate / stop_price / targets` + `exit_rules.ready_to_route` | חסימת ה-R:R **מוצדקת** (R:R 0.06), אבל ה-target המנוון הוא **סימפטום** — אין טבלת stop/target אמיתית | **טבלת stop/target פר-תבנית×day-type** — בלעדיה אין T1/stop ⇒ `r_t1_gate` לעולם לא יעבור (I-3, חופף project stop/target table) |
| **S4 שאר 6 התבניות** | כן — 7/7 armed, fired_today=**1** (id=20, 08:50 CT) | כן — A1–A6 עקבי | `detection.pattern_specific` (אין דפוס בבר) + `targets_stop.*` | לא | אותה טבלת stop/target (כללי ל-S4) |
| **S3 (Footprint) 4 תבניות** | **לא** — 4/4 `blocked`, buffer=0/bars_today=0/flow=null | לא-הגיוני — קובץ נכתב **עכשיו** (gate FRESH 19:12 IL) אך 0 ברים | `data.buffer_size`+`data.bars_today` (ingest שבור) | מוצדק כל עוד אין ברים, אבל השורש=שבר-ingest | I-11: file→bridge→buffer (מושתק S3_MUTE) |
| **day_type / S1** | כן — Variation 0.38/B2, opening_type=OPEN_DRIVE | חלקית — `session_min=0`+`vote_history=[]` ב-163דק' לא-הגיוני | לא חוסם S2 (10/10 armed) ולא S4 (ירה) | — | I-1: session_min/vote feed-instance מת; **פיצול Variation(state/Dashboard/A4/S2-gate) ↔ Trend_Normal(readiness/Build-header)** |
| **Killzone (gate)** | כן — `✗ לא מחווט` ב-Build | סביר (advisory) | KZ לא מאשר | לא חוסם ירי (S2+S4 ירו) | — |

### עדכון חשודים (🔬→ממצא / נמשך)
- **I-3 🔬→ממצא מהותי:** ZLR **הגיע ל-A7 לראשונה** — `active_patterns=[ZLR conf 0.65]`, A1–A6 PASS, **A7 FAIL "missing fire_setup for routable pattern"**. ה-`build/pattern-status` חושף את החוסם המדויק: `targets_stop.r_t1_gate / stop_price / targets` + `exit_rules.ready_to_route` לא נבנים. ה-target המנוון (1pt מול stop 17.75pt) ⇒ R:R≈0.06, אז שער ה-R:R **צודק שחוסם**, אבל הוא **סימפטום של היעדר טבלת stop/target** — בלי T1/stop אמיתיים `fire_setup` לא נבנה ⇒ ZLR לעולם לא יורה. **זהו ה-reject_reason הקונקרטי ל-I-3.** counterfactual חסר-משמעות (target מנוון). CC: לחווט targets_stop/exit_rules ל-fire_setup + טבלת stop/target.
- **I-1 🟡→נמשך:** opening_type=OPEN_DRIVE עקבי (state↔five_min↔Dashboard). נותר **פיצול 2-כיווני** `Variation 0.38`(state+Dashboard+A4+S2-gate) ↔ `Trend_Normal`(readiness+Build-header) + `session_min=0`/`vote_history=[]` ב-163דק'. **לא חוסם S2/S4** (10/10 armed, S2+S4 ירו). feed-instance — CC.
- **I-11 🔴→נמשך (אישור #27):** קובץ footprint נכתב **עכשיו** (gate `[FRESH] 2026-06-09 19:12:01` IL) אך `bars_processed_today=0`/buffer=0/flow=null. עצמאי מ-I-21 (5דק' חי lag 45s). מושתק `S3_MUTE`/crit=false — לא-נפתר. file→bridge→buffer — CC.
- **I-2 🟡→תקין:** A5 PASS `sizing=half` advisory — לא חוסם (A7 הוא החוסם של ZLR, לא A5). תצוגה תקינה.
- **I-15 🔬→נמשך (פער-UI מצטמצם):** מנוע `trend_state=RED` (cci_14=-107.88, נע) + board `s4_trend_not_stuck_gray ✓` — מסכימים. פאנל Woodies-CCI ≈`-96.4/-106.9` מול endpoint `-107.88` (פער ~1–11pt, **הקטן ביותר עד כה**). הצלבת Sierra (WSI/CCI גולמי) חובה.
- **I-16 🔴→לא משחזר:** אין `Missing: data.choppiness_ok` באף תבנית-S2 (10/10 armed). מחזק I-17.
- **I-18 🟡→ממצא חד (נמשך):** `woodies_5min` gate נושא ts עתידי `2026-06-10 22:40:00` (IL-local מתויג `+00:00`, lag_s=null); `imbalance` מתויג `[FRESH]` אך lag 1620s (~27דק') > 90s req = stale-but-Present; cumulative_delta/volume_profile UTC תקין. מפר Rule 4. **פער backend↔Sierra ts = ממצא** — להצליב `v9_export` (woodies_5min) — CC.
- **I-19 🔴→לא משחזר:** `/build/pattern-status` חזר ב-206ms (200, len 86920). נקי.
- **I-20 🟡→נמשך:** bridge aggregate `lag_seconds=-109699` (~−30h) עם `fresh=true`/`last_bar_ts=null`/threshold=90 — predicate לא אוכף סף (קשור ל-ts-העתידי של woodies_5min, I-18). readiness משתמש ב-global_gates → READY נכון.
- **I-21 🟡→לא משחזר:** ערוץ 5דק' **חי** — five_min last_bar `19:10 IL` (=11:10 CT) lag 45s, cci_14 נע, S2+S4 ירו היום. tick_reversal_15 `disabled`/crit=false (לא חוסם).
- **I-22 🔴→ממצא חוזר (עסקה טרייה):** `pnl_r` שבור — id=20 SHORT entry 7489.25/stop_init 7491.75 (risk **2.5pt**) exit 7383.25 = **+106pt** ⇒ R-אמיתי≈**+42R**, אך `pnl_r=233` (~5.5× ניפוח); `pnl_usd=582.5`. **מקלקל ΣR/win-rate ה-counterfactual** — CC לתקן נוסחה (חלוקה ב-risk_$ פר-חוזה, לא בערך-טיק). id=22 פתוח (pnl_r=null עדיין).
- **I-23 🟡→ממצא חוזר:** `gateway.trades_today=0/shadow_active_count=0/daily_pnl=0` בעוד **2 עסקאות היום** (id=20 סגורה + id=22 פתוחה) ו-board "ירו היום S2×1 S4×1". counters לא סופרים shadow fires; `shadow_active_count=0` שגוי (id=22 פתוח). WR/Trades בכותרת מ-trades, לא מ-gateway.
- **I-24 🟡→נמשך (מושתק):** `tpo` DEAD מ-2023-11-25 + `tick_reversal_15` DEAD מ-06-05, שניהם `disabled (S3_MUTE/S5)`/crit=false ⇒ **לא נספרים ב-readiness** (board READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC מול Sierra v9_export (לא כאן)
1. **woodies_5min ts עתידי** (`2026-06-10 22:40`) — להצליב mtime+bar-ts מול `~/SierraChart_Data/v9_export/`. פער backend↔Sierra. (I-18)
2. **CCI-14/TCCI** של S4 (cci_14=-107.88, פאנל ≈-96.4/-106.9) — להצליב study fields גולמיים; לקבוע מי המקור-אמת לפער-UI. (I-3/I-15)
3. **ZLR targets/stop** (entry 7302 / stop 7319.75 / target 7301) — להצליב מול ספֵק-התבנית + טבלת stop/target; ה-target המנוון מקורו בבקנד או ב-Sierra? (I-3)
4. **footprint export** — הקובץ נכתב (mtime עכשיו) אך 0 ברים ב-buffer — file→bridge-parse. (I-11)
5. **pnl_r** id=20/id=22 — להצליב entry/stop/exit-fills מול risk_$ פר-חוזה. (I-22)
6. **`Y IB dll_missing`** (header) — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-`session_min=0`/פיצול day_type. (I-1)

**NOT-DONE:** (1) **counterfactual ל-ZLR לא בר-חישוב** — ה-target המנוון (1pt) הופך אותו לחסר-משמעות; דרושה טבלת stop/target אמיתית (I-3). (2) פיצול day_type Variation↔Trend_Normal + session_min=0/vote_history=[] — feed-instance, CC. (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) FHB-state לא נחשף (I-4). (5) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [11:40 CT · 2026-06-09] snapshot — בדיקה עמוקה (Cowork)

**זמן:** 11:40 CT (~190דק' לתוך RTH, Build-header "198m פתוח"). כל 8 ה-endpoints 200; `build/pattern-status` 200ms/len 87388 (נקי, I-19 לא משחזר). **verdict=READY** (bridge_streams_fresh ✓ · s1_day_type_classified ✓ Trend_Normal · s4_trend_not_stuck_gray ✓ RED · in_rth ✓). board "ירו היום S2×1 S4×1".
**צילומים:** Dashboard=`ss_68693hzb6` · Build-Status=`ss_7775rq86f` (decision-tree + DATA_FRESHNESS + S2/S3/S4 chains; root `:8000`=API `{"detail":"Not Found"}` ⇒ UI ב-`:3000`).

### טבלת 5-השאלות לכל סעיף

| סעיף | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|------|-------------|------------|------------|----------------|-------------|
| **S2 · 10 תבניות** | כן — **10/10 armed**, buffer=3, mode=DAY_TYPE, opening=OPEN_DRIVE, detected=0/setups=0 | כן — חוסמות רק על `detection.*` אמיתי (b3_buyers/b1_buyers/b1_expansion/swing_lows/swing_highs/eve_variant/pole_found) | detection-await (אין דפוס בבר) — **אין** 'Missing: choppiness_ok' ו**אין** day_type_gate block | מוצדק (אין setup בבר) | FHB-state לא נחשף ב-endpoint (I-4) |
| **S2 · REACTIVE (fired)** | כן — id=22 BEAR_FLAG_SHORT ירה היום ונסגר BE | כן — entry=exit=7313.5, $0/0R (stop 7349.75) | נסגר ב-breakeven (לא חסימה) | — | — |
| **S4 · ZLR (headline)** | כן — `active_patterns=[ZLR SHORT conf 0.65 group=CONTINUATION]`, buffer 50, CCI נע | **לא-הגיוני target** — entry 7269.25 / stop 7306.25 (**risk 37pt!**) / target [7268.25] (**1pt**) ⇒ R:R≈**0.027** (גרוע מ-0.06 ב-11:13) | A1–A6 **PASS** (A5 sizing=half), **A7 FAIL "missing fire_setup for routable pattern"** → `targets_stop.r_t1_gate + targets_stop.day_type_matrix + exit_rules.ready_to_route` | חסם R:R **מוצדק** (0.027), אך הוא **סימפטום** של היעדר טבלת stop/target — בלי T1/stop אמיתי `fire_setup` לא נבנה | **טבלת stop/target פר-תבנית×day-type** (I-3, חופף project stop/target table) |
| **S4 · שאר 6 תבניות** | כן — 7/7 armed, fired_today=**1** (id=20 HTLB) | כן — A1–A6 עקבי | `detection.pattern_specific` + `targets_stop.*` + `exit_rules.ready_to_route` | לא (אין דפוס) | אותה טבלת stop/target |
| **S3 · Footprint 4 תבניות** | **לא** — 4/4 `blocked`, bars_today=0/buffer=0/cumulative_delta=0/flow=null/NO_SETUP | לא-הגיוני — gate footprint `[disabled][FRESH] 0s · 19:38:27` (קובץ נכתב **עכשיו**) אך 0 ברים | `data.buffer_size` + `data.bars_today` (ingest שבור) | מוצדק כל עוד 0 ברים — אך השורש=שבר-ingest | I-11: file→bridge→buffer (מושתק S3_MUTE/crit=false) |
| **day_type / S1** | כן — state=Variation 0.38/B2/lock PENDING, opening=OPEN_DRIVE, ib_width WIDE | חלקית — `session_min=0`+`vote_history=[]` ב-~190דק' לא-הגיוני | לא חוסם — S2 10/10 armed + S4 ירה | — | I-1: session_min/vote feed-instance מת; **פיצול Variation(state+A4-touchpoint) ↔ Trend_Normal(readiness+Build-header+Dashboard-panel)** |
| **Bridge / streams** | כן — verdict READY | חלקית — `data_freshness.lag_seconds=-108028` (~-30h)+fresh=true; woodies_5min ts **עתידי** 06-10 | אין חסם (קריטיים: cumulative_delta/volume_profile/imbalance/woodies_5min/bars_5min) | — | I-18/I-20: TZ-mix + predicate לא אוכף סף |
| **Killzone (gate)** | כן — `✗ לא מחווט` ב-Build | סביר (advisory) | KZ לא מאשר | לא חוסם ירי | — |

### ערכים גולמיים (11:40 CT)
- **woodies:** cci_14=-125.13 · cci_6_tcci=-133.86 · ema_34=7357.89 · lsma=7274.47 · swi=3.06 · czi=-347 · trend_state=RED · predictor_next_cci=-165.64 · buffer=50 · classification=TACTICAL · signal=ZLR/SHORT/strength 2. active=[ZLR SHORT 0.65 CONTINUATION entry 7269.25 stop 7306.25 target 7268.25]. tree: A1 PASS(RED)·A2 PASS(11 studies)·A3 PASS(['ZLR'])·A4 PASS(advisory degraded: tpo/veto/killzone/layer0 missing; touchpoint day_type=Variation 0.38)·A5 PASS(sizing=half)·A6 PASS(code=TACTICAL/spec=REACTIVE)·**A7 FAIL(missing fire_setup)**.
- **five_min:** mode=DAY_TYPE_MODE · buffer=3 · opening_type=OPEN_DRIVE · patterns_detected=0 · setups_published=0.
- **footprint:** running+hydrated · bars_processed_today=0 · buffer=0 · cumulative_delta=0 · flow/delta/dominance/cot/amt=null · NO_SETUP.
- **day_type.state:** B2 · Variation · conf 0.38 · lock PENDING · opening_type=OPEN_DRIVE · ib_width WIDE · behavior DEVELOPING · range NORMAL · vote_history=[] · session_min=0.
- **gateway:** shadow_active_count=0 · trades_today=0 · daily_pnl=0 · demo_enabled=[2,4] · live_enabled=[] · chop_state=FOUND · cooldown/cluster/ssv כולם inactive.
- **trades (5):** id=22 S2 BEAR_FLAG_SHORT CLOSED entry 7313.5/exit 7313.5/$0/**0R** (היום) · id=20 S4 HTLB SHORT CLOSED entry 7489.25/stop 7491.75/exit 7383.25/$582.5/**233R** (היום) · id=13 S2 REACTIVE_SHORT $66.88/26.75R (שישי) · id=12 S4 HTLB $20/16R (שישי) · id=10 S2 BEAR_FLAG_SHORT $230/92R (שישי).
- **gates:** woodies_5min `[FRESH] 0s · 2026-06-10 22:40:00`(ts עתידי, lag_s=null, crit=true) · footprint `[disabled][FRESH] 0s · 2026-06-09 19:38:27`(crit=false) · tick_reversal_15 `[disabled][DEAD] 5808min · 2026-06-05 15:51`(crit=false) · imbalance `[FRESH]` אך **lag 868s (~14.5min) > 90s req**(crit=true, stale-but-Present) · tpo `[disabled][DEAD] · 2023-11-25`(crit=false) · cumulative_delta FRESH lag 271s<360s.
- **Dashboard:** price live 7255.50(0.7s) · header pill "Trend Normal · OPEN DRIVE" · day-panel "Trend Normal CLASSIFIED 38% · OPEN_DRIVE WIDE · IBH 7417/IBL 7390.75 26.3pt locked" · "**Y IB dll_missing**" · "11 FOUND" chop · WR 50% · SHADOW 0t $0 · Woodies-CCI panel CCI≈-162.61/CCIDiff -14.95.

### עדכון חשודים (🔬→ממצא / נמשך)
- **I-3 🔬→ממצא (החמרת-target):** ZLR שוב ב-A7 — A1–A6 PASS, **A7 FAIL "missing fire_setup"**, חוסם מדויק `targets_stop.r_t1_gate + day_type_matrix + exit_rules.ready_to_route`. ה-target המנוון **החמיר** (1pt מול stop 37pt ⇒ R:R 0.027, מול 0.06 ב-11:13). שער R:R צודק שחוסם אך זה **סימפטום** של היעדר טבלת stop/target. CC: לחווט targets_stop/exit_rules→fire_setup + טבלת stop/target.
- **I-1 🟡→נמשך:** opening_type=OPEN_DRIVE עקבי. **פיצול 2-כיווני** Variation 0.38(state+A4-touchpoint) ↔ Trend_Normal(readiness+Build-header+Dashboard-panel) — הפעם ה-Dashboard עבר לצד Trend_Normal, state-endpoint+A4 לבד Variation. `session_min=0`/`vote_history=[]` ב-~190דק'. **לא חוסם** (10/10 S2 armed, S2+S4 ירו). feed-instance — CC.
- **I-11 🔴→נמשך (אישור #28):** קובץ footprint נכתב **עכשיו** (gate `[FRESH] 0s · 2026-06-09 19:38:27` IL) אך bars_processed_today=0/buffer=0/flow=null. עצמאי מ-I-21 (5דק' חי). מושתק S3_MUTE/crit=false — לא-נפתר. file→bridge→buffer — CC.
- **I-2 🟡→תקין:** A5 PASS sizing=half advisory — לא חוסם (A7 הוא החוסם, לא A5).
- **I-4 🔬→תקין:** S2 דורך 10/10 armed על ערוץ חי (buffer 3); חוסמות רק detection.*. דריכה תקינה. FHB לא נחשף.
- **I-13 🔴→לא נצפה:** ZLR A5 sizing=half (לא reject); החסם A7 R:R. אין ממצא-sizing לכייל.
- **I-15 🔬→נמשך (פער-UI גדל מחדש):** מנוע trend_state=RED (cci_14=-125.13, נע) + board `s4_trend_not_stuck_gray ✓ RED` — מסכימים, אין קונפליקט. פאנל Woodies-CCI ≈`-162.61` מול endpoint `-125.13` (~37pt, גדל מ-~1–11pt ב-11:13). הצלבת Sierra חובה.
- **I-16 🔴→לא משחזר:** אין `Missing: data.choppiness_ok` (10/10 S2 armed, chop_state=FOUND). מחזק I-17.
- **I-17 🔬→נמשך:** five_min buffer=3 (≠נמוך-מאוד מול קודמים) — מרמז reset/early-bar; תומך בתנודתיות-גבול-בר.
- **I-18 🟡→ממצא חד (נמשך):** woodies_5min gate ts **עתידי** `2026-06-10 22:40:00` (IL-local מתויג +00:00, lag_s=null); imbalance `[FRESH]` אך lag 868s (~14.5min) > 90s = stale-but-Present; cumulative_delta/volume_profile UTC תקין. מפר Rule 4. **פער backend↔Sierra ts = ממצא** — להצליב v9_export — CC.
- **I-19 🔴→לא משחזר:** build/pattern-status 200ms (200). נקי.
- **I-20 🟡→נמשך:** bridge `data_freshness.lag_seconds=-108028/fresh=true/last_bar_ts=null/threshold=90` (~-30h, קשור ל-ts-העתידי I-18). predicate לא אוכף סף. readiness via gates → READY נכון.
- **I-21 🟡→לא משחזר:** ערוץ 5דק' חי — five_min last_bar ~19:10 IL lag~45s, cci נע, S2+S4 ירו. tick_reversal_15 disabled/crit=false (לא חוסם).
- **I-22 🔴→ממצא חוזר (עסקה טרייה):** pnl_r שבור — id=20 SHORT entry 7489.25/stop_init 7491.75 (risk **2.5pt**) exit 7383.25 (**+106pt**) ⇒ R-אמיתי≈**+42R**, מדווח `pnl_r=233` (~5.5× ניפוח); pnl_usd=582.5. id=22 נסגר BE ($0/0R, תקין). **חוסם ΣR/win-rate counterfactual.** נוסחה: חלוקה ב-risk_$ פר-חוזה, לא בערך-טיק — CC.
- **I-23 🟡→ממצא חוזר:** gateway `trades_today=0/shadow_active_count=0/daily_pnl=0` בעוד **2 עסקאות היום** (id=20+id=22, שתיהן סגורות) ו-board "S2×1 S4×1". מוני-היום לא סופרים shadow fires. (shadow_active_count=0 כעת תקין — שתיהן סגורות.)
- **I-24 🟡→נמשך (מושתק):** tpo DEAD מ-2023-11-25 + tick_reversal_15 DEAD מ-06-05, שניהם disabled(S3_MUTE/S5)/crit=false ⇒ לא נספרים ב-readiness (board READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC מול Sierra v9_export (לא כאן)
1. **woodies_5min ts עתידי** `2026-06-10 22:40` — להצליב mtime+bar-ts מול `~/SierraChart_Data/v9_export/`. פער backend↔Sierra = ממצא (I-18).
2. **CCI-14/TCCI** (endpoint cci_14=-125.13 מול פאנל ≈-162.61, ~37pt) — להצליב study fields גולמיים; מי המקור-אמת לפער-UI (I-3/I-15).
3. **ZLR targets/stop** (entry 7269.25 / stop 7306.25 / target 7268.25) — ה-target המנוון מקורו בבקנד או Sierra? להצליב ספֵק-תבנית + stop/target table (I-3).
4. **footprint export** — קובץ נכתב (mtime עכשיו) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
5. **pnl_r** id=20 — להצליב entry/stop/exit-fills מול risk_$ פר-חוזה (I-22).
6. **`Y IB dll_missing`** (header) — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-session_min=0/פיצול day_type (I-1).

**NOT-DONE:** (1) **counterfactual ל-ZLR לא בר-חישוב** — target מנוון (1pt) חסר-משמעות; דרושה טבלת stop/target (I-3). (2) פיצול day_type Variation↔Trend_Normal + session_min=0/vote_history=[] — feed-instance, CC. (3) future-date ts ב-woodies_5min gate לא אופיין שורשית (I-18). (4) FHB-state לא נחשף (I-4). (5) הצלבות-Sierra (1–6) הן ל-CC, לא כאן. (6) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [12:12 CT · 2026-06-09] snapshot — בדיקה עמוקה (Cowork)

**זמן:** 12:12 CT (~222דק' לתוך RTH, Build-header "168m לסגירה · פתוח RTH"). כל 7 ה-endpoints 200 (<60ms); `build/pattern-status` **72ms**/len 88581 (נקי, I-19 לא משחזר). **verdict=DEGRADED** (bridge_streams_fresh ✓ block · s1_day_type_classified ✓ Trend_Normal · **s4_trend_not_stuck_gray ✗ trend_state=GRAY** · in_rth ✓). board "ירו היום S2×1 S4×1". **שינוי-משטר מ-11:40:** trend התהפך RED→**GRAY** (cci_14 חצה לאזור-אפס, +60.22) ⇒ כל S4 חסום ב-A1-veto, ה-verdict ירד READY→DEGRADED.
**צילומים (inline, לא נשמרו לדיסק בסשן זה — save_to_disk ללא-אפקט):** Dashboard=`ss_1278zz6kk` · Build-Status=`ss_5207umknk` (decision-tree banner "מצב מוגבל — מגמה תקועה GRAY", chain `? Day Type × stale → S3 BLOCKED → ? Footprint × stale → ✓ Woodies CCI ✓ Min Patterns-5 · ✓ Bridge·Streams`, verdict DEGRADED, "S2×1 S4×1 ירו היום"; root `:8000`=API `{"detail":"Not Found"}` ⇒ UI ב-`:3000`).

### טבלת 5-השאלות לכל סעיף

| סעיף | 1. יש נתון? | 2. הגיוני? | 3. מה חסם? | 4. צריך לחסום? | 5. מה חסר? |
|------|-------------|------------|------------|----------------|-------------|
| **S2 · REACTIVE (L/S)** | כן — שניהם **armed**, buffer=18, mode=DAY_TYPE, opening=OPEN_DRIVE | כן — חוסמים רק על `detection.b1_sellers`(Long) / `detection.b2_volume_drop`(Short) אמיתי | detection-await (אין דפוס בבר) | מוצדק (אין setup) | FHB-state לא נחשף (I-4) |
| **S2 · INITIATIVE (L/S)** | כן — שניהם **armed** (auth FULL, אין SKIP×daytype) | כן — חוסמים על `detection.b1_expansion` | detection-await | מוצדק | שרשרת opening→entry (I-14) — ל-CC |
| **S2 · FLAGS** | כן — Bull Flag **armed** (`detection.pole_found`), **Bear Flag SHORT = fired** | כן — Bear Flag ירה היום (id=22, נסגר BE) | Bull: detection.pole_found; Bear: ירה ונסגר | מוצדק | — |
| **S2 · day-patterns (INV_HNS/HNS_TOP/DBL_BOT/DBL_TOP)** | חלקית — 4/4 **blocked** | כן — חסומות `day_type_gate.auth_table_cell` + detection.swing/neckline | Auth-Table × **Trend_Normal** (התא לא מאשר day-patterns) | **מוצדק** לפי האפיון (day-patterns מותנות-day_type) | — (אין 'Missing: choppiness_ok' — I-16 לא משחזר) |
| **S4 · ZLR** | כן — buffer 50, אך `active_patterns=[]`, signal=NEUTRAL | כן — trend_state=**GRAY** (cci_14=+60.22, אזור-אפס) ⇒ אין דפוס-ZLR | **`stage_a1.strategic_gate` (A1-veto GRAY)** — לפני A3-detection; +`targets_stop.*`/`exit_rules.ready_to_route` downstream | A1-veto **מוצדק** (GRAY=trend indeterminate, אין כיוון); ≠ ה-target המנוון של 11:40 (אז RED+armed) | טבלת stop/target נשארת חסרה כשיתהפך ל-RED (I-3) |
| **S4 · שאר 8 תבניות (TLB/TT/GB100/HFE/HTLB/FAMIR…)** | כן — buffer 50 | כן — A2 PASS 11 studies | כולן `stage_a1.strategic_gate` (A1-veto GRAY) ראשון, אז `targets_stop.*`+`exit_rules.ready_to_route` | A1-veto מוצדק (GRAY) | אותה טבלת stop/target (I-3/I-13) |
| **S3 · Footprint 4 תבניות** | **לא** — 4/4 `blocked`, bars_today=0/buffer=0/cumulative_delta=0/flow=null/NO_SETUP | לא-הגיוני — gate footprint `[disabled][FRESH] 0s · 2026-06-09 20:09:17`(נכתב **עכשיו**) אך 0 ברים | `data.buffer_size` + `data.bars_today` (ingest שבור) | מוצדק כל עוד 0 ברים — השורש=שבר-ingest, לא היעדר-יצוא | **I-11**: file→bridge→buffer (מושתק S3_MUTE/crit=false) |
| **day_type / S1** | כן — state=**Trend_Normal** B2/0.38/LOCKED_LOW_CONF, opening=OPEN_DRIVE, ib_width WIDE | חלקית — `session_min=0`+`vote_history=[]` ב-~222דק' לא-הגיוני | לא חוסם — readiness `s1_day_type_classified ✓ Trend_Normal`; S2 6 armed + ירה | — | I-1: session_min/vote feed-instance מת. **הפעם אין פיצול 3-כיווני** — state+readiness+Dashboard כולם Trend_Normal (≠11:40 שהיה פיצול) |
| **Bridge / streams** | כן — readiness bridge_streams_fresh ✓ (לא חוסם) | חלקית — `data_freshness.lag_seconds=-106238` (~-29.5h)+`fresh=true`; woodies_5min ts **עתידי** 06-10 22:40; imbalance stale-but-Present | אין חסם (footprint/tick_reversal_15/tpo כולם disabled crit=false) | — | I-18/I-20: TZ-mix + predicate לא אוכף סף |
| **Killzone (gate)** | כן — `✗ KZ לא מחווט` ב-Build | סביר (advisory) | KZ לא מאשר | לא חוסם ירי | — |

### ערכים גולמיים (12:12 CT)
- **woodies:** cci_14=**+60.22** · cci_6_tcci=+106.52 · ema_34=7334.65 · lsma=7259.81 · swi=168.61 · czi=-131.0 · trend_state=**GRAY** · predictor_next_cci=+81.76 · signal=NEUTRAL · direction=null · strength=0 · buffer=50 · classification=NO_SETUP · active_patterns=[]. tree: A1 SKIP(no patterns)·A2 PASS(11 studies)·A3 SKIP(no patterns this bar)·A4 SKIP(no setup needs touch-points)·A5 PASS(advisory:calculate_size=reject)·A6 SKIP(NO_SETUP)·A7 SKIP(no fire_setup). **בלוח Build כל 9 ה-S4 blocked ב-`stage_a1.strategic_gate` (A1-veto GRAY).**
- **five_min:** mode=DAY_TYPE_MODE · buffer=18 · opening_type=OPEN_DRIVE · patterns_detected=0 · setups_published=0. S2 patterns: Reactive L/S armed · Initiative L/S armed · Bull Flag armed · **Bear Flag fired** · 4 day-patterns blocked(auth_table_cell×Trend_Normal). fired_today=2.
- **footprint:** running+hydrated · bars_processed_today=0 · buffer=0 · cumulative_delta=0 · flow/delta/dominance/cot/amt=null · NO_SETUP. fired_today=0.
- **day_type.state:** B2 · **Trend_Normal** · conf 0.38 · lock LOCKED_LOW_CONF · opening_type=OPEN_DRIVE · ib_width WIDE · behavior DEVELOPING · range NORMAL · vote_history=[] · session_min=0.
- **gateway:** shadow_active_count=0 · trades_today=0 · daily_pnl=0 · demo_enabled=[2,4] · live_enabled=[] · chop_state=FOUND · cooldown/cluster/ssv inactive.
- **trades (5):** id=22 S2 SHORT CLOSED entry 7313.5/stop 7349.75/exit 7313.5/$0/**0R** (היום, BE) · id=20 S4 SHORT CLOSED entry 7489.25/stop 7491.75(risk 2.5pt)/exit 7383.25(+106pt)/$582.5/**233R** (היום — מנופח ~5.5×, R-אמיתי≈+42R) · id=13 S2 SHORT $66.88/26.75R (שישי) · id=12 S4 SHORT $20/16R (שישי) · id=10 S2 SHORT $230/92R (שישי).
- **gates:** woodies_5min `[FRESH] 0s · 2026-06-10 22:40:00`(ts **עתידי** ~+30h, freshness.ts מתויג +00:00, lag_s=null, crit=true) · footprint `[disabled][FRESH] 0s · 2026-06-09 20:09:17`(IL-local מתויג +00:00, crit=false) · cumulative_delta `[FRESH] · 2026-06-09T17:04:59`(UTC תקין, lag 262s<360) · volume_profile UTC `17:09:17` · **imbalance `[FRESH] 0s` אך freshness.ts=`16:25:03`/lag_s=2658s (~44min) > 90s req (crit=true) = stale-but-Present** · tick_reversal_15 `[disabled][DEAD] 5838min · 2026-06-05 15:51`(crit=false) · tpo `[disabled][DEAD] · 2023-11-25`(crit=false) · bars_5min `[FRESH] · 2026-06-09 20:05:00`(IL-local מתויג +00:00, lag_s=null, crit=true).
- **Dashboard:** price live 7302.50 · header pill "Trend Normal · OPEN DRIVE" · day-panel "Trend Normal CLASSIFIED 38% · Dir HIGH/Trade LOW · OPEN_DRIVE WIDE · IBH 7417/IBL 7390.75 26.3pt locked" · TODAY POC 7435/VAH 7472.5/VAL 7368 · YEST POC 7416.25 · "**Y IB dll_missing**" · TODAY RANGE 7491/7247 244pt · "11 FOUND" chop · WR 50% · SHADOW 0t $0 · Woodies-CCI panel CCI≈53.74/CCIDiff -10.42.

### עדכון חשודים (🔬→ממצא / נמשך)
- **I-1 🟡→נמשך (ללא פיצול הפעם):** state=Trend_Normal B2/0.38, opening=OPEN_DRIVE עקבי. **אין פיצול 3-כיווני** — state-endpoint + readiness `s1_day_type_classified ✓ Trend_Normal` + Dashboard-panel "Trend Normal" **כולם מסכימים** (≠11:40 שהיה Variation↔Trend_Normal). residual: `session_min=0`+`vote_history=[]` ב-~222דק'. **לא חוסם** S2 (6 armed + ירה). feed-instance — CC.
- **I-2 🟡→תקין:** A5 PASS advisory:calculate_size=reject — לא חוסם (NO_SETUP; A1-veto GRAY הוא החוסם של S4).
- **I-3 🔬→נמשך (GRAY, לא armed):** trend GRAY (cci_14=+60.22, אזור-אפס) ⇒ ZLR חסום `stage_a1.strategic_gate` (A1-veto) **לפני** A3-detection — **לא armed** הפעם (≠11:40 RED+armed+A7). אין setup-ZLR טרי ⇒ אין counterfactual. (כשיתהפך ל-RED, חוסם-ה-target המנוון/היעדר-טבלת-stop/target יחזור.)
- **I-4 🔬→תקין:** S2 דורך — 6/10 armed (REACTIVE/INITIATIVE/BULL_FLAG) + BEAR_FLAG fired, על ערוץ חי (buffer 18, detected=0/setups=0). 4 day-patterns חסומות לגיטימית auth×Trend_Normal. דריכה תקינה. FHB לא נחשף.
- **I-11 🔴→נמשך (אישור #29):** קובץ footprint נכתב **עכשיו** (gate `[disabled][FRESH] 0s · 2026-06-09 20:09:17`) אך bars_processed_today=0/buffer=0/cumulative_delta=0/flow=null, 4 תבניות `blocked [data.buffer_size, data.bars_today]`. ערוץ 5דק' חי (S2 buffer 18, S2/S4 ירו) ⇒ ingest-break **עצמאי מ-I-21**. מושתק S3_MUTE/crit=false — לא-נפתר. file→bridge→buffer — CC.
- **I-13 🔴→לא נצפה:** NO_SETUP ב-S4 (active_patterns=[]), A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing לכייל.
- **I-15 🔬→לא משחזר קונפליקט (פער-UI קטן):** engine cci_14=+60.22/**GRAY** + board `s4_trend_not_stuck_gray ✗ GRAY` — **מסכימים** (CCI באזור-אפס, GRAY אמיתי, לא תקלת-תצוגה). פאנל Woodies-CCI מציג CCI≈53.74/CCIDiff -10.42 מול endpoint +60.22 (~7pt, הפער הקטן ביותר היום). הצלבת Sierra חובה.
- **I-16 🔴→לא משחזר:** אין `Missing: data.choppiness_ok` באף תבנית-S2 (6/10 armed + BEAR_FLAG fired; gateway chop_state=FOUND, UI '11 FOUND'). מחזק I-17.
- **I-17 🔬→נמשך:** five_min buffer=18 (≠3@11:40). תומך בתנודתיות-גבול-בר/buffer.
- **I-18 🟡→ממצא חד (נמשך):** woodies_5min gate ts **עתידי** `2026-06-10 22:40:00` (IL-local מתויג +00:00, lag_s=null); footprint/bars_5min IL-local מתויגים +00:00; cumulative_delta/volume_profile UTC תקין (`17:0x`). **imbalance `[FRESH] 0s` אך lag_s=2658s (~44min) > 90s req = stale-but-Present.** מפר Rule 4. פער backend↔Sierra ts = ממצא — להצליב v9_export — CC.
- **I-19 🔴→לא משחזר:** build/pattern-status **72ms** (200, len 88581). נקי.
- **I-20 🟡→נמשך:** bridge `data_freshness.lag_seconds=-106238.5/fresh=true/last_bar_ts=null/threshold=90` (שלילי ~-29.5h). predicate לא אוכף סף. readiness via gates → DEGRADED נכון (מ-GRAY בלבד, לא מ-freshness).
- **I-21 🟡→לא משחזר:** ערוץ 5דק' חי — five_min buffer=18, opening OPEN_DRIVE, S2/S4 ירו היום, cci נע. אין stall.
- **I-22 🔴→ממצא חוזר (עסקה טרייה):** pnl_r שבור — id=20 S4 SHORT entry 7489.25/stop_init 7491.75 (risk **2.5pt**) exit 7383.25 (**+106pt**) ⇒ R-אמיתי≈**+42R**, מדווח `pnl_r=233` (~5.5× ניפוח, $582.5). id=22 נסגר BE ($0/0R, תקין). **חוסם ΣR/win-rate counterfactual.** נוסחה: חלוקה ב-risk_$ פר-חוזה, לא בערך-טיק — CC.
- **I-23 🟡→ממצא חוזר:** gateway `trades_today=0/daily_pnl=0/shadow_active_count=0` בעוד **2 עסקאות היום** (id=20+id=22, שתיהן סגורות) ו-board "S2×1 S4×1". מוני-היום לא סופרים shadow fires. (shadow_active_count=0 תקין כעת — שתיהן סגורות.)
- **I-24 🟡→נמשך (מושתק):** tpo DEAD מ-2023-11-25 + tick_reversal_15 DEAD מ-06-05, שניהם `disabled (S3_MUTE/S5)`/crit=false ⇒ לא נספרים ב-readiness (bridge_streams_fresh ✓). verdict DEGRADED מ-GRAY בלבד. תואם החלטת-SoT.

### מקור-אמת — להצלבת CC מול Sierra v9_export (לא כאן)
1. **woodies_5min ts עתידי** `2026-06-10 22:40` (~+30h) — להצליב mtime+bar-ts מול `~/SierraChart_Data/v9_export/`. פער backend↔Sierra = ממצא (I-18).
2. **imbalance stale-but-Present** — gate מציג `[FRESH] 0s` אך freshness.ts ~44min ישן (lag 2658s>90s, crit=true) — להצליב mtime-קובץ מול last-bar-ts ב-Sierra; ה-predicate לא אוכף (I-18/I-20).
3. **CCI-14/TCCI** (endpoint cci_14=+60.22/GRAY מול פאנל ≈53.74) — להצליב study fields גולמיים; פער-UI ~7pt (I-15).
4. **footprint export** — קובץ נכתב (mtime עכשיו 20:09 IL) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
5. **pnl_r** id=20 — להצליב entry/stop/exit-fills מול risk_$ פר-חוזה (I-22).
6. **`Y IB dll_missing`** (header) — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-session_min=0/vote_history=[] (I-1).

**NOT-DONE:** (1) **אין counterfactual ל-ZLR** — GRAY ⇒ ZLR לא armed כלל (A1-veto לפני detection); אין signal לחשב. (2) `session_min=0`+`vote_history=[]` ב-~222דק' — feed-instance, CC (לא אופיין שורשית). (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) FHB-state לא נחשף ב-endpoint (I-4). (5) הצלבות-Sierra (1–6) הן ל-CC, לא כאן. (6) צילומים inline בלבד — save_to_disk ללא-אפקט בסשן זה. (7) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [12:41 CT · 2026-06-09] Snapshot עמוק #9 — Cowork (~251דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**הקשר-שלב:** ~4ש' לתוך RTH, day_type מסווג ולוח READY. אין חסימות-שלב — כל חסם להלן אמיתי.
**Latency:** כל 8 ה-endpoints ענו <50ms; `build/pattern-status` **46ms** len 88KB (I-19 לא משחזר — 9 רצופים נקיים היום).
**צילום (Chrome MCP):** Build-Status טבלה מ-live build/pattern-status = `ss_61805womo`. ⚠️ **frontend (localhost:3000) DOWN** ⇒ אין לוח-UI מקורי (לא הופעל, per CLAUDE.md §Service Bring-Up); הטבלה רונדרה מנתוני-ה-endpoint החיים. `save_to_disk` ללא-אפקט בסשן (לא נשמר לדיסק ב-Mac). **computer-use approval timed-out** — ריצה אוטונומית, אין משתמש לאשר.

### ערכים גולמיים
- **woodies/current:** running✓ hydrated✓ · `cci_14=+124.08` (נע +124.49→+124.08) · `cci_6_tcci=+107.16` · `ema_34=7331.97` · `lsma=7304.06` · `swi=-28.83` · `czi=44.0` · **trend_state=BLUE** · signal=NEUTRAL · `classification=NO_SETUP` · buffer=50 · `active_patterns=[]` · last_reasoning="HTLB LONG size=half: CCI=-2.1, trend=RED, conf=0.65, group=REVERSAL".
- **decision_tree:** A1 SKIP(no patterns) · A2 PASS(11 studies present) · A3 SKIP(no patterns this bar) · A4 SKIP(no setup needs touch-points) · A5 PASS(advisory:calculate_size=reject) · A6 SKIP(NO_SETUP) · A7 SKIP(no fire_setup).
- **footprint/current:** running✓ hydrated✓ · **bars_today=0 · buffer=0 · cumulative_delta=0** · flow null.
- **five_min/current + /stats:** running✓ · `mode=DAY_TYPE_MODE` · buffer=35 · `opening_type=OPEN_DRIVE` · patterns_detected=0 · setups_published=0.
- **day_type/state:** `stage=B2 · day_type=Trend_Normal · confidence=0.38 · lock=LOCKED_LOW_CONF · opening_type=OPEN_DRIVE · ib_width=WIDE · behavior=DEVELOPING · range_category=NORMAL · session_min=0 · vote_history=[] · profile_shape=null`.
- **gateway/status:** trades_today=0 · shadow_active=0 · daily_pnl=0 · **chop_state=FOUND** · cooldown/cluster_guard/ssv inactive.
- **readiness:** verdict=**READY**. checks: `bridge_streams_fresh ✓` · `s1_day_type_classified ✓ day_type=Trend_Normal` · `s4_trend_not_stuck_gray ✓ trend_state=BLUE` · `rth ✓`.
- **trades/recent (5):** **2 עסקאות-טריות היום** — id=22 S2 BEAR_FLAG SHORT entry 7313.5/stop 7349.75/exit 7313.5 = **BE $0/0R** (19:00 IL=11:00 CT); id=20 S4 SHORT entry 7489.25/stop 7491.75 (risk 2.5pt)/exit 7383.25 = +106pt **$582.5/`pnl_r=233`** (16:50 IL=08:50 CT). + שישי id=13 `$66.88=26.75R`, id=12 `$20=16R`, id=10 `$230=92R`.
- **global_gates (bridge):** woodies_5min crit `ts 2026-06-10 22:40` ⚠️**עתידי** · footprint `[disabled S3_MUTE] crit=false · 06-09 20:41 IL` · cumulative_delta crit `17:40 UTC` · volume_profile crit `17:41 UTC` · tick_reversal_15 `[disabled] crit=false [DEAD] 06-05 15:51` · imbalance crit `17:40 UTC` · tpo `[disabled] crit=false [DEAD] 2023-11-25` · bars_5min crit `20:40 IL`.
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-104337 (~-29h) · fresh=true · threshold=90` (I-20).

### תבניות-ירי — 5 שאלות

**S4 · Woodies (ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR) — 9 armed, 0 fired-this-bar:**
1. **יש נתון?** כן — 11 studies present (A2 PASS), cci_14 נע +124.08, buffer 50.
2. **הגיוני?** כן — CCI חיובי ⇒ trend_state=BLUE; engine↔board מסכימים BLUE (C-1 לא משחזר). last_reasoning מזכיר RED/CCI=-2.1 — שאריות-בר קודם, לא הבר הנוכחי.
3. **מה חסם?** active_patterns=[] (A3 no patterns this bar) — אין setup הבר. כל 9 ב-build = armed אך blocked על `targets_stop.r_t1_gate ; targets_stop.stop_price ; targets_stop.targets ; exit_rules.ready_to_route` ⇒ **היעדר טבלת stop/target** מונע בניית fire_setup גם כשתבנית תזוהה.
4. **צריך לחסום?** **לא לגיטימי** — זהו ה-bottleneck המבני (I-3/I-13/missed-trades 06-08): גם signals שזוהו (ZLR @11:13 06-09, 9 ZLR+50 HFE @06-08) נחסמו ב-route מהיעדר stop/target אמיתי, לא מ-gate-שוק. דרוש טבלת stop/target פר-תבנית×day-type.
5. **מה חסר?** טבלת stop/target (anchor/T1/stop) → fire_setup; atr_daily/yesterday-IB מה-DLL (`Y IB dll_missing`).

**S2 · Five-Min — 6 armed / 1 fired / 4 blocked:**
1. **יש נתון?** כן — buffer 35, ערוץ חי (mode=DAY_TYPE_MODE), opening=OPEN_DRIVE.
2. **הגיוני?** כן — Reactive/Initiative/Bull-Flag armed על detection אמיתי; Bear-Flag-Short **fired** (=id=22 היום).
3. **מה חסם?** 6 armed חוסמות רק על detection אמיתי (b1_sellers/b1_buyers/b1_expansion/breakout). 4 day-patterns (INV_HNS/HNS_TOP/DOUBLE_BOTTOM_EE/DOUBLE_TOP_AA) blocked על `day_type_gate.auth_table_cell ; detection.swing_*`. **אין `Missing: data.choppiness_ok`** (I-16 לא משחזר; chop gate OFF per standing decision).
4. **צריך לחסום?** **כן לגיטימי** — auth_table_cell×Trend_Normal הוא ה-auth-table המכוון (day-patterns לא מורשות תחת Trend_Normal). detection-await תקין.
5. **מה חסר?** FHB-state לא נחשף ב-endpoint (I-4). אחרת — תקין.

**S3 · Footprint (Absorption/Stacked-Imbalance/Sweep-Return/Exhaustion) — 4 blocked:**
1. **יש נתון?** **לא** — bars_today=0, buffer=0, cumulative_delta=0, flow null.
2. **הגיוני?** לא — 0 ברים ב-4ש' לתוך RTH; הקובץ **כן נכתב** (gate footprint ts 20:41 IL = עכשיו).
3. **מה חסם?** `data.buffer_size ; data.bars_today` — ingest file→bridge→buffer שבור (I-11, אישור #30 היום).
4. **צריך לחסום?** מבחינת readiness לא — footprint crit=false (S3_MUTE), לא חוסם לוח. S3 deferred עד אחרי-LIVE (memory).
5. **מה חסר?** נתיב ה-ingest של footprint (file→bridge-parse→buffer). מוקפא בכוונה (S3_MUTE), לא נפתר.

### חשודים (Issues Register) — סטטוס

- **I-1 (day_type UNKNOWN):** 🟡 **לא חוסם.** state-endpoint + readiness מסכימים **Trend_Normal** B2/0.38 (אין פיצול-3-כיווני בסנאפ-שוט זה); opening_type=OPEN_DRIVE עקבי (state↔five_min). residual: `session_min=0`+`vote_history=[]` ב-~251דק'. feed-instance — CC.
- **I-3 (ZLR):** 🔬 trend **BLUE** (cci_14=+124) ⇒ A1-veto לא חל; ZLR armed אך `active_patterns=[]` (A3 no pattern this bar). אין setup-ZLR טרי ⇒ **אין counterfactual**.
- **I-11 (S3 footprint 0 ברים):** 🔴 **אישור #30** — bars_today=0/buffer=0/cum_delta=0 בעוד gate footprint נכתב עכשיו (20:41 IL); ערוץ 5דק' חי ⇒ ingest-break עצמאי מ-I-21, מושתק S3_MUTE לא-נפתר.
- **I-15 / C-1 (trend split):** ✅ **לא משחזר** — engine BLUE + board `s4_trend_not_stuck_gray ✓ BLUE` מסכימים. frontend DOWN ⇒ אין הצלבת-UI. הצלבת Sierra (WSI/CCI) חובה — CC.
- **I-16 (choppiness_ok):** ✅ **לא משחזר** — 0 תבניות-S2 עם `Missing: data.choppiness_ok` (6 armed). chop_state=FOUND, gate OFF per standing decision. מחזק I-17.
- **I-18 / C-4 (TZ-mix gates):** 🟡 **נמשך** — woodies_5min ts **עתידי `2026-06-10 22:40`**, footprint/bars_5min IL-local (20:40/20:41) ללא TZ-marker; cumulative_delta/volume_profile/imbalance UTC (17:40). מפר Rule 4.
- **I-19 / C-5 (pattern-status hang):** ✅ **לא משחזר** — 46ms (9 רצופים נקיים היום).
- **I-20 / C-6 (lag שלילי fresh=true):** 🟡 **נמשך** — `lag=-104337/fresh=true/threshold=90` (~-29h); predicate לא אוכף `|lag|≤threshold`. readiness via crit-gates → READY (נכון).
- **I-21 (stall 5דק'):** 🟡 **לא משחזר** — ערוץ 5דק' חי (cci נע, S2/S4 ירו היום). אין stall.
- **I-22 / F-1 (pnl_r מנופח):** 🔴 **אישור חוזר** — id=20 S4 SHORT entry 7489.25/stop 7491.75 (risk 2.5pt) exit 7383.25 (+106pt) ⇒ R-אמיתי≈**+42R** אך `pnl_r=233` (~5.5× ניפוח, $582.5). id=22 BE ($0/0R תקין). חוסם ΣR-counterfactual. נוסחה: חלוקה ב-risk_$ פר-חוזה — CC.
- **I-23 / F-2 (gateway counters):** 🟡 **אישור חוזר** — `trades_today=0/daily_pnl=0/shadow_active_count=0` בעוד **2 עסקאות היום** (id=20+id=22, סגורות) + board 'S2×1 S4×1'. מוני-היום לא סופרים shadow fires.
- **I-24 (S5/TPO + tick_reversal מתים, מושתקים):** 🟡 **נמשך/מושתק** — tpo DEAD 2023-11-25 + tick_reversal_15 DEAD 06-05, שניהם `disabled (S3_MUTE/S5)`/crit=false ⇒ לא נספרים ב-readiness (board READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC (לא כאן)
1. **woodies cci_14=+124.08 / trend BLUE** מול Sierra `~/SierraChart_Data/v9_export/` CCI-14/TCCI גולמי.
2. **woodies_5min gate ts עתידי 2026-06-10 22:40** — פער backend↔Sierra ts (I-18); להצליב mtime/last-bar בקובץ.
3. **footprint** — קובץ נכתב (20:41 IL) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
4. **pnl_r id=20** — entry/stop/exit-fills מול risk_$ פר-חוזה (I-22).
5. **`Y IB dll_missing`** — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-session_min=0/vote_history=[] (I-1).

**NOT-DONE:** (1) **אין counterfactual ל-ZLR/HFE** — trend BLUE + active_patterns=[] ⇒ אין signal טרי לחשב. (2) `session_min=0`+`vote_history=[]` ב-~251דק' — feed-instance, לא אופיין שורשית (CC). (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) FHB-state לא נחשף ב-endpoint (I-4). (5) הצלבות-Sierra (1–5) הן ל-CC. (6) **frontend DOWN** — לא הופעל (CLAUDE.md §Service Bring-Up); אין לוח-UI מקורי, אין הצלבת UI↔engine ל-CCI (I-15). (7) צילום inline בלבד — save_to_disk ללא-אפקט + computer-use approval timed-out (ריצה אוטונומית). (8) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

## [13:13 CT · 2026-06-09] Snapshot עמוק #10 — Cowork (~283דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**הקשר-שלב:** ~4.7ש' לתוך RTH, day_type מסווג ולוח READY. אין חסימות-שלב — כל חסם להלן אמיתי. **שינוי-מצב מ-#9:** trend התהפך BLUE→ ו-**ZLR נדרך והגיע ל-A7 עם sizing=FULL** (לא reject) — ראיה חיה ל-bottleneck stop/target.
**Latency:** כל 7 ה-endpoints ענו ≤122ms; `build/pattern-status` **51ms** len 87KB (I-19 לא משחזר — 10 רצופים נקיים היום).
**צילום (Chrome MCP):** Dashboard CCI-panel = `ss_1306g6p4m`; Build-Status decision-tree = `ss_2281nd2ij`. ✅ **frontend (localhost:3000) כבר רץ** (לא הופעל על-ידי — נווטתי וטוען מלא, per CLAUDE.md §Service Bring-Up); הפעם **יש הצלבת UI↔engine ל-CCI** (I-15). `save_to_disk` ללא-אפקט בסשן (inline בלבד).

### ערכים גולמיים
- **woodies/current:** running✓ hydrated✓ · `cci_14=+94.15` · `cci_6_tcci=+105.73` · `ema_34=7336.63` · `lsma=7350.2` · `swi=8.03` · `czi=76.0` · **trend_state=BLUE** · **signal=ZLR LONG** · `classification=TACTICAL` · buffer=50 · **`active_patterns=[ZLR LONG conf 0.65 group=CONTINUATION entry 7355.75 / stop 7344.25 / target 7356.75]`**.
- **decision_tree (ZLR):** A1 PASS(trend_state=BLUE) · A2 PASS(11 studies) · A3 PASS(patterns=['ZLR']) · A4 PASS(touch-point advisory degraded: tpo/veto/killzone/layer0 missing; day_type=Trend_Normal conf 0.38) · **A5 PASS(sizing=full)** · A6 PASS(code=TACTICAL spec=REACTIVE) · **A7 FAIL "missing fire_setup for routable pattern"**.
- **footprint/current:** running✓ hydrated✓ · **bars_today=0 · buffer=0 · cumulative_delta=0** · flow null · NO_SETUP.
- **five_min/current + /stats:** running✓ · `mode=DAY_TYPE_MODE` · buffer=49-51 · `opening_type=OPEN_DRIVE` · last_pattern=BULL_FLAG_LONG conf 91 · patterns_detected=0 · setups_published=0 · last_reasoning="BULL_FLAG LONG size=half: 3-bar, COT=-32643 vs AMT=-38677, location=far".
- **day_type/state:** `stage=B2 · day_type=Trend_Normal · confidence=0.38 · lock=LOCKED_LOW_CONF · opening_type=OPEN_DRIVE · ib_width=WIDE · behavior=DEVELOPING · range_category=NORMAL · session_min=0 · vote_history=[] · profile_shape=null`.
- **gateway/status:** trades_today=0 · shadow_active=0 · daily_pnl=0 · **chop_state=FOUND** · demo_enabled=[2,4] · live_enabled=[] · cooldown/cluster_guard/ssv inactive.
- **readiness:** verdict=**READY** ("all checks passed"). checks: `bridge_streams_fresh ✓ (block)` · `s1_day_type_classified ✓ day_type=Trend_Normal (degrade)` · `s4_trend_not_stuck_gray ✓ trend_state=BLUE (degrade)` · `in_rth ✓`.
- **trades/recent (5):** **2 עסקאות-טריות היום** — id=22 S2 BEAR_FLAG SHORT entry 7313.5/stop 7349.75/exit 7313.5 = **BE $0/0R** (manual, 19:00 IL=11:00 CT); id=20 S4 HTLB SHORT entry 7489.25/stop 7491.75 (risk 2.5pt)/exit 7383.25 T1✓T2✓ TIME_STOP = +106pt **$582.5/`pnl_r=233`** (16:50 IL=08:50 CT). + שישי id=13 `$66.88=26.75R`, id=12 `$20=16R`, id=10 `$230=92R`.
- **global_gates (bridge):** woodies_5min crit `ts 2026-06-10 22:40` ⚠️**עתידי** lag=null · footprint `[disabled S3_MUTE] crit=false · 06-09 21:10 IL` · cumulative_delta crit `18:09:59 UTC lag 32.5s` · volume_profile crit `18:10:27 UTC lag 4.5s` · tick_reversal_15 `[disabled] crit=false [DEAD] 5899min 06-05 15:51` · imbalance crit `18:10:11 UTC lag 20.5s` (תקין הפעם, לא stale) · tpo `[disabled] crit=false [DEAD] 2023-11-25` · bars_5min crit `21:10 IL` (≈עכשיו, חי).
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-102568 (~-28.5h) · fresh=true · threshold=90` (I-20).
- **UI (dashboard, frontend חי):** price 7354.00 "0.9s ago" · TRD 38% H · chop "**11 FOUND**" · Trend Normal CLASSIFIED 38% · OPEN_DRIVE WIDE · IBH 7417/IBL 7390.75 26.3pt · `Y IB dll_missing` · WR 50% · SHADOW 0t $0 · Build-Status verdict **READY** "S2×1 S4×1 ירו היום" · Day Type/Footprint "**? stale**" + Woodies CCI/Min-Patterns "warming 3m" (=artifact-TZ I-18). **Woodies-CCI panel: CCIDiff -13.13 / CCI ≈83.09 מול engine cci_14=+94.15 (~11pt gap).**

### תבניות-ירי — 5 שאלות

**S4 · Woodies (ZLR/TLB/TT/GB100/Vegas/Ghost/FaMir) — 9 armed; ⭐ ZLR הגיע ל-A7:**
1. **יש נתון?** כן — 11 studies present (A2), cci_14=+94.15, buffer 50, ZLR active.
2. **הגיוני?** כן — CCI חיובי ⇒ trend BLUE; **engine↔board מסכימים BLUE (C-1/I-15 לא משחזר קונפליקט)**. אך פער UI↔engine ~11pt (panel CCIDiff -13.13/CCI≈83 מול endpoint +94.15) — skew-תצוגה נמשך.
3. **מה חסם?** ⭐ **ZLR: A1–A6 PASS (A5 sizing=FULL), A7 FAIL "missing fire_setup"** — entry 7355.75/stop 7344.25 (risk 11.5pt)/target **7356.75 (1pt בלבד מעל entry ⇒ R:R≈0.087)**. target מנוון ⇒ fire_setup לא נבנה. כל 9 ב-build = armed אך blocked על `targets_stop.r_t1_gate ; stop_price ; targets ; exit_rules.ready_to_route`.
4. **צריך לחסום?** **לא לגיטימי כשורש** — שער ה-R:R צודק שחוסם target של 1pt, אבל הסימפטום הוא **היעדר טבלת stop/target**: בלי anchor/T1/stop אמיתי המנוע מייצר target מנוון ואז A7 חוסם. זהו ה-bottleneck המבני (I-3/I-13/missed-trades 06-08). **הפעם sizing=FULL (לא reject)** ⇒ מפריך את ההשערה ש-A5 הוא החוסם; A7/stop-target הוא.
5. **מה חסר?** טבלת stop/target פר-תבנית×day-type → fire_setup; atr_daily/yesterday-IB מה-DLL (`Y IB dll_missing`).

**S2 · Five-Min — 6 armed / 1 fired / 4 blocked:**
1. **יש נתון?** כן — buffer 49-51, ערוץ חי (DAY_TYPE_MODE), opening=OPEN_DRIVE, last_pattern=BULL_FLAG_LONG conf 91.
2. **הגיוני?** כן — REACTIVE_L/S, INITIATIVE_L/S, BULL_FLAG armed על detection אמיתי; **BEAR_FLAG_SHORT fired** (=id=22 היום).
3. **מה חסם?** 6 armed חוסמות רק על detection (b2_volume_drop/b1_buyers/b1_expansion/flag_length/pole_found). 4 day-patterns (INV_HNS/HNS_TOP/DOUBLE_BOTTOM_EE/DOUBLE_TOP_AA) blocked על `day_type_gate.auth_table_cell ; detection.swing_*`. **אין `Missing: data.choppiness_ok`** (I-16 לא משחזר; chop_state=FOUND, gate OFF per standing decision).
4. **צריך לחסום?** **כן לגיטימי** — auth_table_cell×Trend_Normal הוא ה-auth-table המכוון. detection-await תקין.
5. **מה חסר?** FHB-state לא נחשף ב-endpoint (I-4). אחרת — תקין.

**S3 · Footprint (Absorption/Stacked-Imbalance/Sweep-Return/Exhaustion) — 4 blocked:**
1. **יש נתון?** **לא** — bars_today=0, buffer=0, cumulative_delta=0, flow null.
2. **הגיוני?** לא — 0 ברים ב-~4.7ש' לתוך RTH; הקובץ **כן נכתב** (gate footprint ts 21:10 IL = עכשיו).
3. **מה חסם?** `data.buffer_size ; data.bars_today` — ingest file→bridge→buffer שבור (I-11, אישור #31 היום).
4. **צריך לחסום?** מבחינת readiness לא — footprint crit=false (S3_MUTE), לא חוסם לוח. S3 deferred עד אחרי-LIVE.
5. **מה חסר?** נתיב ה-ingest של footprint (file→bridge-parse→buffer). מוקפא בכוונה (S3_MUTE), לא נפתר.

### סטטוס חשודים — סבב #10
- **I-1 (day_type UNKNOWN/instance-split):** 🟡 **לא חוסם, אין פיצול-3-כיווני** — state-endpoint + readiness `s1_day_type_classified ✓ Trend_Normal` + S2 auth-gate כולם Trend_Normal; opening_type=OPEN_DRIVE עקבי (state↔five_min↔UI). residual: `session_min=0`+`vote_history=[]` ב-~283דק' (feed-instance — CC).
- **I-2 (A5 advisory):** 🟡 **תקין** — A5 PASS sizing=full (לא reject הפעם, ZLR live). לא חוסם.
- **I-3 (ZLR לא ירה):** 🔬 **ממצא חי — ZLR ב-A7** — A1–A6 PASS, A7 FAIL 'missing fire_setup'; target מנוון 1pt (R:R≈0.087). reject_reason הקונקרטי = היעדר טבלת stop/target. counterfactual חסר-משמעות (target מנוון). CC: targets_stop/exit_rules→fire_setup.
- **I-4 (S2 דריכה):** 🔬 **תקין** — 6/10 armed + 1 fired על ערוץ חי (buffer 49-51); FHB-state עדיין לא נחשף ב-endpoint.
- **I-5 / B-11 (board crash):** 🟡 **לא משחזר** — verdict READY, bridge_streams_fresh ✓, אין באנר OFFLINE שקרי.
- **I-11 (footprint 0 ברים):** 🔴 **אישור #31** — gate footprint נכתב עכשיו (21:10 IL) אך bars_today=0/buffer=0/flow null; ערוץ 5דק' חי (bars_5min FRESH) ⇒ file→bridge→buffer שבור, עצמאי מ-I-21. מושתק S3_MUTE/crit=false.
- **I-13 (A5/sizing מפספס):** 🔴 **לא נצפה ירידת-sizing** — ZLR A5=sizing=**full** (לא reject); החסם A7/stop-target. מחזק ש-A5 אינו ה-bottleneck.
- **I-15 / C-1 (trend conflict):** 🔬 **לא משחזר קונפליקט** — engine cci_14=+94.15/BLUE + board `s4_trend_not_stuck_gray ✓ BLUE` מסכימים. **frontend חי הפעם:** panel CCIDiff -13.13/CCI≈83.09 מול endpoint +94.15 (~11pt skew-תצוגה). הצלבת Sierra (WSI/CCI גולמי) חובה.
- **I-16 (choppiness_ok missing):** 🟡 **לא משחזר** — 6/10 S2 armed, אין 'Missing: data.choppiness_ok' (chop_state=FOUND, UI '11 FOUND'). מחזק I-17.
- **I-17 (restart מאפס buffers / תנודתיות-גבול-בר):** 🔬 **תומך** — five_min buffer=49-51 (≠35@12:41); choppiness_ok present/6 armed ⇒ תנודתיות-גבול-בר.
- **I-18 / C-4 (TZ-mix freshness):** 🟡 **נמשך** — woodies_5min gate ts **עתידי** 2026-06-10 22:40 (IL מתויג +00:00, lag=null); footprint/bars_5min IL-local; cumulative_delta/volume_profile/imbalance UTC תקין (18:0x, lag 4.5-32.5s). board 'Day Type/Footprint × stale' + 'warming 3m' = artifact-TZ. מפר Rule 4.
- **I-19 / C-5 (pattern-status hang):** 🔴→ **לא משחזר** — 51ms (200, len 87479); כל endpoints ≤122ms. 10 רצופים נקיים היום.
- **I-20 / C-6 (lag שלילי fresh=true):** 🟡 **נמשך** — `lag=-102568/fresh=true/threshold=90` (~-28.5h); predicate לא אוכף `|lag|≤threshold`. readiness via crit-gates → READY (נכון).
- **I-21 (stall 5דק'):** 🟡 **לא משחזר** — ערוץ 5דק' חי (bars_5min FRESH 21:10 IL, S2/S4 ירו היום, cci נע). אין stall.
- **I-22 / F-1 (pnl_r מנופח):** 🔴 **אישור חוזר** — id=20 S4 SHORT risk 2.5pt / +106pt ⇒ R-אמיתי≈**+42R** אך `pnl_r=233` (~5.5× ניפוח, $582.5). id=22 BE ($0/0R תקין). חוסם ΣR-counterfactual. נוסחה: חלוקה ב-risk_$ פר-חוזה — CC.
- **I-23 / F-2 (gateway counters):** 🟡 **אישור חוזר** — `trades_today=0/daily_pnl=0/shadow_active_count=0` בעוד **2 עסקאות היום** (id=20+id=22) + board 'S2×1 S4×1'. מוני-היום לא סופרים shadow fires.
- **I-24 (S5/TPO + tick_reversal מתים, מושתקים):** 🟡 **נמשך/מושתק** — tpo DEAD 2023-11-25 + tick_reversal_15 DEAD 06-05, שניהם `disabled (S3_MUTE/S5)`/crit=false ⇒ לא נספרים ב-readiness (board READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC (לא כאן)
1. **woodies cci_14=+94.15 / trend BLUE** + **פער UI↔engine ~11pt** (panel CCIDiff -13.13/CCI≈83 מול endpoint +94.15) — מול Sierra `~/SierraChart_Data/v9_export/` CCI-14/TCCI גולמי; לקבוע איזה ערך נכון.
2. **ZLR fire_setup** — entry 7355.75/stop 7344.25/target 7356.75: למה ה-target מנוון (1pt)? targets_stop→fire_setup מול טבלת stop/target (I-3/I-13).
3. **woodies_5min gate ts עתידי 2026-06-10 22:40** — פער backend↔Sierra ts (I-18); להצליב mtime/last-bar בקובץ.
4. **footprint** — קובץ נכתב (21:10 IL) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
5. **pnl_r id=20** — entry/stop/exit-fills מול risk_$ פר-חוזה (I-22).
6. **`Y IB dll_missing`** — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-session_min=0/vote_history=[] (I-1).

**NOT-DONE:** (1) **counterfactual ל-ZLR חסר-משמעות** — target מנוון 1pt ⇒ R:R≈0.087, לא ניתן לחשב W/L אמין. (2) `session_min=0`+`vote_history=[]` ב-~283דק' — feed-instance, לא אופיין שורשית (CC). (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) FHB-state לא נחשף ב-endpoint (I-4). (5) הצלבות-Sierra (1–6) הן ל-CC. (6) צילום inline בלבד — `save_to_disk` ללא-אפקט. (7) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [13:41 CT · 2026-06-09] Snapshot עמוק #11 — Cowork (~311דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**הקשר-שלב:** ~5.2ש' לתוך RTH, day_type מסווג ולוח READY. אין חסימות-שלב — כל חסם להלן אמיתי. **שינוי-מצב מ-#10:** (א) trend נשאר BLUE אך cci_14 עלה +94→**+147.67** ⇒ ZLR **כבר לא active** (A3 no pattern this bar, signal=NEUTRAL/NO_SETUP) — אין ממצא-A7 ואין counterfactual הפעם. (ב) **frontend (localhost:3000) ירד** (`Failed to fetch`) ⇒ אין הצלבת UI↔engine ל-CCI הפעם. (ג) gate `imbalance` חזר ל-**stale-but-Present** (lag ~9.6דק').
**Latency:** כל 7 ה-endpoints ענו ≤38ms; `build/pattern-status` **97ms** len 89KB (I-19 לא משחזר — 11 רצופים נקיים היום).
**צילום:** frontend down + אין board-HTML ב-:8000 root (404) + אין מאשר אינטראקטיבי לצילום-שולחן (request_access timeout) ⇒ רינדרתי board מתוך ה-JSON ב-tab וצילמתי דרך Chrome-MCP = `ss_9167goqiz` (inline בלבד — `save_to_disk` ללא-אפקט בסשן).

### ערכים גולמיים
- **woodies/current:** running✓ hydrated✓ · `cci_14=+147.67` · `cci_6_tcci=+107.89` · `ema_34=7346.32` · `lsma=7388.78` · `swi=1.58` · `czi=141` · **trend_state=BLUE** · **signal=NEUTRAL** · `classification=NO_SETUP` · buffer=50 · **`active_patterns=[]`**. decision_tree: A1 SKIP(no patterns) · A2 PASS(11 studies) · A3 SKIP(no patterns this bar) · A4 SKIP · A5 PASS(advisory:calculate_size=reject) · A6 SKIP(NO_SETUP) · A7 SKIP(no fire_setup).
- **footprint/current:** running✓ hydrated✓ · **bars_today=0 · buffer=0 · cumulative_delta=0** · flow null · NO_SETUP.
- **five_min/current + /stats:** running✓ · `mode=DAY_TYPE_MODE` · buffer=62 · `opening_type=OPEN_DRIVE` · last_pattern=BULL_FLAG_LONG conf 86 · patterns_detected=0 · setups_published=0 · last_reasoning="BULL_FLAG LONG size=half: 3-bar, COT=-28245 vs AMT=-32029, location=far".
- **day_type/state:** `stage=B2 · day_type=Trend_Normal · confidence=0.38 · lock=LOCKED_LOW_CONF · opening_type=OPEN_DRIVE · ib_width=WIDE · behavior=DEVELOPING · range_category=NORMAL · session_min=0 · vote_history=[] · profile_shape=null`.
- **gateway/status:** trades_today=0 · shadow_active=0 · daily_pnl=0 · **chop_state=FOUND** · demo_enabled=[2,4] · live_enabled=[] · cooldown/cluster_guard/ssv inactive.
- **readiness:** verdict=**READY** ("all checks passed"). checks: `bridge_streams_fresh ✓ (block)` · `s1_day_type_classified ✓ day_type=Trend_Normal (degrade)` · `s4_trend_not_stuck_gray ✓ trend_state=BLUE (degrade)` · `in_rth ✓`.
- **trades/recent (5):** **2 עסקאות-טריות היום** — id=20 S4 HTLB SHORT entry 7489.25/stop 7491.75 (risk 2.5pt)/exit 7383.25, C1 HIT(7485.75 $17.5/14R) C2 HIT(7482.25 $35/28R) C3 OPEN(7383.25 $530/424R) = **$582.5/`pnl_r=233`** (16:50 IL=08:50 CT); id=22 S2 SHORT entry 7313.5/exit 7313.5 כל 3 חוזים OPEN = **BE $0/0R** (19:00 IL=11:00 CT). + שישי id=13 `$66.88=26.75R`, id=12 `$20=16R`, id=10 `$230=92R`.
- **global_gates (bridge):** woodies_5min crit `ts 2026-06-10 22:40:00` ⚠️**עתידי** (IL מתויג +00:00) lag=null · footprint `[disabled S3_MUTE] crit=false · 06-09 21:39:50 IL` (נכתב עכשיו) · cumulative_delta crit `18:34:59 UTC lag 293s` (תקין <360) · volume_profile crit `18:39:49 UTC lag 3.45s` · tick_reversal_15 `[disabled] crit=false [DEAD] 5928min 06-05 15:51` · **imbalance crit `18:30:17 UTC lag 575s (~9.6דק')` = stale-but-Present** (חזר מ-#10 התקין) · tpo `[disabled] crit=false [DEAD] 2023-11-25` · bars_5min crit `21:35:00 IL` (חי, ≈עכשיו).
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-100807 (~-28h) · fresh=true · threshold=90` (I-20). **five_min/woodies data_freshness:** `last_bar_ts=2026-06-09 21:35:00+03:00 (=13:35 CT) · lag=292.5s · fresh=true · threshold=660` (ערוץ 5דק' חי, lag אמיתי).

### תבניות-ירי — 5 שאלות

**S4 · Woodies (ZLR/TLB/TT/GB100/Vegas/Ghost/FaMir) — 9 armed; אין setup-ירי הבר:**
1. **יש נתון?** כן — 11 studies present (A2), cci_14=+147.67, buffer 50.
2. **הגיוני?** כן — CCI חיובי-גבוה ⇒ trend BLUE; **engine↔board מסכימים BLUE (C-1/I-15 לא משחזר קונפליקט)**. frontend down ⇒ אין הצלבת-UI הפעם.
3. **מה חסם?** **אין active_pattern הבר** (A3 SKIP "no patterns this bar"), signal=NEUTRAL ⇒ אין ZLR/setup-ירי לחסום. ב-build כל 9 = armed אך blocked על `detection.pattern_specific ; targets_stop.r_t1_gate ; stop_price ; targets ; exit_rules.ready_to_route` (החוסם המבני הקבוע — היעדר fire_setup/טבלת stop-target).
4. **צריך לחסום?** detection-await תקין (אין תבנית הבר). **החוסם המבני (targets_stop/exit_rules) לא-לגיטימי כשורש** — סימפטום של היעדר טבלת stop/target (I-3/I-13). לא ניתן לאמת counterfactual ללא setup חי.
5. **מה חסר?** טבלת stop/target פר-תבנית×day-type → fire_setup; atr_daily/yesterday-IB מה-DLL (`Y IB dll_missing`).

**S2 · Five-Min — 6 armed / 1 fired / 4 blocked:**
1. **יש נתון?** כן — buffer 62, ערוץ חי (DAY_TYPE_MODE, df lag 292.5s), opening=OPEN_DRIVE.
2. **הגיוני?** כן — REACTIVE_L/S, INITIATIVE_L/S, BULL_FLAG armed על detection אמיתי; **BEAR_FLAG_SHORT fired** (=id=22 היום).
3. **מה חסם?** 6 armed חוסמות רק על detection (b1_sellers/b4_confirm/b1_expansion×2/breakout/pole_found). 4 day-patterns (INV_HNS/HNS_TOP/DOUBLE_BOTTOM_EE/DOUBLE_TOP_AA) blocked על `day_type_gate.auth_table_cell ; detection.swing_*/hns/adam`. **אין `Missing: data.choppiness_ok`** (I-16 לא משחזר; chop_state=FOUND, gate OFF per standing decision).
4. **צריך לחסום?** **כן לגיטימי** — auth_table_cell×Trend_Normal הוא ה-auth-table המכוון. detection-await תקין.
5. **מה חסר?** FHB-state לא נחשף ב-endpoint (I-4). אחרת — תקין.

**S3 · Footprint (Absorption/Stacked-Imbalance/Sweep-Return/Exhaustion) — 4 blocked:**
1. **יש נתון?** **לא** — bars_today=0, buffer=0, cumulative_delta=0, flow null.
2. **הגיוני?** לא — 0 ברים ב-~5.2ש' לתוך RTH; הקובץ **כן נכתב** (gate footprint ts 21:39:50 IL = עכשיו).
3. **מה חסם?** `data.buffer_size ; data.bars_today` — ingest file→bridge→buffer שבור (I-11, אישור #32 היום).
4. **צריך לחסום?** מבחינת readiness לא — footprint crit=false (S3_MUTE), לא חוסם לוח. S3 deferred עד אחרי-LIVE.
5. **מה חסר?** נתיב ה-ingest של footprint (file→bridge-parse→buffer). מוקפא בכוונה (S3_MUTE), לא נפתר.

### סטטוס חשודים — סבב #11
- **I-1 (day_type UNKNOWN/instance-split):** 🟡 **לא חוסם, אין פיצול-3-כיווני** — state-endpoint + readiness `s1_day_type_classified ✓ Trend_Normal` + S2 auth-gate כולם Trend_Normal; opening_type=OPEN_DRIVE עקבי (state↔five_min). residual: `session_min=0`+`vote_history=[]` ב-~311דק' (feed-instance — CC). frontend down ⇒ אין הצלבת-UI.
- **I-2 (A5 advisory):** 🟡 **תקין** — A5 PASS advisory:calculate_size=reject על NO_SETUP — לא חוסם.
- **I-3 (ZLR לא ירה):** 🔬 **לא נדרך הבר** — trend BLUE אך cci_14=+147.67/signal=NEUTRAL, active_patterns=[] (A3 no pattern this bar). אין setup-ZLR טרי ⇒ אין counterfactual. (ב-#10 13:13 ZLR הגיע ל-A7 עם target מנוון 1pt — ה-bottleneck המבני נשאר היעדר טבלת stop/target.)
- **I-4 (S2 דריכה):** 🔬 **תקין** — 6/10 armed + 1 fired (buffer 62, ערוץ חי lag 292.5s). FHB-state עדיין לא נחשף ב-endpoint.
- **I-5 / B-11 (board crash):** 🟡 **לא משחזר** — verdict READY, bridge_streams_fresh ✓, אין באנר OFFLINE שקרי.
- **I-11 (footprint 0 ברים):** 🔴 **אישור #32** — gate footprint נכתב עכשיו (21:39:50 IL) אך bars_today=0/buffer=0/cumulative_delta=0/flow null; ערוץ 5דק' חי (bars_5min FRESH, df lag 292.5s) ⇒ file→bridge→buffer שבור, עצמאי מ-I-21. מושתק S3_MUTE/crit=false.
- **I-13 (A5/sizing מפספס):** 🔴 **לא נצפה** — NO_SETUP (active_patterns=[]), A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing לכייל.
- **I-15 / C-1 (trend conflict):** 🔬 **לא משחזר קונפליקט** — engine cci_14=+147.67/BLUE + board `s4_trend_not_stuck_gray ✓ BLUE` מסכימים. frontend down ⇒ אין הצלבת-UI היום. הצלבת Sierra (WSI/CCI גולמי) חובה.
- **I-16 (choppiness_ok missing):** 🟡 **לא משחזר** — 6/10 S2 armed, אין 'Missing: data.choppiness_ok' (chop_state=FOUND). מחזק I-17.
- **I-17 (restart מאפס buffers / תנודתיות-גבול-בר):** 🔬 **תומך** — five_min buffer=62 (≠49-51@13:13); 6 armed + choppiness_ok present ⇒ תנודתיות-גבול-בר.
- **I-18 / C-4 (TZ-mix freshness):** 🟡 **נמשך + ממצא חד** — woodies_5min gate ts **עתידי** 2026-06-10 22:40 (IL מתויג +00:00, lag=null); footprint/bars_5min IL-local; cumulative_delta/volume_profile UTC תקין (18:3x). **imbalance crit `[FRESH] 0s` אך lag_s=575s (~9.6דק') > req = stale-but-Present** (חזר מ-#10 התקין). מפר Rule 4.
- **I-19 / C-5 (pattern-status hang):** 🔴→ **לא משחזר** — 97ms (200, len 89245); כל endpoints ≤38ms. 11 רצופים נקיים היום.
- **I-20 / C-6 (lag שלילי fresh=true):** 🟡 **נמשך** — bridge `lag=-100807/fresh=true/last_bar_ts=null/threshold=90` (~-28h); predicate לא אוכף `|lag|≤threshold` (קשור ל-ts-עתידי woodies_5min I-18). readiness via crit-gates → READY (נכון).
- **I-21 (stall 5דק'):** 🟡 **לא משחזר** — ערוץ 5דק' חי (five_min/woodies df last_bar=13:35 CT lag 292.5s, bars_5min FRESH 21:35 IL, S2/S4 ירו היום). אין stall.
- **I-22 / F-1 (pnl_r מנופח):** 🔴 **אישור חוזר + הוכחת-נוסחה מ-contracts_pnl** — id=20 C1 `pnl_usd=17.5/pnl_r=14` ⇒ 17.5/14=**$1.25=ערך-טיק** (לא risk $12.5 של stop 2.5pt). ⇒ R מחושב `pnl_usd ÷ $1.25` (טיק) במקום `÷ risk_$`. id=20 +106pt/risk 2.5pt ⇒ **R-אמיתי≈+42R** אך `pnl_r=233`. id=22 BE ($0/0R תקין). חוסם ΣR-counterfactual. נוסחה: חלוקה ב-risk_$ פר-חוזה — CC.
- **I-23 / F-2 (gateway counters):** 🟡 **אישור חוזר** — `trades_today=0/daily_pnl=0/shadow_active_count=0` בעוד **2 עסקאות היום** (id=20+id=22, סגורות) + board 'S2×1 S4×1'. מוני-היום לא סופרים shadow fires.
- **I-24 (S5/TPO + tick_reversal מתים, מושתקים):** 🟡 **נמשך/מושתק** — tpo DEAD 2023-11-25 + tick_reversal_15 DEAD 06-05, שניהם `disabled (S3_MUTE/S5)`/crit=false ⇒ לא נספרים ב-readiness (board READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC (לא כאן)
1. **woodies cci_14=+147.67 / trend BLUE** — מול Sierra `~/SierraChart_Data/v9_export/` CCI-14/TCCI גולמי. (frontend down ⇒ אין הצלבת-UI הפעם; הפער-UI מתועד ב-#10.)
2. **woodies_5min gate ts עתידי 2026-06-10 22:40** — פער backend↔Sierra ts (I-18); להצליב mtime/last-bar בקובץ.
3. **imbalance lag 575s אך Present** — stale-but-Present (I-18); לאכוף required-lag על Present.
4. **footprint** — קובץ נכתב (21:39:50 IL) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
5. **pnl_r id=20** — `pnl_usd ÷ $1.25` (טיק) במקום `÷ risk_$` פר-חוזה (I-22, הוכחה מ-contracts_pnl C1 17.5/14).
6. **`Y IB dll_missing`** — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-session_min=0/vote_history=[] (I-1).

**NOT-DONE:** (1) **אין setup-ZLR טרי הבר** (signal=NEUTRAL) ⇒ אין counterfactual S4. (2) `session_min=0`+`vote_history=[]` ב-~311דק' — feed-instance, לא אופיין שורשית (CC). (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) FHB-state לא נחשף ב-endpoint (I-4). (5) הצלבות-Sierra (1–6) הן ל-CC. (6) **frontend down** ⇒ אין הצלבת UI↔engine; צילום = board מרונדר מ-JSON (`ss_9167goqiz`, inline בלבד). (7) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [14:11 CT · 2026-06-09] Snapshot עמוק #12 — Cowork (~341דק' לתוך RTH, DAY_TYPE_MODE, IB הושלמה)

**הקשר-שלב:** ~5.7ש' לתוך RTH, day_type מסווג ולוח **READY**. אין חסימות-שלב — כל חסם להלן אמיתי. **שינוי-מצב מ-#11:** (א) trend נשאר **BLUE** אך `cci_14` ירד +147.67→**+119.69** (עדיין חיובי, signal=NEUTRAL/NO_SETUP) ⇒ אין ZLR/setup-ירי, אין ממצא-A7 ואין counterfactual הפעם. (ב) `five_min buffer` צנח 62→**1** (גבול-בר/reset — תומך I-17). (ג) **opening_type ב-state נסוג OPEN_DRIVE→UNKNOWN** (פער-instance מול five_min=OPEN_DRIVE חזר). (ד) gate `imbalance` stale-but-Present החמיר ל-lag ~39דק' (מ-~9.6דק' ב-#11).
**Latency:** כל 7 ה-endpoints ענו ≤47ms; `build/pattern-status` **101ms** len 88KB — I-19 **לא משחזר (12 רצופים נקיים היום)**.
**צילום:** frontend(:3000)=`Failed to fetch` (down) + :8000 root=404 (API-only) ⇒ רינדרתי board מתוך ה-JSON ב-tab וצילמתי דרך Chrome-MCP = `ss_0011m5b1g` (inline בלבד — `save_to_disk` ללא-אפקט בסשן). מציג verdict READY + 24 שורות-תבנית (S2/S4/S3) + 8 global-gates.

### ערכים גולמיים
- **woodies/current:** running✓ hydrated✓ · `cci_14=+119.69` · `cci_6_tcci=+81.17` · `ema_34=7357.2` · **trend_state=BLUE** · **signal=NEUTRAL** · `classification=NO_SETUP` · buffer=50 · **`active_patterns=[]`** · last_reasoning="TLB SHORT size=half: CCI=125.6, trend=BLUE, conf=0.54, group=CONTINUATION". decision_tree: A1 SKIP(no patterns) · A2 PASS(11 studies) · A3 SKIP(no patterns this bar) · A4 SKIP · A5 PASS(advisory:calculate_size=reject, details{} ריק) · A6 SKIP(NO_SETUP) · A7 SKIP(no fire_setup).
- **footprint/current:** running✓ hydrated✓ · **bars_today=0 · buffer=0 · cumulative_delta=0 · cot=0 · amt=null** · flow null · NO_SETUP. `data_freshness: last_bar_ts=null/lag=null/fresh=false`.
- **five_min/current + /stats:** running✓ · `mode=DAY_TYPE_MODE` · **buffer=1** · `opening_type=OPEN_DRIVE` · patterns_detected=0 · setups_published=0 · last_pattern=DOUBLE_BOTTOM_EE_LONG · last_reasoning="DOUBLE_BOTTOM_EE LONG size=half: 3-bar, COT=-28562 vs AMT=-30535, location=far".
- **day_type/state:** `stage=B2 · day_type=Trend_Normal · confidence=0.38 · lock=LOCKED_LOW_CONF · opening_type=UNKNOWN · ib_width=WIDE · behavior=DEVELOPING · range_category=NORMAL · session_min=0 · vote_history=[] · profile_shape=null`.
- **gateway/status:** trades_today=0 · shadow_active=0 · daily_pnl=0 · **chop_state=FOUND** · cooldown/cluster_guard/ssv inactive.
- **readiness:** verdict=**READY** ("all checks passed"). checks: `bridge_streams_fresh ✓ (block)` · `s1_day_type_classified ✓ day_type=Trend_Normal (degrade)` · `s4_trend_not_stuck_gray ✓ trend_state=BLUE (degrade)` · `in_rth ✓`.
- **trades/recent (5):** **2 עסקאות-טריות היום** (ללא שינוי מ-#11) — id=20 S4 SHORT entry 7489.25/stop 7491.75 (risk 2.5pt)/exit 7383.25 = **$582.5/`pnl_r=233`** (16:50 IL=08:50 CT); id=22 S2 SHORT entry 7313.5/stop 7349.75/exit 7313.5 = **BE $0/0R** (19:00 IL=11:00 CT). + שישי id=13 `$66.88=26.75R`, id=12 `$20=16R`, id=10 `$230=92R`.
- **global_gates (bridge):** woodies_5min crit `ts 2026-06-10 22:40:00` ⚠️**עתידי** (lag=null) · footprint `[disabled S3_MUTE] crit=false [FRESH] 22:09:36` (נכתב עכשיו) · cumulative_delta crit `19:05:00 UTC lag 279s` (תקין <360) · volume_profile crit `19:09:36 UTC lag 3.16s` · tick_reversal_15 `[disabled] crit=false [DEAD] 5958min · 06-05 15:51` · **imbalance crit `18:30:17 UTC lag 2362s (~39דק') > 90s req` = stale-but-Present** (החמיר מ-#11) · tpo `[disabled] crit=false [DEAD] 2023-11-25` · bars_5min crit `22:05:00 IL` (חי).
- **bridge data_freshness:** `last_bar_ts=null · lag_seconds=-99021 (~-27.5h) · fresh=true · threshold=90` (I-20). **S2/S4 data_freshness:** `last_bar_ts=2026-06-09 22:05:00+03:00 (=14:05 CT) · lag=279s · fresh=true · threshold=660` (ערוץ 5דק' חי, lag אמיתי).

### תבניות-ירי — 5 שאלות

**S4 · Woodies (ZLR/TLB/TT/GB100/Vegas/Ghost/FaMir) — 7 armed / HTLB fired (=id=20 היום):**
1. **יש נתון?** כן — 11 studies present (A2 PASS), cci_14=+119.69, buffer 50.
2. **הגיוני?** כן — CCI חיובי-בינוני ⇒ trend BLUE; **engine↔board מסכימים BLUE (C-1/I-15 לא משחזר קונפליקט)**. frontend down ⇒ אין הצלבת-UI הפעם.
3. **מה חסם?** **אין active_pattern הבר** (A3 SKIP "no patterns this bar", signal=NEUTRAL) ⇒ אין setup-ירי לחסום. ב-build כל 7 = armed אך blocked על `detection.pattern_specific ; targets_stop.r_t1_gate ; stop_price ; targets ; exit_rules.ready_to_route` (החוסם המבני הקבוע — היעדר fire_setup/טבלת stop-target). HTLB=fired (id=20, 08:50 CT).
4. **צריך לחסום?** detection-await תקין (אין תבנית הבר). **החוסם המבני (targets_stop/exit_rules) לא-לגיטימי כשורש** — סימפטום של היעדר טבלת stop/target (I-3/I-13). אין setup חי ⇒ אין counterfactual.
5. **מה חסר?** טבלת stop/target פר-תבנית×day-type → fire_setup; atr_daily/yesterday-IB מה-DLL (`Y IB dll_missing`).

**S2 · Five-Min — 5 armed / 1 fired / 4 blocked:**
1. **יש נתון?** כן — buffer 1 (גבול-בר/reset), ערוץ חי (DAY_TYPE_MODE, df lag 279s), opening=OPEN_DRIVE.
2. **הגיוני?** כן — REACTIVE_L/S, INITIATIVE_L/S, BULL_FLAG armed על detection אמיתי; **BEAR_FLAG_SHORT fired** (=id=22 היום).
3. **מה חסם?** 5 armed חוסמות רק על detection (b1_sellers/b2_volume_drop/b1_expansion×2/breakout). 4 day-patterns (INV_HNS/HNS_TOP/DOUBLE_BOTTOM_EE/DOUBLE_TOP_AA) blocked על `day_type_gate.auth_table_cell ; detection.swing_*/eve_variant`. **אין `Missing: data.choppiness_ok`** (I-16 לא משחזר; chop_state=FOUND, gate OFF per standing decision).
4. **צריך לחסום?** **כן לגיטימי** — auth_table_cell×Trend_Normal הוא ה-auth-table המכוון. detection-await תקין.
5. **מה חסר?** FHB-state לא נחשף ב-endpoint (I-4). אחרת — תקין.

**S3 · Footprint (Absorption/Stacked-Imbalance/Sweep-Return/Exhaustion) — 4 blocked:**
1. **יש נתון?** **לא** — bars_today=0, buffer=0, cumulative_delta=0, flow null.
2. **הגיוני?** לא — 0 ברים ב-~5.7ש' לתוך RTH; הקובץ **כן נכתב** (gate footprint ts 22:09:36 IL = עכשיו).
3. **מה חסם?** `data.buffer_size ; data.bars_today` — ingest file→bridge→buffer שבור (I-11, אישור #33 היום).
4. **צריך לחסום?** מבחינת readiness לא — footprint crit=false (S3_MUTE), לא חוסם לוח. S3 deferred עד אחרי-LIVE.
5. **מה חסר?** נתיב ה-ingest של footprint (file→bridge-parse→buffer). מוקפא בכוונה (S3_MUTE), לא נפתר.

### סטטוס חשודים — סבב #12
- **I-1 (day_type UNKNOWN/instance-split):** 🟡 **לא חוסם, אין פיצול-3-כיווני** — state-endpoint + readiness `s1_day_type_classified ✓ Trend_Normal` + S2 auth-gate כולם Trend_Normal. **רגרסיה residual:** `opening_type` ב-state נסוג OPEN_DRIVE→**UNKNOWN** (מול five_min=OPEN_DRIVE) — פער-instance חזר; `session_min=0`+`vote_history=[]` ב-~341דק' (feed-instance — CC). frontend down ⇒ אין הצלבת-UI.
- **I-2 (A5 advisory):** 🟡 **תקין** — A5 PASS advisory:calculate_size=reject על NO_SETUP — לא חוסם.
- **I-3 (ZLR לא ירה):** 🔬 **לא נדרך הבר** — trend BLUE אך cci_14=+119.69/signal=NEUTRAL, active_patterns=[] (A3 no pattern this bar). אין setup-ZLR טרי ⇒ אין counterfactual. (ה-bottleneck המבני נשאר היעדר טבלת stop/target — ראה #10 13:13 שבו ZLR הגיע ל-A7 עם target מנוון.)
- **I-4 (S2 דריכה):** 🔬 **תקין** — 5/10 armed + 1 fired (buffer 1 גבול-בר, ערוץ חי lag 279s). FHB-state עדיין לא נחשף ב-endpoint.
- **I-5 / B-11 (board crash):** 🟡 **לא משחזר** — verdict READY, bridge_streams_fresh ✓, אין באנר OFFLINE שקרי.
- **I-11 (footprint 0 ברים):** 🔴 **אישור #33** — gate footprint נכתב עכשיו (22:09:36 IL) אך bars_today=0/buffer=0/cumulative_delta=0/flow null; ערוץ 5דק' חי (bars_5min FRESH 22:05, df lag 279s) ⇒ file→bridge→buffer שבור, עצמאי מ-I-21. מושתק S3_MUTE/crit=false.
- **I-13 (A5/sizing מפספס):** 🔴 **לא נצפה** — NO_SETUP (active_patterns=[]), A5 advisory reject בלי setup לחסום ⇒ אין ממצא-sizing לכייל.
- **I-15 / C-1 (trend conflict):** 🔬 **לא משחזר קונפליקט** — engine cci_14=+119.69/BLUE + board `s4_trend_not_stuck_gray ✓ BLUE` מסכימים. frontend down ⇒ אין הצלבת-UI היום. הצלבת Sierra (WSI/CCI גולמי) חובה.
- **I-16 (choppiness_ok missing):** 🟡 **לא משחזר** — S2 armed/fired, אין 'Missing: data.choppiness_ok' (chop_state=FOUND). מחזק I-17.
- **I-17 (restart מאפס buffers / תנודתיות-גבול-בר):** 🔬 **תומך חזק** — five_min buffer=**1** (≠62@#11) — קריסת-buffer חדה לגבול-בר/reset על ערוץ חי ⇒ תנודתיות-גבול-בר.
- **I-18 / C-4 (TZ-mix freshness):** 🟡 **נמשך + ממצא חד** — woodies_5min gate ts **עתידי** 2026-06-10 22:40 (IL מתויג +00:00, lag=null); footprint/bars_5min IL-local; cumulative_delta/volume_profile UTC תקין (19:0x). **imbalance crit `[FRESH] 0s` אך lag_s=2362s (~39דק') > 90s req = stale-but-Present** (החמיר מ-575s ב-#11). מפר Rule 4.
- **I-19 / C-5 (pattern-status hang):** 🔴→ **לא משחזר** — 101ms (200, len 88325); כל endpoints ≤47ms. **12 רצופים נקיים היום**.
- **I-20 / C-6 (lag שלילי fresh=true):** 🟡 **נמשך** — bridge `lag=-99021/fresh=true/last_bar_ts=null/threshold=90` (~-27.5h); predicate לא אוכף `|lag|≤threshold` (קשור ל-ts-עתידי woodies_5min I-18). readiness via crit-gates → READY (נכון).
- **I-21 (stall 5דק'):** 🟡 **לא משחזר** — ערוץ 5דק' חי (S2/S4 df last_bar=14:05 CT lag 279s, bars_5min FRESH 22:05 IL, S2/S4 ירו היום). אין stall.
- **I-22 / F-1 (pnl_r מנופח):** 🔴 **אישור חוזר** — id=20 S4 SHORT entry 7489.25/stop 7491.75 (risk 2.5pt)/exit 7383.25 (+106pt) ⇒ **R-אמיתי≈+42R** אך `pnl_r=233` (~5.5× ניפוח, $582.5). id=22 BE ($0/0R תקין). שורש (מ-#11/06-08 EOD): R=`pnl_usd ÷ $1.25` (ערך-טיק) במקום `÷ risk_$` פר-חוזה. חוסם ΣR-counterfactual — CC.
- **I-23 / F-2 (gateway counters):** 🟡 **אישור חוזר** — `trades_today=0/daily_pnl=0/shadow_active_count=0` בעוד **2 עסקאות היום** (id=20+id=22, סגורות). מוני-היום לא סופרים shadow fires.
- **I-24 (S5/TPO + tick_reversal מתים, מושתקים):** 🟡 **נמשך/מושתק** — tpo DEAD 2023-11-25 + tick_reversal_15 DEAD 06-05, שניהם `disabled (S3_MUTE/S5)`/crit=false ⇒ לא נספרים ב-readiness (board READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC (לא כאן)
1. **woodies cci_14=+119.69 / trend BLUE** — מול Sierra `~/SierraChart_Data/v9_export/` CCI-14/TCCI גולמי. frontend down ⇒ אין הצלבת-UI הפעם.
2. **woodies_5min gate ts עתידי 2026-06-10 22:40** — פער backend↔Sierra ts (I-18); להצליב mtime/last-bar בקובץ.
3. **imbalance lag 2362s (~39דק') אך Present** — stale-but-Present (I-18); לאכוף required-lag על Present.
4. **footprint** — קובץ נכתב (22:09:36 IL) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
5. **pnl_r id=20** — `pnl_usd ÷ $1.25` (טיק) במקום `÷ risk_$` פר-חוזה (I-22).
6. **`Y IB dll_missing`** — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-opening_type=UNKNOWN/session_min=0/vote_history=[] (I-1).

**NOT-DONE:** (1) **אין setup-ZLR טרי הבר** (signal=NEUTRAL) ⇒ אין counterfactual S4. (2) `opening_type` נסוג ל-UNKNOWN + `session_min=0`+`vote_history=[]` ב-~341דק' — feed-instance, לא אופיין שורשית (CC). (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) FHB-state לא נחשף ב-endpoint (I-4). (5) הצלבות-Sierra (1–6) הן ל-CC. (6) **frontend down** ⇒ אין הצלבת UI↔engine; צילום = board מרונדר מ-JSON (`ss_0011m5b1g`, inline בלבד). (7) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## [14:40 CT · 2026-06-09] Snapshot עמוק #13 — Cowork (~370דק' לתוך RTH, DAY_TYPE_MODE, ~19דק' לסגירה)

כל 7 endpoints 200; latency: day_type 38ms · five_min 47ms · five_min/stats 342ms · footprint 12ms · gateway 10ms · trades 50ms · woodies 80ms. **`build/pattern-status` חזר 200 (len 88418) אך ב-2898ms** — איטי-יחסית (לא hang, החזיר) — דגל-קל ל-I-19. verdict **READY** (4 checks pass). **ירו היום: S2 BEAR_FLAG_SHORT id=22 + S4 HTLB id=20** (board "S2×1 S4×1"). frontend **חי** היום ⇒ הצלבת-UI אפשרית. צילומים (inline, disk-persist לא נתמך): `ss_392018sy3` (Dashboard) · `ss_3602swst7` (Build-Status) · `ss_33690u85d` (root 404). **קריאה/תיעוד בלבד.**

**S2 · Five-Minute (REACTIVE_L/S · INITIATIVE_L/S · INV_HNS · HNS_TOP · DOUBLE_BOTTOM_EE · DOUBLE_TOP_AA · BULL_FLAG · BEAR_FLAG) — 9 armed + 1 fired:**
1. **יש נתון?** כן — df fresh, lag 39.3s, last_bar `2026-06-09 22:40:00+03:00`, buffer=11, mode DAY_TYPE_MODE, opening_type=OPEN_DRIVE, patterns_detected=0/setups=0.
2. **הגיוני?** כן — 9 armed על detection-await + **BEAR_FLAG_SHORT fired** (=id=22 היום, entry 7313.5 @ ~12:00 CT, exit BE).
3. **מה חסם?** detection-only: REACTIVE_SHORT `detection.b4_confirm`; INVERSE_HNS_LONG `detection.swing_lows_found`. **אין `Missing: data.choppiness_ok`** (chop_state=FOUND, UI "11 FOUND"); **אין auth-block** (day_type_gate satisfied). 
4. **צריך לחסום?** כן לגיטימי — detection-await תקין. אין שער-שגוי בסנאפ-שוט זה.
5. **מה חסר?** FHB-state עדיין לא נחשף ב-endpoint (I-4).

**S4 · Woodies (ZLR · TLB · TT · GB100 · Vegas · Ghost · FaMir · HFE · HTLB) — 8 armed + 1 fired:**
1. **יש נתון?** כן — df fresh, lag 39.3s. cci_14 נע בין הקריאות (-98.4 → -131.15 → -141.69), tcci -157, trend RED↔GRAY churn (גבול-בר). signal NEUTRAL בקריאה האחרונה.
2. **הגיוני?** כן — **HTLB fired** (=id=20 היום). בקריאה הראשונה **ZLR הגיע ל-active_patterns + A7** (entry 7359/stop 7369.5/group CONTINUATION, conf 0.65, size=half, failed_stages=[A7]); בקריאות הבאות נעלם (no pattern this bar) — churn גבול-בר.
3. **מה חסם?** ZLR blockers: `detection.pattern_specific · targets_stop.r_t1_gate · targets_stop.stop_price · targets_stop.targets · exit_rules.ready_to_route`; `ready_to_route=false`, `last_route.reason=not_ready_to_route`. ⇒ ה-bottleneck המבני = **היעדר טבלת stop/target** (בלי stop/T1 אמיתי `fire_setup` לא נבנה) — I-3.
4. **צריך לחסום?** ה-R:R-gate צודק כשה-target מנוון, אך זהו **סימפטום** של היעדר טבלת stop/target, לא דחייה-לגיטימית-לגופה.
5. **מה חסר?** טבלת stop/target פר-תבנית×day-type → `fire_setup` (I-3). Sierra CCI-14/TCCI גולמי להצלבה (I-15).

**S3 · Footprint (Absorption · Stacked-Imbalance · Sweep-Return · Exhaustion) — 4 blocked:**
1. **יש נתון?** **לא** — bars_processed_today=0, buffer_size=0, cumulative_delta=0, flow null, last_classification NO_SETUP.
2. **הגיוני?** לא — 0 ברים ב-~6.2ש' לתוך RTH; הקובץ **כן נכתב** (gate footprint `[disabled][FRESH] 0s · 22:40:59` IL = עכשיו).
3. **מה חסם?** `data.buffer_size ; data.bars_today` — ingest file→bridge→buffer שבור (I-11, אישור #34 היום).
4. **צריך לחסום?** מבחינת readiness לא — footprint crit=false (S3_MUTE), לא חוסם לוח. S3 deferred עד אחרי-LIVE.
5. **מה חסר?** נתיב ה-ingest של footprint (file→bridge-parse→buffer). מוקפא בכוונה (S3_MUTE), לא נפתר.

**S1 · Day Type (gate) — armed:** blockers `classification.probability_above_threshold · classification.directional_certainty · classification.zohar_rules_evaluated` (detection-await). df fresh, last 22:40 IL.

### סטטוס חשודים — סבב #13
- **I-1 (day_type split):** 🟡 **פיצול 2-כיווני חזר, לא חוסם** — state-endpoint=`Variation 0.38/B2/LOCKED_LOW_CONF/IB WIDE` + Dashboard "Variation CLASSIFIED 38%" מול **readiness `s1_day_type_classified ✓ Trend_Normal` + Build-header "day Trend_Normal"**. **שיפור:** `opening_type=OPEN_DRIVE` כעת **עקבי** (state↔five_min↔Dashboard). residual: `vote_history=[]` ב-~370דק'; `session_min` הוחזר **`[BLOCKED: Sensitive key]`** (redaction של ה-tooling — לא נקרא הסנאפ-שוט). Dashboard `Y IB dll_missing`. לא חוסם S2 (10/10 armed/fired).
- **I-2 (A5 advisory):** 🟡 **תקין** — A5 PASS `advisory:calculate_size=reject`, לא חוסם.
- **I-3 (ZLR לא ירה):** 🔬 **ZLR הגיע ל-A7 שוב** (קריאה ראשונה: entry 7359/stop 7369.5, failed A7) — חסום מבנית ב-`targets_stop.*` + `exit_rules.ready_to_route` (היעדר טבלת stop/target). בקריאות הבאות churn ל-NEUTRAL/no-pattern. אין counterfactual בר-טרי.
- **I-4 (S2 דריכה):** 🔬 **תקין** — 9 armed + 1 fired, buffer=11, ערוץ חי (lag 39.3s). FHB-state עדיין לא נחשף.
- **I-5 / B-11 (board crash):** 🟡 **לא משחזר** — verdict READY, bridge_streams_fresh ✓, אין באנר OFFLINE שקרי.
- **I-11 (footprint 0 ברים):** 🔴 **אישור #34** — gate footprint נכתב עכשיו (`[disabled][FRESH] 0s · 22:40:59` IL) אך bars_today=0/buffer=0/cumulative_delta=0/flow null; ערוץ 5דק' חי (bars_5min FRESH 22:40, lag 39.3s) ⇒ file→bridge→buffer שבור, עצמאי מ-I-21. מושתק S3_MUTE/crit=false.
- **I-13 (A5/sizing מפספס):** 🔴 **לא נצפה ירידת-sizing** — ZLR A5 size=half (לא reject); HTLB ירה. אין reject-A5 לכייל.
- **I-15 / C-1 (trend conflict):** 🔬 **לא משחזר קונפליקט** — engine RED (cci_14 -131→-141 נע) + board `s4_trend_not_stuck_gray ✓ RED` מסכימים. frontend חי: פאנל Woodies-CCI `CCIDiff -31.68 / TrendDown 1.00` מול engine cci_14 ≈-141 (skew גדול — הפאנל מציג CCIDiff לא cci_14). הצלבת Sierra חובה.
- **I-16 (choppiness_ok missing):** 🟡 **לא משחזר** — 10/10 S2 armed/fired, אין `Missing: data.choppiness_ok` (chop_state=FOUND, UI "11 FOUND"). מחזק I-17.
- **I-17 (buffer-edge volatility):** 🔬 **תומך** — five_min buffer=11; trend RED↔GRAY + ZLR armed↔gone churn בין קריאות עוקבות על אותו ערוץ-חי ⇒ תנודתיות-גבול-בר.
- **I-18 / C-4 (TZ-mix freshness):** 🟡 **נמשך + future-date שוחזר** — gate `woodies_5min` ts=**`2026-06-10 22:40:00`** (תאריך-עתיד ~+30h, marked +00:00, lag_s=null); footprint/bars_5min IL-local; cumulative_delta(64s)/volume_profile(3.2s)/**imbalance(39.2s) UTC תקין** — imbalance **בתוך הסף** הפעם (≠ stale-but-Present ב-#11/#12). board `Day Type ? stale`/`Footprint ? stale` = artifact-TZ. מפר Rule 4.
- **I-19 / C-5 (pattern-status hang):** 🔴→🟡 **לא hang אך איטי** — `build/pattern-status` חזר 200 (len 88418) ב-**2898ms** (≫ הטיפוסי <200ms של היום; ≠ hang, החזיר). שאר ה-endpoints <350ms. דגל-קל: heavy-read איטי-יחסית — לנטר.
- **I-20 / C-6 (lag שלילי fresh=true):** 🟡 **נמשך** — bridge `data_freshness.lag_seconds=-97160/fresh=true/last_bar_ts=null/threshold=90` (~-27h); predicate לא אוכף `|lag|≤threshold`. readiness via crit-gates → READY נכון.
- **I-21 (stall 5דק'):** 🟡 **לא משחזר** — ערוץ 5דק'/woodies חי (S2/S4 df last_bar 22:40 IL lag 39.3s, bars_5min FRESH, cci_14 נע). אין freeze.
- **I-22 / F-1 (pnl_r מנופח):** 🔴 **אישור חוזר על fire בן-יום** — id=20 S4 HTLB SHORT entry 7489.25/stop_init 7491.75 (risk 2.5pt=$12.50/חוזה)/exit 7383.25 (+106pt) ⇒ **R-אמיתי≈+42R** אך `pnl_r=233` / `pnl_usd=582.5` (~5.5× ניפוח). id=22 BE ($0/0R תקין). UI top-bar "SHADOW 0t $0". שורש: R=`pnl_usd ÷ $1.25` (ערך-טיק) במקום `÷ risk_$` פר-חוזה. חוסם ΣR-counterfactual — CC.
- **I-23 / F-2 (gateway counters):** 🟡 **אישור חוזר** — gateway `trades_today=0/daily_pnl=0/shadow_active_count=0` בעוד **2 עסקאות היום** (id=20+id=22, סגורות) + board "ירו היום S2×1 S4×1". מוני-היום+shadow_active_count לא מחווטים ל-shadow fires.
- **I-24 (S5/TPO + tick_reversal מתים, מושתקים):** 🟡 **נמשך/מושתק** — tpo DEAD מ-2023-11-25 + tick_reversal_15 DEAD מ-2026-06-05 15:51 (5989min), שניהם `disabled (S3_MUTE/S5)`/critical:false ⇒ לא נספרים ב-readiness (bridge_streams_fresh ✓, verdict READY). תואם החלטת-SoT.

### מקור-אמת — להצלבת CC (לא כאן)
1. **woodies cci_14=-131→-141 / trend RED** — מול Sierra `~/SierraChart_Data/v9_export/` CCI-14/TCCI גולמי. פאנל-UI מציג CCIDiff -31.68 (מדד-נגזר) — איזה הוא ה-SoT?
2. **gate `woodies_5min` ts עתידי `2026-06-10 22:40:00`** (~+30h) — חותמת שגויה, ערוץ חי (I-18); הצלב mtime/last-bar בקובץ.
3. **bridge `lag_seconds=-97160/fresh=true`** — predicate לא אוכף סף (I-20); נרמל-TZ ל-UTC בגבול + אכוף `|lag|≤threshold`.
4. **footprint** — קובץ נכתב (22:40:59 IL) אך 0 ברים ב-buffer — file→bridge-parse (I-11).
5. **pnl_r id=20** — `pnl_usd ÷ $1.25` (טיק) במקום `÷ risk_$` פר-חוזה (I-22).
6. **`Y IB dll_missing`** (Dashboard) — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-vote_history=[] + פיצול day_type (I-1).
7. **ZLR stop/target** — entry 7359/stop 7369.5 אך targets מנוונים ⇒ אין `fire_setup` (I-3); נדרשת טבלת stop/target.

**NOT-DONE:** (1) ZLR setup churn (armed→NEUTRAL בין קריאות) ⇒ אין counterfactual S4 בר-טרי. (2) `session_min` הוחזר redacted (`[BLOCKED: Sensitive key]`) ⇒ לא ניתן לאמת session_min הסנאפ-שוט; `vote_history=[]` אומת. (3) future-date ts ב-woodies_5min gate — לא אופיין שורשית (I-18). (4) `build/pattern-status` 2898ms — לא אופיין מקור-האיטיות (I-19). (5) FHB-state לא נחשף (I-4). (6) הצלבות-Sierra (1–7) הן ל-CC. (7) **אל-תיגע-בקוד נשמר** — קריאה/תיעוד בלבד.

---

## 15:08 CT — מחוץ ל-RTH, מדלג

RTH = 08:30–15:00 CT. השעה הנוכחית 15:08 CT (אחרי הסגירה). אין snapshot — דילוג לפי מפרט המשימה.
