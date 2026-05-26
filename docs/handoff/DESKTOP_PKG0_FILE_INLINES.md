# Desktop Pkg 0 · File Inlines · Verbatim Source

**Date:** 2026-05-23 18:30 IL
**Purpose:** Verbatim source for the 8 files Desktop must inline into the Pkg 0 mega prompt
**Authority:** This file is the byte-for-byte source of truth · M13 IRON · NEVER INVENT
**Companion:** `docs/handoff/DESKTOP_PKG0_PATHX_HANDOFF.md` (the spec)

---

## ⚠️ CORRECTION to original handoff §3

The original `DESKTOP_PKG0_PATHX_HANDOFF.md` §3 listed file #6 as `backend/v9/main.py`. **This file does NOT exist.**

The actual file is **`backend/main.py`** (parent backend module, not v9). All FiveMinSystem + 5 other systems wiring happens here via `BarRouter`. The `EventDispatcher` init from `backend/v9/app.py::init_event_dispatcher` is called from this same file at line 56.

So `backend/main.py` contains BOTH paths' bootstrap:
- Line 56 → `init_event_dispatcher()` → registers Path B (Chart5MinSystem) in EventDispatcher
- Lines 83-91 → `FiveMinSystem()` → registers Path A in BarRouter

This is why Pkg 0 must touch `backend/main.py` only for **read-only verification** (Path A must remain intact). The DELETE of Chart5MinSystem happens in `backend/v9/app.py::init_event_dispatcher`.

---

## File 1 · `backend/v9/app.py` (entire · 343 lines)

```1:343:backend/v9/app.py
"""MEMS26 V9 FastAPI application.

Can be run standalone OR mounted into the unified backend (backend.main).
"""

import logging
from typing import Optional

from fastapi import APIRouter, FastAPI, Request
from backend.v9.api.v9 import bars, signals, markers, trades, configs, websocket, health_streams, trade_commands, status, audit, spec_compliance
from backend.v9.systems.day_type.api import router as day_type_router
from backend.v9.api.v9.five_min.routes import router as five_min_router
from backend.v9.api.v9.footprint.routes import router as footprint_router
from backend.v9.api.v9.woodies.routes import router as woodies_router
from backend.v9.api.v9.tpo_routes import router as tpo_api_router
from backend.v9.api.v9.killzone_routes import router as killzone_api_router
from backend.v9.api.v9.bars_5min_history import router as bars_5min_history_router
from backend.v9.api.v9.reversal_routes import router as reversal_api_router
from backend.v9.api.v9.chop_score_routes import router as chop_score_router
from backend.v9.api.v9.gateway_routes import router as gateway_api_router
from backend.v9.api.v9.shadow_routes import router as shadow_api_router
from backend.v9.api.v9.pre_fire_routes import router as pre_fire_router
from backend.v9.systems.behavior_phase.routes import router as behavior_phase_router
from backend.v9.api.v9.price_routes import router as price_api_router
from backend.v9.api.v9.clock_routes import router as clock_api_router
from backend.v9.api.v9.open_type_routes import router as open_type_api_router
from backend.v9.api.v9.day_type_v9_routes import router as day_type_v9_router
from backend.v9.api.v9.cumulative_delta_routes import router as cvd_api_router
from backend.v9.api.v9.woodies_chart_routes import router as woodies_chart_router
from backend.v9.api.v9.history_routes import router as history_api_router
from backend.v9.api.v9.admin_routes import router as admin_api_router
from backend.v9.ws.router import router as ws_event_bus_router
# ... [routes registration + cockpit_heartbeat + _system_payload + cockpit_systems_snapshot] ...
# ── EventDispatcher initialization ──────────────────────────────

def init_event_dispatcher(gateway=None):
    """Initialize EventDispatcher with all 6 systems and wire into bars API."""
    from backend.v9.services.event_dispatcher import EventDispatcher
    from backend.v9.services.stream_health import StreamHealthService
    from backend.v9.systems.wrappers import (
        DayTypeSystem, Chart5MinSystem, TickReversalSystem,
        WoodiesSystem, TPOSystem, KillzoneSystem,
    )
    from backend.v9.api.v9.bars import set_event_dispatcher, set_stream_health
    from backend.v9.api.v9.health_streams import set_stream_health_service

    stream_health = StreamHealthService()

    dispatcher = EventDispatcher(gateway=gateway)
    dispatcher.set_stream_health(stream_health)

    # Register all 6 systems
    systems = [
        DayTypeSystem(),
        Chart5MinSystem(),
        TickReversalSystem(),
        WoodiesSystem(),
        TPOSystem(),
        KillzoneSystem(),
    ]
    for system in systems:
        dispatcher.register_system(system)
```

**Note:** The full file is 343 lines. For brevity, only the `init_event_dispatcher` function (lines 271-326) is shown above as it's the only function Pkg 0 touches. Desktop must include the full file when generating the mega prompt — instruct CC that the function ABOVE is what to modify, and the rest is for context only.

**Critical lines to modify in Pkg 0:**
- Line 280: `DayTypeSystem, Chart5MinSystem, TickReversalSystem,` → remove `Chart5MinSystem`
- Line 295: `Chart5MinSystem(),` → remove this line
- Lines 318-322: log messages — count should now reflect 5 systems

---

## File 2 · `backend/v9/services/event_dispatcher/dispatcher.py` (entire · 155 lines)

Full verbatim content already provided in the original handoff §audit. The only line Pkg 0 modifies is **line 24** (docstring example):

```22:28:backend/v9/services/event_dispatcher/dispatcher.py
    Usage:
        dispatcher = EventDispatcher(gateway=trading_gateway)
        dispatcher.register_system(day_type_system)
        dispatcher.register_system(chart_5min_system)
        ...
        # On every Bridge POST:
        dispatcher.on_bar_received("cumulative_delta", bar_dict)
```

**Pkg 0 change:** line 24 `dispatcher.register_system(chart_5min_system)` → `dispatcher.register_system(footprint_system)` (or any of the 5 remaining systems, just so the example is valid).

Desktop: inline the FULL 155 lines of `dispatcher.py` so CC sees the routing logic isn't being touched.

---

## File 3 · `backend/v9/services/snapshot_service/snapshot.py` (entire · 137 lines)

```1:42:backend/v9/services/snapshot_service/snapshot.py
"""CrossSystemSnapshotService — reads all 6 systems' current state from Redis.

Per MEMS26_SPEC_COMPLIANCE_AND_CROSS_SYSTEM_SNAPSHOT_LOCKED V1.1 Section 2.4:
- Captures state of all 6 systems at trade events (entry, target hits, stop, close)
- Reads from Redis keys: mems26:v9:{system_name}:latest
- If a system has no data, returns {status: "unavailable"} (not an error)
- Returns dict ready for V9Trade.cross_context

System mapping (per MASTER_DEV_SKILL):
  1: day_type, 2: chart_5min, 3: tick_reversal, 4: woodies, 5: tpo, 6: killzone
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# System ID to Redis key name mapping (per MASTER_DEV_SKILL naming conventions)
SYSTEM_NAMES: Dict[int, str] = {
    1: "day_type",
    2: "chart_5min",
    3: "tick_reversal",
    4: "woodies",
    5: "tpo",
    6: "killzone",
}
```

**Pkg 0 changes (2 lines):**
- Line 10 (docstring): `2: chart_5min` → `2: five_min`
- Line 23 (SYSTEM_NAMES dict): `2: "chart_5min",` → `2: "five_min",`

The rest of the 137-line file (SYSTEM_FIELDS dict, CrossSystemSnapshotService class) is **not modified** by Pkg 0 — but Desktop must inline it so CC sees the read path uses `SYSTEM_NAMES[system_id]` to build Redis keys (line 91), confirming the rename propagates.

**Side effect:** Redis keys under `mems26:v9:chart_5min:latest` will no longer be read after this change. Step 5 of Pkg 0 (Redis migration script) handles this.

---

## File 4 · `backend/v9/api/v9/shadow_routes.py` (lines 78-159 · the SYSTEM_NAMES block + system_health function)

```79:82:backend/v9/api/v9/shadow_routes.py
SYSTEM_NAMES = {
    "day_type": 1, "five_min": 2, "footprint": 3,
    "woodies": 4, "tpo": 5, "killzone": 6,
}
```

```85:158:backend/v9/api/v9/shadow_routes.py
def _get_system_health(system_name: str, request: Request) -> dict:
    """Compute health status for a single system."""
    sys_attr_map = {
        "day_type": "day_type_machine",
        "five_min": "five_min_system",
        "footprint": "footprint_system",
        "woodies": "woodies_system",
        "tpo": "tpo_system",
        "killzone": "killzone_system",
    }
    attr = sys_attr_map.get(system_name)
    sys_obj = getattr(request.app.state, attr, None) if attr else None
    # ... [health computation logic] ...
```

**Pkg 0 changes:** **NONE in this file**. It's already aligned with the future state. Desktop must inline this section so CC knows the target naming exists.

---

## File 5 · `backend/v9/systems/five_min/compliance_manifest.yaml` (entire · 57 lines)

```1:57:backend/v9/systems/five_min/compliance_manifest.yaml
system_id: 2
system_name: five_min
spec_title: MEMS26_5MIN_T1_DECISION_MAKER
spec_version: V3.3
manifest_last_synced: "2026-05-16"

decision_tree_nodes:
  - id: T1_SCHEMA
    name: "D-041 T1Setup output schema"
    status: IMPLEMENTED
    evidence: backend/v9/systems/five_min/output_schema.py
# ... [more nodes] ...

summary:
  total_requirements: 8
  implemented: 6
  partial: 2
  missing: 0
  drift_pct: 12.5
  notes: "Own manifest created to replace reliance on legacy chart_5min manifest."
```

**Pkg 0 change:** Line 56 — `notes: "Own manifest created to replace reliance on legacy chart_5min manifest."` → `notes: "Own manifest for Path A canonical · supersedes legacy chart_5min manifest per D-090."`

(The reference to "legacy chart_5min" is historical commentary, but per the audit it's better to update for clarity.)

---

## File 6 · `backend/main.py` (lines 1-145 · the startup wiring)

**NEW (replaces incorrect `backend/v9/main.py` in original handoff):**

```1:91:backend/main.py
"""MEMS26 unified backend — serves V8-compatible routes + V9 API.

Entry point for Render:
    web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import os
import time
import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.v9.app import v9_router, init_event_dispatcher
from backend.v9.api.journal_compat_routes import router as journal_compat_router
# ... [middleware + routes mount] ...

@app.on_event("startup")
async def _startup():
    """Initialize EventDispatcher + BarIngestionService at unified app startup."""
    import logging
    _logger = logging.getLogger("mems26")

    init_event_dispatcher()  # ← Line 56: calls the function being modified in Pkg 0

    # Start Bar Ingestion (D-077: must run before system hydration)
    from backend.v9.services.bar_ingestion import bar_ingestion_service
    bar_ingestion_service.start()

    # BarRouter: central bar distribution (D1.6)
    import asyncio as _asyncio
    from backend.v9.services.bar_router import BarRouter
    bar_router = BarRouter()
    bar_router.bind_main_loop(_asyncio.get_running_loop())
    app.state.bar_router = bar_router

    # D1.9.3: Instantiate + register systems via BarRouter
    try:
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        five_min_system = FiveMinSystem()
        app.state.five_min_system = five_min_system
        five_min_system.hydrate()
        for bt in five_min_system.subscribed_bar_types():
            bar_router.subscribe(bt, five_min_system.process_bar)
        _logger.info("[Main] FiveMinSystem hydrated + subscribed: %s", five_min_system.subscribed_bar_types())
    except Exception as e:
        _logger.error("[Main] FiveMinSystem startup failed: %s", e)
```

**Pkg 0 changes:** **NONE in this file**. Path A wiring (FiveMinSystem via BarRouter, lines 83-91) is the canonical path D-090 preserves. This file is **read-only** for Pkg 0 — Desktop must instruct CC explicitly: **forbidden to modify backend/main.py**.

**Why include this file:** CC must verify post-Pkg 0 that:
1. `init_event_dispatcher()` (line 56) still imports cleanly from `backend.v9.app`
2. FiveMinSystem (lines 83-91) still wires to `bar_router`
3. The 5 other systems (lines 93-127 · FootprintSystem, WoodiesSystem, TPOSystem, ReversalBarHandler, DayTypeStateMachine) are intact

Full file is 507 lines — Desktop should inline ~lines 1-340 (startup section) for CC to verify the broader wiring isn't broken.

---

## File 7 · `tests/v9/services/test_event_dispatcher.py` (entire · 522 lines)

This file contains **direct dependencies on Chart5MinSystem** in `TestRealWrappers` class (lines 446-521).

**Critical assertions that must change:**

```450:466:tests/v9/services/test_event_dispatcher.py
    def test_all_wrappers_import(self):
        from backend.v9.systems.wrappers import (
            DayTypeSystem, Chart5MinSystem, TickReversalSystem,
            WoodiesSystem, TPOSystem, KillzoneSystem,
        )
        systems = [
            DayTypeSystem(),
            Chart5MinSystem(),
            TickReversalSystem(),
            WoodiesSystem(),
            TPOSystem(),
            KillzoneSystem(),
        ]
        for s in systems:
            assert isinstance(s, BaseSystem)
            assert s.system_id > 0
            assert s.name != ""
```

```467:478:tests/v9/services/test_event_dispatcher.py
    def test_wrapper_subscriptions(self):
        from backend.v9.systems.wrappers import (
            DayTypeSystem, Chart5MinSystem, TickReversalSystem,
            WoodiesSystem, TPOSystem, KillzoneSystem,
        )
        assert DayTypeSystem.subscribed_streams == ["cumulative_delta", "volume_profile"]
        assert Chart5MinSystem.subscribed_streams == ["cumulative_delta"]
        assert TickReversalSystem.subscribed_streams == ["tick_reversal_15", "tick_reversal_12", "footprint"]
        assert WoodiesSystem.subscribed_streams == ["woodies_5min"]
        assert TPOSystem.subscribed_streams == ["volume_profile"]
        assert KillzoneSystem.subscribed_streams == []
```

```479:499:tests/v9/services/test_event_dispatcher.py
    def test_full_dispatcher_wiring(self):
        from backend.v9.systems.wrappers import (
            DayTypeSystem, Chart5MinSystem, TickReversalSystem,
            WoodiesSystem, TPOSystem, KillzoneSystem,
        )
        dispatcher = EventDispatcher()
        for sys_cls in [DayTypeSystem, Chart5MinSystem, TickReversalSystem,
                        WoodiesSystem, TPOSystem, KillzoneSystem]:
            dispatcher.register_system(sys_cls())

        table = dispatcher.get_routing_table()
        assert sorted(table["cumulative_delta"]) == [1, 2]   # ← S1 + S2 (chart_5min)
        assert sorted(table["volume_profile"]) == [1, 5]
        assert table["woodies_5min"] == [4]
        assert table["tick_reversal_15"] == [3]
        assert table["tick_reversal_12"] == [3]
        assert table["footprint"] == [3]

        registered = dispatcher.get_registered_systems()
        assert len(registered) == 6   # ← will need to become 5 post-Pkg 0
```

**Additionally:** `MultiStreamStub2` class (lines 71-82) uses `name = "chart_5min_stub"` — this is a test fixture stub, not a production reference. Pkg 0 may rename or leave as-is (it's a stub).

**Pkg 0 instruction for CC:**
1. `test_all_wrappers_import`: remove `Chart5MinSystem` from import + instantiation list (4 systems → 5 systems remain)
2. `test_wrapper_subscriptions`: remove the `Chart5MinSystem.subscribed_streams` assertion line
3. `test_full_dispatcher_wiring`:
   - Remove `Chart5MinSystem` from imports + loop
   - Change `assert sorted(table["cumulative_delta"]) == [1, 2]` → `assert table["cumulative_delta"] == [1]` (only S1 subscribes)
   - Change `assert len(registered) == 6` → `assert len(registered) == 5`
4. `MultiStreamStub2` (lines 71-82): leave as-is (it's a stub for routing tests, not a real system reference)

**Decision:** REFACTOR (not delete). The dispatcher itself still routes — only the assertions about the count + chart_5min change.

---

## File 8 · `tests/v9/compliance/v2_generated/test_snapshot_compliance.py` (entire · 504 lines)

This file has **3 categories** of chart_5min references:

### Category A · Mock Redis fixture (line 37)

```37:40:tests/v9/compliance/v2_generated/test_snapshot_compliance.py
        "mems26:v9:chart_5min:latest": json.dumps({
            "active_patterns": ["3BR"], "last_signal": "LONG",
            "current_bar": {"o": 5246.0, "h": 5247.25, "l": 5245.5, "c": 5246.75},
        }),
```

**Pkg 0 change:** `"mems26:v9:chart_5min:latest"` → `"mems26:v9:five_min:latest"`

### Category B · `test_system2_chart_5min_fields` (lines 201-206)

```201:206:tests/v9/compliance/v2_generated/test_snapshot_compliance.py
    def test_system2_chart_5min_fields(self):
        svc = CrossSystemSnapshotService(redis_client=_make_redis_with_data())
        result = svc.capture("entry", firing_system_id=2)
        sys2 = result["systems"]["2"]
        for field in ("active_patterns", "last_signal", "current_bar"):
            assert field in sys2, f"System 2 missing field: {field}"
```

**Pkg 0 change:** Rename test function to `test_system2_five_min_fields`. The fields themselves (`active_patterns`, `last_signal`, `current_bar`) **should be kept** — FiveMinSystem produces the same shape per `five_min/compliance_manifest.yaml`.

### Category C · `TestSystemNamesMapping` (lines 481-503)

```481:503:tests/v9/compliance/v2_generated/test_snapshot_compliance.py
class TestSystemNamesMapping:
    """Verify SYSTEM_NAMES matches MASTER_DEV_SKILL naming."""

    def test_has_6_systems(self):
        assert len(SYSTEM_NAMES) == 6

    def test_system_1_is_day_type(self):
        assert SYSTEM_NAMES[1] == "day_type"

    def test_system_2_is_chart_5min(self):
        assert SYSTEM_NAMES[2] == "chart_5min"

    def test_system_3_is_tick_reversal(self):
        assert SYSTEM_NAMES[3] == "tick_reversal"

    def test_system_4_is_woodies(self):
        assert SYSTEM_NAMES[4] == "woodies"

    def test_system_5_is_tpo(self):
        assert SYSTEM_NAMES[5] == "tpo"

    def test_system_6_is_killzone(self):
        assert SYSTEM_NAMES[6] == "killzone"
```

**Pkg 0 changes:**
- `test_system_2_is_chart_5min` (line 490) → rename to `test_system_2_is_five_min`
- Line 491: `assert SYSTEM_NAMES[2] == "chart_5min"` → `assert SYSTEM_NAMES[2] == "five_min"`

**Decision:** REFACTOR (not delete). The test class verifies SYSTEM_NAMES correctness — which is exactly what we want post-Pkg 0.

---

## Summary · what Desktop must produce

For each file, the mega prompt CC receives should contain:

| File | Inline strategy | Modifications CC makes |
|------|-----------------|------------------------|
| 1 | Full 343 lines | Lines 280, 295, 318-322 |
| 2 | Full 155 lines | Line 24 only |
| 3 | Full 137 lines | Lines 10, 23 only |
| 4 | Lines 78-158 | NONE (reference only) |
| 5 | Full 57 lines | Line 56 only |
| 6 | Lines 1-340 (or just §startup) | NONE — forbidden (Path A intact) |
| 7 | Full 522 lines | 3 test methods + assertion updates |
| 8 | Full 504 lines | 1 Redis key + 2 test names + 1 assertion |

**Plus** `backend/v9/systems/wrappers.py` lines 114-174 (Chart5MinSystem class) which Michael confirmed is in Desktop's Project Knowledge — DELETE entire class block.

---

*End of file inlines · Cursor agent · 2026-05-23 18:30 IL*
