# CC Prompt — Trades Page UX / Fields / Filters Upgrade (2026-06-02)

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

מטרה אחת: לשדרג את עמוד `/trades` (UX, איכות שדות, פילטרים) — **בלי** לגעת ב-trading-logic,
ב-Sierra/bridge/market-data routes, או בחישובי PnL/excursion הקיימים. כל השינויים הם
שכבת-תצוגה (frontend) + שני תיקוני-נכונות קטנים שמתועדים מפורשות למטה. כל phase אטומי עם
Acceptance Criteria בינארי + פקודת אימות.

## Risk surface — אסור לגעת
- `sc_study/`, `bridge/`, `backend/v9/services/trade_context.py`, `trade_excursion.py`,
  `compute_trade_pnl` — **read-only**. אל תשנה איך PnL/R/MFE/MAE/excursion מחושבים.
- אל תשנה את ה-polling floors שב-CLAUDE.md. עמוד `/trades` הוא fetch-once (TradesView.tsx:14-18) — שמור על זה.
- אין לבדות שדות. אם השדה חסר ב-payload → render "—"/missing (CLAUDE.md Rule 1).

## State of play שאומת (file:line + evidence)
- `frontend/v9/src/v9/components/trades/TradesView.tsx:36-38` — הטבלה רנדרת inline-expand בלבד.
- `TradesTable.tsx:208` — מרחיב שורה עם `<TradeRowExpand>`.
- `TradeRowExpand.tsx` — **חסר** management-log timeline, confidence, day_type, lifecycle, per-contract PnL.
- `TradeDetailsModal.tsx:56` — רכיב עשיר ומלא (timeline ENTRY→STOP_MOVE→T1-T3→EXIT, confidence,
  day_type, blocked_by, MFE/MAE grid, per-contract PnL) — **קוד מת**: לא מיובא ולא מרונדר בשום מקום
  (`grep -rn "TradeDetailsModal" frontend/v9/src` → רק ההגדרה עצמה). ה"timeline שכבר נשלח" חי רק כאן.
- DB evidence: `v9_trade_management_log` = **804 שורות** → נתוני timeline קיימים אך לא מוצגים בעמוד.
- `outcome` ב-DB = `WIN(126) / LOSS(228) / BE(2) / NULL(28)`. ה-Outcome filter
  (`TradeFilters.tsx:37-48`) מציע WIN/LOSS/SCRATCH/OPEN — **`BE` לא ניתן לסינון ולא תואם לאף אפשרות**.
- `firing_system` ב-DB = רק `3(374)` ו-`4(10)`. System filter (`TradeFilters.tsx:25-36`) מציע S1–S6
  כולל מערכות ריקות → רעש.
- `is_synthetic` = `0` לכל 384 השורות. ה-TEST badge (`TradesTable.tsx:69-86`) נוכח ותקין אך אין כרגע
  נתון סינתטי; אין פילטר synthetic.
- `fetchTrades` (`lib/api.ts:163-169`) מחזיר רק `trades`; `normalizeTradesPayload` (125-131) זורק את
  `total`/`truncated` מה-backend (`trades.py:341`) → **"truncation notice" לא מגיע ל-UI**.
- אין מיון לפי עמודה בכלל (TradesTable thead הוא static).

---

## GROUP A · Fields / Correctness (גבוה — נכונות לפני UX)

### A1 — חבר את TradeDetailsModal העשיר (או מזג ל-Expand) במקום ה-Expand החסר
**Finding:** ה-timeline/confidence/day_type/per-contract שכבר נכתבו חיים רק ב-`TradeDetailsModal.tsx`
שאינו מרונדר. המשתמש רואה רק `TradeRowExpand` הדל.
**Task:** בחר אחת (ודווח מה בחרת ולמה):
- (a) רנדר את `TradeDetailsModal` כשנבחר trade (`setSelectedTradeId`), **או**
- (b) הוסף ל-`TradeRowExpand` את החלקים החסרים: Trade Timeline מ-`management_log`
  (ENTRY→STOP_MOVE/SMART_BE→T1/T2/T3_HIT→STOP_HIT→EXIT, כמו `TradeDetailsModal.tsx:290-329`),
  confidence, day_type, per-contract PnL.
- אם נבחר (a) — מחק את ה-dead-code עודף (אל תשאיר שני מימושים שמתבדרים).
**Acceptance:** בהרחבת trade שיש לו שורות log, מוצג timeline עם ≥1 אירוע ניהול מעבר ל-ENTRY/EXIT.
**Test (anti-tautological):** טסט קומפוננטה שמ-mock-ל-`fetchTradeById` עם `management_log` בן 2 שורות
(STOP_MOVE, T1_HIT) ומאשר שהן מופיעות ב-DOM. *if reverted (חזרה ל-Expand הישן) → RED because timeline rows absent.*
**Verify (Rule 5):** הדבק `grep -rn "management_log\|MgmtLogRow" frontend/v9/src/v9/components/trades` + פלט הטסט.

### A2 — Outcome=BE לא ניתן לסינון
**Finding:** DB מכיל `outcome='BE'` (2 שורות) אך `TradeOutcome` (`types/index.ts:92`) ו-Outcome filter
לא כוללים BE; trades אלה בלתי-נראים לכל בחירת outcome שאינה ALL, ולא נספרים נכון ב-Summary
(`TradesSummaryStrip.tsx:24-29` סופר scratch לפי `pnl_usd===0` בלבד).
**Task:** הוסף `'BE'` ל-`TradeOutcome`, אפשרות "Breakeven" ל-Outcome filter, וקטגוריית BE/scratch מאוחדת
ב-summary (BE = scratch מבחינת WR; אל תשנה את חישוב ה-PnL).
**Acceptance:** בחירת Outcome=Breakeven מציגה בדיוק את שורות ה-BE; ALL עדיין מציג הכל.
**Test:** טסט על `filteredTrades()` עם fixture שכולל trade `outcome:'BE'` — בחירת BE מחזירה אותו, WIN/LOSS לא.
*if reverted → RED because BE trade leaks/disappears.*
**Verify:** הדבק פלט הטסט.

### A3 — System filter מציג מערכות ריקות (רעש)
**Finding:** רק S3/S4 קיימים בנתונים; הפילטר מציג S1–S6 קשיח (`TradeFilters.tsx:30`).
**Task:** הצג בפילטר System רק מערכות עם `count>0` בנתונים הטעונים (גזור מ-`trades` ב-store),
פלוס "All". שמור צבע/שם מ-`SYSTEM_NAMES`/`SYSTEM_COLORS`.
**Acceptance:** עם הנתונים הנוכחיים הפילטר מציג All + S3 + S4 בלבד.
**Test:** טסט יחידה לפונקציית הגזירה: fixture עם systems {3,4} → מחזיר [3,4]. *if reverted → RED because empty systems reappear.*
**Verify:** פלט הטסט.

### A4 — חשיפת truncation/total ל-UI
**Finding:** `fetchTrades` זורק `total`/`truncated`; אין "showing N of M" באף מקום.
**Task:** החזר `{trades,total,truncated}` מ-`fetchTrades` (שמור backward-compat), שמור ב-store, והצג
שורת מצב ב-`TradesView`/`TradesSummaryStrip`: "Showing N of M (truncated — raise limit)" כש-truncated.
**Acceptance:** כשה-API מחזיר `truncated:true` מוצגת ההודעה; אחרת לא.
**Test:** mock payload `{trades:[…500], total:900, truncated:true}` → ההודעה ב-DOM. *if reverted → RED because notice missing.*
**Verify:** פלט הטסט + `grep -n truncated frontend/v9/src/v9/lib/api.ts`.

---

## GROUP B · Filters (בינוני-גבוה)

### B1 — פילטר Direction (LONG/SHORT)
חסר לחלוטין למרות שהוא חיתוך ראשון-מעלה. הוסף FilterSelect Direction (All/Long/Short) ב-`TradeFilters.tsx`
+ ענף ב-`filteredTrades()`.
**Acceptance:** Direction=Short מציג רק SHORT. **Test:** fixture mixed → רק SHORT. *reverted→RED.* **Verify:** פלט.

### B2 — פילטר Synthetic (Show/Hide/Only TEST)
ה-badge קיים אך אין שליטה. הוסף toggle (All / Real only / TEST only) ב-`filteredTrades()` לפי `is_synthetic`.
**Acceptance:** "Real only" מסתיר שורות synthetic. **Test:** fixture עם trade `is_synthetic:true` → מוסתר ב-Real only. *reverted→RED.* **Verify:** פלט.

### B3 — "Clear all filters" + מונה פילטרים פעילים
אין דרך לאפס. הוסף כפתור Reset שמחזיר ל-`DEFAULT_FILTERS` (`tradeStore.ts:45`) + תווית "N filters active".
**Acceptance:** Reset מחזיר את כל הבקרות ל-default ואת הטבלה למצב מלא. **Test:** set filters→reset→`filteredTrades().length===trades.length`. *reverted→RED.* **Verify:** פלט.

---

## GROUP C · UX (בינוני)

### C1 — מיון עמודות בטבלה
**Finding:** thead סטטי (`TradesTable.tsx:22-42`); אין מיון. סדר = entry_ts desc מה-API בלבד.
**Task:** הוסף מיון לחיץ ל-When / Sys / P&L / Outcome (toggle asc/desc, אינדיקטור חזותי). מיון client-side
על המערך המסונן; אל תשנה את ה-fetch.
**Acceptance:** קליק על P&L ממיין עולה/יורד; חץ מציין כיוון. **Test:** טסט comparator: fixture לא-ממוין→ממוין נכון לפי pnl_usd עם null-handling. *reverted→RED.* **Verify:** פלט.

### C2 — Loading / error states לטעינה הראשונית
**Finding:** `TradesView` קורא `fetchTrades().catch(console.error)` (15-18) — כשל שקט, אין spinner/empty
ראשוני (מפר CLAUDE.md "No silent failures"). הטבלה מראה "No trades found matching filters" גם כשהכשל הוא רשת.
**Task:** הוסף `loading`/`error` ל-store; הצג spinner בזמן fetch ובאנר שגיאה ("backend on :8000?") בכשל,
נבדל מ-empty-after-filter.
**Acceptance:** כשל fetch מציג שגיאה מובחנת מ-"0 בפילטר". **Test:** mock fetch reject → באנר error ב-DOM; mock 0 rows → "No trades found". *reverted→RED.* **Verify:** פלט.

### C3 — Density / readability של עמודת Path
**Finding:** `Path` (`tradeRowFormat.ts:73-91`) הוא מחרוזת ארוכה אחת ב-`min-w-[360px]`; טבלה `min-w-[1280px]`
(`TradesTable.tsx:21`) — גלישה אופקית בלתי-נמנעת, אין התנהגות narrow/mobile.
**Task (תצוגה בלבד):** שבור את ה-Path ל-IN/ST/T1-3/OUT מיושרים או הוסף truncation+tooltip; ודא שהטבלה
לא שוברת layout מתחת ל-~1280px (גלילה ממוכלת או stacking). אל תשנה את הנתונים, רק את הרינדור.
**Acceptance:** ב-viewport 1024px אין clipping של תוכן (גלילה אופקית ממוכלת, header sticky נשמר).
**Test/Verify:** snapshot/manual — הדבק תיאור + לכל הפחות אישור build ירוק (`npm run build` בלי errors חדשים).

---

## NOT DONE / DEVIATIONS (חובה למלא בדוח)
פרט כל phase שלא בוצע: מה · למה · מה צריך. אם הכל בוצע — כתוב "none".

## דוח (חלק C מהחוזה)
טבלת phases (A1–C3) · Status · Evidence(command+output) · Deviation. לכל טסט שורת
"if reverted → RED because ___". סעיף NOT-DONE. Open/מה נשאר.
לאחר סיום: עדכן `docs/plans/ROADMAP_TO_LIVE.html` + `docs/plans/STATUS_BOARD.md` (root+fix+verification).
