# ניתוח עסקאות-שלא-בוצעו · 2026-07-01 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:20 CT** (אחרי סגירת RTH 15:00, `TZ=America/Chicago`) ✓. ריצה אוטונומית — Michael לא נוכח. **לא שונה קוד.**

> 🔁 **הצלבה ל-sibling-EOD (15:12 CT, אותו-יום, `PATTERN_EOD_2026-07-01.md` + register §07-01):** ה-sibling כיסה את **צד-העסקאות-שירו** (11 עסקאות, execution-layer). **הדוח הזה משלים את הצד-החסר:** ה-**setups שזוהו-ולא-נותבו** (בעיקר 15 ZLR-DOWN). מספרי-I מיושרים ל-sibling: **I-54** (short-targets רחוקים/give-back) · **I-53** (CVD ts-cast — לא-קשור-כאן) · **I-44/I-51** (day_type-source + `DAYTYPE_POSITION_GATE=0`). **I-31 = נקי (11==11)** per ה-sibling — לא מסמן phantom.

> 🟢 **ממצא-העל #1 — יום פעיל, לא-שקט (היפוך מ-06-29/06-30).** המערכת ירתה **11 עסקאות** (S4=6 · S2=5, ids 260–270, 09:03→13:05 CT), **בשני-הכיוונים** — מול **0** ב-06-29/06-30. **feed-נקי יום-שלישי-רצוף** (overlap מדויק: `bars5min[11:15]c7575.75 == woodies[11:15]cl7575.75`, וכן 11:20/12:00/13:00/14:30 — אין I-40 source-split).
>
> 🔴 **ממצא-העל #2 — סלקטיביות-כיוונית הפוכה בצד-אחה"צ-היורד (שני-מנגנונים).** יום-**היפוך**: בוקר OPEN_DRIVE-**עולה** (7506@08:35 → 7579@11:20, +73נק'), אחה"צ **סל-אוף אדום** (7579→7532, woodies RED 37/50). **(א)** שער-המשפחה **כבוי** היום (`DAYTYPE_POSITION_GATE=0`, לוַלידציה per §07-01) → **2 LONG-נגד-מגמה עברו** (FaMir 12:20 · VEGAS 13:05, **−1R כ"א**) = **under-block** [I-44/I-51]. **(ב)** במקביל **כל 15 ה-ZLR-DOWN המשך-מגמה נחסמו** ב-`ready_to_route=False` (S4 A-layer — **שער אחר**, לא המשפחה) → **+3R שורטים-שפוספסו**. ⇒ **מנגנון-אחד שיחרר לונגים-רעים, מנגנון-שני חסם שורטים-טובים.** swing ≈ **+5R**.
>
> 🟢 **ממצא-העל #3 — endpoint `/api/v9/missed-trades` מאוכלס לראשונה** (50 candidates ZLR-SHORT `ready_to_route=False`) — היה `count=0` רצוף מ-06-08 עד 06-30. הגלאי חי; אך ה-candidates **חסרי `hypothetical_r`** (null) ומשוכפלים (50≈זהים, לא-deduped) → צריך dedup+R-fill.

## מקורות-אמת + כיסוי (הצלבה ל-CC) — **מקור-CCI = Sierra**

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/chart/bars5min?limit=80` | **08:30→14:55 (78 ברי-RTH)** | TZ=+03:00(IL,−8→CT). RTH-מלא. 🟢 overlap מדויק מול woodies (11:15/11:20/12:00/13:00/14:30 close-match). low 7506@08:35 · high 7579@11:20. |
| `/api/v9/woodies/chart?limit=80` | **11:15→15:20 (50 ברים)** | `sierra_woodies_5min_json`, TZ=UTC(−5→CT), fresh. trend אחה"צ **RED 37 / GRAY 9 / BLUE 4**. ZLR-DOWN×15 · ZLR-UP×1 · HFE-UP×12. ⚠️ חלון-endpoint <11:15 חסר — **מגבלת-audit, לא עיוורון-detector** (ZLR-LONG ירה 09:03 CT). |
| `/api/v9/trades/recent?limit=100` | **היום: 11** (ids 260–270) | ground-truth v9_trades. S4=6 (260,261,266,267,269,270) · S2=5 (262,263,264,265,268). `limit=200`→422 (cap=100, I-25). ⚠️ `pnl_r` פסול (I-22) → R מ-replay בלבד. |
| `/api/v9/build/pattern-status` | live post-close | `readiness=READY` · `errors=[]` · Variation · OPEN_DRIVE · s4_trend=RED(בר-אחרון). S2-patterns שלא-ירו = `blocked: Missing data.mode_context` (**benign — I-52**). |
| `/api/v9/missed-trades` | **50 candidates** | 🟢 **מאוכלס לראשונה!** כולם ZLR-SHORT `ready_to_route=False`, entry 7548–7551, ts~14:42–14:45. `hypothetical_r=null` + לא-deduped. |
| `/api/v9/day_type/state` | post-close | Variation · OPEN_DRIVE · stage B2 · conf 0.18 (LOCKED_LOW_CONF) · IB 7506–7553.75 WIDE. |

## מבנה-היום (RTH, מאומת bars5min + woodies)

open **7508.75@08:30** → **שפל-יום 7506@08:35** → **OPEN_DRIVE-עולה** ל-**שיא-יום 7579@11:20** (+73נק' מהשפל) → **היפוך + סל-אוף אדום** (woodies RED-דומיננטי 11:20→) → close-b5 **7542@14:55** → woodies-אחרון **7532.75@15:20**. טווח 73נק', נטו ~+10נק' — **Variation (up-drive→fade).** `opening_type=OPEN_DRIVE` · IB 7506–7553.75.

## עסקאות-שירו היום (הקשר — **לא** פוספסו; ground-truth v9_trades)

| id | זמן(CT) | תבנית | מער' | כיוון | entry | תוצאה | הערה |
|---|---|---|---|---|---|---|---|
| 260/261 | 09:03 | ZLR | S4 | LONG | 7537 | **WIN** (261 T3_HIT demo +$71; 260 +T1) | תפס OPEN_DRIVE-עולה ✅ · **detector-בוקר-חי** |
| 262/263 | 09:15/09:20 | INITIATIVE_LONG | S2 | LONG | 7549.5/7550.75 | −1R כ"א | נעצרו ב-pullback רדוד ואז ראלי המשיך (I-55 watch) |
| 264 | 10:20 | BULL_FLAG_LONG | S2 | LONG | 7568.75 | **WIN** (T1→BE) | המשך-ראלי ✅ |
| 265 | 10:35 | REACTIVE_SHORT | S2 | SHORT | 7570.75 | BE (manual) | שורט-מוקדם סמוך-לשיא |
| 266/267 | 11:30 | HTLB | S4 | SHORT | 7574.5 | **266 WIN +3.33R** · 267 EOD_MANUAL **0** | תפס את ה-**שיא** ✅ — 267 החזיר MFE +31.5→0 (**I-54**) |
| 268 | 11:40 | REACTIVE_SHORT | S2 | SHORT | 7570 | EOD_MANUAL **0** | MFE +27→0 (**I-54** give-back) |
| 269 | 12:20 | FaMir | S4 | **LONG** | 7565 | **−1R** | 🔴 לונג-נגד-מגמה בסל-אוף (gate-OFF עבר, I-44/I-51) |
| 270 | 13:05 | VEGAS | S4 | **LONG** | 7561 | **−1R** | 🔴 לונג-נגד-מגמה בסל-אוף (gate-OFF עבר, I-44/I-51) |

## טבלת setups-שלא-בוצעו — lookback מתגלגל 6-ברים (חלון woodies 11:15→15:20)

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay-אמת) | gate-שחסם | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **12:25** (leg-A) | **ZLR-DOWN** המשך | S4 | ✅ `zlr=DOWN` RED cci−24 | 7564 | 7568.75 (4.75) | 7559.25/— | **+1R** (T1@12:40; MFE +4.75) | 🔴 **`ready_to_route=False`** — זוהה ולא-נותב | ready_to_route |
| **13:25** (leg-B) | **ZLR-DOWN** המשך | S4 | ✅ `zlr=DOWN` RED cci−70 | 7556 | 7560.5 (4.5) | 7551.5/— | **+1R** (T1@13:45; MFE +4.75) | 🔴 `ready_to_route=False` | ↑ |
| **14:25→14:40** (leg-C · **ה-cluster ב-missed-endpoint**) | **ZLR-DOWN** ×4 המשך | S4 | ✅ `zlr=DOWN` ×4 RED cci−29→−137 | 7553.75 | 7561.25 (7.5) | 7546.25/— | **+1R** (T1@14:50; MFE +10.75=1.43R) | 🔴 `ready_to_route=False` (`/missed-trades`: 50 candidates, entry7548–7551) | ↑ |
| 12:05→14:15 | **HFE-UP** ×12 | S4 | ✅ ×12 (RED/GRAY) | — | — | — | (bounces-נגד-מגמה) | **HFE_DISABLED (by-design)** + נגד-trend → **דילוג-נכון** | — |
| 14:15 | ZLR-**UP** | S4 | ✅ `zlr=UP` GRAY cci+102 | (7559) | — | — | נגד-אחה"צ-היורד | **דילוג-נכון** (signal-מבודד ב-GRAY) | — |

**ΣR-נגד (פספוס-אמת, R מ-replay מבני — לא מ-`pnl_r` הפסול):**
- **S4 ZLR-DOWN המשך-מגמה (3 legs-deduped, כולם T1):** 12:25 **+1R** · 13:25 **+1R** · 14:25 **+1R** ⇒ **+3R פוספסו** (זוהו-ולא-נותבו · `ready_to_route=False`).
- **לונגים-נגד-מגמה שכן-ירו (הצד-ההפוך):** FaMir 12:20 **−1R** · VEGAS 13:05 **−1R** = **−2R** ממומש שגוי (gate-OFF, I-44/I-51).
- ⇒ **swing סלקטיביות-כיוונית ≈ +5R** בצד-אחה"צ-היורד.
- **החזר-רווח על 2 שורטים-מנצחים (I-54, execution לא-entry):** id267 HTLB MFE **+31.5→0** · id268 REACTIVE_SHORT MFE **+27→0** (`EOD_MANUAL`@entry; short-targets T1=7482 רחוק 88נק') ⇒ **CF ~+11R אבודים** (עלות-#1, per §07-01).

⇒ **זה לא "אין-setup" ולא "המערכת שקטה":** היום המערכת ירתה הרבה, אבל **שני-שערים-הפוכים** יצרו סלקטיביות-כיוונית שגויה בצד-היורד — שער-המשפחה-הכבוי שיחרר לונגים-נגד-מגמה, ו-`ready_to_route` חסם שורטי-המשך-מגמה תקפים.

## 🎯 BENCHMARK — 5 הסלוטים של Michael (06-05 יום-יורד) מול היום (OPEN_DRIVE-עולה)

ה-benchmark הוא template **יום-יורד** (4/5 SHORT). היום **בוקר-עולה** ⇒ 4/5 סלוטים מתהפכים. **תיקון-מסגור מהותי מול 06-29/06-30:** **S4 לא-היה עיוור-בוקר בזמן-אמת** — **ZLR-LONG ירה 09:03 CT** (id260/261, 14:03 UTC, +T3) ⇒ ל-S4 **היה** CCI-חי בבוקר. חלון ה-woodies-chart (11:15+) הוא **מגבלת-audit-post-close** (rolling-window/retention), **לא** עיוורון-detector. לכן הסלוטים כן ניתנים-לאימות-חלקי דרך bars5min + fired-trades:

| # | סלוט(CT) | סוג(template) | מה קרה (אמת היום) | המערכת | הערכה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2) | **שפל-יום 7506@08:35 → היפוך-עולה** | LONG ראשון @09:03 (ZLR, +T3) | ✅ כיוון-נכון (היפוך-**עולה**); +28דק' מהשפל |
| 2 | 9:00–9:05 | **LONG טקטי** | מחיר עולה 7522→7530 | **ZLR-LONG @09:03 (+T3 WIN)** | ✅ **נורה, כיוון-נכון** |
| 3 | 9:20 | SHORT | ראלי-עולה (up-drive) | INITIATIVE_LONG @09:20 (−1R) | ✅ הפך-כיוון נכון (up-day→LONG) |
| 4 | 9:35 | SHORT | המשך-ראלי | (long-bias) | ✅ שורט היה-שגוי; נכון לא-לירות |
| 5 | 10:00 | SHORT | לקראת-שיא | BULL_FLAG_LONG @10:20 | ✅ שורט היה-שגוי; long-bias נכון |

**שורת-benchmark: ה-template היורד לא-ממפה ליום-עולה, אך ה-*רוח* (לתפוס את תנועת-הבוקר) קוימה:** 2 הסלוטים תואמי-LONG (1 reversal-up, 2 long-tactical) **נתפסו כיוון-נכון** (ZLR-LONG 09:03 +T3), ו-3 סלוטי-SHORT **נכון לא-ירו** ביום-עולה. **⇒ "שתיקת-הבוקר" של 06-29/06-30 לא-חזרה** — 09:03-fire מוכיח detector-בוקר-חי. **0/5-עיוור בוטל.**

## פירוק לפי gate

| gate | #setups | סטטוס |
|---|---|---|
| **🔴 `ready_to_route=False` (S4 A-layer routing)** | 15 ZLR-DOWN | **החוסם-המוביל-לשורטים.** S4 זיהה 15 ZLR-DOWN המשך-מגמה (RED) וניתב **0**; `active_patterns=none` למרות ZLR-detected. **שער נפרד מ-DAYTYPE_POSITION_GATE** (שכבוי). gate-מדויק לא-חשוף post-close → **CC live-trace:** A1-veto? ZLR daily-cap (כבר-ירה 2× כ-LONG)? location-gate? מופיע כבר §06-08 register. |
| **🔴 I-44/I-51 — שער-המשפחה כבוי → under-block** | 2 LONG | `DAYTYPE_POSITION_GATE=0` (לוַלידציה, §07-01) → 269/270 counter-fade LONG עברו (−2R). **07-01 = מראה-הופכית ל-06-30** (gate-ON over-block). זוג-fixtures 06-30(over)/07-01(under) = מבחן-כיול. **החזרת-gate=החלטת-Michael אחרי תיקון-source.** |
| **🔴 I-54 — short-targets רחוקים (give-back)** | 2 שורטים | id267/268 MFE +31.5/+27 → 0 ב-`EOD_MANUAL` (T1=7482, 88נק' מתחת). **CF ~+11R — עלות-#1 היום.** design: target-ביניים R-based. |
| **🟢 I-52 — mode_context = benign** | — | **מאושש-שוב:** S2 ירה **5×** ב-RTH ⇒ mode_context נכח. ה-blocked = snapshot post-close OVERNIGHT. **סוגר D-I52 מ-06-30.** |
| **🟢 missed-trades endpoint — מאוכלס לראשונה** | 50 | היה 0 מ-06-08. חי — אך `hypothetical_r=null` + 50-כפולים (לא-deduped) → dedup+R-fill. |
| **🟢 I-31 — נקי (11==11)** per §07-01 | — | (surface `woodies fired_today_count=8` = ספירת demo/shadow-כפולים, **לא** phantom — ה-sibling אימת 11==11.) |
| **⚫ woodies-morning-blind — reframe ל-audit-only** | — | חלון-chart 11:15+ אבל detector **לא**-עיוור (09:03 ZLR-fire). **תיקון למסגור 06-29/06-30.** מנגנון (retention vs export) → CC. |
| **🟢 I-40/I-47 source-split/dup** | 0 | feed-נקי **יום-שלישי-רצוף** (overlap 5-נק' match). |
| **⚪ גייטי-chop (מושבתים, standing 06-08)** | — | OFF. **לא-רלוונטי · אין המלצה להפעיל — Michael בלבד. תצפית-בלבד.** |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🔴 ready_to_route (S4) — נמשך כחוסם-מוביל-לשורטים.** היום ראיה-מוצקה: 15 ZLR-DOWN RED זוהו-ולא-נותבו + `/missed-trades` מאוכלס (50). **→ CC live-trace** signal→route על ZLR-DOWN 14:25–14:40 — ה-gate המדויק. **הבחנה חשובה:** זה **לא** שער-המשפחה (שכבוי) — שער-אחר.
- **🔴 I-44/I-51 (סלקטיביות-כיוונית) — היום ה-under-block-side.** gate-OFF → 269/270 counter-fade LONG עברו. יחד עם ready_to_route-חוסם-שורטים = **swing +5R**. handoff `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md` קדימות-1.
- **🔴 I-54 (give-back) — אושש (הצד-execution).** ~+11R הוחזרו. משלים את ה-entry-analysis כאן.
- **🟢 I-52 — נסגר-benign** (S2 5-fires ב-RTH). D-I52 מ-06-30 מוכרע.
- **🟢 missed-endpoint — מאוכלס** (חדש-חיובי); צריך dedup+R.
- **🟢 feed-נקי יום-3 · I-31 נקי · detector-בוקר-חי** — שלוש מגמות-חיוביות.
- **⚫ woodies-morning-blind — reframe:** מגבלת-audit, לא-detector. מתקן מסקנת 06-29/06-30.

## נטיפיקציה ל-Michael
**🟢 יום פעיל (11 עסקאות, שני-כיוונים) — היפוך מ-06-29/06-30 השקטים; feed-נקי יום-3; detector-בוקר-חי (ZLR ירה 09:03).**
**🔴 אבל סלקטיביות-כיוונית הפוכה בצד-אחה"צ-היורד — שני-שערים:** (א) שער-המשפחה **כבוי** (`DAYTYPE_POSITION_GATE=0`) → 2 LONG-נגד-מגמה עברו (FaMir/VEGAS **−1R כ"א**); (ב) `ready_to_route=False` חסם את **כל 15 ה-ZLR-DOWN המשך-מגמה** (+3R שפוספסו). **swing ≈ +5R.** בנוסף **~+11R הוחזרו** על 2 שורטים-מנצחים (id267/268 EOD_MANUAL@entry, **I-54** short-targets-רחוקים).
**🟢 endpoint missed-trades מאוכלס לראשונה** (50 candidates ZLR-SHORT ready_to_route=False) — היה 0 מ-06-08.
**benchmark:** ה-template היורד לא-ממפה ליום-עולה, אבל 2 סלוטי-LONG נתפסו כיוון-נכון ו-3 סלוטי-SHORT נכון-לא-ירו; **שתיקת-בוקר לא-חזרה.**
**🟠 דגלי-CC (חי-בלבד):** (1) **ready_to_route** — trace ה-gate שחוסם ZLR-DOWN (נפרד מהמשפחה-הכבוי); (2) **I-44/I-51** — day_type-source לקראת re-enable של gate (החלטת-Michael); (3) **I-54** — target-ביניים R-based. גייטי-chop מושבתים (standing, **לא-להפעיל**). **לא שונה קוד.**

---
*נוצר אוטונומית ע"י Cowork (15:20 CT, 2026-07-01). מאומת-תוכניתית (Rule 2/5): feed-נקי overlap `bars5min==woodies` @11:15(7575.75)·11:20(7577)·12:00(7559.5)·13:00(7561.5)·14:30(7555.5) · day open7508.75@08:30 low7506@08:35 high7579@11:20 close-b5 7542@14:55 woodies-last7532.75@15:20 · Variation OPEN_DRIVE IB7506–7553.75 stageB2 conf0.18 · woodies-aft RED37/GRAY9/BLUE4 · ZLR-DOWN×15 ZLR-UP×1 HFE-UP×12 · trades today=11 (S4=6 ids260,261,266,267,269,270; S2=5 ids262,263,264,265,268; max270; I-31 נקי 11==11 per §07-01) · missed-trades=50 ZLR-SHORT ready_to_route=False (~14:42–14:45 entry7548–7551, hypothetical_r=null, לא-deduped) · replay deduped ZLR-DOWN: 12:25/13:25/14:25 כולם T1 ⇒ +3R · counter-fade longs fired FaMir12:20/VEGAS13:05 ⇒ −2R (gate-OFF I-44/I-51) · give-back id267 MFE+31.5→0 / id268 MFE+27→0 (EOD_MANUAL, I-54) · benchmark: ZLR-LONG fired 09:03 CT ⇒ audit-window≠detector-blind. R מ-replay מבני (pnl_r פסול, I-22). TZ: woodies=UTC(−5→CT), bars5min/trades=+03:00(IL,−8→CT), מאומת-overlap. **לא שונה קוד.***
