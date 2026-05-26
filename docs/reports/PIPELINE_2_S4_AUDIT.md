# Pipeline 2 · S4 Codebase Audit Report

**Package:** W-0
**Date:** 2026-05-26
**Author:** Claude Code (CC)
**Spec authority:** D-092 LOCKED 2026-05-23 + INTAKE v2 LOCKED 2026-05-25 16:50 + DTV1 v1.0

---

## §3.1 · Per-pattern table (9 rows)

| pattern_id | file | LOC | uses_dll | uses_python_fallback | confidence_formula | confidence_type | formula_matches_registry | referenced_anti_patterns | day_type_sensitivity_comments |
|---|---|---|---|---|---|---|---|---|---|
| ZLR | `patterns/zlr.py` | 147 | NO | NO (Python-only) | `min(0.9, 0.5 + current / 400)` (line 54 LONG) · `min(0.9, 0.5 + abs(current) / 400)` (line 85 SHORT) | dynamic | ⚠️ PARTIAL — LONG matches registry `min(0.9, 0.5 + cci/400)`. SHORT uses `abs(current)` — semantically equivalent but literally differs. | AP1: IMPLICIT — `LOOKBACK = 12` (line 13) bounds scan window to 12 bars, implicitly preventing >12-bar pullback detection. No explicit rejection guard. | NONE |
| TLB | `patterns/tlb.py` | 130 | NO | NO | `min(0.85, 0.4 + abs(current - predicted) / 200)` (line 61) | dynamic | ✅ MATCH | NONE | NONE |
| TT | `patterns/tt.py` | 129 | NO | NO | `0.7` (line 49) | fixed | ✅ MATCH | AP7: PARTIAL — code uses `cci6 > cci14 + 5` (line 40) as detection condition, not as rejection guard. Gap < 5 prevents detection but is not an explicit AP check. | NONE |
| GB100 | `patterns/gb100.py` | 106 | NO | NO | `min(0.85, 0.5 + (current - 100) / 200)` (line 40 LONG) · `min(0.85, 0.5 + (abs(current) - 100) / 200)` (line 62 SHORT) | dynamic | ⚠️ PARTIAL — LONG matches. SHORT uses `abs(current)` — semantically correct, literally differs. | AP2: IMPLICIT — requires `trend == "BLUE"` (line 33) / `"RED"` (line 55), excludes YELLOW implicitly. No explicit YELLOW rejection. AP6: MISSING — no bars-opposite-zero-line counting. | NONE |
| VEGAS | `patterns/vegas.py` | 158 | NO | NO | `0.75` (line 71) | fixed | ✅ MATCH | AP3: MISSING — `_find_swings` uses `min_swing=2` (lines 50-51), no guard for 5+ bars between swings. | NONE |
| GHOST | `patterns/ghost.py` | 139 | NO | NO | `0.7` (line 56) | fixed | ✅ MATCH | NONE | NONE |
| FAMIR | `patterns/famir.py` | 118 | NO | NO | `min(0.8, 0.5 + (THRESHOLD - max_recent) / 100)` (line 43, `THRESHOLD=200`) | dynamic | ✅ MATCH | AP9: MISSING — no LSMA field read or checked anywhere in file. | NONE |
| HTLB | `patterns/htlb.py` | 141 | NO | NO | `0.65` (line 68) | fixed | ✅ MATCH | AP4: PRESENT — `MIN_TOUCHES = 2` (line 15), checked at line 43 `if touches >= MIN_TOUCHES`. Detection gate, not labeled as AP. | NONE |
| HFE | `patterns/hfe.py` | 149 | YES — reads `hfe_detected`, `hfe_direction`, `hfe_extreme_bars_ago` (lines 46-48) | YES — Python fallback at line 75+ | DLL: `0.7` (line 61, FIXED) · Python: `min(0.8, 0.5 + hook_distance / 400)` (line 100, DYNAMIC) | MIXED | ❌ MISMATCH on DLL path — registry says `min(0.8, 0.5 + hook/400)` but DLL path uses hardcoded `0.7`. Python fallback MATCHES. | AP5: PRESENT in Python fallback only — `2 <= bars_since_extreme <= LOOKBACK` (line 90). DLL path does NOT validate range. | NONE |

### Pattern file summary
- Total LOC: 1,217 across 9 detectors
- DLL dependency: HFE only (1/9)
- day_type references: ZERO across all 9 files
- Legacy interface gap: HFE has no `detect_hfe()` legacy function — excluded from `ALL_DETECTORS` (8 entries), present only in `ALL_PATTERN_DETECTORS` (9 entries) per `patterns/__init__.py`

---

## §3.2 · Per-stage table (21 rows)

| stage_id | file | LOC | is_touch_point | priority_class | gateway_TODOs_found | wires_correctly_to_pattern_engine |
|---|---|---|---|---|---|---|
| A1 | `stages/a1_strategic_gate.py` | 129 | NO | Entry (gate/veto) | NONE | NO — standalone CCI-14 zero-line logic; correct (runs before detection) |
| A2 | `stages/a2_day_type_query.py` | 68 | **YES** | Entry (advisory) | NONE | NO — maps day-type string to pattern-preference via local `PATTERN_PREFERENCES` dict (line 16-34); correct (advisory only) |
| A3 | `stages/a3_pattern_detection.py` | 96 | NO | Entry (detection) | NONE | **YES** — imports `detect_all_patterns`, `CONTINUATION_PATTERNS`, `REVERSAL_PATTERNS` from `pattern_engine` (lines 11-14), calls `detect_all_patterns(bars, context)` at line 64, filters by color compatibility (lines 74-90) |
| A4 | `stages/a4_poc_suffering_query.py` | 107 | **YES** | Entry (advisory) | NONE | NO — POC/suffering query; correct |
| A5 | `stages/a5_otf_clarity_query.py` | 72 | **YES** | Entry (advisory) | NONE | NO — OTF clarity query; correct |
| A6 | `stages/a6_entry_classification.py` | 78 | NO | Entry (classification) | NONE | INDIRECT — uses `pattern_matched` string from A3 to classify via local `REACTIVE_PATTERNS` / `INITIATIVE_PATTERNS` sets (lines 12-13) |
| A7 | `stages/a7_universal_checks.py` | 93 | NO | Entry (gate/veto) | NONE | NO — safety checks (news/cooldown/cap/stop/bridge/EOD); correct |
| B1 | `stages/b1_stop_check.py` | 43 | NO | ABSOLUTE_EXIT (line 28) | NONE | NO — pure price vs stop; correct |
| B2 | `stages/b2_eod_check.py` | 50 | NO | ABSOLUTE_EXIT (line 30) | NONE | NO — time-only; correct |
| B3 | `stages/b3_color_flip.py` | 55 | NO | STRATEGIC_EXIT (line 30) | NONE | NO — color comparison; correct |
| B4 | `stages/b4_poc_migration_query.py` | 69 | **YES** | ADVISORY_EXIT (line 35) | NONE | NO — POC advisory; correct |
| B5 | `stages/b5_otf_mid_trade_query.py` | 51 | **YES** | ADVISORY_EXIT (line 34) | NONE | NO — OTF advisory; correct |
| B6 | `stages/b6_news_window.py` | 53 | NO | ABSOLUTE_EXIT (line 31) | NONE | NO — news calendar; correct |
| B7 | `stages/b7_time_stop.py` | 48 | NO | TIME_EXIT (line 31) | NONE | NO — elapsed time; correct |
| B8 | `stages/b8_counter_pattern.py` | 75 | NO | TIGHTEN (line 39) | NONE | **YES** — imports `detect_all_patterns`, `REVERSAL_PATTERNS` from `pattern_engine` (line 12). Note: `REVERSAL_PATTERNS` import is **UNUSED** — stage uses local `COUNTER_PATTERN_IDS` set (line 25) instead. |
| B9 | `stages/b9_market_state_query.py` | 57 | **YES** | PARTIAL (line 36) | NONE | NO — market state advisory; correct |
| B10 | `stages/b10_t1_milestone.py` | 56 | NO | TARGET (line 31) | NONE | NO — price vs T1; correct |
| B11 | `stages/b11_t2_milestone.py` | 58 | NO | TARGET (line 28) | NONE | NO — price vs T2; correct |
| B12 | `stages/b12_t3_milestone.py` | 46 | NO | TARGET (line 27) | NONE | NO — price vs T3; correct |
| B13 | `stages/b13_trail_check.py` | 57 | NO | TRAIL (line 31) | NONE | NO — EMA-169 trail; correct |
| B14 | `stages/b14_hold.py` | 31 | NO | NO_ACTION (line 27) | NONE | NO — default no-op; correct |

### Stage summary
- Total LOC: 1,399 across 21 stages + `__init__.py` (7 LOC)
- Touch-points: 6/21 (A2, A4, A5, B4, B5, B9) — all correctly `Blocking: false`
- Pattern engine wiring: A3 (primary detection) + B8 (counter-pattern scan)
- TODOs/FIXMEs: ZERO across all 22 files
- Issues: B8 unused `REVERSAL_PATTERNS` import; B9 doc says "EXTENDING" but code checks `"EXPANDING"` (line 52)

---

## §3.3 · Cross-cut analysis

### (a) ATR-14 calculation: does it exist anywhere?

**In `backend/v9/systems/woodies/`:**
- `atr_stop.py` — W-1 greenfield module (created 2026-05-26). Receives `atr_14` as parameter (in ticks). Does NOT compute ATR-14 — the caller must provide it. Classification: **KEEP** (W-1 deliverable).
- No other ATR-14 computation exists in `woodies/`.

**In `backend/v9/systems/five_min/`:**
- `atr_caps.py:101` — `compute_continuous_atr14()` using Wilder's smoothing. S2-specific. Classification: S2-specific, not directly reusable by S4 `compute_stop()` since S4 expects `atr_14` in ticks.
- `adaptive_stop.py:44-46` — S2-specific stop using ATR-14.

**In `backend/v9/services/`:**
- `trail_engine.py:29,336` — imports `compute_continuous_atr14` from `five_min.atr_caps` for chandelier trail (Layer 2). Cross-system shared dependency.

**In `backend/v9/shared/`:**
- No ATR/indicator utility module exists.

**Conclusion:** W-1 is correctly greenfield. No ATR-14 calc existed in `woodies/` before W-1. The S2 `compute_continuous_atr14()` in `five_min/atr_caps.py` could be imported by the W-6 caller to supply the `atr_14` parameter to `compute_stop()`, but the stop engine itself is independent.

### (b) Day-Type Matrix — touched anywhere?

**In `woodies/`:**
- `stages/a2_day_type_query.py:16-34` — `PATTERN_PREFERENCES` dict maps 6 day-types to pattern preference lists. `VOLATILITY_EXPECTATIONS` dict maps day-types to vol expectations. Advisory only, never vetoes.
- `decision_tree.py:113` — fetches day_type from `http://localhost:8000/api/v9/day_type/v9/current` for touch-point context.
- `decision_tree.py:235,271-275,308-312` — touch-point advisory context includes day_type.
- `entry_phase.py:25,54,99` — imports and maps `A2DayTypeQuery` stage.
- `yaml_loader.py:39` — loads `A2_day_type_query` from YAML config.

**63-cell matrix (7 DayTypes × 9 Patterns):**
- Does **NOT** exist as a single encoded structure anywhere in the codebase.
- `backend/v9/systems/day_type/decision_matrix.py` has a `DECISION_MATRIX` with 18 cells (6 OpeningTypes × 3 IBWidths → DayType). This is S1 day-type classification, not the S4 pattern-gate matrix.
- `a2_day_type_query.py` has a partial mapping (6 day-types → pattern lists) but it is advisory, not a gate.
- **W-3 must build the 63-cell gate from scratch** using Sheet B as source of truth.

### (c) Anti-patterns — checked anywhere?

| AP | Trigger | File | Status | Evidence |
|---|---|---|---|---|
| AP1 | ZLR after >12-bar pullback | `zlr.py` | **IMPLICIT** | `LOOKBACK = 12` (line 13) bounds scan window. Prevents detection beyond 12 bars but no explicit rejection guard or logging. |
| AP2 | GB100 in YELLOW state | `gb100.py` | **IMPLICIT** | Requires `trend == "BLUE"` (line 33) / `"RED"` (line 55). Excludes YELLOW implicitly. No explicit YELLOW rejection guard. |
| AP3 | VEGAS without 5+ bars between swings | `vegas.py` | **MISSING** | `_find_swings` uses `min_swing=2` (lines 50-51). No 5+ bar guard. |
| AP4 | HTLB with <2 touches | `htlb.py` | **PRESENT** | `MIN_TOUCHES = 2` (line 15), checked at line 43. |
| AP5 | HFE bars_since_extreme ∉ [2,12] | `hfe.py` | **PARTIAL** | Present in Python fallback (line 90: `2 <= bars_since_extreme <= LOOKBACK`). DLL path does NOT validate. |
| AP6 | GB100 >6 bars opposite ZL during pullback | `gb100.py` | **MISSING** | No bars-opposite-zero-line counting. |
| AP7 | TT with TCCI gap < 5 | `tt.py` | **IMPLICIT** | Gap threshold used as detection condition (lines 39-40, 65-66), not as rejection guard. |
| AP8 | Any pattern when CCI flat (range < 50) ≥3 bars | ALL | **MISSING** | No file implements this check. |
| AP9 | FAMIR without LSMA agreement | `famir.py` | **MISSING** | No LSMA field read or checked. |

**Summary:** 2/9 fully present (AP4, AP5-Python), 3/9 implicit (AP1, AP2, AP7), 4/9 completely missing (AP3, AP6, AP8, AP9). AP5 partially missing (DLL path). **W-7 must implement all 9 as explicit gates.**

### (d) Confidence normalization status

**Dispatcher (`dispatcher.py`):**
The `Dispatcher` class (104 LOC) resolves B-stage priority conflicts using `PriorityClass` (IntEnum 1-9, lines 21-31). It does **NOT** compare pattern confidences. It sorts `StageOutput` objects by `(priority_class, yaml_order)` — winner is lowest priority number (line 96). This is stage-level dispatch, not pattern-level.

**Pattern confidence comparison (`woodies_system.py:232`):**
```python
best = max(patterns, key=lambda p: p.confidence)
```
Raw confidence values (0.0-1.0) compared directly via `max()`. **No normalization.** 5 dynamic formulas produce values in different ranges (ZLR ≤0.9, TLB ≤0.85, GB100 ≤0.85, FAMIR ≤0.8, HFE ≤0.8) while 4 fixed values (TT=0.7, VEGAS=0.75, GHOST=0.7, HTLB=0.65) create a bias: a mediocre dynamic ZLR (e.g., 0.76) beats VEGAS (0.75 fixed) regardless of pattern quality.

**R_t1:** Not computed anywhere. Does not exist in the codebase. Per P-W8 v2 LOCK, W-6 will add R_t1 emission and W-8 will use two-tier R_t1 dispatch.

**Conclusion:** Current state = raw `max(confidence)` with no normalization. W-8 will replace with R_t1-based dispatch per P-W8 v2 LOCK.

---

## §3.4 · Drift list

### Seed items (verified against live code)

**Drift #1: `__init__.py` pattern count and timeframe**
```
Location:      backend/v9/systems/woodies/__init__.py:1
Code says:     """System 4: Woodies CCI — 8 patterns on 30-min bars."""
Spec says:     D-092 §Scope: 9 patterns. woodies_system.py uses 5-min bars.
Severity:      MED (stale docstring · does not affect runtime · but misleading)
W-X to fix:    W-6 (patterns refit)
```

**Drift #2: HFE GROUP comment**
```
Location:      backend/v9/systems/woodies/patterns/hfe.py:18
Code says:     GROUP = "REVERSAL"  # NEW_TREND per spec → mapped to REVERSAL group
Spec says:     D-092 calls it "REV". DTV1 uses "NEW_TREND" for the category. REVERSAL is the code-level mapping.
Severity:      LOW (comment is explanatory · runtime GROUP value "REVERSAL" is consistent with other REV patterns)
W-X to fix:    N/A — comment is actually helpful documentation of the mapping decision
```

**Drift #3: Two CCI calc files coexist**
```
Location:      backend/v9/systems/woodies/cci.py (26 LOC) vs cci_calc.py (198 LOC)
Code says:     cci.py is a thin bar-dict interface. cci_calc.py is the canonical full implementation with all 11 studies.
Spec says:     Not explicitly addressed.
Severity:      LOW (no functional conflict · cci.py is a convenience wrapper for bar-dict format)
W-X to fix:    W-6 could consolidate, but not urgent. cci_calc.py is CANONICAL.
```

**Drift #4: Dispatcher priority enum**
```
Location:      backend/v9/systems/woodies/dispatcher.py:21-31
Code says:     9-class PriorityClass IntEnum: ABSOLUTE_EXIT(1) → NO_ACTION(9)
Spec says:     DTV1 + P-W6 v2 define same 9 priority classes.
Severity:      NONE — ✅ matches spec
W-X to fix:    N/A
```

**Drift #5: A1 strategic gate YELLOW handling**
```
Location:      backend/v9/systems/woodies/stages/a1_strategic_gate.py:22,80-82,86-88
Code says:     5 colors: BLUE, RED, GREY, YELLOW, INDETERMINATE (line 22).
               YELLOW returns direction_allowed="NONE" (lines 82, 88).
               GREY spelled "GREY" (not "GRAY" per D-092).
Spec says:     D-092 §Trend State: 4 states BLUE/RED/YELLOW/GRAY.
               P-W5 LOCK A: BLOCK ALL 9 in YELLOW.
Severity:      MED — (1) A1 DOES block YELLOW (direction="NONE") ✅ but
               (2) GREY vs GRAY spelling drift (line 22, 34, 76).
               (3) INDETERMINATE is a 5th color not in D-092's 4-state model.
               (4) The enforcement path (does woodies_system.py honor direction_allowed="NONE"?)
                   needs verification — currently `process_bar` uses `detect_all_patterns` directly
                   (line 213) WITHOUT checking A1 output. The A1 gate only runs inside
                   `decision_tree.evaluate_bar` → `run_pre_fire` (line 375-383).
W-X to fix:    W-2 (Trend State Machine + YELLOW block)
```

**Drift #6: ATR-14 stop engine**
```
Location:      backend/v9/systems/woodies/
Code says:     atr_stop.py exists (W-1 created 2026-05-26). NOT wired to patterns yet.
Spec says:     D-092 §Stop Architecture requires ATR-14 stop engine.
Severity:      NONE — ✅ W-1 delivered the engine. W-6 will wire it.
W-X to fix:    W-6 (wiring)
```

**Drift #7: Day-Type Matrix gate**
```
Location:      N/A — does not exist
Code says:     a2_day_type_query.py has PATTERN_PREFERENCES (advisory, 6 day-types × pattern lists)
               but no 63-cell gate (7 DayTypes × 9 Patterns).
Spec says:     D-092 §Day-Type Matrix: 63 cells, day-type determines which patterns fire/block.
Severity:      HIGH — trading logic gap. Advisory ≠ gate.
W-X to fix:    W-3 (greenfield)
```

**Drift #8: Anti-patterns module**
```
Location:      N/A — no dedicated module
Code says:     AP4 (HTLB touches) and AP5 (HFE bars range, Python only) exist as detection conditions
               inside pattern files. No unified anti-patterns gate.
Spec says:     D-092 §Anti-patterns: 9 anti-patterns (AP1-AP9) must be checked.
Severity:      HIGH — 4/9 completely missing (AP3, AP6, AP8, AP9). Trading logic gap.
W-X to fix:    W-7 (greenfield)
```

**Drift #9: Confidence normalization**
```
Location:      backend/v9/systems/woodies/woodies_system.py:232
Code says:     best = max(patterns, key=lambda p: p.confidence)  # raw max, no normalization
Spec says:     P-W8 v2 LOCK: V1 will use R_t1 for dispatch. Raw confidence is KEEP for SHADOW.
Severity:      MED — current raw max creates bias (fixed values always lose to high-dynamic).
               Per P-W8 v2 LOCK, this is expected current state.
W-X to fix:    W-8 (R_t1 dispatcher)
```

### New drifts found during audit

**Drift #10: pattern_engine.py docstring says "8" but runs 9**
```
Location:      backend/v9/systems/woodies/pattern_engine.py:1,5-7,19,41
Code says:     Docstring: "8 CCI pattern detectors" (line 1). Lists 8 in docstring (lines 5-7).
               _DETECTORS list has 9 entries (lines 20-30). Comment says "All 9" (line 19).
               detect_all_patterns docstring says "all 8" (line 41).
Spec says:     D-092: 9 patterns including HFE.
Severity:      LOW (runtime correct — 9 detectors run · docstrings stale)
W-X to fix:    W-6
```

**Drift #11: woodies_system.py says "8-pattern engine"**
```
Location:      backend/v9/systems/woodies/woodies_system.py:212
Code says:     # Run 8-pattern engine
Spec says:     D-092: 9 patterns.
Severity:      LOW (comment only · runtime calls detect_all_patterns which runs 9)
W-X to fix:    W-6
```

**Drift #12: compliance_manifest.yaml lists only 8 patterns**
```
Location:      backend/v9/systems/woodies/compliance_manifest.yaml
Code says:     8 patterns: ZLR/TLB/TT/GB100 (CONT) + VEGAS/GHOST/FAMIR/HTLB (REV). HFE absent.
Spec says:     D-092: 9 patterns including HFE.
Severity:      MED (compliance tracking gap — HFE not in manifest)
W-X to fix:    W-6
```

**Drift #13: HFE confidence divergence between DLL and Python paths**
```
Location:      backend/v9/systems/woodies/patterns/hfe.py:61 vs line 100
Code says:     DLL path: confidence=0.7 (fixed). Python fallback: min(0.8, 0.5 + hook_distance/400) (dynamic).
Spec says:     Registry §5 (INTAKE v2): min(0.8, 0.5 + hook/400) — matches Python, not DLL.
Severity:      MED — DLL path produces different confidence than registered formula.
               Per P-W2 B LOCK, DLL is primary · Python is audit/fallback. The DLL's fixed 0.7
               may intentionally simplify, but it diverges from the registered formula.
W-X to fix:    W-4 (HFE divergence logger)
```

**Drift #14: entry_phase.py and active_phase.py are dead code**
```
Location:      backend/v9/systems/woodies/entry_phase.py:7-10, active_phase.py:7-10
Code says:     Both explicitly marked "NOT the active runtime path". Return STUB_NOT_IMPLEMENTED.
               Active path is woodies_system.py → decision_tree.evaluate_bar().
Spec says:     DTV1: 21 stages should orchestrate entry and active phases.
Severity:      LOW — stubs exist for future YAML-driven migration. Current runtime works through
               decision_tree.py which evaluates A-stages but delegates all B-stages as DELEGATED.
W-X to fix:    Not in W-0..W-9 scope — architectural decision for post-Pipeline-2.
```

**Drift #15: B-stages all DELEGATED in decision_tree.py**
```
Location:      backend/v9/systems/woodies/decision_tree.py:410-412
Code says:     run_active_trade() returns all 14 B-stages as DELEGATED — never evaluates them.
Spec says:     DTV1: B1-B14 should actively manage trades.
Severity:      MED — B-stage logic exists in individual stage files but is never called by
               the active runtime. Trade management currently relies on external trade_manager.
W-X to fix:    W-9 (LiranExitLadderRule) + post-Pipeline-2 active-phase wiring.
```

**Drift #16: Dual pattern detection paths**
```
Location:      pattern_engine.py (active, WoodiesBar-based) vs detector.py (legacy, parallel-array-based)
Code says:     Two separate detection pipelines exist. detector.py (95 LOC) uses legacy PatternSignal
               interface + ALL_DETECTORS (8 patterns). pattern_engine.py uses PatternResult + 9 patterns.
               api.py uses the legacy detector.py path.
Spec says:     D-092 specifies 9 patterns.
Severity:      MED — api.py endpoint runs only 8 patterns (legacy path). Runtime runs 9 (active path).
W-X to fix:    W-6 (consolidate to single path)
```

**Drift #17: GREY vs GRAY spelling**
```
Location:      stages/a1_strategic_gate.py:22,34,76 uses "GREY"
               schemas.py:26 uses "GRAY" (trend_state default)
               cci_calc.py uses "GRAY"
Code says:     Mixed spelling: "GREY" in A1, "GRAY" in schemas + cci_calc
Spec says:     D-092 says "GRAY"
Severity:      HIGH — if A1 returns "GREY" but downstream checks for "GRAY", the gate fails silently.
               The decision_tree and woodies_system need to handle both or standardize.
W-X to fix:    W-2 (Trend State Machine)
```

---

## §3.5 · Per-package readiness verdict

### W-1 (ATR-14 Stop Engine)
```
Classification:    DEFER → DONE (greenfield delivered 2026-05-26)
Baseline estimate: 1 day CC
Audit-adjusted:    0.5 day CC (completed)
Reason:            Audit confirmed no ATR-14 calc in woodies/. atr_stop.py created.
                   22 tests pass. Pending W-0 retroactive verification (this report).
                   One spec ambiguity documented: floor(4T) > primary_cont(3T) always.
```

### W-2 (Trend State Machine + YELLOW block)
```
Classification:    ADAPT
Baseline estimate: 1 day CC
Audit-adjusted:    1 day CC
Reason:            A1 gate EXISTS and DOES block YELLOW (direction="NONE").
                   Needs: (1) GREY→GRAY spelling fix (Drift #17 · HIGH severity)
                   (2) Verify woodies_system.py respects A1 direction_allowed
                   (3) Remove INDETERMINATE (5th color not in D-092's 4-state model)
                   (4) Potentially move trend state machine from cci_calc.py calc_trend_state
                       to a dedicated module
```

### W-3 (Day-Type Matrix Gate · 63 cells)
```
Classification:    DEFER (greenfield)
Baseline estimate: 1.5 days CC
Audit-adjusted:    1.5 days CC
Reason:            63-cell matrix does NOT exist. a2_day_type_query.py has advisory
                   PATTERN_PREFERENCES (6 day-types × pattern lists) but not a gate.
                   Must encode Sheet B verbatim as 7×9 matrix.
```

### W-4 (HFE divergence logger)
```
Classification:    ADAPT
Baseline estimate: 2 days CC
Audit-adjusted:    1.5 days CC
Reason:            HFE has both DLL and Python paths already (hfe.py lines 46-73 DLL,
                   75-147 Python). Needs: (1) divergence logging between paths
                   (2) Confidence formula alignment (DLL 0.7 vs registry dynamic)
                   (3) AP5 enforcement on DLL path (currently Python-only)
                   Structure exists — less greenfield than estimated.
```

### W-5 (ZLR 39 fix · audit-first)
```
Classification:    ADAPT (2-step)
Baseline estimate: 1-2d + 1d
Audit-adjusted:    1.5d + 1d
Reason:            See §3.6 for hypothesis. Key finding: test fixtures declare BLUE
                   trend with CCI peaking at 130 (never +200). ZLR detector does NOT
                   check trend_state — relies on A1 gate (which runs separately).
                   Step 1: audit fixtures against Liran Stage-1. Step 2: fix after review.
                   The "39 failures" claim needs verification — current test suite shows
                   8 ZLR tests, all passing. The 39 may refer to a different test run
                   or fixture set.
```

### W-6 (8 patterns refit · R_t1 emit)
```
Classification:    ADAPT
Baseline estimate: 3 days CC
Audit-adjusted:    3 days CC
Reason:            All 9 pattern files exist and are functional. Needs:
                   (1) Wire atr_stop.compute_stop() into each pattern's stop calc
                   (2) Add R_t1 computation to PatternResult
                   (3) Consolidate dual detection paths (pattern_engine vs detector)
                   (4) Fix docstrings "8→9" across __init__.py, pattern_engine.py,
                       woodies_system.py, compliance_manifest.yaml
                   (5) Remove HFE legacy interface gap (add detect_hfe to ALL_DETECTORS)
```

### W-7 (Anti-patterns gate · AP1-AP9)
```
Classification:    DEFER (greenfield)
Baseline estimate: 1 day CC
Audit-adjusted:    1.5 days CC
Reason:            No unified anti-patterns module. Only AP4 (HTLB touches) and
                   AP5 (HFE Python fallback) are properly implemented. AP1, AP2, AP7
                   are implicit. AP3, AP6, AP8, AP9 completely missing.
                   Slightly more work than estimated: 9 gates × validation × tests.
```

### W-8 (R_t1 dispatcher + YAML loader)
```
Classification:    ADAPT
Baseline estimate: 2 days CC
Audit-adjusted:    2 days CC
Reason:            Dispatcher exists (104 LOC) with correct 9-class PriorityClass.
                   YAML loader exists (210 LOC) with stage parsing.
                   Needs: (1) Add R_t1-based pattern selection to replace raw max()
                   (2) Two-tier dispatch per P-W6 v2 + P-W8 v2
                   yaml_loader is well-structured — ADAPT, not rewrite.
```

### W-9 (LiranExitLadderRule)
```
Classification:    DEFER (greenfield)
Baseline estimate: 1.5 days CC
Audit-adjusted:    1.5 days CC
Reason:            Trail logic does not exist in S4. B13 trail_check uses EMA-169
                   (57 LOC) which is a different mechanism than Liran's 8-rung ladder.
                   helpers/ema_calculator.py (72 LOC) exists for EMA computation.
                   Fully greenfield: new RiskRule subclass after S2 Pkg 6 lands.
```

---

## §3.6 · P-W3 ZLR test failure root-cause hypothesis

### ZLR-related test count
8 ZLR tests identified:
- `tests/v9/systems/test_woodies_patterns.py::TestZLR::test_zlr_up_detected` (line 91)
- `tests/v9/systems/test_woodies_patterns.py::TestZLR::test_zlr_down_detected` (line 105)
- `tests/v9/systems/test_woodies_patterns.py::TestZLR::test_zlr_no_signal_flat` (line 114)
- `tests/v9/systems/test_woodies_patterns.py::TestZLR::test_zlr_insufficient_data` (line 120)
- `tests/v9/systems/test_woodies_patterns.py::TestZLR::test_zlr_confidence_range` (line 125)
- `tests/v9/systems/test_woodies_patterns.py::TestZLR::test_zlr_details_present` (line 131)
- `tests/v9/systems/test_woodies_patterns.py::TestDetectAllPatterns::test_zlr_detected_via_all` (line 522)
- `tests/v9/systems/test_woodies_patterns.py::TestLegacyInterface::test_legacy_zlr` (line 565)

**Note:** The "39 ZLR test failures" referenced in P-W3 may refer to a different test run, fixture set, or historical state. Currently 8 ZLR tests exist and all pass. W-5 Step 1 should verify whether the 39 failures are reproducible in the current codebase.

### 3 specific tests with potential Stage-1 issues

**1. `test_zlr_up_detected` (line 91)**
- Classification: **SPEC_DRIFT**
- CCI sequence: `[0]*5 + [120, 130, 110, 60, 50, 40, 55, 80]`
- Peak CCI: 130 — passes +100 threshold but never +200
- Evidence: Liran Stage-1 requires ≥1 bar with CCI >+100 (ideally >+200). This fixture has a weak Stage-1.

**2. `test_zlr_down_detected` (line 105)**
- Classification: **SPEC_DRIFT**
- CCI sequence: `[0]*5 + [-120, -130, -110, -60, -50, -40, -55, -80]`
- Peak magnitude: 130 — mirrors up case, same weakness.

**3. `test_zlr_confidence_range` (line 125)**
- Classification: **SPEC_DRIFT**
- Same CCI as `test_zlr_up_detected` — same Stage-1 concern.

### Fixture chunk missing Stage-1

From `backend/v9/tests/integration/fixtures/woodies_bar_sequences.py:12-31`:

```python
def generate_trend_blue_sequence(bars=30, base_price=7400.0):
    """Scenario 1: CCI sustained positive (BLUE trend) -> ZLR pattern."""
    result = []
    for i in range(bars):
        cci = 50 + (i * 2)  # steadily rising CCI above zero
        result.append(WoodiesBar(
            ...
            cci_14=cci,
            ...
            trend_state="BLUE",
        ))
```

CCI ranges from 50 to 108 (at bar 29). `trend_state` is hardcoded "BLUE" but **no bar ever exceeds CCI +200** and only bar 26+ barely clears +100. This fixture declares BLUE trend without satisfying Liran Stage-1 properly (≥6 bars above ZL with ≥1 bar >+100, ideally >+200).

### Structural observation

The ZLR detector in `zlr.py` does NOT check `trend_state` — it only examines CCI values. In production, the A1 strategic gate would filter out trades where color is not BLUE/RED. The test fixtures use `make_bars_from_cci` helper which defaults `trend_state="GRAY"`, meaning ZLR tests pass detection without any strategic gate validation. This is a testing gap: the tests verify ZLR pattern detection in isolation but not the full entry pipeline (A1 → A3 → entry).

### `raw_confidence` column in v9_trades

**Result: NOT FOUND.** The `V9Trade` model in `backend/v9/db/models/trades.py` does not contain a `raw_confidence` column. Zero grep matches across `backend/v9/`. The confidence value could be stored in the `quality` JSON blob (nullable) or would need a new column added. **W-6/W-8 will need to address this.**

---

## Appendix: File inventory summary

### Source files (woodies/)

| Category | Files | Total LOC |
|---|---|---|
| Core orchestration | 16 files | 2,511 |
| Pattern detectors | 10 files (9 + __init__) | 1,266 |
| DTV1 stages | 22 files (21 + __init__) | 1,406 |
| Helpers | 2 files | 73 |
| Config/manifest | 2 files | ~305 lines |
| **W-1 new** | 1 file (atr_stop.py) | 157 |
| **Total** | **53 files** | **~5,718** |

### Test files (woodies-related)

| Location | Files |
|---|---|
| `tests/atomic/` | 4 files |
| `tests/v9/systems/` | 4 files |
| `tests/v9/compliance/` | 1 file |
| `tests/v9/frontend/` | 1 file |
| `tests/v9/api/` | 2 files |
| `backend/v9/tests/` | 10 files |
| **Total** | **22 test files** |
