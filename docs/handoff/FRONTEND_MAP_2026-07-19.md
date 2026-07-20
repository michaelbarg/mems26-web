# W7 — Frontend Map (עדכון מחיקות · 2026-07-20)

**בעלים:** cursor-agent · **פסיקת-מייקל:** מחיקת יתומים מאושרת (Sounds / DashboardLayout / tabs-מתים)

## נמחק 2026-07-20 (Michael approved)
| קבוצה | קבצים |
|---|---|
| Sounds | `sounds/SoundManager.ts` · `SoundProvider.tsx` · תיקייה |
| tabs מתים | `DataTab` · `OrdersTab` · `PredActualTab` · `SignalTab` · `StatsTab` · `TradeTab` |
| DashboardLayout + שרשרת | `layout/DashboardLayout.tsx` · `panels/SystemPanelsBar.tsx` · `System1..6Panel.tsx` · `SystemPanelWrapper.tsx` |

**אימות אחרי כל שלב:** `npx tsc --noEmit` — אותם 4 שגיאות-קדם (לא חדשות) · `curl :3000/` `/board` `/build` → **200** · title `MEMS26 V9 Dashboard`.

## נשאר DEFER (לא נמחק)
pills · plan lenses · CumulativeDeltaPane · StreamHealthPanel · StatusDot · TradeChart/TradeReviewPanel · VolumeDragHandle

## חיים (ללא שינוי)
`V9Dashboard` · strips · ChartV5b · BuildTree · DirectionStrip · Switcher · SidePanel Plan (AllPatternsPlan)

## לא-mounted (מועמד-מחיקה — פסיקת מייקל)
`LeftTabs` + 9 sidebar tabs · ChartV5a/ChartArea · Volume* · StreamHealthPanel · old *Pill · TradeReviewPanel · `fetchDayTypeV9`

## אינדקס-סמנטי מלא
→ `docs/handoff/FRONTEND_INDEX.md` (רכיב→endpoint+שדה · טבלת blocked_by→reason · פרוטוקול-עדכון)

## לתקן (לא מחיקה)
`SystemsTab` Consensus → `useDirectionNow` (כמו BuildTree T12) — רק אם LeftTabs יוחזר
