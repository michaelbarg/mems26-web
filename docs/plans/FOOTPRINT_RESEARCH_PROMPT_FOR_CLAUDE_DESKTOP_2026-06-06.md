# פרומפט-מחקר לקלוד דסקטופ — footprint ככלל-כניסה-ויציאה לכל תבניות S2+S4

**איך להשתמש:** העתק את כל מה שמתחת לקו `═══ PROMPT START ═══` והדבק לקלוד דסקטופ (עם deep-research/web). המטרה: למלא את הטבלה — לכל תבנית×סוג-יום, איזה footprint קובע נקודת **כניסה** ו**יציאה** איכותית.

**מקור-אמת לרשימות (מהקוד שלנו, 2026-06-06):**
- **S2 (5-min, 10):** REACTIVE_LONG/SHORT · INITIATIVE_LONG/SHORT · INVERSE_HNS_LONG · HNS_TOP_SHORT · DOUBLE_BOTTOM_EE_LONG · DOUBLE_TOP_AA_SHORT · BULL_FLAG_LONG · BEAR_FLAG_SHORT
- **S4 (Woodies CCI, 9):** ZLR (cont) · TLB (cont) · TT=Turbo-Trend (cont) · GB100=Ghost-Bar-100 (cont) · HFE=Hook-From-Extreme (NEW_TREND) · HTLB=Hook-Turn-at-Line-Break (rev) · FAMIR (rev) · GHOST=CCI-divergence (rev) · VEGAS (rev)
- **סוגי-יום (7):** Trend_Normal · Trend_DD · Variation · Normal · Neutral_Extreme · Neutral_Center · Nontrend(NO-TRADE)
- **גלאי-S3 קיימים:** ABSORPTION · STACKED_IMBALANCE · SWEEP_RETURN · EXHAUSTION (+ delta/CVD)

═══════════════════════════ PROMPT START ═══════════════════════════

# משימה: מחקר עמוק — footprint/order-flow ככלל-כניסה-ויציאה איכותי לתבניות מסחר עתידיים (MES/ES, 5-דק')

אתה חוקר order-flow מומחה. אני מפעיל מערכת מסחר אוטונומית על MES/ES בגרף 5-דקות עם שתי משפחות-תבניות (price-action "S2" ו-Woodies-CCI "S4") ושכבת-footprint נפרדת ("S3") שיש לה 4 גלאים: **ABSORPTION, STACKED_IMBALANCE, SWEEP_RETURN, EXHAUSTION**, בתוספת **bid/ask delta + CVD**.

**מטרת-העל:** להגדיר, לכל תבנית ולכל סוג-יום, **כלל-footprint שקובע (א) נקודת-כניסה איכותית ו-(ב) נקודת-יציאה/יעד איכותית** — ולמלא את הטבלה למטה. footprint כאן הוא שכבת-**אישור/וֵטו** מעל איתות קיים, לא מחולל-איתות.

## הקשר שאתה חייב להשתמש בו

**7 אותות-ה-footprint (אוצר-מילים אחיד — השתמש רק בהם):**
delta/CVD-divergence · absorption · stacked-imbalances (3:1, ≥3 רמות) · exhaustion · sweep+reclaim · POC/Value-Area · HVN/LVN.

**העיקרון-המנחה (אמת אותו, אל תניח):** תבניות-**המשך** רוצות footprint-של-המשך (stacked-imbalance, CVD-בכיוון, קבלת-ערך מעל VAH/מתחת VAL); תבניות-**היפוך** רוצות footprint-של-תשישות (absorption, delta-divergence, exhaustion, sweep+reclaim).

**מודולציה לפי סוג-יום (אמת/דייק):** Trend_Normal/Trend_DD = ימי-מגמה (תעדף continuation, footprint שמאשר המשך, יעדים רחבים/trail). Variation = מעורב (2 חוזים, T3 trail). Normal = יום-טווח (יעד ב-POC, T2 ב-POC). Neutral_Extreme/Center = דחיית-קצוות-VA (תעדף reversal/fade בקצה ה-Value-Area). Nontrend = NO-TRADE.

## מה למלא בכל תא (זו הליבה)

לכל **תבנית** (19 שורות), ולכל סוג-יום שבו היא רלוונטית, מלא:
1. **כניסה-איכותית (footprint ENTRY-gate):** איזה אות-footprint *חייב* להופיע כדי שהכניסה תיחשב איכותית (ולא fakeout). היה ספציפי: היכן ביחס לתבנית (למשל "absorption בשפל-השני", "≥3 stacked-imbalances על נר-הפריצה", "delta-flip בקצה").
2. **יציאה/יעד-איכותי (footprint EXIT-rule):** איזה אות-footprint אומר "ממש כאן צא / קח רווח" — זה החלק החדש והחשוב. למשל: absorption-נגדי ב-T1/T2 (קונים נבלעים → צא), exhaustion בקצה, delta-divergence מול היעד, הגעה ל-POC/HVN-נגדי (מחיר ייעצר), היעלמות-imbalance-בכיוון (המומנטום מת → scale-out). הבחן בין **scale-out חלקי** (C1/C2) ל-**יציאה-מלאה/trail**.
3. **עוגן-סטופ (footprint):** מעבר לאיזה אירוע-order-flow (absorption-edge / sweep-wick / imbalance-cluster / LVN).
4. **וֵטו/דלג (skip):** איזה אות-footprint *פוסל* את האיתות (למשל delta-divergence על continuation = דלג; נזילות-נטענת-נגד-התנועה ב-breakout = מלכודת).
5. **מודולציית-יום:** איך הכלל משתנה בין ימי-מגמה לימי-טווח/ניטרלי.

## הטבלה למילוי

| # | מערכת | תבנית | קבוצה | כיוון | סוגי-יום רלוונטיים | כניסה-איכותית (footprint ENTRY) | יציאה/יעד (footprint EXIT) | עוגן-סטופ | וֵטו/דלג | מודולציית-יום |
|---|-------|-------|-------|-------|-------------------|-------------------------------|---------------------------|----------|---------|--------------|
| 1 | S2 | REACTIVE_LONG | continuation | LONG | | | | | | |
| 2 | S2 | REACTIVE_SHORT | continuation | SHORT | | | | | | |
| 3 | S2 | INITIATIVE_LONG | continuation/breakout | LONG | | | | | | |
| 4 | S2 | INITIATIVE_SHORT | continuation/breakout | SHORT | | | | | | |
| 5 | S2 | INVERSE_HNS_LONG | reversal | LONG | | | | | | |
| 6 | S2 | HNS_TOP_SHORT | reversal | SHORT | | | | | | |
| 7 | S2 | DOUBLE_BOTTOM_EE_LONG | reversal | LONG | | | | | | |
| 8 | S2 | DOUBLE_TOP_AA_SHORT | reversal | SHORT | | | | | | |
| 9 | S2 | BULL_FLAG_LONG | continuation | LONG | | | | | | |
| 10 | S2 | BEAR_FLAG_SHORT | continuation | SHORT | | | | | | |
| 11 | S4 | ZLR (Zero Line Reject) | continuation | both | | | | | | |
| 12 | S4 | TLB (Trend Line Break) | continuation | both | | | | | | |
| 13 | S4 | TT (Turbo Trend) | continuation | both | | | | | | |
| 14 | S4 | GB100 (Ghost Bar 100) | continuation | both | | | | | | |
| 15 | S4 | HFE (Hook From Extreme) | new-trend/fade | both | | | | | | |
| 16 | S4 | HTLB (Hook Turn at Line Break) | reversal | both | | | | | | |
| 17 | S4 | FAMIR (Failed Attempt @ Resistance) | reversal | both | | | | | | |
| 18 | S4 | GHOST (CCI divergence) | reversal | both | | | | | | |
| 19 | S4 | VEGAS | reversal | both | | | | | | |

## כללי-מחקר מחייבים (איכות > כמות)

1. **רב-מקורי + ציטוט:** כל טענה עובדתית עם מקור `[כותרת](URL)`. העדף מקורות-order-flow מבוססים (ATAS, Bookmap, Sierra, Trader-Dale, NinjaTrader, GoCharting) ומיקרו-מבנה אקדמי.
2. **הפרד עובדה מ-INFERENCE:** לתבניות price-action (S2) יש ספרות footprint ישירה — צטט. ל-**Woodies (S4) אין בספרות שילוב עם footprint** — סמן כל מיפוי כ-**INFERENCE** הנגזר מאופי-האיתות (המשך/היפוך), לא כעובדה.
3. **כניסה *וגם* יציאה:** רוב ספרות-ה-footprint מתמקדת בכניסה. השקע מאמץ מיוחד בכלל-ה**יציאה** (footprint שאומר "קח רווח / המהלך מת"), כולל scale-out פר-חוזה (C1/C2/C3) ו-trail. זה הליבה של מה שאני צריך.
4. **יושר-ראיות (חובה, סעיף נפרד בסוף):** מה הראיה האקדמית באמת תומכת (order-flow-imbalance מנבא טווח-קצר — Cont/Kukanov/Stoikov), מה *לא* (אין הוכחה ששיטת-footprint קמעונאית מעלה win-rate; VPIN נכשל ברפליקציה), והמגבלות (footprint=נפח-מבוצע לא נזילות-רוחפת; spoofing/icebergs; סיווג Lee-Ready משוער; עובד רק בשוק-נזיל/טווח-קצר). אל תמכור edge מובטח.
5. **ספציפי-ל-MES/ES 5-דק':** סף-imbalance 3:1, value-area 70%, נתוני-CME centralized (delta/CVD אמין כאן). הכל ל-5-דק' (Woodies הכי-חזק ב-5-דק').

## פורמט-פלט נדרש

1. **הטבלה המלאה** (19 שורות מלאות).
2. **פירוט פר-תבנית** (פסקה קצרה לכל אחת: מנגנון-הכניסה, מנגנון-היציאה, מקור/INFERENCE).
3. **מטריצת סוג-יום × תבנית:** אילו תבניות לתעדף בכל סוג-יום ולמה (Trend vs Range vs Neutral).
4. **3 מסקנות-סינתזה:** (א) איזה אות-footprint יחיד הכי-רחב לכניסה; (ב) איזה הכי-רחב ליציאה; (ג) סעיף-יושר-הראיות.
5. **מקורות** מלאים.

═══════════════════════════ PROMPT END ═══════════════════════════

## הערות-יישום (אחרי שהמחקר חוזר)

- המיפוי נופל ישירות על 4 גלאי-S3 הקיימים → עמודת "footprint-confirm נדרש" + "footprint-exit" פר-תבנית×סוג-יום ב-`MEMS26_STOP_TARGET_PLACEMENT_TABLE` (YAML-tunable, ניתן-לכבות). ([[project-stop-target-placement-table]] · [[project-config-tunable-stop-exits-contracts]])
- עוגני-יציאה מ-footprint (absorption-נגדי/exhaustion ב-T1/T2) = ממד חדש ל-exit-management מעבר ל-R-קבוע.
- **חוסם-קדימוּת:** הכל תאורטי עד ש-I-11/I-21 (S3 מת, 0 ברים) נסגר — בלי הזנת-footprint חיה אין מה לאשר.
- **שער-LIVE:** footprint-gate בנתיב-הירי = שינוי trading-logic → flag-gated + soak + אישור Michael.
