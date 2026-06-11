# MEMS26 · דוח EOD מאוחד — 2026-06-10

**שער-זמן (I-9):** ✅ הופק אחרי הסגירה — בעת הריצה השעה **15:24 CT** (≥15:00 CT). RTH 08:30–15:00 CT.
**מקורות:** 9 snapshots עמוקים ב-`PATTERN_DIAG_2026-06-10.md` (09:54 / 10:18 / 10:44 / 11:18 / 11:48 / 12:14 / 12:43 / 13:13 / 14:52 CT) + API חי דרך Chrome (`/api/v9/trades/recent?limit=100`=8 עסקאות · `/api/v9/chart/bars5min?limit=100`=78 ברי-RTH של היום).
**מצב-יום:** **יום-מגמה RED נקי** — נפתח ~7355, ירד ברציפות לסגירה **7276** (session high 7404.75 = IB · session low 7275). cci_14 התנדנד חריף סביב אפס לאורך היום (+113 ↔ −134, חציות-בר תכופות, I-17). day_type **פיצול** Normal(readiness/Build-header) ↔ Variation(state/Dashboard/S2-gate) 0.48 · `session_min=0` · `vote_history=[]` (I-1) — **לא חוסם ירי**. **קריאה/תיעוד בלבד — לא נגעתי בקוד.**

> **כותרת-העל של היום (מבחן UAT-נגד):** המערכת עשתה את ההפך-הנכון משני הצדדים — **ירתה 3 עסקאות-נגד-מגמה** (HFE LONG בתוך trend RED, 3/3 −1R) **וחסמה את כל הסיגנלים עם-המגמה** (ZLR/TLB/GB100/GHOST/HTLB SHORT) על שער R:R<1.0. בתחזית-נגד, ה-SHORTים עם-המגמה היו **כולם מנצחים** (ΣR ≈ +3R). שורש-יחיד לשני הצדדים = **היעדר טבלת stop/target (I-13/I-3)**.

---

## 1. עסקאות שנורו היום (3 — כולן S4 HFE LONG · כולן STOP_HIT)

| sys | תבנית | id | כיוון | entry | stop (pt) | T1 | כניסה CT | תוצאה | R אמיתי | MFE | MAE |
|-----|-------|----|-------|-------|-----------|----|----------|-------|---------|-----|-----|
| **S4** | HFE | 24 | LONG | 7338.5 | 7337.5 (**1.0**) | 7341.5 | 10:09:57 | STOP_HIT | **−1R** / −$15 | 2.5 | 11.75 |
| **S4** | HFE | 26 | LONG | 7339.25 | 7337.25 (**2.0**) | 7342.25 | 10:10:04 | STOP_HIT | **−1R** / −$30 | 0 | 23.75 |
| **S4** | HFE | 27 | LONG | 7327.5 | 7325.75 (**1.75**) | 7330.5 | 10:15:05 | STOP_HIT | **−1R** / −$26.25 | **16.75** | 6.75 |

**ΣR אמיתי = −3R (~−$71.25 shadow).** כל ה-3 הן **reversal-LONG בתוך trend RED** (נגד-מגמה), `day_type=Normal`, `t2=null` (T1 בלבד), חיו ~3–5 דק' (בר אחד) עד stop.

**שני ממצאים קונקרטיים על ה-3:**
- **id27 — מנצח שנשרף ע"י stop-צמוד.** stop 1.75pt אך **MFE +16.75pt** ⇒ המהלך היה חד לטובת הכניסה (עבר את T1 ב-3pt ומעבר), אך ה-stop-הצמוד נחתך ברעש-הבר. עם stop סביר (≥7pt) זו היתה עסקה מנצחת גדולה.
- **id24/id26 — מפסידים אמיתיים.** MAE 11.75 / 23.75pt מול MFE 2.5 / 0 — תנועה-נגדית אמיתית מיד עם הכניסה (longs נגד trend RED). stop רחב לא היה מציל אותן.

**`pnl_r` על stop-outs טריים = −1R נכון** (id27 C1 `−8.75÷(1.75pt×$5)=−1.0R`) — המחלק-השבור (I-22) **לא** משפיע על stop-out. ה-win-path המנופח (id20 06-09 `233R`, id13 06-05 `+26.75R` על STOP_HIT) עדיין לא-מאומת-תיקון כי **אין WIN טרי ב-06-10**.

---

## 2. טבלת תבניות מסודרת — נדרכה / נורתה / נחסמה

טווח: 9 snapshots (09:54–14:52 CT). "נדרכה" = armed/eligible. pre-IB אינו רלוונטי (ה-snapshot הראשון 09:54 כבר post-IB, IB locked).

| מערכת | תבנית | נדרכה # | נורתה # | לא-נדרכה # (סיבות) | לא-נורתה # (פירוק דחייה) | תחזית-נגד: W/L, ΣR |
|-------|-------|---------|---------|--------------------|--------------------------|---------------------|
| **S2** | REACTIVE_L/S · INITIATIVE_L/S · BULL_FLAG · BEAR_FLAG (6 מומנטום) | armed **9/9** (כל post-IB) | **0** | 0 | **detection-await אמיתי בבר** בלבד: `b1_expansion`/`b1_buyers`/`b2_volume_drop`/`pole_found`/`flag_length`. **אין** auth-block, **אין** `Missing: choppiness_ok` (gate DISABLED per החלטה-עומדת, I-16 לא-משחזר) | — (אין setup; detected 0/setups 0) |
| **S2** | INV_HNS · HNS_TOP · DBL_BOTTOM_EE · DBL_TOP_AA (4 day-patterns) | armed-חלקי | 0 | חלק: `auth_table_cell × day_type` (חוסם **לגיטימית**) | + detection (`swing_lows/highs_found`, `neckline_breakout`) | — (חסימה מוצדקת) |
| **S3** | ABSORPTION · STACKED_IMB · SWEEP_RETURN · EXHAUSTION | **0/9** | 0 | **9/9:** `data.bars_today=0`+`data.buffer_size=0` — שורש **I-11 ingest-break** (file→bridge→buffer; gate present אך 0 ברים); מושתק S3_MUTE/crit=false | — | — (אין נתון כלל; S3 deferred עד אחרי-LIVE) |
| **S4** | **HFE** | armed (ירה) | **3** (id24/26/27 @10:09–10:15) | 0 | — (נורתה ×3, כולן −1R) | **CF (stop סביר ~8pt + targets שפויים): 1W/2L, ΣR ≈ −0.5R** (id27 →+1.5R · id24/26 →−1R) |
| **S4** | **ZLR · TLB · GB100 · GHOST · HTLB** (SHORT עם-המגמה) | armed; הגיעו ל-**A7 ≥4×** | **0** | 0 (כש-trend RED יציב) | **A7 FAIL R:R<1.0** (#4 17.75/8.88 · #5 ≈0.18 · #6 0.5 · #8 ≈0.65) → `targets_stop.r_t1_gate/stop_price/targets`+`exit_rules.ready_to_route`. **target מנוון 3pt** מול stop 12–20pt | **CF (targets שפויים 1R/2R): 4W/0L, ΣR ≈ +3R** (ראה §3) |
| **S4** | TT · Vegas · FaMir | armed | 0 | ~2 snapshots A1-GRAY-veto (flicker) | `detection.pattern_specific` (אין דפוס בבר) + `targets_stop.*` | — (אין setup טרי) |
| **S1** | Day Type (gate) | armed/classified | — | — | פיצול Normal↔Variation (I-1); `session_min=0`/`vote_history=[]` | — (סיווג, לא חוסם ירי) |

---

## 3. תחזית-נגד (counterfactual) — שחזור ברים בפועל

שוחזר מ-**78 ברי-5דק' של RTH היום** (`bars5min`, ts IL = CT+8h). שיטה: entry/stop לפי ספק-התבנית; **targets שפויים** T1=entry−1R / T2=entry−2R (כי ה-targets בפועל היו מנוונים 3pt); יציאה-מדורגת (חצי ב-T1, stop ל-BE, רץ ל-T2); intrabar שמרני (stop-קודם אם שניהם בבר). יום-המגמה ירד 7329→7276.

### 3a. סיגנלים שנחסמו (S4 SHORT עם-המגמה) — מה היה אילו נורו

| signal | snapshot/CT | entry | stop | risk(pt) | מסלול (ברים בפועל) | R משוער |
|--------|-------------|-------|------|----------|---------------------|---------|
| **ZLR/TLB SHORT** | #4 11:18 | 7329 | 7349.25 | 20.25 | T1@12:10 CT · רץ נעצר BE@13:00 | **+0.5R** ✅ |
| **ZLR+TLB SHORT** | #5 11:47 | 7328 | 7344.75 | 16.75 | T1@12:10 CT · רץ נעצר BE@12:55 | **+0.5R** ✅ |
| **ZLR/GB100/GHOST/HTLB SHORT** | #6 12:14 | 7317.25 | 7335.25 | 18.0 | T1@12:40 CT · רץ נעצר BE@12:45 | **+0.5R** ✅ |
| **TLB SHORT** | #8 13:13 | 7326.5 | 7339.25 | 12.75 | T1@13:20 CT · **T2@13:45** | **+1.5R** ✅ |

**ΣR-נגד (S4 SHORT, targets שפויים): ≈ +3R · 4W/0L.** כל סיגנל עם-המגמה היה רווחי. ה-runners ברובם נעצרו ב-BE על pullback-ים (היום ירד אך בגליות), פרט ל-#8 שרץ נקי ל-T2.
**הסתייגות-כפילות:** 4 הסיגנלים הם **re-detection של אותו מהלך-ירידה** — לא 4 עסקאות עצמאיות. ההזדמנות-שפוספסה האמיתית ≈ **+1.5R עד +3R** (כניסה-אחת או שתיים לא-חופפות לאורך היום), לא סכום-נאיבי.
**מסקנה:** שלא כמו 06-09 (ΣR-נגד ≈ +1R, "לא קטע רווח משמעותי"), **היום ה-bottleneck של S4 כן עלה לנו על רווח עקבי עם-המגמה** — שער ה-A7 R:R **צודק מתמטית** (target מנוון 3pt), אבל סימן את **היעדר טבלת ה-stop/target** שמנעה כניסה רווחית.

### 3b. העסקאות שנורו (S4 HFE LONG, נגד-מגמה) — מה היה עם stop סביר

| id | MFE | MAE | stop-CF | מסלול | R-CF |
|----|-----|-----|---------|-------|------|
| 27 | 16.75 | 6.75 | ~8pt | שורד (MAE<stop) → T1+רץ ל-MFE 16.75 | **+1.5R** ✅ |
| 24 | 2.5 | 11.75 | ~8pt | נעצר (MAE>stop), אין מהלך-לטובה | **−1R** ❌ |
| 26 | 0 | 23.75 | ~8pt | נעצר מיד (MAE 23.75) | **−1R** ❌ |

**ΣR-נגד (HFE LONG, stop סביר): ≈ −0.5R** (מול −3R בפועל). stop-נכון היה **חוסך ~2.5R** (הופך את id27 למנצח), אך id24/26 הם **מפסידים-נגד-מגמה אמיתיים** — wide stop לא מציל אותם. ⇒ פתרון ה-stop/target נחוץ אך **לא מספיק** ל-HFE; נדרש גם סינון-מגמה ל-reversal-patterns (חשוד-חדש I-28).

---

## 4. לקחים

**תבניות שנדרכות-הרבה-ולא-יורות (ולמה):**
- **S4 ZLR/TLB/GB100/GHOST/HTLB** — נדרכו והגיעו ל-A7 ≥4× אך **לא ירו לעולם**: ה-`targets_stop` מייצר **target מנוון 3pt** מול stop 12–20pt ⇒ `r_t1_gate`/R:R<1.0 תמיד. **שורש מבני = היעדר טבלת stop/target פר-תבנית×day-type (I-3/I-13)**. זהו ה-bottleneck #1 של S4, ו-§3a מוכיח שהיום הוא עלה לנו על ~+3R עם-המגמה.
- **S4 HFE** — ירה דווקא (3×) אבל **נגד-המגמה ועם stop צמוד 1–2pt** → 3/3 נשרפו. id27 (MFE +16.75pt) מוכיח את עלות ה-stop-הצמוד; id24/26 מוכיחים שגם reversal-LONG-נגד-RED הוא בעיית-איכות (חשוד-חדש I-28).
- **S2 מומנטום (6)** — נדרכו 9/9 אך 0 ירו: detection-await אמיתי (detected 0/setups 0). דריכה תקינה — לא חסימה-שגויה. **אין** `choppiness_ok` block (I-16 לא-משחזר, gate DISABLED).

**תבניות שלא-נדרכות (ולמה):**
- **S3 footprint (4)** — 0 ברים כל היום (`bars_today=0`). שורש **I-11**: ingest file→bridge→buffer שבור (gate present, buffer ריק). מושתק בכוונה (S3_MUTE) — deferred עד אחרי-LIVE, **לא blocker**.
- **S2 day-patterns (4)** — נחסמו חלקית על `auth_table_cell × day_type` + detection. **חסימה מוצדקת.**

**דחיות מוצדקות מול שמרניות-מדי:**
- **מוצדקות מתמטית, שגויות-בשורש:** כל חסימות ה-A7 R:R<1.0 על S4 SHORT **נכונות** בהינתן ה-target המנוון — אבל ה-target המנוון עצמו הוא הבאג (I-13). ⇒ הדחייה "נכונה" חוסמת עסקה שהיתה רווחית. זו **הדגמה ישירה שטבלת ה-stop/target חסרה עולה כסף**, לא שמרנות-יתר בסף.
- **A1 GRAY-veto** (flicker סביב חציית-אפס, #5/#7) — לגיטימי כש-trend אינדטרמיננטי, אך מוגבר ע"י תנודתיות-גבול-בר (I-17).
- **לא נמצאה דחייה שמרנית-מדי בסף עצמו.** הבעיה הפוכה: (א) target מנוון חוסם כניסות-טובות, (ב) stop צמוד שורף עסקאות-שירו, (ג) HFE יורה נגד-מגמה.

---

## 5. מקור-אמת — דורש הצלבת CC מול Sierra v9_export

לסמן ל-CC (לא כאן):
1. **HFE/S4 stop+target (I-3/I-13)** — מקור ה-stop (1–2pt בפועל) וה-target (מנוון 3pt). נדרשת **טבלת stop/target פר-תבנית×day_type** מבוססת ATR/מבנה Sierra. **עדיפות-LIVE #1.**
2. **`pnl_r` מחלק (I-22)** — id20 (06-09) `233R/$582.5` + id13 (06-05) `+26.75R` על STOP_HIT = `÷טיק($1.25)` במקום `÷risk_$ פר-חוזה ($12.50)` ⇒ ×10. הצלב על **WIN/partial טרי** (היום היו רק stop-outs).
3. **A7 reward ↔ target מוצג (I-26, חדש)** — ב-#3 ה-active-pattern הציג target 1pt מ-entry אך A7 reward מחושב=6.00 ⇒ אי-עקביות פנימית. מאיפה מגיע ה-reward?
4. **CCI-14/TCCI גולמי (I-15/I-17)** — חציות-אפס תוך-בר (+10.13→−28.5 ב-~100s; +113↔−134 לאורך היום). engine↔board **מסכימים** same-instant (I-15 לא-משחזר), אך נדרש גולמי-Sierra לברים-הגבול לוודא שזה לא artifact-בקנד.
5. **footprint ingest-break (I-11)** — קובץ נכתב (gate `[FRESH]`) אך 0 ברים ל-buffer. parse/ingest.
6. **freshness TZ-mix + ts-עתידי (I-18/I-20)** — `woodies_5min` gate ts-עתידי/`lag=null`; `imbalance` crit:true [FRESH] אך lag עד ~111דק' > 90s עובר READY (כשל-שקט). נרמול-TZ + אכיפת-סף על Present. Rule 4.
7. **prev_day IB/atr_daily (I-1)** — `Y IB dll_missing` (Input 19 / Y-IB study=0) — חשוד-שורש ל-day_type split + `session_min=0` + `vote_history=[]`.

**NOT-DONE / מגבלות:**
- **אין WIN/partial טרי 06-10** (3 fires = −1R stop-out) ⇒ תיקון-מחלק I-22 לא-מאומת-מלא; מאומת רק ש-stop-out −1R נכון.
- ה-counterfactual של §3a מבוסס **targets שפויים שלי (1R/2R)**, לא טבלת-stop/target אמיתית — כשתוגדר, לחשב מחדש.
- ה-counterfactual של §3b משתמש ב-MFE/MAE הסטטיים (CLOSED trades) + stop-CF משוער ~8pt — להחליף ב-ATR-Sierra אמיתי כשיוגדר.
- כל הצלבת-Sierra v9_export = CC (read-only כאן). פיצול day_type + future-ts = feed-instance, CC.
