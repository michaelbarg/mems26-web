# GAP-3: R:R Fire Selection — Audit Report

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Type:** READ-ONLY audit — zero code changes

---

## A1 · Gateway Call Trace per System

### System 2 (FiveMinSystem) — `five_min_system.py:1026`

```python
self._gateway.route_setup(gateway_setup, 2)
```

Setup dict fields (lines 1013-1024):
- `firing_system`: 2
- `direction`, `classification`, `confidence`
- `entry_price`, `stop`, `t1`, `t2`, `t3`
- `metadata`: `{"pattern": pattern_name, "sizing": sizing_contracts}`

### System 3 (FootprintSystem) — `footprint_system.py:485`

```python
self._gateway.route_setup(gateway_payload, 3)
```

Setup dict built by `_build_gateway_payload` (lines 561-581), same fields + `metadata.qty`.

### System 4 (WoodiesSystem) — `woodies_system.py:448`

```python
route_result = self._gateway.route_setup(setup, 4)
```

Setup dict (lines 435-445), same field structure + `metadata.sizing`.

### Gateway Behavior — `trading_gateway.py:72-141`

**Confirmed first-wins:**
- No R:R comparison
- No buffering of competing setups
- No ranking logic
- SHADOW: every call that passes risk gates creates a trade (parallel unlimited)
- DEMO/LIVE: `if self.demo_slot is None:` → first arrival fills slot, rest skipped

**Can multiple systems fire on same bar?** YES. S2, S3, S4 each have their own `process_bar` subscriber. If all detect a pattern on the same 5-min bar, each independently calls `gateway.route_setup()`. SHADOW records all three; DEMO/LIVE goes to whichever arrives first.

---

## A2 · Dollar-per-Point Constant

| File | Value | Source |
|------|-------|--------|
| `backend/v9/services/trade_context.py:56` | `MES_POINT_VALUE = 5.0` | `# MES $5/point` |
| `backend/v9/services/trade_manager/manager.py:54-56` | `MES_TICK_VALUE = 1.25`, `MES_TICK_SIZE = 0.25` → `MES_POINT_VALUE = 5.0` | Derived |
| `backend/v9/services/active_trade_manager/monitor.py:22` | `MES_POINT_VALUE = 5.0` | `# $5 per point per contract` |
| `backend/v9/api/journal_compat_routes.py:32` | `MES_POINT_VALUE = 5.0` | Hardcoded |

**Finding:** Defined in 4 files (not DRY). All agree on $5/point. MES = Micro E-mini S&P 500 futures, tick size = 0.25, tick value = $1.25, point value = $5.00. Correct per CME spec.

**Gap:** No single source-of-truth constant. Should be in `constants.py` or similar.

---

## A3 · Sizing / Contract Split

**Auth Table** (`auth_table_v1.py`): 70-cell lookup. Max = 3 contracts (HIGH tier). Min = 0 (SKIP).

**Contract Split** (`contract_split.py`):
- OFA (Reactive/Initiative): T1=25%, T2=50%, T3=25%
- H&S / Double: 33%/33%/34%
- Flags: 50%/50%/0%

**Flow:**
```
Pattern fires → emit_t1_setup() → get_quality_tier_v2(pattern, day_type, price)
  → Auth Table cell → (verdict, tier, contracts: int)
  → T1Setup.sizing_contracts = contracts
  → gateway receives metadata.sizing
```

Gateway does NOT validate or use `metadata.sizing` for selection — it's stored in the trade record for audit but never compared.

---

## Evidence (Rule 5)

```
$ grep -n "route_setup" backend/v9/systems/five_min/five_min_system.py
1026:            self._gateway.route_setup(gateway_setup, 2)

$ grep -n "route_setup" backend/v9/systems/footprint/footprint_system.py  
485:            self._gateway.route_setup(gateway_payload, 3)

$ grep -n "route_setup" backend/v9/systems/woodies/woodies_system.py
448:        route_result = self._gateway.route_setup(setup, 4)

$ grep -n "MES_POINT_VALUE" backend/v9/
services/trade_context.py:56:MES_POINT_VALUE = 5.0
services/trade_manager/manager.py:56:MES_POINT_VALUE = MES_TICK_VALUE / MES_TICK_SIZE
services/active_trade_manager/monitor.py:22:MES_POINT_VALUE = 5.0
api/journal_compat_routes.py:32:MES_POINT_VALUE = 5.0
```
