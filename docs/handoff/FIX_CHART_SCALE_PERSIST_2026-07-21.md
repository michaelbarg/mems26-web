# תיקון-תצוגה: ה-scale בצ'ארט מתאפס למייקל בכל רענון (מייקל 2026-07-21 ~19:05)

**הבקשה:** "אני משחק עם scale וזה חוזר כל פעם" — שהכיוון-הידני יישמר.

## השורש (אומת בקוד, read-only)
`frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` (הצ'ארט הפעיל, lightweight-charts):
1. **:622-637** — סוף `loadBars` כופה `setVisibleRange(60-הברים-האחרונים)` (או `fitContent`) **בכל ריצה** —
   דורס zoom/pan ידני בכל טעינה/רענון/החלפת-TF.
2. **:431** — `priceScale().applyOptions(...)` על עדכוני-דאטה — אם מדליק `autoScale` מחדש, דורס Y-scale ידני.
3. **:952** — `scrollToRealTime()` על בר-חדש — דורס pan ידני.

## התיקון (display-only, אפס-לוגיקת-מסחר)
- `userAdjustedRef` — נדלק על אינטראקציה ידנית (wheel / Ctrl+wheel / drag על הצ'ארט; lightweight-charts:
  `subscribeVisibleLogicalRangeChange` תוך הבחנה בין שינוי-user לשינוי-programmatic, או מאזיני-DOM).
- כשהוא דלוק: **מדלגים** על `setVisibleRange`/`fitContent`/`scrollToRealTime`/re-`autoScale` בעדכוני-דאטה —
  דאטה חדשה נכנסת, הענן לא זז.
- כפתור **"↺ Auto"** (קיים כדוגמה ב-ChartV5a:794) / double-click — מכבה את הדגל וחוזר להתנהגות-אוטו.
- **persist** ל-`localStorage` (`chart_v5b_view`): zoom/visible-range פר-TF — שורד גם ריענון-דף וגם remount.
- החלפת-TF מפורשת ע"י המשתמש = איפוס-מותר (התנהגות צפויה).

## ביצוע
הלילה אחרי 23:00 (לא נוגעים במסך חי תוך-מסחר). מבצע: cc או cursor (לצרף לחבילת-הלילה). טסט: סמוך-רענון —
סימולציית loadBars חוזרת עם userAdjusted=true → הטווח לא משתנה; Auto מחזיר. חוק-5: לפני/אחרי בדפדפן.
