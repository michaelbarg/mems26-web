# CC — MEGA CLOSURE PROMPT · "start SHADOW from 0 today" · 2026-06-05

סוגר את כל נושאי הסשן. **3 streams**: A=קריטי (חוסם start), B=תצפיתיות (לבטוח בלוח),
C=עיצוב/UX (מקבילי, **לא חוסם**). כל "DONE" = paste פקודה + raw output (Rule 5) +
NOT-DONE. כללים: `CLAUDE.md` + `CC_HANDOFF_CONTRACT.md` · smallest correct change ·
regression לכל תיקון · localhost-PG בלבד · אל תיגע CLOUD_URL/KeepAlive/risk-VALUES
מעבר ל-session-gate · Cowork יצליב כל פלט.

**קרא קודם:** `CC_PROMPT_CUTOVER_START_FROM_0_2026-06-05.md` ·
`CC_PROMPT_B13_REMEDIATION_FULL_2026-06-05.md` · `G1_WORK_PLAN_2026-06-05.md` +
`CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md` ·
`CC_PROMPT_B11_BRIDGE_INSPECTOR_ROWID_2026-06-05.md` ·
`CC_PROMPT_B14_CHART_5MIN_DUP_2026-06-05.md` · `TRADES_REDESIGN_KIT_2026-06-04.md` +
`CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04.md` ·
`docs/plans/BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md`.

מאומת ע"י Cowork (אל תסרוק מחדש): הגשר **משדר** (live_price 321ms, CVD 2.6s) —
ה-OFFLINE הוא B-11. בר-6/5 ישן (7341/7365.75) עבר ל-S2 כי אין שומר-staleness בכניסה
+ S2 נשאר חמוש אחרי הסגירה. G1 §0: 7/7 ב-`cross_context[0].systems.{...}` → promote-able.

═══════════════════════════════════════════
## STREAM A — קריטי · חוסם את ה-start (gated)
═══════════════════════════════════════════
**A1 · B-13 D2 — שומר-staleness בכניסה** (`bars.py` POST `/5min` + שאר POST שמריצים
`_route_bar`): דחיית בר עם `ts` ישן-מהאחרון-שנקלט > interval אחד, ו/או מחיר רחוק
מהשוק-החי > `STALE_PRICE_BAND`. נדחה=לא נכתב, לא מנותב. regression: בר-6/5→נדחה; הסרה→RED.

**A2 · B-13 D3 — session קנוני America/Chicago 08:30–15:00** (Rule 4):
ירי חסום מחוץ-לחלון **בכל המערכות וכל mode כולל SHADOW**; מעבר DAY_TYPE→OVERNIGHT
ב-15:00 CT ב-S2 **+ אמת S3/S4 ושאר המערכות**; `entry_ts` ב-UTC (תצוגה CT).
ingest מותר עד 16:00 CT ל-data, אבל **ירי אסור** אחרי 15:00 CT. regression: 15:01 CT→אין ירי.

**A3 · G1 — עמודות + אכלוס (בלי backfill)**: `day_type_at_entry`/`pattern_id_at_entry`/
`session_at_entry` (String,nullable,index) + migration; אכלוס-בכניסה ב-`trading_gateway`
מאותו `cross_context` דרך helpers של `trade_context.py` (זהה ל-`extract_trade_display`),
שותק→NULL; litmus: אין killzone→NULL (RED על fallback).

**A4 · gates:** `alembic upgrade head` + `\d v9_trades` → כל ה-regressions (A1-A3) ירוקים
(RED→GREEN, paste raw) → **⛔ STRATEGIC-STOP, דווח ל-Michael, אל תמשיך ל-reset בלי אישור.**

**A5 · (אחרי אישור):** truncate `v9_trades`+`v9_bars_5min/_continuous/_woodies`+
`v9_five_min_state` → restart עם `export S3_MUTE=1` ב-`start_all.sh` (S3 mute, הפיך) +
ingestion טרי → **אימות:** soak ≥10ד' 0err/0deadlock · אין `firing_system=3` ·
אין ירי מחוץ 08:30–15:00 CT · עסקה חדשה עם 3 עמודות-G1 מאוכלסות · ספירות-בארים נקיות ·
S2 mode=OVERNIGHT אחרי 15:00. → התחלת ריצה רב-יומית, דווח ל-Michael.

**אישור Michael נדרש (אל תמציא):** `STALE_PRICE_BAND` + סבילות-staleness — הצע ברירות-מחדל.

═══════════════════════════════════════════
## STREAM B — תצפיתיות · שיהיה אפשר לבטוח בלוח בריצה (לא-מסחרי, low-risk)
═══════════════════════════════════════════
**B1 · B-11 — bridge_inspector OFFLINE שקרי** (הצילום מראה את זה חי): `bridge_inspector.py`
L82+L204 `ORDER BY rowid DESC` → PG זורק → כל הזרמים `no_data`/Bridge OFFLINE **שקרי**
(הגשר משדר — אומת live_price 321ms). **תקן `rowid`→`{ts_col}`** ב-2 המקומות + regression
anti-tautological (revert→RED `column "rowid" does not exist`). אמת: הלוח מראה streams חיים.

**B2 · day_type=UNKNOWN** (DEGRADED בצילום): אמת אם זה **לגיטימי** (RTH סגור, +229 דק'
לפתיחה, אין יום מסווג) או **רגרסיית B-8** (`3820f3b` היה אמור לסגור). שאילתת `v9_day_type_state`
+ לוג ה-inspector; דווח root, אל תתקן בלי אישור אם זה נוגע ב-classifier.

═══════════════════════════════════════════
## STREAM C — עיצוב/UX · מקבילי, **לא חוסם** את ה-start (סוכן-frontend נפרד)
═══════════════════════════════════════════
**C1 · B-14 — כפילות-נרות 5דק'** (frontend, נתונים נקיים): נתיב history-backfill
ב-`ChartV5b.tsx` `onRangeChange` (L764-788) — `setData` עם OHLC שנגזר-מחדש דרך
`sanitizeOhlc(b,prevRaw)` stateful + dedup-by-ts-string. אבחן: ts-format mismatch (#1)
או re-sanitize offset (#2); תקן (dedup לפי epoch / seed עקבי); regression RED→GREEN.
**CVD pane נשאר (מכוון).**

**C2 · Build Status — השלמת P0** (הבסיס BuildTreeView כבר committed `66bd45c`): רינדור
`pre_fire_validator` + `risk_checks` caps + Day-Type Matrix verdict ל-S4 + חיווט S5/S6.
לפי `BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md` (V2). **אל תשתמש** ב-`CC_PROMPT_BUILD_STATUS_REDESIGN.md` (מיושן).

**C3 · Trades Frontend Phase 1** (8 פריטים): לפי `CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04.md`
— ADAPT מ-`PatternPerformanceStrip`, ET-date fix, Edge Matrix גנרי (day_type/killzone gated עד G1→אז מסיר gating),
target-distribution, equity-curve, price/time-axis במודאל, stop-behavior, scratch/BE. **D4 price-sanity נדחה — אל תבנה.**

═══════════════════════════════════════════
## סדר + גבולות
═══════════════════════════════════════════
- **Stream A = נתיב קריטי**, גמור עד A4 ועצור. **B1 לפני/יחד עם ה-run** (שהלוח לא ישקר).
- C מקבילי בסוכן-frontend נפרד, **לא מעכב ולא מערער את A**.
- **אל תבנה: G2–G7 · D4 price-sanity · כל מה שמעבר ל-scope.** smallest correct change.
- כל stream: regression + Rule 5 raw output + NOT-DONE + עדכון `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`.
