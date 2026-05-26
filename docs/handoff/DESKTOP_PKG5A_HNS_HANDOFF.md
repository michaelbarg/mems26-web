# Pkg 5a · Inverse H&S + H&S Top pattern detectors (chart patterns · Stage 3)

**Authority:** D-091 §Scope #5+#6 · D-091 §Stop layers · D-091 §T2 Haircuts · D-091 §Contract Distribution · Master Sheet 2 (S2_Master_Summary.xlsx · rows pasted by Michael 24/5 16:27 IL)
**Predecessor:** Phase A bundle complete (Pkg 0 + 1 + 2a + 2bc + 3a Streams 1/1.5/2 all G3 PASS) · HEAD = `cf6383e`
**Status:** Spec ready · Cursor handoff for Claude Desktop mega-prompt → CC exec
**Estimated CC time:** ~5-6 hours (largest single-Pkg of Phase A · NEW patterns/ subdir + 2 new detectors + integration + 16+ golden tests)
**Independent of:** all other unbuilt Pkgs (does NOT touch `manager.py` · does NOT modify Pkg 1/2a/2bc/3a code paths · only extends `five_min_system.process_bar` post-OFA chain)

---

## §1 · Why this exists

Pkg 5a adds the **first two chart-pattern detectors** beyond OFA (Reactive/Initiative) to S2:
1. **Inverse H&S** (LONG · reversal · Bulkowski 3,197 trades · throwback 65%)
2. **H&S Top** (SHORT · reversal · Bulkowski 2,800 trades · throwback 68%)

These are the **first Phase A Pkg that uses pattern-measure-based targets** (50% / 0.74× of head-to-neckline depth) rather than R-multiples. The setup_emitter already accepts direct `t1_price`/`t2_price`/`t3_price` arguments (Pkg 3a Stream 2 wiring) — no schema change needed.

Three structural decisions baked into the handoff per Michael 24/5 16:32 IL:
1. **Detection geometry defaults** seeded from Bulkowski encyclopedia + Path B prior art (the deleted `chart_5min/patterns/head_shoulders.py`). All 5 detection parameters are documented as **SHADOW-calibratable** in §4.
2. **Architecture: NEW `backend/v9/systems/five_min/patterns/` subdirectory** — first such subdir in `five_min/`. Will host 5b (`double_bt.py`) and 5c (`flags.py`) later.
3. **Stage 3 + day-type gating** — H&S only fires when `self.mode == DAY_TYPE_MODE` (post-IB) AND `self.current_day_type in {"Neutral_Extreme", "Neutral_Center", "Normal", "Variation"}`. Existing NT skip (line 661) already short-circuits before reaching this code path.

---

## §2 · Spec authority

### §2.A · D-091 §Scope (verbatim)

```
| # | Pattern | Status | Stage | Day Types | Direction | Source |
| 5 | Inverse H&S | NEW in Path A | 3 only | NeuE / NeuC / Norm / NV | LONG | Bulkowski 3,197 trades · throwback 65% |
| 6 | H&S Top | NEW in Path A | 3 only | NeuE / NeuC / Norm / NV | SHORT | Bulkowski 2,800 trades · throwback 68% |
```

### §2.B · D-091 §Stop layers (Layer A · structural anchor)

```
| Pattern | Structural anchor (LONG) | Structural anchor (SHORT) |
| Inverse H&S | 1T below right shoulder | n/a |
| H&S Top | n/a | 1T above right shoulder |
```

### §2.C · D-091 §T2 Haircuts

```
| Pattern | Haircut on full measure |
| Inverse H&S | ×0.74 of head-to-neckline |
| H&S Top | ×0.74 of head-to-neckline |
```

### §2.D · D-091 §Contract Distribution

```
| Pattern family | T1 / T2 / T3 split |
| H&S + Inverse H&S | 33% / 33% / 34% |
```

(Pkg 3c will wire the split. Pkg 5a emits a single setup; downstream Pkg 6 TradeManager will manage the 3-tier exit.)

### §2.E · Master Sheet 2 rows (S2_Master_Summary.xlsx · pasted by Michael 24/5 16:27 IL)

| Field | Inverse H&S | H&S Top |
|---|---|---|
| Status | 🟢 NEW Path A | 🟢 NEW Path A |
| Stage | 3 | 3 |
| Direction | LONG (reversal) | SHORT (reversal) |
| **Entry trigger** | 1T above neckline on close · throwback 65% | 1T below neckline on close · throwback 68% |
| **Stop (Layer A)** | 1T below right shoulder (**NOT** head) | 1T above right shoulder |
| **T1** | **50% of head-to-neckline depth** | **50% of depth** |
| **T2** | **×0.74 of full depth** | **×0.74** |
| **T3** | trail (per Day Type) | trail · BTC suppress final 90min bull day |
| **Split** | 33/33/34 | 33/33/34 |
| **Day Types** | NeuE · NeuC · Norm · NV | NeuE · NeuC · Norm · NV |
| **Source** | Bulkowski 3,197 trades · throwback 65% | Bulkowski 2,800 trades · throwback 68% |

**Notes:**
- "1T" on MES = 0.25 (per Pkg 1 `adaptive_stop.py`).
- "throwback %" is a Bulkowski **post-fire statistic** (informational) · NOT an entry trigger. Entry trigger = single bar close that breaks neckline + 1T.
- **T3 BTC suppress** for H&S Top is deferred to Pkg 7 (STC/BTC modes · DEMO-decided). Pkg 5a emits `t3_price=None` (trail per day type · Pkg 6 enforces).
- **Family multiplier** is already wired in Pkg 1 `adaptive_stop.py`: `ATR_MULTIPLIER["HnS"] = 2.0`. Reused as-is.

---

## §3 · SCOPE · 2 NEW files + 2 modified files + 1 NEW test file

### §3.A · NEW · `backend/v9/systems/five_min/patterns/__init__.py`

Empty marker file (~3 lines). Establishes the `patterns/` subpackage so future Pkg 5b (`double_bt.py`) and Pkg 5c (`flags.py`) can land alongside.

```python
"""Five-min chart pattern detectors (Pkg 5a/5b/5c).

Each module exports `detect_<pattern>(bars)` returning (direction, confidence, info)
matching the signature of `five_min_system._detect_reactive`.
"""
```

### §3.B · NEW · `backend/v9/systems/five_min/patterns/head_shoulders.py`

Two pure-function detectors. **No state, no side effects, no I/O.** Read-only over `bars` (list of dicts with `o/h/l/c/vol` keys per the post-Pkg-2bc bar shape).

```python
"""head_shoulders — Inverse H&S (LONG) + H&S Top (SHORT) detectors per D-091 §5+§6.

Geometric Bulkowski-style detection · 3 swing points · neckline · breakout trigger.
Stage 3 only · gated upstream in five_min_system.process_bar.

Detection geometry defaults (Cursor-seeded per Michael 24/5 16:32 IL · SHADOW-calibratable):
  MIN_BARS_REQUIRED  = 12       # Path B seed · Bulkowski "15-25 bar pattern" short end
  SEARCH_WINDOW      = 30       # Path B seed · last N bars searched for pivots
  PIVOT_LOOKBACK     = 2        # Bulkowski standard
  SHOULDER_SYM_PCT   = 0.05     # 5% of head-to-avg-shoulder distance
  HEAD_MIN_EXT_TICKS = 2        # head must be ≥ 2T beyond both shoulders
  TICK_SIZE          = 0.25     # MES (matches adaptive_stop.py)
"""
from __future__ import annotations
import logging
from typing import List, Dict, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

# ── Module constants · SHADOW-calibratable (do NOT hardcode at call sites) ──
MIN_BARS_REQUIRED = 12
SEARCH_WINDOW = 30
PIVOT_LOOKBACK = 2
SHOULDER_SYM_PCT = 0.05
HEAD_MIN_EXT_TICKS = 2
TICK_SIZE = 0.25

Direction = Literal["LONG", "SHORT"]


def detect_inverse_hns(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Inverse Head & Shoulders (bullish reversal).

    Pattern shape: low(LS) > low(H) < low(RS), shoulders within SHOULDER_SYM_PCT.
    Neckline: max of intermediate highs between LS↔H and H↔RS.
    Fire trigger: last bar close > neckline + 1T.

    Returns:
      (None, 0.0, {}) if no pattern.
      ("LONG", conf, info) if fired. info keys:
        - kind: "INVERSE_HNS"
        - pattern_name: "INVERSE_HNS_LONG"
        - structural_anchor: float (right_shoulder_low - 1T · for adaptive_stop Layer A)
        - pattern_measure: float (positive · = neckline_price - head_price)
        - neckline_price, head_price, left_shoulder_price, right_shoulder_price
        - bar_count: int (LS-to-RS span)
        - stage: 3
    """
    # CC: implement per spec §2.E + detection geometry above.
    # Returning the tuple shape regardless · empty info on no-detect.
    raise NotImplementedError("CC implements")


def detect_hns_top(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Head & Shoulders Top (bearish reversal).

    Pattern shape: high(LS) < high(H) > high(RS), shoulders within SHOULDER_SYM_PCT.
    Neckline: min of intermediate lows.
    Fire trigger: last bar close < neckline - 1T.

    Returns ("SHORT", conf, info) on fire · info keys mirror detect_inverse_hns.
    pattern_measure = head_price - neckline_price (positive).
    structural_anchor = right_shoulder_high + 1T.
    """
    raise NotImplementedError("CC implements")


# ── Internal helpers (CC may add) ──
# def _find_pivots(bars, lookback): ...
# def _swing_highs(bars, lookback): ...
# def _swing_lows(bars, lookback): ...
# def _shoulders_symmetric(left, head, right): ...
# def _head_extends_beyond(head, shoulders, direction): ...
```

**Confidence formula** (uniform with existing detectors): `conf = 0.60 + 0.20 * shoulder_symmetry_score + 0.20 * head_extension_score`, clipped to [0, 1]. Where:
- `shoulder_symmetry_score` = `1 - (|LS - RS| / (head_to_avg_shoulder_distance)) / SHOULDER_SYM_PCT` (1.0 = perfectly symmetric · 0.0 = at tolerance edge)
- `head_extension_score` = `min(1.0, (head_extension_ticks / HEAD_MIN_EXT_TICKS - 1) / 4)` (1.0 = head extends ≥ 6T beyond shoulders)

### §3.C · MODIFY · `backend/v9/systems/five_min/output_schema.py`

Extend the `PatternName` Literal · 1-line change.

**Existing (line 13):**
```python
PatternName = Literal['REACTIVE_LONG', 'REACTIVE_SHORT', 'INITIATIVE_LONG', 'INITIATIVE_SHORT']
```

**New (line 13):**
```python
PatternName = Literal[
    'REACTIVE_LONG', 'REACTIVE_SHORT',
    'INITIATIVE_LONG', 'INITIATIVE_SHORT',
    'INVERSE_HNS_LONG', 'HNS_TOP_SHORT',
]
```

### §3.D · MODIFY · `backend/v9/systems/five_min/five_min_system.py`

**3 edits · scope-limited · do NOT touch lines 215-217 (chronic toxicity block · byte-identical per Pkg 0 rule).**

#### Edit 1 · Import at top of file (after existing pattern imports)

After the existing `_detect_reactive` / `_detect_initiative` are defined inline (lines ~390-560), no import is needed there. Add at module top, after existing imports:

```python
from backend.v9.systems.five_min.patterns.head_shoulders import (
    detect_inverse_hns,
    detect_hns_top,
)
```

#### Edit 2 · `process_bar` · insert chart-pattern chain after line 676

**Current (lines 673-678):**
```python
        # Run pattern detectors
        direction, conf, info = self._detect_reactive(self._bar_buffer)
        if not direction:
            direction, conf, info = self._detect_initiative(self._bar_buffer)

        if direction:
```

**Replace with (insert 12 lines between lines 676 and 678):**
```python
        # Run pattern detectors
        direction, conf, info = self._detect_reactive(self._bar_buffer)
        if not direction:
            direction, conf, info = self._detect_initiative(self._bar_buffer)

        # Pkg 5a · chart patterns (Stage 3 + day-type gated · D-091 §5+§6)
        if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
            if self.current_day_type in (
                "Neutral_Extreme", "Neutral_Center", "Normal", "Variation",
            ):
                direction, conf, info = detect_inverse_hns(self._bar_buffer)
                if not direction:
                    direction, conf, info = detect_hns_top(self._bar_buffer)

        if direction:
```

#### Edit 3 · Fork stop + targets when chart pattern fired

The existing `if direction:` block (line 678 onward) assumes OFA family-mapping (`kind == "REACTIVE"` → "Reactive" else "OFA"). Chart patterns need:
1. `family = "HnS"` (multiplier 2.0 · already in `adaptive_stop.ATR_MULTIPLIER`)
2. `structural_anchor` from `info["structural_anchor"]` (NOT `bar.low`/`bar.high`)
3. T1/T2 from pattern measure (NOT from `compute_targets_for_day_type` R-multiples)

**Insert at line 685 (just before `family = "Reactive" if kind == "REACTIVE" else "OFA"`):**
```python
            # Pkg 5a · chart pattern routing (kinds: INVERSE_HNS / HNS_TOP)
            if kind in ("INVERSE_HNS", "HNS_TOP"):
                family = "HnS"
                # Structural anchor comes from detector (right shoulder ± 1T)
                structural_anchor = info["structural_anchor"]
            else:
                family = "Reactive" if kind == "REACTIVE" else "OFA"
                structural_anchor = (
                    bar.get("l", entry_price) if direction == "LONG"
                    else bar.get("h", entry_price)
                )
```

**And remove the current 2 lines (line 686 `family = ...` and line 683 `structural_anchor = ...`).** Replace with the branch above.

**In the targets block (line ~759 onward · the `try:` for setup_emitter):** add a fork for chart-pattern targets BEFORE calling `compute_targets_for_day_type`:

**Insert after line 750 (`pattern_name = f"{kind}_{direction}"`)**, replacing the existing day_type_targets logic:
```python
                pattern_name = f"{kind}_{direction}"

                # Pkg 5a · chart patterns use pattern-measure targets (NOT R-based)
                if kind in ("INVERSE_HNS", "HNS_TOP"):
                    pm = info["pattern_measure"]  # positive (head-to-neckline depth)
                    sign = 1.0 if direction == "LONG" else -1.0
                    t1_price = entry_price + sign * 0.50 * pm
                    t2_price = entry_price + sign * 0.74 * pm
                    t3_price = None  # trail per day type · Pkg 6 enforces
                else:
                    # Existing OFA path · resolve targets per day_type (D-091.Q1)
                    from backend.v9.systems.day_type.day_type_targets import compute_targets_for_day_type
                    _targets = compute_targets_for_day_type(
                        day_type=self.current_day_type,
                        entry_price=entry_price,
                        stop_price=stop_price,
                        direction=direction,
                    )
                    t1_risk = abs(entry_price - stop_price)
                    if _targets is not None:
                        t1_price = _targets["t1_price"]
                        t2_price = _targets.get("t2_price") or (
                            (entry_price + 2 * t1_risk) if direction == "LONG"
                            else (entry_price - 2 * t1_risk)
                        )
                        t3_price = _targets.get("t3_price")
                    else:
                        t1_price = (entry_price + t1_risk) if direction == "LONG" else (entry_price - t1_risk)
                        t2_price = (entry_price + 2 * t1_risk) if direction == "LONG" else (entry_price - 2 * t1_risk)
                        t3_price = None
```

**Constraint:** the existing OFA path (else branch) is **byte-identical** to the current lines 752-770. Diff should show only the new `if kind in (...)` block prepended + 4-line indent of the existing OFA path.

### §3.E · NEW · `tests/v9/systems/test_five_min/test_head_shoulders.py`

16+ golden tests · `pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q` should be 16 pass. See §5.

---

## §4 · Detection geometry · SHADOW-calibratable defaults

Per Michael 24/5 16:32 IL · "OK · use defaults":

| # | Param | Default | Source | Reason |
|---|---|---|---|---|
| 1 | `MIN_BARS_REQUIRED` | **12** | Path B prior art | Bulkowski "15-25 bar pattern" short end |
| 2 | `SEARCH_WINDOW` | **30** | Path B prior art | sufficient for 25-bar pattern + 5-bar slack |
| 3 | `PIVOT_LOOKBACK` | **2** | Bulkowski standard | matches Path B + general TA literature |
| 4 | `SHOULDER_SYM_PCT` | **0.05** (5%) | Bulkowski encyclopedia "similar shoulders" | tighter than Path B's 0.20 absolute (which was unit-ambiguous) |
| 5 | `HEAD_MIN_EXT_TICKS` | **2** (= 0.50 on MES) | Bulkowski "noticeable extension" | minimum for visual asymmetry |

**Calibration note (include verbatim in module docstring):**
> These 5 constants are **SHADOW-calibratable**. Adjust based on hit-rate analysis after ≥20 H&S fires per direction. Re-validate via the 16-test golden suite — any change must keep all 16 green or update fixtures with rationale. Do NOT hardcode at call sites.

---

## §5 · Golden tests (16 minimum)

File: `tests/v9/systems/test_five_min/test_head_shoulders.py`

Each test uses an inline bar fixture (list of dicts with `o/h/l/c/vol`). Fixtures are deterministic · CC composes them per the geometric criteria.

| # | Test name | Fixture shape | Expected |
|---|---|---|---|
| 1 | `test_inverse_hns_classic_symmetric` | LS low=4500 · H low=4490 · RS low=4499 · neckline=4510 · last close=4511 (>neckline+1T) | direction="LONG" · confidence≥0.7 · info["kind"]="INVERSE_HNS" · pattern_measure=20.0 · structural_anchor=4498.75 (4499 - 0.25) |
| 2 | `test_hns_top_classic_symmetric` | LS high=4500 · H high=4510 · RS high=4501 · neckline=4490 · last close=4489 (<neckline-1T) | direction="SHORT" · pattern_measure=20.0 · structural_anchor=4501.25 |
| 3 | `test_inverse_hns_asymmetric_shoulders_rejected` | LS=4500 · H=4490 · RS=4480 (10% asymmetric vs head dist) | direction=None |
| 4 | `test_hns_top_asymmetric_shoulders_rejected` | shoulders differ > 5% | direction=None |
| 5 | `test_inverse_hns_head_not_lowest_rejected` | H=4495 (not below LS=4500) | direction=None |
| 6 | `test_hns_top_head_not_highest_rejected` | H not above shoulders | direction=None |
| 7 | `test_inverse_hns_no_breakout_rejected` | All pivots correct but last close = 4510 (at neckline · NOT +1T above) | direction=None |
| 8 | `test_hns_top_no_breakout_rejected` | Last close at neckline · not -1T below | direction=None |
| 9 | `test_inverse_hns_insufficient_bars` | bars=8 (< MIN_BARS_REQUIRED=12) | direction=None |
| 10 | `test_hns_top_head_extension_below_threshold` | head only 1T (= 0.25) beyond shoulders (< HEAD_MIN_EXT_TICKS=2) | direction=None |
| 11 | `test_inverse_hns_confidence_perfect_pattern` | perfectly symmetric shoulders · head 6T beyond | confidence==1.0 |
| 12 | `test_hns_top_confidence_marginal_pattern` | shoulders at 5% edge · head 2T extension | 0.60 ≤ confidence < 0.70 |
| 13 | `test_inverse_hns_returns_structural_anchor` | classic LONG fixture | info["structural_anchor"] == right_shoulder_low - 0.25 (verifies 1T below RS) |
| 14 | `test_hns_top_returns_structural_anchor` | classic SHORT fixture | info["structural_anchor"] == right_shoulder_high + 0.25 |
| 15 | `test_inverse_hns_pattern_measure_positive` | classic fixture · head=4490 · neckline=4510 | info["pattern_measure"] == 20.0 (positive · = neckline - head) |
| 16 | `test_hns_top_pattern_measure_positive` | head=4510 · neckline=4490 | info["pattern_measure"] == 20.0 (positive · = head - neckline) |

**Additional integration tests (in `test_five_min_day_type_wiring.py` extend or new file):**
| # | Test name | Coverage |
|---|---|---|
| 17 | `test_hns_skipped_on_nt_day_type` | day_type=Nontrend → early-skip line 661 hit · H&S not called |
| 18 | `test_hns_skipped_on_tn_day_type` | day_type=Trend_Normal (not in {NeuE,NeuC,Norm,NV}) → H&S not called |
| 19 | `test_hns_skipped_on_first_hour_mode` | mode=FIRST_HOUR_TACTICAL → H&S not called even on NeuE day |
| 20 | `test_inverse_hns_emits_t1setup_on_neuc` | mode=DAY_TYPE_MODE · day_type=Neutral_Center · LONG fixture · expect `T1Setup(pattern_name="INVERSE_HNS_LONG", t1_price=..., t2_price=..., t3_price=None, time_stop_minutes=30)` |

---

## §6 · Acceptance criteria · G3 PASS gate

CC outputs `STOP — <reason>` if any of these can NOT be achieved without violating a §7 constraint.

1. `pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q` → **16 passed**
2. `pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q` → all green (regression check on existing 8 + new 4 integration tests)
3. `pytest tests/v9/systems/ -q` → **at least 588 passed · 1 skipped** (= 572 baseline + 16 new H&S unit tests + 4 wiring tests = 592 · allow ±2 for fixture variance)
4. `pytest backend/v9/tests/ -q` → **531 passed · 2 skipped** (no regression)
5. `pytest backend/v9/systems/five_min/tests/ -q` → **70 passed · 8 failed** (the F4 pre-existing failures · NO new failures introduced)
6. `ReadLints` on all 5 changed files → 0 new errors
7. `git diff backend/v9/systems/five_min/five_min_system.py` → verify lines 215-217 byte-identical (chronic toxicity block · Pkg 0 rule)
8. `backend.main` imports cleanly (smoke test: `python -c "from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns; print('OK')"` → "OK")
9. Smoke test on classic fixture: `detect_inverse_hns(<classic_bars>)` → returns `("LONG", >=0.7, {kind: "INVERSE_HNS", ...})`
10. `PatternName` Literal includes the 2 new values · `T1Setup(pattern_name="INVERSE_HNS_LONG", ...)` validates without error

---

## §7 · Constraints (must NOT violate)

- **No silent excepts.** Every `except` must include `logger.warning("[head_shoulders] <message>", ...)` rate-limited (1/min via `time.monotonic()` like the NT skip pattern).
- **No `return None` without prior log** at info-level (e.g. log "no LS pivot found" on early-return paths is OK if rate-limited).
- **No new dependencies** (pip install / package.json). Use stdlib `typing`, `logging`, `time`. No `numpy`/`pandas`.
- **No "while I'm here" refactors** outside the 5 files listed in §3. Specifically:
  - Do NOT change `_detect_reactive` / `_detect_initiative` signatures
  - Do NOT change `T1Setup` schema fields other than `PatternName` Literal
  - Do NOT change `compute_targets_for_day_type` (used only on OFA path)
  - Do NOT touch `backend/v9/systems/day_type/*` (Pkg 3a frozen)
  - Do NOT touch `backend/v9/systems/footprint/*` (Pkg 2bc frozen)
  - Do NOT touch `manager.py` (Pkg 6 territory)
- **Hardcoded values forbidden** — the 5 detection constants (`MIN_BARS_REQUIRED`, `SEARCH_WINDOW`, `PIVOT_LOOKBACK`, `SHOULDER_SYM_PCT`, `HEAD_MIN_EXT_TICKS`) MUST live as module-level UPPER_CASE constants at top of `head_shoulders.py` per §3.B docstring. Tests reference them by import, NOT by literal duplication.
- **Lines 215-217 of `five_min_system.py` MUST stay byte-identical** (chronic toxicity block per Pkg 0):
  ```
  # Delegate to existing chart_5min detector for pattern detection
  # (integration point — full wiring in future prompts)
  return None
  ```
  Verify with: `sed -n '/Delegate to existing chart_5min detector/,/return None$/p' backend/v9/systems/five_min/five_min_system.py`
- **Stage 3 + day-type gating MUST be checked at the integration layer (in `five_min_system.process_bar`), NOT inside the detector functions.** Rationale: detectors are pure functions · gating is system context.
- **`t3_price=None` is INTENTIONAL** for H&S · do NOT compute `t3_price = entry + sign * 1.618 * R` (that was Path B's Fibonacci approach · superseded by D-091's "trail per Day Type · Pkg 6 enforces").
- **`time_stop_minutes` is auto-derived** from `day_type` via existing `get_time_stop()` in `setup_emitter.py` · do NOT pass `time_stop_minutes` from detector or integration layer.

---

## §8 · Forbidden zones

```
🛑 DO NOT modify:
  - backend/v9/systems/day_type/*           (Pkg 3a frozen)
  - backend/v9/systems/footprint/*          (Pkg 2bc frozen)
  - backend/v9/systems/five_min/adaptive_stop.py    (Pkg 1 frozen · just IMPORT it)
  - backend/v9/systems/five_min/setup_emitter.py    (Pkg 3a S2 frozen · just CALL it)
  - backend/v9/systems/five_min/time_stop_mapper.py (Pkg 3a S2 frozen)
  - backend/v9/systems/woodies/*            (S4 territory)
  - backend/v9/services/trade_manager/*     (Pkg 6 territory)
  - bridge/, sc_study/, frontend/           (out of scope)
  - backend/v9/systems/five_min/five_min_system.py lines 1-214 and lines 218+ outside the 3 edits in §3.D

🛑 DO NOT add:
  - Any inline detection in five_min_system.py (use the patterns/ subdir)
  - Throwback waiting logic (entry fires on neckline break · throwback is a Bulkowski stat · NOT a trigger)
  - T3 numeric value for H&S (it's trail · t3_price MUST be None)
  - News-event filtering (DEMO-1 territory)
```

---

## §9 · Pre-flight · current code state (verified by Cursor 24/5 16:30 IL)

### §9.A · Files that exist (read-only · do NOT modify outside scope)

```
backend/v9/systems/five_min/
├── __init__.py
├── adaptive_stop.py            # Pkg 1 · ATR_MULTIPLIER["HnS"]=2.0 ✅
├── choppiness.py
├── confluence.py
├── cot_amt.py
├── first_hour_buffer.py
├── first_hour_matrix.py
├── five_min_system.py          # 821 LOC · 3 edits per §3.D
├── output_schema.py            # 42 LOC · 1 edit per §3.C
├── q0_dispatcher.py
├── quality_tier.py
├── setup_emitter.py            # 107 LOC · Pkg 3a S2 · do NOT modify
├── setup_wrapper.py
├── sr_proximity.py
└── time_stop_mapper.py         # Pkg 3a S2 · do NOT modify
```

No `patterns/` subdirectory exists yet. Pkg 5a creates it.

### §9.B · `adaptive_stop.py::ATR_MULTIPLIER` (excerpt · already includes "HnS")

```python
ATR_MULTIPLIER = {
    "Reactive":  1.0,
    "OFA":       1.5,
    "Flag":      1.5,
    "Double_BT": 2.0,
    "HnS":       2.0,   # ← Pkg 5a uses this
}
```

### §9.C · `setup_emitter.emit_t1_setup` signature (already accepts pattern-measure targets)

```python
def emit_t1_setup(
    pattern_name: PatternName,
    direction: Literal['LONG', 'SHORT'],
    entry_price: float,
    stop_price: float,
    t1_price: float,            # ← Pkg 5a passes pattern-measure 50%
    t2_price: float,            # ← Pkg 5a passes pattern-measure × 0.74
    bar_index: int,
    *,
    day_type: Optional[str] = None,
    t3_price: Optional[float] = None,    # ← Pkg 5a passes None (trail)
    current_price: Optional[float] = None,
    tpo_data: Optional[dict] = None,
) -> Optional[T1Setup]:
```

### §9.D · Prior art (informational · DO NOT copy verbatim — D-091 supersedes target logic)

`backend/v9/systems/chart_5min/patterns/head_shoulders.py` and `inverse_head_shoulders.py` existed in Path B (deleted in `1c805ea` per Pkg 0). Their **geometric detection structure** (find_pivots → swing_highs/lows → 3-consecutive-swing-check → neckline → completion threshold) is a sound reference for the algorithm shape. Recoverable via `git show 1c805ea~1:backend/v9/systems/chart_5min/patterns/head_shoulders.py`.

**What to REUSE (concept only · re-implement clean):**
- 3-consecutive-pivot loop pattern
- Neckline = min/max of intermediate lows/highs
- Stop = right shoulder
- Confidence base 0.6 + completion scaling

**What to REJECT (D-091 supersedes):**
- Path B used Fibonacci targets (0.618R/1.0R/1.618R) — **DO NOT use**. Use pattern-measure 50% / ×0.74 / None.
- Path B used `prices_near(ls, rs, 0.20)` with unclear units — **REPLACE** with `SHOULDER_SYM_PCT` (5% relative).
- Path B's `completion = 0.4` proxy — **REPLACE** with strict close-through-neckline + 1T (matches Master Sheet 2 entry trigger).
- Path B stop was raw right shoulder — **CHANGE** to `right_shoulder ± 1T` per D-091 §Stop layers.

### §9.E · Test baseline (24/5 16:30 IL · HEAD = `cf6383e`)

- `tests/v9/systems/` → 572 passed · 1 skipped
- `backend/v9/tests/` → 531 passed · 2 skipped
- `backend/v9/systems/five_min/tests/` → 70 passed · 8 failed (F4 pre-existing · NOT Pkg 5a's responsibility · DO NOT "fix" these as a side effect)
- 1 uncommitted file: `backend/v9/systems/five_min/tests/test_time_stop_mapper.py` (Cursor hand-fix from Stream 2 G3) · Pkg 5a does NOT touch this file · keep it dirty or commit before starting (operator's choice)

---

## §10 · Validation recipe (CC runs after implementation)

```bash
# 1. Lint check
python -m pyflakes backend/v9/systems/five_min/patterns/head_shoulders.py
python -m pyflakes backend/v9/systems/five_min/five_min_system.py

# 2. New tests
pytest tests/v9/systems/test_five_min/test_head_shoulders.py -v

# 3. No regression on existing five_min suite
pytest tests/v9/systems/test_five_min/ -q

# 4. No regression on backend/v9/tests
pytest backend/v9/tests/ -q --no-header

# 5. Full systems suite
pytest tests/v9/systems/ -q

# 6. Chronic toxicity block byte-identical
sed -n '/Delegate to existing chart_5min detector/,/return None$/p' backend/v9/systems/five_min/five_min_system.py
# expect 3 lines · content unchanged from cf6383e baseline

# 7. Smoke
python -c "
from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns, detect_hns_top
print('imports OK')
# classic Inv H&S fixture
bars = [
    {'o':4505,'h':4506,'l':4504,'c':4505,'vol':1000},  # bar 0
    {'o':4505,'h':4505,'l':4500,'c':4501,'vol':1200},  # LS low @ 4500
    {'o':4501,'h':4509,'l':4501,'c':4508,'vol':1100},  # rise to neckline
    {'o':4508,'h':4510,'l':4506,'c':4509,'vol':900},
    {'o':4509,'h':4509,'l':4494,'c':4495,'vol':1500},  # drop to head
    {'o':4495,'h':4495,'l':4490,'c':4492,'vol':1800},  # head low @ 4490
    {'o':4492,'h':4510,'l':4492,'c':4510,'vol':1300},  # rise to neckline
    {'o':4510,'h':4510,'l':4508,'c':4509,'vol':800},
    {'o':4509,'h':4510,'l':4498,'c':4499,'vol':1100},  # drop to RS
    {'o':4499,'h':4500,'l':4499,'c':4499,'vol':1000},  # RS low @ 4499
    {'o':4499,'h':4509,'l':4499,'c':4509,'vol':1100},  # rise toward neckline
    {'o':4509,'h':4511,'l':4509,'c':4511,'vol':1400},  # breakout · close=4511 (>4510+0.25)
]
d, c, info = detect_inverse_hns(bars)
print(f'detected: {d} conf={c:.2f} measure={info.get(\"pattern_measure\")}')
assert d == 'LONG'
assert info['pattern_measure'] == 20.0
print('smoke OK')
"
```

---

## §11 · Stop signals (CC outputs `STOP — <reason>` and halts)

CC must STOP and report (do NOT guess · do NOT add `TODO: ask Michael`) when:

1. **Cannot construct a fixture** that exercises a §5 golden test (e.g. test 11 "perfect pattern · confidence=1.0" requires exact numeric path · if confidence formula can't reach 1.0, STOP).
2. **D-091 vs Master Sheet 2 conflict** — D-091 line 145 says "1T below right shoulder" but `right_shoulder` in code is a swing-low bar with `low` and `close` — STOP and ask: anchor on `.low` or on `.close`?
3. **Forbidden file in edit list** — any file outside the 5 listed in §3 (this would indicate a misread).
4. **Lines 215-217 modification proposed** — even if `sed` check would still pass, ANY edit through those lines = STOP.
5. **Detector function I/O** — if implementation requires DB read, network call, or file I/O — STOP (detectors are pure).
6. **Existing test regression** — if any test in `tests/v9/systems/test_five_min/` or `backend/v9/tests/` that was green at `cf6383e` becomes red after Pkg 5a — STOP with diff vs baseline.
7. **`PatternName` Literal grows beyond 6 values** — if you discover you need a 7th pattern name to make this work, STOP.

For any other ambiguity: STOP. The pre-LIVE protocol forbids silent assumptions.

---

## §12 · Deliverable format (CC outputs after completion)

1. **Files changed** (full paths · A/M/D):
   - `A backend/v9/systems/five_min/patterns/__init__.py`
   - `A backend/v9/systems/five_min/patterns/head_shoulders.py`
   - `M backend/v9/systems/five_min/output_schema.py` (1 line)
   - `M backend/v9/systems/five_min/five_min_system.py` (3 edits)
   - `A tests/v9/systems/test_five_min/test_head_shoulders.py`

2. **Commit message:**
   ```
   feat(s2): Inv H&S + H&S Top chart pattern detectors per D-091 §5+§6

   - NEW backend/v9/systems/five_min/patterns/__init__.py
   - NEW backend/v9/systems/five_min/patterns/head_shoulders.py
     · detect_inverse_hns (LONG · reversal) + detect_hns_top (SHORT · reversal)
     · 5 SHADOW-calibratable detection constants
     · Pattern-measure targets (50% T1 · 0.74× T2 · trail T3)
     · Structural anchor = right shoulder ± 1T per D-091
   - MODIFY output_schema.py · extend PatternName Literal (+ 2 values)
   - MODIFY five_min_system.py · 3 edits
     1. import detectors
     2. process_bar Stage 3 + day-type gated chart-pattern chain
     3. fork stop family + targets for kind in ("INVERSE_HNS", "HNS_TOP")
   - NEW tests/v9/systems/test_five_min/test_head_shoulders.py · 16+ golden tests

   Pkg 5a · NeuE/NeuC/Norm/NV day types · emit-only (Pkg 6 enforces).
   Sources: Bulkowski 3,197 Inv H&S trades + 2,800 H&S Top trades · Master Sheet 2.

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   ```

3. **Self-report:**
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly · if any was resolved by interpretation rather than STOP signal, document the call)
   - Any forbidden constraint accidentally touched? (own up)
   - Lines 215-217 still byte-identical? (yes/no with diff)
   - Detection constants at module top · referenced by tests via import? (yes/no)

4. **ReadLints output** (paste verbatim · 5 files)

5. **pytest output** (paste verbatim · tail 30 lines for each: `test_head_shoulders.py` · `test_five_min_day_type_wiring.py` · `tests/v9/systems/` · `backend/v9/tests/`)

---

## §13 · Estimated CC time

| Sub-task | Estimated | Notes |
|---|---|---|
| Read existing patterns prior art (`git show 1c805ea~1:backend/v9/systems/chart_5min/patterns/head_shoulders.py`) | 10 min | Recover concept · do NOT copy targets |
| Write `patterns/__init__.py` + `patterns/head_shoulders.py` skeleton (constants + signatures) | 20 min | Mostly structure |
| Implement `_find_pivots` · `_swing_highs/lows` helpers | 30 min | Path B has reference impl |
| Implement `detect_inverse_hns` (LONG) | 45 min | Main logic |
| Implement `detect_hns_top` (SHORT · mirror) | 30 min | Reuse helpers |
| Modify `output_schema.py` (1-line Literal extension) | 5 min | |
| Modify `five_min_system.py` 3 edits | 30 min | Surgical |
| Write 16 golden tests | 90 min | Fixture composition is the slow part |
| Run validation recipe · iterate on failures | 60 min | Expect 2-3 iterations |
| **Total** | **~5-6 hours CC time** | + Cursor G3 ~30 min |

---

## §14 · Post-G3 PASS unlocks

| Unlocked | Why |
|---|---|
| **Pkg 5b** (Double Bottom + Top) | Same patterns/ subdir + same emit pattern · CC handoff will be a near-clone of this one |
| **Pkg 5c** (Bull/Bear Flag) | Same · plus Brooks H2/L2 entry trigger variant |
| Phase A is **4 Pkgs from complete** | 5a · 5b · 5c · 3b · 3c (and Pkg 4a/4b dep on 3) · then Pkg 8 + Pkg 6 |
| Coverage of NeuE/NeuC/Norm/NV becomes meaningful | These 4 day types had only OFA before · now get reversal patterns |

---

*End of Pkg 5a handoff · Cursor agent · 2026-05-24 16:35 IL*
*Spec authority: D-091 §5+§6 + Master Sheet 2 (Michael paste 24/5 16:27)*
*Detection geometry defaults: Bulkowski + Path B seed (Michael "OK" 24/5 16:32)*
*Awaiting Claude Desktop mega-prompt drafting → CC execution → Cursor G3 review*
