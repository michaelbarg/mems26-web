# MEMS26 · Pattern Firing Diagnostics — 2026-06-10

בדיקה כל 30 דק' ב-RTH (08:30–15:00 CT). מקור-אמת: Sierra v9_export → bridge → API/DB.
ראה מפרט: `docs/handoff/CC_PROMPT_PATTERN_DIAGNOSTICS_2026-06-05.md` · רשימת-חשודים: `docs/reports/MEMS26_ISSUES_REGISTER.md`.

---

**[08:08 CT]** מחוץ ל-RTH, מדלג. RTH = 08:30–15:00 CT; השעה הנוכחית 08:08 CT (UTC 13:08, CDT), ~22 דק' לפני פתיחת ה-RTH. אין מסחר חי לאבחון — לא בוצעו קריאות-API, צילום-טבלה, או עדכוני-חשודים. הריצה הבאה בחלון תבצע את הבדיקה המלאה.

---

## [09:54 CT] Snapshot עמוק #1 ב-RTH — 2026-06-10 (Cowork)

**הקשר:** ~84 דק' לתוך RTH (IB locked, bar_count S1=13). `build/pattern-status` ts = `2026-06-10T14:54:17Z` (=09:54:17 CT).
**verdict = DEGRADED** (reason: `trend_state=GRAY` בלבד) — bridge_streams_fresh ✓, אין חסם-לוח שקרי. מחיר חי 7354.75 ("0.8s ago"). frontend חי. browser=MACBOOK (2 מחוברים; ריצה אוטונומית — נבחר לוקאלי, מצוין כאן).
**קריאה/תיעוד בלבד — לא שונה קוד.** צילומים: `ss_09697ipin` (Build Status), `ss_642420cbo` (Dashboard).

### ערכים גולמיים (raw)

| endpoint | ms | ערכים-מפתח |
|----------|----|-----------|
| `readiness` | — | verdict=**DEGRADED**; checks: bridge_streams_fresh ✓(block) · s1_day_type_classified ✓(degrade)="day_type=**Normal**" · s4_trend_not_stuck_gray **✗**(degrade)="trend_state=GRAY" · in_rth ✓ |
| `day_type/state` | 42 | **Variation** conf 0.48 · stage B2 · ib_width WIDE · ib_class **null** · lock PENDING · opening_type **OPEN_AUCTION_IN** · behavior DEVELOPING · range NORMAL · vote_history **[]** · session_min=**[BLOCKED: Sensitive key]** (redacted by sandbox — לא-נצפה) |
| `five_min/current`+`/stats` | 35 | buffer **73** · mode DAY_TYPE_MODE · opening_type **OPEN_AUCTION_IN** · last REACTIVE_SHORT conf 75 · running · patterns_detected **0** / setups **0** |
| `woodies/current` | 13 | active_patterns **[]** · bar_count 6 · buffer 50 · cci_14 **-147.13**→S4-panel **-161.32** (נע) · tcci -99.5/-107.35 · trend_state **GRAY** · signal NEUTRAL · swi -196/-210 · czi 14/2 · ema34 7366.8 · lsma 7393 · ready_to_route **false** · last_dir_change=TCCI crossed ABOVE CCI14→BULLISH · A1 SKIP"no patterns"·A2 PASS"11 studies"·A3 SKIP"no patterns this bar"·A4 SKIP·**A5 PASS"advisory:calculate_size=reject"**·A6 SKIP·A7 SKIP"no fire_setup" |
| `footprint/current` | 20 | bars_processed_today **0** · buffer **0** · cumulative_delta 0 · cot 0 · amt null · flow null · running · NO_SETUP |
| `gateway/status` | 26 | chop_state **FOUND** · trades_today **0** · shadow_active_count **0** · daily_pnl 0 · cooldown/cluster/ssv inactive · demo[2,4] · live[] |
| `trades/recent?limit=50` | 69 | **5 עסקאות, אחרונה 06-09** (אין 06-10): id22 BEAR_FLAG_SHORT S2 BE 0/$0 · id20 HTLB S4 WIN **pnl_r 233/$582.5** · id13 REACTIVE_SHORT 26.75/$66.88 · id12 HTLB 16/$20 · id10 BEAR_FLAG_SHORT 92/$230 |
| `key_levels` | — | today POC **7370.75**/VAH 7397.75/VAL 7363.25 · IB **7404.75/7335.25** (69.5pt WIDE, Study ID:6 live) · day_type Variation · opening OPEN_AUCTION_IN · prev(06-09) POC 7369/VAH 7454.5/VAL 7283.5/range 7491-7247/close 7390 |
| `tpo/levels`·`tpo/profile` | — | **404 Not Found** (שניהם) |
| bridge `data_freshness` | — | lag_seconds **-28065** · fresh **true** · last_bar_ts null · threshold 90 |

**bridge global_gates:** woodies_5min crit `[FRESH] ts 2026-06-10 22:40:00+00:00` lag=**null** (ts-עתידי, TZ-mix) · footprint crit:**false** `[disabled][FRESH] 17:54:15` (נכתב עכשיו, 0 ברים) · cumulative_delta crit FRESH UTC lag 258s · volume_profile crit FRESH UTC lag 1.3s · tick_reversal_15 crit:**false** `[disabled][DEAD] 7142min · 2026-06-05 15:51` · imbalance **crit:true** `[FRESH]` אך **lag 3553s (~59דק') > 90s req** (stale-but-Present) · tpo crit:**false** `[disabled][DEAD] · 2023-11-25` · bars_5min crit FRESH `17:50:00`.

**Dashboard UI:** Variation CLASSIFIED 48% · Dir MEDIUM Trade HIGH · IBH **7386.75**/IBL **7363.50** (23.3pt) · Opening OPEN_AUCTION_IN WIDE · "Y IB dll_missing" · "17 FOUND" · פאנל Woodies CCI **-189.11**/CCIDiff -25.16 · 0 trades.
**Build Status UI:** verdict DEGRADED · banner trend GRAY · chain `Day Type×stale → S3 BLOCKED → Footprint×stale → S4 BLOCKED → ✓Woodies CCI · ✓Min Patterns-5 · ✓Bridge·Streams` · header "day **Normal**" · bottom "Day Type: **Normal**" · S2 armed · "הסכמת כיוון 2 חסום" · Killzone ✗ לא-מחווט · 304m לסגירה.

### תבניות — 5 השאלות

**S2 · five_min (10 תבניות: REACTIVE_L/S · INITIATIVE_L/S · INV_HNS · HNS_TOP · DOUBLE_BOTTOM_EE · DOUBLE_TOP_AA · BULL/BEAR_FLAG)**

| שאלה | תשובה |
|------|-------|
| יש נתון? | **כן** — buffer 73, ערוץ חי (last_bar `17:50+03:00`=09:50 CT, lag 134.7s<660), mode DAY_TYPE_MODE, opening OPEN_AUCTION_IN |
| הגיוני? | **כן** — מחיר 7354.75 (0.8s ago), **10/10 תבניות status=armed**, last REACTIVE_SHORT conf 75 |
| מה חסם? | אף תבנית לא נורתה הבר — חסם=**detection-await בלבד** (Reactive Short=`detection.b1_buyers`; Initiative Long=`detection.b1_expansion`). **אין** auth-block, **אין** `Missing: data.choppiness_ok` |
| צריך לחסום? | כן — detection-await לגיטימי (אין setup על הבר); detected 0/setups 0 |
| מה חסר? | כלום ל-arming. FHB-state עדיין לא נחשף ב-endpoint (תיעוד בלבד) |

**S3 · footprint (4 תבניות: ABSORPTION · STACKED_IMBALANCE · SWEEP_RETURN · EXHAUSTION)**

| שאלה | תשובה |
|------|-------|
| יש נתון? | **לא** — bars_today=0, buffer=0, cumulative_delta=0, flow=null, data_freshness.fresh=**false** |
| הגיוני? | לא-רלוונטי (אין דאטה). gate footprint `[disabled][FRESH] 0s · 17:54:15` ⇒ הקובץ **נכתב עכשיו** אך 0 ברים נכנסו ל-buffer |
| מה חסם? | כל 4 התבניות `blocked [data.buffer_size, data.bars_today]` — Insufficient buffer (0, need ≥5) |
| צריך לחסום? | כן (אין דאטה) — אך השורש=**I-11 ingest-break** (file→bridge→buffer), לא היעדר-יצוא |
| מה חסר? | נתיב ה-ingest של footprint שבור; S3 מושתק (S3_MUTE, crit=false) ⇒ לא חוסם לוח. עצמאי מערוץ 5דק' החי. **Sierra-CC** |

**S4 · woodies (9 תבניות: ZLR · TLB · TT · GB100 · HFE · HTLB · FAMIR + CCI-HNS + Failed-ZLR)**

| שאלה | תשובה |
|------|-------|
| יש נתון? | **כן** — cci_14 נע -147.13→-161.32 (ערוץ חי), trend_state GRAY, swi -210, czi 2, ema34 7366.8, 11 studies present (A2 PASS) |
| הגיוני? | **חלקית** — cci_14≈-161 שלילי-מובהק אך trend_state=GRAY (TCCI חצה מעל CCI14 ⇒ מעבר/היפוך). **פער UI↔endpoint:** פאנל Woodies CCI=-189.11 מול endpoint -161.32 (~28pt) ⇒ **Sierra-CC** |
| מה חסם? | כל 9 התבניות **blocked**. ZLR blocker ראשון=`stage_a1.strategic_gate` (**A1 veto trend GRAY**) **לפני** detection; +detection.pattern_specific +targets_stop.r_t1_gate/stop_price/targets +exit_rules.ready_to_route. dtree: A1 SKIP, A5 PASS advisory, A7 SKIP. ready_to_route=false |
| צריך לחסום? | A1-GRAY veto **מוצדק-לפי-אפיון** (לא נכנסים ב-Woodies במגמה לא-ודאית) — **בהנחה ש-GRAY הוא ה-WSI האמיתי**. cci_14=-161 שלילי בעוד GRAY ⇒ **דרושה הצלבת Sierra WSI**. אין setup-ZLR טרי ⇒ אין counterfactual |
| מה חסר? | טבלת stop/target (כש-ZLR מגיע ל-A7 ה-targets מנוונים — לא הבר הזה). Sierra WSI=SoT ל-trend_state |

**Gates (S1=observer · S5/TPO לא-מחווט · S6=killzone):** S1 Day-Type=armed (blockers: classification.probability/directional_certainty/zohar_rules — pending sub-checks). S5/TPO=404 (מת, מושתק). Killzone לא-מחווט (לוח: "KZ ✗"). day_type **לא חוסם** S2 (10/10 armed).

### חשודים — עדכון-סטטוס (I-1…I-25)

| # | סטטוס | יש נתון? | הגיוני? | מה חסם / ממצא היום | צריך לחסום? | מה חסר / Sierra-CC |
|---|-------|----------|---------|---------------------|-------------|---------------------|
| I-1 | 🟡 | כן (Variation 0.48 B2) | כן | **לא חוסם S2** (10/10 armed). **פיצול 2-כיווני חזר:** readiness+Build-header+bottom="**Normal**" מול state+five_min+Dashboard+key_levels="**Variation**". **שיפור:** opening_type=OPEN_AUCTION_IN **עקבי** על 4 משטחים (≠06-09 UNKNOWN) | לא | vote_history=[]; **session_min לא-נצפה (redacted)** ⇒ residual לא-אומת. ראה ממצא-חדש IB-split. Sierra-CC: instance-feed Normal↔Variation, atr_daily/Y-IB ("dll_missing") |
| I-2 | ✅ תקין | — | — | A5 dtree=PASS `advisory:calculate_size=reject` — **לא חוסם**. תצוגה תקינה | — | — |
| I-3 | 🔬 | כן | — | trend GRAY ⇒ ZLR חסום `stage_a1.strategic_gate` (A1 veto) **לפני** detection — **לא armed**. active_patterns=[] | מוצדק אם GRAY אמיתי | אין setup/counterfactual. כשמגיע A7→טבלת stop/target חסרה |
| I-4 | ✅ תקין | כן | כן | S2 10/10 armed, ערוץ חי, detection-await בלבד | כן | FHB-state לא נחשף ב-endpoint |
| I-5 | 🔴→לא-משחזר | — | — | bridge_streams_fresh ✓, **אין באנר OFFLINE שקרי**. verdict DEGRADED מ-GRAY (אמיתי) | — | — |
| I-6 | 🟡 | — | — | frontend — לא נבדק לעומק (chart נטען, לא נצפתה כפילות בולטת) | — | פרומפט B-14 |
| I-7 | 🟡 | — | — | residual write-guard — read-only, לא נבדק | — | לסגור לפני LIVE |
| I-8 | 🟡 | — | — | לא נבדק (נמוך) | — | — |
| I-9 | 🔴 | — | — | ריצה **09:54 CT בתוך RTH**, gating-CT תקין | — | **EOD-after-15:00 עדיין פתוח לאימות בריצת-הסגירה** |
| I-10 | 🟡→קיים | — | — | build/pattern-status חושף patterns[]+blockers לכל S2/S3 + Woodies A1-A7 + readiness chain — עץ שקול קיים | — | — |
| I-11 | 🔴 **מאושש** | **לא** (0 ברים) | — | gate footprint נכתב עכשיו (`17:54:15`) אך bars_today=0/buffer=0/flow null. **ingest-break** file→bridge→buffer. עצמאי מערוץ 5דק' (חי). מושתק crit=false | כן (אין דאטה) | **Sierra-CC: parse/ingest** |
| I-12 | 🟡 | — | — | NO_SETUP, A5 advisory reject; אין setup חי. details{} לא נחשף | — | לחשוף reject-context ב-endpoint |
| I-13 | 🔴 | — | — | NO_SETUP (active_patterns=[]) ⇒ **אין ממצא-sizing לכייל** (S4 חסום A1 לפני detection) | — | כיול sizing מול counterfactual |
| I-14 | 🔴 | כן | כן | opening_type=OPEN_AUCTION_IN. INITIATIVE_L/S **armed** (auth FULL, אין SKIP×daytype), חוסמות על `detection.b1_expansion` בלבד. **חסם-auth נוקה** | detection לגיטימי | שרשרת opening→entry — CC |
| I-15 | 🔬 | כן | חלקית | engine GRAY + board ✗GRAY + Dashboard NEUT — **מסכימים, אין קונפליקט מנוע↔לוח**. **פער UI↔endpoint CCI ~28pt** (-189.11 מול -161.32) | — | **הצלבת Sierra CCI/WSI חובה** |
| I-16 | 🔴→לא-משחזר | — | — | 10/10 S2 armed, **אין** `Missing: data.choppiness_ok` (chop_state=FOUND, UI "17 FOUND") | — | מחזק I-17 (תנודתיות-גבול-בר) |
| I-17 | 🔬 | — | — | five_min buffer=73 (≠ערכים קודמים), 10/10 armed, ערוץ חי. תומך בתנודתיות-גבול-בר (אין סימן restart) | — | — |
| I-18 | 🟡 **נמשך+חד** | — | לא | woodies_5min gate ts **עתידי 22:40:00** מתויג +00:00/lag=null; footprint/bars_5min IL-local +00:00; cum_delta/vol_profile UTC תקין. **imbalance crit:true [FRESH] אך lag 3553s (~59דק') > 90s = stale-but-Present** | — (מפר Rule 4) | **Sierra-CC: נרמול-TZ + אכיפת-סף + ts-עתידי woodies_5min** |
| I-19 | 🔴→לא-משחזר | — | — | build/pattern-status=**104ms** (200, len 89996), שאר endpoints 13-69ms. **נקי, אין hang** | — | — |
| I-20 | 🟡 נמשך | — | לא | bridge `lag_seconds=-28065/fresh=true/last_bar_ts=null/threshold=90` (~-7.8h). predicate לא אוכף סף על lag שלילי/null | — | readiness via crit-gates → DEGRADED נכון. קשור ts-עתידי woodies_5min (I-18) |
| I-21 | 🟡→לא-משחזר | כן | כן | ערוץ 5דק' **חי** — S2/S4 last_bar `17:50+03:00` lag 134.7s, cci_14 נע (לא קפוא), bars_5min/woodies_5min FRESH. tick_reversal_15 DEAD מ-06-05 אך disabled/crit=false (לא חוסם). **אין stall** | — | שורש freeze 06-05 11:35→13:15 עדיין ל-CC |
| I-22 | 🔴 נמשך | — | לא | **אין עסקה-טרייה 06-10**. ערכי-עבר: id20 HTLB pnl_r=233/$582.5 (risk 2.5pt/+106pt ⇒ R-אמיתי≈+42R, ~5.5× ניפוח). R=pnl_usd÷$1.25(טיק) במקום ÷risk_$ | — | חוסם ΣR-counterfactual. CC |
| I-23 | 🟡 | — | — | trades_today=0/shadow_active_count=0/daily_pnl=0 — **נכון היום** (0 עסקאות) | — | לא-ניתן-לשחזר בלי עסקה-טרייה |
| I-24 | 🟡 נמשך/מושתק | כן | כן | key_levels POC=7370.75 (Sierra Study ID:3 live) תקין. **tpo/levels+tpo/profile=404** (S5 מת). tpo+tick_reversal_15 disabled/crit=false ⇒ לא נספרים ב-readiness | — | תואם החלטת-SoT. CC: לאשר כוונה |
| I-25 | 🟢 | — | — | השתמשתי `limit=50` (≤100) — עבד (5 עסקאות) | — | תיקון-מסמך SKILL.md ל-limit=100 פתוח |

### ⭐ ממצא חדש — IB source-split (קשור I-1)
levels-strip/`key_levels` IB=**7404.75/7335.25** (69.5pt WIDE, **Sierra Study ID:6** live) מול S1-day-type/Dashboard-panel IB=**7386.75/7363.50** (23.3pt, source `sierra_tpo`). **שני IB שונים מוצגים בו-זמנית** (~46pt פער-רוחב), שניהם מתויגים WIDE; ה-classifier של day_type משתמש ב-IB הצר (23.3pt). זהו פער-מקור backend↔Sierra. **Sierra-CC: איזה IB קנוני מ-v9_export; ליישר Study ID:6 ↔ day-type IB feed** (IB width מזין את `classify_ib_width_atr`).

### הצלבות-Sierra v9_export (ל-CC, לא כאן)
1. trend_state=GRAY מול cci_14=-161 שלילי — WSI גולמי (I-15/I-3). 2. פער UI↔endpoint CCI ~28pt (I-15). 3. ts-עתידי woodies_5min `22:40` + TZ-mix (I-18). 4. imbalance lag 59min stale-but-Present crit:true (I-18). 5. footprint ingest-break file→bridge→buffer (I-11). 6. IB source-split Study ID:6 ↔ day-type (חדש). 7. pnl_r formula ÷$1.25 (I-22).

### NOT-DONE / מגבלות
- **session_min לא-נצפה** — ה-sandbox החזיר `[BLOCKED: Sensitive key]` עבור session_min/session_date/rtb_session ⇒ residual ה-session_min=0 של I-1 **לא-אומת** בסנאפ-שוט זה.
- **אין עסקה-טרייה 06-10** ⇒ I-22/I-23 לא-ניתנים-לשחזור-חי (ערכי-עבר בלבד).
- frontend **חי** (≠חלק מ-06-09) ⇒ הצלבת-UI בוצעה (Dashboard + Build Status).
- כל הצלבת-Sierra v9_export = CC (read-only כאן).
- screenshots: `ss_09697ipin` (Build Status / decision-tree), `ss_642420cbo` (Dashboard).
