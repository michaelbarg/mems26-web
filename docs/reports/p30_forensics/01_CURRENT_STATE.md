# V9 Current State — Full Architecture Report
Date: 2026-05-21T10:00:00Z
Author: Claude Code
Phase: 1
Mode: READ-ONLY

## Method

Forensic read-only analysis of `/Users/michael/Downloads/mems26_web_git`. Examined: git log (20 commits), directory sizes, all route definitions (grep `@router`/`@app`), every system directory (LOC counts), bridge streams, frontend hooks/components, test inventory, compliance manifests. No files were modified.

---

## 1. Repo Structure

### 1.1 Top-level Layout

```
backend/      4.6 MB   FastAPI v9 API + 6 trading systems + gateway
bridge/       280 KB   DLL JSON export reader, pushes to localhost:8000 + Upstash Redis
frontend/     1.0 GB   Next.js 16 React 19 cockpit (node_modules dominates size)
sc_study/     200 KB   Sierra Chart DLL C++ source (MES_AI_DataExport)
docs/         2.9 MB   ~55 reports, decisions, runbooks, handoffs
tests/        2.7 MB   132 test files (tests/ + backend/v9/tests/)
data/              -   SQLite DB (mems26_local.db) + backups
scripts/           -   ~46 operational scripts
tools/             -   Supplementary tools
schema/            -   Schema definitions
```

### 1.2 Git State

- **Tags:** `pre-prompt-1`, `v9-day2-start-2026-05-13`
- **Last 20 commits** span May 13-21 2026, focused on: footprint thread-safety (D-082), gateway gate ordering, P30 diagnostic reports, Sierra DLL study exports, chart fixes (corrupt bars, sticky rails, stale ticks, CVD sync), Woodies panel, Plan tab, cockpit-minimal bridge preset.

---

## 2. Backend Architecture

### 2.1 Routes & Handlers

**Entry point:** `backend/main.py` -> FastAPI app, version 9.0.0
**Procfile:** `web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

**Route modules mounted via `backend/v9/app.py`:**

| Module | Prefix/Path | Key Endpoints |
|--------|-------------|---------------|
| bars | `/api/v9/bars/` | POST `5min`, `tick_reversal`, `footprint`, `volume_profile`, `imbalance`, `stacked_imbalance`, `cumulative_delta`, `woodies`, `woodies_5min`, `tpo`; GET `5min`, `tick_reversal`, `woodies`, `tpo` |
| signals | `/api/v9/signals` | POST, GET (by system_id) |
| markers | `/api/v9/markers` | POST, GET (by system_id) |
| trades | `/api/v9/trades` | POST, GET, GET `/active`, GET `/recent`, GET `/{trade_id}`, POST `/log` |
| configs | `/api/v9/configs` | GET, GET `/{system_id}/{mode}`, PUT `/{system_id}/{mode}` |
| websocket | `/ws/v9/bars/*`, `/ws/v9/markers/*`, `/ws/v9/signals/*`, `/ws/v9/trades`, `/ws/v9/account`, `/ws/v9/levels` | 9 WebSocket endpoints |
| health_streams | `/api/v9/health/streams` | GET stream health |
| trade_commands | `/command`, `/result` | POST command, GET result |
| status | `/api/v9/status` | GET full system status |
| audit | `/api/v9/audit/events`, `/replay`, `/stats` | GET each |
| spec_compliance | `/api/v9/spec/status` | GET |
| day_type | `/api/v9/day_type/` | `state`, `current`, etc. |
| day_type_v9 | `/api/v9/day_type/v9/` | GET `current`, `history`, `stats` |
| five_min | `/api/v9/five_min/` | GET `current`, `setups`, `fire`, `stats` |
| footprint | `/api/v9/footprint/` | GET `current`, `fire`, `journal` |
| woodies | `/api/v9/woodies/` | GET `current`, `signals`, `patterns`, `fire`; POST `fire` |
| tpo_routes | `/api/v9/tpo/` | GET `current`, `journal`, `sessions`, `previous_day` |
| killzone_routes | `/api/v9/killzone/` | GET `current` |
| bars_5min_history | `/api/v9/chart/` | GET `bars5min`, `bars1m`, `bars3m`, `bars15m`, `bars30m`, `bars1h` |
| reversal_routes | `/api/v9/reversal/` | GET `current`, `history` |
| chop_score_routes | `/api/v9/chop_score/current`, `/api/v9/layer0/state` | GET each |
| gateway_routes | `/api/v9/gateway/` | GET `status`, `risk`; POST `route_setup` |
| shadow_routes | `/api/v9/veto/state`, `/api/v9/shadow/today_wr`, `/api/v9/shadow/soak_progress`, `/api/v9/{system_name}/health` | GET each |
| pre_fire_routes | POST `/validate` | Pre-fire validation |
| behavior_phase | behavior phase routes | |
| price_routes | `/api/v9/live_price` | GET live price from Sierra file |
| clock_routes | `/api/v9/clock/now` | GET market clock |
| open_type_routes | `/api/v9/open_type/current` | GET opening type |
| cvd_routes | `/api/v9/cumulative_delta/current` | GET CVD state |
| woodies_chart | `/api/v9/woodies/chart` | GET Woodies CCI chart data |
| history_routes | `/dates`, `/yesterday`, `/{date}`, POST `/archive_now` | Session history |
| journal_compat | `/trades/log`, `/analytics/setups/recent`, `/analytics/setups/today_summary`, `/analytics/setups/sequential_today_summary` | V8-compat journal |
| ws price_channel | `/ws/v9/price`, `/api/v9/ws/status` | Real-time price WS |

**Inline cockpit routes in app.py:**
- `GET /api/v9/health` — simple health check
- `GET /api/v9/cockpit/heartbeat` — lightweight (<20ms target), no Redis
- `GET /api/v9/cockpit/systems-snapshot` — single batch read of all 6 systems' in-memory state
- `GET /health` — top-level Render health check (in main.py)

**Total: ~90+ route handlers across ~30 route modules.**

### 2.2 Six Systems

| # | System | Dir LOC | Key Files | Status |
|---|--------|---------|-----------|--------|
| S1 | Day Type | 2,932 | `state_machine.py`, `detector.py`, `schemas.py`, `consumer.py`, `prev_day.py`, `api.py` + 20 files | Active. Subscribes to `5min` bars via BarRouter. Persists to `v9_day_type_state` + `v9_day_type_history`. Mid-session restart guard (P30 C1). |
| S2 | Five Min | 1,421 | `five_min_system.py`, compliance_manifest + 13 files | Active. Hydrates on startup. Gateway-injected for auto-routing. |
| S3 | Footprint | 691 | `footprint_system.py` + 6 files | Active. Hydrates on startup. Gateway-injected. Thread-safe journal (D-082). |
| S4 | Woodies | 2,623 | `woodies_system.py`, `active_phase.py`, `entry_phase.py`, `yaml_loader.py` + 24 files | Active. Hydrates on startup. Gateway-injected. Had SLOW handler fix (P30). |
| S5 | TPO | 1,562 | `tpo_system.py`, `schemas.py` + 13 files | Active. Hydrates on startup. Provides IB high/low to Day Type. |
| S6 | Killzone | 809 | `killzone_system.py` + 13 files | Active. Time-based (no bar subscriptions). Ticks every 30s via asyncio loop. |

**Additional subsystems:**
- `reversal/` (333 LOC) — ReversalBarHandler, subscribes to `tick_reversal_15`
- `tick_reversal/` (1,278 LOC) — Tick reversal bar processing
- `behavior_phase/` — Behavior phase routes
- `chart_5min/` — Chart 5-min patterns
- `layer0/` — Chop score / Layer 0 state
- `base/` + `base_system.py` (1,905 LOC) — Base system class

**BarRouter (106 LOC):** Central bar distribution hub. Receives bars from API POST endpoints, dispatches to subscriber callbacks. Logs SLOW handlers (>100ms). Each system subscribes at startup.

### 2.3 Gateway Flow

**`backend/v9/gateway/trading_gateway.py`** (790 LOC total across gateway dir):

```
route_setup(setup, system_id)
  -> Pre-trade risk gates (sequential):
     1. CooldownManager.is_blocked() — 2-stop cooldown
     2. SufferingSideVeto.check_veto() — SSV D-049
     3. Layer0 chop_state == "SEARCHING" gate
     4. ClusterGuard.is_blocked() — D-037 (DEMO/LIVE only, SHADOW passes)
  -> SHADOW: always log (unlimited slots, capped at 500)
  -> DEMO: single slot, if enabled for system_id
  -> LIVE: single slot + passes_strict_checks()
  -> Cross-context snapshot of all 6 systems captured at route time
```

**Gateway wiring at startup:**
- S2, S3, S4 are gateway-injected for validated auto-routing
- TradeManager wired for SHADOW PnL tracking
- BarLevelDetector subscribes to `5min` for auto-close

### 2.4 Redis/Upstash Usage

**Backend Event Bus** (`backend/v9/event_bus/`, 8 files):
- Redis Streams via Upstash REST API (`XADD`, `XRANGE`, `XREAD`)
- Channels defined in `channels.py`
- Audit consumer reads from all streams, persists to AuditEvent table
- `EventBusWSManager` (`backend/v9/ws/manager.py`) polls Redis Streams and relays `price.tick` to WebSocket clients

**Snapshot Service** (`backend/v9/services/snapshot_service/`):
- Reads system state from Redis keys `mems26:v9:{system_name}:latest`
- Currently appears unused by cockpit (cockpit reads in-memory state directly)

**Active Trade Alerts** (`backend/v9/services/active_trade_manager/alerts.py`):
- Publishes to Redis pub/sub channel

**Bridge** (see Section 3):
- Pushes to Upstash Redis (SET latest + LPUSH history list + heartbeat keys)

**Environment vars:** `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`

### 2.5 Suspected Slow Paths

1. **BarRouter SLOW handler warning** at `bar_router.py:84` — triggers when any handler takes >100ms. Known offender: WoodiesSystem (P30 fix applied, see `woodies_system.py:26`).
2. **HistoricalReplay warm_all_systems** — replays ~144 5-min bars. Disabled by default (`V9_DO_WARMUP` env var). Known to hang FastAPI startup when `BarLevelDetector.on_bar` takes 5-11s due to session commit regression.
3. **DayType `_day_type_on_bar`** handler in `main.py` — lines 162-283, ~120 lines of inline processing including SQLite writes, consumer persistence, and event bus publish. Runs on every 5-min bar.
4. **WebSocket relay loop** — polls Redis Streams at 100ms intervals (`manager.py:79`).
5. **KillzoneSystem tick loop** — `asyncio.sleep(30)` every 30s (line 302 in main.py).

---

## 3. Bridge Architecture

### 3.1 Streams

**12 streams** defined in `bridge/v9_streams/__init__.py`:

| Stream | File | Source (DLL JSON) |
|--------|------|-------------------|
| LivePriceStream | `live_price_stream.py` (7,669 B) | `live_price.json` |
| TickReversal15Stream | `tick_reversal_15_stream.py` | tick reversal 15 bars |
| TickReversal12Stream | `tick_reversal_12_stream.py` | tick reversal 12 bars |
| FootprintStream | `footprint_stream.py` (1,658 B) | footprint data |
| VolumeProfileStream | `volume_profile_stream.py` | volume profile |
| ImbalanceFlagsStream | `imbalance_flags_stream.py` | imbalance flags |
| StackedImbalancesStream | `stacked_imbalances_stream.py` | stacked imbalances |
| CumulativeDeltaStream | `cumulative_delta_stream.py` | cumulative delta |
| Woodies30MinStream | `woodies_30min_stream.py` | Woodies 30m CCI |
| Woodies5MinStream | `woodies_5min_stream.py` | Woodies 5m CCI (D-074) |
| TpoStream | `tpo_stream.py` | TPO profile |
| Bars5MinStream | `bars_5min_stream.py` (1,502 B) | 5-min OHLCV bars |

**Base class** (`base_stream.py`, 14,871 B): Uses `watchdog` fsevents for ~10ms file-change detection (falls back to 2s mtime polling). Each stream runs in its own daemon thread.

**Presets:**
- `--bars-5min-only` — just bars_5min
- `--cockpit-minimal` — bars_5min + woodies_5min
- `--streams=name1,name2` — explicit selection

### 3.2 Push Targets

1. **FastAPI local:** `POST http://localhost:8000{api_path}` via `base_stream.py:327`. Hard-enforced: `CLOUD_URL` must be localhost/127.0.0.1 or startup fails.
2. **Upstash Redis:** `SET {redis_key}:latest`, `LPUSH {redis_key}`, `LTRIM` (cap 100), heartbeat keys. Used for history resume and cross-process state.

**Candle Builder** (`bridge/candle_builder.py`): Builds candles from ticks, pushes to Redis list `mems26:candles` (capped at 500).

### 3.3 Error Patterns

- Bridge heartbeat every 60s logs: push count, error count, newest data age, active stream count
- Per-stream heartbeat every 30s to Redis key `{redis_key}:heartbeat`
- `BRIDGE_TOKEN` env var required at startup (hard fail)
- `CLOUD_URL` localhost enforcement (hard fail)
- Watchdog disable via `V9_DISABLE_WATCHDOG` env var
- Optional today-bars wipe on startup (`wipe_today_bars_if_requested`)

---

## 4. Frontend Architecture

### 4.1 Framework & Dependencies

- **Next.js 16.2.6** (React 19.2.4)
- **State:** Zustand 5.0.13 (stores), @tanstack/react-query 5.100.9
- **Charting:** lightweight-charts 5.2.0, Recharts 2.15.0
- **UI:** Tailwind CSS 4, Lucide React icons, react-resizable-panels
- **Testing:** Playwright 1.60.0
- **Total:** 118 .ts/.tsx files, 15,422 LOC

### 4.2 Pages & Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `V9Dashboard` | Main cockpit — chart + systems strip + side panel |
| `/journal` | Journal page (1,026+ lines) | Trade journal with Recharts analytics, day type badges |
| `/trades` | `TradesView` | Trade history/management |

### 4.3 Data Flow & Refresh Strategies

**All polling-based** (no SSE). Key intervals:

| Component | Interval | Endpoint |
|-----------|----------|----------|
| `useLivePricePoll` | 1s | `/api/v9/live_price` (fallback for WS) |
| `useSystemStatePolling` | 2s | `/api/v9/cockpit/systems-snapshot` + 6 individual system endpoints |
| `StreamHealthPanel` | 2s | `/api/v9/health/streams` |
| `WoodiesCciPanel` | 2s | `/api/v9/woodies/chart` |
| `ConnectionIndicator` | 1s | Internal tick counter |
| `PriceMeta` | 500ms | Internal tick counter |
| `ChartV5b` bar poll | 5s | `/api/v9/chart/{ep}?limit=3` |
| `ChartV5a` bar fetch | 5s | `/api/v9/chart/{ep}` |
| `TopBar` heartbeat | 5s | `/api/v9/cockpit/heartbeat` |
| `TopBar` shadow WR | 30s | `/api/v9/shadow/today_wr` |
| `Layer0Strip` | 5s | `/api/v9/layer0/state` + `/api/v9/veto/state` |
| `SoundProvider` | 5s | `/api/v9/footprint/fire` + `/api/v9/gateway/status` |
| `ActiveTradeCard` | 5s | Polls active trade state |
| `ShadowSoakStrip` | 60s | `/api/v9/shadow/soak_progress` |
| `TradeHistoryStrip` | 10s | Trade history |
| `BannerStack` | 30s | `/api/v9/cockpit/heartbeat` + `/api/v9/gateway/status` |
| `systemPlanLive` | 3s | `/api/v9/gateway/status` |
| `ChartArea` | 10s | Chart refresh |
| Journal DT poll | 30s | `/analytics/setups/recent` |
| Journal summary poll | 15s | Sequential today summary |

**WebSocket:** `usePriceStream.ts` connects to `ws://localhost:8000/ws/v9/price` with exponential backoff (max 30s). Falls back to `useLivePricePoll` when WS is unavailable.

### 4.4 TPO Refresh Logic

**Location:** `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx`, lines 60-61 and 811-825.

```typescript
const TPO_RTH_REFRESH_MS = 30 * 60 * 1000;       // 30 min during RTH
const TPO_OFF_HOURS_REFRESH_MS = 10 * 60 * 1000;  // 10 min off-hours
```

- `isRthSessionNow()` checks if current time is 09:30-16:00 ET
- During RTH: TPO levels refresh every 30 minutes
- Off-hours: TPO levels refresh every 10 minutes
- A `modeTick` interval (60s) re-arms the refresh interval to adapt to RTH transitions
- Fetches from `GET /api/v9/tpo/current` and `GET /api/v9/tpo/previous_day`

**ChartV5a** also polls TPO at 30s intervals (`line 240`) and TPO sessions at 30s (`line 293`).

### 4.5 Upstash Usage

**Frontend has zero direct Upstash/Redis usage.** The single reference to "Redis" is a code comment in `TopBar.tsx:27` ("no Redis"). All data flows through the backend API.

---

## 5. Tests Inventory

### 5.1 Test Counts

| Location | Files | LOC |
|----------|-------|-----|
| `tests/` (top-level) | 132 | ~18,214 |
| `backend/v9/tests/` | 47 | ~5,145 |
| **Total** | **179** | **~23,359** |

### 5.2 Test Directories under `tests/v9/`

```
tests/v9/api/          — API route tests
tests/v9/bridge/       — Bridge integration tests
tests/v9/compliance/   — Compliance tests (v1_generated/, v2_generated/)
tests/v9/db/           — Database tests
tests/v9/frontend/     — Frontend smoke tests
tests/v9/gateway/      — Gateway routing tests
tests/v9/layer3/       — Layer 3 tests
tests/v9/replay/       — Replay scenario tests (with fixtures/p29/)
tests/v9/services/     — Service unit tests
tests/v9/shadow/       — Shadow mode tests
tests/v9/systems/      — System tests (chart_5min_patterns/, day_type/, tick_reversal/)
```

### 5.3 Additional Test Locations

- `tests/atomic/` — Atomic/unit tests
- `tests/db/` — Database tests
- `tests/event_bus/` — Event bus tests
- `tests/systems/base/`, `tests/systems/day_type/` — System-specific tests
- `backend/v9/tests/systems/woodies/` — Woodies-specific tests (entry_phase, active_phase, yaml_loader scaffolds)

---

## 6. Compliance & Decisions State

### 6.1 Decisions (`docs/decisions/`)

3 decision records:
- `D-074_woodies_5min.md` — Woodies 5-min stream as primary S4 source
- `D-087_REGISTRY_WAIVER.md` — Registry waiver
- `D-088_CLUSTER_GUARD_SHADOW.md` — Cluster guard blocks DEMO/LIVE only, SHADOW always records

### 6.2 MEMS26_REGISTRY.yaml

Located at repo root. Categories: `REQ-S-*` (system decision trees), `REQ-DATA-*` (data collection), `REQ-ADMIN-*` (admin console), `REQ-UI-*` (dashboard), `REQ-EXPLAIN-*` (tooltips/narratives), `REQ-INFRA-*` (DLL/Bridge/Backend), `REQ-GOVERN-*` (policies). File is 62,875 bytes.

### 6.3 Compliance Manifests

8 per-system compliance manifests found:
- `backend/v9/systems/day_type/compliance_manifest.yaml`
- `backend/v9/systems/chart_5min/compliance_manifest.yaml`
- `backend/v9/systems/five_min/compliance_manifest.yaml`
- `backend/v9/systems/footprint/compliance_manifest.yaml`
- `backend/v9/systems/woodies/compliance_manifest.yaml`
- `backend/v9/systems/tpo/compliance_manifest.yaml`
- `backend/v9/systems/killzone/compliance_manifest.yaml`
- `backend/v9/systems/tick_reversal/compliance_manifest.yaml`

### 6.4 Other Governance Files

- `CALIBRATION_LEDGER.yaml` — calibration tracking
- `CLAUDE.md` — agent guardrails (bridge local-only rule, service bring-up rules, Sierra DLL protocol)
- `.claude/` — 8 agent skill/principle files (CREDENTIALS, DATA_INTEGRITY, INDEPENDENT_VERIFICATION, LATENCY_OPTIMIZATION, MASTER_DEV_SKILL, SMOKE_TEST, drift report, settings)

---

## Evidence

### Key File Paths

- **Backend entry:** `/Users/michael/Downloads/mems26_web_git/backend/main.py` (399 lines)
- **V9 app/router:** `/Users/michael/Downloads/mems26_web_git/backend/v9/app.py` (341 lines)
- **Trading gateway:** `/Users/michael/Downloads/mems26_web_git/backend/v9/gateway/trading_gateway.py`
- **Bar router:** `/Users/michael/Downloads/mems26_web_git/backend/v9/services/bar_router.py` (106 lines)
- **Bridge main:** `/Users/michael/Downloads/mems26_web_git/bridge/json_bridge.py`
- **Bridge base stream:** `/Users/michael/Downloads/mems26_web_git/bridge/v9_streams/base_stream.py` (14,871 bytes)
- **Frontend chart:** `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` (964 lines)
- **System state store:** `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/store/systemStateStore.ts`
- **TPO refresh:** `ChartV5b.tsx:60-61` (constants), `ChartV5b.tsx:811-825` (implementation)
- **SLOW handler:** `bar_router.py:84`, `woodies_system.py:26`
- **Historical replay skip:** `main.py:370` (`V9_DO_WARMUP`)

### Line Number References

- `main.py:50-380` — Full startup sequence (EventDispatcher, BarIngestion, 5min aggregator, BarRouter, 6 systems, gateway, trade manager, historical replay)
- `main.py:162-283` — DayType inline handler (SQLite writes, consumer persist, event publish)
- `main.py:299-303` — KillzoneSystem 30s tick loop
- `app.py:76-107` — Cockpit heartbeat (no Redis, <20ms target)
- `app.py:135-264` — Systems snapshot batch endpoint
- `trading_gateway.py:68-137` — `route_setup` with 4 risk gates
- `manager.py:59-84` — Redis Streams relay loop (100ms poll)

---

## Open Questions

1. **Redis Streams in production?** The Event Bus (`backend/v9/event_bus/`) and WS relay (`ws/manager.py`) depend on Upstash Redis Streams. If `UPSTASH_REDIS_REST_URL` is empty, all Redis operations silently return `None`. Is Redis actually configured and flowing in the current local deployment, or is all real-time data flowing through HTTP POST + in-memory state?

2. **Snapshot Service dead code?** `backend/v9/services/snapshot_service/` reads from Redis keys `mems26:v9:{name}:latest`, but the cockpit switched to the `systems-snapshot` endpoint that reads in-memory state. Is the snapshot service still used by anything?

3. **Frontend polling density.** The cockpit makes roughly 15-20 parallel polling loops at intervals from 500ms to 60s. During RTH, the aggregate request rate is estimated at ~8-10 req/s from a single browser tab. Is this causing observable backend load or latency?

4. **HistoricalReplay permanently disabled?** `V9_DO_WARMUP` defaults to off since P30 2026-05-20 due to startup hang. Does this mean systems start cold every time? What is the impact on Day Type/TPO accuracy in the first hour of RTH?

5. **Two chart components.** Both `ChartV5a.tsx` (831 lines) and `ChartV5b.tsx` (964 lines) exist. Which is active? Are both rendered? ChartV5a has its own set of polling intervals.

6. **WoodiesCciPanel size.** At 1,425 lines, this is the largest frontend component. Is it stable or under active development?

7. **Backend inline DayType handler.** The `_day_type_on_bar` closure in `main.py` (lines 162-283) is 120 lines of inline business logic including direct SQLite writes. This is the most complex piece of startup wiring. Should it be extracted?
