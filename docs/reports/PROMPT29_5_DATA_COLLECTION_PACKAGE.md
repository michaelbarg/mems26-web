# P29.5 — Data Collection Package

**Date:** 2026-05-18
**Status:** GREEN — 6/6 schema categories defined, 31 offline validation tests pass
**No SHADOW/DEMO/LIVE enabled. No trade_command writes. No bridge/services started.**

---

## Summary

P29.5 defines the storage/log contract for SHADOW data collection across 6 categories.
All schemas are Pydantic models validated offline — no runtime wiring, no SHADOW activation.

The schemas are grounded in existing system outputs (`get_state()`, `get_current()`,
`route_setup()`, `pre_fire_validator`, Woodies `decision_tree`, trade state machine).

## Schema Categories

### 1. Bars + Stream Health (`BarRecord`, `StreamHealthSnapshot`)

| Field | Type | Source |
|-------|------|--------|
| ts, open, high, low, close, volume | str, float×4, int | `bar_aggregator_5min.py` |
| session, is_partial | str, bool | BarRouter publish |
| stream.name, status, age_sec, push_count | str, enum, float, int | `StreamHealthService` |
| summary (green/yellow/red/grey counts) | dict | `get_all_streams()` |

**Validation:** `high >= low` enforced by model validator.

### 2. System State Snapshots (`S1-S6` models + `SystemStateSnapshot`)

| System | Model | Key Fields |
|--------|-------|------------|
| S1 Day Type | `S1DayTypeState` | day_type, confidence, classified, stage, opening_type |
| S2 Five-Min | `S2FiveMinState` | running, hydrated, mode, buffer_size, last_pattern |
| S3 Footprint | `S3FootprintState` | running, hydrated, last_pattern, bars_processed_today |
| S4 Woodies | `S4WoodiesState` | trend_state, cci_14, classification, ready_to_route, decision_tree |
| S5 TPO | `S5TPOState` | poc, vah, val, session, bars_processed_today |
| S6 Killzone | `S6KillzoneState` | current_zone, next_zone, clock_status, clock_mode |

**Cross-system wrapper:** `SystemStateSnapshot` captures all 6 at trade events
(entry, t1_hit, t2_hit, t3_hit, stop_hit, close). Trigger values validated.

### 3. Pre-Fire Decisions (`PreFireDecision`)

| Field | Type | Notes |
|-------|------|-------|
| system_id | str | T1_NUMBER_BAR / T2_WOODIES / T3_FOOTPRINT |
| direction | str | LONG / SHORT (validated) |
| entry_price, stop_price, t1_price, t2_price | float | |
| confidence, time_stop_minutes | int | |
| valid | bool | pre_fire_validator result |
| fail_reason | str? | null if valid |

### 4. Gateway Dry-Run Decisions (`GatewayDecision`)

| Field | Type | Notes |
|-------|------|-------|
| system_id | int | 2, 3, or 4 only (validated — S1 rejected) |
| shadow_trade_id | int | Always present |
| demo_trade_id, live_trade_id | int? | null in SHADOW mode |
| rejections | list | [{mode, reason}] |

### 5. Reason Trees (`ReasonTree`)

| Field | Type | Notes |
|-------|------|-------|
| system_id | int | 2, 3, or 4 |
| stages[] | list | stage_id (A1-B14), status (PASS/FAIL/SKIP/DELEGATED/PENDING), message, owner, details |
| outcome | str | fire / block / skip (validated) |
| classification, direction | str? | Pattern name, LONG/SHORT |

Covers the full Woodies 21-stage decision tree and is extensible to S2/S3 reason traces.

### 6. Lifecycle Events (`LifecycleEvent`)

| Field | Type | Notes |
|-------|------|-------|
| trade_id | int | |
| event_type | str | trade.opened / trade.filled / trade.t1_hit / ... |
| from_state, to_state | enum | PENDING / FILLED / PARTIAL / CLOSED |
| mode | str | shadow / demo / live (validated) |
| data | dict | Extra context (fill_price, pnl_usd, exit_reason, ...) |

## Retention Policy

| Category | Sink | TTL |
|----------|------|-----|
| bars | sqlite:v9_bars_5min | 90 days |
| stream_health | memory + sqlite:v9_stream_health | 30 days |
| system_snapshots | sqlite:v9_trade.cross_context (JSON) | 180 days |
| pre_fire | sqlite:v9_pre_fire_log | 90 days |
| gateway | sqlite:v9_trade (mode columns) | 180 days |
| reason_trees | sqlite:v9_reason_trees | 180 days |
| lifecycle | redis:v9:trades:events + sqlite:v9_trade_events | 90 days |

## Files

| File | Role |
|------|------|
| `backend/v9/shadow/__init__.py` | Package marker |
| `backend/v9/shadow/schemas.py` | 6 schema categories as Pydantic models |
| `tests/v9/shadow/__init__.py` | Test package marker |
| `tests/v9/shadow/test_shadow_schemas.py` | 31 offline validation tests |

## Tests

```
$ python3 -m pytest tests/v9/shadow/test_shadow_schemas.py -q
31 passed in 0.23s

$ python3 -m pytest tests/v9/ -q
1286 passed, 1 skipped
```

## Gaps / Deferred

| Gap | Status | Notes |
|-----|--------|-------|
| REQ-DATA-004 `get_prediction()` | DEFERRED to P29.6 | Per PROMPT_LIST_TO_LIVE.md — prediction APIs are a stretch goal |
| Runtime wiring (actual logging) | DEFERRED to Phase 5 | Schemas exist; no SHADOW activation until Phase 5 gate |
| SQLite table creation | NOT NEEDED YET | Tables will be created when SHADOW mode is wired |

## Safety Verification

- SHADOW activated: **no**
- DEMO enabled: **no**
- LIVE enabled: **no**
- `trade_command.json` written: **no**
- Bridge started/stopped: **no**
- Services started/stopped: **no**

## Phase Gate

**STOP: P29.5 is GREEN. Michael must explicitly approve Phase 3 → Phase 4 before
proceeding to SHADOW dashboard / frontend work.**
