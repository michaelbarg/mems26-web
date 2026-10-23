# תיקוני פרונט 23.10.2026 — 5 התיקונים + הסרת הקבצים המתים

> מבוסס על `docs/reports/FRONTEND_BACKEND_AUDIT_2026-10-23.md` (§3, §4, §6), באישור מייקל מהיום.
> מגבלות העבודה: בלי git, בלי ריסטארט, בלי `next build`, בלי `npm install`, בלי לגעת ב-`.env`. ה-dev server (`next dev`, hot-reload) המשיך לרוץ. המסחר רץ ב-DEMO (Sim1) לאורך כל העבודה.
> שום קובץ בנתיב ההחלטה (gateway / tree / trade_manager / systems/* / risk / sizing) לא שונה. קובץ backend אחד שונה — endpoint תצוגה בלבד (§1.3).

## 0. סיכום
| | |
|---|---|
| תיקונים | 5 מתוך 5. ארבעה פעילים כבר עכשיו (hot-reload). בתיקון 3, החלק בצד הבקאנד (`/key_levels`) ייכנס לתוקף רק בריסטארט הבא של הבקאנד (uvicorn רץ בלי `--reload`), והפרונט כבר מסמן את המקור עד אז |
| קבצים שנמחקו | 38 קבצי קוד (4,824 שורות) + 2 בדיקות Playwright של רכיבים שהוסרו + 6 קבצי `_INDEX.md` של תיקיות שנמחקו כולן |
| איחוד חנויות | `src/v9/store/` עבר ל-`src/v9/stores/`: העברה נקייה, 11 נתיבי ייבוא עודכנו |
| tsc | **4 שגיאות לפני, 4 אחרי**. אותן 4 שגיאות בדיוק, כולן קיימות מקודם (PriceDebugConsole:90, SpecFlags:27, TradeChart:133, api.ts:47) |
| עמודים אחרי השינוי | `/` 200 · `/board` 200 · `/trades` 200 · `/build` 200 |
| מה ייראה אחרת על המסך | (1) הבלוק "מערכת 6" בכרטיס העסקה מציג תקין/כשלים. (2) "P&L יומי" בפס-סיירה מציג את Sim1 (‎−$388.75 ב-19:57) במקום $0. (3) **באנר כתום חדש** "Daily loss $389/$250 (100%) · Sim1", כי התקרה בפרונט עדיין 250 קשיח (§4). (4) שבב ה-Killzone מציג `MIDDAY · low` במקום "— CLOSED". (5) קווי-אתמול הלבנים בגרף עברו ל-7714 / 7685.5 / 7698.25, הערכים שהעץ משתמש בהם |

## 1. חמשת התיקונים

### 1.1 הבלוק "מערכת 6 — פיקוח" בכרטיס העסקה הפעילה
- **קובץ:** `frontend/v9/src/v9/components/sidepanel/ActiveTradeCard.tsx:380` (`System6Block`). השימוש בשורה 329.
- **לפני:** הבלוק חיפש `checks/invariants/diagnostics` ו-`ruling/verdict`, ותמיד הציג "אין נתוני פיקוח". על 404 הוא הציג "ממתין ל-endpoint מ-CC".
- **אחרי:** הבלוק קורא `healthy` + `issues[]`, כמו `trades/TradeRecommendations.tsx`. שורת הכותרת היא "✓ הניהול תקין — לא אותרו כשלים" או "⚠ N כשלים בניהול העסקה", בצבע של החומרה הגבוהה ביותר. מתחתיה, לכל issue: כותרת בעברית (`CODE_TITLE`), חומרה ו-action, ו-`detail`. כש-`{error}` מגיע עם HTTP 200, או ב-404 או בשגיאת רשת, מוצגת הודעה שקטה "אין אבחון זמין — …". הטקסט "ממתין ל-endpoint מ-CC" נמחק. הבלוק מקבל `key` לפי מזהה העסקה, כך שעסקה חדשה לא מציגה את האבחון של הקודמת.
- **מקור אחד:** `TradeRecommendations.tsx` מייצא עכשיו את `S6Issue`, `S6Diagnose`, `CODE_TITLE` ו-`sevColor` (שורות 27, 34, 47, 81). שני הרכיבים קוראים את ה-endpoint באותה דרך.
- **ראיה (curl):** `GET /api/v9/s6/diagnose/3898` (עסקת-דמו שהייתה פתוחה בזמן העבודה) → `{"healthy":false,"issues":[{"code":"stop_too_wide","severity":"WARN","action":"ALERT","detail":"risk 14.25pt > cap 9.72pt"}]}`. ‏`.../3876` → `{"healthy":true,"issues":[]}`. ‏`.../999999999` → HTTP 200 `{"error":"trade 999999999 not found"}`.
- **הוסר באותו קובץ:** הכפתור "Move Stop" (ראה §2ב).

### 1.2 פס אמת-סיירה — P&L של החשבון שבו סוחרים
- **קבצים:** `components/layout/SierraTruthStrip.tsx:88,133–148,179`, וקובץ חדש `lib/accountPnl.ts` (78 שורות, משותף לפס ולבאנר).
- **לפני:** "P&L פתוח" ו-"P&L יומי" נקראו תמיד מ-`acct_open_positions_pl` ו-`acct_daily_pl` של ה-Account Monitor. בדמו הוא מסתכל על חשבון אחר (`acct_is_sim:0` מול `is_sim:1` / `trade_account:"Sim1"`), ולכן הוצג $0.00.
- **אחרי:** הכלל ב-`pickAccountPnl`:
  - כש-`acct_is_sim === is_sim` (אותו סוג חשבון): הערכים של ה-Account Monitor, כמו בפסיקה מ-07-28.
  - כשהם שונים: `open_pnl` / `daily_pnl` של `trade_account` (‏Sim1), ותג צהוב "מוניטור-חשבון ≠ Sim1" עם הסבר בטולטיפ.
  - `acct_ok=false`: "—", כמו קודם.
  - "שווי חשבון" / "מזומן" / "פנוי למסחר" מוצגים רק כשה-Monitor מתאר את החשבון שבו סוחרים. אחרת "—".
  - `fmt` ו-`money` מחזירים "—" לכל ערך לא-סופי או ‎|v| ≥ 1e15, כך ש-DBL_MAX ‏(1.797e308) לעולם לא מוצג כמספר.
- **ראיה:** `GET /api/v9/account/state` ב-19:57 → `trade_account:"Sim1", is_sim:1, acct_is_sim:0, daily_pnl:-388.75, acct_daily_pl:0.0, acct_account_value:null`. ב-`sierra_state.json` הגולמי ערכי cash/value/available/margin הם `1.797…e308`, והבקאנד הופך אותם ל-null. הרצה של `pickAccountPnl` על ה-payload החי (Node, type-stripping) נתנה `{"open":0,"daily":-388.75,"source":"trade_account","monitorMismatch":true,"account":"Sim1"}`. בדיקת `finiteOrNull(1.797e308)` החזירה `null`.

### 1.3 רמות סותרות על אותו מסך — ה-VA של אתמול, סיווג ה-IB וה-POC
**המקור של העץ:** `tpo_routes._load_previous_cash_session()` (‏`v9_tpo_sessions`, ‏`session_type='CASH'`). ל-22.10: ‏VAH 7714.0 / VAL 7685.5 / POC 7698.25. אומת: `/tree/state` → `context.prev_va = [7685.5, 7714.0, 7698.25]`, ו-`/tpo/previous_day` → אותם ערכים בדיוק. בלוק ה-`previous_session` של סיירה (‏`/key_levels`, ‏`/tpo/current`) נותן 7732.75 / 7686.75 / 7709.75.

| מה | קובץ:שורה | לפני → אחרי |
|---|---|---|
| קווי-אתמול הלבנים בגרף | `components/chart/v5b/ChartV5b.tsx:879–899` | **לפני:** הגרף העדיף את ה-`previous_session` של סיירה, ו-`/tpo/previous_day` שימש רק כשערך לא היה תקין. **אחרי:** הגרף מעדיף את שורת ה-CASH ב-DB (‏`/tpo/previous_day`, שכבר נמשך), כלומר את הערכים של העץ. ה-block של סיירה הוא גיבוי רק כשאין שורה תקינה ב-DB. `prevSource` נוסף ללוג `[ChartV5b] TPO loaded`. השינוי חי כבר עכשיו: 7714 / 7685.5 / 7698.25 |
| `/key_levels` (בקאנד, endpoint תצוגה) | `backend/v9/api/v9/key_levels_routes.py:162–202,256–258,282` | **לפני:** `prev_day.poc/vah/val` מ-Sierra `previous_session`. **אחרי:** מ-`_load_previous_cash_session()`, באותה שורה שהעץ משתמש בה (import עצל + try/except). הערכים של סיירה נשמרים ב-`prev_day.sierra_poc/vah/val`. `sources.prev_day_va` הוא `"db.v9_tpo_sessions CASH (…)"`, או `"sierra.… — fallback, no DB row"` כשאין שורה. **ייכנס לתוקף רק בריסטארט הבא** (‏uvicorn בלי `--reload`; לא ביצעתי ריסטארט) |
| תווית המקור | `hooks/useKeyLevels.ts:56,63,112` · `components/strips/KeyLevelsStrip.tsx:231` · `components/systems/KeyLevelsCard.tsx:101` | `useKeyLevels` שומר עכשיו גם את `sources`. ‏`prevVaSource()` מתייג את בלוק ה-YEST: **"Sierra ≠ עץ"** (צהוב) עד הריסטארט, ו-**"DB = עץ"** (ירוק) אחריו, כשהטולטיפ מציג גם את ערכי סיירה |
| סיווג ה-IB (‏WIDE מול NORMAL) | `KeyLevelsStrip.tsx:163` · `KeyLevelsCard.tsx:117` · `components/systems/DayTypeLensContent.tsx:99` | ב-Key Levels נוסף טולטיפ: "סיווג מוחלט, ספים 15/25 נק'". בעדשת S1 התווית שונתה ל-"IB (מסווג)", עם טולטיפ: "classify_replay — אחוזון יחסי להיסטוריה". ‏EXTREME (המנוע הישן, `/day_type/v9/history`) לא מוצג היום באף מקום בפרונט: לשונית ה-Hist היא placeholder |
| ה-POC של היום (7660 מול 7671) | `components/strips/DirectionStrip.tsx:83` · `KeyLevelsStrip.tsx:12` | בשורת-הכיוון: `POC` → **`POC(DB)`**, עם טולטיפ "שורת היום ב-v9_tpo_sessions — עלול לפגר". ב-TODAY POC של Key Levels: טולטיפ "סיירה Study ID:3, חי". כרגע שני המקורות מראים 7681.25 |

**הוכחה שהשינוי ב-`/key_levels` לא נוגע בהחלטות (grep):**
- `get_key_levels` לא מיובא בשום מקום. מהמודול הזה מיובאים רק `router` (ב-`app.py:33`) ו-`_load_sierra_tpo` (ב-`trade_manager/manager.py:2219`, עבור prior_day H/L). את `_load_sierra_tpo` לא שיניתי, וגם לא את שורת ה-import שלו.
- אף קוד בבקאנד, בגשר או ב-render_mobile_relay לא קורא ל-`/api/v9/key_levels` ב-HTTP. רק `scripts/sot_health.py` (בודק `today.ib_*`, שלא השתנה) ו-`scripts/mems26_preflight.sh` (מחפש `dll_missing` ב-`prev_day_ib`, שלא השתנה).

**בדיקה offline:** `/tmp/fe_fix_backup/test_key_levels.py` טוען את המודול מהקובץ עם תלויות מדומות, בתהליך Python 3.9 נפרד. התוצאות:
- כשיש שורה ב-DB: 7698.25 / 7714.0 / 7685.5, ‏`session_date` = "2026-10-22", המקור `db…`, ו-`sierra_*` = 7709.75 / 7732.75 / 7686.75.
- כשאין שורה, או כש-DB זורק שגיאה: fallback לסיירה בלי שגיאה.
- `today` ו-`range` לא השתנו, ו-JSON נבנה תקין. **ALL OK**.

גיבוי המקור לפני השינוי: `/tmp/fe_fix_backup/key_levels_routes.py.orig`.

### 1.4 שבב ה-Killzone ב-TopBar
- **קובץ:** `components/layout/TopBar.tsx:29` (צבעים לפי edge), `:101` (הנתונים), `:190` (השבב).
- **לפני:** השבב האזין ל-`useSystemStore.signals` מ-`WS /ws/v9/signals/6`. ה-WS הזה לא שולח אף עדכון (אין Redis), ולכן השבב תקוע על "— CLOSED" באדום.
- **אחרי:** השבב קורא את `useSystemStateStore(s => s.systems[6])`. ה-store הזה נמשך כל 5 שנ' מ-`/cockpit/systems-snapshot`, וה-`raw` שלו הוא `/killzone/current`.
  - מוצג: אזור + edge (למשל `MIDDAY · low`). צבע לפי edge: high ירוק, medium כתום, low אפור, none (CLOSED/WEEKEND) אדום.
  - טולטיפ: שעת הסיום ב-ET, דקות שנותרו, והאזור הבא.
  - OPEN/CLOSED מוצג רק אם יגיע שדה gate: ‏`/killzone/current` לא חושף gate (ראה §4).
- **ראיה:** `/api/v9/killzone/current` ו-`systems-snapshot.systems["6"]` → `state:"MIDDAY", subState:"low", raw.current_zone {name:"MIDDAY", edge_class:"low", minutes_remaining:33}, next_zone NY_PM`. אין שדה `gate_open`.
- **הוסר:** `hooks/useSystemEvents.ts` + `stores/systemStore.ts`. לפני ההסרה אומת ב-grep שהקוראים היחידים היו TopBar (הוחלף), ‏`V9Dashboard.tsx:46` (הקריאה הוסרה), והקבצים המתים. הטענה בביקורת נכונה, וכך נחסכים 6 חיבורי WS שניסו להתחבר מחדש כל 5 שנ' בלי סוף.

### 1.5 באנר תקרת-ההפסד היומי
- **קובץ:** `components/banners/BannerStack.tsx:9–16` (קבועים + TODO), `:55` (מקור ה-P&L), `:70` (הטריגר).
- **לפני:** הבאנר קרא `gateway/status.daily_pnl`, שהוא `0.0` בדמו (`trades_today:0`) גם כשהחשבון בהפסד, ולכן הבאנר לא הופיע בדמו. הסף ‎−200 והתווית "/$250" היו קשיחים בתוך הקוד.
- **אחרי:**
  - P&L היום נלקח מ-`/api/v9/account/state` לפי אותו כלל של §1.2 (‏Sim1 בדמו). `gateway.daily_pnl` משמש רק כגיבוי, כשלסיירה אין מספר.
  - התקרה נשארת קשיחה ($250, אזהרה מ-$200, `DAILY_LOSS_CAP_USD` / `DAILY_LOSS_WARN_USD`), עם `// TODO backend: expose RISK_DAILY_LOSS_CAP`. הסיבה: אף endpoint של הדסקטופ לא מחזיר אותה. בדקתי את `/cockpit/heartbeat`, ‏`/gateway/status` ו-`/account/state`. רק `/mobile/data`, שדורש מפתח, מחזיר `halt_cap`.
  - הטקסט מציין את המקור: `Daily loss $389/$250 (100%) · Sim1`.
  - **ברירות-המחדל של הסיכון בבקאנד לא שונו.**
- **ראיה:** `gateway/status` → `daily_pnl:0.0, trades_today:0`. ‏`account/state` → `daily_pnl:-388.75` ‏(Sim1, 19:57). לכן הבאנר מופיע עכשיו.

## 2. הסרות

### 2א. קבצים שנמחקו (נתיב תחת `frontend/v9/` · שורות)
לפני כל מחיקה הרצתי את `/tmp/fe_fix_backup/check_dead.sh`. הסקריפט מחפש לכל קובץ: ייבוא לפי סוף-נתיב, `import()` / `require()` דינמיים, ואזכור של השם כמילה. החיפוש רץ ב-`src`, ‏`tests`, ‏`next.config.ts`, ‏`playwright.config.ts` ו-`public/*.html`, בלי הקבצים שברשימה עצמה. לא נמצא אף משתמש חי: רק הערות, ומשפט אחד בתוך `public/readiness.html`, שהוא דוח סטטי.

| קובץ | שורות | קובץ | שורות |
|---|---|---|---|
| `src/v9/components/chart/ChartV5a.tsx` | 831 | `src/v9/components/sidebar/tabs/PatternsTab.tsx` | 410 |
| `src/v9/components/chart/ChartArea.tsx` | 223 | `src/v9/components/sidebar/tabs/PerformanceTab.tsx` | 86 |
| `src/v9/components/chart/RightSideLabels.tsx` | 37 | `src/v9/components/sidebar/tabs/PredictionsTab.tsx` | 46 |
| `src/v9/components/chart/StaticLevels.tsx` | 54 | `src/v9/components/sidebar/tabs/SetupsTab.tsx` | 83 |
| `src/v9/components/chart/TPOLines.tsx` | 65 | `src/v9/components/sidebar/tabs/SystemsTab.tsx` | 100 |
| `src/v9/components/chart/TradeMarkerOverlay.tsx` | 150 | `src/v9/components/sidebar/tabs/TraderTab.tsx` | 113 |
| `src/v9/components/chart/VegasEMAs.tsx` | 63 | `src/v9/components/systems/DayTypePill.tsx` | 35 |
| `src/v9/components/chart/TimeframeSelector.tsx` | 77 | `src/v9/components/systems/FiveMinPill.tsx` | 43 |
| `src/v9/components/chart/v5b/CumulativeDeltaPane.tsx` | 136 | `src/v9/components/systems/FootprintPill.tsx` | 35 |
| `src/v9/components/volume/VolumePanel.tsx` | 111 | `src/v9/components/systems/WoodiesPill.tsx` | 41 |
| `src/v9/components/volume/VolumeDragHandle.tsx` | 83 | `src/v9/components/health/StreamHealthPanel.tsx` | 180 |
| `src/v9/hooks/useWebSocket.ts` | 15 | `src/v9/components/settings/SettingsDrawer.tsx` | 143 |
| `src/v9/lib/websocket.ts` | 75 | `src/v9/components/trades/TradeReviewPanel.tsx` | 286 |
| `src/v9/lib/mockData.ts` | 87 | `src/v9/components/trades/TradeMarkChart.tsx` | 373 |
| `src/v9/stores/chartSyncStore.ts` | 69 | `src/v9/components/atoms/StatusDot.tsx` | 25 |
| `src/v9/components/sidebar/LeftTabs.tsx` | 80 | `src/v9/stores/systemStore.ts` | 40 |
| `src/v9/components/sidebar/tabs/DayTab.tsx` | 94 | `src/v9/hooks/useSystemEvents.ts` | 67 |
| `src/v9/components/sidebar/tabs/DecisionsTab.tsx` | 120 | `src/v9/stores/marketStore.ts` | 66 |
| `src/v9/components/sidebar/tabs/MarketTab.tsx` | 195 | `src/v9/components/strips/ShadowSoakStrip.tsx` | 87 |
| **סה"כ קוד** | **38 קבצים, 4,824 שורות** (34 הקבצים של §4א = 4,564 שורות, ועוד systemStore, useSystemEvents, marketStore, ShadowSoakStrip) | | |

נמחקו גם:
- `tests/components/ss-pill.spec.ts` (21) ו-`tests/components/shadow-soak.spec.ts` (20): בדיקות Playwright של השבב "SS:" ושל ShadowSoakStrip, שהוסרו.
- קבצי `_INDEX.md` בתיקיות שהתרוקנו לגמרי, והתיקיות עצמן: `components/sidebar/`, ‏`sidebar/tabs/`, ‏`volume/`, ‏`health/`, ‏`settings/`, ‏`src/v9/store/`.

### 2ב. קוד מת שהוסר מתוך קבצים חיים
| קובץ | מה הוסר |
|---|---|
| `components/layout/TopBar.tsx` | הכפתורים "5 Min / Tick Rev": שינו את `layoutStore.activeChartType`, שרק VolumePanel ו-ChartArea המחוקים קראו. הכפתור 📚 הכפול: נשאר כפתור 📘 אחד שפותח את LibraryModal, עם title "Library (Journal / Spec / Settings)". ה-`ConnectionIndicator` השני: נשאר זה שבקצה השמאלי. בנוסף: הייבוא של `useSystemStore` וה-`useMemo` של הקילזון הישן |
| `components/sidepanel/ActiveTradeCard.tsx` | הכפתור "Move Stop": קפץ רק `alert('…not wired to the API yet')`. כפתור Exit נשאר |
| `components/layout/Layer0Strip.tsx` | השבב "SS:" (Suffering Side), ה-state שלו, והמשיכה ל-`/api/v9/veto/state` כל 15 שנ' (ה-SSV לא מוזן, ולכן תמיד הוצג "SS: NONE") |
| `components/layout/V9Dashboard.tsx` | הקריאה ל-`useSystemEvents()` והייבוא שלה, הרכיב `<ShadowSoakStrip />` והייבוא שלו, הייבוא בהערה של ChartV5a, והייבוא שלא היה בשימוש של `KeyLevelsStrip` |
| `components/chart/v5b/ChartV5b.tsx` | `useMarketStore` + `setMarketLevels(...)`. ה-store הזה רק נכתב ואף אחד חי לא קרא ממנו |
| `lib/api.ts` | `fetchBars5min`, ‏`fetchTickReversalBars`, ‏`fetchWoodiesBars`, ‏`fetchTPOBars`, ‏`fetchSignals`, ‏`fetchMarkers`, ‏`fetchConfigs`, ‏`fetchConfig`, ‏`updateConfig`, ‏`fetchDayTypeV9` + `DayTypeV9Response`, ‏`JOURNAL_API`. כולם אומתו ב-grep: אין קורא, או שהקוראים היו רק ChartArea / SettingsDrawer המחוקים. ‏`apiFetch` נשאר, כי `fetchTrades` משתמש בו |

### 2ג. איחוד `store/` לתוך `stores/`
`src/v9/store/systemStateStore.ts` הועתק אחד-לאחד (אומת ב-`cmp`) ל-`src/v9/stores/systemStateStore.ts`. 11 נתיבי ייבוא הוחלפו בפעולה אחת, כדי שלא יהיו שני מופעים של ה-store באמצע:
- `molecules/SwitcherSlot`, ‏`sidepanel/lens/plan/systemPlanLive`, ‏`layout/TopBar`, ‏`layout/Switcher`
- `systems/{KillzonePill, KillzoneLensContent, WoodiesLensContent, TPOPill, FootprintLensContent, TPOLensContent}`
- `hooks/useSystemStatePolling`

אחרי זה התיקייה `store/` נמחקה. זו העברה נקייה בלי שינוי בתוכן, ו-tsc נשאר 4.

## 3. מה נשאר, ולמה (מועמדים — מייקל מחליט)
| מה | למה נשאר |
|---|---|
| `/board`: ‏`StatusBoardPanel` (+‏`public/task_board.json` מ-22.07), ‏`ProposedDiffsPanel`, ‏`PagesPanel` (+‏`public/pages_index.json` מ-16.07), ‏`DailyPnlPanel` (קורא את חשבון 37138283, ולכן ריק בדמו) | לפי ההנחיה: "candidates, Michael decides" |
| `topbar/AgentHeartbeatDot.tsx` + `app/api/agent-heartbeat/route.ts` (קורא `AGENT_HEARTBEAT.json` מ-28.07) | הביקורת (§6b4) מציעה להסיר, אבל זה לא היה ברשימת ההסרות שאושרה לי. מועמד |
| השבב "News" ב-Layer0Strip (קורא `news_window`, שדה שלא קיים, ולכן תמיד "News —") | לא ברשימה שאושרה (רק "SS:"). להסיר, או לחבר ל-`/agent/news_calendar` |
| ב-TopBar: הבלוק "SHADOW: Nt $X" / "P&L / Trades" והפס "$X/$200" | `accountStatus` לא נקבע אף פעם, וגם לא היה נקבע לפני (הקובע היחיד היה ChartArea המת). הספירות מגיעות מ-tradeStore, שמתמלא רק כשפותחים את עדשת Trades. לא ברשימה שאושרה. להסיר, או להזין מ-`lib/accountPnl` (אותו מקור כמו הבאנר) |
| `layoutStore.activeChartType` / `setActiveChartType` (וגם `chartPercent`, ‏`settingsOpen`, ‏`activeTab` / `TabId` של הסרגל הישן) · `tradeStore.accountStatus` / `setAccountStatus` · טיפוסים ב-`types/` ששימשו רק את הקוד המחוק | state מת, לא מזיק (`layoutStore` נשמר ב-localStorage). ניקוי בהמשך |
| `PriceDebugConsole.tsx` · העמוד `/build` | הביקורת סימנה אותם "לא חובה" |
| `tests/components/tf-selector.spec.ts` | בודק `tf-btn-15m`, שלא קיים בשום מקום ב-src, כבר מלפני היום. לא נגעתי |
| `_INDEX.md` בתיקיות שנמחקו מהן חלק מהקבצים (‏`chart/`, ‏`chart/v5b/`, ‏`systems/`, ‏`trades/`, ‏`atoms/`, ‏`hooks/`, ‏`lib/`, ‏`stores/`, ‏`strips/`, ‏`components/`) ו-`SYSTEM_INDEX.md` | נוצרים ע"י `scripts/gen_index.py`, שמריץ `git log`, ולכן לא הרצתי אותו. **להריץ אחרי ה-commit** |

## 4. משימות המשך בבקאנד (לא בוצעו — נתיב החלטה, או דורשות ריסטארט / פסיקה)
1. **ריסטארט הבקאנד** יפעיל את השינוי ב-`/key_levels` (§1.3). עד אז Key Levels מציג את ה-VA של סיירה, עם התג "Sierra ≠ עץ".
2. **`RISK_DAILY_LOSS_CAP`:**
   - לחשוף את הערך ב-`/api/v9/gateway/status`, כדי שהבאנר יקרא אותו במקום 250 הקשיח.
   - לאחד את ברירות-המחדל של אותו env: ‏`gateway/risk_checks.py:34`=800 (הפסיקה מ-07-24), ‏`gateway/trading_gateway.py:5852`=450, ‏`api/v9/mobile_monitor.py:620`=400. בנוסף יש תקרות קבועות: ‏`services/risk_validator/validator.py:28`=250 ו-`systems/woodies/stages/a7_universal_checks.py:19`=200.
   - הערך האפקטיבי ב-.env לא נבדק (לא נוגעים ב-.env).
3. **`gateway.daily_pnl` = 0 בדמו** (‏`trades_today:0`), בזמן ש-Sim1 ב-‎−$388.75. ה-halt ב-`risk_checks.py:78` משתמש בו. צריך פסיקה אם תקרת ההפסד היומי צריכה לספור גם דמו.
4. **ה-Account Monitor של סיירה מסתכל על חשבון אחר** (‏`acct_is_sim=0` בזמן מסחר על Sim1). בנוסף, ערכי cash / value / available / margin הם DBL_MAX. אפשרויות: להפנות את ה-Monitor (DLL / Sierra) לחשבון המסחר, או לייצא את שם החשבון (`acct_trade_account`), כדי שההשוואה תהיה לפי שם ולא לפי `is_sim`.
5. **`/api/v9/killzone/current` לא חושף את ה-gate.** ‏`KillzoneSystem.gate_open` קיים ב-`systems/wrappers.py:364`, אבל `get_current()` לא מחזיר אותו. לכן השבב לא יכול להציג OPEN/CLOSED אמיתי (‏systems/* — לא נגעתי).
6. **ה-POC של `/day_type/direction_now`** מגיע משורת היום ב-`v9_tpo_sessions` (`systems/direction_context_live.py:137`) ועלול לפגר אחרי ה-POC החי של סיירה ושל העץ. לשקול מקור אחד (‏systems/* — לא נגעתי).
7. **שלושה סיווגי IB שונים:** ‏key_levels מוחלט 15/25, ‏classify_replay לפי אחוזון, ומכונת המצבים הישנה (`/day_type/current` → EXTREME). לבחור אחד לתצוגה.
8. **endpoints שאיבדו את הקורא היחיד שלהם בפרונט:** ‏`GET /api/v9/shadow/soak_progress` (stub), ‏`GET /api/v9/veto/state`, ‏`WS /ws/v9/signals/{1..6}`. מועמדים להסרה יחד עם §5 של הביקורת.

## 5. בדיקות
| בדיקה | תוצאה |
|---|---|
| `npx tsc --noEmit -p .` לפני (`/tmp/tsc_before.txt`) | **4** ‏`error TS` |
| `npx tsc --noEmit -p .` אחרי (`/tmp/tsc_after.txt`) | **4**. אותן ארבע שגיאות שהיו קודם, בלי שגיאה חדשה (‏`diff` על הקבצים בלי מספרי השורות → זהים) |
| ESLint על קבצים שנגעתי בהם (בלי ChartV5b, SierraTruthStrip, V9Dashboard, DayTypeLensContent ו-api.ts, שיש בהם הרבה שגיאות lint ישנות) | נקי, חוץ מאזהרה ישנה ב-`ActiveTradeCard.tsx:62` (exhaustive-deps של ה-effect המקורי) |
| ESLint על חמשת הקבצים עם השגיאות הישנות | כל השגיאות שם מסוגים שהיו קיימים לפני: `any`, ‏`Cell` שמוגדר בתוך render של SierraTruthStrip (מסומן בכל שימוש ב-`<Cell>`, ומספר השימושים לא השתנה), ו-setState / refs בתוך effect ב-V9Dashboard וב-ChartV5b. לא נוסף מופע חדש. ב-api.ts נמחקו כמה מופעים של `any` יחד עם ה-fetchers המתים |
| עמודים (`curl -m 20`) אחרי השינוי | `/` 200 · `/board` 200 · `/trades` 200 · `/build` 200 (ו-`/api/agent-heartbeat` 200) |
| לוג ה-dev server (`/tmp/frontend.log`, ‏`/tmp/frontend.err.log`, כולל שגיאות console שהדפדפן מעביר) | "✓ Compiled" אחרי כל עריכה. אין שגיאות runtime מהדפדפן. היה רק החריג שבסעיף 6 |
| `pickAccountPnl` / `prevVaSource` על ה-JSON החי (Node 24, type-stripping, קריאה בלבד) | ‏Sim1 ‎−388.75 / ‏`trade_account`. התווית של YEST היום: "Sierra ≠ עץ"; אחרי ריסטארט (מדומה): "DB = עץ" |

## 6. אירועים בזמן העבודה (שקיפות)
- **שגיאת קומפילציה רגעית, כ-5 שניות:** בין שתי עריכות רצופות ב-`KeyLevelsStrip.tsx`, הקבוע `IB_CLASS_TITLE` הוגדר פעמיים. ה-dev server הציג "Ecmascript file had an error" עד העריכה הבאה, שתיקנה את זה. הקומפילציה חזרה ל-✓, ו-`/api/agent-heartbeat` החזיר 500 פעם אחת באותו רגע ואז חזר ל-200. אם הדשבורד היה פתוח, ייתכן שהופיעה שכבת-שגיאה לרגע.
- **`npx eslint` רץ מחוץ לפרויקט:** ה-`&` גרם ל-`cd` לרוץ ב-subshell, ולכן `npx eslint` רץ מתיקיית הבית, ו-npx הוריד את eslint@10.13.0 למטמון המשתמש (`~/.npm/_npx/515228b7c8d004a2`). שום דבר בפרויקט לא השתנה: ‏`package.json`, ‏`package-lock.json` ו-`node_modules` עם אותם תאריכים כמו קודם. מחקתי את תיקיית המטמון שנוצרה, ו-`~/.npm/_npx` חזר ל-5 התיקיות שהיו בו. ההרצה החוזרת השתמשה ב-`node_modules/.bin/eslint` המקומי.
- **בלי git, בלי ריסטארט, בלי build, ובלי נגיעה ב-`.env`.** קבצי העבודה נמצאים ב-`/tmp/fe_fix_backup/` על ה-iMac: גיבוי `key_levels_routes.py.orig`, ‏`test_key_levels.py`, ‏`check_dead.sh`, ‏`dead_files.txt`, ‏`dead_files_wc.txt` ופלטי eslint. אפשר למחוק אותם אחרי ה-commit.
