# V9 Database Schema — MEMS26

## Version: v9.0.0
## Created: 2026-05-09

## Overview

V9 tables sit alongside V8 in the same PostgreSQL database. All tables use the `v9_` prefix to avoid conflicts. V8 tables are untouched.

## Tables (11)

### Market Data (4 tables)

| Table | Purpose | Source |
|-------|---------|--------|
| `v9_bars_5min` | 5-minute OHLCV bars + volume profile | Bridge / DLL |
| `v9_bars_tick_reversal` | Tick reversal bars (15/12-tick) + footprint | Bridge streams |
| `v9_bars_30min_woodies` | 30-min Woodies CCI bars (11 studies) | Bridge / DLL |
| `v9_tpo_bars` | TPO letters per price/period | System 5 |

### System Data (2 tables)

| Table | Purpose | Source |
|-------|---------|--------|
| `v9_system_signals` | Classifications from all 6 systems | Systems 1-6 |
| `v9_system_markers` | Visual chart markers/annotations | Systems 1-6 |

### Trading (3 tables)

| Table | Purpose | Source |
|-------|---------|--------|
| `v9_trades` | All trades (SHADOW/SIM/LIVE) | Trade engine |
| `v9_trade_management_log` | Stop moves, partials, adjustments | Active Trade Manager |
| `v9_daily_quality_reports` | EOD stats per system/mode | Stage 4 |

### Config (2 tables)

| Table | Purpose | Source |
|-------|---------|--------|
| `v9_system_configs` | Per-system, per-mode parameters | Admin |
| `v9_account_status` | Running PnL, trade count, margin | Account tracker |

## API Endpoints

### Bar Data (Bridge → API)

| Method | Endpoint | Bridge Stream |
|--------|----------|--------------|
| POST | `/api/v9/bars/5min` | — |
| POST | `/api/v9/bars/tick_reversal?tick_count=15` | tick_reversal_15 |
| POST | `/api/v9/bars/tick_reversal?tick_count=12` | tick_reversal_12 |
| POST | `/api/v9/bars/footprint` | footprint |
| POST | `/api/v9/bars/volume_profile` | volume_profile |
| POST | `/api/v9/bars/imbalance` | imbalance_flags |
| POST | `/api/v9/bars/stacked_imbalance` | stacked_imbalances |
| POST | `/api/v9/bars/cumulative_delta` | cumulative_delta |
| POST | `/api/v9/bars/woodies` | woodies_30min |
| POST | `/api/v9/bars/tpo` | — |
| GET | `/api/v9/bars/5min` | — |
| GET | `/api/v9/bars/tick_reversal?tick_count=N` | — |
| GET | `/api/v9/bars/woodies` | — |
| GET | `/api/v9/bars/tpo` | — |

### Signals & Markers

| Method | Endpoint |
|--------|----------|
| POST | `/api/v9/signals` |
| GET | `/api/v9/signals?system_id=N` |
| POST | `/api/v9/markers` |
| GET | `/api/v9/markers?system_id=N` |

### Trades

| Method | Endpoint |
|--------|----------|
| POST | `/api/v9/trades` |
| GET | `/api/v9/trades?mode=SHADOW` |
| GET | `/api/v9/trades/{id}` |
| POST | `/api/v9/trades/log` |

### Configs

| Method | Endpoint |
|--------|----------|
| GET | `/api/v9/configs` |
| GET | `/api/v9/configs/{system_id}/{mode}` |
| PUT | `/api/v9/configs/{system_id}/{mode}` |

## Auth

All endpoints require `Authorization: Bearer {BRIDGE_TOKEN}` header.
Default token: `michael-mems26-2026` (from env var `BRIDGE_TOKEN`).

## Migration Files

```
schema/v9_migrations/
├── V9_001_bars_5min.sql
├── V9_002_bars_tick_reversal.sql
├── V9_003_bars_30min_woodies.sql
├── V9_004_tpo_bars.sql
├── V9_005_system_signals.sql
├── V9_006_system_markers.sql
├── V9_007_trades.sql
├── V9_008_trade_management_log.sql
├── V9_009_daily_quality_reports.sql
├── V9_010_system_configs.sql
└── V9_011_account_status.sql
```

## Running Migrations

```bash
for f in schema/v9_migrations/V9_*.sql; do
  psql $DATABASE_URL -f "$f"
done
```

## Tests

```bash
PYTHONPATH=. python3 -m pytest tests/v9/db/ -v
```
