# D-094 · Pkg 3b Trail Logic Decisions

**Status:** ✅ **LOCKED** · all decisions resolved · ready for Pkg 3b handoff
**Date opened:** 2026-05-24 17:30 IL · **Date locked:** 2026-05-24 19:00 IL
**Authors:** Claude Desktop (gap analysis + xlsx verbatim) + Cursor (code verification + final lock walkthrough)
**Depends on:** D-091 (S2 LIVE scope · Pkg 1 adaptive stop) · D-092 (S4 Woodies update) · Pkg 3a `targets_table.py`
**Blocks:** Pkg 3b code handoff to CC · Pkg 3c (contract split) · Pipeline 3 SHADOW soak

---

## §0 · TL;DR

Desktop walked 15 trail-logic gaps with Michael 2026-05-24 · then Cursor performed code verification and added 4 new findings. After joint walkthrough on 2026-05-24 evening, Michael locked all open items. **Total 15 → 11 from-spec + 4 cursor-findings + 1 meta = ALL LOCKED.**

| Status | Count | Items |
|--------|-------|-------|
| ✅ Locked (xlsx verbatim) | 4 | Gaps 1, 7, 12, 13 |
| ✅ Locked (Michael session) | 3 | Gaps 5, 8 + Gap 12 confirm |
| ⚙️ Engineering blessing | 5 | Gaps 9, 10, 11, 14, 15 |
| ✅ Locked (Michael 2026-05-24 PM) | 10 | §3.A (hybrid+resolver) · §3.B.1 (code wins) · §3.B.2 (5+5) · §3.B.3 (wiring order) · §3.C (Option 3 layered) · §3.D Q1 (b2 Wilder's) · §3.D Q2 (9 families) · §3.D Q3 (atr_caps.py) · atr_caps ripple (Option 3 Superset) · §4 Meta (Phase A) |
| ✅ Total | 22 | **ALL CLOSED** |

---

## §1 · Source authority hierarchy

For this decision doc:

1. **Michael verbal lock** (highest · `Michael 2026-05-24` citations)
2. **`MEMS26_V9_Pattern_Tables_Enhanced.xlsx`** (latest spec authority · uploaded 2026-05-24)
3. **`S2_Master_Summary.xlsx`** Sheets A/B/C/D (referenced consistently · treat Enhanced as newer if conflicting)
4. **Pkg 3a code outputs** (`targets_table.py` etc. · shipped · `trail_after_t2` flag contested per §3.A)
5. **Pkg 1 code outputs** (`adaptive_stop.py` · 3 ATR functions exist — see §5.A)
6. **Existing Layer 4 services** (`backend/v9/services/layer4/*.py` · exist but NOT WIRED — see §5.B)

When sources conflict → this hierarchy resolves. Michael's lock at top can override anything.

---

## §2 · LOCKED decisions (no action needed · for record)

### Gap 1 · BE+1T (not BE) · LOCKED

**Source:** Sheet C STOP STRATEGY verbatim:
> *"Trail logic (universal): +1R → ratchet to BE. **T1 hit → stop to entry+1T**."*

**Lock:**
```python
# In TradeManager._apply_smart_be_after_t1
tick = MES_TICK_SIZE  # = 0.25
new_stop = entry_price + tick if direction == "LONG" else entry_price - tick
```

**Bug:** `manager.py:257` currently sets `trade.stop = float(trade.entry_price)` (= BE, not BE+1T). Pkg 3b fix.

### Gap 7 · Trend_DD "4R cap" · LOCKED

**Source:** Michael 2026-05-24 verbatim: *"7 - cap true"*

**Lock:** For Trend_DD day type:
- T3 = 4R fixed cap (NOT extended to 6R+)
- `trail_after_t2 = False` (no trail engine after T2)
- After T1: stop moves to BE+1T and stays there
- Exits: T3 (4R) · stop (BE+1T) · time_stop (90min) · or Type A invalidation

Already matches `targets_table.py:55`. No code change needed.

### Gap 12 · Fast T2 (T2 hit without explicit T1) · LOCKED

**Lock · Michael 2026-05-24:** Both T1 and T2 logic apply in same bar. If price gaps past T1 directly to T2:
1. First: T1 logic fires → BE+1T stop move
2. Same bar: T2 logic fires → chandelier engages (or HL/LH trail per Gap 4 resolution)
3. Both events logged in `cross_context` with same `bar_ts`

### Gap 13 · Trail tightens only · LOCKED

**Source:** Sheet C STOP STRATEGY verbatim:
> *"If structural stop > 2.0×ATR-14 on 5-min → reduce position size to maintain dollar-risk OR skip. **Never widen the stop.**"*

Plus 5/5 consensus (Bulkowski · Brooks · Dalton · Wyckoff · Auth Table).

**Lock:**
```python
# LONG
new_stop = max(current_stop, computed_trail)
# SHORT
new_stop = min(current_stop, computed_trail)
```

Applies to ALL trail computations including BE+1T transition (BE+1T also wins if computed_trail < BE+1T for LONG).

### Gap 5 · today_typical freeze at entry · LOCKED (implicit)

**Reasoning:** recomputing today_typical mid-trade could move stop AWAY from price when intraday vol drops → violates Gap 13's "never widen".

**Lock · Michael 2026-05-24 implicit (no objection):** ATR proxy (whatever it ends up being per Gap §3.D) is captured at entry and frozen for the trade's lifetime. No recompute on subsequent bar closes.

### Gap 8 · Variation exit_reason · LOCKED

**Source · Michael 2026-05-24 implicit (no objection to default):**

For Variation day type (`T3 = "trail"`): when chandelier triggers exit, persist `exit_reason = "TRAIL_HIT"` in `v9_trades` (NOT `"T3_HIT"`). The exit was caused by next-bar close < chandelier_price, not by reaching a fixed T3 price.

### Engineering decisions · LOCKED (Michael blessing)

**Source · Michael 2026-05-24 verbatim:** *"להשאיר כמו שקבענו"* (keep as decided)

| Gap | Lock |
|-----|------|
| **9 · API for bar close events** | `TrailEngine` class separate from `TradeManager` · subscribes to `BarRouter` · calls `TradeManager.update_stop()` via hook. SRP. |
| **10 · State persistence** | `trade.quality["trail_state"]` JSON blob: `{max_high_since_T2, last_HL, last_LH, chandelier_engaged, t2_bar_ts}`. |
| **11 · Audit trail** | Append to `cross_context` on every stop move: `{event: "trail_move", from, to, reason, bar_ts}`. **Use `json.dumps(..., default=str)` to avoid datetime serialization bug** (per `P31_TASK_BOARD.md` §10). |
| **14 · Restart recovery** | Reload `trail_state` from `trade.quality` JSON. If missing/corrupt → conservative mode (no trail update until next bar close, log warning). Fallback: recompute `max_high_since_T2` from `MAX(v9_bars_5min.high) WHERE ts > t2_filled_at`. |
| **15 · Concurrency** | Sierra tick fill ALWAYS wins. If stop fill reported by Sierra while bar is closing → trail compute discarded, log entry. Aligns with Sierra > Spec > Computed hierarchy (Guardrail M13). |

---

## §3 · Locked decisions (formerly OPEN items) · Michael 2026-05-24 PM

### §3.A · Gap 6 · Trail-by-day-type · LOCKED · Option 3 hybrid + canonical name resolver

**Decision (Michael 2026-05-24):** Option 3 hybrid · per-pattern override on TDD. Specifically:
- Pkg 3b adds **only** OFA Initiative → TDD override (6R + trail) per Sheet A row 14
- Other pattern overrides (Flag/HnS/etc.) deferred to **Pkg 5a-c** (those patterns don't exist in code yet)
- Pkg 3a `trail_after_t2: False` on TDD stays as default
- Override evaluated at pattern-resolution time (post-T2)

**Implementation pattern (locked):**
```python
# backend/v9/systems/day_type/targets_table.py
TRAIL_OVERRIDE_BY_PATTERN = {
    # (day_type, pattern_family) → override dict
    ("Trend_DD", "OFA_Initiative"): {
        "t3": "6R+trail",
        "trail_after_t2": True,
        "reason": "Dalton TDD second-leg · Sheet A row 14",
    },
    # Future Pkg 5a-c: add other (day_type, family) entries
}

def resolve_trail_config(day_type: str, pattern_name: str) -> dict:
    family = _pattern_to_family(pattern_name)  # see atr_caps.py
    if family is not None:
        override = TRAIL_OVERRIDE_BY_PATTERN.get((day_type, family))
        if override is not None:
            return {**TARGETS[day_type], **override}
    return TARGETS[day_type]
```

**Canonical name resolver (locked · lives in `atr_caps.py`):**
```python
# backend/v9/systems/five_min/atr_caps.py
def _pattern_to_family(pattern_name: str) -> Optional[str]:
    """Map runtime pattern_name to xlsx family.

    Runtime pattern_name comes from five_min detectors as 'REACTIVE' / 'INITIATIVE'.
    xlsx family names are 'OFA_Reactive' / 'OFA_Initiative'.
    Future Pkg 5a-c will add: Flag, Pennant, Wedge, Triangle, HnS, Double_BT.
    """
    name = pattern_name.lower()
    if "initiative" in name:
        return "OFA_Initiative"
    if "reactive" in name:
        return "OFA_Reactive"
    return None
```

Both consumers (Pkg 3a trail override · Pkg 3b ATR chandelier) import the same resolver. Single source of truth.

---

### §3.B · NEW · Zohar CCI exit triggers · LOCKED · Option C+ (3 sub-decisions)

**Decision (Michael 2026-05-24):** Option C · wire 5 existing services + defer 5 missing services to Pkg 4a. Three sub-decisions resolved as below.

#### §3.B.1 · Row 4 drift (SWI red) · LOCKED · code wins

**Spec (Sheet D row 4):** *"SWI turns red → Close entire position"*
**Code (`swi_tighten.py`):** Tightens stop by 25% (does NOT close)

**Decision:** Keep current code behavior (TIGHTEN 25%). Spec is prescriptive intent · code is the operationalized softened version.

**Rationale:**
- We are pre-LIVE · zero SHADOW data showing tighten 25% caused harm
- Closing all on SWI red creates more early exits · could cut profitable runners
- Post-SHADOW: if data shows SWI red always precedes full reversal, upgrade to close-all

**Action items:**
1. `swi_tighten.py` stays as-is (tighten 25%)
2. **Sheet D gets a new column `code_status`** with explicit drift documentation:
   - Row 4: `"softened to TIGHTEN 25% in swi_tighten.py · DEMO re-evaluation pending"`
   - Future drifts in Sheet D follow this pattern

#### §3.B.2 · Status of 2 extras (MFE peak + day_type_targets_verify) · LOCKED · in scope

**Decision:** Both `mfe_peak_tighten.py` and `day_type_targets_verify.py` ARE in scope for Pkg 3b wiring.

**Spec source:** Constitution V3 PART 5 B11 + B12 (per registry §7.3 verbatim):
> *"B11 MFE peak 80% tighten (layer4) · B12 day-type targets verify (layer4)"*

Constitution V3 (higher authority) > Sheet D 8 priorities. The 2 extras have spec-authority backing · they just aren't in Zohar's 8 priorities.

**Revised headline (corrects prior count):** Pkg 3b wires **5 existing** services. Pkg 4a wires **5 missing** services (NOT 3 as previously stated).

**Pkg 3b · 5 existing services to wire:**
1. `swi_tighten.py` (Sheet D row 4)
2. `tcci_cross_exit.py` (Sheet D row 8)
3. `cci_flat_tighten.py` (Sheet D row 7)
4. `mfe_peak_tighten.py` (Constitution V3 B11)
5. `day_type_targets_verify.py` (Constitution V3 B12)

**Pkg 4a · 5 missing services to BUILD:**
1. CCI ±200 cross exit (Sheet D row 1)
2. CCI ±100 cross exit (Sheet D row 2)
3. CCI ZL (line 0) cross exit (Sheet D row 3)
4. Opposing pattern exit (Sheet D row 5)
5. New trend pattern exit (Sheet D row 6)

#### §3.B.3 · Wiring order for the 5 existing services · LOCKED

**Decision (Michael 2026-05-24 · Cursor accepts):**

1. `mfe_peak_tighten` — universal · works on any pattern · cheapest to wire
2. `cci_flat_tighten` + `tcci_cross_exit` — Woodies-specific · only S4 trades · paired
3. `swi_tighten` — after §3.B.1 drift sub-decision is locked
4. `day_type_targets_verify` — most dangerous (can close trades mid-flight) · last

Each wire ~50-100 LOC + 4-6 tests. Total Pkg 3b ≈ 5 wires × 75 LOC + 5×5 tests = ~375 LOC + 25 tests + the price-level engine code. Estimated Pkg 3b LOC total: ~800-1000.

---

### §3.C · NEW · time_stop axis · LOCKED · Option 3 layered (3 layers · time_stop is Layer 3 backstop)

**Decision (Michael 2026-05-24):** Option 3 · `min(day, pattern)` as the **hard backstop (Layer 3)** in a 3-layer trade-management stack. The other two layers (MFE peak tighten · HL/LH trail) handle directional progress checking. time_stop ensures no trade sits forever even if Layers 1+2 don't fire.

**The 3 layers (locked):**

| Layer | Mechanism | Fires when | Severity |
|-------|-----------|------------|----------|
| 1 (primary) | `mfe_peak_tighten` | Retracement ≥ 80% of MFE peak | TIGHTEN_STOP (soft) |
| 2 (secondary · post-T2) | HL/LH trail (5-bar lookback) | Close < min(last 5 lows) for LONG | Stop out (directional) |
| 3 (backstop) | `min(day, pattern)` time_stop | X minutes elapsed since entry, regardless of MFE/HL state | Hard exit ("we don't sit forever") |

Layer 1+2 catch most stagnation cases. Layer 3 catches tail-case trades that creep sideways without triggering MFE retracement or HL violation (e.g., 90-min drift trades on TDD).

**Code implementation (locked):**
```python
# backend/v9/systems/five_min/atr_caps.py (or new time_stops.py — Cursor's call)
PATTERN_TIME_STOPS = {
    "Flag":            20,  # Continuation
    "Pennant":         20,  # Continuation
    "OFA_Initiative":  20,  # Continuation
    "OFA_Reactive":    30,  # Reversal
    "Triangle":        30,  # Reversal default
    "Wedge":           30,  # Reversal
    "HnS":             30,  # Reversal
    "Double_BT":       30,  # Reversal
    "Wyckoff_Spring":  45,  # Wyckoff (Pkg 5+ pattern)
    "Wyckoff_Upthrust":45,  # Wyckoff (Pkg 5+ pattern)
}

def compute_time_stop_minutes(day_type: str, pattern_family: str) -> Optional[int]:
    """Layer 3 backstop · first-to-fire wins between day-axis and pattern-axis."""
    day_stop = TARGETS[day_type].get("time_stop_minutes")
    pat_stop = PATTERN_TIME_STOPS.get(pattern_family)
    candidates = [x for x in (day_stop, pat_stop) if x is not None]
    return min(candidates) if candidates else None
```

**SHADOW telemetry:** log per-exit `exit_reason` ∈ {`MFE_TIGHTEN_STOP`, `HL_LH_TRAIL_HIT`, `TIME_STOP_DAY`, `TIME_STOP_PATTERN`, `TIME_STOP_TIE`} so we can measure Layer 3 firing frequency. If Layer 3 fires > 20% of exits in SHADOW → revisit Layer 1+2 thresholds.

---

### §3.D · NEW · ATR cap per pattern family · LOCKED · Q1 (b2) + Q2 (9 families) + Q3 (atr_caps.py) + ripple (Superset)

#### §3.D Q1 · ATR formula at T2 hit · LOCKED · (b2) continuous Wilder's

**Decision (Michael 2026-05-24):** Option (b2) · continuous Wilder's ATR-14 smoothing across the seam between yesterday and today.

**Code-level requirement (Michael's explicit ask):** the new `compute_continuous_atr14()` function MUST contain an explicit comment stating:

```python
# Overnight gap is included in the TR computation per Wilder canonical behavior.
# TR for today's first bar = max(today_high - today_low,
#                                abs(today_high - yesterday_last_close),
#                                abs(today_low - yesterday_last_close))
# This is intentional: overnight gaps ARE volatility per Wilder's original
# ATR formulation. ATR may be inflated on gap-up/down mornings; this is by design.
# Do NOT introduce a seam-reset that ignores overnight gaps without explicit
# spec change.
```

This comment prevents off-by-one debates 2 weeks later when someone notices the inflated post-gap ATR.

#### §3.D Q2 · Family multiplier extension · LOCKED · 9 families

**Decision (Michael 2026-05-24):** Extend the multiplier table to define all 9 xlsx families, even though only OFA_Reactive and OFA_Initiative are currently invoked by Pkg 1 detectors. Future Pkg 5a-c will activate the rest.

Final 9 families in `atr_caps.py`:

| Family | Multiplier | xlsx source | Pkg invoking |
|--------|-----------|-------------|--------------|
| OFA_Reactive | 1.5× | Sheet C | Pkg 1 + Pkg 3b (live) |
| OFA_Initiative | 2.0× | Sheet C | Pkg 1 + Pkg 3b (live) |
| Flag | 1.5× | Sheet C | Pkg 5a (future) |
| Pennant | 1.5× | Sheet C | Pkg 5a (future) |
| Wedge | 2.0× | Sheet C | Pkg 5b (future) |
| Triangle | 2.0× | Sheet C | Pkg 5b (future) |
| HnS | 2.0× | Sheet C | Pkg 5c (future) |
| Double_BT | 2.0× | Sheet C (matches Pkg 1) | Pkg 5c (future) |
| Reactive | 1.5× | Sheet C "1.0-1.5" mid-default | Pkg 5+ (future) |

#### §3.D Q3 · Module location · LOCKED · new `atr_caps.py`

**Decision (Michael 2026-05-24):** Create `backend/v9/systems/five_min/atr_caps.py` as the single source of truth for:
- `ATR_MULTIPLIERS` table (with legacy + xlsx-aligned keys per atr_caps ripple decision below)
- `PATTERN_TIME_STOPS` table (from §3.C)
- `TRAIL_OVERRIDE_BY_PATTERN` table (from §3.A)
- `_pattern_to_family(pattern_name)` canonical name resolver (from §3.A)
- `compute_continuous_atr14()` (from Q1)
- `compute_time_stop_minutes(day_type, pattern_family)` (from §3.C)

Imports: `from backend.v9.systems.five_min.atr_caps import ATR_MULTIPLIERS, _pattern_to_family, ...`

Consumers: Pkg 1 (entry stop · via existing keys) · Pkg 3a (trail override) · Pkg 3b (chandelier + HL/LH + time_stop).

#### §3.D · atr_caps ripple onto Pkg 1 · LOCKED · Option 3 Superset

**Issue:** xlsx-aligned multipliers (OFA_Reactive=1.5· OFA_Initiative=2.0) differ from Pkg 1's shipped values (Reactive=1.0 · OFA=1.5). Migrating Pkg 1 to xlsx values would widen REACTIVE entry stops by 50% and INITIATIVE by 33% · breaking 5-7 Pkg 1 G3 tests and changing entry-stop behavior.

**Decision (Michael 2026-05-24):** Option 3 · Superset. `atr_caps.py` holds **both** legacy keys (Reactive/OFA) AND xlsx-aligned keys (OFA_Reactive/OFA_Initiative). Pkg 1 keeps reading legacy keys with current behavior (no regression). Pkg 3b reads xlsx-aligned keys for chandelier. Future Pkg 1-rev (post-SHADOW) decides whether to migrate Pkg 1 to xlsx values.

Final `ATR_MULTIPLIERS` table in `atr_caps.py`:

```python
ATR_MULTIPLIERS = {
    # === Pkg 1 legacy keys (entry stop computation · current shipped behavior) ===
    "Reactive": 1.0,            # Pkg 1 REACTIVE entry stop
    "OFA": 1.5,                 # Pkg 1 INITIATIVE entry stop
    "Flag": 1.5,                # Pkg 1 (matches xlsx)
    "Double_BT": 2.0,           # Pkg 1 (matches xlsx)
    "HnS": 2.0,                 # Pkg 1 (matches xlsx)

    # === xlsx-aligned keys (Pkg 3b chandelier · future Pkg 5+ entry stops) ===
    "OFA_Reactive": 1.5,        # Sheet C verbatim
    "OFA_Initiative": 2.0,      # Sheet C verbatim
    "Pennant": 1.5,             # Sheet C verbatim · Pkg 5a pattern (future)
    "Wedge": 2.0,               # Sheet C verbatim · Pkg 5b pattern (future)
    "Triangle": 2.0,            # Sheet C verbatim · Pkg 5b pattern (future)
}
```

**Documentation requirement:** code comment on the module-level docstring explaining the dual-namespace pattern and pointing to D-094 §3.D for the rationale + post-SHADOW migration plan.

---

## §4 · META · Phase A vs DEMO+ · LOCKED · Phase A with calibration flag

**Decision (Michael 2026-05-24):** Proceed with Pkg 3b in Phase A. The trail mechanics from the spec are **mechanical** (5-bar HL/LH lookback · 1×ATR chandelier · BE+1T · 3-layer time backstop) · not parametric. Mechanical correctness can be implemented and tested independently of SHADOW data.

**Required commit message flag (MUST include in Pkg 3b commit body):**

> *"Pkg 3b ships mechanical trail mechanics per D-094 §1-§3 spec.*
> *Numeric parameters (ATR multipliers · HL/LH lookback bars · MFE retracement %)*
> *are seeded from Sheet C verbatim values, NOT calibrated against SHADOW data.*
> *Post-SHADOW Pkg 1-rev + Pkg 3b-rev will re-tune these numerics if data shows*
> *Layer 3 firing > 20% of exits, or if T2→exit avg duration drifts from spec.*
> *Do NOT modify these numerics in Phase A without explicit Michael lock + D-094 amendment."*

**Earlier registry classification** (`mems26-systems-registry.canvas.tsx`):
> *"#9 Trailing stop after T1 · DEMO אחרי SHADOW"*
> *"#13 ATR-adaptive stops · DEMO+ — לא לשנות לפני SHADOW data"*

This classification was correct for the **parametric tuning** of trail logic but conflated mechanical implementation with parametric calibration. The mechanical work IS Phase A · the parametric calibration IS DEMO+. The commit message flag preserves this distinction for future agents.

**Registry update required:** mark `#9` and `#13` in the registry as "Phase A mechanical · DEMO+ parametric" rather than blanket DEMO+. (Action: post-Pkg 3b ship.)

---

## §5 · Cursor verification findings (added to Desktop handoff)

### §5.A · Pkg 1 ATR inventory (corrects Desktop §3.D Q1)

The Desktop handoff claimed "Pkg 1 shipped only with P75". This is **wrong**. `adaptive_stop.py` has:

| Function | Formula | Used for | Status |
|----------|---------|----------|--------|
| `compute_baseline_atr` | Wilder's ATR-14 on yesterday's 5-min bars | Pre-session entry stop | ✅ Pkg 1 G3 PASS |
| `compute_rolling_atr` | Simple mean of today's bar ranges | During-IB entry stop | ✅ Pkg 1 G3 PASS |
| `compute_today_typical` | P75 of today's bar ranges | Post-IB entry stop | ✅ Pkg 1 G3 PASS |

So when xlsx says "ATR-14" — that formula EXISTS (Wilder's), just not currently called from chandelier code (because chandelier doesn't exist yet). Question §3.D Q1 is a real choice among 3 (a/b/c), not a missing implementation.

### §5.B · Layer 4 services exist but NOT WIRED

`backend/v9/services/layer4/` contains 5 service files (`swi_tighten.py` · `tcci_cross_exit.py` · `cci_flat_tighten.py` · `mfe_peak_tighten.py` · `day_type_targets_verify.py`). Each exports `evaluate(...)` returning either `None` or an action dict like `{action: "TIGHTEN_STOP", new_stop: ..., reasoning_notes: ...}`.

**But:** `grep -r "from backend.v9.services.layer4" backend/` returns **0 matches**. Only `tests/atomic/test_l4_*` import them. The 5 services are dead code waiting to be wired by a `TradeManager` consumer.

**Implication for §3.B option C:** wiring is mostly "call `evaluate()` from a new `TrailEngine.on_bar_close()` hook and route the returned action via `TradeManager.update_stop()` or `TradeManager.close_trade()`". Cheap.

### §5.C · BE+1T bug location confirmed

`backend/v9/services/trade_manager/manager.py:257`:
```python
trade.stop = float(trade.entry_price)  # BUG: BE, not BE+1T
```

Plus the early-return guard at line 249-250 (`if abs(stop - entry) < 0.25: return`) means a stop already at BE+1T would be skipped — the new fix must handle that edge.

### §5.D · `trail_after_t2` flag locations confirmed

Per `targets_table.py:33-126` · the 6 trading day types have explicit `trail_after_t2` boolean. Only `Trend_Normal` and `Variation` are `True`. Matches Desktop's claim.

---

## §6 · Next steps · post-lock execution path

### Step A · Cursor drafts Pkg 3b handoff for Desktop · NEXT

The handoff covers:
1. **BE+1T fix** at `manager.py:257` (Gap 1) · +30 LOC + 4 tests
2. **New `atr_caps.py` module** (§3.A + §3.C + §3.D) · ~120 LOC + 15 tests
3. **New `TrailEngine` class** · subscribes to BarRouter (Gap 9 + §3.B Layer 2) · ~150 LOC + 8 tests
4. **HL/LH trail** · 5-bar closes lookback (Phase 1 trail) · ~80 LOC + 6 tests
5. **Chandelier trail** · continuous Wilder's ATR-14 (§3.D Q1 b2) · ~100 LOC + 6 tests
6. **Pkg 3a override hook** · TRAIL_OVERRIDE_BY_PATTERN for OFA Initiative on TDD (§3.A) · ~30 LOC + 4 tests
7. **Wire 5 existing Layer 4 services** (§3.B.2 + §3.B.3 ordering):
   1. `mfe_peak_tighten` (Layer 1 · primary stagnation detector)
   2. `cci_flat_tighten` + `tcci_cross_exit` (Woodies-specific S4 only)
   3. `swi_tighten` (per §3.B.1 keep current tighten 25%)
   4. `day_type_targets_verify` (most dangerous · last)
   ~375 LOC + 25 tests
8. **time_stop computation** · Layer 3 backstop (§3.C) · ~50 LOC + 5 tests
9. **`trade.quality["trail_state"]` persistence** (Gap 10) · ~60 LOC + 5 tests
10. **`cross_context` audit trail** · `json.dumps(default=str)` (Gap 11) · ~40 LOC + 3 tests
11. **Restart recovery** (Gap 14) + **concurrency** (Gap 15) · ~80 LOC + 6 tests
12. **Update `Sheet D` with `code_status` column** (§3.B.1 documentation)

**Estimated totals:** ~1115 LOC code + ~87 tests · ~2-3 days CC execution + ~1 day G3 review + UAT.

### Step B · Desktop converts to MEGA prompt for CC

### Step C · CC executes Pkg 3b in one session

### Step D · Cursor G3 review · standard 10-criterion gate

Includes specific checks:
- BE+1T fix uses `MES_TICK_SIZE = 0.25` constant (not magic number)
- `atr_caps.py` has the dual-namespace docstring per §3.D ripple
- `compute_continuous_atr14()` has the overnight-gap comment per §3.D Q1
- `TrailEngine` is separate class (SRP per Gap 9)
- `cross_context` uses `json.dumps(default=str)` (Gap 11)
- Commit message contains the Phase A calibration flag (§4)

### Step E · Michael G4 smoke trade

DB-only end-to-end with Pkg 1 + 2a + 2bc + 3a + 3b full stack.

---

## §7 · Sign-off · ALL LOCKED ✅

- [x] Michael lock §3.A · Option 3 hybrid + canonical name resolver
- [x] Michael lock §3.B · Option C (5 existing wire + 5 deferred)
- [x] Michael lock §3.B.1 · code wins (tighten 25%) + Sheet D `code_status`
- [x] Michael lock §3.B.2 · 2 extras in scope (MFE peak + day_type_targets_verify)
- [x] Michael lock §3.B.3 · wiring order mfe → cci+tcci → swi → day_type_targets
- [x] Michael lock §3.C · Option 3 layered (Layer 3 backstop)
- [x] Michael lock §3.D Q1 · (b2) continuous Wilder's + overnight-gap comment
- [x] Michael approve §3.D Q2 · 9 families in atr_caps.py
- [x] Michael lock §3.D Q3 · new `atr_caps.py` module
- [x] Michael lock §3.D ripple · Option 3 Superset (legacy + xlsx-aligned keys)
- [x] Michael lock §4 Meta · Phase A with calibration commit flag

**All 11 sign-offs complete · D-094 LOCKED · Pkg 3b handoff draft is the next deliverable.**

---

*End of D-094 · opened 2026-05-24 17:30 IL · locked 2026-05-24 19:00 IL · Cursor + Desktop + Michael joint authorship*
