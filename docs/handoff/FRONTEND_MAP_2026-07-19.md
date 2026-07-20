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
`V9Dashboard` · strips · ChartV5b · LeftTabs (Trader/Market/Setups/Systems/Day/Decisions/Patterns/Performance/Predictions) · BuildTree · DirectionStrip

## לתקן (לא מחיקה)
`SystemsTab` Consensus → `useDirectionNow` (כמו BuildTree T12)
