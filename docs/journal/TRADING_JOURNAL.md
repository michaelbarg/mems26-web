# יומן-מסחר חי — MEMS26 (נוצר אוטומטית בסוף כל יום ע״י `scripts/eod_journal.py`; מחיר-ברוקר; הכללים: `docs/journal/FIX_LEDGER.md`)

## 2026-10-21 (Wed) — נכתב 2026-10-21 23:21 IL

**לייב היום:** 0 עסקאות · Σ **+0.00$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ -232.50$ (7) · מאז 07.07 Σ -927.50$ (194)
**דמו היום:** 8 עסקאות · 2W/4L · Σ **-376.25$** (ספרים; Sierra כשתומחר) · 2 לא-מתומחרות · לפי סיירה (Sim1) -368.75$

| שעה | מערכת | תבנית | כיוון | חוזים | יציאה | $ | מקור |
|---|---|---|---|---|---|---|---|
| 16:50 | S2 | OPENING_EXTREME_REJECT | LONG | 3 | STOP_HIT | -225.00 | ספרים |
| 17:20 | S2 | CEILING_FLIP_TOUCH2 | LONG | 5 | t3_missing | — | לא-מתומחר |
| 17:25 | S2 | CEILING_FLIP_TOUCH2 | LONG | 5 | t3_missing | — | לא-מתומחר |
| 17:55 | S2 | CEILING_FLIP_TOUCH2 | SHORT | 5 | STOP_HIT | -118.75 | ספרים |
| 18:45 | S2 | CEILING_FLIP_TOUCH2 | SHORT | 5 | STOP_HIT | -75.00 | ספרים |
| 19:20 | S2 | CEILING_FLIP_TOUCH2 | SHORT | 5 | STOP_HIT | +97.50 | ספרים |
| 19:45 | S2 | CEILING_FLIP_TOUCH2 | SHORT | 5 | STOP_HIT | -160.00 | ספרים |
| 20:25 | S2 | CEILING_FLIP_TOUCH2 | SHORT | 5 | STOP_HIT | +105.00 | ספרים |

**פתיחה:** מערכת **OPEN_AUCTION_IN** (נעילה 17:30 at IB lock, dir NEUTRAL, 0 ביטולים) · ברים **OPEN_REJECTION_REVERSE** — דרייב ואז חזרה דרך הפתיחה; פתיחה 7779.25 בתוך-טווח (אתמול H/L 7791.5/7710.25, VAH/VAL/POC 7774.5/7746.25/7757.75); 30 דק׳ H/L 7780.75/7764.5, נטו -5.50 · ✗ לא תואם
**סוג-יום:** מערכת 17:30 Normal · 18:30 Normal · 21:00 Variation · אחרון Variation · EOD Variation · 2 ריצודים (101 וקטורים) · ברים **Normal_Variation** (IB 7780.75/7751.0 · טווח 7751.0–7811.75 · rib 2.04 · סגירה 7802.0 pos 0.84 · הרחבה ↑כן ↓לא) · סגירה−פתיחה +22.75
**החלטות:** 101 (עברו את העץ 60) · חסימות: tree:stand_down 13 · tree:location 12 · tree:time_cutoff 9 · tree:bias 5 · tree:kind 2
**בריאות:** backend pid — · feed 26 דק׳ · סוכנים 0 · AC 100% · gap_backfill: gap_backfill 2026-10-21 22:43 IL · battery AC 100% · all 15 trading days have 78 RTH bars 

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** CEILING_FLIP_SHORT n=2 +11$ · DOUBLE_BOTTOM_EE_LONG n=1 +0$ · OPENING_TEST_DRIVE n=1 -44$ · DALTON_EDGE_SHORT n=1 -55$ · CEILING_FLIP_LONG n=1 -65$ · OPENING_DRIVE n=1 -80$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `S1-opening-lock` — S1 נעל סוג-פתיחה שונה מקריאת-הברים — שורש T-594 (נעילה בלי רפרנסים-קודמים) / T-595 (מכונה על בר שטוח); המדידה: hist_o / hist_p / hist_po. *ראיה:* 2026-10-21: מערכת OPEN_AUCTION_IN (17:30 at IB lock) · ברים OPEN_REJECTION_REVERSE (דרייב ואז חזרה דרך הפתיחה; 30 דק׳ נטו -5.50, בתוך-טווח)

**שיקול-דעת (הסוכן):** לפי דלתון (ברים) היום נפתח בתוך טווח אתמול (7779.25), דחה מטה וחזר דרך הפתיחה (OPEN_REJECTION_REVERSE, 30 דק׳ נטו -5.50) ואז התפתח ל-Normal_Variation עם הרחבה ↑ בלבד וסגירה ב-pos 0.84 (+22.75 מהפתיחה). המערכת נעלה OPEN_AUCTION_IN/NEUTRAL ב-17:30 (✗ לא תואם לברים), תייגה Normal עד 18:30 ו-Variation רק מ-21:00 (2 ריצודים), ובדמו S2 ירה 8 עסקאות (2W/4L, Σ -376.25$, 2 לא-מתומחרות): לונג OPENING_EXTREME_REJECT ב-16:50 (-225$) ו-5 שורטים CEILING_FLIP_TOUCH2 נגד ההרחבה כלפי מעלה (2W/3L, Σ -151.25$); לייב 0. התיקון הכי שווה-כסף: `S1-opening-lock` (T-594/T-595) — נעילת-פתיחה בלי רפרנסים-קודמים / על בר שטוח היא מה שהשאיר את S2 בלי ההקשר של יום-הרחבה-למעלה. לאמת, לא להדליק: ב-474 סשני hist_o/hist_p — שיעור ההתאמה נעילה↔ברים, ו-P&L של שורטי CEILING_FLIP_TOUCH2 בימי Normal_Variation עם הרחבה ↑ בלבד (מועמד ל-SKIP).
**מדידה לילית:** chain9b `HISTPR_DONE` / `CHAIN9B_DONE` · hist_o 474 · hist_p 474 (סשנים שנמדדו ל-T-594 / T-593)

## 2026-10-19 (Mon) — נכתב 2026-10-19 23:21 IL

**לייב היום:** 0 עסקאות · Σ **+0.00$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ -238.75$ (11) · מאז 07.07 Σ -927.50$ (194)

**פתיחה:** מערכת **OPEN_REJECTION_REVERSE** (נעילה 16:45 at bar 4, dir DOWN, 3 ביטולים) · ברים **OPEN_REJECTION_REVERSE** — דרייב ואז חזרה דרך הפתיחה; פתיחה 7741.5 בתוך-ערך (אתמול H/L 7803.0/7676.0, VAH/VAL/POC 7761.25/7679.0/7703.0); 30 דק׳ H/L 7749.75/7731.25, נטו -6.50 · ✓ תואם
**סוג-יום:** מערכת 17:30 Normal · 18:30 Normal · 21:00 Variation · אחרון Variation · EOD Variation · 1 ריצודים (109 וקטורים) · ברים **Normal_Variation** (IB 7759.75/7727.5 · טווח 7727.5–7773.25 · rib 1.42 · סגירה 7734.75 pos 0.16 · הרחבה ↑כן ↓לא) · סגירה−פתיחה -6.75
**החלטות:** 109 (עברו את העץ 28) · חסימות: tree:bias 31 · tree:location 28 · tree:time_cutoff 13 · tree:stand_down 9
**בריאות:** backend pid 89555 · feed 1 דק׳ · סוכנים 11 · AC 100% · gap_backfill: gap_backfill 2026-10-19 23:12 IL · battery AC 100% · all 15 trading days have 78 RTH bars 

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** DALTON_EDGE_LONG n=1 +29$ · GB100 n=1 +21$ · CEILING_FLIP_SHORT n=2 +11$ · DOUBLE_BOTTOM_EE_LONG n=1 +0$ · OPENING_TEST_DRIVE n=1 -44$ · DALTON_EDGE_SHORT n=1 -55$ · FAMIR n=2 -56$ · CEILING_FLIP_LONG n=1 -65$ · OPENING_DRIVE n=1 -80$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
— אין המלצה אוטומטית היום.

**שיקול-דעת (הסוכן):** דלתון: פתיחה 7741.5 בתוך-ערך (בין POC 7703 ל-VAH 7761.25) עם OPEN_REJECTION_REVERSE — דרייב וחזרה דרך הפתיחה, IB צר 7727.5–7759.75, הרחבה למעלה בלבד (rib 1.42) שלא החזיקה וסגירה 7734.75 בתחתית הטווח (pos 0.16): יום Normal_Variation רוטציוני, סגירה−פתיחה -6.75, בלי קצה ברור. המערכת נעלה OPEN_REJECTION_REVERSE DOWN ב-16:45 (בר 4, אחרי 3 ביטולים) ✓ תואם לברים, תייגה Normal→Variation מ-21:00 עם ריצוד אחד בלבד ✓, ונשארה מחוץ לשוק: 0 עסקאות מ-109 החלטות (28 עברו את העץ; חסימות: bias 31, location 28, time_cutoff 13, stand_down 9) — התנהגות סבירה ליום כזה. אין המלצה אוטומטית היום; המועמד היחיד ל-SKIP שעולה מטבלת 10 הסשנים הוא משפחת OPENING_DRIVE/OPENING_TEST_DRIVE (-124$ על n=2) — אבל n=2 אינו ראיה. למדוד, לא לשנות: תוחלת לפי תבנית על 194 העסקאות מאז 07.07 ועל 15 ימי ה-RTH המלאים (78 ברים) שאחרי ה-gap_backfill, בפיצול לפי סוג-הפתיחה מהברים; ובנפרד — למה 28 ההחלטות שעברו את העץ לא הפכו לעסקה (תנאי-כניסה של תבנית או חסימה מאוחרת).
**מדידה לילית (chain9b):** רץ — אחרון בלוג `done 2026-03-24 hist_d rc=0` (שלב hist_d); סשנים שנמדדו ב-harness_out/t466: hist_o (T-594) 0 · hist_p (T-593) 0.


## 2026-10-16 (Fri) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 0 עסקאות · Σ **+0.00$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ -293.75$ (13) · מאז 07.07 Σ -1008.75$ (194)

**פתיחה:** מערכת **—** (אין שורת-נעילה בלוג; לפי EOD) · ברים **OPEN_DRIVE** — אין חזרה לפתיחה בברים 2–6 (↓); פתיחה 7802.75 מחוץ-לטווח מעל (אתמול H/L 7801.75/7717.25, VAH/VAL/POC 7801.75/7759.0/7769.0); 30 דק׳ H/L 7803.0/7779.75, נטו -19.00 · ✗ לא תואם
**סוג-יום:** מערכת 17:30 — · 18:30 — · 21:00 — · אחרון — · EOD — · 0 ריצודים (0 וקטורים) · ברים **Normal_Variation** (IB 7803.0/7774.5 · טווח 7676.0–7803.0 · rib 4.46 · סגירה 7703.0 pos 0.21 · הרחבה ↑לא ↓כן) · סגירה−פתיחה -99.75
**החלטות:** 0 (עברו את העץ 0) · חסימות: —
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** DALTON_EDGE_LONG n=1 +29$ · DOUBLE_BOTTOM_EE_LONG n=1 +0$ · GB100 n=2 -6$ · CEILING_FLIP_SHORT n=3 -16$ · OPENING_TEST_DRIVE n=1 -44$ · DALTON_EDGE_SHORT n=1 -55$ · FAMIR n=2 -56$ · CEILING_FLIP_LONG n=1 -65$ · OPENING_DRIVE n=1 -80$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `S1-opening-lock` — S1 נעל סוג-פתיחה שונה מקריאת-הברים — שורש T-594 (נעילה בלי רפרנסים-קודמים) / T-595 (מכונה על בר שטוח); המדידה: hist_o / hist_p / hist_po. *ראיה:* 2026-10-16: מערכת — (EOD) · ברים OPEN_DRIVE (אין חזרה לפתיחה בברים 2–6 (↓); 30 דק׳ נטו -19.00, מחוץ-לטווח מעל)
2. `pattern-CEILING_FLIP_SHORT` — התבנית CEILING_FLIP_SHORT מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-16: n=3 · wins 1 · Σ -16.25$ (מחיר-ברוקר)

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-09 (Fri) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 3 עסקאות · Σ **-80.00$** (מחיר-ברוקר; 2 לפי ספרים) · 10 סשנים אחרונים Σ -356.25$ (25) · מאז 07.07 Σ -1008.75$ (194)

| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |
|---|---|---|---|---|---|---|---|---|
| 16:45 | S2 | OPENING_DRIVE | SHORT | ? | 1 | STOP_HIT | -80.00 | ✓ |
| 18:10 | S2 | CEILING_FLIP_SHORT | SHORT | Variation | 1 | SIERRA_FLAT | +0.00 | ✗ ספרים |
| 18:15 | S2 | DOUBLE_BOTTOM_EE_LONG | LONG | Variation | 1 | SIERRA_FLAT | +0.00 | ✗ ספרים |

**פתיחה:** מערכת **OPEN_REJECTION_REVERSE** (נעילה 16:45 at bar 4, dir DOWN, 1 ביטולים) · ברים **OPEN_REJECTION_REVERSE** — דרייב ואז חזרה דרך הפתיחה; פתיחה 7838.25 בתוך-טווח (אתמול H/L 7850.0/7783.0, VAH/VAL/POC 7831.25/7792.5/7811.75); 30 דק׳ H/L 7844.25/7826.5, נטו -2.50 · ✓ תואם
**סוג-יום:** מערכת 17:30 Variation · 18:30 Variation · 21:00 Variation · אחרון Variation · EOD Variation · 4 ריצודים (49 וקטורים) · ברים **Normal_Variation** (IB 7844.25/7826.5 · טווח 7826.5–7870.75 · rib 2.49 · סגירה 7859.25 pos 0.74 · הרחבה ↑כן ↓לא) · סגירה−פתיחה +21.00
**החלטות:** 49 (עברו את העץ 23) · חסימות: tree:stand_down 16 · tree:bias 9 · tree:kind 1
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=2 +84$ · DOUBLE_TOP_AA_SHORT n=2 +46$ · DALTON_EDGE_LONG n=1 +29$ · DOUBLE_BOTTOM_EE_LONG n=1 +0$ · DALTON_EDGE_SHORT n=2 -9$ · VEGAS n=1 -34$ · GHOST n=1 -39$ · GB100 n=3 -51$ · INITIATIVE_SHORT n=1 -56$ · FAMIR n=2 -56$ · OPENING_EXTREME_REJECT n=1 -61$ · CEILING_FLIP_SHORT n=4 -61$ · CEILING_FLIP_LONG n=3 -68$ · OPENING_DRIVE n=1 -80$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `pattern-CEILING_FLIP_LONG` — התבנית CEILING_FLIP_LONG מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-09: n=3 · wins 1 · Σ -67.50$ (מחיר-ברוקר)
2. `pattern-CEILING_FLIP_SHORT` — התבנית CEILING_FLIP_SHORT מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-09: n=4 · wins 1 · Σ -61.25$ (מחיר-ברוקר)
3. `pattern-GB100` — התבנית GB100 מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-09: n=3 · wins 1 · Σ -51.25$ (מחיר-ברוקר)
4. `books-unpriced` — עסקאות בלי מחיר-ברוקר (pnl_sierra ריק) — להשלים את ה-reconcile (T-10) לפני שמסתמכים על Σ. *ראיה:* 2026-10-09: 2 מתוך 3

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-08 (Thu) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 4 עסקאות · Σ **-152.50$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ -203.75$ (23) · מאז 07.07 Σ -928.75$ (191)

| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |
|---|---|---|---|---|---|---|---|---|
| 16:45 | S2 | OPENING_TEST_DRIVE | SHORT | ? | 1 | STOP_HIT | -43.75 | ✓ |
| 16:55 | S2 | DALTON_EDGE_SHORT | SHORT | ? | 1 | STOP_HIT | -55.00 | ✓ |
| 17:40 | S2 | CEILING_FLIP_SHORT | SHORT | Normal | 1 | STOP_HIT | +11.25 | ✓ |
| 19:20 | S2 | CEILING_FLIP_LONG | LONG | Variation | 1 | STOP_HIT | -65.00 | ✓ |

**פתיחה:** מערכת **OPEN_REJECTION_REVERSE** (נעילה 16:45 at bar 4, dir DOWN, 1 ביטולים) · ברים **OPEN_REJECTION_REVERSE** — דרייב ואז חזרה דרך הפתיחה; פתיחה 7827.25 בתוך-טווח (אתמול H/L 7859.5/7815.75, VAH/VAL/POC 7858.5/7829.5/7851.25); 30 דק׳ H/L 7836.25/7822.75, נטו +4.00 · ✓ תואם
**סוג-יום:** מערכת 17:30 Normal · 18:30 Normal · 21:00 Variation · אחרון Variation · EOD Variation · 4 ריצודים (97 וקטורים) · ברים **Normal_Variation** (IB 7844.5/7822.75 · טווח 7783.0–7850.0 · rib 3.08 · סגירה 7817.5 pos 0.51 · הרחבה ↑לא ↓כן) · סגירה−פתיחה -9.75
**החלטות:** 97 (עברו את העץ 50) · חסימות: tree:stand_down 15 · tree:time_cutoff 14 · tree:bias 9 · tree:location 5 · tree:kind 4
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=2 +84$ · DOUBLE_BOTTOM_EE_LONG n=1 +72$ · DOUBLE_TOP_AA_SHORT n=2 +46$ · DALTON_EDGE_LONG n=1 +29$ · DALTON_EDGE_SHORT n=2 -9$ · VEGAS n=1 -34$ · GHOST n=1 -39$ · GB100 n=3 -51$ · INITIATIVE_SHORT n=1 -56$ · FAMIR n=2 -56$ · OPENING_EXTREME_REJECT n=1 -61$ · CEILING_FLIP_SHORT n=3 -61$ · CEILING_FLIP_LONG n=3 -68$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `pattern-CEILING_FLIP_LONG` — התבנית CEILING_FLIP_LONG מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-08: n=3 · wins 1 · Σ -67.50$ (מחיר-ברוקר)
2. `pattern-CEILING_FLIP_SHORT` — התבנית CEILING_FLIP_SHORT מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-08: n=3 · wins 1 · Σ -61.25$ (מחיר-ברוקר)
3. `pattern-GB100` — התבנית GB100 מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-08: n=3 · wins 1 · Σ -51.25$ (מחיר-ברוקר)

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-07 (Wed) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 0 עסקאות · Σ **+0.00$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ -90.00$ (20) · מאז 07.07 Σ -776.25$ (187)

**פתיחה:** מערכת **OPEN_AUCTION_IN** (נעילה 17:30 at IB lock, dir NEUTRAL, 0 ביטולים) · ברים **OPEN_DRIVE** — אין חזרה לפתיחה בברים 2–6 (↓); פתיחה 7837.5 מחוץ-לטווח מתחת (אתמול H/L 7897.5/7860.25, VAH/VAL/POC 7886.5/7870.5/7879.25); 30 דק׳ H/L 7842.25/7820.75, נטו -9.75 · ✗ לא תואם
**סוג-יום:** מערכת 17:30 Normal · 18:30 Variation · 21:00 Neutral_Extreme · אחרון Neutral_Center · EOD Neutral_Center · 4 ריצודים (106 וקטורים) · ברים **Neutral_Center** (IB 7842.25/7820.0 · טווח 7815.75–7859.5 · rib 1.97 · סגירה 7851.25 pos 0.81 · הרחבה ↑כן ↓כן) · סגירה−פתיחה +13.75
**החלטות:** 106 (עברו את העץ 56) · חסימות: tree:location 24 · tree:bias 10 · tree:time_cutoff 8 · tree:stand_down 6 · tree:kind 2
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=1 +128$ · DOUBLE_BOTTOM_EE_LONG n=1 +72$ · DALTON_EDGE_SHORT n=1 +46$ · DALTON_EDGE_LONG n=1 +29$ · DOUBLE_TOP_AA_SHORT n=3 +8$ · CEILING_FLIP_LONG n=2 -2$ · VEGAS n=1 -34$ · GHOST n=1 -39$ · GB100 n=3 -51$ · INITIATIVE_SHORT n=1 -56$ · FAMIR n=2 -56$ · OPENING_EXTREME_REJECT n=1 -61$ · CEILING_FLIP_SHORT n=2 -72$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `S1-opening-lock` — S1 נעל סוג-פתיחה שונה מקריאת-הברים — שורש T-594 (נעילה בלי רפרנסים-קודמים) / T-595 (מכונה על בר שטוח); המדידה: hist_o / hist_p / hist_po. *ראיה:* 2026-10-07: מערכת OPEN_AUCTION_IN (17:30 at IB lock) · ברים OPEN_DRIVE (אין חזרה לפתיחה בברים 2–6 (↓); 30 דק׳ נטו -9.75, מחוץ-לטווח מתחת)
2. `pattern-GB100` — התבנית GB100 מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-07: n=3 · wins 1 · Σ -51.25$ (מחיר-ברוקר)
3. `keep-DOUBLE_TOP_AA_SHORT` — התבנית DOUBLE_TOP_AA_SHORT מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-07: n=3 · wins 1 · Σ +7.50$

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-06 (Tue) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 4 עסקאות · Σ **-6.25$** (מחיר-ברוקר; 4 לפי ספרים) · 10 סשנים אחרונים Σ -108.75$ (21) · מאז 07.07 Σ -776.25$ (187)

| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |
|---|---|---|---|---|---|---|---|---|
| 19:10 | S4 | GB100 | SHORT | Variation | 1 | T1_HIT | +21.25 | ✗ ספרים |
| 19:35 | S4 | FAMIR | LONG | Variation | 1 | STOP_HIT | -56.25 | ✗ ספרים |
| 20:25 | S2 | DALTON_EDGE_LONG | LONG | Variation | 1 | T1_HIT | +28.75 | ✗ ספרים |
| 20:35 | S4 | FAMIR | LONG | Variation | 1 | SIERRA_FLAT | +0.00 | ✗ ספרים |

**פתיחה:** מערכת **OPEN_AUCTION_IN** (אין שורת-נעילה בלוג; לפי וקטורים) · ברים **OPEN_AUCTION_OUT** — סיבוב סביב הפתיחה מחוץ לטווח הקודם; פתיחה 7862.75 מחוץ-לטווח מעל (אתמול H/L 7847.75/7778.25, VAH/VAL/POC 7837.25/7797.75/7810.25); 30 דק׳ H/L 7880.75/7860.25, נטו +16.00 · ✗ לא תואם
**סוג-יום:** מערכת 17:30 Trend_Normal · 18:30 Normal · 21:00 Variation · אחרון Variation · EOD Variation · 4 ריצודים (60 וקטורים) · ברים **Normal_Variation** (IB 7888.0/7860.25 · טווח 7860.25–7897.5 · rib 1.34 · סגירה 7873.0 pos 0.34 · הרחבה ↑כן ↓לא) · סגירה−פתיחה +10.25
**החלטות:** 60 (עברו את העץ 32) · חסימות: tree:location 10 · tree:time_cutoff 6 · tree:bias 5 · tree:kind 5 · tree:stand_down 2
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=1 +128$ · DOUBLE_BOTTOM_EE_LONG n=1 +72$ · DALTON_EDGE_SHORT n=1 +46$ · DALTON_EDGE_LONG n=1 +29$ · DOUBLE_TOP_AA_SHORT n=3 +8$ · CEILING_FLIP_LONG n=2 -2$ · REACTIVE_LONG n=1 -19$ · VEGAS n=1 -34$ · GHOST n=1 -39$ · GB100 n=3 -51$ · INITIATIVE_SHORT n=1 -56$ · FAMIR n=2 -56$ · OPENING_EXTREME_REJECT n=1 -61$ · CEILING_FLIP_SHORT n=2 -72$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `S1-opening-lock` — S1 נעל סוג-פתיחה שונה מקריאת-הברים — שורש T-594 (נעילה בלי רפרנסים-קודמים) / T-595 (מכונה על בר שטוח); המדידה: hist_o / hist_p / hist_po. *ראיה:* 2026-10-06: מערכת OPEN_AUCTION_IN (EOD) · ברים OPEN_AUCTION_OUT (סיבוב סביב הפתיחה מחוץ לטווח הקודם; 30 דק׳ נטו +16.00, מחוץ-לטווח מעל)
2. `pattern-GB100` — התבנית GB100 מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-06: n=3 · wins 1 · Σ -51.25$ (מחיר-ברוקר)
3. `keep-DOUBLE_TOP_AA_SHORT` — התבנית DOUBLE_TOP_AA_SHORT מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-06: n=3 · wins 1 · Σ +7.50$
4. `books-unpriced` — עסקאות בלי מחיר-ברוקר (pnl_sierra ריק) — להשלים את ה-reconcile (T-10) לפני שמסתמכים על Σ. *ראיה:* 2026-10-06: 4 מתוך 4

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-05 (Mon) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 2 עסקאות · Σ **-55.00$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ -88.75$ (20) · מאז 07.07 Σ -770.00$ (183)

| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |
|---|---|---|---|---|---|---|---|---|
| 19:05 | S2 | CEILING_FLIP_SHORT | SHORT | Trend_Normal | 1 | STOP_HIT | -27.50 | ✓ |
| 19:25 | S4 | GB100 | LONG | Trend_Normal | 1 | BRACKET_EXIT_ACTIVITY | -27.50 | ✓ |

**פתיחה:** מערכת **OPEN_AUCTION_IN** (נעילה 17:30 at IB lock, dir NEUTRAL, 0 ביטולים) · ברים **OPEN_DRIVE** — אין חזרה לפתיחה בברים 2–6 (↑); פתיחה 7778.5 בתוך-ערך (אתמול H/L 7810.5/7754.0, VAH/VAL/POC 7792.5/7766.75/7776.25); 30 דק׳ H/L 7792.0/7778.25, נטו +8.75 · ✗ לא תואם
**סוג-יום:** מערכת 17:30 Trend_Normal · 18:30 Normal · 21:00 Trend_Normal · אחרון Trend_Normal · EOD Variation · 3 ריצודים (98 וקטורים) · ברים **Normal_Variation** (IB 7811.25/7778.25 · טווח 7778.25–7847.75 · rib 2.11 · סגירה 7831.25 pos 0.76 · הרחבה ↑כן ↓לא) · סגירה−פתיחה +52.75
**החלטות:** 98 (עברו את העץ 23) · חסימות: tree:time_cutoff 39 · tree:location 27 · tree:bias 5 · tree:kind 2 · tree:stand_down 2
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=1 +128$ · DOUBLE_BOTTOM_EE_LONG n=1 +72$ · DALTON_EDGE_SHORT n=1 +46$ · CEILING_FLIP_LONG n=3 +21$ · DOUBLE_TOP_AA_SHORT n=3 +8$ · REACTIVE_LONG n=1 -19$ · VEGAS n=1 -34$ · OPENING_DRIVE n=1 -36$ · GHOST n=1 -39$ · GB100 n=3 -46$ · INITIATIVE_SHORT n=1 -56$ · OPENING_EXTREME_REJECT n=1 -61$ · CEILING_FLIP_SHORT n=2 -72$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `S1-opening-lock` — S1 נעל סוג-פתיחה שונה מקריאת-הברים — שורש T-594 (נעילה בלי רפרנסים-קודמים) / T-595 (מכונה על בר שטוח); המדידה: hist_o / hist_p / hist_po. *ראיה:* 2026-10-05: מערכת OPEN_AUCTION_IN (17:30 at IB lock) · ברים OPEN_DRIVE (אין חזרה לפתיחה בברים 2–6 (↑); 30 דק׳ נטו +8.75, בתוך-ערך)
2. `pattern-GB100` — התבנית GB100 מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-05: n=3 · wins 1 · Σ -46.25$ (מחיר-ברוקר)
3. `keep-CEILING_FLIP_LONG` — התבנית CEILING_FLIP_LONG מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-05: n=3 · wins 2 · Σ +21.25$
4. `keep-DOUBLE_TOP_AA_SHORT` — התבנית DOUBLE_TOP_AA_SHORT מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-05: n=3 · wins 1 · Σ +7.50$

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-02 (Fri) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 4 עסקאות · Σ **-67.50$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ +57.50$ (26) · מאז 07.07 Σ -715.00$ (181)

| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |
|---|---|---|---|---|---|---|---|---|
| 16:50 | S2 | DALTON_EDGE_SHORT | SHORT | ? | 1 | T1_FILL | +46.25 | ✓ |
| 16:55 | S4 | GB100 | SHORT | ? | 1 | STOP_HIT | -45.00 | ✓ |
| 17:35 | S2 | CEILING_FLIP_SHORT | SHORT | Normal | 1 | STOP_HIT | -45.00 | ✓ |
| 18:45 | S2 | DOUBLE_TOP_AA_SHORT | SHORT | Variation | 1 | SIERRA_FLAT | -23.75 | ✓ |

**פתיחה:** מערכת **OPEN_REJECTION_REVERSE** (נעילה 16:55 at bar 6, dir DOWN, 1 ביטולים) · ברים **OPEN_REJECTION_REVERSE** — דרייב ואז חזרה דרך הפתיחה; פתיחה 7789.5 מחוץ-לטווח מעל (אתמול H/L 7741.25/7672.75, VAH/VAL/POC 7725.25/7684.0/7694.0); 30 דק׳ H/L 7805.0/7773.5, נטו -1.25 · ✓ תואם
**סוג-יום:** מערכת 17:30 Variation · 18:30 Variation · 21:00 Variation · אחרון Variation · EOD Variation · 4 ריצודים (118 וקטורים) · ברים **Normal_Variation** (IB 7808.75/7773.5 · טווח 7754.0–7810.5 · rib 1.6 · סגירה 7779.0 pos 0.44 · הרחבה ↑לא ↓כן) · סגירה−פתיחה -10.50
**החלטות:** 118 (עברו את העץ 36) · חסימות: tree:bias 43 · tree:stand_down 27 · tree:location 7 · tree:kind 5
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=1 +128$ · DOUBLE_BOTTOM_EE_LONG n=1 +72$ · DALTON_EDGE_SHORT n=1 +46$ · INITIATIVE_LONG n=1 +29$ · CEILING_FLIP_LONG n=3 +21$ · REACTIVE_LONG n=4 +10$ · DOUBLE_TOP_AA_SHORT n=3 +8$ · BULL_FLAG_LONG n=1 +6$ · OPENING_DRIVE n=2 -18$ · GB100 n=2 -19$ · GHOST n=2 -30$ · VEGAS n=1 -34$ · CEILING_FLIP_SHORT n=2 -45$ · INITIATIVE_SHORT n=1 -56$ · OPENING_EXTREME_REJECT n=1 -61$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `keep-CEILING_FLIP_LONG` — התבנית CEILING_FLIP_LONG מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-02: n=3 · wins 2 · Σ +21.25$
2. `keep-REACTIVE_LONG` — התבנית REACTIVE_LONG מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-02: n=4 · wins 3 · Σ +10.00$

**שיקול-דעת (הסוכן/מייקל):** _—_


## 2026-10-01 (Thu) — נכתב 2026-10-19 18:41 IL

**לייב היום:** 3 עסקאות · Σ **+141.25$** (מחיר-ברוקר) · 10 סשנים אחרונים Σ +132.50$ (23) · מאז 07.07 Σ -647.50$ (177)

| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |
|---|---|---|---|---|---|---|---|---|
| 16:45 | S2 | OPENING_TEST_DRIVE | SHORT | ? | 1 | T1_HIT | +127.50 | ✓ |
| 21:00 | S2 | DOUBLE_TOP_AA_SHORT | SHORT | Variation | 1 | T1_HIT | +70.00 | ✓ |
| 21:10 | S2 | INITIATIVE_SHORT | SHORT | Variation | 1 | STOP_HIT | -56.25 | ✓ |

**פתיחה:** מערכת **OPEN_REJECTION_REVERSE** (אין שורת-נעילה בלוג; לפי וקטורים) · ברים **OPEN_REJECTION_REVERSE** — דרייב ואז חזרה דרך הפתיחה; פתיחה 7730.0 בתוך-טווח (אתמול H/L 7782.25/7710.0, VAH/VAL/POC 7778.5/7752.0/7767.25); 30 דק׳ H/L 7740.25/7709.75, נטו -18.75 · ✓ תואם
**סוג-יום:** מערכת 17:30 Normal · 18:30 Variation · 21:00 Variation · אחרון Variation · EOD Variation · 2 ריצודים (99 וקטורים) · ברים **Normal_Variation** (IB 7740.25/7682.25 · טווח 7672.75–7741.25 · rib 1.18 · סגירה 7726.0 pos 0.78 · הרחבה ↑לא ↓כן) · סגירה−פתיחה -4.00
**החלטות:** 99 (עברו את העץ 37) · חסימות: tree:bias 27 · tree:stand_down 17 · tree:location 16 · tree:kind 2
**בריאות:** backend pid 2030 · feed 2 דק׳ · סוכנים 11 · AC 100% · gap_backfill: no run logged

**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** OPENING_TEST_DRIVE n=1 +128$ · DOUBLE_BOTTOM_EE_LONG n=1 +72$ · DOUBLE_TOP_AA_SHORT n=2 +31$ · INITIATIVE_LONG n=1 +29$ · GB100 n=1 +26$ · CEILING_FLIP_LONG n=3 +21$ · REACTIVE_LONG n=4 +10$ · BULL_FLAG_LONG n=1 +6$ · CEILING_FLIP_SHORT n=1 +0$ · OPENING_DRIVE n=3 -10$ · GHOST n=2 -30$ · VEGAS n=1 -34$ · INITIATIVE_SHORT n=1 -56$ · OPENING_EXTREME_REJECT n=1 -61$

**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**
1. `pattern-OPENING_DRIVE` — התבנית OPENING_DRIVE מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים). *ראיה:* עד 2026-10-01: n=3 · wins 2 · Σ -10.00$ (מחיר-ברוקר)
2. `keep-CEILING_FLIP_LONG` — התבנית CEILING_FLIP_LONG מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-01: n=3 · wins 2 · Σ +21.25$
3. `keep-REACTIVE_LONG` — התבנית REACTIVE_LONG מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה. *ראיה:* עד 2026-10-01: n=4 · wins 3 · Σ +10.00$

**שיקול-דעת (הסוכן/מייקל):** _—_


