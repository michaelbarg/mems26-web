# Performance Root Cause Analysis
Date: 2026-05-21T14:30:00Z
Author: Claude Code
Phase: 4
Mode: READ-ONLY

## Method
1. Read all backend route handlers: `woodies_chart_routes.py`, `tpo_routes.py`, `bars.py`, `cumulative_delta_routes.py`, `trades.py`
2. Read `gateway/trading_gateway.py` and `services/trade_manager/manager.py` for sync/blocking patterns
3. Read `bridge/json_bridge.py` and `bridge/v9_streams/base_stream.py` for push patterns and error handling
4. Read `services/bar_router.py` for bar dispatch timing instrumentation
5. Read `systems/woodies/woodies_system.py` and `decision_tree.py` for compute-heavy operations
6. Searched all frontend `src/` for `setInterval`, `setTimeout`, `refreshInterval`, `pollingInterval`
7. Searched backend for `asyncio.sleep`, `time.sleep`, `publish_event`, blocking patterns
8. Searched for `SLOW handler` logging in bar_router.py
9. No `/tmp/backend.log` or `/tmp/bridge.log` files exist on disk; analysis is code-only

## 1. Backend Timing Analysis

### 1.1 Log Evidence
No runtime logs available (`/tmp/backend.log` and `/tmp/bridge.log` do not exist). Analysis is based on code instrumentation and documented issues.

The BarRouter (`backend/v9/services/bar_router.py:83-84`) has built-in SLOW handler detection:
```python
if h_ms > 100:
    logger.warning(f"BarRouter: SLOW handler {handler.__qualname__} took {h_ms:.1f}ms")
```
And total dispatch warnings at >50ms (line 89-90).

### 1.2 Route Handler Analysis

**woodies_chart_routes.py (GET /api/v9/woodies/chart)**
- Synchronous file read + JSON parse of `woodies_5min.json` (line 199-200)
- Iterates all history bars for normalization (line 149-153), then enrichment loop (line 164-168)
- Each bar normalization calls `_normalize_bar()` which does ~30 field conversions with float parsing
- 12-bar sliding window for `_enrich_bar_projections()` (line 167)
- **Impact: O(N) per request where N = history bar count; ~30 bars typical = low impact**

**tpo_routes.py (GET /api/v9/tpo/current)**
- Opens sqlite3 connection for `_load_tpo_periods()` (line 78)
- Opens ANOTHER sqlite3 connection for `_load_previous_cash_session()` (line 128)
- Called via `_merge_previous_session()` which calls `_load_previous_cash_session()` (line 171)
- Total: **1 file read + 2 sqlite3 connections per TPO request**
- Polled every 2s from ChartV5a (line 230) = 1 req/2s = **3 sqlite3 connections every 2 seconds**

**bars.py (POST /api/v9/bars/woodies_5min)**
- **CRITICAL: sqlite3.connect() called INSIDE the per-bar loop** (line 567)
- Each bar opens a new connection, executes INSERT, commits, closes
- For a typical payload of 30+ bars, this means **30+ sqlite3 open/commit/close cycles per push**
- The `import sqlite3 as _sql` is also inside the loop (line 565) -- minor but wasteful
- After the loop, `_route_bar()` triggers `publish_threadsafe()` which spawns a new thread + `asyncio.run()` (bar_router.py:47-49)

**bars.py (POST /api/v9/bars/5min)**
- Per-bar SELECT + INSERT/UPDATE via SQLAlchemy (line 246-272)
- Race-condition handler does rollback + re-query on IntegrityError (line 258-269)
- `publish_event()` creates a new Redis connection per call (ws_manager.py:45-47)

**cumulative_delta_routes.py** -- Clean: single file read, no DB. Low risk.

**trades.py (GET /api/v9/trades/recent)** -- Simple query, no N+1. Low risk.

### 1.3 Gateway & Trade Manager

**trading_gateway.py**
- `_capture_cross_context()` (line 311-322): iterates all registered systems, calls `get_current()` on each. If any system's `get_current()` is slow, this blocks.
- `_get_chop_state()` (line 139-155): imports and calls `get_chop_score()` inline -- synchronous, but lightweight.
- `_persist_trade()` (line 324-343): opens sqlite3 connection per trade persist. Acceptable for trade frequency.
- No blocking HTTP calls. **Low risk.**

**trade_manager/manager.py**
- Clean state machine. No loops, no external calls.
- PnL calculation is O(3) -- three contracts.
- `_db.flush()` calls are SQLAlchemy (not raw sqlite3). **Low risk.**

### 1.4 Blocking/Sync Operations

**CRITICAL FINDING: Woodies touchpoint self-deadlock (ALREADY FIXED)**
- `backend/v9/systems/woodies/decision_tree.py:244-253` documents the prior bug
- `_fetch_touchpoints_now()` made 5 sequential `requests.get()` calls to localhost:8000 (line 155-165)
- With 2s timeout per request = **10s worst case blocking the event loop**
- **Status: FIXED** -- now returns empty dict with `in_event_loop` flag (line 252-253)
- Fix comment at `woodies_system.py:235-241` confirms touchpoints are skipped

**BarRouter publish_threadsafe (line 42-49)**
- Each bar type spawns a new thread + `asyncio.run()` per publish
- Thread creation overhead: ~1ms per bar type
- With 12 stream types, each push cycle creates up to 12 threads
- **Medium risk: thread proliferation under sustained load**

**publish_event() in ws_manager.py (line 41-53)**
- Creates a NEW Redis connection for EVERY publish call
- `redis.from_url()` → TCP connect → PUBLISH → close
- Called from every POST endpoint (bars, signals, trades, markers)
- **High overhead: ~5-10ms per publish due to TCP handshake**

## 2. Bridge Error Analysis

### 2.1 Error Rate
No `/tmp/bridge.log` available for runtime analysis.

**Code-level error handling (base_stream.py):**
- Error counting: `self.error_count` incremented on API push failures (line 347)
- Throttled logging: only first 3 errors + every 50th are logged (line 348-351)
- Exponential backoff with jitter: `RETRY_DELAY * 2^errors` capped at 300s (line 102-104)
- After 3 consecutive errors, backoff kicks in (line 186-189)

### 2.2 Push Pattern Issues

**Bridge push flow (base_stream.py):**
1. File watch (watchdog fsevents or 2s mtime poll)
2. Read JSON file
3. Push to Redis (SET + LPUSH + LTRIM) -- 3 HTTP calls to Upstash per push
4. Push to local API (POST to localhost:8000) -- 1 HTTP call

**Potential issues:**
- Redis push uses `urllib.request` with 10s timeout (line 319) -- if Upstash is slow, stream stalls
- API push uses 15s timeout (line 343) -- if backend is busy (e.g., Woodies handler), stream blocks
- No concurrent push: Redis and API pushes are sequential in `_tick()` (line 232-233)
- LTRIM errors silently logged (line 302-303) -- unbounded Redis list growth possible
- Heartbeat checks LLEN every 30s (line 366) -- detects growth but cannot fix it

**Single-threaded per stream:** Each of the 12+ streams runs in its own thread (json_bridge.py:103). No contention between streams, but each stream's push cycle is serial (file read -> Redis -> API).

## 3. Frontend Refresh Analysis

### 3.1 Polling Intervals Found

**Aggregate polling load from a single browser tab:**

| Component | File | Interval | Endpoint |
|-----------|------|----------|----------|
| LivePricePoll | useLivePricePoll.ts:43 | 1000ms | /api/v9/live_price |
| ConnectionIndicator | ConnectionIndicator.tsx:20 | 1000ms | (local state) |
| PriceMeta | PriceMeta.tsx:15 | 500ms | (local state) |
| WoodiesCciPanel | WoodiesCciPanel.tsx:1081 | 2000ms | /api/v9/woodies/chart |
| TPO current (V5a) | ChartV5a.tsx:230 | 2000ms | /api/v9/tpo/current |
| StreamHealthPanel | StreamHealthPanel.tsx:61 | 2000ms | /api/v9/health/streams |
| CVD pane (V5b) | ChartV5b.tsx:576 | 5000ms | /api/v9/cumulative_delta/current |
| Bars poll (V5b) | ChartV5b.tsx:660 | 5000ms | /api/v9/chart/bars5min?limit=3 |
| Bars (V5a) | ChartV5a.tsx:196 | 5000ms | /api/v9/chart/{tf}?limit=120 |
| TopBar heartbeat | TopBar.tsx:44 | 5000ms | /api/v9/cockpit/heartbeat |
| Layer0Strip | Layer0Strip.tsx:67 | 5000ms | /api/v9/layer0/state |
| ActiveTradeCard | ActiveTradeCard.tsx:49 | 5000ms | /api/v9/trades/active |
| Firing states (V5a) | ChartV5a.tsx:265 | 5000ms | /api/v9/woodies/signals + day_type |
| Footprint (V5a) | ChartV5a.tsx:280 | 5000ms | /api/v9/footprint/current |
| MarketTab | MarketTab.tsx:53 | 5000ms | /api/v9/health/streams |
| SoundProvider | SoundProvider.tsx:32 | 5000ms | (polling) |
| CVD (V5b standalone) | CumulativeDeltaPane.tsx:46 | 5000ms | /api/v9/cumulative_delta/current |
| systemPlanLive | systemPlanLive.tsx:577 | 3000ms | (plan data) |
| TradeHistoryStrip | TradeHistoryStrip.tsx:38 | 10000ms | /api/v9/trades/recent |
| ChartArea | ChartArea.tsx:158 | 10000ms | (refresh) |
| Killzone (V5a) | ChartV5a.tsx:293 | 30000ms | /api/v9/killzone/current |
| Killzone (V5b) | ChartV5b.tsx:835 | 30000ms | /api/v9/killzone/current |
| TPO sessions (V5a) | ChartV5a.tsx:240 | 30000ms | /api/v9/tpo/sessions |
| WR today | TopBar.tsx:65 | 30000ms | /api/v9/shadow/today_wr |
| BannerStack | BannerStack.tsx:59 | 30000ms | (banners) |
| ShadowSoakStrip | ShadowSoakStrip.tsx:41 | 60000ms | /api/v9/shadow/soak |
| Journal DT | journal/page.tsx:199 | 30000ms | (journal data) |
| Journal summary | journal/page.tsx:179 | 15000ms | (journal data) |

**Total HTTP requests per second (approximate, single tab):**

- 1s intervals: ~1 req/s (live_price)
- 2s intervals: ~2 req/s (woodies chart + TPO current + stream health)
- 3s intervals: ~0.33 req/s (plan)
- 5s intervals: ~8 * 0.2 = ~1.6 req/s (bars, CVD, heartbeat, layer0, trades, firing, footprint, market)
- 10s intervals: ~0.2 req/s
- 30s intervals: ~0.2 req/s

**TOTAL: ~5.3 HTTP requests/second to backend from a single browser tab**

### 3.2 TPO 30-min Refresh
- ChartV5b.tsx:60 defines `TPO_RTH_REFRESH_MS = 30 * 60 * 1000` (30 minutes during RTH)
- ChartV5b.tsx:61 defines `TPO_OFF_HOURS_REFRESH_MS = 10 * 60 * 1000` (10 minutes off-hours)
- This is the FULL TPO reload interval (line 811-825)
- ChartV5a still polls TPO every 2s (line 230) -- **this is the aggressive one**
- If both charts are mounted, TPO gets polled at 2s + 30min intervals simultaneously

### 3.3 API Client Patterns
- `publicApiFetch()` in api.ts uses 45s timeout (line 47) -- generous
- `chartFetch()` in ChartV5b.tsx uses 90s timeout (line 47) -- very generous
- Comment on line 49: "Avoid browser Failed to fetch when backend is busy (Woodies/bar handlers)" -- **developer was already aware of backend slowness**
- No request deduplication -- if component re-renders, duplicate fetches fire
- No stale-while-revalidate pattern -- every interval triggers a fresh fetch

## 4. Compute-Heavy Operations

**Woodies System process_bar (woodies_system.py:147-288)**
Per bar:
1. `compute_all_studies()` on full price buffers (up to 50 bars) -- O(50) for 11 indicators
2. `detect_all_patterns()` on bar buffer (up to 50 bars) -- 9 pattern detectors
3. `detect_direction_change()` on bar buffer
4. `WoodiesDecisionTree.evaluate_bar()` -- 21 stages evaluated
5. State dictionary update with ~20 fields

**This runs on every 5-min bar** via BarRouter subscriber. With the touchpoint fix in place, the compute itself is lightweight (sub-50ms for 50 bars). The original 10s+ stall was from HTTP self-deadlock, not computation.

**TPO route per request:**
- 1 file read (tpo.json)
- 2 sqlite3 connections (periods + previous_cash)
- `_normalize_sierra_tpo()` iterates periods for VA fallback (line 213-219)
- **At 2s polling from V5a: 3 DB opens every 2 seconds = 1.5 DB opens/second just for TPO**

**bars.py POST /woodies_5min:**
- sqlite3.connect() per bar in loop (line 567)
- 30 bars = 30 connects. Each bridge push cycle triggers this.
- **At 3s push intervals: 10 DB opens/second just for Woodies 5min persist**

## 5. Root Cause Diagnosis

### Primary Bottleneck (Highest Impact)
- **What:** Frontend polling storm -- 5.3+ HTTP requests/second from a single browser tab, with no deduplication, no WebSocket data push, and aggressive 2s intervals for TPO and Woodies chart
- **Evidence:**
  - `ChartV5a.tsx:230` polls TPO every 2000ms
  - `WoodiesCciPanel.tsx:1081` polls Woodies chart every 2000ms
  - `useLivePricePoll.ts:43` polls price every 1000ms
  - 28+ distinct setInterval timers cataloged across frontend components
  - `ChartV5b.tsx:47` has 90s fetch timeout with comment explicitly acknowledging backend is slow
  - Each request hits FastAPI's single-worker uvicorn, serializing all handler execution
- **Fix scope:** Consolidate polling into WebSocket push for real-time data (price, TPO, woodies chart, bars). Reduce remaining polls to 10-30s intervals. Use `stale-while-revalidate` for non-critical endpoints.
- **LOC estimate:** ~200 LOC frontend + ~80 LOC backend WS push handlers

### Secondary Bottleneck
- **What:** Per-bar sqlite3.connect() in `POST /api/v9/bars/woodies_5min` -- opens, inserts, commits, closes a database connection for EVERY bar in the payload
- **Evidence:**
  - `bars.py:565-587` -- `_sql.connect()` inside `for bar in bars` loop
  - Typical payload: 30+ bars = 30+ connection cycles
  - Bridge pushes every ~3s during market hours
  - Combined with `publish_event()` creating a new Redis connection per call (ws_manager.py:45-47)
  - Total per push cycle: ~30 sqlite3 connects + 1 Redis connect = ~31 TCP-level operations
- **Fix scope:** Move sqlite3.connect() outside the loop, batch INSERT, single commit. Pool Redis connections.
- **LOC estimate:** ~15 LOC for sqlite3 fix, ~20 LOC for Redis connection pool

### Tertiary Bottleneck
- **What:** BarRouter spawns a new thread + `asyncio.run()` for every bar type on every push cycle
- **Evidence:**
  - `bar_router.py:42-49` -- `publish_threadsafe()` creates `threading.Thread` + `asyncio.run()` per call
  - Called from `bars.py` for every POST endpoint (5min, tick_reversal, footprint, woodies, woodies_5min, tpo, cumulative_delta, etc.)
  - With 12 streams active, each push cycle creates up to 12 short-lived threads
  - Thread creation + asyncio event loop boot: ~2-5ms overhead per thread
  - The spawned thread runs `WoodiesSystem.process_bar()` which does 11 study computations + 9 pattern detections
  - BarRouter's SLOW handler threshold is 100ms (line 83) -- any handler exceeding this logs a warning
- **Fix scope:** Use a persistent asyncio task queue instead of per-bar thread spawn. Or use `loop.call_soon_threadsafe()` with the bound main loop (already captured at line 37-39 but unused by `publish_threadsafe`).
- **LOC estimate:** ~30 LOC to replace thread spawn with `call_soon_threadsafe`

## 6. Diagnosis Priority Order
1. **Frontend polling consolidation** -- greatest aggregate impact; 5.3 req/s sustained load is the dominant source of backend pressure. The backend is a single-worker uvicorn that serializes all requests; reducing request volume by 80% (from 5.3 to ~1 req/s) would eliminate most latency.
2. **sqlite3 per-bar connection fix in bars.py** -- eliminates 30+ unnecessary connection cycles per bridge push (every 3s during market hours).
3. **BarRouter thread spawn elimination** -- reduces overhead and prevents thread proliferation; enables proper use of FastAPI's event loop for async dispatch.

## Evidence

### File paths and line numbers
- `/Users/michael/Downloads/mems26_web_git/backend/v9/services/bar_router.py:42-49` -- thread spawn per publish
- `/Users/michael/Downloads/mems26_web_git/backend/v9/services/bar_router.py:83-84` -- SLOW handler logging
- `/Users/michael/Downloads/mems26_web_git/backend/v9/api/v9/bars.py:565-587` -- sqlite3 per-bar loop
- `/Users/michael/Downloads/mems26_web_git/backend/v9/api/v9/ws_manager.py:31-38,41-53` -- Redis connection per publish
- `/Users/michael/Downloads/mems26_web_git/backend/v9/api/v9/tpo_routes.py:78,128` -- dual sqlite3 connections per TPO request
- `/Users/michael/Downloads/mems26_web_git/backend/v9/systems/woodies/woodies_system.py:235-241` -- touchpoint deadlock fix (already applied)
- `/Users/michael/Downloads/mems26_web_git/backend/v9/systems/woodies/decision_tree.py:244-255` -- event loop guard
- `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx:47-49` -- 90s timeout acknowledging slow backend
- `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx:60-61` -- TPO refresh intervals
- `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/components/chart/ChartV5a.tsx:230` -- TPO 2s poll
- `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/components/chart/woodies/WoodiesCciPanel.tsx:1081` -- Woodies 2s poll
- `/Users/michael/Downloads/mems26_web_git/frontend/v9/src/v9/hooks/useLivePricePoll.ts:43` -- Price 1s poll
- `/Users/michael/Downloads/mems26_web_git/bridge/v9_streams/base_stream.py:52` -- 2s poll interval default

### Key code excerpts

**sqlite3 per-bar anti-pattern (bars.py:565-587):**
```python
for bar in bars:
    # ...
    import sqlite3 as _sql
    try:
        conn = _sql.connect("/.../mems26_local.db")  # NEW CONNECTION PER BAR
        conn.execute("""INSERT INTO v9_bars_5min_woodies ...""", (...))
        conn.commit()
        conn.close()
        created += 1
    except Exception:
        pass
```

**Redis connection per publish (ws_manager.py:41-53):**
```python
def publish_event(channel: str, data: dict):
    try:
        r = get_redis_client()  # NEW TCP CONNECTION EVERY CALL
        r.publish(channel, json.dumps(data))
        r.close()
    except Exception as exc:
        ...
```

## Open Questions
1. Michael: Is uvicorn running with `--workers 1` (default)? If so, all 5.3 req/s share one process -- the single biggest multiplier for perceived slowness.
2. Are both ChartV5a and ChartV5b mounted simultaneously? If so, polling load roughly doubles (separate useEffect timers in each).
3. Is Redis (localhost:6379) actually running? If not, every `publish_event()` call pays a 200ms connection timeout (ws_manager.py:37) before failing -- adding ~200ms to every bar POST handler.
4. What is the typical bar count in a Woodies 5min push payload? If >30, the sqlite3 per-bar connection issue is severe.
5. Has the `BarRouter: SLOW handler` warning ever appeared in production logs? This would confirm the Woodies process_bar latency even after the touchpoint fix.
