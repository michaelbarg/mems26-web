# 🧭 GAP REGISTER — פנקס-פערים משותף (S1 · S2 · S4)

**פסיקת-מייקל 2026-07-19:** *"צריך מקום שכל הסוכנים יכולים להוסיף פערים ולבדוק אותם לפני
שהם נקבעים כבעיה."*

**זה המקום.** קובץ אחד, git-tracked. כל סוכן (cowork-dev · cc-macbook · cc-imac · cursor)
**מוסיף** פער חשוד כאן, ו**אף פער לא הופך ל"בעיה" עד שהוא אומת בקוד/דאטה (חוק-5).**
נבנה כי שלושה "פערים" כבר התבררו כ**פנטום** אחרי אימות (ה"פספוסים" של entry_not_confirmed =
מחיר-מעופש · "CVD לא מיוצא" = מפתח-JSON שגוי) — הפנקס הזה מונע לרדוף פנטומים.

## מחזור-החיים של פער (חובה)
```
🔵 SUSPECTED  → מישהו חושד. שורה עם system + תיאור + מצביע-ראיה + מי-מצא + תאריך.
🟡 VERIFYING  → מישהו בודק בקוד/דאטה עכשיו.
🟢 CONFIRMED  → אומת אמיתי. חייב שורת-ראיה (פקודה+פלט או file:line). רק אז הופך לפריט-עבודה.
⚪ PHANTOM    → נבדק ואינו בעיה. חייב שורת-ראיה שמפריכה. נשאר בפנקס (כדי לא לחזור אליו).
🔧 FIXED      → תוקן. שורת-ראיה = קומיט + אימות.
```

## 3 חוקי-הברזל
1. **אסור לקפוץ ל-🟢 CONFIRMED בלי שורת-ראיה** (פקודה+פלט גולמי, או `file:line` שמוכיח). הצהרה ≠ ראיה.
2. **פנטום נשאר בפנקס** עם ההפרכה — לא נמחק (אחרת מישהו יוסיף אותו שוב).
3. **חשד = בסדר גמור.** עדיף לרשום 10 חשדות ש-3 מהם פנטום, מאשר לפספס אחד אמיתי. אבל אל תטפל
   בחשד עד שאומת.

## איך מוסיפים פער (העתק שורה)
`| G-NN | S? | <תיאור בשורה> | 🔵 | <file:line או מסמך> | <מי-מצא> | 2026-07-NN |`

---

## 📋 הפנקס החי

| # | מע' | פער | סטטוס | ראיה / הפרכה | בעלים | תאריך |
|---|---|---|---|---|---|---|
| G-01 | S4 | Paint-lag: `current_bar` מנותב ל-S4 עם `trend_state` גולמי (בלי `_trend_from_cci`) → TT/GB100/ZLR-v2 עיוורים לצבע בראלי | 🟢 **CONFIRMED** | אומת ע"י cowork (B1): `bars.py:1087` בר-סגור מחיל `_trend_from_cci`; `bars.py:1153` current_bar **גולמי**. תיקון הוצע (להחיל גם על current_bar) — **לא בוצע, משטח-סיכון** | **מייקל**(פסיקה)→cc-macbook | 07-19 |
| G-02 | S2 | S2 יורה מאוחר: 7 ברים מינ' (B1-B4+3 רקע) + FHB + avg20-נפח מורעל בגלובקס-דק | 🟢 **CONFIRMED** | אומת ע"י cowork (B2): `MIN_BARS_REQUIRED=7` (`five_min_system.py:34`); avg20 (`:658-659`) + `S2_VSA_VOLUME=1` **חי** → נתיב-מורעל פעיל | ממתין-גישה (מייקל) | 07-19 |
| G-03 | S4/S2 | `FIXED_CONTRACTS_4=1` מתעלם מפסק REDUCED של הפלייבוק → "מופחת" לא ממומש בגודל | 🟢 **CONFIRMED (by-design)** | `trading_gateway.py:633` בודק רק `_pb.allow` (בוליאני), לא ספירת-חוזים; FIXED_4 כופה 4. **תוצאה של פסיקת-4-חוזים** — לא באג | **מייקל**: האם REDUCED יקטין גודל? | 07-19 |
| G-04 | S2 | A5 `OFA_Initiative ≠ INITIATIVE_LONG` → INITIATIVE over-fire על Normal | 🔧 **FIXED** | פסיקה-4: `S2_AUTH_MATRIX_SINGLE_SOURCE_V1=1`, auth_matrix בוטל, 14 טסטים, אפס-שינוי-התנהגות. commit 504d948d | — | 07-19 |
| G-05 | S2 | day-type מעופש על **שער-הזיהוי** של chart-patterns (`self.current_day_type`) בעוד נתיב-הפליטה מודע-override | 🟡 **VERIFYING** | cowork מצא: נתיב-פליטה/סיזינג **כן** מודע (`get_live_day_type` `:1332,:1432`), אבל שער-כשירות-התבניות (`:1139,:1180-1195`) קורא `self.current_day_type` שמוזרם מ-`v9_day_type_state`/event-bus (`:280,:426`). **נותר לאמת:** האם override מגיע לשדה הזה. אם לא → chart-patterns נגייטים על תווית-מעופשת | cowork-dev | 07-19 |
| G-06 | S4 | A6 S4 day-type בלי override → T2/runner שגוי | 🔧 **FIXED** | פסיקה-5: `S4_OVERRIDE_AWARE_V1=1`, S4 קורא `get_live_day_type` ראשון, 5 טסטים. commit 634983c1 | — | 07-19 |
| G-07 | S4 | entry_not_confirmed "פספס" GHOST/FAMIR 07-17 | ⚪ **PHANTOM** | ה"פספוסים" = מחיר-מעופש (GHOST @7534.5 = מחיר מלפני שעה) מזיהום `v9_bars_5min`. תוצאה אמיתית: חסימה-1, gate-right. השער **נשאר** (פסיקה-2). הזיהום עצמו CONFIRMED+FIXED (ראה G-09) | — | 07-19 |
| G-08 | S2 | CONFLUENCE FULL בפלייבוק אבל flag OFF → תא-ירוק בלי ירי-חי | ⚪ **STALE** | `CONFLUENCE_RI_ZLR_LIVE=1` **חי ב-.env** → CONFLUENCE יורה חי. הפער התייחס למצב-ישן | — | 07-19 |
| G-09 | data | `v9_bars_5min` מזוהם בברי-מחיר-מעופש → ATR/סיווג-יום מנופחים | 🔧 **FIXED** | 2 שכבות: שומר-קליטה חוצה-מקורות (>15נק' מ-woodies→דחייה) + הידוק-TS-HOUR. אומת על 07-17: תפס 2/2 רפאים. commit ac8bb9a7 | — | 07-18 |
| G-10 | S1 | Sierra Study ID:1 bar-persistence Input — האם באמת 6? לא בריפו | 🔵 **SUSPECTED** | לא-מוכרע מהקוד (Bible U1). דורש צילום-Inputs מסיירה / מדידה-חיה | **מייקל** (צילום) | 07-19 |
| G-11 | S1/S2/S4 | מספרי `audit_pattern_miss` 15/16/17 — כמה swings נחסמו בפועל פר-שער | 🔵 **SUSPECTED** | לא-מוכרע (Bible U2). `audit_pattern_miss.py` צריך DB חי — רק על ה-MacBook | cc-macbook | 07-19 |
| G-12 | S2 | BE/runner wiring מ-`daytype_style.stop_be_early` — לא עוקב עד trade_manager בכל נתיב | 🔵 **SUSPECTED** | לא-מוכרע (Bible U4). דורש מעקב-קוד מ-YAML→manager | ממתין-בעלים | 07-19 |
| G-13 | S1 | האם YELLOW בכלל מגיע מ-DLL החי? (נעילת-YELLOW עלולה להיות inert) | 🔵 **SUSPECTED** | לא-מוכרע (Bible U7). דורש לוג-חי של trend_state | cc-macbook | 07-19 |

**נסגרו/הופרכו מיידית (07-19, אימות-cowork):** ה-SPEC-flags **כולם דלוקים** (`ZLR_SPEC_V2=1 ·
VEGAS_SPEC_V2=1 · S2_VSA_VOLUME=1 · DIRECTION_CONTEXT=1 · DAYTYPE_LOCATION_GATE=1`) → Bible-U3
מוכרע, ו-`audit_pattern_miss` (שמניח ON) תואם-מציאות.

## סיכום-מצב (07-19)
- **🟢 CONFIRMED פתוחים (דורשים החלטה/עבודה):** G-01 (paint-lag, פסיקה), G-02 (S2-late, גישה),
  G-03 (REDUCED-vs-FIXED4, פסיקה), G-05 (S2 stale-daytype, בבדיקה).
- **🔧 FIXED:** G-04, G-06, G-09.
- **⚪ PHANTOM/STALE:** G-07, G-08 (נשארים בפנקס עם ההפרכה).
- **🔵 SUSPECTED (ממתינים-אימות):** G-10..G-13.

**הכלל למייקל:** רק 🟢 הם "בעיות אמיתיות". G-04/06/09 כבר נסגרו. הנותרים ל-🟢 = 4, ומהם רק
2 דורשים פסיקה שלך (G-01 paint-fix, G-03 REDUCED-size).
