# Footprint/Order-Flow כשכבת אישור/וטו לכניסה ויציאה — MES/ES, 5 דקות

> **מקור:** מחקר Claude-Desktop (deep-research) על-בסיס הפרומפט `FOOTPRINT_RESEARCH_PROMPT_FOR_CLAUDE_DESKTOP_2026-06-06.md`. **תאריך:** 2026-06-06.
> **הצלבת-Cowork (verifier):** הוצלב מול מחקר עצמאי קודם (`FOOTPRINT_CONFIRMATION_RESEARCH_2026-06-06.md`) — **עקבי** בכל הטענות-הליבה: imbalance 3:1/≥3-רמות, value-area 70%, stacked-imbalance→continuation, absorption→reversal, ו-evidence-honesty (OFI לטווח-קצר אמיתי; VPIN נכשל בשחזור; אין edge קמעונאי מוכח). ⚠️ כל שורות S4 (11-19) הן **INFERENCE** לא-מאומת. ⚠️ עמודת ה-EXIT היא החלק הכי-פחות-מתועד בספרות (היציאה נגזרת-עיקרון, לא מצוטטת-ישירות). ⚠️ HTLB בקוד שלנו = "Hook Turn at Line Break" (REVERSAL) — תואם את הסיווג בטבלה.

## TL;DR
- **Footprint הוא שכבת CONFIRMATION/VETO מעל סיגנל קיים — לא מחולל סיגנל.** continuation-patterns דורשים continuation-footprint (stacked-imbalance, CVD-in-direction, value-acceptance מעל VAH/מתחת VAL); reversal-patterns דורשים exhaustion-footprint (absorption, delta-divergence, exhaustion, sweep+reclaim).
- **חוק היציאה:** counter-footprint — absorption נגדי ב-T1/T2, exhaustion בקצה, delta/CVD-divergence נגד היעד, והיעלמות ה-imbalance-in-direction (momentum מת → scale-out). הגעה ל-counter-POC/HVN = מקום לקחת רווח.
- **הראיות תומכות רק ש-OFI מנבא תנועה לטווח קצר מאוד** (Cont/Kukanov/Stoikov). אין ראיה peer-reviewed ש-footprint קמעונאי משפר win-rate; VPIN נכשל בשחזור. **אין למכור edge מובטח.**

## הטבלה המלאה (19 שורות)
| # | Pattern (סוג) | Quality ENTRY (footprint-gate) | Quality EXIT/target (footprint exit-rule) | Stop-anchor (footprint) | Veto/Skip | Day-modulation |
|---|---|---|---|---|---|---|
| 1 | REACTIVE_LONG (continuation, LONG) | stacked buy-imbalance ב-bar הריבאונד מהתמיכה + CVD עולה; delta-flip לחיובי בקצה התמיכה | C1: counter sell-absorption ב-VAH/HVN הבא → scale-out; C2: היעלמות buy-imbalance = momentum מת; C3: exhaustion/divergence בקצה → trail | מתחת ל-absorption-edge/imbalance-cluster של ה-low; או מתחת ל-LVN | delta-divergence על הריבאונד; sell-loading נגד = trap → skip | Trend: target רחב, trail על HVN; Range/Normal: target ב-POC |
| 2 | REACTIVE_SHORT (continuation, SHORT) | stacked sell-imbalance ב-bar הדחייה + CVD יורד; delta-flip שלילי בקצה | C1: counter buy-absorption ב-VAL/HVN → scale; C2: היעלמות sell-imbalance; C3: exhaustion/divergence בתחתית | מעל absorption-edge/imbalance-cluster של ה-high; מעל LVN | delta-divergence על הדחייה; buy-loading נגד = trap | Trend: trail רחב; Range: target ב-POC |
| 3 | INITIATIVE_LONG (breakout, LONG) | ≥3 stacked-imbalances ב-bar הפריצה מעל range/VAH + CVD מתרחב; acceptance מעל VAH | C1: arrival ל-counter-HVN/POC → scale; C2: disappearance של breakout-imbalance; C3: divergence על ה-extension → trail מאחורי volume-clusters | מתחת לקצה ה-imbalance-cluster; חזרה ל-range = כישלון | פריצה ללא delta = fakeout; counter-loading מעל = trap | Trend_DD: רחב מאוד, trail; Neutral/Normal: סקפטי, target קצר ב-HVN |
| 4 | INITIATIVE_SHORT (breakout, SHORT) | ≥3 stacked sell-imbalances מתחת range/VAL + CVD שלילי מתרחב; acceptance מתחת VAL | C1: arrival ל-counter-HVN/POC → scale; C2: disappearance של sell-imbalance; C3: divergence → trail | מעל קצה ה-imbalance-cluster; חזרה ל-range = כישלון | פריצה ללא delta שלילי = fake; buy-loading מתחת = trap | Trend_DD: trail רחב; Neutral: fade בקצה VA |
| 5 | INVERSE_HNS_LONG (reversal, LONG) | absorption ב-head וב-right-shoulder + delta-divergence (low נמוך, CVD גבוה); sweep+reclaim של ה-low | C1: counter-absorption ב-neckline/POC → scale; C2: exhaustion ביעד; C3: divergence נגד התנועה → trail | מתחת ל-sweep-wick של ה-head/shoulder | אין absorption ב-shoulder; CVD low חדש = אין divergence → skip | Neutral_Extreme/Center: אידיאלי; Trend-down חזק: skip |
| 6 | HNS_TOP_SHORT (reversal, SHORT) | absorption ב-head וב-right-shoulder + delta-divergence (high גבוה, CVD נמוך); sweep+reclaim של ה-high | C1: counter buy-absorption ב-neckline/POC → scale; C2: exhaustion ביעד; C3: divergence → trail | מעל ה-sweep-wick של ה-head/shoulder | אין absorption ב-shoulder; CVD high חדש = skip | Neutral edge: אידיאלי; Trend-up חזק: skip |
| 7 | DOUBLE_BOTTOM_EE_LONG (reversal, LONG) | absorption ב-low השני (heavy bid+ask, מחיר לא יורד) + delta-divergence מול ה-low הראשון; sweep+reclaim אופציונלי | C1: counter-absorption ב-neckline → scale; C2: arrival ל-POC/HVN; C3: exhaustion/divergence → trail | מתחת ל-low השני (absorption-edge/sweep-wick) | low שני עם sell-imbalance ממשיך ללא absorption → skip | Neutral/Normal: מצוין; Trend_DD-up: confluence |
| 8 | DOUBLE_TOP_AA_SHORT (reversal, SHORT) | absorption ב-high השני + delta-divergence מול ה-high הראשון; sweep+reclaim | C1: counter buy-absorption ב-neckline → scale; C2: arrival ל-POC/HVN; C3: exhaustion → trail | מעל ה-high השני | high שני עם buy-imbalance חזק ללא absorption → skip | Neutral edge: מצוין; Trend-up: skip |
| 9 | BULL_FLAG_LONG (continuation, LONG) | ב-flag: ירידת volume + delta נייטרלי/חיובי; ב-breakout: stacked buy-imbalance + CVD-surge | C1: arrival ל-HVN/POC → scale; C2: disappearance של buy-imbalance; C3: divergence על ה-leg → trail מאחורי volume-clusters | מתחת ל-flag-low / imbalance-cluster של הפריצה | ב-flag delta שלילי כבד → skip; פריצה ללא delta = fake | Trend: יעד=pole-projection + trail; Range: target צנוע ב-HVN |
| 10 | BEAR_FLAG_SHORT (continuation, SHORT) | ב-flag: ירידת volume + delta נייטרלי/שלילי; ב-breakdown: stacked sell-imbalance + CVD שלילי | C1: arrival ל-HVN/POC → scale; C2: disappearance של sell-imbalance; C3: divergence → trail | מעל ה-flag-high / imbalance-cluster | ב-flag buy-delta כבד; breakdown ללא delta = fake | Trend-down: pole-projection + trail; Range: target צנוע |
| 11 | ZLR — Zero Line Reject (continuation) [INFERENCE] | stacked-imbalance בכיוון המגמה ב-bar שדוחה את ה-ZL + CVD-in-direction | C1: disappearance של imbalance → scale; C2: arrival ל-HVN/POC; C3: divergence → trail | מעבר ל-imbalance-cluster/LVN נגד-המגמה | delta-divergence בכיוון = skip; loading נגד | Trend: setup מועדף, trail רחב; Range/Neutral: סקפטי, target ב-POC |
| 12 | TLB — Trend Line Break (continuation) [INFERENCE] | stacked-imbalance בכיוון הפריצה + CVD מתרחב ברגע שבירת קו ה-CCI | C1: arrival ל-HVN/POC → scale; C2: disappearance של imbalance; C3: divergence → trail | מאחורי imbalance-cluster/LVN | פריצה ללא delta = fake → skip | Trend: רחב; Range: קצר |
| 13 | TT — Turbo Trend (continuation) [INFERENCE] | impulse חזק: stacked-imbalance צפוף + CVD-surge חד בכיוון | C1: disappearance של imbalance (מהיר) → scale מהר; C2: exhaustion-spike; C3: divergence → trail צמוד | מאחורי imbalance-cluster הקרוב | אין CVD-surge = אין turbo → skip | Trend: אידיאלי; Range: skip |
| 14 | GB100 — Ghost Bar 100 (continuation) [INFERENCE] | אחרי חציית 100 וחזרה: stacked-imbalance בכיוון המגמה המקורית ב-bar חציית ה-ZL + CVD | C1: arrival ל-HVN/POC → scale; C2: disappearance של imbalance; C3: divergence → trail | מאחורי imbalance-cluster/LVN | delta-divergence בכיוון → skip | Trend: כן; Range: skip |
| 15 | HFE — Hook From Extreme (fade) [INFERENCE] | exhaustion-spike + delta-divergence בקצה; sweep+reclaim של ה-extreme | C1: scale מהיר (one-clip scalp) ב-counter-POC הקרוב; C2: exhaustion נגדי; C3: divergence — יציאה מהירה, אל תחזיק | מעבר ל-sweep-wick של ה-extreme | רק ספייק ללא exhaustion/divergence = trap → skip | Neutral_Extreme: fade בקצה; Trend חזק: skip |
| 16 | HTLB — Hook Turn at Line Break (reversal) [INFERENCE] | absorption בקצה + delta-divergence ב-bar שבירת ה-TL הנגדי; sweep+reclaim | C1: counter-absorption ב-POC → scale; C2: exhaustion ביעד; C3: divergence → trail | מעבר ל-sweep-wick/absorption-edge | אין absorption/divergence → skip | Neutral edge: מצוין; Trend: זהירות |
| 17 | FAMIR — Failed Attempt (reversal) [INFERENCE] | sweep+reclaim של רמה + absorption בנקודת-הכישלון + delta-divergence | C1: counter-absorption ב-POC/HVN → scale; C2: exhaustion; C3: divergence → trail | מעבר ל-sweep-wick של הניסיון הכושל | reclaim ללא absorption/delta-flip → skip | Neutral/Normal: מצוין; Trend: skip |
| 18 | GHOST — CCI divergence (reversal) [INFERENCE] | delta/CVD-divergence שמאשר את ה-CCI-divergence + absorption בקצה | C1: counter-absorption ב-POC → scale; C2: exhaustion; C3: divergence-מתהפך → trail | מעבר ל-extreme/absorption-edge | CVD מאשר את המחיר (אין divergence) → skip | Neutral edge: מצוין; Trend: skip |
| 19 | VEGAS (reversal) [INFERENCE] | HFE + rounding → exhaustion ממושך + delta-divergence; absorption ברמת ה-rounding | C1: counter-absorption ב-POC/HVN → scale; C2: exhaustion; C3: divergence → trail | מעבר ל-extreme של ה-rounding/sweep-wick | אין exhaustion/absorption ב-rounding → skip | Neutral_Extreme: אידיאלי; Trend: skip |

## מטריצת Day-type × Pattern
| Day-type | תעדף | למה |
|---|---|---|
| Trend_Normal / Trend_DD | INITIATIVE, REACTIVE, BULL/BEAR_FLAG, ZLR, TLB, TT, GB100 | continuation-footprint עובד; target רחב, trail על HVN; Trend_DD=double-distribution → trail אגרסיבי |
| Variation | continuation מתון, 2 חוזים, T3 trail | מעורב; range-extension לצד אחד; trail על ה-leg השני |
| Normal (range) | REACTIVE, DOUBLE_TOP/BOTTOM | target ב-POC, T2 ב-POC; mean-reversion סביב ה-POC |
| Neutral_Extreme / Center | INVERSE_HNS, HNS_TOP, DOUBLE_*, HFE, HTLB, FAMIR, GHOST, VEGAS | דחיית קצה ה-Value-Area; fade ב-VAH/VAL עם exhaustion-footprint |
| Nontrend | — | NO-TRADE (IB צר, אין OTF, נפח נמוך, פרופיל D) |

## שלוש מסקנות-סינתזה
**(א) כניסה:** continuation → stacked-imbalance(3:1, ≥3) + CVD-in-direction; reversal → absorption-בקצה + delta-divergence. שני gates מכסים את רוב 19 הפטרנים.
**(ב) יציאה:** היעלמות ה-imbalance-in-direction + delta/CVD-divergence, ו-arrival ל-counter-POC/HVN. הכלל היחיד שחל גם על continuation (momentum מת) וגם על reversal (exhaustion ביעד) — ה-fill החסר בספרות.
**(ג) Evidence-honesty:** OFI מנבא טווח-קצר-מאוד (Cont-Kukanov-Stoikov 2014) — price-impact קונטמפורני, לא alpha נסחר. אין ראיה peer-reviewed ש-footprint קמעונאי מעלה win-rate (Chague 97% הפסידו; Barber <1% עקביים). VPIN נכשל בשחזור (Andersen-Bondarenko). Lee-Ready סיווג ~73-85% (יורד בשוק מהיר). זיהוי-פטרן ≠ רווחיות אחרי-עלויות (Lo-Mamaysky-Wang).

## Recommendations (יישום הדרגתי)
1. **שני gates קשיחים:** continuation=stacked-imbalance(3:1,≥3)+CVD-in-direction; reversal=absorption-בקצה+delta-divergence. דלג בלי ה-gate. סף: אם >~40% עסקאות-וטו → רכך ל-2.5:1 / 3 רמות.
2. **חוק-יציאה פר-חוזה:** C1 ב-counter-absorption/HVN; C2 כש-imbalance-in-direction נעלם; C3 trail אחרי divergence. מודולציה לפי סוג-יום.
3. **וֵטו קשיח:** divergence-בכיוון על continuation; loading-נגד breakout; reclaim-ללא-absorption ב-reversal → skip.
4. **S4 (11-19) הם INFERENCE — shadow/paper-test לפני הקצאת-הון.**

## שערים ליישום (Cowork)
- **חוסם:** I-11/I-21 (S3 מת, 0 ברים) — בלי הזנת-footprint חיה אין מה לאשר.
- **שער-LIVE:** footprint-gate בנתיב-הירי = שינוי trading-logic → flag-gated + soak + אישור Michael.
- **נתיב-יישום:** עמודות `footprint_entry_gate` + `footprint_exit_rule` + `footprint_veto` פר-תבנית×סוג-יום ב-`MEMS26_STOP_TARGET_PLACEMENT_TABLE` (YAML-tunable). ([[project-stop-target-placement-table]] · [[project-config-tunable-stop-exits-contracts]])

## מקורות
Cont-Kukanov-Stoikov (2014, JFEC 12(1):47-88) · Andersen-Bondarenko (2014, JFM 17:1-46) · Easley-López de Prado-O'Hara (2014, JFM 17:47-52) · Lo-Mamaysky-Wang (2000, J.Finance 55(4)) · Chague-De-Losso-Giovannetti (2020, SSRN 3423101) · Barber-Lee-Liu-Odean (2014, JFM 18:1-24) · Odders-White(2000)/Theissen(2001)/Chakrabarty — Lee-Ready accuracy · NinjaTrader · Trader Dale · ATAS · TradeThePool · Triad City Beat · LiteFinance · Bookmap/CoinGlass · TradingSim · Axia Futures · Woodies CCI docs (wealthv/scribd) · Market Profile day-types (Dalton).
