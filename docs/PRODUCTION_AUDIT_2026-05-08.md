# MEMS26 Production Audit — 8 May 2026

**Purpose:** Map backend architecture for Sprint 4 gate insertion points
**Sprint 4 Schema Lock:** `docs/MEMS26_SPRINT4_SCHEMA.md`

---

## Section 1: backend/ File Tree

| File | Lines | Description |
|------|-------|-------------|
| `main.py` | ~4700 | FastAPI server — all endpoints, Redis helpers, WebSocket, trade execution, analytics endpoints, circuit breaker |
| `quality_score.py` | 393 | Quality Score calculator (0-100), position sizing, target calculation, structural stop shadow |
| `day_config.py` | 62 | Day-type-adaptive weights, thresholds, target rules, BE rules (5 day types) |
| `database.py` | ~850 | asyncpg PostgreSQL — table creation, trade CRUD, setup attempt logging, outcome tracking |
| `analytics.py` | ~400 | Market context snapshots, daily/weekly reports, pattern analytics |
| `engine/signal_engine.py` | ~200 | Claude AI signal engine — builds prompt from MarketData, returns 1-10 score |
| `engine/models.py` | 120 | Dataclasses: `MarketData`, `Bar`, `Features`, `SignalResult` |
| `engine/__init__.py` | — | Package init |
| `tests/test_stop_validation.py` | — | Stop validation tests |
| `tests/__init__.py` | — | Package init |
| `requirements.txt` | 5 | Dependencies: fastapi, uvicorn, httpx, anthropic, asyncpg |

---

## Section 2: Quality Score Location

### Implementation
- **File:** `quality_score.py`
- **Main function:** `calculate_quality_score(market_data, direction, day_type)` → returns `{total, breakdown, reasons, day_type_used, weights_applied}`
- **Score range:** 0–100 (sum of 4 components: vegas, tpo, fvg, footprint)
- **Weights:** Day-adaptive from `day_config.py` — always sum to 100

### Components (4)
1. **Vegas** (20-40 pts) — Tunnel trend match + flow-disagree override
2. **TPO** (20-35 pts) — Price vs POC position + Value Area membership
3. **FVG** (25 pts fixed) — Fair Value Gap direction match, recency-filtered (30 min)
4. **Footprint** (15-20 pts) — Delta confirmation + imbalance ratio

### Where Threshold Is Checked
- **Position sizing:** `determine_position_size(score, mode, day_type)` in `quality_score.py:207`
  - `score >= full_thresh` → 3 contracts (FULL_SIZE)
  - `score >= half_thresh` → 2 contracts (HALF_SIZE)
  - Below → REJECT (LIVE) or WARN (DEMO)
- **Thresholds by day type** (from `day_config.py`):
  - TREND_DAY: full=60, half=45
  - RANGE_DAY: full=70, half=55
  - NORMAL/DEVELOPING: full=70, half=50
  - GAP_FILL: full=65, half=50

### Call Sites
1. `main.py:991` — `/quality/preview` endpoint (both LONG and SHORT scored)
2. `main.py:2710-2714` — `/trade/execute` (gate: rejects if score below threshold in LIVE mode)

---

## Section 3: Existing Endpoints Inventory

### Data Ingestion (2)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Bridge pushes live market snapshot → Redis (auth: X-Bridge-Token) |
| POST | `/ingest/history` | Bulk load historical candles to Redis |
| POST | `/ingest/footprint` | Store footprint data in Redis |

### Market Data (10)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/market/latest` | Current market snapshot from Redis |
| GET | `/market/candles` | 960 × 3min candle history |
| GET | `/market/candles/5m` | 5-minute candles |
| GET | `/market/candles/15m` | 15-minute candles |
| GET | `/market/candles/30m` | 30-minute candles |
| GET | `/market/candles/1h` | 1-hour candles |
| GET | `/market/analyze` | Claude AI signal analysis (Sonnet) |
| GET | `/market/bias` | Market bias/direction analysis |
| GET | `/market/patterns` | Detected patterns from Redis |
| GET | `/market/footprint` | Footprint data from Redis |
| GET | `/market/pre-analysis` | Pre-trade market state analysis |

### State Endpoints (3)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/vegas/state` | Vegas Tunnel state from market data |
| GET | `/tpo/state` | TPO Dual Study state + nearby levels |
| GET | `/trigger/state` | Active triggers (FVG, SWEEP, REVERSAL) |

### Quality Score (2)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/quality/preview?direction=&entry=&stop=` | Preview quality score (GET) |
| POST | `/quality/preview` | Preview quality score (POST, supports day_type_override) |

### Trade Execution (12)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/trade/execute` | Open trade — validates gates, writes to Redis + DB |
| POST | `/trade/close` | Close active trade, update PnL |
| POST | `/trade/bailout` | Emergency close |
| POST | `/trade/modify-stop` | Modify stop price |
| POST | `/trade/modify-target` | Modify target price |
| POST | `/trade/scale` | Scale in/out of position |
| POST | `/trade/event` | Log trade event |
| POST | `/trade/health` | Trade health check |
| GET | `/trade/status` | Current trade status from Redis |
| GET | `/trade/state/{trade_id}` | Full trade state by ID |
| POST | `/trade/state` | Update trade state |
| POST | `/trade/internal/set-order-ids` | Set DLL order IDs on trade |

### Trade Commands (4)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/trade/command` | DLL polls for pending commands |
| POST | `/trade/command/ack` | DLL acknowledges command execution |
| POST | `/trade/command/cancel` | Cancel pending command |
| DELETE | `/trade/command` | Delete pending command |
| POST | `/trade/test-dispatch` | Test command dispatch |

### Circuit Breaker (2)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/trade/circuit-breaker` | Check circuit breaker state |
| POST | `/trade/circuit-breaker/reset` | Reset circuit breaker |

### Trade Journal (4)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/trades` | List all trades from Redis |
| POST | `/trades` | Add trade to journal |
| DELETE | `/trades/{trade_id}` | Delete trade |
| GET | `/trades/analyze/{trade_id}` | AI analysis of specific trade |

### Trade Logging (3)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/trades/log` | Get trade log from DB |
| POST | `/trades/log/test` | Create test trade log entry |
| POST | `/trades/log/shadow` | Create shadow trade log entry |

### Analytics (16)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/daily` | Daily analytics report |
| GET | `/analytics/weekly` | Weekly analytics report |
| GET | `/analytics/patterns` | Pattern frequency analysis |
| GET | `/analytics/by-segment` | Analytics by segment |
| GET | `/analytics/attempts` | Setup attempt history |
| POST | `/analytics/attempts` | Log setup attempt |
| GET | `/analytics/attempts/recent_with_score` | Recent attempts with quality score |
| GET | `/analytics/attempts/with_outcomes` | Attempts with trade outcomes |
| GET | `/analytics/setups/summary` | Setup summary stats |
| GET | `/analytics/setups/recent` | Recent setups |
| GET | `/analytics/setups/today_summary` | Today's setup summary |
| GET | `/analytics/setups/sequential_today_summary` | Sequential simulation summary |
| POST | `/analytics/setups/resimulate` | Resimulate setup outcomes |
| GET | `/analytics/setups/closed` | Closed setups |
| GET | `/analytics/setups/{setup_id}` | Single setup detail |
| GET | `/analytics/by_score_bucket` | Score bucket analysis |
| GET | `/analytics/data_quality_check` | Data quality diagnostics |
| GET | `/analytics/component_correlation` | Score component correlations |
| GET | `/analytics/by_killzone` | Analytics by killzone |
| GET | `/analytics/by_day_type` | Analytics by day type |
| GET | `/analytics/by_direction_hour` | Analytics by direction and hour |
| GET | `/analytics/export/trades` | Export trades CSV |
| GET | `/analytics/export/attempts` | Export attempts CSV |
| GET | `/analytics/export/all` | Export all data |

### System (4)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/versions` | API version info |
| GET | `/news/status` | News event state |
| POST | `/ws/broadcast` | Broadcast message to WebSocket clients |
| WS | `/ws` | WebSocket for real-time updates |

**Total: ~65 endpoints**

---

## Section 4: Where Gates Would Plug In

### Current Gate Chain in `/trade/execute` (main.py:2580)

The execution flow runs gates in this order:

```
1. Input validation (direction, entry, stop)
2. Stop width validation (3-15 pt range)
3. Entry mode detection (STRICT/DEMO from Redis bridge config)
4. Circuit Breaker check → 403 if tripped
5. Killzone enforcement → 403 if outside windows
6. News guard → 403 if PRE_NEWS_FREEZE
7. Vegas Tunnel filter → 400 if direction opposes trend
8. Quality Score gate → 400 if score below threshold
9. Active trade check → 409 if already open
10. Stop expansion (if below minimum)
11. Target calculation (frontend t1/t2/t3 or Quality Score fallback)
12. Trade object creation → Redis + Postgres
```

### Recommended Insertion Point for Suffering Side Gate

**Position: Between step 7 (Vegas) and step 8 (Quality Score)**

Reasoning:
- The Suffering Side Veto is a **binary gate** (PASS/BLOCK), not a scoring component
- It should run AFTER Vegas (which confirms directional alignment) but BEFORE Quality Score (which determines sizing)
- If suffering side blocks, there's no point calculating quality score
- It needs `day_poc` from Redis (`mems26:primitives`) — same data source as other gates
- It should respect `_skip_gates` flag (DEMO test override) like other gates
- It should respect `_exec_entry_mode` (DEMO proceeds with warning, LIVE blocks)

### Implementation Pattern

```python
# After Vegas filter (line ~2707), before Quality Score (line ~2709):

# === Suffering Side Gate (D-049, D-065) ===
if not _skip_gates:
    primitives = await redis_get_key("mems26:primitives")
    if primitives:
        day_poc = float(primitives.get("day_poc.price", 0))
        if day_poc > 0:
            price = entry
            NO_TRADE_ZONE_PT = 2.0
            distance = abs(price - day_poc)
            
            blocked = False
            reason = ""
            if distance <= NO_TRADE_ZONE_PT:
                blocked = True
                reason = "inside POC no-trade zone"
            elif direction == "LONG" and price < day_poc - NO_TRADE_ZONE_PT:
                blocked = True
                reason = "below POC — buyers suffer"
            elif direction == "SHORT" and price > day_poc + NO_TRADE_ZONE_PT:
                blocked = True
                reason = "above POC — sellers suffer"
            
            if blocked and _exec_entry_mode not in ("DEMO", "RESEARCH"):
                raise HTTPException(status_code=400, detail=json.dumps({
                    "ok": False,
                    "error": "SUFFERING_SIDE_VETO",
                    "reason": reason,
                    "day_poc": day_poc,
                    "price": price,
                    "distance_pts": round(distance, 2),
                    "source": "D-049, D-065",
                }))
```

### Gate vs Score

The Suffering Side Veto is a **gate** (binary PASS/BLOCK), NOT a quality score component. Do not add it to `quality_score.py` weights. It belongs in the execution chain in `main.py`, alongside Vegas filter and circuit breaker.

---

## Section 5: Setup Object Lifecycle

### Flow: DLL → Redis → Backend → DB

```
1. DLL (Sierra Chart)
   └─ MES_AI_DataExport.cpp writes mes_ai_data.json every 3s
   └─ Exports: OHLCV, CVD, VWAP, CCI, Market Profile, footprint

2. Bridge (json_bridge.py)
   └─ Reads mes_ai_data.json
   └─ Enriches: session state, ON high/low, daily open, reversals
   └─ Builds 3min candles
   └─ POST /ingest → main.py (auth: X-Bridge-Token)
   
3. Backend /ingest (main.py:730)
   └─ Stores full snapshot to Redis (mems26:latest)
   └─ Broadcasts via WebSocket to frontend

4. Frontend calcSetups()
   └─ Detects patterns (Sweep, Rejection, Momentum, etc.)
   └─ User clicks "Execute" → POST /trade/execute

5. POST /trade/execute (main.py:2580)
   └─ Runs gate chain (CB, killzone, news, Vegas, quality score)
   └─ Calls calculate_quality_score() → score + breakdown
   └─ Calls determine_position_size() → qty + exits
   └─ Calls calculate_targets() → c1/c2/c3
   └─ Calls snapshot_market_context() → enrichment tags
   └─ Writes trade to Redis (mems26:trade:status)
   └─ Writes command to Redis (mems26:trade:command) → DLL polls this
   └─ Writes trade to Postgres (insert_trade)
   └─ Calls mark_attempt_executed() → links to setup attempt

6. /quality/preview (main.py:956)
   └─ Auto-logs BOTH directions to setup_attempts table
   └─ Phase 6 dual-direction unbiased data collection
   └─ Enriches with strategic tags (15 fields)
   └─ Writes to DB via database.py
```

### Key Data Structures

**Market snapshot (Redis `mems26:latest`):**
```
{bar, session, cvd, vwap, woodi, vegas, tpo, volume_context,
 triggers, footprint_bools, mtf, day_classification, ...}
```

**Trade object (Redis `mems26:trade:status`):**
```
{id, direction, entry_price, stop, t1, t2, t3, risk_pts,
 setup_type, entry_ts, status, c1/c2/c3_status,
 setup_quality_score, day_type, pnl_pts, pnl_usd, ...}
```

**DLL command (Redis `mems26:trade:command`):**
```
{cmd, price, qty, stop, t1, t2, t3, brackets[],
 trade_id, expires_at, checksum, c1_target, c2_target,
 c3_mode, qty, score, score_breakdown}
```

---

## Section 6: Risks & Recommendations

### Risk 1: main.py Monolith (4700 lines)
The entire gate chain, all endpoints, Redis helpers, and WebSocket logic live in one file. Adding gates inline increases complexity. **Mitigating approach:** Add the gate as a standalone function (like `validate_setup_against_vegas`) at the module level, then call it from the execution chain. Do NOT split `main.py` — that's a refactor task, not a Sprint 4 goal.

### Risk 2: Redis Key Dependency
The Suffering Side gate needs `mems26:primitives` (new key from schema lock). If DLL hasn't been updated to populate it, the gate will have no data. **Recommendation:** Fail-open or fail-with-warning in the first week until DLL is deployed. Document this in the gate implementation.

### Risk 3: Quality Score Independence
`quality_score.py` is a pure function (no async, no Redis). Gates in `main.py` are async (read Redis). Don't mix — keep gates in `main.py`, scoring in `quality_score.py`. The boundary is clean and should stay clean.

### Risk 4: Gate Bypass in DEMO Mode
All current gates respect `_skip_gates` (test override) and `_exec_entry_mode` (DEMO/RESEARCH). New gates MUST follow the same pattern or tests will break and DEMO trading will be blocked unexpectedly.

### Risk 5: Setup Attempt Logging
`/quality/preview` auto-logs both LONG and SHORT attempts with 15 strategic tags. Sprint 4 adds 9 new DB columns (migration 005). The logging code in `main.py:1000-1230` must be updated to populate these new fields. This is a separate task — don't bundle it with gate implementation.

### Patterns to Follow
1. **Gate pattern:** Write a standalone function like `validate_setup_against_vegas()` (main.py:808). Returns bool. Called from `/trade/execute` chain.
2. **Error format:** Use `HTTPException(status_code=400, detail=json.dumps({...}))` with structured JSON (matches existing Vegas/Quality error format).
3. **Redis read:** Use `await redis_get_key("mems26:primitives")` for new data.
4. **Logging:** Use `log.info(f"[GATE_NAME] ...")` prefix pattern.
5. **Skip pattern:** Check `_skip_gates` and `_exec_entry_mode` before blocking.

### Helper Functions to Reuse
- `redis_get_key(key)` — read any Redis key (main.py:130)
- `redis_get()` — read market snapshot (main.py:54)
- `snapshot_market_context(data)` — enrich trade with market state (analytics.py:122)
- `get_config(day_type)` — get day-adaptive config (day_config.py:40)
- `validate_setup_against_vegas()` — reference gate implementation (main.py:808)
