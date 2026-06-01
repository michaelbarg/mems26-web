# Fix Wiring → Patterns Armed · 2026-06-01

**Date:** 2026-06-01 RTH · **Author:** CC

---

## Bug 1: S2 opening_type=NA (FIXED — commit `2124411`)

**Root:** `day_type_classification` event published only on CHANGE (P5.1.5). S2 missed the initial event → `opening_type=NA` for the entire session.

**Fix:** Publish `day_type_classification` on every bar. Read `opening_type` from the machine's classification (not TPO).

**Result:** `S2 opening_type=OPEN_AUCTION_IN` ✅

## Bug 2: S4 trend stuck GRAY/YELLOW (RESOLVED — not a code bug)

**Root:** After restart, the Woodies system needed 6+ bars above ZL to establish BLUE trend (D-092 §4). CCI crossed ZL → GRAY → YELLOW (5th bar) → BLUE (6th bar). This was **correct behavior** per spec, not a bug.

**Result:** `S4 trend=BLUE, CCI=172.93` ✅

## Bug 3: Build Status armed/blocked logic (FIXED — commit `f493126`)

**Root:** Inspector classified `detection.*` missing as BLOCKED. But detection="no pattern right now" ≠ infrastructure failure.

**Fix:** Separated `data.*`/`gate.*` (infrastructure) from `detection.*` (trigger). Infrastructure OK + detection missing = **ARMED** (ready for trigger).

**Result:**

| System | Armed 🟡 | Blocked ❌ | Fired ✅ |
|--------|---------|-----------|---------|
| S2 Five-Min | **8** | 2 (Initiative SKIP × Normal) | 0 |
| S4 Woodies | **8** | 0 | 1 (HTLB) |
| S3 Footprint | 0 | 4 (buffer rebuilding) | 0 |
| S1 Day Type | 0 | 0 | 1 (Normal p=0.68) |

## Per-pattern detail

**S2 Armed (8):** Reactive L/S, Inverse H&S, HNS Top, Double Bottom/Top, Bull/Bear Flag — all awaiting detection trigger. Infrastructure (data, gates, opening_type) ✅.

**S2 Blocked (2):** Initiative LONG/SHORT — `Auth Table SKIP for INITIATIVE × Normal` (D-091 spec: Initiative fires only on TN/TDD/NV, not Normal).

**S4 Armed (8):** ZLR, TLB, TT, GB100, Vegas, Ghost, FaMir, HFE — trend=BLUE, CCI ready, awaiting pattern-specific conditions.

**S4 Fired (1):** HTLB fired at 13:34 (2 trades).

**S3:** 61 trades fired today (absorption, sweep_return). Buffer=0 after restart, rebuilding.

## Day-type continuous ✅

```
v9_day_type_state: votes every 5 min, stage=B2, Normal p=0.68
Continuous re-classification active — not stuck.
```

## Commits

1. `2124411` — S2 opening_type fix (publish every bar)
2. `f493126` — Build Status armed/blocked logic fix

---

*All patterns that should be armed ARE armed. Blocked = legitimate (Auth Table SKIP, buffer rebuilding).*
