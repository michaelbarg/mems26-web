# PROMPT — Frontend שלב‑1: עמוד Trades לכיול (Trades redesign)

**חוזה:** `docs/handoff/CC_HANDOFF_CONTRACT.md`. כל "DONE" = paste פקודה + raw output
(typecheck/build/diff). מבנה דוח כולל **NOT‑DONE**. מקור‑עיצוב: `HANDOFF_TRADES_PAGE_REDESIGN_NEXT_2026-06-04.md`
+ `docs/plans/TRADES_PAGE_REDESIGN_2026-06-03.md`.
**🎨 מקור-עיצוב ויזואלי (חובה — בנֵה לפיו, פיקסל/טוקן):**
`docs/plans/TRADES_PAGE_PROTOTYPE_2026-06-03.html` — ה-prototype האינטראקטיבי עם הטוקנים
האמיתיים מ-`app/globals.css`. התאם להדמיה הזו, לא רק ל-spec הטקסטואלי.

**Scope (הוכרע Michael 2026‑06‑04):** Frontend שלב‑1 בלבד. **אל תיגע ב‑backend/endpoints/DB/risk/polling.**
**אל תבנה G2–G7** (DEFERRED). smallest correct change · regression test לכל תיקון · אל תריץ dev‑server בלי בקשה
(אימות ב‑typecheck + build + diff).

---

## 0. עובדות‑קוד מאומתות (Cowork קרא — אמת בריצה, אל תסרוק עיוור)
- כניסה: `frontend/v9/src/v9/components/trades/TradesView.tsx` מרכיב TradeFilters · EdgeKpiRow ·
  **PatternPerformanceStrip** · TradeCardList · SelectedTradePanel. `fetchTrades()` נקרא **ללא ארגומנטים**
  (`:16`) → כל ה‑modes, default limit. **לא mounted:** EquityCurveStrip, TradesTable, TradesSummaryStrip.
- store: `stores/tradeStore.ts` — `mode:'ALL'` default (`:57`, ✅ חוב סגור). **באג מסנן‑תאריך** (`:114‑118`):
  `entryDate = t.entry_ts.slice(0,10)` + השוואה לקסיקלית → זה **תאריך‑UTC, לא ET** → עסקה אחה"צ ET נופלת
  ליום הלא‑נכון. = G6.
- ADAPT source: `components/trades/PatternPerformanceStrip.tsx` — כבר מכיל `patternKey()` (`:30`) +
  `aggregateByPattern()` (`:43`) + win%/PF/expectancy/by‑direction/scratch. **זה הבסיס ל‑Edge Matrix הגנרי** —
  אל תבנה רכיב אגרגציה חדש מאפס.
- tokens: `app/globals.css` (bg `--bg-primary` #0d1117, `--sys1`..`--sys4`, `--green` #56d364, `--red` #f85149).

---

## 1. סדר ביצוע (כל פריט במלואו + טסט לפני הבא)

### 1a. תיקון מסנן‑תאריך → ET‑aware (G6) — קודם, קטן, חוסם presets
ב‑`tradeStore.ts:114‑118`: החלף את `slice(0,10)` בהמרת `entry_ts` ל‑**תאריך ET** (`America/New_York`,
DST‑safe — `Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York'})` נותן `YYYY-MM-DD`) לפני ההשוואה.
טסט: עסקה ב‑`2026-06-03T23:30:00Z` (19:30 ET) → נופלת ביום ET `2026-06-03`, לא `06-04`. litmus: אם חוזרים
ל‑slice → RED.

### 1b. date‑presets (תוספת Michael #1)
רצועת presets: היום‑רציף(RTH)/אתמול/7/30/MTD. client‑side, **ET‑aware** (משתמש ב‑1a). "רציף(RTH)" = חלון
09:30–16:00 ET. כל preset קובע `dateFrom`/`dateTo` ב‑store. אין צורך ב‑backend.

### 1c. Edge Matrix גנרי (ADAPT מ‑PatternPerformanceStrip)
הכלל את `patternKey(t)` ל‑`groupKey(t, dim)` עבור `dim ∈ {system, pattern, day_type, killzone, direction}`,
**שימוש חוזר באותו** `aggregateBy...` math. בורר‑ממד (toggle/tabs).
- ✅ עובד עכשיו מ‑שדות קיימים: `system`, `pattern_id`, `direction`.
- ⛔ **`day_type` + `killzone` = gated "pending G1"**: רנדר את העמודה/ציר **אפור מנוטרל** עם תווית
  "pending G1" (Rule 1 — לא לסנתז, לא להסתיר). כשעמודות G1 ינחתו (`day_type_at_entry`/`session_at_entry`
  ב‑Trade type) → רק להסיר את ה‑gating. שמות‑שדות לפי חוזה §5b.

### 1d. Execution‑mode toggle (תוספת Michael #2)
`lib/tradeAuxStatus.ts` **כבר** מחשב `isParallel`/`liveEligible`/`blockedBy` (קיים ב‑store כ‑`auxStatus`).
הבלט toggle ראשי "הכל / ירי‑אחד בכל פעם" + רצועת‑השוואה (win% הכל מול sequential). אל תכתוב לוגיקת‑gating
חדשה — צרוך את הקיים.

### 1e. mount EquityCurveStrip + Target‑dist + Heat (MAE/MFE)
- EquityCurveStrip קיים אך לא‑mounted → mount ל‑TradesView. אם הוא צורך endpoint שלא קיים → רנדר
  client‑side מ‑`lib/tradeMath.ts` (`equityCurveByClose`) מעל הסט הטעון, **עם באנר "≤500 שורות — אינדיקטיבי"**
  (G3 השרת‑צד = DEFERRED).
- Target distribution + Heat MAE/MFE: client‑side מהשדות הקיימים; MAE/MFE מצרפי אם זמין, אחרת "pending G4" gated.

### 1f. ציר price/time במודאל (תוספת Michael #3)
פאנל ממוסגר נפרד במודאל הפרטים: נקודות‑אירוע **אמיתיות** (entry/T1/T2/T3/stop/exit + ה‑ts שלהן) כעמודות.
**אל תדחוס מתחת ל‑R‑path** ואל תסנתז קו‑מחיר רציף (= G7 DEFERRED). סקאלת‑זמן ליניארית מדויקת.

### 1g. פאנל סטופים בתחתית (תוספת Michael #4)
פאנל ייעודי: BE/static/T1_NO_BE מ‑`lib/tradeMath.ts` (`stopMovement`) + תובנת‑כיול. שדות קיימים בלבד.

### 1h. תיקון Scratch/BE
ודא שדלי Scratch/BE מוגדר מפורש (`pnl==0`/`outcome==BE`) בכל אגרגציה חדשה — לא נופל ל‑0 כמו ב‑TradesSummaryStrip
הישן. (ב‑PatternPerformanceStrip זה כבר נכון, `:79‑81` — שמור על זה ב‑Edge Matrix.)

---

## 2. בדיקות (anti‑tautological)
- date‑filter ET: עסקה גבולית UTC↔ET נופלת ביום ET הנכון; litmus revert→RED.
- Edge Matrix: group_by=system נותן אותה התפלגות כמו ספירה ידנית; ממד day_type/killzone מרונדר gated (לא ערך).
- exec‑mode: toggle "ירי‑אחד" מסנן בדיוק לפי `liveEligible` הקיים (לא לוגיקה חדשה).
- אל תשנה טסטים קיימים ל"ירוק". paste typecheck + build raw.

## 3. NOT‑DONE (חובה)
G2–G7 (DEFERRED), backend כלשהו, killzone/day_type live values (gated עד G1), G3 equity שרת‑צד
(client‑side אינדיקטיבי בלבד), G7 קו‑מחיר רציף.
