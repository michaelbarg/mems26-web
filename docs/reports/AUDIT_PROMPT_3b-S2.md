# AUDIT PROMPT 3b-S2 — Wave 0 Complete
Date: 2026-05-16 · Branch: feature/v9_architecture_rebuild

## §A · S2 Internal Inventory

```
backend/v9/systems/five_min/
├── __init__.py              (10 lines)
└── five_min_system.py       (518 lines)

Total: 2 .py files, 528 LOC
```

Also:
- API: `backend/v9/api/v9/five_min/routes.py` (4 endpoints)
- DB: `backend/v9/db/models/five_min_setups.py` + `five_min_state.py`

## §B · pre_fire_validator status

**MISSING.** Zero matches for `pre_fire_validator`, `PreFireValidator`, `M18`, or `D-063` anywhere in `backend/`. The shared service does not exist. `backend/v9/shared/` contains only `volume_spike.py` + `cvd_context.py`.

## §C · Reactive/Initiative status (4 patterns)

| Pattern | Status | Evidence |
|---|---|---|
| REACTIVE LONG | EXISTS | five_min_system.py:273-304 `_detect_reactive()` with belly + POC rising + COT > AMT |
| REACTIVE SHORT | EXISTS | five_min_system.py:305-315 (mirror, POC falling) |
| INITIATIVE LONG | EXISTS | five_min_system.py:327-353 with COT < AMT + expansion bars |
| INITIATIVE SHORT | EXISTS | five_min_system.py:354-362 (mirror) |

Output format: `(direction_str, confidence_float, metadata_dict)` — NOT the full T1Setup schema per D-041.

## §D · COT/AMT status

**EXISTS (partial):**
- `_get_cot_from_footprint()` (line 245-253) — HTTP GET to `/api/v9/footprint/current`, reads cumulative delta
- `_get_amt_from_footprint()` (line 254-260) — HTTP GET, reads 90-min average
- COT/AMT comparison: line 385-391 (1.2x strong bull, 0.8x strong bear)
- Also exists: `backend/v9/systems/tick_reversal/signals/zohar_cot_amt.py` (separate implementation)

**Gap:** No standalone `cot_amt.py` module reading directly from Sierra `cumulative_delta.json`. Current implementation cross-reads from Footprint via HTTP.

## §E · Belly hooks status

| Location | Status | Evidence |
|---|---|---|
| Backend (Footprint) | EXISTS | `footprint/detectors.py:138` — `belly_ratio_dominant` |
| Backend (tick_reversal) | EXISTS | `signal_detectors/zohar_signals.py:18` — `detect_belly_comparison()` |
| five_min consumption | EXISTS | `five_min_system.py:196` — `_get_belly_from_footprint()` HTTP GET |
| DLL (Sierra) | NOT FOUND | No `belly` in `sc_study/*.cpp` |

## §F · S2 Tests

| File | Tests | Status |
|---|---|---|
| tests/test_five_min_system.py | 10 | 10/10 PASS |
| tests/atomic/test_five_min_sizing.py | 5 | 5/5 PASS |
| tests/atomic/test_five_min_patterns.py | 9 | 9/9 PASS |
| **Total** | **24** | **24/24 PASS** |

## §G · S2 Endpoints

| Method | Path | Status |
|---|---|---|
| GET | /api/v9/five_min/current | ALIVE |
| GET | /api/v9/five_min/setups | ALIVE (placeholder, empty) |
| GET | /api/v9/five_min/fire | ALIVE |
| GET | /api/v9/five_min/stats | ALIVE |

## §H · S1 Touchpoints (13 items)

| # | Touchpoint | Status | Path/Endpoint |
|---|---|---|---|
| T1.1 | 6 Day Types classifier | :green_circle: | schemas.py:11-16 (Trend_Normal, Trend_DD, Variation, Normal, Neutral, Nontrend) |
| T1.2 | Targets per Day Type matrix | :green_circle: | day_type/targets_table.py:121 `get_targets()` + layer3/entry_executor.py:130 |
| T1.3 | Time Stop per Day Type | :green_circle: | entry_executor.py:59-62 (Variation=60, Normal=30, Neutral=30, Nontrend=20) |
| T1.4 | Market Clock service | :green_circle: | services/market_clock.py + /api/v9/clock/now (clock_routes.py:8) |
| T1.5 | Open Type (5 sub-types) | :green_circle: | detector.py:36-108 (OD/OTD/ORR/OA_IN/OA_OUT) + opening_detector.py |
| T1.6 | IB data (high/low/width/class) | :green_circle: | TPO system tracks IB, main.py:147-148 cross-reads. NARROW/MEDIUM/WIDE in schemas.py |
| T1.7 | POC Migration State | :green_circle: | tpo/detector.py:118-137 (STUCK/ACCEPTED/ROTATIONAL/FAILED) |
| T1.8 | Previous Day Data (D-070) | :yellow_circle: | Fields exist in BarInput (pd_high/pd_low/pd_close). Endpoint /tpo/previous_day exists. BUT main.py never populates pd_* into state machine. |
| T1.9 | Behavior Phase | :green_circle: | systems/behavior_phase/phase_detector.py (DEVELOPMENT/REVERSAL/TRANSITION/MATURE) + routes |
| T1.10 | 10:30 transition / IB lock | :green_circle: | state_machine.py stage A4 at session_min >= 60 (ib_period_min config). chart_5min/detector.py:39 `_day_type_locked` |
| T1.11 | Tail Detection | :green_circle: | tpo/detector.py:100-101, profile_builder.py:144-148 `compute_tails()` |
| T1.12 | HVN/LVN | :green_circle: | tpo/profile_builder.py:151-153, levels.py compute_hvn_lvn(), schemas.py:151-152 |
| T1.13 | Cumulative Delta | :green_circle: | Sierra v9_export/cumulative_delta.json EXISTS. Bridge streams it. bars.py:395 POST endpoint. |

**Summary: 12/13 GREEN, 1 YELLOW (T1.8 prev day not wired in production).**

## §I · S4 Woodies Safety

- **Latest commits:** 19af326 (direction_change_detector W3-beta), 91bc844 (logic Wave 4 zeta), etc.
- **WIP detection:** Clean (no uncommitted changes in woodies/)
- **pre_fire_validator:** NOT integrated. Only one "fired" log message at line 292.
- **Shared imports:** NONE (woodies does not import from backend.v9.shared)
- **Timeframe:** 30-min ONLY. Zero references to 5-min or five_min inside woodies.
- **39 ZLR fails:** Present in tests/v9/systems/test_woodies_patterns.py (6 real + V1 drift tests)

**Risk verdict: GREEN** — S4 operates on 30-min bars only, no coupling to S2 (5-min), no shared imports. Safe to build S2 without touching woodies.

## §J · S3/S5/S6 Light Scan

| System | S2 Coupling | Notes |
|---|---|---|
| S3 Footprint | READ via HTTP | five_min_system.py:204,249 — GET /api/v9/footprint/current for belly + COT/AMT |
| S5 TPO | NONE in S2 | No poc_tpo/vah/val references in five_min/ |
| S6 Killzone | NONE in S2 | Only a comment at line 372 noting exclusion |

**Routing collisions: 0.** No false routing from S2→S3 (Tree V3.3 §Stage D is stale per V9 correction).

## §K · Sierra Data Verification

| File | Status | Schema Sample |
|---|---|---|
| cumulative_delta.json | :green_circle: EXISTS | `{"type":"cumulative_delta","version":"v9.2.0","points":[{"i":N,"d":float,"cum":float,"p":price}]}` |
| footprint.json | :green_circle: EXISTS | `{"type":"footprint","version":"v9.2.0","bar_count":31,"bars":[{"idx":N,"o/h/l/c":float,"vol":N,"delta":N,"poc_price":P,"levels":[...]}]}` |
| volume_profile.json | :green_circle: EXISTS | `{"type":"volume_profile","version":"v9.2.0","profiles":[{"bar_idx":N,"poc":P,"vah":P,"val":P,"levels":[...]}]}` |
| stacked_imbalances.json | :green_circle: EXISTS | (in /v9_export/, not sampled) |

All v9.2.0 format. Sierra actively exporting.

## §L · Strategic Gap Matrix (16 items)

| # | Component | Status | Source Spec |
|---|---|---|---|
| 1 | pre_fire_validator | :red_circle: MISSING | M18 · D-063 |
| 2 | T1 D-041 output schema (T1Setup) | :red_circle: MISSING | D-041 · Constitution V3 §T1 |
| 3 | COT/AMT standalone module | :yellow_circle: PARTIAL (HTTP cross-read from Footprint, not direct Sierra) | Constitution V3 §T1 |
| 4 | Reactive_Long 4-bar | :green_circle: EXISTS | Constitution V3 §T1 |
| 5 | Reactive_Short 4-bar | :green_circle: EXISTS | Constitution V3 §T1 |
| 6 | Initiative_Long 4-bar | :green_circle: EXISTS | Constitution V3 §T1 |
| 7 | Initiative_Short 4-bar | :green_circle: EXISTS | Constitution V3 §T1 |
| 8 | Belly wiring | :green_circle: EXISTS (via Footprint HTTP) | Constitution V3 §T1 |
| 9 | Quality Tier H/M/L sizing | :yellow_circle: PARTIAL (full/half/reject exists, not H=3/M=2/L=skip) | Tree V3.3 |
| 10 | T1 label wire-up to L3 | :yellow_circle: PARTIAL (layer3/entry_executor.py exists but not wired from S2) | D-051 |
| 11 | Q0 Pre/Post-Lock dispatcher | :red_circle: MISSING | Tree V3.3 §Stage B |
| 12 | First Hour Buffer state machine | :red_circle: MISSING | Tree V3.3 §Stage A |
| 13 | First Hour Matrix (5 Opening Types × pattern) | :red_circle: MISSING | Tree V3.3 §Stage C |
| 14 | Opening Choppiness scorer (3-6 bars) | :red_circle: MISSING | Tree V3.3 §Stage A |
| 15 | Confluence count (max 4) | :red_circle: MISSING | Tree V3.3 §Stage D |
| 16 | 10:30 transition to Day Type Mode | :yellow_circle: PARTIAL (chart_5min/detector.py has `_day_type_locked` flag) | Tree V3.3 §Stage E |
| 17 | Tests >= 10 per module | :green_circle: 24 tests exist | Standard |

**Summary: 5 GREEN, 5 YELLOW (partial), 6 RED (missing).**

## §M · Risk Register (Wave 1 build readiness)

| Task | Risk | Mitigation |
|---|---|---|
| C1 pre_fire_validator | Low — new shared file, no existing code to break | Place in `backend/v9/shared/`, import from S2/S3/S4 later |
| C2 T1Setup schema | Low — new file, won't collide | `backend/v9/systems/five_min/output_schema.py` |
| C3 COT/AMT standalone | Medium — existing HTTP cross-read in five_min_system.py. Must not break existing pattern detection. | Add module alongside, don't remove HTTP fallback yet |
| First Hour Buffer | Medium — new state machine interacting with bar processing | Keep separate from existing `_detect_reactive/initiative` |
| First Hour Matrix | Low — pure data table | New file, no collision |
| 10:30 transition | Medium — chart_5min/detector.py has related logic | Verify no duplication |

## §N · CC's Recommended Wave 1 Sequence

Based on findings, recommended build order:

1. **C1: `pre_fire_validator.py`** (SHARED · P0 · blocks all fires · no dependencies)
   - Path: `backend/v9/shared/pre_fire_validator.py`
   - 7 validations per spec. Tests: 5 minimum.
   - Risk: LOW. New file in shared/, no existing code affected.

2. **C2: `T1Setup` output schema** (P0 · defines contract for all S2 output)
   - Path: `backend/v9/systems/five_min/output_schema.py`
   - Pydantic BaseModel with all D-041 fields.
   - Risk: LOW. New file.

3. **C3: `cot_amt.py` standalone** (P0 · direct Sierra read)
   - Path: `backend/v9/systems/five_min/cot_amt.py`
   - Read from `cumulative_delta.json` (verified exists, schema known).
   - 90-min rolling window (18 × 5-min bars).
   - Risk: MEDIUM. Must coexist with existing HTTP cross-read.

**DEFER to Wave 2:**
- First Hour Buffer (C9) — complex state machine, needs spec clarification
- First Hour Matrix (C9) — depends on Opening Type data flow
- Opening Choppiness scorer — depends on buffer
- Confluence count — depends on matrix

**SKIP (already exists):**
- Reactive/Initiative 4-bar patterns (4/4 exist)
- Belly wiring (exists via Footprint HTTP)
- COT/AMT comparison logic (exists in _score_pattern)

**Estimated Wave 1:** 3 commits, ~1 hour CC time.
