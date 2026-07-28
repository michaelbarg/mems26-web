# ניתוח עסקאות-שלא-בוצעו · 2026-07-20 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:16 CT** (`TZ=America/Chicago date` → `2026-07-20 15:16:36 CDT`, יום ב'; IL 23:16) ✓ — אחרי סגירת RTH 15:00. ריצה אוטונומית — Michael לא נוכח. **לא שונה קוד / flag / .env / DB (read-only).** API-חי דרך Chrome→localhost:8000. **מקור-אמת ל-CCI+trend = Sierra woodies export** · **מקור-אמת לירי/חסימות = OPS_LOG_2026-07-20 (gateway/trade_manager) + `/trades/recent`** (ה-`v9_missed_trades` ריק שוב — I-60).

> ⚠️ הערה תפעולית: לא בוצע `git pull` (המכונה הזו סוחרת + יש שינויים לא-מקומטים כולל תיקון-הדאטה של היום). עבדתי על מצב-הריפו המקומי. הדוח לא נדחף אוטומטית; להריץ `git add/commit/push` ידנית.

---

> 🟢 **ממצא-העל #1 — DATA-QUALITY: תיקון ה-`-1h` של היום החזיק. `bars5min` בריא.** בניגוד ל-07-17 (I-40 corruption, 10/44 match, 8 dup-bars) — היום `bars5min`↔woodies = **37/45 close-match** (max diff 8.25pt, 8 הברים הראשונים בהצלבה = **diff 0 מדויק**), **0 dup-bars צמודים**. הקומיט של היום (`81fe0e2e` — "-1h bars repaired") **עבד**. ⇒ הבוקר (08:30–11:10 CT) **ניתן-לאימות** היום מ-`bars5min` (בניגוד לעיוורון-הבוקר של 07-17). woodies מכסה 11:15→15:20 CT.

> 🟢 **ממצא-העל #2 — אפס פספוס-מגייט "מורעל". חתימת-גייטים בריאה ומבוזרת.** `blocked_by=null` על כל 14 הירי · `/missed-trades count=0`. גייטי-chop OFF (standing 06-08) — **0 חסימות-chop**. ~33 חסימות-RTH **מבוזרות על 5 שערים** (rr_entry_gate ~16 · location_gate 5 · cont_trend_filter 5 · daytype_playbook 5 · s4_risk_cap 2) — **אין שער-יחיד-מורעל.** תואם את Check-1 של ה-session-watch היום ("חתימה בריאה").

> 🔴 **ממצא-העל #3 — הכאב-האמת = ביצוע + יום-chop, לא פספוס-גייט.** המערכת **ירתה 14 ו-11 הפסידו** (יום Neutral_Extreme, ATR≈8.3). 2 ירי-לייב (420 S2-SHORT −$82.5 · 424 S4-SHORT −$42.5) = **live net ≈ −$125**. + 3 ירי-לייב-נוספים (432/434/436) **`ORDER_FAILED:-1`→BE** (לא-מולאו). + **naked orphan short 3c @7542.5** ללא-סטופ (התרעה נפרדת, ALERT_NAKED_SHORT_2026-07-20). ⇒ ביום-כזה, **חסימת-גייט = הגנה**, לא-פספוס: הסטאפים-שנחסמו היו ברובם מפסידים (בדיוק כמו הירי-שירו).

> 🔴 **ממצא-העל #4 — הפספוס-הנקי היחיד: 13:25 REACTIVE_SHORT (S2) נחסם ב-`rr_entry_gate` ≈ +2R.** שורט-המשך-נכון על גלגול-מטה מפסגת-ה-bounce (7516→) שאף ירי לא תפס — רגל 7508→7489 (13:25→13:40). ה-`rr_entry_gate` חסם (חשד R:R-הדוק מול תמיכה-קרובה) בעוד מבנית זו הייתה כניסה תקפה. **False-block יחיד היום.**

> 🟡 **ממצא-העל #5 — R-artifacts (I-22) חוזרים: 3 ה"נצחונות" עם micro-stops.** 423 (stop 0.25pt=0.03×ATR, +$57.5) · 430 (0.25pt, +$21.25) · 431 (0.25pt, +$27.5) — כולם דוּוְּחו WIN אבל עם סטופ תת-רצועתי (S6 EOD סימן "צמוד מדי"). `pnl_r` מנופח (23/17/22 על 0.25pt סטופ). → CC (I-22).

## מקורות-אמת + כיסוי (הצלבה ל-CC)

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart` (limit=80) | **11:15→15:20 (50 ברים)** ✅ **SoT CCI/trend** | `source=sierra_woodies_5min_json` · `age_s=2` fresh · `stale=false`. `ts`=UTC (−5→CT). trend BLUE(פסגה)→RED דומיננטי, bounces BLUE 12:50–13:15 + 14:40–14:45. **בוקר 08:30–11:10 לא בחלון** (50 ברים בלבד). |
| `/api/v9/chart/bars5min` (limit=80) | 08:30→14:55 (78 ברים) ✅ **בריא היום** | `ts`=+03:00(IL,−8→CT). **37/45 match מול woodies, 0 dups, 8 ברי-הצלבה ראשונים diff=0.** תיקון ה-`-1h` החזיק (ניגוד ל-07-17). משמש לשחזור-בוקר. |
| `/api/v9/trades/recent` | **`limit=50`: 14 שורות (419–435). `limit=200`→שגיאה (cap, I-25).** | כל 14 `blocked_by=null` (כולן ירו). מקור-הירי הרשמי. entry_ts=+03:00. |
| OPS_LOG_2026-07-20 (gateway/TM) | 09:25→16:10 CT-events (ts=ET,−1→CT) | **מקור-האמת לחסימות** (`BLOCKED … gate=…`) — כי `/missed-trades` ריק. FIRED/ENTRY-FILL/STOP-HIT מלאים. |
| `/api/v9/build/pattern-status` | live post-close | day_type=**Neutral_Extreme** (degrade) · S4 trend=**RED** · `errors=[]` · woodies FRESH 0s · readiness=READY. |
| `/api/v9/missed-trades` | **count=0, candidates=[]** | 🟡 ריק — פער-persistence נמשך (I-60, כמו 07-08/09/13/17). blocked/shadow לא-נשמרים. |

**הצלבת-מקורות (Rule 2 ✓):** overlap woodies↔bars5min = **37/45 close-match** (max 8.25pt) ⇒ **פיד-בריא היום** (מול 10/44 ב-07-17). 8 הברים הראשונים בהצלבה (11:15–11:50) = diff **0.0 מדויק**. ⚠️ שאריות-desync ~5–8pt בכמה ברי-אחה"צ + פער ~5–12pt בין entry-prices של הגייטוויי (bars5min) ל-woodies-close ב-10:45–11:50 (lag של ~בר-אחד) — → CC לאמת שאין drift-חוזר של I-40.

## מבנה-היום (RTH · בוקר=bars5min · אחה"צ=woodies)

open **7544.75@08:30** → pop ל-**HOD 7552.25@08:45** → **selloff-בוקר ל-7501@09:55** (−51pt) → **bounce ל-7531–7534@11:05–11:15** (+30pt retrace) → **גרינד-יורד אחה"צ** במדרגות עם bounces-נגד-מגמה (12:50–13:15 →7516 · 14:40–14:45 →7494) → **LOD/נעילה 7479.5@15:20**. **יום Neutral_Extreme/יורד** (net **−65pt** open→close). day_type: state=`Neutral_Extreme` · commit-בוקר=`Normal_Variation-DOWN` (פיצול-תווית I-1, אך תפקד הגנתית).

## עסקאות-שירו היום (הקשר — ירו, לא-פוספסו · `/trades/recent` · כולן `blocked_by=null`)

| id | זמן(CT) | תבנית | מער' | כיוון | entry | stop(risk) | תוצאה | mode | הערה |
|---|---|---|---|---|---|---|---|---|---|
| 419 | 09:25 | REACTIVE_SHORT | S2 | SHORT | 7508.75 | 7514 (5.25) | **LOSS −78.75** | shadow | נעצר על ה-bounce ל-7534 |
| **420** | 09:25 | REACTIVE_SHORT | S2 | SHORT | 7508.75 | 7514 (5.25) | **LOSS −82.5** | **live** | 🔴 שורט מוקדם, bounce עצר |
| 421 | 09:43 | ZLR | S4 | SHORT | 7512.5 | 7517.75 (5.25) | **LOSS −52.5** | shadow | bounce |
| 423 | 09:45 | CONFLUENCE_RI_ZLR | S4 | SHORT | 7510.5 | 7510.25 (**0.25!**) | **WIN +57.5** T2 | shadow | 🟡 micro-stop (I-22) — R-artifact |
| **424** | 09:45 | CONFLUENCE_RI_ZLR | S4 | SHORT | 7510.5 | 7515 (4.5) | **LOSS −42.5** | **live** | 🔴 bounce עצר |
| 425 | 10:45 | ZLR | S4 | 🔴LONG | 7523.75 | 7516.25 (7.5) | **LOSS −112.5** | shadow | לונג-נגד-מגמה (יום-יורד) |
| 426 | 11:05 | ZLR | S4 | 🔴LONG | 7525.5 | 7518 (7.5) | **LOSS −112.5** | shadow | לונג-נגד-מגמה |
| 427 | 11:30 | ZLR | S4 | 🔴LONG | 7529.75 | 7524 (5.75) | **LOSS −86.25** | shadow | לונג בפסגה 7531→נפל |
| 428 | 11:50 | REACTIVE_LONG | S2 | 🔴LONG | 7525 | 7518 (7) | **LOSS −105** | shadow | לונג-נגד-מגמה |
| 429 | 12:40 | ZLR | S4 | SHORT | 7504.25 | 7509.5 (5.25) | **LOSS −78.75** | shadow | שורט מוקדם — bounce ל-7516 עצר |
| 430 | 12:50 | GHOST | S4 | 🔴LONG | 7506 | 7506.25 (**0.25!**) | **WIN +21.25** | shadow | 🟡 micro-stop (I-22) |
| 431 | 13:50 | FAMIR | S4 | 🔴LONG | 7490 | 7490.25 (**0.25!**) | **WIN +27.5** | shadow | 🟡 micro-stop (I-22) |
| 433 | 13:55 | FAMIR | S4 | 🔴LONG | 7493.75 | 7487.5 (6.25) | **LOSS −93.75** | shadow | לונג בתחתית-יורדת |
| 435 | 14:14 | ZLR | S4 | SHORT | 7483 | 7496 (13) | **LOSS −47.5** | shadow | T2-fill ואז נגרר-חזרה לסטופ |
| — | — | (432/434/436) | S4 | LONG/SHORT | — | — | **ORDER_FAILED:-1→BE** | live | 🔴 3 ירי-לייב שלא-מולאו (op path) |

**Σ fires-אמת:** **14 ירי → 11 הפסידו, 3 ניצחו-זעיר (כולם micro-stop/I-22).** **live: 420 −$82.5 · 424 −$42.5 = −$125** (+432/434/436 ORDER_FAILED). **7/14 היו לונג-נגד-מגמה** (425/426/427/428/430/431/433) ביום-יורד — הפסידו רובם (I-41/I-50/I-67, פער-פילטר-מגמה נמשך). **הכיוון-השורט המוקדם (419–424) נעצר ע"י ה-bounce ל-7534.** ⇒ **יום-chop קלאסי: המערכת ירתה הרבה והפסידה — לא בעיית-פספוס.**

## טבלת setups-שלא-בוצעו — lookback מתגלגל 6-ברים (08:30→15:00 CT)

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay) | gate-שחסם (blocked_by) | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **08:45–09:05** | reversal-DOWN (pop→sell) | S2/S4 | ⚠️ בוקר (bars5min: 7552→7520) — **אין ירי עד 09:25** | ~7548 | ~7554 | — | 🟡 **המערכת ירתה מאוחר** (09:25 @7508, החמיצה 7552→7508 ~44pt) | אין-fire (late-entry) | I-60-adj (late) |
| 09:25 | REACTIVE_SHORT | S2 | ✅ **ירה** (419/420) | 7508.75 | 7514 | — | **ירה, לא-פוספס** — הפסיד (bounce) | `blocked_by=null` | — (fired) |
| 09:35 | ZLR SHORT | S4 | ✅ זוהה, **נחסם** | ~7515 | ~7522 | T1~7505 | 🟡 marginal (~+1.4R אם stop-רחב; אך 09:40 H7522 איתגר) — bounce ל-7534 אח"כ | **rr_entry_gate** | rr (marginal) |
| 09:55 | VEGAS SHORT | S4 | ✅ זוהה, **נחסם** | ~7506.5 | — | — | 🟢 **הגנתי** — מיד bounce 7501→7534 | **location_gate** | protective |
| 10:05–10:32 | REACTIVE_LONG ×3 | S2 | ✅ זוהה, **נחסם** | 7510–7524 | — | — | 🟢 **הגנתי** — לונג-נגד-מגמה; הלונגים-שירו (425–428) **כולם הפסידו** | **location_gate / daytype_playbook** | protective (I-41/50/67) |
| 10:15 | ZLR SHORT ×2 | S4 | ✅ זוהה, **נחסם** | 7511–7513 | — | — | 🟢 **הגנתי** — שורט בתוך ה-bounce-למעלה (→7534) | **cont_trend_filter** | protective |
| 11:10–11:20 | GHOST LONG ×2 | S4 | ✅ זוהה, **נחסם** | ~7531 | — | — | 🟢 **הגנתי** — לונג בפסגה 7531 (נפל ל-7479) | **s4_risk_cap** | protective |
| 11:40 | ZLR LONG ×2 | S4 | ✅ זוהה, **נחסם** | 7526.75 | — | — | 🟢 **הגנתי** — לונג מול RED (נפל ל-7513) | **cont_trend_filter** | protective |
| 11:40–12:15 | REACTIVE_LONG/SHORT | S2 | ✅ זוהה, **נחסם** | 7503–7527 | — | — | 🟢 מרבית-הגנתי (הלונג-שירו 428 @7525 הפסיד −$105) | **daytype_playbook / rr_entry_gate** | protective |
| **13:25** | **REACTIVE_SHORT** | **S2** | ✅ זוהה, **נחסם** | **7508.25** | **7514 (5.75)** | **T1 7496.75 / T2 7491** | 🔴 **+2R פוספס** — רגל 7508→7489 (13:40 L7488.5); highs≤7512.5 (סטופ שרד); **אף ירי לא תפס** | **rr_entry_gate** | **rr (FALSE-block)** |
| 14:05 | ZLR SHORT | S4 | ✅ זוהה, **נחסם** | 7487.25 | ~7495 (8) | T1~7479 | 🟡 marginal/scratch — 7480 (תמיכה 7pt) הגיע 14:15, אך bounce ל-7495.5 (14:30) עצר | **rr_entry_gate** | rr (protective) |
| 14:25→ | ZLR SHORT / REACTIVE_LONG | S4/S2 | ✅ post-14:25 | — | — | — | ⏱️ **eod_entry_cutoff** ואז **session_gate_closed** — נורמלי, לא-פספוס | time-gate | — (תקין) |

**ΣR-נגד (replay מבני, deduped, מעוגן-woodies/bars5min):**
- 🔴 **פספוס-גייט נקי יחיד = 13:25 REACTIVE_SHORT (rr_entry_gate) ≈ +2R** (T1+T2 על רגל 7508→7489; אף ירי לא כיסה אותה — 429 נעצר 12:41 לפני ה-bounce, 435 תפס רק את הרגל האחרונה). **False-block יחיד.**
- 🟢 **כל שאר ~32 החסימות = הגנתיות** — לונגים-נגד-מגמה (daytype/location), שורטים-לתוך-bounces (cont_trend), לונג-בפסגה (s4_risk_cap). ה-replay שלהן = הפסד/scratch, **בדיוק כמו הירי-שירו-והפסידו** (11/14). ⇒ הגייטים **חסכו הפסדים**.
- 🟡 **בוקר 08:45–09:05 = כניסה-מאוחרת** (המערכת ירתה 09:25 @7508 במקום ~08:50 @7548) — לא-חסימת-גייט אלא detection/entry-lag (עיוורון-woodies-בוקר).
- ⇒ **ΣR-נגד (missed-גייט אמת) ≈ +2R** (setup יחיד). **הכאב-האמת היום איננו ב-missed** אלא ב-(1) ביצוע-לייב (−$125 + 3 ORDER_FAILED + naked-orphan), (2) 7 לונגים-נגד-מגמה שהפסידו (I-41/50/67), (3) R-artifacts (I-22).

## 🎯 BENCHMARK — 5 הסלוטים של Michael (template יום-יורד 06-05) מול היום

היום **יום-Neutral_Extreme/יורד** (open 7544.75→selloff 7501@09:55→**bounce 7534@11:10**→LOD 7479.5@15:20). ה-benchmark-slots כולם 08:30–10:00 CT, אך **היום היה bounce-בוקר גדול** (7501→7534, 09:55–11:10) שקיטע את סלוטי-השורט:

| # | סלוט(CT) | סוג(template) | מה קרה בפועל היום | תקף היום? | המערכת | הערכה |
|---|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2) | pop→HOD 7552.25@08:45 → selloff ל-7501 | ✅ ארכיטיפ-תקף (~08:45) | ⚠️ ירה **מאוחר** (09:25 @7508) | detected-late — החמיץ 7552→7508 |
| 2 | 9:00 | LONG טקטי | מחיר 7522 באמצע-selloff (המשיך ל-7501) | ❌ נגד-הselloff | — | לא-תקף היום (היה נעצר) |
| 3 | 9:20 | SHORT | 09:25 REACTIVE_SHORT ירה (419/420) | ✅ כיוון-נכון | **ירה 09:25** | 🔴 **420 live הפסיד** (−$82.5) — bounce עצר |
| 4 | 9:35 | SHORT | ZLR SHORT @7515 **נחסם** (rr_entry_gate) | 🟡 marginal (bounce אח"כ) | **נחסם (rr)** | detected-but-gated — marginal |
| 5 | 10:00 | SHORT | 10:00 = תוך ה-bounce 7501→7534 | ❌ **מוקדם** (היה נעצר) | — | לא-תקף (זה היה ה-bounce) |

**שורת-benchmark: K/5 — 1/5 ירה-על-הסלוט (9:20→09:25, אך הפסיד לייב) · 1/5 detected-late (8:35→09:25) · 1/5 detected-but-gated (9:35, rr marginal) · 2/5 לא-תקפים-היום (9:00 long, 10:00 short — קוטעו ע"י ה-bounce).** ה-benchmark **לא חשף פער-גייט חדש** — הכיוון-השורט תקף אך ה-bounce-הבוקר (7501→7534) קיטע את הסלוטים; השורט-הלייב היחיד בסלוט (420 @09:25) הפסיד דווקא. ⚠️ הגייטים-ההיסטוריים של ה-benchmark (choppiness/sizing/A1-veto/FHB/opening→entry — I-13/I-14/I-15/I-16) כולם **מושבתים/מיושנים** היום; הגייטים-הפעילים הם דור-חדש (rr/location/cont_trend/daytype/risk_cap).

## פירוק לפי gate (RTH, ללא time-gates)

| gate | #setups (בקירוב) | סטטוס |
|---|---|---|
| **🔴 rr_entry_gate** | **~16 (מוביל)** | R:R filter. **1 false-block (13:25, +2R)**; שאר ~15 = R:R-הדוק-אמת (תמיכה/התנגדות קרובה) ⇒ מרבית-הגנתי ביום-chop. |
| **🟢 location_gate** | 5 | חסם REACTIVE_LONG (S2) + VEGAS — מיקום-כניסה. **הגנתי** (לונגים-נגד-מגמה). |
| **🟢 cont_trend_filter** | 5 | חסם שורטים-לתוך-bounces + לונג-מול-RED. **הגנתי** (כיוון-מקומי). |
| **🟢 daytype_playbook** | 5 | חסם REACTIVE_LONG-נגד-יום-יורד + REACTIVE_SHORT. **הגנתי** (day_type תפקד למרות פיצול-תווית I-1). |
| **🟢 s4_risk_cap** | 2 | חסם GHOST LONG בפסגה 7531. **הגנתי**. |
| **🟢 choppiness (S2/Layer-0)** | **0** | **OFF** (standing 06-08). לא חסם דבר. |
| **⏱️ eod_entry_cutoff / session_gate_closed** | ~9 (post-14:25) | נורמלי — לא-פספוס. |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🟢 השתפר: תיקון ה-`-1h` (I-40) החזיק** — `bars5min` בריא (37/45, 0 dups) מול קורбан-07-17. הבוקר ניתן-לאימות שוב. **לאמת ש-drift לא חוזר** (→ CC).
- **🟢 גייטים-נקיים:** `blocked_by=null` על כל 14 · chop-gates OFF · חתימת-חסימות מבוזרת-ובריאה (אין שער-מורעל). **קטגוריית פספוס-מגייט = 1 בלבד (13:25, +2R).**
- **🔴 פתוח: I-22 (R-artifact / micro-stops)** — 423/430/431 עם סטופ 0.25pt (0.03×ATR). S6 EOD סימן 3× "צמוד מדי". → CC.
- **🔴 פתוח: I-41/I-50/I-67 (לונג-נגד-מגמה)** — 7/14 הירי היו לונג ביום-יורד; מרביתם הפסידו (425/426/427/428/433). פער-פילטר-מגמה נמשך. → CC.
- **🔴 פתוח: ביצוע-לייב** — 420/424 live הפסידו (−$125); 432/434/436 `ORDER_FAILED:-1`; **naked orphan short 3c** (ALERT_NAKED_SHORT_2026-07-20 — reconciler-heal תקוע). זה **הכאב-האמת של היום.**
- **🟡 פתוח: I-60 (missed-store ריק)** · **I-25 (trades/recent limit=200 cap)** · **I-1 (פיצול-תווית day_type: Neutral_Extreme↔Normal_Variation-DOWN — אך תפקד הגנתית).**

## נטיפיקציה ל-Michael
**🟢 אפס פספוס-מגייט מורעל: `blocked_by=null` על כל 14 הירי · chop-gates OFF · ~33 חסימות מבוזרות-ובריא על 5 שערים (rr מוביל ~16). המוביל rr_entry_gate = R:R-הדוק, מרבית-הגנתי.**
**🔴 פספוס-נקי יחיד: 13:25 REACTIVE_SHORT נחסם ב-rr_entry_gate (false-block) ≈ +2R (רגל 7508→7489, אף ירי לא תפס).**
**🔴 הכאב = ביצוע+chop, לא פספוס: המערכת ירתה 14 והפסידה 11 (יום Neutral_Extreme); live −$125 (420/424) + 3 ORDER_FAILED + naked-orphan; 7 לונגים-נגד-מגמה הפסידו (I-41/50/67); 3 "נצחונות" עם micro-stop (I-22).**
**🟢 DATA: תיקון ה-`-1h` החזיק — bars5min בריא (37/45, 0 dups) מול קורбан-07-17. benchmark K/5: 1 ירה-על-סלוט(הפסיד לייב)·1 late·1 gated·2 לא-תקפים (bounce-בוקר קיטע). לא שונה קוד.**

---
*נוצר אוטונומית ע"י Cowork (15:16 CT, 2026-07-20). מאומת-תוכניתית (Rule 2/5): woodies=SoT (sierra_woodies_5min_json, age 2s, ts=UTC) · bars5min בריא (37/45 close-match woodies, 0 dup-adjacent, 8 first-overlap diff=0, ts=+03:00) · struct: open 7544.75@08:30 / HOD 7552.25@08:45 / morn-low 7501@09:55 / bounce 7534@11:10 / LOD 7479.5@15:20 / net −65pt · fires 14 (`/trades/recent` limit=50, all blocked_by=null): 419 S2-REACT-SHORT 09:25 −78.75 · 420 live −82.5 · 421 S4-ZLR-SHORT 09:43 −52.5 · 423 S4-CONF-SHORT 09:45 +57.5(micro-stop) · 424 live −42.5 · 425/426/427 S4-ZLR-LONG 10:45/11:05/11:30 −112.5/−112.5/−86.25(נגד-מגמה) · 428 S2-REACT-LONG 11:50 −105 · 429 S4-ZLR-SHORT 12:40 −78.75 · 430 S4-GHOST-LONG 12:50 +21.25(micro) · 431 S4-FAMIR-LONG 13:50 +27.5(micro) · 433 S4-FAMIR-LONG 13:55 −93.75 · 435 S4-ZLR-SHORT 14:14 −47.5 · +432/434/436 live ORDER_FAILED→BE · blocks(OPS_LOG, ts=ET−1→CT): rr_entry_gate~16 · location_gate 5 · cont_trend_filter 5 · daytype_playbook 5 · s4_risk_cap 2 · eod/session ~9(post-14:25) · missed-store count=0 · pattern-status day_type=Neutral_Extreme errors=[] trend=RED · replay: 13:25-short T1 7496.75 hit@13:40(L7488.5), highs≤7512.5 stop-safe = +2R. **לא שונה קוד/flag/.env/DB.***
