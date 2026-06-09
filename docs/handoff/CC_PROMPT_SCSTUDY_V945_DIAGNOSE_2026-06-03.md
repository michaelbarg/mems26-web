# CC PROMPT — sc_study v9.4.5-wc-fix · DIAGNOSE ONLY · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** **אבחון בלבד — אפס שינוי קוד, אפס build, אפס deploy, אפס commit, אפס `git checkout`.** המטרה: לתת ל-Michael 2 עובדות כדי שיחליט לאמץ/לזרוק את שינוי ה-DLL הלא-מקומט.

**קרא קודם (CLAUDE.md §Sierra DLL):** `docs/runbooks/SIERRA_DLL_OPS.md` · `docs/ENVIRONMENT.md` · `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md`.

## רקע — מה שונה (uncommitted בעץ)
`git diff sc_study/` (לא-מקומט):
- `MES_AI_DataExport.cpp:~611-616`: Sidewinder (SWI) — `GetStudyArrayFromChartUsingID(wc, 6, **5**, arr)` → `(wc, 6, **0**, arr)`. הערה: "SG1=ACSIL 0 = SW Top = actual SWI value. Verified 2026-06-02: SG1=SW Top, SG2=Bottom, SG3=Flat, SG4=Spreadsheet".
- `v9_types.h`: גרסה `v9.4.4-chart5` → `v9.4.5-wc-fix`; הערה "bars from chart12 direct, TrendUp SG4, **SWI SG4**".
- `v9_woodies_export.h`: ~165 שורות.
⚠️ **סתירה לפתור:** הקוד ב-cpp משנה SWI ל-**SG0**, אבל ההערה ב-v9_types.h אומרת **SG4**. אחד מהם שגוי.

## עובדה 1 — איזו גרסת DLL רצה עכשיו? (built+deployed או רק בעץ?)
1. קרא את שדה ה-`version` ב-export החי: `/Users/michael/SierraChart_Data/v9_export/*.json` (5min/woodies/וכו'). הדבק את הערך.
2. השווה את `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` (ה-deployed) מול המקור בעץ — זהים (v9.4.5 deployed) או שונים (רץ עדיין v9.4.4)?
3. `docs/runbooks/SIERRA_DLL_OPS.md` — מתי ה-deploy האחרון + איזו גרסה.
- **תוצאה:** running = `v9.4.4` או `v9.4.5`? (קובע אם הנתונים שנאספים כרגע הם מהמקור הישן או החדש).

## עובדה 2 — האם מיפוי ה-SG נכון? (source-of-truth = Sierra)
1. **Sidewinder (Study 6):** איזה subgraph (SG) באמת מחזיק את ערך ה-SWI? אמת מול הגדרות הסטאדי ב-Sierra (לא מההערה — מהסטאדי עצמו). SG0/ACSIL-0 או SG5? פתור את הסתירה SG0-מול-SG4.
2. **השווה ערכים:** קח ערך SWI/TrendUp מה-export מול מה ש-**פאנל Woodies/Sidewinder ב-Sierra מציג** (האמת הנראית) — איזה מיפוי תואם?
3. **`woodies_export.h` (~165 שורות):** סכם **מה** השתנה (TrendUp SG, "bars from chart12 direct") — היקף + האם נוגע ב-CCI/trend שמזינים את S4.
- **תוצאה:** המיפוי החדש נכון/שגוי/לא-ודאי, עם ראיה גולמית.

## דוח (חלק C)
| עובדה | תוצאה | ראיה (raw) |
טבלה + סיכום + **מסגרת החלטה ל-Michael:**
- אם running=v9.4.4 **ו** מיפוי-חדש מאומת-נכון → מומלץ לאמץ (היום, ללא מסחר).
- אם running=v9.4.5 כבר → זה כבר חי; רק לקמט (אחרי אימות) או לזרוק+rebuild-DLL לחזרה.
- אם מיפוי לא-ודאי → אל תאמץ עד אימות.
**אל תבצע את ההחלטה — רק הצג אותה.** sc_study נשאר לא-מקומט ולא-נגוע.
