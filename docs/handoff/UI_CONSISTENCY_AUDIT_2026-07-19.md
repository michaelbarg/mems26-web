# UI Consistency Audit — האם התצוגה משקפת את המנוע? (טרנד · סוג-יום · כיוון)

**פסיקת-מייקל 2026-07-19** · מפרט: `CURSOR_UI_CONSISTENCY_AUDIT_2026-07-19.md`  
**מבצע: cursor-agent (+ fan-out explore)** · **קריאה-בלבד — אין שינוי-קוד.**  
**מאמת: cowork-dev (חוק-5).** מרחיב **GAP G-16** (לא רק סוג-יום — גם טרנד-חי + כיוון).

## SoT להשוואה (מנוע / שער)
| אות | מה שהמנוע/השער רואים | ראיה |
|---|---|---|
| **טרנד-חי (אחרי G1)** | `_trend_from_cci` על `current_bar` → רק ל-S4 (`_route_bar`); **לא** נכתב ל-DB | `bars.py:1087` (סגור→DB) · `bars.py:1161-1168` (חי→מנוע בלבד) |
| **סוג-יום (שער)** | `get_live_day_type()` (override → machine → prelock → antiflap) | `trade_context.py:520-584` · gateway G1 extract |
| **כיוון-מותר (DC)** | `direction_context_live.current()["dir"]` (+ `dir_sustained` ל-CONT) | `trading_gateway.py` DIRECTION_CONTEXT / CONT_TREND_FILTER |

> הערה: `SOURCE_OF_TRUTH.md` §Day-type עדיין אומר שה-UI קורא `classify_replay` (נכון) ושהשער קורא אותו דרך G1 — **חלקית מיושן**; השער החי קורא `get_live_day_type`. זו בדיוק סתירת G-16.

---

## טבלה ראשית

| רכיב | מציג | מקור (file:line) | תואם-מנוע? | מה-המשתמש-רואה-אם-🔴 | תיקון-מוצע |
|---|---|---|---|---|---|
| **WoodiesCciPanel** | paint BLUE/RED/GRAY + TrendUp/Down | `GET /api/v9/woodies/chart` → `bars[].trend_state` / `current_bar.trend_state` · FE `WoodiesCciPanel.tsx:81,1069` · BE `woodies_chart_routes.py:85-86,300-301` (Sierra raw / DB בלי re-label) | 🔴 | GRAY-דביק על הבר-החי בזמן ש-S4 כבר RED/BLUE אחרי G1 | ב-`woodies/chart`: להחיל `_trend_from_cci` על השורה האחרונה/`current_bar` (אותו דגל) — **לא** לשכפל מנוע; שדה אחד |
| ChartV5b candles | OHLC ירוק/אדום | `/api/v9/chart/bars5min` · אין `trend_state` | N/A | — | אין פעולה (לא paint) |
| LsmaLine | קו LSMA | `/api/v9/woodies/chart` → `lsma_value` · `LsmaLine.tsx:20-33` | ✅ מקור-קו | — | — |
| TradeMarkChart CCI | paint היסטורי | `/api/v9/chart/replay` → `trend` מ-DB · closed | ✅ סגור | — | — |
| BuildTree S4 `trend_state` | טרנד-מנוע | `/api/v9/build/pattern-status` ← `woodies_inspector` / `current_state` | ✅ | — | — |
| System4Panel “Trend” | מיועד `woodiesBars` | store מת · `setWoodiesBars` לא נקרא | 🔴/dead | תמיד `—` | DEFER / למחוק או לחבר ל-`/woodies/current` |
| **TopBar** day-type | תווית סוג-יום + tooltip כיוון | store `systemStateStore.ts:57-69` → `classify_replay` `final.day_type` / `final.direction` · `TopBar.tsx:61-76` | 🔴 | סוג-יום/גישה בלי override/antiflap/prelock; עלול לסתור את השער | S124 G5: תצוגה = `get_live_day_type` (endpoint חדש או שדה ב-status) |
| **Switcher** S1 chip | סוג-יום | אותו store override · `Switcher.tsx:209-211` | 🔴 | כמו TopBar | אותו מקור כמו TopBar |
| **DayTypeLensContent** | סוג-יום + גישה | `useLiveDayType.ts:46-63` → `classify_replay` | 🔴 | כמו TopBar | אותו תיקון G5 |
| DayTypePill | סוג-יום | `useLiveDayType` | 🔴 (אם מורכב) | כמו למעלה | אותו |
| KeyLevelsStrip DT | סוג-יום | `useLiveDayType` + fallback `key_levels.today.day_type` (machine) | 🔴 | replay או machine — שניהם ≠ `get_live` | לקרוא live |
| DayTypeConditionsTable | שורת-פעיל | `classify_replay` · `DayTypeConditionsTable.tsx:63-68` | 🔴 | highlight ≠ שער | live |
| DayTypeLabelTab strip | אלגוריתם | `classify_replay` segments | 🔴 | תצוגת-צל בלבד — לסמן "display≠gate" או לעבור ל-live | |
| BuildTree S1 day_type | יום ב-build | pattern-status ← machine/history | 🔴 | יכול למכונה הישנה | live בשדה אחד |
| Build S2 auth cell | day_type בשער-S2 | aggregator → `get_live_day_type` | ✅ | — | — |
| **DirectionStrip** | LONG/SHORT + LSMA/CVD | `useDirectionNow.ts:29` → `/day_type/direction_now` → `dir` | ✅ מול `DIRECTION_CONTEXT.dir` | — | — |
| DirectionStrip (חסר) | `dir_sustained` | API מחזיר; FE לא מציג · `DirectionStrip.tsx:28-65` | 🔴 vs CONT_TREND_FILTER | LONG בסטריפ בזמן ש-CONT נחסם על sustained | chip "sustained" או כיתוב כש-`dir≠dir_sustained` |
| Switcher S4 ▲/▼ | כיוון-תבנית | systems-snapshot `active_patterns[].direction` | ✅ מנוע-תבנית · 🔴 vs DC | ▲ LONG בזמן ש-DC חוסם | תווית "pattern" + חסימה מ-`blocked_by` אם יש |
| WoodiesLens Dir | כיוון-תבנית | snapshot `woodies.direction` | ✅/🔴 כמו למעלה | כמו Switcher | כמו למעלה |
| BuildTree “הסכמת כיוון” | הצבעת LONG/SHORT | pattern-status interpretations | 🔴 | הצבעה ≠ `dir`/`dir_sustained` | לקשור ל-`direction_now` או להסיר כ-"מותר" |
| Layer0 SS pill | suffering_side | `/api/v9/veto/state` | ✅ SSV (לא DC) | — | — |
| SystemsTab consensus | bias מסיגנלים | `/signals` · **לא מורכב** ב-V9Dashboard | dead | — | לא לגעת |

---

## רשימת-🔴 ממוינת (עדיפות לסוחר)

### P0 — רואה משהו אחר ממה שהמנוע יורה / חוסם
1. **WoodiesCciPanel paint (טרנד-חי)** — GRAY-דביק מול S4 אחרי G1.  
   תיקון: `_trend_from_cci` ב-`/api/v9/woodies/chart` על בר אחרון/`current_bar` תחת אותו דגל (`woodies_chart_routes.py:85-86`).
2. **TopBar + Switcher S1 + DayTypeLens (+ KeyLevels / Conditions)** — `classify_replay` ≠ `get_live_day_type`.  
   תיקון: S124 **G5 / GAP G-16** — מקור-תצוגה אחד = live (override-aware). אל תשכפל מסווג; הוסף שדה/endpoint דק.

### P1 — כיוון-מותר חלקי
3. **DirectionStrip בלי `dir_sustained`** — CONT יכול להיחסם בזמן שהסטריפ ירוק.  
   תיקון: הצג sustained (או אזהרה כששונה מ-`dir`).
4. **Switcher/Woodies “▲ LONG” בלי הקשר-חסימה** — כיוון-תבנית ≠ כיוון-מותר.  
   תיקון: להבדיל תווית "setup" מ-"allowed"; אופציונלי `blocked_by` מהפיד.

### P2 — רעש / מת
5. BuildTree “הסכמת כיוון” (הצבעה) · System4Panel Trend מת · SoT-doc drift.

---

## הרחבת GAP G-16
G-16 המקורי = TopBar/DayTypeLens על `classify_replay`.  
**אחרי הביקורת הזו G-16 מכסה גם:**
- טרנד-חי UI ≠ G1 (`woodies/chart` raw) — תת-פער **G-16b** (או שורה באותו G-16).
- כיוון: `dir` ✅ ב-DirectionStrip; `dir_sustained` חסר; stance מ-`classify_replay.direction` 🔴.

S124 G5 נשאר התיקון לסוג-יום; תיקון-paint הוא נפרד (קרוב ל-G1 / endpoint chart).

---

## סיכום מספרי
- משטחים שנבדקו (חיים רלוונטיים): **~18**
- ✅ תואמים: DirectionStrip.`dir` · Build S2 auth live · BuildTree S4 trend · LsmaLine · TradeMark closed
- 🔴 אי-התאמות: **9** (P0: paint + day-type cluster · P1: sustained + pattern-dir · P2: vote/dead)
- Verdict כולל: **🔴** — ה-UI **לא** משקף באופן עקבי את מה שהמנוע+השער רואים אחרי G1 / `get_live_day_type`.

## מה אסור / מה הבא
❌ אין קוד במשימה הזו.  
✅ אחרי אימות-cowork: מייקל פוסק עדיפות (paint endpoint vs G5 day-type) → cc-macbook מיישם פער אחד בכל פעם, דגל OFF.
