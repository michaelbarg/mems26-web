# MEMS26 · דוח EOD מאוחד — 2026-07-06 (יום שני · יום-מסחר-מלא)

**שער-זמן (I-9):** ✅ הופק אחרי-הסגירה — בעת-הריצה **15:12 CT** (≥15:00 CT, אומת `TZ=America/Chicago date` → `2026-07-06 15:12 CDT`; IL 23:12 IDT). RTH מלא (08:30–15:00 CT). ה-feed בריא — הבר האחרון **14:55 CT** (`sierra.writing=true, last_write_age_s=0.9`), 78 ברי-RTH רציפים.
**מקורות:** API חי דרך Chrome (`http://localhost:8000`): `/trades/recent?limit=100` → **3 רשומות-היום (id 292/294/295, כולן shadow)** · `/chart/bars5min?limit=200` → **78 ברי-RTH (16:30→22:55 IL / 08:30→14:55 CT)** · `/day_type/state` · `/gateway/status` · `/status` · `/chop_score/current` · `/missed-trades` (**count=50** — buffer-artifact, ראו §3). ⚠️ **אין `PATTERN_DIAG_2026-07-06.md`** (סוכן-snapshots מושבת מאז 06-10) ⇒ ספירות-arming intraday לא-זמינות; הטבלה נבנתה מ-fires + `/missed-trades` + הצלבת-78-הברים. ה-API מחזיר `ts` בזמן-IL (UTC+3); **CT = IL−8**.

> **🔴 כותרת-העל #1 — הנתיב-הקובע (DEMO) כבוי היום.** `gateway.demo_enabled_systems=[]` ⇒ **0 עסקאות-דמו** (מול דמו-פעיל עד 07-03: id290 REACTIVE_SHORT WIN). `live_enabled_systems=[2,4]` אך `live_slot=null` ⇒ **0 עסקאות-לייב** בפועל. **רק shadow-sim רץ היום.** ייתכן קידום-מכוון pre-LIVE (S2/S4 הועברו demo→live-enabled) או השבתה-בשוגג — **דורש אישור-Michael** (I-62 חדש). כל התוצאות למטה הן shadow בלבד; אין "נתיב-קובע" להצליב מולו היום.

> **🟡 כותרת-העל #2 — יום-ראלי (+28.75pt), אך הסיגנלים הטקטיים היו רובם שורט-נגד-מגמה.** טווח 50pt (7552.25–7602.25), נטו **+28.75pt** (open 7564.75 → close 7593.5). למרות זאת 2 מ-3 הסיגנלים היו **שורט** (292 ZLR-SHORT, 294 REACTIVE_SHORT) על יום שעלה — **חזרה של הטיה-א-סימטרית I-41/I-50.** שניהם היו נעצרים (−1R כ"א) אלמלא flatten-12:01; ה-LONG-היחיד-הטרנד-תואם (295 GHOST) נעצר כי קנה שיא-מקומי.

> **🟡 כותרת-העל #3 — אירוע-flatten ידני ב-12:01 CT הפך 2 שורטים מ-−1R ל-0R.** 292 ו-294 שניהם נסגרו `exit_reason=manual`, `outcome=BE`, **באותה-דקה (12:01 CT)**, במחיר≈כניסה. השורטים נכנסו לתוך ראלי (הבר 12:00 עלה ל-7589) ⇒ CF-hold = STOP −1R לכל אחד. ה-flatten **חסך +2R** — אבל **המנגנון לא-ברור** (התערבות-ידנית מול חוק-shadow-sim). I-61 חדש · SoT ל-CC.

> **🟡 כותרת-העל #4 — משטחי-מצב: I-44 עדיין קפוא, I-23 עדיין לא-סופר shadow.** `day_type/state`: `Variation/conf=0.18/LOCKED_LOW_CONF/opening_type=OPEN_REJECTION_REVERSE/ib_width=WIDE` — **התוויות סבירות היום** (היום אכן פתח-נדחה-והתהפך), אך `session_min=0`/`vote_history=[]` = **wrapper-קפוא (I-44)**. `gateway`: `trades_today=0/daily_pnl=0` מול 3-fires-shadow (**I-23**). שניהם display-only, לא-חסמו-מסחר.

---

## מצב-היום

**צורת-יום (78 ברים, feed בריא):** פתיחה 7564.75 (08:30 CT) → **דחיית-פתיחה** לשפל-יום **7552.25 @08:35** (−12.5pt) → התאוששות + זחילה-מדורגת-מעלה כל אחה"צ → **שיא-יום 7602.25 @14:20 CT** → דעיכה 35 הדק' האחרונות (7602→7591 @14:50) → נעילה **7593.5 (14:55 CT)**. **טווח 50pt · נטו +28.75pt** — יום-Variation/מגמה-מתונה-מעלה, ווליום-רגיל (10k–29k/בר, שיא-פתיחה 28,981). **OPEN_REJECTION_REVERSE** מתאים-לצורה (פתח, נדחה-נמוך, התהפך-מעלה).

| CT | IL | O | H | L | C | Vol | הערה |
|----|-----|---|---|---|---|-----|------|
| 08:30 | 16:30 | 7564.75 | 7573.25 | 7559.25 | 7570.25 | 28,981 | פתיחה |
| 08:35 | 16:35 | 7570 | 7570.25 | **7552.25** | 7561.5 | 22,615 | **שפל-יום** (דחיית-פתיחה) |
| 11:55 | 19:55 | 7585.5 | 7586.5 | 7581.5 | 7583.75 | 6,896 | **292 ZLR-SHORT entry 7585.25, stop⁰ 7587.5** |
| 12:00 | 20:00 | 7583.75 | **7589** | 7583 | 7587.75 | 6,497 | **294 REACTIVE_SHORT entry 7583.75, stop⁰ 7586.5 · הבר עלה ל-7589 (מעל שני הסטופים)** |
| 12:01 | 20:01 | — | — | — | — | — | **🟡 flatten-ידני: 292+294 נסגרו BE @כניסה (`manual`)** |
| 12:05 | 20:05 | 7588 | 7594.75 | 7587.75 | 7593.25 | 10,677 | המשך-ראלי |
| 12:25 | 20:25 | 7588.75 | 7590.25 | 7585.25 | 7586.25 | 4,642 | **295 GHOST-LONG entry 7589.25, stop⁰ 7587 · הבר נסגר 7586.25 (מתחת-לכניסה)** |
| 12:30 | 20:30 | 7586 | 7586.75 | 7581.75 | 7582.5 | 8,150 | **295 STOP @7587 (low 7581.75) · −$33.75** |
| 14:20 | 22:20 | 7599.25 | **7602.25** | 7598 | 7601.25 | 6,642 | **שיא-יום** |
| 14:47 | 22:47 | (בבר 14:45) | 7600.5 | 7597.25 | — | 5,520 | **~50× ZLR-LONG `ready_to_route=False` (buffer-artifact) @~7599.375** |
| 14:50 | 22:50 | 7597.75 | 7598.25 | **7591** | 7591.25 | 15,204 | דעיכה-לסגירה (מפילה את ה-ZLR-LONG-החסום) |
| 14:55 | 22:55 | 7591.5 | 7593.75 | 7587.75 | 7593.5 | 23,012 | **נעילה 7593.5** |

**Snapshots post-close (15:1x CT):**
- `/status`: `sierra.writing=true, last_write_age_s=0.9` (**feed טרי**) · `mode=live` · `day_type=Variation/LOCKED/0.18/B2/ib_locked=true` · `bar_router received=26,231 dispatched=31,633 failed=0` · `bars_in_db=2,998` · `session=AFTER_HOURS/is_trading_active=true`. ⚠️ `bridge.running=false, streams_active=0/11` — סביר artifact-post-close (Sierra מייצא-ישירות; הברים זרמו טריים), **אך לצלב** (§6).
- `/day_type/state`: `Variation · B2 · conf=0.18 · LOCKED_LOW_CONF · opening_type=OPEN_REJECTION_REVERSE · ib_width=WIDE · behavior=DEVELOPING · range=NORMAL · session_min=0 · vote_history=[]` — **I-44 (wrapper-קפוא)**; ההתוויות סבירות-היום (בניגוד ל-07-03 OPEN_DRIVE/EXTREME על 12.5pt) אך `session_min=0`/`vote_history=[]` עדיין-מסגירים קיפאון.
- `/gateway/status`: `trades_today=0 · daily_pnl=0` (**I-23** — לא-סופר 3-shadow) · `demo_slot=null · demo_enabled_systems=[]` (**דמו-כבוי, I-62**) · `live_enabled_systems=[2,4] · live_slot=null` (0-לייב) · `shadow_active_count=0` (הכל-סגור) · `consecutive_losses=0 · cooldown inactive · cluster_guard inactive · chop_state=EXPANDING`.
- `/chop_score/current`: `chop_score=30 · state=EXPANDING` (לא-choppy — תואם יום-מגמה-מתונה; שערי-chop כבויים ממילא לפי CLAUDE.md).
- `/missed-trades`: **count=50, כולם ZLR-LONG `ready_to_route=False`, מרוכזים ~14:47 CT, `hypothetical_r=null`** — buffer-artifact (§3, D-missed-buffer).

---

## 1. עסקאות שנורו היום — 3 רשומות, כולן shadow (0 demo / 0 live)

⚠️ `pnl_r` היום **תקין** (−1 על STOP, 0 על BE) — I-22 לא-מומש (אין WIN חלקי-R). כלכלה ב-USD. **אין נתיב-דמו/לייב היום** (I-62).

| id | mode | מערכת | תבנית | כיוון | CT-in | entry | stop⁰ (R) | T1 | תוצאה | USD | pnl_r |
|----|------|-------|-------|-------|-------|-------|-----------|-----|--------|-----|-------|
| 292 | shadow | **S4** | ZLR | SHORT | 11:55 | 7585.25 | 7587.5 (2.25pt) | 7578.5 | **BE (manual 12:01)** | **0** | 0 |
| 294 | shadow | **S2** | REACTIVE_SHORT | SHORT | 12:00 | 7583.75 | 7586.5 (2.75pt) | 7578.25 | **BE (manual 12:01)** | **0** | 0 |
| 295 | shadow | **S4** | GHOST | LONG | 12:25 | 7589.25 | 7587 (2.25pt) | 7592 | **STOP (12:30)** | **−33.75** | −1 |

**כלכלה (shadow, אמין):** נטו **−$33.75 · 0W / 1L / 2BE.** אין demo/live. יום-הפסד-קטן.

**הערות פר-עסקה:**
- **292 (ZLR-SHORT, S4):** נכנס 11:55 לתוך רנג'-11:5x, אך הבר 12:00 עלה ל-7589 (מעל stop 7587.5). נסגר `manual` BE @12:01 ⇒ **חסך STOP −1R.** targets: t1 7578.5 / **t2 7558 / t3 7557.25** — t2/t3 מבניים-רחוקים (25+pt) על יום-50pt (I-54 family).
- **294 (REACTIVE_SHORT, S2):** נכנס 12:00 @open, אותו-הבר עלה ל-7589 (מעל stop 7586.5) ⇒ CF-hold STOP −1R. נסגר `manual` BE @12:01. targets: t1 7578.25 / **t2 7558 / t3 7569.75** — **t2 (25.75pt) רחוק-מ-t3 (14pt) = היפוך-מונוטוניות** (D-targets-monotonic).
- **295 (GHOST-LONG, S4):** נכנס 12:25 @7589.25 (בתוך-טווח-הבר 7585.25–7590.25 — **לא phantom**, אומת מול bars5min), אך הבר-12:25 **נסגר 7586.25 — כבר-מתחת-לכניסה** (קנה שיא-מקומי בהיפוך). הבר-הבא (12:30) ירד ל-7581.75 → STOP @7587. `mfe=0`/`price_high=7586.75` = מדידת-MFE על הבר-שאחרי-הכניסה (12:30), קונבנציה — לא-באג. `woodies_trend=BLUE` (טרנד-תואם) אך תזמון-כניסה גרוע.

---

## 2. טבלת תבניות — נדרכה / נורתה / לא-נורתה / תחזית-נגד

| מערכת | תבנית | נורתה# | לא-נורתה# (סיבה) | תוצאה (USD, shadow) | תחזית-נגד (W/L, ΣR) | הערכה |
|-------|-------|--------|------------------|---------------------|----------------------|--------|
| **S4** | ZLR (SHORT) | 1 (292) | — | **$0 (BE-flatten)** | CF-hold = STOP **−1R** (בר-12:00 עלה 7589) | 🟡 שורט-נגד-ראלי · flatten-הציל |
| **S4** | GHOST (LONG) | 1 (295) | — | **−$33.75** | actual **−1R** (קנה שיא-מקומי; אין CF-hold — נעצר) | 🟡 טרנד-תואם אך תזמון-גרוע |
| **S2** | REACTIVE_SHORT | 1 (294) | — | **$0 (BE-flatten)** | CF-hold = STOP **−1R** (בר-12:00 עלה 7589) | 🟡 שורט-נגד-ראלי · flatten-הציל |
| **S4** | ZLR (LONG) | 0 | **~50× `ready_to_route=False`** (buffer-artifact, ~14:47) | — | CF replay: **STOP −1R** (14:50 ל-7591) | 🟢 חסימה-מוצדקת (chase-שיא נכשל) · 🟡 endpoint-artifact |
| S2 | REACTIVE_LONG · INITIATIVE (L/S) · FLAGS · DT/DB/HNS | 0 | לא-נדרכו (אין DIAG; לא-נורו) | — | — | ⚪ לא-נצפו (יום-מגמה-מתון) |
| S4 | TLB/GB100/HFE/VEGAS/FAMIR/HTLB | 0 | לא-נורו | — | — | ⚪ תואם-יום |
| S3 | 4 תבניות | 0 | muted (I-11, deferred) | — | — | ⚪ מחוץ-לסקופ |
| S1 | Day Type | — | — | — | — | 🟡 I-44 wrapper-קפוא (session_min=0/vote_history=[]) — התוויות סבירות היום |

**חסימות ידועות (ללא DIAG intraday):** רק ה-50 ZLR-LONG ב-`/missed-trades` (§3). אין רשומות-חסימה אינטרה-דיי אחרות. **הערה חשובה:** 292/295 (S4 ZLR-SHORT + GHOST-LONG) **כן-נותבו-ב-shadow** — כלומר `ready_to_route=False` חוסם demo/live אך shadow-sim לוכד את הסיגנל. זו נקודת-מידע: ה-shadow הוא-המקום-לראות מה-S4-היה-עושה.

---

## 3. תחזית-נגד (counterfactual) — מוחזר על 78 ברי-אמת

### CF-A · שני-השורטים-הנגד-מגמה (292 ZLR-SHORT + 294 REACTIVE_SHORT) — flatten הציל −2R
עוגנים: 292 entry 7585.25 / stop 7587.5 (1R=2.25pt); 294 entry 7583.75 / stop 7586.5 (1R=2.75pt).
- **בפועל:** שניהם `manual` BE @12:01 → $0.
- **CF-hold:** הבר **12:00** (o 7583.75, **h 7589**, l 7583) — ה-high 7589 חוצה את **שני** הסטופים (7586.5 ו-7587.5) ⇒ **שניהם STOP −1R.** לאחר-מכן הראלי המשיך ל-7594.75 (12:05) ⇒ אין תרחיש שבו T1 (7578.x, ~5–7pt מתחת) נגע. **⇒ ה-flatten-12:01 חסך +2R מדויק.** אבל: אלה **שורטים-נגד-מגמה על יום-ראלי** — הרווח-האמיתי היה **לא-לירות-אותם**, לא "להצילם ב-flatten".

### CF-B · 295 GHOST-LONG — STOP-אמיתי, ללא-מוצא-CF
entry 7589.25, stop 7587 (1R=2.25pt), T1 7592. הבר-12:25 נסגר 7586.25 (מתחת-לכניסה), 12:30 ל-7581.75 → **STOP −1R בפועל.** אין CF-hold (הסטופ נפגע; MFE-post-entry=0). **R-CF-delta = 0.** זו עסקה-מפסידה-נקייה (קנה שיא-מקומי @היפוך).

### CF-C · ~50 ZLR-LONG-החסומים (~14:47 CT) — חסימה-מוצדקת
entries ~7599.25–7599.5 (avg 7599.375). ברי-אחרי: 14:45 (h 7600.5, l 7597.25) לא-נגע T1-סביר (~7602), ואז **14:50 קרס ל-7591** → stop (~2.25pt מתחת, 7597.1) **נפגע** → CF **STOP −1R.** ה-mfe-CF = **−1.125pt** (מעולם-לא-חיובי), mae −8.375pt. ⇒ **כל ZLR-LONG-חסום היה ≈ −1R בסגירה. `ready_to_route=False` חסך — מוצדק.** (50=דופליקטים של ~1 סיגנל ⇒ ΣR-נחסך ≈ −1R, לא ×50.) שיא-היום (7602.25 @14:20) כבר-היה-מאחור ⇒ זה chase-שיא מאוחר שנכשל.

**קביעה:** **ΣCF-היום: אקטואלי = −1R (−$33.75, רק 295).** השערים/exits היו **נטו-מגִנִּים**: flatten-12:01 חסך +2R (2 שורטים-נגד-מגמה), `ready_to_route` חסך +1R (chase-חסום). **אפס-winner-הושאר-על-הרצפה** (אין סיגנל-חסום-שהיה-מנצח). **הלקח:** לא-היה "פספוס" היום — הבעיה ההפוכה: **המערכת ייצרה סיגנלים-נגד-מגמה** ביום-ראלי, וניצלה רק בזכות flatten שמנגנונו-לא-ברור. יום-n-נמוך (3 fires) — לא-מגמה.

---

## 4. ממצאים

### 🔴 I-62 (חדש) — הנתיב-הקובע (DEMO) כבוי
`gateway.demo_enabled_systems=[]` ⇒ 0 עסקאות-דמו היום, מול דמו-פעיל עד 07-03 (id290). `live_enabled_systems=[2,4]` אך `live_slot=null` (0-לייב). ⇒ **רק shadow-sim רץ.** ייתכן **קידום-מכוון pre-LIVE** (העברת S2/S4 מ-demo ל-live-enabled לקראת LIVE) — או **השבתה-בשוגג.** מכיוון ש-07-03 כינה את demo "הנתיב-הקובע", היעדרו משנה את קריאת-התוצאות. **דורש אישור-Michael** (trading-surface — ראו §5-design). SoT: להצליב `.env`/`FLAG_INDEX.md`/gateway-config מתי-ואיך demo_enabled רוקן.

### 🟡 I-61 (חדש) — flatten-ידני של שורטי-shadow ב-12:01 CT, מנגנון-לא-ברור
292 (entry 11:55) ו-294 (entry 12:00) שניהם `exit_reason=manual / outcome=BE` **באותה-דקה 12:01**, במחיר≈כניסה. עבור **שורט** שנכנס-לתוך-ראלי (מהלך-אדוורסרי מיָדִי), BE-stop אמיתי **לא-ייתכן** (הסטופ-ל-BE נקבע רק אחרי מהלך-חיובי; כאן המחיר עלה) ⇒ זו **סגירת-flatten** ולא BE-management. **מנגנון:** התערבות-ידנית של Michael? חוק-shadow-sim? באג? — לא-ברור. **מהותי:** הפך 2×(−1R)→0R (§3 CF-A). SoT ל-CC: לחלץ מ-`on_trade_close`/shadow-exit-path מי-כתב `exit_reason=manual` על 292/294, והאם זה נתיב-אוטומטי או ידני.

### 🟡 D-missed-buffer (שוחזר) — `/missed-trades` חסר-ערך-אינטרה-דיי (מבני)
היום שוב: **count=50, כולם ZLR-LONG `ready_to_route=False`, מרוכזים ~14:47 CT, `hypothetical_r=null`.** אותם שני-פגמים: (א) **אין-dedup** (Sierra ריבוי-UPDATE → אותו-מועמד עד תקרת-50); (ב) **`hypothetical_r` תמיד null** (CF לא-מחושב-בכתיבה). ⇒ ה-store לא-לוכד חסימות-אמצע-יום (שם ה-R-האמיתי) — רק פרץ-מאוחר. **תבנית-שחזרה 06-16→07-03 + היום.** מאחד I-60. display/safe → §5-design.

### 🔴 I-54 / D-targets-monotonic (שוחזר) — short-targets מבניים-רחוקים + היפוך-מונוטוניות
292: t2=7558 (25.75pt) / t3=7557.25 (28pt). 294: t2=7558 (**25.75pt**) / t3=7569.75 (**14pt**) → **t2 רחוק-מ-t3** (היפוך: T2 אמור-להיות-בין-T1-ל-T3). על יום-טווח-50pt, targets של 25+pt לא-בני-השגה. אלמלא ה-flatten, שני-השורטים היו-נעצרים הרבה-לפני שכל target-שני/שלישי היה רלוונטי. חוזר על I-54 (07-01/02) ו-D-targets-monotonic. trading-logic → §5-design.

### 🟡 הטיה-א-סימטרית שורט-נגד-מגמה (I-41/I-50 family, שוחזר)
ביום-ראלי (+28.75pt) 2 מ-3 הסיגנלים היו SHORT (292/294), וה-LONG-היחיד (295) נכנס-גרוע. אין LONG-מנצח שנורה. חוזר על התלונה-ההיסטורית: המערכת מייצרת שורטים-נגד-מגמה בנקודות-היפוך/רנג' בתוך-יום-עולה. n-נמוך היום (shadow-בלבד) — **watch**, לא-חדש.

### שוחזרו (display-only, לא-חסמו-מסחר)
- **🔴 I-44 (day_type-wrapper):** `session_min=0/vote_history=[]` (קפוא). היום ההתוויות **סבירות** (OPEN_REJECTION_REVERSE/WIDE תואמים צורת-יום) — ניגוד ל-07-03 (OPEN_DRIVE/EXTREME בלתי-סביר). ה-wrapper-הקפוא נשאר-הבעיה, לא-התוויות-היום. handoff קיים.
- **🟡 I-23 (gateway counters):** `trades_today=0/daily_pnl=0` מול 3-fires-shadow. design עומד.
- **🟢 I-22 (pnl_r):** **לא-מומש היום** — pnl_r=−1 (STOP) / 0 (BE) תקינים. הניפוח מופיע רק על WIN-חלקי-R (כמו 290 ב-07-03: pnl_r=14). design עומד לכשיחזור WIN.
- **🟡 bridge.running=false / streams 0/11** מול feed-טרי (0.9s): artifact-post-close סביר (כמו 07-03). לצלב §6.
- **🟢 I-25 נעקף** (limit=100) · **🟢 I-56/I-58 לא-שוחזרו** (אין divergence shadow↔demo — כי אין demo היום; לא-נבחן) · **🟢 feed נקי** (78 ברים רציפים, age 0.9s).

---

## 5. לקחים

- **הבעיה-של-היום היא "יריות-נגד-מגמה", לא "פספוסים".** ΣCF≈−1R-אקטואלי, אפס-winner-על-הרצפה. אבל 2 מ-3 סיגנלים היו שורט-נגד-ראלי; ה-flatten-12:01 (I-61) הוא-שהציל, לא-המערכת. **הכיוון-הנכון: להבין למה S2/S4 מייצרים שורטים ביום-BLUE/ראלי** (I-41/I-50), לא לסמוך על flatten-לא-מובן.
- **demo כבוי (I-62) = נקודת-עצירה.** לפני-הסקה-כלשהי — לוודא אם זה קידום-pre-LIVE מכוון (S2/S4→live-enabled) או שוגג. אם שוגג, **הנתיב-הקובע היה דומם יום-שלם.**
- **`ready_to_route=False` חסם-נכון שוב** (chase-שיא 14:47 → CF −1R). כמו 07-03, החסימה-מוצדקת-ברנג'/סוף-יום — אבל עדיין **חסר instrumentation `failed_stages`** (איזה A-stage הפיל). זה התנאי-לפני-כל-כיול (לא-לגעת בלוגיקת-ירי לפני שרואים למה).
- **`/missed-trades` לא-אמין** (50 דופ', r=null) — כל-דיווח-החמצות חייב dedup + hypothetical_r (D-missed-buffer, מאוחד I-60).
- **short-targets עדיין שבורים** (25+pt, t2>t3) — I-54/D-targets-monotonic. ביום-בלי-flatten זו הייתה בעיה-אמיתית (שורט-מנצח נחנק ע"י target-לא-בר-השגה, כמו 07-01/02).
- **אל-תסיק מ-n=3-shadow-בלבד.** אין demo/live להצליב; I-61/I-62 משנים את משמעות-היום.

---

## 6. מקור-אמת — דורש הצלבת CC מול Sierra v9_export / לוג / DB (Rule 2/5)

1. **🔴 I-62 (demo כבוי):** לצלב `.env` / `docs/FLAG_INDEX.md` / gateway-config — **מתי `demo_enabled_systems` רוקן, ומי** (commit/הוראה). לאשר אם `live_enabled=[2,4]` הוא קידום-מכוון (Michael) או drift. **trading-surface — סטופ-אסטרטגי עד אישור.**
2. **🟡 I-61 (flatten 12:01):** לחלץ מ-`fill_poller.py`/`on_trade_close`/shadow-sim-exit את הנתיב שכתב `exit_reason=manual` ל-292/294 באותה-דקה — אוטומטי או ידני? להצליב מול `/tmp` logs סביב 12:01 CT.
3. **🟡 I-54 / targets:** לחלץ את חישוב-ה-targets (t2=7558 על שני-השורטים = חשוד רמה-מבנית-קבועה) מ-`five_min_system`/woodies-target-calc — לאשר את היפוך-המונוטוניות (t2>t3 ב-294) ומקור ה-7558.
4. **🟡 D-missed-buffer:** לאמת מול לוג ה-`missed_trade_detector` שה-50 = דופליקטים (ריבוי-UPDATE), ו-`hypothetical_r=null` נכתב-כך במקור. לצלב ערכי-ZLR (CCI-14/TCCI) של 14:45–14:50 מול `~/SierraChart_Data/v9_export/`.
5. **🟡 bridge.running=false:** לאשר artifact-post-close (Sierra-direct) מול `/tmp/bridge.err.log` + LaunchAgent — לא drift.
6. **🔴 I-44:** ה-handoff `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md` עומד; היום ההתוויות סבירות (OPEN_REJECTION_REVERSE/WIDE) — הבעיה ב-`session_min=0/vote_history=[]` הקפואים, לא-בסיווג.

**NOT-DONE / מגבלות:**
- כל-הקריאות דרך Chrome מול `localhost:8000` (אין PG-ישיר מה-sandbox); ערכי-Sierra-גולמיים לא-הוצלבו — read-only, CC.
- אין intraday-DIAG ⇒ `נדרכה#` מלא לא-זמין; `/missed-trades` לוכד רק פרץ-מאוחר (D-missed-buffer).
- CF מבוסס על 78 ברי-5דק' קנוניים (feed-נקי) — לא על shadow-fills.
- **demo/live כבויים** ⇒ n=3-shadow-בלבד; כל "🟡" הוא נקודת-נתונים-shadow, לא-מגמה.
- **שום קוד/flag/.env/DB לא-שונה בריצה זו** (read-only EOD).
