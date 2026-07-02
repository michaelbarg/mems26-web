# Pattern Fire-Readiness Audit — 2026-06-30

**Scope:** Can EVERY trading pattern fire today? For each S2 (five-min) + S4 (Woodies)
pattern, verify (1) detection function exists AND is called in the live pipeline, and
(2) it receives all required inputs FRESH, and (3) flag/gate blockers. READ-ONLY audit —
no trading code touched.

**Method:** Index-first per CLAUDE.md — read `docs/spec_authority/PATTERN_ACCESS_MAP.md`,
`docs/FLAG_INDEX.md`, `docs/SOURCE_OF_TRUTH.md`, then the actual detector code + live DB.

**DB evidence (psql `postgresql://localhost/mems26`, captured 06-30 ~06:52 CT):**

| source | last bar (CT) | rows | verdict |
|---|---|---|---|
| `v9_bars_5min_woodies` (feeds S4 `woodies_5min` channel) | **06-30 06:50** | 3947 | ✅ LIVE (streaming pre-market, 2 min old) |
| `v9_bars_5min` (feeds S2 `5min` channel + CVD) | **06-29 10:00** | 2356 | 🔴 FROZE mid-RTH 06-29; RTH-only so empty pre-market |

Prior-day `v9_bars_5min` closes were 15:55 CT (normal). 06-29 it produced only 33 bars and
**stopped at 10:00 CT mid-session** (also a gap 09:20→09:45). This is the SoT-flagged stall.

`v9_trades` historical fires by pattern: TLB 50 · ZLR 38 · REACTIVE_SHORT 34 · HFE 27 ·
REACTIVE_LONG 20 · INITIATIVE_SHORT 18 · FAMIR 5 · INITIATIVE_LONG 5 · BULL_FLAG_LONG 3 ·
VEGAS 3 · GHOST 3 · HTLB 3 · GB100 3 · BEAR_FLAG_SHORT 2 · **INVERSE_HNS 0 · HNS_TOP 0 ·
DOUBLE_BOTTOM_EE 0 · DOUBLE_TOP_AA 0 · TT 0**.

---

## Per-pattern readiness table

Legend: ✅ can fire today · ⚠️ wired+fed but realistically won't fire (too-strict detection) ·
❌ cannot fire (wiring/data/flag blocker).

### S2 — Five-Min (subscribes BarRouter channel `"5min"` → `v9_bars_5min`)

| pattern | wired? (detection called live) | required inputs available + FRESH? | blocker (if any) | CAN FIRE TODAY |
|---|---|---|---|---|
| REACTIVE_LONG | ✅ `five_min_system.py:1021` `_detect_reactive` | needs OHLC `5min`; CVD/COT/AMT **not required** (S2_REQUIRE_COT_AMT OFF). **`5min` feed froze 06-29 10:00** | feed-dependent | ⚠️/❌ feed |
| REACTIVE_SHORT | ✅ same dispatch | same | feed-dependent | ⚠️/❌ feed |
| INITIATIVE_LONG | ✅ `:1023` `_detect_initiative` (runs only if Reactive None) | OHLC `5min` only | feed-dependent | ⚠️/❌ feed |
| INITIATIVE_SHORT | ✅ same | same | feed-dependent | ⚠️/❌ feed |
| INVERSE_HNS_LONG | ✅ `:1038` `detect_inverse_hns` (Pkg 5a) | OHLC `5min`; day-type ≠ None/Nontrend (gate passes via `S2_CHART_ALL_DAYTYPES=1`) | **detection too strict** (5% shoulder symmetry) + feed | ❌ never fired |
| HNS_TOP_SHORT | ✅ `:1040` `detect_hns_top` | same | **detection too strict** + feed | ❌ never fired |
| DOUBLE_BOTTOM_EE_LONG | ✅ `:1043` `detect_double_bottom_ee` | OHLC `5min` + ATR | **Eve width ≥3 bars too strict** + feed | ❌ never fired |
| DOUBLE_TOP_AA_SHORT | ✅ `:1045` `detect_double_top_aa` | same | **Adam width ≤2 + sym too strict** + feed | ❌ never fired |
| BULL_FLAG_LONG | ✅ `:1050` `detect_bull_flag` (Pkg 5c) | OHLC `5min` | feed-dependent | ⚠️/❌ feed |
| BEAR_FLAG_SHORT | ✅ `:1052` `detect_bear_flag` | OHLC `5min` | feed-dependent | ⚠️/❌ feed |

All S2 detectors are correctly wired and route to the gateway (`route_setup(..., 2)`,
`five_min_system.py:1454`). **The system-wide S2 blocker today is the `5min` feed**, not the
detectors (the four chart patterns above have additional detector-strictness blockers).

### S4 — Woodies (subscribes BarRouter channel `"woodies_5min"` → `v9_bars_5min_woodies`, LIVE)

All 9 are wired in `pattern_engine.py:_DETECTORS` (`:20-30`); all read CCI-14/CCI-6/SWI/CZI/
EMA-34/LSMA/trend_state from the **Sierra DLL columns** in `v9_bars_5min_woodies` (present +
fresh). Route to gateway via `route_setup(..., 4)` (`woodies_system.py:935`).

| pattern | wired? | required inputs available + FRESH? | blocker (if any) | CAN FIRE TODAY |
|---|---|---|---|---|
| ZLR | ✅ `zlr.detect` | ✅ CCI/SWI/CZI/EMA fresh | ZLR_SPEC_V2 gate ON (quality), HTLB-dir-gate, gateway gates | ✅ |
| TLB | ✅ `tlb.detect` | ✅ fresh | TLB_SPEC_V2 ON (needs ±200 SWI extreme + CONT partner) — selective but fires | ✅ |
| TT | ✅ `tt.detect` | ✅ CCI-14/CCI-6/trend fresh | **detection too strict** (3-bar TCCI touch+bounce+was-above) | ⚠️ never fired |
| GB100 | ✅ `gb100.detect` | ✅ fresh | gateway gates only | ✅ |
| VEGAS | ✅ `vegas.detect` | ✅ fresh | VEGAS_SPEC_V2 ON (cup-and-handle, shallow-handle gate) — selective | ✅ |
| GHOST | ✅ `ghost.detect` | ✅ fresh | gateway gates only | ✅ |
| FAMIR | ✅ `famir.detect` | ✅ fresh | gateway gates only | ✅ |
| HTLB | ✅ `htlb.detect` | ✅ fresh | also sets the direction bias for all S4 | ✅ |
| HFE | ✅ `hfe.detect` (called) | ✅ fresh | **`HFE_DISABLED=1`** — stripped post-detection | ❌ flag-disabled (intentional) |

---

## Patterns that CANNOT fire today — precise reasons

### A. Whole-system S2 feed outage (affects ALL 10 S2 patterns)
**Reason:** S2 (`FiveMinSystem`) subscribes to BarRouter channel **`"5min"`**
(`five_min_system.py:896`), which is fed by the `POST /api/v9/bars/5min` handler. That handler
**persists to `v9_bars_5min` and calls `_route_bar("5min", …)` in the same code path**
(`backend/v9/api/v9/bars.py:418-438`) — so a missing DB row means S2 received no bar. The table
**froze at 06-29 10:00 CT mid-RTH** (last row; only 33 bars that day vs 90-126 on prior days, plus
a 09:20→09:45 gap). The handler is **RTH-only** (`bars.py:395` `if not _is_within_rth(ts): continue`),
so its emptiness *right now* (06:52 pre-market) is expected — but it has produced **zero rows since
06-29 10:00**, i.e. the `5min` bridge stream stalled mid-session and there is no evidence it
recovered. **S4's `woodies_5min` stream is provably live** (06:50 CT), so this is a `5min`-stream
problem, not a backend-down problem.
**Verdict:** S2 readiness is **BROKEN as of last session / UNVERIFIABLE until today's RTH open
(08:30 CT)**. Decisive test: confirm `v9_bars_5min` produces a row at/after 08:30 CT today. If it
stays frozen, every S2 pattern (Reactive/Initiative/HnS/Double/Flags) cannot fire.
**Where:** `backend/v9/systems/five_min/five_min_system.py:896`; `backend/v9/api/v9/bars.py:395,418-438`;
SoT note `docs/SOURCE_OF_TRUTH.md` line 15.

### B. HFE — intentionally disabled (flag)
**Reason:** `HFE_DISABLED=1`. HFE is stripped after detection in BOTH paths:
`woodies_system.py:357-360` (Python detector list) and the DLL-flag fallback is guarded by
`not _HFE_DISABLED` (`woodies_system.py:430`). This is a **deliberate standing decision** (Michael
2026-06-24: "not my pattern"; was the single biggest loser, 27 fires −$2,987). Not a bug.
**Where:** `backend/env_loader.py:73`, `backend/v9/systems/woodies/woodies_system.py:357,430`,
`docs/FLAG_INDEX.md` (HFE_DISABLED ✅ ON).

### C. INVERSE_HNS_LONG + HNS_TOP_SHORT — detection too strict (0 fires ever)
**Reason:** NOT a wiring or day-type-gate blocker. With `S2_CHART_ALL_DAYTYPES=1` (ON),
`chart_patterns_allowed()` returns True for any day-type except None/UNKNOWN/Nontrend
(`five_min_system.py:104-109`), so HnS is reachable on Normal/Variation/Trend/Neutral days. The
killer is the geometry gate `_shoulders_symmetric`: `abs(left−right)/head_to_avg ≤ SHOULDER_SYM_PCT`
with **`SHOULDER_SYM_PCT = 0.05`** (`head_shoulders.py:29,93-103`) — the two shoulders must sit within
5% of the head-to-shoulder height of *each other*, on raw 5-min MES swing pivots
(`PIVOT_LOOKBACK=2`). Combined with `HEAD_MIN_EXT_TICKS=2` and the neckline-break trigger, no real
session produces a triplet that passes. Confirmed by 0 rows in `v9_trades`.
**Where:** `backend/v9/systems/five_min/patterns/head_shoulders.py:26-31,93-103,148-189`.

### D. DOUBLE_BOTTOM_EE_LONG + DOUBLE_TOP_AA_SHORT — detection too strict (0 fires ever)
**Reason:** Also not the day-type gate. Note the symmetry test `_troughs_symmetric` uses
`abs(t1−t2)/lower ≤ 0.03` where `lower` is the **absolute price** (~7500) — that is ~225 pts of
slack, i.e. *permissive*, so symmetry is NOT the blocker. The real blockers are the **variant width
constraints**: Double Bottom (Eve&Eve) requires BOTH troughs to be ≥3 bars wide at the same low
within ~0.75×ATR (`TROUGH_MIN_WIDTH_BARS=3`, `double_bt.py:34,96-111,192`); Double Top (Adam&Adam)
requires BOTH peaks ≤2 bars wide (`PEAK_MAX_WIDTH_BARS=2`, `:35,114-129,258`). On 5-min MES, a swing
pivot rarely has 3 consecutive bars pinned within ~0.75×ATR of the exact low, and the breakout-close
trigger must also fire on the same bar. Result: 0 rows in `v9_trades`.
**Where:** `backend/v9/systems/five_min/patterns/double_bt.py:33-37,96-137,167-228,233-295`.

### E. TT (Turbo Trend, S4) — detection too strict (0 fires ever)
**Reason:** Wired (`pattern_engine.py:23`) and fed fresh CCI data, but the trigger requires a precise
3-bar CCI-6/CCI-14 sequence on a colored trend: `was_above` (CCI-6 >10 above CCI-14 two bars ago) →
`touched` (CCI-6 came within +5 of CCI-14 one bar ago) → `bounced` (CCI-6 now >5 above CCI-14 AND
rising), with `trend_state==BLUE & cci_14>0` (mirror for SHORT) — `tt.py:80-85,140-145`. Plus AP8
(CCI-flat) and AP7 (TT divergence gap) anti-pattern vetoes. This conjunction essentially never lines
up on one bar. The access map already flags TT "0 ירי אי-פעם". Pattern is healthy data-wise; it is a
calibration/strictness issue, not a fire-readiness defect.
**Where:** `backend/v9/systems/woodies/patterns/tt.py:52-145`.

---

## Cross-cutting gate notes (apply to whatever does fire)

- **NONTREND_DISABLE_ALL=1** blocks ALL S2+S4 fires on Nontrend days
  (`daytype_position_gate.py:117`). On a Nontrend day, *nothing* fires — expected, by design.
- **DAYTYPE_POSITION_GATE=1** (direction × price-vs-POC/IB) + **DIRECTION_LSMA_VETO=1** +
  **CONT_TREND_FILTER=1** (CONT patterns need a sustained K=3-bar LSMA trend; REV exempt) are the live
  selectivity layer. They can suppress an otherwise-valid fire but do not make a pattern structurally
  unable to fire.
- **OPENING_TYPE_GATE=1** blocks counter-drive fires in the opening window (until IB lock).
- The per-pattern×day-type matrix (`DAYTYPE_PLAYBOOK`) is **inert** (NO-OP while
  DAYTYPE_POSITION_GATE=1) — known hole R1, not a blocker.
- `FEED_WATCHDOG` is **OFF** (SHADOW) — so a stale feed does **not** auto-block fires today; that is
  why the frozen `5min` stream is dangerous in SHADOW (S2 silently produces nothing rather than being
  cleanly halted). It becomes a hard block at LIVE.

---

## Bottom line

- **S4 Woodies: 7 of 9 can fire today** (ZLR, TLB, GB100, VEGAS, GHOST, FAMIR, HTLB) on the live,
  fresh `woodies_5min` feed — subject to the gateway gates + HTLB direction bias + NONTREND/Nontrend.
  **HFE is intentionally disabled** (flag). **TT is wired+fed but never fires** (too-strict 3-bar CCI
  trigger).
- **S2 Five-Min: blocked at the feed.** All 10 detectors are wired and route to the gateway, but the
  `5min` BarRouter channel (sole S2 input + CVD source) **froze 06-29 10:00 CT and shows no recovery**;
  it is RTH-only so its pre-market emptiness is not itself proof of recovery — **must be re-checked at
  08:30 CT today**. Independently, the 4 S2 chart patterns (HnS×2, Double×2) **have never fired due to
  over-strict detection geometry** (5% shoulder symmetry; Eve ≥3-bar / Adam ≤2-bar width), NOT a
  day-type or `chart_patterns_allowed` gate.
- **Never-fired root cause (the explicit ask):** HnS×2 and Double×2 are fully wired and the day-type
  gate is OPEN (S2_CHART_ALL_DAYTYPES=1). They do not require Neutral days and there is no
  `chart_patterns_allowed` block on non-Nontrend days. They simply **never satisfy their Bulkowski
  geometry thresholds on 5-min MES** — shoulder/​trough symmetry + width constraints are calibrated too
  tight (files cited in §C/§D; both marked "SHADOW-calibratable").

**Action items for Michael (not changed here — strategic):**
1. **Pre-LIVE blocker:** confirm the `5min` stream resumes at today's RTH open; if `v9_bars_5min` is
   still frozen after 08:30 CT, S2 is fully dark. (Diagnose the bridge `5min` stream, distinct from the
   healthy `woodies_5min` stream.)
2. If HnS/Double/TT are wanted live, their detection constants need SHADOW recalibration (loosen
   shoulder symmetry / trough-width; relax the TT 3-bar CCI conjunction) — a trading-logic change →
   sign-off required.
