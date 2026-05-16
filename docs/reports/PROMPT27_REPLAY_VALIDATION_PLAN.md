# Prompt 27: Replay Validation Plan

**Date:** 2026-05-16  
**Mode:** REPLAY (not SHADOW/DEMO/LIVE)  
**Purpose:** Prove full system works end-to-end with historical market data

---

## How Sierra Replay Timestamp Becomes Market Clock

```
Sierra Chart Replay Mode
  → DLL writes JSON with bar timestamps from historical session
  → Bridge reads JSON, pushes to backend
  → Backend BarRouter publishes bar event
  → MarketClock.update_replay_timestamp(bar.ts) called
  → All consumers use market_clock.now_utc() → returns replay timestamp
  → SessionClassifier, Killzone, DayType, TPO, TradeManager all see "historical time"
```

---

## Pre-Validation Commands

```bash
# 1. Set replay mode
export MEMS26_CLOCK_MODE=REPLAY

# 2. Restart services
bash scripts/restart_all.sh

# 3. Check status
bash scripts/run_stage.sh status_check

# 4. Verify clock mode
curl -s localhost:8000/api/v9/clock/state | python3 -m json.tool
# Expect: mode=REPLAY, status=PENDING (until first bar arrives)
```

---

## Endpoints to Verify During Replay

| Endpoint | Expected during replay |
|----------|----------------------|
| `/api/v9/day_type/current` | Classifies based on replay session IB |
| `/api/v9/five_min/fire` | Detects patterns when replay bars trigger |
| `/api/v9/footprint/fire` | Detects absorption/sweep on replay tick data |
| `/api/v9/woodies/fire` | Decision tree evaluates with replay time A4 |
| `/api/v9/tpo/current` | IB lock at replay 10:30 ET |
| `/api/v9/killzone/current` | Zone based on replay time (not wall clock) |
| `/api/v9/gateway/status` | shadow_active_count increases as patterns fire |
| `/api/v9/clock/state` | mode=REPLAY, now_et=replay time, source=bar |

---

## Systems to Watch

### S1 Day Type
- IB should lock at replay 10:30 ET (not real 10:30)
- Classification should reflect replay session data
- `/current` returns replay-time classification

### S2 Five-Min
- Mode should transition from WAITING_OPEN → FIRST_HOUR_TACTICAL at replay 9:30
- Patterns should detect on replay 5-min bars
- Fire should auto-route to gateway

### S3 Footprint/Reversal
- Process tick_reversal bars from replay data
- Absorption/sweep patterns should fire on replay extremes
- calculate_size uses replay delta/dominance

### S4 Woodies
- Subscribes to woodies_5min replay bars
- Decision tree A4 checks killzone at replay time (should PASS during replay RTH)
- ready_to_route should become true when patterns + killzone align

### S5 TPO
- IB lock timestamp from market_clock (replay time)
- POC migration stuck_minutes based on replay time
- Profile builds from replay bars

### S6 Killzone
- Zone detection based on replay ET time
- NY_OPEN / MIDDAY / NY_PM transitions at replay times
- Gate correctly allows/blocks at replay time boundaries

---

## Expected Log Pattern (successful replay)

```
[Main] MarketClock: REPLAY mode, waiting for first bar
[Bridge] Pushed woodies_5min bar ts=2026-05-14T09:35:00
[Main] MarketClock updated: 2026-05-14 09:35:00 ET (source=bar)
[Killzone] Zone transition: NY_OPEN (replay time)
[TPO] IB tracking: H=7465 L=7450 (bars 1-12)
[DayType] Stage: IB_BUILDING → LOCKED (replay 10:30)
[FiveMin] Mode: FIRST_HOUR_TACTICAL
[Woodies] Pattern ZLR detected, A4=PASS (killzone=NY_OPEN)
[Woodies] Auto-routed: ZLR LONG size=full
[Gateway] SHADOW trade recorded: sys=4 dir=LONG
[BarLevelDetector] T1 HIT: trade 1 at 7468.0
```

---

## Pass/Fail Checklist

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Clock in REPLAY mode | `curl .../clock/state` | mode=REPLAY |
| 2 | Clock updates from bar | push a bar, check now_et | now_et = bar timestamp |
| 3 | Killzone uses replay time | `curl .../killzone/current` | zone matches replay ET |
| 4 | S1 IB locks at replay 10:30 | push 12 bars → check ib_locked | true after 12th bar |
| 5 | S2 mode transitions | check /five_min/current | mode=FIRST_HOUR_TACTICAL |
| 6 | S4 A4 passes during replay RTH | `/woodies/fire` | A4=PASS (not WEEKEND) |
| 7 | Gateway records shadow trade | `/gateway/status` | shadow_active_count > 0 |
| 8 | BarLevelDetector closes trade | push bar above T1 | trade state=PARTIAL |
| 9 | No DEMO/LIVE enabled | `/gateway/status` | demo_slot=null, live_slot=null |

---

## What This Does NOT Test

- Real Sierra connection (requires Sierra running)
- Network latency under production load
- DLL export freshness
- Multiple concurrent days of replay
- Frontend visual rendering of replay data

---

## Command to Run Next

```bash
# Dry-run stage validation (safe, no trading mode):
bash scripts/run_stage.sh prompt_27_replay_plan

# Full replay clock smoke (tests only, no mode change):
bash scripts/run_stage.sh prompt_26_replay_clock_smoke

# Status check (all endpoints alive):
bash scripts/run_stage.sh status_check
```

---

*No SHADOW/DEMO/LIVE enabled. No push.*
