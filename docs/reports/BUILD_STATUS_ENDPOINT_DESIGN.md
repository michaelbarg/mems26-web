# `/api/v9/build/pattern-status` · Endpoint Design

**Status:** DRAFT v1 · Cursor authored 2026-05-26 07:10 IL · pending Michael approval before CC implementation
**Goal:** Live debug view feeding the new frontend "Build Status" tab — answers
"why did pattern X fire / not fire / get vetoed in real time?" across the three
systems Michael named: **S2 5-min · Woodies · Day Type**.
**Authority sources:**
- `docs/decisions/D-091_S2_LIVE_SCOPE.md` (S2 day-type coverage matrix)
- `docs/spec_authority/S2_AUTH_TABLE_V1.md` (10 patterns × 7 day-types sizing · 🔒 LOCKED 25/5 12:22)
- `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` (entry/exit logic · 🔒 LOCKED)
- `docs/decisions/D-092_S4_WOODIES_UPDATE.md` (9 Woodies patterns + 21-stage decision tree · 🔒 LOCKED)
- `docs/spec_authority/MEMS26_WOODIES_DECISION_TREE_V1.md`
**Non-goals:**
- This endpoint does NOT route trades. It is read-only debug surface.
- It does NOT compute new strategy logic. Only reflects what existing systems already publish.

---

## 1 · Why a new endpoint (not reusing `/api/v9/spec/status`)

`backend/v9/api/v9/spec_compliance.py` exposes `/api/v9/spec/status` but it
returns only `{compliant, report_path, summary}` from a static markdown file.
It is a CI/spec linter, not a runtime pattern-debug surface.

The three live state surfaces already exposed are:
- `/api/v9/day_type/v9/current` → day type classification + reasoning
- `/api/v9/woodies/current` + `/patterns` + `/fire` → Woodies state + decision tree
- `/api/v9/five_min/nt_skip_stats` (lone S2 endpoint · not pattern-by-pattern)

There is **no endpoint that joins these three** and shows per-pattern "what is
required vs. what is present right now". That gap is what
`/api/v9/build/pattern-status` fills.

---

## 2 · Endpoint contract

### 2.1 Routes

```
GET  /api/v9/build/pattern-status
GET  /api/v9/build/pattern-status/{system_id}/{pattern_id}
```

**Versioning:** new route under `/api/v9/build/...` so it doesn't pollute
existing namespaces. Frontend polls `/api/v9/build/pattern-status` on the
"Refresh" button click (no auto-poll per Michael's `קצב עדכון כפתור רפרש` choice).

### 2.2 Query parameters (summary route)

| Name | Type | Default | Purpose |
|---|---|---|---|
| `systems` | csv string | `five_min,woodies,day_type` | Subset of systems to include · in current scope all 3 are returned |
| `include_history` | bool | `false` | If true, include last 5 fire/no-fire decisions per pattern (DB read) |

### 2.3 Response · top-level shape

```json
{
  "ts": "2026-05-26T07:10:00Z",
  "build_version": "v1",
  "session_date": "2026-05-26",
  "rtb_session": {
    "in_session": true,
    "minutes_to_open": 0,
    "minutes_to_close": 392
  },
  "systems": [
    { /* see §3 */ },
    { /* ... */ }
  ],
  "errors": []
}
```

### 2.4 Status taxonomy (Pill tones in frontend)

| status | label | tone | meaning |
|---|---|---|---|
| `fired` | ✅ Fired | success | Pattern fired today; trade routed |
| `armed` | 🟡 Armed | warning | All requirements satisfied; waiting on trigger (e.g., price level break) |
| `blocked` | ❌ Blocked | warning | One or more requirements missing/failed |
| `vetoed` | 🟠 Vetoed | warning | Detection valid but veto layer (e.g., NT day, Q0 gate) skipped it |
| `not_applicable` | ➖ N/A | neutral | Pattern not in today's coverage matrix (e.g., REACTIVE on NT day) |
| `unknown` | ❓ Unknown | neutral | System not initialized / endpoint missing data |

---

## 3 · Per-system shape

### 3.1 System object

```json
{
  "id": "five_min",
  "name": "S2 · Five-Minute Patterns",
  "running": true,
  "hydrated": true,
  "mode": "SHADOW",
  "data_freshness": {
    "last_bar_ts": "2026-05-26T13:55:00Z",
    "lag_seconds": 18,
    "fresh": true,
    "threshold_seconds": 360
  },
  "global_gates": [
    { "key": "nt_day_type", "spec": "DayType != Nontrend", "present": true, "value": "NeuC" }
  ],
  "patterns": [
    { /* see §3.2 */ }
  ]
}
```

### 3.2 Pattern object

```json
{
  "id": "BULL_FLAG_LONG",
  "name": "Bull Flag Long",
  "status": "armed",
  "label": "🟡 Armed",
  "reason": "Awaiting close > pole high · current=4715.25 · trigger=4717.50",
  "fired_today": false,
  "last_fire_ts": null,
  "components": [
    {
      "stage": "data",
      "key": "five_min_bar_recency",
      "spec": "max(ts) within last 6 min",
      "present": true,
      "value": "lag=18s · ✅"
    },
    {
      "stage": "detection",
      "key": "pole_volume",
      "spec": "pole bars avg vol ≥ 1.5× session avg",
      "present": true,
      "value": "1.83× · ✅"
    },
    {
      "stage": "day_type_gate",
      "key": "auth_table_cell",
      "spec": "S2_AUTH_TABLE_V1[BULL_FLAG_LONG][NeuC] ≠ SKIP",
      "present": false,
      "value": "❌ 0/0/0 (NeuC LOW typo zero)"
    },
    {
      "stage": "quality_tier",
      "key": "tier_classification",
      "spec": "HIGH/MEDIUM/LOW determined from TPO proximity",
      "present": true,
      "value": "MEDIUM · 2 contracts"
    },
    {
      "stage": "stop_setup",
      "key": "structural_anchor",
      "spec": "ATR-14 × 1.5 below swing low",
      "present": true,
      "value": "stop=4712.75 · ATR=2.50"
    },
    {
      "stage": "targets",
      "key": "t1_t2_t3",
      "spec": "3 targets per S2_EXIT_V6 + Type C window",
      "present": true,
      "value": "T1=4720 · T2=4725 · T3=4732 · Time stop=NeuC 30min"
    },
    {
      "stage": "exit_rules",
      "key": "trade_manager_arm",
      "spec": "TM polling armed · 5 Type A triggers ready",
      "present": true,
      "value": "✅"
    }
  ],
  "blockers": ["day_type_gate.auth_table_cell"]
}
```

Frontend renders one row per pattern with status pill + reason. Clicking the
row expands the `components` array as a sub-table.

---

## 4 · System-specific component lists

### 4.1 S2 · Five-Minute (10 patterns)

For each of the 10 PatternName values from `S2_AUTH_TABLE_V1.md` §2:
`REACTIVE_LONG · REACTIVE_SHORT · INITIATIVE_LONG · INITIATIVE_SHORT · INVERSE_HNS_LONG · HNS_TOP_SHORT · DOUBLE_BOTTOM_EE_LONG · DOUBLE_TOP_AA_SHORT · BULL_FLAG_LONG · BEAR_FLAG_SHORT`

| Stage | Key | Spec source | How to evaluate (read-only) |
|---|---|---|---|
| data | `five_min_bar_recency` | latest `bars_5min.ts` within 6 min | DB: `SELECT MAX(ts) FROM bars_5min` |
| data | `tpo_snapshot_present` | TPO Stream B publishing within 60 s | `/api/v9/tpo/current` |
| data | `cci_14_history` | ≥14 5-min bars buffered | `five_min_system._bar_buffer` len |
| detection | `pattern_detector` | pattern-specific detector in `five_min/patterns/*.py` | call detector with current buffer · return present/absent |
| detection | `direction_change_pre_fire` | no opposing direction change in last 2 bars | `direction_change_detector.detect_from_buffer()` |
| day_type_gate | `day_type_known` | `v9_day_type_history` today row classified | `/api/v9/day_type/v9/current` |
| day_type_gate | `auth_table_cell` | S2_AUTH_TABLE_V1 cell ≠ ❌ SKIP | const lookup |
| day_type_gate | `nt_skip` | not Nontrend day type | global short-circuit |
| quality_tier | `tier_classification` | TPO proximity → HIGH/MEDIUM/LOW | `quality_tier.get_quality_tier_v2()` |
| stop_setup | `structural_anchor` | swing pivot identified | detector emits it |
| stop_setup | `atr_14` | ATR computed from buffer | sliding 14-bar calc |
| targets | `t1_t2_t3` | per S2_EXIT_V6 + adaptive_stop | `setup_emitter` output |
| targets | `time_stop_window` | per D-091 day-type column | const lookup by day_type |
| exit_rules | `trade_manager_arm` | TM service running + monitoring | runtime probe |

### 4.2 S4 · Woodies (9 patterns)

For each of the 9 patterns per `D-092_S4_WOODIES_UPDATE.md` §2:
`ZLR · TLB · TT · GB100 · Vegas · Ghost · FaMir · HTLB · HFE`

Source: `WoodiesSystem.get_current()` already returns `active_patterns`,
`trend_state`, `cci_14`, `classification`, `decision_tree`. The endpoint
projects this into the per-pattern shape by joining with the 21-stage
decision tree (`A1..A7`, `B1..B14`):

| Stage | Key | Source |
|---|---|---|
| data | `cci_14_present` | `state.cci_14 is not None` |
| data | `tcci_present` | `state.get("tcci_value")` |
| data | `5min_bar_recency` | same as S2 |
| detection | `pattern_specific` | check `pattern.id in state.active_patterns` |
| stage_a1 | `strategic_gate` | `state.decision_tree.A1.passed` |
| stage_a2 | `pattern_validation` | `state.decision_tree.A2.passed` |
| stage_a3 | `trend_alignment` | `state.decision_tree.A3.passed` |
| ... (A4..A7, B1..B14) | per `MEMS26_WOODIES_DECISION_TREE_V1.md` | `decision_tree` dict |
| sizing | `confidence_score` | `pattern.confidence >= threshold` |
| stop_setup | `atr_14_stop` | from `pattern.stop` field |
| targets | `t1_t2_t3` | `pattern.targets` array |
| exit_rules | `ready_to_route` | `state.ready_to_route` |

Reason field uses `state.entry_classification_spec` when present.

### 4.3 S1 · Day Type (1 entity · 7 types)

The Day Type system is special — it has one "current" state, not 9 patterns.
For the build-status view, render it as a single row with one block of
components:

| Stage | Key | Source |
|---|---|---|
| data | `ib_locked` | `current.data.ib_locked` |
| data | `opening_type_set` | `current.data.opening_type` not null |
| classification | `day_type_assigned` | `current.classified == true` |
| classification | `probability_above_threshold` | `current.data.probability ≥ 0.55` (per spec) |
| classification | `directional_certainty` | `current.data.directional_certainty` ≥ threshold |
| classification | `zohar_rules_evaluated` | `len(active_zohar_rules) > 0` |
| classification | `not_developing` | `current.developing == false` |

`status` here means:
- `fired` → classification COMPLETE for today (probability + directional locked)
- `armed` → ib_locked, opening_type set, awaiting probability
- `blocked` → ib developing or missing data
- `vetoed` → if zohar rules force `UNKNOWN`

---

## 5 · Backend implementation outline (for CC HO-2)

### 5.1 Files to create

- `backend/v9/api/v9/build_status_routes.py` — new router
- `backend/v9/systems/build_status/__init__.py`
- `backend/v9/systems/build_status/aggregator.py` — main `BuildStatusAggregator` class
- `backend/v9/systems/build_status/s2_inspector.py` — produces 10 S2 pattern objects
- `backend/v9/systems/build_status/woodies_inspector.py` — produces 9 Woodies pattern objects
- `backend/v9/systems/build_status/day_type_inspector.py` — produces single day-type row
- `backend/v9/systems/build_status/auth_table_lookup.py` — projects `S2_AUTH_TABLE_V1` cells as a const dict (Python literal, NOT a JSON file read — frontend never sees the auth table directly)
- `backend/v9/systems/build_status/types.py` — Pydantic schemas (System, Pattern, Component)

### 5.2 Wiring

`backend/main.py` (or wherever `app` is constructed) registers the new router:
```python
from backend.v9.api.v9.build_status_routes import router as build_status_router
app.include_router(build_status_router)
```

### 5.3 Dependencies (allowed imports)

- `backend.v9.systems.five_min.five_min_system.FiveMinSystem` — via `app.state.five_min_system`
- `backend.v9.systems.woodies.woodies_system.WoodiesSystem` — via `app.state.woodies_system`
- `backend.v9.systems.day_type.api` reading the same DB row as `day_type_v9_routes.py`
- `backend.v9.systems.five_min.quality_tier` (read-only call)
- `backend.v9.systems.five_min.patterns.*` (read-only detector calls)

**Forbidden imports:**
- Any module that writes to DB (`trade_manager.manager`, `setup_emitter`, gateway)
- Any bridge module (`bridge/*`)
- Any frontend stub

### 5.4 Performance budget

- Endpoint must respond within **300 ms p95** (frontend refresh button UX)
- All inspectors run in-process; no extra DB transactions beyond what
  `day_type_v9.get_current()` already does
- No HTTP self-calls (do NOT have the endpoint curl `/api/v9/woodies/current`
  inside the handler — call the system objects directly)

### 5.5 Failure behavior (no silent errors · §5 §6 of pre-LIVE protocol)

- If `app.state.five_min_system is None` → that system object returns
  `running=false, hydrated=false`, components empty, `errors` array gets one
  entry. **Do not raise 500.**
- If any inspector raises → wrap in try/except, log `logger.warning`
  (rate-limited), and emit a partial result with that system marked
  `status: "unknown"` and `errors: [...]`. **Do not raise 500.**
- If DB read fails → fall back to `unknown` status with explicit error message.
- All logger.* calls on failure paths must be `warning` or `error` — never
  `debug` (per pre-LIVE protocol mistake #6 reminder).

---

## 6 · Tests required (CC G3 acceptance · ≥15 golden tests)

1. `test_build_status_endpoint_returns_200_when_all_systems_up`
2. `test_build_status_endpoint_returns_200_when_woodies_uninitialized` (graceful degradation)
3. `test_build_status_endpoint_p95_latency_under_300ms`
4. `test_s2_inspector_returns_10_patterns` (exact list match against `S2_AUTH_TABLE_V1.md`)
5. `test_woodies_inspector_returns_9_patterns` (exact list match against `D-092`)
6. `test_day_type_inspector_returns_single_entity`
7. `test_pattern_status_fired_when_setup_emitter_emitted_today` (uses DB fixture)
8. `test_pattern_status_armed_when_all_components_present_no_fire_yet`
9. `test_pattern_status_blocked_when_auth_table_cell_is_skip` (NT day case)
10. `test_pattern_status_vetoed_when_nt_day_type` (global gate)
11. `test_pattern_status_unknown_when_day_type_developing`
12. `test_response_shape_matches_pydantic_schema` (round-trip Schema → dict → Schema)
13. `test_endpoint_includes_data_freshness_block`
14. `test_endpoint_handles_inspector_exception_returns_partial_result_with_error` (anti-silent-failure)
15. `test_endpoint_no_self_http_calls` (asserts no `httpx`/`requests` in handler path)
16. `test_build_status_live_repro_with_real_five_min_system_instance` (§5 lesson: live wiring proof, not just mock-test pass)

Tests 15 and 16 are the **§5 anti-regression tests** that catch the
Memorial Day "dead-code wiring" class of bug (see
`docs/handoff/NEXT_CHAT_CONTINUATION_2026-05-26_AM.md` §5).

---

## 7 · Frontend contract (for Cursor T-08)

The frontend tab will:
1. Render once on mount (no auto-poll · Michael's instruction)
2. Show a `Refresh` button → fetches `/api/v9/build/pattern-status`
3. Render 3 sections (one per system) · each with a header row showing
   `running · hydrated · data freshness lag`
4. Per system, render a table of patterns with columns:
   `Pattern | Status pill | Reason | Last fire | Components (expand)`
5. Expanded component table per pattern: `Stage | Key | Spec | Present | Value`
6. Sticky filter at top: "Show only blockers" toggle (default ON during
   debug mode · OFF for survey)

Frontend file plan:
- `frontend/v9/src/v9/components/build_status/BuildStatusTab.tsx` (root)
- `frontend/v9/src/v9/components/build_status/SystemSection.tsx`
- `frontend/v9/src/v9/components/build_status/PatternRow.tsx`
- `frontend/v9/src/v9/components/build_status/ComponentTable.tsx`
- `frontend/v9/src/v9/hooks/useBuildStatus.ts` (fetch + react-query · no auto-refetch)
- `frontend/v9/src/v9/components/layout/V9Dashboard.tsx` — add a tab strip + state
  to switch between existing dashboard and new tab

Per `frontend/v9/AGENTS.md`, Cursor will keep the existing
`V9Dashboard.tsx` structure intact and add the tab as a sibling view, not a
replacement.

---

## 8 · Out of scope (explicitly)

- No new state machines · no new strategy logic
- No changes to `S2_AUTH_TABLE_V1.md`, D-091, D-092, EXIT_V6
- No DLL / bridge / Stream A surface changes
- No DB schema migrations · no new tables
- No auto-polling on frontend
- No alerting / Slack / email integration (debug surface only)

---

## 9 · Open questions for Michael (block until answered)

1. **Frontend tab placement:** Should the new tab appear as the first tab
   (overrides default view) or last tab (preserves current dashboard)?
   → Cursor recommends **last tab** (preserves current habits · default
   view unchanged)
2. **Include history?** Default `include_history=false`. Want a "Last 5 fires"
   side-panel per pattern on click?
   → Cursor recommends **deferred** to a follow-up (keeps Pkg scope tight)
3. **Authentication:** This is a debug endpoint. Same auth as existing
   `/api/v9/*` (none locally · BRIDGE_TOKEN externally) — confirm OK?
   → Cursor assumes yes (consistent with all other read-only debug routes)

---

## 10 · Sequencing

```
[T-06 design · this doc]
       ↓
[Michael approves · 5 min]
       ↓
[T-07 Cursor writes CC HO-2 mega-prompt · 30 min]
       ↓
[CC implements backend endpoint · 2–3 h]
       ↓
[T-08 Cursor builds frontend tab in parallel during CC · 2 h]
       ↓
[T-10 Cursor G3 review CC delivery]
       ↓
[T-11 E2E integration UAT]
```

---

## 11 · Acceptance for Pkg "BUILD-STATUS-1" promotion to G3

- [ ] All 16 tests pass
- [ ] `pytest tests/v9/build_status -q` green
- [ ] Endpoint live · `curl /api/v9/build/pattern-status` returns valid JSON in < 300 ms
- [ ] Frontend tab renders 3 sections × correct pattern counts (10 + 9 + 1)
- [ ] Refresh button fetches fresh data
- [ ] Live repro confirmed: Cursor manually triggers an S2 fire and the
      tab shows `status=fired` after refresh within 5 s
- [ ] No new `logger.debug` on failure paths
- [ ] STATUS_BOARD updated · Pkg report drafted
