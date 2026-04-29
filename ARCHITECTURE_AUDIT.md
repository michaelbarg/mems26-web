# MEMS26 Architecture Audit

Generated: 2026-04-29 | DLL v7.14.1 | Bridge V6.7.0 | Backend 53 endpoints | Frontend 24 components

---

## 1. BACKEND INVENTORY

### 1.1 Python Modules

| File | Lines | Purpose |
|------|-------|---------|
| main.py | 3596 | FastAPI server: 53 endpoints, Redis/WS, trade execution |
| quality_score.py | 204 | Day-adaptive quality scoring, position sizing, targets |
| day_config.py | 62 | Day-type weights, thresholds, BE rules, target rules |
| analytics.py | 432 | MAE/MFE, daily/weekly reports, pattern analysis |
| database.py | 516 | Postgres (asyncpg): trades + setup_attempts tables |
| engine/models.py | 120 | Dataclasses: Bar, Features, MarketData, SignalResult |
| engine/signal_engine.py | 234 | Claude AI signal analysis (Sonnet 4.5) |
| tests/test_stop_validation.py | 157 | Stop validation tests |

### 1.2 All Endpoints (53 total)

#### Market Data (8)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| POST | /ingest | Receive market data from bridge | Bridge (unused — bridge writes to Redis directly) |
| GET | /market/latest | Current market snapshot from Redis | Frontend (multiple panels), Quality preview |
| POST | /ingest/history | Load 960 historical candles | Bridge (startup seed) |
| GET | /market/candles | 3m candles (960 max) | Frontend chart |
| GET | /market/candles/5m | 5m candles | Frontend chart |
| GET | /market/candles/15m | 15m candles | Frontend chart |
| GET | /market/candles/30m | 30m candles | Frontend chart |
| GET | /market/candles/1h | 1h candles | Frontend chart |

#### AI Analysis (3)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /market/analyze | Claude AI analysis (cached 45s) | Frontend "Ask AI" button |
| GET | /market/bias | Rule-based macro bias (EMA 20/50, swing) | Frontend |
| GET | /market/pre-analysis | Deterministic pre-analysis | Frontend |

#### Indicator State (3)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /vegas/state | Vegas Tunnel state | VegasTunnelPanel |
| GET | /tpo/state | TPO POC/VAH/VAL | TPOPanel |
| GET | /trigger/state | Active FVG/SWEEP/REVERSAL triggers | TriggerPanel |

#### Quality Score (3)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /quality/preview | Quality score (GET params) | Frontend (unused?) |
| POST | /quality/preview | Quality score (POST with day override) | QualityScorePanel, DayTypeHero, StrategyPreview |
| — | — | Also auto-logs attempts to Postgres | — |

#### Trade Execution (7)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| POST | /trade/execute | Full execution pipeline (12-step validation) | Frontend BUY/SHORT button |
| POST | /trade/close | Close active trade (P&L, CB update) | Frontend, Bridge EOD flatten |
| POST | /trade/bailout | Aggressive FP_BAILOUT exit | ActiveTradePanelV2 |
| POST | /trade/scale | Scale out C1/C2/C3 | Frontend |
| POST | /trade/modify-stop | Modify stop price (50pt limit) | ActiveTradePanelV2 |
| POST | /trade/modify-target | Modify T1/T2/T3 (50pt limit) | ActiveTradePanelV2 |
| GET | /trade/status | Active trade with live P&L | Frontend |

#### Trade State (5)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /trade/state/{trade_id} | Full trade state (per-contract) | ActiveTradePanelV2 |
| POST | /trade/state | Receive trade_state.json from Bridge | Bridge _poll_trade_state |
| POST | /trade/event | Receive POSITION_CHANGE from Bridge | Bridge _poll_trade_events |
| POST | /trade/internal/set-order-ids | Testing: set 7 order IDs | Manual testing only |
| POST | /trade/health | Trade health check (0-100 score) | PreEntryChecklist |

#### Command Queue (5)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /trade/command | Get pending command for Bridge | Bridge _poll_trade_commands |
| POST | /trade/command/ack | Ack command | Bridge |
| POST | /trade/command/cancel | Enqueue CANCEL command | Frontend |
| DELETE | /trade/command | Clear command+status (testing) | Manual |
| POST | /trade/test-dispatch | Diagnostic: write test command | Manual |

#### Circuit Breaker (2)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /trade/circuit-breaker | CB status | PreEntryChecklist, Frontend |
| POST | /trade/circuit-breaker/reset | Reset CB state | Manual |

#### Trade Journal (5)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /trades/log | Trade log (Postgres + Redis fallback) | Frontend journal page |
| POST | /trades/log/test | Create test trade | Manual |
| POST | /trades/log/shadow | Persist shadow trade | Frontend |
| GET | /trades | All trades from Redis list | Frontend |
| POST | /trades | Save trade to Redis | Frontend |
| DELETE | /trades/{trade_id} | Delete trade | Frontend |
| GET | /trades/analyze/{trade_id} | AI analysis of trade | Frontend |

#### Analytics (7)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /analytics/daily | Daily report | AnalyticsTab |
| GET | /analytics/weekly | Weekly report | AnalyticsTab |
| GET | /analytics/patterns | Pattern analysis | AnalyticsTab |
| GET | /analytics/by-segment | Breakdown by day/killzone/setup | AnalyticsTab |
| GET | /analytics/attempts | Setup attempts | AnalyticsTab |
| POST | /analytics/attempts | Log setup attempt | Quality preview (auto) |
| GET | /analytics/export/trades | Export trades CSV/JSON | Frontend |
| GET | /analytics/export/attempts | Export attempts CSV/JSON | Frontend |
| GET | /analytics/export/all | Export all data bundle | Frontend |

#### System (5)
| Method | Path | Description | Called By |
|--------|------|-------------|----------|
| GET | /news/status | News Guard state | Frontend |
| GET | /api/versions | Version info | VersionModal |
| GET | /health | System health | Render health check |
| POST | /ws/broadcast | Broadcast to WS clients | Bridge |
| WS | /ws | WebSocket endpoint | Frontend |
| POST | /ingest/footprint | Store footprint data | Bridge |
| GET | /market/patterns | Get MSS/FVG patterns | Frontend |
| GET | /market/footprint | Get footprint bars | Frontend |

### 1.3 Redis Keys

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| mems26:latest | JSON | — | Current market snapshot |
| mems26:candles | LIST | — | 3m candles (960 max) |
| mems26:candles:5m | JSON array | — | 5m candles (288 max) |
| mems26:candles:15m | JSON array | — | 15m candles (96 max) |
| mems26:candles:30m | JSON array | — | 30m candles (48 max) |
| mems26:candles:1h | JSON array | — | 1h candles (64 max) |
| mems26:footprint | JSON | — | Footprint bars |
| mems26:patterns | JSON array | — | MSS/FVG patterns |
| mems26:trade:status | JSON | — | Active trade state |
| mems26:trade:command | JSON | 300s | Pending DLL command |
| mems26:daily:pnl | JSON | — | Daily P&L + trade count |
| mems26:trades | LIST | — | General trades list |
| mems26:tradelog:* | JSON | — | Closed trade log entries |
| mems26:bridge_config | JSON | — | Bridge config snapshot |
| mems26:news:state | JSON | — | News Guard state |
| mems26:seen_fills | SET | — | Dedup fill timestamps |

### 1.4 Constants & Thresholds

```
MODE              = SIM | LIVE
CB_SOFT_LIMIT     = $150 (SIM) / $100 (LIVE)
CB_HARD_LIMIT     = $200
CB_MAX_TRADES     = 3/day
CB_CONSEC_LOSSES  = 2 → 30min lock
CONTRACTS         = 3 (SIM) / 1 (LIVE)
STOP_MIN_PT       = 3.0pt
STOP_MAX_PT       = 15.0pt
T1_RR / T2_RR     = 1.5 / 3.0 (fallback; quality_score overrides)
COMMAND_TTL_SEC   = 300 (5min)
AI_CACHE_TTL      = 45s
```

### 1.5 Database Schema

**Table: trades** — 50+ columns including:
- Core: id, direction, entry_price, exit_price, stop, t1, t2, t3
- P&L: risk_pts, pnl_pts, pnl_usd, mae_pts, mfe_pts, exit_efficiency
- Context: setup_type, day_type, killzone, contracts, is_shadow
- Analytics: 15 strategic tags, entry_narrative (JSONB), setup_quality_score
- extra_json (JSONB) for overflow fields

**Table: setup_attempts** — 30+ columns including:
- Core: ts, direction, setup_type, level_name, price_at_detect
- Rejection: rejection_reason, pillars_detail
- Context: day_type, killzone, is_shadow
- Hypothetical: hypothetical_mae_60min_pts, hypothetical_mfe_60min_pts

---

## 2. FRONTEND INVENTORY

### 2.1 All Components (24 files)

| Component | Lines | API Endpoints | Used in Dashboard? |
|-----------|-------|---------------|-------------------|
| Dashboard.tsx | ~5000 | Multiple (core orchestrator) | IS the Dashboard |
| LightweightChart.tsx | ~470 | None (props-driven) | YES |
| ActiveTradePanelV2.tsx | ~300 | /trade/state, /trade/bailout, /trade/modify-stop, /trade/modify-target | YES |
| DayTypeHero.tsx | 118 | /market/latest, /quality/preview (POST) | YES |
| DayTypeBadge.tsx | 87 | /market/latest | YES |
| VegasTunnelPanel.tsx | ~120 | /vegas/state | YES |
| TPOPanel.tsx | ~120 | /tpo/state | YES |
| TriggerPanel.tsx | ~120 | /trigger/state | YES |
| QualityScorePanel.tsx | 228 | /market/latest, /quality/preview (POST) | YES |
| StrategyPreview.tsx | 89 | /market/latest, /quality/preview (POST) | YES |
| PreEntryChecklist.tsx | ~300 | /trade/health, /trade/circuit-breaker | YES |
| AnalyticsTab.tsx | ~600 | /analytics/daily | YES (dynamic import) |
| CVDPanel.tsx | ~100 | None (props-driven) | NO |
| DailyTracker.tsx | ~80 | None (props-driven) | NO |
| LevelsBadges.tsx | ~80 | None (props-driven) | NO |
| ReversalStatus.tsx | ~60 | None (props-driven) | NO |
| SignalCard.tsx | ~100 | None (props-driven) | NO |
| TradingChart.tsx | ~200 | None (props-driven) | NO |
| chartpanel.tsx | ~150 | Hardcoded API URL | NO (legacy) |
| VersionModal.tsx | ~80 | /api/versions | YES (conditional) |

### 2.2 Unused Components (9 files)

These exist as files but are NOT imported in Dashboard.tsx:
1. **CVDPanel.tsx** — standalone CVD display (props-driven)
2. **DailyTracker.tsx** — daily trade counter (props-driven)
3. **LevelsBadges.tsx** — price level badges (props-driven)
4. **ReversalStatus.tsx** — reversal pattern status (props-driven)
5. **SignalCard.tsx** — signal display card (props-driven)
6. **TradingChart.tsx** — alternative canvas-based chart (props-driven)
7. **chartpanel.tsx** — legacy chart (hardcoded API URL)

**Assessment**: CVDPanel, LevelsBadges, ReversalStatus were likely built during earlier phases and superseded by Dashboard.tsx's inline implementations. chartpanel.tsx is clearly legacy.

### 2.3 Duplicate Polling

Three components all poll the SAME two endpoints independently:

| Component | Endpoints | Interval |
|-----------|-----------|----------|
| DayTypeHero | /market/latest + /quality/preview | 30s |
| QualityScorePanel | /market/latest + /quality/preview | 5s |
| StrategyPreview | /market/latest + /quality/preview | 30s |

Plus DayTypeBadge also polls /market/latest every 30s.

**Result**: 4 independent fetches of /market/latest, 3 of /quality/preview running in parallel.

### 2.4 Overlap: DayTypeBadge vs DayTypeHero

Both display day type classification:
- **DayTypeBadge**: Small inline badge, shows type + confidence
- **DayTypeHero**: Full panel with strategy details, weights, BE

Both are rendered in Dashboard. DayTypeBadge was kept "for now" per commit message. Should be removed once DayTypeHero is verified.

---

## 3. DLL INVENTORY (v7.14.1)

### 3.1 Persistent Keys (24 total)

| Key ID | Name | Purpose |
|--------|------|---------|
| 101-107 | C1/C2/C3_TARGET_ID, C1/C2/C3_STOP_ID, BUY_PARENT_ID | Bracket order IDs |
| 111-117 | C1/C2/C3_LAST_STATUS, S1/S2/S3_LAST_STATUS, PARENT_LAST_STATUS | Order status tracking |
| 118 | STATE_FILE_COUNTER | trade_state.json write counter |
| 121-129 | C1/C2_FILLED, C3_ACTIVE, ENTRY_PRICE, BE_APPLIED, BE_STRATEGY, C2_TARGET, STOP_PRICE, C3_ENABLED | Fill & BE tracking |
| 130 | TRIGGER_COUNTER | Unique trigger ID counter |
| 200 | (unnamed) | Position quantity tracking |
| 210 | LAST_CHECKSUM | Command dedup |
| 220-221 | VEGAS_TREND_DIR, VEGAS_PENDING_FLIPS | Vegas hysteresis state |

### 3.2 JSON Output Blocks in mes_ai_data.json

Top-level: `timestamp`, `symbol`, `current_price`, `session_phase`, `session_min`

Nested blocks:
1. `cvd` — CVD current/change/trend/volumes
2. `vwap` — value/distance/above/pullback
3. `woodies_cci` — cci14/cci6/trend/turbo/zlr/hook signals
4. `market_profile` — poc/vah/val/session_high/low/tpo_poc/prev_day_poc
5. `day_context` — day_type/ib/or/gap/extensions
6. `volume_context` — current_vol/avg_vol_20/rel_vol
7. `candle_patterns` — bar0/bar1/bar2/engulfing
8. `woodi_pivots` — pp/r1/r2/s1/s2
9. `time_levels` — weekly/72h/prev/daily_open/overnight
10. `order_flow` — absorption/sweeps/imbalances array
11. `footprint_bools` — absorption/exhaustion/trapped/stacked/pullback
12. `mtf` — m3/m5/m15/m30/m60 OHLCV+delta
13. `footprint` — 10 recent bars with delta/imbalance
14. `order_fills` — actual fills from Sierra
15. `vegas` — ema144/169/tunnel/trend/quality (V7.10.0, null if <50 bars)
16. `tpo` — current_day/previous_day POC/VAH/VAL (V7.11.0, null if no study)
17. `triggers` — active FVG/SWEEP/REVERSAL + footprint_last_bar (V7.12.0)
18. `day_classification` — type/confidence/metrics (V7.13.0)

### 3.3 Trade Command Types

| Command | Handler | Description |
|---------|---------|-------------|
| BUY/SELL | Full bracket | 3 OCO groups (C1+C2+C3 targets + 3 stops) |
| CLOSE | FlattenAndCancel | Close all positions + cancel orders |
| CANCEL | CancelAllOrders | Cancel pending orders |
| SCALE_OUT | (via CLOSE pattern) | Partial exit |
| ARM_BE | Modify stops to entry | Break-even all 3 stops |
| BAILOUT | FlattenAndCancel | Same as CLOSE but tagged differently |
| MODIFY_STOP | Modify 3 stops | Change stop price on all brackets |
| MODIFY_TARGET | Modify targets | Change T1/T2/T3 prices |

### 3.4 Output Files

| File | Trigger | Content |
|------|---------|---------|
| mes_ai_data.json | Every ExportIntervalSec (3s) | Full market data JSON |
| mes_ai_history.json | Periodic | 960-bar history with indicators |
| trade_state.json | On order status transition | 7 order statuses + fill prices |
| trade_events.json | On position quantity change | prev_qty/new_qty/prices |

### 3.5 Configurable Inputs (sc.Input[])

| Index | Name | Default |
|-------|------|---------|
| 0 | Export JSON Path | C:\SierraChart2\Data\mes_ai_data.json |
| 1 | Export Interval (seconds) | 3 |
| 2 | Value Area % | 70.0 |
| 3 | Imbalance Ratio | 3.0 |
| 4 | IB Period (minutes) | 60 |
| 5 | History JSON Path | C:\SierraChart2\Data\mes_ai_history.json |
| 6 | Footprint Bars | 10 |
| 7 | Trade Command JSON Path | trade_command.json |
| 8 | Trade Result JSON Path | trade_result.json |
| 9 | Bridge Token | michael-mems26-2026 |
| 10 | TPO Previous Day Study ID | 1 (0=disabled) |
| 11 | TPO Current Day Study ID | 3 (0=disabled) |

---

## 4. BRIDGE INVENTORY

### 4.1 Redis Keys Written

| Key | Method | Content |
|-----|--------|---------|
| mems26:latest | SET | Enriched market data (enrich() output) |
| mems26:candles | RPUSH/LTRIM | 3m candles (max 960) |
| mems26:candles:5m | SET (JSON array) | 5m candles (max 288) |
| mems26:candles:15m | SET (JSON array) | 15m candles (max 96) |
| mems26:candles:30m | SET (JSON array) | 30m candles (max 48) |
| mems26:candles:1h | SET (JSON array) | 1h candles (max 64) |
| mems26:patterns | SET | Detected patterns |
| mems26:seen_fills | SADD | Fill timestamp dedup |
| mems26:news:state | SET | News guard state |
| mems26:bridge_config | SET | Bridge version/config |

### 4.2 Field Mapping (DLL → Bridge → Redis)

**Pass-through (unchanged):**
- mtf (m3/m5/m15/m30/m60)
- vwap (entire object)
- woodies_cci
- volume_context
- candle_patterns
- footprint (array)
- footprint_bools
- order_fills
- open_orders
- vegas (V7.10.0)
- tpo (V7.11.0)
- triggers (V7.12.0)
- day_classification (V7.13.0)

**Renamed:**
| DLL Field | Bridge Field |
|-----------|-------------|
| current_price | price |
| cvd.current | cvd.total |
| cvd.change_20bar | cvd.d20 |
| cvd.change_5bar | cvd.d5 |
| woodi_pivots | woodi |
| time_levels.h72_high | levels.h72 |
| time_levels.h72_low | levels.l72 |

**Computed by Bridge (not in DLL):**
- cvd.bull (boolean from trend)
- cvd.m15_delta, cvd.m60_delta
- session.sh, session.sl (from market_profile)
- levels.above_open
- order_flow.imbalance_bull/bear (counts)
- order_flow.liq_sweep (backward compat alias)
- day.range (session_high - session_low)
- reversal.rev15_type/price, rev22_type/price
- wall_ts, news_guard, current_candle

### 4.3 Polling Functions

| Function | Polls | Interval | Action |
|----------|-------|----------|--------|
| _poll_trade_events | trade_events.json (mtime) | 1s | POST /trade/event |
| _poll_trade_state | trade_state.json (mtime+counter) | 1s | POST /trade/state |
| _poll_trade_commands | GET /trade/command | 1-2s | Write trade_command.json |
| _heartbeat_watchdog | Redis + SC staleness | 30s | Log warnings |
| _eod_flatten_check | Time check | 60s | POST /trade/close at 15:59 ET |
| news_guard_loop | ForexFactory API | Once/day | Update news state |

### 4.4 Key Constants

```
POST_INTERVAL     = 0.5s (Redis update frequency)
CANDLE_INTERVAL   = 180s (3-minute bars)
STALE_THRESHOLD   = 120s
MAX_CANDLES       = 960
BRIDGE_VERSION    = "V6.7.0"
```

---

## 5. CRITICAL ISSUES

### 5.1 HIGH Priority (Bugs / Broken)

1. **POST /ingest endpoint is dead code** — Bridge writes directly to Redis via Upstash REST API, never calls /ingest. The endpoint exists but is unused. (Lines 300-309 in main.py)

2. **DayTypeBadge renders alongside DayTypeHero** — Duplicate display. Commit message says "kept for now" but creates visual noise and extra API call.

3. **Field name mismatch: current_price vs price** — DLL writes `current_price`, Bridge renames to `price`. Backend quality_score.py had to add multi-field fallback (`price || current_price || bar.c`). This is fragile.

4. **Bridge config.py STOP_MAX_PT = 8.0** — But backend main.py and frontend both use 15.0 (V7.8.2 change). Bridge config is stale/unused for this value but could confuse.

5. **3 components poll /quality/preview independently** — QualityScorePanel (5s), DayTypeHero (30s), StrategyPreview (30s) all make separate POST requests. Should share data via React context or parent state.

### 5.2 MEDIUM Priority (Dead Code / Cleanup)

6. **9 unused frontend components** — CVDPanel, DailyTracker, LevelsBadges, ReversalStatus, SignalCard, TradingChart, chartpanel.tsx are never imported. ~770 lines of dead code.

7. **chartpanel.tsx has hardcoded API URL** — Legacy component with stale URL pattern.

8. **engine/ directory** (models.py + signal_engine.py) — Only used by /market/analyze endpoint for Claude AI calls. Could be simplified since quality_score.py now handles scoring.

9. **redis_set_key_ex() unused** — Added in V7.10.0 for Vegas TTL, but never called. Vegas data stays in mems26:latest instead.

10. **get_nearby_levels() unused** — Added in V7.11.0, never wired to any endpoint or /trade/execute.

11. **get_active_triggers_by_type() unused** — Added in V7.12.0, never wired.

12. **validate_setup_against_vegas() partially redundant** — quality_score.py also checks Vegas alignment. Both run in /trade/execute pipeline (Vegas filter at line ~1810, then quality score at ~1950).

### 5.3 LOW Priority (Nice-to-Have)

13. **Hardcoded API URLs in 6 frontend files** — Should use environment variable or shared constant.

14. **Dashboard.tsx is 5000+ lines** — Monolithic component with inline business logic (setup detection, pattern scanning, level calculation). Should be split.

15. **No centralized API client** — Each component implements its own fetch/error handling.

16. **Poll intervals inconsistent** — 5s for some panels, 30s for others, no documented rationale.

17. **Bridge version (V6.7.0) vs DLL (v7.14.1)** — Major version gap in naming convention.

---

## 6. DATA FLOW MAPS

### Flow A: DLL Setup Detection → Quality Score → UI Display

```
1. DLL (MES_AI_DataExport.cpp)
   - Computes: vegas, tpo, triggers, day_classification, footprint_bools
   - Writes: mes_ai_data.json (every 3s)

2. Bridge (json_bridge.py)
   - Reads: mes_ai_data.json
   - Enriches: enrich(raw) adds session state, reversal detection
   - Passes through: vegas, tpo, triggers, day_classification
   - RENAMES: current_price → price
   - Writes to Redis: mems26:latest (every 0.5s)

3. Backend (main.py)
   - QualityScorePanel polls: GET /market/latest → gets price
   - QualityScorePanel posts: POST /quality/preview {direction, entry, stop}
   - _quality_preview_logic():
     a. Reads: mems26:latest from Redis
     b. Extracts: day_classification.type → day_type
     c. Calls: calculate_quality_score(data, direction, day_type)
     d. Calls: determine_position_size(score, "DEMO", day_type)
     e. Calls: calculate_targets(entry, stop, direction, data, day_type)
     f. Calls: get_be_strategy(day_type)
   - Returns: {score, breakdown, reasons, position, targets, day_type, be_strategy}

4. Frontend (QualityScorePanel.tsx)
   - Receives JSON response
   - Displays: score badge, breakdown table, target prices
   - Shows day_type pill, weight labels when non-default
```

### Flow B: User Clicks EXECUTE → Trade Placed → Logged

```
1. Frontend (Dashboard.tsx BottomTradeBar)
   - User clicks BUY/SHORT button
   - POST /trade/execute {direction, entry_price, stop, t1, t2, t3, setup_type}

2. Backend /trade/execute (main.py line 1902, 12-step pipeline):
   a. Parse body (direction, entry, stop, targets)
   b. Stop validation (3-15pt range)
   c. Entry mode check (STRICT/DEMO/RESEARCH from Redis bridge_config)
   d. X-Test-Override header check
   e. Circuit breaker check (daily P&L, consecutive losses, max trades)
   f. Killzone enforcement (London/NY Open/NY Close)
   g. News Guard check (PRE_NEWS_FREEZE blocks)
   h. Vegas Tunnel filter (direction must align with trend)
   i. Quality Score gate (day-adaptive thresholds)
   j. Target calculation (quality_score.calculate_targets)
   k. Create trade record in Redis (mems26:trade:status)
   l. Enqueue BUY command to Redis (mems26:trade:command) with checksum
   m. Increment daily trade count
   n. Persist to Postgres

3. Bridge (_poll_trade_commands)
   - Polls GET /trade/command every 1-2s
   - Validates checksum (SHA256)
   - Writes trade_command.json to Sierra Chart data directory

4. DLL (C5: Trade Command Execution)
   - Reads trade_command.json every 1s
   - Verifies checksum
   - Creates 3 OCO bracket orders (C1+C2+C3 with targets + stops)
   - Stores 7 order IDs in persistent keys (101-107)
   - Writes trade_result.json

5. Logging:
   - Redis: mems26:trade:status (live)
   - Redis: mems26:tradelog:{exit_ts} (on close)
   - Postgres: trades table (on open + on close)
   - Postgres: setup_attempts table (auto-logged from quality preview)
```

### Flow C: Active Trade → C1 Fills → BE Triggered → Stops Modified

```
1. DLL detects C1 target fill
   - Order status changes: C1 OPEN → FILLED
   - Writes trade_state.json with updated order statuses
   - Increments STATE_FILE_COUNTER

2. Bridge (_poll_trade_state)
   - Detects trade_state.json mtime change
   - Reads JSON, checks counter for dedup
   - POST /trade/state to Backend with full order state

3. Backend POST /trade/state (main.py line 2837)
   - Updates trade record in Redis: c1_status="FILLED", c1_fill_price=X
   - V7.9.0 ARM_BE trigger check:
     a. c1_status == "FILLED"
     b. active_management_state == "NORMAL" (idempotency)
     c. parent fill_price > 0
   - If all true:
     a. Set active_management_state = "BE_ARMED"
     b. Save trade to Redis
     c. Enqueue ARM_BE command to mems26:trade:command with checksum

4. Bridge (_poll_trade_commands)
   - Picks up ARM_BE command
   - ARM_BE bypasses bracket validation (in whitelist)
   - Writes to trade_command.json

5. DLL handles ARM_BE
   - Reads entry_price from command
   - Modifies all 3 stop orders to entry_price (break-even)
   - Sets BE_APPLIED persistent flag
   - Logs: "ARM_BE complete — 3/3 stops modified"
```

---

## 7. RECOMMENDATIONS

### HIGH Priority
1. **Remove DayTypeBadge from Dashboard** — DayTypeHero supersedes it. Saves 1 API poll.
2. **Share quality preview data** — Lift /quality/preview polling to Dashboard level, pass as props to DayTypeHero, QualityScorePanel, StrategyPreview. Eliminates 2 redundant API calls per cycle.
3. **Fix field name**: Standardize on `price` everywhere or `current_price` everywhere. Currently mixed.

### MEDIUM Priority
4. **Delete 7 unused components** — CVDPanel, DailyTracker, LevelsBadges, ReversalStatus, SignalCard, TradingChart, chartpanel.
5. **Delete redis_set_key_ex()** — Never used, adds confusion.
6. **Delete or wire get_nearby_levels() and get_active_triggers_by_type()** — Currently dead helper functions.
7. **Audit /ingest endpoint** — Either remove it or wire Bridge to use it instead of direct Redis writes.
8. **Consolidate Vegas checks** — validate_setup_against_vegas() in main.py and Vegas scoring in quality_score.py overlap. Consider removing the standalone filter and relying solely on quality score.

### LOW Priority
9. **Extract API_URL to env** — All 6 hardcoded instances should use process.env.NEXT_PUBLIC_API_URL.
10. **Split Dashboard.tsx** — Extract setup detection, pattern scanning, level calculation into separate modules.
11. **Add shared API client** — Centralize fetch, error handling, and auth headers.
12. **Standardize polling intervals** — Document why 5s vs 30s, or unify.
13. **Align Bridge version string** — "V6.7.0" vs "v7.14.1" naming convention mismatch.
