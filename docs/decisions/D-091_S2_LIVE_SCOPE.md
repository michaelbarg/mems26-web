# D-091 — S2 LIVE Scope (10 Patterns + Adaptive Stop Engine)

**Status:** 🔒 LOCKED
**Date:** 2026-05-23
**Decided by:** Michael Barg (strategic review · pre-LIVE planning)
**Depends on:** D-090 (Path A canonical · prerequisite)
**Related:** Constitution V3 §T1 · Auth Table V1 (21/5) · D-074 (S4 5-min) · D-089 (S3 Firing)
**Registry:** `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §S2

---

## Context

Auth Table V1 (21/5/2026) declared 4 OFA patterns as the only T1 patterns. Subsequent review of `mems26_v9_pattern_tables.xlsx` (Sheet A · B · C) and `MEMS26_S2_Entry_Exit_By_Approach.docx` (22/5) revealed full Bulkowski-backed specifications for 11 additional chart patterns — with statistical confidence (thousands of trades), throwback rates, and per-day-type matrices.

Two structural gaps blocked LIVE readiness independent of pattern count:

1. **Static stop logic:** `bar.low − 2.00pt` is volatility-agnostic. Constitution V3 PART 5 #15 marks "ATR-adaptive" as MISSING.
2. **Static T3:** `T3 = 0.0` placeholder · Constitution V3 §Layer 4 requires day-type-dependent T3 (4R+trail / 4R cap / trail / SKIP).

This decision sets the LIVE scope for both.

---

## Decision

### Scope · 10 Patterns total

| # | Pattern | Status | Stage | Day Types | Direction | Source |
|---|---------|--------|-------|-----------|-----------|--------|
| 1 | Reactive LONG | Path A · needs fixes | 2 + 3 | All except NT | LONG | Auth Table §T1 |
| 2 | Reactive SHORT | Path A · needs fixes | 2 + 3 | All except NT | SHORT | Auth Table §T1 |
| 3 | Initiative LONG | Path A · needs fixes | 2 + 3 | TN / TDD / NV | LONG | Auth Table §T1 |
| 4 | Initiative SHORT | Path A · needs fixes | 2 + 3 | TN / TDD / NV | SHORT | Auth Table §T1 |
| 5 | Inverse H&S | NEW in Path A | 3 only | NeuE / NeuC / Norm / NV | LONG | Bulkowski 3,197 trades · throwback 65% |
| 6 | H&S Top | NEW in Path A | 3 only | NeuE / NeuC / Norm / NV | SHORT | Bulkowski 2,800 trades · throwback 68% |
| 7 | Double Bottom (Eve&Eve) | NEW in Path A | 3 only | NV / NeuE / NeuC / Norm | LONG | Bulkowski 952 trades · throwback 64% |
| 8 | Double Top (Adam&Adam) | NEW in Path A | 3 only | NV / NeuE / NeuC / Norm | SHORT | Bulkowski AA rank 5/21 |
| 9 | Bull Flag | NEW in Path A | 3 only (bar 6+) | TN / TDD / NV | LONG | Bulkowski 1,028 trades + Brooks H2 |
| 10 | Bear Flag | NEW in Path A | 3 only (bar 6+) | TN / TDD / NV | SHORT | Bulkowski + Brooks L2 + STC |

### Coverage matrix · Day Type × Patterns

| Day Type | Available patterns | Count |
|----------|---------------------|-------|
| TN (Trend Normal) | 1, 2, 3, 4, 9, 10 | 6 |
| TDD (Trend DD) | 1, 2, 3, 4, 9, 10 | 6 |
| NV (Variation) | 1-10 (all) | 10 |
| NeuE (Neutral Extreme) | 1, 2, 5, 6, 7, 8 | 6 |
| NeuC (Neutral Center) | 1, 2, 5, 6, 7, 8 | 6 |
| Norm (Normal) | 1, 2, 5, 6, 7, 8 | 6 |
| NT (Nontrend) | none — NO TRADE | 0 |

### Patterns explicitly OUT of scope

- Pennant (Bulkowski 54% failure rate)
- Wyckoff Spring / UTAD (Phase ID = skill · post-LIVE consideration)
- Falling Wedge (up) / Rising Wedge (down) (Bulkowski: "I avoid wedges")
- Triangle Asc / Desc / Sym (selective edge only — BUST mode considered later)
- Cup & Handle (DROP — no intraday source)

These remain available for future scope expansion via Constitution V3 amendment.

---

### Adaptive Stop Engine (NEW)

Replaces `bar.low − 2.00pt` static stop with 3-layer adaptive computation:

**Pre-session phase (before 09:30 ET):**
```python
baseline_atr = ATR_14(yesterday_5min_bars)
```

**During IB (09:30-10:30):**
```python
rolling_atr = moving_average(today_bar_ranges)  # updated per bar
```

**Post-IB (10:30+):**
```python
today_typical = percentile_75(today_bar_ranges)
today_max     = max(today_bar_ranges)
```

**Stop calculation (3 layers, each pattern fire · CORRECTED 2026-05-23 · supersedes earlier pseudo-code):**

**Layer semantics (Michael approved · 2026-05-23):**
- **Layer A · Structural anchor** — desired stop based on pattern (e.g. belly_low − 1T for Reactive LONG)
- **Layer B · Adaptive ATR cap** — **maximum** allowed loss distance (volatility-aware ceiling on width)
- **Layer C · Floor** — **minimum** allowed distance from entry (4 ticks · 1.0pt MES noise floor · enforced even when pattern wants tighter)

```python
# LONG (stop below entry · higher price = tighter)
stop_structural = pattern_anchor - 1*tick                       # Layer A
adaptive_cap    = entry - ATR_MULTIPLIER[family] * today_typical # Layer B (max distance)
floor_price     = entry - 4*tick                                 # Layer C (min distance · 1.0pt)

candidate  = max(stop_structural, adaptive_cap)   # take the TIGHTER of struct vs cap
stop_price = min(candidate, floor_price)          # CLAMP · never tighter than floor

# SHORT (mirror · stop above entry · lower price = tighter)
candidate  = min(stop_structural, adaptive_cap)
stop_price = max(candidate, floor_price)

# Family multipliers (Layer B)
ATR_MULTIPLIER = {
    "Reactive":  1.0,  # tight stops for rotation
    "OFA":       1.5,  # Initiative
    "Flag":      1.5,
    "Double_BT": 2.0,
    "HnS":       2.0,
}

# Binding layer
if stop_price == floor_price:
    binding_layer = "C"
elif stop_price == stop_structural:
    binding_layer = "A"
else:
    binding_layer = "B"

# Reduce-size signal · Layer A binding means pattern's tight stop
# was accepted (noise-vulnerable) → use smaller position
reduce_size_signal = (binding_layer == "A")
```

**Prior pseudo-code bugs (deprecated · do not implement):**
- ~~`stop = max(stop_structural, adaptive_cap, floor)`~~ — did NOT enforce floor as minimum distance · allowed adaptive_cap to produce sub-floor stops.
- ~~`if stop_structural < adaptive_cap: reduce_size`~~ — inequality reversed for LONG · contradicted the inline comment.

**Authority:** unit tests in `tests/v9/systems/test_five_min/test_adaptive_stop.py` (Pkg 1 deliverable) are authoritative · pseudo-code in this section is illustrative. On any conflict — tests win.

### Stop layers — per pattern (Layer A · structural anchor)

| Pattern | Structural anchor (LONG) | Structural anchor (SHORT) |
|---------|--------------------------|----------------------------|
| Reactive | 1T below belly low | 1T above belly high |
| Initiative | 1T below broken level (POC/VAH) | 1T above broken level (POC/VAL) |
| Bull/Bear Flag | 1T below flag low | 1T above flag high |
| Double Bottom | 1T below lower of two bottoms | n/a |
| Double Top | n/a | 1T above higher of two peaks |
| Inverse H&S | 1T below right shoulder | n/a |
| H&S Top | n/a | 1T above right shoulder |

---

### T1 / T2 / T3 — Day-type targets (replaces T3=0.0)

| Day Type | T1 | T2 | T3 | Time Stop |
|----------|----|----|----|-----------|
| Trend Normal | 1R (50%) | 2R + TPO (30%) | 4R + trail (20%) | None |
| Trend DD | 1R | open | 4R cap | 90 min |
| Variation | 1R | 2.5R | trail | 60 min |
| Neutral | 1R | opposite extreme | SKIP T3 | 45 min |
| Normal | 1R | POC | SKIP T3 | 30 min |
| Nontrend | n/a | n/a | n/a | n/a (NO TRADE) |

### T2 Haircuts (per-pattern · applied to chart patterns only)

| Pattern | Haircut on full measure |
|---------|--------------------------|
| Reactive | n/a (uses POC/VAH/VAL structural targets) |
| Initiative | n/a (uses R-multiples) |
| Bull Flag | ×0.46 of full pole |
| Bear Flag | ×0.46 of full pole |
| Double Bottom (Eve&Eve) | ×0.66 of full height |
| Double Top (Adam&Adam) | ×0.74 of full height |
| Inverse H&S | ×0.74 of head-to-neckline |
| H&S Top | ×0.74 of head-to-neckline |

---

### Contract Distribution

| Pattern family | T1 / T2 / T3 split |
|----------------|---------------------|
| Default (Bulkowski-modal) | 50% / 30% / 20% |
| OFA (Reactive + Initiative) | 25% / 50% / 25% (Zohar) |
| H&S + Inverse H&S | 33% / 33% / 34% |
| Double Bottom + Double Top | 33% / 33% / 34% |
| Bull Flag + Bear Flag | 50% / 50% (no T3 — continuation) |

---

### Trade Management (post-fire)

**Trail logic:**
- T1 hit → stop ← Break-Even +1 tick
- T2 hit → trail under HL (LONG) / over LH (SHORT) on 5-min closes only
- Post-T2 → ATR chandelier using `today_typical`

**Risk Rules (active during trade):**

| Trigger | Action |
|---------|--------|
| SWI (Sidewinder) red | tighten stop 2-4 ticks |
| CCI flat 3+ bars | tighten |
| TCCI crosses CCI14 | **EXIT immediately** |
| Direction change detected | EXIT |
| MFE reaches 80% of T2 | tighten |
| time_stop approaching (within 5 min) | tighten |
| News event (FOMC/NFP/CPI) | pause firing 10 min |

---

## Implementation packages (priority order)

| # | Package | Depends on | Estimated time | Blocks LIVE |
|---|---------|------------|----------------|-------------|
| 0 | Path B deletion (per D-090) | — | 1-2 hours | No (hygiene) |
| 1 | Adaptive Stop Engine | — | 1-2 days | YES |
| 2 | OFA fixes (1-4) — Entry signal · belly_ratio config · 7 validator checks | — | 2-3 days | YES |
| 3 | Layer 4 Day-type targets + Trail logic + Contract split | Package 2 | 2 days | YES |
| 4 | Active Risk Rules (SWI/CCI/TCCI/MFE/news) | Package 3 | 2-3 days | Partial |
| 5a | Patterns 5-6: Inverse H&S + H&S Top | Packages 1-3 | 2 days | YES |
| 5b | Patterns 7-8: Double Bottom + Double Top | Packages 1-3 | 2 days | YES |
| 5c | Patterns 9-10: Bull Flag + Bear Flag | Packages 1-3 | 2 days | YES |

**Estimated total:** ~2.5-3 weeks before SHADOW soak.

---

## Outstanding dependencies (not blocking)

1. **Zohar threshold verification** (Auth Table P-6) — `drop_threshold_pct`, `belly_dominance_ratio`, `cot_window_min`, `amt_window_min`, `expansion_ticks`, `min_bars_for_drop`. Implementation proceeds with V1 defaults from Auth Table; calibration via SHADOW soak.
2. **5-min Tree V3.3 verbatim** (P-1) — to verify Auth Table reconstruction. Implementation proceeds with Auth Table as authoritative until V3.3 verbatim arrives.

---

## Acceptance criteria for LIVE-ready

- [ ] D-090 executed (Path B deleted, 0 references remain)
- [ ] Package 1 (Adaptive Stop) — 100% test coverage on stop calculation
- [ ] Package 2 (OFA fixes) — Entry signal matches Auth Table verbatim · 7/7 validator checks coverable
- [ ] Package 3 (Layer 4) — All 6 day-type target schemas implemented · trail logic verified
- [ ] Package 4 (Risk Rules) — At minimum: time_stop, news pause, direction change implemented
- [ ] Package 5a + 5b + 5c — All 6 new patterns fire correctly per Bulkowski spec, gated to correct day types
- [ ] SHADOW soak: ≥20 trades per pattern OR 10 days of data (whichever first)
- [ ] DEMO soak: 7 days on Sierra Sim
- [ ] P-L0 Preflight (per Registry §18)
- [ ] P-L1 LIVE micro (1 contract · 1 day)

---

## Rationale

1. **Direction balance:** 5 LONG patterns (1, 3, 5, 7, 9) + 5 SHORT patterns (2, 4, 6, 8, 10) — full mirror coverage prevents directional bias.
2. **Day-type balance:** Every day type (except NT) has exactly 6 patterns available — balanced opportunity set.
3. **Source quality:** All 6 new patterns are 🟢 in xlsx Sheet A — Bulkowski-backed with thousands of trades of statistical data.
4. **Adaptive stop:** Solves Constitution V3 PART 5 #15 MISSING item. Stop adapts to today's volatility instead of being calibrated for an "average" day that doesn't exist.
5. **Day-type T3:** Solves the T3=0.0 placeholder. Closes the Layer 4 spec gap.
6. **Risk Rules:** Currently 0 of 8 implemented. Closes the gap between code and Auth Table §Layer 4 Risk Management.

---

## Pkg 3a sub-decisions · LOCKED 2026-05-23 20:10 IL

Three operational decisions resolved before drafting the Pkg 3a mega-prompt. These are sub-decisions of D-091 §"Day-type targets" and authoritative for Pkg 3a implementation. Tests under `tests/v9/systems/test_day_type/` and `tests/v9/systems/test_five_min/` are authority on any conflict.

### D-091.Q1 · NeuE vs NeuC classification criteria — LOCKED

`Neutral` is split into two day types per EXIT_V6 (45min vs 30min Time Stop window). Classification rule for S1:

| Day Type | Code | Rule (Dalton terminology) |
|----------|------|---------------------------|
| Neutral Extreme | NeuE | Cash open price is **at or outside yesterday's VAH/VAL** (within ±1 tick of VA edge or beyond) |
| Neutral Center  | NeuC | Cash open price is **inside yesterday's Value Area**, closer to POC than to either VA edge |

**Data source:** yesterday's VA bounds (VAH · POC · VAL) from S5 TPO via cross-system snapshot.

**Fallback when S5 VA unavailable at classification time:** classify as **NeuC** (the safer / less aggressive choice · 30min window · shorter Type C exposure). Log `[S1] NeuE/NeuC fallback to NeuC · VA missing` at info level (rate-limited per session).

**Why this rule:** matches Mind Over Markets / Dalton convention — extreme opens lead to faster rejection / wider session range (45min for thesis to fail), center opens compress around value (30min before fade is confirmed). Empirically validated by Master Summary Sheet 3.

### D-091.Q2 · NT NO_TRADE gate location — LOCKED

`Nontrend` day type = NO TRADE per D-091 §Coverage Matrix and EXIT_V6 §Time Stop windows (NT row = "n/a · NO TRADE לכתחילה").

**Implementation:** **early-skip** in `FiveMinSystem._check_setup` (or whichever method calls `_detect_reactive` / `_detect_initiative`), BEFORE detection runs:

```python
# Pseudocode · authoritative implementation in Pkg 3a tests
if self.current_day_type == DayType.Nontrend:
    self._nt_skip_count += 1
    if self._last_logged_bar != self.buffer_size:
        logger.info("[S2] NT skip · day_type=Nontrend · bar=%d", self.buffer_size)
        self._last_logged_bar = self.buffer_size  # one log per bar (rate-limit)
    return  # skip detection entirely · do not emit
# normal detection continues below
direction, conf, info = self._detect_reactive(self._bar_buffer)
...
```

**Counter exposure:** `_nt_skip_count` exposed via `shadow_routes.py` SHADOW analysis endpoint (e.g. `/api/v9/shadow/system/2/skips`) so SHADOW soak can verify NT skips happen and at expected frequency.

**Not chosen:** skip in `setup_emitter` (wastes detection CPU) · skip in `pre_fire_validator` (full pipeline waste · pollutes `bridge_test_signals`).

### D-091.Q4 · TradeManager wiring scope in Pkg 3a — LOCKED · "Emit-only"

Pkg 3a is **emit-only** for Type C time-based exit:

| What Pkg 3a does | What Pkg 6 (LAST · TradeManager rewrite) does |
|------------------|------------------------------------------------|
| Compute `time_stop_minutes` per day type from `day_type_targets.py` | Build hook-based architecture with `TypeCTimeExitRule` |
| Emit `time_stop_minutes` field in `T1Setup` schema | Implement DD check (`current_price ≤ entry - 1T` LONG · mirror SHORT) |
| TradeManager persists `time_stop_minutes` to `V9Trade` row | Implement clock check (`now - fire_time ≥ window`) |
| Unit tests verify `time_stop_minutes` is correct per day type | Implement market_exit + cancel_stop action when both fire |

**Rationale:**
- "Smallest correct change" per pre-LIVE protocol — Pkg 3a does not modify `backend/v9/services/trade_manager/manager.py`.
- Pkg 6 is by design the rewrite that adds rule architecture — putting Type C enforcement in Pkg 3a creates throwaway work or pre-locks the hook API before Pkg 6 designs it.
- Phase A soak UAT for Pkg 3a verifies emission correctness only · Type C enforcement UAT is deferred to Pkg 6 soak.

### Pkg 3a stream split

Pkg 3a is now sequenced as three CC mega-prompts (one thread at a time per pre-LIVE protocol). Refined 23/5 20:34 IL with Michael's Option B decision below.

| Stream | Scope | Estimated CC | Blocks |
|--------|-------|--------------|--------|
| **Stream 1 · EXIT_V6 fix** | Split `DayType.Neutral` → `Neutral_Extreme` + `Neutral_Center` in enum + targets_table + 6 of 7 hits in state_machine + classification logic in `api.py` per Q1 + mark Nontrend NO_TRADE in targets_table. Compliance manifest E2 PARTIAL → IMPLEMENTED. Excludes `state_machine.py` line 535 (`_rescore_from_behavior`) — deferred to Stream 1.5 per Option B. | ~3-4 CC hours | Stream 1.5 + Stream 2 + Pipeline 3 verify |
| **Stream 1.5 · prev_day wiring** | Wire `prev_vah` / `prev_val` / `session_open_price` / `session_date` into `DayTypeStateMachine.__init__` via `_stage_a1` (where `load_tpo_previous_day_summary` is presumably already called). Then replace line 535's `return DayType.Neutral` with `classify_neutral_subtype(...)`. | ~1-2 CC hours | (none · cleanup task) |
| **Stream 2 · Pkg 3a proper** | NEW `day_type_targets.py` · wire `T1Setup` t3_price + time_stop_minutes per day type · NT gate per Q2 · fix `self.opening_type → self.current_day_type` bug · unit tests × 7 day types | 1 CC day | Pkg 3b/3c (TradeManager trail · contract split) |

Stream 1.5 and Stream 2 are **independent** (different files · no conflict) and can run in parallel after Stream 1 G3 PASS.

### Option B (23/5 20:34 IL · Michael) — why line 535 deferred to Stream 1.5

The "smallest correct change" review identified that `state_machine.py` line 535 (`_rescore_from_behavior`) is the only call site that needs `prev_vah`/`prev_val`/`session_open_price`/`session_date` as instance fields on the state machine — fields that **do not currently exist** on `DayTypeStateMachine`. Wiring them in would require touching `__init__` + `_stage_a1` + the hydration path · which expands Stream 1's blast radius significantly.

**Option B descopes line 535 from Stream 1.** State machine continues to return `DayType.Neutral` from that method · which aliases to `Neutral_Center` config (30min · HALF sizing) via `targets_table._ALIASES["NEUTRAL"] = "Neutral_Center"`. This is the **safe default** per the Q1 fallback rule. The corrected NeuE/NeuC classification flows through `api.py` line 190 which already has direct access to `prev_day` data via `load_tpo_previous_day_summary()` — that path emits the correct subtype.

**No regression:** S2 consumes the corrected classification through the api path · downstream code that reads `DayType.Neutral` still works · existing DB rows still load.

**Stream 1.5 cleanup** (drafted post-G3): adds the 4 instance fields + line 535 rewrite. Small task · low risk · keeps Stream 1 clean.

---

## D-091.Q5 · Pkg 5c (Bull/Bear Flag) targets + scope — LOCKED 2026-05-24 18:45 IL

While preparing Pkg 5c handoff Michael identified **3 internal contradictions** in D-091's Flag spec and proposed **Path C · day-type conditional flag targets** as the resolution. After Cursor verified the contradictions against the code (`T1Setup.t2_price: Field(gt=0)` · `targets_table` precedent · `_load_sierra_tpo()` data availability), Michael locked Path C with three sub-choices.

### Q5.A · The 3 contradictions (all confirmed real)

| # | Source | Contradiction |
|---|---|---|
| 1 | D-091 §T2 Haircuts row 5: "Bull/Bear Flag ×0.46 of full pole" | `T1=0.50×pole` vs `T2=0.46×pole` puts T2 closer to entry than T1 (geometric impossibility). Pydantic schema would also reject `t2_price < t1_price` for LONG (and vice versa for SHORT) downstream. |
| 2 | D-091 §T1/T2/T3 table row 1 ("Trend Normal: T3=4R+trail") vs §Contract Distribution row 5 ("Bull/Bear Flag 50/50 (no T3)") | Same pattern fires on TN day → spec says trail T3 AND no T3 simultaneously. |
| 3 | D-091 §Contract Distribution row 5: "50/50 (no T3)" is the only 2-way split in the table (all other patterns use 33/33/34 or 50/30/20). | T3 column elsewhere in D-091 vs absent here — implementation must handle 2-way as architectural exception. |

### Q5.B · Path C resolution (LOCKED 24/5 18:45 IL)

**Universal T1:** `T1 = entry + sign × 0.50 × pole_height` (50% of pole · NOT day-type-dependent).

**Day-type conditional T2:** (per Michael's Path C proposal)

| Day Type | T2 formula | trail_active | Fire? | Logic |
|---|---|---|---|---|
| Trend_Normal | `full_pole` (numeric · ceiling) | **True** | YES | TN momentum → ride asymmetric tail · `trail_after_t2` already wired in `targets_table` |
| Variation | `full_pole` (numeric · ceiling) | **True** | YES | NV trend-day-with-pullbacks → trail |
| Trend_DD | `min(full_pole, entry + sign × 4 × stop_dist)` | False | YES | TDD distributed direction → cap at distribution boundary |
| Neutral_Extreme | `VAH` (LONG) / `VAL` (SHORT) | False | **YES (NEW vs D-091)** | NeuE open at VA edge → fade to opposite extreme · Dalton balance |
| Normal | `POC` | False | **YES (NEW vs D-091)** | Norm balance day → POC magnet · "80% of TR breakouts fail" — take quick ref target |
| Neutral_Center | n/a | n/a | **NO (do not fire)** | NeuC = rotation around POC → momentum logic doesn't apply |
| Nontrend | n/a | n/a | NO (no_trade=True existing) | NT is NO_TRADE per D-091.Q2 |

**Universal split:** 50/50 (no T3 leg · `t3_price=None`). D-091 §Contract Distribution row 5 survives intact.

**`t2_price` is always numeric > 0** — no T1Setup schema change. For TN/NV trail mode, T2 = full pole serves as a ceiling that Pkg 6 may exit at if trail does not catch the move first.

### Q5.C · Scope expansion vs D-091 §Coverage Matrix

D-091 §Coverage Matrix (lines 42-52) currently lists Bull Flag / Bear Flag only under TN, TDD, NV. **Q5 amends this** to include NeuE + Norm with reference-price T2.

| Day Type | D-091 original | D-091.Q5 amended |
|---|---|---|
| Trend Normal (TN) | YES (1, 2, 3, 4, 9, 10) | YES — unchanged |
| Trend DD (TDD) | YES | YES — unchanged |
| Variation (NV) | YES (1-10 all) | YES — unchanged |
| **Neutral Extreme (NeuE)** | **NO** (1, 2, 5, 6, 7, 8) | **YES** for Flag (1, 2, 5, 6, 7, 8, 9, 10) |
| **Normal (Norm)** | **NO** (1, 2, 5, 6, 7, 8) | **YES** for Flag (1, 2, 5, 6, 7, 8, 9, 10) |
| Neutral Center (NeuC) | NO | NO — unchanged (Path C agrees) |
| Nontrend (NT) | NO_TRADE | NO_TRADE — unchanged |

**Rationale:** Flag is a momentum-continuation pattern but it can fire as a **continuation of a counter-move on rotation days** when the counter-move reaches a value-area edge (NeuE) or POC (Norm). Brooks's "80% of TR breakouts fail" cuts the other way too — when a breakout AT the VA edge or AT POC IS in the direction of fade, Flag is the entry signal for the rotation back to balance.

This is consistent with Dalton's "Mind Over Markets" — at value-area edges, fades to the opposite edge are higher-probability than continuations. Flag-pattern entries provide a structured trigger for those fades.

### Q5.D · Implementation location — inline in `five_min_system.process_bar` (LOCKED · per Pkg 5a/5b precedent)

Target resolution for Flag lives in `five_min_system.py::process_bar`, mirror of the H&S + DB/DT branches. **NOT** a new file. Reasoning:

- Matches Pkg 5a (`if kind in ("INVERSE_HNS", "HNS_TOP"): ...`) and Pkg 5b (`elif kind == "DOUBLE_BOTTOM"`) precedent.
- Keeps day-type-conditional T2 logic adjacent to the other pattern target forks.
- VAH/VAL/POC retrieval reuses the existing `_load_sierra_tpo()` pattern (already proven in `_compute_location_vs_poc`).
- No new module · no new import paths · no test-discovery friction.

**`trail_active: bool`** is returned in `info` dict from `detect_bull_flag` / `detect_bear_flag` (Pkg 5c detector) and propagated via `compute_targets_for_day_type` → `trail_after_t2` field (already existing in `targets_table.py`). Pkg 6 TradeManager consumes `trail_after_t2` to decide trail vs hard-exit at T2.

### Q5.E · Forward consequences

- **Pkg 5c handoff (`DESKTOP_PKG5C_FLAGS_HANDOFF.md`)** can be written once Master Sheet 2 detection geometry rows (entry trigger · pole criteria · flag retrace · bar 6+) are provided.
- **D-091 §Coverage Matrix** is amended in-place by this Q5 doc (no separate D-095 needed).
- **`targets_table.py`** is unchanged — Pkg 5c does NOT add Flag rows there. Inline logic in `five_min_system.py` reads `trail_after_t2` from existing day-type entries.
- **`T1Setup` schema** is unchanged — `t2_price` stays `Field(gt=0)` with numeric values for all Flag cases.
- **Pkg 6 (TradeManager rewrite)** must implement: read `trail_after_t2` flag (already in T1Setup canonical output via `targets_table`) → if True, trail mode active after T1; if False, hard exit at T2.

### Q5.F · Sub-decisions Michael chose (24/5 18:30-18:45 IL via Cursor question form)

1. **Scope:** A2 (extend D-091 §Coverage Matrix to include NeuE + Norm for Flag) ✅
2. **Schema:** B3 (reuse existing `trail_after_t2` flag in `targets_table` · keep `t2_price` numeric · no T1Setup change) ✅
3. **Location:** C1 (inline in `five_min_system.process_bar` per Pkg 5a/5b precedent) ✅

---

*End of D-091. Sign-off: Michael Barg, 2026-05-23.* · Sub-decisions Q1/Q2/Q4 sign-off: Michael Barg, 2026-05-23 20:10 IL. · Q5 sign-off: Michael Barg, 2026-05-24 18:45 IL.
