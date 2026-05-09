# V9 Bridge Changes — W2

## Architecture

```
SierraChart DLL (W1)
  → writes 7 JSON files to /SierraChart_Data/v9_export/
  → Bridge polls files every 2s (configurable V9_POLL_INTERVAL)
  → On change: push to Redis (Upstash) + POST to FastAPI (W3)
```

## Files Added

| File | Purpose |
|------|---------|
| `bridge/json_bridge.py` | Main entry point — starts all 7 stream threads |
| `bridge/v9_streams/base_stream.py` | Base class: file watch, Redis push, API push, heartbeat, retry |
| `bridge/v9_streams/tick_reversal_15_stream.py` | 15-tick reversal bars |
| `bridge/v9_streams/tick_reversal_12_stream.py` | 12-tick reversal bars |
| `bridge/v9_streams/footprint_stream.py` | Bid×Ask footprint per bar |
| `bridge/v9_streams/volume_profile_stream.py` | POC/VAH/VAL profile per bar |
| `bridge/v9_streams/imbalance_flags_stream.py` | 250%+ ratio imbalance flags |
| `bridge/v9_streams/stacked_imbalances_stream.py` | 3+ consecutive imbalance stacks |
| `bridge/v9_streams/cumulative_delta_stream.py` | Running delta + divergence |

## Redis Keys (Upstash)

| Key | Type | Description |
|-----|------|-------------|
| `mems26:v9:tick_reversal_15` | LIST | Last 100 snapshots |
| `mems26:v9:tick_reversal_15:latest` | STRING | Most recent snapshot |
| `mems26:v9:tick_reversal_12` | LIST/STRING | Same pattern |
| `mems26:v9:footprint` | LIST/STRING | Same pattern |
| `mems26:v9:volume_profile` | LIST/STRING | Same pattern |
| `mems26:v9:imbalance` | LIST/STRING | Same pattern |
| `mems26:v9:stacked_imbalance` | LIST/STRING | Same pattern |
| `mems26:v9:cumulative_delta` | LIST/STRING | Same pattern |
| `*:heartbeat` | STRING | Unix timestamp, updated every 30s |

## FastAPI Endpoints (W3 placeholders)

- `POST /api/v9/bars/tick_reversal?tick_count=15`
- `POST /api/v9/bars/tick_reversal?tick_count=12`
- `POST /api/v9/bars/footprint`
- `POST /api/v9/bars/volume_profile`
- `POST /api/v9/bars/imbalance`
- `POST /api/v9/bars/stacked_imbalance`
- `POST /api/v9/bars/cumulative_delta`

## Environment Variables

| Var | Default | Description |
|-----|---------|-------------|
| `V9_EXPORT_DIR` | `/Users/michael/SierraChart_Data/v9_export` | DLL output directory |
| `UPSTASH_REDIS_REST_URL` | — | Upstash Redis REST endpoint |
| `UPSTASH_REDIS_REST_TOKEN` | — | Upstash auth token |
| `CLOUD_URL` | `https://mems26-web.onrender.com` | FastAPI backend URL |
| `BRIDGE_TOKEN` | `michael-mems26-2026` | API auth token |
| `V9_POLL_INTERVAL` | `2.0` | File poll interval (seconds) |

## Heartbeat + Retry

- Heartbeat: every 30s, writes Unix timestamp to `<key>:heartbeat` in Redis
- Retry: up to 3 consecutive errors before exponential backoff
- Deduplication: skips if `export_ts` hasn't changed since last push

## Running

```bash
cd bridge
python json_bridge.py
```

Graceful shutdown via SIGINT/SIGTERM.
