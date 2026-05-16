# Spec Compliance — COMMIT 3.2 (A1 + A3 + A6 Core Entry Logic)

## Stage A1 — Strategic Gate
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A1

Spec items:
- ✅ CCI 14 > 0 for 6+ consecutive bars → BLUE → LONG → `a1_strategic_gate.py:65` (consecutive_above >= BARS_PERSISTENCE_REQUIRED)
- ✅ CCI 14 < 0 for 6+ consecutive bars → RED → SHORT → `a1_strategic_gate.py:70`
- ✅ Frequent zero-line crosses → GREY → wait → `a1_strategic_gate.py:62` (crosses >= FREQUENT_CROSS_THRESHOLD)
- ✅ Sustained trend → opposite → YELLOW → stand aside → `a1_strategic_gate.py:67,72` (_was_opposite_trend)
- ✅ Else → INDETERMINATE → wait → `a1_strategic_gate.py:76`
- ✅ Outputs: direction_allowed (LONG/SHORT/NONE) + color → `a1_strategic_gate.py:17`
- ✅ Terminal: SKIP color veto (GREY/YELLOW/INDETERMINATE → NONE) → `test_a1.py:87-98`
- ✅ Configurable persistence threshold (6 bars) → `a1_strategic_gate.py:12` (BARS_PERSISTENCE_REQUIRED)
- ✅ No scoring/weighting (RULE 13) → binary color determination only

Terminal states emitted: SKIP (via direction_allowed="NONE") ✅ matches § Section 6
Inputs schema: ✅ cci_14_value, cci_14_history, zero_line — matches spec
Outputs schema: ✅ A1Output(direction_allowed, color) — matches spec

Status: 9/9 ✅ · 0 deferred · 0 missing

---

## Stage A3 — Pattern Detection
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A3

Spec items:
- ✅ 9 patterns scanned via pattern_engine → `a3_pattern_detection.py:56` (detect_all_patterns)
- ✅ Trend-Confirming (ZLR, TT, TLB, GB100) require BLUE/RED → `a3_pattern_detection.py:68-70`
- ✅ New-Trend (VEGAS, GHOST, FAMIR, HTLB, HFE) allowed in any state → `a3_pattern_detection.py:67`
- ✅ Return first match or NONE → `a3_pattern_detection.py:76`
- ✅ Outputs: pattern_matched, pattern_category, pattern_direction → `a3_pattern_detection.py:24-27`
- ✅ Terminal: WAIT (no pattern → NONE) → `test_a3.py:30-41`
- ✅ Uses existing patterns/ modules (not new code) → import from pattern_engine
- ✅ No scoring (RULE 13) → binary match/no-match

Terminal states emitted: WAIT (via pattern_matched="NONE") ✅ matches § Section 6
Inputs schema: ✅ bars (WoodiesBar list), color, context — matches spec
Outputs schema: ✅ A3Output(pattern_matched, pattern_category, pattern_direction) — matches spec

Status: 8/8 ✅ · 0 deferred · 0 missing

---

## Stage A6 — Entry Classification
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A6

Spec items:
- ✅ HFE/FAMIR/TT → REACTIVE → `a6_entry_classification.py:11` (REACTIVE_PATTERNS)
- ✅ VEGAS/GHOST/TLB/HTLB/ZLR/GB100 → INITIATIVE → `a6_entry_classification.py:12` (INITIATIVE_PATTERNS)
- ✅ A4 hint can confirm but NOT override → `a6_entry_classification.py:55-59` (only used for unknown patterns)
- ✅ Pattern wins on conflict → `test_a6.py:73-86` (pattern_hfe_overrides_initiative_hint)
- ✅ REACTIVE: size=2, TIGHT → `a6_entry_classification.py:72-76`
- ✅ INITIATIVE: size=3, WIDE → `a6_entry_classification.py:77-80`
- ✅ All 9 patterns classified → `test_a6.py:103-106` (REACTIVE ∪ INITIATIVE = 9)
- ✅ No scoring (RULE 13) → binary classification only

Terminal states emitted: None (continues to A7) ✅ matches spec
Inputs schema: ✅ pattern_matched, entry_classification_hint, direction — matches spec
Outputs schema: ✅ A6Output(entry_classification, position_size, management_profile) — matches spec

Status: 8/8 ✅ · 0 deferred · 0 missing

---

## Total: 25/25 ✅ · 0 deferred · 0 missing
