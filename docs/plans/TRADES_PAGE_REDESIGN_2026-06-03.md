# עיצוב‑מחדש · עמוד Trades להסקת‑מסקנות (כיול) · 2026‑06‑03

**סוג:** design‑research, **read‑only — לא מומש קוד.** · מאשר: Michael 2026‑06‑03
**תוצרים:** המסמך הזה · `TRADES_PAGE_REDESIGN_MOCKUP_2026-06-03.html` · gap‑list ל‑backend (§7)
**מקורות שנקראו:** `db/models/trades.py`, `db/models/trade_log.py`, `api/v9/trades.py`,
`services/trade_context.py`, `services/trade_excursion.py`,
`frontend/.../components/trades/*`, `stores/tradeStore.ts`, `lib/tradeMath.ts`,
`types/index.ts`, `TRADES_PAGE_CHECKLIST_2026-05-31.md`, `TRADES_PAGE_AUDIT_2026-06-01.md`,
`BUILD_STATUS_REDESIGN_MOCKUP.html`, `design/tokens.ts`.

> **עקרון‑על (CLAUDE.md Rule 1):** מעצבים רק סביב שדות אמיתיים. כל מה שלא קיים
> מסומן **`⛔ ממתין ל‑backend`** ולא מסונתז. רוב פאנלי‑הכיול במסמך זה דורשים
> **אגרגציה בצד‑שרת** — ראה §6 (סיכון Cardinality) ו‑§7 (gap‑list).

---

## 1. מה קיים בפועל (מצב נוכחי — KEEP/ADAPT/REPLACE)

### 1.1 מודל‑הנתונים — `V9Trade` (`v9_trades`)
**עמודות ממשיות (first‑class):**
`id, mode (shadow/demo/live), firing_system (1/2/4), direction, state
(PENDING/FILLED/PARTIAL/CLOSED), entry_ts, entry_price, stop, t1, t2, t3,
t1_hit_ts, t2_hit_ts, t3_hit_ts, stop_hit_ts, exit_ts, exit_price, exit_reason,
pnl_usd, pnl_r, outcome (WIN/LOSS/BE), quality (JSON), cross_context (JSON),
sierra_bracket_id, is_synthetic, created_at, updated_at`.

`v9_trade_management_log`: `id, trade_id, ts, action, value(JSON)`.

**קריטי — מה ש*אינו* עמודה (נגזר ב‑runtime, לא ניתן ל‑GROUP BY ב‑SQL):**

| שדה שטריידר חושב עליו | מאיפה זה בא היום | ל‑aggregation |
|---|---|---|
| `pattern_id`, `trigger`, `classification` | נגזר מ‑`quality`+`cross_context` JSON ב‑`extract_trade_display()` | ⛔ לא ב‑SQL |
| `day_type` (בכניסה) | נגזר מ‑`day_type_machine` בתוך `cross_context` | ⛔ לא ב‑SQL |
| `systems_agreement` (confluence) | נגזר ב‑`extract_system_agreement()` | ⛔ לא ב‑SQL |
| `MFE/MAE`, `price_high/low`, `t1_closest`, `t1_at_mfe` | מחושב **on‑the‑fly** מ‑`v9_bars_5min` ב‑`compute_trade_excursion()` (רזולוציית 5ד׳, לא tick) | ⛔ לא נשמר |
| `contracts_pnl` (C1/C2/C3), `pnl_mode` | נגזר ב‑`compute_trade_pnl()` | נגזר |
| `killzone / session‑at‑entry` | **לא קיים בכלל** | ⛔ ממתין ל‑backend |

> זו הנקודה החשובה ביותר במסמך: **כל ציר‑הכיול שהטריידר ביקש (פר‑מערכת/pattern/
> day‑type/killzone) מבוסס על שדות נגזרים‑מ‑JSON, ולכן אי‑אפשר לבנות עליהם
> אגרגציה נכונה בצד‑שרת בלי לקבע אותם כעמודות.** ראה §7‑G1.

### 1.2 ה‑API (`/api/v9/trades`)

| Route | מה מחזיר | אגרגציה? |
|---|---|---|
| `GET ""` | רשימה: `{trades[], total, truncated}` · פילטרים: `mode`, `firing_system/dominant_system`, `limit≤1000` · token | ❌ שורות בלבד |
| `GET /recent` | feed ל‑strip (≤100), tokenless | ❌ |
| `GET /active` | העסקה הפתוחה + C1/C2/C3 | ❌ |
| `GET /{id}` | פירוט + `insight` (fire/recognition/lifecycle) + `management_log[]` | ❌ |
| `POST ""` / `POST /log` / `POST /{id}/exit` | כתיבה/סגירה | — |

**מסקנה:** אין אף endpoint של אגרגציה. WR/expectancy/R/PF פר‑חתך, התפלגות‑יעדים,
MAE/MFE aggregate, equity curve — **כולם מחושבים היום בצד‑לקוח** מעל הדף שנמשך.

### 1.3 ה‑UI הקיים

| רכיב | תפקיד | סיווג |
|---|---|---|
| `TradesView` | אורקסטרציה: header → `TradeFilters` → `EdgeKpiRow` → `PatternPerformanceStrip` → `TradeCardList` + `SelectedTradePanel` | **ADAPT** (layout) |
| `TradeFilters` | Mode/System/Direction/Stop/Sort/pattern + מתקדם (Outcome/תאריך/Overlap/LIVE‑gate/Confluence) | **KEEP** |
| `EdgeKpiRow` | Net/Win%/PF/Exp/MaxDD/R:R/Streak/ΣR + equity sparkline | **KEEP** (להרחיב BE/scratch) |
| `PatternPerformanceStrip` | טבלת WR/Exp/PF/Net + LONG/SHORT פר‑pattern, קליק→פילטר | **ADAPT** → טבלה גנרית רב‑חתך |
| `TradeCardList` | כרטיסי עסקאות + `TradePathVisual` (ציר‑R) | **KEEP** |
| `TradeDetailsModal` | drill‑down: fire · recognition פר‑מערכת · timeline · C1/C2/C3 · MAE/MFE · execution | **KEEP** (חזק) |
| `TradePathVisual` | סיפור‑R של עסקה בודדת (entry→stop/targets→exit) | **KEEP** |
| `SelectedTradePanel` | סייד‑פאנל בחירה | KEEP |
| `EquityCurveStrip` | עקומת‑הון מלאה by‑close + maxDD | **ADAPT** — קיים אך **לא mounted** → להחזיר |
| `TradesTable`, `TradesSummaryStrip`, `TradeRowExpand` | גרסאות קודמות (טבלה/סיכום) | **REPLACE/DEFER** — לא mounted, מקור באג Scratch |

`tradeMath.ts` כבר מחזיק `equityCurveByClose` (סדר נכון לפי `exit_ts` + maxDD),
`rLevels`, `stopMovement`, `durationMinutes` — תשתית טובה, **לשמר**.

---

## 2. השאלות שהטריידר צריך להסיק → מה עונה עליהן (עיצוב‑לאחור)

| # | שאלת‑כיול | פאנל עונה | קיים? |
|---|---|---|---|
| Q1 | **איפה ה‑edge שלי?** WR/expectancy/avg‑R/PF/N פר **מערכת**, פר **pattern**, פר **day‑type**, פר **killzone**, פר **כיוון** | **Edge Matrix** (טבלה רב‑חתׁך, group‑by מתחלף) | חלקי — `PatternPerformanceStrip` רק פר‑pattern |
| Q2 | **האם סכמת‑היעדים פר‑day‑type מתממשת?** כמה הגיעו T1/T2/T3, כמה stopped, כמה BE/scratch | **Target Distribution** (עמודות מוערמות פר‑חתך) | ⛔ אין ויזואליזציה (הדאטה קיימת: `t1_hit/t2_hit/t3_hit`, `exit_reason`, `outcome`) |
| Q3 | **כמה "כאב" לפני שעבד?** MAE על מנצחות (stop צמוד מדי?), MFE על מפסידות (target רחוק/החזרה?), `t1_at_mfe` (הגיע ל‑T1 והתהפך?) | **Heat / MAE‑MFE** (התפלגות + scatter) | ⛔ קיים per‑trade במודאל בלבד, אין aggregate |
| Q4 | **משתפר או מתדרדר לאורך ה‑soak?** equity by‑close + maxDD + **rolling WR/expectancy** + פילוח לפי שעה‑ביום/killzone | **Trend over soak** | חלקי — `EquityCurveStrip` קיים (unmounted), אין rolling ואין time‑of‑day |
| Q5 | **לצלול לעסקה בודדת ובחזרה** (entry→ניהול→exit, מה כל מערכת ראתה) | **Drill‑down modal** | **KEEP** — כבר חזק; פער: `management_log` ריק (§5‑D) |

---

## 3. Layout מוצע (סקירה → drill‑down)

מבנה אנכי, מלמעלה‑כללי למטה‑פרטני, RTL, שפת‑העיצוב של `BUILD_STATUS_REDESIGN_MOCKUP`:

```
┌ Header: MEMS26 / Trades · קישורי Dashboard/Build Status ─────────────┐
├ Scope bar: Mode · [היום RTH][אתמול][7י][30י][תח׳חודש] · טווח · #trades │  ← presets (§4.5) + TradeFilters ADAPT
├ Execution mode: ( הכל · מקבילות · רצף‑אמת=ירי‑אחד ) + השוואת‑Edge      │  ← §4.6 — מ‑computeAuxStatus (KEEP, להבליט)
├ Edge band: Net · Win% · BE/Scratch · PF · Exp · MaxDD · R:R · ΣR · spark │  ← EdgeKpiRow (KEEP+הרחבה)
├ Pivot tabs:  [System] [Pattern] [Day‑type] [Killzone] [Direction]      │  ← בורר group‑by ל‑Edge Matrix
│   Edge Matrix — N · W/L · Win% · Exp · PF · avgR · Net · התפלגות‑יעדים  │  ← ADAPT PatternPerformanceStrip לגנרי
├ שתי עמודות:                                                            │
│   ┌ Target Distribution (מוערם T1/T2/T3/Stop/BE פר‑חתך) ┐ ┌ Heat MAE/MFE ┐│
│   └ סכמת day‑type: planned מול realized                 ┘ └ scatter+hist ┘│
├ Trend over soak: equity by‑close + maxDD + rolling‑WR + by‑hour         │  ← ADAPT EquityCurveStrip (mount)
├ Trade list (כרטיסים + TradePathVisual + מיני price/time §4.7) │ Selected │  ← KEEP + chart חדש
├ ▼ חלק‑תחתון — התנהגות סטופים (BE / static / T1_NO_BE) פר‑חתך           │  ← §4.8 (הועבר לתחתית לבקשת Michael)
└ Drill‑down modal (fire · recognition · timeline · C1-3 · MAE/MFE · price/time) │ ← KEEP + §4.7
```

עיקרון: **כל קליק על שורת‑חתך (מערכת/pattern/day‑type) מסנן את כל מה שמתחתיו**
(הזרימה `setFilters` שכבר קיימת ב‑store) — סקירה→drill‑down בלי ניווט.

---

## 4. הפאנלים החדשים/המורחבים — מיפוי לשדות אמיתיים

### 4.1 Edge Matrix (ADAPT מ‑PatternPerformanceStrip)
טבלה אחת עם בורר `group_by ∈ {system, pattern, day_type, killzone, direction}`.
עמודות לכל שורה: `N (open)`, `W`, `L`, `BE`, `Scratch`, `Win%`, `Net$`, `avg W/L`,
`Exp$`, `PF`, `avgR`, ומיני‑בר התפלגות‑יעדים.
- `system` ✅ (`firing_system`), `direction` ✅, `pattern`/`day_type`/`killzone` → ⛔ §7‑G1.
- `Win%/Exp/PF/avgR/Net` ✅ נוסחאות כבר ב‑`EdgeKpiRow`/`PatternPerformanceStrip`.

### 4.2 Target Distribution (חדש; דאטה קיימת)
עמודה מוערמת פר‑חתך: `T1‑only / T2 / T3 / Stopped / BE / Scratch / Open`.
מקור: `t1_hit/t2_hit/t3_hit` (✅), `exit_reason` (✅ `STOP_HIT` וכו׳), `outcome` (✅).
"סכמת day‑type": מול ה‑planned schema (מ‑`day_type_targets`) — מציג realized% מול
expected%. ⛔ ה‑planned‑schema צריך חשיפה (§7‑G3).

### 4.3 Heat — MAE/MFE (חדש; דאטה קיימת per‑trade)
- היסטוגרמת MAE על **מנצחות** → האם ה‑stop צמוד מדי (כאב גדול שהוחזר).
- היסטוגרמת MFE על **מפסידות** → רווח שלא נלקח / target רחוק מדי.
- `t1_at_mfe_pts` מרוכז → כמה פעמים המחיר הגיע ~T1 והתהפך.
מקור: `mfe_pts/mae_pts/t1_at_mfe_pts` (✅ קיימים בשורה), אך **per‑trade בלבד** —
לאגרגציה בקנה‑מידה צריך endpoint (§7‑G2). **אזהרת‑דיוק:** 5ד׳ ולא tick — להציג כפי
שמוצג היום במודאל ("not tick precision").

### 4.4 Trend over soak (ADAPT EquityCurveStrip)
- equity by‑close + maxDD ✅ (`equityCurveByClose`).
- **rolling WR/expectancy** (חלון‑N) — חדש; ניתן מ‑`pnl_usd` בסדר‑סגירה.
- פילוח by‑hour‑of‑day / killzone — ⛔ killzone‑at‑entry לא נשמר (§7‑G1); hour‑of‑day
  אפשרי מ‑`entry_ts` ✅ אך **חובה TZ מפורש** (CLAUDE.md Rule 4 — ראה §5‑C).

### 4.5 Date presets (בקשת Michael — חדש; client‑side)
שורת‑כפתורים מהירה ב‑Scope, מעל שדות‑התאריך החופשיים הקיימים:
`היום (מסחר רציף/RTH) · אתמול · 7 ימים · 30 ימים · תחילת‑חודש (MTD)`.
- כל כפתור מחשב `dateFrom/dateTo` מ‑"היום" ✅ (מעל `entry_ts`) — **חובה ET‑aware**
  (CLAUDE.md Rule 4; ראה D‑D + G6). presets פותרים בפועל את באג‑התאריך הלקסיקלי כי
  הגבול נקבע אחת ב‑ET ולא מהשוואת‑מחרוזת חופשית.
- **"מסחר רציף (RTH) היום"** = היום + מסכת‑שעות RTH (09:30–16:00 ET, ללא globex).
  ⛔ מסכת‑ה‑RTH דורשת חלון‑סשן ב‑ET — קיים `services/session_boundary/manager.py`
  (ADAPT) או קבוע‑משותף; לא לסנתז גבול. שאר ה‑presets (אתמול/7/30/MTD) טהורים client‑side.

### 4.6 Execution mode — סימולטני מול "ירי אחד בכל פעם" (בקשת Michael)
**כבר קיים בקוד** — `computeAuxStatus()` (`tradeAuxStatus.ts`) מחשב per‑trade:
`isParallel` (חפפה עסקה אחרת בזמן = SHADOW reality) · `liveEligible` (gating רציף: עד
עסקה‑פתוחה‑אחת בכל רגע = LIVE reality) · `blockedBy` (איזו עסקה חסמה). היום זה קבור
תחת "More" (`overlap`/`liveGated`). העיצוב **מבליט** זאת כ‑toggle ראשי + **רצועת‑השוואה**:

| תצוגה | מה רואים | מקור |
|---|---|---|
| הכל | כל העסקאות (כולל מקבילות) | ✅ |
| מקבילות בלבד | רק `isParallel=true` (כמה ירי בו‑זמנית) | ✅ |
| **רצף‑אמת (ירי אחד)** | רק `liveEligible=true` — מה שהיה נלקח ב‑LIVE | ✅ |

הערך‑לכיול: **"מה ה‑edge האמיתי אם רק ירי‑אחד‑בכל‑פעם?"** — מציגים Net/Win%/Exp של
"הכל" מול "רצף‑אמת" זה‑לצד‑זה. ⚠️ `computeAuxStatus` הוא O(n²) מעל **הדף בלבד**
(תיעוד הקוד: "n≤200, single API page") + cap‑2ש' לעסקה‑פתוחה → לחישוב‑gating **נכון**
מעל כל ה‑soak צריך לחשב שרת‑צד (מתחבר ל‑§6 ול‑G2/G3).

### 4.7 ציר price/time פר‑עסקה — מה קרה בפועל (בקשת Michael)
chart קטן `x=זמן, y=מחיר` שמראה **בפועל**: קו המחבר את נקודות‑האירוע הידועות —
`entry(entry_ts,entry_price) → T1(t1_hit_ts,t1) → T2(t2_hit_ts,t2) → T3(t3_hit_ts,t3)
→ stop(stop_hit_ts,stop) → exit(exit_ts,exit_price)`, עם קווי‑אופק ל‑stop/T1/T2/T3.
- **גרסה "לא מסובכת" (מומלצת, client‑side):** כל הנקודות הן **עמודות ממשיות** ✅ —
  אפס סינתזה. נותן בדיוק "איפה הכניסה / היציאות בפועל". משלים את `TradePathVisual`
  (שהוא ציר‑R אופקי, לא זמן‑מחיר). **מיקום: פאנל ממוסגר נפרד / drill‑down modal — לא
  נדחס מתחת ל‑R‑path בכרטיס** (ניסוי ראשון יצא "מרוח": קווי‑האופק וה‑labels של שני
  הצירים התנגשו). plot עם מסגרת, ציר‑Y מחיר משמאל, ציר‑X זמן למטה, labels מחוץ ל‑plot.
- **גרסה מלאה (אופציונלי):** קו‑מחיר אמיתי בין האירועים דורש את **סדרת ברי‑5ד׳ בחלון** —
  היום `compute_trade_excursion` מחזיר רק hi/lo מצרפי, לא את הסדרה ⛔ G7. בלי הסדרה
  מציגים קו ישר בין אירועים (לא לסנתז wiggle).

### 4.8 התנהגות‑סטופים — חלק תחתון (בקשת Michael: "אולי זה צריך להיות בחלק התחתון")
מעבירים את ניתוח‑הסטופים מהפילטר‑הראשי לפאנל ייעודי **בתחתית** העמוד: התפלגות
`BE‑moved / static(−1R) / T1_NO_BE` פר‑חתך + תובנת‑כיול ("כמה פעמים T1 נפגע בלי
שהסטופ זז ל‑BE"). מקור: `stop_initial` vs `stop` (✅ `_stop_initial_from_trade`),
`stop_issue=='T1_NO_BE'` (✅), `stopMovement()` (✅). ה‑`StopTag` בכרטיס נשאר; הניתוח
המצרפי יורד למטה כפאנל. (D‑C: דלי Scratch/BE עדיין צריך הגדרה מפורשת — §5.)

---

## 5. החוב הידוע — מצב נוכחי וכיצד העיצוב פותר

| # | חוב (מ‑Checklist 05‑31) | מצב נוכחי בקוד | פתרון בעיצוב |
|---|---|---|---|
| D‑A | **mode=SHADOW default** מסתיר עסקאות | ✅ **כבר תוקן** — `DEFAULT_FILTERS.mode='ALL'` (`tradeStore.ts:57`) | לשמר ALL; Scope‑bar מציג בורר‑mode מפורש |
| D‑B | **חסר WR% + R aggregate** | ✅ **נוסף** — `EdgeKpiRow` מציג Win%/ΣR/Exp/PF | להרחיב: BE/Scratch מפורש; פר‑day‑type ב‑Edge Matrix |
| D‑C | **Scratch תמיד 0** | ⚠️ **פתוח** — הבאג ב‑`TradesSummaryStrip` (לא mounted). `EdgeKpiRow` מוציא `pnl===0` מ‑`decided` אך לא סופר אותם כדלי נפרד | להגדיר דלי מפורש: `Scratch = closed ∧ pnl==0 ∧ outcome≠BE`; `BE = outcome=='BE'`. להציג כעמודות נפרדות ולא לבלוע |
| D‑D | **מסנן‑תאריך לקסיקלי** על `entry_ts` עם זמן/TZ | ⚠️ **פתוח** — `tradeStore.ts:114‑118` משווה `entry_ts.slice(0,10)` מול `YYYY‑MM‑DD` | להמיר ל‑TZ‑aware (ET) בגבול; להציג את ה‑TZ ב‑UI (Rule 4). ⛔ לאשר אם החיתוך בצד‑שרת |
| D‑E | truncation ב‑limit | פתוח — ראה §6 | אגרגציה בצד‑שרת (§7) מסירה את התלות ב‑limit |

---

## 6. הסיכון המרכזי — Cardinality (CLAUDE.md: P27.5a "never again")

**כל פאנלי‑הכיול מחושבים היום בצד‑לקוח מעל `filteredTrades()` — שהוא רק הדף שנמשך**
(`TradesView` קורא `fetchTrades()` ללא ארגומנטים → **default `limit=500`, ללא mode**;
cap‑שרת `le=1000`). ברגע ש‑SHADOW יצבור יותר מ‑500 עסקאות:
WR/expectancy/equity/maxDD **יחושבו על תת‑קבוצה שקטה** ויציגו edge שגוי — בדיוק
מחלקת‑הבאג של P27.5a (חיתוך שקט של השורות החדשות). זה **חוסם‑כיול**, לא קוסמטיקה.

**המסקנה לעיצוב:** פאנלי‑האגרגציה חייבים לשאוב מ‑endpoint שמחשב מעל **כל** הקבוצה
ב‑SQL (לא מעל דף), ולעמוד ב‑4 צירי‑UAT (Quality/Recency/Cardinality/Latency).
רשימת‑הכרטיסים (cards) יכולה להישאר מדף‑מעומד עם pagination.

---

## 7. gap‑list ל‑backend (קלט לפרומפט‑מימוש עתידי)

> כל פריט מסומן: **G‑root** (חובה לפני שאר ה‑gaps) / endpoint נדרש / שדות.

**G1 (root) — לקבע חתכי‑כיול כעמודות ניתנות‑ל‑GROUP_BY.**
היום `pattern_id`, `day_type_at_entry`, `systems_agreement`/confluence, ו‑`killzone/
session_at_entry` נגזרים מ‑JSON או לא קיימים. ⛔ נדרש לכתוב אותם כעמודות (או JSONB
מאונדקס) בזמן‑כניסה ב‑`create_trade`/gateway, **מבלי לסנתז** — אם המקור שותק, `NULL`
(Rule 1). זהו תנאי‑קדם ל‑G2/G3/G4.

**G2 — `GET /api/v9/trades/stats?group_by={system|pattern|day_type|killzone|direction}&mode=&from=&to=`**
מחזיר שורה לכל מפתח: `{key, n, open, wins, losses, be, scratch, win_pct, expectancy,
pf, avg_r, net_usd, t1_hit, t2_hit, t3_hit, stopped}` — מחושב ב‑SQL מעל כל הקבוצה.
מזין את Edge Matrix + Target Distribution. עמידה ב‑4 UAT.

**G3 — `GET /api/v9/trades/equity?mode=&from=&to=&rolling=N`**
נקודות עקומה בסדר `exit_ts` + `maxDd` + `rolling_win_pct`/`rolling_expectancy`,
מחושב שרת‑צד מעל כל הקבוצה (לא דף). מזין Trend‑over‑soak. בנוסף: התפלגות planned מול
realized של day‑type targets (חשיפת ה‑schema מ‑`day_type_targets`).

**G4 — `GET /api/v9/trades/excursion_stats?group_by=...`**
אגרגציית MAE/MFE: avg‑MAE‑על‑מנצחות, avg‑MFE‑על‑מפסידות, היסטוגרמת `t1_at_mfe`.
היום `compute_trade_excursion` רץ per‑row מול `v9_bars_5min` — בקנה‑מידה צריך
precompute/caching או לקבע `mfe_pts/mae_pts` כעמודות ב‑EOD. שמר אזהרת 5ד׳‑לא‑tick.

**G5 — אכלוס `v9_trade_management_log` (מ‑Audit 06‑01 F3).**
הטבלה לעולם לא נכתבת אוטומטית; כל הניהול (Smart‑BE/trail/hit) הולך ל‑logger+`cross_
context`. ה‑drill‑down timeline ריק. ⛔ לחווט כתיבה מ‑`TrailEngine`/`TradeManager`/
`BarLevelDetector`, או (זמני) לקרוא `cross_context` כ‑fallback במודאל.

**G6 — TZ מפורש על מסנן‑התאריך + presets + מסכת‑RTH (Rule 4).** חיתוך יומי ב‑ET בגבול
(לא השוואת‑מחרוזת לקסיקלית); presets (היום/אתמול/7/30/MTD) נגזרים מ‑"היום" ב‑ET;
**"מסחר רציף היום"** דורש חלון‑RTH (09:30–16:00 ET) מ‑`session_boundary/manager.py`
(ADAPT) או קבוע‑משותף — לא לסנתז גבול.

**G7 — `GET /api/v9/trades/{id}/path` (אופציונלי, לציר price/time מלא §4.7).**
סדרת ברי‑5ד׳ בחלון‑העסקה (`ts,o,h,l,c`) כדי לצייר קו‑מחיר אמיתי. בלי זה — הציר
מצויר מנקודות‑האירוע הקיימות בלבד (גרסה לא‑מסובכת, אפס‑backend). שמר אזהרת 5ד׳‑לא‑tick.

**הבהרה — Execution mode (§4.6) לא דורש endpoint חדש לתצוגה הבסיסית** (`computeAuxStatus`
קיים), אך לחישוב‑gating **נכון מעל כל ה‑soak** (לא מעל דף) צריך לחשב שרת‑צד — מכוסה ע"י
G2/G3 (אגרגציה מעל הקבוצה המלאה).

**אין צורך ב‑backend (כבר קיים, צד‑לקוח):** Net/Win%/PF/Exp/MaxDD/ΣR/R:R, equity
by‑close, contracts_pnl, MAE/MFE per‑trade, recognition/insight, TradePathVisual.

---

## 8. Invariants שנשמרו
read‑only · לא מומש קוד · לא נגעתי ב‑risk‑logic · source‑of‑truth: כל "חסר" מסומן
`⛔ ממתין ל‑backend` ולא סונתז · localhost. **Michael מאשר את העיצוב לפני מימוש.**
