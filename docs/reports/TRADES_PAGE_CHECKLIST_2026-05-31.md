# צ'ק‑ליסט אימות — עמוד הטריידס (`/trades`)

**נוצר:** 2026‑05‑31 (Cowork, read‑only code audit). **מטרה:** לוודא שכל המסננים
תקינים, החישובים נכונים, ושרואים שהכל פעיל. סימון: ⬜ לבדוק · ⚠️ חשד שזוהה בקוד.

זרימה: `TradesView` → `fetchTrades()` → `GET /api/v9/trades?limit=200` →
`normalizeTradesPayload` → `mapTradeRow` → `tradeStore.setTrades` →
`filteredTrades()` → `TradesSummaryStrip` / `TradesTable` / `PatternPerformanceStrip`.

---

## A · חיווט / קישוריות
- ⬜ `GET /api/v9/trades?limit=200` מחזיר 200 (Cardinality) — אם יש >200 עסקאות, יש truncation.
- ⬜ ה‑endpoint קיים ומגיב <100ms (Latency), ומחזיר את הרשומות החדשות (Recency: `latest_ts == MAX(ts) FROM DB`).
- ⬜ `mapTradeRow` ממפה נכון: `pnl_usd`, `outcome`, `system`, `mode` (קרא `lib/api.ts:140-161`).
- ⬜ אין סינון `is_synthetic` שמסתיר עסקאות אמיתיות (או להפך — phantom @5900 מסוננות).
- ⬜ TradesView קורא `fetchTrades()` **בלי mode** → מושך הכל; הסינון לפי mode קורה בצד לקוח.

## B · מסננים (כל אחד)
- ⚠️ **Mode — ברירת מחדל `SHADOW`** (`tradeStore.ts:46`). אם העסקאות נרשמות תחת mode אחר (SIM/LIVE/`null`) → העמוד **ייראה ריק**. בדוק שזה לא הגורם ל"לא עובד".
- ⬜ System (1–6), Outcome (WIN/LOSS/SCRATCH/OPEN) — תואמים לערכים ב‑DB.
- ⚠️ **date filter** משווה `entry_ts` (מחרוזת עם זמן/TZ) מול מחרוזת `YYYY-MM-DD` לקסיקלית (`tradeStore.ts:98-99`) — לוודא שאין השמטות בגבולות יום/TZ.
- ⬜ pattern search מכסה `pattern_id/trigger/classification/direction`.
- ⬜ Overlap (parallel/sequential), LIVE‑eligible, Confluence — נגזרים מ‑`computeAuxStatus` (`tradeAuxStatus.ts`); לאמת שהלוגיקה שם נכונה.

## C · חישובים (TradesSummaryStrip)
- ⚠️ **Scratch תמיד 0** — `scratch = withPnl.filter(pnl===0)` אבל `withPnl = pnl != null && pnl !== 0` (`TradesSummaryStrip.tsx:23,27`). תנאי סותר → Scratch לעולם לא >0. **באג חישוב לאימות/תיקון.**
- ⬜ Total P&L = `Σ pnl_usd` על המסוננות — מול חישוב DB ישיר (Quality).
- ⬜ Wins/Losses לפי `pnl_usd >0 / <0` — לאמת מול outcome ב‑DB (עקביות).
- ⬜ **Open count** = `outcome==='OPEN' || state∈{FILLED,PARTIAL,PENDING}` — לאמת שאין כפילות מול closed.
- ⚠️ **אין Win Rate %** ואין aggregate **R‑multiple** בסיכום — לשקול הוספה (pnl_r קיים ב‑DB; ראה roadmap UI pnl_r).
- ⬜ By‑system breakdown — סכום ה‑pnl/wins/losses תואם לסכום הכללי.
- ⬜ partial (realized) — `pnl_mode==='partial'` נספר ומוצג נכון.

## D · "הכל פעיל" (live indicators)
- ⬜ עסקה חדשה מ‑`setup_emitter` מגיעה ל‑DB ומופיעה בעמוד אחרי refresh (אין polling חי ב‑TradesView — רק `useEffect` חד‑פעמי; לאמת אם נדרש רענון).
- ⬜ `TradeMarkerOverlay` / `TradeHistoryStrip` בדאשבורד הראשי מסונכרנים עם אותו מקור.
- ⬜ אינדיקציה ויזואלית למצב open/active (open chip, מצב trade פעיל).
- ⬜ TradeDetailsModal פותח רשומה בודדת (`/api/v9/trades/{id}`) ומציג מסננים/חישובים תואמים.

## E · קישור לאבחון "הטרייד לא עובד"
חשד עיקרי מהקוד: **ברירת המחדל SHADOW** + שאלה אם עסקאות בכלל **נורות ונרשמות**
(קשור לחוסמים 1.4 order routing stub / 1.2 gateway כפול). רצף לבדיקה:
`setup_emitter.py` (fire) → `pre_fire_validator` → gateway → executor → DB
(`v9_trades`?) → `GET /api/v9/trades` → store → UI. למצוא היכן השרשרת נקטעת.

---

## סיכום חשדות שכבר זוהו (לאימות, לא לתקן עד אישור)
1. ⚠️ Scratch לעולם 0 — תנאי `withPnl` סותר (חישוב).
2. ⚠️ ברירת מחדל mode=SHADOW עלולה להסתיר את כל העסקאות (תפיסת "לא עובד").
3. ⚠️ date filter לקסיקלי על `entry_ts` עם זמן/TZ — סיכון השמטה בגבולות.
4. ⚠️ אין WR% / R aggregate בסיכום.
5. ⬜ truncation ב‑limit=200.

> כל הבדיקות הדינמיות (טעינה/רינדור/recency) דורשות הרצה חיה — להשלים כשהסביבה
> חוזרת או בהרצה אצל Michael. הקוד‑audit לעיל אינו דורש הרצה.
