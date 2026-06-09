# מגה‑פרומפט — מחקר מלא לכיול מערכת S1 (Day Type)

> הוראות שימוש: העתק את כל הבלוק שמתחת לקו והדבק בצ'אט/agent חדש שיש לו גישה
> ל‑repo `mems26_web_git`. הפרומפט עצמאי — אינו תלוי בשיחה הקודמת.

---

אתה agent מחקר במערכת מסחר אוטונומי **MEMS26** (חוזי MES, Sierra Chart →
bridge → FastAPI/SQLite). המשימה: **מחקר מלא לכיול מערכת S1 (סיווג סוג‑היום)**.
זהו מחקר/AUDIT — **אסור לשנות קוד מסחר, סכימה, או ספים**. התוצר הוא דוח עם
ממצאים, מקדמים מוצעים, וראיות גולמיות. מימוש = שער אישור של מיכאל (בעל המערכת).

## רקע — איך S1 עובדת היום

S1 מסווגת את "סוג היום" (Market Profile / Dalton‑Zohar) דרך מכונת מצבים 13
שלבים (A1→C3) ב‑`backend/v9/systems/day_type/`:

- **A1** הקשר טרום‑פתיחה (gap, מיקום מול אתמול).
- **A2** סיווג פתיחה מ‑3 ברי 5‑דק' ראשונים (15 דק') — `detect_opening_type`.
- **A3/A4** מעקב ונעילת IB מ‑Sierra Study ID:6 בלבד (בלי fallback מהברים).
- **B1** הצבעה ראשונית: `DECISION_MATRIX[(opening_type, ib_width)] → day_type`.
- **B2–B6** עדכון לפי התנהגות (extensions/range/ATR), מחליף סוג רק אם
  שיפור ביטחון >0.15.
- **C1** נעילה כש: confidence ≥0.85, או 2 הצבעות זהות רצופות, או
  `session_min ≥210` (13:00 ET, כפוי).
- **C2/C3** ביטחון סופי + בחירת playbook (אסטרטגיה/sizing/time‑stop).

סוג היום קובע playbook מסחר: Trend_Normal=TREND_FOLLOW · Trend_DD=90דק' ·
Variation=BREAKOUT_FADE · Normal=RANGE_TRADE · Neutral_E/C=FADE_EXTREMES חצי
size · Nontrend=NO‑TRADE/scalp.

## הבעיה — ספים מוחלטים + CVD שלא משפיע

ערכים נוכחיים (אומתו 2026‑05‑31, קרא לאימות):

| נושא | קובץ · פונקציה | ערך |
|------|----------------|-----|
| רוחב IB | `day_type/detector.py::classify_ib_width` | NARROW <15 · MEDIUM 15–25 · WIDE >25 **נק' מוחלט** |
| ספים | `day_type/schemas.py::DayTypeConfig` | `ib_narrow_max_pt=15.0` · `ib_medium_max_pt=25.0` |
| ⚠️ אי‑התאמה | `day_type/schemas.py` IBWidth | הערה אומרת `MEDIUM 15-20`, קוד מריץ **25** |
| תקופת IB | `schemas.py` · `state_machine.py::_stage_a3` | `ib_period_min=60` (נקודה יחידה) |
| פתיחה | `day_type/detector.py::detect_opening_type` | 3 ברים (15 דק'), `net_move/total_range ≥0.7`→DRIVE |
| gap | `day_type/state_machine.py::_stage_a1` (~408) | ±2.0 נק' **מוחלט** |
| CVD | `day_type/state_machine.py` (`update_cvd_state` ~848, שימוש ~948) | מוזרם אך **לא משפיע** — רק `reasoning_notes` |
| מטריצה | `day_type/decision_matrix.py::DECISION_MATRIX` | (opening × width) → day_type |
| נעילה | `day_type/state_machine.py::_stage_c1` | conf ≥0.85 · 2 votes · `session_min≥210` |
| Zohar | `day_type/zohar_rules.py` | delta: extensions שני צדדים `>0` · width TPO `>5` · timing 12:30 |
| התמדה | `day_type/consumer.py` | UPSERT `v9_day_type_history` לפי session_date |

**מנוף:** רוחב ה‑IB מזין ישירות את `DECISION_MATRIX` → הטיה כאן מזיזה את כל
הסיווג. עדות לכשל הדפוס: מערכת S2 עם ספים קבועים `[1.5-1.75pt]` נתנה 0/44 ברים
כי הטווח הממוצע היה פי 4. אותו מנגנון אורב ברוחב IB.

## כללי משחק (Pre‑LIVE — חובה)

1. קרא תחילה `CLAUDE.md` ו‑`.cursor/rules/mems26-pre-live-protocol.mdc`.
2. **אבחן עם נתונים לפני שמציעים** — כל טענה מספרית מאומתת בשאילתת DB /
   bar‑math על נתונים גולמיים. לא מהזיכרון, לא מהמפרט.
3. **קרא את הקוד הנוכחי** לפני כל הצעה. אפס edit מהזיכרון.
4. **Source of truth:** מותר ניתוח offline על ברים שכבר נקלטו. **אסור** לסנתז
   OHLC/CVD/IB או להמציא נתונים.
5. **Verification quote** (Rule 5): כל "עובד/תקין/עובר" מלווה בפקודה + פלט גולמי.
6. **TZ מפורש** (Rule 4): כל זמן (session_min, checkpoints, חלונות SQL) נושא TZ
   מפורש (ET / UTC), אין "assumed".
7. אסור להריץ שירותי MEMS26 או לגעת בנתיב ריצה. סקריפטי מחקר תחת
   `scripts/research/` בלבד, מסומנים throwaway, לא מיובאים ע"י backend.

## שאלות המחקר

### A · רוחב IB יחסי (מנוף גבוה — התחל כאן)
- A1. על ≥40 ימי RTH: התפלגות `ib_range` (נק') — avg/median/רבעונים. כמה ימים
  בכל מחלקה תחת 15/25 הנוכחיים?
- A2. מתאם `ib_range` ל‑ATR: `ib_ratio = ib_range / ATR`. **הגדר מפורשות איזה
  ATR** (תקופה/timeframe/מקור — ראה מוקש 1) ובדוק כמה חלופות.
- A3. אילו מקדמי `ib_ratio` (במקום ניחוש המוצא 0.30/0.50) נותנים התפלגות
  NARROW/MEDIUM/WIDE לא‑מנוונת (לא קריסה לצד אחד כמו 0/44 של S2)?
- A4. יציבות מול דיוק: כמה ימים סווגו אחרת ביחסי מול מוחלט, והאם היחסי תואם
  טוב יותר את סוג‑היום שהתממש בסוף היום?

### B · checkpoints 30/60/90 דק'
- B1. מדוד `ib_range` מתפתח ב‑30/60/90 דק' מ‑09:30 ET (רוחב IB **מתפתח**, לא 3
  IB נפרדים — ב‑30 דק' ה‑IB לא "שלם").
- B2. עד כמה רוחב‑30דק' מנבא את 60/90?
- B3. האם checkpoint נוסף משנה את הצלבת ה‑matrix מול נעילה יחידה ב‑60?

### C · פתיחה 15→30 + CVD
- C1. יציבות סיווג 3 ברים (15דק') מול 6 ברים (30דק') — אחוז התהפכות וכיוון.
- C2. האם CVD קומולטיבי (כיוון+עוצמה) מפריד טוב יותר OPEN_DRIVE (delta חד‑כיווני)
  מ‑OPEN_AUCTION (delta מתחלף), ו‑TEST_DRIVE מ‑REJECTION_REVERSE?
- C3. הצע מודל דו‑שלבי: "מוקדם" 15דק' (ביטחון נמוך) → "מאושר" 30דק', CVD כקלט
  בהחלטה (לא רק בלוג). אמת מול היסטוריה.
- C4. סף gap מוחלט (±2 נק') → יחס ATR? בדוק התפלגות.

### D · day_type מבוסס 30 דק' + ולידציה
- D1. דיוק day_type ב‑30דק' מול הסיווג הסופי (confusion matrix).
- D2. אילו טריגרים מצדיקים שינוי אחרי 30דק' (failed extension, חריגת טווח, CVD
  מתהפך) — מול `_check_reeval` הקיים.
- D3. מעבר ממודל "נעילה מאוחרת" (0.85/13:00) ל"סיווג מוקדם + ולידציה" — משפר
  דיוק או רק זמן?

## מקורות נתונים (אמת שמות בקוד לפני שימוש)
- ברי 5‑דק': `v9_bars_5min`.
- היסטוריית סיווג: `v9_day_type_history` (`consumer.py`).
- CVD: מקור Sierra CDV (COT/AMT). **אמת שם טבלה/שדה בקוד.** אם CVD לא נשמר לכל
  בר → דווח כממצא חוסם לחלק C.
- ATR: אתר היכן מחושב/נשמר (`bar.atr` ב‑`BarInput`); תעד תקופה + timeframe.

## מוקשים שחובה לפתור לפני המלצה
1. **איזה ATR במכנה?** IB=טווח 60דק'. ATR יומי מול ATR 5‑דק' = יחסים שונים
   לחלוטין. הגדר במפורש ותעד.
2. **0.30/0.50 = ניחוש** — כייל מול נתונים.
3. **20↔25** — תעד שהרץ בפועל 25. שינוי ל‑20 = שינוי התנהגות → אישור.
4. **זמינות CVD לכל בר** — אם חסר, חלק C חסום, דווח מיד.
5. **TZ של checkpoints** — 30/60/90 דק' מ‑09:30 **ET**, מפורש.

## תוצרים + שער אישור
תוצר: `docs/reports/S1_CALIBRATION_FINDINGS_<date>.md` עם: טבלאות התפלגות
(A–D) + פקודות + פלט גולמי · מקדמים מוצעים (ib_ratio/gap_ratio) + הצדקה
אמפירית · הגדרת ה‑ATR שנבחר · confusion matrices · רשימת שינויי קוד מוצעים
**כהצעה בלבד, לא ממומשת**.

שום דבר מהבא לא ממומש בלי אישור מפורש של מיכאל: שינוי ספי IB/gap · תיקון
20→25 אם נבחר 20 · CVD כקלט בהחלטה · מעבר ל‑day_type 30 דק'. בטוח בלי מחקר
(אם מיכאל מאשר): יישור ההערה ב‑schemas ל‑25 (תיעוד בלבד).

## סדר ביצוע
A (מנוף גבוה) → B (אותו דאטה) → C (תלוי CVD) → D (מסתמך A–C). אחרי כל חלק:
עצור, הצג ממצאים + ראיות גולמיות, המתן לפני המעבר הבא.
