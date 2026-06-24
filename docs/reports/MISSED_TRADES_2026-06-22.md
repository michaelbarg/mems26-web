# ניתוח עסקאות-שלא-בוצעו · 2026-06-22 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:20 CT** (אחרי סגירת RTH 15:00) ✓. ריצה אוטונומית — Michael לא נוכח.
**משלים את** ה-EOD-consolidation של 15:12 (אותו register, §`[2026-06-22 15:12 CT]`) — מזווית-הפספוסים.

**הקשר (מאומת מדאטה חיה):** **יום-נטו-יורד עם פתיחה-עולה (day_type=`Variation` conf 0.18).** RTH 08:30→15:00 CT.
OHLC: open **7578.25** → **HIGH 7596.75 (08:35–09:05)** → **LOW 7527.25** → close **7540.25** — **טווח 69.5 נק'.**
תבנית: זינוק-פתיחה-עולה → **קריסה ל-7551 עד 09:40** (~46נק') → **chop דו-כיווני 7528–7568** לכל-אחה"צ.
trend(Sierra/Woodies): **BLUE בפתיחה** (08:30–09:05, לפי הצלבת-EOD-15:12) → מתחלף GRAY↔RED↔BLUE כל-אחה"צ
(חלון-מאומת-עצמאית-כאן 11:15→15:00). **המגמה-היומית יורדת, אבל הביצוע ירה SHORT לתוך עליות.**

> 🔴 **הממצא-המהותי — חזרה-מוגברת של תסמונת 06-19: יום-הפסד-מ-over-firing, לא יום-פספוסים.**
> **19 ירי-RTH, כולם SHORT (0 LONG), 7W/12L, net −$1,311.63, win-rate 37%** — היום-הגרוע-בשבוע. ה-setups-האיכותיים
> שפוספסו מעטים (**ΣR-נגד ≈ +1R** — אות-HFE-UP-LONG בודד שנחסם). הסיפור-האמיתי **הפוך מפספוס**: הביצוע ירה
> SHORT לתוך (א) **זינוק-הפתיחה-העולה** (5 שורטים 08:30–09:05 על `trend=BLUE` = **−$516**, counter-trend/I-26)
> ו-(ב) **bounces-אחה"צ** — תוך **התעלמות/חסימה של כל אות-LONG** לאורך-היום (**I-41 — 0 לונגים גם בראלי-פתיחה +18נק'**).

> 🔴 **המנוף-השלילי (מאומת מול ה-EOD-15:12):** **over-firing (19) × timing-נגד-עליות (I-26) × sizing-לא-מורד
> (I-34, כל הפסד = 3-חוזים) × duplicate/cluster (I-39/I-30).** הסטופים **רחבים-יותר** מ-06-19 (risk avg **6.68 נק'**,
> 0.25–13.5) ⇒ יחס loss/win **2.80:1** (מול 1.49). שיא: **id199≡id200 byte-זהים @10:20** (I-39, `cluster_guard` D-037
> קיים-ולא-מנע) + id201 = **−$401.25 בדקה-אחת**.

> ⚪ **הערת-מערכת:** גייטי-ה-chop **מושבתים** (standing 2026-06-08: S2 `choppiness_ok` + Layer-0). **אין המלצה
> להפעיל מחדש** — החלטה-עומדת-של-Michael בלבד (re-enable = שינוי-משטח-סיכון → strategic-stop). תצפית בלבד. **לא שונה קוד.**

## מקורות-אמת + כיסוי (הצלבה ל-CC) — ⚠️ מגבלת-נתונים מהותית לזיהוי-אות-בוקר

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart?limit=80` | **11:15→15:20 (50 ברים)** | **מקור-אמת ל-CCI = Sierra** (`sierra_woodies_5min_json`, `v9.4.5-wc-fix`, `age=0.1s`, `stale=false`). ⚠️ **buffer-מתגלגל מכסה רק חצי-אחה"צ** — **חסר כל ה-RTH-בוקר 08:30→11:10** (50-bar, יום-מלא). זיהוי-zlr/hfe-בוקר **לא-זמין** מכאן. |
| `/api/v9/chart/bars5min` | 08:30→14:55 | 🔴 **3 ברי-זבל מאומתים (I-40):** `08:30 C=5737` · `09:00 C=13456` · `09:30 C=6274` (MES≈7540). תואם SoT (`v9_bars_5min` stalled/gapped; ה-SoT=`_woodies`). **לא-אמין ל-replay-בוקר.** |
| `/api/v9/trades/recent?limit=100` | **היום: 19 (id188–212)** | כיסוי-מלא. `limit=200`→**422** (I-25; ירד ל-100). R מ-`pnl_usd`, **לא** `pnl_r` (I-22). mode=`shadow`. |
| `/api/v9/build/pattern-status` | live post-close | `session_date=2026-06-22` · day_type=**Variation** (conf 0.18, **UNKNOWN ב-08:30–08:55**/opening-lag I-36) · readiness=**DEGRADED** (`trend_state=GRAY` post-close) · `errors=[]` · woodies_5min **FRESH 0s**. *(הנתיב מ-spec `/build_status/pattern-status`→404; הנכון `/build/pattern-status`.)* |
| `/api/v9/missed-trades` | **14:52 בלבד (50)** | ⚠️ כולם `HFE LONG / ready_to_route=False / r=null` — **buffer-artifact, לא דאטת-סשן** (זהה 06-16/18/19). מתעד את ה-HFE-UP-LONG @14:50 שנחסם (setup #1). |

> 🟡 **CAVEAT-נתונים (Rule 1/2):** ה-`/woodies/chart?limit=80` (מקור-ה-CCI-העצמאי-של-ריצה-זו) מחזיק רק **11:15→15:20**
> + bars5min קורּפ (I-40, "מנוקב 09:00–09:35"). ⇒ **ריצה-זו עיוורת-לבוקר ל-re-verification עצמאי**. **אך המערכת לא-עיוורת:**
> ה-engine קרא trend-בוקר דרך ה-live `direction_context`/`woodies_5min` (ראה strip-v2, STATUS_BOARD) ⇒ נתוני-בוקר
> (trend BLUE→GRAY→RED, OHLC-מלא) **שוחזרו ע"י הצוות** ומוצלבים כאן **עם ייחוס**. פער-הכניסה 09:05→09:40 = **GRAY-no-fire-zone
> לגיטימי** (לא-פספוס, לא-עיוורון). ניתוח-הפספוסים-המגודר מתבסס על אחה"צ (woodies-עצמאי-מלא) + טבלת-trades (כיסוי-מלא).

## טבלת setups שזוהו-ולא-ירו / לא-נתפסו (rolling-6-bar · Sierra-CCI 11:15→15:00 · replay stop-first)
entry=close-בר-האות · stop=swing בר-האות+הקודם ±0.5 · T1=1R · replay על OHLC-Sierra-חי, **stop-first**.

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay) | gate-שחסם | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **14:45–14:50** | **HFE-UP → LONG (היפוך)** | S4 | ✅ `hfe_detected=UP`@14:45 + 50× ב-`missed-trades` | 7535.5 | 7528.25 (7.25) | 7542.75 / 7547 | **+1R** (T1@14:50 H7545.25; MFE ~+1.6R @15:00 H7547) | **`ready_to_route=False`** (I-3) — ה-LONG נחסם; **ובאותו-חלון id212 ירה SHORT והפסיד −$78.75** | **I-3 / I-26 / I-41** |
| 12:15–12:20 | ZLR-UP → LONG | S4 | ✅ `zlr_detected=UP` ×2 | ~7546 | ~7542 (4) | 1R | **~0R** (GRAY-chop; דעך מיד 12:25→7543) | לא-נותב (LONG ב-GRAY/chop) — **דילוג-לגיטימי** | I-41 (legit-skip) |
| 12:50 | ZLR-UP → LONG | S4 | ✅ `zlr_detected=UP` | ~7548 | ~7543 (5) | 1R | **~0R** (GRAY; דעך 12:55→7542.75) | לא-נותב (LONG ב-GRAY) — **דילוג-לגיטימי** | I-41 (legit-skip) |
| 09:05–09:40 | down-leg ~46נק' (7597→7551) | S4/S2 | — (trend=GRAY) | — | — | — | **דילוג-לגיטימי** (GRAY-no-fire-zone) | **לא gate-bug:** ניתוח-intraday (`TRADES_TODAY_2026-06-22`, STATUS_BOARD) קבע פער 09:05–09:40 = **GRAY-no-fire-zone** (S4 stood-aside), **לא** עיוורון-נתונים. ירי-הבא 09:40 (תחתית). שאלת-כיול: האם GRAY-veto שמרני-מדי במעבר-מהיר | GRAY-veto (legit) |

**ΣR-נגד (פספוס-אמת) = +1R** (אות-HFE-UP-LONG-בודד @14:45 — היחיד שהיה-נקי-ונחסם). שני ה-ZLR-UP (12:15/12:50)
היו GRAY-chop שדעכו ⇒ **דילוג-לגיטימי**. ⇒ **יום נמוך-פספוסים** (כמו 06-19, +1R) — אבל **הניגוד חריף-יותר**:
ה-+1R-שפוספס מול **−$1,312-שאבד-מ-over-firing**.

## 🔴 הסיפור-האמיתי — over-firing × timing-נגד-עליות × sizing/dup (ground-truth מ-`v9_trades`)
**19 ירי-RTH, 100% SHORT (0 LONG), 7W/12L, net −$1,311.63, win 37%.** avg-win **+$49.41** מול avg-loss **−$138.12**
(יחס **2.80:1** — negative-skew חריף). הסטופים **רחבים-יותר** (risk avg 6.68נק'). **הביצוע ירה SHORT לתוך עליות**
(זינוק-פתיחה-BLUE + bounces) למרות שהמגמה-היומית-יורדת — כשל-**timing**, לא כשל-כיוון-יומי.

| זמן(CT) | id | תבנית | מע' | dir | entry | risk | תוצאה | $ | הערה |
|---|---|---|---|---|---|---|---|---|---|
| 08:30 | 188 | TACTICAL | S4 | SHORT | 7572.5 | 7.25 | LOSS | −108.75 | **short לתוך פתיחה-BLUE-עולה** (I-26) |
| 08:35 | 190 | TACTICAL | S4 | SHORT | 7577.5 | 13.5 | LOSS | −202.5 | stop-רחב; המחיר עלה ל-7591+ |
| 08:50 | 191 | STRATEGIC | S4 | SHORT | 7591.5 | 1.5 | **WIN** | +39 | scratch-scalp (risk 1.5) |
| 08:55 | 193 | STRATEGIC | S4 | SHORT | 7586 | 11.5 | LOSS | −172.5 | short לתוך עליה ל-7597 |
| 09:05 | 194 | STRATEGIC | S4 | SHORT | 7593.5 | 4.75 | LOSS | −71.25 | **slot-2 benchmark (LONG) — ירה SHORT** |
| 09:40 | 195 | NO_SETUP | S2 | SHORT | 7551 | 4.5 | **WIN** | +94.38 | **תפס את תחתית-הקריסה** ✓ |
| 09:45 | 196 | TACTICAL | S2 | SHORT | 7550.5 | 9.5 | **WIN** | +141.88 | המשך-הקריסה — מנצח-היום |
| 10:10 | 197 | STRATEGIC | S2 | SHORT | 7538.5 | 9.25 | LOSS | −138.75 | short לתוך bounce ל-7547 |
| 10:20 | 199 | STRATEGIC | S2 | SHORT | 7537.75 | 8.5 | LOSS | −127.5 | **byte-זהה ל-id200 (I-39 dup)** |
| 10:20 | 200 | STRATEGIC | S2 | SHORT | 7537.75 | 8.5 | LOSS | −127.5 | **duplicate-fire (I-39)** — cluster_guard לא-מנע |
| 10:20 | 201 | TACTICAL | S4 | SHORT | 7538 | 9.75 | LOSS | −146.25 | **triple @10:20 (I-30) = −$401** |
| 10:30 | 202 | TACTICAL | S2 | SHORT | 7539.75 | 8 | LOSS | −120 | נעצר 7547.75 |
| 10:50 | 203 | TACTICAL | S2 | SHORT | 7540.5 | 0.25 | **WIN** | +51.25 | scratch/trail |
| 11:05 | 205 | NO_SETUP | S2 | SHORT | 7533.75 | 11.5 | LOSS | −172.5 | short לתוך bounce 7545 |
| 11:25 | 206 | TACTICAL | S4 | SHORT | 7541.25 | 0.25 | **WIN** | +3.12 | **זוג I-30** עם id208 (אותו-בר) |
| 11:25 | 208 | TACTICAL | S2 | SHORT | 7541.75 | 0.25 | **WIN** | +5.62 | **זוג I-30** (S2+S4 11:25) |
| 13:00 | 209 | NO_SETUP | S2 | SHORT | 7542.75 | 0.25 | **WIN** | +10.62 | scratch |
| 14:00 | 211 | STRATEGIC | S2 | SHORT | 7532.75 | 12.75 | LOSS | −191.25 | stop-רחב; נעצר 7545.5 @14:55 |
| 14:45 | 212 | NO_SETUP | S2 | SHORT | 7529.5 | 5.25 | LOSS | −78.75 | **short לתוך ה-HFE-UP-bounce** (setup #1) — צד-שגוי |

**פילוח:** **זינוק-פתיחה (08:30–09:05, 5 שורטים על BLUE) = −$516** (I-26) · **triple-10:20 = −$401.25** (I-39 dup +
I-30) · אחה"צ-chop ≈ −$395. ה-2 מנצחים-האמיתיים (id195/196, +$236) תפסו את תחתית-הקריסה; שאר-ה-"wins" scratch
(risk 0.25). **כל הפסד = 3-חוזים** ללא הורדת-sizing (**I-34** — מאומת ב-EOD-15:12 `implied_contracts={3.0}`) ⇒ הפסדים-מוגברים.

## 🎯 BENCHMARK — 5 הסלוטים של Michael (06-05, יום-יורד) מול היום
היום **חלקית-תואם-כיוון** ל-benchmark (שניהם נטו-יורדים; אבל היום פתח-בעליה ⇒ ה-bias-היורד "נכון-לסוף" אבל ה-timing נענש).

| # | סלוט(CT) | סוג(benchmark) | מה קרה היום | ירה? | הערה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2/FHB) | זינוק-פתיחה-BLUE ל-7597 | ⚠️ id190 **SHORT** (S4, **−$202.5**) | ירה-SHORT לתוך עליה (counter-BLUE); אין FHB/reversal-setup |
| 2 | 9:00–9:05 | LONG טקטי | מחיר ~7593 (טופ) לפני-קריסה | ❌ id194 **SHORT** (−$71.25) | **שגיאת-כיוון:** benchmark=LONG, ירה SHORT |
| 3 | 9:20 | SHORT | **אמצע-הקריסה** 7593→7551 | ⚠️ **פער-כניסה** | **אין-ירי 09:06–09:39** — פספס את ה-leg-הנקי-ביותר; ירי-הבא 09:40 |
| 4 | 9:35 | SHORT | קריסה ל-7551 | ✅ id195/196 **SHORT** (S2, **+$236**) | **כיוון=benchmark, 2×WIN** — ההתאמה-הנקייה-היחידה ✓ |
| 5 | 10:00 | SHORT | bounce ל-7547 | ⚠️ id197 **SHORT** (10:10, −$138.75) | כיוון=benchmark אבל הפסיד (נכנס לתוך bounce) |

**שורת-benchmark: 4/5 סלוטים כוסו ע"י ירי (±15דק'); סלוט-3 (09:20) = פער-כניסה באמצע-הקריסה.**
כיוון: רק **1/5 ניצח-נקי** (סלוט-4 SHORT). סלוטים 1–2 ירו SHORT לתוך זינוק-הפתיחה-העולה (הפסידו); סלוט-5 SHORT
לתוך bounce (הפסיד). **K/5 = 4/5 ירו · 1/5 כיוון-מנצח.** ה-bias-היורד תאם את ה-benchmark, אבל ה-timing
(short-לתוך-עליות) ענש כל-כניסה פרט-לתחתית-הקריסה.

## פירוק לפי gate
| gate | #setups | סטטוס |
|---|---|---|
| **over-firing (chop-gate מושבת)** | 12 הפסדי-RTH (−$1,657 גרוס) | 🔴/⚪ **המנוף-המוביל** — 19 ירי. גייט-chop מושבת-בכוונה (standing 06-08); זה ה-trade-off. **לא-להפעיל בלי Michael.** |
| **timing נגד-עליות / counter-BLUE (I-26)** | 5 (08:30–09:05, −$516) | 🔴 short לתוך פתיחה-BLUE-עולה; `TREND_DIRECTION_GATE` (343a41b) לא-חסם (flag-OFF / נסמך על day_type=UNKNOWN). |
| **0-LONG anomaly (I-41)** | 19/19 SHORT; כל אות-LONG חסום | 🔴 אף LONG לא-נורה גם בראלי-פתיחה +18נק'; כל ZLR-UP/HFE-UP לא-נותב |
| **duplicate/cluster (I-39/I-30)** | triple-10:20 (−$401) + זוג-11:25 | 🔴 **id199≡id200 byte-זהים** (I-39); `cluster_guard` D-037 קיים-ולא-מנע |
| **sizing לא-מורד (I-34)** | כל 12 ההפסדים (3-חוזים) | 🔴 **חוסם-LIVE** — `implied_contracts={3.0}`; sizing לא מצמצם חוזה ⇒ הפסדים-מוגברים |
| **`ready_to_route=False` (I-3)** | 1 (HFE-UP-LONG @14:45) + 50 buffer | 🔴 ה-LONG-היחיד-האיכותי נחסם (+1R) **בזמן** ש-id212 ירה SHORT-ההפוך-והפסיד |
| **I-13 stop-רחב** | 4 (188/190/193/211, risk 11.5–13.5) | 🟡 **תורם** (≠06-19) — stops-רחבים = −$675 מ-4 ירי; יחס 2.80:1 |
| day_type-gate / footprint (S3) | 0 חוסמים | 🟢 לא-חוסם (S3_MUTE / I-11) |

### תוקנו מול פתוחים (זווית-הפספוסים)
- **🔴 I-41 (0-LONG) + I-26 (counter-BLUE)** — **הסיפור-הדומיננטי**: 19/19 SHORT; 5 שורטי-פתיחה נגד BLUE (−$516);
  כל אות-LONG (ZLR-UP/HFE-UP) לא-נותב. trend-align veto **חסר דו-כיוונית**. (EOD-15:12 פתח I-41 + עדכן I-26.)
- **🔴 I-39 (duplicate-fire) + I-30 (cluster)** — **id199≡id200 byte-זהים @10:20** (−$255) + id201 = triple −$401.25;
  זוג-11:25. `cluster_guard` D-037 קיים-ולא-מנע. de-dup ממתין-אישור-Michael.
- **🔴 I-34 (sizing)** — כל הפסד = 3-חוזים; sizing לא-מורד ⇒ הפסדי-−$120/−$200. **חוסם-LIVE.**
- **🔴 I-3 (ready_to_route)** — חסם את ה-HFE-UP-LONG-היחיד-האיכותי (@14:45, +1R) בעוד id212 ירה SHORT-ההפוך.
- **🟡 I-13 (stop-רחב)** — **תורם היום** (≠06-19): 4 שורטים stop 11.5–13.5נק' = −$675. יחס 2.80.
- **🟢 ניתוב-S4-SHORT תקין** — כל ZLR/TLB/HFE-SHORT נותבו וירו; `ready_to_route=False` רק על ה-LONG-צד.
- **🆕 I-40 (data-quality)** — 3 ברי-זבל `v9_bars_5min` (5737/13456/6274 @08:30/09:00/09:30) **+** woodies-buffer
  מכסה רק 11:15→15:20 ⇒ **בוקר-RTH עיוור לזיהוי-אות**. (EOD-15:12 פתח I-40 על ברי-הזבל; **כאן מתווסף** היבט
  כיסוי-ה-buffer-בוקר.) דגל-CC: retention woodies ל-RTH-מלא + הצלבת-Sierra לברי-הזבל.
- **🟢 D22/I-38 (feed-death) — לא-משחזר היום**: feed טרי (age 0.1s), errors=[]. מחזק את עמדת-06-19 (Juneteenth, לא-כשל).
- **🔴 I-22** נמשך (R מ-pnl_usd). **🟢 I-25** `limit=200`→422→100 (19<100, ללא-אובדן). **missed-endpoint** = buffer-artifact.

## נטיפיקציה ל-Michael
**יום-נטו-יורד-עם-פתיחה-עולה (Variation, טווח 69.5נק': open 7578→HIGH 7597→LOW 7527→close 7540).
ΣR-נגד(פספוס-אמת)=+1R בלבד** (אות-HFE-UP-LONG @14:45 שנחסם `ready_to_route=False`/I-3 — ובדיוק-שם id212 ירה
SHORT-ההפוך והפסיד −$78.75). **הסיפור-האמיתי הפוך מפספוס: over-firing קיצוני — 19 ירי, כולם SHORT (0 LONG),
net −$1,311.63, win 37%** (היום-הגרוע-בשבוע). הביצוע ירה SHORT לתוך זינוק-הפתיחה-העולה (5 שורטים על BLUE,
08:30–09:05 = −$516/I-26) ולתוך bounces-אחה"צ. **מנוף: over-firing × counter-BLUE-timing (I-26) × sizing-לא-מורד
(I-34, כל הפסד 3-חוזים) × duplicate (I-39: id199≡id200 byte-זהים) + cluster (I-30: triple-10:20 −$401).**
benchmark: **4/5 סלוטים ירו, 1/5 כיוון-מנצח** (סלוט-4). 🟢 ניתוב-S4-SHORT תקין; 🟢 אין feed-death (≠D22).
**⚠️ מגבלת-נתונים:** woodies-buffer מכסה רק 11:15→15:20 + bars5min קורּפ (I-40) ⇒ **בוקר-RTH עיוור** לזיהוי-אות
(setup #4 לא-כומת — Rule 1). **🟠 דגלי-CC:** (1) retention woodies-buffer ל-RTH-מלא; (2) הצלבת-Sierra לברי-הזבל
(I-40); (3) trend-align veto דו-כיווני (I-26/I-41); (4) de-dup/cluster_guard (I-39/I-30); (5) sizing→PnL (I-34, חוסם-LIVE).
**החוסם-המוביל: over-firing × directional-SHORT-timing (גייט-chop מושבת — standing-Michael, לא-להפעיל).**

---
*נוצר אוטונומית ע"י Cowork (15:20 CT) — משלים את ה-EOD-consolidation של 15:12. CCI מאומת מ-Sierra
(`sierra_woodies_5min_json`, כיסוי-עצמאי 11:15→15:20); נתוני-בוקר (trend=BLUE, OHLC-מלא, sizing=3, dup-byte) מוצלבים
מ-EOD-15:12 עם ייחוס. R מ-`pnl_usd` (I-22). replay = OHLC-Sierra-חי (אחה"צ), stop-first. חישוב אומת בקוד: 7W +$345.87 /
12L −$1,657.50 / net −$1,311.63 / win 36.8% / avg-loss/win 2.80 / risk avg 6.68נק'. open-block(08:30–09:05)=−$516 /
triple-10:20=−$401.25. ΣR-נגד(פספוס)=+1R (HFE-UP-LONG @14:45 נחסם). missed-endpoint = 50 buffer-artifact
(14:52 HFE-LONG). bars5min קורּפ (I-40: 3 ברי-זבל). אין feed-death. לא שונה קוד.*
