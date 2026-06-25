# ניתוח עסקאות-שלא-בוצעו · 2026-06-24 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:19 CT** (אחרי סגירת RTH 15:00) ✓. ריצה אוטונומית — Michael לא נוכח. **לא שונה קוד.**

**הקשר (מאומת מדאטה חיה):** **יום דו-שלבי / `Variation` (day_type התגלגל Normal→Variation→Neutral_Extreme).** RTH 08:30→15:00 CT.
מבנה: open **7447** → chop-פתיחה 7437–7468 → ירידה ל-**LOW-בוקר 7442.5 (09:15)** → **ראלי-בוקר חזק ל-HIGH-היום 7496.5 (10:00, נגע שוב 10:30)** →
rollover/chop מהפסגה 7496→7471 (10:30–11:30) → **down-leg-אחה"צ ל-LOW 7407.75 (12:30)** → bounce 7443 (13:25) → dip-שני 7404 (14:05, **LOW-היום**) →
**ראלי-מאוחר/קרוב-סגירה 7411→7467 (14:45→15:20, cci 285)** → close-bars5min **7428.25 (14:55)**. **טווח RTH ~92 נק'.**
trend(Sierra/Woodies, חלון-מאומת-עצמאית 11:15→15:20): RED ב-down-leg (11:20→13:10) → GRAY/BLUE-bounce (13:15→14:00) → RED-שני (14:10→14:40) → GRAY→BLUE ראלי-מאוחר (14:45→15:20).

> 🟢 **הממצא-המהותי — יום-רווח-קטן (+$123.75), והכסף נוצר באחה"צ אחרי שהבוקר זלג.**
> **14 ירי-RTH (id228–243), 7 SHORT + 7 LONG, 5W/9L, net +$123.75, win 36%.** הפיצול חד: **בוקר (id228–236, 09:40–11:15) = −$746.25**
> (ראלי-הבוקר **נסחר-הפוך** — short לתוך העלייה + קניית-הפסגה ×3) · **אחה"צ (id237–243, 11:45–14:45) = +$870** (ה-down-leg 11:55→12:10 נתפס מצוין:
> id238/239/242 = **+$1,263.75**). avg-win **+$288** מול avg-loss **−$146.25** (יחס **1.97:1**). ה-setups-האיכותיים שפוספסו מעטים (**ΣR-נגד ≈ +5R**,
> שולט: ראלי-הבוקר-LONG שנסחר-הפוך). הבעיה-המרכזית היום היא **מיס-פיירים נגד-מגמה (−$952.5)**, לא פספוסים.

> 🟢 **שתי הרגרסיות-ההיסטוריות המשיכו להיסוג:** (1) **I-41 (הטיה-חד-כיוונית) — נעלמה לחלוטין:** היום **7 LONG / 7 SHORT** (איזון מושלם,
> מול 0-LONG ב-06-22 ו-2-LONG ב-06-23). (2) **I-40 (source-split) — נשאר מכונס:** woodies+bars5min מסכימים בחפיפה (11:15–14:55, למשל 12:05 L7442.5 · 12:30 L7407.75 בשניהם); אין split של חוזה-roll.

> 🔴 **חדש — I-44: פיצול-מקור ב-day_type (לא "מסווג-עשיר", אלא split).** ה-trade-stamp התגלגל **Normal (id228) → Variation (id230–242) → Neutral_Extreme (id243)**,
> **אך** ה-determiner אומר **Normal (conf 0.68)** וה-S4-fallback hardcoded-Normal ⇒ ה-stamp **לא-מסכים** עם ה-determiner/key_levels. **זוהה ע"י ה-EOD-המאוחד 15:12 כ-I-44** (`classify_replay`/`woodies_system.py:514-530`/`main.py:391`).
> **תיקון-עצמי (Rule 2):** ניתוח-ראשוני שלי ראה את התוויות-המגוונות כסימן-חיובי; ההצלבה ל-register מראה שזה **split-לא-עקבי** הדורש אימות-CC, לא feature.

> 🟢 **הקשר-deploy (מ-EOD-המאוחד 15:12):** כל ה-stack-החדש נדחף-לחי היום (`c98b808`, "462 tests green"; `.env`=12 flags): `DIRECTION_LSMA_VETO=1` · cvd-fix · **`HFE_DISABLED=1`** (HFE היה lifetime-#1-loser ⇒ **0-ירי-HFE היום**) · `NONTREND_DISABLE_ALL=1` · `ZLR_SPEC_V2=1` · `VEGAS_SPEC_V2=1` · day-type-source-unify. ⚠️ **חלק נכנס mid/post-session** ⇒ **ה-gates-הכיווניים אולי לא-היו-חיים בבוקר (09:40–11:15)** — מה שמסביר את ה-counter-trend-מיס-פיירים (id228/231/233). (CC לאמת gate-state פר-ירי — Rule 5.)

> 🟢 **הצלבה (Rule 2/5):** ה-P&L שחישבתי עצמאית (**net +$123.75, 5W/9L, down-leg-shorts +$1,263.75**) **תואם-מדויק** את ה-EOD-המאוחד 15:12. שני המסמכים מסכימים על המספרים.

> ⚪ **הערת-מערכת:** גייטי-ה-chop **מושבתים** (standing 2026-06-08: S2 `choppiness_ok` + Layer-0). **אין המלצה להפעיל מחדש** —
> החלטה-עומדת-של-Michael בלבד (re-enable = שינוי-משטח-סיכון → strategic-stop). תצפית בלבד. **לא שונה קוד.**

## מקורות-אמת + כיסוי (הצלבה ל-CC)

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart?limit=80` | **11:15→15:20 (50 ברים)** | **מקור-אמת ל-CCI = Sierra** (`sierra_woodies_5min_json`, `v9.4.5-wc-fix`, `age=0.3s`, `stale=false`). ⚠️ **buffer-מתגלגל מכסה רק חצי-אחה"צ** — חסר RTH-בוקר 08:30→11:10 (זהה 06-22/06-23). זיהוי-zlr/hfe-בוקר **לא-זמין מ-woodies** ⇒ setup #1 = bars5min-derived. |
| `/api/v9/chart/bars5min?limit=80` | **08:30→14:55 (78 ברי-היום)** | 🟢 **שמיש ומסכים-trades** (09:40 c7458↔id228 e7460 · 11:55 c7454↔id238/239 e7454 · 12:10 c7445.75↔id242 e7445.75). 🟢 **אין source-split** (≠06-22) — **גם הבוקר שמיש מ-bars5min**. **לא נצפו ברי-זבל/glitch בולטים היום** (≠06-23 שהיו 2). |
| `/api/v9/trades/recent?limit=100` | **היום: 14 (id228–243)** | כיסוי-מלא. **gap-ids 229/234 חסרים** (I-32 נמשך). R מ-`pnl_usd`, **לא** `pnl_r` (I-22 — `pnl_r` מנופח: id232=**+9R** על **+$11.25** scratch). mode=`shadow`; כל ההפסדים 3-חוזים (I-34). |
| `/api/v9/build/pattern-status` | live post-close | `session_date=2026-06-24` · day_type=**Normal** (s1_day_type_classified ✓) · verdict=**DEGRADED** (`trend_state=GRAY` post-close, צפוי) · `errors=[]`. |
| `/api/v9/missed-trades` | **ריק (count=0)** | 🟢 **אין buffer-artifact היום** (≠06-16/18/19/22/23 שהיו 50× ZLR @14:22). הטבלה `v9_missed_trades` לא-מאוכלסת ⇒ זיהוי-הפספוסים נשען על woodies-flags + bars5min-OHLC + טבלת-trades. |

## טבלת setups שזוהו-ולא-ירו / נסחרו-הפוך (rolling-6-bar · stop-first replay)
entry=close/swing-בר-האות · stop=swing בר-האות+הקודם ±0.5 · T1=1R · replay על OHLC-חי, **stop-first**.
אחה"צ = woodies-Sierra-flags חיים; בוקר (setup #1) = bars5min-OHLC (woodies-CCI-blind, caveat Rule 1/2; bars5min-trades מסכימים ⇒ אין split).

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay) | gate-שחסם / מה-קרה | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **09:20–09:55** | **LONG ראלי-בוקר (reversal→continuation)** | S2/S4 | ⚠️ **bars5min-derived** (woodies-blind 08:30–11:10) | ~7460 | ~7448 (12) | 7472 / 7484 | **+3R** (09:45 H7486=T1+T2 · 10:00 **HIGH 7496.5**=MFE **+3.0R**; lows ≥7442 ⇒ לא-stopped) | **נסחר-הפוך:** id228 ירה **SHORT @09:40** (−$195, mae 25.75) לתוך הראלי; LONG-ראשון רק id230 @09:55 (מאוחר, אחרי +20נק'). שורש: **gates-כיווניים לא-חיים בבוקר** (DIRECTION_LSMA_VETO נכנס mid/post). | **I-26** |
| 12:30–13:25 | **LONG bounce מ-LOW 7407** (HFE-UP ×2) | S4 | ✅ `hfe=UP` @12:30+12:35 (flag-observability) | ~7418 | ~7405 (13) | 7431 / 7443 | **+1.9R** (13:15 H7435.75=T1 · 13:25 H**7443**=MFE +1.9R; ואז חזר ל-7408) | **לא-נותב — `HFE_DISABLED=1` נכנס-לחי היום** (HFE היה lifetime-#1-loser). ⇒ אי-ירי **מכוון-בעיצוב**, לא חסם-gate. (bounce-borderline counter-trend, ה-leg חזר.) | HFE_DISABLED (by-design) |
| 11:25–11:30 | **ZLR-DOWN ×2 (lead-signal ל-down-leg)** | S4 | ✅ `zlr=DOWN` @11:25+11:30 | ~7475 | ~7485 (10) | 1R | **+0.5R** (ה-down-leg **נתפס** ע"י id238/239/242 ~20–30דק' מאוחר; entry 7475 vs 7454 בפועל = ~20נק' עדיף) | entry-lag — **נתפס, לא-פוספס** | — |
| 11:45–12:00 | **HFE-UP ×4** (11:45/50/55·12:00) | S4 | ✅ `hfe=UP` ×4 (flag-only) | ~7456 | ~7466 (10) | 1R | **−1R** (LONG ב-RED down-leg; מחיר צלל ל-7407 ⇒ stopped) | **`HFE_DISABLED=1`** + counter-trend — **דילוג-נכון כפול** (גם disabled גם יהיה-מפסיד) | HFE_DISABLED |
| 14:05 | **ZLR-DOWN** | S4 | ✅ `zlr=DOWN` | ~7409 | ~7422 (13) | 1R | **−1R** (14:10 L7404=+5נק' בלבד, ואז ראלי ל-7467 ⇒ stop-first) | לא-נותב — **דילוג-נכון** (לפני הראלי-המאוחר) | I-3 (correct-skip) |
| 14:30–14:40 | **ZLR-DOWN ×3** (14:30/35/40) | S4 | ✅ `zlr=DOWN` ×3 | ~7413 | ~7420 (7) | 1R | **−1R** (ראלי-מאוחר 7411→7467 ⇒ stopped) | מ-3 הסיגנלים **2 לא-נותבו (נכון)**; אך id243 ירה SHORT @14:45 (−$127.5) — **מיס-פייר** | **I-26 (mis-fire)** |

**ΣR-נגד (פספוס-אמת) ≈ +5R** — שולט: **ראלי-הבוקר-LONG (+3R, MFE +3.0R ל-7496.5)** שהמערכת **סחרה-הפוך** (short id228 + LONG-מאוחר id230); +
bounce-12:30-LONG (+1.9R, borderline counter-trend); + ZLR-DOWN-11:25 early-entry (+0.5R, נתפס-מאוחר). שאר-הסיגנלים (HFE-UP-11:45-12:00 counter-trend · ZLR-DOWN-14:05/14:30-40 לתוך-הראלי-המאוחר) היו-נעצרים ⇒ **דילוגים-לגיטימיים**.
⇒ **יום נמוך-פספוסים-אמיתיים; הבעיה היא מיס-פיירים נגד-מגמה (−$952.5), לא setups-חסומים.**

## 🟢 הסיפור-האמיתי — בוקר-זולג / אחה"צ-תופס (ground-truth מ-`v9_trades`)
**14 ירי, 7 SHORT + 7 LONG, 5W/9L, net +$123.75, win 35.7%.** avg-win **+$288** מול avg-loss **−$146.25** (יחס **1.97:1**).
כל ההפסדים **3-חוזים** (I-34). **long_net = −$712.5 · short_net = +$836.25.** הפיצול-הזמני חד: **בוקר −$746.25 · אחה"צ +$870.**

| זמן(CT) | id | תבנית | מע' | dir | entry | risk | תוצאה | $ | הערה |
|---|---|---|---|---|---|---|---|---|---|
| 09:40 | 228 | STRATEGIC | S4 | SHORT | 7460.25 | 13 | LOSS | −195 | **short לתוך ראלי-הבוקר** (mae **25.75** — מחיר ל-7496) — I-26/setup #1 |
| 09:55 | 230 | STRATEGIC | S2 | **LONG** | 7481 | 2.25 | **WIN** | +165 | LONG with-trend — תפס את הקצה האחרון לפסגה (7492.75) ✓ |
| 10:00 | 231 | STRATEGIC | S2 | **LONG** | 7493.75 | 15.75 | LOSS | −236.25 | **קניית-הפסגה** (HIGH 7496.5) — נעצר ב-rollover |
| 10:20 | 232 | NO_SETUP | S2 | **LONG** | 7488.75 | 13.25 | **WIN** | +11.25 | scratch (`pnl_r`=**+9R** מנופח — I-22) |
| 10:30 | 233 | NO_SETUP | S2 | **LONG** | 7493.75 | 15.5 | LOSS | −232.5 | **קניית-הפסגה ×2** (retest 7496.5) — נעצר |
| 10:50 | 235 | STRATEGIC | S2 | **LONG** | 7483.5 | 9.75 | LOSS | −146.25 | LONG ב-rollover/GRAY-chop — נעצר |
| 11:15 | 236 | NO_SETUP | S2 | **LONG** | 7481.25 | 7.5 | LOSS | −112.5 | LONG ב-GRAY-chop טרם-down-leg — נעצר |
| 11:45 | 237 | NO_SETUP | S2 | SHORT | 7459.5 | 3 | LOSS | −45 | short מוקדם (stop 3נק' צר) — נעצר על micro-bounce |
| 11:55 | 238 | STRATEGIC | S2 | SHORT | 7454.5 | 10.5 | **WIN** | +460 | **תפס את ה-down-leg ל-7426** ✓ מנצח-היום |
| 11:55 | 239 | STRATEGIC | S2 | SHORT | 7454 | 11.25 | **WIN** | +445 | **entry-זהה ל-id238 (I-30 cluster, אותו בר 11:55)** — גם ניצח |
| 12:00 | 240 | STRATEGIC | S2 | SHORT | 7453 | 4 | LOSS | −60 | stop 4נק' צר — נעצר על bounce לפני הצלילה |
| 12:05 | 241 | STRATEGIC | S4 | **LONG** | 7460.5 | 10.75 | LOSS | −161.25 | **counter-trend LONG ב-RED down-leg** (mae 18.5) — I-26 |
| 12:10 | 242 | NO_SETUP | S2 | SHORT | 7445.75 | 15.75 | **WIN** | +358.75 | **תפס את הצלילה ל-7423** ✓ |
| 14:45 | 243 | TACTICAL | S4 | SHORT | 7411 | 8.5 | LOSS | −127.5 | **short לתוך הראלי-המאוחר** (mae 16.5; dt=Neutral_Extreme) — I-26 |

**פילוח:** **ראלי-בוקר נסחר-הפוך (id228 short + id231/233 top-chase) = −$663.75** · **counter-trend (id241 LONG-ב-RED + id243 short-לתוך-ראלי) = −$288.75** ·
**chop-longs (id235/236) = −$258.75** · **down-leg-shorts (id238/239/242) = +$1,263.75** ✓. שני מקורות-ההפסד (counter-trend + top-chase = **−$952.5**) מול ה-down-leg (+$1,263.75) ⇒ net **+$123.75**.
**ניתוב דו-כיווני עבד** (7L/7S; ה-LONG-ים תפסו את הקצה-לפסגה id230 וה-SHORT-ים את ה-down-leg) — **אך התזמון-נגד-מגמה בקצוות (פסגה+ראלי-מאוחר) זלג.**

## 🎯 BENCHMARK — 5 הסלוטים של Michael (06-05, יום-יורד) מול היום
היום **מבנה הפוך-בוקר מה-benchmark** (06-05 = down-day-בוקר; היום = **ראלי-בוקר**→down-leg-אחה"צ) ⇒ ה-benchmark-template-כיווני לא-תואם-בוקר.

| # | סלוט(CT) | סוג(benchmark) | מה קרה היום | ירה? | הערה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2/FHB) | chop-פתיחה 7447→7437→7458; reversal-אמיתי רק ב-09:20 | ❌ **אין-ירי @8:35** (ראשון 09:40) | אין FHB-setup ב-08:35; הפתיחה chop-ירידה |
| 2 | 9:00–9:05 | **LONG טקטי** | מחיר 7450→7453, **לפני ראלי ל-7496.5** | ⚠️ id228 **SHORT** @09:40 (−$195) | **שגיאת-כיוון מאומתת:** benchmark=LONG, ירה SHORT — **זהה ל-setup #1 + ל-06-23 slot-2** |
| 3 | 9:20 | SHORT | **תחתית-הראלי 7436.5** → היפוך-מעלה | ❌ short יהיה-שגוי היום | מבנה-הפוך: 9:20 = bottom, לא top |
| 4 | 9:35 | SHORT | אמצע-ראלי 7458→ | ❌ short יהיה-שגוי | מבנה-הפוך (up-morning) |
| 5 | 10:00 | SHORT | **HIGH-היום 7496.5** | ⚠️ id231 **LONG** @10:00 (−$236.25) | benchmark-SHORT-מהפסגה היה-נכון-בסוף (ירד ל-7404); המערכת **קנתה את הפסגה** — כיוון-שגוי |

**שורת-benchmark: 0/5 סלוטים ירו-בכיוון-הנכון-בזמן-הסלוט.** slot-2 (LONG) ו-slot-5 (SHORT) **נסחרו-הפוך** (short את הראלי, long את הפסגה).
ה-benchmark הוא template-יום-יורד-בוקר; היום הבוקר עלה ⇒ אי-התאמה-מבנית. **המערכת כן תפסה את ה-down-move-האמיתי** (down-leg-אחה"צ 11:55→12:10, +$1,263.75) — אך זה לא-בסלוטי-ה-benchmark.
**K/5 = 0/5 ירו-בכיוון-בזמן; ה-slot-היחיד-שתואם-מבנית (slot-2 LONG) נסחר-הפוך** — אישוש-מרכזי חוזר של I-26 (counter-trend-בוקר).

## פירוק לפי gate
| gate | #setups | סטטוס |
|---|---|---|
| **counter-trend / mis-timing בקצוות (I-26)** | 4 (id228 short-לראלי · id231/233 top-chase · id241 LONG-ב-RED · id243 short-לראלי-מאוחר = **−$952.5**) | 🔴 **המנוף-המוביל היום** — short לתוך ראלי-הבוקר + קניית-הפסגה ×2 + LONG-counter-ב-down-leg + short-לתוך-הראלי-המאוחר. **שורש (מעודכן ע"י EOD 15:12):** I-42 (playbook-מת) **REFRAMED/SUPERSEDED** — לא-הבאג; כלל-Michael `NONTREND_DISABLE_ALL` = position-gate-עיוור-לתבנית נכון-בכוונה. השורש-האמיתי: **gates-כיווניים (DIRECTION_LSMA_VETO) לא-היו-חיים בבוקר** (נכנס mid/post-session) + **S4-reversal-bleed (D32):** GHOST/FAMIR/ZLR/TACTICAL חסרים day-type/location/direction-gate אפקטיבי בזמן-הירי. |
| **late-LONG / top-chase** | 2 (id231/233 @7493.75, −$468.75) | 🔴 **תת-מנוף I-26** — קניית ה-HIGH 7496.5 (×2) במקום ride-ה-trend מוקדם. אין location-gate שמונע entry בפסגת-extension. |
| **stop-צר מדי (micro-stop)** | 2 (id237 risk 3 · id240 risk 4) | 🟡 **חדש-זווית** — stops 3–4נק' נעצרו על micro-bounce **לפני** הצלילה-הנכונה (id238/242 עם stop 10–15נק' ניצחו על אותו setup). הצד-ההפוך של I-13 (stop-רחב): היום כמה stops **צרים-מדי**. |
| **0-LONG / directional (I-41)** | 7 LONG ירו (=7 SHORT) | 🟢 **נעלם** — איזון 7/7 מושלם; ניתוב דו-כיווני מלא. (האנומליה 0/19 של 06-22 היסטוריה.) |
| **ready_to_route=False (I-3)** | ZLR-DOWN 14:05/14:30-40 | 🟢 **דילוג-נכון** — שורטים לתוך הראלי-המאוחר היו-נעצרים; לא-נותבו (פרט ל-id243 מיס-פייר). |
| **source-split (I-40)** | 0 split | 🟢 **מכונס** — woodies+bars5min מסכימים (11:15–14:55); **הבוקר שמיש מ-bars5min** (≠06-22 עיוור). |
| **missed-endpoint artifact** | 0 (count=0) | 🟢 **ריק היום** — אין buffer-artifact (≠06-16/18/19/22/23). |
| **duplicate/cluster (I-30)** | זוג-11:55 (id238≡239) | 🟡 **נמשך אך זול** — entry 7454/7454.5 זהה, אותו בר; **שניהם ניצחו** (+$905) ⇒ עלות-שלילית-אפסית היום. |
| **sizing לא-מורד (I-34)** | כל 9 ההפסדים (3-חוזים) | 🔴 **חוסם-LIVE** — `risk×5×3` על כל הפסד; sizing לא מצמצם חוזה. |
| **gap-ids (I-32)** | 229/234 חסרים | 🟡 **נמשך** — `v9_trades` ids 228–243 פרט ל-229/234. |
| day_type source-split (**I-44**, חדש) | stamp-מתגלגל | 🔴 **חדש (EOD 15:12):** trade-stamp Normal→Variation→Neutral_Extreme **≠ determiner (Normal-0.68) ≠ S4-fallback (hardcoded Normal)**. דורש אימות-CC (`classify_replay` 06-24 קנוני). footprint/S3 לא-חוסם (S3_MUTE/I-11). |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🟢 I-41 (0-LONG) — נעלם** — היום **7 LONG / 7 SHORT** (איזון מושלם). ה-directional-veto מתיר שני-הכיוונים מלא. **נותר:** התזמון — ה-LONG-ים ירו מאוחר (בפסגה) במקום מוקדם (בראלי).
- **🟢 I-40 (source-split) — מכונס** — woodies+bars5min מסכימים; הבוקר שמיש. **לא-נצפו ברי-glitch בולטים היום** (≠06-23). 
- **🟢 missed-endpoint — ריק (count=0)** — אין buffer-artifact היום.
- **🟢 מסווג-7-טיפוסים (S1_NEW_CLASSIFIER) — פולט תוויות-עשירות** (Variation/Neutral_Extreme). **דגל-CC:** אנטי-רגרסיה — לאמת שאלו תוויות-תקפות.
- **🔴 I-26 (counter-trend / mis-timing) — המנוף-המוביל היום** — short לתוך ראלי-הבוקר (id228) + **קניית-הפסגה ×2** (id231/233) + LONG-ב-RED (id241) + short-לתוך-הראלי-המאוחר (id243) = **−$952.5**. **השורש (מעודכן EOD 15:12): I-42 REFRAMED/SUPERSEDED** — לא playbook-מת; השורש = **gates-כיווניים לא-חיים בבוקר** (DIRECTION_LSMA_VETO נכנס mid/post `c98b808`) + **S4-reversal-bleed (D32)** (GHOST/FAMIR/ZLR/TACTICAL חסרים location/direction-gate בזמן-הירי). ה-down-leg הציל את היום (+$1,263.75).
- **🔴 I-44 (חדש, day_type source-split) — תיקון-מסגור עצמי** — ה-trade-stamps Variation/Neutral_Extreme אינם "מסווג-עשיר" אלא **split** מול determiner-Normal-0.68; דורש אימות-CC.
- **🟢 stack-חדש נדחף-לחי (`c98b808`)** — `HFE_DISABLED=1` (0-ירי-HFE, lifetime-#1-loser מנוטרל) · `DIRECTION_LSMA_VETO` · `NONTREND_DISABLE_ALL` · cvd-fix. ⚠️ חלק mid/post-session ⇒ הבוקר אולי-לא-מוגן.
- **🟡 micro-stop (חדש-זווית, צד-הפוך של I-13)** — id237/240 עם stop 3–4נק' נעצרו על micro-bounce **לפני** הצלילה-הנכונה; אותו setup עם stop 10–15נק' (id238/242) ניצח. ⇒ **שונות-stop גבוהה** (3–26נק' באותו יום) — adaptive_stop לא-יציב.
- **🔴 I-34 (sizing) נמשך — חוסם-LIVE** — כל 9 ההפסדים 3-חוזים; sizing לא-מורד.
- **🟡 I-30 (cluster) נמשך-זול** — זוג-11:55 (entry זהה), **שניהם ניצחו** ⇒ עלות-אפסית. **🟡 I-32** נמשך (229/234 חסרים). **🔴 I-22** נמשך (R מ-pnl_usd; id232 pnl_r=+9R מנופח על +$11.25).
- **⚠️ מגבלת-נתונים נמשכת:** woodies-buffer מכסה רק 11:15→15:20 ⇒ **woodies-CCI-בוקר חסר** (setup #1 = bars5min-derived). דגל-CC: retention woodies-buffer ל-RTH-מלא (לזהות zlr/hfe-בוקר חי).

## נטיפיקציה ל-Michael
**יום דו-שלבי (open 7447→ראלי-בוקר HIGH 7496.5→down-leg LOW 7404→ראלי-מאוחר 7467). net +$123.75 (5W/9L, 7L/7S).** **ΣR-נגד(פספוס-אמת) ≈ +5R** —
שולט: **ראלי-הבוקר-LONG** (7460→7496.5, +3R) שהמערכת **סחרה-הפוך** (short id228 + קניית-פסגה id231/233; slot-2-benchmark מאומת — I-26). **יום נמוך-פספוסים-אמיתיים אך גבוה-מיס-פיירים.**
**הסיפור-האמיתי: בוקר-זולג (−$746.25) / אחה"צ-תופס (+$870).** ה-down-leg (id238/239/242 = +$1,263.75) הציל יום שבו הבוקר נסחר-נגד-מגמה (−$952.5).
**רגרסיות-היסטוריות המשיכו להיסוג:** I-41 (0-LONG) **נעלם** (7L/7S), I-40 (split) **מכונס**, missed-endpoint **ריק**. **stack-חדש נדחף-לחי** (`c98b808`: HFE_DISABLED=1 ⇒ 0-ירי-HFE · DIRECTION_LSMA_VETO · NONTREND_DISABLE_ALL · cvd-fix).
**🟠 דגלי-CC:** (1) **location/extension-gate** למניעת קניית-פסגה (id231/233) + short-נגד-ראלי (id228/243) — שורש = gates-כיווניים-לא-חיים-בבוקר + **S4-reversal-bleed (D32)**; (2) **adaptive_stop יציבות** (micro-stop 3–4נק' נעצר לפני הצלילה; שונות 3–26נק'); (3) sizing→PnL (I-34, חוסם-LIVE); (4) **I-44** (day_type source-split — אימות-CC); (5) retention woodies ל-RTH-מלא. **החוסם-המוביל: counter-trend / mis-timing בקצוות (I-26)** — I-42 **REFRAMED** ע"י EOD-15:12 (לא playbook-מת). גייט-chop מושבת (standing-Michael, **לא-להפעיל**).

---
*נוצר אוטונומית ע"י Cowork (15:19 CT, 2026-06-24). CCI/flags מאומת מ-Sierra (`sierra_woodies_5min_json` v9.4.5-wc-fix, age 0.3s, כיסוי-עצמאי 11:15→15:20);
בוקר (setup #1) מ-bars5min-OHLC (woodies-CCI-blind, caveat Rule 1/2; bars5min↔trades מסכימים ⇒ אין split). R מ-`pnl_usd` (I-22; pnl_r מנופח id232=+9R על +$11.25).
replay = OHLC-חי, stop-first. חישוב אומת-בקוד: 5W +$1,440 / 9L −$1,316.25 / net +$123.75 / win 35.7% / avg-win $288 / avg-loss −$146.25 / ratio 1.97 /
long_net −$712.5 · short_net +$836.25 / בוקר(id228–236) −$746.25 · אחה"צ(id237–243) +$870 / counter-trend+top-chase −$952.5 · down-leg-shorts +$1,263.75.
missed-endpoint count=0. gap-ids 229/234. day_type Normal→Variation→Neutral_Extreme (7-type classifier). אין source-split (I-40 מכונס). לא שונה קוד.*
