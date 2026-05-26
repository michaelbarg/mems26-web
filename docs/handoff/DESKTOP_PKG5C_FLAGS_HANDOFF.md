# Pkg 5c · Bull Flag + Bear Flag pattern detectors (chart patterns · Stage 3 · continuation) — v2 per D-091.Q5

**Authority:** D-091 §Scope #9+#10 · **D-091.Q5 (Path C · day-type conditional T2 · LOCKED 24/5 18:45 IL)** · D-091 §Stop layers · D-091 §Contract Distribution (50/50 · no T3) · Master Sheet 2 (S2_Master_Summary.xlsx · rows pasted by Michael 24/5 16:27 IL)
**Predecessor:** Pkg 5b CC commit `2c001a2` (G3 pending Cursor verification) · HEAD = `2c001a2`
**Status:** Spec ready · v2 supersedes v1 (which used flat ×0.46 — contradicted geometry per Q5.A)
**Estimated CC time:** ~5-6 hours (LARGER than 5a/5b · adds Q5 day-type T2 fork · 5 day-type paths · trail flag wiring · VAH/VAL/POC reads)
**Independent of:** all other unbuilt Pkgs (does NOT touch `manager.py` · does NOT modify Pkg 1/2a/2bc/3a/5a/5b code paths · only extends `five_min_system.process_bar` chart-pattern chain + reads existing `_load_sierra_tpo()`)

> **v2 patch (24/5 19:00 IL):** Sections impacted by D-091.Q5 — §1, §2.C, §2.D, §2.E, §3.C edits 2+3, §4.G (new), §5 (tests +5), §6 (counts +5), §7 (constraints), §11 (stop signals +3). The detection geometry (§3.A constants · pole+flag shape) is UNCHANGED. Q5 only redefines TARGET resolution.

---

## §1 · Why this exists

Pkg 5c is the **last chart-pattern Pkg in Phase A**. It adds two **continuation** patterns (vs the reversal patterns in 5a/5b):

1. **Bull Flag** (LONG · continuation · Bulkowski 1,028 trades · Brooks H2 entry trigger)
2. **Bear Flag** (SHORT · continuation · Bulkowski · Brooks L2 + STC mode)

Architecturally a near-clone of 5a/5b — same `patterns/` subdir, same `(direction, conf, info)` signature, same gating at the integration layer — but **FIVE substantive differences** (#1-3 are detection · #4-5 are NEW Q5 targets):

1. **Wider day-type gate** — TN / TDD / NV / **NeuE / Norm** (5 day types · Q5 expansion vs D-091 original 3). Continuation patterns fire on:
   - Trend days (TN/TDD/NV) — momentum-aligned breakouts → trail mode
   - Rotation days at structural boundaries (NeuE/Norm) — fade-to-reference entries
2. **No T3 leg** — these are continuation/fade setups, not reversals. Contract split is 50/50 (T1 + T2 only). Pkg 5c emits `t3_price=None` always.
3. **Asymmetric pole/flag structure** — not "two extremes + neckline" geometry. Detection needs:
   - **Pole**: strong directional move (≥ POLE_MIN_BARS, ≥ POLE_MIN_HEIGHT_TICKS, directional ratio ≥ POLE_DIRECTIONAL_PCT)
   - **Flag**: counter-trend or sideways pullback (FLAG_MIN_BARS to FLAG_MAX_BARS, max retracement ≤ FLAG_MAX_RETRACE_PCT of pole)
   - **Breakout**: close beyond flag's containment + 1T (in pole direction)
4. **🆕 Day-type-conditional T2 (Q5)** — T1 is always 50% of pole, but T2 varies by day type:
   - TN / NV → `t2 = full_pole` (numeric ceiling) + `trail_active = True`
   - TDD → `t2 = min(full_pole, entry + sign × 4 × stop_dist)` (cap at distribution boundary)
   - NeuE → `t2 = VAH (LONG) / VAL (SHORT)` (fade to opposite VA edge)
   - Norm → `t2 = POC` (balance reverts)
   - NeuC / NT → **do not fire** (gated upstream)
5. **🆕 Trail flag propagation (Q5)** — `info["trail_active"]: bool` set by detector based on `current_day_type` (TN/NV → True, else False). Read at integration layer. Pkg 6 TradeManager consumes via existing `trail_after_t2` field in `targets_table`.

Five structural decisions baked into the handoff per Michael 24/5 16:27 + 18:45 IL + Cursor-seeded SHADOW-calibratable defaults:

1. **Pole geometry defaults** seeded from Bulkowski "high & tight flag" stats (best-of-flag-variants: ≥90° pole · 3-15 bar pole · doubles in pole). Conservatively: 5+ pole bars · ≥16 ticks (4pt) pole height · ≥60% bars in pole direction.
2. **Flag geometry defaults** from Bulkowski "3-8 bar pullback rule" + max retracement ≤50% of pole.
3. **Brooks H2/L2 entry trigger** is operationalized as **"close breaks the flag containment + 1T"**. Brooks' nuanced H2/L2 "second pullback" semantics are deferred — the close-through-level trigger is the V1 implementation; SHADOW data will calibrate whether Brooks' 2-pullback wait improves win rate.
4. **Q5 day-type T2 logic** lives **inline in `five_min_system.process_bar`** (per Q5.D / Michael choice C1) · NOT in `targets_table.py`. Reasoning: matches Pkg 5a/5b precedent · keeps day-type-conditional pattern targets adjacent · VAH/VAL/POC retrieval reuses existing `_load_sierra_tpo()` (proven in `_compute_location_vs_poc`).
5. **`T1Setup.t2_price` stays `Field(gt=0)`** — no schema change. For TN/NV trail mode, T2 = full_pole serves as a numeric ceiling that Pkg 6 may exit at if trail does not catch the move first (per Michael choice B3).

---

## §2 · Spec authority

### §2.A · D-091 §Scope (verbatim)

```
| # | Pattern   | Status        | Stage          | Day Types        | Direction | Source                                        |
| 9 | Bull Flag | NEW in Path A | 3 only (bar 6+) | TN / TDD / NV   | LONG      | Bulkowski 1,028 trades + Brooks H2            |
| 10 | Bear Flag | NEW in Path A | 3 only (bar 6+) | TN / TDD / NV   | SHORT     | Bulkowski + Brooks L2 + STC                   |
```

### §2.B · D-091 §Stop layers (Layer A · structural anchor)

```
| Pattern         | Structural anchor (LONG)    | Structural anchor (SHORT)    |
| Bull/Bear Flag  | 1T below flag low           | 1T above flag high           |
```

### §2.C · D-091 §T2 — SUPERSEDED by D-091.Q5 (Path C)

**D-091 §T2 Haircuts row 5 (×0.46 flat) is DEPRECATED.** The flat ×0.46 placed T2 closer to entry than T1 (T2=0.46 < T1=0.50), making it geometrically meaningless — Q5.A contradiction #1.

**D-091.Q5 Path C resolution — day-type-conditional T2:**

| Day Type | T2 formula | trail_active | Fire? |
|---|---|---|---|
| Trend_Normal | `entry + sign × pole_height` (full pole · numeric ceiling) | **True** | YES |
| Variation | `entry + sign × pole_height` (full pole · numeric ceiling) | **True** | YES |
| Trend_DD | `min(full_pole, entry + sign × 4 × stop_dist)` (cap at 4R if tighter than full pole · sign-aware via min/max) | False | YES |
| **Neutral_Extreme** | `VAH` (LONG · from `_load_sierra_tpo()['vah']`) / `VAL` (SHORT · `['val']`) — **fallback to `full_pole`** if VAH/VAL is `None` | False | **YES (NEW vs D-091 §Coverage Matrix · Q5 amendment)** |
| **Normal** | `POC` (`_load_sierra_tpo()['poc']`) — **fallback to `full_pole`** if POC is `None` | False | **YES (NEW vs D-091 · Q5 amendment)** |
| Neutral_Center | n/a | n/a | **NO** (gated at integration · do-not-fire) |
| Nontrend | n/a | n/a | NO (existing NT skip gate) |

**Universal T1:** `T1 = entry + sign × 0.50 × pole_height` (NOT day-type-dependent · matches Master Sheet 2 row).

**Fallback policy:** When VAH/VAL/POC are unavailable (Sierra TPO file missing or pre-IB period), T2 falls back to `full_pole`. Log rate-limited warning (`logger.warning` 1/min) the first time this happens per session.

### §2.D · D-091 §Contract Distribution

```
| Pattern family            | T1 / T2 / T3 split             |
| Bull Flag + Bear Flag     | 50% / 50% (no T3 — continuation) |
```

**No T3 path.** This is the **first Phase A pattern with only T1+T2.** Downstream Pkg 6 must handle this case — Pkg 5c emits `t3_price=None` and downstream contract management splits exactly 50/50.

### §2.E · Master Sheet 2 rows (S2_Master_Summary.xlsx · pasted by Michael 24/5 16:27 IL) — **T2 column SUPERSEDED by Q5**

| Field | Bull Flag | Bear Flag |
|---|---|---|
| Status | 🟢 NEW Path A | 🟢 NEW Path A |
| Stage | 3 (bar 6+) | 3 (bar 6+) |
| Direction | LONG (continuation) | SHORT (continuation) |
| **Entry trigger** | 1T above flag high on close · Brooks H2 variant | 1T below flag low on close · Brooks L2 variant · STC mode |
| **Stop (Layer A)** | 1T below flag low | 1T above flag high |
| **T1** | **50% of pole height** (universal · Q5) | **50% of pole height** (universal · Q5) |
| **T2** | **Day-type conditional per Q5 §2.C** (TN/NV→full_pole · TDD→min(pole,4R) · NeuE→VAH · Norm→POC) | **Mirror Q5 §2.C** (TN/NV→full_pole · TDD→max(pole,−4R) · NeuE→VAL · Norm→POC) |
| **T3** | **NONE always** (continuation · 50/50 split · no trail leg in setup · Pkg 6 may trail T2 → exit when `trail_active=True`) | **NONE always** |
| **trail_active** | True on TN/NV · False on TDD/NeuE/Norm (Q5) | Same |
| **Split** | 50/50 (T1+T2 only) | 50/50 |
| **Day Types** | TN · TDD · NV · **NeuE · Norm** (Q5 expansion) | TN · TDD · NV · **NeuE · Norm** (Q5 expansion) |
| **Source** | Bulkowski 1,028 Bull Flag trades + Brooks H2 + Dalton (NeuE/Norm fade) | Bulkowski + Brooks L2 + STC mode + Dalton (NeuE/Norm fade) |

**Notes:**
- "1T" on MES = 0.25 (per Pkg 1 `adaptive_stop.py`).
- **Brooks H2/L2 trigger nuance is deferred** to Pkg 7 (entry execution strategy). V1 implementation: simple close-through-flag-boundary + 1T. SHADOW data will validate whether requiring a Brooks-style 2-bar pullback within the flag improves win rate.
- **STC (Sell-The-Close) mode for Bear Flag** is deferred to Pkg 7 (STC/BTC modes · DEMO-decided). Pkg 5c emits regardless; downstream filter applies if STC active.
- **Family multiplier** is already wired in Pkg 1 `adaptive_stop.py`: `ATR_MULTIPLIER["Flag"] = 1.5`. Reused as-is.
- **Bar 6+ gating** is operationalized as `MIN_BARS_REQUIRED >= 10` (pole 5+ bars + flag 3+ bars + breakout bar 1) which guarantees Stage 3 reachability after sufficient session data.
- **Pole height definition**: full vertical move from pole start (first directional bar's low for Bull · high for Bear) to pole end (highest high before flag for Bull · lowest low for Bear). Always positive.
- **Flag containment**: the high/low envelope of the flag bars. Breakout = close > max(flag.high) + 1T (Bull) or close < min(flag.low) - 1T (Bear).

---

## §3 · SCOPE · 1 NEW file + 2 modified files + 1 NEW test file + 1 MODIFIED test file

### §3.A · NEW · `backend/v9/systems/five_min/patterns/flags.py`

Two pure-function detectors in one file (mirrors `head_shoulders.py` + `double_bt.py`). **No state, no side effects, no I/O.** Read-only over `bars` (list of dicts with `o/h/l/c/v` keys).

```python
"""flags — Bull Flag (LONG) + Bear Flag (SHORT) continuation detectors per D-091 §9+§10.

Geometric Bulkowski/Brooks-style detection · pole + flag + breakout trigger.

Stage 3 only · gated upstream in five_min_system.process_bar.

Detection geometry defaults (Cursor-seeded per Michael 24/5 16:27 IL · SHADOW-calibratable):
  MIN_BARS_REQUIRED       = 10    # pole 5 + flag 3 + breakout 1 + 1 buffer
  SEARCH_WINDOW           = 30    # last N bars searched for pole start
  POLE_MIN_BARS           = 5     # Bulkowski "high & tight" lower bound
  POLE_MAX_BARS           = 15    # Bulkowski "high & tight" upper bound
  POLE_MIN_HEIGHT_TICKS   = 16    # 4pt = ~1×ATR on 5-min MES typical
  POLE_DIRECTIONAL_PCT    = 0.60  # ≥60% of pole bars must close in pole direction
  FLAG_MIN_BARS           = 3     # Bulkowski "3-bar pullback" minimum
  FLAG_MAX_BARS           = 8     # Bulkowski "8-bar pullback" maximum
  FLAG_MAX_RETRACE_PCT    = 0.50  # flag cannot retrace > 50% of pole
  TICK_SIZE               = 0.25  # MES

These 10 constants are SHADOW-calibratable. Adjust based on hit-rate analysis after
>=20 Bull Flag and >=20 Bear Flag fires. Re-validate via the 18-test golden suite —
any change must keep all 18 green or update fixtures with rationale.
"""
from __future__ import annotations
import logging
import time
from typing import List, Dict, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

# ── Module constants · SHADOW-calibratable (do NOT hardcode at call sites) ──
MIN_BARS_REQUIRED = 10
SEARCH_WINDOW = 30
POLE_MIN_BARS = 5
POLE_MAX_BARS = 15
POLE_MIN_HEIGHT_TICKS = 16
POLE_DIRECTIONAL_PCT = 0.60
FLAG_MIN_BARS = 3
FLAG_MAX_BARS = 8
FLAG_MAX_RETRACE_PCT = 0.50
TICK_SIZE = 0.25

Direction = Literal["LONG", "SHORT"]

_last_warn_ts: Dict[str, float] = {}


def _rate_limited_warn(category: str, msg: str, *args) -> None:
    now = time.monotonic()
    last = _last_warn_ts.get(category, 0.0)
    if now - last >= 60.0:
        logger.warning(msg, *args)
        _last_warn_ts[category] = now


def detect_bull_flag(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Bull Flag (LONG continuation pattern).

    Pattern shape:
      - Pole: strong upward move over POLE_MIN_BARS to POLE_MAX_BARS bars
        · pole height ≥ POLE_MIN_HEIGHT_TICKS × TICK_SIZE
        · ≥ POLE_DIRECTIONAL_PCT of pole bars close above their open (bull bars)
      - Flag: sideways or counter-trend pullback over FLAG_MIN_BARS to FLAG_MAX_BARS bars
        · max retracement ≤ FLAG_MAX_RETRACE_PCT × pole_height
        · flag's lowest low ≥ pole_start_low (flag did not fully retrace the pole)
      - Breakout: last bar close > max(flag.high) + 1T

    Returns:
      (None, 0.0, {}) if no pattern.
      ("LONG", conf, info) if fired. info keys:
        - kind: "BULL_FLAG"
        - pattern_name: "BULL_FLAG_LONG"
        - structural_anchor: float (min(flag.low) − 1T · for adaptive_stop Layer A)
        - pattern_measure: float (positive · = pole_top_high − pole_start_low)
        - pole_top_price, pole_start_price, flag_low, flag_high
        - pole_bars: int (5-15)
        - flag_bars: int (3-8)
        - bar_count: int (pole_bars + flag_bars + 1)
        - stage: 3
    """
    # CC: implement per spec §2.E + detection geometry above.
    raise NotImplementedError("CC implements")


def detect_bear_flag(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Bear Flag (SHORT continuation pattern).

    Pattern shape:
      - Pole: strong downward move over POLE_MIN_BARS to POLE_MAX_BARS bars
        · pole height ≥ POLE_MIN_HEIGHT_TICKS × TICK_SIZE
        · ≥ POLE_DIRECTIONAL_PCT of pole bars close below their open (bear bars)
      - Flag: sideways or counter-trend pullback over FLAG_MIN_BARS to FLAG_MAX_BARS bars
        · max retracement ≤ FLAG_MAX_RETRACE_PCT × pole_height
        · flag's highest high ≤ pole_start_high (flag did not fully retrace the pole)
      - Breakout: last bar close < min(flag.low) − 1T

    Returns ("SHORT", conf, info) on fire · info keys mirror detect_bull_flag:
      pattern_measure = pole_start_high − pole_bottom_low (positive)
      structural_anchor = max(flag.high) + 1T
    """
    raise NotImplementedError("CC implements")


# ── Internal helpers (CC implements · names suggested) ──
# def _find_pole_start(bars, direction, min_bars, max_bars, min_height, directional_pct): ...
# def _validate_pole(pole_bars, direction): returns bool · checks directional ratio
# def _find_flag_end(bars, pole_end_idx, min_bars, max_bars): returns flag_end_idx
# def _validate_flag(flag_bars, pole_start_price, pole_top_price, max_retrace, direction): ...
# def _confidence_flag(pole_height, flag_bars_count, flag_retrace_pct, direction): ...
```

**Confidence formula** (mirrors H&S/DB logic · 0.60 base + 2 × 0.20 quality bonuses):

```
# Pole quality — taller and tighter is better (Bulkowski "high & tight")
pole_height_score = min(1.0, (pole_height_ticks − POLE_MIN_HEIGHT_TICKS) / POLE_MIN_HEIGHT_TICKS)
                    # 0.0 at minimum height (16 ticks) · 1.0 at 32+ ticks (8pt+)

# Flag quality — shallow retracement is better (less risk of failure)
flag_retrace_score = max(0.0, 1.0 − flag_retrace_pct / FLAG_MAX_RETRACE_PCT)
                    # 1.0 at 0% retrace · 0.0 at 50% retrace

conf = 0.60 + 0.20 × pole_height_score + 0.20 × flag_retrace_score
clamped to [0, 1]
```

### §3.B · MODIFY · `backend/v9/systems/five_min/output_schema.py`

Extend `PatternName` Literal with 2 new values (mirrors Pkg 5a + 5b edit · 1-line change):

```python
PatternName = Literal[
    'REACTIVE_LONG', 'REACTIVE_SHORT',
    'INITIATIVE_LONG', 'INITIATIVE_SHORT',
    'INVERSE_HNS_LONG', 'HNS_TOP_SHORT',
    'DOUBLE_BOTTOM_EE_LONG', 'DOUBLE_TOP_AA_SHORT',
    'BULL_FLAG_LONG', 'BEAR_FLAG_SHORT',
]
```

That brings the total to **10 PatternName values**. **DO NOT** change anything else in this file.

### §3.C · MODIFY · `backend/v9/systems/five_min/five_min_system.py` — 3 edits

#### Edit 1 · Import (top of file · after Pkg 5b's `double_bt` import)

```python
from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns, detect_hns_top
from backend.v9.systems.five_min.patterns.double_bt import detect_double_bottom_ee, detect_double_top_aa
from backend.v9.systems.five_min.patterns.flags import detect_bull_flag, detect_bear_flag  # ← NEW Pkg 5c
```

#### Edit 2 · `process_bar` chart-pattern chain (CRITICAL — Flag has DIFFERENT day-type gate than 5a/5b)

The existing post-5a+5b chain:
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
            direction, conf, info = detect_double_bottom_ee(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_double_top_aa(self._bar_buffer)
```

Becomes (Flags are gated on a **DIFFERENT** day-type set · TN/TDD/Variation · NOT NeuE/NeuC/Norm):

```python
# Pkg 5a + 5b · chart patterns (reversal · Stage 3 + day-type gated · D-091 §5+§8)
if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
    if self.current_day_type in (
        "Neutral_Extreme", "Neutral_Center", "Normal", "Variation",
    ):
        direction, conf, info = detect_inverse_hns(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_hns_top(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_double_bottom_ee(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_double_top_aa(self._bar_buffer)

# Pkg 5c · Flag patterns (continuation · Stage 3 + Q5 expanded day-type gate · D-091 §9+§10 + Q5)
if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
    if self.current_day_type in (
        "Trend_Normal", "Trend_DD", "Variation",
        "Neutral_Extreme", "Normal",         # ← Q5 expansion (NeuC + NT remain excluded)
    ):
        direction, conf, info = detect_bull_flag(self._bar_buffer)
        if not direction:
            direction, conf, info = detect_bear_flag(self._bar_buffer)
```

**CRITICAL — Two separate `if` blocks (Q5):**
- Block 1: Neutral_Extreme/Neutral_Center/Normal/Variation (reversal patterns 5a + 5b)
- Block 2: Trend_Normal/Trend_DD/Variation/**Neutral_Extreme/Normal** (continuation patterns 5c · per Q5 expansion)
- **Variation, Neutral_Extreme, Normal** appear in BOTH blocks — they get BOTH reversal and Flag detectors (reversal checked first per chain order · Flag is the fallback continuation/fade)
- **Trend_Normal, Trend_DD** appear ONLY in Block 2 (Flag-only · trends excluded from reversal patterns per D-091)
- **Neutral_Center, Nontrend** appear in NEITHER (no firing · per Q5)

CC may NOT merge the two `if` blocks (different gate sets · different intent: reversal vs continuation). CC may NOT reorder within blocks (5a/5b reversals checked first because they're more selective).

#### Edit 3 · Extend stop-family fork + targets fork to include Flag kinds

Existing post-5a+5b stop fork:
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    family = "HnS"
    structural_anchor = info["structural_anchor"]
elif kind in ("DOUBLE_BOTTOM_EE", "DOUBLE_TOP_AA"):
    family = "Double_BT"
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
elif kind in ("DOUBLE_BOTTOM_EE", "DOUBLE_TOP_AA"):
    family = "Double_BT"
    structural_anchor = info["structural_anchor"]
elif kind in ("BULL_FLAG", "BEAR_FLAG"):
    family = "Flag"
    structural_anchor = info["structural_anchor"]
else:
    family = "Reactive" if kind == "REACTIVE" else "OFA"
    structural_anchor = (
        bar.get("l", entry_price) if direction == "LONG"
        else bar.get("h", entry_price)
    )
```

Existing post-5a+5b targets fork:
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    pm = info["pattern_measure"]
    sign = 1.0 if direction == "LONG" else -1.0
    t1_price = entry_price + sign * 0.50 * pm
    t2_price = entry_price + sign * 0.74 * pm
    t3_price = None
elif kind == "DOUBLE_BOTTOM_EE":
    pm = info["pattern_measure"]
    t1_price = entry_price + 0.50 * pm
    t2_price = entry_price + 0.66 * pm
    t3_price = None
elif kind == "DOUBLE_TOP_AA":
    pm = info["pattern_measure"]
    t1_price = entry_price - 0.50 * pm
    t2_price = entry_price - 0.74 * pm
    t3_price = None
else:
    # OFA path · resolve targets per day_type
    ...
```

Becomes (add Flag branch with **Q5 day-type-conditional T2** · Q5.B Path C verbatim):
```python
if kind in ("INVERSE_HNS", "HNS_TOP"):
    pm = info["pattern_measure"]
    sign = 1.0 if direction == "LONG" else -1.0
    t1_price = entry_price + sign * 0.50 * pm
    t2_price = entry_price + sign * 0.74 * pm
    t3_price = None
elif kind == "DOUBLE_BOTTOM_EE":
    pm = info["pattern_measure"]
    t1_price = entry_price + 0.50 * pm
    t2_price = entry_price + 0.66 * pm
    t3_price = None
elif kind == "DOUBLE_TOP_AA":
    pm = info["pattern_measure"]
    t1_price = entry_price - 0.50 * pm
    t2_price = entry_price - 0.74 * pm
    t3_price = None
elif kind in ("BULL_FLAG", "BEAR_FLAG"):
    # Pkg 5c · Q5 day-type-conditional T2 (Path C · D-091.Q5 LOCKED 24/5 18:45 IL)
    pole = info["pattern_measure"]              # = pole_height · always positive
    sign = 1.0 if direction == "LONG" else -1.0
    t1_price = entry_price + sign * 0.50 * pole  # universal · 50% of pole
    t3_price = None                              # universal · continuation = no T3 leg

    full_pole = entry_price + sign * pole
    stop_dist = abs(entry_price - stop_price)

    # Read VA refs once (NeuE/Norm need them · fallback to full_pole)
    _tpo_refs: dict = {}
    try:
        from backend.v9.api.v9.tpo_routes import _load_sierra_tpo
        _tpo_refs = _load_sierra_tpo() or {}
    except Exception as _e:
        logger.warning("[FiveMin] Pkg 5c · Sierra TPO read failed for Flag T2: %s", _e)

    dt = self.current_day_type
    if dt in ("Trend_Normal", "Variation"):
        # TN / NV → trail mode · T2 = full pole (ceiling)
        t2_price = full_pole
        info["trail_active"] = True
    elif dt == "Trend_DD":
        # TDD → cap T2 at min(full_pole, 4R) for LONG · max() for SHORT (sign-aware)
        cap_4r = entry_price + sign * 4.0 * stop_dist
        t2_price = min(full_pole, cap_4r) if sign > 0 else max(full_pole, cap_4r)
        info["trail_active"] = False
    elif dt == "Neutral_Extreme":
        # NeuE → fade to opposite VA edge (VAH for LONG · VAL for SHORT) · fallback to full_pole
        va_ref = _tpo_refs.get("vah") if direction == "LONG" else _tpo_refs.get("val")
        if va_ref is None or va_ref <= 0:
            logger.warning("[FiveMin] Pkg 5c · NeuE T2 fallback (VAH/VAL unavailable) · using full_pole")
            t2_price = full_pole
        else:
            t2_price = float(va_ref)
        info["trail_active"] = False
    elif dt == "Normal":
        # Norm → POC magnet · fallback to full_pole
        poc_ref = _tpo_refs.get("poc")
        if poc_ref is None or poc_ref <= 0:
            logger.warning("[FiveMin] Pkg 5c · Norm T2 fallback (POC unavailable) · using full_pole")
            t2_price = full_pole
        else:
            t2_price = float(poc_ref)
        info["trail_active"] = False
    else:
        # Should be unreachable (NeuC/NT gated at chain entry · per Q5 do-not-fire)
        logger.warning("[FiveMin] Pkg 5c · unexpected day_type=%s reached Flag T2 fork", dt)
        t2_price = full_pole
        info["trail_active"] = False

    # Guard: t2 must be on the correct side of entry (sanity check for NeuE/Norm where VA ref could be behind entry)
    if (direction == "LONG" and t2_price <= entry_price) or (direction == "SHORT" and t2_price >= entry_price):
        logger.warning(
            "[FiveMin] Pkg 5c · VA ref on wrong side of entry (dt=%s · t2=%.2f · entry=%.2f · dir=%s) · falling back to full_pole",
            dt, t2_price, entry_price, direction,
        )
        t2_price = full_pole
        info["trail_active"] = (dt in ("Trend_Normal", "Variation"))
else:
    # OFA path · resolve targets per day_type
    ...
```

**Q5 monotonicity guarantee:** for Flag patterns under Q5, **T2 is always FURTHER from entry than T1** (or equal in the pathological full_pole-fallback case). For all 5 day-type paths:

| Day Type | T1 (universal) | T2 (Q5) | T2 vs T1 |
|---|---|---|---|
| TN | `entry + sign × 0.50 × pole` | `full_pole = entry + sign × 1.00 × pole` | ✅ further (T2 = 1.00×pole > 0.50×pole = T1) |
| NV | same | `full_pole` | ✅ further |
| TDD | same | `min(full_pole, 4R)` (sign-aware) | ✅ further (cap is ≥ 0.50×pole in normal stop dist) |
| NeuE | same | VAH/VAL (or full_pole fallback) | ⚠️ usually further · guard rejects if behind entry → fallback to full_pole |
| Norm | same | POC (or full_pole fallback) | ⚠️ usually further · guard rejects if behind entry → fallback to full_pole |

**Removed v1 anomaly:** the v1 ×0.46-flat formula produced T2 < T1 in distance (geometric impossibility · D-091.Q5.A contradiction #1). v2 Q5 path REPLACES this with day-type-conditional T2 that always exceeds T1 in distance. The "side-of-entry guard" at the end of the Flag block enforces this for the VAH/VAL/POC paths where ref data could (rarely) be behind entry — fallback to full_pole.

CC must:
1. Implement the 5 day-type branches verbatim per §3.C edit 3 above
2. Include the side-of-entry guard with rate-limited warning
3. Set `info["trail_active"]: bool` in ALL paths (True only on TN/NV)
4. NOT short-circuit any day type into a fallback when the data IS available
5. NOT remove the explicit `logger.warning` lines — they are required per §7 "no silent failures"

### §3.D · NEW · `tests/v9/systems/test_five_min/test_flags.py`

18+ golden tests (see §5). Mirror of `test_double_bt.py` structure.

### §3.E · MODIFY · `tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py`

Append 5 integration tests (mirror the 5 Pkg 5b added):
- `test_bull_flag_skipped_on_nt_day_type` — verify `detect_bull_flag` not called when `day_type=Nontrend`
- `test_bull_flag_skipped_on_neuc_day_type` — verify NOT called on NeuC (per Q5 do-not-fire · Flags fire on TN/TDD/NV/NeuE/Norm but NOT NeuC/NT)
- `test_bear_flag_skipped_on_first_hour_mode` — gating by `mode == DAY_TYPE_MODE`
- `test_bull_flag_runs_after_5a5b_on_variation` — Variation gets BOTH reversal and continuation detectors · Bull Flag called after H&S/DB chain returns None
- `test_bull_flag_emits_t1setup_on_tdd_with_inverted_t2_distance` — emit `BULL_FLAG_LONG` with t1=4510, t2=4509.2 (T2 closer to entry · validate `T1Setup` accepts this)

---

## §4 · Detection geometry · expanded design notes

### §4.A · MIN_BARS_REQUIRED = 10 · "bar 6+" gating

D-091 says "Stage 3 only (bar 6+)" which is operational shorthand for "after the session has produced at least ~6 bars worth of trend establishment." The detector itself requires `MIN_BARS_REQUIRED=10` to have enough data for pole + flag + breakout. Stage 3 gating (`DAY_TYPE_MODE`) in `five_min_system.process_bar` ensures we're post-IB; `MIN_BARS_REQUIRED` ensures we have enough bars regardless.

### §4.B · Pole detection algorithm

```
1. Within the last SEARCH_WINDOW bars, scan from oldest to newest looking for a candidate
   pole start.
2. For each candidate start_idx:
   a. Scan forward looking for the highest high (Bull) or lowest low (Bear)
   b. Pole length = current_idx - start_idx + 1; reject if < POLE_MIN_BARS or > POLE_MAX_BARS
   c. Pole height = pole_top_high - bars[start_idx]["l"] (Bull) or
                    bars[start_idx]["h"] - pole_bottom_low (Bear)
   d. Reject if pole_height < POLE_MIN_HEIGHT_TICKS × TICK_SIZE
   e. Directional ratio = count_of_bars_closing_in_pole_direction / pole_length
      Reject if < POLE_DIRECTIONAL_PCT
3. The latest valid pole becomes the candidate. If none found, return (None, 0.0, {}).
```

### §4.C · Flag detection algorithm

```
4. From pole_end_idx, scan forward looking for a flag of FLAG_MIN_BARS to FLAG_MAX_BARS bars
   that:
   a. Has no bar with close > pole_top_high (Bull) or close < pole_bottom_low (Bear)
      [i.e., flag does not break above/below the pole extreme during formation]
   b. Total retracement = (pole_top_high - min(flag.low)) / pole_height (Bull)
      [Bear: (max(flag.high) - pole_bottom_low) / pole_height]
      Must be ≤ FLAG_MAX_RETRACE_PCT
5. The last flag bar's idx becomes flag_end_idx.
```

### §4.D · Breakout trigger

```
6. The bar AFTER flag_end_idx (i.e., the most recent bar at end of bar_buffer) is the
   candidate breakout bar.
7. For Bull Flag: close > max(flag.high) + TICK_SIZE
   For Bear Flag: close < min(flag.low) − TICK_SIZE
8. If breakout: emit. Else: return (None, 0.0, {}).
```

**Brooks H2/L2 nuance is V2 work.** V1 fires on the first close-through; SHADOW data will tell us if waiting for a 2nd pullback within the flag improves win rate.

### §4.E · Pattern measure (full pole height)

For Bull Flag: `pattern_measure = pole_top_high − pole_start_low` (always positive).
For Bear Flag: `pattern_measure = pole_start_high − pole_bottom_low` (always positive).

Targets are computed in `five_min_system.py` from `pattern_measure` (per §3.C edit 3) · the detector only returns the raw geometric pole height.

### §4.F · Structural anchor

Per D-091 §Stop layers · returned in `info["structural_anchor"]`:
- Bull Flag: `min(flag.low) − TICK_SIZE`
- Bear Flag: `max(flag.high) + TICK_SIZE`

Note: structural anchor is the **flag's** low/high, NOT the pole's start. This is because the flag is the "consolidation pattern" and a break of the flag in the wrong direction invalidates the continuation setup. The pole start can be far below/above and is not a relevant invalidation point.

Passed to `compute_stop()` as the Layer A anchor · `family="Flag"` triggers the existing `ATR_MULTIPLIER["Flag"]=1.5` (Pkg 1 frozen).

### §4.G · No "variant" filter

Unlike DB/DT (Eve&Eve / Adam&Adam variant filter in Pkg 5b), Flag has no variant restriction. D-091 §Scope says "Bull Flag" / "Bear Flag" without qualifiers. CC does NOT add Pennant/half-mast/etc filtering — only the geometric pole+flag+breakout criteria.

---

## §5 · Golden tests · 18 tests (mirror DB/DT structure adapted to Flag geometry)

| # | Test | Pattern | Expected |
|---|---|---|---|
| 1 | `test_bull_flag_classic_high_and_tight` | Bull · 8-bar pole +24 ticks · 4-bar flag retrace 25% · breakout | `("LONG", conf≥0.8, kind="BULL_FLAG", pattern_measure≈24*TICK_SIZE)` |
| 2 | `test_bear_flag_classic_high_and_tight` | Bear · 8-bar pole -24 ticks · 4-bar flag retrace 25% · breakdown | `("SHORT", conf≥0.8, kind="BEAR_FLAG")` |
| 3 | `test_bull_flag_short_pole_rejected` | Bull · 3-bar pole (< POLE_MIN_BARS=5) | `(None, 0.0, {})` |
| 4 | `test_bear_flag_long_pole_rejected` | Bear · 20-bar pole (> POLE_MAX_BARS=15) | `(None, 0.0, {})` |
| 5 | `test_bull_flag_weak_pole_rejected` | Bull · 8-bar pole only 10 ticks (< POLE_MIN_HEIGHT_TICKS=16) | `(None, 0.0, {})` |
| 6 | `test_bull_flag_choppy_pole_rejected` | Bull · 8-bar pole 24 ticks but only 4/8 bars close up (< POLE_DIRECTIONAL_PCT=0.60) | `(None, 0.0, {})` |
| 7 | `test_bull_flag_too_short_flag_rejected` | Bull · valid pole · 2-bar flag (< FLAG_MIN_BARS=3) | `(None, 0.0, {})` |
| 8 | `test_bull_flag_too_long_flag_rejected` | Bull · valid pole · 10-bar flag (> FLAG_MAX_BARS=8) | `(None, 0.0, {})` |
| 9 | `test_bull_flag_deep_retrace_rejected` | Bull · valid pole · flag retraces 70% (> FLAG_MAX_RETRACE_PCT=0.50) | `(None, 0.0, {})` |
| 10 | `test_bear_flag_full_retrace_rejected` | Bear · valid pole · flag rallies above pole_start_high | `(None, 0.0, {})` |
| 11 | `test_bull_flag_no_breakout_rejected` | Bull · valid pole + flag · last close = max(flag.high) (not > +1T) | `(None, 0.0, {})` |
| 12 | `test_bear_flag_no_breakdown_rejected` | Bear · valid pole + flag · last close = min(flag.low) | `(None, 0.0, {})` |
| 13 | `test_bull_flag_insufficient_bars` | Bars[:8] (< MIN_BARS_REQUIRED=10) | `(None, 0.0, {})` |
| 14 | `test_bull_flag_confidence_perfect_high_and_tight` | Bull · 10-bar pole 40 ticks · 3-bar flag retrace 5% | `conf == 1.0 ± 0.05` |
| 15 | `test_bear_flag_confidence_marginal` | Bear · borderline pole (16 ticks) + max retrace (49%) | `conf == 0.60 ± 0.05` (no quality bonus) |
| 16 | `test_bull_flag_structural_anchor_is_flag_low` | Bull · `flag_lows=[4505, 4503, 4504]` | `info["structural_anchor"] == 4503 - 0.25` (NOT pole_start) |
| 17 | `test_bear_flag_structural_anchor_is_flag_high` | Bear · `flag_highs=[4495, 4497, 4496]` | `info["structural_anchor"] == 4497 + 0.25` |
| 18 | `test_bull_flag_pattern_measure_is_pole_height` | Bull · pole 4500→4524 = 24pt | `info["pattern_measure"] == pytest.approx(24.0, abs=0.5)` |

Plus 5 integration tests appended to `test_five_min_day_type_wiring.py` (per §3.E).

**Total: 18 golden + 5 integration = 23 new tests.** Existing 17 wiring tests + 16 H&S tests + 16 DB/DT tests remain green = **~72 tests total in five_min suite after Pkg 5c**.

---

## §6 · Acceptance criteria · G3 PASS gate

CC outputs `STOP — <reason>` if any of these can NOT be achieved without violating a §7 constraint.

1. `pytest tests/v9/systems/test_five_min/test_flags.py -v` → **18 passed**
2. `pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q` → **22 passed** (was 17 · +5 new)
3. `pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q` → **16 passed** (unchanged · Pkg 5a regression check)
4. `pytest tests/v9/systems/test_five_min/test_double_bt.py -q` → **16 passed** (unchanged · Pkg 5b regression check)
5. `pytest tests/v9/systems/ -q` → **636 passed · 1 skipped** (was 613 · +23 net = 18 unit + 5 wiring)
6. `pytest backend/v9/tests/ -q` → unchanged baseline (no regression)
7. `ReadLints` on all 5 changed/new files → 0 new errors
8. `git diff backend/v9/systems/five_min/five_min_system.py` → verify chronic toxicity block (lines around `BELLY_DOMINANCE_RATIO=1.5` + `LOOKBACK_BARS=3` · and the `# Delegate to existing chart_5min detector` block) **byte-identical** to `2c001a2` baseline
9. `backend.main` imports cleanly (smoke: `python3 -c "from backend.v9.systems.five_min.patterns.flags import detect_bull_flag, detect_bear_flag; print('OK')"` → "OK")
10. Smoke test on classic Bull Flag fixture: returns `("LONG", >=0.7, {"kind": "BULL_FLAG", ...})`
11. `PatternName` Literal includes **10** values · `T1Setup(pattern_name="BULL_FLAG_LONG", ...)` validates
12. `T1Setup(pattern_name="BEAR_FLAG_SHORT", t1_price=4490, t2_price=4490.8, ...)` validates with **T2 closer to entry than T1** (no exception)

---

## §7 · Constraints (must NOT violate)

- **No silent excepts.** Every `except` must include `logger.warning("[flags] <message>", ...)` rate-limited (1/min via `time.monotonic()` like the NT skip pattern).
- **No `return None` without prior log** at info-level (rate-limited).
- **No new dependencies.** Use stdlib `typing`, `logging`, `time`. No `numpy`/`pandas`.
- **No "while I'm here" refactors** outside the 5 files listed in §3. Specifically:
  - Do NOT change `_detect_reactive` / `_detect_initiative` / `detect_inverse_hns` / `detect_hns_top` / `detect_double_bottom_ee` / `detect_double_top_aa` signatures
  - Do NOT change `T1Setup` schema fields other than `PatternName` Literal
  - Do NOT modify `head_shoulders.py` or `double_bt.py` (Pkg 5a + 5b frozen · Flag lives in `flags.py`)
  - Do NOT touch `backend/v9/systems/day_type/*` (Pkg 3a frozen)
  - Do NOT touch `backend/v9/systems/footprint/*` (Pkg 2bc frozen)
  - Do NOT touch `manager.py` (Pkg 6 territory)
  - Do NOT touch `adaptive_stop.py` · `ATR_MULTIPLIER["Flag"]=1.5` already wired (Pkg 1)
- **Hardcoded values forbidden** — all 10 detection constants MUST live as module-level UPPER_CASE constants at top of `flags.py`. Tests reference them by import.
- **Chronic toxicity block in `five_min_system.py` MUST stay byte-identical:**
  ```python
  BELLY_DOMINANCE_RATIO: float = 1.5
  LOOKBACK_BARS: int = 3
  ```
  Verify with: `grep -n "BELLY_DOMINANCE_RATIO\|LOOKBACK_BARS" backend/v9/systems/five_min/five_min_system.py` — values must remain `1.5` and `3`.
- **Two separate `if` blocks for chart-pattern chains** — reversal (5a+5b) and continuation (5c) have DIFFERENT day-type gates. Do NOT merge into a single `if` block.
- **`t3_price=None` is INTENTIONAL** for both Bull and Bear Flag (continuation · no T3 · 50/50 split). Do NOT compute T3 numeric.
- **T2 must be FURTHER from entry than T1** (Q5 monotonicity). The day-type-conditional T2 formula always produces this · the side-of-entry guard at end of Flag block enforces it for VAH/VAL/POC paths (fallback to full_pole). Do NOT remove or weaken the guard.
- **`info["trail_active"]: bool`** must be set in EVERY Flag branch (True only on TN/NV · False elsewhere). This is consumed by Pkg 6 — missing = bug.
- **Stage 3 + day-type gating MUST be checked at the integration layer** (in `five_min_system.process_bar`), NOT inside the detector functions. Rationale: detectors are pure functions · gating is system context.
- **Variation, Neutral_Extreme, Normal day types belong to BOTH gates** — reversal block (5a+5b) AND continuation block (5c · per Q5 expansion). This is intentional per D-091.Q5.
- **Q5 day-type-conditional T2 is locked verbatim per §3.C edit 3** — do NOT optimize / merge / refactor the 5 day-type branches into a lookup table. Inline branches are required for code-review clarity.

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
  - backend/v9/systems/five_min/patterns/double_bt.py      (Pkg 5b frozen)
  - backend/v9/systems/woodies/*            (S4 territory)
  - backend/v9/services/trade_manager/*     (Pkg 6 territory)
  - bridge/, sc_study/, frontend/           (out of scope)

🛑 DO NOT add:
  - Inline Flag detection in five_min_system.py (use patterns/flags.py)
  - Brooks H2/L2 nuanced 2-pullback wait (Pkg 7 entry execution)
  - STC mode logic for Bear Flag (Pkg 7 STC/BTC modes)
  - Pennant detection (D-091 §54 explicitly OUT of scope · "Bulkowski 54% failure rate")
  - High-and-tight flag sub-variant filter (V2 work · all flags treated equally in V1)
  - T3 numeric value (it's None · 50/50 split · no T3 leg in setup)
  - News-event filtering (DEMO-1 territory)
  - **Q5 day-type changes** — Flag fires on TN/TDD/NV/NeuE/Norm (5 day types per D-091.Q5) · NeuC and NT are gated out at chain entry. Do NOT add Flag to NeuC or NT. Do NOT remove NeuE or Norm.
```

---

## §9 · Pre-flight · current code state (verified by Cursor 24/5 19:25 IL)

### §9.A · Files that exist (read-only · do NOT modify outside scope)

```
backend/v9/systems/five_min/
├── __init__.py
├── adaptive_stop.py                # Pkg 1 · ATR_MULTIPLIER["Flag"]=1.5 ✅
├── choppiness.py
├── confluence.py
├── cot_amt.py
├── first_hour_buffer.py
├── first_hour_matrix.py
├── five_min_system.py              # 859 LOC after Pkg 5b · 3 edits per §3.C
├── output_schema.py                # 18 LOC after Pkg 5b · 1 edit per §3.B (extend Literal)
├── patterns/                       # Pkg 5a directory · Pkg 5b populated double_bt.py
│   ├── __init__.py                 # 5 LOC · do NOT modify
│   ├── head_shoulders.py           # 265 LOC · Pkg 5a frozen · do NOT modify
│   └── double_bt.py                # 282 LOC · Pkg 5b frozen · do NOT modify
├── q0_dispatcher.py
├── quality_tier.py
├── setup_emitter.py                # Pkg 3a S2 frozen · do NOT modify
├── setup_wrapper.py
├── sr_proximity.py
└── time_stop_mapper.py             # Pkg 3a S2 frozen · do NOT modify
```

Pkg 5c adds: `patterns/flags.py` + `tests/v9/systems/test_five_min/test_flags.py`.

### §9.B · `adaptive_stop.py::ATR_MULTIPLIER` (already includes "Flag" — DO NOT touch)

```python
ATR_MULTIPLIER = {
    "Reactive":  1.0,
    "OFA":       1.5,
    "Flag":      1.5,   # ← Pkg 5c uses this
    "Double_BT": 2.0,
    "HnS":       2.0,
}
```

### §9.C · `setup_emitter.emit_t1_setup` signature (already accepts pattern-measure targets · INCLUDING T2 < T1)

Identical to Pkg 5a + 5b — accepts `t1_price` / `t2_price` / `t3_price=None` directly. No schema change needed. Pydantic validation accepts inverted distances (no `gt` constraint relating t1 and t2).

### §9.D · Prior art (informational · DO NOT copy verbatim — D-091 supersedes target logic)

`backend/v9/systems/chart_5min/patterns/bull_flag.py` and `bear_flag.py` existed in Path B (deleted in `1c805ea` per Pkg 0). Recoverable via:
```
git show 1c805ea~1:backend/v9/systems/chart_5min/patterns/bull_flag.py
```

**What to REUSE (concept only · re-implement clean):**
- Pole detection scan
- Flag detection (3-8 bar pullback)
- Close-through-flag-extreme + 1T trigger
- Confidence base 0.6 + quality bonuses

**What to REJECT (D-091 + Master Sheet 2 supersedes):**
- Path B used **measured-move targets at 1.0×pole + Fibonacci 0.618/1.618** — **REPLACE** with D-091.Q5 Path C: T1=50%×pole universal · T2 day-type-conditional (TN/NV→full_pole · TDD→min(pole,4R) · NeuE→VAH/VAL · Norm→POC) · T3=None always.
- Path B's stop at `entry - 2×ATR` static — **REPLACE** with `flag_low - 1T` (D-091 §Stop layers).
- Path B accepted any flag retracement — **TIGHTEN** to FLAG_MAX_RETRACE_PCT=0.50.
- Path B used 4-bar minimum pole — **TIGHTEN** to POLE_MIN_BARS=5 (Bulkowski "high & tight").

### §9.E · Test baseline (24/5 19:25 IL · HEAD = `2c001a2` · Pkg 5b G3 PASS)

- `tests/v9/systems/` → **613 passed · 1 skipped**
- `backend/v9/tests/` → 531 passed · 2 skipped (unchanged from Pkg 5a/5b baseline)
- `backend/v9/systems/five_min/tests/` → 70 passed · 8 failed (F4 pre-existing · NOT Pkg 5c's responsibility · DO NOT "fix" these as a side effect)
- 1 uncommitted file: `backend/v9/systems/five_min/tests/test_time_stop_mapper.py` (Cursor hand-fix from Pkg 3a Stream 2 G3) · Pkg 5c does NOT touch this file · keep it dirty

---

## §10 · Validation recipe (CC runs after implementation)

```bash
# 1. Lint check (pyflakes optional · ReadLints is authoritative in Cursor G3)
python3 -m pyflakes backend/v9/systems/five_min/patterns/flags.py
python3 -m pyflakes backend/v9/systems/five_min/five_min_system.py

# 2. New tests
python3 -m pytest tests/v9/systems/test_five_min/test_flags.py -v

# 3. Pkg 5a + 5b regression check
python3 -m pytest tests/v9/systems/test_five_min/test_head_shoulders.py -q
python3 -m pytest tests/v9/systems/test_five_min/test_double_bt.py -q

# 4. Wiring regression + new integration tests
python3 -m pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -q

# 5. Full systems suite (target: 636 passed · 1 skipped)
python3 -m pytest tests/v9/systems/ -q

# 6. Backend baseline
python3 -m pytest backend/v9/tests/ -q --no-header

# 7. F4 baseline check (unchanged · 70 passed · 8 failed pre-existing)
python3 -m pytest backend/v9/systems/five_min/tests/ -q --no-header

# 8. Chronic toxicity byte-identical check
grep -n "BELLY_DOMINANCE_RATIO\|LOOKBACK_BARS" backend/v9/systems/five_min/five_min_system.py
# Expected exactly:
# BELLY_DOMINANCE_RATIO: float = 1.5
# LOOKBACK_BARS: int = 3

# 9. Smoke
python3 -c "
from backend.v9.systems.five_min.patterns.flags import (
    detect_bull_flag, detect_bear_flag,
    MIN_BARS_REQUIRED, POLE_MIN_BARS, POLE_MIN_HEIGHT_TICKS,
    FLAG_MIN_BARS, FLAG_MAX_BARS, FLAG_MAX_RETRACE_PCT,
)
print('imports OK')

# Classic Bull Flag fixture · 8-bar pole +24 ticks · 4-bar flag retrace 25% · breakout
# Pole: 4500 → 4524 (24pt = 96 ticks · way above POLE_MIN_HEIGHT_TICKS=16)
# Flag: pulls back to 4518 then breaks at 4525
bars = [
    # Pole bars (8 bars · 3pt each on close)
    {'o':4500,'h':4503,'l':4499,'c':4503,'v':1200},
    {'o':4503,'h':4506,'l':4502,'c':4506,'v':1300},
    {'o':4506,'h':4509,'l':4505,'c':4509,'v':1400},
    {'o':4509,'h':4512,'l':4508,'c':4512,'v':1300},
    {'o':4512,'h':4515,'l':4511,'c':4515,'v':1400},
    {'o':4515,'h':4518,'l':4514,'c':4518,'v':1300},
    {'o':4518,'h':4521,'l':4517,'c':4521,'v':1400},
    {'o':4521,'h':4524,'l':4520,'c':4524,'v':1500},
    # Flag bars (4 bars · pullback to 4518 then sideways)
    {'o':4524,'h':4524,'l':4520,'c':4521,'v':1200},
    {'o':4521,'h':4522,'l':4518,'c':4519,'v':1100},
    {'o':4519,'h':4521,'l':4518,'c':4520,'v':1000},
    {'o':4520,'h':4522,'l':4519,'c':4521,'v':1100},
    # Breakout bar
    {'o':4521,'h':4525,'l':4520,'c':4525,'v':1500},
]
d, c, info = detect_bull_flag(bars)
print(f'detected: {d} conf={c:.2f} measure={info.get(\"pattern_measure\")}')
assert d == 'LONG', f'expected LONG, got {d}'
assert info['kind'] == 'BULL_FLAG'
assert abs(info['pattern_measure'] - 24.0) < 1.0, f'expected pole height 24, got {info[\"pattern_measure\"]}'
print('smoke OK')
"
```

---

## §11 · Stop signals (CC outputs `STOP — <reason>` and halts)

CC must STOP and report (do NOT guess) when:

1. **Cannot construct a fixture** for a §5 golden test (especially the borderline cases #6 directional ratio · #9 deep retrace · #11/12 no-breakout).
2. **Pole detection ambiguous** — multiple non-overlapping poles in the SEARCH_WINDOW · STOP and ask which to pick (newest? tallest? newest valid?). Suggested default: newest valid pole, but DO NOT commit without lock.
3. **T2 < T1 distance assertion failure** — if any existing code (Pydantic validator · pre-existing test · downstream consumer) rejects `BULL_FLAG_LONG` with t2 closer to entry than t1, STOP and report which line rejects it.
4. **Forbidden file in edit list** — any file outside the 5 listed in §3.
5. **Lines around `BELLY_DOMINANCE_RATIO=1.5` / `LOOKBACK_BARS=3` modification proposed** — any edit through these constants = STOP.
6. **Pkg 5a or Pkg 5b file modification proposed** — STOP. Flag must live in `flags.py` exclusively.
7. **Detector function I/O** — DB read, network call, or file I/O = STOP (detectors are pure).
8. **Existing test regression** — any test that was green at `2c001a2` becomes red after Pkg 5c — STOP with diff.
9. **`PatternName` Literal grows beyond 10 values** — if an 11th name is needed, STOP.
10. **Day-type gate ambiguity** — if you discover Variation in both gates (intentional per spec §3.C edit 2) causes a Pkg 5a or 5b test failure, STOP (the test may be wrong, but verify before changing).

For any other ambiguity: STOP. The pre-LIVE protocol forbids silent assumptions.

---

## §12 · Deliverable format (CC outputs after completion)

1. **Files changed** (full paths · A/M/D):
   - `A backend/v9/systems/five_min/patterns/flags.py`
   - `M backend/v9/systems/five_min/output_schema.py` (1 line · extend Literal +2 values)
   - `M backend/v9/systems/five_min/five_min_system.py` (3 edits · including new `if` block for continuation gate)
   - `A tests/v9/systems/test_five_min/test_flags.py`
   - `M tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py` (append 5 tests)

2. **Commit message:**
   ```
   feat(s2): Bull Flag + Bear Flag continuation detectors per D-091 §9+§10

   - NEW backend/v9/systems/five_min/patterns/flags.py
     · detect_bull_flag (LONG · continuation · Bulkowski 1,028 + Brooks H2)
     · detect_bear_flag (SHORT · continuation · Bulkowski + Brooks L2 + STC)
     · 10 SHADOW-calibratable detection constants (POLE_MIN_BARS=5 · MAX=15 ·
       MIN_HEIGHT_TICKS=16 · DIRECTIONAL_PCT=0.60 · FLAG_MIN_BARS=3 · MAX=8 ·
       FLAG_MAX_RETRACE_PCT=0.50 · etc)
     · Targets per D-091.Q5 Path C (universal T1=50%×pole · day-type-conditional T2:
       TN/NV→full_pole+trail · TDD→min(pole,4R) · NeuE→VAH/VAL · Norm→POC · T3=None always)
     · Structural anchor = flag_low ± 1T (NOT pole_start)
     · NO variant filter (Pennant out of scope per D-091 §54)
     · NO Brooks H2/L2 2-pullback wait (Pkg 7 entry execution)
   - MODIFY output_schema.py · extend PatternName Literal (+2 values · total 10)
   - MODIFY five_min_system.py · 3 edits
     1. import detect_bull_flag + detect_bear_flag
     2. NEW separate `if` block for continuation chain (Q5 expanded gate ·
        TN/TDD/NV/NeuE/Norm · Variation+NeuE+Norm in BOTH gates · NeuC+NT excluded)
     3. extend stop family fork (Flag → 1.5× ATR · structural_anchor from info)
        + Q5 day-type-conditional T2 fork (5 branches · trail_active flag ·
        side-of-entry guard · TPO ref reads with fallback to full_pole)
   - NEW test_flags.py · 18 golden tests + 5 day-type T2 path tests
   - MODIFY test_five_min_day_type_wiring.py · +5 integration tests

   Pkg 5c · TN/TDD/NV/NeuE/Norm day types per D-091.Q5 · emit-only
   (Pkg 6 enforces 50/50 split + trail_active · Pkg 7 enforces Brooks H2/L2 + STC mode).
   Sources: Bulkowski 1,028 Bull Flag + Brooks H2/L2 + Dalton (NeuE/Norm fade) · Master Sheet 2.

   D-091.Q5 (Path C) resolves 3 contradictions in v1 spec (T2<T1 · T3 column vs Split ·
   3-way vs 2-way). t2_price always > t1_price in distance per Q5 monotonicity.

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   ```

3. **Self-report:**
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly)
   - Any forbidden constraint accidentally touched? (own up)
   - Chronic toxicity block byte-identical? (yes/no with grep output)
   - Detection constants at module top · referenced by tests via import? (yes/no)
   - Two separate `if` blocks for reversal+continuation chains? (yes/no)
   - T2 < T1 distance passes through emit_t1_setup without rejection? (yes/no · paste test output)
   - Pattern order: H&S → DB/DT → Bull/Bear Flag preserved per §3.C? (yes/no)

4. **ReadLints output** (paste verbatim · 5 files)

5. **pytest output** (paste verbatim · tail 30 lines for each: `test_flags.py` · `test_head_shoulders.py` · `test_double_bt.py` · `test_five_min_day_type_wiring.py` · `tests/v9/systems/`)

---

## §13 · Estimated CC time

| Sub-task | Estimated | Notes |
|---|---|---|
| Read Path B prior art (`git show 1c805ea~1:backend/v9/systems/chart_5min/patterns/bull_flag.py`) + Pkg 5a/5b `patterns/*` for helper patterns | 10 min | Pole+flag is novel geometry vs H&S/DB |
| Write `patterns/flags.py` skeleton (constants + signatures + helpers) | 15 min | Mostly structure |
| Implement `_find_pole_start` + `_validate_pole` helpers | 25 min | Directional ratio + height + bar count gate |
| Implement `_find_flag_end` + `_validate_flag` helpers | 25 min | Retrace + bar count gate |
| Implement `detect_bull_flag` (LONG) | 30 min | Main logic |
| Implement `detect_bear_flag` (SHORT · mirror) | 20 min | Reuse helpers with direction flip |
| Modify `output_schema.py` (1-line Literal extension) | 5 min | |
| Modify `five_min_system.py` 3 edits (especially new `if` block) | 25 min | Two gate blocks need care |
| Write 18 golden tests · 5 integration tests | 80 min | Pole+flag fixtures are slow to construct |
| Run validation recipe · iterate on failures | 35 min | Expect 1-2 iterations (pole detection edge cases) |
| **Total** | **~3-4 hours CC time** | + Cursor G3 ~30 min |

(Pkg 5b took ~3 hours · 5c is similar with new "no T3 / inverted T2" handling balanced against simpler geometry vs DB's variant filter.)

---

## §14 · Post-G3 PASS unlocks

| Unlocked | Why |
|---|---|
| **Phase A chart patterns COMPLETE** | All 10 patterns of D-091 §Scope shipped (Reactive×2 + Initiative×2 + Inv H&S + H&S Top + DB Eve&Eve + DT Adam&Adam + Bull Flag + Bear Flag) |
| **Pkg 3b** (Trail engine) | D-094 LOCKED · handoff ready (`DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md`) · Pkg 3b becomes the next focus |
| **Pkg 3c** (Contract split) | Splits 50/30/20 default · 25/50/25 OFA · 33/33/34 reversals · 50/50 Flag — Pkg 5c is the last input that defines the 50/50 case |
| **Coverage of all 6 trading day types complete** for at least one pattern family · NeuE/NeuC/Norm/NV → 5a/5b reversals · TN/TDD/NV → 5c continuations + OFA |
| **Pre-SHADOW soak window opens** | After Pkg 5c + 3b + 3c · Phase A is feature-complete and ready for SHADOW data accumulation |

---

## §15 · Numerical anomaly handout (CRITICAL · Pkg 6 author must read)

Pkg 5c introduces **two architectural firsts** for Phase A:

### Anomaly 1: T3 = None (50/50 split · no trail)

All prior Phase A patterns (Reactive · Initiative · Inv H&S · H&S Top · DB · DT) emit `t3_price` either as a numeric (OFA day-type-based) or as `None` with `t3_label="trail"` semantics (reversal patterns). Flag emits `t3_price=None` with **truly no T3** — Pkg 6 must:
- NOT engage trail logic post-T2 for Flag patterns
- Split contracts 50/50 (T1 50% · T2 50% · NO T3 tranche)
- Use `trade.pattern_name` to determine if T3 trail applies

### Anomaly 2: REMOVED · superseded by D-091.Q5 Path C

The v1 of this handoff documented an "inverted T2 < T1 distance" anomaly caused by the flat ×0.46 haircut. **D-091.Q5 fixed this contradiction** (24/5 18:45 IL · Michael lock).

Under Q5, T2 is always FURTHER from entry than T1 (by construction · plus a side-of-entry guard at end of Flag block enforces this for the VAH/VAL/POC paths where ref data could rarely be behind entry → fallback to full_pole). See §3.C edit 3 + the "Q5 monotonicity guarantee" table.

**Pkg 6 implications:** distance ordering `|t2 − entry| > |t1 − entry|` is now SAFE to assume for Flag patterns under Q5. The `info["trail_active"]` flag (True on TN/NV · False on TDD/NeuE/Norm) tells Pkg 6 whether to engage trailing logic after T1 (TN/NV) or to enforce a hard T2 exit (TDD/NeuE/Norm).

The only remaining anomaly (Anomaly 1 above · `t3_price=None`) survives Q5 — continuation/fade Flag setups have no T3 leg by design.

---

*End of Pkg 5c handoff · Cursor agent · 2026-05-24 19:25 IL*
*Spec authority: D-091 §9+§10 + Master Sheet 2 (Michael paste 24/5 16:27)*
*Detection geometry defaults: Bulkowski "high & tight" + Path B seed (Michael lock 3 via §Scope)*
*Awaiting Claude Desktop mega-prompt drafting → CC execution → Cursor G3 review*
