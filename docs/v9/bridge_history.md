# V9 Bridge Historical Backfill — W2.5

## V8 → V9 Comparison

| Feature | V8 (json_bridge.py) | V9 (v9_history.py) |
|---------|---------------------|---------------------|
| History source | `SC_HISTORY_PATH` (mes_ai_history.json) | Per-stream DLL export files (7 files) |
| File freshness | < 2 hours (604800s bug — actually 1 week) | < 168 hours (configurable `V9_HISTORY_MAX_AGE_H`) |
| Resume tracking | None — always reloads | `export_ts` saved to Redis, skips if unchanged |
| Dedup | None | By `export_ts` comparison |
| Redis structure | RPUSH to single `mems26:candles` list | Per-stream: SET latest + LPUSH history list |
| MTF aggregation | Aggregates 3m → 5m/15m/30m/60m from candles | Not needed — each stream has its own timeframe |
| Footprint seed | Once from Sierra footprint bars (200 bars) | Footprint is its own stream — loaded directly |
| API push | POST `/ingest/history` (bulk) | POST per-stream v9 endpoint |
| ET→UTC fix | `sc_ts_to_utc()` applied to all timestamps | Not needed — V9 DLL exports UTC timestamps |

## Architecture

```
Bridge Startup
  ├─ For each of 7 streams:
  │   ├─ historical_load()
  │   │   ├─ Check file exists
  │   │   ├─ Check file age (< V9_HISTORY_MAX_AGE_H)
  │   │   ├─ Check resume_ts in Redis (skip if same export_ts)
  │   │   ├─ Read JSON file
  │   │   ├─ SET <key>:latest in Redis
  │   │   ├─ LPUSH <key> (history list, max 100)
  │   │   ├─ SET <key>:resume_ts (save position)
  │   │   └─ POST to API (best-effort)
  │   └─ Start live polling loop
  └─ All 7 streams running
```

## Redis Keys (added by W2.5)

| Key | Type | Description |
|-----|------|-------------|
| `mems26:v9:<stream>:resume_ts` | STRING | Last loaded `export_ts` — prevents duplicate loads |

## Environment Variables

| Var | Default | Description |
|-----|---------|-------------|
| `V9_HISTORY_MAX_AGE_H` | `168` (1 week) | Max file age in hours before skipping |
| `SC_HISTORY_DAYS` | `30` | Backfill depth in days (for future use) |
| `V9_HISTORY_BATCH_SIZE` | `50` | Batch size for API POST (for future use) |

## Usage

### Normal startup (history + live)
```bash
cd bridge
python3 json_bridge.py
```
Each stream loads history automatically before going live.

### History-only mode (backfill then exit)
```bash
python3 json_bridge.py --history-only
```
Loads all 7 streams, reports status, then exits.

### Force reload (clear resume position)
Delete the resume keys in Redis, then restart:
```bash
# In redis-cli or via Upstash console:
DEL mems26:v9:tick_reversal_15:resume_ts
DEL mems26:v9:tick_reversal_12:resume_ts
# ... etc for all 7 streams
```

## Files

| File | Description |
|------|-------------|
| `bridge/v9_history.py` | Shared history module — `historical_load()`, `get_resume_ts()`, `clear_resume()` |
| `bridge/v9_streams/base_stream.py` | Updated — calls `historical_load()` on `start()` |
| `bridge/json_bridge.py` | Updated — `--history-only` flag |
