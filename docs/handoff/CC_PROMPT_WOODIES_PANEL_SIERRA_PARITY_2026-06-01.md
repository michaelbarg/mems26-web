# CC PROMPT — פאנל Woodies בדאשבורד = Sierra chart 12 בזמן אמת · diagnose-first

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW
**חשש (Michael):** טבלת ה-Woodies בעמוד הדאשבורד **לא מעודכנת לפי Sierra chart 12** בזמן אמת. השערה: אולי צריך לסמן/לייצא **עוד שדות מ-chart 12** בסטאדי.
**משמעת:** **diagnose-first — לא לשנות לפני שמיפינו את הפער** · **sc_study = anti-regression (CLAUDE.md §7a + `SIERRA_DLL_OPS.md`)** · אם נדרש שינוי DLL → **strategic-stop: הצג diff לפני build/deploy, אל תשבור chart 12/chart 5** · Rule 5 · אפס שינוי order/risk/sizing.

## הקשר
ה-DLL (`MES_AI_DataExport`) רץ על **chart 12** (Woodies, RTH) ומייצא את מדדי Woodies ל-`woodies_5min.json` → bridge → backend → פאנל Woodies CCI. chart #5 הרציף מייצא OHLC/CVD בלבד (לא מדדי Woodies). הפאנל אמור לשקף את מדדי chart 12 בזמן אמת.

## ⚠️ ראיה מאומתת (צילומי Michael, side-by-side 1/6)
**המחיר בפאנל חי אך מדדי הסטאדי קפואים על 29/5:**
| שדה | דאשבורד (פאנל) | Sierra chart 12 (חי) |
|---|---|---|
| CCI | 74.85 | -103.86 |
| CCIDiff | -52.57 | 54.29 |
| ProjHi / ProjLo | 7653.25 / 7545.50 | 7909.00 / 7310.25 |
| ציר זמן | **5/29 11:50-14:55** | June 1 (חי) |
| מחיר | 7609.62 (חי ✓) | 7610.00 |
**מסקנה מקדימה:** המחיר עודכן (live injection), אבל **כל מדדי ה-Woodies (CCI/CCIDiff/Proj/trend/histogram) תקועים על ה-RTH האחרון (29/5)** — הפאנל מציג fallback "LAST SESSION" לנתוני הסטאדי, בעוד Sierra מחשב אותם חי. סביר: ה-export/ingestion של מדדי woodies הוא RTH-only/stale ב-overnight, או שהפאנל קורא רשומת study ישנה. **אמת זאת ב-Phase A.**

## Phase A · אבחון (READ-ONLY, ראיות גולמיות)
1. **מפה את מקור הפאנל:** איזה endpoint/שדות הפאנל מציג → איזה קובץ export (`woodies_5min.json`?) → אילו שדות-סטאדי. **רשום את השדות שהפאנל מציג מול השדות שמיוצאים בפועל** — מה חסר.
2. **טריות בזמן אמת:** האם `woodies_5min.json` (chart 12) מתעדכן רציף ב-RTH? בדוק mtime + האם הערכים **משתנים** בין pushes, או **frozen** (frozen-tail / DLL mapIdx clamp — ~13 ברים אחרונים עם מדדים זהים). זה החוסם-LIVE הפתוח.
3. **השוואה מול Sierra (ground-truth):** ⚠️ CC לא רואה את Sierra — **Michael יספק את ערכי chart 12** (CCI-14/TCCI/SWI/CZI/LSMA/EMA/trend_state/וכו') לרגע נתון, ו-CC ישווה לערכי הפאנל/ה-export. סמן כל שדה שלא תואם או חסר.
4. **בלי ערבוב מקורות:** ודא שהפאנל קורא מדדי-סטאדי מ-chart 12 (לא בטעות מחיר מ-chart #5 שמערבב). 

## Phase B · תיקון (אחרי אבחון)
- **אם שדות חסרים ב-export:** הוסף אותם ל-export של chart 12 ב-DLL (runbook §7a · strategic-stop: diff לפני deploy · אל תשבור exports קיימים).
- **אם frozen-tail:** ודא ש-current_bar override / staleness-fix פעיל; אמת ב-RTH ש-CCI משתנה על ברים שונים.
- **אם backend/frontend קורא מקור שגוי/stale:** תקן את המיפוי.
- ודא **בזמן אמת ב-RTH:** הפאנל משקף את chart 12 חי (CCI/trend וכו' זזים עם הברים).

## פלט
`docs/reports/WOODIES_PANEL_SIERRA_PARITY_2026-06-01.md`: מיפוי שדות (פאנל מול export מול Sierra) · ממצא frozen/חסר/מקור-שגוי · diff תיקון (אם DLL — diff לאישור Michael לפני deploy) · אימות real-time ב-RTH. עדכון STATUS_BOARD.

**שערים:** diagnose-first — דווח את מפת השדות והפער לפני תיקון. שינוי DLL = strategic-stop + diff + runbook + לא לשבור chart 12/#5. השוואת ground-truth דורשת ערכי Sierra מ-Michael. אימות real-time סופי ב-RTH (16:30).
