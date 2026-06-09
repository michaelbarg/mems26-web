# HANDOFF — עמוד Trades (עיצוב‑מחדש לכיול) · המשך לצ'אט הבא · 2026‑06‑04

> 🧰 **START HERE:** `docs/handoff/TRADES_REDESIGN_KIT_2026-06-04.md` — מסמך‑אב שמארגן את כל הערכה
> (החלטה · סדר · בעלות · חוזה · 2 פרומפטים מוכנים). מסמך זה הוא ההקשר המלא שמאחוריו.

**מצב:** עיצוב הושלם (read‑only). **לא מומש קוד עדיין.** scope **הוכרע** (Michael 2026‑06‑04):
Frontend‑שלב‑1 עכשיו + G1 במקביל (§5). בעלות + חוזה‑ממשק G1 ב‑§5a/§5b — קריאת‑חובה לכל סוכן
לפני שנוגעים בקוד, כדי שלא תהיה עבודה כפולה. כל מה שצריך כדי להמשיך נמצא כאן.

---

## 1. מה הצ'אט הזה עשה
חקירה read‑only + עיצוב‑מחדש של `/trades` כ‑משטח **הסקת‑מסקנות לכיול** (לא רק רשימה).
שלושה תוצרים (ב‑`docs/plans/`):
1. **`TRADES_PAGE_REDESIGN_2026-06-03.md`** — מסמך‑עיצוב מלא: שאלות‑מפתח → פאנלים →
   layout → מיפוי שדות אמיתיים מול חסרים → **gap‑list ל‑backend (§7 שם, G1–G7)**.
2. **`TRADES_PAGE_REDESIGN_MOCKUP_2026-06-03.html`** — mockup סטטי (שפת BUILD_STATUS).
3. **`TRADES_PAGE_PROTOTYPE_2026-06-03.html`** — **prototype אינטראקטיבי** עם הטוקנים
   האמיתיים מ‑`globals.css`; פילטרים/טאבים/drill‑down עובדים; אגרגציה client‑side חיה
   מעל נתוני‑דמה; ציר price/time מדויק (סקאלה ליניארית). אומת: `render()` ללא שגיאות,
   BE/Scratch מאוכלסים, השוואת exec‑mode (הכל 68% → ירי‑אחד 75% win).

תיעוד עודכן: `STATUS_BOARD.md` (לוג 2026‑06‑04) + `ROADMAP_TO_LIVE.html` (item + "עודכן").

## 2. ארבע התוספות של Michael — כולן שולבו בעיצוב+prototype
1. **date‑presets**: היום‑רציף(RTH)/אתמול/7/30/MTD. client‑side אך **חובה ET‑aware**;
   "רציף(RTH)" צריך חלון 09:30–16:00 ET מ‑`services/session_boundary/manager.py` (G6).
2. **Execution mode** (סימולטני מול "ירי אחד בכל פעם"): **כבר קיים** ב‑
   `frontend/v9/src/v9/lib/tradeAuxStatus.ts` → `isParallel`/`liveEligible`/`blockedBy`.
   רק להבליט כ‑toggle ראשי + רצועת‑השוואה (היום קבור תחת "More").
3. **ציר price/time פר‑עסקה**: נקודות‑אירוע אמיתיות (entry/T1/T2/T3/stop/exit + ה‑ts שלהן)
   = עמודות ממשיות, אפס סינתזה. **לא לדחוס מתחת ל‑R‑path** (יצא "מרוח") — פאנל ממוסגר נפרד.
   קו‑מחיר מלא בין אירועים = G7 (סדרת ברי‑5ד׳).
4. **התנהגות‑סטופים בתחתית**: פאנל ייעודי למטה (BE/static/T1_NO_BE) + תובנת‑כיול.

## 3. עובדות‑קוד שאומתו (אל תסרוק מחדש)
- **מודל** `backend/v9/db/models/trades.py` `V9Trade`: עמודות ממשיות = mode, firing_system,
  direction, state, entry_ts/price, stop, t1/t2/t3, t{1,2,3}_hit_ts, stop_hit_ts,
  exit_ts/price/reason, pnl_usd, pnl_r, outcome(WIN/LOSS/BE), quality(JSON), cross_context(JSON),
  sierra_bracket_id, is_synthetic. **אין** עמודות pattern/day_type/killzone/MAE/MFE.
- **נגזרים ב‑runtime** (`services/trade_context.py`): pattern_id/day_type/classification/
  trigger/confidence/systems_agreement — מתוך quality+cross_context JSON. **לא ל‑GROUP_BY ב‑SQL.**
- **MFE/MAE** (`services/trade_excursion.py`): מחושב on‑the‑fly מ‑`v9_bars_5min` (5ד׳, לא tick),
  מחזיר hi/lo מצרפי בלבד (לא סדרת‑ברי).
- **API** `backend/v9/api/v9/trades.py`: `GET ""`(list, limit≤1000), `/recent`, `/active`,
  `/{id}`, `POST ""`/`/log`/`/{id}/exit`. **אין endpoint אגרגציה.**
- **Frontend**: `app/trades/page.tsx` → `components/trades/TradesView.tsx` מרכיב:
  TradeFilters · EdgeKpiRow · PatternPerformanceStrip · TradeCardList · SelectedTradePanel ·
  TradeDetailsModal. **לא mounted**: EquityCurveStrip, TradesTable, TradesSummaryStrip, TradeRowExpand.
  `lib/api.ts:165 fetchTrades(mode?, limit=500)` — TradesView קורא ללא ארגומנטים (כל ה‑mode, 500 שורות).
  `stores/tradeStore.ts:57 mode:'ALL'` · `lib/tradeMath.ts` (equityCurveByClose/rLevels/stopMovement).
  טוקנים אמיתיים: `app/globals.css` (bg #0d1117, sys1 #58a6ff, sys2 #56d364, sys3 #d2a8ff,
  sys4 #fb950b, green #56d364, red #f85149).

## 4. חוב ידוע — מצב
- mode=SHADOW default → **✅ כבר ALL**. · WR%+R → **✅ נוסף ל‑EdgeKpiRow**.
- **⚠️ פתוח:** Scratch‑תמיד‑0 (ב‑`TradesSummaryStrip` הלא‑mounted; להגדיר דלי Scratch/BE מפורש).
- **⚠️ פתוח:** מסנן‑תאריך לקסיקלי (`tradeStore.ts:114‑118`, slice(0,10)) — לתקן ל‑ET‑aware.

## 5. ✅ ההחלטה — scope מימוש (הוכרע ע"י Michael 2026‑06‑04)
**DECIDED: שלב‑1 Frontend עכשיו + G1 במקביל.** רציונל: שלב‑1 נותן את כל הערך הנראה בלי
לגעת ב‑DB/risk/polling (המשטחים הרגישים‑לבטיחות לפני LIVE). G2–G7 הם follow‑up.

**⚠️ תיקון‑דיוק (אומת בקוד 2026‑06‑04, Rule 2):** הטענה הקודמת "killzone‑at‑entry לא נשמר"
**אינה מדויקת.** `trading_gateway._capture_cross_context()` (`:399‑410`) מצלם את כל 6
המערכות — כולל `killzone_system` — לתוך `cross_context` JSON **בזמן הכניסה**, ושומר ב‑INSERT
(`:414`). כלומר killzone/day_type/pattern **כבר נלכדים** (אם המערכת רשומה ב‑registry) — רק
קבורים ב‑JSON ולא ניתנים ל‑GROUP_BY. לכן G1 הוא בעיקר **promote JSON→עמודה אינדקסבילית**,
וברובו **backfillable** מ‑ה‑JSON. הסיכון‑שלא‑סובל‑דחייה מצטמצם לשדות שמערכת **לא** מצלמת בכניסה
→ זה מה ש‑VERIFY‑FIRST בפרומפט G1 בודק לפני שמוסיפים עמודות. מקור שותק → NULL, אפס סינתזה (Rule 1).

נדחו: **Backend‑first מלא** (migration + soak ממש לפני LIVE = סיכון מיותר) · **תכנון בלבד**
(העיצוב כבר קיים; אין צורך בסבב‑תכנון נוסף).

### 5a. חלוקת בעלות — מניעת עבודה כפולה (קריאה ראשונה לכל סוכן)
| מנה | בעלים | מצב | אסור לסוכן אחר |
|-----|-------|-----|----------------|
| **Frontend שלב‑1** (layout, Edge Matrix גנרי, presets, exec‑mode toggle, Heat, Target‑dist, mount EquityCurveStrip, price/time במודאל, פאנל סטופים, תיקון Scratch/BE) | סוכן‑Frontend | בביצוע | אל תיגע ב‑DB/endpoints/risk; ADAPT מ‑`PatternPerformanceStrip.tsx`, אל תיצור פאנל אגרגציה חדש |
| **G1** (קיבוע day_type/pattern/killzone(session)_at_entry כעמודות/JSONB בזמן‑כניסה) | CC (backend) | מוכן לפרומפט | זו העבודה היחידה ש"עוצרת דימום"; אל תתחיל G2–G7 לפניה |
| **G2–G7** (stats/equity/excursion/management‑log/TZ/path endpoints) | — | **DEFERRED follow‑up** | ⛔ אל תבנה עכשיו — חכה ש‑G1 + Frontend‑1 ינחתו |

### 5b. חוזה‑ממשק G1 (נקודת‑החיבור — כך שאף צד לא בונה מחדש)
זהו ה‑contract שמונע עבודה כפולה: Frontend ו‑Backend מסכימים על שמות‑השדות **מראש**, כך
שכש‑G1 ינחת, ה‑frontend רק יחליף "missing" בשדה האמיתי — בלי rework.
- שמות עמודות מוסכמים: `day_type_at_entry`, `pattern_id_at_entry`, `session_at_entry` (killzone).
- מקור שותק → **`NULL`**, לא סינתזה (Rule 1).
- **סימון‑חוסר ב‑runtime (לא רק בתיעוד):** עד ש‑G1 ינחת, ה‑frontend מרנדר את חיתוך
  killzone/day_type כ‑**"missing — pending G1"** במפורש. זה הסיגנל החי שאומר לכל מערכת
  שהדאטה חסרה — לא מסונתז, ולא "נראה כאילו עובד".
- ה‑Edge Matrix של שלב‑1 כולל את ציר killzone כעמודה **מנוטרלת/אפורה** עם תווית "pending G1",
  כך שכשהשדה יגיע אין צורך להוסיף UI — רק להפעיל את הציר.

## 6. gap‑list ל‑backend (קלט לפרומפט‑מימוש; פירוט מלא ב‑§7 של מסמך‑העיצוב)
- **G1 (root)** — לקבע day_type_at_entry / pattern_id_at_entry / session_at_entry כעמודות
  אינדקסביליות, מאוכלסות **מאותו `cross_context` snapshot** שכבר נלכד בכניסה (לא מקור שני),
  בלי סינתזה (מקור שותק → NULL). תנאי‑קדם ל‑G2–G4. פרומפט מוכן (verify‑first + seam‑map +
  anti‑tautological tests): `docs/handoff/CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md`.
- **G2** `GET /api/v9/trades/stats?group_by={system|pattern|day_type|killzone|direction}` (SQL מעל הקבוצה).
- **G3** `GET /api/v9/trades/equity` (נקודות by‑close + maxDD + rolling‑WR שרת‑צד).
- **G4** `GET /api/v9/trades/excursion_stats` (אגרגציית MAE/MFE; היום per‑row יקר).
- **G5** אכלוס `v9_trade_management_log` (Audit‑06‑01 F3 — היום ריק; ניהול הולך ל‑logger+cross_context).
- **G6** TZ מפורש על מסנן‑התאריך + presets + מסכת‑RTH.
- **G7** `GET /api/v9/trades/{id}/path` (סדרת ברי‑5ד׳ לקו‑מחיר מלא; אופציונלי).

## 7. Invariants
read‑only עד כה · **שום קוד לא מומש** · לא נגעתי ב‑risk‑logic / polling‑floors / DB · source‑of‑truth:
כל "חסר" = ⛔ ממתין ל‑backend, לא סונתז · localhost. **Michael מאשר scope (§5) לפני מימוש.**

## 8. הצעד הראשון בצ'אט הבא
ה‑scope כבר הוכרע (§5: Frontend‑1 now + G1 parallel). אין צורך לשאול שוב — להתחיל בביצוע:
1. **Frontend שלב‑1:** לפתוח מ‑`TradesView.tsx` + `tradeStore.ts`; Edge Matrix גנרי
   (ADAPT מ‑`PatternPerformanceStrip.tsx`, **לא** רכיב חדש) + presets (תיקון באג‑התאריך הלקסיקלי) +
   ציר killzone מנוטרל "pending G1" (§5b). smallest correct change, regression test לכל תיקון,
   אימות ב‑typecheck/build + diff (לא להריץ dev‑server בלי בקשה).
2. **G1 במקביל (CC):** לכתוב prompt לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti‑tautological
   tests + NOT‑DONE section) לקיבוע `day_type_at_entry`/`pattern_id_at_entry`/`session_at_entry`
   בזמן‑כניסה לפי חוזה §5b. מקור שותק → NULL, אפס סינתזה.
3. **אל תתחיל G2–G7** — DEFERRED (§5a). הם follow‑up אחרי ש‑G1 + Frontend‑1 ינחתו.
