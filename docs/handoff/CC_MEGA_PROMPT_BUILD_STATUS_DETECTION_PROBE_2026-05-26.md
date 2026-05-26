# MEGA PROMPT · Package BUILD-STATUS-2 · S2 Pattern Detection Probe Layer

**Owner:** Cursor (authored 2026-05-26 07:50 IL)
**Consumer:** Claude Code (CC)
**Reviewer:** Cursor verifies in G3 after delivery
**Depends on:** BUILD-STATUS-1 (already delivered · endpoint live)
**Problem being solved:**
When S2 pattern status is `armed` ("all pipeline requirements met"), the panel
currently shows only "Awaiting pattern trigger" — it does NOT explain WHY the
pattern hasn't triggered: pole missing? flag too long? no breakout yet? how far
from trigger? This package adds a **detection sub-layer** of `Component` objects
to each S2 pattern that answers this at the geometric level.

---

## Spec authority

- `backend/v9/systems/five_min/patterns/flags.py` — Bull Flag / Bear Flag geometry constants + `_find_pole_bull`, `_find_pole_bear` helpers (read full file before writing)
- `backend/v9/systems/five_min/patterns/head_shoulders.py` — H&S geometry + `_swing_lows`, `_swing_highs`, `_shoulders_symmetric` helpers (read full file)
- `backend/v9/systems/five_min/patterns/double_bt.py` — Double Bottom EE / Double Top AA geometry (read full file)
- `backend/v9/systems/five_min/five_min_system.py` lines 440–563 — `_detect_reactive()` and `_detect_initiative()` instance methods (read these lines verbatim before writing OFA probers)
- `backend/v9/systems/build_status/s2_inspector.py` (existing · MODIFY EXISTING in SCOPE) — add detection components
- `backend/v9/systems/build_status/types.py` — `Component` schema (already exists · read-only)

**No other spec sources needed. Do NOT invent conditions that aren't in these files.**

---

## What the probe layer does (per pattern · step-by-step)

### BULL_FLAG_LONG probe steps (implement in this order, stop at first fail)

```
Step 1  · min_bars           buffer ≥ MIN_BARS_REQUIRED (10)
Step 2  · pole_found         _find_pole_bull(bars) is not None
          value: "no valid pole" OR "pole=N bars · height=X.XXpts"
Step 3  · flag_length        FLAG_MIN_BARS(3) ≤ flag_len ≤ FLAG_MAX_BARS(8)
          value: "flag=N bars" OR "flag=N bars (out of range 3–8)"
Step 4  · flag_retrace       retrace ≤ FLAG_MAX_RETRACE_PCT(50%)
          value: "retrace=XX% ≤ 50% ✓" OR "retrace=XX% > 50% ✗"
Step 5  · breakout           last_bar.close > flag_high + TICK_SIZE
          value: "close=X · trigger=Y · gap=Z pts" (gap negative = still below trigger)
```

### BEAR_FLAG_SHORT probe — mirror of BULL_FLAG (step names: `pole_found` / `flag_length` / `flag_retrace` / `breakout`)

### INVERSE_HNS_LONG probe steps

```
Step 1  · min_bars           buffer ≥ MIN_BARS_REQUIRED (12)
Step 2  · swing_lows_found   len(_swing_lows(bars[-SEARCH_WINDOW:])) ≥ 3
          value: "N swing lows found in last 30 bars"
Step 3  · hns_structure      find LS/HEAD/RS triplet · HEAD lowest · _shoulders_symmetric()
          value: "no valid triplet" OR "LS=X.XX · HEAD=X.XX · RS=X.XX · sym=OK/FAIL"
Step 4  · neckline_breakout  last_bar.close > neckline_level + TICK_SIZE
          value: "close=X · neckline=Y · gap=Z pts"
```

### HNS_TOP_SHORT probe — mirror using `_swing_highs` (highest head · close BELOW neckline)

### DOUBLE_BOTTOM_EE_LONG probe steps

```
Step 1  · min_bars           buffer ≥ MIN_BARS_REQUIRED (10)
Step 2  · swing_lows_found   len(_swing_lows(...)) ≥ 2
          value: "N swing lows found"
Step 3  · trough_pair        find 2 lows within TROUGH_SYM_PCT(3%) of each other
          value: "T1=X.XX · T2=X.XX · diff=X.X%" OR "no symmetric pair found"
Step 4  · eve_variant        each trough width ≥ TROUGH_MIN_WIDTH_BARS(3)
          value: "T1 width=N bars · T2 width=M bars" OR "T1 width=N < 3 (not Eve)"
Step 5  · neckline_breakout  last_bar.close > neckline + TICK_SIZE
          value: "close=X · neckline=Y · gap=Z pts"
```

### DOUBLE_TOP_AA_SHORT probe — mirror using `_swing_highs` · peak width ≤ PEAK_MAX_WIDTH_BARS(2)

### REACTIVE_LONG probe steps (last 4 bars = b1,b2,b3,b4)

```
Step 1  · min_bars           buffer ≥ MIN_BARS_REQUIRED (from five_min_system.py constants)
Step 2  · b1_sellers         b1.close < b1.open AND b1.volume > 0
          value: "b1 close=X open=Y dir=bear/bull"
Step 3  · b2_volume_drop     b2.volume ≤ b1.volume × DROP_THRESHOLD_PCT
          value: "b2_vol=N · b1_vol=M · ratio=X.X"
Step 4  · b3_buyers          b3.close > b3.open
          value: "b3 close=X open=Y"
Step 5  · b4_confirm         b4.close > b4.open AND b4.close > b3.high
          value: "b4 close=X · b3_high=Y · above=T/F"
Step 6  · lookback_quiet     "max lookback vol < b1_vol × LOOKBACK_MAX_VOL_RATIO"
          value: "lookback_max=N · threshold=M"
NOTE: belly + COT/AMT are footprint-dependent. Show as:
  step: "belly_cot_amt" · present=True (assume pass for display · footprint live)
  value: "footprint-dependent · live value not probed here"
```

### REACTIVE_SHORT probe — mirror of REACTIVE_LONG (b1_buyers, b3_sellers, b4_close_below_b3_low)

### INITIATIVE_LONG probe steps (last 4 bars = b1,b2,b3,b4)

```
Step 1  · min_bars           buffer ≥ MIN_BARS_REQUIRED
Step 2  · b1_expansion       EXPANSION_MIN_PT ≤ (b1.high - b1.low) ≤ EXPANSION_MAX_PT
          value: "b1 range=X.XX · need [1.5, 1.75]"
Step 3  · b1_bull            b1.close > b1.open
Step 4  · b2_test            b2.low > b1.low (higher low) OR b2.poc_return within tolerance
          value: "b2_low=X · b1_low=Y · higher_low=T/F · poc_return=T/F"
Step 5  · b3_joining         b3 range > b1 range
          value: "b3_range=X · b1_range=Y"
Step 6  · b4_test            b4.low ≥ b2.low AND b4.close > b1.high
          value: "b4_close=X · b1_high=Y"
Step 7  · lookback_quiet     same as REACTIVE
NOTE: COT/AMT as: present=True value="footprint-dependent · live value not probed here"
```

### INITIATIVE_SHORT — mirror (b1_bear, b2_lower_high, b4_close_below_b1_low, COT above AMT)

---

## SCOPE — exactly these files

**WRITE NEW:**
- `backend/v9/systems/build_status/s2_pattern_probe.py`
  - One public function: `probe_pattern(pattern_id: str, bar_buffer: list, five_min_system=None) -> List[Component]`
  - Dispatches to private `_probe_bull_flag`, `_probe_bear_flag`, `_probe_inverse_hns`, `_probe_hns_top`, `_probe_double_bottom`, `_probe_double_top`, `_probe_reactive_long`, `_probe_reactive_short`, `_probe_initiative_long`, `_probe_initiative_short`
  - All probe functions are pure / read-only (no mutations on bar_buffer or system)
  - Import helpers from pattern files by **name** (e.g. `from backend.v9.systems.five_min.patterns.flags import _find_pole_bull, _find_pole_bear, ...`) — these are "private" functions but calling them for inspection is fine since we own the codebase
- `tests/v9/build_status/test_s2_pattern_probe.py`
  - ≥12 golden tests (see §Golden tests)

**MODIFY EXISTING:**
- `backend/v9/systems/build_status/s2_inspector.py`
  - After the `day_type_gate.nt_skip` component, add a detection probe section:
    ```python
    # detection sub-layer — probe pattern geometry
    from .s2_pattern_probe import probe_pattern
    probe_components = probe_pattern(pid, bar_buffer, five_min_system)
    components.extend(probe_components)
    ```
  - The probe may return `[]` (e.g., when buffer is empty). That's fine.
  - Do NOT change existing components (data / day_type_gate) — only append.
  - Status derivation logic: if already `fired` or `vetoed` → skip probe (no-op). If `armed` and ALL probe components present → keep `armed` label as "🟡 Armed (trigger close)". If some probe components `present=False` → keep `armed` label but update reason to show the first failing probe step.

**FORBIDDEN — do NOT touch:**
- `backend/v9/systems/five_min/` (read-only imports only — do NOT modify any detector file)
- `backend/v9/systems/build_status/aggregator.py`
- `backend/v9/systems/build_status/types.py`
- `backend/v9/systems/build_status/auth_table_lookup.py`
- `backend/v9/systems/build_status/woodies_inspector.py`
- `backend/v9/systems/build_status/day_type_inspector.py`
- `backend/v9/api/v9/build_status_routes.py`
- `backend/main.py`
- `bridge/`, `sc_study/`, `frontend/`
- Spec authority docs (locked)
- Existing tests outside `tests/v9/build_status/`

---

## Golden tests (≥12 · in `test_s2_pattern_probe.py`)

Fixtures: construct bar lists manually (dict with `o`, `h`, `l`, `c`, `v` keys · no DB needed).

1. `test_probe_bull_flag_no_bars_returns_min_bars_component`
   — `probe_pattern("BULL_FLAG_LONG", [])` → 1 component with `key="min_bars"` `present=False`

2. `test_probe_bull_flag_no_pole_found`
   — 15 flat bars (h-l=0.25) → pole component `present=False` · value contains "no valid pole"

3. `test_probe_bull_flag_pole_flag_no_breakout`
   — construct 20 bars: pole (5 bullish bars, 5pt rise) + flag (4 consolidation bars NOT breaking out)
   → pole component `present=True` · flag component `present=True` · breakout `present=False` · value shows gap negative

4. `test_probe_bull_flag_all_conditions_met`
   — construct bars: pole + flag + breakout bar (close > flag_high + TICK_SIZE)
   → all components `present=True` · value has trigger level and "gap=+" (positive)

5. `test_probe_bear_flag_no_pole`
   — 15 flat bars → pole `present=False`

6. `test_probe_bear_flag_full_detection`
   — construct bear pole + flag + breakdown → all present

7. `test_probe_inverse_hns_fewer_than_3_swing_lows`
   — monotonically declining bars (no swing lows) → `swing_lows_found` `present=False`

8. `test_probe_inverse_hns_pivots_no_breakout`
   — bars with 3 clear swing lows (LS/HEAD/RS) · neckline identified · last bar does NOT break neckline
   → structure component `present=True` · neckline_breakout `present=False` · value shows gap

9. `test_probe_double_bottom_no_symmetric_pair`
   — bars with 2 swing lows far apart (>3% diff) → trough_pair `present=False`

10. `test_probe_double_bottom_full_detection`
    — 2 symmetric Eve&Eve troughs + neckline break → all present

11. `test_probe_reactive_long_b1_not_sellers`
    — last 4 bars: b1 bullish · → `b1_sellers` `present=False`

12. `test_probe_reactive_long_b2_volume_not_dropping`
    — b1 bearish · b2.volume = b1.volume (no drop) → `b2_volume_drop` `present=False`

13. `test_probe_initiative_long_b1_range_too_small`
    — b1.high - b1.low = 0.5pt (below EXPANSION_MIN_PT 1.5pt) → `b1_expansion` `present=False`

14. `test_probe_returns_empty_list_for_unknown_pattern_id`
    — `probe_pattern("MADE_UP_ID", bars)` → returns `[]` (no crash, no exception)

---

## Allowed imports (whitelist)

```python
# Standard library
import logging
from typing import List, Optional

# Internal pattern helpers (read-only · inspect only)
from backend.v9.systems.five_min.patterns.flags import (
    _find_pole_bull, _find_pole_bear,
    TICK_SIZE, MIN_BARS_REQUIRED, POLE_MIN_BARS, POLE_MAX_BARS,
    FLAG_MIN_BARS, FLAG_MAX_BARS, FLAG_MAX_RETRACE_PCT,
    POLE_MIN_HEIGHT_TICKS, POLE_DIRECTIONAL_PCT,
)
from backend.v9.systems.five_min.patterns.head_shoulders import (
    _swing_lows, _swing_highs, _shoulders_symmetric,
    MIN_BARS_REQUIRED as HS_MIN_BARS,
    SEARCH_WINDOW as HS_SEARCH_WINDOW,
    PIVOT_LOOKBACK, TICK_SIZE as HS_TICK,
    HEAD_MIN_EXT_TICKS, SHOULDER_SYM_PCT,
)
from backend.v9.systems.five_min.patterns.double_bt import (
    _swing_lows as dbt_swing_lows,
    _swing_highs as dbt_swing_highs,
    MIN_BARS_REQUIRED as DBT_MIN_BARS,
    PIVOT_LOOKBACK as DBT_PIVOT_LOOKBACK,
    TROUGH_SYM_PCT, TROUGH_MIN_WIDTH_BARS, PEAK_MAX_WIDTH_BARS,
    NECKLINE_MIN_RISE_PCT, TICK_SIZE as DBT_TICK,
)

# Build-status types (existing)
from backend.v9.systems.build_status.types import Component
```

**For OFA constants (REACTIVE/INITIATIVE):** read `five_min_system.py` near the top of the file to find `MIN_BARS_REQUIRED`, `DROP_THRESHOLD_PCT`, `EXPANSION_MIN_PT`, `EXPANSION_MAX_PT`, `POC_RETURN_TOLERANCE_PT`, `LOOKBACK_BARS`, `LOOKBACK_MAX_VOL_RATIO`, `BELLY_DOMINANCE_RATIO`. Import them by name from the module top-level constants OR re-declare them as module constants in `s2_pattern_probe.py` with a comment citing the source file and line. Do NOT hardcode numeric literals for these thresholds.

**Forbidden imports:**
- `httpx`, `requests`, `aiohttp`
- `setup_emitter`, `contract_split`, `trade_manager.*`, `trail_engine`
- Any new pip package
- Any import that writes to DB or routes a trade

---

## Constraints

a) **Pure read-only probers.** `probe_pattern` must not mutate `bar_buffer` or call any method that routes trades, writes DB, or emits events. Treat bar_buffer as read-only.

b) **Stop-at-first-fail.** Each prober halts at the first failing step and returns components up to (and including) the failing step. This is more informative than showing all steps regardless.

c) **No exception propagation.** Wrap the entire `probe_pattern` function body in try/except — if it raises, log `logger.warning` and return `[]` (no crash to the inspector caller).

d) **No silent debug on error paths.** `logger.debug` on exception paths is forbidden. Use `logger.warning`.

e) **Value strings are human-readable.** The `value` field is rendered directly in the frontend. Include numbers with 2 decimal places, units (pts, bars, %), and a ✓/✗ indicator. Example: `"pole=7 bars · height=3.25pts ✓"`.

f) **OFA footprint conditions shown as pass.** For belly/COT/AMT conditions: `present=True`, `value="footprint-dependent · not probed (live system has access)"`. Do NOT attempt to call footprint methods in the probe.

g) **Import private helpers by name.** Functions like `_find_pole_bull` start with `_` but they're pure functions in our own codebase. Importing them by name is fine — this is an explicit design choice for the debug layer, not monkey-patching.

h) **OFA constants — do NOT hardcode.** Find `DROP_THRESHOLD_PCT`, `EXPANSION_MIN_PT`, etc. in `five_min_system.py` (they'll be near the top near `MIN_BARS_REQUIRED`). Read and import them.

i) **Keep existing s2_inspector components.** Probe components are APPENDED after existing ones, never replacing.

---

## Deliverable format

1. **Files** (full paths · A/M markers):
   - A `backend/v9/systems/build_status/s2_pattern_probe.py`
   - A `tests/v9/build_status/test_s2_pattern_probe.py`
   - M `backend/v9/systems/build_status/s2_inspector.py` (diff: added probe import + component extend + reason update · ≤ 15 lines added)

2. **Commit message:**
   `feat(build-status): add S2 detection probe layer — per-pattern geometry sub-conditions`

3. **Self-report:**
   - Any OFA constant not found at expected location? (list)
   - Any private helper import that failed? (list)
   - Exception raised in any probe during testing? (must be none)
   - Fake bars used in tests vs. real fixture data? (fake is fine here — pure geometric)

4. **`ReadLints` output** (paste verbatim)

5. **`pytest tests/v9/build_status/ -q` output** (paste verbatim · all tests including existing 57 + new ≥12)

6. **`pytest tests/v9/ -q` tail** (paste verbatim · 30 lines · prove no regression)

7. **Live curl sample** — call endpoint and show first S2 pattern's components (should now include detection steps):
   ```bash
   curl -fsS http://localhost:8000/api/v9/build/pattern-status | python3 -c "
   import json,sys; d=json.load(sys.stdin)
   s2 = next(s for s in d['systems'] if s['id']=='five_min')
   p = s2['patterns'][0]
   print('Pattern:', p['id'])
   print('Status:', p['status'])
   print('Components:')
   for c in p['components']:
       print(f'  [{\"✓\" if c[\"present\"] else \"✗\"}] {c[\"stage\"]}.{c[\"key\"]} → {c[\"value\"]}')
   "
   ```
   Expected output format:
   ```
   Pattern: REACTIVE_LONG
   Status: blocked
   Components:
     [✓] data.five_min_bar_recency → lag=18.0s
     [✓] data.cci_14_history → buffer=156
     [✗] day_type_gate.day_type_known → unknown
     [✗] day_type_gate.auth_table_cell → day_type unknown — cannot evaluate
     [✓] day_type_gate.nt_skip → OK
     [✓] detection.min_bars → buffer=156 ≥ 10 ✓
     [✗] detection.b1_sellers → b1 close=7539.50 open=7540.00 dir=bull
   ```
   (exact values will differ · structure must match)

---

## Stop signal

STOP and output `STOP — <reason> · need Michael decision on <specific question>` if:
- An OFA constant (`DROP_THRESHOLD_PCT`, `EXPANSION_MIN_PT`, etc.) not found in `five_min_system.py` — do NOT guess the value
- A private helper (`_find_pole_bull`, `_swing_lows`, etc.) import fails at runtime
- The `bar_buffer` items in live production are objects (not dicts) with different key names than `o/h/l/c/v`
- A golden test for full detection cannot be constructed from the geometry constants (i.e., the constants' ranges are contradictory)
- Any imported function raises an exception during testing

---

## Memorial Day lesson reminders

1. **Field name check before use.** Bar buffer items may be dicts with keys `o/h/l/c/v` OR objects with attributes `.o/.h/.l/.c`. Read `five_min_system.py` lines near `_detect_reactive` to see how bars are accessed — match that exactly.
2. **No silent returns.** If `probe_pattern` catches an exception and returns `[]`, the warning log MUST fire (test 14 verifies this implicitly — unknown ID returns `[]` silently, but real exceptions must warn).
3. **Stop-at-first-fail is not optional.** Without it, every pattern would show all 5 steps as failed when just step 1 is the root cause — confusing the user. Stop-at-first-fail keeps the reason on the single root cause.

---

**End of mega-prompt · CC begin work · ETA ~1.5 hours · report back on completion.**
