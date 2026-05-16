# REPORT — PROMPT 3a-AUDIT Findings
## Inspection-only · for PROMPT 3a scope refinement

Date: 2026-05-15
Branch: feature/v9_architecture_rebuild

## §1 — Day Type System Implementation

### Files found (8 Python files):
- api.py (11.5KB) — V1 classifier + /current endpoint
- state_machine.py (22.6KB) — full state machine with IB tracking + re-eval
- detector.py (9.2KB) — classify_ib_width, detect_opening_type, detect_behavior, check_reeval_triggers
- targets_table.py (3.9KB) — get_targets() for all 6 types
- schemas.py (6.9KB) — DayType enum, BarInput, DayTypeState
- models.py (1.2KB) — DB model V9DayTypeState
- hydration.py (1.6KB)
- compliance_manifest.yaml (7.3KB)

### Inputs consumed:
| Input | In code? | Source |
|---|---|---|
| ib_high | ✅ YES | state_machine.py:146, api.py:97 |
| ib_low | ✅ YES | state_machine.py:147, api.py:98 |
| ib_width | ✅ YES | detector.py:14 (classify_ib_width) |
| ib_class | ✅ YES | state_machine.py:148 |
| ib_locked | ✅ YES | state_machine.py:149, api.py:99 |
| poc (TPO) | ❌ NO | Not consumed by day_type system |
| vah | ❌ NO | Not consumed |
| val | ❌ NO | Not consumed |
| poc_migration_state | ❌ NO | Not consumed |
| open_price | ❌ NO | Not as explicit field |
| open_type | ✅ YES | detector.py detect_opening_type() |
| high_of_day | ❌ NO | Not tracked |
| low_of_day | ❌ NO | Not tracked |
| tails | ❌ NO | Not consumed (exists in TPO system) |
| single_prints | ❌ NO | Not consumed |
| distribution_shape | ❌ NO | Not consumed |
| previous_day | ❌ NO | No previous day data consumed |

### Day Type classification:
Two paths exist:
1. **V1 classifier** (api.py:80): Simple IB extension ratio rules. Reads TPO ib_locked + bars.
   Types: Normal, Neutral, Trend_Normal, Nontrend, Variation (5 types — no Trend_DD)
2. **State machine** (state_machine.py): Full 22.6KB engine with DECISION_MATRIX (15 entries).
   Types: All 6 (Trend_Normal, Trend_DD, Variation, Normal, Neutral, Nontrend)
   BUT: only used by main.py inline closure, NOT by /current endpoint

### Tests: None found in backend/v9/tests/ for day_type (compliance tests referenced but files missing)

## §2 — API Surface

### Endpoints found (200):
- /api/v9/day_type/current — 200 (V1 classifier, returns day_type + confidence + ib_h/l)
- /api/v9/day_type/state — 200 (state machine output)
- /api/v9/tpo/current — 200 (POC/VAH/VAL/IB/migration/HVN/LVN)
- /api/v9/tpo/sessions — 200 (6 sessions with full data incl previous days)
- /api/v9/behavior_phase/current — 200
- /api/v9/live_price — 200

### Endpoints MISSING (404):
- /api/v9/session/open — 404 (open price)
- /api/v9/session/current — 404 (session summary)
- /api/v9/open_type/current — 404
- /api/v9/tpo/previous_day — 404
- /api/v9/session/previous — 404
- /api/v9/clock/now — 404 (market clock)
- /api/v9/market/clock — 404
- /api/v9/day_type/history — 500 (exists but errors)

### Previous day data: AVAILABLE in tpo/sessions (trading_date=2026-05-14 CASH session has POC/VAH/VAL/IB)

## §3 — Sierra Source

### mes_ai_data.json provides:
- session_phase: "OVERNIGHT"
- session_min: -1
- market_profile: { poc, vah, val, session_high, session_low, tpo_poc }
- vwap: { value, distance, above, pullback }
- woodi_pivots: { pp, r1, r2, s1, s2 }
- cvd: { current, trend, delta }

### DLL exports session_high/session_low (lines 396-397)

### IB study: NOT explicit in DLL — computed by Python TPO system from first 12 bars

### Previous day TPO: NOT in DLL — available from v9_tpo_sessions DB table

## §4 — Time/Clock Infrastructure

### SessionClassifier: EXISTS at backend/v9/common/session_classifier.py
- 8 sessions: WEEKEND, MAINTENANCE, OVERNIGHT, PRE_MARKET, CASH_OPEN, FIRST_HOUR, CASH_HOURS, AFTER_HOURS
- Uses pytz America/New_York
- Time boundaries hardcoded (09:30, 10:30, 16:00 ET)

### Holiday handling: PARTIAL in killzone/detector.py
- `is_holiday_half_day` parameter exists
- No holiday calendar loaded — relies on caller passing the flag
- No CME calendar integration

### Clock endpoint: MISSING — no /api/v9/clock/now endpoint

## §5 — CME Calendar
- CME holiday page requires browser/PDF — not reliably fetchable via curl
- MARK FOR MANUAL: verify at https://www.cmegroup.com/tools-information/holiday-calendar.html
- 2026 US market holidays (standard): MLK Jan 19, Presidents Feb 16, Good Friday Apr 3, Memorial May 25, Independence Jul 3, Labor Sep 7, Thanksgiving Nov 26, Christmas Dec 25

## §6 — GAP ANALYSIS

### ✅ VERIFIED EXISTS (use as-is):
- Day Type state machine (22.6KB, full 6-type classifier with decision matrix)
- Day Type targets table (6 types, per-type T1/T2/T3 + time stops)
- IB tracking in TPO system (ib_high/low/locked/width/class)
- SessionClassifier (8 sessions, ET timezone)
- Previous day data in v9_tpo_sessions DB
- Behavior Phase detector (4 phases)
- Live price endpoint
- mes_ai_data.json (session_high/low, POC, VWAP, pivots)

### ❓ NEEDS EXTENSION:
- V1 classifier: missing Trend_DD (only 5 of 6 types)
- Day Type /current: uses V1 path, not state machine path
- Holiday handling: flag exists but no calendar

### ❌ MISSING (must build):
1. /api/v9/clock/now — market clock endpoint (session, ET time, next boundary)
2. /api/v9/session/previous — previous day summary (POC/VAH/VAL/IB/type)
3. Open Type classification in V1 path (state machine has it, V1 doesn't)
4. HoD/LoD tracking (session_high/low from mes_ai_data not piped to day_type)
5. Day Type /current should use state machine OR expose both paths

### 🚫 BLOCKED:
- CME holiday calendar: needs manual verification or PDF parse

## §7 — PROMPT 3a SCOPE RECOMMENDATION

| Item | Status | Effort |
|---|---|---|
| A.1.1 Day Type audit | ✅ DONE (this report) | 0 |
| A.1.2 Market Clock service | ❌ BUILD | ~1 commit |
| A.1.3 /api/v9/clock/now | ❌ BUILD | part of A.1.2 |
| A.1.4 Wire Day Type to clock | ❓ EXTEND (V1→state machine) | ~1 commit |
| A.1.5 Previous Day endpoint | ❌ BUILD (data in DB) | ~1 commit |
| A.1.6 Open Type in V1 path | ❓ EXTEND | ~1 commit |
| A.1.7 IB Width history | ✅ EXISTS (in tpo/sessions) | 0 |
| A.1.8 Tests | ❌ BUILD | ~1 commit |

Estimated PROMPT 3a effort: **~5 commits · ~2-3 hours**
