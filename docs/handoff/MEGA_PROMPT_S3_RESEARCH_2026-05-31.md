# מגה‑פרומפט 2/2 — מחקר כיול S3 (footprint) · נפח/טווח מוחלט → יחסי

> שלח את הפרומפט הזה **שני**, אחרי שמחקר S2 (Prompt 1/2) הסתיים.
> העתק את כל הבלוק שמתחת לקו והדבק בצ'אט/agent חדש עם גישה ל‑repo `mems26_web_git`.

---

אתה agent מחקר במערכת מסחר אוטונומי **MEMS26** (חוזי MES · Sierra Chart →
bridge → FastAPI/SQLite). המשימה: **מחקר לכיול מערכת S3 (footprint)**. שים לב:
S3 מתוכננת היטב ורוב הספים שלה **כבר יחסיים** — לכן המחקר ממוקד וקטן: שני ספים
מוחלטים על ציר נפח/טווח, ואימות שהספירות המבניות אכן צריכות להישאר שלמות. זהו
מחקר/AUDIT — **אסור לשנות קוד מסחר, סכימה, או ספים**. התוצר = דוח עם ממצאים
וראיות. מימוש = שער אישור של מיכאל.

## רקע — מהי S3

S3 = מערכת ה‑footprint (`backend/v9/systems/footprint/`). מזהה אותות
order‑flow: cluster/POC (`detectors.py`), stacked imbalance + absorption +
exhaustion + sweep (`signals/`), ומחשבת confluence → fire.

## מצב נוכחי — רובו יחסי (אומת 2026‑05‑31, קרא לאימות)

**כבר יחסי (תקין — לאימות בלבד, לא לשנות):**
`poc_threshold_pct=30%` · `empty_zones threshold_pct=5%` · `IMB_THRESHOLD=2.5`
(ask/bid) · `imbalance_pct≥250` (=250%) · `EXHAUSTION_FACTOR=0.6` ·
`DIRECTIONAL_BODY_PCT=0.5` · `curr_vol < prev_vol×0.1` · `agg_buy > 1.5×agg_sell`.

**ספים מוחלטים (מוקד המחקר):**

| פרמטר | ערך | קובץ | תפקיד |
|--------|-----|------|-------|
| `MIN_LEVEL_VOL` | 10 חוזים | `signals/stacked_imbalance.py:21` | רצפת נפח לרמה כדי לספור imbalance — **לא יחסי לנפח היום** |
| `range_ticks` | 15.0 טיקים | `detectors.py:102` (`analyze_context`) | רוחב טווח לזיהוי צבירה (accumulation) |

**ספירות מבניות (כנראה צריכות להישאר שלמות — לאמת):**
`STACK_N=3` (רמות imbalance רצופות, `stacked_imbalance.py:19`) · `TREND_BARS=4`
(`exhaustion.py:19`) · `min_acc_bars=5` (`detectors.py:102`) · `jumps_count≥3` ·
`confluence≥4/6` (`footprint_system.py`).

## כללי משחק (Pre‑LIVE — חובה)

1. קרא תחילה `CLAUDE.md` ו‑`.cursor/rules/mems26-pre-live-protocol.mdc`.
2. **אבחן עם נתונים לפני שמציעים** — כל טענה מאומתת בשאילתת DB. לא מהזיכרון.
3. **קרא את הקוד הנוכחי** לפני כל הצעה. אפס edit מהזיכרון.
4. **Source of truth:** ניתוח offline על נתונים שנקלטו בלבד. אסור לסנתז.
5. **Verification quote** (Rule 5): כל "עובד/תקין" מלווה בפקודה + פלט גולמי.
6. **TZ מפורש** (Rule 4).
7. אסור להריץ שירותי MEMS26. סקריפטי מחקר `scripts/research/` בלבד, throwaway.

## שאלות המחקר

1. **`MIN_LEVEL_VOL=10`:** על ≥40 ימי RTH — התפלגות נפח לרמת footprint לפי
   שעת‑יום. האם 10 חוזים קבוע פוסל יותר מדי רמות בשעות נפח נמוך (צהריים),
   ומדי מעט בפתיחה? הצע צורה יחסית: `MIN_LEVEL_VOL = bar_volume × k` או יחס
   לנפח חציוני של הבר. כייל k.
2. **`range_ticks=15.0`:** התפלגות טווח ברים מול 15 טיק (=3.75 נק'). האם זה
   צריך להיות `ATR × k` כמו ב‑S1/S2? לבדוק כמה ימים נחשבים "צבירה" תחת הקבוע
   מול תחת יחסי.
3. **ספירות מבניות:** אמת אמפירית ש‑`STACK_N`, `TREND_BARS`, `min_acc_bars`,
   `confluence` הן ספירות מבניות בלתי‑תלויות בסקאלת‑מחיר/נפח (מספר רמות/ברים)
   ולכן ראוי שיישארו שלמות. אם יש לאחת מהן רגישות לנפח/תנודתיות — דווח.
4. בדיקת רגרסיה רעיונית: שינוי `MIN_LEVEL_VOL` ליחסי משנה כמה stacked‑imbalance
   signals נפלטים → השפעה על confluence → fire rate. לכמת.

## מקורות נתונים (אמת שמות בקוד לפני שימוש)

- footprint לכל בר/רמה: `bars_footprint` / `footprint_markers`
  (`db/models/`). אמת אם נפח per‑level נשמר; אם לא — שאלה 1 חסומה, דווח מיד.
- ברי 5‑דק': `v9_bars_5min`. ATR: אתר מקור, תעד תקופה/timeframe.
- `MES_TICK_SIZE = 0.25`.

## מוקשים

1. **זמינות נפח per‑level** — אם ה‑footprint לא נשמר ברזולוציית רמה ב‑DB, שאלה 1
   חסומה. דווח מיד, אל תניח.
2. **איזה ATR/נפח בסיס** לנרמול — הגדר מפורשות (תקופה/timeframe/מקור).
3. אל תהפוך ספירות מבניות ליחסיות סתם — הצדק כל החלטה.

## תוצרים + שער אישור

תוצר: `docs/reports/S3_CALIBRATION_FINDINGS_<date>.md` — התפלגויות + פקודות +
פלט גולמי · הצעה ל‑`MIN_LEVEL_VOL` ו‑`range_ticks` יחסיים + הצדקה · הכרעה לגבי
הספירות המבניות · שינויי קוד **כהצעה בלבד**.

שום שינוי לא ממומש בלי אישור מיכאל. עדכן ROADMAP §1 + STATUS_BOARD MED עם הממצא
(OPEN line), בלי לשנות קוד.

## סדר ביצוע

`MIN_LEVEL_VOL` (נפח — מוקד) → `range_ticks` → אימות ספירות מבניות.
אחרי כל אחד: עצור, הצג ממצאים + ראיות, המתן.
