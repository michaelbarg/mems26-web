# FRONTEND_INDEX — אינדקס-סמנטי (2026-07-20)

**מבצע:** cursor · **תצוגה/דוקומנטציה** · חוק-5 · cowork מאמת  
**בונה על:** `FRONTEND_MAP_2026-07-19.md` (יומן-מחיקות) · `CURSOR_PRECISE_BLOCK_REASON` · `CURSOR_FRONTEND_INDEX_2026-07-20.md`

---

## ⭐ פרוטוקול-עדכון (חובה — אותו קומיט)

כל שינוי-backend שמוסיף / משנה / מוחק **שער** (`blocked_by`) או **סיבה** (`result["reason"]`) או **שדה** שרכיב-UI קורא ממנו:

1. עדכן את השורה המתאימה ב**§B טבלת-שערים** למטה.
2. עדכן `GATE_HE` + `REASON_PHRASES` ב-`frontend/v9/src/v9/components/sidepanel/lens/plan/planHelp.ts`.
3. עדכן את שורת-הרכיב ב**§A** אם endpoint/שדה השתנה.
4. הוסף/עדכן טסט ב-`tests/v9/regression/test_gateway_block_reason_precise.py` (reason לא-ריק על החסימה).
5. **אותו קומיט** — אל תשאיר את הפרונטאנד מפגר אחרי המנוע.

`blockWhy()` מעדיף `planReasonHe(decision.reason)` ורק אז נופל ל-`GATE_HE.why` הגנרי.

---

## §A — רכיבים חיים → endpoint + שדה → מה מציג

### `/` · V9Dashboard

| רכיב (file) | מה מציג | מקור (endpoint + שדה) | סוג? | הערות |
|---|---|---|---|---|
| ViewTabs `layout/ViewTabs.tsx` | Dashboard / Build / Trades / DayType | local `?view=` | UI | |
| BannerStack `banners/BannerStack.tsx` | באנרי מצב/שער/בריאות | `/cockpit/heartbeat` · `/gateway/status` | מחסום/מצב | |
| DemoMonitor `layout/DemoMonitor.tsx` | DEMO/LIVE + S6 | `/system6/diagnose` · `/status` · `/gateway/status` · active trade | | |
| TopBar `layout/TopBar.tsx` | mode, מחיר, סוג-יום, WR | heartbeat `.mode`/`.price_*` · store S1 · `/shadow/today_wr` | סוג-יום | לא `/day_type/current` |
| PriceDisplay / PriceMeta / ConnectionIndicator | מחיר + חיבור | `priceStore` ← WS + `/live_price` | | |
| AgentHeartbeatDot | פעימת-agent | `/api/agent-heartbeat` | | Next, לא v9 |
| NewsDropdown | חדשות / NO_TRADE | `/agent/news_calendar` | מחסום | |
| Layer0Strip | chop + 6 מדדים + suffering | `/layer0/state` · `/veto/state` | מחסום | 15s |
| KeyLevelsStrip | POC/VAH/VAL/IB + סוג-יום | `/key_levels` · `useLiveDayType`→`classify_replay`+`/day_type/live` | סוג-יום/רמות | SoT |
| ChartV5b | נרות + CVD + TPO/IB + Woodies | `/chart/bars5min` · `/cumulative_delta/current` · `/tpo/*` · `/killzone/current` | | |
| WoodiesCciPanel | CCI/TCCI/ZLR | `/woodies/chart` | | 5s |
| LiveTradeOverlay | כניסה/סטופ/יעדים על גרף | `/trades/active` · heartbeat | סטופ/יעד | |
| DirectionStrip | LONG/SHORT + LSMA/CVD | `/day_type/direction_now` (`.dir`, `.dir_sustained`, `.reason`, …) | כיוון | |
| TradeHistoryStrip | פסי עסקאות | `/trades/recent` | | 30s |
| ShadowSoakStrip | soak WR (SHADOW) | `/status` · `/shadow/soak_progress` | | |
| SidePanel + ActiveTradeCard | עסקה פתוחה | `/trades/active` · `/s6/diagnose/{id}` | סטופ/יעד | |
| Switcher | S1–S6 מצב/תבנית | `systems-snapshot` store · `useDirectionNow` | | |
| TPOPill / KillzonePill | S5/S6 קומפקטי | store `systems[5\|6]` | | |
| *LensContent + *Plan | Now/Plan/Shadow | `/five_min\|footprint\|woodies\|tpo\|killzone/current` · Plan→SystemPlanLive | | |
| AllPatternsPlan | תבניות + למה לא ירה | `/build/pattern-status` + `/gateway/decisions` | **מחסום** | `blockWhy` |
| SystemPlanLive / planFireDiagnosis | TO FIRE / lifecycle | store + `/gateway/status` | מחסום | |
| planHelp.ts | תרגומי שער/סיבה | static + `reason` מה-API | מחסום | פרוטוקול §⭐ |
| BuildStatusTab + DayTypeConditionsTable | תנאי 7-סוגים | `classify_replay` · `/day_type/live` | סוג-יום | |
| BuildTreeView | עץ-בנייה S1–S6 | `/build/pattern-status` | | גם `/build` |
| TradeReviewTab | רשימת עסקאות | `/trades` · `/trade_reviews` | | |
| DayTypeLabelTab | תיוג ידני | `/chart/replay` · classify_replay | סוג-יום | |
| TradeDetailsModal | פרטי עסקה | `/trades/{id}` | | |
| SystemControlPanel | admin | `/admin/services/*` | | |
| AgentChatWidget | צ'אט | `POST /agent/chat` | | layout |

### `/board` · `/build` · `/trades`

| רכיב | מה מציג | מקור | הערות |
|---|---|---|---|
| ProposedDiffsPanel | diffs | `/agent/proposed_diffs` | |
| SierraLiveCheckPanel | Sierra check | `/agent/sierra_live_check` | |
| NewsCalendarPanel | לוח חדשות | `/agent/news_calendar` | |
| LiveLedgerPanel | ledger | `/live_ledger` | |
| System6SupervisorPanel | S6 | `/system6/diagnose` | |
| StatusBoardPanel | משימות | `/agent/backlog_board` | |
| BuildTreeView (page) | עץ מלא | `/build/pattern-status` | |
| TradesView + analytics strips | KPIs / טבלה | `/trades` (+ client) | |
| TradeRowExpand → TradeChart | מיני-גרף | `/chart/bars5min` | |

### Stores / hooks משותפים

| Hook | צרכנים | Endpoint | שדות מפתח |
|---|---|---|---|
| useSystemStatePolling | TopBar S1, Switcher, Plan | `/cockpit/systems-snapshot` (+ classify_replay ל-S1) | `systems[n].*` |
| usePatternFeed | AllPatternsPlan | `/build/pattern-status` + `/gateway/decisions` | `blocked_by`, **`reason`** |
| useDirectionNow | DirectionStrip, Switcher | `/day_type/direction_now` | `dir`, `dir_sustained` |
| useKeyLevels / useLiveDayType | strips | `/key_levels` · classify_replay · `/day_type/live` | |

---

## §B — כל `blocked_by` → `result["reason"]` → תרגום תצוגה

מקור: `backend/v9/gateway/trading_gateway.py` · מיפוי: `planHelp.ts` (`blockWhy` / `REASON_PHRASES` / `GATE_HE`)

| blocked_by | reason מהמנוע (דוגמה / תבנית) | תרגום-תצוגה | planHelp |
|---|---|---|---|
| kill_switch | `_ks_reason` / `kill switch engaged` | מתג-חירום + סיבה | GATE + phrase |
| session_gate_closed | `outside firing window 08:30–15:00 CT` | מחוץ לחלון-ירי | phrase |
| eod_entry_cutoff | `past EOD entry cutoff (N min before 15:00 CT close)` | אחרי חיתוך סוף-יום | phrase |
| feed_watchdog | `_feed_reason` / `canonical feed stale` | פיד תקוע | phrase |
| cooldown | `2-stop cooldown active` | צינון 2-סטופים | phrase |
| suffering_side_veto | `{dir} is suffering side (SSV D-049)` | צד-סובל | phrase |
| duplicate_fire | `duplicate S{n} {dir} {pat} @{ep} within 30s` | ירי-כפול | phrase |
| chop_searching | `Layer-0 chop_state=SEARCHING (high chop)` | שוק-קופצני | phrase |
| opening_type_gate | `_reason` ממנוע הפתיחה | שער סוג-פתיחה + מדויק | reason pass-through |
| daytype_playbook | `_pb.reason` (למשל `responsive SHORT not at VAH (below_value) on Variation`) | שורט-fade לא ב-VAH · מתחת לערך · Variation | phrases VAH/VAL |
| trend_direction_gate | `_reason` | שער כיוון-מגמה + מדויק | pass-through |
| reactive_location | `_reason` | מיקום ריאקטיבי + מדויק | pass-through |
| location_gate | `_lg_reason` | שער-מיקום + מדויק | pass-through |
| daytype_position_gate | `_reason` | משפחה×סוג-יום + מדויק | pass-through |
| cont_trend_filter | `{pat} (CONT) setup {dir} vs sustained {sus}` | המשך מול מגמה-מתמשכת | phrase |
| direction_context | `setup {dir} vs day-context {dc} ({reason})` | סטאפ מול הקשר-יום | phrase |
| lsma_flat | `\|LSMA slope x\| < min pts/bar (flat LSMA, scope=…)` | LSMA שטוח + מספרים | phrase |
| news_blackout | `news blackout: {event} @{time} ET ({window})` | חלון-חדשות + אירוע | phrase |
| day_direction_doctrine | `{dir} against {exp} expansion on {dt} (no halt-proof)` | נגד התרחבות | phrase |
| entry_not_confirmed | `_ec_reason` | אין אישור-כניסה | pass-through |
| t1_wrong_side | `{dir} t1=… on wrong side of entry=…` | T1 בצד הלא-נכון | phrase |
| rr_entry_gate | `T1_dist=… < stop_dist=… × min=… (R:R=…)` או confluence avg | R:R מדויק | phrase |
| zone_limit_late_entry | `adverse drift …` או `signal age …` | כניסה מאוחרת | phrase |
| daily_loss_halt | `daily pnl $… <= -$… (STOP DAY)` | עצירת-יום | phrase |
| consecutive_loss_halt | `N consecutive losses >= lim (STOP DAY)` | הפסדים-רצופים | phrase |
| s4_risk_cap | `str(_s4_rcb)` | תקרת-סיכון S4 | pass-through |
| pattern_loss_breaker | `pattern_loss_breaker:…` | שובר-הפסדים לתבנית | phrase prefix |
| cluster_guard | `cluster guard D-037 (too many fires…)` | שומר-צבירה | phrase |

החלטות נרשמות ב-`gw.decisions[]` עם `"reason": result.get("reason")` → `/gateway/decisions`.

---

## §C — מועמדי-מחיקה (פסיקה בלבד — אל תמחק בלי אישור מייקל)

| פריט | ראייה | המלצה |
|---|---|---|
| LeftTabs + 9 sidebar tabs | אין importer — לא mounted | מועמד-מחיקה |
| ChartV5a, ChartArea, StaticLevels, RightSideLabels, VegasEMAs, TimeframeSelector | לא בשימוש / backup | DEFER |
| VolumePanel, VolumeDragHandle | אין importers | DEFER |
| CumulativeDeltaPane standalone | CVD בתוך ChartV5b | DEFER |
| StreamHealthPanel, SettingsDrawer, StatusDot | אין importers | DEFER |
| DayType/FiveMin/Footprint/WoodiesPill | הוחלפו ב-Switcher | DEFER |
| TradeReviewPanel | orphan; TradeReviewTab חי | DEFER |
| `fetchDayTypeV9` → `/day_type/v9/current` | helper מת ב-`api.ts` | מועמד-הסרה (לא לקרוא) |
| SoundProvider | **כבר נמחק** 2026-07-20 | — |

תיקון-מסמך: `FRONTEND_MAP` רשם LeftTabs כ"חיים" — **לא mounted**. ראה §A לחיים האמיתיים.

---

## §D — SoT (הצלבה קצרה)

| נתיב-UI | SoT |
|---|---|
| סוג-יום: classify_replay + `/day_type/live` | ✅ |
| כיוון: `/day_type/direction_now` | ✅ |
| גרף חי: `/chart/bars5min` | ✅ (לא raw `/bars/5min`) |
| מחסומים: `/gateway/decisions`.reason | ✅ display |

---

## אימות (חוק-5)

ראה LOG ב-`LIVE_CHANNEL.md` אחרי commit — `pytest` + `tsc` + `curl :3000`.
