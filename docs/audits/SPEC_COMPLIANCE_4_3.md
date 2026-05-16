# Spec Compliance — COMMIT 4.3 (Full E2E Flow · 5 Scenarios)

## 5 E2E Scenarios
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Sections 4-6

### Scenario 1 — Trend BLUE → T1 → T2 → trail → SUCCESS_TRAIL
- ✅ A1 BLUE + LONG direction → `test:77-82`
- ✅ A7 approves with defaults → `test:85-86`
- ✅ B10 T1 → CLOSE_C1, NO BE (D-002) → `test:89-94`
- ✅ B11 T2 INITIATIVE → CLOSE_C2 + Smart BE (D-055) → `test:97-103`
- ✅ B13 trail → CLOSE_C3 → `test:106-110`
- ✅ Terminal emission: BUY + SUCCESS_TRAIL → `test:113-120`
- ✅ Bridge: submit + close_contracts → `test:122-134`

### Scenario 2 — Trend RED → STOP_LOSS
- ✅ A1 RED + SHORT → `test:143-148`
- ✅ B1 stop hit → CLOSE_ALL → `test:150-154`
- ✅ Terminal: STOP_LOSS emitted → `test:156-159`
- ✅ Bridge: close_all → `test:161-163`

### Scenario 3 — Color flip → STRATEGIC_EXIT
- ✅ B3 BLUE→RED flip detected → `test:171-175`
- ✅ Dispatcher: STRATEGIC_EXIT wins → `test:177-183`
- ✅ Terminal: STRATEGIC_EXIT emitted → `test:185-188`

### Scenario 4 — News window → NEWS_EXIT
- ✅ B6 Tier 1 within 5min → CLOSE_ALL → `test:196-201`
- ✅ Dispatcher: ABSOLUTE wins over TARGET → `test:203-209`
- ✅ Terminal: NEWS_EXIT emitted → `test:211-214`

### Scenario 5 — EOD force → EOD_FORCE
- ✅ B2 15:58 → no trigger → `test:222-224`
- ✅ B2 15:59 → CLOSE_ALL → `test:226-229`
- ✅ Terminal: EOD_FORCE emitted → `test:231-234`
- ✅ D-002 no overnight noted → `test:233`

### Cross-scenario
- ✅ All 5 scenarios emit distinct terminal states → `test:242-252`

Status: 22/22 ✅ · 0 deferred · 0 missing
