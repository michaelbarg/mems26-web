# CC — תיקון 4 console-errors ב-Build Status (frontend) · 2026-06-05

נוצרו ב-visual rewrite (`5bb2e4c`). אזהרות-React: ערבוב shorthand↔non-shorthand באותו
inline-style → "styling bugs". frontend בלבד, smallest correct change. VERIFY בקונסול נקי.

## הבאג
```
Updating a style property during rerender (border) when a conflicting property is set
(borderBottom) ... don't mix shorthand and non-shorthand properties for the same value.
```
מקור ראשון: `BuildTreeView.tsx:1866-1867` — ה-`<div>` עם `borderBottom` מכיל ילדים עם
`style={tabStyle(...)}` שמחזיר `border` (shorthand) — ה-shorthand דורס/מתנגש ל-borderBottom.

## מה לעשות
1. אתר את **כל 4 המופעים** (Michael ספר 4) של ערבוב `border` (shorthand) עם
   `borderTop/Bottom/Left/Right` (non-shorthand) באותו אלמנט/style-object —
   ב-`BuildTreeView.tsx` (`tabStyle` ועוד) ובכל רכיבי build_status שנגעת בהם ב-rewrite.
2. **תקן: השתמש ב-non-shorthand בלבד** לאותו אלמנט (`borderTop/borderBottom/borderLeft/borderRight`
   + `borderColor/Width/Style`), **או** shorthand בלבד — לא ערבוב. (בפרט `tabStyle` יחזיר
   `borderBottom` במקום `border` כשיש active-tab underline.)
3. אל תשנה את המראה — רק את אופן-הגדרת-ה-style (הפיקסל זהה).

## VERIFY
- פתח `/build` + dashboard-tab, **console נקי** (0 אזהרות "shorthand/non-shorthand") — צילום-קונסול.
- העמוד נראה **זהה** (לפני/אחרי) — צילום side-by-side.
- `grep -n "border:" frontend/v9/src/v9/components/build_tree/BuildTreeView.tsx` — אין ערבוב עם borderBottom באותו object.
- NOT-DONE: אם נשארו אזהרות-React אחרות (לא border) — סמן.
