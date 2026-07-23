# CC — DAYTYPE_ACCEPTANCE_DEMOTION_V1: תווית יורדת לפי acceptance (פסיקת-D2 של מייקל) — בניית-לילה

**ההקשר (07-22, live):** המכונה סיווגה Trend_Normal על ראיות-השעה-הראשונה (drive+28pt, שבירת-PDH),
המחיר החזיר הכל וחזר-ל-IB — יום-Normal מובהק (walkthrough דלתוני מלא ב-LOG 18:15) — אבל **אסקלציה-בלבד**
תקעה את התווית, והמערכת שותקה על תווית-שגויה עד override-ידני של מייקל (18:20). ה-audit-replay כבר אמר
Normal — רק המכונה-החיה לא יודעת לרדת.

**הפסיקה הקיימת (מייקל 06-30, D2, ratified):** מעברי-סוג-יום הם acceptance-driven לפי דלתון — **דו-כיווני**,
כולל Trend→Normal_Variation, עם שער-בר-מאשר. מעולם לא קודד. עכשיו מקודד. ("איך זה לא קורה יותר ולסדר" —
מייקל 07-22 18:18.)

## הכלל (מכני, שמרני)
כשהתווית-החיה היא Trend_* והמחיר **חוזר ומתקבל בתוך ה-IB**:
- acceptance-חזרה = ≥K ברים-סגורים רצופים (K=3, config) שכל-כולם בתוך טווח-ה-IB (High<IB_high−tol,
  Low>IB_low+tol; tol=זהה ל-location tol) **אחרי** שהייתה הרחבה מעבר.
- → demote צעד-אחד: Trend_Normal/Trend_DD → Normal_Variation. (המשך-ירידה ל-Normal — רק דרך אותו כלל
  בסבב-הבא, לעולם לא ישירות; עלייה-מחדש = האסקלציה הקיימת.)
- לוג מלא: `[DayType] ACCEPTANCE-DEMOTION: Trend_Normal → Normal_Variation (K=3 bars re-accepted inside IB
  7556.25/7525.00)` + עדכון consumer/DB באותו מסלול כמו אסקלציה.
- Fixture חובה מהיום: ברי-07-22 (סיווג-Trend ~17:30-47 → ברים 17:35-17:50 בתוך-IB → demote ל-Normal_Variation
  עד ~17:50) + counter-fixture: **יום-Trend אמיתי = 07-16 (Trend_Normal DOWN, אומת קנונית)** — אין חזרה-מלאה
  ל-IB → אין demote. **תיקון (מייקל 2026-07-22, סמכות-S1):** 07-21 היה **Variation** (לא Trend — הקנוני מסכים:
  Normal_Variation UP), אז הוא counter-fixture שגוי; השתמש ב-07-16 כיום-ה-Trend שאסור-לו-לרדת.

## מיקום + דגל
- הלוגיקה במכונת-התווית-החיה (איפה שהאסקלציה חיה — אותו נתיב שכתב "promoted:"), לא ב-getter.
- דגל `DAYTYPE_ACCEPTANCE_DEMOTION_V1` (OFF עד אימות) + RULED (ציטוט D2 06-30 + 07-22). הדלקה בריסטארט-בוקר.
- **לא** נוגע ב-classify_replay (audit) ולא ב-override (מייקל תמיד גובר).

## הערת-אמת-על
זה גשר. הפתרון-הסופי = S1_ENGINE part-b (התווית-החיה = המסווג-הקנוני פר-בר, Task#5 המלא) — ה-audit ידע
נכון כל היום. עד שזה נבנה, ה-demotion סוגר את מחלקת-התקיעה.

חוק-5 · cursor מאמת · cowork מאמת-סימטרית.
