# מחקר — CVD ו-One-Directionality לסיווג Open-Drive מול Open-Auction (ES/MES)

**מקור:** מחקר חיצוני (web/ספרות) שהתקבל 2026‑05‑31 · **סטטוס:** שכבת ידע +
נוסחאות — דורש אימות זמינות CVD ב-DB + כיול פנימי לפני מימוש · **שער:** אישור
Michael.

> ⚠️ **עודכן/הוחלף ע"י `RESEARCH_01_CVD_OPENING_FINDINGS_2026-05-31.md`** —
> מספרים מדויקים יותר (דגימת ES 6,142 ימים: double-break 15-דק' 61% / 30-דק'
> 47.9%; gap 4 קטגוריות; ספי priors PE>0.65). השתמש ב-RESEARCH 01 כמקור.
> תיעוד נאמן של תוצאת המחקר. ראה §"מיפוי ל-detect_opening_type שלנו" בתחתית.

---

## TL;DR
- לסווג את הפתיחה ב-ES/MES עם **ציון CVD/efficiency היברידי + פילטר range-
  expansion מנורמל-ATR**, על 30 הדק' הראשונות (עם קריאה מקדימה ב-15 דק'):
  Open-Drive = CVD חתום גבוה + path efficiency גבוה + range expansion ≳1×ATR15;
  Open-Auction = net CVD ~0, path efficiency נמוך, טווח מוכל בברי הפתיחה.
- חתימת trades: **tick rule** או aggressor side מהבורסה לדאטת tick; **BVC** רק
  כשיש דאטת בר בלבד. ב-ES, Andersen & Bondarenko (2015): tick rule עדיף על BVC.
- המטריקה המבחינה ביותר: **path/persistence efficiency = net_CVD / Σ|delta_i|**,
  מנורמל ב-range expansion מבוסס-ATR — לא delta גולמי. ספים לפי פרסנטילים, לא
  מספרים מוחלטים.

## ממצאי מפתח

### 1 · נוסחאות CVD
- delta לבר = aggressive buy − aggressive sell · `CVD_t = CVD_{t-1} + delta_t`.
  הערך באו ובשיפוע וביחס למחיר, לא ברמה המוחלטת.
- חתימה — tick rule / Lee-Ready (1991): Quote Rule + Tick Test. דיוק: Lee-Ready
  ~85–93% (Odders-White/Lee-Radhakrishna); tick test לבד ~75–83%. בעתידיים עם
  ספר מרכזי הדיוק גבוה; ב-ES — tick rule מנצח BVC.
- BVC (Easley-López de Prado-O'Hara, RFS 2012): `V_buy = Σ V_i·Z[(ΔP)/σ_ΔP]`,
  Z=CDF נורמלי (או Student-t עם 0.25 df ב-JFE 2016 לזנבות שמנים). חותם *שבר*
  מהנפח, רציף, מול חתימה דיסקרטית של Lee-Ready.
- נרמולים: `delta/total_volume` (delta efficiency, [−1,1]) · `delta/range`
  (לחץ נפח ליחידת מחיר) · z-score `(CVD−μ)/σ` על lookback ~60 בר.

### 2 · מטריקות One-Directionality
- (a) **delta efficiency** = net_CVD/total_volume — שבר הנפח שהיה כיווני נטו.
- (b) **path/persistence efficiency** = net_CVD/Σ|delta_i| — **המטריקה הכי
  ישירה ל"חד-כיווניות"**: ~1 = כל בר דחף לאותו כיוון (drive); ~0 = התחלפות
  (auction).
- (c) OFI (Cont-Kukanov-Stoikov 2014) — שינויי תור ב-best bid/ask (limit+market+
  cancel); מנבא price-impact קצר-טווח. שונה מ-CVD (רק aggressor volume).
- (d) VPIN — gauge רעילות על volume-clock; **לא** מסווג פתיחה ישיר.
- (e) **CVD-price divergence** — מחיר שיא חדש ו-CVD לא מאשר = exhaustion; CVD
  חזק ומחיר תקוע = absorption. שניהם נגד drive מתמשך.

### 3 · חתימות סוגי פתיחה (Dalton/Steidlmayer)

| סוג פתיחה | ביטחון | חתימת CVD/delta | טווח |
|---|---|---|---|
| Open-Drive | הגבוה | CVD חתום-אחיד גדול מהפעמון; path eff ≈1; מחיר לא חוזר דרך open | range expansion חזק |
| Open-Test-Drive | גבוה | delta הפוך קצר (test), אז CVD חזק אותו-כיוון; net גדול | בוחן רפרנס ואז מתרחב |
| Open-Rejection-Reverse | נמוך (~50%) | CVD לכיוון, אז CVD הפוך *גדול יותר*; net הופך סימן; divergence בשיא | קצה נדחה, מתרחב הפוך |
| Open-Auction (in) | הנמוך | net CVD ~0; path eff נמוך; delta מתחלף | מוכל, סיבובי סביב open |
| Open-Auction (out) | בינוני | דו-צדדי סביב open עם הטיה מתפתחת | סביב open, אז התרחבות |

פתיחות גבוהות-ביטחון (Drive/Test) → ימי טרנד; נמוכות (Auction) → ימי איזון.
פתיחה מחוץ לטווח/value אתמול → סיכויי יום כיווני; בפנים → רוטציה.

### 4 · חלון זמן 15 מול 30 דק'
- היוריסטיקה: high/low היום ב-30 הדק' הראשונות ~50%, ב-60 הדק' ~75%. Drive
  קריא ב-5–15 דק'; פתיחה נמוכת-ביטחון צריכה 30–60 דק'.
- Market Profile: יחידה קנונית = TPO 30-דק'; **Initial Balance = 60 דק'
  ראשונות (A+B)**. opening range = 15 או 30 דק'.
- Whipsaw (Edgeful/SPY, 6 ח'): שבירת **שני** צידי הטווח — **15-דק': 56%**,
  30-דק': 42%, 45-דק': 31%. כלומר 15 דק' הרבה יותר חשוף ל-false drives.
- **המלצה:** סיווג provisional ב-15 דק' (3 ברי 5-דק') → נעילה ב-30 דק'. 15 דק'
  לבד מספיק רק ל-Open-Drive חד-משמעי.

### 5 · נרמול ATR של ספי gap/range
- סף gap קבוע ±2 נק' **לא** רובסטי — ATR יומי של ES נע ~40–60 נק'. להמיר לשבר
  ATR.
- למדוד opening-range/ATR ו-gap/ATR. True Range תופס את ה-gap. מכפילי stop:
  scalping ~1×, day ~1.5–2×, swing ~2–3×; מתחת ל-1× → רעש.
- **בנייה:** ATR(14) על ה-timeframe (או ATR יום-קודם ל-gap). gap/ATR_daily,
  range expansion = OR_range/ATR15. drive מאושר כש-range expansion > ~1×ATR15 +
  CVD תומך; auction כשמוכל היטב בתוך ~1×ATR. לכייל מכפיל per-instrument.

## סקיצת מסווג (לכל session)
1. בנה ברי delta 5-דק' מ-tick-rule (או aggressor); צבור CVD מ-cash open.
2. ב-15 דק': net_CVD, path_eff=net/Σ|delta|, delta_eff=net/total, range_exp=
   (H−L)/ATR15, gap/ATR_daily, דגל divergence.
3. provisional: Drive אם |path_eff| גבוה (top-quartile, סימן עקבי) ו-range_exp≳1
   ובלי divergence; Auction אם z-score של |net_CVD| נמוך ו-path_eff נמוך
   ו-range_exp קטן.
4. ב-30 דק': הערך מחדש; זהה Test-Drive (delta הפוך מוקדם אז same-signed דומיננטי)
   ו-Rejection-Reverse (היפוך סימן net CVD + divergence בשיא המוקדם).

## המלצות
1. חתימה: aggressor/tick rule כברירת מחדל; BVC רק לדאטת בר.
2. מטריקה ראשית: path efficiency (net/Σ|delta|), נתמך ב-delta efficiency + z-score.
3. ספים: לא לקודד מוחלטים — פרסנטילים מ-trailing (~75th של ~60 sessions). לכייל
   מחדש כשמשטר זז.
4. ATR: נרמל gap (gap/ATR_daily) ו-range expansion (OR/ATR15). התחל ~1×ATR15.
5. חלון: provisional 15 דק' → נעילה 30 דק'. קריאת Drive ב-15 דק' רק כש-path eff +
   range expansion + divergence מתיישרים (56% double-break).
6. divergence guard: דכא Drive אם יש divergence/absorption בשיא הפתיחה (=Rejection-
   Reverse).
7. benchmarks: אם double-break ב-15 דק' בדגימת ES/MES שלך >>56% → הארך חלון. אם
   דיוק BVC נופל הרבה מתחת ל-tick rule → נטוש BVC לחוזה הזה.

## Caveats
רוב סטטיסטיקות הביטחון/timing הן retail (Edgeful/SPY 6 ח'), לא peer-reviewed —
לגזור מחדש על ES/MES שלך. דיוק BVC שנוי במחלוקת, גרוע בתנודתיות (=הפתיחה). VPIN
לא מסווג פתיחה. CVD דורש דאטת aggressor אמינה — חתימה לא-עקבית משחיתה הכל.
ספים תלויי-משטר — כל מכפיל קבוע יסחף; דרוש כיול per-instrument מתמשך.

---

## מיפוי ל-detect_opening_type שלנו (תוספת Cowork 2026‑05‑31)

| היבט | מה שיש לנו | המלצת המחקר | פער / פעולה |
|---|---|---|---|
| קלט סיווג | מחיר בלבד: `net_move/total_range ≥0.7` | מחיר **+ CVD** (path eff) + range/ATR + divergence | להוסיף CVD כקלט |
| מטריקת CVD | אין (CVD רק ב-reasoning_notes) | `path_eff = net_CVD/Σ|delta_i|` ראשית | הנוסחה ש-prompt הפתיחה ביקש |
| חתימת CVD | Sierra CDV (COT/AMT) — לאמת שיטה | aggressor/tick rule | לאמת ש-Sierra נותן aggressor per-level |
| נרמול | אין | delta/total, delta/range, z-score(60) | להוסיף |
| ספים | קבוע 0.7 | פרסנטיל trailing (~75th, 60 sessions) | כיול פנימי |
| gap | ±2 נק' מוחלט | gap/ATR_daily | להמיר |
| חלון | 3 ברים (15 דק') יחיד | provisional 15 → lock 30 | מודל דו-שלבי (תואם 30/60/90) |
| Rejection-Reverse | היפוך מחיר בלבד | היפוך + **divergence guard** | להוסיף divergence |
| זמינות נתונים | — | CVD per-bar חובה | **חוסם: לאמת ש-CVD נשמר per-bar ב-DB** |

**עדיין חסר (השלב הבא):** (1) אימות שדאטת ה-CVD/aggressor נשמרת per-bar ב-DB.
(2) כיול פנימי על `v9_bars_5min` — פרסנטילים של path_eff/range_exp, ובדיקת
double-break rate בפועל מול 56%. הנוסחאות והמכפילים כאן = priors בלבד.
