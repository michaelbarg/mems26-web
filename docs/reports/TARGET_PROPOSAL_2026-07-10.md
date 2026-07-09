# הצעת-יעדים לפסיקת-בוקר — 2026-07-10

**מקור:** TP Audit v2 (276 trades, 30 days, psql). **עיקרון:** T1 = p25–p50 של MFE
(הזדמנות ריאלית); T2/T3 = מדרגות-מעלה לכיוון p75. כפוף ל-TP-1 (לא מעבר ל-IB edge
ביום שאינו Neutral/Trend).

## 5 השינויים הגדולים (פסיקת מייקל)

### 1. REACTIVE_LONG × Variation — 🔴 hit-rate 28% (18 trades)
- **T1 נוכחי:** ~9.3 נק' (מחציון)
- **MFE p25/p50/p75:** 4.2/18.2/22.2
- **המלצה:** T1 → **6 נק'** (p25+, hit-rate צפוי ~55%). T1 הנוכחי מפספס כי הוא
  מעל חציון ה-MFE רק ב-Variation שבו התנועה הפוכה שכיחה.

### 2. FAMIR × Variation — 🔴 T1/MFE = 2.10 (5 trades)
- **T1 נוכחי:** ~12.6 נק'
- **MFE p50:** 6.0 בלבד
- **המלצה:** T1 → **5 נק'** (p25+). הרוב של ה-MFE נגמר לפני T1 → סטופ-פאנדינג.

### 3. TLB × Trend_Normal — 🟡 T1 captures 26% of MFE (22 trades)
- **T1 נוכחי:** ~5.6 נק'
- **MFE p50:** 21.5 נק' (!)
- **המלצה:** T1 → **9 נק'** (p25). ביום Trend, ה-MFE גבוה מאוד — T1 קרוב מדי
  מוותר על 75% מהתנועה. Hit-rate ירד ל-~55% אבל R:R ישתפר.

### 4. INITIATIVE_LONG × Variation — 🔴 hit-rate 17% (6 trades)
- **T1 נוכחי:** ~18.4 נק'
- **MFE p50:** 21.0
- **המלצה:** T1 → **8 נק'** (p25-). Hit-rate 17% = 5 מתוך 6 מגיעות לסטופ.
  T1 רחוק מדי ביחס לסביבת-Variation.

### 5. BULL_FLAG_LONG × Variation — 🔴 T1/MFE = 1.56 (4 trades)
- **T1 נוכחי:** ~12.1 נק'
- **MFE p50:** 7.8
- **המלצה:** T1 → **6 נק'** (p25+). T1 מעבר ל-MFE = סטופ-פאנדינג מובנה.

## טבלת T1 מוצע (תאים עם n≥3)

| תבנית | סוג-יום | T1 נוכחי | T1 מוצע | עיקרון |
|--------|---------|----------|---------|--------|
| REACTIVE_SHORT | Variation | 9.8 | 9.0 | p25 (שמרני, hit-rate סביר) |
| REACTIVE_LONG | Variation | 9.3 | **6.0** | p25+ (hit-rate 28%→~55%) |
| TLB | Trend_Normal | 5.6 | **9.0** | p25 (מוותר על מעט MFE) |
| ZLR | Variation | 5.8 | 5.5 | p25- (ללא שינוי — 52% hit) |
| ZLR | Trend_Normal | 5.4 | 5.5 | ללא שינוי (69% hit) |
| TLB | Variation | 8.3 | 8.0 | ללא שינוי (69% hit) |
| INITIATIVE_SHORT | Variation | 14.0 | 10.0 | p25+ (36%→~50%) |
| INITIATIVE_LONG | Variation | 18.4 | **8.0** | p25- (17%→~50%) |
| REACTIVE_SHORT | Trend_Normal | 6.0 | 6.0 | ללא שינוי |
| FAMIR | Variation | 12.6 | **5.0** | p25+ (T1/MFE 2.1→~0.8) |
| BULL_FLAG_LONG | Variation | 12.1 | **6.0** | p25+ (T1/MFE 1.56→~0.8) |
| HTLB | Variation | 14.0 | 10.0 | p25+ (שמרני, n=5) |

## הערות
- T2/T3 = T1×2 / T1×3 (לרץ runners — כפוף ל-TP-1 clamp)
- HFE disabled (פסיקה קיימת) — לא בטבלה
- SIM_TEST — לא רלוונטי
- n<3 = מדגם קטן מדי, לא מוצע שינוי

_אפס שינויים בוצעו. הטבלה = פסיקת מייקל בלבד._
