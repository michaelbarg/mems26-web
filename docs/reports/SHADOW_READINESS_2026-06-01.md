# SHADOW READINESS REPORT — 2026-06-01

**Date:** 2026-06-01 13:05 IL (06:05 ET) · **Author:** CC
**For:** Michael sign-off before SHADOW data collection

---

## Executive Summary

The system is ready for SHADOW data collection. All 4 phases complete:

| Phase | Status | Commit |
|-------|--------|--------|
| Phase 1: Calibration wiring (4 flags) | ✅ PASS | `70848a6` |
| Phase 2: Bar continuity + live price | ✅ PASS (verified hold) | `8e4aaae`, `80e37ba` |
| Phase 3a: Live price all surfaces | ✅ PASS | `80e37ba` |
| Phase 3b: 6 systems receiving | ✅ PASS (5/6 healthy, S1 pre-RTH=expected) | — |
| Phase 3c: Fire path e2e | ✅ PASS (391 tests + live gateway) | — |
| Phase 4: SHADOW readiness | ✅ See below | — |

---

## Phase 4 Checklist

### Mode
```
mode=shadow  alive=True  ws_clients=1
```
✅ SHADOW mode confirmed. No demo/live slots active.

### Bridge Health (zero errors since restart)
```
[heartbeat] alive — newest_data_age=0s streams=11/12
total_pushes=40,406  total_errors=16,054 (all historical, pre-restart)

Push rate: ~270 pushes/min, 0 new errors
```
✅ Zero push errors since backend restart.

### DLL Export Freshness
```
All 14 export files: FRESH (< 2s age)
Only woodies_diag.json: STALE (optional/informational)
```
✅ Sierra DLL exporting all streams.

### Systems Status
| System | Health | State | Buffer |
|--------|--------|-------|--------|
| S1 Day Type | unknown (pre-RTH) | — | Will populate at 09:30 ET |
| S2 Five-Min | healthy | OVERNIGHT_MODE | 12 bars |
| S3 Footprint | healthy | BALANCED | 25 bars |
| S4 Woodies | healthy | RED trend | 50 bars |
| S5 TPO | healthy | (pre-RTH) | 12 bars |
| S6 Killzone | healthy | LONDON | active |

### Live Price
```
/api/v9/live_price → price=7610.88 (bid/ask midpoint, not stale)
Woodies CCI panel → current_bar.close=7610.88 (injected live price)
```
✅ All surfaces show live market price.

### Calibration Flags (all 4 wired, default OFF)
| Flag | Status | Behavior Change (ON) |
|------|--------|---------------------|
| S3_RELATIVE | ✅ Wired | MIN_LEVEL_VOL = 0.3 × median |
| S1_IB_WIDTH_ATR | ✅ Wired | IB_range / ATR-14 ratio tiers |
| S1_CVD_OPENING | ✅ Wired | CVD-enhanced opening type |
| S1_DAYTYPE_STAGING | ✅ Wired | Confidence cap before 60min |

Golden regression: **2556 passed, 0 failed** (flags OFF).

### Fire Path
```
/api/v9/gateway/status → all 5 risk gates green
  cooldown: 0 consecutive stops
  cluster_guard: 0 attempts
  SSV: no suffering side
  chop_state: RESPECTING
  demo_enabled_systems: [2, 4]

391 fire/trade/gateway tests PASS
```
✅ Fire chain complete: detection → risk gates → TradeManager → DB → API.

### RTH Safety Gates (verified)
6 independent gates block overnight firing:
1. FiveMinSystem OVERNIGHT_MODE → no detection
2. WoodiesSystem _is_rth_bar() → 09:30-16:00 ET
3. DayTypeStateMachine is_rth → skip Globex
4. BarRouter session tag
5. HistoricalReplay WARMUP mode
6. PreFireValidator _check_rth_open()

### Backend Auto-Restart
```
LaunchAgent: com.mems26.backend (KeepAlive: SuccessfulExit=false)
LaunchAgent: com.mems26.bridge (KeepAlive: SuccessfulExit=false)
Current uptime: 3+ minutes (just restarted for code changes)
```
✅ Both services auto-restart on crash.

---

## Known Limitations (non-blocking for SHADOW)

| Item | Impact | Mitigation |
|------|--------|-----------|
| S1 Day Type shows "unknown" pre-RTH | No classification until 09:30 ET | Expected — populates at RTH open |
| Overnight bar history gaps | Backend downtime = no backfill | LaunchAgent prevents future gaps |
| sc.Close frozen overnight | Bar OHLC stale during Globex | Live price uses bid/ask midpoint |
| DLL frozen-tail (woodies_diag.json stale) | Last 13 bars of Woodies history may have frozen studies | Current_bar override fix (`f3caa89`) compensates |
| V9_DO_WARMUP disabled | Full system warm-up skipped at startup | Bars accumulate in DB; CCI buffer fills after ~14 bars |
| .env not loading in LaunchAgent | Sandbox restriction | Critical vars hardcoded in plist |

---

## DLL Frozen-Tail Check (deferred to RTH)

The DLL frozen-tail check requires RTH bars with varying CCI values. Pre-RTH, all bars have the same frozen study values (expected). **Recommend re-checking during RTH (after 10:00 ET) to verify the frozen-tail current_bar override is working.**

---

## Sign-Off Required

Michael — this report summarizes the system state as of 06:05 ET. The system is ready to collect clean SHADOW data starting at next RTH open (09:30 ET, ~16:30 IL).

**To proceed:**
1. Confirm you want to open SHADOW collection
2. Optional: enable calibration flags (S3_RELATIVE, S1_IB_WIDTH_ATR, S1_CVD_OPENING, S1_DAYTYPE_STAGING) for shadow data with flag-ON behavior
3. Re-check DLL frozen-tail during RTH

**No action needed from CC until your sign-off.**

---

*Zero order/risk/sizing/polling changes throughout this session.*
