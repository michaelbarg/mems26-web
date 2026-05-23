# D-086 — S3 firing violation deferred to post-SHADOW

**Date:** 2026-05-20  
**Authority:** Michael Barg (Strategic chat)  
**Status:** LOCKED

## Context

Cursor P0.5 Task 4 discovered `footprint_system.py:426` calls `route_setup(3)`. This violates **D-082** (S3 = Observer ONLY per V3 spec `1iPndwDKwYn70pXCwkHNJVyAwLeU8WislDGAQX3HXvT4`).

## Decision

- Acknowledge violation as **KNOWN ISSUE**
- **Defer fix** to POST-SHADOW phase
- **SHADOW proceeds** with current S3 firing behavior (harmless — no real money)
- Fix scope later: **Option A** (disable `route_setup(3)`) or **Option B** (full refactor)
- **A vs B:** decided after post-SHADOW data review

## Rationale

- SHADOW = observation + data collection
- Fixing before SHADOW start = regression risk
- Post-SHADOW data informs V4 dual-role spec vs restore V3 observer-only

## Conditions (before LIVE)

- Must be revisited **before LIVE**
- If kept firing → S3 spec must update to **V4**
- If reverted → code fix per Option A or B

## What D-086 approves vs does NOT approve

**D-086 does NOT mean** S3 gets full trade management and live position handling (like S4 Woodies B1–B14 or LIVE TradeManager). It only tolerates the **existing SHADOW logging path** until post-SHADOW.

### S3 in SHADOW today (code path)

```
signal (absorption / stacked imbalance)
  → calculate_size (full / half / reject — qty in metadata only)
  → pre_fire_validator
  → gateway.route_setup(3)
       → gateway gates (cooldown, cluster_guard, SSV, chop)
       → _execute_shadow only → INSERT v9_trades (no Sierra)
```

Reference: `footprint_system.py` `_fire()` · `gateway/trading_gateway.py` `_execute_shadow()`

### Included in SHADOW (YES)

| Capability | In SHADOW? |
|------------|------------|
| Observer journal every bar (`v9_footprint_journal`) | Yes |
| Signal detection + internal sizing (full/half/reject) | Yes |
| `pre_fire_validator` | Yes |
| SHADOW row in `v9_trades` (entry, stop, t1, t2 in setup) | Yes |
| Gateway risk gates on route attempt | Yes |
| `last_fire` / reasoning in footprint state (Plan tab) | Yes |

### NOT included (NO)

| Capability | In SHADOW? |
|------------|------------|
| Sierra order / broker execution | No |
| DEMO or LIVE slot (`enable_demo/live(3)` not set) | No |
| Production gateway → `TradeManager.accept_setup` | No |
| Full active-trade lifecycle (BE, scale C1–C3, time stop, EOD via B-stages) | No for S3 on this path |
| “Full position management” as for LIVE firing systems | No |

### Plain language

- **Approved:** S3 may keep producing **SHADOW log records** for soak analysis (known V3 spec drift).
- **Not approved:** Treating S3 as a **fully managed firing system** with complete trade lifecycle — that remains **S2 / S4** (and future DEMO/LIVE with explicit enable + TM).

### Comparison

| System | SHADOW = what actually runs |
|--------|----------------------------|
| S4 Woodies | A1–A7 tree + SHADOW persist |
| S2 FiveMin | Pattern + `emit_t1_setup` + pre_fire + SHADOW persist |
| S3 Footprint (D-086) | **T3 signal** + pre_fire + **SHADOW persist** **in addition to** observer journal |
| Layer 4 full TM | Post-entry management for enabled DEMO/LIVE paths — **not** S3 SHADOW today |

## Linked

| ID | Relationship |
|----|----------------|
| D-082 | VIOLATED but **TOLERATED in SHADOW** |
| P0.5 Task 4 | `docs/reports/P30_S3_OBS_CHECK.md` |
