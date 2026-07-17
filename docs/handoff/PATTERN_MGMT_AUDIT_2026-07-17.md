# PATTERN × DAY-TYPE MANAGEMENT / GATING AUDIT — 2026-07-17

**Author:** cowork-dev (Cowork MacBook) · **Type:** READ-ONLY code audit · **No code changed.**
**Trigger:** 3 live bugs of the "silently blocks a valid trade per day-type" class were found + fixed today
(#1 Woodies GRAY veto lag → `TREND_CCI_DIRECT_V1`; #2 auth read stale engine day-type ignoring override;
#3 S2 `calculate_size` inverted location + hard COT/AMT → `S2_REACTIVE_EDGE_FIX_V1`). Michael: *"where are
the OTHER such mistakes?"* This is the map for Michael's ruling — **nothing here is fixed.**

> ⚠ **Every proposed fix is a trading-risk-surface change → strategic stop + Michael sign-off. All proposed
> flags are default-OFF.** Do not enable/edit without a ruling.

---

## 0. Live gating topology (verified from `.env` 2026-07-17 20:03 + code)

This determines which code is LIVE vs inert. **Read this first — several "gates" are dead code today.**

**Money-live:** `MEMS26_MODE=live`, `LIVE_EXECUTION_V1=1`, `LIVE_TRADING_ARMED=1`.
**Today's day-type:** `DAY_TYPE_MANUAL_OVERRIDE=2026-07-17:Normal` → live day-type = **Normal** (override wins over the machine; auto-expires at ET roll).

**The LIVE per-pattern day-type gates (in gateway `_route_setup_inner` order):**
1. `daytype_playbook.decide()` — `DAYTYPE_PLAYBOOK=1` — the YAML SKIP/REDUCED matrix + `require_with_trend`. (trading_gateway.py:622)
2. `location_gate.decide_location()` — `DAYTYPE_LOCATION_GATE=1` — REV fades only at the correct value edge on rotation days; CONT-with-expansion on Variation. (trading_gateway.py:703)
3. `direction_context` block — `DIRECTION_CONTEXT=1` — contains `cont_trend_filter` (`CONT_TREND_FILTER=1`) + the LSMA-lead veto + the `NEUTRAL_RESPONSIVE_V1=1` REV exemption. (trading_gateway.py:763)

All three resolve day-type via `extract_g1_entry_context()` → `get_live_day_type()` (**override-aware** — good).

**INERT today (do NOT assume these protect a trade):**
- `DAYTYPE_POSITION_GATE=0` → `daytype_position_gate.decide()` early-returns `"gate OFF"`. Therefore its entire
  location engine (`_decide_normal/_variation/_trend`), **`DAYTYPE_PATTERN_AWARE_V1` family gate (CONT/REV)**,
  and **`NONTREND_DISABLE_ALL`** (only read inside that gate, line 127) are all **DEAD CODE**. Nontrend is still
  blocked, but only via the playbook `Nontrend: SKIP` cells — not the flag.
- `REACTIVE_LOCATION_GATE=0`, `TREND_DIRECTION_GATE=0`, `DAY_DIRECTION_DOCTRINE_V1`=unset, `S2_REQUIRE_COT_AMT`=unset(OFF),
  `NONCONVICTION_ACTIVE_V1`=unset(OFF), `DAYTYPE_HONEST_PRELOCK_V1`=OFF, `LSMA_FLAT_GATE_V1=0`.
- **`docs/FLAG_INDEX.md` is drifted**: its semantics column claims `DAYTYPE_POSITION_GATE` is "ON" while the
  generated state + `.env` say `0`. Trust `.env`.

---

## 1. CONFIRMED findings — RANKED (most likely to block/mis-manage a live trade first)

| # | Pattern(s) | Day-type(s) | File:line | What's wrong | Doctrine ref | Proposed fix (flag, default-OFF) | Confidence |
|---|---|---|---|---|---|---|---|
| **A1** | REACTIVE / VEGAS / GHOST / FAMIR / HTLB / DBDT (all REV) | **Normal** (= today) | `gateway/trading_gateway.py:811` | The `NEUTRAL_RESPONSIVE_V1` REV-fade exemption is `str(_nr_dt).startswith(("Neutral","Variation","Normal_Variation"))` — it **omits bare `"Normal"`**. So on a Normal day a REV fade that opposes `direction_context.dir` (LSMA-lead) is **blocked** (`blocked_by=direction_context`). But a fade at VAH is *by definition* against the up-push into the edge → LSMA `dir=UP` → REACTIVE_SHORT (DOWN) blocked. `location_gate._ROTATION_PREFIXES` (line 28) AND the RR-relief (line 1438) BOTH include `"Normal"` — only this exemption forgot it. **Same class as bug #3, LIVE today.** | S1_TRADE_MANAGEMENT_3CONTRACTS.md (Normal = fade IB edges); RESEARCH Part E line 19 "Fade בקצוות ה-IB (REV)" | Add `"Normal"` to the tuple (behind e.g. `NEUTRAL_RESPONSIVE_NORMAL_V1`, or just extend since the sibling gates already include it). | **CONFIRMED** logic; impact conditional on `dir` being directional (usual on a push to an edge) |
| **A2** | ALL S2 (REACTIVE + INITIATIVE + chart patterns) | any (stale=Nontrend) | `five_min/five_min_system.py:1139` | `if self.current_day_type == "Nontrend": return` — S2 **skips all detection**. `self.current_day_type` tracks the OLD engine's event stream (line 426), **not** `get_live_day_type()`/override. If the stream transiently says `Nontrend` while the live/override day-type is tradeable, **S2 goes fully blind (no fire, silent)**. (07-09 memory: exactly this — REACTIVE/ZLR SKIP'd on a transient Nontrend during a +50pt drive.) | Bug #2 class (stale source ignores override) | Resolve via `get_live_day_type()` first, fall back to `current_day_type` (`S2_NONTREND_SKIP_OVERRIDE_AWARE_V1`). | **CONFIRMED** stale source; impact when stream=Nontrend |
| **A3** | ALL S4 fades on a rotation stop (REACTIVE-equivalent) | **Normal** (= today), (Trend not affected) | `stop_anchors/stop_resolver.py:75` | Rotation stop-floor (`0.8×ATR`) is `_dt.startswith(("Variation","Normal_Variation","Neutral"))` — **omits bare `"Normal"`**. On a Normal day the floor stays `0.5×ATR` → a fade gets a stop *inside the noise* (the #372-class premature stop-out the fix was meant to prevent). Doctrine, `location_gate`, and RR-relief all treat Normal as rotation. | S1 doc + RESEARCH line 19 (Normal = wide IB, rotation within); comment lines 68-72 | Add `"Normal"` to the tuple (`STOP_FLOOR_ROTATION_NORMAL_V1`). | **CONFIRMED** inconsistency; **SUSPECTED** intent (comment scoped to Variation/Neutral — needs ruling) |
| **A4** | HnS / Double / Flag (S2 chart patterns) | any (stale None / Nontrend) | `five_min/five_min_system.py:1170,1180,1192` | `chart_patterns_allowed(self.current_day_type, …)` gates chart-pattern **detection** on the stale `current_day_type`. `None`→silently skipped (explicit warning at 1174); wrong stale value→wrong gate. `S2_CHART_ALL_DAYTYPES=1` bypasses the allow-list but `chart_patterns_allowed` still returns **False on None/UNKNOWN/Nontrend** (five_min_system.py:104). | Bug #2 class | Feed `get_live_day_type()` into the chart-pattern gate. | **CONFIRMED** stale source |
| **A5** | INITIATIVE_LONG / INITIATIVE_SHORT | Normal / Neutral_* | `stop_anchors/sizing.py:42-46` + `five_min/five_min_system.py:1348-1373` | S2 passes family key `"OFA_Initiative"`. `_auth_cell` tries `("OFA_Initiative",dt)` then `("OFA_INITIATIVE_LONG",dt)` — the auth table key is `"INITIATIVE_LONG"` → **both miss** → "using max" → verdict **FULL**. So the LOCKED `INITIATIVE×Normal=SKIP` / `×Neutral=SKIP` verdicts are **silently bypassed** in V2 sizing (an OVER-fire). Playbook still SKIPs Neutral, but on **Normal** playbook says REDUCED (allows) → INITIATIVE fires on a Normal fade day at full size (`FIXED_CONTRACTS_4=1`→4). Note `_auth_cell` docstring already fixed the *Reactive* variant of this exact bug but not Initiative. | auth_table_v1.py (LOCKED 2026-05-25): INITIATIVE×Normal/Neutral = SKIP | Add an `"OFA_Initiative"→"INITIATIVE"` alias in `_auth_cell` so the FAMILY_DIRECTION key resolves (`S2_INITIATIVE_AUTH_KEY_FIX_V1`). | **CONFIRMED** (over-fire, not a block) |
| **A6** | S4: ZLR / TLB / TT / GB100 / HTLB / VEGAS / GHOST / FAMIR | any with override≠machine | `woodies/woodies_system.py:640-669` | `_s4_day_type` = `current_state["day_type"]` → **`app.state.day_type_machine.day_type` (RAW)** → DB → `"Normal"`. **Never calls `get_live_day_type()`**, so `DAY_TYPE_MANUAL_OVERRIDE` (and anti-flap, honest-prelock) are **ignored for S4**. Bug #2's exact class, unfixed on S4 (D-0717-A patched only S2). *Not a hard block* — S4 patterns are intentionally absent from the auth table (sizing.py:38-40), so no auth-SKIP. It **mis-computes the `RUNNER_TARGETS_V1` T2 struct level** (woodies_system.py:930 → `compute_targets_for_day_type(_s4_day_type)`) → wrong runner target. | Bug #2 class; CLAUDE.md Codebase-Index (real path) | Route S4 day-type through `get_live_day_type()` first (`S4_DAYTYPE_OVERRIDE_AWARE_V1`). | **CONFIRMED** (management divergence) |
| **A7** | BULL_FLAG / BEAR_FLAG (FLAGS) | any with override≠machine | `five_min/five_min_system.py:1551` | Flag-T2 target style selects on `dt = self.current_day_type` (stale), while the SAME fire uses override-aware `_emit_day_type` for auth/sizing/emit (lines 1375, 1434, 1602). Inconsistent within one fire → wrong T2 + wrong `trail_active` (e.g. override=Normal→POC T2, but stale=Variation→full_pole+trail). | Bug #2 class | Use `_emit_day_type` instead of `self.current_day_type` at 1551 (`FLAG_T2_OVERRIDE_AWARE_V1`). | **CONFIRMED** (management) |

---

## 2. SUSPECTED / needs-ruling / lower-severity

| # | Area | File:line | Concern | Confidence / note |
|---|---|---|---|---|
| **S1** | Contracts per day-type | `config/targets.yaml:42,55,68,81` (Variation=2, Normal=1, Neutral_*=1) | Contradicts the 3-contract doctrine AND the playbook `daytype_style` (Normal=3, Variation=3, NeuC=2, NeuE=3) AND `structural_targets.py` (all 3). BUT `sizing_contracts` does **not** appear to drive the live contract count (`FIXED_CONTRACTS_4=1` forces 4; `compute_v2_sizing`/`calculate_size` own sizing; the OFA target path reads only prices). Likely cosmetic/dead. | **SUSPECTED** — verify no consumer of `sizing_contracts`/`targets.contracts` before acting |
| **S2** | Two target authorities | `structural_targets.py` (C2=VAL/opposite-edge, `DAYTYPE_TARGETS_STRUCTURAL=1`) vs `day_type_targets.py`/`targets.yaml` (t2=POC/extreme, R-based) | Both are live. Gateway applies structural targets (block ~1088-1112); S2 emit path (five_min_system.py:1600) computes R-based `compute_targets_for_day_type`. Which wins depends on gateway-vs-emit ordering. Potential double-authority / overwrite. | **SUSPECTED** — needs a runtime trace of which T1/T2/T3 actually reaches the bracket |
| **S3** | S2 CVD dependency | `five_min/five_min_system.py:740-743, 791-794` (`S2_CVD_DETECTION_V1=1`) | Fail-OPEN on empty CVD (`_compute_setup_cvd` returns None when <2 rows → check skipped) — good. BUT if a **thin/stale** stream returns ≥2 rows without absorption, REACTIVE is rejected (`return (None,0,{})`, silent, falls to INITIATIVE). Given "today's empty-CVD reality" this is a re-introduced order-flow dependency (separate from the disabled COT/AMT). | **SUSPECTED / LOW** — doctrine-consistent when CVD real (S1 doc: "בלי CVD divergence — אל תיכנס"), but at odds with S2⟂S3 when CVD is partial |
| **S4** | Playbook vs auth-table conflict | `daytype_playbook.yaml` vs `auth_table_v1.py` | Two pattern×day-type matrices with different verdicts govern the same fire (playbook=gateway veto, auth=S2 sizing). E.g. INITIATIVE×Normal: playbook REDUCED vs auth SKIP. They mostly agree; where they don't, behavior depends on which layer + A5's bypass. | **SUSPECTED** — reconcile the two matrices to one source of truth |

---

## 3. Per-axis coverage notes

- **Axis A (location/side inversions):** The 3 location gates are directionally **correct** —
  `reactive_location_gate.py` (LONG≤POC / SHORT≥POC), `location_gate.py` (LONG@VAL-side / SHORT@VAH-side on
  rotation days; CONT-with-expansion on Variation), and `daytype_position_gate._decide_normal/_variation/_trend`.
  The S4 pattern detectors (`zlr/tlb/tt/gb100/htlb/vegas/ghost/famir`) are **CCI-geometry** based — no POC/VAH
  inversion. `structural_targets.py` C1/C2/C3 per day-type match the doctrine exactly (Normal SHORT: IB-center→VAL→IBL,
  etc.). **The only live "location" defect is A1** — a rotation-day *omission*, not a per-pattern inversion.
  Caveat: `reactive_location_gate` & `daytype_position_gate` are **inert** (flags off); the live location logic is
  `location_gate.py` (correct).
- **Axis B (targets/stops/contracts/runner):** Playbook YAML cells are **faithful** to RESEARCH Part E (ZLR `E E D E S S S`,
  VEGAS/GHOST/FAMIR `S S E D E E S`) — no cell bug. Target *levels* are correct in `structural_targets.py`.
  Findings: **A3** (Normal stop-floor omission), **S1** (contract-count drift, likely inert), **S2** (double target authority).
- **Axis C (stale-source / override):** The gateway gates (playbook, location, direction-context, day-direction, structural
  targets, RR) are **all override-aware** via `extract_g1_entry_context→get_live_day_type`. The **non-override-aware**
  decision sites are: **A2** (five_min:1139), **A4** (five_min:1170-1192), **A6** (woodies:640-669), **A7** (five_min:1551).
  `get_live_day_type()` itself is correct (override checked *before* the `DAYTYPE_GATE_LIVE_V1` flag, so override always wins).
- **Axis D (silent rejects before `route_setup`):** `calculate_size` (bug #3) is fixed. S2 detection silent rejects:
  CVD (S3, fail-open), `S2_B4_VOL_V1` (OFF), the Nontrend skip (A2). S4: `compute_v2_sizing` returns None only on an auth
  SKIP — which **cannot happen for S4** (not in auth table) and is **bypassed for INITIATIVE** (A5); the monotonic-target
  guard (`_build_result` / A7 validator) reorders rather than rejects. `A7` universal checks (news/cooldown/daily-loss/
  stop-range/bridge/EOD) are legitimate, not day-type. **No new silent day-type reject beyond A2/A4.**
- **Axis E (COT/AMT/footprint/CVD hard-deps):** Detection COT/AMT is **bypassed** (`S2_REQUIRE_COT_AMT` unset →
  `cot_above_amt=True` always; five_min:694/757/871/906). `belly`/`belly_ratio` are **graceful** (`None` passes; 708/762).
  `calculate_size` flow is a booster not a gate (fixed). The only residual order-flow dependency is **S3** (`S2_CVD_DETECTION_V1`,
  fail-open). No un-bypassed hard COT/AMT block remains.

---

## 4. Could NOT be determined from code alone (needs live DB / runtime)

1. **Does A2/A4 actually bite right now?** Depends on whether the OLD engine's classification stream ever pushes
   `Nontrend`/`None` into `self.current_day_type` while the override says Normal. Needs a live read of the S2 system
   state + the `system.day_type.classification` event stream.
2. **A1 live impact** depends on `direction_context.dir` being UP/DOWN (not NEUTRAL) at the moment of a Normal-day fade —
   needs `direction_context_live.current()` trace at a fade attempt.
3. **S1 (contract count):** whether `targets.contracts` / `sizing_contracts` is read anywhere for the real bracket size —
   grep found no consumer, but a runtime confirm (fire a setup, inspect the routed `contracts`) is the honest check.
4. **S2 (double target authority):** which of structural vs R-based T1/T2/T3 actually reaches the Sierra bracket — needs a
   live fire trace through the gateway target pipeline.
5. **Which day-type the machine holds vs the override** at any instant (to quantify A6/A7 divergence) — needs
   `app.state.day_type_machine.day_type` vs `DAY_TYPE_MANUAL_OVERRIDE` at fire time.

---

## 5. One-line ruling asks for Michael

- **A1 (top, live):** Should the `direction_context` REV-fade exemption include **Normal** (like `location_gate` + RR-relief already do)? — expected YES.
- **A3:** Should the **0.8×ATR rotation stop-floor apply to Normal**? — doctrine says Normal is a rotation day (expected YES); the stop comment scoped it to Variation/Neutral, so confirm.
- **A2/A4/A6/A7:** Approve making all four stale `self.current_day_type`/machine-direct reads **override-aware** (`get_live_day_type` first)?
- **A5:** Approve the `OFA_Initiative→INITIATIVE` auth-key alias so the LOCKED INITIATIVE SKIP verdicts stop being bypassed? (this *reduces* firing — a risk-surface change)

*All fixes default-OFF, one flag each, add a regression test per fix (Pre-LIVE Discipline).*
