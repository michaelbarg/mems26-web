# Handoff to Claude Desktop · Pkg 1 (Adaptive Stop Engine)

**Date:** 2026-05-23 18:50 IL
**From:** Michael (via Cursor agent · G3 PASS on Pkg 0)
**To:** Claude Desktop
**Task:** Write the full MEGA prompt for Claude Code (CC) to execute Pkg 1 · Adaptive Stop Engine.
**Authority:** D-091 §Adaptive Stop Engine + Master Summary Sheet 4 (multipliers locked)

---

## 0 · Pkg 0 G3 verdict · PASS

Pkg 0 finished. G3 review: 9/10 ✅, 1 informational finding (2 stale comments in `five_min_system.py` lines 5 + 206-208 — to be cleaned up in Pkg 1 + Pkg 2a respectively).

5613 LOC removed · 95 LOC added · 46 files. Backend boots with 5 systems. Zero new test failures. ReadLints clean.

---

## 1 · Pkg 1 scope · Adaptive Stop Engine

Replace static stop (`bar.low − 2.00pt`) with 3-layer adaptive computation as per D-091.

### ⚠️ 2 BUGS in D-091 pseudo-code · TESTS ARE AUTHORITY

D-091's pseudo-code §Stop calculation has 2 inconsistencies. **Resolution rule for CC:**

> **TESTS in §4 of this handoff are AUTHORITY.**
> **Pseudo-code in D-091 is ILLUSTRATIVE only.**
> **If conflict — TESTS WIN. STOP and report if any test cannot be satisfied.**

#### Bug 1 · `reduce_size_signal` inequality reversed
D-091 line 107-110:
```python
# COMMENT: If structural > adaptive_cap → reduce position size  ← CORRECT
if stop_structural < adaptive_cap:                                 ← CODE REVERSED
    contracts = reduce_size(default_contracts)
```
For LONG (stops below entry): `structural > adaptive_cap` means structural is HIGHER (tighter, closer to entry). When Layer A (structural) is the tightest → it's a tight stop → vulnerable to noise → reduce size.

**Correct rule (use this):**
```python
reduce_size_signal = (binding_layer == "A")
# Layer A binding = structural was tightest = we accepted a cramped stop
# Layer B binding = adaptive_cap clamped us to a moderate stop = normal sizing
# Layer C binding = floor enforced minimum = unusually-low-vol scenario · normal sizing
```

#### Bug 2 · `max(structural, adaptive_cap, floor)` does not enforce floor

D-091 line 105:
```python
stop = max(stop_structural, adaptive_cap, floor)   # ← WRONG · floor not enforced
```

For LONG with `structural=entry-5.25`, `adaptive_cap=entry-0.1`, `floor=entry-1.0`:
- `max(-5.25, -0.1, -1.0) = -0.1` → final stop is **0.4T from entry** · TIGHTER than 4T floor ✗
- Floor is meant to be **the tightest ALLOWED** stop (4-tick noise minimum) · not a candidate for tightening.

**Correct formula (use this):**
```python
# LONG (stop below entry · higher number = tighter)
candidate = max(stop_structural, adaptive_cap)     # take tighter of pattern vs volatility
stop = min(candidate, floor_price)                  # clamp · not tighter than floor

# SHORT (stop above entry · lower number = tighter)
candidate = min(stop_structural, adaptive_cap)
stop = max(candidate, floor_price)
```

Where `floor_price = entry - 4*tick` (LONG) or `entry + 4*tick` (SHORT).

**Binding layer determination:**
```python
if stop == floor_price:
    binding_layer = "C"
elif (LONG and stop == stop_structural) or (SHORT and stop == stop_structural):
    binding_layer = "A"
else:
    binding_layer = "B"
```

### Spec authority (verbatim from D-091 §Adaptive Stop Engine · with bug-fix overrides above)

**3 phases (time-dependent):**

```python
# Pre-session (before 09:30 ET):
baseline_atr = ATR_14(yesterday_5min_bars)

# During IB (09:30-10:30):
rolling_atr = moving_average(today_bar_ranges)  # updated per bar

# Post-IB (10:30+):
today_typical = percentile_75(today_bar_ranges)
today_max     = max(today_bar_ranges)
```

**3 stop layers (per pattern fire):**

```python
# D-091 (corrected 2026-05-23) — Layer semantics:
#   Layer A · Structural anchor (per pattern · pattern_anchor ± 1 tick)
#   Layer B · Adaptive ATR cap = MAX allowed distance (volatility ceiling)
#   Layer C · Floor             = MIN allowed distance (4 ticks · 1.0pt noise floor)

# LONG · stop below entry · higher price = tighter
stop_structural = pattern_anchor - 1*tick
adaptive_cap    = entry - ATR_MULTIPLIER[family] * today_typical
floor_price     = entry - 4*tick

candidate  = max(stop_structural, adaptive_cap)   # take TIGHTER of A vs B
stop_price = min(candidate, floor_price)          # CLAMP · never tighter than floor

# SHORT · mirror (lower = tighter)
# candidate  = min(stop_structural, adaptive_cap)
# stop_price = max(candidate, floor_price)

ATR_MULTIPLIER = {
    "Reactive":  1.0,  # tight stops for rotation
    "OFA":       1.5,  # Initiative
    "Flag":      1.5,
    "Double_BT": 2.0,
    "HnS":       2.0,
}

# Binding layer + reduce-size signal
if stop_price == floor_price:
    binding_layer = "C"
elif stop_price == stop_structural:
    binding_layer = "A"
else:
    binding_layer = "B"

reduce_size_signal = (binding_layer == "A")
```

**Two D-091 pseudo-code bugs deprecated (do NOT implement):**
- ~~`max(structural, adaptive_cap, floor)`~~ did NOT enforce the floor as a minimum distance.
- ~~`if stop_structural < adaptive_cap: reduce_size(...)`~~ had the inequality reversed for LONG.

> **These 2 bugs are NOT a Stop signal trigger (see §9).** They are pre-resolved by this handoff. Use the corrected formulas above directly. No need to ask Michael · no need to STOP · no need to update D-091 (already updated 2026-05-23).

### Per-pattern structural anchors (Layer A · D-091 table)

| Pattern | LONG anchor | SHORT anchor |
|---------|--------------------------|----------------------------|
| Reactive | 1T below belly low | 1T above belly high |
| Initiative | 1T below broken level (POC/VAH) | 1T above broken level (POC/VAL) |
| Bull/Bear Flag | 1T below flag low | 1T above flag high |
| Double Bottom | 1T below lower of two bottoms | n/a |
| Double Top | n/a | 1T above higher of two peaks |
| Inverse H&S | 1T below right shoulder | n/a |
| H&S Top | n/a | 1T above right shoulder |

### Tick size · MES = 0.25pt = $1.25 (CME spec · constant)

### Pattern family → multiplier mapping (Master Summary Sheet 4)

| Family | Patterns | Multiplier |
|--------|----------|-----------|
| Reactive | Reactive LONG, Reactive SHORT | 1.0× today_typical |
| OFA | Initiative LONG, Initiative SHORT | 1.5× today_typical |
| Flag | Bull Flag, Bear Flag | 1.5× today_typical |
| Double_BT | Double Bottom, Double Top | 2.0× today_typical |
| HnS | Inverse H&S, H&S Top | 2.0× today_typical |

---

## 2 · Files in scope

### WRITE NEW
- `backend/v9/systems/five_min/adaptive_stop.py` (~150-200 LOC)
- `tests/v9/systems/test_five_min/test_adaptive_stop.py` (~300-400 LOC · 15+ golden tests)

### MODIFY EXISTING (precise lines only)
- `backend/v9/systems/five_min/five_min_system.py`:
  - **Line 5** (module docstring): remove stale `chart_5min/` reference
  - **Line 561** (static stop): replace with call to `adaptive_stop.compute()`

### FORBIDDEN — do NOT touch
- `backend/v9/systems/footprint/`
- `backend/v9/systems/woodies/`
- `backend/v9/systems/day_type/`
- `backend/v9/systems/tpo/`
- `backend/v9/systems/killzone/`
- `frontend/`
- `bridge/`
- `sc_study/`
- `backend/main.py`
- `backend/v9/app.py`
- `backend/v9/services/event_dispatcher/`
- All other files in `backend/v9/systems/five_min/` except `five_min_system.py` line 5 + line 561
- 🛑 `backend/v9/systems/five_min/five_min_system.py` **lines 206-208 — FORBIDDEN to modify in Pkg 1**
  (stale `chronic toxicity` comment referencing chart_5min architecture · deferred to Pkg 2a in the Pattern Library Refactor wave · touching it in Pkg 1 will fail G3 review)

---

## 3 · API contract for `adaptive_stop.py`

CC must implement these public functions (Desktop · please specify in mega prompt):

```python
"""adaptive_stop.py — Adaptive Stop Engine per D-091.

Replaces static `bar.low - 2.0pt` with 3-layer adaptive computation:
  A) structural anchor (per pattern)
  B) ATR cap (per family · today_typical multiplier)
  C) floor (4 ticks)
"""
from dataclasses import dataclass
from typing import List, Literal, Optional

MES_TICK = 0.25
FLOOR_TICKS = 4
ATR_MULTIPLIERS = {
    "Reactive":  1.0,
    "OFA":       1.5,
    "Flag":      1.5,
    "Double_BT": 2.0,
    "HnS":       2.0,
}


@dataclass
class StopComputation:
    """Output of compute_stop · all layers visible for audit."""
    stop_price: float                # final stop · see compute_stop docstring for formula
    structural_anchor: float          # Layer A · raw price (e.g., belly_low)
    stop_structural: float           # Layer A applied: anchor ± 1 tick offset
    adaptive_cap: float              # Layer B · entry ± mult*today_typical
    floor_price: float               # Layer C · entry ± 4 ticks
    binding_layer: Literal["A", "B", "C"]   # which layer = final stop_price
    reduce_size_signal: bool         # True iff binding_layer == "A" (structural was tightest)
    today_typical: float             # debug · the volatility input used


def compute_baseline_atr(yesterday_bars: List[dict]) -> float:
    """Pre-session ATR-14 from yesterday's 5-min bars (D-091 §Pre-session phase).

    Args:
        yesterday_bars: list of bars with 'h', 'l', 'c' keys

    Returns:
        ATR-14 as pure number (in price points, not ticks)
    """
    # Wilder's ATR-14 standard formula


def compute_rolling_atr(today_bars_so_far: List[dict]) -> float:
    """During-IB rolling ATR (D-091 §During IB phase).

    Args:
        today_bars_so_far: bars from open until current (≤12 bars during IB)

    Returns:
        Moving average of bar ranges (h-l)
    """


def compute_today_typical(today_bars: List[dict]) -> float:
    """Post-IB · 75th percentile of today's bar ranges (D-091 §Post-IB phase).

    Args:
        today_bars: today's bars (≥12 expected post-IB)

    Returns:
        75th percentile of bar ranges
    """


def compute_today_max(today_bars: List[dict]) -> float:
    """Post-IB · max of today's bar ranges (D-091 §Post-IB phase)."""


def compute_stop(
    *,
    entry_price: float,
    direction: Literal["LONG", "SHORT"],
    structural_anchor: float,          # raw price (e.g., belly_low) · 1 tick offset applied internally
    family: Literal["Reactive", "OFA", "Flag", "Double_BT", "HnS"],
    today_typical: float,              # current volatility input (changes by phase)
) -> StopComputation:
    """Compute final stop per D-091 §Stop calculation (3 layers · CORRECTED formulas · see handoff §1).

    Returns StopComputation with all 3 layers + binding decision.

    Logic (LONG · stop below entry · higher price = tighter):
        stop_structural = structural_anchor - 1*MES_TICK
        adaptive_cap    = entry_price - ATR_MULTIPLIERS[family] * today_typical
        floor_price     = entry_price - FLOOR_TICKS * MES_TICK
        candidate       = max(stop_structural, adaptive_cap)   # tighter of A vs B
        stop_price      = min(candidate, floor_price)          # clamp · not tighter than floor

    Logic (SHORT · stop above entry · lower price = tighter): mirror with min/max swapped.

    Binding layer:
        stop_price == floor_price          → binding_layer = "C"
        stop_price == stop_structural      → binding_layer = "A"
        otherwise                          → binding_layer = "B"

    reduce_size_signal = (binding_layer == "A")
        Layer A binding means pattern said "tight stop" and volatility allowed it · noise-vulnerable.

    DO NOT implement `max(structural, adaptive_cap, floor)` — D-091 pseudo-code has 2 bugs (see handoff §1).
    """
```

**Edge cases CC must handle:**
- `yesterday_bars` empty → `RuntimeError("baseline_atr requires ≥14 prior bars")` (NOT silent zero)
- `today_bars_so_far` < 5 → fall back to `baseline_atr` (log info, not error)
- `today_typical` ≤ 0 → fall back to floor only (log warning)
- Unknown `family` → `KeyError` (NOT silent default)

---

## 4 · Golden tests — minimum 15 (CC must implement)

| # | Test | Input | Expected |
|---|------|-------|----------|
| 1 | `test_baseline_atr_14_basic` | 14 bars w/ ranges [1, 1.2, 1.5, ...] | ATR ≈ Wilder's formula result |
| 2 | `test_baseline_atr_insufficient_bars` | 5 bars only | `RuntimeError` raised |
| 3 | `test_rolling_atr_during_ib` | 6 bars in IB | mean of bar ranges |
| 4 | `test_today_typical_p75` | 20 bars with known ranges | 75th percentile exact |
| 5 | `test_today_max` | bars with max range 2.5 | returns 2.5 |
| 6 | `test_stop_long_layer_a_binds` | Reactive LONG · entry=100.0 · belly_low=98.75 · today_typical=2.0pt | stop=98.5 (struct − 1T · Layer A) · `binding_layer="A"` · stop_structural=98.5 · adaptive_cap=98.0 · floor_price=99.0 |
| 7 | `test_stop_long_layer_b_binds` | Reactive LONG · entry=100.0 · belly_low=95.0 · today_typical=1.5pt | stop=98.5 (cap · Layer B) · `binding_layer="B"` · stop_structural=94.75 · adaptive_cap=98.5 · floor_price=99.0 |
| 8 | `test_stop_long_layer_c_binds` | Reactive LONG · entry=100.0 · belly_low=95.0 · today_typical=0.1pt | stop=99.0 (floor · Layer C) · `binding_layer="C"` · stop_structural=94.75 · adaptive_cap=99.9 · floor_price=99.0 |
| 9 | `test_stop_short_layer_a_binds` | Reactive SHORT · entry=100.0 · belly_high=101.25 · today_typical=2.0pt | stop=101.5 · `binding_layer="A"` (mirror of 6) |
| 10 | `test_stop_short_layer_b_binds` | Reactive SHORT · entry=100.0 · belly_high=105.0 · today_typical=1.5pt | stop=101.5 · `binding_layer="B"` (mirror of 7) |
| 11 | `test_family_multipliers_all_5` | OFA / Flag / Double_BT / HnS / Reactive · entry=100.0 · belly_low=90.0 · today_typical=1.0pt | adaptive_cap distances: 1.0 / 1.5 / 1.5 / 2.0 / 2.0pt respectively |
| 12 | `test_reduce_size_signal_when_a_binds` | same inputs as test 6 (Layer A binds) | `reduce_size_signal=True` |
| 13 | `test_reduce_size_signal_false_when_b_binds` | same inputs as test 7 (Layer B binds) | `reduce_size_signal=False` |
| 13b | `test_reduce_size_signal_false_when_c_binds` | same inputs as test 8 (Layer C binds) | `reduce_size_signal=False` (only A triggers reduce) |
| 14 | `test_unknown_family_raises` | family="Unknown" | `KeyError` |
| 15 | `test_binding_layer_field_correct` | each of 3 tests above | binding_layer matches |
| 16 | `test_today_typical_fallback_to_baseline` | today_bars=2 (insufficient) | uses `baseline_atr` from yesterday |
| 17 | `test_negative_today_typical_floor_only` | today_typical=0 | returns floor (entry - 4T) · warning logged |

**Golden fixtures for tests 1, 4, 6-8 must use EXACT computed values, not approximations.**

**Note on tests 6/7/8 numerics (Layer-A/B/C binding · LONG only · CORRECTED formula `min(max(A,B), floor)`):**

| Test | belly_low | today_typical | A=struct (=belly_low−1T) | B=cap (=entry−mult·typ) | C=floor (=entry−1.0) | `max(A,B)` | `min(.,C)` | Binding | reduce_size |
|------|-----------|----------------|-----------------------------|--------------------------|------------------------|------------|------------|---------|--------------|
| 6 | 98.75 | 2.0 | 98.5 | 98.0 | 99.0 | 98.5 | **98.5** | **A** | True |
| 7 | 95.0  | 1.5 | 94.75 | 98.5 | 99.0 | 98.5 | **98.5** | **B** | False |
| 8 | 95.0  | 0.1 | 94.75 | 99.9 | 99.0 | 99.9 | **99.0** | **C** | False |

Verify by hand · entry = 100.0 · Reactive (1.0× multiplier) · MES tick = 0.25.

**Important:** Under D-091's deprecated `max(A,B,C)` formula, test 8 would yield 99.9 (Layer B), not 99.0 (Layer C) — because that formula never enforced the floor. The corrected formula in §1 is what makes Layer C binding actually achievable. If CC implements `max(A,B,C)` instead, test 8 will fail · this is the intended early-detection mechanism for the bug.

---

## 5 · Integration in `five_min_system.py` (precise change)

### Current code (line 561 · static stop)

```python
            # Stop: opposite extreme + 2pt 🟡 default("to-calibrate-in-SHADOW")
            stop_price = (bar.get("l", entry_price) - 2.0) if direction == "LONG" else (bar.get("h", entry_price) + 2.0)
```

### New code (Pkg 1 replacement · uses adaptive_stop module)

```python
            # Stop: 3-layer adaptive (D-091 §Adaptive Stop Engine)
            from backend.v9.systems.five_min.adaptive_stop import compute_stop, compute_today_typical
            structural_anchor = bar.get("l", entry_price) if direction == "LONG" else bar.get("h", entry_price)
            today_typical = compute_today_typical(self._bar_buffer)  # uses today's bars in buffer
            family = "Reactive" if kind in ("REACTIVE_LONG", "REACTIVE_SHORT") else "OFA"  # Initiative → OFA
            stop_comp = compute_stop(
                entry_price=entry_price,
                direction=direction,
                structural_anchor=structural_anchor,
                family=family,
                today_typical=today_typical,
            )
            stop_price = stop_comp.stop_price
            if stop_comp.reduce_size_signal:
                logger.info("[FiveMin] adaptive_stop reduce_size: family=%s · A_tighter_than_B", family)
                # actual size reduction handled in Pkg 3c · for now just log
```

### Module docstring fix (line 5)

```python
"""FiveMinSystem — 5-min Decision Maker with full D-077 lifecycle.

Implements hydrate() for cold start scenarios (Addendum Section 1).
Uses SessionClassifier (D-083) — never raw time checks.
"""
```

(remove the `Integrates with existing chart_5min/...` line)

---

## 6 · Files Desktop must inline into the mega prompt

Desktop, attach these full files inline so CC can reference them:

1. `backend/v9/systems/five_min/five_min_system.py` lines 530-650 (the bar processing + fire path · so CC sees where to integrate)
2. `backend/v9/systems/five_min/setup_emitter.py` (entire · so CC sees how stop_price flows)
3. `backend/v9/systems/five_min/output_schema.py` (so CC knows T1Setup expects float stop_price)
4. `backend/v9/systems/day_type/decision_matrix.py` (search for existing ATR usage · ~50 lines context)
5. `backend/v9/systems/five_min/choppiness.py` (existing rolling stats reference)
6. `backend/v9/systems/five_min/first_hour_matrix.py` (existing time-based logic reference)
7. D-091 §Adaptive Stop Engine (verbatim · lines 66-122 of D-091)
8. Empty file template `tests/v9/systems/test_five_min/__init__.py` (verify it exists OR CC creates)

---

## 7 · Acceptance criteria (G4 UAT)

CC must self-verify:

- ✅ `pytest tests/v9/systems/test_five_min/test_adaptive_stop.py -q` exit 0 · all 17+ tests pass
- ✅ `pytest tests/v9/systems/test_five_min/ -q` exit 0 (no regression on existing five_min tests)
- ✅ `BRIDGE_TOKEN=dummy python3 -c "from backend.v9.systems.five_min.five_min_system import FiveMinSystem; FiveMinSystem()"` succeeds
- ✅ `BRIDGE_TOKEN=dummy python3 -c "from backend.v9.systems.five_min.adaptive_stop import compute_stop"` succeeds
- ✅ ReadLints clean
- ✅ No new dependencies added (no `import numpy` · no `import pandas` · use pure Python)
- ✅ Line 5 cleanup **conditional**: BEFORE editing · `rg -n "chart_5min" backend/v9/systems/five_min/five_min_system.py` must be run.
  - If the only hit is line 5 (docstring) → edit line 5 to remove `chart_5min/` reference · keep the rest of the docstring intact.
  - If line 5 is **already clean** (Pkg 0 may have done it in a follow-up commit) → report "line 5 already clean · skipped" · do NOT invent a fake reference to delete (this would be an M13 violation).
  - **DO NOT** edit lines 206-208 even though they also contain `chart_5min` references (deferred to Pkg 2a · see §8).
- ✅ Post-edit verify: `rg -n "chart_5min" backend/v9/systems/five_min/five_min_system.py` returns hits **only at lines 206-207** (the deferred chronic-toxicity comment).
- 🛑 **Lines 206-208 byte-identical to HEAD** — verify with `git diff HEAD -- backend/v9/systems/five_min/five_min_system.py | grep -E "^[+-].*chronic|toxicity"` returns 0 hits
- ✅ Coverage: each `compute_*` function called by at least 1 test
- ✅ All 17+ tests in §4 pass · no test skipped · no test marked xfail

---

## 8 · Constraints (must not violate)

- **No silent excepts** — every `except` must include `logger.warning(...)` rate-limited
- **No `return None` without prior log** — all error paths must log first
- **No new dependencies** — pure Python · use `statistics.quantiles` for P75 if needed
- **No hardcoded magic numbers** — `MES_TICK`, `FLOOR_TICKS`, `ATR_MULTIPLIERS` as module constants
- **Maintain Path A canonical** — no imports from deleted `chart_5min/`
- **`today_typical` fallback to baseline_atr** is acceptable (early session), but must log info
- **`KeyError` for unknown family is INTENTIONAL** — not handled · fails loud
- 🛑 **Do NOT touch lines 206-208 of `five_min_system.py`** — the `chronic toxicity` comment is intentionally preserved · its removal is scoped to Pkg 2a (Pattern Library Refactor wave). Modifying these 3 lines in Pkg 1 is **FORBIDDEN** and will fail G4 acceptance.
- **Do NOT modify any other files in `five_min/`** beyond what's specified
- 🛑 **TESTS ARE AUTHORITY · pseudo-code is illustrative** — if D-091 pseudo-code conflicts with §4 tests, **TESTS WIN**. Two known D-091 bugs documented in §1: (1) `reduce_size_signal` inequality reversed, (2) `max(struct, cap, floor)` does not enforce floor. Use the corrected formulas in §1.

---

## 9 · Stop signal triggers

CC must STOP and report (NOT guess) if:

- D-091 §Adaptive Stop Engine has ambiguous formula NOT covered by §1 of this handoff (e.g. "Wilder's ATR" vs "simple ATR" not specified · or new ambiguity beyond the 2 documented bugs)
- Existing test fixture format for bars is unclear (h/l/o/c naming · timestamp format)
- `tests/v9/systems/test_five_min/` directory doesn't exist (must report instead of creating it silently)
- `five_min_system.py` line 561 location has shifted from current state · STOP and report new line number
- The 5 `ATR_MULTIPLIERS` values from D-091 conflict with Master Summary Sheet 4 · STOP
- 🛑 **Lines 206-208 of `five_min_system.py` were modified by accident** (e.g. via auto-format / multi-line edit / search-replace) — STOP immediately, `git checkout HEAD -- backend/v9/systems/five_min/five_min_system.py`, re-apply line 5 + line 561 edits surgically, retry.

**The 2 D-091 pseudo-code bugs documented in §1 are NOT stop triggers** — they are pre-resolved by this handoff. CC must use the corrected formulas in §1 / §3 directly without asking.

Output format on STOP: `"STOP — <reason> · need Michael decision on <specific question>"`

---

## 10 · Deliverable format CC must produce

1. **Files added** (full paths · A): `backend/v9/systems/five_min/adaptive_stop.py` + `tests/v9/systems/test_five_min/test_adaptive_stop.py`
2. **Files modified** (full paths · M · with diff lines): `backend/v9/systems/five_min/five_min_system.py` (line 5 + line 561)
3. **Commit message:** `feat(s2): adaptive stop engine + 3-layer cap per D-091`
4. **pytest output tail** (last 30 lines · including new test names + counts)
5. **Boot smoke** output: dispatcher init still loads 5 systems
6. **Self-report:**
   - Any TODOs left? (must be empty)
   - Any spec ambiguity encountered? (list)
   - Any forbidden constraint accidentally violated? (own up)
7. **ReadLints output** (paste verbatim)
8. **Sample stop computation** (run `compute_stop` with sample inputs · paste result · for Michael visual review)

---

## 11 · Desktop's deliverable

Desktop, please produce a single MEGA prompt for CC following `docs/templates/MEGA_PROMPT_TEMPLATE.md` (7 fields + Stop signal).

Use this handoff as the spec authority. Inline the file contents listed in §6. The mega prompt is what Michael will paste into Claude Code.

**Length expectation:** ~500-700 lines (includes inlined files). Quality > brevity.

---

*End of handoff · Cursor agent · 2026-05-23 18:50 IL*
