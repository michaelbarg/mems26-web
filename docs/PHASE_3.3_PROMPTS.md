# Phase 3.3 — System Status Layer Prompts

**Locked:** Sunday May 3, 2026 (Chat 3.3)
**For execution:** Friday May 8, 2026 (Phase 3.3 Day 2)
**Estimated total time:** 6 hours across 3 parallel CC windows

---

## 🎯 Goal

Make system health visible. Today the dashboard shows the same UI whether the system is live, partially down, or weekend-closed. Operator (Michael) cannot tell at a glance whether what he sees is fresh data or stale Friday-close. This layer fixes that with:

1. Sticky **Status Banner** at top — overall state in one glance
2. **Components Panel** (collapsible) — per-component health
3. **Auto-Dim wrapper** — widgets that depend on live data fade when data is unavailable

---

## 📐 Decisions Locked

| # | Decision | Value |
|---|---|---|
| 1 | UI Pattern | Hybrid (Banner + Lights + Auto-Dim) — option C |
| 2 | Timing | Phase 3.3 Day 2 (Friday May 8, 2026) |
| 3 | Sierra detection | Bridge reports via JSON file mtime check |
| 4 | Polling interval | 10 seconds |
| 5 | dim_widgets list | live_setups, current_pnl, tpo_panel, vegas_panel, footprint_panel |
| 6 | NEWS_FROZEN state | Included from day 1 (uses existing /news/status endpoint) |
| 7 | Architecture | 3 parallel prompts: Backend / Bridge / Frontend |

---

## 🏗️ Backend Schema — `GET /system/status`

```json
{
  "overall_state": "LIVE",
  "market_session": {
    "current": "RTH",
    "rth_open_at": "2026-05-04T16:30:00+03:00",
    "rth_close_at": "2026-05-04T23:00:00+03:00",
    "next_event": {
      "type": "RTH_OPEN",
      "in_seconds": 23400,
      "human": "in 6h 30m"
    }
  },
  "components": {
    "backend":  {"status": "UP", "uptime_sec": 12340},
    "database": {"status": "UP", "trades_count": 103, "attempts_today": 12},
    "redis":    {"status": "UP", "last_msg_age_sec": 8},
    "bridge":   {"status": "UP", "last_heartbeat": "2026-05-04T16:35:42+03:00", "age_sec": 8},
    "sierra":   {"status": "UP", "last_data_age_sec": 3, "via": "bridge_mtime"}
  },
  "ui_hints": {
    "show_banner": true,
    "banner_color": "green",
    "banner_text": "SYSTEM LIVE • RTH",
    "dim_widgets": [],
    "expand_components": false
  }
}
```

### Enums
- `overall_state`: `LIVE` | `MARKET_CLOSED` | `DEGRADED` | `OFFLINE` | `NEWS_FROZEN`
- `market_session.current`: `WEEKEND` | `OVERNIGHT` | `PRE_MARKET` | `RTH` | `POST_MARKET` | `NEWS_FREEZE`
- `components.*.status`: `UP` | `STALE` | `DOWN` | `UNKNOWN`
- `banner_color`: `green` | `yellow` | `orange` | `gray` | `red`

### State Machine

| market_session | components state | → overall_state | banner_color |
|---|---|---|---|
| WEEKEND | bridge=DOWN expected | MARKET_CLOSED | gray |
| OVERNIGHT | bridge=DOWN expected | MARKET_CLOSED | gray |
| RTH | all UP | LIVE | green |
| RTH | bridge=DOWN | DEGRADED | yellow |
| RTH | backend=DOWN or db=DOWN | OFFLINE | red |
| NEWS_FREEZE | all UP | NEWS_FROZEN | orange |
| any | redis=DOWN | OFFLINE | red |

### dim_widgets Logic

| State | dim_widgets |
|---|---|
| LIVE | `[]` |
| MARKET_CLOSED | `["live_setups", "current_pnl", "tpo_panel", "vegas_panel", "footprint_panel"]` |
| DEGRADED (bridge=DOWN) | `["live_setups", "current_pnl"]` |
| OFFLINE | `["live_setups", "current_pnl", "tpo_panel", "vegas_panel", "footprint_panel"]` |
| NEWS_FROZEN | `["live_setups"]` (display PnL/TPO/Vegas, just no new entries) |

Always-live widgets (never dimmed): `historical_analytics`, `trade_history`, `v2_simulator`, `day_type_panels`

---

## 🚀 Prompt 1 — Backend (~2h)

```
Version: V8.3.0 - System Status endpoint + market_session calculator

ALLOWED FILES:
- backend/app/routers/system.py (NEW)
- backend/app/services/market_session.py (NEW)
- backend/app/services/system_health.py (NEW)
- backend/app/main.py (only to register new router)
- backend/tests/test_market_session.py (NEW)
- backend/tests/test_system_health.py (NEW)

DO NOT TOUCH:
- bridge/* (separate prompt)
- frontend/* (separate prompt)
- Any other existing routers/services/models
- ~/.mems26_env or any secrets

TASK 1: backend/app/services/market_session.py
- Function: get_market_session(now: datetime) -> dict
- Returns dict matching schema:
  {current, rth_open_at, rth_close_at, next_event: {type, in_seconds, human}}
- Logic (all in ET, then convert to user TZ for display):
  - Saturday ALL DAY → WEEKEND
  - Sunday before 18:00 ET → WEEKEND
  - Sunday 18:00 ET onwards → OVERNIGHT (futures globex open)
  - Mon-Thu 17:00 ET → 09:30 ET next day → OVERNIGHT
  - Mon-Fri 09:00-09:30 ET → PRE_MARKET
  - Mon-Fri 09:30-16:00 ET → RTH
  - Mon-Fri 16:00-17:00 ET → POST_MARKET
  - Friday 17:00 ET onwards → WEEKEND
- News freeze override: if /news/status reports active high-impact event window → NEWS_FREEZE
- DST aware (use zoneinfo, not pytz - we're on Python 3.9+)
- next_event computed: time until next state transition

TASK 2: backend/app/services/system_health.py
- Function: get_system_status() -> dict matching full /system/status schema
- Component checks:
  1. backend: always UP. uptime_sec from process start time captured at module load.
  2. database: SELECT COUNT(*) FROM trades + COUNT(*) FROM setup_attempts WHERE created_at::date = CURRENT_DATE.
     status=UP if query returns <500ms, STALE 500-2000ms, DOWN if exception.
  3. redis: PING. UP if PONG <200ms. last_msg_age_sec from Redis key 'bridge:last_heartbeat' field 'reported_at_iso'.
  4. bridge: read 'bridge:last_heartbeat' from Redis.
     UP if age <30s, STALE 30-90s, DOWN >90s or key missing.
  5. sierra: read 'bridge:sierra_status' from Redis (set by Bridge in V8.3.1).
     If bridge.status==DOWN → sierra.status=UNKNOWN (we can't tell).
     Else → use Bridge's reported value (UP/STALE/DOWN).
- Compute overall_state per State Machine table in spec
- Compute ui_hints:
  - banner_text format: "{emoji} {STATE_NAME} • {session_name}"
    - LIVE → "🟢 SYSTEM LIVE • RTH"
    - MARKET_CLOSED → "⚫ MARKET CLOSED — WEEKEND" (or session name)
    - DEGRADED → "🟡 DEGRADED — Bridge DOWN" (name failed component)
    - OFFLINE → "🔴 SYSTEM OFFLINE"
    - NEWS_FROZEN → "⏸️ NEWS FREEZE — {event_name from /news/status}"
  - dim_widgets per table in spec
  - expand_components: true if state in [DEGRADED, OFFLINE], else false

TASK 3: backend/app/routers/system.py
- GET /system/status → returns get_system_status()
- Response time target: <300ms (cache component checks for max 5s if needed)
- No auth required
- Add to main.py router list

TASK 4: tests
- test_market_session.py:
  - test_saturday_returns_weekend
  - test_sunday_before_18et_returns_weekend
  - test_sunday_after_18et_returns_overnight
  - test_weekday_rth_returns_rth
  - test_dst_transition_spring_forward
  - test_dst_transition_fall_back
  - test_friday_evening_returns_weekend
- test_system_health.py:
  - test_all_up_returns_live (mock all components UP)
  - test_bridge_down_during_rth_returns_degraded
  - test_redis_down_returns_offline
  - test_weekend_with_bridge_down_returns_market_closed (this is the key one)
  - test_sierra_unknown_when_bridge_down

ACCEPTANCE:
- curl https://mems26-web.onrender.com/system/status returns valid JSON matching schema
- Sunday call (any component state) → market_session.current="WEEKEND"
- Sunday + bridge stopped → overall_state="MARKET_CLOSED" (NOT degraded! weekend is expected down)
- Tuesday 17:00 IDT (RTH) + bridge running → overall_state="LIVE"
- Tuesday 17:00 IDT + bridge stopped → overall_state="DEGRADED"
- All 12 unit tests pass

COMMIT: "V8.3.0: System Status endpoint + market_session calculator"
DO NOT PUSH.
```

---

## 🌉 Prompt 2 — Bridge (~1h)

```
Version: V8.3.1 - Bridge reports Sierra status via JSON file mtime

ALLOWED FILES:
- bridge/json_bridge.py
- bridge/sierra_monitor.py (NEW)
- bridge/tests/test_sierra_monitor.py (NEW)

DO NOT TOUCH:
- Any backend files
- Any frontend files
- Any DLL or Sierra source
- ~/.mems26_env or any secrets

TASK 1: bridge/sierra_monitor.py
- Function: check_sierra_status(json_path: str) -> dict
- Returns: {status, last_data_age_sec, via, reported_at_iso}
  - status: "UP" | "STALE" | "DOWN"
  - last_data_age_sec: int (-1 if file missing)
  - via: "bridge_mtime"
  - reported_at_iso: now in ISO 8601
- Logic:
  - File missing → status="DOWN", age=-1
  - mtime <60s old → "UP"
  - mtime 60-300s old → "STALE"
  - mtime >300s old → "DOWN"

TASK 2: bridge/json_bridge.py modifications
- Find existing watchdog/heartbeat loop
- In each cycle, additionally:
  1. Call check_sierra_status(SC_JSON_PATH)
  2. Write to Redis key 'bridge:sierra_status' with TTL 90s:
     {status, last_data_age_sec, via, reported_at_iso}
  3. Write to Redis key 'bridge:last_heartbeat' with TTL 90s:
     {bridge_status: "UP", reported_at_iso, sierra_status_summary: <status from above>}
- Use existing Redis client. SET with EX=90.
- DO NOT log SC_JSON_PATH value or any path containing user data

TASK 3: tests
- test_sierra_monitor_file_missing → DOWN, age=-1
- test_sierra_monitor_recent_file → UP (touch tmp file, age <60s)
- test_sierra_monitor_stale_file → STALE (set mtime to 90s ago using os.utime)
- test_sierra_monitor_old_file → DOWN (set mtime to 400s ago)

ACCEPTANCE:
- Bridge running with Sierra writing JSON → Redis has fresh keys with bridge:sierra_status:status=UP
- Bridge running, Sierra closed (no JSON updates) → after 60s, sierra=STALE; after 300s, sierra=DOWN
- Bridge stopped → keys expire after 90s, Backend reports bridge=DOWN, sierra=UNKNOWN
- All 4 unit tests pass

COMMIT: "V8.3.1: Bridge reports Sierra status via JSON mtime + Redis heartbeat keys"
DO NOT PUSH.
```

---

## 🎨 Prompt 3 — Frontend (~3h)

```
Version: V8.3.2 - Status Banner + Components Panel + Auto-Dim wrapper

ALLOWED FILES:
- frontend/components/SystemStatus/StatusBanner.tsx (NEW)
- frontend/components/SystemStatus/ComponentsPanel.tsx (NEW)
- frontend/components/SystemStatus/DimWrapper.tsx (NEW)
- frontend/components/SystemStatus/index.ts (NEW, exports)
- frontend/hooks/useSystemStatus.ts (NEW)
- frontend/lib/api.ts (only to add fetchSystemStatus function)
- frontend/pages/index.tsx OR app/page.tsx (only to wrap dashboard)

DO NOT TOUCH:
- Any backend files
- Any bridge files
- Existing widget components (only wrap them, don't modify their internals)
- Any other pages

TASK 1: frontend/hooks/useSystemStatus.ts
- Polls GET /system/status every 10 seconds
- Use SWR (preferred — already in project) or react-query
- Returns: { status: SystemStatus | null, isLoading: boolean, error: Error | null, lastFetched: Date | null }
- TypeScript types must match backend schema exactly
- Handle network errors gracefully (don't crash dashboard if endpoint down)

TASK 2: StatusBanner.tsx
- Sticky at top of page (position: sticky, top: 0, z-index: 50)
- Reads from useSystemStatus hook
- 5 visual states based on overall_state:
  - LIVE: green bg (#10b981), white text
  - MARKET_CLOSED: dark gray (#374151), light text
  - DEGRADED: yellow (#f59e0b), dark text
  - OFFLINE: red (#dc2626), white text
  - NEWS_FROZEN: orange (#ea580c), white text
- Layout: [emoji + banner_text] [...] [next_event.human] [▼ expand]
- Click expand → toggle ComponentsPanel below banner

TASK 3: ComponentsPanel.tsx
- Hidden by default; shows when StatusBanner expanded OR ui_hints.expand_components=true
- 5 rows: Backend, Database, Redis, Bridge, Sierra
- Each row: [status dot] [name] [status text] [age/details]
- Status dots: 🟢=UP, 🟡=STALE, ⚫=DOWN (expected), 🔴=DOWN (unexpected), ❓=UNKNOWN
- Compact, monospace for ages

TASK 4: DimWrapper.tsx
- Component: <DimWrapper widgetId="live_setups">{children}</DimWrapper>
- Reads ui_hints.dim_widgets from useSystemStatus
- If widgetId in dim_widgets:
  - Apply opacity: 0.4
  - Apply pointer-events: none
  - Overlay: centered text matching state:
    - MARKET_CLOSED → "Live data unavailable — market closed"
    - DEGRADED → "Bridge offline — data may be stale"
    - OFFLINE → "System offline"
    - NEWS_FROZEN → "Frozen during news event"
- If not in dim_widgets → render children as-is, no wrapper effect

TASK 5: Apply to existing widgets in main page
- Wrap LiveSetups with <DimWrapper widgetId="live_setups">
- Wrap CurrentPnL with <DimWrapper widgetId="current_pnl">
- Wrap TPOPanel with <DimWrapper widgetId="tpo_panel">
- Wrap VegasPanel with <DimWrapper widgetId="vegas_panel">
- Wrap FootprintPanel with <DimWrapper widgetId="footprint_panel">
- Historical analytics + trade history NOT wrapped (always live)
- If actual widget component names differ, use closest match and document in commit message

ACCEPTANCE (manual QA on Sunday after deploy):
- Sunday afternoon view: banner shows "MARKET CLOSED — WEEKEND" gray, 5 widgets dimmed with overlay
- Click banner → expands, shows Bridge=DOWN (gray, expected), Sierra=UNKNOWN
- Tuesday 17:00 IDT view with bridge running: banner green "SYSTEM LIVE", nothing dimmed
- Stop bridge during RTH: banner turns yellow "DEGRADED — Bridge DOWN" within 30s, live widgets dim
- Restart bridge: banner returns green within 30s, dim removed

COMMIT: "V8.3.2: Status Banner + Components Panel + Auto-Dim wrapper"
DO NOT PUSH.
```

---

## 🧪 Integration Test (after all 3 deployed, Phase 3.3 Day 3)

Run on Saturday May 10:

1. **Stop bridge** → Frontend banner turns gray within 30s (90s TTL + 10s poll worst case)
2. **Start bridge** → Banner turns green/proper-state within 20s
3. **Block Redis** (firewall sim) → Banner red OFFLINE
4. **Restore Redis** → Banner returns within 20s
5. **Trigger NEWS_FROZEN** (if news event scheduled) or mock /news/status → Banner orange
6. **Sunday natural state** → Banner gray MARKET_CLOSED, no manual intervention needed

---

## ⚠️ Caveats & Open Questions for Phase 3.3 Day 2

1. **Widget component names:** Frontend prompt assumes names like `LiveSetups`, `CurrentPnL`, `TPOPanel`, `VegasPanel`, `FootprintPanel`. If actual names differ, CC adapts and documents the mapping in the commit. No spec change needed.

2. **NEWS_FROZEN logic:** Pulls from existing `/news/status`. If that endpoint's contract differs from assumption (active event with name), Backend prompt needs minor adjustment. Verify `/news/status` schema before Day 2 starts.

3. **Bridge module structure:** Bridge prompt assumes existing watchdog loop in `json_bridge.py`. If watchdog is in separate file, prompt needs path adjustment.

4. **Sierra JSON path:** `SC_JSON_PATH` env var presumed. If Bridge uses different config name, adjust. Bridge prompt does NOT log the path value — security preserved.

---

## 📍 References

- **Source chat:** Chat 3.3 (Sunday May 3, 2026)
- **Master handoff:** `MEMS26_HANDOFF_CHAT_3.3.md`
- **Day Type spec:** `MEMS26_DAY_TYPE_SPEC_V2.md`
- **CC commands:** `docs/CC_COMMANDS.md`
- **Phase 3.3 timeline:** May 8-10, 2026

---

**Document version:** 1.0
**Locked:** Sunday May 3, 2026, 18:55 IDT
**Ready for execution:** Friday May 8, 2026
