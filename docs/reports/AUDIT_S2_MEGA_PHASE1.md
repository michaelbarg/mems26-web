# AUDIT S2 MEGA Phase 1 — Wave 1.5 Layer 3 Discovery
Date: 2026-05-16

## §A · Layer 3 Verdict

| Component | Status | Evidence |
|---|---|---|
| Layer 3 directory | :green_circle: EXISTS | `backend/v9/layer3/` + `backend/v9/services/layer3/` |
| Cluster detection | :green_circle: EXISTS | `layer3/cluster.py:43` `identify_cluster()` returns `Cluster` with `yellow_poc`, `yellow_poc_vol`, `top`, `bottom` |
| Empty zone detection | :green_circle: EXISTS | `layer3/empty_zone.py:25` `identify_empty_zones()` returns list of `EmptyZone` with `zone_low`, `zone_high`, `zone_width_pt` |
| Entry executor | :green_circle: EXISTS | `layer3/entry_executor.py:88` calls `identify_cluster` + `identify_empty_zones`, computes entry/stop/targets, returns `EntryPlan` |
| L3 handoff service | :green_circle: EXISTS | `services/layer3/handoff.py:14` wraps layer3 modules, imports `compute_entry_plan` |
| Gateway routing | :green_circle: EXISTS | `services/trading_gateway/gateway.py:67` `route_setup()` + API POST `/route_setup` at `gateway_routes.py:45` |
| EventDispatcher L3 wire | :green_circle: EXISTS | `event_dispatcher/dispatcher.py:149` `self._gateway.route_setup(setup, system_id)` |
| 15-tick reversal bars | :green_circle: EXISTS | Sierra exports `tick_reversal_15.json`, bridge streams it, `historical_replay.py:99` replays it |
| Per-bar VP (for cluster) | :green_circle: EXISTS | `layer3/cluster.py` takes `levels: List[PriceLevel]` from reversal bar VP data. DLL exports per-bar VP. |

**OVERALL: :green_circle: READY.** All Layer 3 components exist and are wired. Cluster + empty_zone + entry_executor + gateway routing all operational.

## §B · S1 targets_table

`backend/v9/systems/day_type/targets_table.py` — 6 Day Types covered:

| Day Type | T1 | T2 | T3 | Time Stop | Sizing | Contracts |
|---|---|---|---|---|---|---|
| Trend_Normal | 1R | 2R+TPO | 4R+trail | none | AGGRESSIVE | 3 |
| Trend_DD | 1R | open | 4R cap | 90min | AGGRESSIVE | 3 |
| Variation | 1R | 2.5R | trail | 60min | FULL | 2 |
| Normal | 1R | POC | NO T3 | 30min | HALF | 1 |
| Neutral | 1R | extreme | NO T3 | 45min | HALF | 1 |
| Nontrend | 1R | NO T2 | NO T3 | 20min | MIN | 1 |

`get_targets(day_type)` function at line 121. Used by `layer3/entry_executor.py:130` and `layer4/day_type_targets_verify.py:22`.

## §C · S5 /tpo/current

`backend/v9/api/v9/tpo_routes.py:8` — `tpo_current()` returns `sys.get_current()`. Based on TPO system state, provides: poc, vah, val, ib_high, ib_low, ib_locked, ib_class, poc_migration_state, hvn/lvn prices.

Available for S2 quality tier consumption.

## §D · L3 Routing

:green_circle: EXISTS. Two paths:
1. **EventDispatcher path:** `dispatcher.py:149` → `gateway.route_setup(setup, system_id)` — automatic when system's `analyze()` returns a Signal.
2. **Manual API path:** POST `/api/v9/gateway/route_setup` at `gateway_routes.py:45-51`.

For S2 integration, the EventDispatcher path is the standard flow.

## §E · POC Return Alt (Initiative Bar -2)

Current logic (five_min_system.py:348):
```python
b2_higher_low = b2["l"] > b1["l"]
```

Only checks Higher Low. No "return to POC_VOL" alternative.

**Refactor scope: SMALL.** Add `OR poc_return` check:
```python
b2_higher_low = b2["l"] > b1["l"]
b2_poc_return = abs(b2["c"] - poc_vol) < tolerance  # return to POC_VOL
b2_test = b2_higher_low or b2_poc_return
```

Minimal diff: ~3 lines added, 1 line changed. Low risk.

## §F · Wave 2 Path Recommendation

**PATH A: Layer 3 READY :green_circle:**

All Layer 3 components exist:
- `identify_cluster()` → yellow_poc for entry
- `identify_empty_zones()` → stop placement
- `compute_entry_plan()` → full entry/stop/targets
- `route_setup()` → gateway routing

**Recommended: PATH A.**

Estimated Phase 2 scope with Path A:
- §2.A Quality Tier wire (3 tests) — 1 commit
- §2.B time_stop mapper (3 tests) — 1 commit
- §2.C setup_emitter composer (4 tests) — 1 commit
- §2.D POC return alt (2 tests) — 1 commit (MODIFICATION)
- §2.E.A Layer 3 wiring (3 tests) — 1 commit
- Total: **5 commits, ~15 tests, ~2 hours**

T1Setup.provisional can be set to **False** since Layer 3 cluster + empty_zone are available for real entry/stop computation.
