# MEMS26 Shadow Live — RTH Day Audit 2026-05-27

**Date:** 2026-05-27  
**Session:** RTH 09:30–16:00 ET  
**Author:** Cursor Agent (Post-market forensic)  
**Status:** ❌ FAILED — Zero opportunities fired despite 46 CCI detections

---

## 1. Executive Summary

The system was active all day but fired zero shadow/demo trades. Two independent structural bugs blocked the pipeline:

| # | System | Bug | Impact |
|---|--------|-----|--------|
| B1 | S2 (FiveMin) | `process_bar()` missing FIRST_HOUR → DAY_TYPE mode transition | All chart patterns (H&S, flags, doubles) never ran |
| B2 | S4 (Woodies) | `demo_enabled_systems=[]` in gateway + shadow trades not persisted | Signals detected but invisible in UI |

---

## 2. Data Evidence

### 2.1 RTH Woodies Detections (`v9_woodies_signals`)

| Time (ET) | Pattern | Direction | Confidence | Trend | Routing outcome |
|-----------|---------|-----------|------------|-------|-----------------|
| 10:07 | HTLB | SHORT | 0.65 | YELLOW | Blocked — YELLOW lock (correct) |
| 10:33 | HTLB + GB100 | SHORT | 0.65 / 0.50 | RED | Should have routed — never confirmed |
| 13:15 | FAMIR | LONG | 0.69 | RED | Sizing reject — all indicators bearish (correct) |
| 14:05 | HTLB | SHORT | 0.65 | GRAY | A5 fail — size=reject (CCI=6.7 at exact tick) |

**Total RTH signals:** 8 (out of 46 today)  
**Traded:** 0

### 2.2 RTH Trend Distribution (5,614 ticks processed)

| Trend | Bars | % |
|-------|------|---|
| GRAY | 2,730 | 48.6% |
| RED | 1,602 | 28.5% |
| BLUE | 796 | 14.2% |
| YELLOW | 489 | 8.7% |

GRAY dominance → A1 gate blocks low-confidence patterns. Only HIGH-conf (≥ 0.55) can pass GRAY.

### 2.3 S2 FiveMin — Zero setups

- `v9_five_min_setups`: 0 records (all time)
- `v9_bars_5min` RTH rows today: 0
- Mode stuck at: `FIRST_HOUR_TACTICAL` (should be `DAY_TYPE_MODE` after 10:30 ET)

### 2.4 Gateway Status at Market Close

```
demo_enabled_systems: []
live_enabled_systems: []
shadow_active_count: 0
trades_today: 0
cluster_guard_active: true (5 attempts in 60s — from post-market HTLB fires)
chop_state: EXPANDING
```

---

## 3. Root Cause Analysis

### Bug B1 — S2 Mode Transition Missing

**Location:** `backend/v9/systems/five_min/five_min_system.py` → `process_bar()`

**Mechanism:**  
`hydrate()` correctly sets `mode = FIRST_HOUR_TACTICAL` when backend starts during first hour.  
The transition `FIRST_HOUR_TACTICAL → DAY_TYPE_MODE` exists only in `_on_bar_closed()`, which is never called (not wired to BarRouter in `main.py`). `process_bar()` only handles `OVERNIGHT_MODE → FIRST_HOUR/DAY_TYPE`.

**Effect:** Mode stuck at `FIRST_HOUR_TACTICAL` all day. Pattern detection gates:
- `detect_inverse_hns()`, `detect_hns_top()` → gated on `DAY_TYPE_MODE` → never called
- `detect_double_bottom/top()` → same
- `detect_bull/bear_flag()` → same
- FHB gate blocks reactive/initiative patterns in first hour mode

**Fix:** Add inside `process_bar()`, after the OVERNIGHT_MODE block:
```python
elif self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
    try:
        info = self.session_classifier.classify()
        if info.session == Session.CASH_HOURS:
            self.mode = FiveMinMode.DAY_TYPE_MODE
            self._fhb.lock()
            logger.info("[FiveMin] Mode: FIRST_HOUR_TACTICAL → DAY_TYPE_MODE")
    except Exception:
        pass
```

### Bug B2 — No Demo Mode + Shadow Not Persisted

**Location:** `backend/main.py` → gateway setup; `backend/v9/gateway/trading_gateway.py` → `_execute_shadow()`

**Mechanism:**  
Gateway `_demo_enabled_systems` defaults to empty set. No `enable_demo()` call in `main.py` for any system. Shadow trades written to `self.shadow_trades` (in-memory list, capped 500 items, lost on restart). `v9_trades` table only written by DEMO/LIVE mode — never by shadow.

**Effect:** Even when Woodies correctly detects a pattern, passes all decision-tree stages (A1-A7 PASS), and routes to gateway → nothing visible in UI, nothing persistent in DB.

**Fix:**
1. In `main.py`: call `trading_gateway.enable_demo(4)` after gateway setup (Woodies system 4)
2. In `_execute_shadow()`: persist shadow trades to `v9_trades` with `mode='SHADOW'`

### Bug B3 — Footprint Gateway Error (secondary)

**Location:** `backend/v9/systems/footprint/footprint_system.py`

**Symptom:** `[Footprint] Gateway route_setup failed: Invalid firing_system: 3`

The pre_fire_validator `FireRequest` uses string literals (`T1_NUMBER_BAR`, `T2_WOODIES`, `T3_FOOTPRINT`) but the footprint system passes integer `3`.

---

## 4. Fix Plan (Pre Next Trading Day)

### Priority 1 — MUST FIX (blocks all signals)

| Fix | File | Lines | Risk |
|-----|------|-------|------|
| F1: S2 mode transition FIRST_HOUR → DAY_TYPE | `five_min_system.py` | ~680 | LOW |
| F2: Enable demo for Woodies (system 4) in gateway | `main.py` | ~391 | LOW |
| F3: Persist shadow trades to DB with mode='SHADOW' | `trading_gateway.py` | `_execute_shadow()` | MEDIUM |

### Priority 2 — SHOULD FIX

| Fix | File | Risk |
|-----|------|------|
| F4: Fix Footprint firing_system=3 error | `footprint_system.py` | LOW |
| F5: Enable demo for S2 (FiveMin) in gateway | `main.py` | LOW |

### Priority 3 — OBSERVE (no code change)

- Monitor chop_state at RTH open — if SEARCHING, no signals will fire (by design)
- Verify IB contamination fix holds (is_rth flag working)
- Confirm day_type classification fires within first 30 min of RTH

---

## 5. UAT Axes for Next Day

After fixes are deployed, verify before trading:

1. **Quality:** `v9_five_min_setups` has rows within 60 min of RTH open
2. **Mode:** `GET /api/v9/five_min/current` shows `mode: DAY_TYPE_MODE` after 10:30 ET
3. **Demo:** `GET /api/v9/gateway/status` shows `demo_enabled_systems: [4]`
4. **Shadow:** `v9_trades` has rows with `mode='SHADOW'` after first signal
5. **Bridge:** Build Status shows all streams FRESH within 90s

---

## 6. What Worked Correctly Today

- ✅ Bridge sending all streams (woodies_5min: 5,895 dispatches, footprint: active)
- ✅ Woodies CCI engine detecting patterns (46 woodies_signals written)
- ✅ RTH gate (`_rth_only`) blocking overnight bars correctly (new backend)
- ✅ YELLOW lock blocking patterns during YELLOW bars (correct)
- ✅ is_rth fix preventing IB contamination
- ✅ IB correctly shows 40 pts (clean RTH IB after fix)
- ✅ Day type classified as Trend_Normal with OPEN_DRIVE
- ✅ Previous day POC fix applied
- ✅ Footprint + cumulative_delta + volume_profile all receiving data

---

*Report prepared by Cursor Agent post-market 2026-05-27 21:20 IL*
