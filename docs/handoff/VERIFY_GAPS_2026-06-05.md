# VERIFY — Complete Gaps · 2026-06-05 eve

## A · Housekeeping

### A1: Commits (raw output)
```
$ git log --oneline -10
e1ce925 fix(I-15): trend_state DB fallback when in-memory state is default GRAY
33296b9 fix(B-13): add price-band write-guard to POST /5min DB path
d589a3c chore(index): regenerate after session commits (683 files, 108 dirs, 44 orphans)
4902a56 docs: CLAUDE.md index protocol + VERIFY files + board updates
0aa1284 feat(frontend): Build Status P0 redesign + Trades Phase 1
9dbfc2c fix(I-16): choppiness_score continuous — unblocks 8 S2 patterns
fc69315 fix(B-11): bridge_inspector ORDER BY rowid → ts_col for Postgres
cb036b8 fix(day_type): endpoint reads live machine + A5 advisory + wrapper cleanup
bb75bd8 fix(safety): B-13 cutover — staleness guard + session gate + G1 columns + S3 mute
c0cddec fix: display filter RTH-only (09:30-16:00 ET) — matches Sierra chart#5
```

### A2: Index regen (raw output)
```
$ python3 scripts/gen_index.py
{"files": 683, "dirs_indexed": 108, "orphans": 44}

$ grep "main.py" backend/_INDEX.md
| `main.py` | ▶ entry/test | 664 | 2026-06-02 | MEMS26 unified backend — serves V8-compatible routes + V9 API. |
```
`backend/main.py` correctly identified as entrypoint. `backend/v9/main.py` does not exist (confusion resolved).

---

## B · Safety residuals

### B3: I-7 B-13 write-guard (raw output)
Added price-band check to POST /5min DB write path (`bars.py`). Fresh bars with off-market
prices are rejected from DB writes. Old valid bars (ts older than MAX_STALE_AGE) pass through
for chart history.

```
$ BRIDGE_TOKEN=test python3 -m pytest backend/v9/tests/test_b13_write_guard.py -v --no-header
backend/v9/tests/test_b13_write_guard.py::test_write_guard_present_in_post_5min PASSED [ 50%]
backend/v9/tests/test_b13_write_guard.py::test_write_guard_preserves_old_bars PASSED [100%]
======================== 2 passed in 0.04s
```
Revert the write-guard → `test_write_guard_present_in_post_5min` turns RED.

### B4: I-15 trend_state (fix applied)
**Root cause:** on startup, `current_state["trend_state"]` defaults to "GRAY" (line 116 of
`woodies_system.py`). The build_status inspector reads this default before any bars arrive,
causing A1 veto on all 9 patterns. `/woodies/current` shows RED after DB replay populates
the state, but the build_status page (manual refresh, fetched earlier) still shows GRAY.

**Fix:** `woodies_inspector.py` — when `trend_state == "GRAY" and bar_count == 0`, fall back
to the latest `v9_bars_5min_woodies` DB row's `trend_state`. This ensures the inspector shows
the same value as `/woodies/current` after startup replay.

**Verification:** requires live backend — Cowork should verify at next RTH that build_status
and /woodies/current show the same trend_state.

---

## C · Diagnose-only reports

### C5: I-13 sizing=reject diagnosis

**Mechanism:** `woodies_system.py:694-741` `calculate_size()` uses:
- `base_tier`: ZLR/TT/GB100=high, VEGAS/GHOST/FAMIR/HTLB=medium, TLB=low
- `aux_count`: sum of [SWI_aligned, CZI_aligned, TCCI_leading] (0–3)
- `trend_ok`: close > LSMA AND close > EMA34 (direction-aware)

**Decision tree:**
- high + aux>=3 + trend_ok → **full** (3 contracts)
- high/medium + aux>=2 → **half** (2 contracts)
- low + aux>=2 → **half**
- low + aux<2 → **reject**
- else → **reject**

**Problem:** When aux_count < 2 (only 0 or 1 of SWI/CZI/TCCI aligned), ALL patterns
get reject. In choppy markets where studies disagree, this blocks everything. The threshold
of >=2 means a pattern needs majority agreement from 3 auxiliary indicators.

**Exposure gap:** The sizing inputs (swi_aligned, czi_aligned, tcci_leading, base_tier,
aux_count, trend_ok) are NOT exposed in any `details{}` field. The pattern just shows
"sizing=reject" with no visibility into why.

**Proposal (for Michael):**
1. Expose sizing inputs in `current_state["sizing_details"]` so the dashboard shows exactly
   which indicators failed.
2. Consider whether aux>=1 (instead of >=2) is appropriate for medium-tier patterns, or
   whether trend_ok alone should be sufficient for high-tier patterns (currently ignored
   unless aux>=3).
3. Counterfactual: count how many patterns were blocked by sizing=reject vs would have
   been profitable. (EOD agent can track this.)

### C6: I-14 opening→entry chain diagnosis

**Finding:** The `opening_type` IS classified by `opening_detector.py` (e.g. OPEN_REJECTION_REVERSE)
and stored in `v9_day_type_state`. The `decision_matrix.py` maps (opening_type × width_class) →
day_type probabilities. **However:**

**The chain breaks at:** There is NO code that reads opening_type and decides whether to
authorize/skip a trade entry. The opening→day_type→targets path exists:
- `opening_detector.detect_opening_type()` → stored in DB
- `decision_matrix.get_probabilities()` → returns day_type distribution
- `day_type_targets.resolve_targets()` → returns prices

But there is NO trade-entry authorization gate that says "opening_type=ORR + Normal_day
→ SKIP this pattern" or "→ ENTER with modified targets". The opening_type classification
happens but is **informational only** — it doesn't affect any firing decision.

**Where it should be wired (proposal):**
The natural insertion point is in the `pre_fire_validator` or as a new gate in the
firing systems' dispatch path. The Authorization Table (from the strategy spec) should
map (opening_type × day_type × pattern_family) → ALLOW/SKIP/MODIFY.

**Not fixed — design decision required from Michael.**

### C7: I-10 S2/S3 decision tree design

**Current state:** Only S4 (Woodies) has a structured A1–A7 decision tree with inspector
exposure to build_status. S2 and S3 have equivalent logic scattered across detectors/gates
but no unified tree.

**Proposed design for S2 (5-Min):**

| Stage | S2 equivalent | Source code | Inspector key |
|-------|--------------|-------------|---------------|
| A1 strategic_gate | choppiness_ok + trend alignment | `five_min_system.py` choppiness, package eligibility | `choppiness_gate` |
| A2 day_type_query | day_type != UNKNOWN + Authorization Table | `decision_tree_v3.yaml` Pkg 5a/b/c gating | `day_type_gate` |
| A3 pattern_detection | 8 detector functions (reactive/initiative/chart) | `detectors/*.py` | `pattern_detected` |
| A4 context_query | S/R proximity + COT/AMT + volume profile | `five_min_system.py` confluence | `context_ok` |
| A5 TPO advisory | POC/VAH/VAL alignment (non-blocking) | `tpo_system` cross-ref | `tpo_advisory` |
| A6 entry_classification | entry/stop/targets + sizing | `calculate_size` + `stop_anchors` | `entry_classified` |
| A7 universal_checks | pre_fire_validator + risk_checks + dedup | `pre_fire_validator.py` | `universal_ok` |

**Proposed design for S3 (Footprint):**

| Stage | S3 equivalent | Source code | Inspector key |
|-------|--------------|-------------|---------------|
| A1 strategic_gate | S3 enabled (not muted) | `atr.py` FOOTPRINT_DISABLED flag | `enabled_gate` |
| A2 day_type_query | day_type gate | (same as S2) | `day_type_gate` |
| A3 signal_detection | 4 signal types (absorption/stacked/sweep/exhaustion) | `footprint_detector.py` | `signal_detected` |
| A4 dedup_gate | level+direction+bar_ts dedup | `_fire()` dedup logic | `dedup_ok` |
| A5 context_query | delta context + bid/ask volume | footprint bar fields | `context_ok` |
| A6 entry_classification | entry/stop (min(low, entry-tick)) + targets | inline in `_fire()` | `entry_classified` |
| A7 universal_checks | pre_fire_validator + risk | same as S2/S4 | `universal_ok` |

**Implementation approach:**
1. Create `s2_decision_tree.py` and `s3_decision_tree.py` (read-only stage evaluators)
2. Wire into `s2_inspector.py` / `footprint_inspector.py` to emit components per stage
3. Frontend `SystemBranch` already renders components — no frontend change needed
4. Each stage maps to a `Component` with stage/key/spec/present/live/freshness

**Not implemented — design only, pending Michael's approval on the stage mapping.**

---

## NOT-DONE

1. **Live verification** of I-15 (trend_state) — requires running backend + RTH data
2. **Sizing exposure** (I-13) — proposal only, not implemented (trading-logic surface)
3. **Opening→entry authorization table** (I-14) — design decision required
4. **S2/S3 decision tree implementation** (I-10) — design only, pending approval
5. **Remaining untracked files** (269 files) — handoff docs, test fixtures, older CC work; not committed (separate triage needed)
