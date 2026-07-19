# W7 — Frontend Map (2026-07-19)

**בעלים:** cursor-agent · `python3 scripts/gen_index.py` · **מחיקה = פסיקת-מייקל בלבד**

## חוק-5
```
$ python3 scripts/gen_index.py
{"files": 849, "dirs_indexed": 117, "orphans": 46}
```
Scope כולל `frontend/v9/src` · 179 קבצי-FE · כל תיקייה עם `_INDEX.md` מרוענן (2026-07-19).  
אגדה ב-`SYSTEM_INDEX.md`: ✅N = importers · ⚠️ orphan? = 0 importers (חשוד — לא למחוק עיוור).

## מפת-על (חי vs יתום vs מת-לוגי)

### חיים בדשבורד האמיתי (`V9Dashboard` — לא `DashboardLayout`)
| אזור | רכיבים מרכזיים | מטרה |
|---|---|---|
| Top / strips | `TopBar` · `KeyLevelsStrip` · `DirectionStrip` · `Layer0Strip` · `TradeHistoryStrip` | סטטוס · רמות · כיוון-שער · היסטוריה |
| Chart | `ChartV5b` + woodies overlays | מחיר + CCI |
| Side | `SidePanel` / lenses | פירוט מערכת |
| Build / trades | `BuildStatusTab` · `BuildTreeView` (/build) · `TradeReviewTab` | מוכנות · סקירת עסקאות |
| Controls | `SystemControlPanel` · banners | בקרה / התראות |
| Day-type tools | `DayTypeLabelTab` · `DayTypeConditionsTable` | תיוג / תנאים (live-aware אחרי T14) |

### מת-מסלול (קוד קיים, לא מורכב ב-V9Dashboard)
| רכיב | Usage index | מצב | הערה |
|---|---|---|---|
| `DashboardLayout.tsx` | ⚠️ orphan? | **מת-מסלול** | V9Dashboard מחליף אותו במפורש (הערה בקוד 07-09/07-10) |
| `SystemPanelsBar` + `System1..6Panel` | ✅ דרך DashboardLayout בלבד | **מת-מסלול** | System4Panel תוקן T14 אבל הפאנל-בר עצמו לא מוצג |
| `woodiesBars` / `setWoodiesBars` ב-`marketStore` | נשאר | **מת-שדה** | אין קורא אחרי T14 |

### יתומים מהאינדקס (FE בלבד — 26)
*חשודים למחיקה/DEFER — לא נמחקו.*

| קובץ | הצעה |
|---|---|
| `sounds/SoundManager.ts` · `SoundProvider.tsx` | **מועמד-מחיקה** — "Sound removed per Michael 2026-05-22" |
| `systems/*Pill.tsx` (DayType/FiveMin/Footprint/Woodies) | **DEFER** — הוחלפו ב-Switcher; לאמת שאין import דינמי |
| `sidebar/tabs/{Data,Orders,PredActual,Signal,Stats,Trade}Tab.tsx` | **מועמד-מחיקה / DEFER** — placeholders / לא ב-LeftTabs החי |
| `sidepanel/lens/plan/*Plan.tsx` (6) | **DEFER** — plan lenses; לבדוק SidePanel registry |
| `chart/TimeframeSelector.tsx` · `v5b/CumulativeDeltaPane.tsx` | **DEFER** — ייתכן backup/feature-flag |
| `health/StreamHealthPanel.tsx` | **DEFER** — ייתכן הוסר מ-dashboard |
| `atoms/StatusDot.tsx` | **DEFER** |
| `trades/TradeChart.tsx` · `TradeReviewPanel.tsx` | **DEFER** — TradeReviewTab עשוי להחליף |
| `volume/VolumeDragHandle.tsx` | **DEFER** |
| `layout/DashboardLayout.tsx` | **מועמד-מחיקה** אחרי אימות שאין route ישן |

### לא-עדכניים (חיים אבל לוגיקה מיושנת מול אודיט-UI)
| רכיב | בעיה | סטטוס |
|---|---|---|
| `SystemsTab` Consensus | הצבעת LONG/SHORT מסיגנלים ≠ `direction_now` | ✅ מורכב ב-LeftTabs · **לעדכן כמו BuildTree T12** (לא למחוק) |
| `DayTypeLabelTab` | עדיין `classify_replay` ללא overlay live | 🟡 לסמן display≠gate או live |
| `System4Panel` | תוקן T14 | 🟢 קוד · 🔴 עדיין לא נראה (מת-מסלול DashboardLayout) |

## רשימת מועמדים לפסיקה (מייקל)

**למחיקה (אחרי אישור):**
1. `SoundManager.ts` / `SoundProvider.tsx` (כבר מסומנים removed)
2. `DashboardLayout.tsx` + שרשרת `SystemPanelsBar` **או** לחבר מחדש ל-V9Dashboard (עדיף לחבר אם רוצים את פאנלי S1–S6)
3. Sidebar tabs יתומים: Orders/PredActual/Signal/Stats/Trade/Data (אם LeftTabs לא מפנה אליהם)

**לא למחוק בלי בדיקה נוספת:** plan lenses · pills · CumulativeDeltaPane · StreamHealthPanel.

**לתקן (לא מחיקה):** SystemsTab consensus → `useDirectionNow` · אופציונלי: להרכיב SystemPanelsBar ב-V9Dashboard אם רוצים את תיקון-T14 על המסך.

## קבצים שנכתבו/רוענן
- כל `frontend/v9/src/**/_INDEX.md` + `SYSTEM_INDEX.md` (מ-`gen_index.py`)
- מסמך זה: `FRONTEND_MAP_2026-07-19.md`
