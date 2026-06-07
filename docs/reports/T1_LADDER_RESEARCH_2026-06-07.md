# מחקר: מיקום T1 כפונקציה של גודל-הסטופ (סולם יורד) — 2026-06-07

> הוזמן ע"י Michael בשיחת עוגני-ZLR. 5 צירי-חיפוש מקבילים, ~20 מקורות.
> מסקנה בקצרה: **הסולם היורד נתמך כיוונית (THEORY+doctrine), המקדמים המדויקים
> חייבים כיול מ-MFE של SHADOW — אין backtest פומבי שסוגר את זה.**

## 1 · מה המתמטיקה אומרת (חזק)
- תחת random-walk: ‏P(פגיעה ב-T1 לפני הסטופ) = ‏1/(1+R). ‏1R→50% · ‏0.75R→57% ·
  ‏0.65R→61% · ‏0.5R→67% · ‏0.4R→71%. אומת ב-Monte-Carlo ‏500k ([EdgeTools](https://www.tradingview.com/chart/SPX/HUmb4N1D-The-Math-Retail-Traders-Ignore-Risk-Reward-Ratios-Are-Worthless/)).
- אינטראדיי 5–15 דק' המדדים **מתואמים-שלילית** (mean-reverting, Chordia et al.;
  [CESA WP](https://www.fernuni-hagen.de/igas/docs/cesa_wp_14.pdf)) ⇒ יעדים רחוקים
  מתחת לקו-ה-random-walk לכניסות-מומנטום. סטיות קטנות (1–2 נק' אחוז).
- הפסדים נפגעים ~פי-3 מהר מרווחים ב-3:1 (אסימטריית זמן, מאומת סימולציה).

## 2 · סולם יורד לסטופים רחבים — נתמך כיוונית (THEORY)
שרשרת הטיעון ([Macroption](https://www.macroption.com/is-volatility-mean-reverting/), [Speight et al. JFM](https://onlinelibrary.wiley.com/doi/10.1002/(SICI)1096-9934(200005)20:5%3C425::AID-FUT2%3E3.0.CO;2-0)):
סטופ רחב = כניסה על spike-תנודתיות → לרכיב-ה-spike יש דעיכה מהירה → ה-MFE
שאחרי הכניסה נמשך מהתפלגות רגועה יותר → MFE במונחי-R מתכווץ ⇒ T1 יחסי-יורד.
**חולשה:** תנודתיות אינטראדיי לפעמים trending ולא mean-reverting בטווח דקות-שעות;
אין backtest ישיר. ⇒ היפותזה-לכיול, לא עובדה.

## 3 · הצלבת-דוקטרינה (Bulkowski + Woodies)
- Bulkowski (מדוד, 10k+ תבניות): תבניות משיגות רק **30–80% מה-measure המלא**
  (עליות ~58–75%, ירידות ~30–55%) — יעד-ראשון ב-50–60% מהמדידה אמין בהרבה
  ([measure rule](https://thepatternsite.com/measure.html)). ‏throwback/pullback ב-**~55–74%**
  מהפריצות תוך ~5 ימים — מימוש-חלקי-מוקדם מוצדק סטטיסטית.
- Woodies (doctrine): מימוש-ראשון **מהר** — בסיגנל-CCI הראשון או כשהרווח ≈ גודל-הסטופ
  (≈1R על סטופים רגילים 7–10 ticks), ואז BE+1 ([wealthv](http://wealthv.com/TradingSystems/Naked/woodie7entry_exit.htm)).
  תואם את אזור ה-0–5 נק' = ‏1R של Michael.

## 4 · scale-out בכלל (כנות)
המתמטיקה: scale-out **מוריד** תוחלת-לעסקה מול all-out (מקור מדוד יחיד: ~50%
מהרווח התאדה; [Mabe](https://davemabe.com/should-you-ever-take-partials)). ההצדקה האמיתית: הקטנת שונות/drawdown — לגיטימי
ובמיוחד לקראת LIVE. להחזיק בידיעה הזו: המבנה הוא בחירת-סיכון, לא מקור-edge.

## 5 · כלל-BE (חוזה בודד)
מדוד ([Davey](https://easylanguagemastery.com/building-strategies/breakeven-stops-worth-effort/), [ATAS/QS](https://atas.net/blog/break-even-in-trading/)): BE ≈ ניטרלי-עד-+6% רווח, אבל **−25% drawdown**;
BE-מוקדם (<1R) מזיק — spike של scratches. המלצה: BE עם **חיץ-רעש** (entry−2T
ללונג) ולא entry מדויק; ב->25 נק' סיכון ה-BE ב-+15 (≈0.5–0.6R) מוצדק כבקרת-drawdown
גם אם לפני 1R (חוזה יחיד, $125+ בסיכון).

## 6 · ההמלצה — הסולם המלא ל-ZLR (היפותזת-פתיחה לכיול)
| סיכון (נק') | חוזים | T1 | T1 בפועל | ‏P(T1) ‏RW |
|---|---|---|---|---|
| 0–5 | 3 | **1.00R** | עד 5 נק' | ~50% |
| 5–10 | 3 | **0.75R** | 3.75–7.5 | ~57% |
| 10–15 | 3 | **0.65R** | 6.5–9.75 | ~61% |
| 15–20 | 2 | **0.50R** ← המלצת-מחקר | 7.5–10 | ~67% |
| 20–25 | 2 | **0.40R** ← המלצת-מחקר | 8–10 | ~71% |
| >25 | 1 | ‏TP ‏1:1 · ‏BE ב-+15 (עם חיץ −2T) | — | — |
תכונה יפה: ‏T1 האבסולוטי מתייצב על ~7.5–10 נק' בכל טווח הסטופים הרחבים —
בדיוק ההיגיון ש"השוק נותן מה שהוא נותן" ולא לפי גודל נר-הכניסה.

## 7 · תוכנית-הכיול (החלק החזק באמת)
במהלך ה-SHADOW soak לבנות **עקומות-שרידות MFE פר-תבנית×סוג-יום** (≥200 עסקאות,
רצוי tick/1-min כי ברי-5-דק' מחסירים MFE): לקבוע T1 בנקודת-שרידות ‏70–80%,
runner ב-25–35%. הסולם שלמעלה = נקודת-פתיחה; ה-MFE שלנו = הפוסק.

---
# חלק ב' — מחקר ייעודי: שכבת 3-חוזים ושכבת חוזה-1 (4 סוכנים נוספים)

## ב1 · שכבת 3-חוזים (סטופ ≤15 נק') — האזורים של Michael אושרו
- **0–5 → 1R: ממוקם היטב.** תקדים-Woodies (partial כשהרווח ≈ הסטופ) + עקומות-MFE
  (1R על מרחק קטן יושב באזור-שרידות 60–85%) ([NexusFi](https://nexusfi.com/a/risk-management/maximum-favorable-excursion-mfe), [Woodies doc](http://wealthv.com/TradingSystems/Naked/woodie7entry_exit.htm)).
- **5–10 → 0.75R: סביר** · **10–15 → 0.65R: נכון-כיוונית, הכי-פחות-מגובה** — לאמת ב-MFE.
- **⚠️ ממצא-עלויות (MEASURED, חדש):** חיכוך MES מלא (עמלות ~$1.30 + ספרד $1.25 +
  slippage) ≈ **0.5–0.75 נק' לעסקה-הלוך-ושוב**. יעד מתחת ל-~3 נק' מאבד 17–75%
  מהברוטו לחיכוך; מתחת ל-10% רק מ-**6–7 נק'** ([Tradovate fees](https://tradovate.zendesk.com/hc/en-us/articles/360022418214), [CrossTrade](https://crosstrade.io/learn/futures-trading/es-vs-mes), [Tradeify](https://tradeify.co/post/micro-vs-mini-futures-trading-comparison-strategy)).
  ⇒ הצעת-knob: `t1_min_points` (רצפת-T1 אבסולוטית ~3 נק') לסטופים הזעירים — להחלטת כיול.

## ב2 · שכבת חוזה-1 (>25 נק') — אישור חזק ל-BE, עדכון ליעד
- **ה-BE ב-+15 שלך אושר ע"י המקור המדוד החזק ביותר:** מחקר-Davey (567k backtests,
  40 שווקים): יציאות-BE = הטובות ביותר אחרי stop&reverse, וסף-BE מתון
  **0.3–0.6R הוא האופטימום** — ‏+15 על סיכון 25–30 = ‏0.5–0.6R, בדיוק בתחום
  ([KJ Trading 567k study](https://kjtradingsystems.com/algo-trading-exits.html)).
- **עדכון ליעד ה-1:1 (MEASURED):** טווח-יומי ES נורמלי = 25–45 נק'; יעד 25+ נק'
  + סטופ 25 נק' = ~כל טווח-היום ⇒ שיעור-פגיעה נמוך מהותית ביום רגיל
  ([YMI ADR stats](https://youngmoneyinvestments.com/blog/es-nq-futures-average-daily-range-statistics), [TradingStats 12y ORB](https://tradingstats.net/orb-strategy-research/), [OU first-passage](https://arxiv.org/pdf/1810.13010)).
  ⇒ המלצה: **TP = min(1R · ‏50–75% מהטווח-היומי-שנותר · הרמה-המבנית הקרובה
  (POC/VA-edge/PDH-PDL))** — לא R-עיוור.
- **time-stop:** יציאות-זמן מהירות = הגרוע-במבחן; אם בכלל — ארוך (30–45 ברים) או
  סגירת-סשן. **כניסה:** רק spike ראשון במהלך — לא לרדוף spike שני/שלישי.
- **לא לכווץ את הסטופ "לנוחות":** stop+target צמודים = משפחת-היציאות הגרועה במבחן.

## ב3 · הסולם הסופי המעודכן (היפותזת-כיול ל-SHADOW)
| סיכון | חוזים | T1 | הערה |
|---|---|---|---|
| 0–5 | 3 | ‏1R (אופציה: רצפה 3 נק') | חיכוך כבד מתחת ל-3 נק' |
| 5–10 | 3 | ‏0.75R | |
| 10–15 | 3 | ‏0.65R | לאמת ב-MFE |
| 15–20 | 2 | ‏0.5R | |
| 20–25 | 2 | ‏0.4R | |
| >25 | 1 | ‏min(1R, ‏%ADR-שנותר, רמה-מבנית) · ‏BE ב-+15 (−2T חיץ) | ‏BE מאומת-Davey |

*רמות-ראיה מסומנות פר-טענה בגוף שני החלקים.*
