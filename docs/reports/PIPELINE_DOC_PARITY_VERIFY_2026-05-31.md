# Pipeline Doc Parity Verification

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Source doc:** `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md`  
**Type:** READ-ONLY verification — zero code changes

---

## Verdict

**The As-built document is largely faithful to code (13/15 MATCH).** Two drifts found — one cosmetic (conf threshold label), one substantive (cited file doesn't exist, 3 management rules not implemented).

---

## Verification Table

| # | Phase | Point Verified | Verdict | Evidence |
|---|-------|---------------|---------|----------|
| 1 | P1 (S1) | Lock condition: conf threshold | **DRIFT** | Code: `ConfidenceThreshold()` = 0.85. Doc says "≥0.70". GAP-5 note partly corrects but main table row misleading. |
| 2 | P1 (S1) | IBWidth enum + DayTypeConfig | MATCH | NARROW<15, MEDIUM≤25, WIDE>25, EXTREME (flag-ON). Config: `ib_narrow_max_pt=15.0`, `ib_medium_max_pt=25.0`, `min_session_min_for_lock=210`. |
| 3 | P3 (sizing) | Auth Table 70 cells, max=3 | MATCH | `assert len(_AUTH_TABLE_V1) == 70` (line 106), `max(...) == 3` (line 110). |
| 4 | P3 (stop) | ATR multipliers | MATCH | `Reactive:1.0, OFA:1.5, Flag:1.5, Double_BT:2.0, HnS:2.0` — verbatim in `adaptive_stop.py:21-27`. |
| 5 | P3 (sizing) | Contract splits | MATCH | OFA: `(0.25,0.50,0.25)`, H&S/Double: `(0.33,0.33,0.34)`, Flag: `(0.50,0.50,0.00)` — `contract_split.py:15-30`. |
| 6 | P3 (time) | Time stop per day_type | MATCH | TN:None, TDD:90, NV:60, NeuE:45, NeuC/Norm:30, NT:no_trade — `targets_table.py`. |
| 7 | P4 (gateway) | 5 risk gates in order | MATCH | cooldown(:88)→SSV(:92)→chop(:98)→cluster(:104)→strict(:134) — `trading_gateway.py`. |
| 8 | P4 (gateway) | First-wins routing | MATCH | `if self.demo_slot is None:` (line 125), no ranking/buffering. |
| 9 | P4 (gateway) | MAX_CONTRACTS=2 dead code | MATCH | Defined `risk_checks.py:20`, zero references in any `if` — grep confirmed. |
| 10 | P5 (mgmt) | Stop-first priority | MATCH | `# 1. Stop check FIRST` comment + logic before target checks — `bar_level_detector.py:100-126`. |
| 11 | P5 (mgmt) | Smart BE+1T after T1 | MATCH | `_apply_smart_be_after_t1`: stop→entry±0.25pt, idempotent — `manager.py:261-315`. |
| 12 | P5 (mgmt) | trade_management.py C.2/C.4/C.6/C.7 | **DRIFT** | File does not exist. See below. |
| 13 | GAP-3 | Zero ranking in gateway | MATCH | `grep "rank\|R:R\|rr_score\|buffer\|candidate" trading_gateway.py` → 0 matches. |
| 14 | GAP-4 | MAX_CONTRACTS dead code | MATCH | `grep "MAX_CONTRACTS" backend/v9/gateway/` → only definition line 20. |
| 15 | GAP-6 | ZLR 0 failures | MATCH | `pytest tests/v9/systems/woodies/ -v`: 8 passed, 0 failed, 0 skipped. |

---

## Drift Details

### Drift 1: Confidence Threshold Label (LOW severity)

**Doc says (Phase 1/C1):** "conf ≥ 0.70"  
**Code says:** `ConfidenceThreshold()` = 0.85. The `__eq__` hack makes `0.85 == 0.70` return True (backwards compat), but the runtime check is `>= 0.85`.

**Impact:** Doc row is misleading. The GAP-5 footnote already notes this ("effectively ≥ 0.85") but the main table should say 0.85.

**Action needed:** Cosmetic doc fix (no code change).

### Drift 2: trade_management.py Does Not Exist (MEDIUM severity)

**Doc says (Phase 5):** "C.2 Trail T3: watermark-2.0pt · C.4 Lock-in 2R: 2R→stop to 1R · C.6 Time Decay: 10 bars → close at open · C.7 Reversal Exit: opposing system fire → emergency close" — cites `trade_management.py:17-124`.

**Code reality:**
- No file `backend/v9/services/trade_manager/trade_management.py` exists
- **C.2 Trail T3:** Partially in `manager.py` trail-engine API (lines 397-452) + `trail_engine.py`. Trail config resolved from `targets_table.py` per day_type+pattern. Not a watermark-2.0pt rule as described.
- **C.4 Lock-in 2R:** NOT FOUND in any file. No `2R` or `lock_in` logic.
- **C.6 Time Decay:** NOT FOUND. Time-stop exists (W-10 bar count) but no "10 bars → close at open" rule.
- **C.7 Reversal Exit:** NOT FOUND. No "opposing system fire → emergency close" logic.

**Impact:** The doc describes trade management rules that are **spec-only (not yet implemented)**. The As-built document should mark these as ⚠️ GAP rather than ✅.

**Action needed:** Doc should reclassify C.4/C.6/C.7 as "spec-only, not implemented" with a GAP marker.

---

## Overall Assessment

| Category | Count |
|----------|-------|
| MATCH (code = doc) | 13 |
| DRIFT (cosmetic) | 1 |
| DRIFT (substantive) | 1 |
| Not found / broken | 0 |

**The document is reliable for Phase 0-4 (day type through gateway).** Phase 5 (trade management) overstates implementation — 3 of 4 cited management rules (C.4/C.6/C.7) are spec-only, not yet in code.

---

## GAP Status Confirmation

| GAP | Doc Status | Code Status | Verified |
|-----|-----------|-------------|----------|
| GAP-1 (LIVE stub) | ⚠️ | Confirmed: `_execute_live` logs warning, no Sierra send | ✅ |
| GAP-3 (first-wins) | ⚠️ | Confirmed: zero ranking/buffering logic | ✅ |
| GAP-4 (MAX_CONTRACTS) | ⚠️ | Confirmed: dead code, never enforced | ✅ |
| GAP-5 (conf threshold) | ⚠️ | Confirmed: 0.85 masquerades as 0.70 via __eq__ | ✅ |
| GAP-6 (ZLR) | ✅ RESOLVED | Confirmed: 8/8 pass, 0 skip/xfail | ✅ |
