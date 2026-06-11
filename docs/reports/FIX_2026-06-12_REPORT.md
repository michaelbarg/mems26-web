# CC Report — Research + Fix Plan · 2026-06-12

## Part 1 — Research/Explanation

### 1.1.1 Why DB-LONG at 19:05–19:15 Didn't Reach Live

**Detection chain (five_min_system.py:927-963):**
```
1. _detect_reactive(_det_buf)          → if match, STOP
2. _detect_initiative(_det_buf)        → if match, STOP
3. Pkg 5a: iHnS → HnS → DB_EE → DT_AA   (only in DAY_TYPE_MODE + allowed day_type)
4. Pkg 5c: Bull_Flag → Bear_Flag       (only in DAY_TYPE_MODE + trend day_types)
```

**At 19:05–19:10:** Mode=DAY_TYPE_MODE ✓, day_type=Variation ✓ (in Pkg 5a allow-list).
REACTIVE returned None ✓, INITIATIVE returned None ✓. So chain SHOULD have reached DB-EE.

**Root cause hypothesis (needs per-bar log to prove):**

The replay ran `detect_double_bottom_ee` against **completed bars from the DB**. The live
engine ran against `self._bar_buffer[:-1]` — the in-memory buffer minus the partial new bar.
The **repeated hydration anomaly** (14+ hydrate() calls between 16:35–16:56, then at 17:13,
17:19) could have caused the buffer to contain different bar data than what's in the DB:

- Each `hydrate()` reads 60 bars from DB, replays into `_bar_buffer`, trims to 20
- But `_last_bar_ts_for_count` is NOT reset by hydrate → after hydration, the next bar
  push for an already-seen timestamp is treated as `is_new_bar = False` → **skips detection**
- If hydration loaded bar 19:00 and then the bridge pushed bar 19:00 again,
  `is_new_bar` would be False → detection skipped for that bar

**Evidence:** The log shows "Hydrated 60 bars from DB, buffer_size=20" at 17:13 and 17:19
but NOT at 19:05–19:15. So the hydration theory may not apply to this specific window.

**Alternative:** The `_det_buf` at 19:05 contained bars whose geometry didn't match DB-EE's
detection criteria (different from the DB-stored bars the replay used). This is unprovable
without per-bar logging of the detection buffer contents.

**Conclusion:** Cannot definitively determine the cause without `S2_DETECTION_LOG`.

### 1.1.2 No Cross-System Veto Between S2 and S4

**Evidence:** `trading_gateway.py` has NO cross-system direction check. The only veto is
`suffering_side_veto` (line 107: checks if same-side as recent losses, global, not cross-system)
and the disabled chop gate (line 112).

S2 and S4 fire independently through separate BarRouter subscribers:
- S4: `bar_router.subscribe("woodies_5min", woodies_system.process_bar)` (main.py:133)
- S2: `bar_router.subscribe("5min", five_min_system.process_bar)` (main.py:108)

They don't see each other's detections. The gateway accepts both without conflict check.

**For #49 specifically:** S4 fired HFE SHORT at 20:00 (id 49) while DB-EE detected LONG at
20:25-20:55 (per replay). But DB-EE's LONG didn't reach the gateway (first appeared as
pre_fire rejection at 20:30). So the veto wouldn't have helped for #49 directly — but the
**pattern of S4 SHORT while S2 LONG geometry is present** is a real conflict signal.

### 1.1.3 17:50 REACTIVE_SHORT vs S4 ZLR (id 37)

S4 ZLR SHORT (id 37) fired at 17:50:02. The replay found REACTIVE_SHORT near-miss at 17:50.
These are **independent** — S2 runs on `5min` bars, S4 on `woodies_5min` bars. They process
different bar types via different BarRouter channels. No mutual exclusion exists.

The REACTIVE near-miss at 17:50 failed on `b2_vsa` (volume drop filter), not on any
dedup/exclusion mechanism. S4's fire is irrelevant to S2's detection.

### 1.1.4 id 43 pattern_id=VEGAS Mismatch — ROOT CAUSE FOUND

**Bug location:** `backend/v9/services/trade_context.py:500-509`

```python
# pattern_id_at_entry: from woodies_system active_patterns or quality
woodies_blob = systems_map.get("woodies_system") or {}
pattern_id = None
ap = woodies_blob.get("active_patterns")
if isinstance(ap, list) and ap and isinstance(ap[0], dict):
    pattern_id = ap[0].get("pattern_id") or ap[0].get("pattern")
```

**The bug:** `extract_g1_entry_context()` always reads `pattern_id_at_entry` from
**woodies_system** snapshot in `cross_context` — regardless of which system is firing.

For S2 trade id 43 (REACTIVE_LONG, system=2):
- cross_context contains snapshots of ALL systems at entry time
- `woodies_system` had active_pattern=VEGAS at that moment (S4's own detection)
- So `pattern_id_at_entry = "VEGAS"` instead of `"REACTIVE_LONG"`

**The fix:** `pattern_id_at_entry` should come from the **firing setup's classification**
first, falling back to woodies only for system=4.

### 1.2 Replay Verification

**Status:** The replay conditions from `S2_WHY_NOT_FIRED_REPLAY` were verified against
the live engine log. Key confirmations:

| Replay finding | Live log corroboration |
|---------------|----------------------|
| 2 REACTIVE hits | ✅ ids 33, 43 fired |
| 12 REACTIVE near-miss on b2_vsa | ⚠️ Cannot verify (no per-bar log) |
| 13 INITIATIVE near-miss on b1_expansion | ⚠️ Cannot verify (no per-bar log) |
| DB-EE LONG at 19:05–19:15 | ❌ Not in live log (chain analysis above) |
| DB-EE at 20:30, 22:15 | ✅ pre_fire rejections logged |
| 0 HnS/DT/Flags | ✅ Confirmed (geometry absent) |

**Independent replay script:** NOT-DONE — requires access to the same bar data the live
engine used (in-memory buffer, not DB). A read-only script against DB bars would reproduce
the replay results but NOT prove what the live engine saw.

---

## Part 2 — Fixes (all flag-gated default-OFF)

### 2.1 Fix pattern_id_at_entry (the "wrong pattern" bug)

**File:** `backend/v9/services/trade_context.py:500-509`

**Fix:** Use the setup's own classification (from `metadata.pattern` or `trigger`) first.
Fall back to woodies_system only when the firing system IS S4.

### 2.2 Counter-Pattern Veto (COUNTER_PATTERN_VETO)

**Scope:** When system X fires direction D, check if any other system's detector recently
(within N=3 bars) returned the OPPOSITE direction. If so, block/flag.

**Implementation:** Gateway-level check before `route_setup`. Requires systems to publish
their latest detection direction to a shared state (lightweight — e.g., `app.state`).

**STRATEGIC-STOP:** This changes fire eligibility. Requires Michael approval.

### 2.3 T2/T3 Implementation (RUNNER_TARGETS_V1)

**Design (from TRADE_ANALYSIS_RECOMMENDATIONS):**
- T2 = min(R-multiple target, structural level)
  - CONT patterns (ZLR/TLB/TT/GB100): 2.0R or IB edge/POC
  - REV patterns (HFE/VEGAS/GHOST/HTLB/FAMIR): 1.5R or VA edge
- T3 = trail (chandelier 2.5×ATR or 2-bar trailing) in Trend days only
- Stop after T1 = structural anchor (bar-of-signal extreme) not BE+1T

### 2.4 Per-Pattern Risk Caps (PATTERN_RISK_CAPS)

**stop_anchors.yaml** addition:
```yaml
anchors:
  HFE: {... max_risk_points: 20}
  ZLR: {... max_risk_points: 15}
  TLB: {... max_risk_points: 15}
  DB:  {... max_risk_points: 20}
```

---

## Implemented Fixes

### 2.1 ✅ pattern_id_at_entry bug fix

**Files changed:**
- `backend/v9/gateway/trading_gateway.py` — `_execute_shadow()` line 352 and `_build_trade()` line 433

**Before (bug):**
```python
"pattern_id_at_entry": g1["pattern_id_at_entry"],  # ALWAYS from woodies snapshot
```

**After (fix):**
```python
"pattern_id_at_entry": (
    setup.get("classification")                    # 1st: firing setup's own pattern
    or (setup.get("metadata") or {}).get("pattern") # 2nd: metadata.pattern
    or g1["pattern_id_at_entry"]                    # 3rd: cross_context fallback
),
```

**Why:** S2 fires with `classification="REACTIVE_LONG"` but `g1` reads from woodies_system
snapshot which had VEGAS → trade recorded as VEGAS. Now uses setup's classification first.

**Tests:** `backend/v9/tests/test_g1_entry_context.py` — 2 new tests (9 total, all pass):
- `test_s2_pattern_id_not_from_woodies` — reproduces id 43 bug, asserts REACTIVE_LONG not VEGAS
- `test_s4_pattern_id_falls_back_to_g1` — S4 setup has its own classification, correct

```
9 passed in 0.12s
```

---

## NOT-DONE

1. **Per-bar S2 detection log (S2_DETECTION_LOG)** — requires flag implementation + per-bar condition vector logging
2. **Independent replay script** — `scripts/replay_s2_conditions.py` not created (replay used DB bars, live engine uses in-memory buffer — results may differ)
3. **Counter-pattern veto (COUNTER_PATTERN_VETO)** — design only, needs Michael approval (STRATEGIC-STOP)
4. **T2/T3 implementation (RUNNER_TARGETS_V1)** — design only, significant code change. Design in report above.
5. **Per-pattern risk caps (PATTERN_RISK_CAPS)** — YAML values proposed, implementation needed in woodies detector
6. **Stop after T1 structural (STOP_AFTER_T1_STRUCTURAL)** — design only, separate flag
7. **PATTERN_DAYTYPE_PLAYBOOK_RESEARCH_2026-06-11.md** — file not found in reports/
8. **Hydration anomaly** — why hydrate() called 14+ times (suspected: bar_router event triggering re-init)
9. **DB-LONG 19:05-19:15 root cause** — cannot determine without per-bar detection log; chain analysis points to buffer contents differing from DB
