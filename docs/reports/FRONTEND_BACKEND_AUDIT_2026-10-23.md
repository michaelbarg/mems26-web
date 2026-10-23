# ביקורת פרונט↔בקאנד 23.10.2026

> ביקורת קריאה-בלבד: בלי git, בלי עריכות קוד, בלי ריסטארט. המסחר רץ ב-DEMO ‏(Sim1) על ה-iMac.
> מקורות: `frontend/v9/src` (grep וגרף-ייבוא), ‏`backend/v9/api/v9` + ‏`/openapi.json` של הבקאנד החי, לוגי הגישה של היום (`/tmp/backend.log`, ‏`/tmp/backend.err.log`), ובקשות `curl -s -m 5` GET בודדות.

## 1. סיכום
| מדד | ערך |
|---|---|
| קריאות פרונט שנבדקו | 70 נתיבי REST ייחודיים (+2 WebSocket, ‏2 נתיבי Next, ‏2 קבצי JSON סטטיים), מול 153 נתיבי בקאנד |
| שבורות — מציגות מידע שגוי או לא עובדות | **6** |
| מיושנות — stub, נתונים ישנים או חשבון לא נכון | **11** |
| אי-עקביות — אותו נתון, ערכים שונים בנתיבים שונים | **5** |
| קבצי פרונט מתים | **34** מתוך 172 קבצי קוד (~4,560 שורות), ועוד 13 אלמנטים מתים בתוך קבצים חיים |
| נתיבי בקאנד שאף אחד לא קורא | **66** (49 בלי שום קורא בריפו + 17 שרק סקריפטים מפנים אליהם) |
| 404 היום | 4 נתיבים (9 קריאות) — כולם בדיקות-יד של סוכן, **לא מהפרונט** |

**מה הכי חשוב:**
1. בכרטיס העסקה הפעילה, בלוק "מערכת 6 — פיקוח" **אף פעם לא מציג כלום**. הבקאנד שולח `healthy/issues`, הרכיב מחפש `checks/ruling` — ורכיב אחר קורא את אותו endpoint נכון.
2. פס אמת-סיירה מציג P&L של חשבון אחר: בדמו "P&L יומי $0" כשבפועל Sim1 ב-**‎−$175**. גם באנר תקרת-ההפסד לא יופיע בדמו, והוא קשיח על $250 (בבקאנד יש 800 / 450 / 400).
3. על אותו מסך מוצגות **רמות סותרות**: ה-VA של אתמול (7732.75 מול 7714 שהעץ משתמש בו), סיווג ה-IB (WIDE / NORMAL / EXTREME), ה-POC (7660 מול 7671), והביטחון בסוג-היום (0% / 18% / 38%).
4. 20% מקבצי הפרונט מתים: הגרף הישן ChartV5a/ChartArea, הסרגל השמאלי הישן ו-4 Pills. בנוסף 6 חיבורי WebSocket לא מקבלים אף עדכון (אין Redis) — ולכן שבב ה-Killzone ב-TopBar תקוע על "— CLOSED".
5. ה-404 של היום אינם מהפרונט. אבל ל-66 מתוך 153 נתיבי הבקאנד אין קורא, והבקאנד קורא לעצמו ב-HTTP (‏`chop_score.py`: ‏6 × `requests.get` לכל חישוב), מה שמנפח את הלוג ומעמיס על השרת.

## 2. קריאות הפרונט מול נתיבי הבקאנד

**שיטה:** 70 נתיבי REST ייחודיים נאספו מ-`grep` על `frontend/v9/src` (בלי שורות הערה), והושוו מול 153 הנתיבים ב-`/openapi.json` החי ומול לוג-הגישה `/tmp/backend.log` (880K שורות מאז עליית הבקאנד היום). חיבורי WebSocket נרשמים בנפרד, ב-`/tmp/backend.err.log`.
**הסתייגות על הספירות:** ספירה של 1–3 היא כנראה בדיקה (probe) של הסוכן הקודם, לא של הדפדפן. ‏`woodies/signals`, ‏`tpo/current` ו-`chart/bars5min?limit=6|14` נקראים גם **ע"י הבקאנד עצמו**: ‏`backend/v9/systems/layer0/chop_score.py:24,64` שולח `requests.get("http://localhost:8000/...")`, וכך גם woodies_system / decision_tree / five_min_system / quality_tier / day_type/api. לכן הספירה שלהם מנופחת.
**מקרא:** † = הקורא נמצא בקובץ מת, שאף עמוד לא טוען (§4). ‏"מסך ראשי" = `/` → ‏`V9Dashboard` בתצוגת `main`.

### 2א. המסך הראשי (`/`)
| נתיב | קובץ:שורה | קיים בבקאנד? | היום (status×count) | פסק | הערה |
|---|---|---|---|---|---|
| `/api/v9/cockpit/heartbeat` | TopBar:46 · BannerStack:33 · LiveTradeOverlay:53 | כן | 200×3,639 | תקין | 3 רכיבים מושכים אותו בנפרד |
| `/api/v9/cockpit/systems-snapshot` | store/systemStateStore:49 | כן | 200×1,697 | תקין | כל 5 שנ'. ‏S1 מדולג בכוונה |
| `/api/v9/day_type/classify_replay?date=` | systemStateStore:65 · useLiveDayType:58 · DayTypeConditionsTable:65 · DayTypeLabelTab:79 | כן | 200×2,753 | תקין, כפול | ה-store מושך כל 5 שנ' וה-hook כל 30 שנ'. התאריך מחושב ב-Chicago ב-store וב-New_York ב-hook (§3) |
| `/api/v9/day_type/live` | systemStateStore:66 · useLiveDayType:60 · DayTypeConditionsTable:67 | כן | 200×2,752 | תקין, כפול | מחזיר רק `{day_type, source}` |
| `/api/v9/account/state` | SierraTruthStrip:68,196 · board/AccountStatePanel:83 | כן | 200×1,258 | תקין, שדות שגויים בדמו (§3) | ב-AccountStatePanel הכתובת `http://localhost:8000` קשיחה |
| `/api/v9/context/radar` | ContextRadar:53,126 · MultidayProfilePanel:96 | כן | 200×2,845 | תקין | כל 5 שנ', ‏0.24 שנ' לקריאה. ‏stage/conf/lock סותרים נתיבים אחרים (§3) |
| `/api/v9/context/multiday` | MultidayProfilePanel:87 | כן | 200×1,057 | תקין, כבד | ‏40KB, ‏0.47 שנ' לקריאה, כל 60 שנ' |
| `/api/v9/layer0/state` | Layer0Strip:40 | כן | 200×1,253 | שבור חלקית | השבב "News" קורא `d.news_window` — שדה שלא קיים (§3) |
| `/api/v9/veto/state` | Layer0Strip:59 | כן | 200×1,253 | מיושן | ‏SSV לא מקבל תוצאות ("0 recent outcomes"), ולכן מוצג "SS: NONE" תמיד |
| `/api/v9/day_type/opening_panel` | OpeningTypePanel:123 · OpeningTypeChip:55 | כן | 200×2,469 | תקין | |
| `/api/v9/open_type/current` | OpeningTypeChip:62 | כן | ~0 | תקין (גיבוי) | נקרא רק אם opening_panel נכשל |
| `/api/v9/tree/state` | TreeV3Strip:103 · NearestFireStrip:115,321 · TreeStarField:181 | כן | 200×2,478 | תקין | |
| `/api/v9/tree/next_fire` | NearestFireStrip:116 · TreeStarField:182 | כן | 200×1,233 | תקין | |
| `/api/v9/build/pattern-status` | NearestFireStrip:111,157 · BuildTreeView:494,1740,1856 · useBuildStatus:29 · usePatternFeed:78 | כן | 200×1,232 | תקין, כבד | ‏**93KB** בכל משיכה, כל 15 שנ' במסך הראשי |
| `/api/v9/chart/bars{1m,3m,5min,15m,30m,1h}` | ChartV5b:560,775,824 · TradeChart:31 | כן | 200×7,266 (5min) | תקין | חלק גדול מהספירה הוא קריאות-עצמיות של הבקאנד |
| `/api/v9/tpo/current` | ChartV5b:874 · systemStateStore:96 (גיבוי) | כן | 200×2,917 | תקין | כולל קריאות-עצמיות |
| `/api/v9/tpo/previous_day` | ChartV5b:875 | כן | 200×2 | תקין | נטען פעם אחת, בטעינת הדף |
| `/api/v9/killzone/current` | ChartV5b:969 · systemStateStore:97 | כן | 200×1,037 | תקין | אבל שבב ה-Killzone ב-TopBar לא משתמש בו (§3) |
| `/api/v9/cumulative_delta/current` | ChartV5b:544 · †CumulativeDeltaPane:40 | כן | 200×1,507 | תקין | |
| `/api/v9/woodies/chart` | WoodiesCciPanel:1069 · LsmaLine:23 | כן | 200×2,990 | תקין | |
| `/api/v9/chart/setup_markers` | SetupMarkersOverlay:81 | כן | 200×1,758 | תקין | |
| `/api/v9/day_type/direction_now` | useDirectionNow:30 (DirectionStrip, Switcher, BuildTreeView) | כן | 200×2,737 | תקין | ה-POC שלו שונה מזה של key_levels / tree (§3) |
| `/api/v9/key_levels` | useKeyLevels:68 (KeyLevelsStrip, KeyLevelsCard) | כן | 200×1,233 | תקין | ה-VA של אתמול שונה מזה שהעץ משתמש בו (§3) |
| `/api/v9/trades/active` | lib/api:180 (ActiveTradeCard 10 שנ', ‏DemoMonitor 5 שנ', ‏LiveTradeOverlay 5 שנ') | כן | 200×4,964 | תקין, משולש | 3 רכיבים מושכים בנפרד — הנתיב שהדפדפן קורא הכי הרבה |
| `/api/v9/trades/recent` | lib/api:174 (DemoMonitor, TradeHistoryStrip, Switcher) | כן | 200×2,175 | תקין | |
| `/api/v9/s6/diagnose/{id}` | ActiveTradeCard:402 · TradeRecommendations:162 | כן (alias) | 200×84 | **שבור (שדות)** | מחזיר `{trade_id,state,outcome,healthy,issues}`, וה-UI מחפש `checks/ruling` → מוצג תמיד "אין נתוני פיקוח" (§3) |
| `/api/v9/system6/diagnose` | DemoMonitor:215 · board/System6SupervisorPanel:45,83 | כן | 200×~1 | תקין | ב-DemoMonitor מוצג רק כשיש עסקה והפאנל פתוח |
| `POST /api/v9/trades/{id}/exit` | lib/api:63 (כפתור Exit ב-ActiveTradeCard) | כן | 0 | תקין | הבקאנד שולח CANCEL לסיירה, ורק אחר כך סוגר ב-DB |
| `/api/v9/gateway/status` | BannerStack:39 · DemoMonitor:308 · systemPlanLive:571 | כן | 200×1,227 | תקין | הבאנר "Daily loss $X/$250" קשיח בפרונט (§3) |
| `/api/v9/status` | DemoMonitor:305 · ShadowSoakStrip:20 | כן | 200×61 | מיושן חלקית | ‏`bridge.running=false`, ‏`event_bus.reachable=false`, ‏`audit.running=false` — בזמן שהגשר דוחף 50K POST (§3) |
| `/api/v9/shadow/today_wr` | TopBar:87 | כן | 200×1,121 | מיושן (משמעות) | נקרא "Shadow WR", אבל סופר את **כל** העסקאות בכל המצבים (`shadow_routes.py:33`) |
| `/api/v9/shadow/soak_progress` | ShadowSoakStrip:29 | כן (stub) | 200×3 | **להסיר** | ‏stub: תאריך התחלה קשיח 14.05, ‏`wr_7d=0.0`, ‏`trades_today=0` (`shadow_routes.py:58`). הפס מוסתר במצב demo ממילא |
| `/api/v9/agent/news_calendar` | NewsDropdown:29 · board/NewsCalendarPanel:26 | כן | 200×1,066 | תקין | ‏20KB; ‏`localhost:8000` קשיח |
| `/api/v9/live_price` (GET) | useLivePricePoll:23 | כן | 200×29 | תקין | גיבוי ל-WS |
| `WS /ws/v9/price` | usePriceStream:33 | כן | accepted ×7 | תקין | |
| `WS /ws/v9/signals/{1..6}` | useSystemEvents:21 (6 חיבורים) | כן | accepted ×7 לכל אחד | **מת** | אין Redis (`ws_manager.py:13`, פסיקה 28.08), ולכן אף `update` לא מגיע. ה-snapshot נזרק בפרונט |
| `/api/agent-heartbeat` (Next) | AgentHeartbeatDot:53 | קובץ | — | **מיושן** | קורא `docs/reports/AGENT_HEARTBEAT.json`, שנכתב לאחרונה ב-**28.07** |
| `POST /api/v9/agent/chat` | AgentChatWidget:83 (מותקן ב-`layout.tsx`, בכל עמוד) | כן | 0 | לא בשימוש | ‏`localhost:8000` קשיח; דורש ANTHROPIC_API_KEY |
| admin ×6 (`services/status`, `history/db_state`, `archive_state`, `last_gap_fill`, `services/{n}/start\|stop\|restart`, `history/gap_fill`) | SystemControlPanel:116–150 | כן | 0 | תקין | לא היה בשימוש היום (הפאנל סגור כברירת-מחדל) |

### 2ב. עדשות הפאנל הצדדי, תצוגות ועמודים אחרים
| נתיב | קובץ:שורה | קיים בבקאנד? | היום | פסק | הערה |
|---|---|---|---|---|---|
| `/api/v9/five_min/current` | FiveMinLensContent:28 · systemStateStore:93 (גיבוי) | כן | ~0 | תקין | נקרא רק כשהעדשה פתוחה |
| `/api/v9/footprint/current` | systemStateStore:94 (גיבוי) · †ChartV5a:279 | כן | ~0 | מיושן | ‏S3 מושבת לפני LIVE |
| `/api/v9/woodies/current` | systemStateStore:95 (גיבוי) | כן | ~0 | תקין (גיבוי) | |
| `/api/v9/day_type/v9/history` | DayTypeLensContent:170 | כן | 0 | מיושן | המנוע הישן: `ib_width_class:"EXTREME"`, כשהמסווג החדש אומר NORMAL (§3) |
| `/api/v9/gateway/decisions` | usePatternFeed:79 (עדשת Plan) · TreeStarField:180 | כן | 200×7 | תקין | |
| `/api/tree-board` (Next) | TreeStarField:171 (תצוגת 🌌 עץ) | קובץ | — | מיושן | קורא `render_mobile_relay/static/docs/data/tree_v3.json` מ-**05.10** |
| `/api/v9/trade_reviews` | TradeReviewTab:85 · †TradeReviewPanel:84 | כן | 0 | תקין | בתצוגת Trade Review. הכתיבה נעשית דרך iframe ‏`public/marker.html` |
| `/api/v9/trades` · `/api/v9/trades/{id}` | lib/api:169,204 (TradesView, TradeReviewTab, TradesTab, TradeRowExpand, TradeDetailsModal) | כן | 0 | תקין | העמוד `/trades` לא נפתח היום |
| `/api/v9/chart/replay` | DayTypeLabelTab:61 · †TradeMarkChart:248 | כן | 0 | תקין | בתצוגת Day Type |
| `/api/v9/account/daily_pnl` | board/DailyPnlPanel:38 | כן | ~0 | **מיושן** | קורא את חשבון הכסף-האמיתי **37138283** → ‏`rows:[]`, בזמן שהמסחר היום ב-Sim1 |
| `/api/v9/agent/backlog_board` + `/task_board.json` | board/StatusBoardPanel:48,60 | כן | ~0 | **מיושן** | נוצר מ-DEV_BACKLOG, ‏`updated: 2026-07-22`; גם ‏`public/task_board.json` מ-22.07 |
| `/api/v9/agent/proposed_diffs` + `POST apply_targets_diff` | board/ProposedDiffsPanel:20,31 | כן | ~0 | מיושן | ‏`{"diffs":[]}` — הסוכנים נעצרו ב-19.10 |
| `/pages_index.json` | board/PagesPanel:28 | קובץ סטטי | — | מיושן | מ-16.07 |
| `/api/v9/agent/sierra_live_check` | board/SierraLiveCheckPanel:23 | כן | 200×69 | תקין | ‏`localhost:8000` קשיח |
| `/api/v9/live_ledger` | board/LiveLedgerPanel:40,84 | כן | 200×2 | תקין | עובד גם על Sim1 (`trade_fills.json`) |

### 2ג. קריאות שקיימות רק בקוד מת (יוסרו יחד עם הקבצים, §4)
| נתיב | קורא (מת) | היום | הערה |
|---|---|---|---|
| `/api/v9/woodies/signals` · `/day_type/state` · `/tpo/sessions` | †ChartV5a:249,250,236 | ‏2,914 / 24 / 0 | הספירות מגיעות מהבקאנד עצמו ומסקריפטים, לא מהדפדפן |
| `/api/v9/health/streams` | †StreamHealthPanel:43 · †MarketTab:44 | ~0 | |
| `/api/v9/bars/{5min,tick_reversal,woodies,tpo}` (GET) · `/signals` · `/markers` | lib/api:91–106 — בשימוש רק ב-†ChartArea | 0 (‏`signals` 422×1 = probe) | |
| `/api/v9/configs` · `/configs/{id}/{mode}` (GET/PUT) | lib/api:229,256,259 — בשימוש רק ב-†SettingsDrawer | 0 | |
| `/api/v9/day_type/v9/current` | lib/api:253 ‏`fetchDayTypeV9` — אף אחד לא קורא לו | ~0 | ב-TopBar:66 כתוב שהנתיב "retired 06-22" |
| `POST /api/v9/trades/{id}/review` | †TradeMarkChart:303 | 0 | הכתיבה עברה ל-`marker.html` |

### 2ד. ה-404 של היום — לא מהפרונט
`/api/v9/flags` ×6, ‏`/api/v9/day-type/state`, ‏`/api/v9/bridge/status`, ‏`/api/v9/sierra_live_check` ×1 — **אף אחד מהם לא מופיע באף קובץ בריפו** (py/ts/tsx/js/sh/html). כלומר אלה בדיקות-יד של סוכן (כנראה הניסיון הקודם של הביקורת), לא באג בפרונט, ואין מה לתקן.

## 3. אי-סנכרון בשדות
(הערכים נלקחו מ-`curl` בודד ב-23.10, בין 18:15 ל-18:30 שעון ישראל, בזמן עסקת-דמו 3876 ‏SHORT ‏5@7686.75 ואחרי שנסגרה)

| שדה | רכיב | endpoint | מה הבקאנד שולח בפועל |
|---|---|---|---|
| `checks`/`invariants`/`diagnostics` + `ruling`/`verdict` | ActiveTradeCard.tsx:406–408 (הבלוק "מערכת 6 — פיקוח" בכרטיס העסקה) | `/api/v9/s6/diagnose/{id}` | `{"trade_id":3876,"state":"FILLED","outcome":null,"healthy":true,"issues":[]}` — אין אף אחד מהשדות שהרכיב מחפש, ולכן תמיד מוצג "אין נתוני פיקוח". ‏TradeRecommendations.tsx:196 קורא **את אותו endpoint** נכון (`healthy`/`issues`). גם הטקסט "ממתין ל-endpoint מ-CC" (שורה 450) כבר לא נכון |
| `news_window` | Layer0Strip.tsx:54 (השבב "News") | `/api/v9/layer0/state` | רק `chop_score, state, indicators, computed_at` → מוצג "News —" תמיד. נתוני החדשות נמצאים ב-`/agent/news_calendar` |
| `payload.session_phase` / `payload.gate_open` (אות של מערכת 6) | TopBar.tsx:92–99 (שבב Killzone) | `WS /ws/v9/signals/6` | אף `update` לא מגיע (אין Redis) → מוצג "— CLOSED" באדום כל הזמן. הנתון האמיתי כבר נמשך מ-`/api/v9/killzone/current` (`current_zone`) |
| `accountStatus.daily_pnl` / `trade_count` | TopBar.tsx:250 + הפס "$X/$200" (שורה 222) | אין — נקבע רק ב-†ChartArea.tsx:201 (WS `/ws/v9/account`) | לא נקבע אף פעם, ולכן מוצג "SHADOW: 0t $0" ו-"$0/$200" מתוך tradeStore — שמתמלא רק אם פותחים את `/trades` או את עדשת Trades |
| `acct_open_positions_pl`, ‏`acct_daily_pl`, ‏`acct_account_value`, ‏`acct_cash_balance`, ‏`acct_available_funds` | SierraTruthStrip.tsx:135–151 ("P&L פתוח", "P&L יומי", "שווי חשבון"...) | `/api/v9/account/state` | בזמן העסקה: `open_pnl:12.5` אבל `acct_open_positions_pl:0.0`. אחרי הסגירה: `daily_pnl:-175.0` אבל `acct_daily_pl:0.0`. ‏`acct_is_sim:0` מול `is_sim:1` ו-`trade_account:"Sim1"` — שדות ה-Account Monitor מתארים חשבון אחר. **בדמו הפס מראה $0 כשהיום ב-Sim1 הוא ‎−$175** |
| `ib_class` / `ib_width_class` (אותו IB של 27.75 נק') | KeyLevelsStrip.tsx:232 · OpeningTypePanel · DayTypeLensContent (היסטוריה) | `/key_levels` · `/day_type/opening_panel` + `/classify_replay` · `/day_type/v9/history` + `/day_type/current` | ‏**WIDE** / ‏**NORMAL** (pctile 0.345) / ‏**EXTREME** — שלוש תוויות לאותו IB על אותו מסך |
| ה-VA של אתמול (VAH / VAL / POC) | KeyLevelsStrip.tsx:174 (`prev_day`) מול העץ | `/key_levels` מול `/tree/state` (`context.prev_va`) ו-`/classify_replay` (`prior_vah/val`) | ‏7732.75 / 7686.75 / 7709.75 **מול** 7714.0 / 7685.5 / 7698.25 — פער של 18.75 נק' ב-VAH. המסך מציג "ערך של אתמול" אחר מזה שהעץ סוחר לפיו |
| `poc` של היום | DirectionStrip.tsx:77 ("POC …") מול KeyLevelsStrip / TreeV3Strip | `/day_type/direction_now` מול `/key_levels` (`today.poc`) ו-`/tree/state` | ‏**7660.0** מול **7671.0** — שני POC שונים על אותו מסך |
| ביטחון / שלב / נעילה של סוג-היום | ContextRadar.tsx:131–134 ("סוג יום … %", ובחלונית: stage / lock) | `/context/radar` מול `/status` מול `/classify_replay` מול `/day_type/current` | ‏radar: ‏B2, ‏0.0, ‏PENDING · ‏status: ‏B2, ‏0.18, ‏LOCKED · ‏classify_replay: ‏Normal_Variation, ‏0.38, ‏CLASSIFIED · ‏day_type/current: ‏C3, ‏0. הרדאר מציג "0%" |
| `today_wr_pct` | TopBar.tsx:87 (התג "WR: 41%") | `/api/v9/shadow/today_wr` | ‏`SELECT outcome FROM v9_trades WHERE date(created_at)=today` — כל המצבים יחד (27 עסקאות היום), לא רק צל ולא רק דמו |
| תקרת הפסד יומי | BannerStack.tsx:50–52 (טריגר ב-‎−$200, תווית "/$250") | `/api/v9/gateway/status` (`daily_pnl`) | ‏`daily_pnl:0.0, trades_today:0` גם אחרי ‎−$175 ב-Sim1 → הבאנר לא יופיע בדמו. בבקאנד יש 3 ברירות-מחדל שונות לאותו `RISK_DAILY_LOSS_CAP`: ‏800 (`risk_checks.py:34`, "Michael 07-24"), ‏450 (`trading_gateway.py:5808`), ‏400 (`mobile_monitor.py:620` — זה מה שהטלפון מציג); ובנוסף 250 (`risk_validator/validator.py:28`) ו-200 (`a7_universal_checks.py:19`) |
| התאריך `?date=` של המסווג | systemStateStore.ts:59 (Chicago) מול useLiveDayType.ts:16 (New_York) | `/day_type/classify_replay` | שני קוראים של אותו endpoint מחשבים "היום" בשני אזורי-זמן שונים; הבקאנד עובד ב-ET (`et_today`) |
| `bridge.running`, ‏`event_bus.reachable`, ‏`audit.running` | (לא מוצג כרגע; ‏DemoMonitor קורא רק `mode`) | `/api/v9/status` | ‏`false / false / false` ו-`streams_active:0/11`, בזמן שהגשר דוחף כ-50K POST לכל סוג בר. בדיקת ה-bridge ב-`status.py` מיושנת |

## 4. רכיבים / עמודים / חנויות מתים בפרונט

**שיטה:** גרף-ייבוא על כל 174 הקבצים (`import` / `require` / `import()`; ייבוא שנמצא בהערה לא נספר), החל מנקודות הכניסה `app/**/page.tsx`, ‏`layout.tsx` ו-`route.ts`. ‏**139 קבצים נטענים ו-36 לא**: ‏34 קבצי קוד (≈**4,560 שורות**) ועוד 2 קבצי בדיקה.

### 4א. קבצים שאף עמוד לא טוען (בטוח למחוק)
| קובץ (תחת `frontend/v9/src/v9/`) | למה מת | להסיר? |
|---|---|---|
| `components/chart/ChartV5a.tsx` (831 ש') | הייבוא שלו בהערה ב-`V9Dashboard.tsx:13` ("kept as backup"); הוחלף ב-ChartV5b | כן |
| `components/chart/ChartArea.tsx` (223), עם `RightSideLabels` (37), ‏`StaticLevels` (54), ‏`TPOLines` (65), ‏`TradeMarkerOverlay` (150), ‏`VegasEMAs` (63) ו-`TimeframeSelector` (77) | מחסנית-הגרף הישנה. רק ChartArea טוען אותם, ו-ChartArea עצמו לא נטען מאף מקום | כן |
| `components/chart/v5b/CumulativeDeltaPane.tsx` (136) | הוחלף ב-`CvdChartPane.tsx` | כן |
| `components/volume/VolumePanel.tsx` (111) + `VolumeDragHandle.tsx` (83) | אף אחד לא מייבא אותם | כן |
| `hooks/useWebSocket.ts` (15) + `lib/websocket.ts` (75) + `lib/mockData.ts` (87) + `stores/chartSyncStore.ts` (69) | בשימוש רק ב-ChartArea / VolumePanel המתים | כן |
| `components/sidebar/LeftTabs.tsx` (80) + 9 לשוניות ב-`sidebar/tabs/` (Day, Decisions, Market, Patterns 410 ש', Performance, Predictions, Setups, Systems, Trader — 1,247 ש') | הסרגל השמאלי הישן; הוחלף ב-SidePanel / Switcher | כן |
| `components/systems/DayTypePill.tsx`, ‏`FiveMinPill.tsx`, ‏`FootprintPill.tsx`, ‏`WoodiesPill.tsx` | ‏Switcher משתמש רק ב-KillzonePill, ‏TPOPill ו-OpeningTypeChip | כן |
| `components/health/StreamHealthPanel.tsx` (180) | אף אחד לא מייבא אותו (קורא `/health/streams`) | כן |
| `components/settings/SettingsDrawer.tsx` (143) | אף אחד לא מייבא אותו (קורא `/configs`) | כן |
| `components/trades/TradeReviewPanel.tsx` (286) + `TradeMarkChart.tsx` (373) | הוחלפו ב-TradeReviewTab + iframe ‏`public/marker.html` | כן |
| `components/atoms/StatusDot.tsx` (25) | אף אחד לא מייבא אותו | כן |
| `lib/__tests__/toETDate.test.ts`, ‏`tradeMath.test.ts` | קבצי בדיקה, לא קוד שרץ | להשאיר |

### 4ב. קוד מת בתוך קבצים חיים (13)
| קובץ | למה מת | להסיר? |
|---|---|---|
| `lib/api.ts:90–106,228–260` — ‏`fetchBars5min`, ‏`fetchTickReversalBars`, ‏`fetchWoodiesBars`, ‏`fetchTPOBars`, ‏`fetchSignals`, ‏`fetchMarkers`, ‏`fetchConfigs`, ‏`fetchConfig`, ‏`updateConfig`, ‏`fetchDayTypeV9`, ‏`JOURNAL_API` | בשימוש רק ב-ChartArea / SettingsDrawer המתים, או בכלל לא | כן |
| `hooks/useSystemEvents.ts` + `stores/systemStore.ts` | פותח 6 WebSocket ל-`/ws/v9/signals/{1..6}`, שאף פעם לא שולחים עדכון (אין Redis). הקורא היחיד הוא שבב ה-Killzone ב-TopBar. יש גם באג: ב-`onclose` התנאי `connectionsRef.current.size < 6` תמיד נכון אחרי ה-delete, ולכן יש ניסיון חיבור מחדש כל 5 שנ' בלי סוף | כן — ולהזין את שבב ה-Killzone מ-`systemStateStore.systems[6]` (כבר נמשך מ-`/killzone/current`) |
| `stores/marketStore.ts` | בקוד החי רק ChartV5b.tsx:231 **כותב** אליו (`setLevels`); כל מי שקורא ממנו מת | כן, כולל השורה ב-ChartV5b |
| `V9Dashboard.tsx:17` — ‏`import { KeyLevelsStrip }` | מיובא ולא מוצג (השורה עברה ל-SidePanel) | כן |
| TopBar — הכפתורים "5 Min / Tick Rev" (בערך שורות 170–190) | משנים `activeChartType`, שרק VolumePanel המת קורא. לחיצה לא עושה כלום | כן |
| TopBar — הכפתורים 📘 Playbook ו-📚 Library | שניהם קוראים ל-`setShowPlaybook(true)` ופותחים את אותו חלון | לאחד לכפתור אחד |
| TopBar — `ConnectionIndicator` מוצג פעמיים (משמאל ומימין) | כפילות | להשאיר אחד |
| TopBar — הבלוק "P&L / Trades" והפס "$X/$200" | ‏`accountStatus` לא נקבע אף פעם, ובדמו מוצג "SHADOW: 0t $0" (§3) | להסיר, או להזין מ-`/account/state` |
| ActiveTradeCard — הכפתור "Move Stop" (שורות 354–366) | מקפיץ `alert('Move Stop is not wired to the API yet')` | להסיר (או לחבר ל-`POST /trade/modify_target`) |
| ShadowSoakStrip (`strips/ShadowSoakStrip.tsx`) | מחזיר `null` כשהמצב אינו SHADOW (היום demo), והנתונים שלו stub | כן, יחד עם `/shadow/soak_progress` |
| Layer0Strip — השבבים "SS:" ו-"News" | ‏SSV לא מוזן, ו-`news_window` לא קיים (§3) | להסיר את שניהם, או לחבר |
| `topbar/AgentHeartbeatDot.tsx` + `app/api/agent-heartbeat/route.ts` | קורא `docs/reports/AGENT_HEARTBEAT.json`, שנכתב לאחרונה ב-28.07 (פתק על לונג ידני מיולי) | כן (הסוכנים נעצרו ב-19.10) |
| `PriceDebugConsole.tsx` | פאנל דיבאג, מוסתר כברירת-מחדל (נפתח מהמקלדת) | לא חובה |

### 4ג. עמודים, חנויות וקבצים סטטיים
| קובץ | למה מת / מיושן | להסיר? |
|---|---|---|
| `app/build/page.tsx` (`/build`) | מציג רק את `BuildTreeView` — אותו רכיב שכבר מוצג בלשונית "Build Status" (`/?view=build_status`). מקושר רק מ-`public/pages_index.json` | לא חובה (כפילות) |
| `/board` → `DailyPnlPanel` | קורא את חשבון הכסף-האמיתי 37138283, ולכן ריק בדמו (§2ב) | להפנות לחשבון הפעיל, או להסיר |
| `/board` → `StatusBoardPanel` + `public/task_board.json` | לוח-משימות מ-22.07 (DEV_BACKLOG) | כן (או להזין מ-TASK_LOG הנוכחי) |
| `/board` → `ProposedDiffsPanel` | ‏`{"diffs":[]}` — מנגנון הסוכנים שהופסק ב-19.10 | כן, כל עוד הסוכנים כבויים |
| `/board` → `PagesPanel` + `public/pages_index.json` | אינדקס מ-16.07; כולל `http://localhost:8000/docs` | לרענן או להסיר |
| `src/v9/store/` מול `src/v9/stores/` | אין כפילות תוכן. ב-`store/` יש קובץ אחד חי (`systemStateStore.ts`, 15 צרכנים). ב-`stores/` יש 6 קבצים: `chartSyncStore` מת, ‏`marketStore` כתיבה-בלבד, ‏`systemStore` מוזן רק מ-WS מת. כלומר יש שני מושגים מקבילים של "מצב מערכות" (`systemStore` ו-`systemStateStore`) | למחוק את 3 המתים ולהעביר את `systemStateStore.ts` ל-`stores/` — תיקייה אחת |
| `public/readiness.html` (1.6MB, 23.09) | צילום סטטי ישן שמפנה ל-`localhost:6379` (Redis, שלא קיים). מקושר מ-SidePanel.tsx:105 | לרענן, או להסיר את הקישור |
| `public/system6.html`, ‏`public/trade-review.html` | אף רכיב ב-`src` לא מקשר אליהם | כנראה להסיר (לוודא מול מייקל) |
| התצוגה "🌌 עץ" (`TreeStarField`) | נתוני העץ מגיעים מקובץ סטטי מ-05.10 (`tree_v3.json`), לא בזמן אמת | להשאיר, ולהריץ `scripts/tree_measure.py` או לסמן "נכון ל-05.10" |

### 4ד. כתובת backend קשיחה במקום `getApiBase()`
36 קבצים מגדירים בעצמם `const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'`, ורק 7 משתמשים ב-`getApiBase()` מ-`lib/api.ts`. ‏8 קריאות כותבות את הכתובת המלאה בתוך ה-fetch: ‏AgentChatWidget:83, ‏NewsDropdown:29 ו-board/{SierraLiveCheckPanel:23, NewsCalendarPanel:26, AccountStatePanel:83, ProposedDiffsPanel:20,31, StatusBoardPanel:48}. ב-8 קבצים יש גם ערך-ברירת-מחדל קשיח לטוקן (`'michael-mems26-2026'`), והוא נשלח לדפדפן. כל זה עובד רק כשהדפדפן רץ על ה-iMac עצמו: אם פותחים את `:3000` ממכונה אחרת, כל הקריאות הולכות ל-localhost **של המכונה ההיא**.

## 5. נתיבי בקאנד שאף אחד לא קורא
ב-`/openapi.json` יש 153 נתיבים (ועוד 10 נתיבי WebSocket). ל-**66** מהם אין קורא חי בפרונט, והם גם לא נקראים מהגשר, מהטלפון או מקריאה-עצמית של הבקאנד. החיפוש כיסה גם את `scripts/`, ‏`tools/`, ‏`bridge/`, ‏`render_mobile_relay/`, ‏`sc_study/` ו-`launchagents/`.

**5א. 49 נתיבים בלי שום קורא בריפו (0 קריאות היום)** — מועמדים להסרה:
- תאימות-יומן ישנה (`backend/main.py`, ‏journal_compat_router): `GET /analytics/setups/recent`, ‏`/analytics/setups/today_summary`, ‏`/analytics/setups/sequential_today_summary`, ‏`GET /trades/log`, ‏`POST /api/v9/trades/log`.
- מנוע סוג-היום הישן: `GET /day_type/current` (ב-TopBar:66 כתוב "retired 06-22", ובכל זאת הוא עדיין מחזיר `stage:C3, ib_width_class:EXTREME`), ‏`/day_type/v9/current`, ‏`/day_type/history`, ‏`/day_type/v9/stats`.
- מערכות ישנות או מושבתות: `/five_min/{fire,setups,stats,nt_skip_stats}`, ‏`/footprint/{fire,journal}`, ‏`POST /bars/footprint` (S3 מושבת), ‏`GET|POST /woodies/fire`, ‏`/reversal/{current,history}`, ‏`/behavior_phase/current`, ‏`/chop_score/current` (הפרונט משתמש ב-`/layer0/state`), ‏`/clock/now`, ‏`/tpo/journal`, ‏`/tpo/sessions`, ‏`/missed-trades`, ‏`GET /trade/result`.
- היסטוריה: `/history/{dates,yesterday,{date}}`, ‏`POST /history/archive_now`.
- כפילויות: `GET /system6/diagnose/{trade_id}` (הפרונט משתמש ב-alias ‏`/s6/…`), ‏`GET /s6/diagnose` (בלי id), ‏`GET /live_ledger/` (עם לוכסן בסוף).
- ‏catch-all: ‏`GET /api/v9/{system_name}/health` (`shadow_routes.py:163`) — תופס כל `/api/v9/<מילה>/health`.
- נתיבים שרק הקוד המת בפרונט קרא (§2ג): `GET /bars/{5min,tick_reversal,woodies,tpo}`, ‏`GET|POST /signals`, ‏`GET|POST /markers`, ‏`GET|PUT /configs…`, ‏`/health/streams`, ‏`GET /trades/{id}/timeline`, ‏`POST /api/v9/trades`.

**5ב. 17 נתיבים שרק סקריפטים / כלים מפנים אליהם (0 קריאות היום)** — להשאיר, או למחוק יחד עם הסקריפט:
`/audit/{events,replay,stats}` (ולפי `/status`: ‏`audit.running=false, events_in_db=0`), ‏`/spec/status`, ‏`/gateway/risk`, ‏`/day_type/stats`, ‏`/woodies/patterns`, ‏`POST /trade/command`, ‏`POST /trade/debug_gateway_fire` (**נתיב דיבאג שיורה עסקה** — כדאי לחסום), ‏`POST /gateway/route_setup`, ‏`POST /trade/modify_target`, ‏`POST /pre_fire/validate`, ‏`GET|POST /admin/kill`, ‏`POST /admin/resume` (מתג-חירום שאין לו כפתור בדסקטופ; בטלפון משתמשים ב-`/mobile/flatten|pause|resume`), ‏`/ws/status`, ‏`POST /day_type/process`.

**5ג. בשימוש ע"י לקוחות שאינם הפרונט** — להשאיר:
- גשר סיירה: 9 × `POST /api/v9/bars/*` (כ-50K כל אחד היום), ‏`POST /api/v9/live_price` (151K).
- הטלפון: `GET /api/v9/mobile/data` (63K), ‏`/mobile`, ‏`POST /mobile/{flatten,pause,resume,gate_override}`.
- סקריפטים ובדיקות-בריאות: `/api/v9/health` (104), ‏`/health` (38), ‏`/day_type/state` (24 — ‏morning_briefing / s6_eod_report / fire_drill / readiness.html).
- **הבקאנד קורא לעצמו ב-HTTP:** ‏`chop_score.py:64` שולח 6 × `requests.get` סינכרוניים ל-`localhost:8000` בכל חישוב (`woodies/signals` ×2, ‏`tpo/current` ×3, ‏`chart/bars5min?limit=6|14`). כך גם `woodies_system.py`, ‏`decision_tree.py`, ‏`five_min_system.py`, ‏`quality_tier.py`, ‏`day_type/api.py`, ‏`behavior_phase/routes.py` ו-`history_routes.py`. זה לא באג בפרונט, אבל זה מנפח את הלוג ומעמיס על ה-threadpool של אותו שרת.

## 6. ההצעה למייקל

### (a) לתקן עכשיו — דברים שמציגים מידע שגוי
1. **הבלוק "מערכת 6" בכרטיס העסקה תמיד ריק.** ‏`frontend/v9/src/v9/components/sidepanel/ActiveTradeCard.tsx:406–408,450` — לקרוא `healthy` + `issues` (כמו `trades/TradeRecommendations.tsx:196`) במקום `checks/ruling`, ולמחוק את הטקסט "ממתין ל-endpoint מ-CC".
2. **פס אמת-סיירה מציג $0 בדמו.** ‏`layout/SierraTruthStrip.tsx:135–151` — כש-`acct_is_sim ≠ is_sim` (כלומר ה-Account Monitor מסתכל על חשבון אחר), להציג את `open_pnl`/`daily_pnl` של הפוזיציה ולסמן "חשבון-מוניטור ≠ Sim1". אחרת להשאיר "—". בצד הבקאנד: `backend/v9/api/v9/account_state_routes.py`.
3. **רמות סותרות על אותו מסך:** ה-VA של אתמול (`/key_levels` ‏7732.75 מול 7714.0 של העץ), סיווג ה-IB (WIDE / NORMAL / EXTREME) וה-POC (‏`/direction_now` ‏7660 מול 7671). צריך לבחור בבקאנד מקור אחד — זה שהעץ משתמש בו — ולגזור ממנו את `key_levels_routes.py`, ‏`day_type/direction_now` ו-`/day_type/current`.
4. **שבב ה-Killzone ב-TopBar תקוע על "— CLOSED".** ‏`layout/TopBar.tsx:92–99` — להזין אותו מ-`useSystemStateStore(s => s.systems[6])`, שכבר נמשך מ-`/killzone/current`. אחר כך למחוק את `hooks/useSystemEvents.ts` ואת `stores/systemStore.ts`: ‏6 חיבורי WebSocket שלא מקבלים נתונים, עם באג של ניסיון חיבור מחדש בלי סוף.
5. **תקרת ההפסד בבאנר קשיחה ולא מופיעה בדמו.** ‏`banners/BannerStack.tsx:50–52` (‏‎−$200 / "$250") — לקרוא את התקרה מהבקאנד. ל-`RISK_DAILY_LOSS_CAP` יש בקוד 3 ברירות-מחדל שונות: ‏`gateway/risk_checks.py:34`=800, ‏`trading_gateway.py:5808`=450, ‏`mobile_monitor.py:620`=400. צריך לאחד אותן, ולהחליט אם `gateway.daily_pnl` סופר גם דמו.
6. תיקונים קטנים: `layout/Layer0Strip.tsx:54` (‏`news_window` לא קיים); ‏`TopBar.tsx:87` (התווית "WR" צריכה להבהיר שזה כל המצבים, או לסנן לפי mode ב-`shadow_routes.py:33`); ‏`TopBar.tsx:250` (בלוק P&L/Trades שאף אחד לא מזין); ‏`store/systemStateStore.ts:59` מחשב את התאריך ב-Chicago, ו-`hooks/useLiveDayType.ts:16` ב-New York — לאחד ל-ET.

### (b) להסיר — קוד מת שאף עמוד לא טוען
1. מחסנית-הגרף הישנה (≈2,080 ש'): `components/chart/{ChartV5a,ChartArea,RightSideLabels,StaticLevels,TPOLines,TradeMarkerOverlay,VegasEMAs,TimeframeSelector}.tsx`, ‏`chart/v5b/CumulativeDeltaPane.tsx`, ‏`components/volume/*`, ‏`hooks/useWebSocket.ts`, ‏`lib/websocket.ts`, ‏`lib/mockData.ts`, ‏`stores/chartSyncStore.ts`.
2. הסרגל השמאלי הישן ושאריות נוספות (≈2,490 ש'): `components/sidebar/**` (LeftTabs + 9 לשוניות), ‏`systems/{DayType,FiveMin,Footprint,Woodies}Pill.tsx`, ‏`atoms/StatusDot.tsx`, ‏`health/StreamHealthPanel.tsx`, ‏`settings/SettingsDrawer.tsx`, ‏`trades/{TradeReviewPanel,TradeMarkChart}.tsx`.
3. חנויות ו-API מתים: `stores/systemStore.ts` + `hooks/useSystemEvents.ts` (אחרי תיקון a4), ‏`stores/marketStore.ts` (+‏`ChartV5b.tsx:231`), ‏`lib/api.ts:90–106,228–260`. אחר כך להעביר את `store/systemStateStore.ts` ל-`stores/` ולמחוק את התיקייה `store/`.
4. אלמנטים מתים במסך הראשי: `strips/ShadowSoakStrip.tsx` + ‏`GET /shadow/soak_progress` (stub); ‏`topbar/AgentHeartbeatDot.tsx` + ‏`app/api/agent-heartbeat/` (קובץ מ-28.07). ב-TopBar: הכפתורים "5 Min / Tick Rev", הכפתור 📚 הכפול ו-`ConnectionIndicator` השני. בנוסף: "Move Stop" ב-`ActiveTradeCard.tsx:354–366`, השבב "SS:" ב-Layer0Strip והייבוא של `KeyLevelsStrip` ב-`V9Dashboard.tsx:17`.
5. פאנלים מיושנים ב-`/board`: ‏`board/StatusBoardPanel.tsx` + ‏`public/task_board.json` (22.07), ‏`board/ProposedDiffsPanel.tsx`, ‏`board/PagesPanel.tsx` + ‏`public/pages_index.json` (16.07), ‏`public/system6.html`, ‏`public/trade-review.html`. בצד הבקאנד: 49 הנתיבים של §5א, ובנוסף לחסום את `POST /trade/debug_gateway_fire` (§5ב).

### (c) להשאיר
- הליבה במסך הראשי: ChartV5b והשכבות שלו, ‏TreeV3Strip, ‏NearestFireStrip (`/tree/state` + `/tree/next_fire`), ‏ContextRadar, ‏MultidayProfilePanel, ‏OpeningTypePanel, ‏DirectionStrip, ‏KeyLevelsStrip (אחרי a3), ‏SierraTruthStrip (אחרי a2), ‏ActiveTradeCard + כפתור Exit (מבצע flatten בסיירה לפני הסגירה ב-DB), ‏DemoMonitor, ‏BannerStack (אחרי a5), ‏SystemControlPanel ו-TradeDetailsModal.
- הלשוניות Build Status, ‏Trade Review (עם `public/marker.html`), ‏Day Type ו-🌌 עץ (לרענן את `tree_v3.json`), והעמוד `/trades`.
- ב-`/board`: ‏SierraLiveCheckPanel, ‏LiveLedgerPanel, ‏AccountStatePanel, ‏System6SupervisorPanel ו-NewsCalendarPanel. את DailyPnlPanel — רק אחרי שיופנה לחשבון הפעיל.
- הנתיבים ב-§5ג (גשר, טלפון, סקריפטים) וב-§5ב (נתיבים שסקריפטים משתמשים בהם).
- לשקול בהמשך: `trades/active` נמשך ע"י 3 רכיבים בנפרד, ‏`classify_replay` + `day_type/live` ע"י 2, ו-`build/pattern-status` (93KB) נמשך כל 15 שנ' במסך הראשי. מקור משותף אחד (react-query או store) יחסוך בערך חצי מהקריאות. וגם לעבור מ-`const API = … 'http://localhost:8000'` ב-36 קבצים ל-`getApiBase()` אחד.

---
*קבצי עבודה זמניים של הביקורת נמצאים ב-`/tmp/fbaudit/` על ה-iMac (צילומי JSON, טבלת הלוג, גרף הייבוא). אפשר למחוק אותם.*
