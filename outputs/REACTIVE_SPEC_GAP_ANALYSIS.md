# Reactive-Long Detector Library — GAP ANALYSIS vs. MEMS26 AS-BUILT

_Author: Cowork · 2026-06-29 · Evidence-based, code-cited. No code modified._
_Spec under review: `outputs/reactive_detector_lib_spec.py` (v0.1, Strategic-Architect → CC)._
_Index consulted first (per CLAUDE.md): `docs/spec_authority/PATTERN_ACCESS_MAP.md`, `docs/FLAG_INDEX.md`, `docs/SOURCE_OF_TRUTH.md`._

---

## 1 · What the spec IS (and its key design decisions)

`reactive_detector_lib_spec.py` is a **pure, stateless detector library** — not a system. It is a
collection of boolean "is this setup present right now?" functions over a rolling buffer of
**closed 5-min bars**, returning a typed `Setup` (entry / stop / T1-T3) or `None`. It is built for
the **long side only** ("the reactive-long pattern and its variations"), and it replaces the single
rigid 4-bar REACTIVE template with a **taxonomy of 12 detectors routed by regime**.

### Core design decisions

1. **Regime routing (`scan()`, spec L464-484).** One entry point, called once per closed bar,
   dispatches by `ctx.regime` and `ctx.opening_window`:
   - `BALANCE` → **reversal family** (8 detectors: double_bottom_div, one_two_three_low, spring,
     absorption, climax, bullish_engulfing, b_shape_flush, poor_low_retest).
   - `TREND_UP` → **continuation family** (hidden_div, pullback_flag) — "the inverted reactive long".
   - `opening_window` → **opening family** (open_test_drive, open_rejection_reverse), Dalton opening types.
   - Best-tier-first dedup (L480-484).

2. **Robustness tiers A–D** (spec docstring L18-22) order the build: **A** = clean structure +
   invalidation (double_bottom_div, one_two_three_low, hidden_div); **B** = strong but
   threshold-sensitive (spring, absorption, pullback_flag); **C** = high-payoff/loose/rare
   (climax, engulfing, b_shape_flush); **D** = context-dependent (poor_low_retest, opening pair).

3. **Shared entry gate (`passes_entry_gate`, L160-170) — necessary-not-sufficient.** A detector
   firing is only a candidate. To become a `Setup` it must ALSO pass:
   - **no `news_blackout`** (L162),
   - **proximity to a qualifying VP level** (entry within `2×vp_level_max_ticks` of the level, L165;
     and `_near_support` must find a level within `vp_level_max_ticks` of the structure low, via
     `_finish` L200-201),
   - **LSMA reclaim** (`reclaim.c > lsma AND lsma_slope >= 0`, L167-169),
   - and the correct **regime** (enforced in `scan()` and inside continuation detectors).
   The VP support set is `{dval, pval, ib_low, ppoc, dpoc, vwap, naked_pocs}` (`_support_levels`, L144-147).

4. **Structured stops (`_build_long`, L181-186).** Stop = `struct_low − stop_buffer_ticks·tick`,
   then **clamped to [stop_min_pts, stop_max_pts]** = [4.0, 12.0] pts. Stop is anchored to the
   **structural extreme of the detected pattern** (each detector passes its own `struct_low`).

5. **VP-level targets with minimum R:R (`_targets_above`, L171-180; `_build_long` L187-195).**
   Targets are **structural prices**, not R-multiples: continuation mode → `{dvah, ib_high,
   ib_high+ext, ib_high+2·ext, pday_high}`; reversal mode → `{dpoc, vwap, dvah, ib_high, pvah,
   pday_high}` + naked POCs, filtered to levels above entry and sorted. **Whole-trade R:R is
   gated**: rejects the setup if `(t3 − entry) < min_rr_overall·stop_pts` (= 1.5×, L193).

6. **CVD / delta / footprint are first-class inputs** baked into `Bar` (L31-40): every bar carries
   `volume`, **per-bar `delta`** (ask-initiated − bid-initiated), and **session `cvd`** (running
   cumulative). Detectors use them directly — e.g. CVD-divergence magnitude
   (`double_bottom_div` requires price equal/lower low BUT `cvd` higher low ≥ `div_min_frac` of the
   recent CVD range, L224-226); delta-flip on reclaim (`_delta_flip_ok`, L152-156); footprint
   diagonal imbalance config (`imbalance_ratio`, `stacked_levels`, L85-88, reserved for the
   absorption/imbalance refinement).

7. **The non-negotiables (spec L10-17):**
   - **#1 — Compute order flow (CVD/delta/footprint) on ES, the liquid leg; EXECUTE on MES.**
     "MES order flow is too thin to threshold directly."
   - **#2 — Every number in `DetectorConfig` is a CALIBRATION TARGET, not a constant.** Fit on
     ≥24h of ES RTH order-flow (London + NY Open + NY Close) before locking; no threshold changes
     off a single session.
   - **#3 — A detector firing is necessary, not sufficient** (the shared gate above).

In one line: **the spec keeps the "reactive" idea but moves the edge from a single fragile
candle-template to (a) a structural-pattern taxonomy, (b) a VP-location + LSMA + news gate, and
(c) real ES order-flow divergence/flip confirmation — with structural stops/targets and an R:R floor.**

---

## 2 · Capability-by-capability mapping to the AS-BUILT system

Legend: **EXISTS** (built, reusable) · **PARTIAL** (a version exists but differs materially) · **MISSING** (no equivalent).

| Spec capability | Status | Where it lives / why it differs |
|---|---|---|
| 4-bar reactive template (the thing being replaced) | EXISTS | `five_min_system.py::_detect_reactive` L580-720. B1 bearish climax + high vol → B2 90%/VSA volume collapse → B3 bullish + POC-rising → B4 close beyond B3 extreme. SHORT mirror. Entry = B4 close (`entry_price = _completed_bar["c"]`, L1083). |
| **Regime routing** (BALANCE→reversal / TREND_UP→continuation / opening) | PARTIAL | The system has **day-type** (7-type S1 classifier) and **direction context**, but **no `BALANCE/TREND_UP` `Regime` enum routing inside the detector**. Patterns are split CONT vs REV by *name* (`REVERSAL_PATTERNS`, gateway L334), and day-type is applied as a **gateway gate**, not a detector dispatcher. Reactive itself is hard-classified **CONT** (PATTERN_ACCESS_MAP §1) and is the SAME pattern in every regime. |
| **VP-level entry gate** (entry must be near dval/pval/ib_low/ppoc/dpoc/vwap) | PARTIAL | Two partial pieces, both **post-detection in the gateway**, not in the detector: (a) `daytype_position_gate.py` `_decide_normal` L88-112 gates LONG below POC / SHORT above POC; (b) legacy `reactive_location_gate.py` (POC-only) is **inert** (FLAG_INDEX: superseded by position gate). The detector `_detect_reactive` itself **never sees a VP level** — it computes `location_vs_poc` only AFTER firing for *sizing* (L1167, `_compute_location_vs_poc` L865-891). The spec's multi-level support set (VAL/PVAL/IB_low/PPOC/VWAP/naked-POC) does NOT exist as a gate; only POC is checked. |
| **CVD-divergence detection** (price LL + CVD HL) | MISSING | No code computes price-vs-CVD divergence for entry. CVD exists in the DB (`v9_bars_5min.cumulative_delta`) and feeds **only** the gateway **direction** gate (`direction_context_live.py` `cvd_slope`, L100-116) — a binary "is direction UP/DOWN", never a divergence at a swing low. `_detect_reactive` reads **no CVD at all**. |
| **Footprint imbalance** (diagonal bid/ask ≥ 3:1, stacked levels) | PARTIAL-DISABLED | The S3 footprint system exists (`forces_history`, belly, COT/AMT) and `_get_belly_ratio_from_footprint` L486-510 reads ask/bid, but **S3 is fully muted**: `FOOTPRINT_DISABLED=1` + `S3_MUTE=1` (FLAG_INDEX). `_footprint_state()` returns `{}` (L473). So belly/COT/AMT are all `None` → "graceful pass". There is **no diagonal-imbalance / stacked-imbalance ratio detector** at all (the bridge has `imbalance_flags_stream`/`stacked_imbalances_stream`, but they are not wired into S2 detection). |
| **Structured VP-level stops** (struct extreme − buffer, clamp 4-12 pts) | PARTIAL | `config/stop_anchors.yaml` + `adaptive_stop.compute_stop_v2` (wired at L1105-1143) give per-pattern **structural anchors** with a 3-tick offset and an ATR/`max_risk_points` cap. For Reactive: `support_zone`, window 4, `max_risk_points: 15` (stop_anchors.yaml L91). This is **conceptually identical** to the spec's "beyond structural extreme + min/max clamp", but the clamp is a single `max_risk_points` cap (15-25 pt), not the spec's `[min=4, max=12]` two-sided clamp, and the anchor is a **cluster-low window**, not the spec's per-detector struct_low. |
| **Structured VP-level targets** (dpoc/vwap/dvah/ib_high/pvah; min R:R) | PARTIAL | `structural_targets.py` (flag `DAYTYPE_TARGETS_STRUCTURAL=1`, ON) overrides T1/T2/T3 with **IB/POC/VA** prices **per day-type** (L94-114). This is the closest existing analog and it **aligns with the spec's intent**. BUT: (a) it is keyed by **day-type**, not by reversal/continuation *mode*; (b) it has **no whole-trade R:R floor** (the spec's `min_rr_overall` gate at L193 has no equivalent — the system instead has a per-fire stop-risk sanity band `MEMS_MIN/MAX_RISK_POINTS` 2-60 pt, `pre_fire_validator`); (c) targets come from `v9_tpo_sessions` (CASH), not a `dvah/dval/naked_pocs` set; naked POCs are not modeled. |
| **LSMA reclaim gate** (close > LSMA AND slope ≥ 0) | PARTIAL | LSMA exists and is live (`v9_bars_5min_woodies.lsma_value`). It powers `DIRECTION_LSMA_VETO` (direction = LSMA side) and `CONT_TREND_FILTER` (K-bar sustained LSMA side, L332-346). BUT the existing use is **direction/sustain**, not the spec's **per-bar "this reclaim bar closed back above LSMA with non-negative slope"** entry condition. `lsma_slope` as a gate input is **not** computed in the detector. CONT_TREND_FILTER is the nearest live equivalent and it is **CONT-only** (reversals exempt), whereas the spec applies LSMA-reclaim to **every** long. |
| **News blackout** (no fire within ±window of a release) | PARTIAL | A hardcoded calendar **exists**: `services/risk_validator/news_calendar.py` (FOMC/CPI/NFP 2026, ±10 min, L22-60) and S4 has a news stage (`woodies/stages/b6_news_window.py`). BUT it is **not wired into the S2 gateway chain** — the live gate list (PATTERN_ACCESS_MAP §0, 15 gates) has **no news gate**. So today an S2 reactive long CAN fire inside an FOMC/CPI/NFP window. The data is reusable; the wiring to S2 is missing. |
| **Multi-detector taxonomy** (12 detectors, tiers A-D) | MISSING (for reactive); EXISTS-elsewhere | S2 has 5 *families* (Reactive, Initiative, Double_BT, HnS, Flags) and S4 has 9 Woodies patterns — so the system **knows how to host many detectors**. But the spec's specific reversal/continuation/opening reactive-long taxonomy (spring/absorption/climax/engulfing/b-shape/1-2-3/double-bottom-div/hidden-div/pullback-flag/open-*) does **not** exist. The existing `Double_BT` ≈ spec `double_bottom_div` **without the CVD-divergence requirement**. |
| **Calibration discipline** (every config a fit target on ≥24h ES) | PARTIAL-PHILOSOPHY | The repo has the *discipline* (CLAUDE.md Pre-LIVE "data-first", flag/backtest gating, `config/*.yaml` with per-value provenance markers ✅/🔬/📜) and **most thresholds are already externalized to YAML** (stop_anchors, targets, daytype_playbook, s2_firing). BUT the calibration substrate the spec demands — **≥24h of ES RTH order-flow** — **does not exist** (system is MES-only; see §3). The thresholds today were fit on **MES** SHADOW data, not ES. |

### Detector-time data availability (a recurring blocker)

The spec's detectors need, **at the moment of detection**, inside the pure function: the bar's
`delta` + `cvd`, and the full `Levels` struct (dpoc/dvah/dval/ppoc/pvah/pval/ib_high/ib_low/vwap/
lsma/lsma_slope/naked_pocs). In the AS-BUILT system:

- `_detect_reactive` receives **only OHLCV dicts** (`bars_5m: List[Dict]` with o/h/l/c/v, L580).
  It has **no `delta`, no `cvd`, no levels** in its argument. Per-bar `delta` IS ingested into the
  DB (`bars.py` L755-766: `cum_value = pt.get("cum") or ... or pt.get("delta")`; dedicated table
  `v9_bars_cumulative_delta` carries both `delta` and `cumulative`, L770), and CVD/levels ARE
  available **elsewhere** (TPO via `_load_sierra_tpo()`, direction via `direction_context_live`),
  but they are **not threaded into the detector** — they are consulted post-fire (gateway gates,
  sizing, targets). Adopting the spec requires **plumbing delta+cvd+levels into the detection
  buffer**, which today they are not.

---

## 3 · CRITICAL — the ES-vs-MES question (spec non-negotiable #1)

**VERDICT: MEMS26 is MES-ONLY. It ingests NO ES order flow anywhere. The spec's #1 non-negotiable
is not satisfiable on the current feed — it is a hard blocker.**

Evidence (file:line):

1. **Every bar/order-flow table defaults symbol to "MES":**
   - `backend/v9/db/models/bars_5min.py:20` → `symbol = Column(String(20), ... default="MES")`
   - `backend/v9/db/models/bars_woodies.py:18`, `bars_5min_continuous.py:17`,
     `bars_footprint.py:14`, `bars_tick_reversal.py:14`, `tpo_bars.py:14` — all `default="MES"`.
2. **The Sierra DLL exports the MES contract:**
   - `sc_study/MES_AI_DataExport.cpp` — study `scsf_MES_AI_DataExport`; exports `"symbol":"MEMS26"`
     (the MES contract id) ~L421; `ContinuousChartNumber.SetInt(5)` ~L142 with the comment
     "Chart #5 = MESM26 5-Min 24h Globex".
3. **The cumulative-delta stream reads that MES chart:** `bridge/v9_streams/cvd_continuous_stream.py:1-3`
   ("cumulative_delta_continuous.json, chart #5, 24h Globex"); `cumulative_delta_stream.py:8-11`;
   `bars_5min_stream.py:1-3` ("5min.json"). All consume MES exports.
4. **Trading instrument is MES, confirmed in the Windows handoff:**
   `docs/handoff/WINDOWS_COWORK_HANDOFF.md:46` — "set every chart to MESU26 (September)".
5. **Zero ES references** anywhere in the repo: no `"ES"` symbol constant, env var, ES chart config,
   ES stream, or ES table. (Verified by a thorough Explore sweep of bridge/, sc_study/, backend/v9/db/models/, docs/.)

**So:** the `cumulative_delta` and footprint the system would feed to the spec's detectors are
**MES order flow** — exactly the thin leg the spec says is "too thin to threshold directly". To
honor non-negotiable #1 you would need a **new ES data path**: a second Sierra chart (ES front
month) → new DLL export → new bridge stream → new ES order-flow tables → detectors read ES delta/CVD
while execution stays on MES. None of that exists. This is the single largest build item.

> Nuance worth stating to Michael: the spec treats ES-flow as a hard prerequisite for *thresholding*.
> The system's own SHADOW evidence (your established finding) says **location/VAH-VAL is the dominant
> edge and volume/CVD are secondary**. That means the spec's *structural* half (regime + VP gate +
> structured stops/targets + R:R floor) can be adopted on the existing MES feed and capture most of
> the edge, **deferring** the ES-flow-dependent half (CVD-divergence magnitude, footprint imbalance
> ratios) until/unless an ES feed is built. The ES blocker blocks the *order-flow detectors*, not the
> *location architecture*.

---

## 4 · GAP ANALYSIS TABLE (KEEP / ADAPT / BUILD / BLOCKED)

Classification per spec capability, with the controlling file/flag.

| Spec capability | Verdict | Evidence + rationale |
|---|---|---|
| **Regime routing** (BALANCE/TREND_UP/opening dispatch) | **BUILD** | No `Regime` dispatcher in-detector. The inputs to derive it exist (7-type day-type `S1_NEW_CLASSIFIER`; `direction_context_live`; `opening_type_gate`), so it's a wiring/build, not blocked. `scan()`-style dispatcher is new code. |
| **VP-level entry gate** (multi-level proximity) | **ADAPT** | `daytype_position_gate.py` (POC) + the inert `reactive_location_gate.py` are the seed. ADAPT = extend from POC-only to the spec's `{VAL,PVAL,IB_low,PPOC,DPOC,VWAP,naked_pocs}` set AND move the check to **detection time**. TPO levels are live (`v9_tpo_sessions`, `_load_sierra_tpo`). |
| **CVD-divergence detection** | **BUILD (data: ADAPT)** | The divergence detector itself is new. The CVD data path exists (`v9_bars_5min.cumulative_delta` + dedicated `v9_bars_cumulative_delta.delta/cumulative`, `bars.py` L755-770) but holds **MES** flow and is **per-bar-delta-as-misnomer** in the main table (`SOURCE_OF_TRUTH.md`). True running CVD must be threaded into the detector. *Order-flow magnitude thresholds are BLOCKED on ES (§3); the divergence logic itself is buildable on MES as a first cut.* |
| **Footprint imbalance** (diagonal ≥3:1, stacked) | **BLOCKED** | S3 is `FOOTPRINT_DISABLED=1`/`S3_MUTE=1` (standing-OFF, Michael sign-off to re-enable). Memory: *S3 deferred until after LIVE*. Even re-enabled, diagonal/stacked imbalance ratios are **MES** flow → spec non-negotiable #1 (BLOCKED on ES). Bridge `imbalance_flags_stream`/`stacked_imbalances_stream` exist but unwired to S2. |
| **Structured VP-level stops** (struct−buffer, clamp) | **KEEP/ADAPT** | KEEP `STOP_ANCHORS_V2` + `stop_anchors.yaml` (Reactive: `support_zone` w4, −3T, cap 15pt) + `adaptive_stop.compute_stop_v2`. ADAPT = add the spec's two-sided `[4,12]` clamp if desired (today: one-sided `max_risk_points` cap + `floor_ticks:4`). |
| **Structured VP-level targets** (+ R:R floor) | **KEEP/ADAPT** | KEEP `DAYTYPE_TARGETS_STRUCTURAL` + `structural_targets.py` (IB/POC/VA per day-type — already ON, "98/104 sim trades resolved structural"). ADAPT = (a) key by reversal/continuation mode (spec) in addition to day-type; (b) **BUILD the missing whole-trade `min_rr_overall` gate** (no equivalent today). |
| **LSMA reclaim gate** | **ADAPT** | KEEP the LSMA feed (`v9_bars_5min_woodies.lsma_value`, `DIRECTION_LSMA_VETO`, `CONT_TREND_FILTER`). ADAPT from "direction/sustain" to the spec's per-bar "reclaim closed > LSMA & slope≥0" applied to **all** longs (today reversals are exempt from the LSMA filter). |
| **News blackout** | **ADAPT** | Data EXISTS (`news_calendar.py` FOMC/CPI/NFP ±10min; S4 `b6_news_window`). ADAPT = wire a news gate into the S2/gateway chain (PATTERN_ACCESS_MAP §0 has none today). Low effort, high safety value pre-LIVE. |
| **Multi-detector taxonomy** (12 detectors A-D) | **BUILD** | Host architecture EXISTS (5 S2 families, 9 S4 patterns prove the pattern-registry model). The specific reactive-long detectors are new code. `Double_BT` ≈ `double_bottom_div` minus CVD — ADAPT-able as one of the 12. |
| **Calibration discipline** (≥24h ES fit) | **BLOCKED (substrate) / KEEP (process)** | KEEP the YAML-externalization + flag/backtest gating process (already strong). BLOCKED on the **ES** substrate — there is no ES data to fit on (§3). Until ES exists, calibration can only happen on MES, which the spec explicitly forbids for the flow thresholds. |

**Summary of verdicts:** KEEP/ADAPT 5 (stops, targets, LSMA, news, VP-gate seed) · BUILD 3 (regime
dispatcher, CVD-divergence logic, taxonomy) · BLOCKED 2-3 (footprint imbalance, ES calibration
substrate, and the ES-flow magnitude thresholds inside CVD-divergence).

---

## 5 · How the current system would respond to adopting this spec **today**

### Directly reusable (drop-in or light-glue)
- **Structural stops:** `stop_anchors.yaml` + `compute_stop_v2` already produce
  "beyond-structural-extreme + cap" stops for Reactive (`support_zone`, w4). The spec's stop model
  is the same family.
- **Structural targets:** `DAYTYPE_TARGETS_STRUCTURAL` (ON) already replaces R-targets with
  IB/POC/VA. This is the spec's `_targets_above` philosophy, already in production-SHADOW.
- **Live levels feed:** TPO (`v9_tpo_sessions` / `_load_sierra_tpo`) gives POC/VAH/VAL/IB; LSMA
  (`v9_bars_5min_woodies`) is live; CVD (`v9_bars_5min` / dedicated table) is live. The *raw
  materials* for `Levels` mostly exist (gaps: **naked_pocs**, **dvah/dval intrabar developing
  value**, **lsma_slope** — none are first-class today).
- **News calendar:** reusable as-is for `ctx.news_blackout`.
- **Pattern-registry hosting:** the S2 detection chain (L1021-1052) already routes
  detect-fn → emit → gateway; a new detector slots into the same shape.

### What conflicts with current code/flags
- **`DAYTYPE_POSITION_GATE` is PATTERN-BLIND (FLAG_INDEX R2; PATTERN_ACCESS_MAP §0 #10).** It
  ignores its `pattern` arg and gates purely on day-type × price-vs-POC/IB. The spec's whole point
  is **pattern-specific** routing (a spring vs a hidden-div vs an open-rejection are gated
  differently). The spec's `scan()` and the live position gate **disagree on who decides
  direction**: the gate says "LONG only below POC on Normal"; the spec's continuation family wants
  LONG **above** rising value on TREND_UP. **If you feed spec longs through the unchanged gateway,
  the position gate will veto exactly the continuation/breakout longs the spec is designed to take.**
- **`DAYTYPE_PLAYBOOK` is inert** (returns FULL whenever POSITION_GATE=1 — root hole R1). The spec's
  per-detector × day-type SKIP/REDUCED matrix has no live home; you'd be building on top of a known
  dead surface.
- **`CONT_TREND_FILTER` (ON) vs the spec's reversal family.** The filter blocks **continuation**
  patterns that lack a K-bar sustained LSMA trend, and **exempts reversals**. The spec applies an
  LSMA-reclaim to **all** longs (incl. reversals). Reactive is hard-tagged **CONT**
  (PATTERN_ACCESS_MAP §1), so today every spec reversal-family long fired as "REACTIVE" would be
  subjected to CONT_TREND_FILTER — the opposite of the spec's intent. Mode-tagging must be fixed.
- **`DAYTYPE_TARGETS_STRUCTURAL` keys by day-type, not mode.** The spec computes targets by
  reversal/continuation mode. These can coexist but will fight over T1/T2/T3 unless reconciled
  (gateway override runs AFTER the detector sets targets — gateway wins, L362-391).
- **`S2_REQUIRE_COT_AMT` is standing-OFF**, `FOOTPRINT_DISABLED`/`S3_MUTE` ON. Any spec detector
  that *requires* footprint/COT/AMT (absorption, the imbalance config) would **silently no-op**
  today (`_footprint_state()` → `{}`), i.e. degrade to price-geometry-only — re-enabling is a
  trading-risk-surface change needing Michael sign-off (standing decision).
- **Entry-price model differs.** AS-BUILT reactive enters at **B4 close** (L1083). The spec enters
  at **the reclaim bar's close** for most detectors but **on a confirmed break** for `climax`
  (`entry = cl.h + tick`, L322) and uses level-relative entries for opening detectors. The emit
  path assumes close-entry; confirmed-break entries are new.

### What's missing (must be built before the spec can run as designed)
1. **ES order-flow feed** (the §3 blocker) — for the flow-thresholded detectors + the spec's
   calibration mandate.
2. **`delta` + running `cvd` + full `Levels` threaded into the detection buffer** — today the
   detector sees OHLCV only.
3. **`naked_pocs`, developing `dvah/dval`, `lsma_slope`** as first-class level fields.
4. **A `Regime` (BALANCE/TREND_UP) classifier** distinct from the 7-type day-type, OR a mapping
   from day-type → regime.
5. **CVD-divergence, delta-flip, and the 12 structural detectors** themselves.
6. **A whole-trade `min_rr_overall` gate** (no equivalent today).
7. **A news gate wired into S2.**
8. **A pattern-aware position gate** (or making the spec's `scan()` the authority and demoting the
   pattern-blind gate to a sanity backstop).

### Where the spec ALIGNS with the empirical findings (independent validation)
This is the strongest reason to take the spec seriously, and it should be stated plainly to Michael:

- **The spec's #1 gate is LOCATION (VP-level proximity).** Your SHADOW forensic finding is that
  **location/value-area is the dominant edge** (SHORT inside value & LONG above VAH lose; the
  mirror wins) and that **volume threshold and CVD are secondary**. The spec independently
  reaches the same conclusion: `passes_entry_gate` makes a qualifying VP level a **hard
  precondition** for *every* detector, and routes the *direction* by regime/value. The spec is, in
  effect, a principled generalization of "only take reactives at the right location" — which is
  exactly what the −$3,198 / 40.7%-T1 SHADOW result says is missing from the current rigid template.
- **The spec's CVD-divergence is the right *secondary* confirmation**, matching your finding that
  CVD is a real-but-secondary signal currently used only for gateway direction, never for the
  reactive entry quality. The spec promotes it to a *swing-low divergence* check — a higher-value
  use than the binary direction slope.
- **Caveat (your data, honestly):** the spec asserts ES-flow thresholds are non-negotiable, but
  your evidence is that on MES the *location* gate carries the edge and flow is secondary. So the
  spec's structural half is **empirically validated**; its ES-flow half is **asserted, not yet
  validated on your data** — and is the part blocked by the MES-only feed.

### Realistic smallest-first migration path
Ordered by value/effort, each a separate flag-gated SHADOW step (per CLAUDE.md "one thread at a
time", smallest-correct-change, four-UAT-axes):

1. **Fix the mode tag + make the location gate pattern-aware (no new detectors).** Stop treating
   the existing REACTIVE as monolithic-CONT; let a reactive long that is a *reversal-at-VAL* be
   gated as a reversal. This is the cheapest way to test the spec's central claim with code you
   already have, and directly attacks the −$3,198 SHADOW bleed (SHORT-inside-value / LONG-above-VAH
   losers). *Lever, not a rewrite.*
2. **Wire a news gate into S2** (reuse `news_calendar.py`). Pure safety, near-zero risk, pre-LIVE win.
3. **Thread `delta` + `cvd` + `Levels` (incl. lsma_slope) into the detection buffer.** Enables
   everything downstream; no behavior change by itself (observability-only first).
4. **Build Tier-A reversal detectors on the MES feed as a SHADOW trial**, starting with
   `double_bottom_div` (adapt the existing `Double_BT` + add the CVD-HL requirement) and
   `one_two_three_low` — clean structure, hard invalidation, location-gated. Backtest-gate each
   (the system's standard: flag default-OFF, counterfactual P&L, Michael sign-off).
5. **Add the whole-trade `min_rr_overall` floor** to the target resolver.
6. **(Strategic stop → Michael) Decide on ES.** Building the ES order-flow feed is the gate to the
   flow-thresholded detectors (absorption/imbalance) and to honoring the spec's calibration mandate.
   Until then, run the structural half on MES and **explicitly DEFER** the ES-flow half — do not let
   the missing ES feed block the location/structure gains that your own data says are the real edge.

---

## Appendix — primary evidence index (file:line)

- Spec: `outputs/reactive_detector_lib_spec.py` (L10-17 non-negotiables; L160-170 gate; L171-195
  stops/targets; L213-453 detectors; L464-484 `scan`).
- AS-BUILT reactive: `backend/v9/systems/five_min/five_min_system.py` L580-720 (`_detect_reactive`),
  L722-819 (`_detect_initiative`), L1078-1461 (fire → stop → targets → emit), L865-891 (`_compute_location_vs_poc`).
- Gateway gate chain: `backend/v9/gateway/trading_gateway.py` L204-228 (opening), L237-254 (playbook,
  inert), L259-314 (position gate, pattern-blind), L321-356 (direction + CONT_TREND_FILTER), L362-391
  (structural targets).
- Gates/flags: `docs/FLAG_INDEX.md` (DAYTYPE_POSITION_GATE R2 pattern-blind; DAYTYPE_PLAYBOOK inert R1;
  CONT_TREND_FILTER; FOOTPRINT_DISABLED/S3_MUTE; S2_REQUIRE_COT_AMT off; DAYTYPE_TARGETS_STRUCTURAL on).
- Position/location gates: `backend/v9/systems/daytype_position_gate.py` L88-205;
  `backend/v9/systems/reactive_location_gate.py` (inert).
- LSMA/direction: `backend/v9/systems/direction_context_live.py` L17-148.
- Targets/stops config: `config/structural_targets.py` (`structural_targets.py` L45-114),
  `config/targets.yaml`, `config/stop_anchors.yaml` L77-104.
- CVD ingest: `backend/v9/api/v9/bars.py` L722-786 (per-bar delta → `cumulative_delta`; dedicated
  `v9_bars_cumulative_delta` carries delta+cumulative); `docs/SOURCE_OF_TRUTH.md` (cumulative_delta misnomer).
- ES-vs-MES: `backend/v9/db/models/bars_5min.py:20` (+ sibling models), `sc_study/MES_AI_DataExport.cpp`
  (~L142 chart#5 MESM26, ~L421 symbol MEMS26), `bridge/v9_streams/cvd_continuous_stream.py:1-3`,
  `docs/handoff/WINDOWS_COWORK_HANDOFF.md:46`. **No ES anywhere.**
- News: `backend/v9/services/risk_validator/news_calendar.py` L22-60; `backend/v9/systems/woodies/stages/b6_news_window.py`.
