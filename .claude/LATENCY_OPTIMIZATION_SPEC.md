# MEMS26 — LATENCY OPTIMIZATION SPEC (LOCKED PRINCIPLE)

**Companion to:** MEMS26_DATA_INTEGRITY_PRINCIPLE_LOCKED (1EXCgoE7XxcDzhtXxa3_QwEP7qLncWSLT9GsiY7q-KWQ)
**Version:** 1.0 · 2026-05-10 · 🔒 LOCKED
**Authority:** Equal tier with Data Integrity — both gate phase advancement

## 1. THE PRINCIPLE

**End-to-end latency from market event to trader-visible decision MUST be ≤ 500ms in production.**
Latency above this threshold causes trade decisions on stale data, which is functionally equivalent
to a Data Integrity violation. Phase advancement to LIVE requires verified latency budget compliance.

## 2. WHY LATENCY MATTERS

In intraday futures (MES), price moves 0.25-1.00 pt in 200-500ms during volatility. A 6-second pipeline means:

- The "current" data the system sees is actually ~6 seconds old
- Setup detected at T+6 may have already filled at T+0
- Stop placement based on stale price → wrong by 1-3 ticks
- Quality Score computed on outdated TPO/Footprint

This is functionally a Data Integrity violation: the trader receives data that does not reflect
reality at the moment of decision.

## 3. LATENCY BUDGET (locked targets)

| Layer                          | Current  | Target   | Method              |
|--------------------------------|----------|----------|---------------------|
| 1. Sierra DLL → JSON write     | 3000 ms  |  200 ms  | Export Interval     |
| 2. Bridge file detection       | 1000 ms  |   10 ms  | fsevents/watchdog   |
| 3. Bridge → Backend            |  150 ms  |   50 ms  | WebSocket persistent|
| 4. Backend → Redis             |   30 ms  |   30 ms  | (already optimal)   |
| 5. Redis → Frontend            | 2000 ms  |   10 ms  | WebSocket push      |
| 6. Frontend render             |   50 ms  |   50 ms  | (already optimal)   |
| TOTAL                          | 6230 ms  |  350 ms  | (factor 18× faster) |

Maximum acceptable per phase:

- SHADOW: ≤ 1000 ms (observation, not trading)
- SIM:    ≤ 500 ms
- LIVE:   ≤ 300 ms (must)

## 4. CURRENT VIOLATIONS

### 🔴 LATENCY VIOLATION #1 — Sierra Export Interval too high

**Component:** Sierra Custom Studies DLL Inputs (In:2)
**Current:** 3 seconds
**Target:** 200-500ms
**Impact:** 2.5-2.8 sec lost per cycle
**Resolution:** Reduce In:2 to 0.5, monitor RAM stability
**Test required:** 4-hour soak with new interval, verify RAM stays < 500 MB

### 🔴 LATENCY VIOLATION #2 — Bridge polling instead of fsevents

**Component:** bridge/json_bridge.py
**Current:** mtime polling every 2 seconds
**Target:** macOS fsevents push notification (≤ 10ms)
**Impact:** 1.9 seconds average wait for new data
**Resolution:** Worker BRIDGE_FSEVENTS — replace polling with watchdog library
**Effort:** 2-3 hours

### 🔴 LATENCY VIOLATION #3 — Frontend polling instead of WebSocket

**Component:** frontend/v9/src/v9/lib/api.ts + stores
**Current:** REST polling every 2 seconds
**Target:** WebSocket push from Backend (≤ 50ms)
**Impact:** 1.9 seconds average wait for new state
**Resolution:** Wire ws_manager.py end-to-end (already exists per Bug #6 fix)
**Effort:** 4-6 hours

### 🟡 LATENCY VIOLATION #4 — Bridge → Backend HTTPS per cycle

**Component:** Bridge POSTs to /api/v9/* endpoints
**Current:** New connection per request
**Target:** Persistent WebSocket connection
**Impact:** ~100ms TLS handshake on each batch
**Resolution:** Worker BRIDGE_WS — replace POST with WS push
**Effort:** 3-4 hours

## 5. ENFORCEMENT

### Phase transition gates (added to SKILL §18)

**Before SHADOW:**
- E2E latency measured ≤ 1000ms in 95th percentile
- All 4 latency violations either resolved OR explicitly deferred per spec

**Before SIM:**
- E2E latency measured ≤ 500ms in 95th percentile
- Latency violation #1 (Sierra interval) RESOLVED
- Latency violation #2 (Bridge fsevents) RESOLVED

**Before LIVE:**
- E2E latency measured ≤ 300ms in 95th percentile (10,000 samples)
- All 4 latency violations RESOLVED
- No regressions in 7-day SIM test

### Audit script — added to scripts/data_integrity_audit.sh

TEST 7 — Latency budget check:
- bridge_heartbeat_age_sec > 30 → 🔴
- sc_data_age_sec > 30 → 🔴

## 6. MEASUREMENT METHODOLOGY

Latency is measured E2E by the timestamp chain:

T0: Sierra bar close timestamp        (in JSON: "ts" field)
T1: Bridge read timestamp              (POST body: "bridge_ts")
T2: Backend receive timestamp          (in DB: "received_at")
T3: WebSocket emit timestamp           (in WS frame: "emit_ts")
T4: Frontend receive timestamp         (browser: performance.now())
T5: DOM render complete                (browser: requestAnimationFrame)

E2E = T5 - T0

Measurement happens automatically once Backend instrumented (Phase 3.5).
Until then: measure manually via tail -f log timestamps.

## 7. INTEGRATION INTO ALL SPECS

This Latency Spec is referenced (not duplicated) in:

- MASTER_DEV_SKILL §0.6 (NEW)
- All 6 system specs § "Latency requirements"
- 3_MODE_TRADING_SPEC § "Latency caps"
- DASHBOARD_SPEC § "Real-time refresh"

## 8. ARCHITECTURAL PRINCIPLES

1. **Push > Pull** wherever possible (WebSocket, fsevents, server-sent events)
2. **Persistent connections** > new connection per request
3. **Co-location matters** — Bridge is local (Mac), Backend is cloud (US-East)
   ⚠️ Crossing public internet adds 30-100ms baseline. Cannot be eliminated for cloud backend.
4. **Render only when state changes** — frontend should NEVER poll if WS available
5. **Batch where possible, but not where it adds latency** — small payloads frequent > large payloads occasional

## 9. NON-NEGOTIABLE RULES

- No silent latency degradation — instrumented + alerted
- No "good enough for now" — if missing budget, mark as violation in §17
- No bypass even if user pressures — same as Data Integrity
- New code that adds latency > 50ms requires user approval

## 10. SUMMARY

**Stale data → wrong decisions → real money loss.**
**Latency is a first-class architectural concern, not an afterthought.**

🔒 LOCKED. Modifications require explicit user approval.
