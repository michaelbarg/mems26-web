# ניתוח עסקאות-שלא-בוצעו · 2026-06-29 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:20 CT** (אחרי סגירת RTH 15:00, `TZ=America/Chicago`) ✓. ריצה אוטונומית — Michael לא נוכח. **לא שונה קוד.**

> 🟢 **ממצא-העל — feed נקי היום (אין I-47, אין I-45).** חלון 06-25(חושך)/06-26(פאנטום) נסגר: `woodies[aft]` **≠** `bars5min[morn−3h]` ב-**0/12 ברים** (13:05→7495.25 מול 10:05→7461.25 … אין-התאמה), woodies `age_s=1.7 stale:false`, bars5min מכסה RTH-מלא 08:30→14:55. ⇒ **הניתוח היום על דאטה-קנונית-נקייה-מאומתת** (ראשון מאז 06-24).
>
> 🔴 **הממצא-המהותי — היפוך-כיוון (I-41) עלה למפלס-עלות-ממשי:** יום-**OPEN_DRIVE עולה** (open 7457→close 7497, **+39.75נק'**, high 7505, low 7409; trend=**BLUE** כל-הסשן, **0 ברי-RED**). המערכת ירתה **4 עסקאות — כולן SHORT — כולן −1R** (ΣPnL **−$513.75**), בעוד **8 דגלי-ZLR-UP** (תואמי-מגמה) **לא-ירו כלל** (S4 `fired_today=0`). **0 LONG נורו ביום של +40נק'.**

**מה אמיתי היום:** כל-הסשן 08:30→15:20 CT (אין חלון-פאנטום/חושך). מבנה-בוקר: פופ-פתיחה 7457→7489 (08:30-08:50) → **selloff חד ל-7409** (08:55-09:15) → **היפוך-V ל-מעלה מ-09:25** → grind-up ל-7505. `opening_type=OPEN_DRIVE` · `ib_width=WIDE`. **day_type:** endpoint `/day_type/state`=`Variation` conf**0.18** (`LOCKED_LOW_CONF`), **אך זהו ה-wrapper-המת (I-44)** — ה-stamp-בכניסה היה `Trend_Normal` (ראה sibling-EOD למטה). live_price-בעת-אודיט **7498.25**.

> 🔁 **הצלבה ל-sibling-EOD (15:12 CT, אותו-יום, `PATTERN_EOD_2026-06-29.md`):** מאשש-עצמאית את ה-core — feed-נקי (I-47 לא-שוחזר), 4-שורט-באשכול-בשפל-7409, LONG-תואם-מגמה-הוחמץ, I-31 S2=5↔DB=4. **הבדלי-עידון:** (א) ה-sibling רושם את התבניות כ-**INITIATIVE_SHORT** (`_detect_initiative`) + day_type-stamp=**Trend_Normal** — מאומץ כאן. (ב) ה-sibling מעריך LONG-מוחמץ **+8R** (כולל היפוך-הבוקר 7409→7505, גלוי-ל-bars5min); הערכת-ה-ZLR-שלי **+2R** מכסה רק את החלק ש-**woodies זיהה** (>11:15, אחרי-העיוורון) ⇒ **woodies-morning-blind מקטין את ספירתי**; שתיהן נכונות מזוויות-שונות. (ג) ה-sibling מאחד I-48/I-23 — **כל-המונים=0** (cooldown/cluster_guard/ssv/gateway) ⇒ **כל-מפסקי-הזרם inert** (שורש עמוק-מ-הניואנס-שלי "entries-קדמו-ל-stops"). (ד) ה-sibling פתח **I-50** (אשכול-שורט-נגד-מגמה) = המסגור-שלי כ-I-41.

## מקורות-אמת + כיסוי (הצלבה ל-CC) — **מקור-CCI = Sierra**

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart?limit=80` | **11:15→15:20 (50 ברים)** · בוקר<11:15 **חסר** | `sierra_woodies_5min_json` v9.4.5-wc-fix · `age_s=1.7 stale:false` · 🟢 **לא-פאנטום** (הצלבת `woodies[aft]≠bars5min[morn−3h]` 0/12). trend=BLUE/GRAY בלבד (אין RED). **woodies-morning-blind (<11:15) נמשך** — מבני, חוסם זיהוי-CCI לבוקר + אימות-benchmark לבוקר. |
| `/api/v9/chart/bars5min?limit=80` | **08:30→14:55 (78 ברי-RTH)** | TZ=+03:00(IL). מכסה RTH-מלא. שימש ל-replay (H/L). 🟢 אין self-dup (13:05=7495.25≠10:05=7461.25). |
| `/api/v9/trades/recent?limit=100` | **היום: 4 (id256–259)** | רצף נקי. כל-4 S2 SHORT, כל-4 STOP −1R. `limit=200`→422 (cap=100, I-25). |
| `/api/v9/build/pattern-status` | live post-close | `session_date=2026-06-29` · `errors=[]` · `readiness=READY`. fired: **S2=5** מול DB **4** ⇒ **I-31 (ספירה-פנטומית) חוזר** (+1). S4=0 · S1=0 · Bridge mode=LIVE. ⚠️ pattern/global_gates/interpretations **ריקים פוסט-קלוז** ⇒ אין reject_reason היסטורי לברי-RTH (כמו תמיד). **שים-לב:** הנתיב הוא `build/` ולא `build_status/` (ה-SKILL מפנה לנתיב-404; תיקון-מסמך). |
| `/api/v9/missed-trades` | **ריק (count=0)** | אין candidate-list / אין reject היסטורי (`missed_trade_detector.py` לא-מאוכלס — נמשך). |
| `/api/v9/day_type/state` | post-close | `Variation` conf=0.18 · `OPEN_DRIVE` · `WIDE` · `B2` · `vote_history=[]`. readiness-check: `s1_day_type_classified=Variation` · `s4_trend_not_stuck_gray=BLUE` · `bridge_streams_fresh=false (dead: bars_5min)` (info, פוסט-קלוז) · `in_rth=false`. |

## 🔴 4 ירִיות (ground-truth מ-`v9_trades`) — **כולן SHORT, כולן −1R, על דאטה-נקייה**

| זמן(CT) | id | תבנית | מע' | dir | entry | stop(risk) | תוצאה | $ / R | הערה |
|---|---|---|---|---|---|---|---|---|---|
| 09:15 | 256 | INITIATIVE_SHORT | S2 | SHORT | 7435 | 7443.25 (8.25) | STOP −1R (09:25) | **−$123.75** | שורט ב-low-ה-selloff (7415-7435) ⊥ ל-היפוך 09:25. 3 חוזים. |
| 09:15 | 257 | INITIATIVE_SHORT | S2 | SHORT | 7435 | 7443.25 (8.25) | STOP −1R (09:27) | **−$123.75** | כפילות-קרובה ל-256 (אותו entry/stop). |
| 09:20 | 258 | INITIATIVE_SHORT | S2 | SHORT | 7421 | 7429.25 (8.25) | STOP −1R (09:25) | **−$123.75** | entry בקרקעית-ממש (7409 ב-09:15) → reversal. = benchmark slot-3 (ראה למטה). |
| 09:24 | 259 | INITIATIVE_SHORT | S2 | SHORT | 7425.75 | 7435.25 (9.5) | STOP −1R (09:25) | **−$142.50** | ה-fire-האחרון (last_fire 09:24); 09:25 ריפ ל-7450. |

**פילוח:** 4 ירִיות · **4/4 STOP −1R** · ΣPnL **−$513.75** · ΣR **−4R**. כל-4 SHORT, כל-4 בחלון **09:15-09:24** (9 דק'), כולן **שורט-את-הקרקעית** של ה-selloff בדיוק לפני היפוך-09:25. כל-4 `blocked_by=null`. כולן 3-חוזים → **I-34 (sizing→PnL) שוב לא-מובחן.**

## טבלת setups-שלא-בוצעו — **חלונות-אמת (כל הסשן)**

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay-אמת) | gate / מה-קרה | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **11:40** | **ZLR-UP** (trend-cont) | S4 | ✅ `zlr_detected=UP` BLUE cci27 | 7475.5 | 7470 (5.5) | 7481/7486.5 | **+2R** (T2@12:10; MFE +17.25=+3.1R) | 🔴 **S4 `fired_today=0`** — זוהה ולא-ירה. gate-מדויק לא-חשוף פוסט-קלוז (pattern-array ריק) → הצלבת-CC. | I-41 / I-13/I-15? |
| 11:50 / 12:00 | ZLR-UP (המשך) | S4 | ✅ ×2 | — | — | — | (חלק מ-leg-11:40) | המשך-אותו-leg (7479→7491). לא-נספר-כפול. | — |
| **12:50** | **ZLR-UP** | S4 | ✅ `zlr=UP` BLUE cci97 | 7495.75 | 7491 (4.75) | 7500.5/7505.25 | **+1R** (T1@13:40; MFE +9.25) | 🔴 **S4 `fired_today=0`** — זוהה ולא-ירה. | I-41 / S4-mute |
| 13:00 / 13:05 | ZLR-UP (המשך) | S4 | ✅ ×2 | — | — | — | (חלק מ-leg-12:50) | המשך. | — |
| **14:05** | **ZLR-UP** | S4 | ✅ `zlr=UP` BLUE cci36 | 7497.5 | 7494.5 (3) | 7500.5/7503.5 | **−1R** (stop@14:15; MFE +0.25) | 🔴 S4 לא-ירה — **הפעם דילוג-מזל** (היה מפסיד). | — |
| 14:20 | ZLR-UP | S4 | ✅ | — | — | — | (אזור-ה-high 7505; chop) | סמוך-לפסגה. | — |
| 12:20→13:10 | **HFE-DOWN** ×7 | S4 | ✅ `hfe_detected=DOWN` | — | — | — | **שלילי** (DOWN ב-BLUE) | **HFE_DISABLED (by-design)** + נגד-מגמה. **דילוג-נכון.** | — |

**ΣR-נגד (פספוס-אמת, deduped) = +2R** (11:40 +2R · 12:50 +1R · 14:05 −1R). **2 setups-איכות-רווחיים פוספסו** (11:40, 12:50) — שניהם LONG תואמי-מגמה ש-S4 זיהה (`zlr_detected=UP`) ולא-ירה.
⇒ **פער-ההזדמנות היום ≈ 6R:** המערכת מימשה **−4R** בצד-השגוי (SHORT), בעוד **+2R** היו זמינים בצד-הנכון (LONG תואם-OPEN_DRIVE). **זה לא "אין-setup" — זה setup-תקף-שזוהה-ולא-ירה + ירִיות-נגד-המגמה.**

## 🎯 BENCHMARK — 5 הסלוטים של Michael (06-05 יום-יורד) מול היום (OPEN_DRIVE עולה)

ה-benchmark הוא template **יום-יורד** (4/5 SHORT). היום **עולה** ⇒ הסלוטים מתהפכים מבנית. **חריג:** סלוט-3 (9:20 SHORT) **ירה בפועל היום** — אך הפסיד (שורט-את-הקרקעית).

| # | סלוט(CT) | סוג(benchmark) | מה קרה (אמת היום) | ירה? | הערה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2/FHB) | 08:35 סמוך-לשיא-הפתיחה (c7471, אחרי 7489) | ❌ | אין-היפוך; טרם-החל ה-selloff. **דילוג-נכון.** |
| 2 | 9:00–9:05 | **LONG טקטי** | 09:00-09:05 **באמצע ה-selloff** (c7449→7439, יורד ל-7409) | ❌ | **replay: LONG@09:05 → STOP −1R @09:10** (MFE +3). **אי-התאמה היום** (down-context ⊥ benchmark-up). |
| 3 | 9:20 | SHORT | 09:20 בקרקעית (7421) לפני היפוך-09:25 | ✅ **ירה (id258)** | **הסלוט-היחיד-שירה.** SHORT@09:20 → **STOP −1R.** התאמת-תזמון+כיוון, אך timing-בקרקעית → הופסד. |
| 4 | 9:35 | SHORT | 09:35 בהתאוששות (c7460, עולה) | ❌ | מבנה-הפוך (עולה). |
| 5 | 10:00 | SHORT | 10:00 דשדוש (~7463) | ❌ | אין-leg-המשך. |

**שורת-benchmark: K/5 = 1/5 ירו בזמן-ה-benchmark** (סלוט-3 SHORT @09:20, id258) — **אך 0/5 רווחיים.** סלוט-3 ירה-בכיוון-הנכון-של-ה-template אך נכשל כי **היום עולה** (היפוך-V מ-09:25). סלוטים 1/2/4/5 לא-ירו (אי-התאמה down↔up). **slot-2 (LONG) — היחיד שתואם-כיוון לעלייה-של-היום — היה מפסיד גם הוא** (9:05=אמצע-selloff). ⇒ **ה-benchmark תלוי-day-type; ביום-עולה הוא לא-מודד-edge.**

## פירוק לפי gate

| gate | #setups | סטטוס |
|---|---|---|
| **🔴 I-41 — היפוך-כיוון (4/4 SHORT, 0 LONG)** | 4 ירִיות + 3 ZLR-UP-פוספסו | **החוסם-המוביל היום.** ביום +40נק' עולה: 0 LONG נורו, 8 ZLR-UP זוהו-ולא-ירו, 4 SHORT נורו-ונכשלו. **מתחזק** (כמו 06-22 19/19-SHORT). חוסם-edge. **→ Michael/CC: למה detector-asymmetry / bias-מבני.** |
| **🔴 S4 `fired_today=0` (ZLR→fire מנותק)** | 8 ZLR-UP | S4 זיהה 8 ZLR-UP (`zlr_detected=UP`) BLUE אך ירה **0**. mode=null. ⇒ או S4-mute או שרשרת-ZLR→fire-שבורה (קרוב ל-I-14 opening→entry). **gate-מדויק לא-חשוף פוסט-קלוז** ⇒ **דורש הצלבת-CC חיה** (האם A1/I-15 · sizing-aux<2/I-13 · day_type-Variation-low-conf-0.18 גוזרים). |
| **🟡 I-31 — ספירה-פנטומית** | S2 | pattern-status S2=**5** מול DB=**4** (+1). 🟠 CC: `SELECT firing_system,COUNT(*) FROM v9_trades WHERE date=today GROUP BY 1` (צפוי S2=4/S4=0). |
| **🔴 I-48/I-23 — כל-מפסקי-הזרם inert** | id256-259 | 4 stop-outs ב-9 דק', **0 גייטים נדרכו** (sibling-EOD: `cooldown.consecutive_stops=0 · cluster_guard.recent_attempts=0 · ssv.recent_outcomes=0 · gateway.{trades_today,daily_pnl,consecutive_losses}=0`). **שורש: המונים לא-קוראים shadow/demo-fills** ⇒ כל-שכבת-ההגנה מתה. (הניואנס-שלי "entries-קדמו-ל-stops" משני — גם אילו-נרשמו, המונים=0.) **ב-LIVE = אין-מפסק-זרם.** 🟠 CC: תיקון-מקור-אחד (counters↔fill-event) + rapid-fire-burst-guard. |
| **⚫ woodies-morning-blind (<11:15)** | בוקר | חוסם זיהוי-CCI/ZLR לבוקר (08:30-11:10) + אימות-benchmark לבוקר. מבני, חוזר. ה-4-שורטים (09:15-09:24) בחלון-העיוור-של-woodies (S2 על bars5min). |
| **HFE_DISABLED (by-design)** | 7 HFE-DOWN | לא-ירו (מנוטרל) + נגד-מגמה. **דילוג-נכון.** |
| **⚪ גייטי-chop (מושבתים, standing 06-08)** | — | OFF (S2 `choppiness_ok` + Layer-0). **לא-רלוונטי כחוסם היום. אין המלצה להפעיל — Michael בלבד. תצפית-בלבד.** |
| **🟢 I-47 (שכפול-3h) — לא-שוחזר** | 0 | feed נקי (הצלבה 0/12). 🟢 **אם ה-promoter-fix תוקן — אומת היום.** |
| missed-endpoint | 0 | 🟢/⚪ ריק (count=0) — detector לא-מאוכלס, נמשך. |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🟢 I-47 (שכפול-3h בקנוני) — לא-שוחזר היום.** הצלבה תוכניתית `woodies[aft]≠bars5min[morn−3h]` **0/12 ברים** (Rule 2/5). ⇒ הרגרסיה של 06-26 **לא-נוכחת** ב-06-29. **אל-תסמן closed** עד-שורש-CC מאושר (אותו נתיב-promoter), אך **התצפית חיובית** — ראשון מאז 06-24 עם feed-נקי-מאומת.
- **🔴 I-41 (היפוך-כיוון) — מתחזק, החוסם-המוביל.** 4/4 SHORT + 0 LONG ביום-עולה-+40נק'; 8 ZLR-UP-תואמי-מגמה זוהו-ולא-ירו. ΣR-מומש −4R בצד-שגוי מול +2R-זמין בצד-נכון. **→ D25 (CC-audit→Michael):** detector-asymmetry או bias-מבני (day_type/opening). **חוסם-edge ל-LIVE.**
- **🔴 S4-mute (ZLR→fire) — חדש-בולט.** S4 `fired_today=0` מול 8 ZLR-UP. צריך-אבחון-חי: האם S4 ירה ZLR-UP אי-פעם לאחרונה (06-26 S4=4 ⇒ S4 *כן* ירה אז) — ומה-שונה היום (day_type=Variation-conf-0.18? trend-just-flipped? location-gate?). 🟠 CC חי-בלבד (post-close ריק).
- **🟡 I-31 (ספירה-פנטומית) — חוזר.** S2=5↔DB=4. 🟠 CC count-query.
- **🟡 I-48 (cooldown) — ניואנס היום.** 4-stops-רצופים, אך entries קדמו-ל-stops ⇒ 2-stop-cooldown לא-ישים-מבנית; הסיכון-האמת = burst של 4-שורט-ב-9דק'. 🟠 CC: rapid-fire-guard בנוסף-ל-consecutive-stops.
- **🟢 I-25 (cap=100) — נמשך-מינורי.** `trades?limit=200`→422. תיקון-מסמך ל-`limit≤100` + **נתיב pattern-status הנכון = `/api/v9/build/` (לא `build_status/`)**.
- **⚪ הערת-מערכת:** גייטי-chop מושבתים (standing). **אין המלצה להפעיל — Michael בלבד. לא שונה קוד.**

## נטיפיקציה ל-Michael
**🟢 feed נקי היום (אין I-47/I-45) — ראשון מאז 06-24.** הצלבה `woodies[aft]≠bars5min[morn−3h]` 0/12; woodies fresh (age 1.7s); RTH-מלא 08:30→14:55.
**🔴 אבל היום חשף את I-41 בעלות-ממשית:** יום-**OPEN_DRIVE עולה (+39.75נק', trend BLUE, 0 ברי-RED)**, והמערכת ירתה **4 עסקאות — כולן SHORT — כולן −1R (−$513.75)**, ששורטו את **קרקעית-ה-selloff (7409)** בדיוק לפני היפוך-09:25. במקביל **8 דגלי-ZLR-UP תואמי-מגמה לא-ירו כלל** (S4 `fired_today=0`). **0 LONG נורו ביום-של-עלייה.**
**setups פוספסו (זוהו-ולא-ירו):** **3 ZLR-UP longs** — replay **+2R** (11:40 **+2R**, 12:50 **+1R**, 14:05 −1R). **ΣR-נגד=+2R; פער-הזדמנות-יומי ≈ 6R** (−4R-מומש-שגוי מול +2R-זמין-נכון).
**benchmark K/5=1/5** — רק slot-3 (9:20 SHORT, id258) ירה-בזמן-הסלוט, **אך הפסיד** (היום עולה ⊥ template-יורד); slot-2 (LONG) היה מפסיד גם הוא (9:05=אמצע-selloff). **0/5 רווחיים.**
**🟠 דגלי-CC (קדימויות, חי-בלבד — post-close ריק):** (1) **I-41/S4-mute** — למה 8 ZLR-UP-BLUE לא-ירו + 4-SHORT-נגד-OPEN_DRIVE-כן (detector-asymmetry? day_type-Variation-conf-0.18? location/A1-gate?) — **חוסם-edge**; (2) **I-31** count S2=5↔DB=4; (3) **I-48** rapid-fire-burst (4-שורט-9דק'); (4) **I-47-שורש** — אשר-תוקן (אומת-נקי היום). גייטי-chop מושבתים (standing, **לא-להפעיל**). **לא שונה קוד.**

---
*נוצר אוטונומית ע"י Cowork (15:20 CT, 2026-06-29). מאומת-תוכניתית (Rule 2/5): feed-נקי `woodies[aft]≠bars5min[morn−3h]` 0/12 · day open7457.25→close7497 (+39.75) high7505 low7409 range96 · trend BLUE/GRAY (0 RED) · day_type=Variation conf0.18 OPEN_DRIVE · trades n=4 (id256-259, 4/4 S2 SHORT, 4/4 STOP −1R, ΣPnL−$513.75, 3-contracts-each) · S2 fired=5↔DB=4 (I-31) · S4 fired=0 מול 8 ZLR-UP (זוהו-ולא-ירו) · missed-endpoint count=0 · replay-deduped ZLR-UP: 11:40 T2+2R/12:50 T1+1R/14:05 stop−1R ⇒ ΣR+2R · benchmark K/5=1/5-ירה-0/5-רווחי (slot-3 short id258 stopped; slot-2 long replay −1R). TZ: woodies=UTC, bars5min/trades=+03:00(IL). **לא שונה קוד.***
