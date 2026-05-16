# Spec Compliance — COMMIT 5.1 (ZLR + HFE Test Failures Fix)

## ZLR Test Failures (8 resolved)

### ZLR Failure #1 · test_zlr_up (test_woodies.py:162)
- Expected: ZLR UP detected with CCI peaks of 120-130
- Actual: None returned (not detected)
- Root cause: SPEC_DRIFT — zlr.py required CCI >= 200 (HFE territory), but DTV1 § A3 ZLR needs CCI >= 100
- Fix: Changed Stage 1 threshold from 200 to 100 in detect() and detect_zlr()
- Reference: Decision Tree V1 § A3: "CCI approaches ZL from trend side"
- Status: ✅ resolved

### ZLR Failure #2 · test_zlr_down (test_woodies.py:170)
- Same root cause as #1 (mirror: -200 → -100)
- Status: ✅ resolved

### ZLR Failure #3-6 · test_zlr_up_detected, down_detected, confidence_range, details_present
- Same root cause: CCI >= 200 threshold too strict
- Status: ✅ resolved (all use same test data with CCI peaks 120-130)

### ZLR Failure #7 · test_zlr_detected_via_all (test_woodies_patterns.py:527)
- ZLR not detecting → detect_all_patterns returned empty for ZLR data
- Status: ✅ resolved (ZLR now detects with lower threshold)

### ZLR Failure #8 · test_legacy_zlr (test_woodies_patterns.py:569)
- Legacy detect_zlr() had same 200 threshold
- Status: ✅ resolved

## Pattern Count Fix (3 resolved)

### test_all_8_detectors_registered → test_all_9_detectors_registered
- Root cause: TEST_DRIFT — test still expected 8 patterns, but HFE was added in PROMPT 1
- Fix: Updated assertion from 8 to 9
- Status: ✅ resolved

### test_pattern_ids_complete
- Root cause: TEST_DRIFT — expected set missing "HFE"
- Fix: Added "HFE" to expected set
- Status: ✅ resolved

### test_continuation_vs_reversal
- Root cause: TEST_DRIFT — expected 4 reversal, now 5 (includes HFE)
- Fix: Updated REVERSAL count from 4 to 5
- Status: ✅ resolved

## HFE Edge Case Fix (3 resolved)

### test_no_hfe_when_no_extreme, test_no_hfe_when_no_hook, test_no_hfe_insufficient_bars
- Root cause: hfe.py returned None for non-detection, but pattern contract is PatternResult(detected=False)
- Fix: Changed `return None` to `return PatternResult(detected=False, pattern_id="HFE")`
- Updated test assertions from `is None` to `.detected is False`
- Status: ✅ resolved

## Summary
- Total resolved: 14 failures (8 ZLR + 3 pattern count + 3 HFE edge case)
- Baseline: 25 → 12 failures (all remaining are pre-existing non-Woodies)
- Regressions: 0

Status: 14/14 ✅ · 0 deferred · 0 missing
