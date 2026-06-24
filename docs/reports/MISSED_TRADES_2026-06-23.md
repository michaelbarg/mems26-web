# ניתוח עסקאות-שלא-בוצעו · 2026-06-23 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:21 CT** (אחרי סגירת RTH 15:00) ✓. ריצה אוטונומית — Michael לא נוכח.

**הקשר (מאומת מדאטה חיה):** **יום-Normal רוטציוני (day_type=`Normal`, readiness DEGRADED post-close GRAY).** RTH 08:30→15:00 CT.
מבנה: open **7432** (L 7415) → **עליית-בוקר ל-HIGH 7487–7491 (09:15–09:20)** → ירידה ל-7440 (10:25) → chop ל-7476 (12:20) →
**down-leg ל-LOW 7428.75 (13:50)** → bounce 7446–7453 → close **7439.25**. **טווח ~76 נק'.**
trend(Sierra/Woodies, חלון-מאומת-עצמאית 11:15→15:20): BLUE/GRAY-chop בצהריים → RED ב-down-leg (13:05→14:20) → GRAY בסוף.

> 🟢 **הממצא-המהותי — יום-תיקון מול 06-22: near-breakeven, לא יום-הפסד; ושתי הרגרסיות-הגדולות של אתמול נסוגו.**
> **13 ירי-RTH (id213–227), 11 SHORT + 2 LONG, 7W/6L, net −$137.86, win 54%.** ה-setups-האיכותיים שפוספסו מעטים
> (**ΣR-נגד ≈ +3R** — בעיקר LONG-עליית-הבוקר שנסחר-נגדו). מול 06-22: net השתפר מ-**−$1,311.63 ל-−$137.86** (≈90% פחות),
> ה-0-LONG-anomaly (**I-41**) נסוג (היום **2 לונגים** ירו, כולל id227 FAMIR +$112.5), ופיצול-מקור-האמת (**I-40**) **התכנס**
> (trades+bars5min+woodies מסכימים ~7430–7491; אין split של חוזה-roll). ה-over-firing ירד מ-19 ל-13 ירי.

> 🟡 **המנוף-השלילי שנותר (מאומת מ-`v9_trades`):** **counter-trend-בוקר (I-26)** + **stop-רחב בודד (I-13)**.
> 4 שורטי-S4 לתוך עליית-הבוקר (08:55–09:15, 7458→7484 = **−$266.25**, I-26) + id220 REACTIVE_SHORT עם **stop 17.75 נק'**
> (10:25, bounced ל-7457.75 = **−$266.25**, I-13) = **−$532.50 מ-5 ירי**. כל שאר-הירי כיסה כמעט-מלא: ה-down-leg (id221/223/224/225
> = **+$289**) וה-reversal (id226+227 = **+$22.5 נטו**). avg-loss/win = **1.50:1** (מול 2.80 אתמול — שיפור חד).

> ⚪ **הערת-מערכת:** גייטי-ה-chop **מושבתים** (standing 2026-06-08: S2 `choppiness_ok` + Layer-0). **אין המלצה
> להפעיל מחדש** — החלטה-עומדת-של-Michael בלבד (re-enable = שינוי-משטח-סיכון → strategic-stop). תצפית בלבד. **לא שונה קוד.**

## מקורות-אמת + כיסוי (הצלבה ל-CC) — 🟢 ה-split של 06-22 התכנס; bars5min-בוקר שמיש היום

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart?limit=80` | **11:15→15:20 (50 ברים)** | **מקור-אמת ל-CCI = Sierra** (`sierra_woodies_5min_json`, `v9.4.5-wc-fix`, `age=2.5s`, `stale=false`). ⚠️ **buffer-מתגלגל מכסה רק חצי-אחה"צ** — חסר RTH-בוקר 08:30→11:10 (זהה 06-22). זיהוי-zlr/hfe-בוקר **לא-זמין מ-woodies**. |
| `/api/v9/chart/bars5min?limit=80` | 08:30→14:55 (78 ברי-היום) | 🟢 **שמיש היום ומסכים-trades** (08:55 c7465↔id213 e7458 · 09:15 c7486↔id217 e7484 · 13:30 c7447↔id224 e7448). **אין source-split** (≠06-22). 🟡 **2 ברי-זבל בודדים (I-40 residual):** `09:30 c=4214` · `14:30 c=3745` — spike-glitches מבודדים (לא systemic), קלים-לסינון. + 2 ברי-זבל-אתמול בראש ה-buffer (`06-22 17:00 c=13456`). |
| `/api/v9/trades/recent?limit=100` | **היום: 13 (id213–227)** | כיסוי-מלא. **gap-ids 214/222 חסרים** (I-32). R מ-`pnl_usd`, **לא** `pnl_r` (I-22 — `pnl_r` מנופח ל-scratch-wins: id218=**35.6R** על +$44.5). mode=`shadow`. |
| `/api/v9/build/pattern-status` | live post-close | `session_date=2026-06-23` · day_type=**Normal** (s1_day_type_classified ✓) · verdict=**DEGRADED** (`trend_state=GRAY` post-close, צפוי) · `errors=[]`. |
| `/api/v9/missed-trades` | **14:22 בלבד (50)** | ⚠️ כולם `ZLR SHORT @14:22 / ready_to_route=False / r=null` — **buffer-artifact, לא דאטת-סשן** (זהה 06-16/18/19/22). מתעד את ה-ZLR-DOWN-SHORT @~14:15–14:22 שנחסם `ready_to_route=False` (I-3) — **חסימה נכונה היום** (ראה setup #5). |

> 🟢 **שיפור-נתונים מהותי מול 06-22:** אתמול ה-bars5min היה קורּפ-מערכתית (split חוזה-roll, trades~7590 מול woodies~7540)
> ⇒ הבוקר היה **עיוור**. היום, יומיים-אחרי-roll, **שלושת-המקורות התכנסו** (~7430–7491) וה-bars5min-בוקר **שמיש** (פרט ל-2 ברי-glitch
> מבודדים). ⇒ **הבוקר ניתן-לשחזור** מ-bars5min (עם caveat: woodies-CCI עדיין חסר-בוקר ⇒ זיהוי-detector-בוקר נסמך על מבנה-מחיר,
> לא על flag-חי). ניתוח-הפספוסים-המגודר: אחה"צ = woodies-מלא (flags + CCI); בוקר = bars5min-OHLC + טבלת-trades.

## טבלת setups שזוהו-ולא-ירו / לא-נתפסו (rolling-6-bar · stop-first replay)
entry=close/swing-בר-האות · stop=swing בר-האות+הקודם ±0.5 · T1=1R · replay על OHLC-חי, **stop-first**.
אחה"צ = woodies-Sierra-flags חיים; בוקר (setup #1) = bars5min-OHLC (woodies-CCI-blind, caveat Rule 1/2).

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay) | gate-שחסם | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **08:50–09:15** | **LONG עליית-בוקר (breakout/continuation)** | S2/S4 | ⚠️ **bars5min-derived** (woodies-blind; אין flag-CCI חי לבוקר) | ~7458 | ~7448 (10) | 7468 / 7478 | **+2R** (T2; MFE **+3.3R** @09:20 H7491) — lows נשארו ≥7454 ⇒ לא-stopped | **0-LONG-בוקר (I-41) + ירו 4 שורטים-נגד במקום (I-26)** — id213/215/216/217 SHORT לתוך העלייה (−$266.25) | **I-41 / I-26** |
| 11:35–12:35 | **ZLR-UP ×5** (11:35/40/55·12:10/35) | S4 | ✅ `zlr=UP` ×5 | ~7470 | ~7464 (6) | 1R | **−1R/0R** (BLUE/GRAY-chop 7462–7476; 12:05 L**7460.5** < stop ⇒ stop-first) | לא-נותב (LONG ב-BLUE/GRAY-chop) — **דילוג-לגיטימי** | I-41 (legit-skip) |
| 13:00–13:25 | **HFE-UP ×5** (13:00/10/15/20/25) | S4 | ✅ `hfe=UP` ×5 | ~7453 | ~7448 (5) | 1R | **−1R** (RED-drift down; 13:20 L**7447.75** < stop ⇒ stop-first) | לא-נותב (LONG-counter-trend ב-RED) — **דילוג-לגיטימי** | legit-skip |
| 14:10 | **ZLR-DOWN** | S4 | ✅ `zlr=DOWN` | ~7441 | ~7448 (7) | 7434 / 7427 | **+1R** (14:15 L**7434** tags T1) — אך **מתנגש עם ה-LONG-החי id227** (14:00) | not-routed (פוזיציית-LONG פעילה) — conflict | I-3 / conflict |
| ~14:15–14:22 | **ZLR-DOWN ×50** (missed-artifact) | S4 | ✅ (`missed-trades` 50×) | ~7439 | ~7449 (10) | 1R | **−1R** (14:50 H**7453** > stop **לפני** הירידה ⇒ stop-first) | **`ready_to_route=False` (I-3)** — **חסימה נכונה היום** (חסכה −1R) | **I-3 (correct-block)** |
| 15:15 | **ZLR-DOWN** | S4 | ✅ `zlr=DOWN` | ~7438 | ~7444 (6) | 1R | **~0R** (15:20 C**7439** — אין follow-through, near-close) | timeout near-close — **דילוג-לגיטימי** | — |

**ΣR-נגד (פספוס-אמת) ≈ +3R** — שולט: **LONG-עליית-הבוקר (+2R, MFE +3.3R)** שנסחר-נגדו (I-26/I-41); +
ZLR-DOWN @14:10 (+1R, אך התנגש עם id227-החי). שני ה-clusters-של-LONG (ZLR-UP 11:35–12:35 / HFE-UP 13:00–13:25)
היו chop/counter-trend-RED שהיו-נעצרים ⇒ **דילוגים-לגיטימיים**. החסימות `ready_to_route=False` @14:22 (I-3) היו
**נכונות היום** (חסכו −1R) — היפוך מ-06-22 (שם I-3 חסם LONG-מנצח). ⇒ **יום נמוך-פספוסים**, וגם נמוך-נזק (−$138).

## 🟢 הסיפור-האמיתי — יום-תיקון: כיסוי-טוב + 2 רגרסיות-אתמול נסוגו (ground-truth מ-`v9_trades`)
**13 ירי, 11 SHORT + 2 LONG, 7W/6L, net −$137.86, win 54%.** avg-win **+$69.23** מול avg-loss **−$103.75**
(יחס **1.50:1** — מול 2.80 ב-06-22). כל ההפסדים **3-חוזים** (I-34 — `−$123.75/8.25נק'=$15/נק'=3×$5`). הביצוע **כיסה את
ה-down-leg וה-reversal**; ההפסד רוכז ב-**counter-trend-בוקר (I-26)** + **stop-רחב בודד (I-13)**.

| זמן(CT) | id | תבנית | מע' | dir | entry | risk | תוצאה | $ | הערה |
|---|---|---|---|---|---|---|---|---|---|
| 08:55 | 213 | TLB | S4 | SHORT | 7458.25 | 8.25 | LOSS | −123.75 | **short לתוך עליית-בוקר** (I-26) |
| 09:05 | 215 | HFE | S4 | SHORT | 7474.25 | 4.5 | LOSS | −67.5 | **slot-2 benchmark (LONG) — ירה SHORT** לתוך עלייה ל-7487 |
| 09:10 | 216 | HFE | S4 | SHORT | 7478.75 | 2.75 | LOSS | −41.25 | short-נגד (stop צר ⇒ הפסד-קטן) |
| 09:15 | 217 | HFE | S4 | SHORT | 7483.75 | 2.25 | LOSS | −33.75 | short ב-HIGH-היום (7487.5) — נגד |
| 10:20 | 218 | BEAR_FLAG_SHORT | S2 | SHORT | 7446.75 | 10.5 | **WIN** | +44.5 | תפס את הירידה ל-7440; **זוג I-30** עם id219 |
| 10:20 | 219 | REACTIVE_SHORT | S2 | SHORT | 7446.75 | 11 | **WIN** | +38.25 | **entry-זהה ל-id218 (I-30 cluster, אותו בר)** |
| 10:25 | 220 | REACTIVE_SHORT | S2 | SHORT | 7440 | **17.75** | LOSS | **−266.25** | **stop-רחב (I-13)** — bounced ל-7457.75; ההפסד-הגדול-היום |
| 12:45 | 221 | REACTIVE_SHORT | S2 | SHORT | 7467.75 | 9 | **WIN** | +143.12 | **תפס את תחילת ה-down-leg** ✓ מנצח-היום |
| 12:55 | 223 | REACTIVE_SHORT | S2 | SHORT | 7456.25 | 13.5 | **WIN** | +18.12 | המשך-leg (scratch/trail) |
| 13:30 | 224 | REACTIVE_SHORT | S2 | SHORT | 7448.25 | 7.25 | **WIN** | +62.2 | down-leg ל-7428; **זוג I-30** עם id225 |
| 13:30 | 225 | ZLR | S4 | SHORT | 7448.5 | 8.25 | **WIN** | +65.95 | **ZLR-DOWN נותב+ירה+ניצח** (S2+S4 אותו בר, I-30) |
| 13:50 | 226 | REACTIVE_LONG | S2 | **LONG** | 7435.5 | 6 | LOSS | −90 | **LONG-reversal** ב-LOW (7428.75) — מוקדם-מדי, נעצר |
| 14:00 | 227 | FAMIR | S4 | **LONG** | 7436 | 8 | **WIN** | +112.5 | **LONG-reversal ניצח** (+bounce ל-7446) — ה-0-LONG-anomaly נסוג ✓ |

**פילוח:** **counter-trend-בוקר (08:55–09:15, 4 שורטים נגד-עלייה) = −$266.25** (I-26) · **id220 stop-רחב = −$266.25** (I-13) ·
**down-leg-shorts (12:45–13:30, 4 ירי) = +$289** ✓ · **reversal-longs (13:50–14:00) = +$22.5 נטו** ✓. ה-2 מקורות-ההפסד
(−$532.50) מול שאר-היום (+$394.64) ⇒ net −$137.86. **ניתוב דו-כיווני עבד היום** (ZLR-DOWN-S4 ירה+ניצח id225; LONG-reversal
ירה id226/227) — היפוך מ-19/19-SHORT של 06-22.

## 🎯 BENCHMARK — 5 הסלוטים של Michael (06-05, יום-יורד) מול היום
היום **מבנה-שונה מה-benchmark** (06-05 = down-day-נקי; היום = עלייה-בוקר→down-leg-אחה"צ) ⇒ ה-benchmark template-כיווני-רופף.

| # | סלוט(CT) | סוג(benchmark) | מה קרה היום | ירה? | הערה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2/FHB) | מחיר עולה מ-LOW-פתיחה 7415→7436 | ❌ **אין-ירי** (ראשון 08:55) | reversal-LONG מ-התחתית היה-נכון; אין FHB-setup ב-08:35 |
| 2 | 9:00–9:05 | **LONG טקטי** | מחיר 7474→7479 (עולה חזק ל-HIGH 7487) | ⚠️ id215 **SHORT** (−$67.5) | **שגיאת-כיוון מאומתת:** benchmark=LONG, ירה SHORT — **זהה ל-setup #1 (פספוס-הבוקר)** |
| 3 | 9:20 | SHORT | **TOP-היום** 7491 → ירידה ל-7440 | ⚠️ **פער-כניסה** 09:15–10:20 | benchmark-SHORT מה-top היה-נכון; פספס את ה-leg, נתפס ב-10:20 |
| 4 | 9:35 | SHORT | המשך-ירידה 7470→7459 | ⚠️ פער-כניסה | חלק מאותו פער 09:15–10:20 |
| 5 | 10:00 | SHORT | ירידה ל-7440 | ✅ id218/219 **SHORT** (10:20, **+$83**) | **כיוון=benchmark, 2×WIN** — ההתאמה-הנקייה ✓ |

**שורת-benchmark: 2/5 סלוטים ירו (slot-2 כיוון-שגוי + slot-5 כיוון-מנצח); 1/5 כיוון-מנצח (slot-5).**
**K/5 = 2/5 ירו · 1/5 כיוון-מנצח.** ה-benchmark-validation-המרכזי: **slot-2 (9:00–9:05 LONG)** = בדיוק פספוס-עליית-הבוקר
שזוהה עצמאית (setup #1) — המערכת ירתה SHORT לתוך עלייה-מאומתת ל-7487. סלוטים 3–4 (SHORT מה-top) = פער-כניסה
09:15–10:20 שנסגר ב-10:20 (slot-5 ✓). היום ה-bias-היומי **דו-כיווני** (עלייה→ירידה) ⇒ ה-benchmark-down-day תפס רק את החצי-השני.

## פירוק לפי gate
| gate | #setups | סטטוס |
|---|---|---|
| **counter-trend-בוקר (I-26 / root=I-42)** | 4 (08:55–09:15, −$266.25) | 🟡 **המנוף-המוביל-שנותר** — short לתוך עליית-בוקר. **מנגנון-השורש (§EOD-15:12): I-42 — playbook-מת**: HFE×Trend_Normal/BLUE (תא **SKIP** ב-YAML) ירה `blocked_by=null` (id215/216/217). + D29: gates-כיוון (HTLB_DIRECTION_GATE/TLB_SPEC_V2) **טרם-חיים** ב-08:55–09:15 (הודלקו תוך-סשן). **stops-צרים ⇒ נזק-מוגבל** (≠06-22 −$516). |
| **stop-רחב (I-13)** | 1 (id220, risk 17.75, −$266.25) | 🟡 **ההפסד-הבודד-הגדול** — REACTIVE_SHORT stop 17.75נק' bounced. adaptive_stop/ATR-cap לא-הידק. |
| **0-LONG / directional (I-41)** | 2 LONG ירו (≠0) | 🟢 **נסוג** — היום 2 לונגים (id226/227) כולל מנצח; ניתוב דו-כיווני עבד. (פספוס-LONG-בוקר נותר — setup #1.) |
| **ready_to_route=False (I-3)** | 50× ZLR-DOWN @14:22 | 🟢 **חסימה נכונה היום** — ה-ZLR-DOWN-SHORT היו-נעצרים (14:50 H7453 לפני הירידה); I-3 חסך −1R. היפוך מ-06-22. |
| **source-split (I-40)** | 0 split | 🟢 **התכנס** — trades+bars5min+woodies מסכימים ~7430–7491 (יומיים-post-roll). residual: 2 ברי-glitch מבודדים. |
| **duplicate/cluster (I-30)** | זוג-10:20 + זוג-13:30 | 🟡 **נמשך אך זול היום** — id218≡219 (entry 7446.75 זהה) + id224/225 (13:30); שניהם **ניצחו** ⇒ עלות-נמוכה. |
| **sizing לא-מורד (I-34)** | כל 6 ההפסדים (3-חוזים) | 🟡 **חוסם-LIVE** — `$15/נק'=3×$5` על כל הפסד; sizing לא מצמצם חוזה. (נזק-מתון היום בזכות stops-צרים פרט ל-id220.) |
| **over-firing (chop-gate מושבת)** | 13 ירי (מול 19) | ⚪ ירד; גייט-chop מושבת-בכוונה (standing 06-08). תצפית בלבד — **לא-להפעיל בלי Michael.** |
| day_type / footprint (S3) | 0 חוסמים | 🟢 לא-חוסם (S3_MUTE / I-11). day_type=Normal סווג. |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🟢 I-41 (0-LONG) נסוג** — היום **2 לונגים ירו** (id226 −$90, id227 +$112.5) מול 0/19 ב-06-22. ה-directional-veto התיר LONG
  ב-reversal; ה-down-leg נסחר SHORT וה-bounce LONG. **נותר:** LONG-עליית-הבוקר (setup #1) עדיין-לא-נתפס (I-26/I-41-בוקר).
- **🟢 I-40 (source-split) התכנס** — יומיים-אחרי-roll-יוני, trades+bars5min+woodies מסכימים. **bars5min-בוקר שמיש** (≠06-22-עיוור).
  residual: 2 ברי-glitch מבודדים (09:30 c=4214 · 14:30 c=3745) — דגל-CC: סינון-spike ב-`/chart/bars5min`.
- **🟢 I-3 (ready_to_route) — חסימה נכונה היום** — חסם 50× ZLR-DOWN-SHORT @14:22 שהיו-נעצרים (−1R) ⇒ חסך הפסד. היפוך מ-06-22.
- **🟡 I-26 (counter-trend-בוקר) נמשך** — 4 שורטים לתוך עליית-7458→7484 (−$266.25). **המנוף-המוביל-שנותר.** trend-align-veto עדיין
  לא-חוסם-בוקר (trend BLUE, flag-OFF). אך **stops-צרים ⇒ −$266 מול −$516 אתמול.**
- **🟡 I-13 (stop-רחב) נמשך** — id220 risk 17.75נק' = ההפסד-הבודד-הגדול (−$266.25). adaptive_stop/ATR-cap צריך הידוק.
- **🟡 I-34 (sizing) נמשך — חוסם-LIVE** — כל הפסד 3-חוזים; sizing לא-מורד. נזק-מתון היום בזכות stops-צרים.
- **🟡 I-30 (cluster) נמשך-זול** — זוג-10:20 (entry זהה) + זוג-13:30; שניהם ניצחו ⇒ עלות-נמוכה היום (≠triple-10:20 של 06-22).
- **🟡 I-32 (gap-ids) נמשך** — 214/222 חסרים ב-`v9_trades`. **🔴 I-22** נמשך (R מ-pnl_usd; pnl_r מנופח 35.6R ל-scratch).
- **⚠️ מגבלת-נתונים נמשכת:** woodies-buffer מכסה רק 11:15→15:20 ⇒ **woodies-CCI-בוקר חסר** (setup #1 = bars5min-derived, לא flag-חי).
  דגל-CC: retention woodies-buffer ל-RTH-מלא (כדי לזהות zlr/hfe-בוקר חי, לא רק מבנה-מחיר).

## נטיפיקציה ל-Michael
**יום-Normal-רוטציוני (open 7432→HIGH 7491→LOW 7428.75→close 7439, טווח 76נק'). ΣR-נגד(פספוס-אמת) ≈ +3R** —
בעיקר **LONG-עליית-הבוקר** (7458→7491, +2R/MFE+3.3R) שהמערכת **ירתה-נגדו SHORT** (slot-2-benchmark מאומת; I-26/I-41-בוקר);
+ ZLR-DOWN @14:10 (+1R, התנגש עם id227-החי). **יום נמוך-פספוסים וגם נמוך-נזק.** **הסיפור-האמיתי: יום-תיקון מול 06-22 —
net השתפר מ-−$1,311.63 ל-−$137.86, 2 לונגים ירו (I-41 נסוג), source-split התכנס (I-40), I-3 חסם-נכון.** ההפסד רוכז ב-2:
counter-trend-בוקר (4 שורטים, −$266/I-26) + stop-רחב-בודד (id220, −$266/I-13). ה-down-leg וה-reversal **כוסו** (+$311).
benchmark: **2/5 ירו, 1/5 כיוון-מנצח** (slot-5). **🟠 דגלי-CC:** (1) trend-align-veto-בוקר דו-כיווני (I-26 — המנוף-המוביל);
(2) ATR-cap/adaptive_stop להידוק stop-רחב (I-13); (3) sizing→PnL (I-34, חוסם-LIVE); (4) retention woodies ל-RTH-מלא +
סינון-spike bars5min (I-40 residual). **החוסם-המוביל: counter-trend-בוקר SHORT (I-26)** (גייט-chop מושבת — standing-Michael, לא-להפעיל).

---
*נוצר אוטונומית ע"י Cowork (15:21 CT). CCI/flags מאומת מ-Sierra (`sierra_woodies_5min_json`, כיסוי-עצמאי 11:15→15:20);
בוקר (setup #1) מ-bars5min-OHLC (woodies-CCI-blind, caveat Rule 1/2; bars5min-trades מסכימים ⇒ אין split). R מ-`pnl_usd`
(I-22; pnl_r מנופח על scratch). replay = OHLC-חי, stop-first. חישוב אומת בקוד: 7W +$484.64 / 6L −$622.50 / net −$137.86 /
win 53.8% / avg-loss/win 1.50 / כל-הפסד 3-חוזים ($15/נק'). counter-trend-בוקר(08:55–09:15)=−$266.25 · id220-stop-רחב=−$266.25 ·
down-leg(12:45–13:30)=+$289 · reversal=+$22.5. ΣR-נגד(פספוס)≈+3R (LONG-בוקר +2R + ZLR-DOWN@14:10 +1R). missed-endpoint =
50 buffer-artifact (14:22 ZLR-DOWN, I-3 חסם-נכון). bars5min 2 ברי-glitch (09:30/14:30). אין source-split (I-40 התכנס). לא שונה קוד.*
