# ניתוח עסקאות-שלא-בוצעו · 2026-06-15 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-15:23 CT (אחרי סגירת RTH 15:00) ✓. ריצה אוטונומית — Michael לא נוכח.
יום-מסחר ראשון אחרי סוף-השבוע (אחרון: 06-12 שישי).

**הקשר (מאומת מדאטה חיה):** יום **Trend_Normal** (S1) — **בוקר-עולה / אחה"צ-דועך**. פתיחת RTH
7599.25 (08:30) → ראלי רצוף ל-**HIGH סשן 7648.75 (11:00)** → דעיכה/range עד סגירה **7630
(14:55)**. טווח-RTH ~50 נק'. IB 7598.25–7622.50 (locked). ברי-ה-RTH (7598–7648) = **חוזה-ספטמבר
החי** (front-month אחרי הגלגול), real.

> 🔴 **CAVEAT-נתונים (קריטי — Rule 2, מאומת מ-STATUS_BOARD 06-15 ~14:20–14:27 IDT):** היום בוצע
> **גלגול-חוזה MES יוני→ספטמבר**, וחלק מיצואי-Sierra נותרו **קפואים על יוני-שפג ~7498.50**
> (`mes_ai_data.json`/`5min.json`/`live_price.price`/`v9_tpo_history`), בעוד נתיב-הירי (woodies/
> continuous → S4 + day_type IB) רץ על **ספטמבר החי ~7600**. ⇒ ה**`session_low=7498.50`** ב-day_type
> וה**2× `uncaptured_move` "ramp +109נק' 7498→7607" @08:35/08:40** ב-missed-endpoint הם **artifact
> של גלגול-החוזה — לא מהלך-מחיר אמיתי ולא setup**. הוצאו מחישוב-ה-R. **דגל-CC:** value-area/TPO-context
> שמזין observers של S4 ייתכן והיה קפוא-יוני בזמן-הירי ⇒ לאמת אם גרם מיס-פייר (day_type עצמו סווג
> על IB-ספטמבר אמיתי 7598–7622, ✓).

> 🔗 **הצלבה:** צד **העסקאות-שירו** (26 ירי, נטו −$394.45 shadow) מכוסה ע"י קונסולידציית
> ה-EOD (`PATTERN_EOD_2026-06-15` / STATUS_BOARD). דוח זה = הצד המשלים: **מה לא ירה ולמה**,
> + אימות benchmark. הממצאים מתואמים, לא כפולים.

> 🟢 **שינוי מהותי מול 06-05→06-12: S4 ירה היום.** היסטורית S4/ZLR כמעט-לא נותב (A7 `R:R<1.0`
> / `missing fire_setup` — I-3). **היום נותבו 18 עסקאות-S4** (ZLR×6, TLB×7, HFE×4, GB100×1).
> ⇒ נראה שטבלת stop/target / `fire_setup` (D1/D8) **נחתה**. **דגל-CC (Rule 5):** לאשר מ-diff/deploy
> שזה תיקון-קוד ולא תנאי-שוק; אם תוקן — I-3 יורד 🔴→🟡 (ראה residual VEGAS/GHOST/FAMIR למטה).

## מקורות-אמת + כיסוי (הצלבה ל-CC)
| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/missed-trades` | **08:35→14:55 (סשן מלא)** | **חדש — מחשב rolling-6-bar server-side**: 42 candidates (40 `blocked_signal` + 2 `uncaptured_move`). `hypothetical_r=null` ⇒ replay בוצע כאן על OHLC חי |
| `/api/v9/woodies/chart?limit=80` | **11:30→15:35 (50 ברים)** | **מקור-אמת ל-CCI = Sierra** (`source=sierra_export`, `cci_14` chart12/study4) · ts=UTC · trend אחה"צ: RED 31 / GRAY 17 / BLUE 2 |
| `/api/v9/chart/bars5min?limit=80` | **08:30→14:55 (78 ברי RTH)** | ts=IL(+03:00) · משמש ל-replay-קדימה |
| `/api/v9/trades/recent?limit=100` | היום: **26 עסקאות** (8×S2 + 18×S4) | R מ-`pnl_usd/risk` — **לא** מ-`pnl_r` (I-22, מנופח ~50×) |
| `/api/v9/build/pattern-status` | live post-close | readiness=**DEGRADED** (trend_state=GRAY post-close); day_type=Trend_Normal; errors=[] |

> ⚠️ **פער-מקור מסומן ל-CC (Rule 1 — אין סינתזה):** buffer ה-study החי = 50 ברים (11:30 CT ואילך).
> flags ZLR/HFE לבוקר 08:30–11:25 **אינם** בזיכרון-ה-study החי. עם זאת — **`missed-trades` endpoint
> כן מכסה את הבוקר** (signals מ-08:50), כך שהצלבת-הבוקר נשענת עליו + על טבלת ה-trades, לא על
> סינתזה מקומית. CCI-בוקר טרם-אומת מול Sierra — דגל-CC.

## טבלת setups שזוהו-ולא-ירו (rolling-6-bar · 31 distinct, deduped + 2 uncaptured)
entry=מחיר-האות (endpoint) · stop=swing בר-האות+הקודם · T1=1R/T2=2R · replay על OHLC חי
(stop-first בעימות-באותו-בר). כיוון מסומן aligned/counter מול שלב-המגמה (AM-up עד 11:00 / PM-fade).

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay) | gate-שחסם | I-# |
|---|---|---|---|---|---|---|---|---|---|
| 08:35/08:40 | ⚠️ **roll-artifact (לא-setup)** | move | ❌ | 7498.5→7607 | — | — | **לא-אמיתי** — 7498.5 = פיד-יוני-קפוא, ה"מהלך" = פער-גלגול (ראה CAVEAT) | זיהום-נתונים, לא gate | — |
| 08:50 | HFE | S4 | ✅ | 7620 | 7622.5 (2.5) | T1/T2 | **+2R** (counter-AM, top-tick) | `ready_to_route=False` | I-3 |
| 08:55 | HFE | S4 | ✅ | 7618.75 | 7622.5 (3.75) | — | **+1R** (counter-AM) | `ready_to_route=False` | I-3 |
| 10:15–10:55 | HFE×5 / TLB | S4 | ✅ | 7627–7641 | 1.5–6 | — | **−5R** net (counter-AM לתוך הראלי) | `ready_to_route=False` — **חסם נכון** | I-3 |
| 11:00 | HFE | S4 | ✅ | 7643.25 | 7648.75 (5.5) | — | +1R (PM-fade, aligned) | `ready_to_route=False` | I-3 |
| 11:45–12:30 | **VEGAS/GHOST×8** | S4 | ✅ | 7640–7643 | 1.25–3.5 | — | **+1R net** (PM-fade, aligned; 12:00/12:05/12:25 = +2R) | `ready_to_route=False` — **תבניות שלא-נותבות אף-פעם** | **I-3 residual** |
| 12:25–12:30 | TLB LONG×2 | S4 | ✅ | 7643 | 7639–7640 | — | −1R כ"א (counter-PM) | `ready_to_route=False` — חסם נכון | I-3 |
| 13:25–14:00 | HFE LONG×5 | S4 | ✅ | 7628–7634 | 2–5 | — | −2R net (1×+2R 13:30; שאר counter-PM) | `ready_to_route=False` — חסם נכון | I-3 |
| 14:05 | ZLR SHORT | S4 | ✅ | 7630 | 7632.25 (2.25) | — | −1R | `ready_to_route=False` — חסם נכון | I-3 |
| 14:50 | **FAMIR/TLB LONG** | S4 | ✅ | 7626 | 7620.25 (5.75) | — | −1R (counter-PM) | `ready_to_route=False` — FAMIR **לא-נותבת אף-פעם** | **I-3 residual** |
| 14:55 | ZLR SHORT | S4 | ✅ | 7621.5 | 7631.5 (**10**) | — | −0.85R (timeout; stop-רחב) | `ready_to_route=False` (+ stop 10נק' = I-13) | I-3/I-13 |

**ΣR של ה-unfired (31 distinct, replay-מלא):** אילו **כולם** היו יורים: 10 מנצחים **+15R** / 21 מפסידים
**−20.85R** ⇒ **net −5.85R**. כלומר **אי-הירי חסך ≈ +5.85R** — ה-gates עבדו לטובתנו (רוב ה-blocked
היו counter-trend בבוקר + churn-אחה"צ). **פספוס-אמת אינקרמנטלי ≈ +1R בלבד** (cluster VEGAS/GHOST
ב-PM-fade), והוא **כמעט-כולו רדונדנטי** — אותו דעיכת-אחה"צ נתפסה ע"י id105 GB100-S (12:09, WIN)
+ id107 ZLR-S (12:45, WIN) שכן ירו.

### 🎯 הפספוס-המבני-האמיתי היום (אחד — אחרי ניכוי ה-artifact)
1. **VEGAS / GHOST / FAMIR — זוהו 17×, ירו 0×** (`ready_to_route=False` תמידי). בניגוד ל-HFE/TLB/ZLR
   שנותבו סלקטיבית (נחסמו רק כשפוזיציה כבר פתוחה/cooldown), שלוש התבניות האלה **לעולם אינן מגיעות
   לירי** — נתיב-ירי חסר. השפעת-$ היום זניחה (~+1R, רדונדנטי), אבל זו **דליפת-I-3 מובחנת** שיש לחווט.

> ⚠️ הפריט ה"שני" שדווח בימים קודמים (ramp-פתיחה / "המשך-אחרי-expansion", I-28/D3) **לא תקף היום** —
> ה"ramp +109נק'" @08:35 הוא **artifact של גלגול-החוזה** (7498.5 = פיד-יוני-קפוא), לא מהלך-אמיתי.
> אין ראיה ל-leg-המשך אמיתי-שפוספס היום. I-28/D3 נותר פתוח מימים קודמים אך **לא נצפה היום**.

## 🎯 BENCHMARK — 5 הסלוטים של Michael (ground-truth 06-05, יום-יורד) מול היום (יום-עולה)
| # | סלוט(CT) | סוג(benchmark) | מה קרה היום בסלוט | ירה? | הערה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2/FHB) | פתיחה = **המשך-עולה**, לא reversal | ~✓ id89 08:45 TLB-S (−$101) | **כיוון הפוך** (יום-עולה): id89 short נגד-המהלך הפסיד. (ה"ramp 7498→7607" = artifact-גלגול, לא מהלך-אמיתי) |
| 2 | 9:00–9:05 | LONG טקטי | pullback בתוך עלייה | ✅✅ id92 09:00 TLB-S (WIN) · id93 09:05 HFE-S (WIN) | ירה **בסלוט-מדויק** — אך SHORT (סקאלפ-pullback), לא LONG |
| 3 | 9:20 | SHORT | המשך-עלייה (short היה מפסיד) | ✅ id96 09:25 HFE-S (−$191) | ירה ±5דק', **כיוון-benchmark (SHORT)** — אבל הפסיד ביום-עולה |
| 4 | 9:35 | SHORT | leg-עולה | ✅ id97 09:30 ZLR-**LONG** (WIN **+$289**) | **הסתגל-לכיוון** — LONG עם-המגמה במקום SHORT-benchmark → המנצח-הגדול של היום |
| 5 | 10:00 | SHORT | אמצע ראלי | ✅ id99 10:05 REACTIVE-**LONG** (WIN **+$146**) | **הסתגל-לכיוון** — LONG עם-המגמה → מנצח |

**שורת-benchmark: 5/5 סלוטים עם ירי בסלוט/±10דק' (2/5 בסלוט-מדויק) — התוצאה הטובה ביותר עד כה.**
**הממצא המהותי:** המערכת **לא עקבה עיוורת אחרי תבנית-ה-benchmark** (06-05 = יום-יורד, סלוטים 3–5
SHORT) — אלא **הסתגלה לכיוון-היום-בפועל** (יום-עולה) וירתה **LONG** בסלוטים 4–5 → שני המנצחים
הגדולים (+$289, +$146). זה ההפך מהבעיה ההיסטורית (ירי-נגד-מגמה, I-26/I-28). הסלוטים = תבנית-שעות
תקפה; הכיוון נקבע נכון מ-day_type/trend, לא מה-benchmark.

## פירוק לפי gate
| gate | #setups | סטטוס |
|---|---|---|
| `ready_to_route=False` (I-3) | 40 signal-instances → **אבל 18 S4 כן ירו** | 🟡 **השתפר מהותית** — נותב סלקטיבית. **residual:** VEGAS/GHOST/FAMIR (17, 0-ירי, נתיב חסר) — דגל-CC |
| ירי-נגד-מגמה (I-26/I-28) | ≥3 (id89 08:45 S-לתוך-up · id101/113/114 REACTIVE-LONG לתוך-fade) | 🔴 פתוח — veto-תיאום-מגמה עדיין חסר דו-כיוונית |
| sizing / stop-רחב (I-13) | מפסידי-$-גדולים: id101 −$187.5 (12.5נק') · id96 −$191 (12.75נק') · ZLR 14:55 stop 10נק' | 🔴 פתוח — $-risk לא-מנורמל; D8/טבלת stop-target |
| היעדר detector להמשך-אחרי-expansion | — (ה"ramp" @08:35 = artifact-גלגול, לא מהלך) | ⚪ **לא-נצפה היום** — I-28/D3 פתוח מימים קודמים |
| choppiness / Layer-0 | 0 | ✅ מושבת (standing 2026-06-08) |
| day_type / auth / footprint | 0 | ✅ לא חוסמים (S3_MUTE) |

### תוקנו מול פתוחים
- **🟢 I-3 (ניתוב-S4)** 🔴→🟡 — **S4 ירה 18 עסקאות היום** (ZLR/TLB/HFE/GB100) מול ~0 היסטורית.
  נראה ש-`fire_setup`/טבלת stop-target נחתו. **דגל-CC לאישור מ-diff (Rule 5).** residual: VEGAS/GHOST/FAMIR.
- **🟢 benchmark-כיוון** — סלוטים 4–5 ירו LONG **עם** המגמה (ולא SHORT-benchmark) → 2 המנצחים הגדולים.
  הסתגלות-מגמה עבדה היום.
- **🔴 I-13 sizing/stop-רחב** — נמשך: 13W/13L אבל net **−$394.45** כי המפסידים על stops 10–12.75נק'
  ($-risk לא-מנורמל) מול מנצחים על stops צרים. מצטרף ל-D8.
- **🔴 I-26/I-28 ירי-נגד-מגמה** — נמשך דו-כיווני: id89 SHORT לתוך ramp-עולה (−$101); 3× REACTIVE-LONG
  לתוך דעיכת-אחה"צ (−$60/−$123.75/−$187.5).
- **🟡 I-31 ספירת-ירי** — לא-נבדק כאן; ground-truth = `v9_trades` (26 עסקאות). CC להצליב מול
  `build/pattern-status` counts (חשד-ניפוח קודם).
- **🔴 I-22 pnl_r** — נמשך (מנופח ~50×); כל ה-R בדוח חושב מ-`pnl_usd/risk`.

## נטיפיקציה ל-Michael
**יום-כיסוי חזק (06-15, Trend_Normal עולה). 26 ירי (18×S4 — S4 נותב סוף-סוף!). פספוס-אמת
אינקרמנטלי ≈ +1R בלבד (cluster VEGAS/GHOST ב-PM-fade, כמעט-כולו רדונדנטי ל-GB100/ZLR שכן ירו).
אי-הירי של שאר ה-31 setups חסך ≈ +5.85R (רובם counter-trend). פער-מבני-אחד: VEGAS/GHOST/FAMIR זוהו
17× וירו 0× — נתיב-ירי חסר (residual I-3). benchmark: 5/5 סלוטים אותרו, וסלוטים 4–5 הסתגלו-לכיוון
(LONG עם-המגמה → +$289/+$146) — הטוב ביותר עד כה. החוסם-המוביל ההיסטורי (I-3 ready_to_route) ירד
🔴→🟡 — דגל-CC לאשר את ה-deploy. ⚠️ CAVEAT: גלגול-חוזה יוני→ספטמבר השאיר חלק מפידי-Sierra קפואים
~7498 (session_low + 2× 'uncaptured_move' = artifact-גלגול, לא setup); נתיב-הירי רץ על ספטמבר-חי —
CC לאמת ש-TPO/value-area context לא היה קפוא-יוני בזמן-הירי.**

---
*נוצר אוטונומית ע"י Cowork. CCI מאומת מ-Sierra (חלון 11:30→15:35; בוקר מ-missed-endpoint, טרם-מוצלב).
R מ-pnl_usd/risk — לא pnl_r (I-22). replay = OHLC חי, stop-first. לא שונה קוד. משלים את
`PATTERN_EOD_2026-06-15` — לא מחליף.*
