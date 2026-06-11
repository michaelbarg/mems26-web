# ניתוח עסקאות-שלא-בוצעו · 2026-06-10 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-15:20 CT (אחרי סגירת RTH 15:00) ✓. ריצה אוטונומית — Michael לא נוכח.

**הקשר (מאומת מדאטה חיה):** יום-מגמה-**יורד**. פתיחה 7355 (08:30) → **שיא-סשן 7404.75 (09:20)** →
היפוך והמשך-ירידה לאורך כל היום → **שפל 7261 (~15:10)**, סגירת-אזור ~7274. trend=**RED** ברוב
אחה"צ (RED×19 רצוף 13:50→15:20). המערכת **זיהתה** signals אבל ירתה **רק 3 עסקאות — כולן LONG
נגד-מגמה — וכולן נעצרו**. השורט-של-היום (היפוך-השיא + leg-יורד) **לא ירה אף פעם**.

## מקורות-אמת + כיסוי (הצלבה ל-CC)
| endpoint | כיסוי (CT) | שדות | הערה |
|---|---|---|---|
| `/api/v9/woodies/chart` | **11:15→15:20** (50 ברים) | cci_14/tcci/trend/zlr_detected/hfe_detected/OHLC | **מקור-אמת ל-CCI = Sierra** (`sierra_woodies_5min_json`, age 2.8s) |
| `/api/v9/chart/bars5min` | **08:30→14:55** (78 ברים) | OHLC בלבד | מכסה את חלון-ה-benchmark, **בלי שדות-study** |
| `/api/v9/trades/recent` | היום: 3 עסקאות (shadow) | outcome מלא | היתר ברשימה = ימים קודמים (סוננו לפי תאריך) |
| `/api/v9/missed-trades` | snapshot 15:20–15:23 בלבד | 50× TLB SHORT `ready_to_route=False`, `hypothetical_r=null` | מעריך את הבר-הנוכחי, **לא** replay-סשן → ה-replay למטה בוצע ידנית |

> ⚠️ **פער-מקור מסומן ל-CC (Rule 1 — אין סינתזה):** ה-buffer של study-ה-Woodies מחזיק 50 ברים בלבד
> (חזרה ל-11:15 CT). שדות ה-detector (cci/zlr/hfe/FHB) ל**חלון-הבוקר 08:30–11:10** (כולל כל ה-benchmark)
> **אינם בזיכרון החי**. לא סונתזו ערכי-CCI לברים אלה — נדרשת **הצלבת CC מול DB/Sierra היסטורי** לאישור
> ה-flags של 8:35/9:20/9:35/10:00. החלון 11:15→15:20 מנותח מ-study מלא.

## 🎯 BENCHMARK — 5 העסקאות שמיכאל ציפה (מול הדאטה החי של היום)
מקור: `MISSED_TRADES_ANALYSIS_2026-06-05.md`. replay-המחיר על bars5min (OHLC); stop מבני = swing-high
של בר-האות+הקודם; T1 = 1R.

| # | שעה(CT) | סוג(benchmark) | מחיר-היום בפועל | זוהה? | gate-שחסם | R היפותטי |
|---|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL | היפוך **UP** +28נק' (7335→7366) | ⚠️ study-fields חסר (pre-11:15) | לא נדרך LONG-פתיחה | n/a (study חסר) |
| 2 | 9:00–9:05 | LONG טקטי | עלייה 7378→7391 | ⚠️ study-fields חסר | FIRST_HOUR_TACTICAL לא ירה | n/a |
| 3 | 9:20 | SHORT | **שיא-סשן 7404.75** | ⚠️ study-fields חסר | לא ירה SHORT בשיא | **T1 ✓ · MFE 11.71R** |
| 4 | 9:35 | SHORT | דחייה 7400→7386 (תחילת ה-leg) | ⚠️ study-fields חסר | לא ירה | **T1 ✓ · MFE 7.93R** |
| 5 | 10:00 | SHORT | המשך 7351.5 | ⚠️ study-fields חסר | **ירו 3 LONG נגד-מגמה במקום** (10:09–10:15) | **T1 ✓ · MFE 4.14R** |

**שורת-benchmark:** **0/5 אושרו כ"ירו" ע"י המערכת.** שלושת השורטים (9:20/9:35/10:00) — *העסקאות
האמיתיות של היום* — תפסו את השיא ואת ה-leg היורד (MFE 4.1–11.7R ב-replay-מחיר) ולא ירו. גרוע מכך:
באזור ה-10:00-short המערכת ירתה **3 LONG נגד-מגמה** (S4 HFE) שכולם נעצרו. אישור ה-detector-flags
ל-4 הברים האלה **ממתין להצלבת CC** (buffer-study לא מגיע ל-pre-11:15).

## טבלת ה-setups שזוהו-ולא-ירו (אחה"צ · כיסוי-study מלא 11:15→15:20)
כל השורות: `zlr_detected=true DOWN` במנוע (✅ זוהה) · 0 ירו. entry=close בר-האות · stop=swing-high
בר-האות+הקודם · T1=1R / T2=2R · replay קדימה עד T1/stop.

| זמן(CT) | תבנית | מערכת | זוהה?(flag) | entry | stop | T1/T2 | R-נגד | gate-שחסם | I-# |
|---|---|---|---|---|---|---|---|---|---|
| 11:45 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7320.25 | 7343.5 | 7297 / 7273.75 | **+1R** (MFE 2.55R) | A7 `R:R<1.0` → ready_to_route=False | I-3 |
| 11:55 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7324 | 7331 | 7317 / 7310 | −1R (נעצר) | A7 `R:R<1.0` | I-3 |
| 12:05 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7317 | 7334.5 | 7299.5 / 7282 | **+1R** (MFE 1.04R) | A7 `R:R<1.0` | I-3 |
| 12:10 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7310.75 | 7332.5 | 7289 / 7267.25 | −1R (נעצר) | A7 `R:R<1.0` | I-3 |
| 12:30 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7309 | 7319 | 7299 / 7289 | **+1R** (MFE 1.02R) | A7 `R:R<1.0` | I-3 |
| 13:25 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7316.5 | 7325 | 7308 / 7299.5 | **+1R** (MFE **6.53R**) | A7 `R:R<1.0` | I-3 |
| 13:30 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7311.25 | 7322 | 7300.5 / 7289.75 | **+1R** (MFE 4.67R) | A7 `R:R<1.0` | I-3 |
| 13:35 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7305.75 | 7316.5 | 7295 / 7284.25 | **+1R** (MFE 4.16R) | A7 `R:R<1.0` | I-3 |
| 14:10 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7291.5 | 7302 | 7281 / 7270.5 | **+1R** (MFE **2.9R**) | A7 `R:R<1.0` | I-3 |
| 14:15 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7286.25 | 7299.5 | 7273 / 7259.75 | −1R (נעצר) | A7 `R:R<1.0` | I-3 |
| 14:45 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7290 | 7298.75 | 7281.25 / 7272.5 | **+1R** (MFE 0.71R) | A7 `R:R<1.0` | I-3 |
| 14:50 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7290 | 7300.5 | 7279.5 / 7269 | **+1R** (MFE 2.76R) | A7 `R:R<1.0` | I-3 |
| 14:55 | ZLR-DOWN | S4 | ✅ zlr DOWN | 7276 | 7300.5 | 7251.5 / 7227 | +0.61R (open) | A7 `R:R<1.0` | I-3 |
| **15:20 (live)** | **TLB** | S4 | ✅ active conf 0.77 | 7278 | 7301.25 | 7274.25 / 7270.5 | חסום עכשיו | **A7 FAIL `R:R<1.0 (risk=23.25 reward=9.30)`** | I-3 |

**ראיית-ה-gate (Rule 5 — ציטוט גולמי, `/api/v9/woodies/current` decision_tree @ 15:23):**
`A1:PASS trend=RED · A2:PASS 11 studies · A3:PASS patterns=['TLB'] · A4:PASS (touch-point advisory
degraded: tpo/veto/killzone/layer0 missing) · A5:PASS sizing=half · A6:PASS TACTICAL/REACTIVE ·`
**`A7:FAIL "R:R < 1.0 (risk=23.25 reward=9.30)"`** → `ready_to_route=False`, `last_route.skipped=true
reason=not_ready_to_route`. הסטופ מבני (23.25נק') תקין; ה-**target מנוון** (reward 9.30נק' בלבד) ⇒
R:R=0.40 ⇒ `fire_setup` לא נבנה. זהו **היעדר טבלת stop/target** (anchor-מבני אמיתי), לא באג-חישוב.

## עסקאות שכן ירו היום (3 · כולן shadow · כולן נגד-מגמה)
| # | מערכת | תבנית | זמן | dir | entry | stop | exit | R | תוצאה |
|---|---|---|---|---|---|---|---|---|---|
| 24 | S4 | HFE | 10:09 | **LONG** | 7338.5 | 7337.5 | 7337.5 | −1 | STOP_HIT |
| 26 | S4 | HFE | 10:10 | **LONG** | 7339.25 | 7337.25 | 7337.25 | −1 | STOP_HIT |
| 27 | S4 | HFE | 10:15 | **LONG** | 7327.5 | 7325.75 | 7325.75 | −1 | STOP_HIT |

**ΣR ממומש (ירה) = −3R.** שלושתן HFE-**LONG** שנפלטו בדיוק כשהמחיר שבר למטה (תחילת ה-leg היורד) —
כיוון הפוך מהמגמה. ה-A7 R:R-gate שחסם את כל השורטים **לא חסם את הלונגים** (stop צמוד 1–2נק' ⇒
R:R "עבר") ⇒ אסימטריה: ה-gate סינן דווקא את העסקאות-הנכונות והעביר את ההפוכות.

## סיכום
- **setups-איכות שזוהו-ולא-ירו:** 13 (אחה"צ, כיסוי-study מלא) + 3 שורטי-benchmark בבוקר (price-confirmed,
  detector-flag ממתין ל-CC) = **עד 16**.
- **ΣR-נגד (opportunity cost):**
  - אחה"צ, non-overlapping שמרני (4 setups, יעד 1R): **+3.61R**.
  - אחה"צ, כל 13 האותות ביעד 1R: **+6.61R** (9/13 הגיעו T1).
  - פוטנציאל-MFE על ה-legs (13:25, 13:30, 14:10, 14:50): **2.9–6.5R** לכל setup.
  - שורטי-benchmark (9:20/9:35/10:00, replay-מחיר): MFE **4.1–11.7R**.
- **ΣR ממומש בפועל = −3R** (3 לונגים נגד-מגמה).

### פירוק לפי gate
| gate | #setups שחסם | סטטוס |
|---|---|---|
| **A7 `R:R<1.0` / ready_to_route=False** (target מנוון · היעדר טבלת stop/target) | **13 + live TLB** | 🔴 **החוסם המוביל** = I-3 |
| HFE-LONG נגד-מגמה ללא trend-alignment veto | 3 fires (−3R) | 🔴 **ממצא חדש** — אין veto שמונע LONG ב-day-trend=RED |
| A4 touch-point degraded (tpo/veto/killzone/layer0 missing) | advisory | 🟡 לא חוסם (PASS) |
| choppiness / Layer-0 chop | 0 | ✅ מושבת ב-standing decision (2026-06-08) — לא גורם היום |
| day_type (Variation↔Normal split) | 0 | ✅ לא חוסם (S2 10/10 armed) — residual instance בלבד (I-1) |
| footprint / S3 | 0 | ✅ מושתק (S3_MUTE), נדחה עד אחרי LIVE — לא חוסם (I-11) |
| sizing (A5) | 0 | ✅ PASS sizing=half |

### תוקנו מול פתוחים
- **I-16 choppiness_ok** — *לא גורם היום*. שערי-chop מושבתים בהחלטת-קבע (2026-06-08); 0 חסימות.
- **I-1 day_type** — *לא חוסם*. S2 10/10 armed; נותר רק פיצול-instance תצוגתי (Variation↔Normal) + session_min=0.
- **I-3 / A7 missing fire_setup / טבלת stop-target** — 🔴 **פתוח, החוסם הדומיננטי**. חסם את כל 13 השורטים
  + ה-TLB החי. השורש: target מנוון (reward קצר מול stop מבני) ⇒ R:R<1.0 ⇒ אין fire_setup. **התיקון =
  טבלת stop/target פר-תבנית×day-type** (anchor מבני) — בדיוק הממד-החסר שכבר תועד.
- **🆕 HFE-LONG נגד-מגמה** — 🔴 **פתוח, חדש**. 3 לונגים נפלטו ב-day-trend=RED ונעצרו (−3R). ה-A7 R:R-gate
  אסימטרי: סינן שורטים תקפים (stop רחב→R:R<1) והעביר לונגים הפוכים (stop צמוד→R:R≥1). דרוש trend-alignment
  veto או נימול-stop אחיד.

## נטיפיקציה ל-Michael
**16 setups פוספסו (13 שורטי-אחה"צ zlr_detected + 3 שורטי-benchmark בוקר), ΣR-נגד שמרני +3.61R
(עד +6.61R / MFE 2.9–11.7R), החוסם המוביל = A7 `R:R<1.0` (טבלת stop/target חסרה, I-3), benchmark:
0/5 ירו. בנוסף: 3 HFE-LONG נגד-מגמה ירו ל-−3R — gate אסימטרי. אישור detector-flags לבוקר ממתין
להצלבת CC מול DB.**

---
*נוצר אוטונומית ע"י Cowork. CCI מאומת מ-Sierra (`sierra_woodies_5min_json`). replay = OHLC חי.
ההמלצה היחידה: טבלת stop/target (I-3) פותחת בו-זמנית את כל 13 השורטים + מתקנת את אסימטריית ה-A7.
לא שונה קוד.*
