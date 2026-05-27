י ה# W-5 Step 1: ZLR Failure Audit

**Date:** 2026-05-26  
**Author:** Claude (W-5 audit-only pass)  
**Scope:** Count, classify, and root-cause every ZLR-related test in the MEMS26 codebase

---

## 1. Test Count Reconciliation

### Raw search results

| Source file | ZLR test functions | ZLR class defs |
|---|---|---|
| `tests/v9/systems/test_woodies_patterns.py` | 8 (`test_zlr_up_detected`, `test_zlr_down_detected`, `test_zlr_no_signal_flat`, `test_zlr_insufficient_data`, `test_zlr_confidence_range`, `test_zlr_details_present`, `test_zlr_detected_via_all`, `test_legacy_zlr`) | 1 (`TestZLR`) |
| `tests/v9/systems/test_woodies.py` | 3 (`test_zlr_up`, `test_zlr_down`, `test_zlr_no_signal`) | 1 (`TestZLR`) |
| `tests/v9/systems/test_atr_stop.py` | 3 (`test_zlr_long_normal_vol_cap_hit`, `test_zlr_long_low_vol_cap_clamps`, `test_zlr_short_normal_vol`) | 0 |
| `tests/v9/compliance/v1_generated/test_system4_v1.py` | 2 (`test_zlr_detected_in_studies`, `test_zlr_direction_in_studies`) | 2 (`TestZLRDetectedInOutput`, `TestZLRDirectionInOutput`) |
| `backend/v9/tests/systems/woodies/stages/test_a6.py` | 1 (`test_zlr_is_initiative`) | 0 |

**Files that mention ZLR but have NO ZLR test functions:**

- `tests/atomic/test_woodies_runtime_contract.py` -- uses ZLR as fixture data, no ZLR-specific test
- `tests/atomic/test_woodies_fire_endpoint.py` -- uses ZLR in mock payload, no ZLR-specific test
- `tests/atomic/test_cross_system_integration.py` -- uses ZLR in fixture, no ZLR-specific test
- `tests/atomic/test_woodies_decision_tree.py` -- uses ZLR in fixture, no ZLR-specific test
- `backend/v9/tests/systems/woodies/stages/test_a2.py` -- asserts ZLR in pattern_preference, not a ZLR detector test
- `backend/v9/tests/systems/woodies/stages/test_a3.py` -- asserts ZLR in CONTINUATION_PATTERNS, not a ZLR detector test
- `backend/v9/tests/systems/woodies/test_hfe_pattern.py` -- uses zlr_detected=False in fixture, not a ZLR test

### Totals

| Metric | Count |
|---|---|
| **Dedicated ZLR test functions** | **17** |
| Of which: ZLR pattern detector tests | 11 (test_woodies_patterns.py: 8, test_woodies.py: 3) |
| Of which: ZLR stop-placement tests | 3 (test_atr_stop.py) |
| Of which: ZLR compliance gap tests | 2 (test_system4_v1.py) |
| Of which: ZLR classification tests | 1 (test_a6.py) |
| Files mentioning ZLR as data (not ZLR-specific tests) | 7 |

### Reconciliation with prior claims

| Claim | Claimed | Actual | Verdict |
|---|---|---|---|
| P-W3 "39 ZLR tests" | 39 | 17 | **INFLATED.** 39 likely counted every file that mentions `ZLR`, including non-test mentions and files using ZLR as fixture data. |
| W-0 "8 ZLR tests" | 8 | 17 | **UNDERCOUNTED.** 8 matches only `test_woodies_patterns.py -k zlr` (the 8 that pytest selects with `-k zlr` in that one file). Missed test_woodies.py (3), test_atr_stop.py (3), test_system4_v1.py (2), test_a6.py (1). |

---

## 2. Per-Test Classification Table

### Key for classification

- **PASSING** -- test passes, CCI sequence is doctrinally sound
- **PASSING-WEAK** -- test passes, but CCI sequence does not meet full Liran Stage-1 doctrine (max CCI only 120-130, no bar >+200, <6 consecutive bars above ZL)
- **FIXTURE_BUG** -- test passes but fixture is doctrinally incorrect
- **DETECTOR_BUG** -- detector logic causes wrong result
- **SPEC_DRIFT** -- test asserts something that contradicts current spec
- **NOT_ZLR_DETECTOR** -- test uses ZLR as input data but tests a different subsystem

### All 17 ZLR tests

| # | File | Test name | Line | CCI sequence | Max CCI | Bars >ZL | Bars >+100 | Bars >+200 | Status | Classification |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | test_woodies_patterns.py | `test_zlr_up_detected` | 91 | `[0]*5 + [120,130,110,60,50,40,55,80]` | 130 | 8 (all positive after zeros) | 3 (120,130,110) | 0 | PASS | PASSING-WEAK |
| 2 | test_woodies_patterns.py | `test_zlr_down_detected` | 105 | `[0]*5 + [-120,-130,-110,-60,-50,-40,-55,-80]` | -130 (abs) | 8 below ZL | 3 | 0 | PASS | PASSING-WEAK |
| 3 | test_woodies_patterns.py | `test_zlr_no_signal_flat` | 114 | `[0]*15` | 0 | 0 | 0 | 0 | PASS | PASSING |
| 4 | test_woodies_patterns.py | `test_zlr_insufficient_data` | 120 | `[50,60]` | 60 | 2 | 0 | 0 | PASS | PASSING |
| 5 | test_woodies_patterns.py | `test_zlr_confidence_range` | 125 | `[0]*5 + [120,130,110,60,50,40,55,80]` | 130 | 8 | 3 | 0 | PASS | PASSING-WEAK |
| 6 | test_woodies_patterns.py | `test_zlr_details_present` | 131 | `[0]*5 + [120,130,110,60,50,40,55,80]` | 130 | 8 | 3 | 0 | PASS | PASSING-WEAK |
| 7 | test_woodies_patterns.py | `test_zlr_detected_via_all` | 522 | `[0]*5 + [120,130,110,60,50,40,55,80]` | 130 | 8 | 3 | 0 | PASS | PASSING-WEAK |
| 8 | test_woodies_patterns.py | `test_legacy_zlr` | 565 | `[0]*5 + [120,130,110,60,50,40,55,80]` | 130 | 8 | 3 | 0 | PASS | PASSING-WEAK |
| 9 | test_woodies.py | `test_zlr_up` | 163 | `[0]*5 + [120,130,110,60,50,40,55,80]` | 130 | 8 | 3 | 0 | PASS | PASSING-WEAK |
| 10 | test_woodies.py | `test_zlr_down` | 171 | `[0]*5 + [-120,-130,-110,-60,-50,-40,-55,-80]` | -130 (abs) | 8 | 3 | 0 | PASS | PASSING-WEAK |
| 11 | test_woodies.py | `test_zlr_no_signal` | 177 | `[0]*15` | 0 | 0 | 0 | 0 | PASS | PASSING |
| 12 | test_atr_stop.py | `test_zlr_long_normal_vol_cap_hit` | 27 | N/A (tests stop calc, not detection) | N/A | N/A | N/A | N/A | PASS | NOT_ZLR_DETECTOR |
| 13 | test_atr_stop.py | `test_zlr_long_low_vol_cap_clamps` | 46 | N/A | N/A | N/A | N/A | N/A | PASS | NOT_ZLR_DETECTOR |
| 14 | test_atr_stop.py | `test_zlr_short_normal_vol` | 62 | N/A | N/A | N/A | N/A | N/A | PASS | NOT_ZLR_DETECTOR |
| 15 | test_system4_v1.py | `test_zlr_detected_in_studies` | 38 | N/A (tests compute_all_studies output keys) | N/A | N/A | N/A | N/A | PASS | NOT_ZLR_DETECTOR |
| 16 | test_system4_v1.py | `test_zlr_direction_in_studies` | 58 | N/A (tests compute_all_studies output keys) | N/A | N/A | N/A | N/A | PASS | NOT_ZLR_DETECTOR |
| 17 | test_a6.py | `test_zlr_is_initiative` | 59 | N/A (tests entry classification) | N/A | N/A | N/A | N/A | PASS | NOT_ZLR_DETECTOR |

### Summary

| Classification | Count | Tests |
|---|---|---|
| PASSING (negative/edge) | 2 | #3, #11 |
| PASSING-WEAK (detect positive but doctrinally weak fixtures) | 8 | #1, #2, #5, #6, #7, #8, #9, #10 |
| NOT_ZLR_DETECTOR (tests other subsystem) | 7 | #12-17 |
| FIXTURE_BUG | 0 | -- |
| DETECTOR_BUG | 0 | -- |
| SPEC_DRIFT | 0 | -- |

**All 17 tests PASS.** Zero failures.

---

## 3. Fixture Chunk Evidence

### 3a. Inline test fixtures (test_woodies_patterns.py, test_woodies.py)

All 8 positive ZLR detection tests use the **same CCI sequence**:

```
[0, 0, 0, 0, 0, 120, 130, 110, 60, 50, 40, 55, 80]
```

**Analysis against Liran Stage-1 doctrine:**

| Criterion | Required | Actual | Verdict |
|---|---|---|---|
| Bars consecutively above/below ZL | >=6 | 8 (indices 5-12 are all positive) | PASS |
| At least 1 bar >= +100 | Yes | 3 bars (120, 130, 110) | PASS |
| At least 1 bar >= +200 (ideal) | Ideal | 0 bars | WEAK -- max is 130 |
| Pullback stays within bounds | -100 < CCI < +100 | Yes (60,50,40 are in bounds) | PASS |
| Bounce (current > prev) | Yes | 80 > 55 | PASS |
| trend_state checked | Per doctrine | No -- make_bars_from_cci defaults to "GRAY" | WEAK |

**Key finding:** The CCI sequence technically satisfies the detector's Stage-1 threshold (`cci >= 100`), but barely. The maximum CCI of 130 is far below the 200+ ideal. This means the tests prove the detector *works* at minimum thresholds but do not cover strong-trend ZLR scenarios. The `trend_state="GRAY"` default means these tests bypass any trend-state gating.

### 3b. E2E fixture generator (woodies_bar_sequences.py)

**File:** `backend/v9/tests/integration/fixtures/woodies_bar_sequences.py`

```python
# Lines 12-31
def generate_trend_blue_sequence(bars=30, base_price=7400.0):
    """Scenario 1: CCI sustained positive (BLUE trend) -> ZLR pattern.

    30 bars with CCI > 0, creating BLUE color for strategic gate.
    """
    result = []
    for i in range(bars):
        cci = 50 + (i * 2)  # steadily rising CCI above zero
        result.append(WoodiesBar(
            ts=1000.0 + i * 1800,
            open=base_price + i * 0.5,
            high=base_price + i * 0.5 + 3,
            low=base_price + i * 0.5 - 2,
            close=base_price + i * 0.5 + 1,
            cci_14=cci,
            cci_6_tcci=cci * 0.9,
            ema_34=base_price + i * 0.3,
            trend_state="BLUE",
        ))
    return result
```

**Analysis:**

| Criterion | Value |
|---|---|
| CCI range | 50 to 108 (50 + 29*2) |
| Bars > +100 | 5 (bars 25-29: CCI 100,102,104,106,108) |
| Bars > +200 | 0 |
| Max CCI | 108 |
| Pullback pattern | None -- CCI is monotonically increasing |
| ZLR shape | **NO** -- this is a steadily rising CCI, not a pull-back-and-bounce |

**Verdict:** This fixture is labeled "ZLR pattern" in its docstring but does NOT produce a ZLR-shaped CCI trajectory. It generates a monotonic ramp. It is used for E2E flow tests (Scenario 1), not for ZLR detection testing. **Misleading docstring, but not a test bug** since no test asserts ZLR detection from this fixture.

### 3c. Git history of fixture file

```
5a37092 2026-05-16 feat(woodies): full E2E flow - 5 scenarios - entry to terminal (PROMPT 4 - 4.3)
```

Single commit, dated 2026-05-16. This is **after** the April 2026 Stage-1 doctrine. The Caveat #7 hypothesis (fixtures predate doctrine) is **REFUTED** -- the fixture was created in May 2026. However, the fixture's docstring claiming "ZLR pattern" is misleading regardless of date.

---

## 4. Root Cause Summary Table

| Issue ID | Category | Description | Severity | Affects test correctness? |
|---|---|---|---|---|
| RC-1 | FIXTURE_WEAKNESS | All positive ZLR tests use identical CCI `[0]*5+[120,130,110,60,50,40,55,80]` with max=130. No test covers strong-trend (CCI>200) ZLR. | LOW | No -- tests pass and are technically correct, but coverage is thin |
| RC-2 | FIXTURE_WEAKNESS | All positive ZLR tests use `trend_state="GRAY"` (the `make_bars_from_cci` default). No test verifies ZLR in BLUE/RED trend context. | LOW | No -- the detector (`zlr.py`) does not check trend_state, so this is consistent |
| RC-3 | DETECTOR_GAP | `zlr.py` does not check `trend_state` at all. Liran doctrine says ZLR is a continuation pattern requiring established trend (BLUE/RED). Detector fires on GRAY. | MEDIUM | Not a test bug -- it's a detector design choice that may need future tightening |
| RC-4 | DOCSTRING_MISLEADING | `generate_trend_blue_sequence` docstring says "ZLR pattern" but produces monotonic CCI ramp, not a ZLR pullback-bounce shape | LOW | No -- no test uses this fixture to assert ZLR detection |
| RC-5 | TEST_DUPLICATION | test_woodies.py tests #9-11 are exact duplicates of test_woodies_patterns.py tests #1-2,#3 (same CCI, same assertions via legacy API) | LOW | No -- redundancy is harmless |
| RC-6 | COUNT_DISCREPANCY | Prior claims of "39 tests" and "8 tests" are both wrong. Actual: 17 ZLR test functions (11 detector, 6 non-detector). | INFO | Historical confusion only |

---

## 5. Recommended Step 2 Plan

### Priority 1: Add strong-trend ZLR test fixtures

- Add a CCI sequence with max > 200 (e.g., `[0]*5 + [150, 220, 180, 60, 40, 30, 50, 75]`)
- Add a CCI sequence with `trend_state="BLUE"` for LONG and `trend_state="RED"` for SHORT
- These tests should PASS with the current detector (it does not gate on trend_state)

### Priority 2: Decide on trend_state gating in detector

- `zlr.py` ignores `trend_state`. If Liran doctrine requires BLUE/RED trend for ZLR, a gate should be added.
- If the gate is added, a negative test (`trend_state="GRAY"` should NOT detect ZLR) must follow.
- **This is a design decision for Michael**, not an automatic fix.

### Priority 3: Fix misleading docstring

- `generate_trend_blue_sequence` docstring should say "sustained BLUE trend" not "ZLR pattern"

### Priority 4: De-duplicate test_woodies.py ZLR tests

- tests/v9/systems/test_woodies.py::TestZLR duplicates test_woodies_patterns.py::TestZLR
- Consider removing the older test_woodies.py versions or marking them as legacy-compat

---

## 6. Findings Outside W-5 Scope

### 6a. Dedup tests are NOT ZLR-related failures

`tests/v9/systems/test_woodies_dedup.py` -- all 5 tests **PASS** (verified 2026-05-26). The file tests bar-timestamp deduplication logic, not ZLR detection. It uses `ZLR_SHORT` as a dictionary key in one test (`test_dedup_key_per_pattern_direction`) but this is just string data. **No asyncio event loop issues observed** -- all 5 pass cleanly.

### 6b. Compliance gap tests (test_system4_v1.py) pass

The two ZLR compliance tests (`test_zlr_detected_in_studies`, `test_zlr_direction_in_studies`) both **PASS**, meaning `compute_all_studies` now returns `zlr_detected` and `zlr_direction` keys. These were originally written as expected-failure gap tests but the gaps have been closed.

### 6c. All 17 ZLR tests pass (zero failures)

```
test_woodies_patterns.py -k zlr:  8 passed
test_woodies.py::TestZLR:         3 passed
test_atr_stop.py -k zlr:          3 passed
test_system4_v1.py -k zlr:        2 passed
test_a6.py::test_zlr_is_initiative: 1 passed
                            Total: 17 passed, 0 failed
```

### 6d. Detector architecture note

`zlr.py` uses a 12-bar lookback (`LOOKBACK = 12`). The Stage-1 check threshold is `cci >= 100` (line 39) for UP and `cci <= -100` (line 71) for DOWN. The Stage-2 pullback check correctly bounds CCI within (-100, +100]. The Stage-3 bounce check requires `current > prev` (UP) or `current < prev` (DOWN) plus `0 < current < 200` bounds. This is self-consistent but does not enforce minimum trend duration (6+ bars above ZL) as a separate check -- it relies on the 12-bar window implicitly.
