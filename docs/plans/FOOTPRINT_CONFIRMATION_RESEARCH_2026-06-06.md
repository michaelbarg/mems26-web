# מחקר: S3 (Footprint) כשכבת-אישור-וירי ל-S2 (5-min) ו-S4 (Woodies CCI)

**תאריך:** 2026-06-06 · **סוג:** מחקר תאורטי-חיצוני (לא ניתוח הקוד שלנו) · **מקור:** 5 סוכני-מחקר, מקורות מתועדים בתחתית.
**שאלת-המחקר (Michael):** איזה סוג footprint מאשר כל תבנית, והאם זה משפר את **דיוק/ודאות הכניסה** ואת **תזמון/מיקום הסטופים**.

> **TL;DR.** כן — footprint יכול לשמש שכבת-**אישור/וֵטו** (לא מחולל-איתות) שמשפרת דיוק-כניסה ומחדדת סטופים, **בתנאי** שמכבדים את ההבחנה היחידה החשובה: **תבניות-המשך (continuation) רוצות footprint של המשך** (stacked imbalances, CVD-בכיוון, קבלת-ערך), ו**תבניות-היפוך (reversal) רוצות footprint של תשישות** (absorption, delta-divergence, exhaustion, sweep+reclaim). הבשורה החשובה-פחות: **אין ראיה אקדמית שזה משפר win-rate קמעונאי** — היתרון המוכח חי ב-HFT, לא בקריאה ויזואלית. לכן זו שכבת-veto לכיול-עצמי-מול-soak, לא קסם.

> **חיבור למערכת שלנו:** ל-S3 כבר יש בדיוק 4 הגלאים הרלוונטיים — **ABSORPTION · STACKED_IMBALANCE · SWEEP_RETURN · EXHAUSTION** — בתוספת CVD. כל המיפוי למטה נופל ישירות על 4 אלה. ⚠️ **חוסם:** S3 כרגע מת (0 ברים, I-11/I-21) — אי-אפשר לאסוף דאטת-אישור-אמת עד שההזנה תתוקן.

---

## 1 · טקסונומיה — 7 אותות footprint (מאומת)

| אות | מה הוא | מאשר | סף-אצבע |
|-----|--------|------|---------|
| **Delta / CVD divergence** | מחיר עושה שיא/שפל חדש, ה-delta/CVD לא מאשר | **היפוך** (תשישות-מומנטום) | מבני, אין מספר; *context*, לא טריגר-יחיד |
| **Absorption** | נפח-ענק על שני הצדדים בלי תזוזת-מחיר; limit פסיבי בולע aggression | **היפוך** ברמת S/R | "effort≠result" איכותי |
| **Stacked imbalances** | ≥3 רמות-מחיר רצופות עם imbalance אלכסוני באותו כיוון | **המשך** + הופך ל-S/R בריטסט | יחס **3:1 (300%)**, **≥3 רמות** (תקן NinjaTrader/Sierra) |
| **Exhaustion** | נפח/aggression מתייבש בקצה — נגמר הדלק | **היפוך / סוף-מגמה** | יורד-נפח לקצה, ספייק-delta בלי המשך |
| **Sweep + reclaim** | מחיר חוצה swing (מפעיל סטופים) ואז חוזר דרכו | **היפוך — רק אם ה-reclaim מחזיק** | reclaim תוך 1-כמה נרות + ספייק-נפח על הדקירה |
| **POC / Value-Area** | רמת-הנפח-הגבוהה / טווח-70% | המשך-מול-היפוך לפי קבלה/דחייה בקצה-VA | 70% value-area (תקן) |
| **HVN / LVN** | צמתי נפח גבוה (קבלה, S/R) / נמוך (דחייה, מעבר-מהיר) | HVN=עצירה/S-R · LVN=מעבר-מהיר | צורני (peak/valley) |

**כלל-על שחוזר בכל המקורות:** אף אחד מאלה אינו טריגר-עצמאי — תמיד **שכבת-confluence על-גבי מבנה ומיקום** (S/R, Volume Profile).

---

## 2 · ⭐ הטבלה המרכזית — תבניות 5-דק' (S2) × footprint

| תבנית (S2) | סוג | Footprint לאישור (ראשי → משני) | מנגנון — למה זה מאשר | תועלת-כניסה | עוגן-סטופ |
|------------|-----|-------------------------------|---------------------|-----------|----------|
| **DOUBLE_BOTTOM (Eve)** | היפוך | **ABSORPTION** בשפל-השני → +delta divergence | קרקעית תקפה היא אירוע-בליעה (limit-buyers), לא מומנטום | כניסה *בשפל* על הדפסת-הבליעה, לא בשבירת-צוואר → R:R כפול | **מתחת לאזור-הבליעה** (איפה ש-imbalance שורי נוצר) |
| **DOUBLE_TOP (Adam)** | היפוך | **ABSORPTION/EXHAUSTION** בשיא-השני → −delta divergence | קונים נבלעים/מותשים; שיא חד = הדפסת-exhaustion קלימקטית שמיד נכשלת | מסנן fakeout בשיא | **מעל אזור-הבליעה** / מעל תחילת ה−delta החזק |
| **INV_HNS (בסיס)** | היפוך | **+CVD divergence** לאורך המבנה → ABSORPTION בכתף-ימין → aggression דרך הצוואר | מכירה דועכת לאורך הראש→כתף-ימין; שבירת-צוואר תקפה רק אם CVD מתרחב | ה-divergence מתריע **מוקדם** (בכתף-ימין, לפני שבירה) | מתחת לשפל-הבליעה של כתף-ימין |
| **HNS_TOP** | היפוך | **−CVD divergence** → aggression מוכרת דרך הצוואר | מראה (ראש על +delta חזק, כתף-ימין על +delta חלש) | אזהרה מוקדמת בכתף-ימין | מעל שיא כתף-ימין |
| **BULL_FLAG** | המשך | **STACKED_IMBALANCE** על נר-הפריצה → delta-pullback רדוד | ≥3 imbalances = קונים-תוקפניים נכנסים → לא false-breakout. דגל בריא = −delta רדוד | מבדיל פריצה-אמת מ-chop בזמן-אמת | **מאחורי צביר-ה-imbalance** (מתחת לדגל) |
| **BEAR_FLAG** | המשך | **STACKED_IMBALANCE** (מכירה) על השבירה → +delta-pullback רדוד | מראה | מסנן fakeout | **מעל צביר-ה-imbalance** |
| **INITIATIVE (breakout)** | המשך | **aggression דרך הרמה + ריק-נזילות + bid נטען מתחת כ-S** (צ'קליסט Bookmap על ES) | ה-anti-signal: נזילות-מכירה נטענת *נגד* התנועה = מלכודת/absorption | פילטר fakeout בזמן-אמת ("הטיק הראשון מעבר לרמה לרוב מלכודת") | מתחת למדף-ה-bid החדש שנוצר מתחת לרמה |
| **REACTIVE (pullback)** | המשך | **ABSORPTION** של הדחיפה-הנגדית באזור-ביקוש קודם → imbalance מחודש + התאוששות-CVD | אזור-imbalance קודם = איפה שתוקפנים התחייבו; בריטסט הם "נעשים תוקפנים שוב" | מתזמן בנקודת-המפנה (נר-הבליעה), לא מנחש עומק-דחייה | מתחת לנר-הבליעה / לאזור-הביקוש המוגן |

---

## 3 · ⭐ הטבלה המרכזית — Woodies CCI (S4) × footprint

> **אזהרת-מקור:** Woodies CCI הוא שיטה נישתית (~2000) שסוחרת CCI *בלי מחיר* — **אין בספרות שילוב "footprint + Woodies"**. ההגדרות מתועדות; **המיפוי ל-footprint הוא INFERENCE** מעיקרון (אופי המשך-מול-היפוך של כל איתות), לא עובדה מצוטטת.

| תבנית (S4) | סוג CCI | Footprint לאישור (INFERENCE) | למה |
|------------|---------|------------------------------|-----|
| **ZLR** (Zero-Line Reject) | המשך | **STACKED_IMBALANCE + CVD-עולה-בכיוון** על נר-המפנה; הדחייה החזיקה מעל POC/VAL | הדיפ נקנה / הראלי נמכר — קבלת-ערך, לא שבירה |
| **GB100** (overshoot+resume) | המשך | כמו ZLR אך חזק יותר: ה-overshoot צריך להיראות **sweep+reclaim** (SWEEP_RETURN) עם delta-flip | מוכיח שה-overshoot היה stop-run, לא הפצה |
| **TT** (Tony, מומנטום-חלש) | המשך | **ABSORPTION שקטה + imbalances קטנים-יציבים**, CVD שטוח-עד-עולה (grind) | ה-CCI אומר שמומנטום חלש; ה-footprint מסביר למה זה עדיין עובד. ⚠️ divergence כאן = דלג |
| **TLB** (with-trend) | המשך | **imbalances + CVD מתרחב בכיוון-השבירה** + קבלה דרך VAH/VAL | אישור-פריצה קלאסי שמבדיל אמת משקר |
| **TLB** (counter-trend) | היפוך | **delta-divergence בקצה + ABSORPTION** ברמה שה-CCI מתהפך ממנה | fade — דורש הוכחת-תשישות |
| **HTLB** (chop) | שניהם | with-trend: **STACKED_IMBALANCE** דרך הרמה. counter: **ABSORPTION→EXHAUSTION** ברמה. הרמה האופקית של ה-CCI לרוב = POC/S-R אמיתי | יורה ב-chop — שם ה-footprint הכי מבחין |
| **HFE** (Hook From Extreme, ±200) | היפוך | **EXHAUSTION + delta/CVD divergence + ABSORPTION**; טריגר נקי = **SWEEP_RETURN** דרך קצה-המחיר | HFE גולמי הוא ~50% win — **כאן ה-footprint מוסיף את ה-edge** |
| **Famir** (failed-ZLR fade) | היפוך | **היעדר** המשך: על נר-ה-resume, CVD מתבדר / אין imbalance / נבלע מיד | היעדר-ההמשך הוא חתימת-ה-footprint של הכשל שאתה fade |

---

## 4 · עוגני-סטופ ותזמון-כניסה (העיקרון שמשיב על "תזמון הסטופים")

**הכלל האחיד בכל המקורות:** הנח את הסטופ **ממש מעבר לאירוע-ה-order-flow שמגדיר את התזה** — לא ברמת-המחיר השרירותית. כי שם העסקה באמת מתבטלת:
- **Absorption** → סטופ מעבר לאזור-הבליעה (אם הרמה נשברה — ההגנה נכשלה).
- **Sweep wick** → סטופ מעבר לקצה-הדקירה (כדי לא להיעצר מאותו stop-hunt שאתה fade).
- **Stacked imbalance / HVN** → עוגן-מבני (מחיר מגן עליהם). **LVN = אזור-דחייה/מעבר-מהיר, לא כרית-סטופ** (מחיר חותך דרכו).

**תזמון-כניסה — מה footprint מוסיף (מתועד):**
- **מפחית כניסות מוקדמות/שקריות:** דרוש *גם* שבירת-רמה *וגם* ספייק-delta בכיוון → מסנן fake-breakouts.
- **מפחית כניסות מאוחרות:** delta-divergence (מחיר↑, delta↓) מסמן מהלך-מותש → דלג על המרדף.
- **delta-flip / absorption-complete = הטריגר המדויק** להיכנס *אחרי* שהמוֹכרים מותשים → פחות adverse excursion, מחיר-כניסה טוב יותר.
- **העלות (trade-off):** ההמתנה-לאישור מאטה — מוותרים על המחיר-הכי-טוב תמורת ודאות גבוהה יותר. בשוק דק זה מייצר false-signals → לא להדק סטופ על רעש.

---

## 5 · שתי שאלות-הסינתזה

**(1) איזה אות-footprint יחיד עוזר הכי הרבה לרוחב?**
שניים, לפי סוג-התבנית — אין אחד-לכולם:
- **STACKED_IMBALANCE** — האות היחיד הכי-רחב ל**המשך** (דגלים, breakouts, ZLR/GB100/TLB-with-trend, reactive). נותן גם אישור-פריצה *וגם* עוגן-סטופ מבני.
- **ABSORPTION (+delta-divergence)** — האות היחיד הכי-רחב ל**היפוך** (double-bottom/top, HFE, Famir, H&S, counter-trend).
אם חייבים לבחור **אחד** למערכת: **delta/CVD** הוא הבסיס שמשרת את שניהם (מאשר המשך כשהוא בכיוון, מתריע היפוך כשהוא מתבדר) — אבל הוא *context*, וזקוק ל-absorption/imbalance לטריגר חד.

**(2) מה אומרת הראיה על שיפור win-rate / R:R — והמגבלות? (ביושר)**
- ✅ **גרעין אקדמי אמיתי:** order-flow imbalance מנבא שינויי-מחיר בטווח-קצר (Cont-Kukanov-Stoikov, JFEC 2014), order-flow הוא long-memory (Lillo-Farmer), זרימה-מיודעת מזוהה בעיקרון (Kyle). **לא פולקלור.**
- ⚠️ **אבל היתרון-המוכח חי בשכבה הלא-נכונה:** הוא נתפס ע"י **HFT/execution algos** על tick-data ב-sub-second. עד שזה קריא-לעין-אדם — "המהלך כבר קרה", הוא דועך מהר, ומושחת מ-spoofing/icebergs/שגיאת-סיווג (Lee-Ready ~73-93%).
- ❌ **אין ולו מחקר אחד** שמראה ששיטת-footprint *קמעונאית-דיסקרציונרית* מעלה win-rate/R:R. רוב תוכן-ה"edge" הוא שיווק-vendor. (רקע: ~95-97% מסוחרי-היום המתמידים מפסידים — Chague et al.)
- 🧪 **VPIN** הוא אזהרה קנונית: מטריקת-"רעילות-זרימה" משווקת שטענת-הניבוי שלה לא שרדה רפליקציה עצמאית (Andersen-Bondarenko 2014).

**מסקנה כנה:** התייחס ל-footprint כ**פילטר-context תאורטי-מבוסס שמפחית חלק מהאיתותים-השקריים בשוק נזיל** (ES/MES נזיל — טוב), **לא** כ-edge-רווח מוכח. **כל כלל-אישור חייב אימות ב-backtest שלך (out-of-sample, כולל עלויות+latency) לפני שסומכים עליו ב-LIVE.**

---

## 6 · המלצה ל-MEMS26 (ישימוּת)

1. **תפקיד S3 = veto/דירוג, לא מחולל.** עקבי עם §Source-of-Truth ב-CLAUDE.md: footprint *מסנן או מדרג* איתות S2/S4 קיים, לעולם לא *מסנתז* אותו. כל שדה-footprint מ-Sierra export, לא נגזר.
2. **מיפוי לגלאים הקיימים:** ל-S3 כבר יש ABSORPTION/STACKED_IMBALANCE/SWEEP_RETURN/EXHAUSTION — נתב לפי הטבלאות: **המשך→STACKED_IMBALANCE/CVD-בכיוון · היפוך→ABSORPTION/EXHAUSTION/SWEEP_RETURN/divergence.**
3. **גייט confluence פר-תבנית:** הוסף לטבלת-הסטופ/יעד (`MEMS26_STOP_TARGET_PLACEMENT_TABLE`) עמודת "footprint-confirm נדרש" פר-תבנית×סוג-יום — YAML-tunable, ניתן-לכבות.
4. **עוגן-סטופ מ-footprint:** זה בדיוק ה"anchor" החסר שדיברנו עליו ([[project-stop-target-placement-table]]) — absorption-edge / sweep-wick / imbalance-cluster כעוגנים חדשים ל-`stop_anchors.yaml`.
5. **חוסם-קדימוּת:** כל זה תאורטי עד ש**I-11/I-21 (S3 מת, 0 ברים)** נסגר — בלי הזנת-footprint חיה אין מה לאשר. לכן I-21 הוא תנאי-מקדים.
6. **שער-LIVE:** הוספת footprint-gate לנתיב-הירי = שינוי trading-logic → flag-gated, soak, אישור Michael לפני LIVE.

---

## 7 · מקורות

**Peer-reviewed / אקדמי:** Cont-Kukanov-Stoikov ([arXiv:1011.6402](https://arxiv.org/abs/1011.6402)) · Lillo-Farmer long-memory ([arXiv:1108.1632](https://arxiv.org/pdf/1108.1632)) · Lee-Ready accuracy ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1042443100000482)) · VPIN ([Easley et al.](https://www.quantresearch.org/VPIN.pdf)) + רבטל ([Andersen-Bondarenko, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1881731)) · retail base-rate ([Chague et al., SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101)).
**Practitioner (context, לא הוכחה):** ATAS absorption ([atas.net](https://atas.net/blog/absorption-of-demand-and-supply-in-the-footprint-chart/)) · GoCharting imbalances ([gocharting](https://gocharting.com/docs/orderflow/imbalance-charts)) · Bookmap CVD + breakout-checklist ([CVD](https://bookmap.com/blog/how-cumulative-volume-delta-transform-your-trading-strategy), [breakout/fakeout](https://bookmap.com/blog/breakout-or-fakeout-the-3-point-checklist-for-confirmation)) · Trader Dale absorption + stacked-imbalances ([absorption](https://www.trader-dale.com/order-flow-how-to-trade-the-absorption-setup-trade-entry-confirmation/), [stacked](https://www.trader-dale.com/order-flow-day-trading-strategy-stacked-imbalances/)) · Woodies CCI ([Gannon](http://wealthv.com/TradingSystems/Naked/woodie8_patterns.htm), [O'Connell](https://www.scribd.com/doc/172192725/Woodies-Cci-Patterns-and-Terminology-by-Jim-O-Connell)) · POC/VA ([TradingView](https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/)) · HVN/LVN + stops ([Optimus Futures](https://optimusfutures.com/blog/footprint-charts/)) · liquidity-sweep stops ([Intl Trading Institute](https://internationaltradinginstitute.com/blog/liquidity-sweeps-entry-exit-strategies/)) · delta-entry-confirmation ([TradeFundrr](https://tradefundrr.com/entry-confirmation-with-delta/)).
