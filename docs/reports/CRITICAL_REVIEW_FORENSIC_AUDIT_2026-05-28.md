# Independent Critical Review — S2/S4 Forensic Audit · 2026-05-28

**Reviewer:** Claude Code (CC) — independent review of Cursor forensic audit
**Subject:** `AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` (Cursor) vs `DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` (CC prior)
**Mode:** READ-ONLY evidence review against source code + spec

---

## 1. Headline Verdict

**The forensic audit's headline ("data-integrity bug, not logic bug, primary cause = DLL frozen-tail") HOLDS UP.** The evidence chain is solid: 12+ patterns in `v9_woodies_signals` falsify the prior "no patterns matched" diagnosis; the frozen-tail symptom is mechanically explained by the DLL code; `calculate_size()` demonstrably rejects on stale inputs. The prior CC diagnosis (mine) was wrong on the headline — I concluded "no patterns detected" without querying `v9_woodies_signals`. The forensic audit's root-cause ranking is sound.

---

## 2. Per-Claim Verdicts

### Claim 1 — DLL frozen-tail bug
**CONFIRMED**

The C++ code at `v9_woodies_export.h:460-462`:
```cpp
auto mapIdx = [&](int dll_bar_idx) -> int {
    if (!have_sierra || wc == 0 || wc == sc.ChartNumber) return dll_bar_idx;
    return sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx);
};
```

When `wc != sc.ChartNumber` (the DLL chart and Woodies chart are different chart numbers), every history bar goes through `GetContainingIndexForDateTimeIndex`. This Sierra API maps a datetime index from one chart to another. For in-progress or not-yet-computed bars on the target chart, it clamps to the last valid index — producing the same mapped index `mi` for multiple DLL bars.

At `v9_woodies_export.h:493-500`:
```cpp
float sv;
sv = S_VAL(s_cci14_arr, mi);  cci14  = (sv != 0) ? sv : v9_calc_cci(bars, bi, 14);
```

The fallback `v9_calc_cci` only fires when `sv == 0`. A stale non-zero value bypasses the fallback — exactly matching the observed 13-bar freeze where all values are non-zero and identical.

In contrast, `MES_AI_DataExport.cpp:587` uses `arr[idx]` directly (no `GetContainingIndexForDateTimeIndex`) — explaining why `current_bar.cci_14` is live (47.21) while `history[-1].cci_14` is frozen (49.70).

**The asymmetry between the history loop (mapped, frozen) and the current-bar read (direct, live) is confirmed in the code.**

### Claim 2 — Backend ignores current_bar
**CONFIRMED**

`bars.py:223-231`:
```python
@property
def all_bars(self) -> List[Dict]:
    if self.bars:
        return self.bars
    if self.history:
        return self.history
    if self.current_bar:
        return [self.current_bar]
    return []
```

`history` is always non-empty (200 bars from DLL), so `current_bar` is never reached. At `bars.py:842-852`, `last_flat = history[-1]` (the frozen bar) is what gets routed to S4. No comment indicates this is intentional — it appears to be an unintended fallback ordering.

### Claim 3 — A5/sizing reject is the actual fire-blocker
**CONFIRMED**

`woodies_system.py:592-612` — `calculate_size()` reads from `self.current_state`:
```python
st = self.current_state
swi = st.get("swi_value") or 0  # ← frozen -78.17
tcci = st.get("cci_6_tcci") or 0  # ← frozen -21.09
```

For ZLR LONG (conf=0.83) with frozen values:
- `swi_aligned = (swi > 0)` → `(-78.17 > 0)` → **False**
- `czi_aligned = (czi > 0)` → `(54 > 0)` → **True**
- `tcci_leading = (tcci > cci_14)` → `(-21.09 > 49.70)` → **False**
- `aux_count = 0 + 1 + 0 = 1`

ZLR is `'high'` tier. Needs `aux_count >= 3 and trend_ok` for `'full'`, or `aux_count >= 2` for `'half'`. With `aux_count=1`, falls through to `return 'reject'` at line 628.

**With plausible live values** (SWI ~+20, TCCI ~+150, CCI ~+131):
- `swi_aligned = (+20 > 0)` → **True**
- `czi_aligned = (54 > 0)` → **True**
- `tcci_leading = (+150 > +131)` → **True**
- `aux_count = 3` → `'full'` (with trend_ok) or `'half'`

**The audit's math is correct.** Frozen inputs directly cause the reject.

### Claim 4 — Chicago TS over-correction
**CONFIRMED (with nuance)**

`base_stream.py:283-300` — `_chicago_to_utc()` interprets the unix timestamp as Chicago wall-clock and converts to UTC. It uses `America/Chicago` timezone, which IS DST-aware (CDT=UTC-5 in summer, CST=UTC-6 in winter).

`woodies_chart_routes.py:43` — hardcoded `ts_unix += 5 * 3600` — is NOT DST-aware. This adds exactly 5h regardless of season. In CDT (summer) this is correct; in CST (winter) it would under-correct by 1h.

The audit's claim that "Sierra chart appears to be in ET" is plausible if the chart uses ET instead of CT — but `v9_sc_datetime_to_unix` (`v9_exports.h:147-152`) does pure Excel-serial math with no timezone awareness at all:
```cpp
return (long long)((serial - 25569.0) * 86400.0 + 0.5);
```

This produces whatever timezone the SCDateTime is stored in (chart-local). If Sierra chart is set to ET(EDT=UTC-4), the bridge adds 5h (CDT assumption) when it should add 4h — yielding a +1h future drift. This matches the audit's evidence (DB shows 17:10 UTC at wall-clock 12:10 ET → exactly 1h ahead).

**The bridge's `_chicago_to_utc` IS DST-aware; `woodies_chart_routes.py:43` is NOT.**

### Claim 5 — Frontend shows 13 identical bars then a jump
**CONFIRMED (mechanically)**

`woodies_chart_routes.py:188-193`:
```python
elif ts_bug_detected:
    cur["ts_unix"] = normalized[-1]["ts_unix"]
    cur["ts"] = normalized[-1]["ts"]
    normalized[-1] = cur
```

When all history bars share the same ts (ts_bug_detected=True), current_bar replaces the last history bar. But when bars have DIFFERENT timestamps (the normal case with the Chicago fix applied), the merge follows lines 194-198 which either overlays or appends. The 13 frozen bars pass through untouched — the function doesn't detect the frozen-value symptom, only the frozen-timestamp symptom.

### Claim 6 — v9_woodies_patterns never written
**CONFIRMED**

```bash
rg "V9WoodiesPattern\(" backend/ → 0 hits
```

The model class exists but no code ever instantiates it. `v9_woodies_signals` is the actual signals table. My prior diagnosis didn't check `v9_woodies_signals` — a process error.

### Claim 7 — Bridge/push freshness is healthy
**CONFIRMED**

The DLL writes every ~3s, bridge pushes at bar cadence, 9,383 bars routed today. `S4_WOODIES_TABLE_A_Pattern_Setup.csv` specifies pattern detection on closed 5-min bars, not tick-level. Transport layer is working correctly; the bug is in the data content, not the delivery.

---

## 3. Per-Question Answers

### Q1 — Is the frozen-tail hypothesis consistent with C++ code?
**CONFIRMED.** See Claim 1 analysis above. `GetContainingIndexForDateTimeIndex` clamping to the last valid Woodies-chart index for in-progress bars is the most parsimonious explanation. All 7 Sierra study fields freeze simultaneously because they all use the same `mi = mapIdx(bars[bi].chart_bar_start)` at line 489. No alternative explanation fits the simultaneous 7-field freeze with varying OHLC.

### Q2 — Do the 9 pattern detectors match spec?
**CONFIRMED — no silent drift found.** Pattern IDs (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE) match `S4_WOODIES_TABLE_A_Pattern_Setup.csv`. Anti-pattern wiring (AP1-9) blocks detection via `detected=False`. The spec-vs-impl deltas D-1 (lunch skip) and D-2 (FOMC) are real omissions but are explicitly documented as Pipeline 2 scope deferrals.

### Q3 — Does calculate_size read current_state or studies?
**`current_state` (line 592).** `current_state` is updated at `woodies_system.py:356-370` from the `studies` dict of the JUST-PROCESSED bar. Since S4 receives the frozen `history[-1]` bar, `studies` contains frozen values, and `current_state` is updated with those frozen values. So both paths are frozen. **This matters** — even if sizing read `studies` directly, it would still get frozen inputs because the routed bar itself is frozen.

### Q4 — Is the +5h Chicago fix DST-aware?
**PARTIALLY.** The bridge's `_chicago_to_utc` (base_stream.py:283-300) uses `zoneinfo.ZoneInfo("America/Chicago")` which IS DST-aware. But `woodies_chart_routes.py:43` uses hardcoded `+5*3600` which is NOT DST-aware — it's correct only during CDT (March-November). The DLL's `v9_sc_datetime_to_unix` has no TZ awareness at all — it outputs whatever timezone the chart uses. No code probes the actual Sierra chart timezone setting.

### Q5 — Is all_bars preferring history deliberate?
**LIKELY UNINTENDED.** No comment or docstring explains the priority. The property tries `self.bars` first (a legacy field), then `self.history`, then `self.current_bar`. This looks like a "try everything" fallback chain, not a deliberate choice to exclude `current_bar` when `history` is present. The correct behavior for S4 routing would be to use `current_bar` (live) for the latest bar's study values, since `history[-1]` is subject to the frozen-tail bug.

### Q6 — Other frozen-tail symptoms elsewhere?
**NEW GAP — PARTIAL.** The `GetContainingIndexForDateTimeIndex` pattern is specific to `v9_woodies_export.h`. The 5min bars (`v9_exports.h:154+`) use `v9_build_5min_ohlcv_bars` which builds bars from the DLL chart's own OHLCV — no cross-chart study fetch. Footprint and TPO streams use separate data paths. **The frozen-tail bug is likely Woodies-specific.**

### Q7 — Was the prior diagnosis defensible anywhere?
**PARTIALLY.** My diagnosis correctly identified: (a) S2 gates are open, (b) S4 doesn't depend on S1, (c) opening_type INDETERMINATE has zero classification impact. These hold. What I got wrong: concluding "no patterns detected" without checking `v9_woodies_signals`. The forensic audit was right to challenge this. The opening_type NA/INDETERMINATE divergence is indeed cosmetic as I stated.

### Q8 — Are D-1 (lunch skip) and D-2 (FOMC) LOW severity?
**AGREED for shadow; DISAGREE for LIVE.** Lunch session (12:00-13:30 ET) on MES has lower liquidity and wider spreads — firing patterns there increases slippage risk. For shadow observation this is acceptable. For LIVE, both should be enforced. I'd raise D-1 to **MEDIUM** for LIVE.

### Q9 — min_r_t1_threshold 0.0 → 1.0 test gap?
**YES — gap exists.** There are no tests that verify behavior with `min_r_t1_threshold >= 1.0`. The dispatcher tests in `test_pattern_dispatcher.py` test the current config. Switching to 1.0 for LIVE without regression tests for the new threshold is a risk. A parameterized test covering 0.0, 0.5, and 1.0 thresholds should exist before LIVE.

### Q10 — Is the headline root cause correct?
**YES.** The DLL frozen-tail → backend uses frozen → sizing rejects chain is the right primary cause. It is the most parsimonious explanation that fits ALL evidence:
- 12+ signals detected (pattern logic works)
- All have `A5=reject` (sizing gate triggered)
- Frozen SWI/TCCI values mechanically produce `aux_count < 2`
- OHLC varies but Sierra studies freeze (cross-chart mapping bug)
- `current_bar` has live values but is ignored by `all_bars`

No simpler explanation accounts for all five observations simultaneously.

---

## 4. New Gaps the Audit Missed

1. **S2 volume key mismatch (`"v"` vs `"vol"`)** — discovered in this session, not in the forensic audit. The bridge sends `"vol"`, all S2 detectors read `"v"`. S2 Reactive/Initiative have NEVER seen volume data. This is a separate pre-LIVE blocker, independent of the DLL frozen-tail issue. **Fix already applied in this session** (`five_min_system.py:698`).

2. **S2 `current_day_type=None` on mid-session restart** — the hydrate query works but wasn't called when the backend started before the `v9_day_type_state` row existed. After restart it would resolve, but it means S2 runs with `None` day_type until an event arrives — the NT gate at line 710 doesn't trigger (correct), but chart pattern day-type gating at lines 728-749 silently skips when `current_day_type is None` because `None` is not in the set `{"Neutral_Extreme", "Neutral_Center", "Normal", "Variation"}`.

3. **`woodies_chart_routes.py:43` hardcoded +5h is a winter-time bomb** — during CST (Nov-Mar), this would under-correct by 1h. The bridge is DST-aware but this endpoint is not.

---

## 5. Pre-LIVE Blockers (Independent Ranking)

| Rank | Blocker | Severity | Source |
|------|---------|----------|--------|
| **1** | DLL frozen-tail: `GetContainingIndexForDateTimeIndex` clamping | **CRITICAL** — all S4 fires blocked | Forensic audit Claim 1 |
| **2** | Backend `all_bars` routing `history[-1]` (frozen) instead of `current_bar` (live) | **CRITICAL** — compounds #1, blocks even a partial DLL fix | Forensic audit Claim 2 |
| **3** | S2 volume key `"v"` vs `"vol"` mismatch | **HIGH** — S2 Reactive/Initiative have never seen volume | This session's finding (fix applied) |

---

## 6. What I Couldn't Verify

- **Sierra Chart UI values** — cannot open Sierra from code review; would need a screenshot at the same moment as an API call to definitively confirm the parity break
- **Exact Sierra chart timezone setting** — no code probes it; would need to check Sierra's `Use Global Settings for Time Zone` and the chart's explicit TZ
- **Whether `GetContainingIndexForDateTimeIndex` clamps or returns -1** for unmapped bars — Sierra's API documentation would confirm, but the behavior (13-bar freeze to a non-zero value) strongly implies clamping
- **Live `v9_woodies_signals` table** — I accepted the forensic audit's DB evidence; would need a live query to re-verify the 12+ row count
