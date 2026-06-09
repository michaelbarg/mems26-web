# מגה‑פרומפט 1/2 — מחקר כיול S2 (five_min) · ספים מוחלטים → יחסיים

> שלח את הפרומפט הזה ראשון. אחרי שהמחקר הזה מסתיים, שלח את Prompt 2/2 (S3).
> העתק את כל הבלוק שמתחת לקו והדבק בצ'אט/agent חדש עם גישה ל‑repo `mems26_web_git`.

---

אתה agent מחקר במערכת מסחר אוטונומי **MEMS26** (חוזי MES · Sierra Chart →
bridge → FastAPI/SQLite). המשימה: **מחקר לכיול מערכת S2 (five_min)** — להמיר את
ספי הנקודות/טיקים המוחלטים בזיהוי התבניות וב‑stops לספים **יחסיים** (ATR או
יחס מתאים). זהו מחקר/AUDIT — **אסור לשנות קוד מסחר, סכימה, או ספים**. התוצר הוא
דוח עם ממצאים, מקדמים מוצעים, וראיות גולמיות. מימוש = שער אישור של מיכאל.

## רקע — מהי S2

S2 = מערכת ה‑five_min (`backend/v9/systems/five_min/`). מזהה setups של 5 דק':
תבניות Initiative/Reactive (`five_min_system.py`) ותבניות צ'ארט (`patterns/`:
double bottom/top, head & shoulders, flags), מחשבת quality tier + sizing
(`quality_tier.py`), stop (`adaptive_stop.py`), וקרבה ל‑S/R (`sr_proximity.py`),
ואז פולטת `T1Setup` דרך `setup_emitter.py` ל‑gateway (SHADOW).

## הבעיה — ספים מוחלטים תלויי סקאלת‑מחיר

עדות קיימת לכשל הדפוס: ספי ה‑Initiative expansion `[1.5–1.75 נק']` נתנו
**0/44 ברים** ברטיח כי הטווח הממוצע היה ~6 נק' (פי 4). אותו מנגנון אורב בכל סף
נקודות/טיקים קבוע — כשהתנודתיות (ATR) זזה, אותו ערך מוחלט הופך "קטן/גדול מדי".

ספים מוחלטים שאותרו (אומתו 2026‑05‑31 — קרא לאימות):

| פרמטר | ערך | קובץ | תפקיד |
|--------|-----|------|-------|
| `EXPANSION_MIN_PT` / `MAX_PT` | 1.5 / 1.75 נק' | `five_min_system.py:31-32` | טווח בר Initiative (= ROADMAP 1.16) |
| `POC_RETURN_TOLERANCE_PT` | 0.5 נק' | `five_min_system.py:33` | חזרת bar‑2 ל‑POC |
| `PROXIMITY_PT` | 2.0 נק' | `quality_tier.py:22` | קרבה לרמה → quality tier |
| `DEFAULT_PROXIMITY_TICKS` | 5 (=1.25 נק') | `sr_proximity.py:17` | קרבה ל‑S/R |
| `FLOOR_TICKS` | 4 (=1.0 נק') | `adaptive_stop.py:20` | רצפת stop |
| `POLE_MIN_HEIGHT_TICKS` | 16 (=4 נק') | `patterns/flags.py:11,36` | גובה מוט מינ' (Flag) |
| `HEAD_MIN_EXT_TICKS` | 2 (=0.5 נק') | `patterns/head_shoulders.py:11,30` | בליטת ראש מינ' |
| tolerance "שפל דומה" | `TICK_SIZE×2` = 0.5 נק' | `patterns/double_bt.py:87,104` | סובלנות שיא/שפל |

**כבר יחסי (לא לגעת — לאימות בלבד):** אחוזי סימטריה/ריטרייס
(`SHOULDER_SYM_PCT 5%`, `TROUGH_SYM_PCT 3%`, `NECKLINE_MIN_RISE_PCT 10%`,
`POLE_DIRECTIONAL_PCT 60%`, `FLAG_MAX_RETRACE_PCT 50%`) ויחסי נפח
(`DROP_THRESHOLD_PCT 10%`, `LOOKBACK_MAX_VOL_RATIO 0.6`, `BELLY_DOMINANCE_RATIO 1.5`).

## כללי משחק (Pre‑LIVE — חובה)

1. קרא תחילה `CLAUDE.md` ו‑`.cursor/rules/mems26-pre-live-protocol.mdc`.
2. **אבחן עם נתונים לפני שמציעים** — כל טענה מספרית מאומתת בשאילתת DB / bar‑math
   על נתונים גולמיים. לא מהזיכרון, לא מהמפרט.
3. **קרא את הקוד הנוכחי** לפני כל הצעה. אפס edit מהזיכרון.
4. **Source of truth:** ניתוח offline על ברים שנקלטו בלבד. אסור לסנתז נתונים.
5. **Verification quote** (Rule 5): כל "עובד/תקין" מלווה בפקודה + פלט גולמי.
6. **TZ מפורש** (Rule 4): כל זמן/חלון נושא TZ מפורש (ET/UTC).
7. אסור להריץ שירותי MEMS26. סקריפטי מחקר תחת `scripts/research/` בלבד,
   throwaway, לא מיובאים ע"י backend.

## שאלות המחקר

1. על ≥40 ימי RTH: התפלגות טווח בר 5‑דק' (`high-low`) בנק' — avg/median/רבעונים,
   ופילוח לפי שעת‑יום (פתיחה תנודתית מול צהריים שקטים).
2. לכל סף מהטבלה: מהו אחוז ההזדמנויות שעובר/נכשל תחת הערך הנוכחי? היכן הסף
   "חונק" (כמו 0/44 של EXPANSION)?
3. המרה ליחסי: לכל סף, הצע צורה יחסית — `EXPANSION = ATR×k`, `PROXIMITY = ATR×k`,
   `STOP_FLOOR = ATR×k` וכו'. **הגדר מפורשות איזה ATR** (תקופה/timeframe/מקור —
   ראה מוקש 1). כייל את k מול ההתפלגות כך שתהיה לא‑מנוונת.
4. תבניות הצ'ארט (`patterns/`): האם הספים המוחלטים (`POLE_MIN_HEIGHT_TICKS`,
   `HEAD_MIN_EXT_TICKS`, `double_bt tolerance`) צריכים להיות יחסיים ל‑ATR, או
   שלהם הצדקה מבנית להישאר בטיקים? נמק לכל אחד בנפרד.
5. אינטראקציה: שינוי `EXPANSION` יחסי משנה כמה setups נפלטים → השפעה על
   `quality_tier`/sizing? לכמת.

## מקורות נתונים (אמת שמות בקוד לפני שימוש)

- ברי 5‑דק': `v9_bars_5min`.
- setups היסטוריים: `v9_five_min_setups` (`db/models/five_min_setups.py`).
- ATR: אתר היכן מחושב/נשמר; תעד תקופה + timeframe.
- `MES_TICK_SIZE = 0.25` (`five_min/constants.py`).

## מוקשים שחובה לפתור

1. **איזה ATR?** טווח בר 5‑דק' מול ATR יומי מול ATR 5‑דק' = יחסים שונים לחלוטין.
   הגדר במפורש ותעד. (זה אי‑בהירות מסוג שכלל TZ אוסר.)
2. **k = ניחוש** עד שיכויל מול נתונים.
3. **רצפת stop** (`FLOOR_TICKS`) — להמרה ליחסי יש סיכון risk: stop יחסי גדול
   מדי ביום תנודתי → סיכון $ גבוה. לבדוק מול תקרת ה‑risk ($250/יום, 2 חוזים).
4. **תבניות מבניות מול תלויות‑סקאלה** — להפריד: אחוז (כבר יחסי) מול נקודות.

## תוצרים + שער אישור

תוצר: `docs/reports/S2_CALIBRATION_FINDINGS_<date>.md` — טבלאות התפלגות + פקודות
+ פלט גולמי · מקדמי k מוצעים לכל סף + הצדקה אמפירית · הגדרת ה‑ATR שנבחר ·
רשימת שינויי קוד מוצעים **כהצעה בלבד, לא ממומשת**.

שום שינוי בספים אינו ממומש בלי אישור מפורש של מיכאל (לוגיקת‑מסחר). עדכן את
ROADMAP §1 (1.16) ו‑STATUS_BOARD MED עם הממצא + ההצעה (OPEN line), בלי לשנות קוד.

## סדר ביצוע

EXPANSION/POC (1.16 — המנוף) → PROXIMITY/SR → STOP floor → תבניות צ'ארט.
אחרי כל קבוצה: עצור, הצג ממצאים + ראיות, המתן לאישור לפני המעבר.
