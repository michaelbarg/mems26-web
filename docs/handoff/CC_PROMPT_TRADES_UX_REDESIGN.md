# CC Prompt — Trades Page UX Redesign (frontend-only, additive)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**מטרה אחת:** לשדרג את חוויית עמוד `/trades` (יומן המסחר) ל-redesign שאומת ב-Cowork
על נתונים אמיתיים. **Frontend בלבד. Additive. אפס שינוי ב-backend, בלוגיקת מסחר,
ב-decision pipeline, ב-polling floors או ב-bridge.**

מקור האמת לעיצוב: ה-mockup האינטראקטיבי שאושר מול Michael + מסמך
`docs/reports/UX_AUDIT_TRADES_BUILD_2026-06-02.md`.

---

## 0 · גבולות — מה אסור לגעת (risk surface)

- **אסור** לגעת ב-`backend/`, ב-DLL, ב-bridge, ב-decision/dispatcher, או בכל לוגיקת
  ירי/סיכון.
- **אסור** לשנות endpoints. כל השדות שצריך כבר חוזרים מ-`GET /api/v9/trades`
  (אומת ב-`backend/v9/api/v9/trades.py:99 _trade_list_row`).
- **אסור** לשנות את `useSystemStatePolling`/SoundProvider/שאר polling floors
  (CLAUDE.md §Frontend Polling Floors).
- **אסור** למחוק את `TradesTable.tsx` הקיים — להשאיר אותו כ-fallback מאחורי toggle.
- **Source-of-truth (CLAUDE.md Rule 1):** אם שדה הוא `null`/חסר — להציג `—`.
  **אסור** לסנתז ערך (R:R, סטופ, קומולטיב) ולסמן אותו כאילו הגיע מהמקור.

---

## 1 · Audit לפני בנייה (KEEP / ADAPT / REPLACE)

| רכיב | קובץ | סיווג | פעולה |
|---|---|---|---|
| `PatternPerformanceStrip` | `frontend/v9/src/v9/components/trades/PatternPerformanceStrip.tsx` | KEEP | ללא שינוי |
| `TradeRowExpand` | `…/trades/TradeRowExpand.tsx` | KEEP | ללא שינוי |
| `TradesTable` | `…/trades/TradesTable.tsx` | KEEP (fallback) | מאחורי toggle "classic/visual" |
| `TradesSummaryStrip` | `…/trades/TradesSummaryStrip.tsx` | ADAPT→REPLACE | מוחלף ב-`EdgeKpiRow`+`EquityCurveStrip` (לשמור הקומפוננטה עד שה-toggle יציב) |
| `TradeFilters` | `…/trades/TradeFilters.tsx` | ADAPT | סרגל בוררים קומפקטי + מצב/הצלבה/סטופ/R:R-sort |
| `tradeStore` | `…/stores/tradeStore.ts` | ADAPT | להוסיף filters: `stopMove`, ולוודא `mode`/`overlap` קיימים |
| `tradeAuxStatus` | `…/lib/tradeAuxStatus.ts` | KEEP | משתמשים ב-`isParallel` הקיים ל-overlap |

חובה לקרוא כל קובץ לפני שינוי (CLAUDE.md §Pre-LIVE: read current code).

---

## 2 · מקורות נתונים (כולם קיימים — אסור backend)

מתוך `GET /api/v9/trades` (ראה `trades.py:99`): `entry_ts, exit_ts, entry_price,
stop, stop_initial, stop_note, stop_issue, t1, t2, t3, t1_hit, t2_hit, t3_hit,
exit_price, exit_reason, pnl_usd, pnl_r, outcome, state, mode, system,
direction, systems_agreement, is_synthetic`.

נגזרות frontend בלבד (טהורות, ניתנות ל-unit test):

- **R יחסי לרמה:** `risk = |entry_price − stop_initial|`; `favorable(level) =
  dir==='LONG' ? (level−entry)/risk : (entry−level)/risk`. כניסה=0, סטופ התחלתי=−1R.
- **R:R:** `1 : favorable(t1)` (T1) ו-`1 : favorable(t2)` (T2). אם `t1==null` → `—`.
- **תנועת סטופ:** `moved = stop_initial != null && stop != null &&
  |stop_initial − stop| ≥ 0.01`. verdict:
  `moved` → "זז ל-BE לפי אפיון (SMART_BE)"; `!moved && stop_issue==='T1_NO_BE'`
  → "⚠ T1 נגע אך לא זז"; אחרת → "סטופ ב-−1R — T1 לא נגע". (אל תמציא — הכל מ-flags קיימים.)
- **משך:** `exit_ts − entry_ts` (פתוח → "פתוח").
- **קומולטיב סגירה:** מיון לפי `exit_ts` ואז סכום רץ של `pnl_usd`. **קומולטיב פתיחה:**
  מיון לפי `entry_ts`. (עסקה פתוחה ללא `exit_ts` לא נכנסת לקומ׳ סגירה.)
- **Overlap (מוצלבת/נפרדת):** מ-`tradeAuxStatus.isParallel` הקיים. אסור לחשב מחדש בנפרד.
- **פורמט כספי חשבונאי:** הפסד בסוגריים ללא מינוס — `($33.75)`; רווח `+$5.00`; אפס `$0.00`.

---

## 3 · Phases אטומיים (כל אחד: Acceptance בינארי + פקודת אימות)

### P1 — `lib/tradeMath.ts` (נגזרות טהורות) + unit tests
מימוש: `rLevels(trade)`, `riskReward(trade)`, `stopMovement(trade)`,
`durationMinutes(trade)`, `cumulativeByClose(list)`, `cumulativeByOpen(list)`,
`formatUsdAccounting(v)`.
- **Acceptance:**
  - `formatUsdAccounting(-33.75)==='($33.75)'`, `(5)==='+$5.00'`, `(0)==='$0.00'`.
  - `stopMovement` על trade עם `stop_initial≠stop` מחזיר `moved:true`; על שווים → `false`.
  - `riskReward` עם `t1==null` מחזיר `null` (לא מספר מסונתז).
  - `cumulativeByClose` ממיין לפי `exit_ts` (טסט עם שתי עסקאות שסדר הכניסה ≠ סדר היציאה
    מחזיר סדר נכון — זה ה-bug שזיהינו: #382 נסגרה לפני #371 למרות שנכנסה אחריה).
- **פקודת אימות:** `cd frontend/v9 && npx vitest run src/v9/lib/__tests__/tradeMath.test.ts`
- **anti-tautological:** הטסט מייבא מ-`../tradeMath` וקורא לפונקציה האמיתית; *if reverted
  (להחזיר מיון ל-`entry_ts`) → RED because cumulativeByClose order assertion fails.*

### P2 — `EdgeKpiRow` + `EquityCurveStrip`
KPI: Net, Win rate, Profit factor, Max DD, R:R~ (ממוצע favorable(t2)), "סטופ זז N/total",
"מוצלבות N/total" — **כולם מחושבים על הסט המסונן** ומתעדכנים עם הפילטר. Equity = קומולטיב
סגירה של הסט המסונן.
- **Acceptance:** שינוי פילטר (מערכת/כיוון) משנה את ה-KPI ואת העקומה; Max DD שלילי מוצג `($X)`.
- **אימות:** component test (vitest + @testing-library) שמרנדר עם 3 trades, משנה prop של
  filter, ובודק ש-`Net` ו-data של ה-chart השתנו. *if reverted (KPI על כל הסט במקום המסונן)
  → RED.*

### P3 — `TradePathRow` (ציר R יחסי)
ציר R: קו מקווקו לבן ב-0 (כניסה), קו אדום ב-−1R; markers: stop(−1R), entry(0),
T1/T2 (כחול, מלא אם hit), exit (ענבר, R = `pnl_r`); חץ ירוק מ-−1R ל-BE כש-`moved`.
תוויות מדורגות (stop/targets מעל, entry/exit מתחת) — בלי חפיפה. סטיקר LONG/SHORT,
פס צבע-מערכת + גוון רקע (צבע המערכת דומיננטי), צ'יפ `R:R 1:x`, תג BE✓/סטטי, אייקון
"מוצלבת". כספים בפורמט חשבונאי.
- **Acceptance:** trade שזז (stop_initial≠stop) מציג חץ + "BE ✓"; trade שלא — "סטטי".
  שתי תוויות במחיר זהה אינן חופפות (bounding boxes נפרדים).
- **אימות:** component test על trade שזז ועל trade שלא — בדיקת נוכחות `BE ✓` / `סטטי`.
  *if reverted (להסיר את לוגיקת ה-moved) → RED.*

### P4 — סרגל פילטר קומפקטי (`TradeFilters` ADAPT)
בוררים קטנים בשורה אופקית אחת: מצב (All/Live/Demo/Shadow — קיים), כיוון, מערכת,
**סטופ (All/זז BE/סטטי — חדש)**, **הצלבה (All/מוצלבות/נפרדות — מ-`overlap` הקיים)**,
מיון (כולל **R:R↓ — חדש**), חיפוש פטרן, reset. בלי dropdowns ענקיים/חיתוך.
- **Acceptance:** כל ששת הבוררים גלויים ברוחב 1280px בלי גלילה אופקית; בחירת "זז BE"
  מציגה רק trades עם `moved`.
- **אימות:** component test — set filter `stopMove='moved'` ⇒ הרשימה מכילה רק trades שזזו.
  *if reverted (filter לא מסנן) → RED.* + צילום מסך ב-1280px (להדביק ל-report).

### P5 — פנל פרטים (`SelectedTradePanel`) ב-rail
לחיצה על שורה בוחרת (highlight) וממלאת פנל קבוע: כניסה/סטופ/T1/T2/יציאה (מחיר + R),
P&L, בלוק "סיכון/סיכוי" (נקודות + R + יחס + מומש), בלוק "ניהול סטופ" (verdict מ-P1),
קומ׳ פתיחה + קומ׳ סגירה, מצב, מוצלבת/נפרדת. בלי layout shift.
- **Acceptance:** בחירת trade מעדכנת את הפנל; trade מחוץ לסט המסונן מציג "—" בקומולטיב.
- **אימות:** component test — click row ⇒ הפנל מציג את אותו `#id` ואת ה-verdict הנכון.

### P6 — שילוב ב-`TradesView` + toggle
`TradesView` מציג: header → toolbar (P4) → KPI (P2) → equity (P2) → גוף (rows P3 +
panel P5). Toggle "Visual / Classic" שמחזיר את `TradesTable` הישן (לא נמחק).
- **Acceptance:** `/trades` עולה ללא שגיאות console; toggle מחליף בין שתי התצוגות;
  ברירת מחדל = Visual.
- **אימות:** `cd frontend/v9 && npm run build` (0 errors) + `npx playwright test
  tests/components/trades-view.spec.ts` (אם קיים — אחרת ליצור spec מינימלי שטוען את הדף).

---

## 4 · ארבעת צירי ה-UAT (CLAUDE.md) — לבלוק נתונים
1. **Quality:** אין trade עם R:R/קומולטיב מסונתז כשהמקור `null` (בדוק שמופיע `—`).
2. **Recency:** `cumulativeByClose` של הסט כולו = `SUM(pnl_usd)` מ-DB לאותם ids.
3. **Cardinality:** מספר השורות המוצגות == אורך הסט המסונן.
4. **Latency:** רינדור הרשימה ל-500 trades < 200ms (React profiler / `performance.now`).

---

## 5 · דוח חובה (חלק C בחוזה)
טבלת phases (Status + Evidence command+output + Deviation), שורת "if reverted → RED"
לכל טסט, סעיף **NOT DONE / DEVIATIONS** (גם אם "none"), ו-Open.

## 6 · עדכון roadmap (CLAUDE.md §Roadmap auto-update — חובה)
בסיום: עדכן `docs/plans/ROADMAP_TO_LIVE.html` (פריט "Trades UX redesign" → done +
פאזה) ו-`docs/plans/STATUS_BOARD.md` (שורת log מתוארכת עם finding+fix+verification).

---

## 7 · עצירה אסטרטגית
זה frontend-only ולכן אינו risk-surface — אבל אם phase כלשהו חושף צורך בשינוי backend/
endpoint/לוגיקה (למשל שדה חסר באמת) — **עצור ודווח** (B6), אל תרחיב בשקט.
