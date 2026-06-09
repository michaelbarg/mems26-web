# CC Agent — audit כל תבניות S2 (10) + S4 (9): מה חסר לכל אחת כדי לירות

הרץ **agent** שמפיק, לכל 19 התבניות, **מה בדיוק חוסם אותה מלהידרך/לירות** — ומסווג
את החוסם ל-3 סוגים. read-only. פלט מסודר ל-`docs/reports/PATTERN_ARMING_AUDIT_2026-06-08.md`.

## מקור-נתונים
`curl -s localhost:8000/api/v9/build/pattern-status` — לכל system (`five_min`, `woodies`)
שדה `patterns[]` עם `name/status/armed/blocked_reason`. בנוסף readiness.checks + global_gates.

## הפק טבלה — שורה לכל תבנית, עמודות:
| מערכת | תבנית | כיוון | status | מה חסר (blocked_reason הגולמי) | **סיווג-החוסם** | day_type נוכחי |
סיווג-החוסם (חובה — שלוש קטגוריות):
- **🟢 נכון-דוקטרינה** — `Auth Table SKIP × <day_type>` (תבנית לא מתאימה ליום הזה — תקין, לא באג).
- **🔴 חוסם-נתונים** — `Missing: data.X` / stream dead (choppiness_ok, tick_reversal_15, tpo, footprint).
  ציין **על איזה stream/שדה** היא תלויה ומה מצבו (fresh/dead).
- **🟡 ממתין-setup** — armed-תנאים קיימים אבל אין trigger כרגע (תקין, סתם אין setup).

## בנוסף — לכל תבנית, מהקוד (לא רק מה-API):
קרא את ה-detector של כל תבנית (`five_min/patterns/*.py`, `woodies/patterns/*.py`) וציין
את **רשימת התנאים לדריכה** (gates) + מאיזה stream/שדה כל תנאי בא — כך שלכל תבנית רואים
את מסלול-הירי המלא ומה בדיוק חסר. השתמש ב-SYSTEM_INDEX/_INDEX לאיתור (חוק #1).

## דגשים ידועים (להצליב, לא להניח)
- היום day_type=**Trend_Normal** → REV (H&S/Double/VEGAS/GHOST/FAMIR/HFE) צפויים SKIP = 🟢 תקין.
- ‏Reactive/Initiative חסומים על `Missing: data.choppiness_ok` → ברר מאיפה choppiness_ok
  נגזר (chop_score/layer0) ועל איזה stream הוא תלוי (tick_reversal_15? tpo?). זה החוסם-המרכזי.
- footprint מנוטרל (`S3_MUTE=1`, Michael "עד הודעה חדשה") — ודא שאף תבנית-S2/S4 לא תלויה
  ב-footprint לדריכה; אם כן — זה חיווט-לתיקון (choppiness לא צריך להיות תלוי בערוץ-מושתק).

## פלט סופי
טבלת 19 השורות + סיכום: כמה 🟢/🔴/🟡, ומה **שני-שלושה התיקונים** שיפתחו הכי הרבה
תבניות (כנראה: tick_reversal_15+tpo freshness → choppiness_ok). Cowork קורא ומצליב מול
`MEMS26_MASTER_TRADE_SPEC_ONE_TABLE.xlsx`.
