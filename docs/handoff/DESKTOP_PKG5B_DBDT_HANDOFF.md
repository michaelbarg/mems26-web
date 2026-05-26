# Pkg 5b · Double Bottom (Eve&Eve) + Double Top (Adam&Adam) pattern detectors (chart patterns · Stage 3)

**Authority:** D-091 §Scope #7+#8 · D-091 §Stop layers · D-091 §T2 Haircuts · D-091 §Contract Distribution · Master Sheet 2 (S2_Master_Summary.xlsx · rows pasted by Michael 24/5 17:57 IL)
**Predecessor:** Pkg 5a G3 PASS (Inv H&S + H&S Top · commit `7ffab50` · 24/5 17:45 IL) · HEAD = `7ffab50`
**Status:** Spec ready · Cursor handoff for Claude Desktop mega-prompt → CC exec
**Estimated CC time:** ~4-5 hours (near-clone of 5a · adds Eve/Adam variant filter · `patterns/` subdir already exists)
**Independent of:** all other unbuilt Pkgs (does NOT touch `manager.py` · does NOT modify Pkg 1/2a/2bc/3a/5a code paths · only extends `five_min_system.process_bar` chart-pattern chain · the H&S detectors stay in place untouched)

---

## §1 · Why this exists

Pkg 5b adds **two more chart-pattern detectors** to S2, completing the reversal-pattern set on `NeuE/NeuC/Norm/NV` day types:

1. **Double Bottom (Eve&Eve)** (LONG · reversal · Bulkowski 952 Eve&Eve trades · throwback 64% · split T1 hint deferred to Pkg 7)
2. **Double Top (Adam&Adam)** (SHORT · reversal · Bulkowski AA rank 5/21 · BTC override TN bull final 90min hint deferred to Pkg 7)

Architecturally identical to Pkg 5a — same `patterns/` subdir, same `(direction, conf, info)` signature, same pattern-measure target math, same gating. The only **new** concept is the **variant filter**: Eve (rounded · wide cluster of bars at extreme) vs Adam (sharp · narrow cluster).

Two structural decisions baked into the handoff per Michael 24/5 17:57 IL:
1. **Detection geometry defaults** seeded from Bulkowski encyclopedia + Path B prior art (the deleted `chart_5min/patterns/double_bottom.py` + `double_top.py`). All 9 detection parameters are documented as **SHADOW-calibratable** in §4.
2. **Eve&Eve / Adam&Adam variant restriction is enforced inside the detector** (per D-091 §Scope — DB row says explicitly "Double Bottom (Eve&Eve)" not "any DB"). The variant filter rejects Adam&Adam-shaped Double Bottoms and Eve&Eve-shaped Double Tops.

---

## §2 · Spec authority

### §2.A · D-091 §Scope (verbatim)

```
| # | Pattern                  | Status        | Stage | Day Types               | Direction | Source                              |
| 7 | Double Bottom (Eve&Eve)  | NEW in Path A | 3 only | NV / NeuE / NeuC / Norm | LONG      | Bulkowski 952 trades · throwback 64% |
| 8 | Double Top (Adam&Adam)   | NEW in Path A | 3 only | NV / NeuE / NeuC / Norm | SHORT     | Bulkowski AA rank 5/21              |
```

### §2.B · D-091 §Stop layers (Layer A · structural anchor)

```
| Pattern        | Structural anchor (LONG)             | Structural anchor (SHORT)         |
| Double Bottom  | 1T below lower of two bottoms        | n/a                               |
| Double Top     | n/a                                  | 1T above higher of two peaks      |
```

### §2.C · D-091 §T2 Haircuts

```
| Pattern                 | Haircut on full measure |
| Double Bottom (Eve&Eve) | ×0.66 of full height    |
| Double Top (Adam&Adam)  | ×0.74 of full height    |
```

**Note:** DB and DT have **different** haircuts (DB=0.66, DT=0.74). This is per D-091 + Master Sheet 2 — Eve bottoms have shallower target due to slower-developing breakouts; Adam peaks have sharper measured-move follow-through.

### §2.D · D-091 §Contract Distribution

```
| Pattern family               | T1 / T2 / T3 split |
| Double Bottom + Double Top   | 33% / 33% / 34%    |
```

(Pkg 3c will wire the split. Pkg 5b emits a single setup; downstream Pkg 6 TradeManager will manage the 3-tier exit.)

### §2.E · Master Sheet 2 rows (S2_Master_Summary.xlsx · pasted by Michael 24/5 17:57 IL)

| Field | Double Bottom (Eve&Eve) | Double Top (Adam&Adam) |
|---|---|---|
| Status | 🟢 NEW Path A | 🟢 NEW Path A |
| Stage | 3 | 3 |
| Direction | LONG (reversal) | SHORT (reversal) |
| **Entry trigger** | 1T above neckline · throwback 64% (split T1) | 1T below neckline · BTC override TN bull final 90min |
| **Stop (Layer A)** | 1T below lower bottom | 1T above higher peak |
| **T1** | 50% of pattern height | 50% of height |
| **T2** | ×0.66 of full height | ×0.74 |
| **T3** | trail under HL closes | trail |
| **Split** | 33/33/34 | 33/33/34 |
| **Day Types** | NV · NeuE · NeuC · Norm | NV · NeuE · NeuC · Norm |
| **Source** | Bulkowski 952 trades Eve&Eve | Bulkowski AA rank 5/21 |

**Notes:**
- "1T" on MES = 0.25 (per Pkg 1 `adaptive_stop.py`).
- **"throwback 64% (split T1)"** for DB is a Bulkowski post-fire statistic + an entry execution hint — defer to Pkg 7 (entry-execution strategy). Pkg 5b emits a single setup on initial neckline break + 1T.
- **"BTC override TN bull final 90min"** for DT — deferred to Pkg 7 (STC/BTC modes · DEMO-decided). Pkg 5b emits regardless · downstream filter applies on TN bull final 90min if BTC active.
- **Variant restriction (Eve&Eve / Adam&Adam) is part of detection**, not a post-fire filter. See §4.C.
- **Family multiplier** is already wired in Pkg 1 `adaptive_stop.py`: `ATR_MULTIPLIER["Double_BT"] = 2.0`. Reused as-is.
- **Neckline definition** (Bulkowski + Path B): for DB the neckline = **highest** swing high between the two bottoms; for DT the neckline = **lowest** swing low between the two peaks.
- **Pattern height = full vertical depth**: DB = `neckline − min(bottom1, bottom2)`; DT = `max(peak1, peak2) − neckline`. Always positive.

---

## §3 · SCOPE · 1 NEW file + 2 modified files + 1 NEW test file + 1 MODIFIED test file

### §3.A · NEW · `backend/v9/systems/five_min/patterns/double_top_bottom.py`

Two pure-function detectors in one file (mirrors `head_shoulders.py` from Pkg 5a). **No state, no side effects, no I/O.** Read-only over `bars` (list of dicts with `o/h/l/c/v` keys).

```python
"""double_top_bottom — Double Bottom (Eve&Eve) LONG + Double Top (Adam&Adam) SHORT per D-091 §7+§8.

Geometric Bulkowski-style detection · 2 swing extremes + intermediate neckline + breakout trigger
+ variant filter (Eve = rounded/wide cluster · Adam = sharp/narrow cluster).

Stage 3 only · gated upstream in five_min_system.process_bar.

Detection geometry defaults (Cursor-seeded per Michael 24/5 17:57 IL · SHADOW-calibratable):
  MIN_BARS_REQUIRED          = 14    # Path B used 8 · widened for cluster-bar analysis room
  SEARCH_WINDOW              = 30    # Path B used 20 · widened to match H&S 5a
  PIVOT_LOOKBACK             = 2     # Bulkowski standard · matches H&S 5a
  BOTTOMS_SYM_PCT            = 0.05  # |b1-b2|/pattern_height ≤ 5%
  MIN_BARS_BETWEEN_EXTREMES  = 5     # min span between bottom1 and bottom2 (or peak1 and peak2)
  EXTREME_CLUSTER_TOL_PCT    = 0.10  # bars within 10% of pattern_height of the extreme count as "near"
  EVE_MIN_CLUSTER_BARS       = 4     # Eve: ≥4 consecutive-or-nearby bars near each bottom
  ADAM_MAX_CLUSTER_BARS      = 3     # Adam: ≤3 bars near each peak (sharp)
  TICK_SIZE                  = 0.25  # MES

These 9 constants are SHADOW-calibratable. Adjust based on hit-rate analysis after
≥20 DB and ≥20 DT fires. Re-validate via the 18-test golden suite — any change must
keep all 18 green or update fixtures with rationale.
"""
from __future__ import annotations
import logging
import time
from typing import List, Dict, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

# ── Module constants · SHADOW-calibratable (do NOT hardcode at call sites) ──
MIN_BARS_REQUIRED = 14
SEARCH_WINDOW = 30
PIVOT_LOOKBACK = 2
BOTTOMS_SYM_PCT = 0.05
MIN_BARS_BETWEEN_EXTREMES = 5
EXTREME_CLUSTER_TOL_PCT = 0.10
EVE_MIN_CLUSTER_BARS = 4
ADAM_MAX_CLUSTER_BARS = 3
TICK_SIZE = 0.25

Direction = Literal["LONG", "SHORT"]


def detect_double_bottom(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Double Bottom Eve&Eve (bullish reversal).

    Pattern shape:
      - Two swing lows of approximately equal price (within BOTTOMS_SYM_PCT × pattern_height)
      - Separated by ≥ MIN_BARS_BETWEEN_EXTREMES bars
      - A swing high (neckline) between them (max of intermediate highs)
      - Last bar close > neckline + 1T (breakout)
      - BOTH bottoms are Eve variant (cluster of ≥ EVE_MIN_CLUSTER_BARS bars within
        EXTREME_CLUSTER_TOL_PCT × pattern_height of the bottom)

    Returns:
      (None, 0.0, {}) if no pattern.
      ("LONG", conf, info) if fired. info keys:
        - kind: "DOUBLE_BOTTOM"
        - pattern_name: "DOUBLE_BOTTOM_LONG"
        - structural_anchor: float (lower_of_two_bottoms − 1T · for adaptive_stop Layer A)
        - pattern_measure: float (positive · = neckline_price − min(b1, b2))
        - neckline_price, bottom1_price, bottom2_price
        - bottom1_cluster_bars: int (variant evidence)
        - bottom2_cluster_bars: int (variant evidence)
        - bar_count: int (bottom1-to-bottom2 span)
        - variant: "Eve&Eve"
        - stage: 3
    """
    # CC: implement per spec §2.E + detection geometry above.
    # Returning the tuple shape regardless · empty info on no-detect.
    raise NotImplementedError("CC implements")


def detect_double_top(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Double Top Adam&Adam (bearish reversal).

    Pattern shape:
      - Two swing highs of approximately equal price (within BOTTOMS_SYM_PCT × pattern_height)
      - Separated by ≥ MIN_BARS_BETWEEN_EXTREMES bars
      - A swing low (neckline) between them (min of intermediate lows)
      - Last bar close < neckline − 1T (breakout)
      - BOTH peaks are Adam variant (cluster of ≤ ADAM_MAX_CLUSTER_BARS bars within
        EXTREME_CLUSTER_TOL_PCT × pattern_height of the peak)

    Returns ("SHORT", conf, info) on fire · info keys mirror detect_double_bottom:
      pattern_measure = max(p1, p2) − neckline_price (positive)
      structural_anchor = max(p1, p2) + 1T
      variant: "Adam&Adam"
    """
    raise NotImplementedError("CC implements")


# ── Internal helpers (CC implements · names suggested) ──
# def _swing_lows(bars, lookback): ...                       # already in head_shoulders.py · CC may duplicate or factor to patterns/_pivots.py (CC's choice)
# def _swing_highs(bars, lookback): ...
# def _extremes_symmetric(p1, p2, pattern_height): ...       # |p1-p2|/pattern_height ≤ BOTTOMS_SYM_PCT
# def _count_cluster_bars(window, extreme_price, tol, direction): ...   # how many bars have l/h within tol of extreme
# def _is_eve(cluster_bars): return cluster_bars >= EVE_MIN_CLUSTER_BARS
# def _is_adam(cluster_bars): return cluster_bars <= ADAM_MAX_CLUSTER_BARS
# def _confidence(p1, p2, pattern_height, cluster_min_or_max, variant): ...
```

**Confidence formula** (mirrors H&S logic):

```
sym_score      = max(0, 1 − asymmetry/BOTTOMS_SYM_PCT)
                 where asymmetry = |p1 − p2| / pattern_height

# Variant quality — how cleanly does this fit Eve or Adam?
For DB (Eve · more cluster bars = better):
  variant_score = min(1.0, max(0, (min(cluster1, cluster2) − EVE_MIN_CLUSTER_BARS) / 4))
For DT (Adam · fewer cluster bars = better):
  variant_score = max(0, (ADAM_MAX_CLUSTER_BARS − max(cluster1, cluster2) + 1) / ADAM_MAX_CLUSTER_BARS)
  (clamped to [0, 1])

conf = 0.60 + 0.20 × sym_score + 0.20 × variant_score
clamped to [0, 1]
```

### §3.B · MODIFY · `backend/v9/systems/five_min/output_schema.py`

Extend `PatternName` Literal with 2 new values (mirrors Pkg 5a edit · 1-line change):

```python
PatternName = Literal[
    'REACTIVE_LONG', 'REACTIVE_SHORT',
    'INITIATIVE_LONG', 'INITIATIVE_SHORT',
    'INVERSE_HNS_LONG', 'HNS_TOP_SHORT',
    'DOUBLE_BOTTOM_LONG', 'DOUBLE_TOP_SHORT',
]
```

That brings the total to 8 PatternName values. **DO NOT** change anything else in this file.

### §3.C · MODIFY · `backend/v9/systems/five_min/five_min_system.py` — 3 edits

#### Edit 1 · Import (top of file · after Pkg 5a's H&S import on line 18)

```python
from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns, detect_hns_top
from backend.v9.systems.five_min.patterns.double_top_bottom import detect_double_bottom, detect_double_top  # ← NEW Pkg 5b
```

#### Edit 2 · `process_bar` chart-pattern chain (extend the Pkg 5a chain · after line 686)

The existing Pkg 5a block:
```python
# Pkg 5a · chart patterns (Stage 3 + day-type gated · D-091 §5+§6)
if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
    if self.current_day_type in (
        "Neutral_Extreme", "Neutral_Center", "Normal", "Variation",
    ):
        direction, conf, info = detect_inverse_hns(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_hns_top(self._bar_buffer)
```

Becomes (append 2 lines · DB then DT · per Bulkowski Eve-LONG bias on neutral days):

```python
# Pkg 5a + 5b · chart patterns (Stage 3 + day-type gated · D-091 §5+§8)
if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
    if self.current_day_type in (
        "Neutral_Extreme", "Neutral_Center", "Normal", "Variation",
    ):
        direction, conf, info = detect_inverse_hns(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_hns_top(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_double_bottom(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_double_top(self._bar_buffer)
```

**Order rationale:** H&S patterns are statistically rarer than DB/DT (Bulkowski) but have higher win-rate when they form · check first to avoid mis-binding a borderline pattern to DB/DT. **CC may NOT reorder** — this is locked.

#### Edit 3 · Extend stop-family fork + targets fork to include DB/DT kinds (extend the Pkg 5a fork)

Existing Pkg 5a stop fork (around line 694-703):
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    family = "HnS"
    structural_anchor = info["structural_anchor"]
else:
    family = "Reactive" if kind == "REACTIVE" else "OFA"
    structural_anchor = (
        bar.get("l", entry_price) if direction == "LONG"
        else bar.get("h", entry_price)
    )
```

Becomes:
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    family = "HnS"
    structural_anchor = info["structural_anchor"]
elif kind in ("DOUBLE_BOTTOM", "DOUBLE_TOP"):
    family = "Double_BT"
    structural_anchor = info["structural_anchor"]
else:
    family = "Reactive" if kind == "REACTIVE" else "OFA"
    structural_anchor = (
        bar.get("l", entry_price) if direction == "LONG"
        else bar.get("h", entry_price)
    )
```

Existing Pkg 5a targets fork (around line 769-797):
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    pm = info["pattern_measure"]
    sign = 1.0 if direction == "LONG" else -1.0
    t1_price = entry_price + sign * 0.50 * pm
    t2_price = entry_price + sign * 0.74 * pm
    t3_price = None
else:
    # OFA path · resolve targets per day_type
    ...
```

Becomes:
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    pm = info["pattern_measure"]
    sign = 1.0 if direction == "LONG" else -1.0
    t1_price = entry_price + sign * 0.50 * pm
    t2_price = entry_price + sign * 0.74 * pm
    t3_price = None
elif kind == "DOUBLE_BOTTOM":
    pm = info["pattern_measure"]
    t1_price = entry_price + 0.50 * pm
    t2_price = entry_price + 0.66 * pm    # ← D-091: DB haircut = 0.66
    t3_price = None
elif kind == "DOUBLE_TOP":
    pm = info["pattern_measure"]
    t1_price = entry_price - 0.50 * pm
    t2_price = entry_price - 0.74 * pm    # ← D-091: DT haircut = 0.74
    t3_price = None
else:
    # OFA path · resolve targets per day_type
    ...
```

### §3.D · NEW · `tests/v9/systems/test_five_min/test_double_top_bottom.py`

18+ golden tests (see §5). Mirror of `test_head_shoulders.py` structure.

### §3.E · MODIFY · `tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py`

Append 4 integration tests (mirror the 4 Pkg 5a added):
- `test_db_skipped_on_nt_day_type` — verify `detect_double_bottom` not called when `day_type=Nontrend`
- `test_dt_skipped_on_tn_day_type` — verify `detect_double_top` not called when `day_type=Trend_Normal` (not in NV/NeuE/NeuC/Norm)
- `test_db_skipped_on_first_hour_mode` — verify gating by `mode == DAY_TYPE_MODE`
- `test_double_bottom_emits_t1setup_on_neuc` — emit_t1_setup accepts `DOUBLE_BOTTOM_LONG` with `time_stop_minutes=30` (NeuC)

---

## §4 · Detection geometry · expanded design notes

### §4.A · MIN_BARS_REQUIRED = 14 · SEARCH_WINDOW = 30

Tighter than H&S (which used 12/30) because DB/DT must accommodate cluster-bar analysis on BOTH extremes — need ≥4 bars near each bottom (Eve) or ≤3 bars near each peak (Adam) PLUS pivot lookback of 2 each side PLUS intermediate neckline pivot. Math: 4 + 2 + 2 + 1 + 2 + 2 + 4 = 17 in the worst Eve&Eve case · 14 is the practical lower bound after overlap. SHADOW may raise to 16-18.

### §4.B · BOTTOMS_SYM_PCT = 0.05

Two bottoms (or peaks) considered "approximately equal" when `|b1 − b2| / pattern_height ≤ 5%`. Path B used `prices_near(b1, b2, 0.15%)` of price — much looser. Master Sheet 2 doesn't give an explicit number; this matches H&S `SHOULDER_SYM_PCT = 0.05` for consistency. SHADOW-calibratable.

### §4.C · Eve vs Adam — cluster bar criterion

Bulkowski defines Eve = rounded (wide cluster of bars at extreme · 5+ bars · gradual price change near bottom) and Adam = sharp (narrow cluster · 1-3 bars · V-shape).

**Numerical proxy used here:**
```
For each candidate extreme E (at index i_E with price p_E):
  cluster_window = window indices in [i_E − 5, i_E + 5] (clamped to bar buffer)
  cluster_bars = count of indices j in cluster_window where
                   |bar[j][low_or_high] − p_E| ≤ EXTREME_CLUSTER_TOL_PCT × pattern_height
                   (use bar[j].l for DB · bar[j].h for DT)

DB is Eve&Eve  iff  cluster_bars(bottom1) ≥ EVE_MIN_CLUSTER_BARS  AND  cluster_bars(bottom2) ≥ EVE_MIN_CLUSTER_BARS
DT is Adam&Adam iff  cluster_bars(peak1) ≤ ADAM_MAX_CLUSTER_BARS AND  cluster_bars(peak2) ≤ ADAM_MAX_CLUSTER_BARS
```

If a candidate fails the variant filter, **return `(None, 0.0, {})`** — do NOT downgrade confidence and emit. D-091 §Scope is explicit that DB = Eve&Eve only and DT = Adam&Adam only.

### §4.D · Pattern measure (full height)

For DB: `pattern_measure = neckline_price − min(bottom1, bottom2)` (always positive · used as projected upside target).
For DT: `pattern_measure = max(peak1, peak2) − neckline_price` (always positive · used as projected downside target).

Targets are computed in `five_min_system.py` from `pattern_measure` (per §3.C edit 3) · the detector only returns the raw geometric height.

### §4.E · Structural anchor

Per D-091 §Stop layers · returned in `info["structural_anchor"]`:
- DB: `min(bottom1, bottom2) − TICK_SIZE`
- DT: `max(peak1, peak2) + TICK_SIZE`

Passed to `compute_stop()` as the Layer A anchor · `family="Double_BT"` triggers the existing `ATR_MULTIPLIER["Double_BT"]=2.0` (Pkg 1 frozen).

### §4.F · Variant returned in info dict

CC adds `info["variant"] = "Eve&Eve"` (DB) or `"Adam&Adam"` (DT). This is informational for telemetry · downstream Pkg 6/7 may use it for variant-specific exit rules. Not consumed elsewhere in Pkg 5b.

---

## §5 · Golden tests · 18 tests (mirror H&S 16 + 2 variant filter)

| # | Test | Pattern | Expected |
|---|---|---|---|
| 1 | `test_double_bottom_eve_eve_classic_symmetric` | DB · two rounded bottoms · neckline break +1T | `("LONG", conf≥0.7, kind="DOUBLE_BOTTOM", variant="Eve&Eve", pattern_measure≈ΔH, structural_anchor=lower_bottom − 1T)` |
| 2 | `test_double_top_adam_adam_classic_symmetric` | DT · two sharp peaks · neckline break −1T | `("SHORT", conf≥0.7, kind="DOUBLE_TOP", variant="Adam&Adam")` |
| 3 | `test_double_bottom_asymmetric_rejected` | DB · `|b1-b2|/height > 5%` | `(None, 0.0, {})` |
| 4 | `test_double_top_asymmetric_rejected` | DT · `|p1-p2|/height > 5%` | `(None, 0.0, {})` |
| 5 | `test_double_bottom_too_close_rejected` | DB · bottoms only 3 bars apart (< MIN_BARS_BETWEEN_EXTREMES=5) | `(None, 0.0, {})` |
| 6 | `test_double_top_too_close_rejected` | DT · peaks only 3 bars apart | `(None, 0.0, {})` |
| 7 | `test_double_bottom_no_neckline_rejected` | DB · no intermediate swing high between two bottoms | `(None, 0.0, {})` |
| 8 | `test_double_top_no_neckline_rejected` | DT · no intermediate swing low between two peaks | `(None, 0.0, {})` |
| 9 | `test_double_bottom_no_breakout_rejected` | DB · last close = neckline (NOT > neckline + 1T) | `(None, 0.0, {})` |
| 10 | `test_double_top_no_breakout_rejected` | DT · last close = neckline (NOT < neckline − 1T) | `(None, 0.0, {})` |
| 11 | `test_double_bottom_insufficient_bars` | DB · `bars[:12]` (less than MIN_BARS_REQUIRED=14) | `(None, 0.0, {})` |
| 12 | `test_double_bottom_confidence_perfect` | DB · symmetric + both Eve cluster≥6 bars | `conf == 1.0 ± 0.01` |
| 13 | `test_double_top_confidence_marginal` | DT · borderline Adam (cluster=3 exactly) | `conf == 0.60 + small bonus` |
| 14 | `test_double_bottom_structural_anchor_lower_bottom` | DB · `b1=4500, b2=4501` | `info["structural_anchor"] == 4500 - 0.25` |
| 15 | `test_double_top_structural_anchor_higher_peak` | DT · `p1=4500, p2=4501` | `info["structural_anchor"] == 4501 + 0.25` |
| 16 | `test_double_bottom_pattern_measure_positive` | DB · neckline at 4520 · bottoms at 4500 | `pattern_measure ≈ 20.0` |
| 17 | **`test_double_bottom_adam_shape_rejected`** | **DB direction but bottoms are sharp (Adam · cluster=2)** | `(None, 0.0, {})` — Eve&Eve filter rejects |
| 18 | **`test_double_top_eve_shape_rejected`** | **DT direction but peaks are rounded (Eve · cluster=6)** | `(None, 0.0, {})` — Adam&Adam filter rejects |

Plus 4 integration tests appended to `test_five_min_day_type_wiring.py` (per §3.E).

**Total: 18 golden + 4 integration = 22 new tests.** Existing 12 wiring tests + 16 H&S tests remain green = **50 tests total in five_min suite after Pkg 5b**.

---

## §6 · Acceptance criteria · G3 PASS gate

CC outputs `STOP — <reason>` if any of these can NOT be achieved without violating a §7 constraint.

1. `pytest tests/v9/systems/test_five_min/test_double_top_bottom.py -v` → **18 passed**
2. `pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q` → **16 passed** (was 12 · +4 new)
3. `pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q` → **16 passed** (unchanged · Pkg 5a regression check)
4. `pytest tests/v9/systems/ -q` → **610 passed · 1 skipped** (was 592 · +18 net = 18 DB/DT + 4 wiring − 4 absorbed, net +18)
5. `pytest backend/v9/tests/ -q` → **531 passed · 2 skipped** (unchanged)
6. `pytest backend/v9/systems/five_min/tests/ -q` → **70 passed · 8 failed** (F4 pre-existing · NO new failures introduced)
7. `ReadLints` on all 4 changed files + 1 new file → 0 new errors
8. `git diff backend/v9/systems/five_min/five_min_system.py` → verify lines 215-217 byte-identical (chronic toxicity block · Pkg 0 rule)
9. `backend.main` imports cleanly (smoke test: `python -c "from backend.v9.systems.five_min.patterns.double_top_bottom import detect_double_bottom; print('OK')"` → "OK")
10. Smoke test on classic fixture: `detect_double_bottom(<classic_eve_bars>)` → returns `("LONG", >=0.7, {kind: "DOUBLE_BOTTOM", variant: "Eve&Eve", ...})`
11. `PatternName` Literal includes 8 values · `T1Setup(pattern_name="DOUBLE_BOTTOM_LONG", ...)` validates
12. `T1Setup(pattern_name="DOUBLE_TOP_SHORT", ...)` validates

---

## §7 · Constraints (must NOT violate)

- **No silent excepts.** Every `except` must include `logger.warning("[double_top_bottom] <message>", ...)` rate-limited (1/min via `time.monotonic()` like the NT skip pattern).
- **No `return None` without prior log** at info-level (e.g. log "no candidate pair found" on early-return paths is OK if rate-limited).
- **No new dependencies** (pip install / package.json). Use stdlib `typing`, `logging`, `time`. No `numpy`/`pandas`.
- **No "while I'm here" refactors** outside the 5 files listed in §3. Specifically:
  - Do NOT change `_detect_reactive` / `_detect_initiative` / `detect_inverse_hns` / `detect_hns_top` signatures
  - Do NOT change `T1Setup` schema fields other than `PatternName` Literal
  - Do NOT change `compute_targets_for_day_type` (used only on OFA path)
  - Do NOT modify `head_shoulders.py` (Pkg 5a frozen · DB/DT lives in `double_top_bottom.py`)
  - Do NOT touch `backend/v9/systems/day_type/*` (Pkg 3a frozen)
  - Do NOT touch `backend/v9/systems/footprint/*` (Pkg 2bc frozen)
  - Do NOT touch `manager.py` (Pkg 6 territory)
  - Do NOT touch `adaptive_stop.py` · `ATR_MULTIPLIER["Double_BT"]=2.0` already wired (Pkg 1)
- **Hardcoded values forbidden** — the 9 detection constants (`MIN_BARS_REQUIRED`, `SEARCH_WINDOW`, `PIVOT_LOOKBACK`, `BOTTOMS_SYM_PCT`, `MIN_BARS_BETWEEN_EXTREMES`, `EXTREME_CLUSTER_TOL_PCT`, `EVE_MIN_CLUSTER_BARS`, `ADAM_MAX_CLUSTER_BARS`, `TICK_SIZE`) MUST live as module-level UPPER_CASE constants at top of `double_top_bottom.py`. Tests reference them by import.
- **Lines 215-217 of `five_min_system.py` MUST stay byte-identical** (chronic toxicity block per Pkg 0):
  ```
  # Delegate to existing chart_5min detector for pattern detection
  # (integration point — full wiring in future prompts)
  return None
  ```
  Verify with: `sed -n '/Delegate to existing chart_5min detector/,/return None$/p' backend/v9/systems/five_min/five_min_system.py`
- **Stage 3 + day-type gating MUST be checked at the integration layer (in `five_min_system.process_bar`), NOT inside the detector functions.** Rationale: detectors are pure functions · gating is system context.
- **`t3_price=None` is INTENTIONAL** for both DB and DT (trail per Day Type · Pkg 6 enforces). Do NOT compute T3 numeric.
- **`time_stop_minutes` is auto-derived** from `day_type` via existing `get_time_stop()` in `setup_emitter.py` · do NOT pass `time_stop_minutes` from detector or integration layer.
- **Variant filter is hard-gated** — Eve&Eve required for DB · Adam&Adam required for DT. Do NOT emit with a "downgraded confidence" if the variant doesn't match. Return `(None, 0.0, {})`.
- **Pattern order in `process_bar` chain is locked** — H&S detectors come BEFORE DB/DT detectors per §3.C edit 2. Do NOT reorder.

---

## §8 · Forbidden zones

```
🛑 DO NOT modify:
  - backend/v9/systems/day_type/*           (Pkg 3a frozen)
  - backend/v9/systems/footprint/*          (Pkg 2bc frozen)
  - backend/v9/systems/five_min/adaptive_stop.py    (Pkg 1 frozen · just IMPORT it)
  - backend/v9/systems/five_min/setup_emitter.py    (Pkg 3a S2 frozen · just CALL it)
  - backend/v9/systems/five_min/time_stop_mapper.py (Pkg 3a S2 frozen)
  - backend/v9/systems/five_min/patterns/head_shoulders.py (Pkg 5a frozen)
  - backend/v9/systems/woodies/*            (S4 territory)
  - backend/v9/services/trade_manager/*     (Pkg 6 territory)
  - bridge/, sc_study/, frontend/           (out of scope)
  - backend/v9/systems/five_min/five_min_system.py lines 1-17 (above Pkg 5a import) and lines 218+ outside the 3 edits in §3.C

🛑 DO NOT add:
  - Inline DB/DT detection in five_min_system.py (use the patterns/ subdir)
  - Throwback waiting logic for DB (entry fires on neckline break · throwback is Pkg 7)
  - BTC override logic for DT (Pkg 7 STC/BTC modes)
  - Adam&Eve or Eve&Adam DB variants (D-091 §Scope locks Eve&Eve only)
  - Adam&Eve or Eve&Adam DT variants (D-091 §Scope locks Adam&Adam only)
  - T3 numeric value (it's trail · t3_price MUST be None)
  - News-event filtering (DEMO-1 territory)
```

---

## §9 · Pre-flight · current code state (verified by Cursor 24/5 17:57 IL)

### §9.A · Files that exist (read-only · do NOT modify outside scope)

```
backend/v9/systems/five_min/
├── __init__.py
├── adaptive_stop.py                # Pkg 1 · ATR_MULTIPLIER["Double_BT"]=2.0 ✅
├── choppiness.py
├── confluence.py
├── cot_amt.py
├── first_hour_buffer.py
├── first_hour_matrix.py
├── five_min_system.py              # 836 LOC after Pkg 5a · 3 edits per §3.C
├── output_schema.py                # 46 LOC after Pkg 5a · 1 edit per §3.B (extend Literal)
├── patterns/                       # NEW directory · created by Pkg 5a
│   ├── __init__.py                 # 5 LOC · do NOT modify
│   └── head_shoulders.py           # 265 LOC · Pkg 5a frozen · do NOT modify
├── q0_dispatcher.py
├── quality_tier.py
├── setup_emitter.py                # Pkg 3a S2 frozen · do NOT modify
├── setup_wrapper.py
├── sr_proximity.py
└── time_stop_mapper.py             # Pkg 3a S2 frozen · do NOT modify
```

Pkg 5b adds: `patterns/double_top_bottom.py` + `tests/v9/systems/test_five_min/test_double_top_bottom.py`.

### §9.B · `adaptive_stop.py::ATR_MULTIPLIER` (excerpt · already includes "Double_BT")

```python
ATR_MULTIPLIER = {
    "Reactive":  1.0,
    "OFA":       1.5,
    "Flag":      1.5,
    "Double_BT": 2.0,   # ← Pkg 5b uses this
    "HnS":       2.0,
}
```

### §9.C · `setup_emitter.emit_t1_setup` signature (already accepts pattern-measure targets)

Identical to Pkg 5a — accepts `t1_price` / `t2_price` / `t3_price=None` directly. No schema change needed.

### §9.D · Prior art (informational · DO NOT copy verbatim — D-091 supersedes target logic)

`backend/v9/systems/chart_5min/patterns/double_bottom.py` and `double_top.py` existed in Path B (deleted in `1c805ea` per Pkg 0). Their **geometric detection structure** (find_pivots → swing_lows/highs → 2-extreme-loop → neckline → completion threshold) is a sound reference for the algorithm shape. Recoverable via `git show 1c805ea~1:backend/v9/systems/chart_5min/patterns/double_bottom.py`.

**What to REUSE (concept only · re-implement clean):**
- 2-consecutive-pivot loop pattern
- Neckline = max/min of intermediate highs/lows
- Stop = lower bottom / higher peak
- Confidence base 0.6 + scaling

**What to REJECT (D-091 + Master Sheet 2 supersedes):**
- Path B used **Fibonacci targets** (0.618×height / 1.0×height / 1.618×height) — **DO NOT use**. Use Master Sheet 2: T1=50%, DB-T2=0.66, DT-T2=0.74, T3=None.
- Path B used `prices_near(b1, b2, 0.15%)` of price — **REPLACE** with `BOTTOMS_SYM_PCT=0.05` (5% relative to pattern height · matches H&S 5a).
- Path B had **NO variant filter** (detected any DB/DT shape) — **ADD** Eve&Eve / Adam&Adam variant filter per D-091.
- Path B's `completion = 0.5` proxy — **REPLACE** with strict close-through-neckline + 1T (matches Master Sheet 2 entry trigger).
- Path B used raw lower-bottom as stop — **CHANGE** to `lower_bottom − 1T` per D-091 §Stop layers.
- Path B's `bar_count >= 4` minimum — **REPLACE** with `MIN_BARS_BETWEEN_EXTREMES = 5` (allows cluster room).

### §9.E · Test baseline (24/5 17:50 IL · HEAD = `7ffab50` · Pkg 5a G3 PASS)

- `tests/v9/systems/` → 592 passed · 1 skipped
- `backend/v9/tests/` → 531 passed · 2 skipped
- `backend/v9/systems/five_min/tests/` → 70 passed · 8 failed (F4 pre-existing · NOT Pkg 5b's responsibility · DO NOT "fix" these as a side effect)
- 1 uncommitted file: `backend/v9/systems/five_min/tests/test_time_stop_mapper.py` (Cursor hand-fix from Stream 2 G3) · Pkg 5b does NOT touch this file · keep it dirty

---

## §10 · Validation recipe (CC runs after implementation)

```bash
# 1. Lint check (pyflakes optional · ReadLints is authoritative in Cursor G3)
python -m pyflakes backend/v9/systems/five_min/patterns/double_top_bottom.py
python -m pyflakes backend/v9/systems/five_min/five_min_system.py

# 2. New tests
pytest tests/v9/systems/test_five_min/test_double_top_bottom.py -v

# 3. Pkg 5a regression check
pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q

# 4. Wiring regression + new integration tests
pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q

# 5. Full systems suite
pytest tests/v9/systems/ -q

# 6. Backend baseline
pytest backend/v9/tests/ -q --no-header

# 7. F4 baseline check
pytest backend/v9/systems/five_min/tests/ -q --no-header

# 8. Chronic toxicity byte-identical
sed -n '/Delegate to existing chart_5min detector/,/return None$/p' backend/v9/systems/five_min/five_min_system.py

# 9. Smoke
python -c "
from backend.v9.systems.five_min.patterns.double_top_bottom import (
    detect_double_bottom, detect_double_top,
    MIN_BARS_REQUIRED, EVE_MIN_CLUSTER_BARS, ADAM_MAX_CLUSTER_BARS,
)
print('imports OK')

# Classic Eve&Eve fixture · two rounded bottoms at 4500 · neckline at 4520 · breakout to 4521
# Each bottom has ≥4 bars clustered within 2pt (10% of 20pt height)
bars = [
    # 0-4: approach + first Eve bottom (cluster of 5 bars near 4500)
    {'o':4506,'h':4507,'l':4505,'c':4506,'v':1000},
    {'o':4505,'h':4505,'l':4501.5,'c':4502,'v':1200},
    {'o':4502,'h':4502,'l':4500.5,'c':4501,'v':1300},
    {'o':4501,'h':4501,'l':4500,'c':4500.5,'v':1400},
    {'o':4500.5,'h':4501,'l':4500,'c':4501,'v':1300},
    # 5-9: rise to neckline
    {'o':4501,'h':4510,'l':4501,'c':4509,'v':1200},
    {'o':4509,'h':4519,'l':4508,'c':4518,'v':1100},
    {'o':4518,'h':4520,'l':4517,'c':4519,'v':1000},
    {'o':4519,'h':4520,'l':4518,'c':4519,'v':900},
    {'o':4519,'h':4519,'l':4515,'c':4515,'v':1100},
    # 10-14: drop + second Eve bottom (cluster of 5 bars near 4500)
    {'o':4515,'h':4515,'l':4505,'c':4506,'v':1300},
    {'o':4506,'h':4506,'l':4501,'c':4502,'v':1400},
    {'o':4502,'h':4502,'l':4500.5,'c':4501,'v':1400},
    {'o':4501,'h':4501,'l':4500,'c':4500.5,'v':1500},
    {'o':4500.5,'h':4501,'l':4500,'c':4501,'v':1400},
    # 15-16: breakout
    {'o':4501,'h':4515,'l':4501,'c':4514,'v':1300},
    {'o':4514,'h':4521,'l':4514,'c':4521,'v':1500},
]
d, c, info = detect_double_bottom(bars)
print(f'detected: {d} conf={c:.2f} variant={info.get(\"variant\")} measure={info.get(\"pattern_measure\")}')
assert d == 'LONG', f'expected LONG, got {d}'
assert info['variant'] == 'Eve&Eve'
assert info['pattern_measure'] == pytest.approx(20.0, abs=1.0) if False else abs(info['pattern_measure'] - 20.0) < 1.5
print('smoke OK')
"
```

---

## §11 · Stop signals (CC outputs `STOP — <reason>` and halts)

CC must STOP and report (do NOT guess · do NOT add `TODO: ask Michael`) when:

1. **Cannot construct a fixture** that exercises a §5 golden test (especially #17 / #18 variant rejection — these require carefully crafted bar layouts).
2. **D-091 vs Master Sheet 2 conflict** — D-091 §Stop layers says "1T below lower of two bottoms" but DB structural anchor in code uses `min(b1, b2)` of the swing-low **bar prices** — STOP and clarify: anchor on `bar.l` or on the swing-low **close**?
3. **Forbidden file in edit list** — any file outside the 5 listed in §3 (this would indicate a misread).
4. **Lines 215-217 modification proposed** — any edit through those lines = STOP.
5. **Pkg 5a (H&S) file modification proposed** — STOP. DB/DT must live in `double_top_bottom.py` exclusively.
6. **Detector function I/O** — DB read, network call, or file I/O = STOP (detectors are pure).
7. **Existing test regression** — any test in `tests/v9/systems/` or `backend/v9/tests/` that was green at `7ffab50` becomes red after Pkg 5b — STOP with diff.
8. **`PatternName` Literal grows beyond 8 values** — if a 9th name is needed, STOP.
9. **Variant filter ambiguous** — if `EXTREME_CLUSTER_TOL_PCT` and `EVE_MIN_CLUSTER_BARS` give different answers for the same fixture depending on subtle pivot lookback, STOP and report the ambiguity.
10. **Pattern order in process_bar chain different from §3.C edit 2** — if you discover H&S→DB→DT order causes a missed fire, STOP (do NOT reorder).

For any other ambiguity: STOP. The pre-LIVE protocol forbids silent assumptions.

---

## §12 · Deliverable format (CC outputs after completion)

1. **Files changed** (full paths · A/M/D):
   - `A backend/v9/systems/five_min/patterns/double_top_bottom.py`
   - `M backend/v9/systems/five_min/output_schema.py` (1 line · extend Literal)
   - `M backend/v9/systems/five_min/five_min_system.py` (3 edits)
   - `A tests/v9/systems/test_five_min/test_double_top_bottom.py`
   - `M tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py` (append 4 tests)

2. **Commit message:**
   ```
   feat(s2): Double Bottom (Eve&Eve) + Double Top (Adam&Adam) detectors per D-091 §7+§8

   - NEW backend/v9/systems/five_min/patterns/double_top_bottom.py
     · detect_double_bottom (LONG · reversal · Eve&Eve only)
     · detect_double_top (SHORT · reversal · Adam&Adam only)
     · 9 SHADOW-calibratable detection constants
     · Pattern-measure targets (50% T1 · 0.66× T2 for DB · 0.74× T2 for DT · trail T3)
     · Structural anchor = lower bottom ± 1T (DB) / higher peak ± 1T (DT)
     · Variant filter (Eve = cluster ≥ 4 bars / Adam = cluster ≤ 3 bars)
   - MODIFY output_schema.py · extend PatternName Literal (+ 2 values · total 8)
   - MODIFY five_min_system.py · 3 edits
     1. import DB/DT detectors (after Pkg 5a H&S import)
     2. extend chart-pattern chain with DB then DT (after H&S in chain)
     3. extend stop family + targets fork (Double_BT + DB/DT branches)
   - NEW tests/v9/systems/test_five_min/test_double_top_bottom.py · 18 golden tests
   - MODIFY tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py · +4 integration tests

   Pkg 5b · NeuE/NeuC/Norm/NV day types · emit-only (Pkg 6 enforces trail · Pkg 7 enforces split T1 + BTC override).
   Sources: Bulkowski 952 Eve&Eve DB trades + AA-rank-5/21 DT · Master Sheet 2.

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   ```

3. **Self-report:**
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly · if any was resolved by interpretation rather than STOP signal, document the call)
   - Any forbidden constraint accidentally touched? (own up)
   - Lines 215-217 still byte-identical? (yes/no with diff)
   - Detection constants at module top · referenced by tests via import? (yes/no)
   - Eve&Eve / Adam&Adam variant filter implemented as hard gate (return None) and NOT as confidence haircut? (yes/no)
   - Pattern order H&S → DB → DT preserved per §3.C edit 2? (yes/no)

4. **ReadLints output** (paste verbatim · 5 files: double_top_bottom.py · output_schema.py · five_min_system.py · test_double_top_bottom.py · test_five_min_day_type_wiring.py)

5. **pytest output** (paste verbatim · tail 30 lines for each: `test_double_top_bottom.py` · `test_head_shoulders.py` · `test_five_min_day_type_wiring.py` · `tests/v9/systems/` · `backend/v9/tests/`)

---

## §13 · Estimated CC time

| Sub-task | Estimated | Notes |
|---|---|---|
| Read Path B prior art (`git show 1c805ea~1:backend/v9/systems/chart_5min/patterns/double_bottom.py`) + Pkg 5a `head_shoulders.py` for helper patterns | 10 min | Helpers may be duplicated · CC's choice |
| Write `patterns/double_top_bottom.py` skeleton (constants + signatures) | 15 min | Mostly structure |
| Implement `_swing_lows` / `_swing_highs` / `_count_cluster_bars` helpers | 30 min | Cluster counter is new · others mirror H&S |
| Implement `detect_double_bottom` (LONG · Eve&Eve gated) | 50 min | Main logic + variant filter |
| Implement `detect_double_top` (SHORT · Adam&Adam · mirror) | 30 min | Reuse helpers + flip variant criterion |
| Modify `output_schema.py` (1-line Literal extension) | 5 min | |
| Modify `five_min_system.py` 3 edits | 20 min | Surgical · pattern of 5a |
| Write 18 golden tests · 4 integration tests | 100 min | Fixtures with cluster control are the slow part |
| Run validation recipe · iterate on failures | 50 min | Expect 1-2 iterations (cluster math edge cases) |
| **Total** | **~4-5 hours CC time** | + Cursor G3 ~30 min |

(Pkg 5a took ~3 hours per its commit timestamps · 5b is +1h for the variant filter complexity.)

---

## §14 · Post-G3 PASS unlocks

| Unlocked | Why |
|---|---|
| **Pkg 5c** (Bull/Bear Flag) | Last chart-pattern Pkg in Phase A · continuation patterns (TN/TDD/NV) · ×0.46 haircut · 50/50 split (no T3) |
| **Pkg 3b** (Trail engine) | Phase A is then **3 Pkgs from complete** (5c + 3b + 3c) before SHADOW soak |
| Coverage of NeuE/NeuC/Norm/NV becomes **complete** for reversal patterns (4 detectors · LONG+SHORT × 2 families) |

---

*End of Pkg 5b handoff · Cursor agent · 2026-05-24 18:00 IL*
*Spec authority: D-091 §7+§8 + Master Sheet 2 (Michael paste 24/5 17:57)*
*Detection geometry defaults: Bulkowski + Path B seed (Michael approved variants via D-091 §Scope)*
*Awaiting Claude Desktop mega-prompt drafting → CC execution → Cursor G3 review*
