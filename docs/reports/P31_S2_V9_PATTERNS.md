# P31 — S2 V9 Pattern Inventory

**Date:** 2026-05-21 · **Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Authority:** V9 (LOCKED 10/5/2026) — pre-10/5 trees ARCHIVED
**Mode:** READ-ONLY · evidence-based · file:line citations
**Scope:** S2 5-min Tree V3.3 (Drive `1dP8x4vaat49BAw0L1DgOBTBqQ4Ci1YllUoWTwoy1DSQ`)
**Companion:** [`P31_S2_V9_SPEC_CODE_AUDIT.md`](./P31_S2_V9_SPEC_CODE_AUDIT.md) (Task 1)

---

## §0 · TL;DR

| Surface | Count | Routes to gateway? | V9 spec coverage |
|---|---|---|---|
| **Path A** — `backend/v9/systems/five_min/five_min_system.py` | **4 pattern variants** (Reactive×2dir, Initiative×2dir) | **YES** — `_gateway.route_setup` at L585 | matches manifest |
| **Path B** — `backend/v9/systems/chart_5min/patterns/` | **19 pattern detectors** (PATTERN_REGISTRY, see §2) | **NO** — generates `Signal` only, never reaches gateway | **15 not in manifest** |
| V9 manifest claim | 2 named families (REACTIVE / INITIATIVE) | n/a | manifest knows of 4 variants only |

**Headline drift:** Path B contains **15 chart-pattern detectors** that the
S2 V9 compliance manifest does not name — bull/bear flag, bull/bear pennant,
double top/bottom, ascending/descending/symmetrical triangle, head &
shoulders + inverse, cup & handle + inverse, rising/falling wedge. They run
on every bar today, generate `PatternDetection` results, but **never reach
the trading gateway.**

---

## §1 · Path A — Production firing patterns (4 variants)

All four are inline in `backend/v9/systems/five_min/five_min_system.py`,
called from `process_bar` at L498-500:

```497:500:backend/v9/systems/five_min/five_min_system.py
        # Run pattern detectors
        direction, conf, info = self._detect_reactive(self._bar_buffer)
        if not direction:
            direction, conf, info = self._detect_initiative(self._bar_buffer)
```

| # | Variant | Function | Lines | Bars required | COT/AMT condition | Confidence range |
|---|---|---|---|---|---|---|
| A1 | REACTIVE LONG | `_detect_reactive` | `:318-329` | 4 | `cot > amt` | 0.75 / 0.80 (poc_rising bonus) |
| A2 | REACTIVE SHORT | `_detect_reactive` | `:332-340` | 4 | `cot < amt` | 0.75 / 0.80 (poc_falling bonus) |
| A3 | INITIATIVE LONG | `_detect_initiative` | `:371-383` | 4 | `cot < amt` | 0.80 fixed |
| A4 | INITIATIVE SHORT | `_detect_initiative` | `:386-395` | 4 | `cot > amt` | 0.80 fixed |

### A1 · Reactive LONG — emit conditions

Per Constitution V3 §Layer 1 T1, the Reactive 4-bar (LONG = "seller weakness"):

| Bar | Code condition (line) | Spec narrative |
|---|---|---|
| b1 | `b1["c"] < b1["o"] and b1_vol > 0` (`:319`) | sellers dominate, bearish close + non-zero volume |
| b2 | `b2_vol <= b1_vol * 0.10` (`:320`) | 90% volume drop vs Bar 1 (sell exhaustion) |
| b3 | `b3["c"] > b3["o"]` (`:321`) AND `belly is not False` (`:322`) | bullish close + buyer-belly footprint |
| b4 | `b4["c"] > b4["o"]` (`:323`) | bullish confirmation close |
| flow | `cur_cot > cur_amt` (`:324`) | COT(cumulative delta) above AMT(90-min average) |

**Bonus:** `poc_rising` over last 3 bars promotes 0.75 → 0.80 (`:325`, `:328`).

### A2 · Reactive SHORT — mirror of A1

| Bar | Code condition (line) | Spec narrative |
|---|---|---|
| b1 | `b1["c"] > b1["o"] and b1_vol > 0` (`:332`) | buyers dominate, bullish + volume |
| b2 | same 90% drop as A1 (`:320` shared) | buy exhaustion |
| b3 | `b3["c"] < b3["o"]` (`:333`) AND `belly is not False` (`:322` shared) | bearish close + seller-belly footprint |
| b4 | `b4["c"] < b4["o"]` (`:334`) | bearish confirmation |
| flow | `cur_cot < cur_amt` (`:335`) | COT below AMT |

**Bonus:** `poc_falling` over last 3 bars promotes 0.75 → 0.80 (`:336`, `:339`).

### A3 · Initiative LONG — emit conditions

Per Constitution V3 §Layer 1 T1, the Initiative 4-bar (LONG = expansion + test):

| Bar | Code condition (line) | Spec narrative |
|---|---|---|
| b1 | `b1["c"] > b1["o"]` (`:372`) AND `1.5 ≤ range ≤ 1.75` (`:367`) | bullish + 6-7 ticks expansion (MES = 0.25/tick) |
| b2 | `b2["l"] > b1["l"]` (`:373`) **OR** `abs(b2["c"] - b2_poc) ≤ 0.5` (`:376`) | higher low **or** POC return (within 0.5pt) |
| b3 | `b3_range > b1_range` (`:369`) | joining bar with range > Bar 1 |
| b4 | `b4["l"] >= b2["l"]` (`:378`) | second test holds |
| flow | `cur_cot < cur_amt` (`:379`) | initiative requires accumulation **below** average |

### A4 · Initiative SHORT — mirror of A3

| Bar | Code condition (line) | Spec narrative |
|---|---|---|
| b1 | `b1["c"] < b1["o"]` (`:386`) AND same expansion check (`:367` shared) | bearish + 6-7 ticks expansion |
| b2 | `b2["h"] < b1["h"]` (`:387`) **OR** POC return (`:388`) | lower high **or** POC return |
| b3 | same `b3_joining` (`:369` shared) | range > Bar 1 |
| b4 | `b4["h"] <= b2["h"]` (`:390`) | second test holds |
| flow | `cur_cot > cur_amt` (`:391`) | distribution above average |

### Path A → exit / management

After detection, `process_bar` runs:

1. **Sizing** (S2-internal, `:401-441`): `full` (3 contracts) / `half` (2) / `reject` (0) — based on bars_formed × COT/AMT alignment × location_vs_poc_vol. **Per-system only — no cross-system inputs.** (Cockpit V5 LOCKED — verified at `:404-409`.)
2. **Stop**: opposite extreme + 2pt fixed (`:506`). 🟡 marked default("to-calibrate-in-SHADOW").
3. **Targets**: T1 = 1R, T2 = 2R, T3 = `0.0` placeholder (`:560-562`, `:581`).
4. **Persist** to `V9FiveMinSetup` (`:537-553`).
5. **Emit** via `setup_emitter.emit_t1_setup` (`:563-570`):
   - quality_tier (S5 TPO advisory)
   - time_stop (S1 Day Type)
   - **`pre_fire_validator`** at `setup_emitter.py:81` — **rejects fail invalid**.
6. **Route** to gateway SHADOW: `self._gateway.route_setup(gateway_setup, 2)` at `:585`.

There is **no per-pattern exit logic** in Path A. Once routed, exit is owned by `BarLevelDetector` (T1/T2/STOP_HIT) and `TradeManager` per P31-01 work — separate from S2.

---

## §2 · Path B — chart_5min PATTERN_REGISTRY (19 detectors, parallel)

`backend/v9/systems/chart_5min/patterns/__init__.py:28-48` defines:

```28:48:backend/v9/systems/chart_5min/patterns/__init__.py
PATTERN_REGISTRY = {
    "reactive_buyer": detect_reactive_buyer,
    "reactive_seller": detect_reactive_seller,
    "initiative_buyer": detect_initiative_buyer,
    "initiative_seller": detect_initiative_seller,
    "bull_flag": detect_bull_flag,
    "bear_flag": detect_bear_flag,
    "bull_pennant": detect_bull_pennant,
    "bear_pennant": detect_bear_pennant,
    "double_bottom": detect_double_bottom,
    "double_top": detect_double_top,
    "ascending_triangle": detect_ascending_triangle,
    "descending_triangle": detect_descending_triangle,
    "head_shoulders": detect_head_shoulders,
    "inverse_head_shoulders": detect_inverse_head_shoulders,
    "symmetrical_triangle": detect_symmetrical_triangle,
    "falling_wedge": detect_falling_wedge,
    "rising_wedge": detect_rising_wedge,
    "cup_handle": detect_cup_handle,
    "inverse_cup_handle": detect_inverse_cup_handle,
}
```

Driven by `Chart5MinDetector.process_bar` (`detector.py:90-177`) → `_run_detection` (`:181-210`) → tier filtering.

### Tier configuration (`models.py:84-118`)

| Tier | Buffer | Cadence | Patterns | File:lines |
|---|---|---|---|---|
| 1 | 30 bars | every bar | reactive_buyer, reactive_seller, initiative_buyer, initiative_seller, bull_flag, bear_flag, bull_pennant, bear_pennant | `models.py:84-92` |
| 2 | 80 bars | every bar | double_bottom, double_top, ascending_triangle, descending_triangle, inverse_head_shoulders, head_shoulders, falling_wedge, rising_wedge, symmetrical_triangle | `models.py:94-103` |
| 3 | 200 bars | every 3 bars | cup_handle, inverse_cup_handle, **inverse_head_shoulders**, **head_shoulders** | `models.py:105-111` |
| 4 | 500 bars | every 6 bars | (empty — Wyckoff "future") | `models.py:113-115` |

**DRIFT-2.A:** `head_shoulders` and `inverse_head_shoulders` appear in **both Tier 2 and Tier 3** (`models.py:99-101` and `:109-110`). The detector function will run twice per qualifying bar — once at Tier 2 cadence (every bar, 80-bar window), once at Tier 3 cadence (every 3 bars, 200-bar window). Latent duplicate work + ambiguous semantics.

### First Hour Eligibility (`models.py:121-128`)

| `bar_count` | Eligible patterns |
|---|---|
| < 4 | none |
| 4-5 | reactive×2 + initiative×2 (4 patterns) |
| 6-9 | + bull/bear flag + bull/bear pennant (8 patterns) |
| 10-11 | + double_bottom + double_top (10 patterns) |
| 12+ | full Tier rotation |

**DRIFT-2.B:** This 4 / 6 / 10 / 12 banding **does not match** the 4 / 6 / 9 / 12 / 13 banding declared in `backend/v9/systems/five_min/first_hour_buffer.py:18-32` (ACCUMULATING / EARLY / DEVELOPING / MATURE / COMPLETE). The two parallel S2 paths use **different pattern-eligibility band schemes**. (Already flagged in Task 1 §2 anchor 1 DRIFT-B; restated here because it is also a pattern-set drift.)

### Pattern detail — sample (`reactive_buyer.py`)

```12:55:backend/v9/systems/chart_5min/patterns/reactive_buyer.py
def detect_reactive_buyer(bars: List[Bar]) -> PatternResult:
    """Detect Reactive Buyer pattern in last 4 bars.

    Criteria:
    1. Bar[-4] or [-3]: strong selling (belly_sellers > 60%)
    2. Bar[-2]: selling exhaustion (belly_sellers drops or belly_buyers rises)
    3. Bar[-1]: reversal — close > open, POC holds above recent low
    4. Price near a support level (val or recent swing low)
    """
    if len(bars) < 4:
        return PatternResult()

    window = bars[-4:]
    b0, b1, b2, b3 = window

    # Phase 1: Selling pressure in first bars
    total_range = max(b.h for b in window) - min(b.l for b in window)
    if total_range == 0:
        return PatternResult()
```

**Same name `reactive_buyer`, very different implementation** from Path A's `_detect_reactive` LONG branch:

| Aspect | Path A `_detect_reactive` LONG | Path B `detect_reactive_buyer` |
|---|---|---|
| Bar 1 trigger | bearish + non-zero volume | `b0.is_bearish or b1.is_bearish` (less strict) |
| Volume drop | 90% (`b2_vol ≤ b1_vol*0.10`) | not checked |
| Belly | reads `belly_ratio_dominant` from Footprint (live) | uses `b.belly_buyers` / `b.belly_sellers` columns on `Bar` dataclass (static per-bar) |
| Confirmation | Bar 4 bullish close (`b4.c > b4.o`) | reversal: `b3.is_bullish and b3.c > b2.mid` |
| Flow | requires `cot > amt` from Footprint | not checked |
| Output entry | `bar.c` (close of Bar 4) | `b3.c` (close of last bar in 4-bar window) |
| Stop | `bar.l - 2.0` | `pattern_low - total_range * 0.25` |
| Targets | T1 = 1R, T2 = 2R | T1 = 2R, T2 = 3R, T3 = 4R |

**These produce different fires on the same bar input.** They share a name but not semantics. This is the largest single concrete consequence of the §3.4 path-A-vs-path-B drift in Task 1.

---

## §3 · V9 spec patterns (per compliance manifest + Constitution V3)

### `compliance_manifest.yaml` (the explicit V3.3 contract)

```13:21:backend/v9/systems/five_min/compliance_manifest.yaml
  - id: REACTIVE_PATTERNS
    name: "Reactive LONG/SHORT 4-bar patterns"
    status: IMPLEMENTED
    evidence: backend/v9/systems/five_min/five_min_system.py

  - id: INITIATIVE_PATTERNS
    name: "Initiative LONG/SHORT 4-bar patterns"
    status: IMPLEMENTED
    evidence: backend/v9/systems/five_min/five_min_system.py
```

**Manifest declares 2 pattern families × 2 directions = 4 named pattern
variants**, with evidence pointing to Path A (`five_min_system.py`).

### Constitution V3 FINAL (T1 narrative)

`docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` defines T1 as the
4-bar Reactive/Initiative pair only. **No chart patterns** (flag, pennant,
H&S, etc.) are mentioned as T1 firing candidates in the locked V9
constitution.

### Drive V3.3 — auth-gated

The Drive doc `1dP8x4vaat49BAw0L1DgOBTBqQ4Ci1YllUoWTwoy1DSQ` returns a
sign-in page on plain export, identical to the Task 1 audit's
`§0` finding. **OPEN QUESTION P-1** (also Task 1 Q1): can Michael paste the
verbatim V3.3 body into `docs/spec_authority/S2_V3_3.md` so this inventory
can be diffed line-by-line against Drive?

---

## §4 · Comparison — code vs spec patterns

| Pattern (code id) | In V9 manifest? | In Constitution V3? | In Path A code? | In Path B code? | Reaches gateway? |
|---|---|---|---|---|---|
| reactive_buyer / Reactive LONG | **YES** | **YES** | YES (`five_min_system.py:318-329`) | YES (`patterns/reactive_buyer.py`) | **A only** |
| reactive_seller / Reactive SHORT | **YES** | **YES** | YES (`:332-340`) | YES (`patterns/reactive_seller.py`) | **A only** |
| initiative_buyer / Initiative LONG | **YES** | **YES** | YES (`:371-383`) | YES (`patterns/initiative_buyer.py`) | **A only** |
| initiative_seller / Initiative SHORT | **YES** | **YES** | YES (`:386-395`) | YES (`patterns/initiative_seller.py`) | **A only** |
| bull_flag | NO | NO | NO | YES (`patterns/bull_flag.py`) | **never** |
| bear_flag | NO | NO | NO | YES (`patterns/bear_flag.py`) | **never** |
| bull_pennant | NO | NO | NO | YES (`patterns/bull_pennant.py`) | **never** |
| bear_pennant | NO | NO | NO | YES (`patterns/bear_pennant.py`) | **never** |
| double_bottom | NO | NO | NO | YES (`patterns/double_bottom.py`) | **never** |
| double_top | NO | NO | NO | YES (`patterns/double_top.py`) | **never** |
| ascending_triangle | NO | NO | NO | YES (`patterns/ascending_triangle.py`) | **never** |
| descending_triangle | NO | NO | NO | YES (`patterns/descending_triangle.py`) | **never** |
| symmetrical_triangle | NO | NO | NO | YES (`patterns/symmetrical_triangle.py`) | **never** |
| head_shoulders | NO | NO | NO | YES (`patterns/head_shoulders.py`) | **never** |
| inverse_head_shoulders | NO | NO | NO | YES (`patterns/inverse_head_shoulders.py`) | **never** |
| rising_wedge | NO | NO | NO | YES (`patterns/rising_wedge.py`) | **never** |
| falling_wedge | NO | NO | NO | YES (`patterns/falling_wedge.py`) | **never** |
| cup_handle | NO | NO | NO | YES (`patterns/cup_handle.py`) | **never** |
| inverse_cup_handle | NO | NO | NO | YES (`patterns/inverse_cup_handle.py`) | **never** |

### Counts

- **In V9 spec, in Path A, fires:** 4
- **In V9 spec, in Path B, never fires:** 4 (same names, different implementations — see §2 contrast table)
- **NOT in V9 spec, in Path B only, never fires:** 15
- **In V9 spec, missing from code:** 0

---

## §5 · Per-pattern fire / block / exit truth table

### Path A only (the production firing set)

| Pattern | Will emit if … | Will block if … | Exit owner |
|---|---|---|---|
| Reactive LONG | 4-bar buffer + b1 sellers + b2 90% drop + b3 buyers + buyer-belly + b4 bull confirm + COT>AMT | any clause above false; or `pre_fire_validator` rejects (R:R<1.0, time_stop out of range, etc. — see `pre_fire_validator.py`); or gateway risk/cluster/cooldown blocks | BarLevelDetector + TradeManager (out-of-S2) |
| Reactive SHORT | mirror of LONG | mirror | same |
| Initiative LONG | 4-bar buffer + b1 bull + 1.5-1.75 expansion + (HL or POC return) + b3 joining + b4 holds + COT<AMT | mirror (any false) | same |
| Initiative SHORT | mirror | mirror | same |

**Fire conditions (post-detect):**

1. `pre_fire_validator(req)` returns `valid=True` (`setup_emitter.py:81`).
2. `_gateway` is injected (`five_min_system.py:571`).
3. `gateway.route_setup(gateway_setup, 2)` does not raise (`:585`).

**Block conditions (system-internal, before gateway):**

| Block point | Condition | File:line |
|---|---|---|
| mode | `mode in {WEEKEND, MAINTENANCE, OVERNIGHT_MODE}` | `:81-98` |
| buffer | `len(bars_5m) < 4` | `:303`, `:357` |
| flow data | `cur_cot is None or cur_amt is None` | `:309-310`, `:363-364` |
| sizing | `calculate_size(...) == "reject"` | `:411-441` |
| validator | `not resp.valid` (5 explicit + 4 Pydantic checks) | `setup_emitter.py:83-85` |

**Block conditions (gateway-side, after S2 emits):**

| Block point | Condition | Owner |
|---|---|---|
| firing-system contract | `system_id ∉ {2,3,4}` | `trading_gateway/gateway.py` `FIRING_SYSTEMS` |
| risk | `risk_validator.check_setup → False` | injected validator |
| cooldown | last fire within cooldown window | `gateway.route_setup` |
| cluster_guard | shadow cluster guard active | `trading_gateway/cluster_guard.py` (D-088) |
| mode flags | `demo_enabled` / `live_enabled` per system | `gateway` |

### Path B (never reaches gateway today)

Every Path B pattern produces a `PatternDetection` and (best-of) a
`SetupPackage` that lands in `Chart5MinSystem._last_setup` and is exposed
via `Chart5MinSystem.get_state()`. **None of these objects ever reach a
`route_setup` call.** Confirmed by:

```bash
$ rg "route_setup" backend/v9/systems/chart_5min/
# 0 hits
```

The only consumers of Path B are:

- `Chart5MinSystem.analyze` → calls `init_event_dispatcher` to publish a
  `Signal` to the EventDispatcher signal queue (`backend/v9/app.py:294` per
  Task 1 §3.4).
- The (un-mounted) `chart_5min/api.py` router that `02_SYSTEMS_SPEC.md:140`
  documents but `backend/v9/app.py` does not mount.

So the 15 chart-pattern detectors are **dead-weight CPU** today. Per Task 1
§5 risk register, "two parallel S2 paths burn CPU + diverge" — this section
quantifies the divergence at **15 unique pattern detectors that are not in
V9 spec.**

---

## §6 · DRIFT summary specific to patterns

| ID | Severity | Drift | Evidence |
|---|---|---|---|
| 2.A | LOW | `head_shoulders` + `inverse_head_shoulders` listed in BOTH Tier 2 and Tier 3 | `models.py:94-103` and `:105-111` |
| 2.B | MEDIUM | First-hour eligibility bands diverge between paths (Path A `first_hour_buffer.py` 4/6/9/12/13 vs Path B `models.py` 4/6/10) | `first_hour_buffer.py:18-32` vs `models.py:121-128` |
| 2.C | HIGH | 15 chart patterns implemented in Path B that are **NOT in V9 manifest, NOT in Constitution V3** | `chart_5min/patterns/*.py` |
| 2.D | HIGH | 4 patterns implemented in BOTH paths with **same name but different semantics** (different bar-condition sets, stops, targets) | §2 contrast table |
| 2.E | LOW | `Chart5MinSystem.is_first_hour` uses `bar_count <= 12`; Path A uses SessionClassifier `CASH_HOURS` transition. **Two different "first hour" definitions** coexist. | `detector.py:48-50` vs `five_min_system.py:201-203` |
| 2.F | LOW | Path A's bonuses (poc_rising → 0.80, b2_alt POC return) and Path B's confidence (e.g. `0.7` near support, `0.5` else in `reactive_buyer.py:58`) use **different confidence scales** for the same nominal pattern. Difficult to reconcile in a single UI / audit. | `five_min_system.py:328` vs `patterns/reactive_buyer.py:58` |

---

## §7 · Open questions for Michael (consolidated, P-prefix to avoid Task 1 collision)

- **P-1** — Drive V3.3 source: same as Task 1 Q1. Paste verbatim into
  `docs/spec_authority/S2_V3_3.md` so the 15 chart patterns can be
  formally classified as REJECT (delete) / DEFER (kept for later T2 use)
  / OUT-OF-SCOPE (S2 owns 4 only; chart patterns belong to a different
  system or were retired).
- **P-2** — Single source of truth for V9 patterns: Path A or Path B?
  This is functionally Task 1 Q3 phrased through the pattern lens. A pattern
  named `reactive_buyer` returns different fires depending on which path
  reads it. We need ONE.
- **P-3** — If Path B is being kept (e.g. as analytics-only), do we
  *delete* the 15 non-V9 patterns to reduce surface area, or do we
  *promote* them into V9 spec via a Constitution V3 amendment? Today they
  are in code limbo: not in spec, not reaching gateway, but consuming
  buffer + CPU on every bar.
- **P-4** — First-hour banding: which is canonical, the Path A
  `first_hour_buffer.py` 5-state machine (4/6/9/12/13) or the Path B
  `FIRST_HOUR_ELIGIBILITY` 3-state map (4/6/10)? The audit's anchor 1
  identified this; from a pattern perspective the answer drives **which
  patterns are eligible at bar 7-9** which is materially different.
- **P-5** — Confidence scale: Path A returns 0.75 / 0.80, Path B returns
  0.5-0.7. Cockpit V5 `last_confluence` reads `int(conf * 100)`
  (`five_min_system.py:523`) which gives 75-80 today. If Path B ever wires
  into the same field it would yield 50-70. Decide a single scale before
  any UI integration.

---

## §8 · Recommended next concrete steps (read-only audit closes here)

1. **Confirm Q3 / P-2** — pin one of Path A / Path B as canonical V9 S2.
2. If Path A canonical → **delete `backend/v9/systems/chart_5min/`
   subtree** (not just stop calling it). It is 19 detectors + matrix +
   schemas ≈ 2,000 LOC of code that today runs on every bar with
   no consumer in the firing path.
3. If Path B canonical → **promote `chart_5min/api.py` mount in
   `backend/v9/app.py`**, **add 15 patterns to compliance_manifest**, and
   wire `Chart5MinSystem.analyze` outputs into a `route_setup` call.
4. Either way: **delete the duplicate `head_shoulders`/`inverse_head_shoulders`
   in `models.py` Tier 3** (DRIFT-2.A) — trivial fix, regardless of P-2.
5. Add a **regression test** that asserts `PATTERN_REGISTRY.keys() ⊆
   compliance_manifest.yaml.allowed_patterns` so a future code-only
   pattern addition fails CI loudly.

---

## Footer

```
   ─────────────────────────────────────────
   📊 STATUS — P31 Task 2 of 3
   ─────────────────────────────────────────
   Current Phase: P31 — Strategic V9 Audit
   Current Task:  Task 2 — S2 V9 Pattern Inventory (this report)
   Code patterns:  Path A 4 ·  Path B 19 (15 unique to B)
   Spec patterns:  manifest 4 ·  Constitution V3 4
   Drift:         15 patterns in code with no V9 spec mapping
   Read-only:     ✓ no code changes
   Next concrete: Michael's call on Q3 / P-2 (pin canonical path)
   ─────────────────────────────────────────
```

*End of P31_S2_V9_PATTERNS.md · 2026-05-21 · Cursor Strategic Partner*
